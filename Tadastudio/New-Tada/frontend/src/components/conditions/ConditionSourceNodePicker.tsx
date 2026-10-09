"use client";

import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import { Code, FileText, GitBranch, Sparkles } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import type { Node } from "reactflow";

interface SimpleCondition {
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
	operator?: string;
	value?: any;
	value_type?: string;
	dynamic_source?: any;
	custom_template?: string;
}

interface ConditionSourceNodePickerProps {
	condition: SimpleCondition;
	availableNodes: Node[];
	onChange: (condition: SimpleCondition) => void;
}

const getNodeIcon = (nodeType: string) => {
	const baseClass =
		"flex h-7 w-7 items-center justify-center rounded-lg border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)]/80 text-[color:var(--color-text-secondary)]";
	const iconClass = "h-3.5 w-3.5";

	switch (nodeType) {
		case "START":
			return (
				<div
					className={clsx(
						baseClass,
						"border-emerald-400/30 bg-emerald-500/10 text-emerald-600",
					)}
				>
					<FileText className={iconClass} />
				</div>
			);
		case "AGENT":
			return (
				<div
					className={clsx(
						baseClass,
						"border-[color:var(--color-accent)]/40 bg-[color:var(--color-accent)]/12 text-[color:var(--color-accent)]",
					)}
				>
					<GitBranch className={iconClass} />
				</div>
			);
		default:
			return (
				<div
					className={clsx(
						baseClass,
						"border-[rgba(var(--color-primary-rgb),0.4)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary-light)]",
					)}
				>
					<Code className={iconClass} />
				</div>
			);
	}
};

const ConditionSourceNodePicker: React.FC<ConditionSourceNodePickerProps> = ({
	condition,
	availableNodes,
	onChange,
}) => {
	const handleNodeSelect = useCallback(
		(nodeId: string) => {
			onChange({
				...condition,
				source_node_id: nodeId,
				field_path: undefined, // Clear field path when selecting a new node
			});
		},
		[condition, onChange],
	);

	const handleClearSelection = useCallback(() => {
		onChange({
			...condition,
			source_node_id: undefined,
			field_path: undefined,
		});
	}, [condition, onChange]);

	const selectedNode = condition.source_node_id
		? availableNodes.find((n) => n.id === condition.source_node_id)
		: undefined;

	return (
		<section className="rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 p-4 backdrop-blur-sm">
			<h3 className="text-base font-semibold text-slate-900 mb-4">Source Nodes</h3>

			<div className="space-y-3">
				<div className="space-y-2">
					<p className="text-xs capitalize tracking-wide text-[color:var(--color-text-muted)]">
						Active source
					</p>
					{selectedNode ? (
						<div className="flex items-center justify-between rounded-lg border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/45 px-3 py-2 text-sm text-slate-900">
							<div className="flex items-center gap-3">
								{getNodeIcon(selectedNode.data.type ?? "AGENT")}
								<div>
									<span className="block font-medium">
										{selectedNode.data?.name}
									</span>
									<span className="text-xs text-[color:var(--color-text-muted)]">
										Currently chosen. Switch nodes below or clear the selection.
									</span>
								</div>
							</div>
							<button
								type="button"
								onClick={handleClearSelection}
								className="rounded-full border border-[color:var(--color-border)]/60 px-3 py-1 text-xs text-[color:var(--color-text-muted)] transition-colors hover:border-[color:var(--color-accent)]/60 hover:text-[color:var(--color-accent)]"
							>
								Clear
							</button>
						</div>
					) : (
						<div className="rounded-lg border border-dashed border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/30 px-3 py-2 text-sm text-[color:var(--color-text-muted)]">
							No node selected yet. Choose a source below.
						</div>
					)}

					<div className="grid gap-1.5 sm:grid-cols-2">
						{availableNodes.map((n) => {
							const isActive = condition.source_node_id === n.id;
							const isStructured = Boolean(
								n.data.agent_config?.structured_outputs?.length,
							);
							const isSubagent = Boolean(n.data._isSubagent);
							return (
								<button
									key={n.id}
									type="button"
									onClick={() => handleNodeSelect(n.id)}
									className={clsx(
										"group flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left transition-all duration-200",
										isActive
											? "border-[color:var(--color-accent)]/60 bg-[color:var(--color-accent)]/12 shadow-[0_6px_16px_rgba(58,120,255,0.18)]"
											: "border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/45 hover:border-[color:var(--color-accent)]/40",
									)}
								>
									<div className="flex items-center gap-2.5">
										{getNodeIcon(n.data.type)}
										<div>
											<div className="flex flex-wrap items-center gap-1.5 text-sm font-medium text-slate-900">
												{n.data.name}
												{isSubagent && (
													<span className="rounded-full bg-purple-500/15 px-1.5 py-0.5 text-[9px] font-medium capitalize tracking-wide text-purple-600/90">
														Subagent
													</span>
												)}
												{isStructured && (
													<span className="inline-flex items-center gap-0.5 rounded-full bg-[color:var(--color-accent)]/15 px-1.5 py-0.5 text-[9px] font-medium capitalize tracking-wide text-[color:var(--color-accent)]/90">
														<Sparkles className="h-2.5 w-2.5" />
														Structured
													</span>
												)}
											</div>
											<p className="text-xs text-[color:var(--color-text-muted)]/80">
												ID: {n.id}
											</p>
										</div>
									</div>
									<span
										className={clsx(
											"inline-flex h-5 min-w-[2.5rem] items-center justify-center rounded-full border px-2.5 text-[10px] font-medium capitalize tracking-wide transition-colors",
											isActive
												? "border-[color:var(--color-accent)] bg-[color:var(--color-accent)] text-slate-950"
												: "border-[color:var(--color-border)] text-[color:var(--color-text-muted)]/75",
										)}
									>
										{isActive ? "Active" : "Use"}
									</span>
								</button>
							);
						})}
					</div>

					{condition.source_node_id && (
						<div className="rounded-lg border border-dashed border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/45 px-3 py-2 text-xs text-[color:var(--color-text-muted)]/90">
							This condition will use the output from the selected node. If the
							source returns structured data you can choose specific fields
							below.
						</div>
					)}
				</div>
			</div>
		</section>
	);
};

export default ConditionSourceNodePicker;
