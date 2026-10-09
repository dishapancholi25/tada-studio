"""Structured output handling for agent execution.

This module handles structured output processing including two-phase execution
for orchestrators and single-phase for regular agents.
"""

import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.services.structured_output import (
    StructuredOutputGenerator,
    StructuredOutputSchema,
)


logger = logging.getLogger("agent_execution")


class StructuredOutputHandler:
    """Handles structured output processing for agents."""

    @staticmethod
    def process_with_structured_output(
        llm: Any,
        pydantic_model: Any,
        raw_response: Any,
        tool_results: Optional[List[Any]] = None,
    ) -> AIMessage:
        """Process a response with structured output formatting.

        Args:
            llm: LLM instance
            pydantic_model: Pydantic model for structured output
            raw_response: Raw response from initial execution
            tool_results: Optional tool results to include

        Returns:
            AIMessage with JSON-formatted structured output
        """
        # Build formatting prompt
        if tool_results:
            format_prompt = f"""Based on the following information gathered from tools:

Tool Results:
{chr(10).join(str(r) for r in tool_results)}

Agent Analysis:
{raw_response.content if hasattr(raw_response, "content") else str(raw_response)}

Extract and format the relevant information according to the required output schema."""
        else:
            format_prompt = f"""Based on the following information:

{raw_response.content if hasattr(raw_response, "content") else str(raw_response)}

Extract and format the relevant information according to the required output schema."""

        # Apply structured output to LLM
        structured_llm = llm.with_structured_output(pydantic_model)

        # Get structured result
        result = structured_llm.invoke(
            [
                SystemMessage(
                    content="You are a formatting assistant. Extract and organize "
                    "information into the required structured format."
                ),
                HumanMessage(content=format_prompt),
            ]
        )

        logger.info(f"Received structured result: {type(result).__name__}")

        # Convert Pydantic model to JSON string for response
        json_output = result.model_dump_json(indent=2)
        logger.info(f"JSON output: {json_output}")

        return AIMessage(content=json_output), result

    @staticmethod
    def get_pydantic_model(schema_dict: Dict[str, Any]) -> Any:
        """Generate Pydantic model from schema dictionary.

        Args:
            schema_dict: Schema definition dictionary

        Returns:
            Generated Pydantic model class
        """
        schema = StructuredOutputSchema(**schema_dict)
        pydantic_model = StructuredOutputGenerator.generate_pydantic_model(schema)

        logger.info(f"Generated Pydantic model: {pydantic_model.__name__}")
        logger.info(f"Model fields: {list(pydantic_model.model_fields.keys())}")

        return pydantic_model

    @staticmethod
    def execute_with_tools_then_format(
        llm: Any,
        tools: List[Any],
        pydantic_model: Any,
        system_prompt: str,
        user_message: str,
        tool_execution_tracker: Optional[List] = None,
    ) -> tuple:
        """Execute with tools first, then format with structured output.

        This is used for regular agents with both tools and structured outputs.

        Args:
            llm: LLM instance
            tools: List of tools
            pydantic_model: Pydantic model for output
            system_prompt: System prompt
            user_message: User message
            tool_execution_tracker: Optional tool execution tracker

        Returns:
            Tuple of (response, result, tool_results)
        """
        from langchain_core.messages import ToolMessage

        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)

        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        # Get tool calls
        response_with_tools = llm_with_tools.invoke(messages)

        tool_results = []

        # Execute tool calls if any
        if (
            hasattr(response_with_tools, "tool_calls")
            and response_with_tools.tool_calls
        ):
            logger.info(f"Found {len(response_with_tools.tool_calls)} tool calls")
            messages.append(response_with_tools)

            for tool_call in response_with_tools.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

                # Find and execute the tool
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            tool_result = tool.invoke(tool_args)
                            messages.append(
                                ToolMessage(
                                    content=str(tool_result),
                                    tool_call_id=tool_call["id"],
                                )
                            )
                            tool_results.append(tool_result)
                            break
                        except Exception as e:
                            logger.error(f"Tool execution failed: {e}")
                            messages.append(
                                ToolMessage(
                                    content=f"Error: {str(e)}",
                                    tool_call_id=tool_call["id"],
                                )
                            )

            # Get final response after tool execution
            logger.info("Getting final response after tool execution...")
            final_response = llm_with_tools.invoke(messages)

            raw_output = (
                final_response.content
                if hasattr(final_response, "content")
                else str(final_response)
            )
        else:
            logger.info("No tool calls found, using direct response")
            raw_output = (
                response_with_tools.content
                if hasattr(response_with_tools, "content")
                else str(response_with_tools)
            )
            final_response = response_with_tools

        logger.info(f"Phase 1 complete. Raw output: {raw_output[:200]}...")

        # Phase 2: Format with structured output
        logger.info("Phase 2: Formatting with structured output...")

        # Build structured response
        response, result = StructuredOutputHandler.process_with_structured_output(
            llm, pydantic_model, final_response, tool_results if tool_results else None
        )

        return response, result, tool_results
