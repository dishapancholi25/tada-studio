/**
 * Guardrails configuration types for agent safety policies.
 *
 * Mirrors the backend dataclasses in backend/models/workflow/configs/guardrails.py.
 * Supports content filtering, tool call policies, token budgets, and behavioral safety.
 */

/** How violations are handled */
export type EnforcementMode = "enforce" | "audit" | "disabled";

/** What to do when a pattern rule matches */
export type FilterAction = "block" | "warn" | "redact";

/** PII detection action */
export type PIIAction = "off" | "block" | "warn" | "anonymize";

/** Scanner action for block/warn toggles */
export type ScannerAction = "off" | "block" | "warn";

/** Where a pattern rule applies */
export type FilterScope = "input" | "output" | "both";

/**
 * A single labeled regex pattern within a pattern rule.
 */
export interface PatternEntry {
	/** Human-readable label describing what this pattern detects */
	label: string;
	/** Regex pattern to match against content */
	regex: string;
}

/**
 * A single pattern matching rule for data loss prevention.
 */
export interface PatternRule {
	/** Human-readable rule name */
	name: string;
	/** Short description for the preset picker (optional) */
	description?: string;
	/** Labeled regex patterns to match against content */
	patterns: PatternEntry[];
	/** What to do on match */
	action: FilterAction;
	/** Where to apply the rule */
	applies_to: FilterScope;
	/** Custom message shown when rule triggers */
	message: string;
	/** If this rule originated from a built-in preset, its ID */
	preset_id: string;
}

/**
 * Policy for controlling tool behavior — network, database, and file restrictions.
 */
export interface ToolCallPolicy {
	/** Glob patterns for allowed URLs (empty = allow all) */
	allowed_url_patterns: string[];
	/** Glob patterns for blocked URLs */
	blocked_url_patterns: string[];
	/** CIDR ranges blocked for SSRF protection */
	blocked_ip_ranges: string[];
	/** Allowed SQL operations (e.g. ["SELECT"]) */
	allowed_sql_operations: string[];
	/** Table names that cannot be queried */
	blocked_tables: string[];
	/** Maximum rows a query can return */
	max_query_rows: number;
	/** Allowed file extensions for writes (empty = allow all) */
	allowed_file_extensions: string[];
	/** Path patterns blocked for file writes */
	blocked_file_paths: string[];
	/** Maximum file size in megabytes */
	max_file_size_mb: number;
	/** Total tool call limit per execution */
	max_tool_calls_per_execution: number;
	/** Timeout for individual tool calls in seconds */
	tool_timeout_seconds: number;
}

/**
 * Token and cost budget limits per execution.
 */
export interface TokenBudget {
	/** Max input tokens across all LLM calls (null = unlimited) */
	max_input_tokens_per_execution: number | null;
	/** Max output tokens across all LLM calls (null = unlimited) */
	max_output_tokens_per_execution: number | null;
	/** Max total tokens across all LLM calls (null = unlimited) */
	max_total_tokens_per_execution: number | null;
	/** Max number of LLM invocations */
	max_llm_calls_per_execution: number;
	/** Emit warning when usage hits this fraction (0.0-1.0) */
	warn_at_percentage: number;
}

/**
 * LLM configuration for the behavioral judge model.
 * Uses model_deployment_id for selection, same as ReviewerLLMConfig.
 */
export interface JudgeLLMConfig {
	/** Model deployment ID from model deployments */
	model_deployment_id?: string;
	/** Provider (azure_openai, openai, anthropic) */
	provider?: string;
	/** Model name */
	model_name?: string;
	/** Temperature for generation */
	temperature?: number;
	/** Display name for UI */
	display_name?: string;
}

/**
 * Behavioral safety settings for detecting adversarial inputs.
 * Supports both LLM-as-judge and local HuggingFace model approaches.
 */
