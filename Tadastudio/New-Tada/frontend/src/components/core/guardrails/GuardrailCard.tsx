"use client";

import { ChevronDown, ChevronRight, GripVertical, Layers, Plus, Sparkles, Trash2, X } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import type { GuardrailItem, GuardrailItemType } from "@/types/guardrail-items";
import type {
	AdversarialItemConfig,
	CustomFilterItemConfig,
	DatabaseItemConfig,
	ExecutionLimitsItemConfig,
	FilesystemItemConfig,
	GeneralSafetyItemConfig,
	InputContentItemConfig,
	InputPolicyItemConfig,
	LLMJudgeItemConfig,
	NetworkItemConfig,
	OutputContentItemConfig,
	OutputPolicyItemConfig,
	OutputQualityItemConfig,
	PIIItemConfig,
	PatternRuleItemConfig,
	TokenBudgetItemConfig,
} from "@/types/guardrail-items";
import type { FilterAction, FilterScope, PIIAction, PatternEntry, ScannerAction } from "@/types/guardrails";
import {
	PATTERN_RULE_PRESETS,
} from "@/types/guardrails";
import { CATALOG_CATEGORIES } from "./catalog";
import Dropdown from "@/components/ui/Dropdown";
import NumberInput from "@/components/ui/NumberInput";
import Toggle from "@/components/ui/Toggle";
import RegexInput from "@/components/panels/properties/sections/guardrails/RegexInput";
import StringListEditor from "@/components/panels/properties/sections/guardrails/StringListEditor";
import PythonCodeFilterEditor from "@/components/panels/properties/sections/guardrails/filters/PythonCodeFilterEditor";
import LLMJudgeFilterEditor from "@/components/panels/properties/sections/guardrails/filters/LLMJudgeFilterEditor";
import DeclarativeFilterEditor from "@/components/panels/properties/sections/guardrails/filters/DeclarativeFilterEditor";
import PIIEntitySelector from "./PIIEntitySelector";

// ---------------------------------------------------------------------------
// Label / icon lookup
// ---------------------------------------------------------------------------

function findCatalogEntry(item: GuardrailItem) {
	for (const cat of CATALOG_CATEGORIES) {
		for (const entry of cat.entries) {
			if (entry.type !== item.type) continue;
			if (item.type === "pattern_rule") {
				return entry;
			} else if (item.type === "custom_filter") {
				const cfg = item.config as CustomFilterItemConfig;
				if (entry.templateId && entry.templateId === cfg.template_id)
					return entry;
				// Match by filter_type for non-template entries
				if (!entry.templateId) {
					if (
						cfg.filter_type === "python_code" &&
						entry.label === "Python Code Filter"
					)
						return entry;
					if (
						cfg.filter_type === "llm_judge" &&
						entry.label === "LLM Judge Filter"
					)
						return entry;
				}
			} else {
				return entry;
			}
		}
	}
	return null;
}

// ---------------------------------------------------------------------------
// Summary text
// ---------------------------------------------------------------------------

