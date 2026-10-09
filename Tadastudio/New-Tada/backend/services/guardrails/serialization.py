"""Decomposed guardrail serialization for export and API responses.

Converts the flat ``GuardrailsConfig`` blob into a structured list of
individually named guardrails, each with its own config.  This format is
used for workflow export (``guardrails_pipeline``) and the resolve API.

DB storage (``to_dict()`` / ``from_dict()``) is unaffected — decomposition
happens only at the serialization boundary.
"""

from typing import Any, Dict, List

from backend.models.workflow.configs.guardrails import (
    GuardrailsConfig,
    ToolCallPolicy,
)

# Default instances for comparison
_DEFAULT_TCP = ToolCallPolicy()


# ---------------------------------------------------------------------------
# Decompose: GuardrailsConfig → list of named guardrails
# ---------------------------------------------------------------------------


def decompose_config(cfg: GuardrailsConfig) -> List[Dict[str, Any]]:
    """Convert a GuardrailsConfig into a list of individually named guardrails.

    Only includes guardrails that are **active** (non-off, non-default,
    non-empty).  Each entry is ``{"guardrail_name": str, "guardrail_config": dict}``.
    """
    guardrails: List[Dict[str, Any]] = []

    # ── Input behavioral scanners ──────────────────────────────────────

    if cfg.detect_prompt_injection and cfg.detect_prompt_injection != "off":
        guardrails.append({
            "guardrail_name": "prompt_injection",
            "guardrail_config": {
                "action": cfg.detect_prompt_injection,
                "threshold": cfg.prompt_injection_threshold,
            },
        })

    if cfg.detect_jailbreak_attempts and cfg.detect_jailbreak_attempts != "off":
        guardrails.append({
            "guardrail_name": "jailbreak_detection",
            "guardrail_config": {
                "action": cfg.detect_jailbreak_attempts,
                "threshold": cfg.jailbreak_threshold,
            },
        })

    if cfg.detect_toxicity and cfg.detect_toxicity != "off":
        guardrails.append({
            "guardrail_name": "toxicity_detection",
            "guardrail_config": {
                "action": cfg.detect_toxicity,
                "threshold": cfg.toxicity_threshold,
            },
        })

    if cfg.anonymize_pii and cfg.anonymize_pii != "off":
        guardrails.append({
            "guardrail_name": "pii_anonymization",
            "guardrail_config": {
                "action": cfg.anonymize_pii,
                "use_faker": cfg.use_faker,
                "entity_types": list(cfg.pii_entity_types),
            },
        })

    if cfg.detect_secrets and cfg.detect_secrets != "off":
        guardrails.append({
            "guardrail_name": "secret_detection",
            "guardrail_config": {"action": cfg.detect_secrets},
        })

    if cfg.detect_gibberish and cfg.detect_gibberish != "off":
        guardrails.append({
            "guardrail_name": "gibberish_detection",
            "guardrail_config": {"action": cfg.detect_gibberish},
        })

    if cfg.ban_code and cfg.ban_code != "off":
        guardrails.append({
            "guardrail_name": "code_detection",
            "guardrail_config": {"action": cfg.ban_code},
        })

    if cfg.ban_topics:
        guardrails.append({
            "guardrail_name": "topic_ban",
            "guardrail_config": {"topics": list(cfg.ban_topics)},
        })

    if cfg.allowed_languages:
        guardrails.append({
            "guardrail_name": "language_restriction",
            "guardrail_config": {"languages": list(cfg.allowed_languages)},
        })

    if cfg.max_input_tokens is not None:
        guardrails.append({
            "guardrail_name": "token_limit",
            "guardrail_config": {"max_tokens": cfg.max_input_tokens},
        })

    if cfg.system_prompt_protection:
        guardrails.append({
            "guardrail_name": "system_prompt_protection",
            "guardrail_config": {"enabled": True},
        })

    if cfg.max_input_length != 50000:
        guardrails.append({
            "guardrail_name": "input_length_limit",
            "guardrail_config": {"max_length": cfg.max_input_length},
        })

    if cfg.max_output_length != 100000:
        guardrails.append({
            "guardrail_name": "output_length_limit",
            "guardrail_config": {"max_length": cfg.max_output_length},
        })

    if cfg.judge_llm_config:
        guardrails.append({
            "guardrail_name": "llm_judge",
            "guardrail_config": cfg.judge_llm_config.to_dict(),
        })

    # ── Pattern rules (one entry per rule) ─────────────────────────────

    for rule in cfg.pattern_rules:
        guardrails.append({
            "guardrail_name": "pattern_rule",
            "guardrail_config": {
                "name": rule.name,
                "patterns": [{"label": p.label, "regex": p.regex} for p in rule.patterns],
                "action": rule.action,
                "applies_to": rule.applies_to,
                "message": rule.message,
                "preset_id": rule.preset_id,
            },
        })

    # ── Output scanners ────────────────────────────────────────────────

    out = cfg.output_scanners
    if out:
        if out.detect_toxicity and out.detect_toxicity != "off":
            guardrails.append({
                "guardrail_name": "output_toxicity",
                "guardrail_config": {
                    "action": out.detect_toxicity,
                    "threshold": out.toxicity_threshold,
                },
            })

        if out.detect_refusal and out.detect_refusal != "off":
            guardrails.append({
                "guardrail_name": "output_refusal",
                "guardrail_config": {"action": out.detect_refusal},
            })

        if out.detect_sensitive_data and out.detect_sensitive_data != "off":
            guardrails.append({
                "guardrail_name": "output_sensitive_data",
                "guardrail_config": {"action": out.detect_sensitive_data},
            })

        if out.check_relevance and out.check_relevance != "off":
            guardrails.append({
                "guardrail_name": "output_relevance",
                "guardrail_config": {"action": out.check_relevance},
            })

        if out.detect_gibberish and out.detect_gibberish != "off":
            guardrails.append({
                "guardrail_name": "output_gibberish",
                "guardrail_config": {"action": out.detect_gibberish},
            })

        if out.detect_bias and out.detect_bias != "off":
            guardrails.append({
                "guardrail_name": "output_bias",
                "guardrail_config": {"action": out.detect_bias},
            })

        if out.check_factual_consistency and out.check_factual_consistency != "off":
            guardrails.append({
                "guardrail_name": "output_factual_consistency",
                "guardrail_config": {"action": out.check_factual_consistency},
            })

        if out.ban_topics:
            guardrails.append({
                "guardrail_name": "output_topic_ban",
                "guardrail_config": {"topics": list(out.ban_topics)},
            })

        if out.allowed_languages:
            guardrails.append({
                "guardrail_name": "output_language_restriction",
                "guardrail_config": {"languages": list(out.allowed_languages)},
            })

        if out.ban_competitors:
            guardrails.append({
                "guardrail_name": "output_competitor_ban",
                "guardrail_config": {"competitors": list(out.ban_competitors)},
            })

    # ── Tool call policy (split into sub-guardrails) ───────────────────

    tcp = cfg.tool_call_policy
    if tcp:
        has_network = (
            tcp.allowed_url_patterns
            or tcp.blocked_url_patterns
            or tcp.blocked_ip_ranges != _DEFAULT_TCP.blocked_ip_ranges
        )
        if has_network:
            guardrails.append({
                "guardrail_name": "tool_network_policy",
                "guardrail_config": {
                    "allowed_url_patterns": tcp.allowed_url_patterns,
                    "blocked_url_patterns": tcp.blocked_url_patterns,
                    "blocked_ip_ranges": tcp.blocked_ip_ranges,
                },
            })

        has_db = (
            tcp.allowed_sql_operations != _DEFAULT_TCP.allowed_sql_operations
            or tcp.blocked_tables
            or tcp.max_query_rows != _DEFAULT_TCP.max_query_rows
        )
        if has_db:
            guardrails.append({
                "guardrail_name": "tool_database_policy",
                "guardrail_config": {
                    "allowed_sql_operations": tcp.allowed_sql_operations,
                    "blocked_tables": tcp.blocked_tables,
                    "max_query_rows": tcp.max_query_rows,
                },
            })

        has_fs = (
            tcp.allowed_file_extensions
            or tcp.blocked_file_paths
            or tcp.max_file_size_mb != _DEFAULT_TCP.max_file_size_mb
        )
        if has_fs:
            guardrails.append({
                "guardrail_name": "tool_filesystem_policy",
                "guardrail_config": {
                    "allowed_file_extensions": tcp.allowed_file_extensions,
                    "blocked_file_paths": tcp.blocked_file_paths,
                    "max_file_size_mb": tcp.max_file_size_mb,
                },
            })

        has_exec = (
            tcp.max_tool_calls_per_execution != _DEFAULT_TCP.max_tool_calls_per_execution
            or tcp.tool_timeout_seconds != _DEFAULT_TCP.tool_timeout_seconds
        )
        if has_exec:
            guardrails.append({
                "guardrail_name": "tool_execution_limits",
                "guardrail_config": {
                    "max_tool_calls_per_execution": tcp.max_tool_calls_per_execution,
                    "tool_timeout_seconds": tcp.tool_timeout_seconds,
                },
            })

    # ── Token budget ───────────────────────────────────────────────────

    if cfg.token_budget:
        tb = cfg.token_budget
        guardrails.append({
            "guardrail_name": "token_budget",
            "guardrail_config": {
                "max_input_tokens_per_execution": tb.max_input_tokens_per_execution,
                "max_output_tokens_per_execution": tb.max_output_tokens_per_execution,
                "max_total_tokens_per_execution": tb.max_total_tokens_per_execution,
                "max_llm_calls_per_execution": tb.max_llm_calls_per_execution,
                "warn_at_percentage": tb.warn_at_percentage,
            },
        })

    # ── Provider content filter ────────────────────────────────────────

    if cfg.provider_content_filter and cfg.provider_content_filter.enabled:
        guardrails.append({
            "guardrail_name": "provider_content_filter",
            "guardrail_config": {
                "categories": list(cfg.provider_content_filter.categories),
            },
        })

    # ── Custom filters (one entry per enabled filter) ──────────────────

    for f in cfg.custom_filters:
        if not f.enabled:
            continue
        gc: Dict[str, Any] = {
            "id": f.id,
            "name": f.name,
            "filter_type": f.filter_type,
            "action": f.action,
            "scope": f.scope,
            "priority": f.priority,
            "message": f.message,
        }
        if f.filter_type == "python_code":
            gc["python_code"] = f.python_code
        elif f.filter_type == "llm_judge":
            gc["judge_prompt"] = f.judge_prompt
            gc["judge_llm_config"] = f.judge_llm_config.to_dict() if f.judge_llm_config else None
            gc["judge_threshold"] = f.judge_threshold
        elif f.filter_type == "declarative":
            gc["template_id"] = f.template_id
            gc["template_params"] = f.template_params

        guardrails.append({
            "guardrail_name": "custom_filter",
            "guardrail_config": gc,
        })

    return guardrails


