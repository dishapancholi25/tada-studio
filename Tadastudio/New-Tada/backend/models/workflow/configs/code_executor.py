"""Configuration for CODE_EXECUTOR nodes.

This module defines the configuration dataclass for code execution nodes
that can run Python or JavaScript code within workflows.

CODE_EXECUTOR nodes allow users to write custom code that:
- Receives input from previous nodes via the `input` variable
- Can access workflow state through mapped variables
- Returns output via the `result` variable (configurable)
- Supports both Python and JavaScript execution

Example workflow usage:
    1. FILE_READ node reads a PDF file
    2. CODE_EXECUTOR receives PDF content in `input` variable
    3. Code processes the data and sets `result`
    4. Next node receives the result

Input Variable Behavior:
    - If no input_variables configured: previous node output is passed as `input`
    - User can add custom mappings in Variables tab
    - Static values, previous output, or specific node outputs supported

Output Variable:
    - Default: `result` - code should set this variable
    - Can be customized in config
    - Value is passed to next node in workflow
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class CodeExecutorConfig:
    """Configuration for CODE_EXECUTOR nodes.

    Attributes:
        language: Programming language to execute ('python' or 'javascript')
        code: The source code to execute
        timeout_seconds: Maximum execution time in seconds
        memory_limit_mb: Maximum memory usage in MB

        # Permissions (configurable security settings)
        allow_network: Whether code can make network requests
        allow_filesystem: Whether code can access the filesystem
        allow_subprocess: Whether code can spawn subprocesses
        allowed_packages: List of Python packages that can be imported

        # Input/Output mapping
        input_variables: Variables to pass from workflow state to code
        output_variable: Name of variable to capture as output

        # Advanced settings
        working_directory: Working directory for code execution
        environment_variables: Environment variables to set
        capture_stdout: Whether to capture stdout in output
        capture_stderr: Whether to capture stderr in output
    """

    language: Literal["python", "javascript"] = "python"
    code: str = ""
    timeout_seconds: int = 30
    memory_limit_mb: int = 256

    # Permissions
    allow_network: bool = True
    allow_filesystem: bool = True
    allow_subprocess: bool = False
    allowed_packages: List[str] = field(default_factory=list)

    # Input/Output mapping
    input_variables: List[Dict[str, Any]] = field(default_factory=list)
    output_variable: str = "result"

    # Advanced settings
    working_directory: Optional[str] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    capture_stdout: bool = True
    capture_stderr: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeExecutorConfig":
        """Create config from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            CodeExecutorConfig instance
        """
        return cls(
            language=data.get("language", "python"),
            code=data.get("code", ""),
            timeout_seconds=data.get("timeout_seconds", 30),
            memory_limit_mb=data.get("memory_limit_mb", 256),
            allow_network=data.get("allow_network", True),
            allow_filesystem=data.get("allow_filesystem", True),
            allow_subprocess=data.get("allow_subprocess", False),
            allowed_packages=data.get("allowed_packages", []),
            input_variables=data.get("input_variables", []),
            output_variable=data.get("output_variable", "result"),
            working_directory=data.get("working_directory"),
            environment_variables=data.get("environment_variables", {}),
            capture_stdout=data.get("capture_stdout", True),
            capture_stderr=data.get("capture_stderr", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary.

        Returns:
            Dictionary representation of config
        """
        return {
            "language": self.language,
            "code": self.code,
            "timeout_seconds": self.timeout_seconds,
            "memory_limit_mb": self.memory_limit_mb,
            "allow_network": self.allow_network,
            "allow_filesystem": self.allow_filesystem,
            "allow_subprocess": self.allow_subprocess,
            "allowed_packages": self.allowed_packages,
            "input_variables": self.input_variables,
            "output_variable": self.output_variable,
            "working_directory": self.working_directory,
            "environment_variables": self.environment_variables,
            "capture_stdout": self.capture_stdout,
            "capture_stderr": self.capture_stderr,
        }


@dataclass
class InputVariableMapping:
    """Mapping for passing workflow state to code variables.

    Attributes:
        variable_name: Name of variable in code
        source_mode: How to get the value ('previous', 'specific', 'static', 'original_input')
        source_node_id: Node ID to get value from (for 'specific' mode)
        source_field_path: Path to field in source node output
        static_value: Static value (for 'static' mode)
        default_value: Default if source not found
    """

    variable_name: str = ""
    source_mode: Literal["previous", "specific", "static", "original_input"] = "previous"
    source_node_id: Optional[str] = None
    source_field_path: Optional[str] = None
    static_value: Optional[str] = None
    default_value: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputVariableMapping":
        """Create mapping from dictionary."""
        return cls(
            variable_name=data.get("variable_name", ""),
            source_mode=data.get("source_mode", "previous"),
            source_node_id=data.get("source_node_id"),
            source_field_path=data.get("source_field_path"),
            static_value=data.get("static_value"),
            default_value=data.get("default_value"),
        )
