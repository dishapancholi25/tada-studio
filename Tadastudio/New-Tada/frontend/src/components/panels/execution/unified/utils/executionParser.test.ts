import type { NodeExecution } from "@/types/api";
import type {
	DatabaseQueryExecution,
	HttpRequestExecution,
	FileWriteExecution,
} from "../types/execution.types";
import { parseToolExecutions } from "./executionParser";

describe("executionParser", () => {
	describe("review_iteration propagation", () => {
		it("should propagate review_iteration from node to tool executions", () => {
			const node: NodeExecution = {
				id: "test-id",
				node_id: "http-node-1",
				node_name: "HTTP Request",
				node_type: "HTTP_REQUEST",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.5,
				input_data: {
					url: "https://api.example.com/data",
					method: "GET",
				},
				output_data: {
					status_code: 200,
					body: { result: "success" },
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				review_iteration: 2, // Second review iteration
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"http_request",
			) as HttpRequestExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].review_iteration).toBe(2);
		});

		it("should handle undefined review_iteration gracefully", () => {
			const node: NodeExecution = {
				id: "test-id",
				node_id: "db-node-1",
				node_name: "Database Query",
				node_type: "DATABASE_QUERY",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.3,
				input_data: { query: "SELECT 1" },
				output_data: { results: [{ "1": 1 }], rowCount: 1 },
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				// review_iteration is undefined/not present
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"database_query",
			) as DatabaseQueryExecution[];

			expect(executions).toHaveLength(1);
			// Should not have review_iteration when not present on node
			expect(executions[0].review_iteration).toBeUndefined();
		});

		it("should propagate review_iteration=1 (first iteration)", () => {
			const node: NodeExecution = {
				id: "test-id",
				node_id: "http-node-2",
				node_name: "HTTP Request",
				node_type: "HTTP_REQUEST",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.4,
				input_data: {
					url: "https://api.example.com/submit",
					method: "POST",
				},
				output_data: {
					status_code: 201,
					body: { id: 123 },
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				review_iteration: 1, // First review iteration
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"http_request",
			) as HttpRequestExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].review_iteration).toBe(1);
		});
	});

	describe("parseDatabaseQueryNode", () => {
		it("should parse database query node with JSON string input_data", () => {
			const node: NodeExecution = {
				id: "test-id",
				node_id: "4684949d-0e4c-4e63-9d77-b04ee20b3f00",
				node_name: "Database Query",
				node_type: "DATABASE_QUERY",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.25,
				// This is how it comes from the API - as a JSON string
				input_data:
					'{"query": "SELECT * FROM node_executions ORDER BY start_time DESC LIMIT 3"}',
				output_data: {
					results: [
						{ id: 1, node_name: "Test Node 1", status: "completed" },
						{ id: 2, node_name: "Test Node 2", status: "completed" },
						{ id: 3, node_name: "Test Node 3", status: "completed" },
					],
					rowCount: 3,
					columns: ["id", "node_name", "status"],
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"database_query",
			) as DatabaseQueryExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].tool).toBe("database_query");
			expect(executions[0].query).toBe(
				"SELECT * FROM node_executions ORDER BY start_time DESC LIMIT 3",
			);
			expect(executions[0].results).toBeDefined();
			expect(executions[0].parsed_results).toBeDefined();
			expect(executions[0].parsed_results?.rowCount).toBe(3);
		});

		it("should parse database query node with object input_data", () => {
			const node: NodeExecution = {
				id: "test-id",
				node_id: "test-node-2",
				node_name: "Database Query",
				node_type: "DATABASE_QUERY",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.3,
				// This is an object, not a string
				input_data: { query: "SELECT COUNT(*) as total FROM users" },
				output_data:
					'{"results": [{"total": 42}], "rowCount": 1, "columns": ["total"]}',
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"database_query",
			) as DatabaseQueryExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].query).toBe("SELECT COUNT(*) as total FROM users");
			expect(executions[0].results).toBeDefined();
			expect(executions[0].parsed_results?.rowCount).toBe(1);
		});

		it("should handle malformed JSON gracefully", () => {
			const node: NodeExecution = {
				id: "test-id",
				node_id: "test-node-3",
				node_name: "Database Query",
				node_type: "DATABASE_QUERY",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.2,
				// Not valid JSON
				input_data: "SELECT * FROM users",
				output_data: "Query executed successfully",
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"database_query",
			) as DatabaseQueryExecution[];

			expect(executions).toHaveLength(1);
			// Should use the string as-is when it's not valid JSON
			expect(executions[0].query).toBe("SELECT * FROM users");
			expect(executions[0].results).toBe("Query executed successfully");
		});
	});

	describe("parseFileWriteNode", () => {
		it("should parse file write node with result nested in output_data", () => {
			const node: NodeExecution = {
				id: "test-file-id",
				node_id: "file-write-node-1",
				node_name: "File Write",
				node_type: "FILE_WRITE",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.15,
				input_data: {
					filename: "report.json",
					content_type: "text",
					subdirectory: "outputs",
				},
				output_data: {
					result: {
						filepath: "/workspace/outputs/report.json",
						file_size: 2048,
						success: true,
						content: '{"data": "test"}',
					},
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"file_write",
			) as FileWriteExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].tool).toBe("file_write");
			expect(executions[0].filename).toBe("report.json");
			expect(executions[0].filepath).toBe("/workspace/outputs/report.json");
			expect(executions[0].content_type).toBe("text");
			expect(executions[0].file_size).toBe(2048);
			expect(executions[0].subdirectory).toBe("outputs");
			expect(executions[0].status).toBe("success");
			expect(executions[0].content).toBe('{"data": "test"}');
		});

		it("should parse file write node with JSON string input_data", () => {
			const node: NodeExecution = {
				id: "test-file-id-2",
				node_id: "file-write-node-2",
				node_name: "File Write",
				node_type: "FILE_WRITE",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.1,
				// Input comes as JSON string
				input_data: '{"filename": "data.csv", "content_type": "text"}',
				output_data: {
					result: {
						filepath: "/workspace/data.csv",
						file_size: 512,
					},
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"file_write",
			) as FileWriteExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].filename).toBe("data.csv");
			expect(executions[0].filepath).toBe("/workspace/data.csv");
			expect(executions[0].content_type).toBe("text");
			expect(executions[0].status).toBe("success");
		});

		it("should detect failed status from error field", () => {
			const node: NodeExecution = {
				id: "test-file-id-3",
				node_id: "file-write-node-3",
				node_name: "File Write",
				node_type: "FILE_WRITE",
				execution_order: 1,
				status: "failed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.05,
				input_data: { filename: "failed.txt" },
				output_data: {
					result: {
						error: "Permission denied: cannot write to directory",
						success: false,
					},
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"file_write",
			) as FileWriteExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].status).toBe("failed");
			expect(executions[0].error).toBe(
				"Permission denied: cannot write to directory",
			);
		});

		it("should handle output_data directly without result nesting", () => {
			const node: NodeExecution = {
				id: "test-file-id-4",
				node_id: "file-write-node-4",
				node_name: "File Write",
				node_type: "FILE_WRITE",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.2,
				input_data: { filename: "output.md" },
				// output_data without result wrapper
				output_data: {
					filepath: "/workspace/output.md",
					file_size: 1024,
					content: "# Report\n\nContent here",
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"file_write",
			) as FileWriteExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].filename).toBe("output.md");
			expect(executions[0].filepath).toBe("/workspace/output.md");
			expect(executions[0].file_size).toBe(1024);
			expect(executions[0].content).toBe("# Report\n\nContent here");
		});

		it("should return empty array when no filename is found", () => {
			const node: NodeExecution = {
				id: "test-file-id-5",
				node_id: "file-write-node-5",
				node_name: "File Write",
				node_type: "FILE_WRITE",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.1,
				// No filename in input or output
				input_data: {},
				output_data: { result: { filepath: "/some/path" } },
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"file_write",
			) as FileWriteExecution[];

			expect(executions).toHaveLength(0);
		});

		it("should handle base64 content type", () => {
			const node: NodeExecution = {
				id: "test-file-id-6",
				node_id: "file-write-node-6",
				node_name: "File Write",
				node_type: "FILE_WRITE",
				execution_order: 1,
				status: "completed",
				start_time: new Date().toISOString(),
				end_time: new Date().toISOString(),
				duration_seconds: 0.3,
				input_data: { filename: "image.png", content_type: "base64" },
				output_data: {
					result: {
						filepath: "/workspace/image.png",
						file_size: 4096,
					},
				},
				error_message: null,
				node_metadata: null,
				is_sub_agent: false,
				input_tokens: null,
				output_tokens: null,
				total_tokens: null,
				token_metadata: null,
				created_at: new Date().toISOString(),
			};

			const executions = parseToolExecutions(
				node,
				"file_write",
			) as FileWriteExecution[];

			expect(executions).toHaveLength(1);
			expect(executions[0].content_type).toBe("base64");
			expect(executions[0].filename).toBe("image.png");
		});
	});
});
