"use client";

import clsx from "clsx";
import {
	ChevronDown,
	Code,
	GripVertical,
	Hash,
	List,
	Search,
	ToggleLeft,
	Type,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { getNodeColorRgb, getNodeIcon } from "../inputSourceTypes";
import type { VariableGroup, VariableInfo } from "./templateBuilderTypes";

interface VariableSourcePanelProps {
	groups: VariableGroup[];
	onInsert: (variable: VariableInfo) => void;
}

export default function VariableSourcePanel({
	groups,
	onInsert,
}: VariableSourcePanelProps) {
	const [searchQuery, setSearchQuery] = useState("");
	const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
		new Set(),
	);

	const filteredGroups = useMemo(() => {
		if (!searchQuery.trim()) return groups;
		const q = searchQuery.toLowerCase();
		return groups
			.map((group) => ({
				...group,
				variables: group.variables.filter(
					(v) =>
						v.displayLabel.toLowerCase().includes(q) ||
						v.description.toLowerCase().includes(q) ||
						v.key.toLowerCase().includes(q),
				),
			}))
			.filter((g) => g.variables.length > 0);
	}, [groups, searchQuery]);

	const toggleGroup = useCallback((groupId: string) => {
		setCollapsedGroups((prev) => {
			const next = new Set(prev);
			if (next.has(groupId)) {
				next.delete(groupId);
			} else {
				next.add(groupId);
			}
			return next;
		});
	}, []);

	const handleDragStart = useCallback(
		(e: React.DragEvent, variable: VariableInfo) => {
			e.dataTransfer.setData(
				"application/x-template-variable",
				JSON.stringify(variable),
			);
			e.dataTransfer.effectAllowed = "copy";
		},
		[],
	);

	return (
		<div className="flex h-full flex-col">
			{/* Search */}
			<div className="border-b border-slate-200 p-3">
				<div className="relative">
					<Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
					<input
						type="text"
						placeholder="Search variables..."
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						className="w-full rounded-[4px] border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-900 placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
					/>
				</div>
			</div>

			{/* Groups */}
			<div className="flex-1 overflow-y-auto p-2">
				{filteredGroups.map((group) => {
					const isCollapsed =
						collapsedGroups.has(group.id) && !searchQuery.trim();
					return (
						<div key={group.id} className="mb-2">
							{/* Group header */}
							<button
								type="button"
								onClick={() => toggleGroup(group.id)}
								className="flex w-full items-center gap-2 rounded-[4px] px-2 py-1.5 text-left transition-colors hover:bg-slate-50"
							>
								{group.nodeType && (
									<div className="flex-shrink-0 scale-75 origin-left">
										{getNodeIcon(group.nodeType)}
									</div>
								)}
								<span className="flex-1 text-[0.6rem] font-semibold capitalize text-slate-700">
									{group.label}
								</span>
								{group.nodeType && (
									<span className="rounded-full border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[9px] text-slate-600">
										{group.nodeType}
									</span>
								)}
								<ChevronDown
									className={clsx(
										"h-3 w-3 text-slate-500 transition-transform",
										isCollapsed && "-rotate-90",
									)}
								/>
							</button>

							{/* Variables */}
							{!isCollapsed && (
								<div className="mt-1 space-y-0.5 pl-1">
									{group.variables.map((variable) => (
										<VariableCard
											key={variable.key}
											variable={variable}
											onInsert={onInsert}
											onDragStart={handleDragStart}
										/>
									))}
								</div>
							)}
						</div>
					);
				})}

				{filteredGroups.length === 0 && (
					<p className="px-3 py-6 text-center text-xs text-slate-500">
						No variables match your search.
					</p>
				)}
			</div>
		</div>
	);
}

function VariableCard({
	variable,
	onInsert,
	onDragStart,
}: {
	variable: VariableInfo;
	onInsert: (v: VariableInfo) => void;
	onDragStart: (e: React.DragEvent, v: VariableInfo) => void;
}) {
	const colorRgb = variable.nodeType
		? getNodeColorRgb(variable.nodeType)
		: "var(--color-primary-rgb)";
	const isField = variable.category === "field";

	return (
		<div
			draggable
			onDragStart={(e) => onDragStart(e, variable)}
			onClick={() => onInsert(variable)}
			onKeyDown={(e) => {
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					onInsert(variable);
				}
			}}
			tabIndex={0}
			role="button"
			aria-label={`Insert variable ${variable.displayLabel}`}
			className={clsx(
				"group flex cursor-pointer items-center gap-2 rounded-[4px] border px-2 py-1.5 transition-all",
				isField
					? "ml-2 border-transparent hover:border-slate-200 hover:bg-slate-50"
					: "border-slate-200 bg-white hover:border-orange-400 hover:bg-slate-50",
			)}
		>
			<GripVertical className="h-3 w-3 flex-shrink-0 text-slate-400 opacity-0 transition-opacity group-hover:opacity-100" />

			{variable.fieldType ? (
				getFieldIcon(variable.fieldType)
			) : (
				<div
					className="flex h-4 w-4 flex-shrink-0 items-center justify-center rounded"
					style={{
						backgroundColor: `rgba(${colorRgb}, 0.15)`,
					}}
				>
					<Code
						className="h-2.5 w-2.5"
						style={{ color: `rgba(${colorRgb}, 0.8)` }}
					/>
				</div>
			)}

			<div className="min-w-0 flex-1">
				<p className="truncate font-mono text-[11px] text-slate-800">
					{isField ? `.${variable.displayLabel.split(".").pop()}` : `{${variable.displayLabel}}`}
				</p>
			</div>

			{variable.fieldType && (
				<span className="flex-shrink-0 rounded border border-slate-200 bg-slate-50 px-1 py-0.5 text-[9px] text-slate-600">
					{variable.fieldType}
				</span>
			)}
		</div>
	);
}

function getFieldIcon(type: string) {
	const baseClass = "h-3.5 w-3.5 flex-shrink-0";
	switch (type) {
		case "string":
			return <Type className={clsx(baseClass, "text-emerald-600")} />;
		case "integer":
		case "float":
			return <Hash className={clsx(baseClass, "text-violet-600")} />;
		case "boolean":
			return <ToggleLeft className={clsx(baseClass, "text-[#0DA931]")} />;
		case "array":
			return <List className={clsx(baseClass, "text-orange-600")} />;
		case "object":
			return (
				<Code className={clsx(baseClass, "text-blue-600")} />
			);
		default:
			return (
				<Code className={clsx(baseClass, "text-slate-500")} />
			);
	}
}
