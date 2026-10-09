"use client";

import { Download, Scale } from "lucide-react";
import { useCallback, useState } from "react";
import type { Node } from "reactflow";
import Dropdown from "@/components/ui/Dropdown";
import StructuredFieldPicker from "@/components/ui/StructuredFieldPicker";
import TabBar, { type TabBarItem } from "@/components/ui/TabBar";
import ConditionInputModeSelector from "./ConditionInputModeSelector";
import ConditionSourceNodePicker from "./ConditionSourceNodePicker";

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

interface ConditionEditorTabsProps {
	condition: SimpleCondition;
	onConditionChange: (condition: SimpleCondition) => void;
	availableNodes: Node[];
	index: number;
}

const operatorOptions = [
	{ value: "==", label: "Equals" },
	{ value: "!=", label: "Not Equals" },
	{ value: ">", label: "Greater Than" },
	{ value: "<", label: "Less Than" },
	{ value: ">=", label: "Greater or Equal" },
	{ value: "<=", label: "Less or Equal" },
	{ value: "contains", label: "Contains" },
	{ value: "starts_with", label: "Starts With" },
	{ value: "ends_with", label: "Ends With" },
	{ value: "is_empty", label: "Is Empty" },
	{ value: "is_not_empty", label: "Is Not Empty" },
];

