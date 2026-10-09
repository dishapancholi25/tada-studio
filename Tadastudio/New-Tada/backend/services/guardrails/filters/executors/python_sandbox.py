"""Sandboxed Python code executor for user-defined filters.

Executes user-written Python filter functions with restricted capabilities:
- AST validation allows imports only from the ALLOWED_MODULES allowlist
- Curated builtins whitelist (no file I/O, no system access)
- Allowlisted modules are pre-imported and injected into the sandbox globals
- Thread-based timeout (30 seconds) via concurrent.futures
- Output size cap (100K characters)
- Sandbox environment caching: heavy module init (spaCy, PyTorch) happens
  only on the first execution of a given code string; subsequent calls
  reuse the cached globals and filter function.
"""

import ast
import hashlib
import importlib
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Set

from backend.services.guardrail_provisioning import resolve_models_dir

# Where the guardrail models are kept: a repo-local `models/guardrail` folder
# (mirrors the container's /app/models/guardrail), git-ignored, overridable with
# GUARDRAIL_MODELS_DIR. Resolution lives in the shared provisioning module so the
# app, the download script, and local.py all agree on one location.
_CACHE_DIR = resolve_models_dir()
os.environ.setdefault("HF_HOME", _CACHE_DIR)
os.environ.setdefault("TRANSFORMERS_CACHE", os.path.join(_CACHE_DIR, "transformers"))
os.environ.setdefault("TORCH_HOME", os.path.join(_CACHE_DIR, "torch"))
os.environ.setdefault("XDG_CACHE_HOME", _CACHE_DIR)

logger = logging.getLogger(__name__)

# Modules allowed for import in user filter code.
# Each entry maps a top-level module name to the set of submodules permitted.
# An empty set means only the top-level module is allowed (e.g. "re").
# Add entries here to expand what filter authors can use.
ALLOWED_MODULES: Dict[str, Set[str]] = {
    "re": set(),
    "json": set(),
    "math": set(),
    "datetime": set(),
    "hashlib": set(),
    "unicodedata": set(),
    "string": set(),
    "collections": set(),
    "presidio_analyzer": set(),
    "presidio_anonymizer": set(),
    "detoxify": set(),
}

# Modules that should NOT be eagerly imported at sandbox init time because
# they are heavyweight (load ML models, large dependencies like spaCy/PyTorch).
# These are still allowed — they just get imported on-demand when user code
# actually calls `import <module>`, via the _safe_import function.
LAZY_MODULES: Set[str] = {
    "presidio_analyzer",
    "presidio_anonymizer",
    "detoxify",
}


def preload_heavy_modules() -> None:
    """Pre-build sandbox caches for heavyweight filter templates.

    Called once at application startup (in a background thread).  Rather
    than just importing modules, this executes the known heavy filter
    code strings through :class:`PythonSandboxExecutor` so the entire
    sandbox — imports, model loading, compiled filter function — is
    cached and ready before the first real request arrives.

    Because ``spacy.load()`` and ``AnalyzerEngine()`` are expensive on
    every call (~4-10 s), simply importing the module is not enough;
    we must run the same code the user filter will run so the sandbox
    cache (keyed by code hash) is pre-populated.
    """
    executor = get_shared_sandbox_executor()

    # Warm the sandbox for every Python code filter currently saved in
    # guardrail policies.  This covers all user-customised variants of the
    # Presidio / Detoxify templates as well as any bespoke filters.
    try:
        from backend.services.guardrails.policy_service import GuardrailPolicyService

        policies = GuardrailPolicyService.list_policies(
            user_id="__system__", is_admin=True
        )
        code_strings: Dict[str, str] = {}  # deduplicate by hash

        for policy in policies:
            config = policy.get("config", {})
            for filt in config.get("custom_filters", []):
                code = filt.get("python_code", "")
                if code.strip() and filt.get("filter_type") == "python_code":
                    key = hashlib.sha256(code.encode()).hexdigest()[:12]
                    code_strings[key] = code

        for key, code in code_strings.items():
            try:
                executor._get_or_build_sandbox(code)
                logger.info("Pre-warmed sandbox cache for filter code %s", key)
            except Exception:
                logger.warning(
                    "Failed to pre-warm sandbox for filter code %s",
                    key,
                    exc_info=True,
                )

        if code_strings:
            logger.info(
                "Sandbox pre-warm complete: %d unique filter(s)", len(code_strings)
            )
        else:
            logger.info("No Python code filters found — sandbox pre-warm skipped")
    except Exception:
        logger.warning(
            "Sandbox pre-warm failed (could not load policies)", exc_info=True
        )