export interface BehavioralGuardrails {
	/** Prompt injection scanner action — "off", "block", or "warn" */
	detect_prompt_injection: ScannerAction;
	/** Jailbreak scanner action — "off", "block", or "warn" */
	detect_jailbreak_attempts: ScannerAction;
	/** Wrap system prompt with anti-override anchoring */
	system_prompt_protection: boolean;
	/** Maximum input character length */
	max_input_length: number;
	/** Maximum output character length */
	max_output_length: number;
	/** LLM configuration for the behavioral judge model */
	judge_llm_config?: JudgeLLMConfig | null;
	/** Toxicity input scanner action — "off", "block", or "warn" */
	detect_toxicity: ScannerAction;
	/** PII detection action — "off", "block", "warn", or "anonymize" (vault round-trip) */
	anonymize_pii: PIIAction;
	/** When anonymize action is selected, use realistic fake data instead of [REDACTED_*] placeholders */
	use_faker: boolean;
	/** PII entity types to detect (empty = all types) */
	pii_entity_types: string[];
	/** Secrets input scanner action — "off", "block", or "warn" */
	detect_secrets: ScannerAction;
	/** Zero-shot topic ban list (empty = disabled) */
	ban_topics: string[];
	/** Allowed input languages by ISO 639-1 code (empty = allow all) */
	allowed_languages: string[];
	/** Gibberish input scanner action — "off", "block", or "warn" */
	detect_gibberish: ScannerAction;
	/** Code detection scanner action — "off", "block", or "warn" */
	ban_code: ScannerAction;
	/** Maximum input token count (null = unlimited) */
	max_input_tokens: number | null;
	/** Confidence threshold for prompt injection scanner (0.0-1.0) */
	prompt_injection_threshold: number;
	/** Confidence threshold for jailbreak scanner (0.0-1.0) */
	jailbreak_threshold: number;
	/** Confidence threshold for input toxicity scanner (0.0-1.0) */
	toxicity_threshold: number;
}

/**
 * Configuration for handling provider-level content filter responses.
 * Cloud LLM providers (Azure OpenAI, OpenAI) have built-in content safety
 * filters. When enabled, rejections are recorded as guardrail violations.
 */
export interface ProviderContentFilter {
	/** Whether to treat provider content filter errors as violations */
	enabled: boolean;
	/** Which categories to act on (empty = all).
	 *  Common: violence, sexual, self_harm, hate_speech, jailbreak, protected_material */
	categories: string[];
}

/**
 * LLM Guard output scanner configuration.
 * Controls ML-based scanners that run on LLM responses.
 */
export interface OutputScanners {
	/** Toxicity output scanner action — "off", "block", or "warn" */
	detect_toxicity: ScannerAction;
	/** No-refusal output scanner action — "off", "block", or "warn" */
	detect_refusal: ScannerAction;
	/** Sensitive data output scanner action — "off", "block", or "warn" */
	detect_sensitive_data: ScannerAction;
	/** Zero-shot topic ban list (empty = disabled) */
	ban_topics: string[];
	/** Allowed output languages by ISO 639-1 code (empty = allow all) */
	allowed_languages: string[];
	/** Relevance output scanner action — "off", "block", or "warn" */
	check_relevance: ScannerAction;
	/** Gibberish output scanner action — "off", "block", or "warn" */
	detect_gibberish: ScannerAction;
	/** Competitor names to flag in output */
	ban_competitors: string[];
	/** Bias output scanner action — "off", "block", or "warn" */
	detect_bias: ScannerAction;
	/** Factual consistency output scanner action — "off", "block", or "warn" */
	check_factual_consistency: ScannerAction;
	/** Confidence threshold for output toxicity scanner (0.0-1.0) */
	toxicity_threshold: number;
}

// --- Custom filter types ---

/** Execution mode for a custom filter */
export type CustomFilterType = "python_code" | "llm_judge" | "declarative";

/** What to do when a custom filter triggers */
export type CustomFilterAction = "block" | "warn" | "transform";

/** Where a custom filter applies in the pipeline */
export type CustomFilterScope = "ingress" | "egress" | "both";

/**
 * A user-defined filter for ingress/egress content processing.
 *
 * Supports three execution modes:
 * - python_code: User-written Python function, executed in sandbox
 * - llm_judge: Natural language policy prompt, LLM evaluates
 * - declarative: Predefined template with configurable parameters
 */
