"use client";

import { Info } from "lucide-react";
import React from "react";
import type { ToolOption } from "./ToolTile";

interface ToolInfoPanelProps {
	selectedToolOption: ToolOption | undefined;
}

export default function ToolInfoPanel({
	selectedToolOption,
}: ToolInfoPanelProps) {
	const getToolDescription = () => {
		switch (selectedToolOption?.value) {
			case "document_search":
				return (
					<>
						<strong className="text-blue-700">Document Search:</strong>{" "}
						Enable your agent to search through configured document collections
						with semantic understanding. Perfect for knowledge bases,
						documentation, and research materials.
					</>
				);
			case "database_query":
				return (
					<>
						<strong className="text-[#0DA931]">Database Query:</strong>{" "}
						Connect to SQL databases and execute queries safely. Ideal for data
						retrieval, reporting, and analytics workflows.
					</>
				);
			case "http_request":
				return (
					<>
						<strong className="text-[#0DA931]">HTTP Request:</strong> Make API
						calls to external services and webhooks. Great for integrating with
						third-party services and custom endpoints.
					</>
				);
			case "web_search":
				return (
					<>
						<strong className="text-orange-700">Web Search:</strong> Search the
						internet for real-time information. Essential for research,
						fact-checking, and staying current.
					</>
				);
			case "mcp_server":
				return (
					<>
						<strong className="text-cyan-700">MCP Server:</strong> Connect to
						Model Context Protocol servers for advanced tool integration.
						Enables communication with specialized AI services and custom tools.
					</>
				);
			case "email_send":
				return (
					<>
						<strong className="text-emerald-700">Email Send:</strong> Send
						emails with AI-generated content directly from your workflow.
						Supports templates, dynamic recipients, and rich formatting for
						notifications and outreach.
					</>
				);
			case "file_write":
				return (
					<>
						<strong className="text-amber-800">File Write:</strong> Write and
						save files to a sandboxed workspace directory. Useful for generating
						reports, exporting data, and creating structured output files.
					</>
				);
			case "document_retrieve":
				return (
					<>
						<strong className="text-teal-700">Document Retrieve:</strong>{" "}
						Retrieve full document content from your configured collections.
					</>
				);
			default:
				return (
					<span className="text-slate-600">
						Select a tool to extend your agent&apos;s capabilities.
					</span>
				);
		}
	};

	return (
		<div className="relative rounded-2xl border border-slate-200 bg-white shadow-sm">
			<div className="flex gap-3 p-4">
				<div className="shrink-0 self-start rounded-lg border border-orange-200 bg-orange-100 p-2">
					<Info className="h-4 w-4 text-orange-600" />
				</div>
				<div className="min-w-0 flex-1 text-sm leading-relaxed text-slate-700">
					{getToolDescription()}
				</div>
			</div>
		</div>
	);
}
