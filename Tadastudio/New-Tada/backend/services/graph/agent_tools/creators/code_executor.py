"""Code executor tool creator for agents.

This module creates code execution tool instances that agents can use
to execute Python or JavaScript code dynamically.

The agent can call execute_code() to run code and get results.
"""

from typing import Any, Callable, Optional, Set

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


class ExecuteCodeInput(BaseModel):
    """Input schema for execute_code tool."""

    code: Optional[str] = Field(
        default=None,
        description="Python code to execute. If not provided, uses the pre-configured code from the node. Must set a 'result' variable with the output value."
    )
    language: str = Field(
        default="python",
        description="Programming language: 'python' or 'javascript'"
    )
    input_data: Optional[dict] = Field(
        default=None,
        description="Input data to pass to the code. Available as 'input' variable in the code namespace."
    )


def create_code_executor_tool_from_node(
    target_node: EnhancedNodeData,
    used_tool_names: Optional[Set[str]] = None,
    node_execution_id_provider: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[Any]:
    """Create a code execution tool from a CODE_EXECUTOR node.

    Args:
        target_node: The CODE_EXECUTOR node configuration
        used_tool_names: Optional set to track used tool names for collision detection
        node_execution_id_provider: Callback to get node_execution_id at runtime

    Returns:
        Code executor tool instance, or None if configuration is invalid
    """
    logger.info(f"Creating code executor tool from node: {target_node.name}")

    # Get config (may be None for default behavior)
    config = target_node.code_executor_config

    # Extract settings from config
    if config:
        if isinstance(config, dict):
            timeout_seconds = config.get("timeout_seconds", 30)
            memory_limit_mb = config.get("memory_limit_mb", 256)
            default_language = config.get("language", "python")
            preconfigured_code = config.get("code", None)
        else:
            timeout_seconds = getattr(config, "timeout_seconds", 30)
            memory_limit_mb = getattr(config, "memory_limit_mb", 256)
            default_language = getattr(config, "language", "python")
            preconfigured_code = getattr(config, "code", None)
    else:
        timeout_seconds = 30
        memory_limit_mb = 256
        default_language = "python"
        preconfigured_code = None

    # Build semantic tool name from node name
    tool_name = build_tool_name(
        tool_type_prefix="execute_code",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="Code Executor",
        used_names=used_tool_names,
    )

    # Build description
    description = (
        f"Execute Python or JavaScript code dynamically. "
        f"Node: '{target_node.name}'. "
    )
    if target_node.description:
        description += f"{target_node.description}. "

    if preconfigured_code:
        description += (
            "This tool has PRE-CONFIGURED code. Just call it with input_data parameter - no need to provide code. "
            "Pass input_data with the file content or data to process. "
        )
    else:
        description += (
            "The code must set a 'result' variable with the output value. "
            "Pass data via input_data parameter - available as 'input' variable in code. "
        )

    # Create the execution function
    def execute_code_func(code: Optional[str] = None, language: str = "python", input_data: Optional[dict] = None) -> dict:
        """Execute code and return result."""
        import asyncio
        import concurrent.futures
        from backend.services.code_execution import get_code_execution_service

        # Use pre-configured code if no code provided
        actual_code = code if code else preconfigured_code

        if not actual_code:
            return {
                "success": False,
                "output": None,
                "error": "No code provided and no pre-configured code available in the node.",
                "stdout": "",
                "stderr": "",
            }

        logger.info(f"[CODE_EXECUTOR_TOOL] Executing {language} code ({len(actual_code)} chars), input_data: {bool(input_data)}")

        # Prepare variables to inject into code namespace
        variables = {"input": input_data or {}}

        try:
            service = get_code_execution_service()

            # Define the async execution
            async def run_code():
                return await service.execute(
                    language=language,
                    code=actual_code,
                    variables=variables,
                    output_variable="result",
                    timeout_seconds=timeout_seconds,
                    memory_limit_mb=memory_limit_mb,
                )

            # Always use a thread pool with asyncio.run() for clean event loop
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, run_code())
                result = future.result(timeout=timeout_seconds + 10)

            return result.to_dict()

        except Exception as e:
            logger.error(f"[CODE_EXECUTOR_TOOL] Error: {e}")
            return {
                "success": False,
                "output": None,
                "error": str(e),
                "stdout": "",
                "stderr": "",
            }

    # Create the tool
    tool = StructuredTool.from_function(
        func=execute_code_func,
        name=tool_name,
        description=description,
        args_schema=ExecuteCodeInput,
        return_direct=False,
    )

    # Attach metadata for tracking
    tool._node_id = target_node.uniq_id
    tool._node_name = target_node.name
    tool._node_type = target_node.type

    logger.info(f"Created code executor tool: {tool_name}")
    return tool