export interface CustomFilter {
	/** Unique filter identifier */
	id: string;
	/** Human-readable filter name */
	name: string;
	/** Execution mode */
	filter_type: CustomFilterType;
	/** What to do when filter triggers */
	action: CustomFilterAction;
	/** Where to apply — ingress (before LLM), egress (after LLM), or both */
	scope: CustomFilterScope;
	/** Per-filter toggle */
	enabled: boolean;
	/** Execution order (lower = first, 0-999) */
	priority: number;
	/** Python function source code (python_code type) */
	python_code: string;
	/** Natural language policy prompt (llm_judge type) */
	judge_prompt: string;
	/** LLM configuration for judge model (llm_judge type) */
	judge_llm_config: JudgeLLMConfig | null;
	/** Confidence threshold for triggering (llm_judge type, 0.0-1.0) */
	judge_threshold: number;
	/** Predefined template identifier (declarative type) */
	template_id: string;
	/** Template-specific parameters (declarative type) */
	template_params: Record<string, unknown>;
	/** Custom violation/transform message */
	message: string;
}

/** Definition of a declarative filter template for the UI */
export interface FilterTemplate {
	id: string;
	name: string;
	description: string;
	params: Record<string, FilterTemplateParam>;
	/** Whether this template requires an LLM judge model to execute */
	requires_llm_judge?: boolean;
}

/** Parameter definition for a declarative filter template */
export interface FilterTemplateParam {
	type: "string" | "int" | "float" | "bool" | "enum" | "list";
	default: unknown;
	min?: number;
	max?: number;
	options?: string[];
	description?: string;
}

/**
 * Complete guardrails configuration for an agent.
 *
 * Behavioral safety fields (formerly nested in BehavioralGuardrails) are
 * now top-level. The backend serializes them flat; old configs with a
 * nested "behavioral" key are auto-flattened by from_dict().
 */
export interface GuardrailsConfig {
	/** Master toggle for guardrails */
	enabled: boolean;
	/** How violations are handled */
	enforcement_mode: EnforcementMode;
	/** Pattern matching rules for data loss prevention */
	pattern_rules: PatternRule[];
	/** Tool call restrictions */
	tool_call_policy: ToolCallPolicy | null;
	/** Token/cost budget limits */
	token_budget: TokenBudget | null;
	/** LLM Guard output scanner configuration */
	output_scanners: OutputScanners | null;
	/** Provider content filter handling (Azure/OpenAI safety filters) */
	provider_content_filter: ProviderContentFilter | null;
	/** User-defined ingress/egress filters */
	custom_filters: CustomFilter[];

	// ── Behavioral safety fields (promoted from BehavioralGuardrails) ──
	/** Prompt injection scanner action — "off", "block", or "warn" */
	detect_prompt_injection: ScannerAction;
	/** Jailbreak scanner action — "off", "block", or "warn" */
	detect_jailbreak_attempts: ScannerAction;
	/** Wrap system prompt with anti-override anchoring */
	system_prompt_protection: boolean;
	/** Maximum input character length */
	max_input_length: number;
	/** Maximum output character length */
	max_output_length: number;
	/** LLM configuration for the behavioral judge model */
	judge_llm_config?: JudgeLLMConfig | null;
	/** Toxicity input scanner action — "off", "block", or "warn" */
	detect_toxicity: ScannerAction;
	/** PII detection action — "off", "block", "warn", or "anonymize" (vault round-trip) */
	anonymize_pii: PIIAction;
	/** When anonymize action is selected, use realistic fake data */
	use_faker: boolean;
	/** PII entity types to detect (empty = all types) */
	pii_entity_types: string[];
	/** Secrets input scanner action — "off", "block", or "warn" */
	detect_secrets: ScannerAction;
	/** Zero-shot topic ban list (empty = disabled) */
	ban_topics: string[];
	/** Allowed input languages by ISO 639-1 code (empty = allow all) */
	allowed_languages: string[];
	/** Gibberish input scanner action — "off", "block", or "warn" */
	detect_gibberish: ScannerAction;
	/** Code detection scanner action — "off", "block", or "warn" */
	ban_code: ScannerAction;
	/** Maximum input token count (null = unlimited) */
	max_input_tokens: number | null;
	/** Confidence threshold for prompt injection scanner (0.0-1.0) */
	prompt_injection_threshold: number;
	/** Confidence threshold for jailbreak scanner (0.0-1.0) */
	jailbreak_threshold: number;
	/** Confidence threshold for input toxicity scanner (0.0-1.0) */
	toxicity_threshold: number;
}

