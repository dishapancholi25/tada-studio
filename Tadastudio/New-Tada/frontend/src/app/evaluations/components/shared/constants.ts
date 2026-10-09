import type { DropdownOption } from "@/components/ui/Dropdown";
import { ProviderLogo } from "@/components/ui/ProviderLogos";
import type { ModelDeploymentOption } from "@/lib/model-deployment-api";
import React from "react";

// ── Tab type ───────────────────────────────────────────────────────

export type TabId = "datasets" | "runs" | "settings";

export const TABS: { id: TabId; label: string }[] = [
	{ id: "datasets", label: "Datasets" },
	{ id: "runs", label: "Runs" },
	{ id: "settings", label: "Settings" },
];

// ── Judge criteria presets ─────────────────────────────────────────

export interface CriterionRow {
	key: string;
	value: string;
}

export const JUDGE_CRITERIA_PRESETS: { label: string; criteria: CriterionRow[] }[] = [
	{
		label: "General Quality",
		criteria: [
			{ key: "correctness", value: "Output is factually accurate and free of errors" },
			{ key: "completeness", value: "Output covers all key points and required information" },
			{ key: "coherence", value: "Output is well-structured and logically consistent" },
			{ key: "relevance", value: "Output stays on topic and addresses the task" },
		],
	},
	{
		label: "Accuracy & Precision",
		criteria: [
			{ key: "factual_accuracy", value: "All facts and data points are correct" },
			{ key: "format_compliance", value: "Output follows the expected format and structure" },
			{ key: "numerical_precision", value: "Numbers, calculations, and quantities are exact" },
		],
	},
	{
		label: "Customer Support",
		criteria: [
			{ key: "helpfulness", value: "Response directly addresses the customer's issue" },
			{ key: "tone", value: "Response is professional, empathetic, and courteous" },
			{ key: "actionability", value: "Response includes clear next steps or resolution" },
			{ key: "policy_compliance", value: "Response adheres to company policies and guidelines" },
		],
	},
	{
		label: "Safety & Guardrails",
		criteria: [
			{ key: "harmlessness", value: "Output contains no harmful, offensive, or dangerous content" },
			{ key: "pii_protection", value: "Output does not expose personal or sensitive information" },
			{ key: "boundary_adherence", value: "Output stays within the defined scope and does not hallucinate" },
		],
	},
	{
		label: "RAG / Knowledge",
		criteria: [
			{ key: "grounding", value: "Output is grounded in the retrieved documents and sources" },
			{ key: "attribution", value: "Claims are properly attributed to source material" },
			{ key: "no_hallucination", value: "Output does not fabricate facts beyond what sources support" },
			{ key: "completeness", value: "Output uses all relevant information from retrieved context" },
		],
	},
];

// ── Shared dropdown trigger styling (light form field) ────────────

/** Trigger styling for light/form Dropdowns (slate border, white surface, orange hover). */
export const FORM_DROPDOWN_TRIGGER_CLASS =
	"border border-slate-200 bg-white hover:bg-white hover:border-orange-400 text-slate-900";

// ── Model dropdown helper ──────────────────────────────────────────

export function buildModelDropdownOptions(deployments: ModelDeploymentOption[]): DropdownOption[] {
	return deployments
		.filter((d) => d.model_type === "llm" && d.is_active)
		.map((d) => ({
			value: d.id,
			label: d.display_name || d.name,
			description: `${d.provider} \u2022 ${d.model_name}`,
			icon: React.createElement(ProviderLogo, { provider: d.provider, className: "h-5 w-5" }),
		}));
}

// ── Rerun name helper ──────────────────────────────────────────────

export function nextRerunName(name: string | undefined | null): string | undefined {
	if (!name) return undefined;
	const numbered = name.match(/^(.*\(rerun #)(\d+)\)$/);
	if (numbered) return `${numbered[1]}${Number(numbered[2]) + 1})`;
	if (name.endsWith("(rerun)")) return `${name.slice(0, -7)}(rerun #2)`;
	return `${name} (rerun #1)`;
}

// ── Environment options ────────────────────────────────────────────

export const ENVIRONMENT_OPTIONS = [
	{ value: "dev", label: "Development" },
	{ value: "uat", label: "UAT" },
	{ value: "prod", label: "Production" },
] as const;

// ── Modal tab type ─────────────────────────────────────────────────

export type ModalTab = "cases" | "manual" | "ai" | "import-executions" | "export-import";

export const MAX_CAP = 200;
