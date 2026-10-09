/**
 * Bidirectional mapper between the flat GuardrailItem[] list (UI state)
 * and the nested GuardrailsConfig (API / persistence format).
 */

import type {
	CustomFilter,
	EnforcementMode,
	GuardrailsConfig,
	OutputScanners,
	ProviderContentFilter,
	TokenBudget,
	ToolCallPolicy,
} from "@/types/guardrails";
import {
	DEFAULT_BEHAVIORAL,
	DEFAULT_BLOCKED_IP_RANGES,
	DEFAULT_TOKEN_BUDGET,
	DEFAULT_TOOL_CALL_POLICY,
} from "@/types/guardrails";
import type {
	AdversarialItemConfig,
	CustomFilterItemConfig,
	DatabaseItemConfig,
	ExecutionLimitsItemConfig,
	FilesystemItemConfig,
	GeneralSafetyItemConfig,
	GuardrailItem,
	InputContentItemConfig,
	InputPolicyItemConfig,
	LLMJudgeItemConfig,
	NetworkItemConfig,
	OutputContentItemConfig,
	OutputPolicyItemConfig,
	OutputQualityItemConfig,
	PIIItemConfig,
	PatternRuleItemConfig,
	ProviderContentFilterItemConfig,
	TokenBudgetItemConfig,
} from "@/types/guardrail-items";
import { generateItemId } from "@/types/guardrail-items";

// ─── Config → Items ─────────────────────────────────────────────────────────

