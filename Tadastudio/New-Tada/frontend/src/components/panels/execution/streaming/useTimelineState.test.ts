import { act, renderHook } from "@testing-library/react";
import type {
	ToolCallCompleteEvent,
	ToolCallErrorEvent,
	ToolCallStartEvent,
} from "@/hooks/useExecutionWebSocket";
import type { NodeExecution } from "@/types/api";
import { useTimelineState } from "./useTimelineState";

describe("useTimelineState", () => {
	describe("handleNodeUpdate", () => {
		describe("multiple sub-agent executions", () => {
			it("should create separate entries for multiple sub-agent executions with same node_id", () => {
				const { result } = renderHook(() => useTimelineState());

				// First sub-agent execution
				act(() => {
					result.current.handleNodeUpdate("subagent-1", "running", undefined, {
						node_name: "Math Agent",
						node_type: "AGENT",
						is_sub_agent: true,
						database_node_id: "db-exec-1",
					});
				});
				act(() => {
					result.current.handleNodeUpdate(
						"subagent-1",
						"completed",
						{ response: "Answer: 32" },
						{
							node_name: "Math Agent",
							node_type: "AGENT",
							is_sub_agent: true,
							database_node_id: "db-exec-1",
						},
					);
				});

				// Second sub-agent execution (same node_id, different db id)
				act(() => {
					result.current.handleNodeUpdate("subagent-1", "running", undefined, {
						node_name: "Math Agent",
						node_type: "AGENT",
						is_sub_agent: true,
						database_node_id: "db-exec-2",
					});
				});
				act(() => {
					result.current.handleNodeUpdate(
						"subagent-1",
						"completed",
						{ response: "Answer: 74" },
						{
							node_name: "Math Agent",
							node_type: "AGENT",
							is_sub_agent: true,
							database_node_id: "db-exec-2",
						},
					);
				});

				// Should have 2 separate entries
				expect(result.current.wsNodeExecutions.size).toBe(2);

				const entries = Array.from(result.current.wsNodeExecutions.values());
				expect(entries[0].output_data?.response).toBe("Answer: 32");
				expect(entries[1].output_data?.response).toBe("Answer: 74");
			});

			it("should match running sub-agent by node_id for completion update", () => {
				const { result } = renderHook(() => useTimelineState());

				// Start sub-agent (no database_node_id yet)
				act(() => {
					result.current.handleNodeUpdate("subagent-1", "running", undefined, {
						node_name: "Math Agent",
						node_type: "AGENT",
						is_sub_agent: true,
					});
				});

				expect(result.current.wsNodeExecutions.size).toBe(1);

				// Complete with database_node_id
				act(() => {
					result.current.handleNodeUpdate(
						"subagent-1",
						"completed",
						{ response: "Done" },
						{
							node_name: "Math Agent",
							node_type: "AGENT",
							is_sub_agent: true,
							database_node_id: "db-123",
						},
					);
				});

				// Should still have 1 entry (matched running entry)
				expect(result.current.wsNodeExecutions.size).toBe(1);
				const entry = Array.from(result.current.wsNodeExecutions.values())[0];
				expect(entry.status).toBe("completed");
			});
		});

		it("should add new entry on running status", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_name: "Agent 1",
					node_type: "AGENT",
					database_node_id: "db-123",
				});
			});

			expect(result.current.wsNodeExecutions.size).toBe(1);
			expect(result.current.runningNodes.has("node1")).toBe(true);

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.node_name).toBe("Agent 1");
			expect(entry.status).toBe("running");
		});

		it("should update existing entry by database_node_id", () => {
			const { result } = renderHook(() => useTimelineState());

			// First update - running
			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					database_node_id: "db-123",
					node_name: "Agent 1",
					node_type: "AGENT",
				});
			});

			expect(result.current.wsNodeExecutions.size).toBe(1);

			// Second update - completed with same db id
			act(() => {
				result.current.handleNodeUpdate(
					"node1",
					"completed",
					{ result: "done" },
					{
						database_node_id: "db-123",
						node_name: "Agent 1",
						node_type: "AGENT",
					},
				);
			});

			// Should still only have one entry
			expect(result.current.wsNodeExecutions.size).toBe(1);

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.status).toBe("completed");
		});

		it("should preserve streaming content on AGENT completion", () => {
			const { result } = renderHook(() => useTimelineState());

			// Start agent
			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_name: "Agent 1",
					node_type: "AGENT",
					database_node_id: "db-123",
				});
			});

			// Stream tokens
			act(() => {
				result.current.handleTokenStream({
					nodeId: "node1",
					content: "Hello ",
				});
				result.current.handleTokenStream({
					nodeId: "node1",
					content: "world",
				});
			});

			// Complete - should preserve accumulated content
			act(() => {
				result.current.handleNodeUpdate(
					"node1",
					"completed",
					{ final: true },
					{
						node_name: "Agent 1",
						node_type: "AGENT",
						database_node_id: "db-123",
					},
				);
			});

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.output_data?.raw).toBe("Hello world");
			expect(entry.status).toBe("completed");
			expect(entry.output_data?.isThinking).toBe(false);
		});

		it("should set isThinking when AGENT starts", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_name: "Agent 1",
					node_type: "AGENT",
				});
			});

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.output_data?.isThinking).toBe(true);
		});

		it("should track running nodes", () => {
			const { result } = renderHook(() => useTimelineState());

			// Start first node
			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {});
			});
			expect(result.current.runningNodes.size).toBe(1);
			expect(result.current.runningNodes.has("node1")).toBe(true);

			// Start second node
			act(() => {
				result.current.handleNodeUpdate("node2", "running", undefined, {});
			});
			expect(result.current.runningNodes.size).toBe(2);

			// Complete first node
			act(() => {
				result.current.handleNodeUpdate("node1", "completed", undefined, {});
			});
			expect(result.current.runningNodes.size).toBe(1);
			expect(result.current.runningNodes.has("node1")).toBe(false);
			expect(result.current.runningNodes.has("node2")).toBe(true);
		});

		it("should call onNodeRunning and onNodeStopped callbacks", () => {
			const onNodeRunning = jest.fn();
			const onNodeStopped = jest.fn();

			const { result } = renderHook(() =>
				useTimelineState({ onNodeRunning, onNodeStopped }),
			);

			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {});
			});
			expect(onNodeRunning).toHaveBeenCalledWith("node1");

			act(() => {
				result.current.handleNodeUpdate("node1", "completed", undefined, {});
			});
			expect(onNodeStopped).toHaveBeenCalledWith(null);
		});

		it("should handle sub-agent updates", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleNodeUpdate("subagent1", "running", undefined, {
					node_name: "Research Agent",
					node_type: "AGENT",
					is_sub_agent: true,
					parent_agent_id: "parent-agent-1",
				});
			});

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.is_sub_agent).toBe(true);
			expect(entry.parent_agent_id).toBe("parent-agent-1");
		});
	});

	describe("handleTokenStream", () => {
		it("should accumulate tokens", () => {
			const { result } = renderHook(() => useTimelineState());

			// Start node first
			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_type: "AGENT",
				});
			});

			act(() => {
				result.current.handleTokenStream({ nodeId: "node1", content: "A" });
				result.current.handleTokenStream({ nodeId: "node1", content: "B" });
				result.current.handleTokenStream({ nodeId: "node1", content: "C" });
			});

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.output_data?.raw).toBe("ABC");
		});

		it("should claim entry with step on first token", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_type: "AGENT",
				});
			});

			act(() => {
				result.current.handleTokenStream({
					nodeId: "node1",
					step: 5,
					content: "first",
				});
			});

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.step).toBe(5);
		});

		it("should not match wrong step", () => {
			const { result } = renderHook(() => useTimelineState());

			// Create entry with step 5
			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_type: "AGENT",
					step: 5,
				});
			});

			// Try to append to step 6 (different iteration)
			act(() => {
				result.current.handleTokenStream({
					nodeId: "node1",
					step: 6,
					content: "new iteration",
				});
			});

			// Should have 2 entries now
			expect(result.current.wsNodeExecutions.size).toBe(2);
		});

		it("should clear isThinking on first token", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_type: "AGENT",
				});
			});

			// Should be thinking initially
			let entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.output_data?.isThinking).toBe(true);

			act(() => {
				result.current.handleTokenStream({ nodeId: "node1", content: "Hello" });
			});

			// Should no longer be thinking after first token
			entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.output_data?.isThinking).toBe(false);
		});

		it("should create new entry if no match found", () => {
			const { result } = renderHook(() => useTimelineState());

			// Add node to runningNodes to enable token targeting
			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {});
			});

			// Clear the map but keep node in runningNodes
			act(() => {
				result.current.handleTokenStream({
					nodeId: "node1",
					step: 1,
					content: "Token",
				});
			});

			// Should update existing entry
			expect(result.current.wsNodeExecutions.size).toBe(1);
		});
	});

	describe("handleToolCallStart/Complete/Error", () => {
		it("should create tool entry on start", () => {
			const { result } = renderHook(() => useTimelineState());

			const event: ToolCallStartEvent = {
				call_id: "call-1",
				tool_name: "document_search",
				tool_args: { query: "test" },
				agent_id: "agent-1",
				agent_name: "Research Agent",
				timestamp: new Date().toISOString(),
				tool_node_id: "tool-node-1",
				tool_node_name: "Document Search",
				tool_node_type: "DOCUMENT_SEARCH",
			};

			act(() => {
				result.current.handleToolCallStart(event);
			});

			expect(result.current.wsNodeExecutions.size).toBe(1);
			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.status).toBe("running");
			expect(entry.parent_agent_id).toBe("agent-1");
			expect(entry.node_name).toBe("Document Search");
			expect(entry.input_data).toEqual({ query: "test" });
		});

		it("should update tool entry on complete", () => {
			const { result } = renderHook(() => useTimelineState());

			// Start tool
			act(() => {
				result.current.handleToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "a1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
				});
			});

			// Complete tool
			const completeEvent: ToolCallCompleteEvent = {
				call_id: "call-1",
				tool_name: "search",
				duration_ms: 500,
				timestamp: new Date().toISOString(),
				tool_node_id: "tool-1",
				result_preview: "Found 3 results",
			};

			act(() => {
				result.current.handleToolCallComplete(completeEvent);
			});

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.status).toBe("completed");
			expect(entry.duration_seconds).toBe(0.5);
			expect(entry.output_data?.raw).toBe("Found 3 results");
		});

		it("should update tool entry on error", () => {
			const { result } = renderHook(() => useTimelineState());

			// Start tool
			act(() => {
				result.current.handleToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "a1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
				});
			});

			// Error
			const errorEvent: ToolCallErrorEvent = {
				call_id: "call-1",
				tool_name: "search",
				error: "Connection timeout",
				duration_ms: 3000,
				timestamp: new Date().toISOString(),
				tool_node_id: "tool-1",
			};

			act(() => {
				result.current.handleToolCallError(errorEvent);
			});

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.status).toBe("failed");
			expect(entry.duration_seconds).toBe(3);
			expect(entry.error_message).toBe("Connection timeout");
		});

		it("should be idempotent - reuse existing key", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "a1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
				});
				// Duplicate call (e.g., from network retry)
				result.current.handleToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "a1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
				});
			});

			// Should still only have one entry
			expect(result.current.wsNodeExecutions.size).toBe(1);
		});

		it("should ignore events without tool_node_id", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "a1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					// No tool_node_id
				});
			});

			expect(result.current.wsNodeExecutions.size).toBe(0);
		});
	});

	describe("loadInitialData", () => {
		it("should populate map from node array", () => {
			const { result } = renderHook(() => useTimelineState());

			const nodes: NodeExecution[] = [
				{
					id: "exec-1",
					node_id: "node1",
					node_name: "Start",
					node_type: "START",
					status: "completed",
					execution_order: 1,
					start_time: new Date().toISOString(),
					end_time: new Date().toISOString(),
					duration_seconds: 0.1,
					input_data: null,
					output_data: null,
					error_message: null,
					node_metadata: null,
					is_sub_agent: false,
					input_tokens: null,
					output_tokens: null,
					total_tokens: null,
					token_metadata: null,
					created_at: new Date().toISOString(),
				},
				{
					id: "exec-2",
					node_id: "node2",
					node_name: "Agent",
					node_type: "AGENT",
					status: "running",
					execution_order: 2,
					start_time: new Date().toISOString(),
					end_time: null,
					duration_seconds: null,
					input_data: null,
					output_data: null,
					error_message: null,
					node_metadata: null,
					is_sub_agent: false,
					input_tokens: null,
					output_tokens: null,
					total_tokens: null,
					token_metadata: null,
					created_at: new Date().toISOString(),
				},
			];

			act(() => {
				result.current.loadInitialData(nodes);
			});

			expect(result.current.wsNodeExecutions.size).toBe(2);
		});

		it("should deduplicate checkpoints preferring completed", () => {
			const { result } = renderHook(() => useTimelineState());

			const nodes: NodeExecution[] = [
				{
					id: "cp-1",
					node_id: "checkpoint1",
					node_name: "Checkpoint",
					node_type: "CHECKPOINT",
					status: "paused",
					execution_order: 1,
					start_time: new Date().toISOString(),
					end_time: null,
					duration_seconds: null,
					input_data: null,
					output_data: null,
					error_message: null,
					node_metadata: null,
					is_sub_agent: false,
					input_tokens: null,
					output_tokens: null,
					total_tokens: null,
					token_metadata: null,
					created_at: new Date().toISOString(),
				},
				{
					id: "cp-2",
					node_id: "checkpoint1",
					node_name: "Checkpoint",
					node_type: "CHECKPOINT",
					status: "completed",
					execution_order: 1,
					start_time: new Date().toISOString(),
					end_time: new Date().toISOString(),
					duration_seconds: 0.1,
					input_data: null,
					output_data: null,
					error_message: null,
					node_metadata: null,
					is_sub_agent: false,
					input_tokens: null,
					output_tokens: null,
					total_tokens: null,
					token_metadata: null,
					created_at: new Date().toISOString(),
				},
			];

			act(() => {
				result.current.loadInitialData(nodes);
			});

			// Should only have one checkpoint entry
			expect(result.current.wsNodeExecutions.size).toBe(1);

			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.status).toBe("completed");
		});

		it("should preserve multiple executions of same sub-agent node_id", () => {
			const { result } = renderHook(() => useTimelineState());

			const nodes: NodeExecution[] = [
				{
					id: "exec-1",
					node_id: "subagent-1",
					node_name: "Math Agent",
					node_type: "AGENT",
					status: "completed",
					execution_order: 1,
					start_time: new Date().toISOString(),
					end_time: new Date().toISOString(),
					duration_seconds: 3.5,
					input_data: { task: "5 squared + 7" },
					output_data: { response: "32" },
					error_message: null,
					node_metadata: null,
					is_sub_agent: true,
					parent_agent_id: "orchestrator-1",
					input_tokens: 100,
					output_tokens: 50,
					total_tokens: 150,
					token_metadata: null,
					created_at: new Date().toISOString(),
				},
				{
					id: "exec-2",
					node_id: "subagent-1", // Same node_id
					node_name: "Math Agent",
					node_type: "AGENT",
					status: "completed",
					execution_order: 2,
					start_time: new Date().toISOString(),
					end_time: new Date().toISOString(),
					duration_seconds: 2.8,
					input_data: { task: "11 * 7 - 3" },
					output_data: { response: "74" },
					error_message: null,
					node_metadata: null,
					is_sub_agent: true,
					parent_agent_id: "orchestrator-1",
					input_tokens: 95,
					output_tokens: 45,
					total_tokens: 140,
					token_metadata: null,
					created_at: new Date().toISOString(),
				},
				{
					id: "exec-3",
					node_id: "subagent-1", // Same node_id
					node_name: "Math Agent",
					node_type: "AGENT",
					status: "completed",
					execution_order: 3,
					start_time: new Date().toISOString(),
					end_time: new Date().toISOString(),
					duration_seconds: 4.1,
					input_data: { task: "reverse binary of 19" },
					output_data: { response: "25" },
					error_message: null,
					node_metadata: null,
					is_sub_agent: true,
					parent_agent_id: "orchestrator-1",
					input_tokens: 110,
					output_tokens: 60,
					total_tokens: 170,
					token_metadata: null,
					created_at: new Date().toISOString(),
				},
			];

			act(() => {
				result.current.loadInitialData(nodes);
			});

			// Should preserve all 3 executions (not deduplicated like checkpoints)
			expect(result.current.wsNodeExecutions.size).toBe(3);

			const entries = Array.from(result.current.wsNodeExecutions.values());
			const responses = entries.map((e) => e.output_data?.response);
			expect(responses).toContain("32");
			expect(responses).toContain("74");
			expect(responses).toContain("25");
		});
	});

	describe("token stream not misrouted to completed tool node", () => {
		it("should not create a running entry for a tool node when agent tokens arrive after tool calls complete", () => {
			const { result } = renderHook(() => useTimelineState());

			// Start agent
			act(() => {
				result.current.handleNodeUpdate("agent-1", "running", undefined, {
					node_name: "Research Agent",
					node_type: "AGENT",
					database_node_id: "db-agent-1",
				});
			});

			// Tool call starts (sets lastRunningNodeRef to "mcp-1")
			act(() => {
				result.current.handleToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: { query: "test" },
					agent_id: "agent-1",
					agent_name: "Research Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "mcp-1",
					invocation_index: 0,
				});
			});

			// Second tool call
			act(() => {
				result.current.handleToolCallStart({
					call_id: "call-2",
					tool_name: "search",
					tool_args: { query: "test2" },
					agent_id: "agent-1",
					agent_name: "Research Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "mcp-1",
					invocation_index: 1,
				});
			});

			// Both tool calls complete (mcp-1 removed from runningNodes)
			act(() => {
				result.current.handleToolCallComplete({
					call_id: "call-1",
					tool_name: "search",
					duration_ms: 500,
					timestamp: new Date().toISOString(),
					tool_node_id: "mcp-1",
					invocation_index: 0,
				});
				result.current.handleToolCallComplete({
					call_id: "call-2",
					tool_name: "search",
					duration_ms: 600,
					timestamp: new Date().toISOString(),
					tool_node_id: "mcp-1",
					invocation_index: 1,
				});
			});

			// At this point: agent-1 is still running, mcp-1 is NOT in runningNodes
			// lastRunningNodeRef.current still points to "mcp-1" (last tool started)
			expect(result.current.runningNodes.has("mcp-1")).toBe(false);
			expect(result.current.runningNodes.has("agent-1")).toBe(true);

			// Agent starts streaming tokens WITHOUT nodeId (simulates missing node_id in event)
			// With the bug: these tokens would target "mcp-1" via lastRunningNodeRef,
			// creating a spurious "running" entry that hides the tool-usage badge.
			act(() => {
				result.current.handleTokenStream({ content: "Here are the results..." });
			});

			// No new entry should be created for mcp-1 — tokens should route to agent-1
			const entries = Array.from(result.current.wsNodeExecutions.values());
			const mcpEntries = entries.filter((e) => e.node_id === "mcp-1");
			const runningMcpEntries = mcpEntries.filter((e) => e.status === "running");

			// There must be no new "running" entry for the MCP node
			expect(runningMcpEntries).toHaveLength(0);

			// All mcp-1 entries must remain completed
			mcpEntries.forEach((e) => {
				expect(e.status).toBe("completed");
			});

			// Token should have been routed to agent-1 (single remaining running node)
			const agentEntry = Array.from(result.current.wsNodeExecutions.values()).find(
				(e) => e.node_id === "agent-1",
			);
			expect(agentEntry?.output_data?.raw).toContain("Here are the results...");
		});
	});

	describe("clearState", () => {
		it("should reset all state", () => {
			const { result } = renderHook(() => useTimelineState());

			// Add some data
			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {});
			});

			expect(result.current.wsNodeExecutions.size).toBe(1);
			expect(result.current.runningNodes.size).toBe(1);

			// Clear
			act(() => {
				result.current.clearState();
			});

			expect(result.current.wsNodeExecutions.size).toBe(0);
			expect(result.current.runningNodes.size).toBe(0);
		});
	});

	describe("getNodeExecutions", () => {
		it("should return array of entries from ref", () => {
			const { result } = renderHook(() => useTimelineState());

			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_name: "Agent 1",
				});
				result.current.handleNodeUpdate("node2", "running", undefined, {
					node_name: "Agent 2",
				});
			});

			const executions = result.current.getNodeExecutions();
			expect(executions).toHaveLength(2);
			expect(executions.map((e) => e.node_name)).toEqual(
				expect.arrayContaining(["Agent 1", "Agent 2"]),
			);
		});
	});

	describe("onExecutionChange callback", () => {
		it("should call onExecutionChange when state updates", () => {
			const onExecutionChange = jest.fn();

			const { result } = renderHook(() =>
				useTimelineState({
					onExecutionChange,
					executionId: "exec-123",
					dbExecutionId: "db-456",
				}),
			);

			act(() => {
				result.current.handleNodeUpdate("node1", "running", undefined, {
					node_name: "Agent 1",
				});
			});

			expect(onExecutionChange).toHaveBeenCalledWith(
				expect.objectContaining({
					id: "exec-123",
					db_execution_id: "db-456",
					status: "running",
					node_executions: expect.any(Array),
				}),
			);
		});
	});
});