// --- Defaults (match backend exactly) ---

export const DEFAULT_BLOCKED_IP_RANGES: string[] = [
	"10.0.0.0/8",
	"172.16.0.0/12",
	"192.168.0.0/16",
	"127.0.0.0/8",
	"169.254.0.0/16",
	"0.0.0.0/8",
];

export const DEFAULT_TOOL_CALL_POLICY: ToolCallPolicy = {
	allowed_url_patterns: [],
	blocked_url_patterns: [],
	blocked_ip_ranges: [...DEFAULT_BLOCKED_IP_RANGES],
	allowed_sql_operations: ["SELECT"],
	blocked_tables: [],
	max_query_rows: 1000,
	allowed_file_extensions: [],
	blocked_file_paths: [],
	max_file_size_mb: 1024.0,
	max_tool_calls_per_execution: 50,
	tool_timeout_seconds: 60,
};

export const DEFAULT_TOKEN_BUDGET: TokenBudget = {
	max_input_tokens_per_execution: null,
	max_output_tokens_per_execution: null,
	max_total_tokens_per_execution: null,
	max_llm_calls_per_execution: 20,
	warn_at_percentage: 0.8,
};

export const DEFAULT_BEHAVIORAL: BehavioralGuardrails = {
	detect_prompt_injection: "block",
	detect_jailbreak_attempts: "block",
	system_prompt_protection: true,
	max_input_length: 50000,
	max_output_length: 100000,
	judge_llm_config: null,
	detect_toxicity: "off",
	anonymize_pii: "off",
	use_faker: false,
	pii_entity_types: [],
	detect_secrets: "off",
	ban_topics: [],
	allowed_languages: [],
	detect_gibberish: "off",
	ban_code: "off",
	max_input_tokens: null,
	prompt_injection_threshold: 0.75,
	jailbreak_threshold: 0.75,
	toxicity_threshold: 0.5,
};

export const DEFAULT_OUTPUT_SCANNERS: OutputScanners = {
	detect_toxicity: "off",
	detect_refusal: "off",
	detect_sensitive_data: "off",
	ban_topics: [],
	allowed_languages: [],
	check_relevance: "off",
	detect_gibberish: "off",
	ban_competitors: [],
	detect_bias: "off",
	check_factual_consistency: "off",
	toxicity_threshold: 0.5,
};

export const DEFAULT_PROVIDER_CONTENT_FILTER: ProviderContentFilter = {
	enabled: true,
	categories: [],
};

export const DEFAULT_GUARDRAILS_CONFIG: GuardrailsConfig = {
	enabled: false,
	enforcement_mode: "enforce",
	pattern_rules: [],
	tool_call_policy: null,
	token_budget: null,
	output_scanners: null,
	provider_content_filter: null,
	custom_filters: [],
	// Behavioral defaults (all off)
	detect_prompt_injection: "off",
	detect_jailbreak_attempts: "off",
	system_prompt_protection: false,
	max_input_length: 50000,
	max_output_length: 100000,
	judge_llm_config: null,
	detect_toxicity: "off",
	anonymize_pii: "off",
	use_faker: false,
	pii_entity_types: [],
	detect_secrets: "off",
	ban_topics: [],
	allowed_languages: [],
	detect_gibberish: "off",
	ban_code: "off",
	max_input_tokens: null,
	prompt_injection_threshold: 0.75,
	jailbreak_threshold: 0.75,
	toxicity_threshold: 0.5,
};

