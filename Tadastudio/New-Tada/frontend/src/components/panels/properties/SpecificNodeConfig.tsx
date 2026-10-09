import clsx from "clsx";
import { Check, Sparkles } from "lucide-react";
import type { Node } from "reactflow";
import { useOutputSchemas } from "@/contexts/OutputSchemaContext";
import MultiSourceChips from "./MultiSourceChips";
import type { InputSourceConfig } from "./inputSourceTypes";
import { getNodeIcon } from "./inputSourceTypes";
import { formatFieldsSummary } from "./outputFormatUtils";

interface SpecificNodeConfigProps {
	config: InputSourceConfig;
	availableNodes: Node[];
	multiSelectMode: boolean;
	onToggleMultiSelect: () => void;
	onSingleSelect: (nodeId: string) => void;
	onClearSelection: () => void;
	onNodeToggle: (nodeId: string, checked: boolean) => void;
	onIncludeNodeLabelsChange: (checked: boolean) => void;
}

/** Get an output summary string for a node, considering dynamic AGENT fields. */
function getNodeOutputSummary(
	node: Node,
	schemas: Record<string, { fields: Array<{ name: string; type: string }> }> | null,
): string | null {
	// AGENT with structured outputs: use dynamic fields
	const structuredFields =
		node.data?.agent_config?.structured_outputs?.[0]?.fields;
	if (structuredFields && structuredFields.length > 0) {
		return formatFieldsSummary(structuredFields);
	}

	// Fall back to static schema
	if (!schemas) return null;
	const nodeType = (node.data?.node_type || node.data?.type || "").toUpperCase();
	const schema = schemas[nodeType];
	if (!schema) return null;
	return formatFieldsSummary(schema.fields);
}

