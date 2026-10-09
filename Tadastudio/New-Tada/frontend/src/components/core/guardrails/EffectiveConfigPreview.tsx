"use client";

import type {
	DecomposedGuardrail,
	DecomposedPipelineEntry,
} from "@/types/guardrail-policies";
import * as guardrailsApi from "@/lib/guardrails-api";
import {
	ChevronDown,
	ChevronRight,
	Eye,
	Loader2,
	Shield,
	ShieldAlert,
	ShieldCheck,
	ShieldOff,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface EffectiveConfigPreviewProps {
	workflowId?: string;
	nodeId?: string;
	refreshTrigger?: number;
	appearance?: "default" | "light";
}

const ENFORCEMENT_ICONS: Record<string, typeof ShieldAlert> = {
	enforce: ShieldAlert,
	audit: ShieldCheck,
	disabled: ShieldOff,
};

const ENFORCEMENT_COLORS: Record<string, string> = {
	enforce: "text-red-400",
	audit: "text-yellow-400",
	disabled: "text-slate-400",
};

const GUARDRAIL_LABELS: Record<string, string> = {
	prompt_injection: "Prompt Injection Detection",
	jailbreak_detection: "Jailbreak Detection",
	toxicity_detection: "Toxicity Detection",
	pii_anonymization: "PII Anonymization",
	secret_detection: "Secret Detection",
	gibberish_detection: "Gibberish Detection",
	code_detection: "Code Detection",
	topic_ban: "Topic Ban",
	language_restriction: "Language Restriction",
	token_limit: "Token Limit",
	system_prompt_protection: "System Prompt Protection",
	input_length_limit: "Input Length Limit",
	output_length_limit: "Output Length Limit",
	llm_judge: "LLM Judge",
	pattern_rule: "Pattern Rule",
	output_toxicity: "Output Toxicity",
	output_refusal: "Output Refusal Detection",
	output_sensitive_data: "Output Sensitive Data",
	output_relevance: "Output Relevance Check",
	output_gibberish: "Output Gibberish Detection",
	output_bias: "Output Bias Detection",
	output_factual_consistency: "Factual Consistency Check",
	output_topic_ban: "Output Topic Ban",
	output_language_restriction: "Output Language Restriction",
	output_competitor_ban: "Competitor Mention Ban",
	tool_network_policy: "Network Access Policy",
	tool_database_policy: "Database Access Policy",
	tool_filesystem_policy: "Filesystem Access Policy",
	tool_execution_limits: "Tool Execution Limits",
	token_budget: "Token Budget",
	provider_content_filter: "Provider Content Filter",
	custom_filter: "Custom Filter",
};

const ACTION_COLORS: Record<string, string> = {
	block: "bg-red-500/15 text-red-400 border-red-500/25",
	warn: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
	redact: "bg-purple-500/15 text-purple-400 border-purple-500/25",
	transform: "bg-blue-500/15 text-blue-400 border-blue-500/25",
	audit: "bg-yellow-500/15 text-yellow-400 border-yellow-500/25",
};

const ACTION_COLORS_LIGHT: Record<string, string> = {
	block: "border-red-200 bg-red-50 text-red-800",
	warn: "border-amber-200 bg-amber-50 text-amber-900",
	redact: "border-purple-200 bg-purple-50 text-purple-900",
	transform: "border-blue-200 bg-blue-50 text-blue-900",
	audit: "border-amber-200 bg-amber-50 text-amber-900",
};

export default function EffectiveConfigPreview({
	workflowId,
	nodeId,
	refreshTrigger,
	appearance = "default",
}: EffectiveConfigPreviewProps) {
	const isLight = appearance === "light";
	const [expanded, setExpanded] = useState(false);
	const [loading, setLoading] = useState(false);
	const [pipelineEntries, setPipelineEntries] = useState<
		DecomposedPipelineEntry[]
	>([]);

	const fetchEffectiveConfig = useCallback(async () => {
		if (!expanded) return;
		setLoading(true);
		try {
			const result = await guardrailsApi.resolveConfig({
				workflow_id: workflowId,
				node_id: nodeId,
			});
			setPipelineEntries(result.decomposed_pipeline || []);
		} catch {
			setPipelineEntries([]);
		} finally {
			setLoading(false);
		}
	}, [workflowId, nodeId, expanded]);

	useEffect(() => {
		fetchEffectiveConfig();
	}, [fetchEffectiveConfig, refreshTrigger]);

	const activePolicies = pipelineEntries.filter(
		(p) => p.enabled && p.enforcement_mode !== "disabled",
	);
	const totalGuardrails = activePolicies.reduce(
		(sum, p) => sum + p.guardrails.length,
		0,
	);

	return (
		<div className="space-y-2">
			<button
				type="button"
				onClick={() => setExpanded(!expanded)}
				className={
					isLight
						? "flex w-full items-center gap-2 text-sm font-medium text-slate-700 transition-colors hover:text-slate-900"
						: "flex w-full items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)] transition-colors hover:text-[color:var(--color-text-primary)]"
				}
			>
				{expanded ? (
					<ChevronDown className="h-4 w-4" />
				) : (
					<ChevronRight className="h-4 w-4" />
				)}
				<Eye
					className={`h-4 w-4 ${isLight ? "text-blue-600" : "text-blue-400"}`}
				/>
				Effective Guardrails Preview
			</button>

			{expanded && (
				<div className="ml-6 space-y-3">
					{loading ? (
						<div
							className={
								isLight
									? "flex items-center justify-center py-4 text-slate-600"
									: "flex items-center justify-center py-4 text-[color:var(--color-text-secondary)]"
							}
						>
							<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
							<span className="ml-2 text-xs">Resolving...</span>
						</div>
					) : activePolicies.length === 0 ? (
						<div
							className={
								isLight
									? "rounded-[4px] border border-dashed border-slate-300 px-4 py-4 text-center text-sm text-slate-600"
									: "rounded-lg border border-dashed border-[color:var(--color-border)] px-4 py-4 text-center text-sm text-[color:var(--color-text-tertiary)]"
							}
						>
							No guardrail policies apply to this target
						</div>
					) : (
						<>
							<div
								className={
									isLight
										? "flex items-center gap-2 rounded-[4px] border border-slate-200 bg-slate-50 px-3 py-2.5"
										: "flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] px-3 py-2.5"
								}
							>
								<Shield
									className={`h-4 w-4 ${isLight ? "text-blue-600" : "text-blue-400"}`}
								/>
								<span
									className={
										isLight
											? "text-xs text-slate-700"
											: "text-xs text-[color:var(--color-text-secondary)]"
									}
								>
									{activePolicies.length}{" "}
									{activePolicies.length === 1
										? "policy"
										: "policies"}{" "}
									active &middot; {totalGuardrails} guardrail
									{totalGuardrails !== 1 ? "s" : ""}
								</span>
							</div>

							{activePolicies.map((entry, idx) => (
								<PolicySection
									key={`${entry.policy_id}-${idx}`}
									entry={entry}
									isLight={isLight}
								/>
							))}
						</>
					)}
				</div>
			)}
		</div>
	);
}

/* ── Section components ────────────────────────────────────── */

function PolicySection({
	entry,
	isLight,
}: {
	entry: DecomposedPipelineEntry;
	isLight: boolean;
}) {
	const Icon =
		ENFORCEMENT_ICONS[entry.enforcement_mode] || ShieldCheck;
	const color = isLight
		? entry.enforcement_mode === "enforce"
			? "text-red-600"
			: entry.enforcement_mode === "audit"
				? "text-amber-700"
				: "text-slate-400"
		: ENFORCEMENT_COLORS[entry.enforcement_mode] || "text-slate-500";

	const headerBg = isLight ? "bg-slate-100" : "bg-[color:var(--color-bg-tertiary)]";

	return (
		<div
			className={
				isLight
					? "rounded-[4px] border border-slate-200 bg-white p-3 shadow-sm"
					: "rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] p-3"
			}
		>
			<div className="mb-2 flex items-center gap-2">
				<Icon className={`h-3.5 w-3.5 flex-shrink-0 ${color}`} />
				<span
					className={
						isLight
							? "text-xs font-semibold text-slate-900"
							: "text-xs font-semibold text-[color:var(--color-text-primary)]"
					}
				>
					{entry.policy_name || "Unnamed Policy"}
				</span>
				<span
					className={`ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium capitalize ${color} ${headerBg}`}
				>
					{entry.enforcement_mode}
				</span>
			</div>

			{entry.guardrails.length === 0 ? (
				<div
					className={
						isLight
							? "text-xs italic text-slate-500"
							: "text-xs italic text-[color:var(--color-text-tertiary)]"
					}
				>
					No active guardrails
				</div>
			) : (
				<div className="space-y-1">
					{entry.guardrails.map((g, i) => (
						<GuardrailRow
							key={`${g.guardrail_name}-${i}`}
							guardrail={g}
							isLight={isLight}
						/>
					))}
				</div>
			)}
		</div>
	);
}

function GuardrailRow({
	guardrail,
	isLight,
}: {
	guardrail: DecomposedGuardrail;
	isLight: boolean;
}) {
	const label =
		GUARDRAIL_LABELS[guardrail.guardrail_name] ||
		formatGuardrailName(guardrail.guardrail_name);
	const action = guardrail.guardrail_config.action as string | undefined;
	const name = guardrail.guardrail_config.name as string | undefined;

	const actionClass = isLight
		? ACTION_COLORS_LIGHT[action || ""] ||
			"border-slate-200 bg-slate-50 text-slate-700"
		: ACTION_COLORS[action || ""] ||
			"border-slate-200 bg-slate-50 text-slate-500";

	return (
		<div
			className={
				isLight
					? "flex items-center justify-between gap-2 rounded-[4px] border border-slate-100 bg-slate-50 px-2.5 py-1.5"
					: "flex items-center justify-between gap-2 rounded bg-[color:var(--color-bg-tertiary)] px-2.5 py-1.5"
			}
		>
			<div className="min-w-0 flex-1">
				<span
					className={
						isLight
							? "text-xs font-medium text-slate-900"
							: "text-xs font-medium text-[color:var(--color-text-primary)]"
					}
				>
					{guardrail.guardrail_name === "pattern_rule" && name
						? name
						: guardrail.guardrail_name === "custom_filter" && name
							? name
							: label}
				</span>
			</div>
			{action && (
				<span
					className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium ${actionClass}`}
				>
					{action}
				</span>
			)}
		</div>
	);
}

function formatGuardrailName(name: string): string {
	return name
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase());
}