export const createDefaultCustomFilter = (
	filterType: CustomFilterType = "python_code",
): CustomFilter => ({
	id: typeof crypto !== "undefined" && crypto.randomUUID
		? crypto.randomUUID()
		: `filter-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
	name: "",
	filter_type: filterType,
	action: "block",
	scope: "both",
	enabled: true,
	priority: 100,
	python_code: "",
	judge_prompt: "",
	judge_llm_config: null,
	judge_threshold: 0.7,
	template_id: "",
	template_params: {},
	message: "",
});

/**
 * Common pattern rule templates for the UI preset picker.
 *
 * These are NOT auto-applied — they exist purely as convenience templates
 * that users can select from a dropdown to pre-fill a custom pattern rule.
 * The backend presets list remains empty; patterns only activate when a user
 * explicitly adds them to a policy.
 */
export const PATTERN_RULE_PRESETS: PatternRule[] = [
	// --- Single-pattern presets (PII / secrets) ---
	{
		name: "SSN (US)",
		description: "US Social Security Number format",
		patterns: [
			{ label: "SSN (US)", regex: "\\b\\d{3}-\\d{2}-\\d{4}\\b" },
		],
		action: "redact",
		applies_to: "both",
		message: "US Social Security Number detected",
		preset_id: "ssn_us",
	},
	{
		name: "Credit Card",
		description: "Credit card number (13-19 digits)",
		patterns: [
			{
				label: "Credit Card",
				regex: "\\b\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}\\b",
			},
		],
		action: "redact",
		applies_to: "both",
		message: "Credit card number detected",
		preset_id: "credit_card",
	},
	{
		name: "Email Address",
		description: "Standard email address format",
		patterns: [
			{
				label: "Email",
				regex: "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
			},
		],
		action: "warn",
		applies_to: "both",
		message: "Email address detected",
		preset_id: "email",
	},
	{
		name: "Phone (US)",
		description: "US phone number formats",
		patterns: [
			{
				label: "Phone (US)",
				regex: "(\\+?1[-.\\s]?)?\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}\\b",
			},
		],
		action: "warn",
		applies_to: "both",
		message: "US phone number detected",
		preset_id: "phone_us",
	},
	{
		name: "API Key",
		description: "Common API key and token prefixes",
		patterns: [
			{
				label: "API Key",
				regex: "\\b(sk-|pk_|api_key_|AKIA|ghp_|gho_|github_pat_)[A-Za-z0-9_-]{20,}\\b",
			},
		],
		action: "redact",
		applies_to: "both",
		message: "API key or secret token detected",
		preset_id: "api_key",
	},
	{
		name: "AWS Access Key",
		description: "AWS access key ID (AKIA prefix)",
		patterns: [
			{ label: "AWS Key", regex: "\\bAKIA[0-9A-Z]{16}\\b" },
		],
		action: "block",
		applies_to: "both",
		message: "AWS access key detected",
		preset_id: "aws_key",
	},
	{
		name: "Private Key",
		description: "PEM-encoded private key material",
		patterns: [
			{
				label: "Private Key",
				regex: "-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
			},
		],
		action: "block",
		applies_to: "both",
		message: "Private key material detected",
		preset_id: "private_key",
	},
	// --- Multi-pattern presets (security / compliance) ---
	{
		name: "SQL Injection",
		description: "Common SQL injection patterns",
		patterns: [
			{
				label: "SQL Keywords",
				regex: "(?i)\\b(DROP|DELETE|INSERT|UPDATE|EXEC|EXECUTE|UNION|ALTER|CREATE|TRUNCATE)\\b",
			},
			{
				label: "SQL Operators",
				regex: "(?i)(--|;|'\\s*OR\\s+'|'\\s*AND\\s+')",
			},
		],
		action: "block",
		applies_to: "input",
		message: "Potential SQL injection detected",
		preset_id: "sql_injection",
	},
	{
		name: "Prompt Injection",
		description: "Common prompt injection and jailbreak attempts",
		patterns: [
			{
				label: "Ignore Instructions",
				regex: "(?i)(ignore\\s+(all\\s+)?(previous|above|prior)\\s+(instructions|prompts|rules))",
			},
			{
				label: "Role Override",
				regex: "(?i)(you\\s+are\\s+now|act\\s+as\\s+(if|a)|pretend\\s+(to\\s+be|you\\s+are)|from\\s+now\\s+on\\s+you)",
			},
			{
				label: "System Prompt Extraction",
				regex: "(?i)(show|reveal|repeat|print|output|display)\\s+(your|the|system)\\s+(system\\s+)?(prompt|instructions|rules)",
			},
		],
		action: "block",
		applies_to: "input",
		message: "Potential prompt injection detected",
		preset_id: "prompt_injection",
	},
	{
		name: "Code Execution",
		description: "Dangerous code execution and shell command patterns",
		patterns: [
			{
				label: "Shell Commands",
				regex: "(?i)\\b(rm\\s+-rf|sudo\\s+|chmod\\s+|curl\\s+.*\\|\\s*sh|wget\\s+.*\\|\\s*bash)\\b",
			},
			{
				label: "Script Injection",
				regex: "(?i)(<script[^>]*>|javascript:|on(load|error|click)\\s*=)",
			},
			{
				label: "OS Command Injection",
				regex: "(?i)(;\\s*(ls|cat|whoami|id|uname|pwd)\\b|\\|\\s*(bash|sh|cmd)\\b)",
			},
		],
		action: "block",
		applies_to: "input",
		message: "Potentially dangerous code execution detected",
		preset_id: "code_execution",
	},
	{
		name: "Confidential Data Leak",
		description: "API keys, credentials, and connection strings",
		patterns: [
			{
				label: "API Keys / Secrets",
				regex: "(?i)(api[_-]?key|secret[_-]?key|access[_-]?token|private[_-]?key)\\s*[:=]\\s*['\"]?[a-zA-Z0-9_\\-]{16,}",
			},
			{
				label: "AWS Credentials",
				regex: "(?i)(AKIA[0-9A-Z]{16}|aws[_-]?secret[_-]?access[_-]?key)",
			},
			{
				label: "Connection Strings",
				regex: "(?i)(mongodb(\\+srv)?://|postgres(ql)?://|mysql://|redis://)[^\\s]+",
			},
		],
		action: "block",
		applies_to: "both",
		message: "Potential confidential data exposure detected",
		preset_id: "confidential_data",
	},
	{
		name: "URL / Link Filtering",
		description: "Detect URLs and hyperlinks in content",
		patterns: [
			{
				label: "HTTP/HTTPS URLs",
				regex: "https?://[^\\s\"'<>]+",
			},
			{
				label: "Data URIs",
				regex: "data:[a-zA-Z]+/[a-zA-Z0-9.+\\-]+;base64,",
			},
		],
		action: "warn",
		applies_to: "output",
		message: "URL or link detected in content",
		preset_id: "url_filtering",
	},
];

// --- Declarative filter templates ---

export const FILTER_TEMPLATES: FilterTemplate[] = [
	{
		id: "topic_guard",
		name: "Topic Guard",
		description:
			"Restricts content to allowed topics or blocks forbidden topics",
		requires_llm_judge: true,
		params: {
			mode: {
				type: "enum",
				default: "blocklist",
				options: ["allowlist", "blocklist"],
				description:
					"Allowlist mode permits only listed topics; blocklist blocks them",
			},
			topics: {
				type: "list",
				default: [],
				description: "Topics to allow or block",
			},
		},
	},
	{
		id: "language_detector",
		name: "Language Detector",
		description: "Ensures content is in allowed languages",
		requires_llm_judge: true,
		params: {
			allowed_languages: {
				type: "list",
				default: ["en"],
				options: [
					"en",
					"es",
					"fr",
					"de",
					"it",
					"pt",
					"zh",
					"ja",
					"ko",
					"ar",
					"hi",
					"ru",
				],
				description: "Allowed language codes",
			},
		},
	},
	{
		id: "word_count_limit",
		name: "Word Count Limit",
		description: "Limits content to a maximum word count",
		params: {
			max_words: {
				type: "int",
				default: 500,
				min: 1,
				max: 100000,
				description: "Maximum number of words allowed",
			},
		},
	},
];