function getSummary(item: GuardrailItem): string {
	switch (item.type) {
		case "pattern_rule": {
			const c = item.config as PatternRuleItemConfig;
			const scope =
				c.applies_to === "both" ? "input & output" : c.applies_to;
			const patternLabels = (c.patterns ?? [])
				.map((p) => p.label)
				.filter(Boolean);
			const patternSuffix = patternLabels.length > 0
				? ` · ${patternLabels.join(", ")}`
				: "";
			return `${c.action} · ${scope}${patternSuffix}`;
		}
		case "llm_judge": {
			const c = item.config as LLMJudgeItemConfig;
			const judgeName = c.judge_llm_config?.display_name || "No judge model";
			return `Judge: ${judgeName}`;
		}
		case "general_safety": {
			const c = item.config as GeneralSafetyItemConfig;
			const features: string[] = [];
			if (c.system_prompt_protection) features.push("Prompt Protection");
			features.push(`Input: ${c.max_input_length.toLocaleString()}`);
			features.push(`Output: ${c.max_output_length.toLocaleString()}`);
			return features.join(" · ");
		}
		case "tool_network": {
			const c = item.config as NetworkItemConfig;
			const parts: string[] = [];
			if (c.allowed_url_patterns.length)
				parts.push(`${c.allowed_url_patterns.length} allowed`);
			if (c.blocked_url_patterns.length)
				parts.push(`${c.blocked_url_patterns.length} blocked`);
			parts.push(`${c.blocked_ip_ranges.length} IP ranges`);
			return parts.join(" · ");
		}
		case "tool_database": {
			const c = item.config as DatabaseItemConfig;
			return `${c.allowed_sql_operations.join(", ")} · max ${c.max_query_rows} rows`;
		}
		case "tool_filesystem": {
			const c = item.config as FilesystemItemConfig;
			return `max ${c.max_file_size_mb}MB · ${c.allowed_file_extensions.length || "all"} extensions`;
		}
		case "tool_execution_limits": {
			const c = item.config as ExecutionLimitsItemConfig;
			return `max ${c.max_tool_calls_per_execution} calls · ${c.tool_timeout_seconds}s timeout`;
		}
		case "token_budget": {
			const c = item.config as TokenBudgetItemConfig;
			const parts: string[] = [];
			if (c.max_total_tokens_per_execution)
				parts.push(
					`${(c.max_total_tokens_per_execution / 1000).toFixed(0)}k tokens`,
				);
			parts.push(`${c.max_llm_calls_per_execution} calls`);
			parts.push(`warn at ${Math.round(c.warn_at_percentage * 100)}%`);
			return parts.join(" · ");
		}
		case "provider_content_filter": {
			const c = item.config as import("@/types/guardrail-items").ProviderContentFilterItemConfig;
			return c.categories.length
				? `Categories: ${c.categories.join(", ")}`
				: "All categories";
		}
		case "llm_guard_adversarial": {
			const c = item.config as AdversarialItemConfig;
			const labels: string[] = [];
			if (c.detect_prompt_injection && c.detect_prompt_injection !== "off") labels.push(`Prompt Injection (${c.detect_prompt_injection})`);
			if (c.detect_jailbreak_attempts && c.detect_jailbreak_attempts !== "off") labels.push(`Jailbreak (${c.detect_jailbreak_attempts})`);
			return labels.length ? labels.join(" · ") : "No scanners enabled";
		}
		case "llm_guard_pii": {
			const c = item.config as PIIItemConfig;
			const piiLabels: Record<string, string> = {
				block: "Block",
				warn: "Warn",
				anonymize: "Anonymize",
			};
			const label = piiLabels[c.anonymize_pii] ?? "Disabled";
			return c.anonymize_pii === "anonymize" && c.use_faker ? `${label} (Faker)` : label;
		}
		case "llm_guard_input_content": {
			const c = item.config as InputContentItemConfig;
			const labels: string[] = [];
			if (c.detect_toxicity && c.detect_toxicity !== "off") labels.push(`Toxicity: ${c.detect_toxicity === "block" ? "Block" : "Warn"}`);
			if (c.detect_gibberish && c.detect_gibberish !== "off") labels.push(`Gibberish: ${c.detect_gibberish === "block" ? "Block" : "Warn"}`);
			if (c.ban_code && c.ban_code !== "off") labels.push(`Code: ${c.ban_code === "block" ? "Block" : "Warn"}`);
			return labels.length ? labels.join(" · ") : "No scanners enabled";
		}
		case "llm_guard_input_policy": {
			const c = item.config as InputPolicyItemConfig;
			const labels: string[] = [];
			if (c.ban_topics?.length) labels.push("Ban Topics");
			if (c.allowed_languages?.length) labels.push("Language Filter");
			if (c.max_input_tokens !== null && c.max_input_tokens !== undefined) labels.push(`Token Limit: ${c.max_input_tokens}`);
			if (c.detect_secrets && c.detect_secrets !== "off") labels.push(`Secrets: ${c.detect_secrets === "block" ? "Block" : "Warn"}`);
			return labels.length ? labels.join(" · ") : "No policies active";
		}
		case "llm_guard_output_quality": {
			const c = item.config as OutputQualityItemConfig;
			const labels: string[] = [];
			if (c.detect_refusal && c.detect_refusal !== "off") labels.push(`Refusal: ${c.detect_refusal === "block" ? "Block" : "Warn"}`);
			if (c.check_relevance && c.check_relevance !== "off") labels.push(`Relevance: ${c.check_relevance === "block" ? "Block" : "Warn"}`);
			if (c.check_factual_consistency && c.check_factual_consistency !== "off") labels.push(`Factual: ${c.check_factual_consistency === "block" ? "Block" : "Warn"}`);
			if (c.detect_gibberish && c.detect_gibberish !== "off") labels.push(`Gibberish: ${c.detect_gibberish === "block" ? "Block" : "Warn"}`);
			return labels.length ? labels.join(" · ") : "No scanners enabled";
		}
		case "llm_guard_output_content": {
			const c = item.config as OutputContentItemConfig;
			const labels: string[] = [];
			if (c.detect_toxicity && c.detect_toxicity !== "off") labels.push(`Toxicity: ${c.detect_toxicity === "block" ? "Block" : "Warn"}`);
			if (c.detect_bias && c.detect_bias !== "off") labels.push(`Bias: ${c.detect_bias === "block" ? "Block" : "Warn"}`);
			return labels.length ? labels.join(" · ") : "No scanners enabled";
		}
		case "llm_guard_output_policy": {
			const c = item.config as OutputPolicyItemConfig;
			const labels: string[] = [];
			if (c.detect_sensitive_data && c.detect_sensitive_data !== "off") labels.push(`Sensitive Data: ${c.detect_sensitive_data === "block" ? "Block" : "Warn"}`);
			if (c.ban_competitors?.length) labels.push("Ban Competitors");
			if (c.ban_topics?.length) labels.push("Ban Topics");
			if (c.allowed_languages?.length) labels.push("Language Filter");
			return labels.length ? labels.join(" · ") : "No policies active";
		}
		case "custom_filter": {
			const c = item.config as CustomFilterItemConfig;
			const typeLabel =
				c.filter_type === "python_code"
					? "Python"
					: c.filter_type === "llm_judge"
						? "LLM Judge"
						: c.template_id || "Template";
			return `${typeLabel} · ${c.action} · ${c.scope}${c.name ? ` · ${c.name}` : ""}`;
		}
		default:
			return "";
	}
}

// ---------------------------------------------------------------------------
// Category color
// ---------------------------------------------------------------------------

