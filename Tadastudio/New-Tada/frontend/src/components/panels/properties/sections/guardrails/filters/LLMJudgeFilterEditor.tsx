import { AlertTriangle, Loader2 } from "lucide-react";
import type { CustomFilter, JudgeLLMConfig } from "@/types/guardrails";
import Dropdown from "../../../../../ui/Dropdown";

interface LLMJudgeFilterEditorProps {
	judgePrompt: string;
	judgeLlmConfig: JudgeLLMConfig | null;
	judgeThreshold: number;
	onChange: (updates: Partial<CustomFilter>) => void;
	modelOptions: Array<{
		value: string;
		label: string;
		description?: string;
		model?: Record<string, unknown>;
	}>;
	modelsLoading: boolean;
}

export default function LLMJudgeFilterEditor({
	judgePrompt,
	judgeLlmConfig,
	judgeThreshold,
	onChange,
	modelOptions,
	modelsLoading,
}: LLMJudgeFilterEditorProps) {
	const handleModelChange = (value: string) => {
		const option = modelOptions.find((o) => o.value === value);
		if (!option?.model) return;

		const model = option.model as Record<string, string>;
		const newConfig: JudgeLLMConfig = {
			model_deployment_id: model.model_deployment_id || value,
			provider: model.provider || "",
			model_name: model.model_name || "",
			display_name: option.label,
			temperature: 0.0,
		};
		onChange({ judge_llm_config: newConfig });
	};

	return (
		<div className="space-y-3">
			<div>
				<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
					Policy Prompt
				</label>
				<textarea
					value={judgePrompt}
					onChange={(e) => onChange({ judge_prompt: e.target.value })}
					placeholder="Describe the policy to enforce in natural language. Example: 'Flag responses that contain medical advice or diagnoses.'"
					rows={4}
					className="w-full resize-y rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm leading-relaxed text-[color:var(--color-text-primary)] placeholder-[color:var(--color-text-secondary)]/50 focus:outline-none"
				/>
				<p className="mt-1 text-[10px] text-[color:var(--color-text-secondary)]/70">
					The LLM judge will evaluate content against this policy and
					flag violations.
				</p>
			</div>

			<div className="grid grid-cols-2 gap-3">
				<div>
					<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
						Judge Model
					</label>
					{modelsLoading ? (
						<div className="flex items-center gap-2 rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2">
							<Loader2 className="h-4 w-4 animate-spin text-[color:var(--color-text-secondary)]" />
							<span className="text-xs text-[color:var(--color-text-secondary)]">
								Loading models...
							</span>
						</div>
					) : (
						<Dropdown
							value={
								judgeLlmConfig?.model_deployment_id || ""
							}
							onChange={handleModelChange}
							options={modelOptions}
							placeholder="Select model"
						/>
					)}
					{!judgeLlmConfig?.model_deployment_id && !modelsLoading && (
						<div className="mt-1 flex items-center gap-1">
							<AlertTriangle className="h-3 w-3 text-amber-400/80" />
							<span className="text-[10px] text-amber-400/80">
								Judge model required for LLM filter
							</span>
						</div>
					)}
				</div>
				<div>
					<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
						Confidence Threshold
					</label>
					<div className="flex items-center gap-2">
						<input
							type="range"
							min={0}
							max={1}
							step={0.05}
							value={judgeThreshold}
							onChange={(e) =>
								onChange({
									judge_threshold: Number(e.target.value),
								})
							}
							className="flex-1"
						/>
						<span className="min-w-[2.5rem] text-right text-xs font-mono text-[color:var(--color-text-secondary)]">
							{judgeThreshold.toFixed(2)}
						</span>
					</div>
					<p className="mt-0.5 text-[10px] text-[color:var(--color-text-secondary)]/70">
						Filter triggers when judge confidence exceeds this
						threshold
					</p>
				</div>
			</div>
		</div>
	);
}
