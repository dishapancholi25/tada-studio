/**
 * Static catalog of available guardrail items and quick-start bundles.
 *
 * Each CatalogEntry describes one guardrail type the user can add.
 * Bundles group multiple entries for one-click setup.
 */

import {
	Brain,
	Code,
	Coins,
	Database,
	FileText,
	Gavel,
	Globe,
	type LucideIcon,
	MessageSquare,
	Puzzle,
	ScanSearch,
	Shield,
	ShieldAlert,
	ShieldBan,
	ShieldCheck,
	Timer,
	Zap,
} from "lucide-react";
import type { GuardrailItemType } from "@/types/guardrail-items";
import { FILTER_TEMPLATES } from "@/types/guardrails";

// ---------------------------------------------------------------------------
// Entry / Category / Bundle types
// ---------------------------------------------------------------------------

export interface CatalogEntry {
	type: GuardrailItemType;
	label: string;
	description: string;
	icon: LucideIcon;
	/** Can only be added once to a policy */
	singleton: boolean;
	/** For custom_filter declarative templates */
	templateId?: string;
	/** Feature not yet implemented — show as disabled with a "Coming soon" badge in the UI instead of being addable */
	comingSoon?: boolean;
}

export interface CatalogCategory {
	id: string;
	label: string;
	icon: LucideIcon;
	entries: CatalogEntry[];
}

export interface CatalogBundle {
	id: string;
	label: string;
	description: string;
	icon: LucideIcon;
	/** Which catalog entries to add (by type + templateId) */
	items: Array<{ type: GuardrailItemType; templateId?: string }>;
}

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export const CATALOG_CATEGORIES: CatalogCategory[] = [
	{
		id: "data_protection",
		label: "Data Protection",
		icon: ScanSearch,
		entries: [
			{
				type: "pattern_rule",
				label: "Custom Pattern Rule",
				description: "Write a custom regex pattern to detect domain-specific content",
				icon: ScanSearch,
				singleton: false,
			},
		],
	},
	{
		id: "input_safety",
		label: "Input Safety",
		icon: ShieldAlert,
		entries: [
			{
				type: "llm_guard_adversarial",
				label: "Adversarial Detection",
				description: "Prompt injection and jailbreak detection using ML classifiers",
				icon: ShieldAlert,
				singleton: true,
			},
			{
				type: "llm_guard_pii",
				label: "PII Detection",
				description: "Detect personally identifiable information with block, warn, or anonymize actions",
				icon: ScanSearch,
				singleton: true,
			},
			{
				type: "llm_guard_input_content",
				label: "Input Content Safety",
				description: "Toxicity, gibberish and code injection detection",
				icon: Brain,
				singleton: true,
			},
			{
				type: "llm_guard_input_policy",
				label: "Input Policy Controls",
				description: "Topic ban, language filter, token limit and secrets detection",
				icon: Shield,
				singleton: true,
			},
			{
				type: "llm_judge",
				label: "LLM Judge",
				description: "LLM-based adversarial content classification (requires model)",
				icon: Gavel,
				singleton: true,
			},
			{
				type: "general_safety",
				label: "General Safety",
				description: "System prompt protection and input/output length limits",
				icon: Shield,
				singleton: true,
			},
		],
	},
	{
		id: "output_safety",
		label: "Output Safety",
		icon: ShieldCheck,
		entries: [
			{
				type: "llm_guard_output_quality",
				label: "Response Quality",
				description: "Detect refusals, hallucinations and irrelevant responses",
				icon: ShieldCheck,
				singleton: true,
			},
			{
				type: "llm_guard_output_content",
				label: "Output Content Safety",
				description: "Toxicity and bias detection on LLM responses",
				icon: ShieldBan,
				singleton: true,
			},
			{
				type: "llm_guard_output_policy",
				label: "Output Policy Controls",
				description: "Sensitive data, competitor mentions, topic and language enforcement",
				icon: ShieldAlert,
				singleton: true,
			},
		],
	},
	{
		id: "provider_safety",
		label: "Provider Safety",
		icon: ShieldAlert,
		entries: [
			{
				type: "provider_content_filter",
				label: "Provider Content Filter",
				description:
					"Detect and log Azure/OpenAI content safety filter violations",
				icon: ShieldAlert,
				singleton: true,
				// Coming soon: keep implementation intact, but disable adding this guardrail
				// from the UI and show a "Coming soon" badge until this feature is released.
				comingSoon: true,
			},
		],
	},
	{
		id: "tool_restrictions",
		label: "Tool Restrictions",
		icon: Globe,
		entries: [
			// Coming soon: Tool Restrictions entries below are fully implemented, but are
			// disabled and marked "Coming soon" in the catalog UI until this feature is released.
			{
				type: "tool_network",
				label: "Network & SSRF Protection",
				description: "URL allowlist/blocklist and IP range restrictions",
				icon: Globe,
				singleton: true,
				comingSoon: true,
			},
			{
				type: "tool_database",
				label: "Database Restrictions",
				description: "SQL operation and table access controls",
				icon: Database,
				singleton: true,
				comingSoon: true,
			},
			{
				type: "tool_filesystem",
				label: "File System Restrictions",
				description: "File extension, path, and size controls",
				icon: FileText,
				singleton: true,
				comingSoon: true,
			},
			{
				type: "tool_execution_limits",
				label: "Execution Limits",
				description: "Max tool calls and per-call timeout",
				icon: Timer,
				singleton: true,
				comingSoon: true,
			},
		],
	},
	{
		id: "cost_controls",
		label: "Cost Controls",
		icon: Coins,
		entries: [
			{
				type: "token_budget",
				label: "Token Budget & Call Limits",
				description: "Token limits, LLM call caps, and warning thresholds",
				icon: Coins,
				singleton: true,
			},
		],
	},
	{
		id: "custom_filters",
		label: "Custom Filters",
		icon: Code,
		entries: [
			{
				type: "custom_filter",
				label: "Python Code Filter",
				description: "Write a custom filter function in Python",
				icon: Code,
				singleton: false,
				templateId: undefined,
			},
			{
				type: "custom_filter",
				label: "LLM Judge Filter",
				description: "Natural language policy evaluated by an LLM",
				icon: MessageSquare,
				singleton: false,
				templateId: undefined,
			},
			...FILTER_TEMPLATES.map((t) => ({
				type: "custom_filter" as const,
				label: t.name,
				description: t.description,
				icon: Puzzle,
				singleton: false,
				templateId: t.id,
			})),
		],
	},
];

