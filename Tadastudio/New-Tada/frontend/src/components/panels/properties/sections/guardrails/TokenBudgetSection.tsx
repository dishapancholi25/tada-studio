"use client";

import { useCallback } from "react";
import type { TokenBudget } from "@/types/guardrails";
import NumberInput from "../../../../ui/NumberInput";

interface TokenBudgetSectionProps {
	budget: TokenBudget;
	onChange: (budget: TokenBudget) => void;
}

export default function TokenBudgetSection({
	budget,
	onChange,
}: TokenBudgetSectionProps) {
	const handleNumberChange = useCallback(
		(field: keyof TokenBudget, value: number) => {
			onChange({ ...budget, [field]: value });
		},
		[budget, onChange],
	);

	const handleOptionalChange = useCallback(
		(field: keyof TokenBudget, value: number) => {
			onChange({ ...budget, [field]: value || null });
		},
		[budget, onChange],
	);

	const warnPercentDisplay = Math.round(budget.warn_at_percentage * 100);
	const sliderProgress = budget.warn_at_percentage * 100;

	return (
		<div className="space-y-5">
			{/* Token Limits */}
			<div className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-[color:var(--color-text-secondary)]">
					Token Limits
				</h4>
				<p className="text-xs text-[color:var(--color-text-muted)]">
					Set to 0 to leave unlimited. Limits are cumulative across all
					LLM calls in one execution.
				</p>
				<div className="grid gap-4 md:grid-cols-3">
					<NumberInput
						label="Max Input Tokens"
						value={budget.max_input_tokens_per_execution ?? 0}
						onChange={(v) =>
							handleOptionalChange(
								"max_input_tokens_per_execution",
								v,
							)
						}
						min={0}
						max={10000000}
						step={1000}
					/>
					<NumberInput
						label="Max Output Tokens"
						value={budget.max_output_tokens_per_execution ?? 0}
						onChange={(v) =>
							handleOptionalChange(
								"max_output_tokens_per_execution",
								v,
							)
						}
						min={0}
						max={10000000}
						step={1000}
					/>
					<NumberInput
						label="Max Total Tokens"
						value={budget.max_total_tokens_per_execution ?? 0}
						onChange={(v) =>
							handleOptionalChange(
								"max_total_tokens_per_execution",
								v,
							)
						}
						min={0}
						max={10000000}
						step={1000}
					/>
				</div>
			</div>

			{/* LLM Call Limit */}
			<div className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-[color:var(--color-text-secondary)]">
					LLM Calls
				</h4>
				<NumberInput
					label="Max LLM Calls per Execution"
					description="Maximum number of LLM invocations allowed"
					value={budget.max_llm_calls_per_execution}
					onChange={(v) =>
						handleNumberChange("max_llm_calls_per_execution", v)
					}
					min={1}
					max={200}
					step={1}
				/>
			</div>

			{/* Warning Threshold */}
			<div className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-[color:var(--color-text-secondary)]">
					Warning Threshold
				</h4>
				<div>
					<label className="mb-2 block text-sm font-medium text-[color:var(--color-text-secondary)]">
						Warn at {warnPercentDisplay}% of budget
					</label>
					<div className="flex items-center gap-4">
						<input
							type="range"
							min="0"
							max="100"
							value={warnPercentDisplay}
							onChange={(e) =>
								onChange({
									...budget,
									warn_at_percentage:
										Number.parseInt(e.target.value) / 100,
								})
							}
							className="flex-1 transition-all duration-200"
							style={{
								background: `linear-gradient(to right, rgba(6,182,212,0.85) 0%, rgba(6,182,212,0.85) ${sliderProgress}%, rgba(55,65,81,0.6) ${sliderProgress}%, rgba(55,65,81,0.6) 100%)`,
								accentColor: "rgb(6,182,212)",
							}}
						/>
						<span className="w-12 text-center text-sm font-semibold text-cyan-600">
							{warnPercentDisplay}%
						</span>
					</div>
					<p className="mt-1.5 text-xs text-[color:var(--color-text-muted)]">
						Emit a warning event when usage reaches this percentage
						of the budget.
					</p>
				</div>
			</div>
		</div>
	);
}
