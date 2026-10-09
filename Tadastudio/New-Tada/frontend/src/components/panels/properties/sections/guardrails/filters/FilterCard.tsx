import { ChevronDown, ChevronRight, Trash2 } from "lucide-react";
import { useState } from "react";
import type {
	CustomFilter,
	CustomFilterAction,
	CustomFilterScope,
} from "@/types/guardrails";
import Dropdown from "../../../../../ui/Dropdown";
import PythonCodeFilterEditor from "./PythonCodeFilterEditor";
import LLMJudgeFilterEditor from "./LLMJudgeFilterEditor";
import DeclarativeFilterEditor from "./DeclarativeFilterEditor";

interface FilterCardProps {
	filter: CustomFilter;
	index: number;
	onChange: (updates: Partial<CustomFilter>) => void;
	onDelete: () => void;
	modelOptions: Array<{
		value: string;
		label: string;
		description?: string;
		model?: Record<string, unknown>;
	}>;
	modelsLoading: boolean;
}

const TYPE_LABELS: Record<string, string> = {
	python_code: "Python",
	llm_judge: "LLM Judge",
	declarative: "Template",
};

const TYPE_COLORS: Record<string, string> = {
	python_code: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
	llm_judge: "bg-violet-500/20 text-violet-400 border-violet-500/30",
	declarative: "bg-amber-500/20 text-amber-400 border-amber-500/30",
};

const SCOPE_OPTIONS = [
	{ value: "both", label: "Both", description: "Ingress & egress" },
	{ value: "ingress", label: "Ingress", description: "Before LLM call" },
	{ value: "egress", label: "Egress", description: "After LLM response" },
];

const ACTION_OPTIONS = [
	{ value: "block", label: "Block", description: "Stop execution" },
	{ value: "warn", label: "Warn", description: "Log but continue" },
	{
		value: "transform",
		label: "Transform",
		description: "Modify content in-flight",
	},
];

export default function FilterCard({
	filter,
	index,
	onChange,
	onDelete,
	modelOptions,
	modelsLoading,
}: FilterCardProps) {
	const [isExpanded, setIsExpanded] = useState(false);

	return (
		<div className="rounded-xl border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/30 p-4">
			{/* Header */}
			<div className="flex items-center gap-3">
				<button
					type="button"
					onClick={() => setIsExpanded(!isExpanded)}
					className="flex h-6 w-6 items-center justify-center rounded-md hover:bg-[color:var(--color-border)]/30"
				>
					{isExpanded ? (
						<ChevronDown className="h-4 w-4 text-[color:var(--color-text-secondary)]" />
					) : (
						<ChevronRight className="h-4 w-4 text-[color:var(--color-text-secondary)]" />
					)}
				</button>

				{/* Toggle */}
				<button
					type="button"
					onClick={() => onChange({ enabled: !filter.enabled })}
					className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
						filter.enabled
							? "bg-cyan-500"
							: "bg-[color:var(--color-border)]/60"
					}`}
				>
					<span
						className={`absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
							filter.enabled ? "translate-x-4" : "translate-x-0"
						}`}
					/>
				</button>

				{/* Name or placeholder */}
				<span
					className={`flex-1 text-sm font-medium ${
						filter.enabled
							? "text-[color:var(--color-text-primary)]"
							: "text-[color:var(--color-text-secondary)]"
					}`}
				>
					{filter.name || `Filter ${index + 1}`}
				</span>

				{/* Type badge */}
				<span
					className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold capitalize tracking-wider ${
						TYPE_COLORS[filter.filter_type] || TYPE_COLORS.python_code
					}`}
				>
					{TYPE_LABELS[filter.filter_type] || filter.filter_type}
				</span>

				{/* Delete */}
				<button
					type="button"
					onClick={onDelete}
					className="rounded-lg p-1.5 text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-border)]/40 hover:text-red-400"
				>
					<Trash2 className="h-3.5 w-3.5" />
				</button>
			</div>

			{/* Expanded content */}
			{isExpanded && (
				<div className="mt-4 space-y-4 border-t border-[color:var(--color-border)]/40 pt-4">
					{/* Common fields */}
					<div className="grid grid-cols-2 gap-3">
						<div>
							<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
								Name
							</label>
							<input
								type="text"
								value={filter.name}
								onChange={(e) => onChange({ name: e.target.value })}
								placeholder="Filter name"
								className="w-full rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm text-[color:var(--color-text-primary)] placeholder-[color:var(--color-text-secondary)]/50"
							/>
						</div>
						<div>
							<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
								Priority
							</label>
							<input
								type="number"
								value={filter.priority}
								onChange={(e) =>
									onChange({
										priority: Math.max(
											0,
											Math.min(999, Number(e.target.value)),
										),
									})
								}
								min={0}
								max={999}
								className="w-full rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm text-[color:var(--color-text-primary)]"
							/>
						</div>
					</div>

					<div className="grid grid-cols-2 gap-3">
						<div>
							<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
								Scope
							</label>
							<Dropdown
								value={filter.scope}
								onChange={(val) =>
									onChange({ scope: val as CustomFilterScope })
								}
								options={SCOPE_OPTIONS}
							/>
						</div>
						<div>
							<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
								Action
							</label>
							<Dropdown
								value={filter.action}
								onChange={(val) =>
									onChange({ action: val as CustomFilterAction })
								}
								options={ACTION_OPTIONS}
							/>
						</div>
					</div>

					<div>
						<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
							Violation Message
						</label>
						<input
							type="text"
							value={filter.message}
							onChange={(e) => onChange({ message: e.target.value })}
							placeholder="Custom message shown when filter triggers"
							className="w-full rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm text-[color:var(--color-text-primary)] placeholder-[color:var(--color-text-secondary)]/50"
						/>
					</div>

					{/* Type-specific editor */}
					{filter.filter_type === "python_code" && (
						<PythonCodeFilterEditor
							pythonCode={filter.python_code}
							onChange={(code) => onChange({ python_code: code })}
						/>
					)}
					{filter.filter_type === "llm_judge" && (
						<LLMJudgeFilterEditor
							judgePrompt={filter.judge_prompt}
							judgeLlmConfig={filter.judge_llm_config}
							judgeThreshold={filter.judge_threshold}
							onChange={(updates) => onChange(updates)}
							modelOptions={modelOptions}
							modelsLoading={modelsLoading}
						/>
					)}
					{filter.filter_type === "declarative" && (
						<DeclarativeFilterEditor
							templateId={filter.template_id}
							templateParams={filter.template_params}
							judgeLlmConfig={filter.judge_llm_config}
							onChange={(updates) => onChange(updates)}
							modelOptions={modelOptions}
							modelsLoading={modelsLoading}
						/>
					)}
				</div>
			)}
		</div>
	);
}
