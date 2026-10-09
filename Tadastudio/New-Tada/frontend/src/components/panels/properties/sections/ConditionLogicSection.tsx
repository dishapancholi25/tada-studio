"use client";

import { AlertCircle, Code, Info, Plus, Zap } from "lucide-react";
import { useCallback } from "react";
import type { Node } from "reactflow";
import BranchConditionCard from "@/components/conditions/BranchConditionCard";
import EnhancedConditionRow from "@/components/conditions/EnhancedConditionRow";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import { InputSourceConfig } from "@/components/ui/UnifiedInputSourcePicker";

interface SimpleCondition {
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
	operator?: string;
	value?: any;
	value_type?: string;
	dynamic_source?: any;
}

interface BranchConfig {
	label: string;
	color: string;
	handle_id: string;
	condition: SimpleCondition;
}

interface ConditionLogicSectionProps {
	branchMode: string;
	conditionType: string;
	onConditionTypeChange: (type: "simple" | "expression") => void;
	simpleConditions: SimpleCondition[];
	onSimpleConditionsChange: (conditions: SimpleCondition[]) => void;
	expression: string;
	onExpressionChange: (expression: string) => void;
	logicOperator: string;
	onLogicOperatorChange: (operator: "AND" | "OR") => void;
	branches: BranchConfig[];
	onBranchesChange: (branches: BranchConfig[]) => void;
	availableNodes: Node[];
}

