"""Synchronous agent executor.

This module provides the main SyncAgentExecutor class that orchestrates
agent execution with memory, tools, structured outputs, and more.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from backend.models.workflow import EnhancedNodeData, GraphData
from .context_builder import ContextBuilder
from .memory_handler import MemoryHandler
from .structured_output_handler import StructuredOutputHandler
from .token_utils import count_message_tokens, count_string_tokens, extract_token_counts
from .tool_execution import ToolExecutionTracker


logger = logging.getLogger("agent_execution")


class SyncAgentExecutor:
    """Executes agents synchronously with comprehensive feature support."""

    def __init__(
        self,
        graph_manager: Any,  # Type hint would create circular dependency
    ):
        """Initialize the executor.

        Args:
            graph_manager: GraphManager instance for accessing tools, LLM factory, etc.
        """
        self.graph_manager = graph_manager

    def execute_simple_chat(
        self,
        agent_node: EnhancedNodeData,
        user_message: str,
        format_output: bool = True,
        db_execution_id: Optional[str] = None,
        tool_execution_tracker: Optional[list] = None,
        return_token_counts: bool = False,
        return_raw_response: bool = False,
    ) -> Any:
        """Execute agent chat with support for structured outputs, tools, and memory.

        Args:
            agent_node: The agent node to execute
            user_message: The user's message
            format_output: If True and structured outputs are configured, format the final output
            db_execution_id: Database execution ID for memory context
            tool_execution_tracker: Optional list to track tool executions
            return_token_counts: If True, return a tuple of (response, token_counts)
            return_raw_response: If True, include raw LLM response object in return tuple

        Returns:
            Agent response, optionally with token counts and raw response
        """
        # Initialize token tracking
        total_token_counts = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }

        try:
            logger.info("=== AGENT EXECUTION START ===")
            logger.info(f"Agent: {agent_node.name}")
            logger.info(f"User Message: {user_message}")
            logger.info(f"System Prompt: {agent_node.agent_config.system_prompt}")
            logger.info(f"Format Output: {format_output}")

            # Store original message before modifications
            original_message = user_message

            # Load memory if enabled
            memory_context = MemoryHandler.load_memory_context_sync(
                agent_node, db_execution_id
            )
            if memory_context:
                user_message = f"{memory_context}\n\nCurrent Message: {user_message}"

            # Find the graph containing this agent
            current_graph = self._find_agent_graph(agent_node)

            # Build system prompt with MCP context and other enhancements
            system_prompt = ContextBuilder.build_system_prompt(
                agent_node, current_graph
            )

            # Create base LLM
            llm = self.graph_manager._create_llm_from_config(
                agent_node.agent_config.llm_config
            )

            logger.info(
                f"LLM Config: Provider={agent_node.agent_config.llm_config.provider}, "
                f"Model={agent_node.agent_config.llm_config.model_name}, "
                f"Temperature={agent_node.agent_config.llm_config.temperature}"
            )

            # Determine execution path based on configuration
            has_structured_outputs = bool(agent_node.agent_config.structured_outputs)
            is_orchestrator = agent_node.agent_config.is_orchestrator

            # Execute based on configuration
            if has_structured_outputs and is_orchestrator and format_output:
                # Path 1: Orchestrator with structured outputs (two-phase)
                response, total_token_counts = (
                    self._execute_orchestrator_with_structured_output(
                        agent_node,
                        llm,
                        system_prompt,
                        user_message,
                        original_message,
                        db_execution_id,
                        tool_execution_tracker,
                        current_graph,
                    )
                )
            elif has_structured_outputs and not is_orchestrator:
                # Path 2: Regular agent with structured outputs
                response, total_token_counts = (
                    self._execute_agent_with_structured_output(
                        agent_node,
                        llm,
                        system_prompt,
                        user_message,
                        original_message,
                        db_execution_id,
                        tool_execution_tracker,
                        current_graph,
                    )
                )
            else:
                # Path 3: Agent with tools or simple LLM call
                response, total_token_counts = self._execute_agent_with_tools(
                    agent_node,
                    llm,
                    system_prompt,
                    user_message,
                    original_message,
                    db_execution_id,
                    tool_execution_tracker,
                    current_graph,
                )

            # Return in the requested format
            if return_raw_response:
                return (
                    (response, total_token_counts, response)
                    if return_token_counts
                    else (response, None, response)
                )
            elif return_token_counts:
                return response, total_token_counts
            return response

        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            error_response = AIMessage(content=f"Agent execution failed: {str(e)}")
            if return_raw_response:
                return (
                    (error_response, total_token_counts, None)
                    if return_token_counts
                    else (error_response, None, None)
                )
            elif return_token_counts:
                return error_response, total_token_counts
            return error_response

    def _execute_orchestrator_with_structured_output(
        self,
        agent_node: EnhancedNodeData,
        llm: Any,
        system_prompt: str,
        user_message: str,
        original_message: str,
        db_execution_id: Optional[str],
        tool_execution_tracker: Optional[List],
        current_graph: Optional[GraphData],
    ) -> Tuple[AIMessage, Dict]:
        """Execute orchestrator with two-phase execution (tools then formatting).

        Args:
            agent_node: Agent node
            llm: LLM instance
            system_prompt: Enhanced system prompt
            user_message: User message (with memory)
            original_message: Original user message (without memory)
            db_execution_id: Database execution ID
            tool_execution_tracker: Tool execution tracker
            current_graph: Graph containing the agent

        Returns:
            Tuple of (response, token_counts)
        """
        logger.info(
            "Orchestrator with structured outputs detected - using two-phase execution"
        )

        # Phase 1: Execute with tools (delegation) without structured output
        logger.info("Phase 1: Executing with delegation tools...")
        logger.info(
            f"[TOOL_TRACKER] tool_execution_tracker before Phase 1: {tool_execution_tracker}"
        )

        # Recursively call execute_simple_chat with format_output=False
        raw_response = self.execute_simple_chat(
            agent_node,
            user_message,
            format_output=False,
            db_execution_id=db_execution_id,
            tool_execution_tracker=tool_execution_tracker,
            return_token_counts=False,
        )

        logger.info(
            f"[TOOL_TRACKER] tool_execution_tracker after Phase 1: "
            f"{len(tool_execution_tracker) if tool_execution_tracker else 0} tools executed"
        )

        # Phase 2: Format the response using structured output
        logger.info("Phase 2: Formatting response with structured output...")

        schema_dict = agent_node.agent_config.structured_outputs[0]
        logger.info(
            f"Using structured output schema: {schema_dict.get('model_name', 'unknown')}"
        )

        pydantic_model = StructuredOutputHandler.get_pydantic_model(schema_dict)

        # Format with structured output
        response, result = StructuredOutputHandler.process_with_structured_output(
            llm, pydantic_model, raw_response, None
        )

        # Count tokens
        result_tokens = extract_token_counts(result, "[Structured] ")
        total_token_counts = {
            "input_tokens": result_tokens["input_tokens"],
            "output_tokens": result_tokens["output_tokens"],
            "total_tokens": result_tokens["input_tokens"]
            + result_tokens["output_tokens"],
            "metadata": {},
        }

        # Store memory
        MemoryHandler.store_memory_sync(
            agent_node, original_message, response.content, db_execution_id
        )

        return response, total_token_counts

    def _execute_agent_with_structured_output(
        self,
        agent_node: EnhancedNodeData,
        llm: Any,
        system_prompt: str,
        user_message: str,
        original_message: str,
        db_execution_id: Optional[str],
        tool_execution_tracker: Optional[List],
        current_graph: Optional[GraphData],
    ) -> Tuple[AIMessage, Dict]:
        """Execute agent with structured outputs (and optionally tools).

        Args:
            agent_node: Agent node
            llm: LLM instance
            system_prompt: Enhanced system prompt
            user_message: User message (with memory)
            original_message: Original user message (without memory)
            db_execution_id: Database execution ID
            tool_execution_tracker: Tool execution tracker
            current_graph: Graph containing the agent

        Returns:
            Tuple of (response, token_counts)
        """
        logger.info("Regular agent with structured outputs - checking for tools")

        # Get tools
        tools = self._get_agent_tools(agent_node, current_graph)

        schema_dict = agent_node.agent_config.structured_outputs[0]
        pydantic_model = StructuredOutputHandler.get_pydantic_model(schema_dict)

        total_token_counts = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }

        if tools:
            # Execute with tools then format
            logger.info(
                f"Agent has {len(tools)} tools and structured output - "
                "using tool calling approach"
            )

            # Wrap tools for tracking
            clean_tools = self.graph_manager._create_serializable_tools(
                tools, tool_execution_tracker
            )

            response, result, tool_results = (
                StructuredOutputHandler.execute_with_tools_then_format(
                    llm,
                    clean_tools,
                    pydantic_model,
                    system_prompt,
                    user_message,
                    tool_execution_tracker,
                )
            )

            # Count tokens
            result_tokens = extract_token_counts(result, "[Structured] ")
            total_token_counts["input_tokens"] += result_tokens["input_tokens"]
            total_token_counts["output_tokens"] += result_tokens["output_tokens"]
            total_token_counts["total_tokens"] = (
                total_token_counts["input_tokens"] + total_token_counts["output_tokens"]
            )
        else:
            # No tools, just apply structured output directly
            logger.info("No tools found, applying structured output directly")
            structured_llm = llm.with_structured_output(pydantic_model)

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]

            result = structured_llm.invoke(messages)

            # Count tokens
            result_tokens = extract_token_counts(result, "[Structured] ")
            total_token_counts = result_tokens

            # Convert to response
            json_output = result.model_dump_json(indent=2)
            response = AIMessage(content=json_output)

        # Store memory
        MemoryHandler.store_memory_sync(
            agent_node, original_message, response.content, db_execution_id
        )

        return response, total_token_counts

    def _execute_agent_with_tools(
        self,
        agent_node: EnhancedNodeData,
        llm: Any,
        system_prompt: str,
        user_message: str,
        original_message: str,
        db_execution_id: Optional[str],
        tool_execution_tracker: Optional[List],
        current_graph: Optional[GraphData],
    ) -> Tuple[AIMessage, Dict]:
        """Execute agent with tools or as simple LLM call.

        Args:
            agent_node: Agent node
            llm: LLM instance
            system_prompt: Enhanced system prompt
            user_message: User message (with memory)
            original_message: Original user message (without memory)
            db_execution_id: Database execution ID
            tool_execution_tracker: Tool execution tracker
            current_graph: Graph containing the agent

        Returns:
            Tuple of (response, token_counts)
        """
        total_token_counts = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }

        # Get tools (including delegation tools for orchestrators)
        tools = self._get_agent_tools(agent_node, current_graph)

        if tools:
            # Execute with tools
            response, total_token_counts = self._execute_with_tools(
                agent_node,
                llm,
                system_prompt,
                user_message,
                original_message,
                tools,
                db_execution_id,
                tool_execution_tracker,
            )
        else:
            # Simple LLM call
            response, total_token_counts = self._execute_simple_llm_call(
                agent_node,
                llm,
                system_prompt,
                user_message,
                original_message,
                db_execution_id,
            )

        return response, total_token_counts

    def _execute_with_tools(
        self,
        agent_node: EnhancedNodeData,
        llm: Any,
        system_prompt: str,
        user_message: str,
        original_message: str,
        tools: List[Any],
        db_execution_id: Optional[str],
        tool_execution_tracker: Optional[List],
    ) -> Tuple[AIMessage, Dict]:
        """Execute agent with tools using ReAct or forced tool choice.

        Args:
            agent_node: Agent node
            llm: LLM instance
            system_prompt: Enhanced system prompt
            user_message: User message
            original_message: Original message
            tools: List of tools
            db_execution_id: Database execution ID
            tool_execution_tracker: Tool execution tracker

        Returns:
            Tuple of (response, token_counts)
        """
        from langgraph.prebuilt import create_react_agent

        logger.info(
            f"Using {len(tools)} tools: {[getattr(t, 'name', str(t)) for t in tools]}"
        )

        # Create serializable tools
        clean_tools = self.graph_manager._create_serializable_tools(
            tools, tool_execution_tracker
        )

        # Wrap tools for tracking
        wrapped_tools = ToolExecutionTracker.wrap_tools_with_tracking(
            clean_tools, tool_execution_tracker
        )

        # Get tool_choice configuration
        tool_choice = getattr(agent_node.agent_config, "tool_choice", "auto")

        # Check if provider supports tool_choice
        supports_tool_choice = agent_node.agent_config.llm_config.provider.lower() in [
            "azure_openai",
            "openai",
            "mistralai",
            "fireworksai",
            "groq",
        ]

        # Handle forced tool choice
        if tool_choice not in ["auto", "any"] and supports_tool_choice:
            return self._execute_forced_tool_choice(
                agent_node,
                llm,
                system_prompt,
                user_message,
                original_message,
                wrapped_tools,
                tool_choice,
                db_execution_id,
                tool_execution_tracker,
            )

        # Use ReAct agent for normal tool execution
        if tool_choice == "any" and supports_tool_choice:
            llm = llm.bind_tools(wrapped_tools, tool_choice="any")
        else:
            llm = llm.bind_tools(wrapped_tools)

        agent_executor = create_react_agent(llm, wrapped_tools)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        self._log_verbose_input(agent_node, messages, wrapped_tools)

        # Count input tokens
        input_token_count = count_message_tokens(messages)
        total_token_counts = {
            "input_tokens": input_token_count["total"],
            "output_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }

        # Execute
        result = agent_executor.invoke({"messages": messages})

        self._log_react_result(result)

        # Extract final message
        result_messages = result.get("messages", [])
        if result_messages:
            final_response = result_messages[-1]

            # Count output tokens
            output_messages = result_messages[2:]  # Skip system and human
            for msg in output_messages:
                if hasattr(msg, "content") and msg.content:
                    total_token_counts["output_tokens"] += count_string_tokens(
                        str(msg.content)
                    )

            total_token_counts["total_tokens"] = (
                total_token_counts["input_tokens"] + total_token_counts["output_tokens"]
            )

            # Store memory
            MemoryHandler.store_memory_sync(
                agent_node, original_message, final_response.content, db_execution_id
            )

            return final_response, total_token_counts
        else:
            response = AIMessage(content="No response generated")
            MemoryHandler.store_memory_sync(
                agent_node, original_message, response.content, db_execution_id
            )
            return response, total_token_counts

    def _execute_forced_tool_choice(
        self,
        agent_node: EnhancedNodeData,
        llm: Any,
        system_prompt: str,
        user_message: str,
        original_message: str,
        tools: List[Any],
        tool_choice: Any,
        db_execution_id: Optional[str],
        tool_execution_tracker: Optional[List],
    ) -> Tuple[AIMessage, Dict]:
        """Execute with forced tool choice.

        Args:
            agent_node: Agent node
            llm: LLM instance
            system_prompt: System prompt
            user_message: User message
            original_message: Original message
            tools: List of tools
            tool_choice: Tool choice configuration
            db_execution_id: Database execution ID
            tool_execution_tracker: Tool execution tracker

        Returns:
            Tuple of (response, token_counts)
        """
        logger.info(f"Forcing single tool call with tool_choice='{tool_choice}'")

        llm_with_forced_tool = llm.bind_tools(tools, tool_choice=tool_choice)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        forced_tool_name = (
            tool_choice.get("name")
            if isinstance(tool_choice, dict)
            else str(tool_choice)
        )

        self._log_verbose_forced_tool_input(agent_node, messages, forced_tool_name)

        # Get the tool call
        tool_response = llm_with_forced_tool.invoke(messages)

        # Execute tool calls if any
        if hasattr(tool_response, "tool_calls") and tool_response.tool_calls:
            messages.append(tool_response)

            # Execute each tool call
            ToolExecutionTracker.execute_tool_calls(
                tool_response.tool_calls, tools, messages, tool_execution_tracker
            )

            # Get final response
            llm_final = llm.bind_tools(tools)
            final_response = llm_final.invoke(messages)

            MemoryHandler.store_memory_sync(
                agent_node, original_message, final_response.content, db_execution_id
            )
            return final_response, {}
        else:
            # No tool was called
            MemoryHandler.store_memory_sync(
                agent_node, original_message, tool_response.content, db_execution_id
            )
            return tool_response, {}

    def _execute_simple_llm_call(
        self,
        agent_node: EnhancedNodeData,
        llm: Any,
        system_prompt: str,
        user_message: str,
        original_message: str,
        db_execution_id: Optional[str],
    ) -> Tuple[AIMessage, Dict]:
        """Execute simple LLM call without tools.

        Args:
            agent_node: Agent node
            llm: LLM instance
            system_prompt: System prompt
            user_message: User message
            original_message: Original message
            db_execution_id: Database execution ID

        Returns:
            Tuple of (response, token_counts)
        """
        logger.info("No tools or structured outputs - performing direct LLM call")

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]

        self._log_verbose_simple_input(agent_node, messages)

        # Count input tokens
        input_token_count = count_message_tokens(messages)
        total_token_counts = {
            "input_tokens": input_token_count["total"],
            "output_tokens": 0,
            "total_tokens": 0,
            "metadata": {},
        }

        response = llm.invoke(messages)

        # Extract token counts
        response_tokens = extract_token_counts(response, "[Direct] ")
        if response_tokens["total_tokens"] > 0:
            total_token_counts = response_tokens
        else:
            # Manual counting
            output_token_count = count_string_tokens(response.content)
            total_token_counts["output_tokens"] = output_token_count
            total_token_counts["total_tokens"] = (
                total_token_counts["input_tokens"] + total_token_counts["output_tokens"]
            )

        # Store memory
        MemoryHandler.store_memory_sync(
            agent_node, original_message, response.content, db_execution_id
        )

        return response, total_token_counts

    def _find_agent_graph(self, agent_node: EnhancedNodeData) -> Optional[GraphData]:
        """Find the graph containing an agent node.

        Args:
            agent_node: Agent node to find

        Returns:
            Graph containing the agent, or None
        """
        for graph_name, graph in self.graph_manager.active_graphs.items():
            if any(n.uniq_id == agent_node.uniq_id for n in graph.nodes):
                return graph
        return None

    def _get_agent_tools(
        self, agent_node: EnhancedNodeData, graph: Optional[GraphData]
    ) -> List[Any]:
        """Get tools for an agent.

        Args:
            agent_node: Agent node
            graph: Graph containing the agent

        Returns:
            List of tools
        """
        graph_name = None
        if graph:
            for name, g in self.graph_manager.active_graphs.items():
                if g == graph:
                    graph_name = name
                    break

        return self.graph_manager.get_tools(
            agent_node.agent_config.tools or [],
            agent_config=agent_node.agent_config,
            graph_name=graph_name,
            agent_node_id=agent_node.uniq_id,
        )

    def _log_verbose_input(
        self, agent_node: EnhancedNodeData, messages: List, tools: List
    ) -> None:
        """Log verbose input for tool-based execution."""
        logger.info("===== VERBOSE AGENT INPUT LOGGING (WITH TOOLS) =====")
        logger.info(f"Agent Name: {agent_node.name}")
        logger.info(f"Agent ID: {agent_node.uniq_id}")
        logger.info(f"Total Messages: {len(messages)}")
        logger.info(f"Tools Available: {len(tools)} - {[t.name for t in tools]}")
        total_chars = 0
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            msg_content = msg.content
            msg_chars = len(msg_content)
            total_chars += msg_chars
            logger.info(f"--- Message {i + 1} ({msg_type}) - {msg_chars} chars ---")
            logger.info(msg_content)
            logger.info(f"--- End Message {i + 1} ---")
        logger.info(f"TOTAL INPUT SIZE: {total_chars} characters")
        logger.info(f"ESTIMATED TOKENS (chars/4): ~{total_chars // 4} tokens")
        logger.info("===== END VERBOSE INPUT LOGGING =====")

    def _log_verbose_forced_tool_input(
        self, agent_node: EnhancedNodeData, messages: List, forced_tool_name: str
    ) -> None:
        """Log verbose input for forced tool execution."""
        logger.info("===== VERBOSE AGENT INPUT LOGGING (FORCED TOOL) =====")
        logger.info(f"Agent Name: {agent_node.name}")
        logger.info(f"Agent ID: {agent_node.uniq_id}")
        logger.info(f"Forced Tool: {forced_tool_name}")
        logger.info(f"Total Messages: {len(messages)}")
        total_chars = 0
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            msg_content = msg.content
            msg_chars = len(msg_content)
            total_chars += msg_chars
            logger.info(f"--- Message {i + 1} ({msg_type}) - {msg_chars} chars ---")
            logger.info(msg_content)
            logger.info(f"--- End Message {i + 1} ---")
        logger.info(f"TOTAL INPUT SIZE: {total_chars} characters")
        logger.info(f"ESTIMATED TOKENS (chars/4): ~{total_chars // 4} tokens")
        logger.info("===== END VERBOSE INPUT LOGGING =====")

    def _log_verbose_simple_input(
        self, agent_node: EnhancedNodeData, messages: List
    ) -> None:
        """Log verbose input for simple LLM calls."""
        logger.info("===== VERBOSE AGENT INPUT LOGGING (SIMPLE) =====")
        logger.info(f"Agent Name: {agent_node.name}")
        logger.info(f"Agent ID: {agent_node.uniq_id}")
        logger.info(f"Total Messages: {len(messages)}")
        total_chars = 0
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            msg_content = msg.content
            msg_chars = len(msg_content)
            total_chars += msg_chars
            logger.info(f"--- Message {i + 1} ({msg_type}) - {msg_chars} chars ---")
            logger.info(msg_content)
            logger.info(f"--- End Message {i + 1} ---")
        logger.info(f"TOTAL INPUT SIZE: {total_chars} characters")
        logger.info(f"ESTIMATED TOKENS (chars/4): ~{total_chars // 4} tokens")
        logger.info("===== END VERBOSE INPUT LOGGING =====")

    def _log_react_result(self, result: Dict) -> None:
        """Log ReAct agent result."""
        logger.info("===== REACT AGENT RESULT =====")
        result_messages = result.get("messages", [])
        logger.info(f"Total Messages in Result: {len(result_messages)}")
        total_result_chars = 0
        for i, msg in enumerate(result_messages):
            msg_type = type(msg).__name__
            msg_content = getattr(msg, "content", str(msg))
            msg_chars = len(str(msg_content))
            total_result_chars += msg_chars
            logger.info(
                f"--- Result Message {i + 1} ({msg_type}) - {msg_chars} chars ---"
            )
            # For tool calls, show brief summary
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                logger.info(
                    f"Tool Calls: {[tc.get('name', 'unknown') for tc in msg.tool_calls]}"
                )
            # Limit content display for very long messages
            if msg_chars > 1000:
                logger.info(
                    f"{str(msg_content)[:500]}... [truncated, total {msg_chars} chars]"
                )
            else:
                logger.info(str(msg_content))
        logger.info(f"TOTAL RESULT SIZE: {total_result_chars} characters")
        logger.info(f"ESTIMATED RESULT TOKENS: ~{total_result_chars // 4} tokens")
        logger.info("===== END REACT AGENT RESULT =====")