const TYPE_COLORS: Record<string, string> = {
	pattern_rule: "border-amber-500/30 bg-amber-500/10 text-amber-400",
	llm_judge: "border-violet-500/30 bg-violet-500/10 text-violet-400",
	general_safety: "border-indigo-500/30 bg-indigo-500/10 text-indigo-400",
	tool_network: "border-blue-500/30 bg-blue-500/10 text-blue-400",
	tool_database: "border-blue-500/30 bg-blue-500/10 text-blue-400",
	tool_filesystem: "border-blue-500/30 bg-blue-500/10 text-blue-400",
	tool_execution_limits: "border-blue-500/30 bg-blue-500/10 text-blue-400",
	llm_guard_adversarial: "border-red-500/30 bg-red-500/10 text-red-400",
	llm_guard_pii: "border-purple-500/30 bg-purple-500/10 text-purple-400",
	llm_guard_input_content: "border-orange-500/30 bg-orange-500/10 text-orange-400",
	llm_guard_input_policy: "border-blue-500/30 bg-blue-500/10 text-blue-400",
	llm_guard_output_quality: "border-[#0DA931]/30 bg-[#0DA931]/10 text-[#0DA931]",
	llm_guard_output_content: "border-orange-500/30 bg-orange-500/10 text-orange-400",
	llm_guard_output_policy: "border-blue-500/30 bg-blue-500/10 text-blue-400",
	provider_content_filter:
		"border-rose-500/30 bg-rose-500/10 text-rose-400",
	token_budget: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
	custom_filter: "border-cyan-500/30 bg-cyan-500/10 text-cyan-400",
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ModelOption {
	value: string;
	label: string;
	description?: string;
	model?: Record<string, unknown>;
}

interface GuardrailCardProps {
	item: GuardrailItem;
	isExpanded: boolean;
	onToggleExpand: () => void;
	onChange: (updated: GuardrailItem) => void;
	onRemove: () => void;
	readOnly?: boolean;
	modelOptions?: ModelOption[];
	modelsLoading?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GuardrailCard({
	item,
	isExpanded,
	onToggleExpand,
	onChange,
	onRemove,
	readOnly = false,
	modelOptions = [],
	modelsLoading = false,
}: GuardrailCardProps) {
	const entry = findCatalogEntry(item);
	const Icon = entry?.icon;
	const catalogLabel = entry?.label ?? item.type;
	// For pattern rules and custom filters, prefer the user-defined name over the generic catalog label
	const customName =
		item.type === "pattern_rule"
			? (item.config as PatternRuleItemConfig).name
			: item.type === "custom_filter"
				? (item.config as CustomFilterItemConfig).name
				: undefined;
	const label = customName || catalogLabel;
	const summary = getSummary(item);
	const colorClass = TYPE_COLORS[item.type] ?? TYPE_COLORS.custom_filter;

	const updateConfig = (partial: Record<string, unknown>) => {
		onChange({
			...item,
			config: { ...item.config, ...partial },
		} as GuardrailItem);
	};

	return (
		<div className="rounded-xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/20 transition-all hover:border-[color:var(--color-border)]/70">
			{/* Header */}
			<div className="flex w-full items-center gap-3 px-4 py-3">
				<div
					role="button"
					tabIndex={0}
					onClick={onToggleExpand}
					onKeyDown={(e) => {
						if (e.key === "Enter" || e.key === " ") onToggleExpand();
					}}
					className="flex min-w-0 flex-1 items-center gap-3 cursor-pointer"
				>
					<GripVertical className="h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-muted)]/40" />
					<div
						className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border ${colorClass}`}
					>
						{Icon && <Icon className="h-3.5 w-3.5" />}
					</div>
					<div className="min-w-0 flex-1">
						<div className="text-sm font-medium text-[color:var(--color-text-primary)] truncate">
							{label}
						</div>
						<div className="text-xs text-[color:var(--color-text-muted)] truncate">
							{summary}
						</div>
					</div>
					{isExpanded ? (
						<ChevronDown className="h-4 w-4 shrink-0 text-[color:var(--color-text-muted)]" />
					) : (
						<ChevronRight className="h-4 w-4 shrink-0 text-[color:var(--color-text-muted)]" />
					)}
				</div>
				{!readOnly && (
					<button
						type="button"
						onClick={onRemove}
						className="shrink-0 rounded-lg p-1.5 text-[color:var(--color-text-muted)] transition-colors hover:bg-red-500/10 hover:text-red-400"
					>
						<Trash2 className="h-3.5 w-3.5" />
					</button>
				)}
			</div>

			{/* Expanded editor */}
			{isExpanded && (
				<div className="border-t border-[color:var(--color-border)]/40 px-4 py-4">
					<ItemEditor
						item={item}
						updateConfig={updateConfig}
						readOnly={readOnly}
						modelOptions={modelOptions}
						modelsLoading={modelsLoading}
					/>
				</div>
			)}
		</div>
	);
}

// ---------------------------------------------------------------------------
// Inline editor — dispatches by item type
// ---------------------------------------------------------------------------

function ItemEditor({
	item,
	updateConfig,
	readOnly,
	modelOptions,
	modelsLoading,
}: {
	item: GuardrailItem;
	updateConfig: (partial: Record<string, unknown>) => void;
	readOnly: boolean;
	modelOptions: ModelOption[];
	modelsLoading: boolean;
}) {
	switch (item.type) {
		case "pattern_rule":
			return (
				<PatternRuleEditor
					config={item.config as PatternRuleItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_judge":
			return (
				<LLMJudgeEditor
					config={item.config as LLMJudgeItemConfig}
					onChange={updateConfig}
					modelOptions={modelOptions}
					modelsLoading={modelsLoading}
					readOnly={readOnly}
				/>
			);
		case "general_safety":
			return (
				<GeneralSafetyEditor
					config={item.config as GeneralSafetyItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_guard_adversarial":
			return (
				<AdversarialEditor
					config={item.config as AdversarialItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_guard_pii":
			return (
				<PIIEditor
					config={item.config as PIIItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_guard_input_content":
			return (
				<InputContentEditor
					config={item.config as InputContentItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_guard_input_policy":
			return (
				<InputPolicyEditor
					config={item.config as InputPolicyItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_guard_output_quality":
			return (
				<OutputQualityEditor
					config={item.config as OutputQualityItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_guard_output_content":
			return (
				<OutputContentEditor
					config={item.config as OutputContentItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "llm_guard_output_policy":
			return (
				<OutputPolicyEditor
					config={item.config as OutputPolicyItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "tool_network":
			return (
				<NetworkEditor
					config={item.config as NetworkItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "tool_database":
			return (
				<DatabaseEditor
					config={item.config as DatabaseItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "tool_filesystem":
			return (
				<FilesystemEditor
					config={item.config as FilesystemItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "tool_execution_limits":
			return (
				<ExecutionLimitsEditor
					config={item.config as ExecutionLimitsItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "provider_content_filter":
			return (
				<ProviderContentFilterEditor
					config={
						item.config as import("@/types/guardrail-items").ProviderContentFilterItemConfig
					}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "token_budget":
			return (
				<TokenBudgetEditor
					config={item.config as TokenBudgetItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
				/>
			);
		case "custom_filter":
			return (
				<CustomFilterEditor
					config={item.config as CustomFilterItemConfig}
					onChange={updateConfig}
					readOnly={readOnly}
					modelOptions={modelOptions}
					modelsLoading={modelsLoading}
				/>
			);
		default:
			return null;
	}
}

// ---------------------------------------------------------------------------
// Shared input class
// ---------------------------------------------------------------------------

const inputClass =
	"w-full rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm text-[color:var(--color-text-primary)] placeholder-[color:var(--color-text-muted)]/50 focus:border-[rgba(6,182,212,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(6,182,212,0.45)]";

const ACTION_OPTIONS = [
	{ value: "block", label: "Block", description: "Reject content" },
	{ value: "warn", label: "Warn", description: "Log but allow" },
	{ value: "redact", label: "Redact", description: "Replace with [REDACTED]" },
];

const SCOPE_OPTIONS = [
	{ value: "both", label: "Both", description: "Input and output" },
	{ value: "input", label: "Input", description: "User input only" },
	{ value: "output", label: "Output", description: "Agent output only" },
];

const SCANNER_ACTION_OPTIONS = [
	{ value: "off", label: "Off", description: "Disabled" },
	{ value: "block", label: "Block", description: "Reject content" },
	{ value: "warn", label: "Warn", description: "Log but allow" },
];

// ---------------------------------------------------------------------------
// Pattern Rule Editor
// ---------------------------------------------------------------------------

function PatternRuleEditor({
	config,
	onChange,
	readOnly,
}: {
	config: PatternRuleItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	const [pickerOpen, setPickerOpen] = useState(false);
	const pickerRef = useRef<HTMLDivElement>(null);

	const handlePickerBlur = useCallback((e: React.FocusEvent) => {
		if (
			pickerRef.current &&
			!pickerRef.current.contains(e.relatedTarget as Node)
		) {
			setPickerOpen(false);
		}
	}, []);

	// Merge existing patterns with new ones from a preset/template,
	// replacing any leading empty placeholder pattern.
	const addPatternsFrom = useCallback(
		(newPatterns: PatternEntry[]) => {
			const current = config.patterns ?? [];
			// Strip leading empty placeholders so presets fill them
			const base = current.filter((p) => p.label || p.regex);
			const existingRegexes = new Set(base.map((p) => p.regex));
			const merged = [...base];
			for (const p of newPatterns) {
				if (!existingRegexes.has(p.regex)) merged.push(p);
			}
			onChange({ patterns: merged });
			setPickerOpen(false);
		},
		[config.patterns, onChange],
	);

	const patterns: PatternEntry[] = config.patterns ?? [];

	return (
		<div className="space-y-3">
			<div>
				<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
					Name
				</label>
				<input
					type="text"
					value={config.name}
					onChange={(e) => onChange({ name: e.target.value })}
					placeholder="e.g. block_pii"
					className={inputClass}
					disabled={readOnly}
				/>
			</div>

			{/* Patterns list */}
			<div>
				<div className="mb-1 flex items-center justify-between">
					<label className="text-xs text-[color:var(--color-text-muted)]">
						Patterns (regex)
					</label>
					{!readOnly && (
						<div
							ref={pickerRef}
							className="relative"
							onBlur={handlePickerBlur}
						>
							<button
								type="button"
								onClick={() => setPickerOpen((o) => !o)}
								className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] text-cyan-400 transition-colors hover:bg-[rgba(6,182,212,0.1)] hover:text-cyan-600"
							>
								<Sparkles className="h-3 w-3" />
								Add from preset
								<ChevronDown
									className={`h-3 w-3 transition-transform ${pickerOpen ? "rotate-180" : ""}`}
								/>
							</button>

							{pickerOpen && (
								<div className="absolute right-0 z-50 mt-1 w-80 max-h-80 overflow-y-auto rounded-xl border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)] py-1 shadow-xl">
									<div className="px-3 py-1.5 text-[10px] font-semibold capitalize tracking-wider text-[color:var(--color-text-muted)]/60">
										Pattern presets
									</div>
									{PATTERN_RULE_PRESETS.map((preset) => (
										<button
											key={preset.preset_id}
											type="button"
											onClick={() =>
												addPatternsFrom(preset.patterns)
											}
											className="flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors hover:bg-[rgba(168,85,247,0.08)]"
										>
											<div className="min-w-0 flex-1">
												<div className="text-sm font-medium text-[color:var(--color-text-primary)]">
													{preset.name}
												</div>
												<div className="text-[11px] text-[color:var(--color-text-muted)]/70">
													{preset.description}
												</div>
											</div>
											{preset.patterns.length > 1 && (
												<span className="mt-0.5 shrink-0 rounded bg-purple-500/10 px-1.5 py-0.5 text-[10px] font-medium text-purple-400">
													{preset.patterns.length}
												</span>
											)}
										</button>
									))}
								</div>
							)}
						</div>
					)}
				</div>
				<div className="space-y-2">
					{patterns.map((pat, i) => (
						<div key={`pat-${i}`} className="rounded-lg border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/20 p-2 space-y-1.5">
							<div className="flex gap-1.5">
								<input
									type="text"
									value={pat.label}
									onChange={(e) => {
										const updated = [...patterns];
										updated[i] = { ...updated[i], label: e.target.value };
										onChange({ patterns: updated });
									}}
									placeholder="Label (e.g. SSN, Credit Card)"
									className={`${inputClass} flex-1`}
									disabled={readOnly}
								/>
								{!readOnly && (
									<button
										type="button"
										onClick={() => {
											if (patterns.length > 1) {
												onChange({
													patterns: patterns.filter(
														(_, j) => j !== i,
													),
												});
											} else {
												onChange({
													patterns: [{ label: "", regex: "" }],
												});
											}
										}}
										className="rounded p-1.5 text-[color:var(--color-text-muted)] transition-colors hover:bg-[color:var(--color-border)]/40 hover:text-red-400"
									>
										<X className="h-3.5 w-3.5" />
									</button>
								)}
							</div>
							<RegexInput
								value={pat.regex}
								onChange={(val) => {
									const updated = [...patterns];
									updated[i] = { ...updated[i], regex: val };
									onChange({ patterns: updated });
								}}
								placeholder="Regex (e.g. \\b\\d{3}-\\d{2}-\\d{4}\\b)"
								disabled={readOnly}
							/>
						</div>
					))}
					{!readOnly && (
						<button
							type="button"
							onClick={() =>
								onChange({ patterns: [...patterns, { label: "", regex: "" }] })
							}
							className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-600"
						>
							<Plus className="h-3 w-3" />
							Add pattern
						</button>
					)}
				</div>
			</div>

			<div className="grid gap-3 md:grid-cols-2">
				<div>
					<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
						Action
					</label>
					<Dropdown
						value={config.action}
						onChange={(v) => onChange({ action: v as FilterAction })}
						options={ACTION_OPTIONS}
						disabled={readOnly}
					/>
				</div>
				<div>
					<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
						Applies To
					</label>
					<Dropdown
						value={config.applies_to}
						onChange={(v) => onChange({ applies_to: v as FilterScope })}
						options={SCOPE_OPTIONS}
						disabled={readOnly}
					/>
				</div>
			</div>
			<div>
				<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
					Violation Message
				</label>
				<input
					type="text"
					value={config.message}
					onChange={(e) => onChange({ message: e.target.value })}
					placeholder="Custom message shown when rule triggers"
					className={inputClass}
					disabled={readOnly}
				/>
			</div>
		</div>
	);
}

// ---------------------------------------------------------------------------
// LLM Judge Editor
// ---------------------------------------------------------------------------

function LLMJudgeEditor({
	config,
	onChange,
	modelOptions,
	modelsLoading,
	readOnly,
}: {
	config: LLMJudgeItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	modelOptions: ModelOption[];
	modelsLoading: boolean;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<p className="text-xs text-[color:var(--color-text-muted)]/70">
				Select the LLM used to classify inputs for adversarial patterns. This provides deeper context-aware analysis beyond ML scanners. A fast, low-cost model is recommended.
			</p>
			<Dropdown
				value={config.judge_llm_config?.model_deployment_id ?? ""}
				onChange={(modelId) => {
					const opt = modelOptions.find((o) => o.value === modelId);
					if (opt?.model) {
						const m = opt.model as Record<string, string>;
						onChange({
							judge_llm_config: {
								model_deployment_id: m.id,
								provider: m.provider,
								model_name: m.model_name,
								display_name: m.display_name || m.name,
								temperature: 0.0,
							},
						});
					}
				}}
				options={modelOptions.map((o) => ({
					value: o.value,
					label: o.label,
					description: o.description,
				}))}
				placeholder={
					modelsLoading ? "Loading models..." : "Select judge model..."
				}
				disabled={readOnly || modelsLoading}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// General Safety Editor
// ---------------------------------------------------------------------------

function GeneralSafetyEditor({
	config,
	onChange,
	readOnly,
}: {
	config: GeneralSafetyItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-4">
			<div className="flex items-start justify-between rounded-lg bg-[color:var(--color-surface)]/40 px-3 py-2">
				<div className="flex-1">
					<label className="block text-xs font-medium text-[color:var(--color-text-primary)]">
						System Prompt Protection
					</label>
					<p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
						Wrap system prompt with anti-override anchoring (passive, no model)
					</p>
				</div>
				<Toggle
					checked={config.system_prompt_protection}
					onChange={(v) => onChange({ system_prompt_protection: v })}
					disabled={readOnly}
				/>
			</div>

			<div className="space-y-2">
				<h4 className="text-xs font-semibold text-[color:var(--color-text-primary)] capitalize tracking-wide">
					Length Limits
				</h4>
				<div className="grid gap-3 md:grid-cols-2">
					<NumberInput
						label="Max Input Length"
						description="Maximum input characters"
						value={config.max_input_length}
						onChange={(v) => onChange({ max_input_length: v })}
						min={100}
						max={500000}
						step={1000}
					/>
					<NumberInput
						label="Max Output Length"
						description="Maximum output characters"
						value={config.max_output_length}
						onChange={(v) => onChange({ max_output_length: v })}
						min={100}
						max={500000}
						step={1000}
					/>
				</div>
			</div>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Network Editor
// ---------------------------------------------------------------------------

function NetworkEditor({
	config,
	onChange,
	readOnly: _readOnly,
}: {
	config: NetworkItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<StringListEditor
				label="Allowed URL Patterns"
				description="Glob patterns. Empty = allow all external URLs."
				values={config.allowed_url_patterns}
				onChange={(v) => onChange({ allowed_url_patterns: v })}
				placeholder="e.g. https://api.example.com/*"
				monospace
			/>
			<StringListEditor
				label="Blocked URL Patterns"
				values={config.blocked_url_patterns}
				onChange={(v) => onChange({ blocked_url_patterns: v })}
				placeholder="e.g. *.internal.corp"
				monospace
			/>
			<StringListEditor
				label="Blocked IP Ranges"
				description="CIDR ranges for SSRF protection."
				values={config.blocked_ip_ranges}
				onChange={(v) => onChange({ blocked_ip_ranges: v })}
				placeholder="e.g. 192.168.0.0/16"
				monospace
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Database Editor
// ---------------------------------------------------------------------------

function DatabaseEditor({
	config,
	onChange,
	readOnly: _readOnly,
}: {
	config: DatabaseItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<StringListEditor
				label="Allowed SQL Operations"
				description="Only these SQL operations will be permitted."
				values={config.allowed_sql_operations}
				onChange={(v) => onChange({ allowed_sql_operations: v })}
				placeholder="e.g. SELECT"
			/>
			<StringListEditor
				label="Blocked Tables"
				values={config.blocked_tables}
				onChange={(v) => onChange({ blocked_tables: v })}
				placeholder="e.g. users"
			/>
			<NumberInput
				label="Max Query Rows"
				description="Maximum rows a query can return"
				value={config.max_query_rows}
				onChange={(v) => onChange({ max_query_rows: v })}
				min={1}
				max={100000}
				step={100}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Filesystem Editor
// ---------------------------------------------------------------------------

function FilesystemEditor({
	config,
	onChange,
	readOnly: _readOnly,
}: {
	config: FilesystemItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<StringListEditor
				label="Allowed File Extensions"
				description="Empty = allow all. Include the dot (e.g. .txt)."
				values={config.allowed_file_extensions}
				onChange={(v) => onChange({ allowed_file_extensions: v })}
				placeholder="e.g. .txt"
			/>
			<StringListEditor
				label="Blocked File Paths"
				values={config.blocked_file_paths}
				onChange={(v) => onChange({ blocked_file_paths: v })}
				placeholder="e.g. /etc/"
				monospace
			/>
			<NumberInput
				label="Max File Size (MB)"
				description="Maximum file size for writes"
				value={config.max_file_size_mb}
				onChange={(v) => onChange({ max_file_size_mb: v })}
				min={0.1}
				max={100}
				step={0.5}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Execution Limits Editor
// ---------------------------------------------------------------------------

const AZURE_CONTENT_FILTER_CATEGORIES = [
	"violence",
	"sexual",
	"self_harm",
	"hate_speech",
	"jailbreak",
	"protected_material",
];

function ProviderContentFilterEditor({
	config,
	onChange,
	readOnly,
}: {
	config: import("@/types/guardrail-items").ProviderContentFilterItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	const selected = new Set(config.categories.map((c) => c.toLowerCase()));
	const allSelected = selected.size === 0;

	const toggle = (cat: string) => {
		if (readOnly) return;
		if (selected.has(cat)) {
			onChange({
				categories: config.categories.filter(
					(c) => c.toLowerCase() !== cat,
				),
			});
		} else {
			onChange({ categories: [...config.categories, cat] });
		}
	};

	return (
		<div className="space-y-3">
			<p className="text-xs text-[color:var(--color-text-muted)]">
				Select which provider content filter categories to enforce. Leave
				empty to enforce all categories.
			</p>
			<div className="flex flex-wrap gap-2">
				{AZURE_CONTENT_FILTER_CATEGORIES.map((cat) => {
					const isActive = allSelected || selected.has(cat);
					return (
						<button
							key={cat}
							type="button"
							disabled={readOnly}
							onClick={() => toggle(cat)}
							className={`rounded-full border px-3 py-1 text-xs transition-colors ${
								isActive
									? "border-rose-500/50 bg-rose-500/20 text-rose-600"
									: "border-[color:var(--color-border)] text-[color:var(--color-text-muted)] hover:border-rose-500/30"
							}`}
						>
							{cat.replace(/_/g, " ")}
						</button>
					);
				})}
			</div>
			{allSelected && (
				<p className="text-xs text-[color:var(--color-text-muted)] italic">
					All categories are active. Click a category to filter to
					specific ones.
				</p>
			)}
		</div>
	);
}

// ---------------------------------------------------------------------------
// Execution Limits Editor
// ---------------------------------------------------------------------------

function ExecutionLimitsEditor({
	config,
	onChange,
	readOnly: _readOnly,
}: {
	config: ExecutionLimitsItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="grid gap-4 md:grid-cols-2">
			<NumberInput
				label="Max Tool Calls"
				description="Per execution"
				value={config.max_tool_calls_per_execution}
				onChange={(v) => onChange({ max_tool_calls_per_execution: v })}
				min={1}
				max={500}
				step={5}
			/>
			<NumberInput
				label="Tool Timeout (s)"
				description="Per individual call"
				value={config.tool_timeout_seconds}
				onChange={(v) => onChange({ tool_timeout_seconds: v })}
				min={5}
				max={600}
				step={5}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Token Budget Editor
// ---------------------------------------------------------------------------

function TokenBudgetEditor({
	config,
	onChange,
	readOnly: _readOnly,
}: {
	config: TokenBudgetItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	const warnDisplay = Math.round(config.warn_at_percentage * 100);
	return (
		<div className="space-y-4">
			<div>
				<p className="mb-2 text-xs text-[color:var(--color-text-muted)]">
					Set to 0 to leave unlimited. Cumulative across all LLM calls.
				</p>
				<div className="grid gap-3 md:grid-cols-3">
					<NumberInput
						label="Max Input Tokens"
						value={config.max_input_tokens_per_execution ?? 0}
						onChange={(v) =>
							onChange({
								max_input_tokens_per_execution: v || null,
							})
						}
						min={0}
						max={10000000}
						step={1000}
					/>
					<NumberInput
						label="Max Output Tokens"
						value={config.max_output_tokens_per_execution ?? 0}
						onChange={(v) =>
							onChange({
								max_output_tokens_per_execution: v || null,
							})
						}
						min={0}
						max={10000000}
						step={1000}
					/>
					<NumberInput
						label="Max Total Tokens"
						value={config.max_total_tokens_per_execution ?? 0}
						onChange={(v) =>
							onChange({
								max_total_tokens_per_execution: v || null,
							})
						}
						min={0}
						max={10000000}
						step={1000}
					/>
				</div>
			</div>
			<NumberInput
				label="Max LLM Calls"
				description="Maximum LLM invocations per execution"
				value={config.max_llm_calls_per_execution}
				onChange={(v) => onChange({ max_llm_calls_per_execution: v })}
				min={1}
				max={200}
				step={1}
			/>
			<div>
				<label className="mb-2 block text-sm font-medium text-[color:var(--color-text-secondary)]">
					Warn at {warnDisplay}% of budget
				</label>
				<div className="flex items-center gap-4">
					<input
						type="range"
						min="0"
						max="100"
						value={warnDisplay}
						onChange={(e) =>
							onChange({
								warn_at_percentage:
									Number.parseInt(e.target.value) / 100,
							})
						}
						className="flex-1"
						style={{
							background: `linear-gradient(to right, rgba(6,182,212,0.85) 0%, rgba(6,182,212,0.85) ${warnDisplay}%, rgba(55,65,81,0.6) ${warnDisplay}%, rgba(55,65,81,0.6) 100%)`,
							accentColor: "rgb(6,182,212)",
						}}
					/>
					<span className="w-12 text-center text-sm font-semibold text-cyan-600">
						{warnDisplay}%
					</span>
				</div>
			</div>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Adversarial Editor
// ---------------------------------------------------------------------------

function ThresholdSlider({
	label,
	value,
	onChange,
	disabled,
	defaultValue = 75,
}: {
	label: string;
	value: number;
	onChange: (v: number) => void;
	disabled: boolean;
	defaultValue?: number;
}) {
	const display = Math.round(value * 100);
	return (
		<div className="pl-3 pt-1 pb-1">
			<div className="flex items-center justify-between mb-1">
				<label className="text-[11px] text-[color:var(--color-text-muted)]">
					{label}
				</label>
				<span className="text-[11px] font-medium text-cyan-600">{display}%</span>
			</div>
			<input
				type="range"
				min="0"
				max="100"
				value={display}
				onChange={(e) => onChange(Number.parseInt(e.target.value) / 100)}
				className="w-full h-1.5"
				disabled={disabled}
				style={{
					background: `linear-gradient(to right, rgba(6,182,212,0.85) 0%, rgba(6,182,212,0.85) ${display}%, rgba(55,65,81,0.6) ${display}%, rgba(55,65,81,0.6) 100%)`,
					accentColor: "rgb(6,182,212)",
				}}
			/>
			<p className="text-[10px] text-[color:var(--color-text-muted)]/60 mt-0.5">
				Lower = more sensitive (more detections). Default: {defaultValue}%
			</p>
		</div>
	);
}

function AdversarialEditor({
	config,
	onChange,
	readOnly,
}: {
	config: AdversarialItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-2">
			<ScannerActionField
				label="Prompt Injection"
				description="Detect attempts to override system instructions"
				value={config.detect_prompt_injection as ScannerAction ?? "off"}
				onChange={(v) => onChange({ detect_prompt_injection: v })}
				disabled={readOnly}
			>
				{config.detect_prompt_injection && config.detect_prompt_injection !== "off" && (
					<ThresholdSlider
						label="Prompt Injection Threshold"
						value={config.prompt_injection_threshold ?? 0.75}
						onChange={(v) => onChange({ prompt_injection_threshold: v })}
						disabled={readOnly}
					/>
				)}
			</ScannerActionField>
			<ScannerActionField
				label="Jailbreak Attempts"
				description="Detect role bypass and format injection attacks"
				value={config.detect_jailbreak_attempts as ScannerAction ?? "off"}
				onChange={(v) => onChange({ detect_jailbreak_attempts: v })}
				disabled={readOnly}
			>
				{config.detect_jailbreak_attempts && config.detect_jailbreak_attempts !== "off" && (
					<ThresholdSlider
						label="Jailbreak Threshold"
						value={config.jailbreak_threshold ?? 0.75}
						onChange={(v) => onChange({ jailbreak_threshold: v })}
						disabled={readOnly}
					/>
				)}
			</ScannerActionField>
		</div>
	);
}

// ---------------------------------------------------------------------------
// PII Editor
// ---------------------------------------------------------------------------

const PII_ACTION_OPTIONS = [
	{ value: "block", label: "Block", description: "Reject input containing PII" },
	{ value: "warn", label: "Warn", description: "Log PII detection but allow through" },
	{ value: "anonymize", label: "Anonymize", description: "Replace PII via Vault round-trip" },
];

const PII_INFO: Record<string, string> = {
	block: "Input containing PII will be rejected and the workflow will not proceed.",
	warn: "PII will be detected and logged as a warning, but the original content is sent to the LLM unchanged.",
	anonymize:
		"PII is anonymized via Vault before reaching the LLM. The Deanonymize output scanner automatically restores original values in the response.",
};

function PIIEditor({
	config,
	onChange,
	readOnly,
}: {
	config: PIIItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	const action = config.anonymize_pii && config.anonymize_pii !== "off" ? config.anonymize_pii : "";
	const entityTypes = config.pii_entity_types ?? [];
	
	return (
		<div className="space-y-3">
			<div className="space-y-1.5">
				<label className="block text-xs font-medium text-[color:var(--color-text-primary)]">
					PII Detection Action
				</label>
				<Dropdown
					value={action}
					onChange={(v) => onChange({ anonymize_pii: (v || "off") as PIIAction })}
					options={PII_ACTION_OPTIONS}
					disabled={readOnly}
					placeholder="Select action..."
				/>
			</div>
			{action && PII_INFO[action] && (
				<div className="rounded-lg bg-blue-500/10 border border-blue-500/30 px-3 py-2 text-xs text-blue-400">
					{PII_INFO[action]}
				</div>
			)}
			{action && (
				<PIIEntitySelector
					value={entityTypes}
					onChange={(types) => onChange({ pii_entity_types: types })}
					disabled={readOnly}
				/>
			)}
			{action === "anonymize" && (
				<div className="flex items-start justify-between rounded-lg bg-[color:var(--color-surface)]/40 px-3 py-2">
					<div className="flex-1">
						<label className="block text-xs font-medium text-[color:var(--color-text-primary)]">
							Use Realistic Fake Data
						</label>
						<p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
							Replace PII with realistic fake values (e.g. fake names, addresses) instead of [REDACTED_*] placeholders
						</p>
					</div>
					<Toggle
						checked={config.use_faker ?? false}
						onChange={(v) => onChange({ use_faker: v })}
						disabled={readOnly}
					/>
				</div>
			)}
		</div>
	);
}

// ---------------------------------------------------------------------------
// Shared Scanner Action Field (Block / Warn dropdown with off state)
// ---------------------------------------------------------------------------

function ScannerActionField({
	label,
	description,
	value,
	onChange,
	disabled,
	children,
}: {
	label: string;
	description: string;
	value: ScannerAction;
	onChange: (v: ScannerAction) => void;
	disabled: boolean;
	children?: React.ReactNode;
}) {
	return (
		<div className="rounded-lg bg-[color:var(--color-surface)]/40 px-3 py-2">
			<div className="flex items-start justify-between gap-3">
				<div className="flex-1 min-w-0">
					<label className="block text-xs font-medium text-[color:var(--color-text-primary)]">
						{label}
					</label>
					<p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
						{description}
					</p>
				</div>
				<div className="shrink-0 w-32">
					<Dropdown
						value={value || "off"}
						onChange={(v) => onChange((v || "off") as ScannerAction)}
						options={SCANNER_ACTION_OPTIONS}
						disabled={disabled}
					/>
				</div>
			</div>
			{children}
		</div>
	);
}

// ---------------------------------------------------------------------------
// Input Content Editor
// ---------------------------------------------------------------------------

function InputContentEditor({
	config,
	onChange,
	readOnly,
}: {
	config: InputContentItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<ScannerActionField
				label="Toxicity Detection"
				description="Detect toxic, offensive, or harmful language in input"
				value={config.detect_toxicity}
				onChange={(v) => onChange({ detect_toxicity: v })}
				disabled={readOnly}
			>
				{config.detect_toxicity && config.detect_toxicity !== "off" && (
					<ThresholdSlider
						label="Toxicity Threshold"
						value={config.toxicity_threshold ?? 0.5}
						onChange={(v) => onChange({ toxicity_threshold: v })}
						disabled={readOnly}
						defaultValue={50}
					/>
				)}
			</ScannerActionField>
			<ScannerActionField
				label="Gibberish Detection"
				description="Detect nonsensical or garbled input"
				value={config.detect_gibberish}
				onChange={(v) => onChange({ detect_gibberish: v })}
				disabled={readOnly}
			/>
			<ScannerActionField
				label="Code Detection"
				description="Detect code injection in prompts"
				value={config.ban_code}
				onChange={(v) => onChange({ ban_code: v })}
				disabled={readOnly}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Input Policy Editor
// ---------------------------------------------------------------------------

function InputPolicyEditor({
	config,
	onChange,
	readOnly,
}: {
	config: InputPolicyItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<StringListEditor
				label="Banned Topics"
				description="Zero-shot classifier; empty = disabled"
				values={config.ban_topics ?? []}
				onChange={(v) => onChange({ ban_topics: v })}
				placeholder="Add topic..."
				readOnly={readOnly}
			/>
			<StringListEditor
				label="Allowed Languages (ISO 639-1)"
				description="Empty = allow all languages"
				values={config.allowed_languages ?? []}
				onChange={(v) => onChange({ allowed_languages: v })}
				placeholder="e.g. en, fr..."
				readOnly={readOnly}
			/>

			<div className="flex items-start justify-between rounded-lg bg-[color:var(--color-surface)]/40 px-3 py-2">
				<div className="flex-1">
					<label className="block text-xs font-medium text-[color:var(--color-text-primary)]">
						Token Limit
					</label>
					<p className="mt-0.5 text-xs text-[color:var(--color-text-muted)]">
						Maximum input token count per request
					</p>
				</div>
				<Toggle
					checked={config.max_input_tokens !== null && config.max_input_tokens !== undefined}
					onChange={(v) => onChange({ max_input_tokens: v ? 4096 : null })}
					disabled={readOnly}
				/>
			</div>
			{config.max_input_tokens !== null && config.max_input_tokens !== undefined && (
				<div className="pl-3">
					<NumberInput
						label="Max Input Tokens"
						description="Token count limit for input"
						value={config.max_input_tokens}
						onChange={(v) => onChange({ max_input_tokens: v })}
						min={1}
						max={1000000}
						step={256}
					/>
				</div>
			)}

			<ScannerActionField
				label="Secrets Detection"
				description="Detect API keys, passwords, and other secrets in input"
				value={config.detect_secrets}
				onChange={(v) => onChange({ detect_secrets: v })}
				disabled={readOnly}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Output Quality Editor
// ---------------------------------------------------------------------------

function OutputQualityEditor({
	config,
	onChange,
	readOnly,
}: {
	config: OutputQualityItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<ScannerActionField
				label="No-Refusal Detection"
				description="Detect when model refuses to answer appropriately"
				value={config.detect_refusal}
				onChange={(v) => onChange({ detect_refusal: v })}
				disabled={readOnly}
			/>
			<ScannerActionField
				label="Relevance Check"
				description="Flag output not relevant to the input prompt"
				value={config.check_relevance}
				onChange={(v) => onChange({ check_relevance: v })}
				disabled={readOnly}
			/>
			<ScannerActionField
				label="Factual Consistency"
				description="Flag output inconsistent with reference context"
				value={config.check_factual_consistency}
				onChange={(v) => onChange({ check_factual_consistency: v })}
				disabled={readOnly}
			/>
			<ScannerActionField
				label="Gibberish Detection"
				description="Flag nonsensical or garbled output"
				value={config.detect_gibberish}
				onChange={(v) => onChange({ detect_gibberish: v })}
				disabled={readOnly}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Output Content Editor
// ---------------------------------------------------------------------------

function OutputContentEditor({
	config,
	onChange,
	readOnly,
}: {
	config: OutputContentItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<ScannerActionField
				label="Toxicity Detection"
				description="Detect toxic or harmful language in model output"
				value={config.detect_toxicity}
				onChange={(v) => onChange({ detect_toxicity: v })}
				disabled={readOnly}
			>
				{config.detect_toxicity && config.detect_toxicity !== "off" && (
					<ThresholdSlider
						label="Toxicity Threshold"
						value={config.toxicity_threshold ?? 0.5}
						onChange={(v) => onChange({ toxicity_threshold: v })}
						disabled={readOnly}
						defaultValue={50}
					/>
				)}
			</ScannerActionField>
			<ScannerActionField
				label="Bias Detection"
				description="Flag gender, racial or political bias"
				value={config.detect_bias}
				onChange={(v) => onChange({ detect_bias: v })}
				disabled={readOnly}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Output Policy Editor
// ---------------------------------------------------------------------------

function OutputPolicyEditor({
	config,
	onChange,
	readOnly,
}: {
	config: OutputPolicyItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
}) {
	return (
		<div className="space-y-3">
			<ScannerActionField
				label="Sensitive Data Detection"
				description="Detect leaked sensitive information in model output"
				value={config.detect_sensitive_data}
				onChange={(v) => onChange({ detect_sensitive_data: v })}
				disabled={readOnly}
			/>

			<StringListEditor
				label="Banned Competitors"
				values={config.ban_competitors ?? []}
				onChange={(v) => onChange({ ban_competitors: v })}
				placeholder="e.g. CompetitorA..."
				readOnly={readOnly}
			/>
			<StringListEditor
				label="Banned Topics"
				values={config.ban_topics ?? []}
				onChange={(v) => onChange({ ban_topics: v })}
				placeholder="Add topic..."
				readOnly={readOnly}
			/>
			<StringListEditor
				label="Allowed Languages (ISO 639-1)"
				description="Empty = allow all languages"
				values={config.allowed_languages ?? []}
				onChange={(v) => onChange({ allowed_languages: v })}
				placeholder="e.g. en, fr..."
				readOnly={readOnly}
			/>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Custom Filter Editor
// ---------------------------------------------------------------------------

const FILTER_ACTION_OPTIONS = [
	{ value: "block", label: "Block", description: "Stop execution" },
	{ value: "warn", label: "Warn", description: "Log but continue" },
	{ value: "transform", label: "Transform", description: "Modify content" },
];

const FILTER_SCOPE_OPTIONS = [
	{ value: "both", label: "Both", description: "Ingress & egress" },
	{ value: "ingress", label: "Ingress", description: "Before LLM call" },
	{ value: "egress", label: "Egress", description: "After LLM response" },
];

function CustomFilterEditor({
	config,
	onChange,
	readOnly,
	modelOptions,
	modelsLoading,
}: {
	config: CustomFilterItemConfig;
	onChange: (p: Record<string, unknown>) => void;
	readOnly: boolean;
	modelOptions: ModelOption[];
	modelsLoading: boolean;
}) {
	return (
		<div className="space-y-3">
			<div className="grid gap-3 md:grid-cols-2">
				<div>
					<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
						Name
					</label>
					<input
						type="text"
						value={config.name}
						onChange={(e) => onChange({ name: e.target.value })}
						placeholder="Filter name"
						className={inputClass}
						disabled={readOnly}
					/>
				</div>
				<div>
					<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
						Priority
					</label>
					<input
						type="number"
						value={config.priority}
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
						className={inputClass}
						disabled={readOnly}
					/>
				</div>
			</div>
			<div className="grid gap-3 md:grid-cols-2">
				<div>
					<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
						Scope
					</label>
					<Dropdown
						value={config.scope}
						onChange={(v) => onChange({ scope: v })}
						options={FILTER_SCOPE_OPTIONS}
						disabled={readOnly}
					/>
				</div>
				<div>
					<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
						Action
					</label>
					<Dropdown
						value={config.action}
						onChange={(v) => onChange({ action: v })}
						options={FILTER_ACTION_OPTIONS}
						disabled={readOnly}
					/>
				</div>
			</div>
			<div>
				<label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">
					Violation Message
				</label>
				<input
					type="text"
					value={config.message}
					onChange={(e) => onChange({ message: e.target.value })}
					placeholder="Custom message shown when filter triggers"
					className={inputClass}
					disabled={readOnly}
				/>
			</div>

			{config.filter_type === "python_code" && (
				<PythonCodeFilterEditor
					pythonCode={config.python_code}
					onChange={(code) => onChange({ python_code: code })}
				/>
			)}
			{config.filter_type === "llm_judge" && (
				<LLMJudgeFilterEditor
					judgePrompt={config.judge_prompt}
					judgeLlmConfig={config.judge_llm_config}
					judgeThreshold={config.judge_threshold}
					onChange={(updates) => onChange(updates)}
					modelOptions={modelOptions}
					modelsLoading={modelsLoading}
				/>
			)}
			{config.filter_type === "declarative" && (
				<DeclarativeFilterEditor
					templateId={config.template_id}
					templateParams={config.template_params}
					judgeLlmConfig={config.judge_llm_config ?? null}
					onChange={(updates) => onChange(updates)}
					modelOptions={modelOptions}
					modelsLoading={modelsLoading}
				/>
			)}
		</div>
	);
}