/** Decompose a GuardrailsConfig into a flat item list for the builder UI. */
export function configToItems(config: GuardrailsConfig): GuardrailItem[] {
	const items: GuardrailItem[] = [];

	// Pattern rules → one item each
	for (const rule of config.pattern_rules ?? []) {
		items.push({
			id: generateItemId(),
			type: "pattern_rule",
			config: {
				name: rule.name,
				patterns: rule.patterns ?? [],
				action: rule.action,
				applies_to: rule.applies_to,
				message: rule.message,
				preset_id: rule.preset_id ?? "",
			},
		});
	}

	// Decompose behavioral fields (now top-level on config) into up to 6 UI items:
	// 1-4. LLM Guard input scanners (adversarial, PII, content, policy)
	// 5. LLM Judge (judge model config)
	// 6. General Safety (system prompt protection + length limits)

	// Adversarial detection
	const _dpi = typeof config.detect_prompt_injection === "boolean"
		? (config.detect_prompt_injection ? "block" : "off")
		: (config.detect_prompt_injection || "off");
	const _dja = typeof config.detect_jailbreak_attempts === "boolean"
		? (config.detect_jailbreak_attempts ? "block" : "off")
		: (config.detect_jailbreak_attempts || "off");
	if (_dpi !== "off" || _dja !== "off") {
		items.push({
			id: generateItemId(),
			type: "llm_guard_adversarial",
			config: {
				detect_prompt_injection: _dpi,
				detect_jailbreak_attempts: _dja,
				prompt_injection_threshold: config.prompt_injection_threshold ?? 0.75,
				jailbreak_threshold: config.jailbreak_threshold ?? 0.75,
			},
		});
	}

	// PII anonymization
	if (config.anonymize_pii && config.anonymize_pii !== "off") {
		items.push({
			id: generateItemId(),
			type: "llm_guard_pii",
			config: {
				anonymize_pii: config.anonymize_pii,
				use_faker: config.use_faker ?? false,
				pii_entity_types: config.pii_entity_types ?? [],
			},
		});
	}

	// Input content safety
	if ((config.detect_toxicity && config.detect_toxicity !== "off")
		|| (config.detect_gibberish && config.detect_gibberish !== "off")
		|| (config.ban_code && config.ban_code !== "off")) {
		items.push({
			id: generateItemId(),
			type: "llm_guard_input_content",
			config: {
				detect_toxicity: config.detect_toxicity ?? "off",
				detect_gibberish: config.detect_gibberish ?? "off",
				ban_code: config.ban_code ?? "off",
				toxicity_threshold: config.toxicity_threshold ?? 0.5,
			},
		});
	}

	// Input policy controls
	if ((config.ban_topics?.length ?? 0) > 0 || (config.allowed_languages?.length ?? 0) > 0
		|| config.max_input_tokens != null || (config.detect_secrets && config.detect_secrets !== "off")) {
		items.push({
			id: generateItemId(),
			type: "llm_guard_input_policy",
			config: {
				ban_topics: config.ban_topics ?? [],
				allowed_languages: config.allowed_languages ?? [],
				max_input_tokens: config.max_input_tokens ?? null,
				detect_secrets: config.detect_secrets ?? "off",
			},
		});
	}

	// LLM Judge — only if judge model is configured
	if (config.judge_llm_config) {
		items.push({
			id: generateItemId(),
			type: "llm_judge",
			config: {
				judge_llm_config: config.judge_llm_config,
			},
		});
	}

	// General Safety — if system prompt protection or non-default length limits
	const hasGeneralSafety = config.system_prompt_protection
		|| config.max_input_length !== DEFAULT_BEHAVIORAL.max_input_length
		|| config.max_output_length !== DEFAULT_BEHAVIORAL.max_output_length;
	if (hasGeneralSafety) {
		items.push({
			id: generateItemId(),
			type: "general_safety",
			config: {
				system_prompt_protection: config.system_prompt_protection,
				max_input_length: config.max_input_length,
				max_output_length: config.max_output_length,
			},
		});
	}

	// Provider content filter
	const pcf = config.provider_content_filter;
	if (pcf && pcf.enabled) {
		items.push({
			id: generateItemId(),
			type: "provider_content_filter",
			config: {
				categories: pcf.categories,
			},
		});
	}

	// LLM Guard output scanners → split into 3 items
	const outScan = config.output_scanners;
	if (outScan) {
		// Output quality
		if ((outScan.detect_refusal && outScan.detect_refusal !== "off")
			|| (outScan.check_relevance && outScan.check_relevance !== "off")
			|| (outScan.check_factual_consistency && outScan.check_factual_consistency !== "off")
			|| (outScan.detect_gibberish && outScan.detect_gibberish !== "off")) {
			items.push({
				id: generateItemId(),
				type: "llm_guard_output_quality",
				config: {
					detect_refusal: outScan.detect_refusal ?? "off",
					check_relevance: outScan.check_relevance ?? "off",
					check_factual_consistency: outScan.check_factual_consistency ?? "off",
					detect_gibberish: outScan.detect_gibberish ?? "off",
				},
			});
		}

		// Output content safety
		if ((outScan.detect_toxicity && outScan.detect_toxicity !== "off")
			|| (outScan.detect_bias && outScan.detect_bias !== "off")) {
			items.push({
				id: generateItemId(),
				type: "llm_guard_output_content",
				config: {
					detect_toxicity: outScan.detect_toxicity ?? "off",
					detect_bias: outScan.detect_bias ?? "off",
					toxicity_threshold: outScan.toxicity_threshold ?? 0.5,
				},
			});
		}

		// Output policy controls
		if ((outScan.detect_sensitive_data && outScan.detect_sensitive_data !== "off")
			|| (outScan.ban_competitors?.length ?? 0) > 0
			|| (outScan.ban_topics?.length ?? 0) > 0 || (outScan.allowed_languages?.length ?? 0) > 0) {
			items.push({
				id: generateItemId(),
				type: "llm_guard_output_policy",
				config: {
					detect_sensitive_data: outScan.detect_sensitive_data ?? "off",
					ban_competitors: outScan.ban_competitors ?? [],
					ban_topics: outScan.ban_topics ?? [],
					allowed_languages: outScan.allowed_languages ?? [],
				},
			});
		}
	}

	// Tool call policy → split into sub-items (only if non-default)
	const tcp = config.tool_call_policy;
	if (tcp) {
		const def = DEFAULT_TOOL_CALL_POLICY;

		const hasNetwork =
			tcp.allowed_url_patterns.length > 0 ||
			tcp.blocked_url_patterns.length > 0 ||
			JSON.stringify(tcp.blocked_ip_ranges) !==
				JSON.stringify(def.blocked_ip_ranges);
		if (hasNetwork) {
			items.push({
				id: generateItemId(),
				type: "tool_network",
				config: {
					allowed_url_patterns: tcp.allowed_url_patterns,
					blocked_url_patterns: tcp.blocked_url_patterns,
					blocked_ip_ranges: tcp.blocked_ip_ranges,
				},
			});
		}

		const hasDb =
			JSON.stringify(tcp.allowed_sql_operations) !==
				JSON.stringify(def.allowed_sql_operations) ||
			tcp.blocked_tables.length > 0 ||
			tcp.max_query_rows !== def.max_query_rows;
		if (hasDb) {
			items.push({
				id: generateItemId(),
				type: "tool_database",
				config: {
					allowed_sql_operations: tcp.allowed_sql_operations,
					blocked_tables: tcp.blocked_tables,
					max_query_rows: tcp.max_query_rows,
				},
			});
		}

		const hasFs =
			tcp.allowed_file_extensions.length > 0 ||
			tcp.blocked_file_paths.length > 0 ||
			tcp.max_file_size_mb !== def.max_file_size_mb;
		if (hasFs) {
			items.push({
				id: generateItemId(),
				type: "tool_filesystem",
				config: {
					allowed_file_extensions: tcp.allowed_file_extensions,
					blocked_file_paths: tcp.blocked_file_paths,
					max_file_size_mb: tcp.max_file_size_mb,
				},
			});
		}

		const hasExec =
			tcp.max_tool_calls_per_execution !== def.max_tool_calls_per_execution ||
			tcp.tool_timeout_seconds !== def.tool_timeout_seconds;
		if (hasExec) {
			items.push({
				id: generateItemId(),
				type: "tool_execution_limits",
				config: {
					max_tool_calls_per_execution: tcp.max_tool_calls_per_execution,
					tool_timeout_seconds: tcp.tool_timeout_seconds,
				},
			});
		}
	}

	// Token budget
	if (config.token_budget) {
		const tb = config.token_budget;
		items.push({
			id: generateItemId(),
			type: "token_budget",
			config: {
				max_input_tokens_per_execution: tb.max_input_tokens_per_execution,
				max_output_tokens_per_execution: tb.max_output_tokens_per_execution,
				max_total_tokens_per_execution: tb.max_total_tokens_per_execution,
				max_llm_calls_per_execution: tb.max_llm_calls_per_execution,
				warn_at_percentage: tb.warn_at_percentage,
			},
		});
	}

	// Custom filters → one item each
	for (const f of config.custom_filters ?? []) {
		items.push({
			id: generateItemId(),
			type: "custom_filter",
			config: {
				filter_id: f.id,
				name: f.name,
				filter_type: f.filter_type,
				action: f.action,
				scope: f.scope,
				enabled: f.enabled,
				priority: f.priority,
				python_code: f.python_code,
				judge_prompt: f.judge_prompt,
				judge_llm_config: f.judge_llm_config,
				judge_threshold: f.judge_threshold,
				template_id: f.template_id,
				template_params: f.template_params,
				message: f.message,
			},
		});
	}

	return items;
}

