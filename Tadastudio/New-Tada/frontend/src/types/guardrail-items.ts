/**
 * Guardrail item types for the builder UI.
 *
 * Each GuardrailItem represents a single, discrete guardrail the user has
 * added to a policy.  The flat item list is the UI's internal representation;
 * it is converted to/from the nested GuardrailsConfig for persistence.
 */

import type {
	CustomFilterAction,
	CustomFilterScope,
	FilterAction,
	FilterScope,
	JudgeLLMConfig,
	PIIAction,
	PatternEntry,
	ScannerAction,
} from "./guardrails";

export type { ScannerAction } from "./guardrails";

// ---------------------------------------------------------------------------
// Item type discriminator
// ---------------------------------------------------------------------------

export type GuardrailItemType =
	// Data Protection — one item per pattern rule
	| "pattern_rule"
	// LLM Judge — opt-in LLM-based adversarial classification
	| "llm_judge"
	// General Safety — system prompt protection + length limits
	| "general_safety"
	// LLM Guard input scanners — split by concern
	| "llm_guard_adversarial"
	| "llm_guard_pii"
	| "llm_guard_input_content"
	| "llm_guard_input_policy"
	// LLM Guard output scanners — split by concern
	| "llm_guard_output_quality"
	| "llm_guard_output_content"
	| "llm_guard_output_policy"
	// Tool Restrictions — split from ToolCallPolicy
	| "tool_network"
	| "tool_database"
	| "tool_filesystem"
	| "tool_execution_limits"
	// Provider Content Filters
	| "provider_content_filter"
	// Cost Controls
	| "token_budget"
	// Custom Filters — one item per filter instance
	| "custom_filter";

// ---------------------------------------------------------------------------
// Per-type config shapes
// ---------------------------------------------------------------------------

export interface PatternRuleItemConfig {
	name: string;
	patterns: PatternEntry[];
	action: FilterAction;
	applies_to: FilterScope;
	message: string;
	preset_id: string;
}

export interface LLMJudgeItemConfig {
	judge_llm_config: JudgeLLMConfig | null;
}

export interface GeneralSafetyItemConfig {
	system_prompt_protection: boolean;
	max_input_length: number;
	max_output_length: number;
}

export interface AdversarialItemConfig {
	detect_prompt_injection: ScannerAction;
	detect_jailbreak_attempts: ScannerAction;
	prompt_injection_threshold: number;
	jailbreak_threshold: number;
}

export interface PIIItemConfig {
	anonymize_pii: PIIAction;
	use_faker: boolean;
	pii_entity_types: string[];  // Empty array = all types
}

export interface InputContentItemConfig {
	detect_toxicity: ScannerAction;
	detect_gibberish: ScannerAction;
	ban_code: ScannerAction;
	toxicity_threshold: number;
}

export interface InputPolicyItemConfig {
	ban_topics: string[];
	allowed_languages: string[];
	max_input_tokens: number | null;
	detect_secrets: ScannerAction;
}

export interface OutputQualityItemConfig {
	detect_refusal: ScannerAction;
	check_relevance: ScannerAction;
	check_factual_consistency: ScannerAction;
	detect_gibberish: ScannerAction;
}

export interface OutputContentItemConfig {
	detect_toxicity: ScannerAction;
	detect_bias: ScannerAction;
	toxicity_threshold: number;
}

export interface OutputPolicyItemConfig {
	detect_sensitive_data: ScannerAction;
	ban_competitors: string[];
	ban_topics: string[];
	allowed_languages: string[];
}

export interface NetworkItemConfig {
	allowed_url_patterns: string[];
	blocked_url_patterns: string[];
	blocked_ip_ranges: string[];
}

export interface DatabaseItemConfig {
	allowed_sql_operations: string[];
	blocked_tables: string[];
	max_query_rows: number;
}

export interface FilesystemItemConfig {
	allowed_file_extensions: string[];
	blocked_file_paths: string[];
	max_file_size_mb: number;
}

export interface ExecutionLimitsItemConfig {
	max_tool_calls_per_execution: number;
	tool_timeout_seconds: number;
}

export interface TokenBudgetItemConfig {
	max_input_tokens_per_execution: number | null;
	max_output_tokens_per_execution: number | null;
	max_total_tokens_per_execution: number | null;
	max_llm_calls_per_execution: number;
	warn_at_percentage: number;
}

export interface ProviderContentFilterItemConfig {
	categories: string[];
}

export interface CustomFilterItemConfig {
	filter_id: string;
	name: string;
	filter_type: "python_code" | "llm_judge" | "declarative";
	action: CustomFilterAction;
	scope: CustomFilterScope;
	enabled: boolean;
	priority: number;
	python_code: string;
	judge_prompt: string;
	judge_llm_config: JudgeLLMConfig | null;
	judge_threshold: number;
	template_id: string;
	template_params: Record<string, unknown>;
	message: string;
}

// ---------------------------------------------------------------------------
// Discriminated union
// ---------------------------------------------------------------------------

interface BaseItem<T extends GuardrailItemType, C> {
	id: string;
	type: T;
	config: C;
}

export type GuardrailItem =
	| BaseItem<"pattern_rule", PatternRuleItemConfig>
	| BaseItem<"llm_judge", LLMJudgeItemConfig>
	| BaseItem<"general_safety", GeneralSafetyItemConfig>
	| BaseItem<"llm_guard_adversarial", AdversarialItemConfig>
	| BaseItem<"llm_guard_pii", PIIItemConfig>
	| BaseItem<"llm_guard_input_content", InputContentItemConfig>
	| BaseItem<"llm_guard_input_policy", InputPolicyItemConfig>
	| BaseItem<"llm_guard_output_quality", OutputQualityItemConfig>
	| BaseItem<"llm_guard_output_content", OutputContentItemConfig>
	| BaseItem<"llm_guard_output_policy", OutputPolicyItemConfig>
	| BaseItem<"tool_network", NetworkItemConfig>
	| BaseItem<"tool_database", DatabaseItemConfig>
	| BaseItem<"tool_filesystem", FilesystemItemConfig>
	| BaseItem<"tool_execution_limits", ExecutionLimitsItemConfig>
	| BaseItem<"provider_content_filter", ProviderContentFilterItemConfig>
	| BaseItem<"token_budget", TokenBudgetItemConfig>
	| BaseItem<"custom_filter", CustomFilterItemConfig>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** LLM Judge item types share a judge config */
export const LLM_JUDGE_ITEM_TYPES: GuardrailItemType[] = [
	"llm_judge",
];

export function isLLMJudgeType(t: GuardrailItemType): boolean {
	return LLM_JUDGE_ITEM_TYPES.includes(t);
}

/** Singleton types — can only appear once in a policy */
export const SINGLETON_TYPES: GuardrailItemType[] = [
	"llm_judge",
	"general_safety",
	"llm_guard_adversarial",
	"llm_guard_pii",
	"llm_guard_input_content",
	"llm_guard_input_policy",
	"llm_guard_output_quality",
	"llm_guard_output_content",
	"llm_guard_output_policy",
	"provider_content_filter",
	"tool_network",
	"tool_database",
	"tool_filesystem",
	"tool_execution_limits",
	"token_budget",
];

let _nextId = 0;
export function generateItemId(): string {
	_nextId++;
	return `gi-${Date.now()}-${_nextId}-${Math.random().toString(36).slice(2, 7)}`;
}
