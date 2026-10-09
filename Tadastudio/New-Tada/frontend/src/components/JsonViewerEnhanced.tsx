import { Code, Eye, Table } from "lucide-react";
import React, { memo, useMemo, useState } from "react";
import {
	guessMimeType,
	hasMarkdownWithBase64,
	processContentForRendering,
	shouldRenderAsMarkdown,
} from "@/lib/markdown-utils";
import JsonTree from "./json-viewer/JsonTree";
import JsonTreeTableView from "./json-viewer/JsonTreeTableView";
import TextModal from "./ui/TextModal";
import SimpleMarkdown from "./utils/SimpleMarkdown";

interface JsonViewerEnhancedProps {
	data: unknown;
	className?: string;
	maxHeight?: string;
}

const JsonViewerEnhanced = memo(function JsonViewerEnhanced({
	data,
	className = "",
	maxHeight = "500px",
}: JsonViewerEnhancedProps) {
	const [view, setView] = useState<"tree" | "table" | "raw">("tree");
	const [modalContent, setModalContent] = useState<{
		isOpen: boolean;
		content: string;
		title?: string;
	}>({
		isOpen: false,
		content: "",
		title: undefined,
	});

	// Process the data to ensure it's properly parsed
	const processedData = useMemo(() => {
		// Handle the case where data is an object with a 'response' field containing JSON string
		if (data && typeof data === "object" && "response" in data) {
			const response = (data as any).response;
			if (typeof response === "string") {
				const trimmed = response.trim();
				if (
					(trimmed.startsWith("{") && trimmed.endsWith("}")) ||
					(trimmed.startsWith("[") && trimmed.endsWith("]"))
				) {
					try {
						return { response: JSON.parse(trimmed) };
					} catch (e) {
						// Not valid JSON, check if it's double-escaped JSON
						try {
							// Try to unescape and parse
							const unescaped = trimmed
								.replace(/\\n/g, "\n")
								.replace(/\\"/g, '"')
								.replace(/\\\\/g, "\\");
							return { response: JSON.parse(unescaped) };
						} catch (e2) {
							// Still not valid, return as is
							return data;
						}
					}
				}
			}
		}

		// If data is a string, try to parse it as JSON
		if (typeof data === "string") {
			const trimmed = data.trim();
			if (
				(trimmed.startsWith("{") && trimmed.endsWith("}")) ||
				(trimmed.startsWith("[") && trimmed.endsWith("]"))
			) {
				try {
					return JSON.parse(trimmed);
				} catch (e) {
					// Not valid JSON, return as is
					return data;
				}
			}
		}
		return data;
	}, [data]);

	// Check if data can be displayed as a table
	const canShowTable = useMemo(() => {
		if (!Array.isArray(processedData)) return false;
		if (processedData.length === 0) return false;

		// Check if it's an array of objects with consistent structure
		const firstItem = processedData[0];
		if (
			typeof firstItem !== "object" ||
			firstItem === null ||
			Array.isArray(firstItem)
		)
			return false;

		// Check if at least 80% of items are objects with similar keys
		const firstKeys = Object.keys(firstItem).sort().join(",");
		let similarCount = 0;

		for (let i = 0; i < Math.min(10, processedData.length); i++) {
			const item = processedData[i];
			if (typeof item === "object" && item !== null && !Array.isArray(item)) {
				const keys = Object.keys(item).sort().join(",");
				if (keys === firstKeys) similarCount++;
			}
		}

		return similarCount >= Math.min(8, processedData.length * 0.8);
	}, [processedData]);

	const openModal = (content: string, title?: string) => {
		setModalContent({ isOpen: true, content, title });
	};

	const closeModal = () => {
		setModalContent({ isOpen: false, content: "", title: undefined });
	};

	// Handle primitive values
	if (processedData === null || processedData === undefined) {
		// Only show "null" explicitly; undefined returns empty (placeholder handled elsewhere)
		if (processedData === null) {
			return (
				<div
					className={`font-mono text-sm text-[color:var(--color-text-muted)] italic ${className}`}
				>
					null
				</div>
			);
		}
		return null;
	}

	if (typeof processedData === "boolean" || typeof processedData === "number") {
		return (
			<div className={`font-mono text-sm ${className}`}>
				<span
					className={
						typeof processedData === "boolean"
							? "text-[#B00020]"
							: "text-[color:var(--color-accent)]"
					}
				>
					{String(processedData)}
				</span>
			</div>
		);
	}

	if (typeof processedData === "string") {
		// More permissive: Check if this string should be rendered as markdown
		// Also check for markdown image syntax with base64 even if shouldRenderAsMarkdown fails
		if (
			shouldRenderAsMarkdown(processedData) ||
			/!\[[^\]]*\]\(\s*data:image\//.test(processedData) ||
			processedData.includes("data:image/")
		) {
			const processedContent = processContentForRendering(processedData);

			if (processedContent) {
				return (
					<div className={`${className}`}>
						<SimpleMarkdown content={processedContent} />
					</div>
				);
			}
		}

		// Check if it's a raw base64 image (without data: prefix)
		// Support PNG, JPEG, GIF, WebP
		const isRawBase64 =
			!processedData.startsWith("data:image/") &&
			/^[A-Za-z0-9+/=\s]{100,}$/.test(processedData) &&
			(processedData.startsWith("iVBORw0") || // PNG
				processedData.startsWith("/9j/") || // JPEG
				processedData.startsWith("R0lGOD") || // GIF
				processedData.startsWith("UklGR")); // WebP

		if (isRawBase64) {
			// Guess MIME type and add data URI prefix
			const cleanBase64 =
				processContentForRendering(processedData) || processedData;
			const mimeType = guessMimeType(cleanBase64);
			const imageSrc = `data:${mimeType};base64,${cleanBase64}`;


			return (
				<div className={`${className}`}>
					<div className="my-2">
						<p className="text-xs text-[color:var(--color-text-muted)] mb-2">
							Base64 Image ({mimeType}):
						</p>
						<img
							src={imageSrc}
							alt="Base64 encoded image"
							loading="lazy"
							decoding="async"
							className="max-w-full h-auto rounded-lg border border-[color:var(--color-border)] shadow-lg cursor-pointer hover:border-[color:var(--color-surface-hover)] transition-all"
							style={{ maxHeight: "400px", objectFit: "contain" }}
							onClick={() => {
								if (typeof window !== "undefined") {
									window.open(imageSrc, "_blank");
								}
							}}
							title="Click to view full size"
						/>
					</div>
				</div>
			);
		}

		const shouldTruncate = processedData.length > 200;
		const displayValue = shouldTruncate
			? `${processedData.substring(0, 200)}...`
			: processedData;

		return (
			<div className={`${className}`}>
				<div className="flex items-start gap-2">
					<span className="font-mono text-sm text-[color:var(--color-accent)] break-all">
						&quot;{displayValue}&quot;
					</span>
					{shouldTruncate && (
						<button
							onClick={() => openModal(processedData, "String Value")}
							className="text-[color:var(--color-text-muted)] hover:text-[color:var(--color-accent)] transition-all p-1 hover:scale-110 hover:bg-[color:var(--color-accent)]/10 rounded"
							title="View full content"
						>
							<Eye className="w-3 h-3" />
						</button>
					)}
				</div>
				<TextModal
					isOpen={modalContent.isOpen}
					onClose={closeModal}
					content={modalContent.content}
					title={modalContent.title}
				/>
			</div>
		);
	}

	// For objects and arrays, show view switcher
	return (
		<div className={className}>
			{/* View Switcher */}
			<div className="flex items-center gap-2 mb-3 p-1.5 rounded-2xl border border-slate-200 bg-white shadow-sm">
				<button
					onClick={() => setView("tree")}
					className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 ${
						view === "tree"
							? "border border-orange-400 bg-orange-50 text-orange-700 shadow-sm"
							: "border border-[color:var(--color-border)]/40 text-[color:var(--color-text-muted)] hover:border-[rgba(var(--color-primary-rgb),0.35)] hover:text-slate-900"
					}`}
				>
					<Code className="w-3.5 h-3.5" />
					Tree
				</button>

				{canShowTable && (
					<button
						onClick={() => setView("table")}
						className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 ${
							view === "table"
								? "border border-orange-400 bg-orange-50 text-orange-700 shadow-sm"
								: "border border-[color:var(--color-border)]/40 text-[color:var(--color-text-muted)] hover:border-[rgba(var(--color-primary-rgb),0.35)] hover:text-slate-900"
						}`}
					>
						<Table className="w-3.5 h-3.5" />
						Table
					</button>
				)}

				<button
					onClick={() => setView("raw")}
					className={`flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 ${
						view === "raw"
							? "border border-orange-400 bg-orange-50 text-orange-700 shadow-sm"
							: "border border-[color:var(--color-border)]/40 text-[color:var(--color-text-muted)] hover:border-[rgba(var(--color-primary-rgb),0.35)] hover:text-slate-900"
					}`}
				>
					<Eye className="w-3.5 h-3.5" />
					Raw
				</button>

				<div className="ml-auto">
					<span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/50 px-3 py-1.5 text-xs font-medium text-[color:var(--color-text-secondary)]">
						{Array.isArray(processedData) ? (
							<>
								<span className="text-[color:var(--color-accent)]">Array</span>
								<span className="text-[color:var(--color-text-muted)]">·</span>
								<span>
									{processedData.length}{" "}
									{processedData.length === 1 ? "item" : "items"}
								</span>
							</>
						) : (
							<>
								<span className="text-[color:var(--color-accent)]">Object</span>
								<span className="text-[color:var(--color-text-muted)]">·</span>
								<span>
									{Object.keys(processedData as object).length}{" "}
									{Object.keys(processedData as object).length === 1
										? "property"
										: "properties"}
								</span>
							</>
						)}
					</span>
				</div>
			</div>

			{/* Content */}
			<div style={{ maxHeight }} className="overflow-auto">
				{view === "tree" && (
					<JsonTree data={processedData as any} defaultExpandedDepth={2} />
				)}

				{view === "table" && canShowTable && (
					<JsonTreeTableView data={processedData as any[]} />
				)}

				{view === "raw" && (
					<div className="bg-[color:var(--color-bg-secondary)]/50 rounded-lg border border-[color:var(--color-surface)] p-4">
						<pre className="text-xs text-[color:var(--color-text-secondary)] font-mono whitespace-pre-wrap break-all">
							{JSON.stringify(processedData, null, 2)}
						</pre>
					</div>
				)}
			</div>

			<TextModal
				isOpen={modalContent.isOpen}
				onClose={closeModal}
				content={modalContent.content}
				title={modalContent.title}
			/>
		</div>
	);
});

export default JsonViewerEnhanced;