// ─── Items → Config ─────────────────────────────────────────────────────────

/** Reassemble a GuardrailsConfig from a flat item list. */
export function itemsToConfig(
	items: GuardrailItem[],
	enforcementMode: EnforcementMode,
): GuardrailsConfig {
	const patternRules = items
		.filter((i) => i.type === "pattern_rule")
		.map((i) => {
			const c = i.config as PatternRuleItemConfig;
			return {
				name: c.name,
				patterns: c.patterns,
				action: c.action,
				applies_to: c.applies_to,
				message: c.message,
				preset_id: c.preset_id,
			};
		});

	// Behavioral — merge 4 input scanner types + LLM Judge + General Safety items
	// Fields are written directly to top-level config (no nested "behavioral" object)
	const adversarialItem = items.find((i) => i.type === "llm_guard_adversarial");
	const piiItem = items.find((i) => i.type === "llm_guard_pii");
	const inputContentItem = items.find((i) => i.type === "llm_guard_input_content");
	const inputPolicyItem = items.find((i) => i.type === "llm_guard_input_policy");
	const llmJudgeItem = items.find((i) => i.type === "llm_judge");
	const generalSafetyItem = items.find((i) => i.type === "general_safety");

	const advCfg = adversarialItem?.config as AdversarialItemConfig | undefined;
	const piiCfg = piiItem?.config as PIIItemConfig | undefined;
	const contentCfg = inputContentItem?.config as InputContentItemConfig | undefined;
	const policyCfg = inputPolicyItem?.config as InputPolicyItemConfig | undefined;
	const judgeCfg = llmJudgeItem?.config as LLMJudgeItemConfig | undefined;
	const safetyCfg = generalSafetyItem?.config as GeneralSafetyItemConfig | undefined;

	const behavioralFields = {
		detect_prompt_injection: advCfg?.detect_prompt_injection ?? "off" as const,
		detect_jailbreak_attempts: advCfg?.detect_jailbreak_attempts ?? "off" as const,
		system_prompt_protection: safetyCfg?.system_prompt_protection ?? false,
		judge_llm_config: judgeCfg?.judge_llm_config ?? null,
		max_input_length: safetyCfg?.max_input_length ?? DEFAULT_BEHAVIORAL.max_input_length,
		max_output_length: safetyCfg?.max_output_length ?? DEFAULT_BEHAVIORAL.max_output_length,
		detect_toxicity: contentCfg?.detect_toxicity ?? "off" as const,
		anonymize_pii: piiCfg?.anonymize_pii ?? "off" as const,
		use_faker: piiCfg?.use_faker ?? false,
		pii_entity_types: piiCfg?.pii_entity_types ?? [],
		detect_secrets: policyCfg?.detect_secrets ?? "off" as const,
		ban_topics: policyCfg?.ban_topics ?? [],
		allowed_languages: policyCfg?.allowed_languages ?? [],
		detect_gibberish: contentCfg?.detect_gibberish ?? "off" as const,
		ban_code: contentCfg?.ban_code ?? "off" as const,
		max_input_tokens: policyCfg?.max_input_tokens ?? null,
		prompt_injection_threshold: advCfg?.prompt_injection_threshold ?? 0.75,
		jailbreak_threshold: advCfg?.jailbreak_threshold ?? 0.75,
		toxicity_threshold: contentCfg?.toxicity_threshold ?? 0.5,
	};

	// LLM Guard output scanners — merge 3 output scanner types
	const outputQualityItem = items.find((i) => i.type === "llm_guard_output_quality");
	const outputContentItem = items.find((i) => i.type === "llm_guard_output_content");
	const outputPolicyItem = items.find((i) => i.type === "llm_guard_output_policy");
	let output_scanners: OutputScanners | null = null;
	if (outputQualityItem || outputContentItem || outputPolicyItem) {
		const qualCfg = outputQualityItem?.config as OutputQualityItemConfig | undefined;
		const contCfg = outputContentItem?.config as OutputContentItemConfig | undefined;
		const polCfg = outputPolicyItem?.config as OutputPolicyItemConfig | undefined;
		output_scanners = {
			detect_toxicity: contCfg?.detect_toxicity ?? "off",
			detect_refusal: qualCfg?.detect_refusal ?? "off",
			detect_sensitive_data: polCfg?.detect_sensitive_data ?? "off",
			ban_topics: polCfg?.ban_topics ?? [],
			allowed_languages: polCfg?.allowed_languages ?? [],
			check_relevance: qualCfg?.check_relevance ?? "off",
			detect_gibberish: qualCfg?.detect_gibberish ?? "off",
			ban_competitors: polCfg?.ban_competitors ?? [],
			detect_bias: contCfg?.detect_bias ?? "off",
			check_factual_consistency: qualCfg?.check_factual_consistency ?? "off",
			toxicity_threshold: contCfg?.toxicity_threshold ?? 0.5,
		};
	}

	// Provider content filter
	const pcfItem = items.find((i) => i.type === "provider_content_filter");
	let providerContentFilter: ProviderContentFilter | null = null;
	if (pcfItem) {
		const c = pcfItem.config as ProviderContentFilterItemConfig;
		providerContentFilter = {
			enabled: true,
			categories: c.categories ?? [],
		};
	}

	// Tool call policy — merge sub-items back into one object
	const toolItems = items.filter((i) => i.type.startsWith("tool_"));
	let toolCallPolicy: ToolCallPolicy | null = null;
	if (toolItems.length > 0) {
		toolCallPolicy = { ...DEFAULT_TOOL_CALL_POLICY };
		for (const item of toolItems) {
			if (item.type === "tool_network") {
				const c = item.config as NetworkItemConfig;
				toolCallPolicy.allowed_url_patterns = c.allowed_url_patterns;
				toolCallPolicy.blocked_url_patterns = c.blocked_url_patterns;
				toolCallPolicy.blocked_ip_ranges = c.blocked_ip_ranges;
			} else if (item.type === "tool_database") {
				const c = item.config as DatabaseItemConfig;
				toolCallPolicy.allowed_sql_operations = c.allowed_sql_operations;
				toolCallPolicy.blocked_tables = c.blocked_tables;
				toolCallPolicy.max_query_rows = c.max_query_rows;
			} else if (item.type === "tool_filesystem") {
				const c = item.config as FilesystemItemConfig;
				toolCallPolicy.allowed_file_extensions = c.allowed_file_extensions;
				toolCallPolicy.blocked_file_paths = c.blocked_file_paths;
				toolCallPolicy.max_file_size_mb = c.max_file_size_mb;
			} else if (item.type === "tool_execution_limits") {
				const c = item.config as ExecutionLimitsItemConfig;
				toolCallPolicy.max_tool_calls_per_execution =
					c.max_tool_calls_per_execution;
				toolCallPolicy.tool_timeout_seconds = c.tool_timeout_seconds;
			}
		}
	}

	// Token budget
	const tbItem = items.find((i) => i.type === "token_budget");
	let tokenBudget: TokenBudget | null = null;
	if (tbItem) {
		const c = tbItem.config as TokenBudgetItemConfig;
		tokenBudget = {
			max_input_tokens_per_execution: c.max_input_tokens_per_execution,
			max_output_tokens_per_execution: c.max_output_tokens_per_execution,
			max_total_tokens_per_execution: c.max_total_tokens_per_execution,
			max_llm_calls_per_execution: c.max_llm_calls_per_execution,
			warn_at_percentage: c.warn_at_percentage,
		};
	}

	// Custom filters
	const customFilters: CustomFilter[] = items
		.filter((i) => i.type === "custom_filter")
		.map((i) => {
			const c = i.config as CustomFilterItemConfig;
			return {
				id: c.filter_id,
				name: c.name,
				filter_type: c.filter_type,
				action: c.action,
				scope: c.scope,
				enabled: c.enabled,
				priority: c.priority,
				python_code: c.python_code,
				judge_prompt: c.judge_prompt,
				judge_llm_config: c.judge_llm_config,
				judge_threshold: c.judge_threshold,
				template_id: c.template_id,
				template_params: c.template_params,
				message: c.message,
			};
		});

	return {
		enabled: items.length > 0,
		enforcement_mode: enforcementMode,
		pattern_rules: patternRules,
		output_scanners,
		provider_content_filter: providerContentFilter,
		tool_call_policy: toolCallPolicy,
		token_budget: tokenBudget,
		custom_filters: customFilters,
		...behavioralFields,
	};
}