# Module-level singleton so the pre-warmed cache is shared with the
# evaluator's executor.  The CustomFilterEvaluator should use
# ``get_shared_sandbox_executor()`` instead of creating its own instance.
_shared_executor: "PythonSandboxExecutor | None" = None


def get_shared_sandbox_executor() -> "PythonSandboxExecutor":
    """Return the process-wide PythonSandboxExecutor singleton.

    The singleton is created lazily on first access.  When
    ``preload_heavy_modules()`` runs at startup it populates this
    instance's cache, so later callers get pre-warmed sandboxes.
    """
    global _shared_executor
    if _shared_executor is None:
        _shared_executor = PythonSandboxExecutor()
    return _shared_executor


# Builtins allowed in the sandbox
SAFE_BUILTINS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "frozenset": frozenset,
    "range": range,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "sorted": sorted,
    "reversed": reversed,
    "min": min,
    "max": max,
    "sum": sum,
    "abs": abs,
    "round": round,
    "isinstance": isinstance,
    "type": type,
    "hasattr": hasattr,
    "any": any,
    "all": all,
    "print": print,
    "True": True,
    "False": False,
    "None": None,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "KeyError": KeyError,
    "IndexError": IndexError,
    "Exception": Exception,
}

# AST node types that are always forbidden (imports checked separately via allowlist)
FORBIDDEN_NODES = {
    ast.Global,
    ast.Nonlocal,
    ast.AsyncFunctionDef,
    ast.AsyncFor,
    ast.AsyncWith,
}

# Attribute/name strings that are forbidden
FORBIDDEN_NAMES = {
    "exec",
    "eval",
    "compile",
    "globals",
    "locals",
    "vars",
    "__import__",
    "open",
    "breakpoint",
    "exit",
    "quit",
    "input",
    "memoryview",
    "bytearray",
    "bytes",
}


class CodeValidationError(Exception):
    """Raised when user code fails AST validation."""


class FilterTimeoutError(Exception):
    """Raised when user code exceeds execution time limit."""


@dataclass
class _CachedSandbox:
    """Cached sandbox environment for a specific code string."""

    filter_fn: Callable[..., Dict[str, Any]]
    globals: Dict[str, Any] = field(repr=False)


