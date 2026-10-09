"use client";

import {
	ChevronDown,
	Code,
	Hash,
	List,
	ToggleLeft,
	Type,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Node } from "reactflow";
import { useOutputSchemas } from "@/contexts/OutputSchemaContext";
import { buildVariableList } from "./template-builder/templateBuilderTypes";

interface CustomTemplateConfigProps {
	template: string | null;
	availableNodes: Node[];
	onTemplateChange: (value: string) => void;
}

interface Suggestion {
	label: string;
	insertValue: string;
	description: string;
	type: "builtin" | "node" | "field";
	fieldType?: string;
}

export default function CustomTemplateConfig({
	template,
	availableNodes,
	onTemplateChange,
}: CustomTemplateConfigProps) {
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	const [showSuggestions, setShowSuggestions] = useState(false);
	const [filterText, setFilterText] = useState("");
	const [braceStartPos, setBraceStartPos] = useState(-1);
	const [dropdownPosition, setDropdownPosition] = useState({
		top: 0,
		left: 0,
	});
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
	const dropdownRef = useRef<HTMLDivElement>(null);

	const { schemas: schemaRegistry } = useOutputSchemas();

	// Build flat list of all suggestions from shared utility
	const allSuggestions = useMemo((): Suggestion[] => {
		const variables = buildVariableList(availableNodes, schemaRegistry);
		return variables.map((v) => ({
			label: v.key,
			insertValue: `{${v.key}}`,
			description: v.description,
			type: v.category === "builtin" ? "builtin" : v.category === "node" ? "node" : "field",
			fieldType: v.fieldType,
		}));
	}, [availableNodes, schemaRegistry]);

	// Filter suggestions
	const filteredSuggestions = useMemo(() => {
		if (!filterText) return allSuggestions;
		const lower = filterText.toLowerCase();
		return allSuggestions.filter(
			(s) =>
				s.label.toLowerCase().includes(lower) ||
				s.description.toLowerCase().includes(lower),
		);
	}, [allSuggestions, filterText]);

	// Reset selected index when filter changes
	useEffect(() => {
		setSelectedIndex(0);
	}, [filterText]);

	const insertVariable = useCallback(
		(variable: string) => {
			const textarea = textareaRef.current;
			if (!textarea) return;

			const start = textarea.selectionStart;
			const end = textarea.selectionEnd;
			const current = template ?? "";
			const newValue =
				current.substring(0, start) + variable + current.substring(end);
			onTemplateChange(newValue);

			requestAnimationFrame(() => {
				textarea.focus();
				const newPos = start + variable.length;
				textarea.setSelectionRange(newPos, newPos);
			});
		},
		[template, onTemplateChange],
	);

	const insertSuggestion = useCallback(
		(suggestion: Suggestion) => {
			const textarea = textareaRef.current;
			if (!textarea) return;

			const current = template ?? "";
			// Replace from the { position to current cursor
			const before = current.substring(0, braceStartPos);
			const after = current.substring(textarea.selectionStart);
			const newValue = before + suggestion.insertValue + after;
			onTemplateChange(newValue);

			setShowSuggestions(false);
			setFilterText("");
			setBraceStartPos(-1);

			requestAnimationFrame(() => {
				textarea.focus();
				const newPos = braceStartPos + suggestion.insertValue.length;
				textarea.setSelectionRange(newPos, newPos);
			});
		},
		[template, onTemplateChange, braceStartPos],
	);

	const updateDropdownPosition = useCallback(() => {
		const textarea = textareaRef.current;
		if (!textarea) return;
		const rect = textarea.getBoundingClientRect();
		setDropdownPosition({
			top: rect.bottom + 4,
			left: rect.left,
		});
	}, []);

	// Detect { typing to show autocomplete
	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			const newValue = e.target.value;
			const cursorPos = e.target.selectionStart;
			onTemplateChange(newValue);

			// Check if we're inside an unclosed brace
			const textBeforeCursor = newValue.slice(0, cursorPos);
			const lastOpenBrace = textBeforeCursor.lastIndexOf("{");
			const lastCloseBrace = textBeforeCursor.lastIndexOf("}");

			if (lastOpenBrace > lastCloseBrace && lastOpenBrace >= 0) {
				const filter = textBeforeCursor.slice(lastOpenBrace + 1);
				setFilterText(filter);
				setBraceStartPos(lastOpenBrace);
				setShowSuggestions(true);
				updateDropdownPosition();
			} else {
				setShowSuggestions(false);
				setFilterText("");
				setBraceStartPos(-1);
			}
		},
		[onTemplateChange, updateDropdownPosition],
	);

	// Keyboard navigation in dropdown
	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
			if (!showSuggestions || filteredSuggestions.length === 0) return;

			if (e.key === "ArrowDown") {
				e.preventDefault();
				setSelectedIndex((prev) =>
					Math.min(prev + 1, filteredSuggestions.length - 1),
				);
			} else if (e.key === "ArrowUp") {
				e.preventDefault();
				setSelectedIndex((prev) => Math.max(prev - 1, 0));
			} else if (e.key === "Enter" || e.key === "Tab") {
				e.preventDefault();
				insertSuggestion(filteredSuggestions[selectedIndex]);
			} else if (e.key === "Escape") {
				setShowSuggestions(false);
			}
		},
		[showSuggestions, filteredSuggestions, selectedIndex, insertSuggestion],
	);

	// Close dropdown on outside click
	useEffect(() => {
		if (!showSuggestions) return;
		const handleClick = (e: MouseEvent) => {
			const target = e.target as globalThis.Node;
			if (
				dropdownRef.current &&
				!dropdownRef.current.contains(target) &&
				target !== textareaRef.current
			) {
				setShowSuggestions(false);
			}
		};
		document.addEventListener("mousedown", handleClick);
		return () => document.removeEventListener("mousedown", handleClick);
	}, [showSuggestions]);

	// Build variable pills grouped by node
	const variablePillGroups = useMemo(() => {
		const builtins = [
			{ label: "{original}", value: "{original}" },
			{ label: "{previous}", value: "{previous}" },
		];

		const nodeGroups = availableNodes.map((n) => {
			const nodeId = n.id;
			const nodeName = n.data.name || nodeId;
			const nodeType = (
				n.data.node_type ||
				n.data.type ||
				""
			).toUpperCase();
			const schema = schemaRegistry?.[nodeType];

			const pills: Array<{ label: string; value: string }> = [
				{ label: nodeName, value: `{${nodeId}}` },
			];

			if (schema && expandedNodes.has(nodeId)) {
				const agentStructuredFields =
					n.data.agent_config?.structured_outputs?.[0]?.fields;
				const fields =
					schema.supports_dynamic_schema && agentStructuredFields
						? agentStructuredFields
						: schema.fields;

				for (const f of fields) {
					const name = f.name;
					pills.push({
						label: `.${name}`,
						value: `{${nodeId}.${name}}`,
					});
				}
			}

			return { nodeId, nodeName, pills, hasFields: Boolean(schema?.fields.length) };
		});

		return { builtins, nodeGroups };
	}, [availableNodes, schemaRegistry, expandedNodes]);

	return (
		<div className="space-y-3" onClick={(e) => e.stopPropagation()}>
			<label className="block text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
				Input template
			</label>
			<div className="rounded-lg border border-[color:var(--color-border)]/50 bg-black/30 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
				<textarea
					ref={textareaRef}
					placeholder='Type { to see available variables, e.g. {original}, {node_id.field_name}...'
					value={template ?? ""}
					onChange={handleChange}
					onKeyDown={handleKeyDown}
					className="h-28 w-full resize-y rounded-lg bg-transparent px-3 py-2 font-mono text-sm text-slate-700/85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
				/>
			</div>

			{/* Autocomplete dropdown */}
			{showSuggestions &&
				filteredSuggestions.length > 0 &&
				createPortal(
					<div
						ref={dropdownRef}
						className="fixed rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] shadow-xl overflow-hidden"
						style={{
							top: `${dropdownPosition.top}px`,
							left: `${dropdownPosition.left}px`,
							width: "360px",
							maxHeight: "280px",
							zIndex: 99999,
						}}
						data-template-autocomplete
					>
						<div className="px-3 py-2 border-b border-[color:var(--color-border)] text-xs text-[color:var(--color-text-muted)]">
							{filteredSuggestions.length} variable
							{filteredSuggestions.length !== 1 ? "s" : ""} available
							<span className="float-right text-[10px]">
								↑↓ navigate · Enter select · Esc close
							</span>
						</div>
						<div
							className="overflow-y-auto py-1"
							style={{ maxHeight: "240px" }}
						>
							{filteredSuggestions.slice(0, 30).map((suggestion, idx) => (
								<div
									key={suggestion.insertValue}
									className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
										idx === selectedIndex
											? "bg-[color:var(--color-surface)]"
											: "hover:bg-[color:var(--color-surface)]/50"
									}`}
									onClick={() => insertSuggestion(suggestion)}
									onMouseEnter={() => setSelectedIndex(idx)}
								>
									{suggestion.fieldType && getFieldIcon(suggestion.fieldType)}
									{!suggestion.fieldType && suggestion.type === "builtin" && (
										<Code className="w-3.5 h-3.5 text-[color:var(--color-accent)] flex-shrink-0" />
									)}
									{!suggestion.fieldType && suggestion.type === "node" && (
										<Code className="w-3.5 h-3.5 text-[color:var(--color-text-muted)] flex-shrink-0" />
									)}
									<code className="font-mono text-xs text-emerald-400 flex-shrink-0">
										{suggestion.insertValue}
									</code>
									<span className="text-[11px] text-[color:var(--color-text-muted)] truncate flex-1">
										{suggestion.description}
									</span>
									{suggestion.fieldType && (
										<span className="text-[10px] px-1 py-0.5 rounded border bg-[color:var(--color-surface)] border-[color:var(--color-border)] text-[color:var(--color-text-muted)]">
											{suggestion.fieldType}
										</span>
									)}
								</div>
							))}
						</div>
					</div>,
					document.body,
				)}

			{/* Variable pills */}
			<div className="space-y-2">
				{/* Builtins */}
				<div className="flex flex-wrap items-center gap-1.5">
					<span className="text-[11px] text-[color:var(--color-text-muted)]">
						Insert:
					</span>
					{variablePillGroups.builtins.map((pill) => (
						<button
							key={pill.value}
							type="button"
							onClick={() => insertVariable(pill.value)}
							className="rounded-full border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/50 px-2 py-0.5 font-mono text-[10px] text-[color:var(--color-text-muted)] transition-colors hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-[color:var(--color-primary-light)]"
						>
							{pill.label}
						</button>
					))}
				</div>

				{/* Node groups with expandable fields */}
				{variablePillGroups.nodeGroups.map((group) => (
					<div key={group.nodeId} className="flex flex-wrap items-center gap-1.5">
						<button
							type="button"
							onClick={() => insertVariable(group.pills[0].value)}
							className="rounded-full border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/50 px-2 py-0.5 font-mono text-[10px] text-[color:var(--color-text-muted)] transition-colors hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-[color:var(--color-primary-light)]"
						>
							{group.pills[0].label}
						</button>
						{group.hasFields && (
							<button
								type="button"
								onClick={() => {
									const next = new Set(expandedNodes);
									if (next.has(group.nodeId)) {
										next.delete(group.nodeId);
									} else {
										next.add(group.nodeId);
									}
									setExpandedNodes(next);
								}}
								className="inline-flex items-center gap-0.5 rounded-full border border-[color:var(--color-border)]/30 px-1.5 py-0.5 text-[10px] text-[color:var(--color-text-muted)] transition-colors hover:text-[color:var(--color-primary-light)]"
								title="Show available fields"
							>
								<ChevronDown
									className={`w-3 h-3 transition-transform ${expandedNodes.has(group.nodeId) ? "rotate-180" : ""}`}
								/>
								fields
							</button>
						)}
						{/* Expanded field pills */}
						{group.pills.slice(1).map((pill) => (
							<button
								key={pill.value}
								type="button"
								onClick={() => insertVariable(pill.value)}
								className="rounded-full border border-emerald-500/30 bg-emerald-900/20 px-2 py-0.5 font-mono text-[10px] text-emerald-400 transition-colors hover:border-emerald-500/50 hover:bg-emerald-900/30"
							>
								{pill.label}
							</button>
						))}
					</div>
				))}
			</div>
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