// ─── Helpers for creating new items from catalog ────────────────────────────

export function createPatternRuleItem(
	preset?: PatternRuleItemConfig,
): GuardrailItem {
	return {
		id: generateItemId(),
		type: "pattern_rule",
		config: preset ?? {
			name: "",
			patterns: [{ label: "", regex: "" }],
			action: "block",
			applies_to: "both",
			message: "",
			preset_id: "",
		},
	};
}

export function createLLMJudgeItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_judge",
		config: {
			judge_llm_config: null,
		},
	};
}

export function createGeneralSafetyItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "general_safety",
		config: {
			system_prompt_protection: true,
			max_input_length: DEFAULT_BEHAVIORAL.max_input_length,
			max_output_length: DEFAULT_BEHAVIORAL.max_output_length,
		},
	};
}

export function createToolNetworkItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "tool_network",
		config: {
			allowed_url_patterns: [],
			blocked_url_patterns: [],
			blocked_ip_ranges: [...DEFAULT_BLOCKED_IP_RANGES],
		},
	};
}

export function createToolDatabaseItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "tool_database",
		config: {
			allowed_sql_operations: ["SELECT"],
			blocked_tables: [],
			max_query_rows: 1000,
		},
	};
}

export function createToolFilesystemItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "tool_filesystem",
		config: {
			allowed_file_extensions: [],
			blocked_file_paths: [],
			max_file_size_mb: 1024,
		},
	};
}