export default function ConditionLogicSection({
	branchMode,
	conditionType,
	onConditionTypeChange,
	simpleConditions,
	onSimpleConditionsChange,
	expression,
	onExpressionChange,
	logicOperator,
	onLogicOperatorChange,
	branches,
	onBranchesChange,
	availableNodes,
}: ConditionLogicSectionProps) {
	const addCondition = () => {
		onSimpleConditionsChange([
			...simpleConditions,
			{
				input_source: "previous",
				source_node_id: "",
				field_path: "",
				operator: "==",
				value: "",
				value_type: "static",
			},
		]);
	};

	const updateCondition = (index: number, condition: SimpleCondition) => {
		const conditions = [...simpleConditions];
		conditions[index] = condition;
		onSimpleConditionsChange(conditions);
	};

	const removeCondition = (index: number) => {
		const conditions = [...simpleConditions];
		conditions.splice(index, 1);
		onSimpleConditionsChange(conditions);
	};

	const duplicateCondition = (index: number) => {
		const conditions = [...simpleConditions];
		const conditionToDuplicate = { ...conditions[index] };
		conditions.splice(index + 1, 0, conditionToDuplicate);
		onSimpleConditionsChange(conditions);
	};

	const handleBranchConditionChange = (
		index: number,
		condition: SimpleCondition,
	) => {
		const updatedBranches = [...branches];
		updatedBranches[index] = {
			...updatedBranches[index],
			condition: condition,
		};
		onBranchesChange(updatedBranches);
	};

	return (
		<div className="space-y-6">
			<div className="rounded-2xl border-2 border-[color:var(--color-primary)]/30 bg-[color:var(--color-surface)]/35 p-6 backdrop-blur-sm shadow-[0_20px_45px_rgba(7,9,16,0.55)]">
				{/* Section header with icon */}
				<div className="flex items-start justify-between gap-4 pb-5 border-b border-[color:var(--color-primary)]/20">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)] shadow-[0_0_20px_rgba(var(--color-primary-rgb),0.25)]">
							<Zap className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Condition Logic
							</h3>
							<p className="text-sm text-[color:var(--color-text-muted)]">
								Define rules and evaluation criteria
							</p>
						</div>
					</div>
				</div>

				{/* Section content */}
				<div className="mt-6 space-y-6">
					{/* Binary Mode Content */}
					{branchMode === "binary" && (
						<>
							{/* Condition Type Selector */}
							<div>
								<div className="flex items-center gap-2 mb-3">
									<label className="block text-sm font-semibold text-[color:var(--color-text-secondary)]">
										Condition Type
									</label>
									<InfoTooltip text="Choose between simple conditions or custom Python expressions" />
								</div>

								<div className="flex gap-2 bg-[color:var(--color-surface)]/60 p-1.5 rounded-lg">
									<button
										onClick={() => onConditionTypeChange("simple")}
										className={`flex-1 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
											conditionType === "simple"
												? "bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] text-[color:var(--button-primary-text)] shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.3)]"
												: "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface)]"
										}`}
									>
										<Zap className="w-4 h-4" />
										Simple Conditions
									</button>
									<button
										onClick={() => onConditionTypeChange("expression")}
										className={`flex-1 px-4 py-3 rounded-lg text-sm font-semibold transition-all duration-200 flex items-center justify-center gap-2 ${
											conditionType === "expression"
												? "bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] text-[color:var(--button-primary-text)] shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.3)]"
												: "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface)]"
										}`}
									>
										<Code className="w-4 h-4" />
										Expression
									</button>
								</div>
							</div>

							{/* Simple Conditions */}
							{conditionType === "simple" && (
								<div className="p-6 bg-[color:var(--color-surface)]/40 rounded-xl border-2 border-[color:var(--color-border)]/40 animate-in fade-in duration-200">
									<div className="flex items-center justify-between mb-5">
										<div className="flex items-center gap-3">
											<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)] shadow-[0_0_12px_rgba(var(--color-primary-rgb),0.2)]">
												<Zap className="w-4 h-4" />
											</div>
											<span className="text-base font-semibold text-slate-900">
												Conditions
											</span>
										</div>
										<button
											onClick={addCondition}
											className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-[color:var(--button-primary-text)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] border border-[rgba(var(--color-primary-rgb),0.5)] rounded-xl transition-all duration-200 shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.25)] hover:shadow-[0_6px_16px_rgba(var(--color-primary-rgb),0.35)] hover:scale-[1.02] active:scale-[0.98]"
										>
											<Plus className="w-4 h-4" />
											Add Condition
										</button>
									</div>

									{simpleConditions.length === 0 && (
										<div className="p-10 bg-[color:var(--color-surface)] rounded-xl border-2 border-[color:var(--color-border)]/50 text-center animate-in fade-in zoom-in-95 duration-300">
											<div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/20 mx-auto mb-4">
												<AlertCircle className="w-8 h-8 text-[color:var(--color-primary)]" />
											</div>
											<h4 className="text-base font-semibold text-slate-900 mb-2">
												No conditions configured
											</h4>
											<p className="text-sm text-[color:var(--color-text-muted)] mb-6 max-w-sm mx-auto">
												Create your first condition to define the logic for this
												workflow branch
											</p>
											<button
												onClick={addCondition}
												className="px-6 py-3 text-[color:var(--button-primary-text)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] border border-[rgba(var(--color-primary-rgb),0.5)] rounded-xl transition-all duration-200 text-sm font-semibold shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.25)] hover:shadow-[0_6px_16px_rgba(var(--color-primary-rgb),0.35)] hover:scale-105 active:scale-95"
											>
												Add Your First Condition
											</button>
										</div>
									)}

									<div className="space-y-4">
										{simpleConditions.map((condition, index) => (
											<EnhancedConditionRow
												key={`condition-${index}`}
												condition={condition}
												index={index}
												onUpdate={(updated) => updateCondition(index, updated)}
												onRemove={() => removeCondition(index)}
												onDuplicate={() => duplicateCondition(index)}
												availableNodes={availableNodes}
												showDragHandle={false}
											/>
										))}
									</div>

									{/* Logic Operator */}
									{simpleConditions.length > 1 && (
										<div className="mt-6 pt-6 border-t-2 border-[color:var(--color-border)]/50 animate-in fade-in slide-in-from-top-2 duration-300">
											<div className="flex items-center gap-3 mb-4">
												<span className="text-sm font-semibold text-slate-900">
													Combine Conditions With
												</span>
												<InfoTooltip text="How multiple conditions should be evaluated together" />
											</div>
											<div className="flex gap-3">
												{["AND", "OR"].map((op) => (
													<button
														key={op}
														onClick={() =>
															onLogicOperatorChange(op as "AND" | "OR")
														}
														className={`flex-1 px-6 py-3.5 rounded-xl border-2 font-semibold text-sm transition-all duration-200 ${
															logicOperator === op
																? "bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.2)] to-[rgba(var(--color-primary-rgb),0.1)] border-[rgba(var(--color-primary-rgb),0.7)] text-[color:var(--color-primary)] shadow-[0_4px_12px_rgba(var(--color-primary-rgb),0.25)] scale-[1.02]"
																: "bg-[color:var(--color-surface)]/40 border-[color:var(--color-border)]/60 text-[color:var(--color-text-muted)] hover:border-[color:var(--color-border-hover)] hover:bg-[color:var(--color-surface)]/60 hover:text-[color:var(--color-text-secondary)] hover:scale-[1.01]"
														}`}
													>
														{op}
													</button>
												))}
											</div>
										</div>
									)}
								</div>
							)}

							{/* Expression */}
							{conditionType === "expression" && (
								<div className="p-6 bg-[color:var(--color-surface)]/40 rounded-xl border-2 border-[color:var(--color-border)]/40 animate-in fade-in duration-200">
									<div className="flex items-center gap-3 mb-4">
										<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)] shadow-[0_0_12px_rgba(var(--color-primary-rgb),0.2)]">
											<Code className="w-4 h-4" />
										</div>
										<div className="flex-1">
											<label
												htmlFor="python-expression"
												className="text-base font-semibold text-slate-900"
											>
												Python Expression
											</label>
											<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
												Write a Python expression that evaluates to True or
												False
											</p>
										</div>
										<InfoTooltip text="Use Python syntax to write complex condition logic" />
									</div>
									<textarea
										id="python-expression"
										value={expression}
										onChange={(e) => onExpressionChange(e.target.value)}
										placeholder="e.g., node_outputs['abc123']['fields']['score'] > 80"
										className="w-full px-4 py-3.5 bg-[color:var(--color-surface)] border-2 border-[color:var(--color-border)]/50 rounded-xl text-slate-900 font-mono text-sm h-40 placeholder-[color:var(--color-text-muted)] focus:border-[color:var(--color-primary)]/50 focus:ring-2 focus:ring-[color:var(--color-primary)]/20 focus:outline-none transition-all duration-200 hover:border-[color:var(--color-border)] resize-none"
									/>
									<div className="mt-3 p-3 bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/20 rounded-lg">
										<p className="text-xs text-[color:var(--color-text-muted)] flex items-start gap-2">
											<Info className="w-4 h-4 text-[color:var(--color-primary)] flex-shrink-0 mt-0.5" />
											<span>
												<span className="font-semibold text-slate-900">
													Available variables:
												</span>{" "}
												<code className="text-[color:var(--color-primary)] font-mono">
													node_outputs
												</code>
												,{" "}
												<code className="text-[color:var(--color-primary)] font-mono">
													message
												</code>
												,{" "}
												<code className="text-[color:var(--color-primary)] font-mono">
													results
												</code>
											</span>
										</p>
									</div>
								</div>
							)}
						</>
					)}

					{/* Multi-Branch Mode Content */}
					{branchMode === "multi" && (
						<div className="p-6 bg-[color:var(--color-surface)]/40 rounded-xl border-2 border-[color:var(--color-border)]/40 animate-in fade-in duration-200">
							<div className="flex items-center gap-3 mb-6">
								<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)] shadow-[0_0_12px_rgba(var(--color-primary-rgb),0.2)]">
									<Zap className="w-4 h-4" />
								</div>
								<span className="text-base font-semibold text-slate-900">
									Branch Conditions
								</span>
								<InfoTooltip text="Configure conditions for each branch" />
							</div>

							<div className="space-y-4">
								{branches.map((branch, index) => (
									<BranchConditionCard
										key={branch.handle_id || `branch-${index}`}
										branchLabel={branch.label}
										branchColor={branch.color}
										condition={branch.condition || {}}
										onConditionChange={(condition) =>
											handleBranchConditionChange(index, condition)
										}
										availableNodes={availableNodes}
										index={index}
									/>
								))}
							</div>

							{branches.length === 0 && (
								<div className="p-10 bg-[color:var(--color-surface)] rounded-xl border-2 border-[color:var(--color-border)]/50 text-center animate-in fade-in zoom-in-95 duration-300">
									<div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/20 mx-auto mb-4">
										<AlertCircle className="w-8 h-8 text-[color:var(--color-primary)]" />
									</div>
									<h4 className="text-base font-semibold text-slate-900 mb-2">
										No branches configured
									</h4>
									<p className="text-sm text-[color:var(--color-text-muted)] max-w-sm mx-auto">
										Add branches in the Branch Configuration tab to define
										multiple decision paths
									</p>
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