// ---------------------------------------------------------------------------
// Quick-start bundles
// ---------------------------------------------------------------------------

export const CATALOG_BUNDLES: CatalogBundle[] = [
	{
		id: "llm_safety",
		label: "LLM Safety",
		description: "Input/output scanners, general safety & token budget",
		icon: Brain,
		items: [
			{ type: "llm_guard_adversarial" },
			{ type: "llm_guard_input_content" },
			{ type: "llm_guard_output_content" },
			{ type: "general_safety" },
			{ type: "token_budget" },
		],
	},
	{
		id: "compliance_kit",
		label: "Compliance Kit",
		description: "Full scanner suite, LLM judge, general safety & cost controls",
		icon: ShieldCheck,
		items: [
			{ type: "llm_guard_adversarial" },
			{ type: "llm_guard_pii" },
			{ type: "llm_guard_input_content" },
			{ type: "llm_guard_input_policy" },
			{ type: "llm_guard_output_quality" },
			{ type: "llm_guard_output_content" },
			{ type: "llm_guard_output_policy" },
			{ type: "llm_judge" },
			{ type: "general_safety" },
			{ type: "token_budget" },
		],
	},
	{
		id: "ai_safety_suite",
		label: "AI Safety Suite",
		description: "All LLM Guard input and output scanners",
		icon: Zap,
		items: [
			{ type: "llm_guard_adversarial" },
			{ type: "llm_guard_pii" },
			{ type: "llm_guard_input_content" },
			{ type: "llm_guard_input_policy" },
			{ type: "llm_guard_output_quality" },
			{ type: "llm_guard_output_content" },
			{ type: "llm_guard_output_policy" },
		],
	},
];
