"use client";

import JsonTree from "@/components/json-viewer/JsonTree";
import {
	Check,
	Code,
	Copy,
	Database,
	Eye,
	EyeOff,
	FileJson,
	MessageSquare,
	Table,
	Terminal,
} from "lucide-react";
import React, { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import SyntaxHighlighter from "react-syntax-highlighter";
import { atomOneDark } from "react-syntax-highlighter/dist/esm/styles/hljs";
import remarkGfm from "remark-gfm";

interface SmartDataViewerProps {
	data: any;
	title?: string;
	className?: string;
	defaultViewMode?: "smart" | "raw";
	maxHeight?: string;
}

type ContentType =
	| "json"
	| "markdown"
	| "sql"
	| "code"
	| "table"
	| "text"
	| "empty";

export default function SmartDataViewer({
	data,
	title,
	className = "",
	defaultViewMode = "smart",
	maxHeight = "600px",
}: SmartDataViewerProps) {
	const [viewMode, setViewMode] = useState<"smart" | "raw">(defaultViewMode);
	const [copied, setCopied] = useState(false);

	// Extract content from nested structures
	const extractContent = (data: any): any => {
		// Check for common response patterns
		if (data && typeof data === "object") {
			// Check for response field (common in agent outputs)
			if ("response" in data && data.response) {
				return data.response;
			}
			// Check for result field
			if ("result" in data && data.result) {
				return data.result;
			}
			// Check for message field
			if ("message" in data && data.message) {
				return data.message;
			}
			// Check for content field
			if ("content" in data && data.content) {
				return data.content;
			}
			// Check for output field
			if ("output" in data && data.output) {
				return data.output;
			}
			// Check for text field
			if ("text" in data && data.text) {
				return data.text;
			}
			// Check for answer field
			if ("answer" in data && data.answer) {
				return data.answer;
			}
		}
		return data;
	};

	// Detect content type
	const detectContentType = (value: any): ContentType => {
		if (value === null || value === undefined) return "empty";

		// First try to extract content from nested structures
		const extractedValue = extractContent(value);

		// Check for markdown indicators
		if (typeof extractedValue === "string") {
			const strValue = extractedValue.trim();

			// SQL detection
			if (
				/^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\s+/i.test(strValue)
			) {
				return "sql";
			}

			// Check if it looks like natural language (for agent responses)
			// More lenient detection for agent outputs
			if (
				strValue.length > 20 && // Has some content
				/[a-zA-Z]/.test(strValue) && // Contains letters
				(strValue.split(" ").length > 3 || // Has multiple words
					/[.!?]/.test(strValue)) // Or has punctuation
			) {
				return "markdown";
			}

			// Markdown detection (headers, lists, links, code blocks)
			if (
				/^#{1,6}\s+/m.test(strValue) || // Headers
				/^\s*[-*+]\s+/m.test(strValue) || // Lists
				/\[.*?\]\(.*?\)/.test(strValue) || // Links
				/```[\s\S]*?```/.test(strValue) || // Code blocks
				/^\s*>\s+/m.test(strValue) // Blockquotes
			) {
				return "markdown";
			}

			// Code detection (simple heuristics)
			if (
				/function\s+\w+\s*\(/.test(strValue) ||
				/const\s+\w+\s*=/.test(strValue) ||
				/class\s+\w+/.test(strValue) ||
				/import\s+.+from/.test(strValue)
			) {
				return "code";
			}

			return "text";
		}

		// Check for table-like data (array of objects with consistent keys)
		if (
			Array.isArray(value) &&
			value.length > 0 &&
			typeof value[0] === "object"
		) {
			const firstKeys = Object.keys(value[0]);
			const isTable = value.every(
				(item) =>
					typeof item === "object" &&
					Object.keys(item).length === firstKeys.length &&
					firstKeys.every((key) => key in item),
			);
			if (isTable) return "table";
		}

		// Default to JSON for objects and arrays
		if (typeof value === "object") return "json";

		return "text";
	};

	const extractedContent = useMemo(() => extractContent(data), [data]);
	const contentType = useMemo(() => detectContentType(data), [data]);

	const copyToClipboard = async () => {
		try {
			const text =
				typeof data === "string" ? data : JSON.stringify(data, null, 2);
			await navigator.clipboard.writeText(text);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	};

	// Render table view for array data
	const renderTable = (tableData: any[]) => {
		if (!tableData || tableData.length === 0) return null;

		const columns = Object.keys(tableData[0]);

		return (
			<div className="overflow-auto rounded-xl border border-[color:var(--color-border)]/40">
				<table className="w-full text-sm">
					<thead>
						<tr className="border-b border-[color:var(--color-border)]/60">
							{columns.map((col) => (
								<th
									key={col}
									className="px-4 py-3 text-left text-[0.65rem] capitalize font-semibold text-[color:var(--color-text-secondary)] sticky top-0 bg-[color:var(--color-surface)]/80 backdrop-blur-sm"
								>
									{col}
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{tableData.slice(0, 100).map((row, idx) => (
							<tr
								key={`row-${JSON.stringify(row).substring(0, 50)}-${idx}`}
								className="border-b border-[color:var(--color-border)]/30 hover:bg-[color:var(--color-surface-hover)]/50 transition-colors duration-150"
							>
								{columns.map((col) => (
									<td
										key={col}
										className="px-4 py-3 text-[color:var(--color-text-primary)]"
									>
										{typeof row[col] === "object"
											? JSON.stringify(row[col])
											: String(row[col] ?? "")}
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
				{tableData.length > 100 && (
					<div className="text-center py-3 text-sm text-[color:var(--color-text-muted)] border-t border-[color:var(--color-border)]/30">
						Showing first 100 of {tableData.length} rows
					</div>
				)}
			</div>
		);
	};

	// Render smart view based on content type
	const renderSmartView = () => {
		switch (contentType) {
			case "empty":
				return (
					<div className="text-[color:var(--color-text-muted)] text-sm italic">
						No data available
					</div>
				);

			case "markdown":
				return (
					<div className="prose prose-sm prose-invert max-w-none prose-p:my-2 prose-headings:mt-4 prose-headings:mb-2">
						<ReactMarkdown
							remarkPlugins={[remarkGfm]}
							components={{
								code({ className, children, ...props }: any) {
									const match = /language-(\w+)/.exec(className || "");
									const inline = props.inline;
									return !inline && match ? (
										<SyntaxHighlighter
											style={atomOneDark}
											language={match[1]}
											PreTag="div"
											customStyle={{
												backgroundColor: "rgba(0, 0, 0, 0.2)",
												padding: "0.75rem",
												borderRadius: "0.75rem",
												fontSize: "0.875rem",
												border: "1px solid rgba(var(--color-border-rgb), 0.4)",
											}}
											{...props}
										>
											{String(children).replace(/\n$/, "")}
										</SyntaxHighlighter>
									) : (
										<code
											className="bg-[rgba(var(--color-primary-rgb),0.1)] px-1.5 py-0.5 rounded-md text-sm text-[color:var(--color-primary-light)]"
											{...props}
										>
											{children}
										</code>
									);
								},
								pre({ children }) {
									return <div className="my-2">{children}</div>;
								},
								table({ children }) {
									return (
										<table className="w-full border-collapse rounded-xl overflow-hidden">
											{children}
										</table>
									);
								},
								th({ children }) {
									return (
										<th className="border border-[color:var(--color-border)]/40 px-4 py-3 text-left text-[0.65rem] capitalize font-semibold bg-[color:var(--color-surface)]/60">
											{children}
										</th>
									);
								},
								td({ children }) {
									return (
										<td className="border border-[color:var(--color-border)]/30 px-4 py-3">
											{children}
										</td>
									);
								},
							}}
						>
							{String(extractedContent)}
						</ReactMarkdown>
					</div>
				);

			case "sql":
				return (
					<SyntaxHighlighter
						language="sql"
						style={atomOneDark}
						customStyle={{
							backgroundColor: "transparent",
							padding: "0",
							margin: "0",
							fontSize: "0.875rem",
						}}
					>
						{String(extractedContent)}
					</SyntaxHighlighter>
				);

			case "code":
				return (
					<SyntaxHighlighter
						language="javascript"
						style={atomOneDark}
						customStyle={{
							backgroundColor: "transparent",
							padding: "0",
							margin: "0",
							fontSize: "0.875rem",
						}}
					>
						{String(extractedContent)}
					</SyntaxHighlighter>
				);

			case "table":
				return renderTable(data);

			case "json":
				return (
					<div className="p-2">
						<JsonTree data={data} defaultExpandedDepth={2} />
					</div>
				);

			case "text":
			default:
				return (
					<pre className="text-sm text-[color:var(--color-text-primary)] whitespace-pre-wrap font-mono p-2">
						{String(extractedContent)}
					</pre>
				);
		}
	};

	// Render raw JSON view
	const renderRawView = () => {
		return (
			<div className="p-2">
				<JsonTree data={data} defaultExpandedDepth={999} />
			</div>
		);
	};

	// Get icon for content type
	const getContentIcon = () => {
		switch (contentType) {
			case "markdown":
				return <MessageSquare className="w-4 h-4" />;
			case "sql":
				return <Database className="w-4 h-4" />;
			case "code":
				return <Code className="w-4 h-4" />;
			case "table":
				return <Table className="w-4 h-4" />;
			case "json":
				return <FileJson className="w-4 h-4" />;
			default:
				return <Terminal className="w-4 h-4" />;
		}
	};

	// For inline usage (in messages), render without wrapper
	if (className?.includes("border-0")) {
		return (
			<div className="overflow-auto custom-scrollbar" style={{ maxHeight }}>
				{renderSmartView()}
			</div>
		);
	}

	return (
		<div className={`${className}`}>
			{/* Header - only show if we have a title or if it's not inline */}
			{title && (
				<div className="flex items-center justify-between px-4 py-3 border-b border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/30">
					<div className="flex items-center gap-2.5">
						<div className="w-6 h-6 rounded-lg border border-[rgba(var(--color-primary-rgb),0.3)] bg-[rgba(var(--color-primary-rgb),0.08)] flex items-center justify-center">
							{getContentIcon()}
						</div>
						<span className="text-xs capitalize font-semibold text-[color:var(--color-text-secondary)]">
							{title}
						</span>
					</div>
					<div className="flex items-center gap-1.5">
						{/* View mode toggle */}
						<button
							onClick={() =>
								setViewMode(viewMode === "smart" ? "raw" : "smart")
							}
							className="p-1.5 text-xs hover:bg-[color:var(--color-surface-hover)]/60 rounded-lg transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
							title={viewMode === "smart" ? "Show raw JSON" : "Show smart view"}
						>
							{viewMode === "smart" ? (
								<EyeOff className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
							) : (
								<Eye className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
							)}
						</button>

						{/* Copy button */}
						<button
							onClick={copyToClipboard}
							className="p-1.5 text-xs hover:bg-[color:var(--color-surface-hover)]/60 rounded-lg transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
						>
							{copied ? (
								<Check className="w-3.5 h-3.5 text-[color:var(--color-success)]" />
							) : (
								<Copy className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
							)}
						</button>
					</div>
				</div>
			)}

			{/* Content */}
			<div className="overflow-auto custom-scrollbar p-4" style={{ maxHeight }}>
				{viewMode === "smart" ? renderSmartView() : renderRawView()}
			</div>
		</div>
	);
}
