import { act, renderHook } from "@testing-library/react";
import type {
	SubAgentCompleteEvent,
	SubAgentStartEvent,
	ToolCallCompleteEvent,
	ToolCallErrorEvent,
	ToolCallProgressEvent,
	ToolCallStartEvent,
} from "@/hooks/useExecutionWebSocket";
import { useExecutionStreaming } from "./useExecutionStreaming";

describe("useExecutionStreaming", () => {
	describe("handler coordination", () => {
		it("should update both timeline and activity on tool_call_start", () => {
			const { result } = renderHook(() => useExecutionStreaming());

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
				result.current.handlers.onToolCallStart(event);
			});

			// Check timeline updated
			expect(result.current.wsNodeExecutions.size).toBe(1);
			const timelineEntry = Array.from(
				result.current.wsNodeExecutions.values(),
			)[0];
			expect(timelineEntry.status).toBe("running");
			expect(timelineEntry.node_name).toBe("Document Search");

			// Check activity updated
			expect(result.current.activities.length).toBe(1);
			expect(result.current.activities[0].type).toBe("tool_call");
			expect(result.current.activities[0].status).toBe("running");
		});

		it("should update both on tool_call_complete", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			// Start tool
			act(() => {
				result.current.handlers.onToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "agent-1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
					tool_node_name: "Search Tool",
				});
			});

			// Complete tool
			const completeEvent: ToolCallCompleteEvent = {
				call_id: "call-1",
				tool_name: "search",
				duration_ms: 500,
				timestamp: new Date().toISOString(),
				tool_node_id: "tool-1",
				result_preview: "Found results",
			};

			act(() => {
				result.current.handlers.onToolCallComplete(completeEvent);
			});

			// Both should be complete
			const timelineEntry = Array.from(
				result.current.wsNodeExecutions.values(),
			)[0];
			expect(timelineEntry.status).toBe("completed");
			expect(result.current.activities[0].status).toBe("complete");
		});

		it("should update both on tool_call_error", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			// Start tool
			act(() => {
				result.current.handlers.onToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "agent-1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
				});
			});

			// Error
			const errorEvent: ToolCallErrorEvent = {
				call_id: "call-1",
				tool_name: "search",
				error: "Connection failed",
				duration_ms: 1000,
				timestamp: new Date().toISOString(),
				tool_node_id: "tool-1",
			};

			act(() => {
				result.current.handlers.onToolCallError(errorEvent);
			});

			// Both should show error
			const timelineEntry = Array.from(
				result.current.wsNodeExecutions.values(),
			)[0];
			expect(timelineEntry.status).toBe("failed");
			expect(result.current.activities[0].status).toBe("error");
		});

		it("should handle tool progress (activity only)", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			// Start tool
			act(() => {
				result.current.handlers.onToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "agent-1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
				});
			});

			// Progress update
			const progressEvent: ToolCallProgressEvent = {
				call_id: "call-1",
				tool_name: "search",
				message: "Processing 50%",
				progress: 50,
				timestamp: new Date().toISOString(),
			};

			act(() => {
				result.current.handlers.onToolCallProgress(progressEvent);
			});

			// Activity should show progress
			const activity = result.current.activities[0];
			if (activity.type === "tool_call") {
				expect(activity.progressMessage).toBe("Processing 50%");
				expect(activity.progressPercent).toBe(50);
			}
		});

		it("should handle sub-agent start (activity only)", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			const event: SubAgentStartEvent = {
				subagent_id: "sub-1",
				subagent_name: "Research Agent",
				task_description: "Find documents",
				parent_agent_id: "agent-1",
				parent_agent_name: "Main Agent",
				timestamp: new Date().toISOString(),
			};

			act(() => {
				result.current.handlers.onSubAgentStart(event);
			});

			// Activity should have sub-agent
			expect(result.current.activities.length).toBe(1);
			expect(result.current.activities[0].type).toBe("subagent");
			expect(result.current.activities[0].status).toBe("running");
		});

		it("should handle sub-agent complete (activity only)", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			// Start sub-agent
			act(() => {
				result.current.handlers.onSubAgentStart({
					subagent_id: "sub-1",
					subagent_name: "Research Agent",
					task_description: "Find documents",
					parent_agent_id: "agent-1",
					parent_agent_name: "Main Agent",
					timestamp: new Date().toISOString(),
				});
			});

			// Complete sub-agent
			const completeEvent: SubAgentCompleteEvent = {
				subagent_id: "sub-1",
				subagent_name: "Research Agent",
				success: true,
				response_preview: "Found 5 documents",
				duration_ms: 2000,
				tools_used: ["document_search", "web_search"],
				timestamp: new Date().toISOString(),
			};

			act(() => {
				result.current.handlers.onSubAgentComplete(completeEvent);
			});

			// Activity should show complete
			expect(result.current.activities[0].status).toBe("complete");
		});

		it("should handle node update (timeline only)", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {
					node_name: "Agent 1",
					node_type: "AGENT",
					database_node_id: "db-123",
				});
			});

			// Timeline should have entry
			expect(result.current.wsNodeExecutions.size).toBe(1);
			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.node_name).toBe("Agent 1");
			expect(entry.status).toBe("running");

			// Activities should be empty (node update doesn't affect activity feed)
			expect(result.current.activities.length).toBe(0);
		});

		it("should handle token stream (timeline only)", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			// Start a node first
			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {
					node_type: "AGENT",
				});
			});

			// Stream tokens
			act(() => {
				result.current.handlers.onTokenStream({
					nodeId: "node1",
					content: "Hello ",
				});
				result.current.handlers.onTokenStream({
					nodeId: "node1",
					content: "world",
				});
			});

			// Timeline should accumulate tokens
			const entry = Array.from(result.current.wsNodeExecutions.values())[0];
			expect(entry.output_data?.raw).toBe("Hello world");
		});
	});

	describe("clearState", () => {
		it("should clear both timeline and activities", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			// Add data to both
			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {
					node_name: "Agent",
				});
				result.current.handlers.onToolCallStart({
					call_id: "call-1",
					tool_name: "search",
					tool_args: {},
					agent_id: "a1",
					agent_name: "Agent",
					timestamp: new Date().toISOString(),
					tool_node_id: "tool-1",
				});
			});

			expect(result.current.wsNodeExecutions.size).toBeGreaterThan(0);
			expect(result.current.activities.length).toBeGreaterThan(0);

			act(() => {
				result.current.clearState();
			});

			expect(result.current.wsNodeExecutions.size).toBe(0);
			expect(result.current.activities.length).toBe(0);
		});
	});

	describe("options passthrough", () => {
		it("should pass onExecutionChange to timeline", () => {
			const onExecutionChange = jest.fn();

			const { result } = renderHook(() =>
				useExecutionStreaming({
					onExecutionChange,
					executionId: "exec-1",
				}),
			);

			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {
					node_name: "Agent",
				});
			});

			expect(onExecutionChange).toHaveBeenCalled();
		});

		it("should pass onNodeRunning callback", () => {
			const onNodeRunning = jest.fn();

			const { result } = renderHook(() =>
				useExecutionStreaming({ onNodeRunning }),
			);

			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {});
			});

			expect(onNodeRunning).toHaveBeenCalledWith("node1");
		});

		it("should pass onNodeStopped callback", () => {
			const onNodeStopped = jest.fn();

			const { result } = renderHook(() =>
				useExecutionStreaming({ onNodeStopped }),
			);

			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {});
			});
			act(() => {
				result.current.handlers.onNodeUpdate(
					"node1",
					"completed",
					undefined,
					{},
				);
			});

			expect(onNodeStopped).toHaveBeenCalledWith(null);
		});

		it("should respect maxActivities option", () => {
			const { result } = renderHook(() =>
				useExecutionStreaming({ maxActivities: 2 }),
			);

			// Add 3 activities
			act(() => {
				for (let i = 0; i < 3; i++) {
					result.current.handlers.onToolCallStart({
						call_id: `call-${i}`,
						tool_name: "search",
						tool_args: {},
						agent_id: "a1",
						agent_name: "Agent",
						timestamp: new Date().toISOString(),
						tool_node_id: `tool-${i}`,
					});
				}
			});

			// Should be limited to 2
			expect(result.current.activities.length).toBeLessThanOrEqual(2);
		});
	});

	describe("utilities", () => {
		it("should expose loadInitialData from timeline", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			const nodes = [
				{
					id: "exec-1",
					node_id: "node1",
					node_name: "Start",
					node_type: "START" as const,
					status: "completed" as const,
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

			expect(result.current.wsNodeExecutions.size).toBe(1);
		});

		it("should expose getNodeExecutions from timeline", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {
					node_name: "Agent 1",
				});
				result.current.handlers.onNodeUpdate("node2", "running", undefined, {
					node_name: "Agent 2",
				});
			});

			const executions = result.current.getNodeExecutions();
			expect(executions).toHaveLength(2);
		});

		it("should expose runningNodes from timeline", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {});
			});

			expect(result.current.runningNodes.has("node1")).toBe(true);
		});

		it("should expose wsNodeExecutionsRef for closures", () => {
			const { result } = renderHook(() => useExecutionStreaming());

			act(() => {
				result.current.handlers.onNodeUpdate("node1", "running", undefined, {});
			});

			expect(result.current.wsNodeExecutionsRef.current.size).toBe(1);
		});
	});
});
