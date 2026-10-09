"""Code execution service for running Python and JavaScript code.

This module provides secure code execution with:
- Timeout handling
- Memory limits
- Input/output mapping
- Stdout/stderr capture
- Configurable permissions
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from backend.services.config import get_logger


logger = get_logger("code_execution")


# ---------------------------------------------------------------------------
# ISG Security Finding #2 (Critical, Open):
# "Remote Code Execution via Unsandboxed Code Executor Workflow Node".
#
# The Code Executor node runs arbitrary Python/JavaScript in a local
# subprocess with no real sandbox, which is a Remote Code Execution vector.
# The feature is DISABLED in code (it is also hidden in the UI). It must stay
# disabled until a properly hardened sandbox is in place.
# TODO(security): re-enable only once a hardened sandbox is added.
# ---------------------------------------------------------------------------


@dataclass
class CodeExecutionResult:
    """Result from code execution.

    Attributes:
        success: Whether execution completed successfully
        output: The captured output/result from the code
        stdout: Captured stdout
        stderr: Captured stderr
        error: Error message if execution failed
        execution_time_ms: Execution time in milliseconds
        memory_used_mb: Memory used in MB (if available)
    """

    success: bool = False
    output: Any = None
    stdout: str = ""
    stderr: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "memory_used_mb": self.memory_used_mb,
        }


class CodeExecutionService:
    """Service for executing Python and JavaScript code.

    Provides secure code execution with configurable permissions,
    timeout handling, and input/output mapping.

    Example:
        >>> service = CodeExecutionService()
        >>> result = await service.execute_python(
        ...     code="result = x + y",
        ...     variables={"x": 1, "y": 2},
        ...     output_variable="result",
        ...     timeout_seconds=30,
        ... )
        >>> print(result.output)  # 3
    """

    def __init__(self):
        """Initialize the code execution service."""
        self._temp_dir = tempfile.gettempdir()

    async def execute(
        self,
        language: Literal["python", "javascript"],
        code: str,
        variables: Dict[str, Any] = None,
        output_variable: str = "result",
        timeout_seconds: int = 30,
        memory_limit_mb: int = 256,
        allow_network: bool = True,
        allow_filesystem: bool = True,
        allow_subprocess: bool = False,
        allowed_packages: List[str] = None,
        working_directory: Optional[str] = None,
        environment_variables: Dict[str, str] = None,
        capture_stdout: bool = True,
        capture_stderr: bool = True,
    ) -> CodeExecutionResult:
        """Execute code in the specified language.

        Args:
            language: Programming language ('python' or 'javascript')
            code: Source code to execute
            variables: Variables to pass to the code
            output_variable: Name of variable to capture as output
            timeout_seconds: Maximum execution time
            memory_limit_mb: Maximum memory usage
            allow_network: Whether to allow network access
            allow_filesystem: Whether to allow filesystem access
            allow_subprocess: Whether to allow subprocess spawning
            allowed_packages: List of allowed Python packages
            working_directory: Working directory for execution
            environment_variables: Environment variables to set
            capture_stdout: Whether to capture stdout
            capture_stderr: Whether to capture stderr

        Returns:
            CodeExecutionResult with output and execution details
        """
        # ISG Security Finding #2 (Critical): unsandboxed code execution is an
        # RCE vector. Code execution is disabled in code and must not run.
        logger.warning(
            "[CODE-EXECUTOR] Blocked code execution: Code Executor node is "
            "disabled (ISG Critical finding #2)."
        )
        return CodeExecutionResult(
            success=False,
            error=(
                "Code Executor node is disabled for security reasons "
                "(unsandboxed remote code execution risk)."
            ),
        )

        if language == "python":
            return await self.execute_python(
                code=code,
                variables=variables or {},
                output_variable=output_variable,
                timeout_seconds=timeout_seconds,
                memory_limit_mb=memory_limit_mb,
                allow_network=allow_network,
                allow_filesystem=allow_filesystem,
                allow_subprocess=allow_subprocess,
                allowed_packages=allowed_packages or [],
                working_directory=working_directory,
                environment_variables=environment_variables or {},
                capture_stdout=capture_stdout,
                capture_stderr=capture_stderr,
            )
        elif language == "javascript":
            return await self.execute_javascript(
                code=code,
                variables=variables or {},
                output_variable=output_variable,
                timeout_seconds=timeout_seconds,
                memory_limit_mb=memory_limit_mb,
            )
        else:
            return CodeExecutionResult(
                success=False,
                error=f"Unsupported language: {language}",
            )

    async def execute_python(
        self,
        code: str,
        variables: Dict[str, Any] = None,
        output_variable: str = "result",
        timeout_seconds: int = 30,
        memory_limit_mb: int = 256,
        allow_network: bool = True,
        allow_filesystem: bool = True,
        allow_subprocess: bool = False,
        allowed_packages: List[str] = None,
        working_directory: Optional[str] = None,
        environment_variables: Dict[str, str] = None,
        capture_stdout: bool = True,
        capture_stderr: bool = True,
    ) -> CodeExecutionResult:
        """Execute Python code in a subprocess.

        The code is wrapped in a script that:
        1. Loads input variables from JSON
        2. Executes the user code
        3. Captures the output variable
        4. Returns results as JSON

        Args:
            code: Python code to execute
            variables: Variables to inject into the code namespace
            output_variable: Variable name to capture as output
            timeout_seconds: Maximum execution time
            memory_limit_mb: Maximum memory (not enforced on all platforms)
            allow_network: Whether to allow network access (informational)
            allow_filesystem: Whether to allow filesystem access (informational)
            allow_subprocess: Whether to allow subprocess (informational)
            allowed_packages: List of allowed packages (informational)
            working_directory: Working directory for execution
            environment_variables: Additional environment variables
            capture_stdout: Whether to capture stdout
            capture_stderr: Whether to capture stderr

        Returns:
            CodeExecutionResult with execution results
        """
        import time
        import base64

        start_time = time.time()
        variables = variables or {}

        # Encode code and variables as base64 to avoid quote escaping issues
        code_b64 = base64.b64encode(code.encode('utf-8')).decode('ascii')
        vars_b64 = base64.b64encode(json.dumps(variables).encode('utf-8')).decode('ascii')

        wrapper_code = f'''
import sys
import json
import io
import base64

# Capture stdout/stderr
_stdout_capture = io.StringIO()
_stderr_capture = io.StringIO()
_original_stdout = sys.stdout
_original_stderr = sys.stderr

if {capture_stdout}:
    sys.stdout = _stdout_capture
if {capture_stderr}:
    sys.stderr = _stderr_capture

# Load input variables from base64
_input_vars = json.loads(base64.b64decode("{vars_b64}").decode("utf-8"))

# Create namespace with input variables
_namespace = {{"__builtins__": __builtins__}}
_namespace.update(_input_vars)

_error = None
_output = None

# Load user code from base64
_user_code = base64.b64decode("{code_b64}").decode("utf-8")

try:
    # Compile and execute user code
    _compiled = compile(_user_code, "<user_code>", "exec")
    exec(_compiled, _namespace)

    # Get output variable
    _output = _namespace.get("{output_variable}")

except Exception as e:
    import traceback
    _error = traceback.format_exc()

# Restore stdout/stderr
sys.stdout = _original_stdout
sys.stderr = _original_stderr

# Build result
_result = {{
    "success": _error is None,
    "output": _output,
    "stdout": _stdout_capture.getvalue() if {capture_stdout} else "",
    "stderr": _stderr_capture.getvalue() if {capture_stderr} else "",
    "error": _error,
}}

# Handle non-JSON-serializable output
try:
    print(json.dumps(_result))
except TypeError:
    _result["output"] = str(_output)
    print(json.dumps(_result))
'''

        try:
            env = os.environ.copy()
            if environment_variables:
                env.update(environment_variables)

            cwd = working_directory or self._temp_dir

            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                wrapper_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CodeExecutionResult(
                    success=False,
                    error=f"Execution timed out after {timeout_seconds} seconds",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")

            execution_time_ms = (time.time() - start_time) * 1000

            if process.returncode != 0:
                return CodeExecutionResult(
                    success=False,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    error=f"Process exited with code {process.returncode}: {stderr_str}",
                    execution_time_ms=execution_time_ms,
                )

            try:
                result_data = json.loads(stdout_str.strip().split("\n")[-1])
                return CodeExecutionResult(
                    success=result_data.get("success", False),
                    output=result_data.get("output"),
                    stdout=result_data.get("stdout", ""),
                    stderr=result_data.get("stderr", ""),
                    error=result_data.get("error"),
                    execution_time_ms=execution_time_ms,
                )
            except json.JSONDecodeError as e:
                return CodeExecutionResult(
                    success=False,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    error=f"Failed to parse execution result: {e}",
                    execution_time_ms=execution_time_ms,
                )

        except Exception as e:
            logger.error(f"Python execution error: {e}", exc_info=True)
            return CodeExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    async def execute_javascript(
        self,
        code: str,
        variables: Dict[str, Any] = None,
        output_variable: str = "result",
        timeout_seconds: int = 30,
        memory_limit_mb: int = 256,
    ) -> CodeExecutionResult:
        """Execute JavaScript code using Node.js.

        Falls back to a simple eval-based approach if Node.js is not available.

        Args:
            code: JavaScript code to execute
            variables: Variables to inject
            output_variable: Variable name to capture as output
            timeout_seconds: Maximum execution time
            memory_limit_mb: Maximum memory (for Node.js)

        Returns:
            CodeExecutionResult with execution results
        """
        import time

        start_time = time.time()
        variables = variables or {}

        wrapper_code = f'''
const inputVars = {json.dumps(variables)};

// Inject variables into scope
Object.keys(inputVars).forEach(key => {{
    global[key] = inputVars[key];
}});

let _stdout = [];
let _stderr = [];
const originalLog = console.log;
const originalError = console.error;

console.log = (...args) => _stdout.push(args.map(String).join(' '));
console.error = (...args) => _stderr.push(args.map(String).join(' '));

let _output = null;
let _error = null;

try {{
    {code}
    _output = typeof {output_variable} !== 'undefined' ? {output_variable} : null;
}} catch (e) {{
    _error = e.stack || e.message || String(e);
}}

console.log = originalLog;
console.error = originalError;

const result = {{
    success: _error === null,
    output: _output,
    stdout: _stdout.join('\\n'),
    stderr: _stderr.join('\\n'),
    error: _error
}};

console.log(JSON.stringify(result));
'''

        try:
            process = await asyncio.create_subprocess_exec(
                "node",
                "-e",
                wrapper_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CodeExecutionResult(
                    success=False,
                    error=f"Execution timed out after {timeout_seconds} seconds",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )

            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")
            execution_time_ms = (time.time() - start_time) * 1000

            if process.returncode != 0:
                return CodeExecutionResult(
                    success=False,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    error=f"Node.js exited with code {process.returncode}: {stderr_str}",
                    execution_time_ms=execution_time_ms,
                )

            try:
                lines = stdout_str.strip().split("\n")
                result_data = json.loads(lines[-1])
                return CodeExecutionResult(
                    success=result_data.get("success", False),
                    output=result_data.get("output"),
                    stdout=result_data.get("stdout", ""),
                    stderr=result_data.get("stderr", ""),
                    error=result_data.get("error"),
                    execution_time_ms=execution_time_ms,
                )
            except json.JSONDecodeError as e:
                return CodeExecutionResult(
                    success=False,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    error=f"Failed to parse execution result: {e}",
                    execution_time_ms=execution_time_ms,
                )

        except FileNotFoundError:
            return CodeExecutionResult(
                success=False,
                error="Node.js is not installed or not in PATH. JavaScript execution requires Node.js.",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"JavaScript execution error: {e}", exc_info=True)
            return CodeExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )


_code_execution_service: Optional[CodeExecutionService] = None


def get_code_execution_service() -> CodeExecutionService:
    """Get the singleton code execution service instance.

    Returns:
        CodeExecutionService instance
    """
    global _code_execution_service
    if _code_execution_service is None:
        _code_execution_service = CodeExecutionService()
    return _code_execution_service