export default function ConditionEditorTabs({
	condition,
	onConditionChange,
	availableNodes,
	index,
}: ConditionEditorTabsProps) {
	const [activeTab, setActiveTab] = useState<string>("input");

	const handleModeChange = useCallback(
		(mode: string) => {
			onConditionChange({
				...condition,
				input_source: mode,
				source_node_id: undefined,
				field_path: undefined,
			});
		},
		[condition, onConditionChange],
	);

	const handleFieldPathChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onConditionChange({
				...condition,
				field_path: e.target.value,
			});
		},
		[condition, onConditionChange],
	);

	const handleCustomTemplateChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			onConditionChange({
				...condition,
				custom_template: e.target.value,
			});
		},
		[condition, onConditionChange],
	);

	const handleOperatorChange = useCallback(
		(value: string) => {
			onConditionChange({ ...condition, operator: value });
		},
		[condition, onConditionChange],
	);

	const handleValueTypeChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			onConditionChange({ ...condition, value_type: e.target.value });
		},
		[condition, onConditionChange],
	);

	const handleValueChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onConditionChange({
				...condition,
				value: (e.target as HTMLInputElement).value,
			});
		},
		[condition, onConditionChange],
	);

	const tabs: TabBarItem[] = [
		{
			id: "input",
			label: "Input Source",
			icon: <Download className="w-4 h-4" />,
			description: "Select data source",
			accent: "input",
		},
		{
			id: "comparison",
			label: "Comparison",
			icon: <Scale className="w-4 h-4" />,
			description: "Define logic",
			accent: "core",
		},
	];

	return (
		<div className="space-y-4">
			{/* Tab Navigation */}
			<TabBar
				tabs={tabs}
				activeTab={activeTab}
				onChange={setActiveTab}
				size="sm"
				variant="subtle"
				equalWidth={true}
			/>

			{/* Tab Content */}
			<div className="min-h-[200px]">
				{activeTab === "input" && (
					<div className="space-y-4 animate-in fade-in duration-200">
						<ConditionInputModeSelector
							selectedMode={condition.input_source || "previous"}
							onModeChange={handleModeChange}
						/>

						{condition.input_source === "specific" && (
							<ConditionSourceNodePicker
								condition={condition}
								availableNodes={availableNodes}
								onChange={onConditionChange}
							/>
						)}

						{condition.input_source === "field" && (
							<section className="rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 p-4 backdrop-blur-sm">
								<h3 className="mb-3 text-base font-semibold text-white">
									Field Path
								</h3>
								<input
									type="text"
									value={condition.field_path || ""}
									onChange={handleFieldPathChange}
									placeholder="e.g., result.data"
									className="w-full px-4 py-3 bg-[color:var(--color-surface)]/50 border-2 border-[color:var(--color-border)]/50 rounded-xl text-slate-900 text-sm placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200 hover:border-[color:var(--color-border)]"
								/>
								<p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
									Extract a value from the workflow state using a field path
								</p>
							</section>
						)}

						{condition.input_source === "specific" &&
							condition.source_node_id && (
								<section className="rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 p-4 backdrop-blur-sm">
									<h3 className="mb-3 text-base font-semibold text-white">
										Field Path (Optional)
									</h3>
									<input
										type="text"
										value={condition.field_path || ""}
										onChange={handleFieldPathChange}
										placeholder="e.g., columns.status or result.data"
										className="w-full px-4 py-3 bg-[color:var(--color-surface)]/50 border-2 border-[color:var(--color-border)]/50 rounded-xl text-slate-900 text-sm placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200 hover:border-[color:var(--color-border)]"
									/>
									<p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
										Extract a specific field using dot notation (e.g.,
										columns.field_name for CSV data), or leave empty for
										full output
									</p>
									{(() => {
										const selectedNode = availableNodes.find(
											(n) => n.id === condition.source_node_id,
										);
										const hasStructuredOutput = Boolean(
											selectedNode?.data?.agent_config
												?.structured_outputs?.length,
										);
										if (hasStructuredOutput && selectedNode) {
											return (
												<div className="mt-3">
													<StructuredFieldPicker
														fields={
															selectedNode.data.agent_config
																.structured_outputs[0]?.fields ||
															[]
														}
														value={condition.field_path || ""}
														onChange={(field: string) =>
															onConditionChange({
																...condition,
																field_path: field,
															})
														}
													/>
												</div>
											);
										}
										return null;
									})()}
								</section>
							)}

						{condition.input_source === "custom" && (
							<section className="rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 p-4 backdrop-blur-sm">
								<h3 className="mb-3 text-base font-semibold text-white">
									Custom Template
								</h3>
								<textarea
									value={condition.custom_template || ""}
									onChange={handleCustomTemplateChange}
									placeholder={`Use placeholders to reference data:\n{original} - Workflow input\n{previous} - Previous node output\n{node_id} - Full output from a node\n{node_id.field} - Specific field from a node`}
									rows={4}
									className="w-full px-4 py-3 bg-[color:var(--color-surface)]/50 border-2 border-[color:var(--color-border)]/50 rounded-xl text-slate-900 text-sm font-mono placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200 hover:border-[color:var(--color-border)] resize-y"
								/>
								<p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
									Build a value using placeholders that get replaced with
									actual data at runtime
								</p>
							</section>
						)}
					</div>
				)}

				{activeTab === "comparison" && (
					<div className="space-y-4 animate-in fade-in duration-200">
						{/* Operator Selector */}
						<div>
							<label
								htmlFor={`operator-${index}`}
								className="block text-sm font-semibold text-[color:var(--color-text-secondary)] mb-3"
							>
								Operator
							</label>
							<Dropdown
								value={condition.operator || "=="}
								onChange={handleOperatorChange}
								options={operatorOptions}
								placeholder="Select operator"
							/>
						</div>

						{/* Comparison Value */}
						{!["is_empty", "is_not_empty"].includes(
							condition.operator || "",
						) && (
							<div>
								<label
									htmlFor={`compare-value-type-${index}`}
									className="block text-sm font-semibold text-[color:var(--color-text-secondary)] mb-3"
								>
									Compare Value
								</label>
								<div className="space-y-3">
									<select
										id={`compare-value-type-${index}`}
										value={condition.value_type || "static"}
										onChange={handleValueTypeChange}
										className="w-full px-4 py-3 bg-[color:var(--color-surface)]/50 border-2 border-[color:var(--color-border)]/50 rounded-xl text-slate-900 text-sm font-medium focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200 hover:border-[color:var(--color-border)]"
									>
										<option value="static">Static Value</option>
										<option value="dynamic">From Another Node</option>
									</select>

									{condition.value_type !== "dynamic" ? (
										<input
											id={`compare-value-input-${index}`}
											type="text"
											value={condition.value || ""}
											onChange={handleValueChange}
											placeholder="Enter value to compare..."
											className="w-full px-4 py-3 bg-[color:var(--color-surface)]/50 border-2 border-[color:var(--color-border)]/50 rounded-xl text-slate-900 text-sm placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200 hover:border-[color:var(--color-border)]"
										/>
									) : (
										<div className="p-4 bg-[color:var(--color-surface)] border-2 border-[color:var(--color-border)] rounded-xl">
											<p className="text-sm text-[color:var(--color-text-muted)]">
												Dynamic value comparison coming soon
											</p>
										</div>
									)}
								</div>
							</div>
						)}
					</div>
				)}
			</div>
		</div>
	);
}