class PythonSandboxExecutor:
    """Execute user-defined Python filter functions in a restricted sandbox.

    Caches the initialised sandbox environment (globals, loaded models,
    filter function) keyed by a SHA-256 hash of the code string.  The first
    execution of a given code string pays the full model-loading cost;
    subsequent calls reuse the cached state and only invoke the filter
    function, making them near-instant.
    """

    MAX_EXECUTION_TIME_SECONDS = 30
    MAX_OUTPUT_SIZE = 100_000
    MAX_CACHE_SIZE = 64

    def __init__(self) -> None:
        self._sandbox_cache: Dict[str, _CachedSandbox] = {}
        self._build_lock = threading.Lock()  # Prevent concurrent spaCy model loading

    @staticmethod
    def _import_allowed_modules() -> Dict[str, Any]:
        """Pre-import lightweight allowlisted modules into sandbox globals.

        Heavy modules listed in LAZY_MODULES are skipped here — they are
        imported on-demand when user code executes an import statement,
        via the _safe_import function provided as __import__.
        """
        modules: Dict[str, Any] = {}
        for module_name in ALLOWED_MODULES:
            if module_name in LAZY_MODULES:
                continue
            try:
                modules[module_name] = importlib.import_module(module_name)
            except ImportError:
                logger.warning(
                    "Allowed module '%s' could not be imported — skipping", module_name
                )
        return modules

    def _validate_import(self, node: ast.AST) -> List[str]:
        """Check an import node against the allowlist. Returns errors for disallowed imports."""
        errors: List[str] = []
        allowed = ALLOWED_MODULES

        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                if top_level not in allowed:
                    errors.append(
                        f"Import not allowed: '{alias.name}'. "
                        f"Allowed modules: {', '.join(sorted(allowed))}"
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top_level = module.split(".")[0]
            if top_level not in allowed:
                errors.append(
                    f"Import not allowed: 'from {module} import ...'. "
                    f"Allowed modules: {', '.join(sorted(allowed))}"
                )
            elif allowed[top_level] and module not in allowed[top_level]:
                errors.append(
                    f"Submodule not allowed: '{module}'. "
                    f"Allowed submodules for {top_level}: {', '.join(sorted(allowed[top_level]))}"
                )

        return errors

    def validate_code(self, code: str) -> List[str]:
        """AST-validate code before execution.

        Returns:
            List of validation errors (empty if valid)
        """
        errors: List[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [f"Syntax error at line {e.lineno}: {e.msg}"]

        for node in ast.walk(tree):
            # Check forbidden node types
            if type(node) in FORBIDDEN_NODES:
                errors.append(
                    f"Forbidden construct: {type(node).__name__} (global/nonlocal/async not allowed)"
                )

            # Validate imports against allowlist
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                errors.extend(self._validate_import(node))

            # Check forbidden attribute access (dunder attributes)
            if (
                isinstance(node, ast.Attribute)
                and node.attr.startswith("__")
                and node.attr.endswith("__")
            ):
                errors.append(f"Forbidden attribute access: {node.attr}")

            # Check forbidden names
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                errors.append(f"Forbidden name: {node.id}")

            # Check Await nodes separately (not in FORBIDDEN_NODES since it's an expression)
            if isinstance(node, ast.Await):
                errors.append("Forbidden construct: Await (async not allowed)")

        return errors

    @staticmethod
    def _code_hash(code: str) -> str:
        """Return a stable hash for a code string, used as cache key."""
        return hashlib.sha256(code.encode()).hexdigest()

    def _get_or_build_sandbox(self, code: str) -> _CachedSandbox:
        """Return a cached sandbox for *code*, or build and cache a new one.

        The first call for a given code string compiles and executes the
        top-level statements (imports, model loading, etc.) and caches the
        resulting globals dict and filter function.  Subsequent calls with
        the same code skip all of that and return the cached sandbox
        immediately.

        Uses a lock to prevent concurrent spaCy/Presidio model loading which
        causes 'Artifact already registered' errors.
        """
        key = self._code_hash(code)
        cached = self._sandbox_cache.get(key)
        if cached is not None:
            logger.debug("Sandbox cache HIT for %s", key[:12])
            return cached

        # Use lock to prevent concurrent sandbox building (spaCy model loading is not thread-safe)
        with self._build_lock:
            # Double-check after acquiring lock
            cached = self._sandbox_cache.get(key)
            if cached is not None:
                logger.debug("Sandbox cache HIT (after lock) for %s", key[:12])
                return cached

            logger.info(
                "Sandbox cache MISS for %s — building (keys in cache: %s)",
                key[:12],
                [k[:12] for k in self._sandbox_cache],
            )
            # --- Build a fresh sandbox environment ---
            imported_modules = self._import_allowed_modules()

            def _safe_import(name: str, *args: Any, **kwargs: Any) -> Any:
                """Import function that only allows modules from the allowlist."""
                top_level = name.split(".")[0]
                if top_level not in ALLOWED_MODULES:
                    raise ImportError(
                        f"Import not allowed: '{name}'. Allowed: {', '.join(sorted(ALLOWED_MODULES))}"
                    )
                return importlib.import_module(name)

            builtins_with_import = {**SAFE_BUILTINS, "__import__": _safe_import}
            restricted_globals: Dict[str, Any] = {
                "__builtins__": builtins_with_import,
                **imported_modules,
            }
            restricted_locals: Dict[str, Any] = {}

            # Compile
            try:
                compiled = compile(code, "<filter>", "exec")
            except SyntaxError as e:
                raise CodeValidationError(f"Compilation error: {e}") from e

            # Execute code definition (imports, model loading, etc.) with timeout
            def _exec_code() -> None:
                exec(compiled, restricted_globals, restricted_locals)  # noqa: S102

            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_exec_code)
                try:
                    future.result(timeout=self.MAX_EXECUTION_TIME_SECONDS)
                except FuturesTimeoutError as e:
                    raise FilterTimeoutError(
                        f"Filter code definition exceeded {self.MAX_EXECUTION_TIME_SECONDS}s timeout"
                    ) from e
                except Exception as e:
                    raise ValueError(
                        f"Code execution error: {type(e).__name__}: {e}"
                    ) from e

            # Merge locals into globals so that names created by import
            # statements are visible inside the filter function.
            restricted_globals.update(restricted_locals)

            filter_fn = restricted_locals.get("filter")
            if not callable(filter_fn):
                raise ValueError(
                    "Code must define a 'filter(content, direction)' function"
                )

            # Evict oldest entry if cache is full
            if len(self._sandbox_cache) >= self.MAX_CACHE_SIZE:
                oldest_key = next(iter(self._sandbox_cache))
                del self._sandbox_cache[oldest_key]

            sandbox = _CachedSandbox(filter_fn=filter_fn, globals=restricted_globals)
            self._sandbox_cache[key] = sandbox
            return sandbox

    def invalidate_cache(self, code: str | None = None) -> None:
        """Drop cached sandbox(es).  Pass *code* to drop one, or None to clear all."""
        if code is None:
            self._sandbox_cache.clear()
        else:
            self._sandbox_cache.pop(self._code_hash(code), None)

    def execute(
        self, code: str, content: str, direction: str, **context
    ) -> Dict[str, Any]:
        """Execute a user filter function in the sandbox.

        The user code must define a function:
            def filter(content: str, direction: str, **context) -> dict

        The function should return a dict with:
            - "passed": bool — True if content passes the filter
            - "message": str — Description of the result (optional)
            - "content": str — Modified content (required for transform action)

        On the first call for a given *code* string, the full code body is
        executed (imports, model loading, etc.) and the result is cached.
        Subsequent calls with identical code skip initialisation and call
        the filter function directly.

        Args:
            code: Python source code defining a filter() function
            content: The content to filter
            direction: "ingress" or "egress"
            **context: Additional context passed to the filter function (e.g., action="warn")

        Returns:
            Dict with filter result

        Raises:
            CodeValidationError: If code fails AST validation
            FilterTimeoutError: If execution exceeds time limit
            ValueError: If code doesn't define a valid filter function
        """
        # Step 1: Validate
        errors = self.validate_code(code)
        if errors:
            raise CodeValidationError(f"Code validation failed: {'; '.join(errors)}")

        # Step 2: Get or build cached sandbox (first call loads models, later calls are instant)
        sandbox = self._get_or_build_sandbox(code)

        # Step 3: Call the filter function with timeout
        def _call_filter() -> Dict[str, Any]:
            return sandbox.filter_fn(content, direction, **context)

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_call_filter)
            try:
                result = future.result(timeout=self.MAX_EXECUTION_TIME_SECONDS)
            except FuturesTimeoutError as e:
                raise FilterTimeoutError(
                    f"Filter execution exceeded {self.MAX_EXECUTION_TIME_SECONDS}s timeout"
                ) from e
            except Exception as e:
                raise ValueError(
                    f"Filter function error: {type(e).__name__}: {e}"
                ) from e

        # Step 4: Validate result
        if not isinstance(result, dict):
            raise ValueError(
                f"Filter function must return a dict, got {type(result).__name__}"
            )

        # Enforce output size limit
        result_content = result.get("content", "")
        if (
            isinstance(result_content, str)
            and len(result_content) > self.MAX_OUTPUT_SIZE
        ):
            raise ValueError(
                f"Filter output exceeds {self.MAX_OUTPUT_SIZE} character limit"
            )

        return result
