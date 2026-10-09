"use client";

import {
	GitBranch,
	Info,
	Layers,
	Palette,
	Plus,
	Sparkles,
	Trash2,
} from "lucide-react";
import { useMemo } from "react";
import type { Node } from "reactflow";
import ConditionInputModeSelector from "@/components/conditions/ConditionInputModeSelector";
import ConditionSourceNodePicker from "@/components/conditions/ConditionSourceNodePicker";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import StructuredFieldPicker from "@/components/ui/StructuredFieldPicker";

interface BranchConfig {
	label: string;
	color: string;
	handle_id: string;
	condition: any;
}

interface ConditionBranchSectionProps {
	branchMode: string;
	onBranchModeChange: (mode: "binary" | "multi") => void;
	branchLabels: string[];
	onBranchLabelsChange: (labels: string[]) => void;
	branches: BranchConfig[];
	onBranchesChange: (branches: BranchConfig[]) => void;
	// Passthrough mode props for binary mode
	inputSource?: string;
	sourceNodeId?: string;
	fieldPath?: string;
	onInputSourceChange?: (source: string) => void;
	onSourceNodeChange?: (nodeId?: string) => void;
	onFieldPathChange?: (path: string) => void;
	availableNodes?: Node[];
}

export default function ConditionBranchSection({
	branchMode,
	onBranchModeChange,
	branchLabels,
	onBranchLabelsChange,
	branches,
	onBranchesChange,
	// Passthrough mode props
	inputSource = "previous",
	sourceNodeId,
	fieldPath = "",
	onInputSourceChange,
	onSourceNodeChange,
	onFieldPathChange,
	availableNodes = [],
}: ConditionBranchSectionProps) {
	// Detect structured outputs from selected node
	const selectedNode = useMemo(
		() => availableNodes.find((n) => n.id === sourceNodeId),
		[availableNodes, sourceNodeId],
	);

	const structuredOutputs =
		selectedNode?.data?.agent_config?.structured_outputs;
	const hasStructuredOutputs = Boolean(
		structuredOutputs && structuredOutputs.length > 0,
	);
	const availableFields = useMemo(() => {
		if (!hasStructuredOutputs) return [];
		return structuredOutputs?.[0]?.fields || [];
	}, [hasStructuredOutputs, structuredOutputs]);

	const handleAddBranch = () => {
		const newBranch: BranchConfig = {
			label: `Branch ${branches.length + 1}`,
			color: "#8b5cf6",
			handle_id: `branch-${branches.length}`,
			condition: {},
		};
		onBranchesChange([...branches, newBranch]);
	};

	const handleBranchLabelChange = (index: number, label: string) => {
		const updatedBranches = [...branches];
		updatedBranches[index] = { ...updatedBranches[index], label };
		onBranchesChange(updatedBranches);
	};

	const handleBranchColorChange = (index: number, color: string) => {
		const updatedBranches = [...branches];
		updatedBranches[index] = { ...updatedBranches[index], color };
		onBranchesChange(updatedBranches);
	};

	const handleRemoveBranch = (index: number) => {
		const updatedBranches = branches.filter((_, i) => i !== index);
		onBranchesChange(updatedBranches);
	};

	const handleBinaryLabelChange = (index: number, value: string) => {
		const labels = [...branchLabels];
		labels[index] = value;
		onBranchLabelsChange(labels);
	};

	return (
		<div className="space-y-6">
			<div className="rounded-2xl border-2 border-[color:var(--color-primary)]/30 bg-[color:var(--color-surface)]/35 p-6 backdrop-blur-sm shadow-[0_20px_45px_rgba(7,9,16,0.55)]">
				{/* Section header with icon */}
				<div className="flex items-start justify-between gap-4 pb-5 border-b border-[color:var(--color-primary)]/20">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)] shadow-[0_0_20px_rgba(var(--color-primary-rgb),0.25)]">
							<GitBranch className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Branch Configuration
							</h3>
							<p className="text-sm text-[color:var(--color-text-muted)]">
								Configure branching mode and paths
							</p>
						</div>
					</div>
				</div>

				{/* Section content */}
				<div className="mt-6 space-y-6">
					{/* Branch Mode Selection */}
					<div>
						<div className="flex items-center gap-2 mb-3">
							<label className="block text-sm font-semibold text-[color:var(--color-text-secondary)]">
								Branch Mode
							</label>
							<InfoTooltip text="Choose between binary (true/false) or multi-branch conditions" />
						</div>

						<div className="grid grid-cols-2 gap-3">
							<button
								onClick={() => onBranchModeChange("binary")}
								className={`px-4 py-4 rounded-xl border-2 transition-all duration-200 font-semibold ${
									branchMode === "binary"
										? "bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.2)] to-[rgba(var(--color-primary-rgb),0.1)] border-[rgba(var(--color-primary-rgb),0.7)] text-white shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.25)] scale-[1.02]"
										: "bg-[color:var(--color-surface)]/40 border-[color:var(--color-border)]/60 text-[color:var(--color-text-muted)] hover:border-[color:var(--color-border-hover)] hover:bg-[color:var(--color-surface)]/60 hover:text-[color:var(--color-text-secondary)]"
								}`}
							>
								<div className="flex flex-col items-center justify-center gap-2">
									<div
										className={`p-2 rounded-lg transition-all duration-200 ${branchMode === "binary" ? "bg-[rgba(var(--color-primary-rgb),0.25)] text-[color:var(--color-primary)]" : "bg-[color:var(--color-surface)] text-[color:var(--color-text-secondary)]"}`}
									>
										<GitBranch className="w-5 h-5" />
									</div>
									<span className="text-sm">Binary (True/False)</span>
								</div>
							</button>
							<button
								onClick={() => onBranchModeChange("multi")}
								className={`px-4 py-4 rounded-xl border-2 transition-all duration-200 font-semibold ${
									branchMode === "multi"
										? "bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.2)] to-[rgba(var(--color-primary-rgb),0.1)] border-[rgba(var(--color-primary-rgb),0.7)] text-white shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.25)] scale-[1.02]"
										: "bg-[color:var(--color-surface)]/40 border-[color:var(--color-border)]/60 text-[color:var(--color-text-muted)] hover:border-[color:var(--color-border-hover)] hover:bg-[color:var(--color-surface)]/60 hover:text-[color:var(--color-text-secondary)]"
								}`}
							>
								<div className="flex flex-col items-center justify-center gap-2">
									<div
										className={`p-2 rounded-lg transition-all duration-200 ${branchMode === "multi" ? "bg-[rgba(var(--color-primary-rgb),0.25)] text-[color:var(--color-primary)]" : "bg-[color:var(--color-surface)] text-[color:var(--color-text-secondary)]"}`}
									>
										<Layers className="w-5 h-5" />
									</div>
									<span className="text-sm">Multi-Branch</span>
								</div>
							</button>
						</div>
					</div>

					{/* Binary Mode - Branch Labels and Input Source */}
					{branchMode === "binary" && (
						<>
							{/* Info Banner for Direct Boolean Evaluation */}
							<div className="p-4 rounded-xl border border-[color:var(--color-primary)]/30 bg-[rgba(var(--color-primary-rgb),0.08)]">
								<div className="flex items-start gap-3">
									<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)] flex-shrink-0">
										<Info className="w-4 h-4" />
									</div>
									<div>
										<h4 className="text-sm font-semibold text-slate-900 mb-1">
											Direct Boolean Evaluation
										</h4>
										<p className="text-sm text-[color:var(--color-text-secondary)]">
											The selected input value will be interpreted as a boolean.
											Values of &quot;true&quot;, &quot;True&quot;, or
											&quot;TRUE&quot; route to the True branch. Values of
											&quot;false&quot;, &quot;False&quot;, or &quot;FALSE&quot;
											route to the False branch.
										</p>
									</div>
								</div>
							</div>

							{/* Input Source Selector */}
							{onInputSourceChange && (
								<ConditionInputModeSelector
									selectedMode={inputSource}
									onModeChange={onInputSourceChange}
								/>
							)}

							{/* Specific Node Picker */}
							{inputSource === "specific" && onSourceNodeChange && (
								<ConditionSourceNodePicker
									condition={{
										input_source: inputSource,
										source_node_id: sourceNodeId,
										field_path: fieldPath,
									}}
									availableNodes={availableNodes}
									onChange={(condition) => {
										if (condition.source_node_id !== undefined) {
											onSourceNodeChange(condition.source_node_id);
										}
										if (
											condition.field_path !== undefined &&
											onFieldPathChange
										) {
											onFieldPathChange(condition.field_path);
										}
									}}
								/>
							)}

							{/* Field Path / Structured Field Picker */}
							{(inputSource === "field" ||
								(inputSource === "specific" && sourceNodeId)) &&
								onFieldPathChange && (
									<div className="rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 p-4 backdrop-blur-sm">
										{inputSource === "specific" && hasStructuredOutputs ? (
											<>
												{/* Structured Field Picker */}
												<div className="flex items-center gap-2 mb-3">
													<Sparkles className="w-4 h-4 text-[color:var(--color-accent)]" />
													<h3 className="text-base font-semibold text-slate-900">
														Structured Fields
													</h3>
													<span className="text-xs text-[color:var(--color-text-muted)]">
														({availableFields.length} available)
													</span>
												</div>
												<StructuredFieldPicker
													fields={availableFields}
													value={fieldPath}
													onChange={onFieldPathChange}
													placeholder="Select a boolean field"
													nodeName={selectedNode?.data?.name}
													allowManualInput={true}
												/>
												<p className="mt-3 text-xs text-[color:var(--color-text-muted)]">
													Select a field to evaluate as boolean. Boolean fields
													are recommended for binary conditions.
												</p>
											</>
										) : (
											<>
												{/* Manual Field Path Input */}
												<h3 className="mb-3 text-base font-semibold text-slate-900">
													Field Path{" "}
													{inputSource === "specific" ? "(Optional)" : ""}
												</h3>
												<input
													type="text"
													value={fieldPath}
													onChange={(e) => onFieldPathChange(e.target.value)}
													placeholder="e.g., result.is_approved"
													className="w-full px-4 py-3 bg-[color:var(--color-surface)]/50 border-2 border-[color:var(--color-border)]/50 rounded-xl text-slate-900 text-sm placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200 hover:border-[color:var(--color-border)]"
												/>
												<p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
													Extract a boolean field from the selected source
												</p>
											</>
										)}
									</div>
								)}

							{/* Branch Labels */}
							<div className="p-5 bg-[color:var(--color-surface)]/40 rounded-xl border border-[color:var(--color-border)]/40">
								<div className="flex items-center gap-2 mb-4">
									<GitBranch className="w-4 h-4 text-[color:var(--color-primary)]" />
									<span className="text-sm font-semibold text-[color:var(--color-text-secondary)]">
										Branch Labels
									</span>
									<InfoTooltip text="Customize the labels for each branch outcome" />
								</div>
								<div className="space-y-3">
									{branchLabels.map((label, index) => (
										<div key={`label-${index}`} className="flex gap-3">
											<input
												id={`branch-label-input-${index}`}
												type="text"
												value={label}
												onChange={(e) =>
													handleBinaryLabelChange(index, e.target.value)
												}
												placeholder={
													index === 0
														? "True branch label"
														: "False branch label"
												}
												aria-label={`${index === 0 ? "True" : "False"} branch label`}
												className="flex-1 px-4 py-2.5 bg-[color:var(--color-surface)] border border-[color:var(--color-border)]/50 rounded-lg text-slate-900 text-sm placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200"
											/>
											<div
												className={`px-4 py-2.5 rounded-lg flex items-center gap-2.5 font-medium text-sm min-w-[120px] justify-center ${
													index === 0
														? "bg-[#0DA931]/20 text-[#0DA931] border border-[#0DA931]/30"
														: "bg-red-500/20 text-red-400 border border-red-500/30"
												}`}
											>
												<div
													className={`w-3 h-3 rounded-full ${
														index === 0 ? "bg-[#0DA931]" : "bg-red-500"
													}`}
												/>
												Branch {index + 1}
											</div>
										</div>
									))}
								</div>
							</div>
						</>
					)}

					{/* Multi-Branch Mode - Branch List */}
					{branchMode === "multi" && (
						<div className="p-5 bg-[color:var(--color-surface)]/40 rounded-xl border border-[color:var(--color-border)]/40">
							<div className="flex items-center justify-between mb-4">
								<div className="flex items-center gap-2">
									<Layers className="w-4 h-4 text-[color:var(--color-primary)]" />
									<span className="text-sm font-semibold text-[color:var(--color-text-secondary)]">
										Branches ({branches.length}/4)
									</span>
									<InfoTooltip text="Create and configure multiple conditional branches" />
								</div>
								{branches.length < 4 && (
									<button
										onClick={handleAddBranch}
										className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-[color:var(--button-primary-text)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] border border-[rgba(var(--color-primary-rgb),0.5)] rounded-lg transition-all shadow-[0_2px_8px_rgba(var(--color-primary-rgb),0.25)] hover:shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.35)] hover:scale-105"
									>
										<Plus className="w-4 h-4" />
										Add Branch
									</button>
								)}
							</div>

							{/* Branch Cards */}
							<div className="space-y-3">
								{branches.map((branch, index) => (
									<div
										key={branch.handle_id || `branch-${index}`}
										className="bg-[color:var(--color-surface)] rounded-lg border border-[color:var(--color-border)]/50 p-4 hover:bg-[color:var(--color-surface)]/80 transition-all duration-200"
									>
										<div className="flex items-center justify-between">
											<div className="flex items-center gap-3 flex-1">
												<div
													className="w-8 h-8 rounded-full border-2 border-[color:var(--color-border)] shadow-md flex-shrink-0"
													style={{ backgroundColor: branch.color }}
												/>
												<input
													id={`branch-label-${index}`}
													type="text"
													value={branch.label}
													onChange={(e) =>
														handleBranchLabelChange(index, e.target.value)
													}
													className="flex-1 px-3 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)]/50 rounded-lg text-slate-900 text-sm placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200"
													placeholder="Branch label"
													aria-label={`Branch ${index + 1} label`}
												/>
											</div>
											<div className="flex items-center gap-2 ml-3">
												{/* Color Picker */}
												<div className="relative group">
													<input
														id={`branch-color-${index}`}
														type="color"
														value={branch.color}
														onChange={(e) =>
															handleBranchColorChange(index, e.target.value)
														}
														className="w-9 h-9 rounded-lg cursor-pointer border-2 border-[color:var(--color-border)] hover:border-[color:var(--color-primary)]/50 transition-all duration-200"
														style={{ backgroundColor: branch.color }}
														title="Choose branch color"
														aria-label={`Branch ${index + 1} color`}
													/>
													<Palette className="w-3 h-3 text-white absolute bottom-0.5 right-0.5 pointer-events-none" />
												</div>
												<button
													onClick={() => handleRemoveBranch(index)}
													className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-all duration-200"
													title="Remove branch"
												>
													<Trash2 className="w-4 h-4" />
												</button>
											</div>
										</div>

										{/* Handle ID Display */}
										<div className="mt-3 px-3 py-2 bg-[color:var(--color-bg-secondary)]/50 rounded-lg border border-[color:var(--color-border)]/30">
											<span className="text-xs text-[color:var(--color-text-muted)]">
												Handle ID:{" "}
												<span className="text-[color:var(--color-text-secondary)] font-mono">
													{branch.handle_id}
												</span>
											</span>
										</div>
									</div>
								))}
							</div>

							{branches.length === 0 && (
								<div className="p-6 bg-[color:var(--color-surface)]/60 rounded-lg border border-[color:var(--color-border)]/40 text-center">
									<Layers className="w-8 h-8 text-[color:var(--color-text-muted)] mx-auto mb-2" />
									<p className="text-sm text-[color:var(--color-text-muted)] mb-3">
										No branches configured
									</p>
									<button
										onClick={handleAddBranch}
										className="px-4 py-2 text-[color:var(--button-primary-text)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] border border-[rgba(var(--color-primary-rgb),0.5)] rounded-lg transition-all text-sm font-semibold shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.25)] hover:shadow-[0_6px_16px_rgba(var(--color-primary-rgb),0.35)] hover:scale-105"
									>
										Add First Branch
									</button>
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
