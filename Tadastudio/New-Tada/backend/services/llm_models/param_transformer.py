"""Config-driven model parameter transformation.

Loads transformation rules from model_params_config.json and applies them
before parameters are passed to LangChain provider constructors. This allows
parameter renaming, dropping, and defaults to be managed without code changes.

Usage:
    from backend.services.llm_models.param_transformer import get_param_transformer

    transformer = get_param_transformer()
    result = transformer.transform(
        provider="openai",
        model_name="o3-mini",
        params={"max_tokens": 4096, "temperature": 0.7},
    )
    # result.direct_params  -> params to pass directly to constructor
    # result.model_kwargs   -> params to pass via model_kwargs dict
    # result.dropped_params -> params that were dropped (for logging)
"""

import json
import logging
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "model_params_config.json"


@dataclass
class TransformResult:
    """Result of applying parameter transformations."""

    direct_params: Dict[str, Any] = field(default_factory=dict)
    model_kwargs: Dict[str, Any] = field(default_factory=dict)
    dropped_params: List[str] = field(default_factory=list)


class ModelParamTransformer:
    """Applies config-driven parameter transformations for LLM providers."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._config: Dict[str, Any] = {}
        self._load_config(config_path or _CONFIG_PATH)

    def _load_config(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                self._config = json.load(fh)
            logger.info(
                "Model param transformer: loaded config v%s from %s",
                self._config.get("version", "unknown"),
                path,
            )
        except Exception as exc:
            logger.warning(
                "Model param transformer: failed to load config from %s: %s",
                path,
                exc,
            )
            self._config = {"providers": {}}

    # ------------------------------------------------------------------
    # API version parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_version(version_str: str) -> Optional[Tuple[int, ...]]:
        """Parse a date-style version string like '2024-10-01' or '2025-01-01-preview' into a tuple.

        Only the leading numeric segments are used; trailing non-numeric
        suffixes (e.g. '-preview') are ignored.
        """
        try:
            parts = version_str.strip().split("-")
            numeric: list[int] = []
            for p in parts:
                try:
                    numeric.append(int(p))
                except ValueError:
                    break
            return tuple(numeric) if numeric else None
        except AttributeError:
            return None

    # ------------------------------------------------------------------
    # Rule resolution
    # ------------------------------------------------------------------

    def _resolve_rules(
        self, provider: str, model_name: str, api_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve the effective rules for a provider+model+api_version combination.

        Pipeline order:
        1. api_version_rules  — infrastructure constraints (applied first)
        2. Model-level rules  — override provider-level defaults
        """
        provider_cfg = self._config.get("providers", {}).get(provider, {})
        if not provider_cfg:
            return {}

        # Start with provider-level defaults
        rules: Dict[str, Any] = {
            "param_transforms": dict(provider_cfg.get("param_transforms", {})),
            "drop_params": list(provider_cfg.get("drop_params", [])),
            "force_params": dict(provider_cfg.get("force_params", {})),
            "defaults": dict(provider_cfg.get("defaults", {})),
        }

        # Resolve API version rules (merged, all matching rules cumulate)
        if api_version:
            parsed_version = self._parse_version(api_version)
            if parsed_version and len(parsed_version) == 3:
                api_drop: List[str] = []
                api_force: Dict[str, Any] = {}
                for rule in provider_cfg.get("api_version_rules", []):
                    min_ver = self._parse_version(rule.get("min_version", ""))
                    if min_ver and len(min_ver) == 3 and parsed_version >= min_ver:
                        api_drop.extend(rule.get("drop_params", []))
                        api_force.update(rule.get("force_params", {}))
                # API version rules are prepended so they run first
                rules["api_version_drop_params"] = api_drop
                rules["api_version_force_params"] = api_force

        # Find matching model pattern (longest pattern = most specific)
        models_cfg = provider_cfg.get("models", {})
        name_lower = model_name.lower().strip()
        best_pattern: Optional[str] = None
        best_len = -1

        for pattern in models_cfg:
            if fnmatch(name_lower, pattern.lower()) and len(pattern) > best_len:
                best_pattern = pattern
                best_len = len(pattern)

        if best_pattern is not None:
            model_rules = models_cfg[best_pattern]
            # Model-level rules fully replace provider-level for each key present
            if "param_transforms" in model_rules:
                rules["param_transforms"] = dict(model_rules["param_transforms"])
            if "drop_params" in model_rules:
                rules["drop_params"] = list(model_rules["drop_params"])
            if "force_params" in model_rules:
                rules["force_params"] = dict(model_rules["force_params"])
            if "defaults" in model_rules:
                rules["defaults"] = dict(model_rules["defaults"])

        return rules

    # ------------------------------------------------------------------
    # Transform
    # ------------------------------------------------------------------

    def transform(
        self,
        provider: str,
        model_name: str,
        params: Dict[str, Any],
        api_version: Optional[str] = None,
    ) -> TransformResult:
        """Apply transformation rules to a set of parameters.

        Args:
            provider: Provider name (e.g. "openai", "azure_openai").
            model_name: Model name (e.g. "o3-mini", "gpt-4o").
            params: Input parameters (e.g. {"max_tokens": 4096, "temperature": 0.7}).
            api_version: Optional API version string (e.g. "2024-10-01").
                         Used to match api_version_rules for the provider.

        Returns:
            TransformResult with direct_params, model_kwargs, and dropped_params.
        """
        rules = self._resolve_rules(provider, model_name, api_version)
        if not rules:
            return TransformResult(direct_params=dict(params))

        result = TransformResult()
        working = dict(params)

        # 1. API version drops (infrastructure constraints, applied first)
        for param_name in rules.get("api_version_drop_params", []):
            if param_name in working and working[param_name] is not None:
                working.pop(param_name)
                result.dropped_params.append(param_name)
                logger.debug(
                    "Model param transformer: %s (api_version) dropped %s",
                    provider,
                    param_name,
                )

        # 2. API version force (override values for infrastructure constraints)
        for param_name, forced_value in rules.get(
            "api_version_force_params", {}
        ).items():
            if param_name in working and working[param_name] != forced_value:
                logger.debug(
                    "Model param transformer: %s (api_version) forced %s=%s (was %s)",
                    provider,
                    param_name,
                    forced_value,
                    working[param_name],
                )
                working[param_name] = forced_value

        # 3. Apply renames (model-level)
        for param_name, transform_spec in rules.get("param_transforms", {}).items():
            if param_name not in working or working[param_name] is None:
                continue

            value = working.pop(param_name)
            target_name = transform_spec.get("rename_to", param_name)
            via = transform_spec.get("via")

            if via == "model_kwargs":
                result.model_kwargs[target_name] = value
            else:
                working[target_name] = value

            logger.debug(
                "Model param transformer: %s/%s renamed %s -> %s%s",
                provider,
                model_name,
                param_name,
                target_name,
                f" (via {via})" if via else "",
            )

        # 4. Drop unsupported params (model-level)
        for param_name in rules.get("drop_params", []):
            if param_name in working and working[param_name] is not None:
                working.pop(param_name)
                result.dropped_params.append(param_name)
                logger.debug(
                    "Model param transformer: %s/%s dropped %s",
                    provider,
                    model_name,
                    param_name,
                )

        # 5. Force params (model-level)
        for param_name, forced_value in rules.get("force_params", {}).items():
            if param_name in working and working[param_name] != forced_value:
                working[param_name] = forced_value

        # 6. Apply defaults for missing params
        for param_name, default_value in rules.get("defaults", {}).items():
            if param_name not in working or working[param_name] is None:
                working[param_name] = default_value

        result.direct_params = working
        return result

    def reload(self, config_path: Optional[Path] = None) -> None:
        """Reload the config file (e.g. after an update)."""
        self._load_config(config_path or _CONFIG_PATH)


# Module-level singleton
_transformer: Optional[ModelParamTransformer] = None


def get_param_transformer() -> ModelParamTransformer:
    """Return the module-level singleton transformer."""
    global _transformer
    if _transformer is None:
        _transformer = ModelParamTransformer()
    return _transformer