export default function SpecificNodeConfig({
	config,
	availableNodes,
	multiSelectMode,
	onToggleMultiSelect,
	onSingleSelect,
	onClearSelection,
	onNodeToggle,
	onIncludeNodeLabelsChange,
}: SpecificNodeConfigProps) {
	const selectedIds = config.source_node_ids ?? [];
	const { schemas } = useOutputSchemas();

	return (
		<div className="space-y-3" onClick={(e) => e.stopPropagation()}>
			{/* Multi-source toggle */}
			<div className="flex items-center justify-between">
				<span className="text-[0.6rem] font-semibold capitalize text-slate-600">
					Source nodes
				</span>
				<button
					type="button"
					onClick={onToggleMultiSelect}
					className={clsx(
						"inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[10px] font-medium capitalize tracking-wide transition-all duration-200",
						multiSelectMode
							? "border-orange-500 bg-white text-orange-900 shadow-sm"
							: "border-slate-200 bg-white text-slate-600 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900",
					)}
				>
					Multi-source
					<span
						className={clsx(
							"relative inline-flex h-4 w-7 items-center rounded-full transition-colors",
							multiSelectMode ? "bg-orange-500" : "bg-slate-300",
						)}
					>
						<span
							className={clsx(
								"absolute h-2.5 w-2.5 rounded-full bg-white shadow-sm transition-transform",
								multiSelectMode ? "translate-x-3.5" : "translate-x-0.5",
							)}
						/>
					</span>
				</button>
			</div>

			{/* Single-select mode */}
			{!multiSelectMode && (
				<div className="space-y-2">
					{selectedIds.length > 0 && (
						<MultiSourceChips
							selectedNodeIds={selectedIds}
							availableNodes={availableNodes}
							onRemove={() => onClearSelection()}
						/>
					)}
					<div className="space-y-1">
						{availableNodes.map((n) => {
							const isActive = selectedIds[0] === n.id;
							const isStructured = Boolean(
								n.data.agent_config?.structured_outputs?.length,
							);
							const isSubagent = Boolean(n.data._isSubagent);
							const outputSummary = getNodeOutputSummary(n, schemas);
							return (
								<button
									key={n.id}
									type="button"
									onClick={() => onSingleSelect(n.id)}
									className={clsx(
										"group flex w-full items-center justify-between gap-2 rounded-[4px] border px-3 py-2 text-left transition-all duration-200",
										isActive
											? "border-orange-500 bg-white shadow-sm"
											: "border-slate-200 bg-white hover:border-orange-400 hover:bg-slate-50",
									)}
								>
									<div className="flex items-center gap-2.5">
										{getNodeIcon(n.data.type)}
										<div>
											<div className="flex flex-wrap items-center gap-1.5 text-sm font-medium text-slate-900">
												{n.data.name}
												{isSubagent && (
													<span className="rounded-full border border-purple-200 bg-purple-50 px-1.5 py-0.5 text-[9px] font-medium capitalize tracking-wide text-purple-800">
														Subagent
													</span>
												)}
												{isStructured && (
													<span className="inline-flex items-center gap-0.5 rounded-full border border-orange-200 bg-white px-1.5 py-0.5 text-[9px] font-medium capitalize tracking-wide text-orange-800">
														<Sparkles className="h-2.5 w-2.5" />
														Structured
													</span>
												)}
											</div>
											{outputSummary && (
												<p className="mt-0.5 max-w-[240px] truncate text-[11px] text-slate-600">
													{outputSummary}
												</p>
											)}
										</div>
									</div>
									{isActive && (
										<span className="flex h-5 w-5 items-center justify-center rounded-full bg-orange-500 text-white">
											<Check className="h-3 w-3" />
										</span>
									)}
								</button>
							);
						})}
					</div>
				</div>
			)}

			{/* Multi-select mode */}
			{multiSelectMode && (
				<div className="space-y-2">
					<MultiSourceChips
						selectedNodeIds={selectedIds}
						availableNodes={availableNodes}
						onRemove={(nodeId) => onNodeToggle(nodeId, false)}
					/>
					<div className="max-h-48 space-y-1 overflow-y-auto pr-1">
						{availableNodes.map((n) => {
							const isChecked = selectedIds.includes(n.id);
							const isStructured = Boolean(
								n.data.agent_config?.structured_outputs?.length,
							);
							const isSubagent = Boolean(n.data._isSubagent);
							const outputSummary = getNodeOutputSummary(n, schemas);
							return (
								<label
									key={n.id}
									className={clsx(
										"group flex w-full cursor-pointer items-center justify-between gap-2 rounded-[4px] border px-3 py-2 transition-all duration-200",
										isChecked
											? "border-orange-500 bg-white shadow-sm"
											: "border-slate-200 bg-white hover:border-orange-400 hover:bg-slate-50",
									)}
								>
									<input
										type="checkbox"
										checked={isChecked}
										onChange={(e) => onNodeToggle(n.id, e.target.checked)}
										className="sr-only"
									/>
									<div className="flex items-center gap-2.5">
										{getNodeIcon(n.data.type)}
										<div>
											<div className="flex flex-wrap items-center gap-1.5 text-sm font-medium text-slate-900">
												{n.data.name}
												{isSubagent && (
													<span className="rounded-full border border-purple-200 bg-purple-50 px-1.5 py-0.5 text-[9px] font-medium capitalize tracking-wide text-purple-800">
														Subagent
													</span>
												)}
												{isStructured && (
													<span className="inline-flex items-center gap-0.5 rounded-full border border-orange-200 bg-white px-1.5 py-0.5 text-[9px] font-medium capitalize tracking-wide text-orange-800">
														<Sparkles className="h-2.5 w-2.5" />
														Structured
													</span>
												)}
											</div>
											{outputSummary && (
												<p className="mt-0.5 max-w-[240px] truncate text-[11px] text-slate-600">
													{outputSummary}
												</p>
											)}
										</div>
									</div>
									<span
										className={clsx(
											"flex h-5 w-5 items-center justify-center rounded-full border transition-colors",
											isChecked
												? "border-orange-500 bg-orange-500 text-white"
												: "border-slate-300 text-transparent",
										)}
									>
										<Check className="h-3 w-3" />
									</span>
								</label>
							);
						})}
					</div>

					{/* Include node labels toggle */}
					{selectedIds.length > 1 && (
						<label className="flex cursor-pointer items-center justify-between gap-3 rounded-[4px] border border-slate-200 bg-white px-3 py-2 hover:border-orange-400">
							<div>
								<p className="text-xs font-semibold text-slate-900">
									Add node names to output
								</p>
								<p className="text-[11px] text-slate-600">
									Label each section so readers know where it came from.
								</p>
							</div>
							<div className="relative inline-flex items-center">
								<input
									type="checkbox"
									checked={config.include_node_labels !== false}
									onChange={(e) =>
										onIncludeNodeLabelsChange(e.target.checked)
									}
									className="peer sr-only"
								/>
								<div className="h-5 w-9 rounded-full bg-slate-200 transition-colors peer-checked:bg-orange-500" />
								<div className="absolute left-1 top-1 h-3 w-3 rounded-full bg-white transition-transform peer-checked:translate-x-4" />
							</div>
						</label>
					)}
				</div>
			)}

			{/* Info hint */}
			{selectedIds.length > 0 && (
				<p className="text-[11px] text-slate-600">
					{selectedIds.length === 1
						? "This node will receive the entire response. If the source returns structured data you can choose specific fields below."
						: `Merging ${selectedIds.length} selected responses in the order you picked.`}
				</p>
			)}
		</div>
	);
}