export function createToolExecutionLimitsItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "tool_execution_limits",
		config: {
			max_tool_calls_per_execution: 50,
			tool_timeout_seconds: 60,
		},
	};
}

export function createProviderContentFilterItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "provider_content_filter",
		config: { categories: [] },
	};
}

export function createTokenBudgetItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "token_budget",
		config: { ...DEFAULT_TOKEN_BUDGET },
	};
}

export function createAdversarialItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_guard_adversarial",
		config: {
			detect_prompt_injection: "block",
			detect_jailbreak_attempts: "block",
			prompt_injection_threshold: 0.75,
			jailbreak_threshold: 0.75,
		},
	};
}

export function createPIIItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_guard_pii",
		config: {
			anonymize_pii: "off",
			use_faker: false,
			pii_entity_types: [],
		},
	};
}

export function createInputContentItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_guard_input_content",
		config: {
			detect_toxicity: "off",
			detect_gibberish: "off",
			ban_code: "off",
			toxicity_threshold: 0.5,
		},
	};
}

export function createInputPolicyItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_guard_input_policy",
		config: {
			ban_topics: [],
			allowed_languages: [],
			max_input_tokens: null,
			detect_secrets: "off",
		},
	};
}

export function createOutputQualityItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_guard_output_quality",
		config: {
			detect_refusal: "off",
			check_relevance: "off",
			check_factual_consistency: "off",
			detect_gibberish: "off",
		},
	};
}

