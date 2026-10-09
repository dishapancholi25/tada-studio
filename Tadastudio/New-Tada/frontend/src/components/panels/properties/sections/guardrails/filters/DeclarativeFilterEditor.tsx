import { useMemo } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { CustomFilter, JudgeLLMConfig } from "@/types/guardrails";
import { FILTER_TEMPLATES } from "@/types/guardrails";
import Dropdown from "../../../../../ui/Dropdown";

interface DeclarativeFilterEditorProps {
	templateId: string;
	templateParams: Record<string, unknown>;
	judgeLlmConfig: JudgeLLMConfig | null;
	onChange: (updates: Partial<CustomFilter>) => void;
	modelOptions: Array<{
		value: string;
		label: string;
		description?: string;
		model?: Record<string, unknown>;
	}>;
	modelsLoading: boolean;
}

export default function DeclarativeFilterEditor({
	templateId,
	templateParams,
	judgeLlmConfig,
	onChange,
	modelOptions,
	modelsLoading,
}: DeclarativeFilterEditorProps) {
	const templateOptions = useMemo(
		() =>
			FILTER_TEMPLATES.map((t) => ({
				value: t.id,
				label: t.name,
				description: t.description,
			})),
		[],
	);

	const selectedTemplate = useMemo(
		() => FILTER_TEMPLATES.find((t) => t.id === templateId),
		[templateId],
	);

	const handleTemplateChange = (value: string) => {
		const template = FILTER_TEMPLATES.find((t) => t.id === value);
		if (!template) return;

		// Initialize params with defaults from template
		const defaults: Record<string, unknown> = {};
		for (const [key, param] of Object.entries(template.params)) {
			defaults[key] = param.default;
		}

		onChange({
			template_id: value,
			template_params: defaults,
			name: template.name,
		});
	};

	const handleParamChange = (key: string, value: unknown) => {
		onChange({
			template_params: { ...templateParams, [key]: value },
		});
	};

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
					Template
				</label>
				<Dropdown
					value={templateId}
					onChange={handleTemplateChange}
					options={templateOptions}
					placeholder="Select a filter template"
				/>
			</div>

			{selectedTemplate && (
				<div className="space-y-3 rounded-lg border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/20 p-3">
					<p className="text-xs text-[color:var(--color-text-secondary)]">
						{selectedTemplate.description}
					</p>

					{Object.entries(selectedTemplate.params).map(
						([key, paramDef]) => (
							<div key={key}>
								<label className="mb-1 block text-xs font-medium text-[color:var(--color-text-secondary)]">
									{key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
								</label>
								{paramDef.description && (
									<p className="mb-1 text-[10px] text-[color:var(--color-text-secondary)]/70">
										{paramDef.description}
									</p>
								)}
								{renderParamInput(
									key,
									paramDef,
									templateParams[key] ?? paramDef.default,
									handleParamChange,
								)}
							</div>
						),
					)}
				</div>
			)}

			{selectedTemplate?.requires_llm_judge && (
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
							value={judgeLlmConfig?.model_deployment_id || ""}
							onChange={handleModelChange}
							options={modelOptions}
							placeholder="Select judge model"
						/>
					)}
					{!judgeLlmConfig?.model_deployment_id && !modelsLoading && (
						<div className="mt-1 flex items-center gap-1">
							<AlertTriangle className="h-3 w-3 text-amber-400/80" />
							<span className="text-[10px] text-amber-400/80">
								This template requires an LLM judge model to evaluate content
							</span>
						</div>
					)}
					<p className="mt-1 text-[10px] text-[color:var(--color-text-secondary)]/70">
						The LLM judge evaluates content against the template rules.
					</p>
				</div>
			)}
		</div>
	);
}

function renderParamInput(
	key: string,
	paramDef: { type: string; default: unknown; min?: number; max?: number; options?: string[] },
	value: unknown,
	onChange: (key: string, value: unknown) => void,
) {
	switch (paramDef.type) {
		case "int":
		case "float":
			return (
				<input
					type="number"
					value={value as number}
					onChange={(e) =>
						onChange(
							key,
							paramDef.type === "int"
								? Number.parseInt(e.target.value, 10)
								: Number.parseFloat(e.target.value),
						)
					}
					min={paramDef.min}
					max={paramDef.max}
					step={paramDef.type === "float" ? 0.05 : 1}
					className="w-full rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm text-[color:var(--color-text-primary)]"
				/>
			);

		case "bool":
			return (
				<button
					type="button"
					onClick={() => onChange(key, !value)}
					className={`relative h-5 w-9 rounded-full transition-colors ${
						value
							? "bg-cyan-500"
							: "bg-[color:var(--color-border)]/60"
					}`}
				>
					<span
						className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
							value ? "translate-x-4" : "translate-x-0.5"
						}`}
					/>
				</button>
			);

		case "enum":
			return (
				<Dropdown
					value={value as string}
					onChange={(v) => onChange(key, v)}
					options={
						paramDef.options?.map((o) => ({
							value: o,
							label: o.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
						})) || []
					}
				/>
			);

		case "list":
			return (
				<ListParamInput
					value={(value as string[]) || []}
					onChange={(v) => onChange(key, v)}
					options={paramDef.options}
				/>
			);

		default:
			return (
				<input
					type="text"
					value={value as string}
					onChange={(e) => onChange(key, e.target.value)}
					className="w-full rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm text-[color:var(--color-text-primary)]"
				/>
			);
	}
}

function ListParamInput({
	value,
	onChange,
	options,
}: {
	value: string[];
	onChange: (value: string[]) => void;
	options?: string[];
}) {
	if (options && options.length > 0) {
		// Checkbox list for known options
		return (
			<div className="flex flex-wrap gap-1.5">
				{options.map((opt) => {
					const isSelected = value.includes(opt);
					return (
						<button
							key={opt}
							type="button"
							onClick={() => {
								if (isSelected) {
									onChange(value.filter((v) => v !== opt));
								} else {
									onChange([...value, opt]);
								}
							}}
							className={`rounded-md border px-2 py-1 text-[10px] font-medium transition-colors ${
								isSelected
									? "border-cyan-500/40 bg-cyan-500/15 text-cyan-400"
									: "border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/30 text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-border)]"
							}`}
						>
							{opt}
						</button>
					);
				})}
			</div>
		);
	}

	// Free-text tag input for custom lists
	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter" || e.key === ",") {
			e.preventDefault();
			const input = e.currentTarget;
			const newValue = input.value.trim();
			if (newValue && !value.includes(newValue)) {
				onChange([...value, newValue]);
				input.value = "";
			}
		}
	};

	return (
		<div className="space-y-1.5">
			<div className="flex flex-wrap gap-1">
				{value.map((item) => (
					<span
						key={item}
						className="flex items-center gap-1 rounded-md border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/40 px-2 py-0.5 text-[10px] text-[color:var(--color-text-secondary)]"
					>
						{item}
						<button
							type="button"
							onClick={() => onChange(value.filter((v) => v !== item))}
							className="text-[color:var(--color-text-secondary)]/50 hover:text-red-400"
						>
							&times;
						</button>
					</span>
				))}
			</div>
			<input
				type="text"
				placeholder="Type and press Enter to add"
				onKeyDown={handleKeyDown}
				className="w-full rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-1.5 text-xs text-[color:var(--color-text-primary)] placeholder-[color:var(--color-text-secondary)]/50"
			/>
		</div>
	);
}
