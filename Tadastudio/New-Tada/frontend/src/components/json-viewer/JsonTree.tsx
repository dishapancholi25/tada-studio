"use client";

import {
	Box,
	ChevronDown,
	ChevronRight,
	Hash,
	List,
	Maximize2,
	ToggleLeft,
	Type,
} from "lucide-react";
import React, { useMemo, useState } from "react";
import TextModal from "../ui/TextModal";
import type { FlattenedTree, JsonValue, NodeType, TreeNodeMeta } from "./types";

// Convert JSON path to user-friendly title
function formatPathAsTitle(path: string): string {
	if (!path) return "Content";

	// Remove $ prefix and split by dots and brackets
	const cleanPath = path.replace(/^\$\.?/, "");
	if (!cleanPath) return "Root";

	// Split by dots and brackets, handling array indices
	const parts = cleanPath.split(/[.[\]]+/).filter(Boolean);

	// Format each part
	const formatted = parts.map((part, index) => {
		// Check if it's a number (array index)
		if (/^\d+$/.test(part)) {
			return `Item ${parseInt(part) + 1}`;
		}
		// Capitalize first letter and add spaces before capitals
		return part
			.replace(/([A-Z])/g, " $1")
			.replace(/^./, (str) => str.toUpperCase())
			.trim();
	});

	// Join with ' > ' for hierarchy
	return formatted.join(" > ");
}

function detectType(value: unknown): NodeType {
	if (value === null) return "null";
	if (Array.isArray(value)) return "array";
	switch (typeof value) {
		case "object":
			return "object";
		case "string":
			return "string";
		case "number":
			return "number";
		case "boolean":
			return "boolean";
		default:
			return "string";
	}
}

function makePath(parentPath: string, key: string | number): string {
	if (typeof key === "number") return `${parentPath}[${key}]`;
	if (parentPath === "$") return `$.${key}`;
	return `${parentPath}.${key}`;
}

// Helper function to try parsing a string as JSON
function tryParseJson(value: string): { parsed: boolean; data: any } {
	const trimmed = value.trim();
	if (
		(trimmed.startsWith("{") && trimmed.endsWith("}")) ||
		(trimmed.startsWith("[") && trimmed.endsWith("]"))
	) {
		try {
			const parsed = JSON.parse(trimmed);
			return { parsed: true, data: parsed };
		} catch (e) {
			return { parsed: false, data: value };
		}
	}
	return { parsed: false, data: value };
}

function buildFlattened(value: JsonValue): FlattenedTree {
	const nodes: Record<string, TreeNodeMeta> = {};
	const rootId = "$";

	const walk = (
		val: JsonValue,
		path: string,
		depth: number,
		key?: string | number,
	): string => {
		// Check if it's a string that contains JSON
		if (typeof val === "string") {
			const { parsed, data } = tryParseJson(val);
			if (parsed) {
				// Treat the parsed JSON as the actual value
				val = data;
			}
		}

		const type = detectType(val);
		const id = path;
		const meta: TreeNodeMeta = {
			id,
			path,
			key: typeof key === "number" ? String(key) : key,
			type,
			depth,
			size: 1,
			preview: "",
			children: undefined,
		};

		if (type === "object") {
			const obj = val as any;
			const keys = Object.keys(obj);
			meta.size = keys.length;
			meta.preview = keys.length === 0 ? "{}" : `{ ${keys.length} }`;
			meta.children = [];
			nodes[id] = meta;
			keys.forEach((k) => {
				const childPath = makePath(path, k);
				meta.children!.push(childPath);
				walk(obj[k], childPath, depth + 1, k);
			});
		} else if (type === "array") {
			const arr = val as any[];
			meta.size = arr.length;
			meta.preview = arr.length === 0 ? "[]" : `[ ${arr.length} ]`;
			meta.children = [];
			nodes[id] = meta;
			arr.forEach((item, idx) => {
				const childPath = makePath(path, idx);
				meta.children!.push(childPath);
				walk(item, childPath, depth + 1, idx);
			});
		} else {
			// For primitive values, store the actual value for display
			if (type === "string") {
				const strVal = String(val);
				// Check if this string is actually JSON that couldn't be parsed earlier
				// (this shouldn't happen due to the check above, but just in case)
				meta.preview = strVal;
			} else if (type === "null") {
				meta.preview = "null";
			} else {
				meta.preview = String(val);
			}
			nodes[id] = meta;
		}

		return id;
	};

	walk(value, "$", 0);
	return { nodes, rootId };
}