export function createOutputContentItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_guard_output_content",
		config: {
			detect_toxicity: "off",
			detect_bias: "off",
			toxicity_threshold: 0.5,
		},
	};
}

export function createOutputPolicyItem(): GuardrailItem {
	return {
		id: generateItemId(),
		type: "llm_guard_output_policy",
		config: {
			detect_sensitive_data: "off",
			ban_competitors: [],
			ban_topics: [],
			allowed_languages: [],
		},
	};
}

export function createCustomFilterItem(
	filterType: "python_code" | "llm_judge" | "declarative",
	templateId?: string,
	defaultCode?: string,
	defaultName?: string,
): GuardrailItem {
	const filterId =
		typeof crypto !== "undefined" && crypto.randomUUID
			? crypto.randomUUID()
			: `filter-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
	return {
		id: generateItemId(),
		type: "custom_filter",
		config: {
			filter_id: filterId,
			name: defaultName ?? "",
			filter_type: filterType,
			action: defaultCode ? "transform" : "block",
			scope: "both",
			enabled: true,
			priority: 100,
			python_code: defaultCode ?? "",
			judge_prompt: "",
			judge_llm_config: null,
			judge_threshold: 0.7,
			template_id: templateId ?? "",
			template_params: {},
			message: "",
		},
	};
}
