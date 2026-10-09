"""Structured output handler for async agent execution.

This module handles execution of LLMs with structured output constraints,
including schema creation and validation.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from backend.models.workflow import AgentConfig

if TYPE_CHECKING:
    from .tool_executor import AsyncToolExecutor
from backend.services.config import get_logger
from backend.services.structured_output import StructuredOutputGenerator

from .exceptions import StructuredOutputError


# Get logger for this module
structured_output_logger = get_logger("async_agent.structured_output")


class StructuredOutputHandler:
    """Handles structured output execution.

    This class manages LLM execution with structured output constraints,
    creating schemas from configuration and binding them to the LLM.
    """

    def __init__(self):
        """Initialize the structured output handler."""
        self.logger = structured_output_logger
        self.generator = StructuredOutputGenerator()

    async def execute_with_structured_output(
        self,
        llm: BaseChatModel,
        messages: List[BaseMessage],
        agent_config: AgentConfig,
    ) -> Any:
        """Execute LLM with structured output constraints.

        Args:
            llm: The LLM instance
            messages: Input messages for the LLM
            agent_config: Agent configuration with structured output settings

        Returns:
            Structured response from LLM

        Raises:
            StructuredOutputError: If structured output execution fails
        """
        try:
            self.logger.info("[STRUCTURED] Executing with structured output")

            # Get structured output configuration
            structured_outputs = agent_config.structured_outputs
            if not structured_outputs or len(structured_outputs) == 0:
                raise StructuredOutputError(
                    "No structured output configuration found in agent config"
                )

            # Use the first structured output config
            structured_config = structured_outputs[0]

            # Create schema
            schema = self._create_schema(structured_config)

            # Bind schema to LLM via the tool-calling path. The default
            # ``method`` resolves to OpenAI's strict ``json_schema`` route
            # (``beta.chat.completions.parse``), which some Azure gateways
            # answer with ``choices: null`` for schemas containing open
            # ``Dict[str, Any]`` fields. Function-calling is universally
            # supported and tolerates open dicts.
            llm_with_structure = llm.with_structured_output(
                schema, method="function_calling"
            )

            # Execute asynchronously
            self.logger.debug("[STRUCTURED] Invoking LLM with structured output")
            result = await llm_with_structure.ainvoke(messages)

            # Convert structured output result to AIMessage for downstream handling
            if hasattr(result, "model_dump_json"):
                content = result.model_dump_json(indent=2)
            else:
                content = str(result)

            response = AIMessage(
                content=content, additional_kwargs={"structured": True}
            )

            self.logger.info(
                "[STRUCTURED] Successfully executed with structured output"
            )
            return response

        except StructuredOutputError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            error_msg = f"Structured output execution failed: {str(e)}"
            self.logger.error(f"[STRUCTURED] {error_msg}", exc_info=True)
            raise StructuredOutputError(error_msg) from e

    def _create_schema(self, structured_config: Dict[str, Any]) -> Any:
        """Create structured output schema from configuration.

        Args:
            structured_config: Structured output configuration dictionary

        Returns:
            Schema object for LLM binding

        Raises:
            StructuredOutputError: If schema creation fails
        """
        try:
            schema_name = (
                structured_config.get("model_name")
                or structured_config.get("name")
                or "Output"
            )
            schema_fields = structured_config.get("fields", [])
            schema_description = structured_config.get(
                "description", "Structured output schema"
            )
            schema_id = structured_config.get("id")

            if not schema_fields:
                raise StructuredOutputError(
                    f"No fields defined in structured output '{schema_name}'"
                )

            self.logger.debug(
                f"[STRUCTURED] Creating schema '{schema_name}' with {len(schema_fields)} fields"
            )

            schema = self.generator.create_schema(
                model_name=schema_name,
                fields=schema_fields,
                schema_id=schema_id,
                description=schema_description,
            )

            self.logger.debug(
                f"[STRUCTURED] Successfully created schema '{schema_name}'"
            )
            return schema

        except Exception as e:
            error_msg = f"Failed to create structured output schema: {str(e)}"
            self.logger.error(f"[STRUCTURED] {error_msg}", exc_info=True)
            raise StructuredOutputError(error_msg) from e

    def should_use_structured_output(
        self,
        agent_config: AgentConfig,
        format_output: bool = True,
    ) -> bool:
        """Check if structured output should be used.

        Args:
            agent_config: Agent configuration
            format_output: Whether output formatting is enabled

        Returns:
            True if structured output should be used, False otherwise
        """
        if not format_output:
            return False

        if not hasattr(agent_config, "structured_outputs"):
            return False

        if not agent_config.structured_outputs:
            return False

        if len(agent_config.structured_outputs) == 0:
            return False

        return True

    async def execute_with_tools_then_format(
        self,
        llm: BaseChatModel,
        messages: List[BaseMessage],
        tools: List[Any],
        agent_config: AgentConfig,
        tool_executor: "AsyncToolExecutor",
        tool_execution_tracker: Optional[List] = None,
        agent_name: str = "",
        **kwargs,
    ) -> AIMessage:
        """Execute with tools first (Phase 1), then format with structured output (Phase 2).

        This enables both tool calling (including sub-agent delegation) AND structured
        output in the same agent execution.

        Args:
            llm: The LLM instance
            messages: Input messages for the LLM
            tools: List of tools to bind
            agent_config: Agent configuration with structured output settings
            tool_executor: AsyncToolExecutor instance for tool execution
            tool_execution_tracker: Optional tracker for tool executions
            agent_name: Name of the agent (for logging)
            **kwargs: Additional kwargs for tool_executor (ws_notifier, execution_id, etc.)

        Returns:
            AIMessage with JSON-formatted structured output

        Raises:
            StructuredOutputError: If execution fails
        """
        try:
            self.logger.info(
                f"[STRUCTURED] Two-phase execution for {agent_name}: tools then format"
            )

            # Phase 1: Execute with tools (ReAct pattern)
            self.logger.debug("[STRUCTURED] Phase 1: Executing with tools")
            tool_response = await tool_executor.execute_with_tools(
                llm, messages, tools, tool_execution_tracker, agent_name, **kwargs
            )

            self.logger.debug(
                f"[STRUCTURED] Phase 1 complete. Response length: "
                f"{len(tool_response.content) if hasattr(tool_response, 'content') else 'N/A'}"
            )

            # Phase 2: Format the tool response with structured output
            self.logger.debug("[STRUCTURED] Phase 2: Formatting with structured output")

            # Get structured output config
            structured_outputs = agent_config.structured_outputs
            if not structured_outputs or len(structured_outputs) == 0:
                raise StructuredOutputError(
                    "No structured output configuration found in agent config"
                )

            structured_config = structured_outputs[0]
            schema = self._create_schema(structured_config)

            # Build formatting messages
            format_messages = self._build_format_messages(tool_response)

            # Apply structured output. Force function-calling to avoid
            # the strict ``json_schema`` path (see comment in
            # ``execute_with_structured_output``).
            llm_with_structure = llm.with_structured_output(
                schema, method="function_calling"
            )
            try:
                result = await llm_with_structure.ainvoke(format_messages)
            except TypeError as sdk_err:
                # The OpenAI SDK crashes with
                # ``'NoneType' object is not iterable`` when the provider
                # returns HTTP 200 with ``choices: null`` (prompt-level
                # content filter or an impossible strict schema). Surface a
                # clearer message so operators aren't misled.
                if "NoneType" in str(sdk_err) and "iterable" in str(sdk_err):
                    raise StructuredOutputError(
                        "Provider returned an empty response (choices=null). "
                        "This usually means the structured-output schema is "
                        "unsatisfiable (e.g. an open ``Dict[str, Any]`` under "
                        "strict mode) or the request was blocked by a content "
                        "filter. Simplify the schema to concrete fields."
                    ) from sdk_err
                raise

            # Convert to AIMessage
            if hasattr(result, "model_dump_json"):
                content = result.model_dump_json(indent=2)
            else:
                content = str(result)

            response = AIMessage(
                content=content, additional_kwargs={"structured": True}
            )

            self.logger.info(
                f"[STRUCTURED] Two-phase execution complete for {agent_name}"
            )
            return response

        except StructuredOutputError:
            raise
        except Exception as e:
            error_msg = f"Two-phase execution failed: {str(e)}"
            self.logger.error(f"[STRUCTURED] {error_msg}", exc_info=True)
            raise StructuredOutputError(error_msg) from e

    def _build_format_messages(self, tool_response: Any) -> List[BaseMessage]:
        """Build messages for the formatting phase.

        Args:
            tool_response: Response from tool execution phase

        Returns:
            List of messages for structured output formatting
        """
        raw_content = (
            tool_response.content
            if hasattr(tool_response, "content")
            else str(tool_response)
        )

        return [
            SystemMessage(
                content="You are a formatting assistant. Extract and organize "
                "information into the required structured format."
            ),
            HumanMessage(
                content=f"Based on the following information:\n\n{raw_content}\n\n"
                "Extract and format the relevant information according to the "
                "required output schema."
            ),
        ]
