import {
	generateInlinePreview,
	formatExpandedResult,
	getToolDisplayInfo,
	summarizeToolGroup,
	unwrapToolArgs,
} from "./toolCallDisplayUtils";

describe("toolCallDisplayUtils", () => {
	// ========================================================================
	// getToolDisplayInfo
	// ========================================================================
	describe("getToolDisplayInfo", () => {
		it("extracts toolAction from MCP_SERVER tool args target", () => {
			const result = getToolDisplayInfo(
				"mcp_server_abc123",
				"SharePoint MCP Server",
				"MCP_SERVER",
				{ action: "tool", target: "search_content", arguments: { query: "APA" } },
			);
			expect(result.displayName).toBe("SharePoint MCP Server");
			expect(result.toolAction).toBe("Search Content");
		});

		it("extracts toolAction from MCP adapter tool_name field", () => {
			const result = getToolDisplayInfo(
				"mcp_adapter_abc123",
				"SharePoint MCP Server",
				"MCP_SERVER",
				{ action: "tool_call", tool_name: "search_files", arguments: { query: "APA" } },
			);
			expect(result.displayName).toBe("SharePoint MCP Server");
			expect(result.toolAction).toBe("Search Files");
		});

		it("prefers tool_name over target when both present", () => {
			const result = getToolDisplayInfo(
				"mcp_adapter_abc",
				"Notion MCP",
				"MCP_SERVER",
				{ action: "tool_call", tool_name: "search_pages", target: "fallback" },
			);
			expect(result.toolAction).toBe("Search Pages");
		});

		it("returns no toolAction for non-MCP tools", () => {
			const result = getToolDisplayInfo(
				"search_web_abc123",
				"Web Search",
				"WEB_SEARCH",
				{ query: "test" },
			);
			expect(result.displayName).toBe("Web Search");
			expect(result.toolAction).toBeUndefined();
		});

		it("uses toolNodeName when available for non-MCP", () => {
			const result = getToolDisplayInfo("http_request_xyz", "My HTTP Node", "HTTP_REQUEST");
			expect(result.displayName).toBe("My HTTP Node");
		});

		it("formats raw tool name when no node name given", () => {
			const result = getToolDisplayInfo("search_web_abc123");
			expect(result.displayName).toBe("Web Abc123");
		});

		it("handles MCP tool without target in args", () => {
			const result = getToolDisplayInfo(
				"mcp_server_abc",
				"Notion MCP",
				"MCP_SERVER",
				{ action: "discover" },
			);
			expect(result.displayName).toBe("Notion MCP");
			expect(result.toolAction).toBeUndefined();
		});
	});

	// ========================================================================
	// unwrapToolArgs
	// ========================================================================
	describe("unwrapToolArgs", () => {
		it("unwraps MCP arguments wrapper to inner arguments", () => {
			const result = unwrapToolArgs(
				{
					action: "tool",
					target: "search_content",
					arguments: { query: "APA", entity_types: "driveItem", page_size: 10 },
				},
				"MCP_SERVER",
			);
			expect(result).toEqual({ query: "APA", entity_types: "driveItem", page_size: 10 });
		});

		it("unwraps MCP adapter args with tool_name", () => {
			const result = unwrapToolArgs(
				{
					action: "tool_call",
					tool_name: "search_files",
					arguments: { site_id: "abc", query: "budget" },
				},
				"MCP_SERVER",
			);
			expect(result).toEqual({ site_id: "abc", query: "budget" });
		});

		it("strips action/target/tool_name when no inner arguments object", () => {
			const result = unwrapToolArgs(
				{ action: "discover", target: "list_tools", extra_param: "value" },
				"MCP_SERVER",
			);
			expect(result).toEqual({ extra_param: "value" });
		});

		it("returns original args when no extra keys after stripping", () => {
			const result = unwrapToolArgs(
				{ action: "discover", target: "list_tools" },
				"MCP_SERVER",
			);
			expect(result).toEqual({ action: "discover", target: "list_tools" });
		});

		it("returns args unchanged for non-MCP tools", () => {
			const args = { url: "https://example.com", method: "GET" };
			const result = unwrapToolArgs(args, "HTTP_REQUEST");
			expect(result).toEqual(args);
		});

		it("returns args unchanged when no toolNodeType", () => {
			const args = { query: "test" };
			const result = unwrapToolArgs(args);
			expect(result).toEqual(args);
		});
	});

	// ========================================================================
	// generateInlinePreview
	// ========================================================================
	describe("generateInlinePreview", () => {
		// --- Valid JSON cases ---
		it("shows count for results array", () => {
			const json = JSON.stringify({ results: [{ id: 1 }, { id: 2 }, { id: 3 }] });
			expect(generateInlinePreview(json)).toBe("Found 3 results");
		});

		it("shows count with total for partial results", () => {
			const json = JSON.stringify({ results: [{ id: 1 }, { id: 2 }], total: 42 });
			expect(generateInlinePreview(json)).toBe("Found 2 of 42 results");
		});

		it("shows count for items array", () => {
			const json = JSON.stringify({ items: [{ name: "a" }] });
			expect(generateInlinePreview(json)).toBe("Found 1 item");
		});

		it("shows empty array message", () => {
			const json = JSON.stringify({ results: [] });
			expect(generateInlinePreview(json)).toBe("No results found");
		});

		it("shows error message from result", () => {
			const json = JSON.stringify({ error: "Permission denied" });
			expect(generateInlinePreview(json)).toBe("Error: Permission denied");
		});

		it("shows message field", () => {
			const json = JSON.stringify({ message: "Email sent successfully" });
			expect(generateInlinePreview(json)).toBe("Email sent successfully");
		});

		it("shows success status", () => {
			const json = JSON.stringify({ status: "success" });
			expect(generateInlinePreview(json)).toBe("Completed successfully");
		});

		it("shows content field truncated", () => {
			const json = JSON.stringify({ content: "This is a long document content that should be truncated appropriately for the preview display." });
			const preview = generateInlinePreview(json);
			expect(preview).toContain("This is a long document");
			expect(preview.length).toBeLessThanOrEqual(83); // 80 + "..."
		});

		it("shows table dimensions", () => {
			const json = JSON.stringify({ columns: ["a", "b", "c"], rows: [{}, {}, {}, {}] });
			expect(generateInlinePreview(json)).toBe("4 rows, 3 columns");
		});

		it("shows name field for single objects", () => {
			const json = JSON.stringify({ name: "My Document.pdf", size: 1024 });
			expect(generateInlinePreview(json)).toBe("My Document.pdf");
		});

		it("handles top-level array", () => {
			const json = JSON.stringify([{ id: 1 }, { id: 2 }]);
			expect(generateInlinePreview(json)).toBe("Found 2 items");
		});

		it("handles double-encoded JSON", () => {
			const inner = JSON.stringify({ results: [{ id: 1 }] });
			const doubled = JSON.stringify(inner);
			expect(generateInlinePreview(doubled)).toBe("Found 1 result");
		});

		// --- Truncated JSON cases (backend 500-char limit) ---
		it("extracts count from truncated JSON with results array", () => {
			const preview = '{ "results": [ { "id": "01FG", "name": "doc1" }, { "id": "02AB", "name": "doc2" }, { "id": "03CD", "name": "doc3" ...';
			const result = generateInlinePreview(preview);
			expect(result).toMatch(/Found 3\+ results/);
		});

		it("extracts count from truncated JSON with items array", () => {
			const preview = '{ "items": [ { "title": "Page 1" }, { "title": "Page 2" } ...';
			const result = generateInlinePreview(preview);
			expect(result).toMatch(/Found 2\+ items/);
		});

		it("extracts count with total from truncated JSON", () => {
			const preview = '{ "total": 42, "results": [ { "id": "abc" }, { "id": "def" } ...';
			const result = generateInlinePreview(preview);
			expect(result).toBe("Found 2+ of 42 results");
		});

		it("extracts error from truncated JSON", () => {
			const preview = '{ "error": "Access denied", "code": 403, "details": { "re...';
			expect(generateInlinePreview(preview)).toBe("Error: Access denied");
		});

		it("extracts message from truncated JSON", () => {
			const preview = '{ "message": "File uploaded successfully", "file_id": "abc...';
			expect(generateInlinePreview(preview)).toBe("File uploaded successfully");
		});

		it("extracts name from truncated JSON", () => {
			const preview = '{ "name": "Budget Report 2024.xlsx", "size": 1048576, "cre...';
			expect(generateInlinePreview(preview)).toBe("Budget Report 2024.xlsx");
		});

		it("returns fallback for bare opening brace", () => {
			expect(generateInlinePreview("{")).toBe("Result received");
		});

		it("returns fallback for bare opening bracket", () => {
			expect(generateInlinePreview("[")).toBe("Result received");
		});

		it("handles non-JSON text gracefully", () => {
			expect(generateInlinePreview("Operation completed")).toBe("Operation completed");
		});
	});

	// ========================================================================
	// formatExpandedResult
	// ========================================================================
	describe("formatExpandedResult", () => {
		it("pretty-prints valid JSON", () => {
			const json = JSON.stringify({ key: "value", count: 5 });
			const result = formatExpandedResult(json);
			expect(result).toContain('"key": "value"');
			expect(result).toContain('"count": 5');
		});

		it("truncates long JSON output", () => {
			const data = { items: Array.from({ length: 50 }, (_, i) => ({ id: i, name: `Item ${i}` })) };
			const json = JSON.stringify(data);
			const result = formatExpandedResult(json);
			expect(result).toContain("more lines");
		});

		it("returns raw text for non-JSON", () => {
			expect(formatExpandedResult("plain text result")).toBe("plain text result");
		});

		it("handles double-encoded JSON", () => {
			const inner = JSON.stringify({ hello: "world" });
			const doubled = JSON.stringify(inner);
			const result = formatExpandedResult(doubled);
			expect(result).toContain('"hello": "world"');
		});
	});

	// ========================================================================
	// summarizeToolGroup
	// ========================================================================
	describe("summarizeToolGroup", () => {
		it("shows single provider name when all same type", () => {
			const tools = [
				{ toolNodeName: "SharePoint MCP Server", toolNodeType: "MCP_SERVER", status: "complete" },
				{ toolNodeName: "SharePoint MCP Server", toolNodeType: "MCP_SERVER", status: "complete" },
				{ toolNodeName: "SharePoint MCP Server", toolNodeType: "MCP_SERVER", status: "complete" },
			];
			const { label } = summarizeToolGroup(tools);
			expect(label).toBe("Used 3 SharePoint MCP Server calls");
		});

		it("shows breakdown for mixed types", () => {
			const tools = [
				{ toolNodeName: "SharePoint MCP Server", toolNodeType: "MCP_SERVER", status: "complete" },
				{ toolNodeName: "SharePoint MCP Server", toolNodeType: "MCP_SERVER", status: "complete" },
				{ toolNodeName: "Web Search", toolNodeType: "WEB_SEARCH", status: "complete" },
			];
			const { label } = summarizeToolGroup(tools);
			expect(label).toContain("Used 3 tools");
			expect(label).toContain("2 SharePoint MCP Server");
			expect(label).toContain("1 Web Search");
		});

		it("uses 'Using' verb when tools are running", () => {
			const tools = [
				{ toolNodeName: "SharePoint MCP Server", status: "running" },
				{ toolNodeName: "SharePoint MCP Server", status: "complete" },
			];
			const { label, isRunning } = summarizeToolGroup(tools);
			expect(label).toMatch(/^Using/);
			expect(isRunning).toBe(true);
		});

		it("uses 'Used' verb when all complete", () => {
			const tools = [
				{ toolNodeName: "HTTP Request", status: "complete" },
			];
			const { label, isRunning } = summarizeToolGroup(tools);
			expect(label).toMatch(/^Used/);
			expect(isRunning).toBe(false);
		});
	});
});
