"""Guardrails configuration for workflow and agent safety.

This module defines dataclasses for configuring guardrails that enforce
safety policies on inputs, outputs, tool calls, token budgets, and
behavioral patterns within AI workflow executions.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from backend.models.workflow.configs.llm import LLMConfig


@dataclass
class PatternEntry:
    """A single labeled regex pattern within a PatternRule.

    Attributes:
        label: Human-readable name describing what this pattern detects
        regex: The regex pattern string
    """

    label: str = ""
    regex: str = ""


@dataclass
class PatternRule:
    """A pattern matching rule for data loss prevention.

    Contains one or more labeled regex patterns that are evaluated together
    under the same action and scope.

    Attributes:
        name: Human-readable rule name
        patterns: List of labeled regex patterns to match against content
        action: What to do on match - "block", "warn", or "redact"
        applies_to: Where to apply - "input", "output", or "both"
        message: Custom message shown when rule triggers
        preset_id: If this rule originated from a built-in preset, its ID (e.g. "ssn_us")
    """

    name: str = ""
    patterns: List[PatternEntry] = field(default_factory=list)
    action: str = "block"  # "block" | "warn" | "redact"
    applies_to: str = "both"  # "input" | "output" | "both"
    message: str = ""
    preset_id: str = ""


@dataclass
class ToolCallPolicy:
    """Policy for controlling tool behavior.

    Attributes:
        allowed_url_patterns: Glob patterns for allowed URLs (empty = allow all)
        blocked_url_patterns: Glob patterns for blocked URLs
        blocked_ip_ranges: CIDR ranges blocked for SSRF protection
        allowed_sql_operations: Allowed SQL operations (e.g. ["SELECT"])
        blocked_tables: Table names that cannot be queried
        max_query_rows: Maximum rows a query can return
        allowed_file_extensions: Allowed file extensions for writes (empty = allow all)
        blocked_file_paths: Path patterns blocked for file writes
        max_file_size_mb: Maximum file size in megabytes
        max_tool_calls_per_execution: Total tool call limit per execution
        tool_timeout_seconds: Timeout for individual tool calls
    """

    allowed_url_patterns: List[str] = field(default_factory=list)
    blocked_url_patterns: List[str] = field(default_factory=list)
    blocked_ip_ranges: List[str] = field(
        default_factory=lambda: [
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
            "127.0.0.0/8",
            "169.254.0.0/16",
            "0.0.0.0/8",
        ]
    )
    allowed_sql_operations: List[str] = field(default_factory=lambda: ["SELECT"])
    blocked_tables: List[str] = field(default_factory=list)
    max_query_rows: int = 1000
    allowed_file_extensions: List[str] = field(default_factory=list)
    blocked_file_paths: List[str] = field(default_factory=list)
    max_file_size_mb: float = 1024.0
    max_tool_calls_per_execution: int = 50
    tool_timeout_seconds: int = 60


@dataclass
class TokenBudget:
    """Token and cost budget limits per execution.

    Attributes:
        max_input_tokens_per_execution: Max input tokens across all LLM calls
        max_output_tokens_per_execution: Max output tokens across all LLM calls
        max_total_tokens_per_execution: Max total tokens across all LLM calls
        max_llm_calls_per_execution: Max number of LLM invocations
        warn_at_percentage: Emit warning when usage hits this fraction (0.0-1.0)
    """

    max_input_tokens_per_execution: Optional[int] = None
    max_output_tokens_per_execution: Optional[int] = None
    max_total_tokens_per_execution: Optional[int] = None
    max_llm_calls_per_execution: int = 20
    warn_at_percentage: float = 0.8


@dataclass
class BehavioralGuardrails:
    """Settings for behavioral safety checks.

    .. deprecated::
        These fields have been promoted to top-level on ``GuardrailsConfig``.
        This class is kept only for backward-compatible deserialization of
        legacy stored configs. Do not construct new instances.

    Supports LLM Guard scanners for input detection and LLM-as-judge as a
    fallback when no scanner flags are set.

    Attributes:
        detect_prompt_injection: Prompt injection scanner action — "off", "block", or "warn"
        detect_jailbreak_attempts: Jailbreak scanner action — "off", "block", or "warn"
        system_prompt_protection: Wrap system prompt with anti-override anchoring
        max_input_length: Maximum input character length
        max_output_length: Maximum output character length
        judge_llm_config: LLM configuration for the behavioral judge model
        detect_toxicity: Toxicity input scanner action — "off", "block", or "warn"
        anonymize_pii: PII detection action — "off", "block", "warn", or "anonymize" (vault round-trip)
        use_faker: When anonymize_pii is "anonymize", replace PII with realistic fake data instead of [REDACTED_*] placeholders
        pii_entity_types: List of PII entity types to detect (empty = all types). Supported: CREDIT_CARD, CRYPTO, EMAIL_ADDRESS, IBAN_CODE, IP_ADDRESS, PERSON, PHONE_NUMBER, US_SSN, US_BANK_NUMBER, CREDIT_CARD_RE, UUID, EMAIL_ADDRESS_RE, US_SSN_RE
        detect_secrets: Secrets input scanner action — "off", "block", or "warn"
        ban_topics: List of topic strings to ban via LLM Guard BanTopics scanner
        allowed_languages: List of language codes to allow via LLM Guard Language scanner
        detect_gibberish: Gibberish input scanner action — "off", "block", or "warn"
        ban_code: BanCode input scanner action — "off", "block", or "warn"
        max_input_tokens: Maximum input token count via LLM Guard TokenLimit scanner
        prompt_injection_threshold: Confidence threshold for the prompt injection scanner (0.0-1.0)
        jailbreak_threshold: Confidence threshold for the jailbreak scanner (0.0-1.0)
        toxicity_threshold: Confidence threshold for input toxicity scanner (0.0-1.0)
    """

    detect_prompt_injection: str = "block"  # "off" | "block" | "warn"
    detect_jailbreak_attempts: str = "block"  # "off" | "block" | "warn"
    system_prompt_protection: bool = True
    max_input_length: int = 50000
    max_output_length: int = 100000
    judge_llm_config: Optional["LLMConfig"] = None
    detect_toxicity: str = "off"  # "off" | "block" | "warn"
    anonymize_pii: str = "off"  # "off" | "block" | "warn" | "anonymize"
    use_faker: bool = False
    pii_entity_types: List[str] = field(default_factory=list)  # Empty = all types
    detect_secrets: str = "off"  # "off" | "block" | "warn"
    ban_topics: List[str] = field(default_factory=list)
    allowed_languages: List[str] = field(default_factory=list)
    detect_gibberish: str = "off"  # "off" | "block" | "warn"
    ban_code: str = "off"  # "off" | "block" | "warn"
    max_input_tokens: Optional[int] = None
    prompt_injection_threshold: float = 0.75
    jailbreak_threshold: float = 0.75
    toxicity_threshold: float = 0.5


@dataclass
class OutputScanners:
    """LLM Guard output scanner configuration.

    Controls which ML-based scanners run on LLM output.

    Attributes:
        detect_toxicity: Toxicity output scanner action — "off", "block", or "warn"
        detect_refusal: No-refusal output scanner action — "off", "block", or "warn"
        detect_sensitive_data: Sensitive data output scanner action — "off", "block", or "warn"
        check_relevance: Relevance output scanner action — "off", "block", or "warn"
        detect_gibberish: Gibberish output scanner action — "off", "block", or "warn"
        detect_bias: Bias output scanner action — "off", "block", or "warn"
        check_factual_consistency: Factual consistency output scanner action — "off", "block", or "warn"
        toxicity_threshold: Confidence threshold for output toxicity scanner (0.0-1.0)
    """

    detect_toxicity: str = "off"  # "off" | "block" | "warn"
    detect_refusal: str = "off"  # "off" | "block" | "warn"
    detect_sensitive_data: str = "off"  # "off" | "block" | "warn"
    ban_topics: List[str] = field(default_factory=list)
    allowed_languages: List[str] = field(default_factory=list)
    check_relevance: str = "off"  # "off" | "block" | "warn"
    detect_gibberish: str = "off"  # "off" | "block" | "warn"
    ban_competitors: List[str] = field(default_factory=list)
    detect_bias: str = "off"  # "off" | "block" | "warn"
    check_factual_consistency: str = "off"  # "off" | "block" | "warn"
    toxicity_threshold: float = 0.5


@dataclass
class ProviderContentFilter:
    """Configuration for handling provider-level content filter responses.

    Cloud LLM providers (Azure OpenAI, OpenAI) have built-in content safety
    filters that may reject requests.  When enabled, the guardrails engine
    intercepts these rejections and records them as guardrail violations.
    The parent policy's enforcement_mode controls whether the execution
    fails (enforce) or simply logs the event (audit).

    Attributes:
        enabled: Whether to treat provider content filter errors as violations
        categories: Which filter categories to act on (empty = all).
                    Common Azure categories: violence, sexual, self_harm,
                    hate_speech, jailbreak, protected_material.
    """

    enabled: bool = True
    categories: List[str] = field(default_factory=list)


@dataclass
class CustomFilter:
    """A user-defined filter for ingress/egress content processing.

    Supports three execution modes:
    - python_code: User-written Python function, executed in a restricted sandbox
    - llm_judge: Natural language policy prompt, evaluated by an LLM judge
    - declarative: Predefined template with configurable parameters

    Attributes:
        id: Unique filter identifier (UUID)
        name: Human-readable filter name
        filter_type: Execution mode — "python_code", "llm_judge", or "declarative"
        action: What to do when filter triggers — "block", "warn", or "transform"
        scope: Where to apply — "ingress" (before LLM), "egress" (after LLM), or "both"
        enabled: Per-filter toggle
        priority: Execution order (lower = first, 0-999)
        python_code: Python function source code (for python_code type)
        judge_prompt: Natural language policy prompt (for llm_judge type)
        judge_llm_config: LLM configuration for the judge model (for llm_judge type)
        judge_threshold: Confidence threshold for triggering (for llm_judge type)
        template_id: Predefined template identifier (for declarative type)
        template_params: Template-specific parameters (for declarative type)
        message: Custom violation/transform message
    """

    id: str = ""
    name: str = ""
    filter_type: str = "python_code"  # "python_code" | "llm_judge" | "declarative"
    action: str = "block"  # "block" | "warn" | "transform"
    scope: str = "both"  # "ingress" | "egress" | "both"
    enabled: bool = True
    priority: int = 100
    python_code: str = ""
    judge_prompt: str = ""
    judge_llm_config: Optional["LLMConfig"] = None
    judge_threshold: float = 0.7
    template_id: str = ""
    template_params: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class GuardrailsConfig:
    """Complete guardrails configuration for an agent or workflow.

    Can be set at the workflow level (applies to all agents) or per-agent
    (overrides workflow defaults). Supports three enforcement modes:
    - "enforce": Block violations
    - "audit": Log violations but allow through
    - "disabled": No checking

    Attributes:
        enabled: Master toggle for guardrails
        enforcement_mode: How violations are handled
        inherit_from_workflow: Whether agent inherits workflow-level guardrails
        pattern_rules: List of pattern matching rules for DLP
        detect_prompt_injection: Prompt injection scanner action
        detect_jailbreak_attempts: Jailbreak scanner action
        system_prompt_protection: Wrap system prompt with anti-override anchoring
        max_input_length: Maximum input character length
        max_output_length: Maximum output character length
        judge_llm_config: LLM configuration for the behavioral judge model
        detect_toxicity: Toxicity input scanner action
        anonymize_pii: PII detection action
        use_faker: Use realistic fake data for PII anonymization
        pii_entity_types: PII entity types to detect (empty = all)
        detect_secrets: Secrets input scanner action
        ban_topics: Topic strings to ban
        allowed_languages: Language codes to allow (empty = all)
        detect_gibberish: Gibberish input scanner action
        ban_code: Code detection scanner action
        max_input_tokens: Maximum input token count
        prompt_injection_threshold: Confidence threshold for prompt injection scanner
        jailbreak_threshold: Confidence threshold for jailbreak scanner
        toxicity_threshold: Confidence threshold for input toxicity scanner
        tool_call_policy: Policy for tool call restrictions
        token_budget: Token/cost budget limits
        output_scanners: LLM Guard output scanner configuration
        provider_content_filter: Provider content filter handling
        custom_filters: User-defined ingress/egress filters
    """

    enabled: bool = False
    enforcement_mode: str = "enforce"  # "enforce" | "audit" | "disabled"
    inherit_from_workflow: bool = True
    pattern_rules: List[PatternRule] = field(default_factory=list)

    # Behavioral guardrail fields (formerly nested in BehavioralGuardrails)
    detect_prompt_injection: str = "off"  # "off" | "block" | "warn"
    detect_jailbreak_attempts: str = "off"  # "off" | "block" | "warn"
    system_prompt_protection: bool = False
    max_input_length: int = 50000
    max_output_length: int = 100000
    judge_llm_config: Optional["LLMConfig"] = None
    detect_toxicity: str = "off"  # "off" | "block" | "warn"
    anonymize_pii: str = "off"  # "off" | "block" | "warn" | "anonymize"
    use_faker: bool = False
    pii_entity_types: List[str] = field(default_factory=list)
    detect_secrets: str = "off"  # "off" | "block" | "warn"
    ban_topics: List[str] = field(default_factory=list)
    allowed_languages: List[str] = field(default_factory=list)
    detect_gibberish: str = "off"  # "off" | "block" | "warn"
    ban_code: str = "off"  # "off" | "block" | "warn"
    max_input_tokens: Optional[int] = None
    prompt_injection_threshold: float = 0.75
    jailbreak_threshold: float = 0.75
    toxicity_threshold: float = 0.5

    tool_call_policy: Optional[ToolCallPolicy] = None
    token_budget: Optional[TokenBudget] = None
    # Deprecated: kept for from_dict() backward compatibility only.
    behavioral: Optional[BehavioralGuardrails] = None
    provider_content_filter: Optional[ProviderContentFilter] = None
    output_scanners: Optional[OutputScanners] = None
    custom_filters: List[CustomFilter] = field(default_factory=list)
    priority: int = 0
    policy_id: str = ""
    policy_name: str = ""

    @property
    def has_behavioral_checks(self) -> bool:
        """Return True if any behavioral scanner field is non-default."""
        return (
            self.detect_prompt_injection != "off"
            or self.detect_jailbreak_attempts != "off"
            or self.system_prompt_protection
            or self.detect_toxicity != "off"
            or self.anonymize_pii != "off"
            or self.detect_secrets != "off"
            or self.detect_gibberish != "off"
            or self.ban_code != "off"
            or bool(self.ban_topics)
            or bool(self.allowed_languages)
            or self.max_input_tokens is not None
            or self.judge_llm_config is not None
            or self.max_input_length != 50000
            or self.max_output_length != 100000
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the config
        """
        result: Dict[str, Any] = {
            "enabled": self.enabled,
            "enforcement_mode": self.enforcement_mode,
            "inherit_from_workflow": self.inherit_from_workflow,
            "priority": self.priority,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "pattern_rules": [
                {
                    "name": r.name,
                    "patterns": [
                        {"label": p.label, "regex": p.regex} for p in r.patterns
                    ],
                    "action": r.action,
                    "applies_to": r.applies_to,
                    "message": r.message,
                    "preset_id": r.preset_id,
                }
                for r in self.pattern_rules
            ],
            # Behavioral fields (top-level, no longer nested)
            "detect_prompt_injection": self.detect_prompt_injection,
            "detect_jailbreak_attempts": self.detect_jailbreak_attempts,
            "system_prompt_protection": self.system_prompt_protection,
            "max_input_length": self.max_input_length,
            "max_output_length": self.max_output_length,
            "detect_toxicity": self.detect_toxicity,
            "anonymize_pii": self.anonymize_pii,
            "use_faker": self.use_faker,
            "pii_entity_types": self.pii_entity_types,
            "detect_secrets": self.detect_secrets,
            "ban_topics": self.ban_topics,
            "allowed_languages": self.allowed_languages,
            "detect_gibberish": self.detect_gibberish,
            "ban_code": self.ban_code,
            "max_input_tokens": self.max_input_tokens,
            "prompt_injection_threshold": self.prompt_injection_threshold,
            "jailbreak_threshold": self.jailbreak_threshold,
            "toxicity_threshold": self.toxicity_threshold,
        }
        if self.judge_llm_config:
            result["judge_llm_config"] = self.judge_llm_config.to_dict()
        if self.tool_call_policy:
            result["tool_call_policy"] = {
                "allowed_url_patterns": self.tool_call_policy.allowed_url_patterns,
                "blocked_url_patterns": self.tool_call_policy.blocked_url_patterns,
                "blocked_ip_ranges": self.tool_call_policy.blocked_ip_ranges,
                "allowed_sql_operations": self.tool_call_policy.allowed_sql_operations,
                "blocked_tables": self.tool_call_policy.blocked_tables,
                "max_query_rows": self.tool_call_policy.max_query_rows,
                "allowed_file_extensions": self.tool_call_policy.allowed_file_extensions,
                "blocked_file_paths": self.tool_call_policy.blocked_file_paths,
                "max_file_size_mb": self.tool_call_policy.max_file_size_mb,
                "max_tool_calls_per_execution": self.tool_call_policy.max_tool_calls_per_execution,
                "tool_timeout_seconds": self.tool_call_policy.tool_timeout_seconds,
            }
        if self.token_budget:
            result["token_budget"] = {
                "max_input_tokens_per_execution": self.token_budget.max_input_tokens_per_execution,
                "max_output_tokens_per_execution": self.token_budget.max_output_tokens_per_execution,
                "max_total_tokens_per_execution": self.token_budget.max_total_tokens_per_execution,
                "max_llm_calls_per_execution": self.token_budget.max_llm_calls_per_execution,
                "warn_at_percentage": self.token_budget.warn_at_percentage,
            }
        if self.provider_content_filter:
            result["provider_content_filter"] = {
                "enabled": self.provider_content_filter.enabled,
                "categories": self.provider_content_filter.categories,
            }
        if self.output_scanners:
            result["output_scanners"] = {
                "detect_toxicity": self.output_scanners.detect_toxicity,
                "detect_refusal": self.output_scanners.detect_refusal,
                "detect_sensitive_data": self.output_scanners.detect_sensitive_data,
                "ban_topics": self.output_scanners.ban_topics,
                "allowed_languages": self.output_scanners.allowed_languages,
                "check_relevance": self.output_scanners.check_relevance,
                "detect_gibberish": self.output_scanners.detect_gibberish,
                "ban_competitors": self.output_scanners.ban_competitors,
                "detect_bias": self.output_scanners.detect_bias,
                "check_factual_consistency": self.output_scanners.check_factual_consistency,
                "toxicity_threshold": self.output_scanners.toxicity_threshold,
            }
        if self.custom_filters:
            result["custom_filters"] = [
                {
                    "id": f.id,
                    "name": f.name,
                    "filter_type": f.filter_type,
                    "action": f.action,
                    "scope": f.scope,
                    "enabled": f.enabled,
                    "priority": f.priority,
                    "python_code": f.python_code,
                    "judge_prompt": f.judge_prompt,
                    "judge_llm_config": f.judge_llm_config.to_dict()
                    if f.judge_llm_config
                    else None,
                    "judge_threshold": f.judge_threshold,
                    "template_id": f.template_id,
                    "template_params": f.template_params,
                    "message": f.message,
                }
                for f in self.custom_filters
            ]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuardrailsConfig":
        """Create GuardrailsConfig from dictionary.

        Handles both the new flat format (behavioral fields at top level)
        and the legacy nested format (behavioral fields inside a
        ``"behavioral"`` dict). Legacy format fields are merged to top
        level; top-level values take precedence if both exist.

        Args:
            data: Dictionary containing guardrails configuration

        Returns:
            GuardrailsConfig instance
        """
        if not data:
            return cls()

        data = dict(data)  # shallow copy to avoid mutating caller's dict
        # Migration safety: silently discard old attribution fields
        data.pop("source_policies", None)
        data.pop("rule_policy_map", None)

        # --- Backward compat: flatten legacy "behavioral" nested dict ---
        bh_data = data.pop("behavioral", None)
        if isinstance(bh_data, dict):
            bh_data = dict(bh_data)  # shallow copy
            # Remove deprecated keys from the behavioral dict
            for _dep in ("detect_instruction_override", "use_local_models",
                         "local_model_threshold", "fallback_to_llm"):
                bh_data.pop(_dep, None)
            # Merge into top-level data; existing top-level keys win
            for k, v in bh_data.items():
                data.setdefault(k, v)
        elif isinstance(bh_data, BehavioralGuardrails):
            # Dataclass instance — extract fields to top-level
            for f in BehavioralGuardrails.__dataclass_fields__:
                data.setdefault(f, getattr(bh_data, f))

        # --- Migration: bool → str action enums for behavioral fields ---
        raw_pii = data.get("anonymize_pii")
        if isinstance(raw_pii, bool):
            data["anonymize_pii"] = "anonymize" if raw_pii else "off"

        for _flag in (
            "detect_prompt_injection",
            "detect_jailbreak_attempts",
            "detect_toxicity",
            "detect_gibberish",
            "ban_code",
            "detect_secrets",
        ):
            _raw = data.get(_flag)
            if isinstance(_raw, bool):
                data[_flag] = "block" if _raw else "off"

        # --- Parse judge_llm_config ---
        from backend.models.workflow.configs.llm import LLMConfig

        judge_llm_config = None
        jlc_data = data.pop("judge_llm_config", None)
        if jlc_data:
            if isinstance(jlc_data, dict):
                judge_llm_config = LLMConfig(**jlc_data)
            elif isinstance(jlc_data, LLMConfig):
                judge_llm_config = jlc_data

        # --- Pattern rules ---
        pattern_rules = []
        raw_rules = data.get("pattern_rules") or data.get("content_filter_rules", [])
        for rule_data in raw_rules:
            if isinstance(rule_data, dict):
                rule_data = dict(rule_data)  # shallow copy
                # Migrate legacy single-pattern string → PatternEntry list
                if "pattern" in rule_data and "patterns" not in rule_data:
                    legacy = rule_data.pop("pattern", "")
                    rule_data["patterns"] = (
                        [PatternEntry(regex=legacy)] if legacy else []
                    )
                elif "pattern" in rule_data:
                    rule_data.pop("pattern", None)
                # Normalise patterns list: bare strings → PatternEntry
                raw_patterns = rule_data.get("patterns", [])
                normalised: List[PatternEntry] = []
                for p in raw_patterns:
                    if isinstance(p, PatternEntry):
                        normalised.append(p)
                    elif isinstance(p, dict):
                        normalised.append(
                            PatternEntry(
                                label=p.get("label", ""), regex=p.get("regex", "")
                            )
                        )
                    elif isinstance(p, str):
                        normalised.append(PatternEntry(regex=p))
                rule_data["patterns"] = normalised
                pattern_rules.append(PatternRule(**rule_data))
            elif isinstance(rule_data, PatternRule):
                pattern_rules.append(rule_data)

        tool_call_policy = None
        tcp_data = data.get("tool_call_policy")
        if tcp_data:
            if isinstance(tcp_data, dict):
                tool_call_policy = ToolCallPolicy(**tcp_data)
            elif isinstance(tcp_data, ToolCallPolicy):
                tool_call_policy = tcp_data

        token_budget = None
        tb_data = data.get("token_budget")
        if tb_data:
            if isinstance(tb_data, dict):
                token_budget = TokenBudget(**tb_data)
            elif isinstance(tb_data, TokenBudget):
                token_budget = tb_data

        provider_content_filter = None
        pcf_data = data.get("provider_content_filter")
        if pcf_data:
            if isinstance(pcf_data, dict):
                provider_content_filter = ProviderContentFilter(
                    enabled=pcf_data.get("enabled", True),
                    categories=pcf_data.get("categories", []),
                )
            elif isinstance(pcf_data, ProviderContentFilter):
                provider_content_filter = pcf_data

        output_scanners = None
        os_data = data.get("output_scanners")
        if os_data:
            if isinstance(os_data, dict):
                os_data = dict(os_data)  # shallow copy
                # Migration: output scanner bool → str action enum
                _os_bool_defaults = {
                    "detect_toxicity": "block",
                    "detect_refusal": "warn",
                    "detect_sensitive_data": "warn",
                    "check_relevance": "warn",
                    "detect_gibberish": "block",
                    "detect_bias": "warn",
                    "check_factual_consistency": "warn",
                }
                for _flag, _default_action in _os_bool_defaults.items():
                    _raw = os_data.get(_flag)
                    if isinstance(_raw, bool):
                        os_data[_flag] = _default_action if _raw else "off"
                output_scanners = OutputScanners(**os_data)
            elif isinstance(os_data, OutputScanners):
                output_scanners = os_data

        custom_filters = []
        for cf_data in data.get("custom_filters", []):
            if isinstance(cf_data, dict):
                cf_data = dict(cf_data)  # shallow copy
                cf_jlc_data = cf_data.pop("judge_llm_config", None)
                cf_judge_llm_config = None
                if cf_jlc_data:
                    if isinstance(cf_jlc_data, dict):
                        cf_judge_llm_config = LLMConfig(**cf_jlc_data)
                    elif isinstance(cf_jlc_data, LLMConfig):
                        cf_judge_llm_config = cf_jlc_data
                custom_filters.append(
                    CustomFilter(**cf_data, judge_llm_config=cf_judge_llm_config)
                )
            elif isinstance(cf_data, CustomFilter):
                custom_filters.append(cf_data)

        return cls(
            enabled=data.get("enabled", False),
            enforcement_mode=data.get("enforcement_mode", "enforce"),
            inherit_from_workflow=data.get("inherit_from_workflow", True),
            pattern_rules=pattern_rules,
            detect_prompt_injection=data.get("detect_prompt_injection", "off"),
            detect_jailbreak_attempts=data.get("detect_jailbreak_attempts", "off"),
            system_prompt_protection=data.get("system_prompt_protection", False),
            max_input_length=data.get("max_input_length", 50000),
            max_output_length=data.get("max_output_length", 100000),
            judge_llm_config=judge_llm_config,
            detect_toxicity=data.get("detect_toxicity", "off"),
            anonymize_pii=data.get("anonymize_pii", "off"),
            use_faker=data.get("use_faker", False),
            pii_entity_types=data.get("pii_entity_types", []),
            detect_secrets=data.get("detect_secrets", "off"),
            ban_topics=data.get("ban_topics", []),
            allowed_languages=data.get("allowed_languages", []),
            detect_gibberish=data.get("detect_gibberish", "off"),
            ban_code=data.get("ban_code", "off"),
            max_input_tokens=data.get("max_input_tokens", None),
            prompt_injection_threshold=data.get("prompt_injection_threshold", 0.75),
            jailbreak_threshold=data.get("jailbreak_threshold", 0.75),
            toxicity_threshold=data.get("toxicity_threshold", 0.5),
            tool_call_policy=tool_call_policy,
            token_budget=token_budget,
            output_scanners=output_scanners,
            provider_content_filter=provider_content_filter,
            custom_filters=custom_filters,
            priority=data.get("priority", 0),
            policy_id=data.get("policy_id", ""),
            policy_name=data.get("policy_name", ""),
        )