# ---------------------------------------------------------------------------
# Pipeline entry: policy wrapper around decomposed guardrails
# ---------------------------------------------------------------------------


def config_to_pipeline_entry(cfg: GuardrailsConfig) -> Dict[str, Any]:
    """Serialize a GuardrailsConfig as a decomposed pipeline entry.

    Returns a dict with policy-level metadata and a ``guardrails`` list
    of individually named guardrails.
    """
    return {
        "policy_name": cfg.policy_name or "",
        "policy_id": cfg.policy_id or "",
        "enforcement_mode": cfg.enforcement_mode,
        "priority": cfg.priority,
        "enabled": cfg.enabled,
        "guardrails": decompose_config(cfg),
    }


# ---------------------------------------------------------------------------
# Compose: decomposed format → GuardrailsConfig (import / round-trip)
# ---------------------------------------------------------------------------


def pipeline_entry_to_config(entry: Dict[str, Any]) -> GuardrailsConfig:
    """Reconstruct a GuardrailsConfig from a decomposed pipeline entry.

    If *entry* does not contain a ``"guardrails"`` key, falls back to
    ``GuardrailsConfig.from_dict(entry)`` for backward compatibility.
    """
    if "guardrails" not in entry:
        return GuardrailsConfig.from_dict(entry)

    from backend.models.workflow.configs.guardrails import (
        CustomFilter,
        OutputScanners,
        PatternEntry,
        PatternRule,
        ProviderContentFilter,
        TokenBudget,
    )
    from backend.models.workflow.configs.llm import LLMConfig

    kwargs: Dict[str, Any] = {
        "enabled": entry.get("enabled", True),
        "enforcement_mode": entry.get("enforcement_mode", "enforce"),
        "priority": entry.get("priority", 100),
        "policy_id": entry.get("policy_id", ""),
        "policy_name": entry.get("policy_name", ""),
    }

    pattern_rules: List = []
    output_scanner_fields: Dict[str, Any] = {}
    tcp_fields: Dict[str, Any] = {}
    custom_filters: List = []

    for g in entry.get("guardrails", []):
        name = g.get("guardrail_name", "")
        gc = g.get("guardrail_config", {})

        # ── Input behavioral ───────────────────────────────────────
        if name == "prompt_injection":
            kwargs["detect_prompt_injection"] = gc.get("action", "block")
            kwargs["prompt_injection_threshold"] = gc.get("threshold", 0.75)
        elif name == "jailbreak_detection":
            kwargs["detect_jailbreak_attempts"] = gc.get("action", "block")
            kwargs["jailbreak_threshold"] = gc.get("threshold", 0.75)
        elif name == "toxicity_detection":
            kwargs["detect_toxicity"] = gc.get("action", "block")
            kwargs["toxicity_threshold"] = gc.get("threshold", 0.5)
        elif name == "pii_anonymization":
            kwargs["anonymize_pii"] = gc.get("action", "anonymize")
            kwargs["use_faker"] = gc.get("use_faker", False)
            kwargs["pii_entity_types"] = gc.get("entity_types", [])
        elif name == "secret_detection":
            kwargs["detect_secrets"] = gc.get("action", "block")
        elif name == "gibberish_detection":
            kwargs["detect_gibberish"] = gc.get("action", "block")
        elif name == "code_detection":
            kwargs["ban_code"] = gc.get("action", "block")
        elif name == "topic_ban":
            kwargs["ban_topics"] = gc.get("topics", [])
        elif name == "language_restriction":
            kwargs["allowed_languages"] = gc.get("languages", [])
        elif name == "token_limit":
            kwargs["max_input_tokens"] = gc.get("max_tokens")
        elif name == "system_prompt_protection":
            kwargs["system_prompt_protection"] = gc.get("enabled", True)
        elif name == "input_length_limit":
            kwargs["max_input_length"] = gc.get("max_length", 50000)
        elif name == "output_length_limit":
            kwargs["max_output_length"] = gc.get("max_length", 100000)
        elif name == "llm_judge":
            kwargs["judge_llm_config"] = LLMConfig(**gc) if gc else None

        # ── Pattern rules ──────────────────────────────────────────
        elif name == "pattern_rule":
            pattern_rules.append(PatternRule(
                name=gc.get("name", ""),
                patterns=[PatternEntry(**p) for p in gc.get("patterns", [])],
                action=gc.get("action", "block"),
                applies_to=gc.get("applies_to", "both"),
                message=gc.get("message", ""),
                preset_id=gc.get("preset_id", ""),
            ))

        # ── Output scanners ────────────────────────────────────────
        elif name == "output_toxicity":
            output_scanner_fields["detect_toxicity"] = gc.get("action", "block")
            output_scanner_fields["toxicity_threshold"] = gc.get("threshold", 0.5)
        elif name == "output_refusal":
            output_scanner_fields["detect_refusal"] = gc.get("action", "block")
        elif name == "output_sensitive_data":
            output_scanner_fields["detect_sensitive_data"] = gc.get("action", "block")
        elif name == "output_relevance":
            output_scanner_fields["check_relevance"] = gc.get("action", "block")
        elif name == "output_gibberish":
            output_scanner_fields["detect_gibberish"] = gc.get("action", "block")
        elif name == "output_bias":
            output_scanner_fields["detect_bias"] = gc.get("action", "block")
        elif name == "output_factual_consistency":
            output_scanner_fields["check_factual_consistency"] = gc.get("action", "block")
        elif name == "output_topic_ban":
            output_scanner_fields["ban_topics"] = gc.get("topics", [])
        elif name == "output_language_restriction":
            output_scanner_fields["allowed_languages"] = gc.get("languages", [])
        elif name == "output_competitor_ban":
            output_scanner_fields["ban_competitors"] = gc.get("competitors", [])

        # ── Tool policies ──────────────────────────────────────────
        elif name == "tool_network_policy":
            tcp_fields["allowed_url_patterns"] = gc.get("allowed_url_patterns", [])
            tcp_fields["blocked_url_patterns"] = gc.get("blocked_url_patterns", [])
            tcp_fields["blocked_ip_ranges"] = gc.get("blocked_ip_ranges", [])
        elif name == "tool_database_policy":
            tcp_fields["allowed_sql_operations"] = gc.get("allowed_sql_operations", ["SELECT"])
            tcp_fields["blocked_tables"] = gc.get("blocked_tables", [])
            tcp_fields["max_query_rows"] = gc.get("max_query_rows", 1000)
        elif name == "tool_filesystem_policy":
            tcp_fields["allowed_file_extensions"] = gc.get("allowed_file_extensions", [])
            tcp_fields["blocked_file_paths"] = gc.get("blocked_file_paths", [])
            tcp_fields["max_file_size_mb"] = gc.get("max_file_size_mb", 10.0)
        elif name == "tool_execution_limits":
            tcp_fields["max_tool_calls_per_execution"] = gc.get("max_tool_calls_per_execution", 50)
            tcp_fields["tool_timeout_seconds"] = gc.get("tool_timeout_seconds", 60)

        # ── Token budget ───────────────────────────────────────────
        elif name == "token_budget":
            kwargs["token_budget"] = TokenBudget(
                max_input_tokens_per_execution=gc.get("max_input_tokens_per_execution"),
                max_output_tokens_per_execution=gc.get("max_output_tokens_per_execution"),
                max_total_tokens_per_execution=gc.get("max_total_tokens_per_execution"),
                max_llm_calls_per_execution=gc.get("max_llm_calls_per_execution", 20),
                warn_at_percentage=gc.get("warn_at_percentage", 0.8),
            )

        # ── Provider content filter ────────────────────────────────
        elif name == "provider_content_filter":
            kwargs["provider_content_filter"] = ProviderContentFilter(
                enabled=True,
                categories=gc.get("categories", []),
            )

        # ── Custom filters ─────────────────────────────────────────
        elif name == "custom_filter":
            custom_filters.append(CustomFilter(
                id=gc.get("id", ""),
                name=gc.get("name", ""),
                filter_type=gc.get("filter_type", "python_code"),
                action=gc.get("action", "block"),
                scope=gc.get("scope", "both"),
                enabled=True,
                priority=gc.get("priority", 100),
                python_code=gc.get("python_code", ""),
                judge_prompt=gc.get("judge_prompt", ""),
                judge_llm_config=LLMConfig(**gc["judge_llm_config"]) if gc.get("judge_llm_config") else None,
                judge_threshold=gc.get("judge_threshold", 0.7),
                template_id=gc.get("template_id", ""),
                template_params=gc.get("template_params", {}),
                message=gc.get("message", ""),
            ))

    if pattern_rules:
        kwargs["pattern_rules"] = pattern_rules
    if output_scanner_fields:
        kwargs["output_scanners"] = OutputScanners(**output_scanner_fields)
    if tcp_fields:
        kwargs["tool_call_policy"] = ToolCallPolicy(**tcp_fields)
    if custom_filters:
        kwargs["custom_filters"] = custom_filters

    return GuardrailsConfig(**kwargs)
