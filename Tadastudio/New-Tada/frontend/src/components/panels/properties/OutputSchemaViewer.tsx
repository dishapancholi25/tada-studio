"use client";

import {
	ChevronRight,
	Code,
	Hash,
	List,
	ToggleLeft,
	Type,
} from "lucide-react";
import { useState } from "react";
import type { OutputField, NodeOutputSchema } from "@/types/io";

interface OutputSchemaViewerProps {
	schema: NodeOutputSchema;
	/** For AGENT nodes with user-defined structured outputs, overrides schema.fields */
	dynamicFields?: OutputField[];
	/** Optional label to show above the schema */
	label?: string;
	/** When true, show checkboxes for field selection */
	selectable?: boolean;
	/** Currently selected field paths */
	selectedFields?: string[];
	/** Called when a field is toggled (in selectable mode) */
	onFieldToggle?: (fieldPath: string) => void;
	/** Called when a field path is clicked (for template insertion) */
	onFieldClick?: (fieldPath: string) => void;
	/** Compact mode - less padding */
	compact?: boolean;
}

export default function OutputSchemaViewer({
	schema,
	dynamicFields,
	label,
	selectable = false,
	selectedFields = [],
	onFieldToggle,
	onFieldClick,
	compact = false,
}: OutputSchemaViewerProps) {
	const fields = dynamicFields ?? schema.fields;

	return (
		<div
			className={`rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] ${compact ? "p-2" : "p-3"}`}
		>
			{label && (
				<div className="flex items-center gap-2 mb-2">
					<span className="text-xs font-medium text-[color:var(--color-text-secondary)]">
						{label}
					</span>
					<span className="text-xs text-[color:var(--color-text-muted)]">
						{schema.node_type}
					</span>
				</div>
			)}

			<div className="text-xs text-[color:var(--color-text-muted)] mb-2">
				{schema.description}
			</div>

			<div className="space-y-0.5">
				{/* Raw output field (hidden when redundant with structured fields, e.g. AGENT) */}
				{!schema.raw_is_redundant && (
					<>
						<FieldRow
							field={{
								name: "raw",
								type: "string",
								description: schema.raw_description,
							}}
							path="raw"
							depth={0}
							selectable={selectable}
							selected={selectedFields.includes("raw")}
							onToggle={onFieldToggle}
							onClick={onFieldClick}
						/>

						{fields.length > 0 && (
							<div className="border-t border-[color:var(--color-border)] my-1.5" />
						)}
					</>
				)}

				{/* Structured fields */}
				{fields.map((field) => (
					<FieldTree
						key={field.name}
						field={field}
						path={field.name}
						depth={0}
						selectable={selectable}
						selectedFields={selectedFields}
						onToggle={onFieldToggle}
						onClick={onFieldClick}
					/>
				))}
			</div>
		</div>
	);
}

function FieldTree({
	field,
	path,
	depth,
	selectable,
	selectedFields,
	onToggle,
	onClick,
}: {
	field: OutputField;
	path: string;
	depth: number;
	selectable: boolean;
	selectedFields: string[];
	onToggle?: (path: string) => void;
	onClick?: (path: string) => void;
}) {
	const [expanded, setExpanded] = useState(depth < 1);
	const hasChildren = field.children && field.children.length > 0;

	return (
		<div>
			<FieldRow
				field={field}
				path={path}
				depth={depth}
				selectable={selectable}
				selected={selectedFields.includes(path)}
				onToggle={onToggle}
				onClick={onClick}
				expandable={hasChildren}
				expanded={expanded}
				onToggleExpand={() => setExpanded(!expanded)}
			/>
			{hasChildren && expanded && (
				<div className="border-l border-[color:var(--color-border)] ml-4">
					{field.children!.map((child) => (
						<FieldTree
							key={child.name}
							field={child}
							path={`${path}.${child.name}`}
							depth={depth + 1}
							selectable={selectable}
							selectedFields={selectedFields}
							onToggle={onToggle}
							onClick={onClick}
						/>
					))}
				</div>
			)}
		</div>
	);
}

function FieldRow({
	field,
	path,
	depth,
	selectable,
	selected,
	onToggle,
	onClick,
	expandable,
	expanded,
	onToggleExpand,
}: {
	field: OutputField;
	path: string;
	depth: number;
	selectable: boolean;
	selected: boolean;
	onToggle?: (path: string) => void;
	onClick?: (path: string) => void;
	expandable?: boolean;
	expanded?: boolean;
	onToggleExpand?: () => void;
}) {
	const handleClick = () => {
		if (selectable && onToggle) {
			onToggle(path);
		} else if (onClick) {
			onClick(path);
		}
	};

	return (
		<div
			className={`flex items-center gap-2 py-1.5 px-2 rounded-md text-sm transition-colors ${
				selectable || onClick
					? "cursor-pointer hover:bg-[color:var(--color-surface)]"
					: ""
			} ${selected ? "bg-emerald-900/30 border border-emerald-500/40" : ""}`}
			style={{ paddingLeft: `${depth * 16 + 8}px` }}
			onClick={handleClick}
		>
			{expandable && (
				<button
					onClick={(e) => {
						e.stopPropagation();
						onToggleExpand?.();
					}}
					className="p-0.5 hover:bg-[color:var(--color-border)] rounded transition-colors"
				>
					<ChevronRight
						className={`w-3 h-3 text-[color:var(--color-text-muted)] transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
					/>
				</button>
			)}

			{selectable && (
				<input
					type="checkbox"
					checked={selected}
					onChange={() => onToggle?.(path)}
					onClick={(e) => e.stopPropagation()}
					className="h-3.5 w-3.5 rounded border-[color:var(--color-border)] accent-emerald-500"
				/>
			)}

			{getFieldIcon(field.type)}

			<code className="font-mono text-xs text-[color:var(--color-text-primary)]">
				{field.name}
			</code>

			<span
				className={`text-[10px] px-1.5 py-0.5 rounded border ${getTypeColor(field.type)}`}
			>
				{field.type}
				{field.nullable && "?"}
				{field.items_type && `<${field.items_type}>`}
			</span>

			<span className="text-[11px] text-[color:var(--color-text-muted)] truncate flex-1">
				{field.description}
			</span>
		</div>
	);
}

function getFieldIcon(type: string) {
	switch (type) {
		case "string":
			return <Type className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />;
		case "integer":
		case "float":
			return <Hash className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />;
		case "boolean":
			return (
				<ToggleLeft className="w-3.5 h-3.5 text-[#0DA931] flex-shrink-0" />
			);
		case "array":
			return <List className="w-3.5 h-3.5 text-orange-400 flex-shrink-0" />;
		case "object":
			return (
				<Code className="w-3.5 h-3.5 text-[color:var(--color-accent)] flex-shrink-0" />
			);
		default:
			return (
				<Code className="w-3.5 h-3.5 text-[color:var(--color-text-muted)] flex-shrink-0" />
			);
	}
}

function getTypeColor(type: string) {
	switch (type) {
		case "string":
			return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
		case "integer":
		case "float":
			return "bg-purple-500/20 text-purple-400 border-purple-500/30";
		case "boolean":
			return "bg-[#0DA931]/20 text-[#0DA931] border-[#0DA931]/30";
		case "array":
			return "bg-orange-500/20 text-orange-400 border-orange-500/30";
		case "object":
			return "bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] border-[color:var(--color-border)]/30";
		default:
			return "bg-gray-500/20 text-gray-400 border-gray-500/30";
	}
}
