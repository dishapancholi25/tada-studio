"use client";

import { Code, Info, Settings, Shield } from "lucide-react";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

interface SettingsSectionProps {
	hasDefaultBranch: boolean;
	onHasDefaultBranchChange: (has: boolean) => void;
	defaultBranchLabel: string;
	onDefaultBranchLabelChange: (label: string) => void;
	conditionType: string;
	onConditionTypeChange: (type: "simple" | "expression") => void;
	expression: string;
	onExpressionChange: (expression: string) => void;
	branchMode: string;
}

export default function SettingsSection({
	hasDefaultBranch,
	onHasDefaultBranchChange,
	defaultBranchLabel,
	onDefaultBranchLabelChange,
	conditionType,
	onConditionTypeChange,
	expression,
	onExpressionChange,
	branchMode,
}: SettingsSectionProps) {
	return (
		<div className="space-y-6">
			<div className="space-y-3">
				<div className="flex items-center gap-2">
					<Shield className="h-3.5 w-3.5 text-gray-600" />
					<span className="text-xs font-semibold capitalize text-gray-700">
						Fallback Branch
					</span>
				</div>

				<div className="rounded-[4px] border border-gray-200 bg-white p-3.5 shadow-sm">
					<label className="group flex cursor-pointer items-center justify-between gap-3">
						<div>
							<p className="text-sm font-medium text-gray-900 transition-colors group-hover:text-slate-900">
								Enable Default Branch
							</p>
							<p className="text-[10px] text-gray-600">
								Route to a fallback when no conditions match
							</p>
						</div>
						<div className="relative inline-flex items-center">
							<input
								type="checkbox"
								checked={hasDefaultBranch}
								onChange={(e) => onHasDefaultBranchChange(e.target.checked)}
								className="peer sr-only"
							/>
							<div className="h-6 w-11 rounded-full bg-gray-300 transition-colors peer-checked:bg-orange-600" />
							<div className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white transition-transform peer-checked:translate-x-5" />
						</div>
					</label>

					{hasDefaultBranch && (
						<div className="mt-3 animate-in fade-in border-t border-gray-200 pt-3 duration-150">
							<label className="mb-1.5 block text-[10px] capitalize text-gray-600">
								Default Branch Label
							</label>
							<input
								type="text"
								value={defaultBranchLabel}
								onChange={(e) => onDefaultBranchLabelChange(e.target.value)}
								placeholder="Default"
								className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							/>
						</div>
					)}
				</div>
			</div>

			{branchMode === "multi" && (
				<div className="space-y-3">
					<div className="flex items-center gap-2">
						<Code className="h-3.5 w-3.5 text-gray-600" />
						<span className="text-xs font-semibold capitalize text-gray-700">
							Condition Type
						</span>
					</div>

					<div className="flex gap-1.5 rounded-[4px] border border-gray-200 bg-white p-1">
						<button
							type="button"
							onClick={() => onConditionTypeChange("simple")}
							className={`flex flex-1 items-center justify-center gap-1.5 rounded-[4px] px-3 py-2 text-xs font-semibold transition-colors duration-200 ${
								conditionType === "simple"
									? "border border-orange-500 bg-white text-orange-900 shadow-sm"
									: "text-gray-600 hover:bg-slate-50 hover:text-slate-900"
							}`}
						>
							<Settings className="h-3.5 w-3.5" />
							Visual Builder
						</button>
						<button
							type="button"
							onClick={() => onConditionTypeChange("expression")}
							className={`flex flex-1 items-center justify-center gap-1.5 rounded-[4px] px-3 py-2 text-xs font-semibold transition-colors duration-200 ${
								conditionType === "expression"
									? "border border-orange-500 bg-white text-orange-900 shadow-sm"
									: "text-gray-600 hover:bg-slate-50 hover:text-slate-900"
							}`}
						>
							<Code className="h-3.5 w-3.5" />
							Python Expression
						</button>
					</div>

					{conditionType === "expression" && (
						<div className="animate-in fade-in space-y-2 duration-200">
							<div className="flex items-center gap-2">
								<label
									htmlFor="python-expression"
									className="text-xs font-semibold text-gray-800"
								>
									Python Expression
								</label>
								<InfoTooltip text="Write a Python expression that returns the branch handle_id to route to" />
							</div>
							<textarea
								id="python-expression"
								value={expression}
								onChange={(e) => onExpressionChange(e.target.value)}
								placeholder="e.g., 'branch-0' if node_outputs['abc123']['fields']['score'] > 80 else 'branch-1'"
								className="h-32 w-full resize-none rounded-[4px] border border-gray-200 bg-white px-3 py-3 font-mono text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							/>
							<div className="rounded-[4px] border border-orange-400 bg-white p-2.5 shadow-sm">
								<p className="flex items-start gap-2 text-[10px] text-gray-700">
									<Info className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-orange-600" />
									<span>
										<span className="font-semibold text-gray-900">
											Available variables:
										</span>{" "}
										<code className="font-mono text-orange-800">node_outputs</code>
										,{" "}
										<code className="font-mono text-orange-800">message</code>
										,{" "}
										<code className="font-mono text-orange-800">results</code>
									</span>
								</p>
							</div>
						</div>
					)}
				</div>
			)}
		</div>
	);
}