// Icon component for type badges
const TypeIcon = ({ type }: { type: NodeType }) => {
	switch (type) {
		case "object":
			return <Box className="w-3 h-3" />;
		case "array":
			return <List className="w-3 h-3" />;
		case "string":
			return <Type className="w-3 h-3" />;
		case "number":
			return <Hash className="w-3 h-3" />;
		case "boolean":
			return <ToggleLeft className="w-3 h-3" />;
		default:
			return null;
	}
};

interface JsonTreeProps {
	data: JsonValue;
	defaultExpandedDepth?: number;
	className?: string;
}

export default function JsonTree({
	data,
	defaultExpandedDepth = 2,
	className = "",
}: JsonTreeProps) {
	// Pre-process the data to parse any JSON strings
	const processedData = useMemo(() => {
		const processValue = (val: any): any => {
			if (typeof val === "string") {
				const { parsed, data } = tryParseJson(val);
				if (parsed) return data;
				return val;
			}
			if (Array.isArray(val)) {
				return val.map(processValue);
			}
			if (val && typeof val === "object") {
				const result: any = {};
				for (const [k, v] of Object.entries(val)) {
					result[k] = processValue(v);
				}
				return result;
			}
			return val;
		};

		return processValue(data);
	}, [data]);

	const tree = useMemo(() => buildFlattened(processedData), [processedData]);
	const [expanded, setExpanded] = useState<Set<string>>(() => {
		const s = new Set<string>();
		const expandToDepth = (id: string) => {
			const meta = tree.nodes[id];
			if (!meta) return;
			if (meta.depth < defaultExpandedDepth && meta.children) {
				s.add(id);
				meta.children.forEach(expandToDepth);
			}
		};
		expandToDepth(tree.rootId);
		return s;
	});
	const [modal, setModal] = useState<{
		open: boolean;
		content: string;
		title?: string;
	}>({ open: false, content: "" });

	const toggle = (id: string) => {
		const next = new Set(expanded);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		setExpanded(next);
	};

	const visibleRows = useMemo(() => {
		const rows: TreeNodeMeta[] = [];
		const walkVisible = (id: string) => {
			const meta = tree.nodes[id];
			if (!meta) return;
			rows.push(meta);
			const showChildren = expanded.has(id) || meta.depth === 0;
			if (showChildren && meta.children) {
				meta.children.forEach((cid) => walkVisible(cid));
			}
		};
		walkVisible(tree.rootId);
		return rows.slice(1); // skip the synthetic root
	}, [tree, expanded]);

	const renderValue = (meta: TreeNodeMeta) => {
		const hasChildren = !!meta.children?.length;

		if (!hasChildren) {
			const value = meta.preview;
			const isLongString = meta.type === "string" && value.length > 100;

			// Color coding for different types
			let valueClass = "text-[color:var(--color-text-secondary)]";
			if (meta.type === "string")
				valueClass = "text-[color:var(--color-accent)]";
			else if (meta.type === "number")
				valueClass = "text-[color:var(--color-accent)]";
			else if (meta.type === "boolean") valueClass = "text-[#B00020]";
			else if (meta.type === "null")
				valueClass = "text-[color:var(--color-text-muted)] italic";

			// Format string values with quotes
			let displayValue = value;
			if (meta.type === "string") {
				displayValue = `"${value.length > 100 ? value.substring(0, 100) + "..." : value}"`;
			}

			return (
				<div className="flex items-center gap-2">
					<span className={`${valueClass} break-words`}>{displayValue}</span>
					{isLongString && (
						<button
							className="opacity-0 group-hover:opacity-100 transition-opacity px-2 py-0.5 rounded text-xs bg-[color:var(--color-text-muted)]/20 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-text-muted)]/30"
							onClick={() =>
								setModal({
									open: true,
									content: value,
									title: formatPathAsTitle(meta.path),
								})
							}
						>
							<Maximize2 className="w-3 h-3" />
						</button>
					)}
				</div>
			);
		}

		return (
			<span className="text-[color:var(--color-text-muted)] text-sm">
				{meta.preview}
			</span>
		);
	};

	const renderRow = (meta: TreeNodeMeta) => {
		const hasChildren = !!meta.children?.length;
		const indent = Math.max(0, meta.depth - 1);

		// Improved color scheme
		const typeColors = {
			object:
				"bg-[#F7971C]/20 text-[#F7971C] border-[#F7971C]/30",
			array: "bg-[#B00020]/20 text-[#B00020] border-[#B00020]/30",
			string:
				"bg-[#F7971C]/20 text-[#F7971C] border-[#F7971C]/30",
			number:
				"bg-[#F7971C]/20 text-[#F7971C] border-[#F7971C]/30",
			boolean: "bg-[#B00020]/20 text-[#B00020] border-[#B00020]/30",
			null: "bg-[#F7971C]/20 text-[#F7971C] border-[#F7971C]/30",
		};

		return (
			<div
				key={meta.id}
				className="group flex items-center py-1.5 hover:bg-[color:var(--color-surface)]/30 transition-colors relative"
				style={{ paddingLeft: `${indent * 20 + 2}px` }}
			>
				{/* Indentation guide lines */}
				{indent > 0 && (
					<div
						className="absolute left-0 top-0 bottom-0 border-l border-[color:var(--color-surface)]"
						style={{ left: `${(indent - 1) * 20 + 16}px` }}
					/>
				)}

				{/* Expand/Collapse button */}
				<div className="flex items-center mr-1.5">
					{hasChildren ? (
						<button
							onClick={() => toggle(meta.id)}
							className="p-0.5 rounded hover:bg-[color:var(--color-border)] transition-colors"
						>
							{expanded.has(meta.id) ? (
								<ChevronDown className="w-4 h-4 text-[#F7971C]" />
							) : (
								<ChevronRight className="w-4 h-4 text-[#F7971C]" />
							)}
						</button>
					) : (
						<span className="w-5" />
					)}
				</div>

				{/* Key/Field name */}
				{meta.key && (
					<span className="font-mono font-medium text-[color:var(--color-text-secondary)] mr-3">
						{meta.key}
						<span className="text-[color:var(--color-text-muted)]">:</span>
					</span>
				)}

				{/* Type badge - smaller and more elegant */}
				{hasChildren && (
					<span
						className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs border ${typeColors[meta.type as keyof typeof typeColors]} mr-2`}
					>
						<TypeIcon type={meta.type} />
						<span className="font-medium">{meta.type}</span>
					</span>
				)}

				{/* Value */}
				<div className="flex-1 min-w-0">{renderValue(meta)}</div>
			</div>
		);
	};

	return (
		<div
			className={`bg-[color:var(--color-bg-secondary)]/50 rounded-lg border border-[color:var(--color-surface)] ${className}`}
		>
			<div className="p-2">
				{/* Header with data type info */}
				<div className="flex items-center justify-between mb-2 px-2 py-1 border-b border-[color:var(--color-surface)]">
					<span className="text-xs text-[color:var(--color-text-muted)] font-medium">
						JSON Viewer
					</span>
					<span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/40 px-2.5 py-0.5 text-xs font-medium text-[color:var(--color-text-secondary)]">
						{visibleRows.length} {visibleRows.length === 1 ? "item" : "items"}
					</span>
				</div>

				{/* Tree rows */}
				<div className="overflow-auto max-h-[500px] custom-scrollbar">
					{visibleRows.map(renderRow)}
				</div>
			</div>

			<TextModal
				isOpen={modal.open}
				onClose={() => setModal({ open: false, content: "" })}
				content={modal.content}
				title={modal.title}
			/>
		</div>
	);
}
