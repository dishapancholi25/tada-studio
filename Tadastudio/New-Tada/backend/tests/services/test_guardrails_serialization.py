"""Tests for guardrail serialization (decompose / compose / round-trip)."""

from backend.models.workflow.configs.guardrails import (
    CustomFilter,
    GuardrailsConfig,
    OutputScanners,
    PatternEntry,
    PatternRule,
    ProviderContentFilter,
    TokenBudget,
    ToolCallPolicy,
)
from backend.services.guardrails.serialization import (
    config_to_pipeline_entry,
    decompose_config,
    pipeline_entry_to_config,
)


class TestDecomposeConfig:
    """Tests for decompose_config()."""

    def test_empty_config_produces_no_guardrails(self):
        cfg = GuardrailsConfig()
        result = decompose_config(cfg)
        assert result == []

    def test_only_active_guardrails_included(self):
        cfg = GuardrailsConfig(
            enabled=True,
            detect_prompt_injection="warn",
            detect_jailbreak_attempts="off",
            detect_toxicity="off",
        )
        result = decompose_config(cfg)
        names = [g["guardrail_name"] for g in result]
        assert "prompt_injection" in names
        assert "jailbreak_detection" not in names
        assert "toxicity_detection" not in names

    def test_prompt_injection_config(self):
        cfg = GuardrailsConfig(
            detect_prompt_injection="block",
            prompt_injection_threshold=0.9,
        )
        result = decompose_config(cfg)
        pi = next(g for g in result if g["guardrail_name"] == "prompt_injection")
        assert pi["guardrail_config"] == {"action": "block", "threshold": 0.9}

    def test_pii_anonymization_config(self):
        cfg = GuardrailsConfig(
            anonymize_pii="anonymize",
            use_faker=True,
            pii_entity_types=["CREDIT_CARD", "US_SSN"],
        )
        result = decompose_config(cfg)
        pii = next(g for g in result if g["guardrail_name"] == "pii_anonymization")
        assert pii["guardrail_config"]["action"] == "anonymize"
        assert pii["guardrail_config"]["use_faker"] is True
        assert pii["guardrail_config"]["entity_types"] == ["CREDIT_CARD", "US_SSN"]

    def test_system_prompt_protection(self):
        cfg = GuardrailsConfig(system_prompt_protection=True)
        result = decompose_config(cfg)
        spp = next(g for g in result if g["guardrail_name"] == "system_prompt_protection")
        assert spp["guardrail_config"]["enabled"] is True

    def test_non_default_length_limits(self):
        cfg = GuardrailsConfig(max_input_length=20000, max_output_length=100000)
        result = decompose_config(cfg)
        names = [g["guardrail_name"] for g in result]
        assert "input_length_limit" in names
        assert "output_length_limit" not in names  # 100000 is default

    def test_pattern_rules_each_separate(self):
        cfg = GuardrailsConfig(
            pattern_rules=[
                PatternRule(name="SSN", patterns=[PatternEntry(label="SSN", regex=r"\d{3}-\d{2}-\d{4}")],
                            action="redact", applies_to="both", message="SSN detected"),
                PatternRule(name="Email", patterns=[PatternEntry(label="Email", regex=r"\S+@\S+")],
                            action="warn", applies_to="output", message="Email detected"),
            ]
        )
        result = decompose_config(cfg)
        pr_entries = [g for g in result if g["guardrail_name"] == "pattern_rule"]
        assert len(pr_entries) == 2
        assert pr_entries[0]["guardrail_config"]["name"] == "SSN"
        assert pr_entries[1]["guardrail_config"]["name"] == "Email"

    def test_output_scanners_decompose_individually(self):
        cfg = GuardrailsConfig(
            output_scanners=OutputScanners(
                detect_toxicity="warn",
                detect_refusal="block",
                detect_bias="off",
                toxicity_threshold=0.8,
            ),
        )
        result = decompose_config(cfg)
        names = [g["guardrail_name"] for g in result]
        assert "output_toxicity" in names
        assert "output_refusal" in names
        assert "output_bias" not in names

        tox = next(g for g in result if g["guardrail_name"] == "output_toxicity")
        assert tox["guardrail_config"] == {"action": "warn", "threshold": 0.8}

    def test_tool_policy_splits(self):
        cfg = GuardrailsConfig(
            tool_call_policy=ToolCallPolicy(
                blocked_url_patterns=["*.evil.com"],
                blocked_tables=["secrets"],
                max_file_size_mb=5.0,
                tool_timeout_seconds=30,
            ),
        )
        result = decompose_config(cfg)
        names = [g["guardrail_name"] for g in result]
        assert "tool_network_policy" in names
        assert "tool_database_policy" in names
        assert "tool_filesystem_policy" in names
        assert "tool_execution_limits" in names

    def test_token_budget(self):
        cfg = GuardrailsConfig(
            token_budget=TokenBudget(max_total_tokens_per_execution=50000),
        )
        result = decompose_config(cfg)
        tb = next(g for g in result if g["guardrail_name"] == "token_budget")
        assert tb["guardrail_config"]["max_total_tokens_per_execution"] == 50000

    def test_provider_content_filter(self):
        cfg = GuardrailsConfig(
            provider_content_filter=ProviderContentFilter(
                enabled=True, categories=["violence"]
            ),
        )
        result = decompose_config(cfg)
        pcf = next(g for g in result if g["guardrail_name"] == "provider_content_filter")
        assert pcf["guardrail_config"]["categories"] == ["violence"]

    def test_disabled_provider_filter_excluded(self):
        cfg = GuardrailsConfig(
            provider_content_filter=ProviderContentFilter(enabled=False),
        )
        result = decompose_config(cfg)
        assert not any(g["guardrail_name"] == "provider_content_filter" for g in result)

    def test_custom_filters_per_enabled(self):
        cfg = GuardrailsConfig(
            custom_filters=[
                CustomFilter(id="f1", name="Active", enabled=True, filter_type="python_code"),
                CustomFilter(id="f2", name="Disabled", enabled=False, filter_type="python_code"),
            ],
        )
        result = decompose_config(cfg)
        cf_entries = [g for g in result if g["guardrail_name"] == "custom_filter"]
        assert len(cf_entries) == 1
        assert cf_entries[0]["guardrail_config"]["name"] == "Active"

    def test_topic_ban_and_language_restriction(self):
        cfg = GuardrailsConfig(
            ban_topics=["politics", "religion"],
            allowed_languages=["en", "fr"],
        )
        result = decompose_config(cfg)
        tb = next(g for g in result if g["guardrail_name"] == "topic_ban")
        assert tb["guardrail_config"]["topics"] == ["politics", "religion"]
        lr = next(g for g in result if g["guardrail_name"] == "language_restriction")
        assert lr["guardrail_config"]["languages"] == ["en", "fr"]

    def test_token_limit(self):
        cfg = GuardrailsConfig(max_input_tokens=1000)
        result = decompose_config(cfg)
        tl = next(g for g in result if g["guardrail_name"] == "token_limit")
        assert tl["guardrail_config"]["max_tokens"] == 1000


class TestConfigToPipelineEntry:
    """Tests for config_to_pipeline_entry()."""

    def test_policy_metadata(self):
        cfg = GuardrailsConfig(
            enabled=True,
            enforcement_mode="audit",
            priority=500,
            policy_id="pol-123",
            policy_name="Test Policy",
        )
        entry = config_to_pipeline_entry(cfg)
        assert entry["policy_name"] == "Test Policy"
        assert entry["policy_id"] == "pol-123"
        assert entry["enforcement_mode"] == "audit"
        assert entry["priority"] == 500
        assert entry["enabled"] is True
        assert isinstance(entry["guardrails"], list)

    def test_guardrails_key_present(self):
        cfg = GuardrailsConfig(
            enabled=True,
            detect_prompt_injection="block",
        )
        entry = config_to_pipeline_entry(cfg)
        assert "guardrails" in entry
        assert len(entry["guardrails"]) >= 1


class TestPipelineEntryToConfig:
    """Tests for pipeline_entry_to_config() (compose)."""

    def test_fallback_to_from_dict(self):
        """Dicts without 'guardrails' key use legacy from_dict()."""
        legacy = {
            "enabled": True,
            "enforcement_mode": "enforce",
            "detect_prompt_injection": "block",
        }
        cfg = pipeline_entry_to_config(legacy)
        assert cfg.detect_prompt_injection == "block"

    def test_compose_basic_behavioral(self):
        entry = {
            "policy_name": "Test",
            "policy_id": "p1",
            "enforcement_mode": "audit",
            "priority": 200,
            "enabled": True,
            "guardrails": [
                {"guardrail_name": "prompt_injection", "guardrail_config": {"action": "warn", "threshold": 0.9}},
                {"guardrail_name": "pii_anonymization", "guardrail_config": {"action": "anonymize", "use_faker": True, "entity_types": ["EMAIL"]}},
            ],
        }
        cfg = pipeline_entry_to_config(entry)
        assert cfg.policy_name == "Test"
        assert cfg.enforcement_mode == "audit"
        assert cfg.detect_prompt_injection == "warn"
        assert cfg.prompt_injection_threshold == 0.9
        assert cfg.anonymize_pii == "anonymize"
        assert cfg.use_faker is True
        assert cfg.pii_entity_types == ["EMAIL"]

    def test_compose_pattern_rules(self):
        entry = {
            "guardrails": [
                {
                    "guardrail_name": "pattern_rule",
                    "guardrail_config": {
                        "name": "SSN",
                        "patterns": [{"label": "SSN", "regex": r"\d{3}-\d{2}-\d{4}"}],
                        "action": "redact",
                        "applies_to": "both",
                        "message": "SSN detected",
                        "preset_id": "ssn",
                    },
                },
            ],
        }
        cfg = pipeline_entry_to_config(entry)
        assert len(cfg.pattern_rules) == 1
        assert cfg.pattern_rules[0].name == "SSN"

    def test_compose_output_scanners(self):
        entry = {
            "guardrails": [
                {"guardrail_name": "output_toxicity", "guardrail_config": {"action": "warn", "threshold": 0.8}},
                {"guardrail_name": "output_refusal", "guardrail_config": {"action": "block"}},
            ],
        }
        cfg = pipeline_entry_to_config(entry)
        assert cfg.output_scanners is not None
        assert cfg.output_scanners.detect_toxicity == "warn"
        assert cfg.output_scanners.toxicity_threshold == 0.8
        assert cfg.output_scanners.detect_refusal == "block"

    def test_compose_tool_policy(self):
        entry = {
            "guardrails": [
                {"guardrail_name": "tool_network_policy", "guardrail_config": {"blocked_url_patterns": ["*.evil.com"]}},
                {"guardrail_name": "tool_execution_limits", "guardrail_config": {"tool_timeout_seconds": 30}},
            ],
        }
        cfg = pipeline_entry_to_config(entry)
        assert cfg.tool_call_policy is not None
        assert cfg.tool_call_policy.blocked_url_patterns == ["*.evil.com"]
        assert cfg.tool_call_policy.tool_timeout_seconds == 30

    def test_compose_token_budget(self):
        entry = {
            "guardrails": [
                {"guardrail_name": "token_budget", "guardrail_config": {"max_total_tokens_per_execution": 50000}},
            ],
        }
        cfg = pipeline_entry_to_config(entry)
        assert cfg.token_budget is not None
        assert cfg.token_budget.max_total_tokens_per_execution == 50000

    def test_compose_provider_content_filter(self):
        entry = {
            "guardrails": [
                {"guardrail_name": "provider_content_filter", "guardrail_config": {"categories": ["violence"]}},
            ],
        }
        cfg = pipeline_entry_to_config(entry)
        assert cfg.provider_content_filter is not None
        assert cfg.provider_content_filter.enabled is True
        assert cfg.provider_content_filter.categories == ["violence"]


class TestRoundTrip:
    """Verify decompose→compose produces equivalent configs."""

    def _assert_equivalent(self, original: GuardrailsConfig, restored: GuardrailsConfig):
        """Check key fields match between original and restored config."""
        assert restored.detect_prompt_injection == original.detect_prompt_injection
        assert restored.detect_jailbreak_attempts == original.detect_jailbreak_attempts
        assert restored.detect_toxicity == original.detect_toxicity
        assert restored.anonymize_pii == original.anonymize_pii
        assert restored.system_prompt_protection == original.system_prompt_protection
        assert restored.enforcement_mode == original.enforcement_mode
        assert restored.policy_name == original.policy_name
        assert len(restored.pattern_rules) == len(original.pattern_rules)

    def test_roundtrip_behavioral(self):
        cfg = GuardrailsConfig(
            enabled=True,
            enforcement_mode="audit",
            policy_name="Test",
            policy_id="p1",
            detect_prompt_injection="warn",
            detect_jailbreak_attempts="block",
            anonymize_pii="anonymize",
            use_faker=True,
            pii_entity_types=["EMAIL"],
            system_prompt_protection=True,
            max_input_length=20000,
            prompt_injection_threshold=0.9,
        )
        entry = config_to_pipeline_entry(cfg)
        restored = pipeline_entry_to_config(entry)
        self._assert_equivalent(cfg, restored)
        assert restored.use_faker is True
        assert restored.pii_entity_types == ["EMAIL"]
        assert restored.max_input_length == 20000
        assert restored.prompt_injection_threshold == 0.9

    def test_roundtrip_full_config(self):
        cfg = GuardrailsConfig(
            enabled=True,
            enforcement_mode="enforce",
            policy_name="Full",
            detect_prompt_injection="block",
            detect_toxicity="warn",
            pattern_rules=[
                PatternRule(name="SSN", patterns=[PatternEntry(label="SSN", regex=r"\d{3}")],
                            action="redact", message="SSN found"),
            ],
            output_scanners=OutputScanners(detect_toxicity="warn", detect_refusal="block"),
            tool_call_policy=ToolCallPolicy(blocked_url_patterns=["*.bad.com"]),
            token_budget=TokenBudget(max_total_tokens_per_execution=50000),
            provider_content_filter=ProviderContentFilter(enabled=True, categories=["violence"]),
        )
        entry = config_to_pipeline_entry(cfg)
        restored = pipeline_entry_to_config(entry)

        self._assert_equivalent(cfg, restored)
        assert restored.output_scanners is not None
        assert restored.output_scanners.detect_toxicity == "warn"
        assert restored.tool_call_policy is not None
        assert restored.tool_call_policy.blocked_url_patterns == ["*.bad.com"]
        assert restored.token_budget is not None
        assert restored.token_budget.max_total_tokens_per_execution == 50000
        assert restored.provider_content_filter is not None

    def test_roundtrip_empty_config(self):
        cfg = GuardrailsConfig()
        entry = config_to_pipeline_entry(cfg)
        assert entry["guardrails"] == []
        restored = pipeline_entry_to_config(entry)
        assert restored.detect_prompt_injection == "off"
        assert restored.detect_jailbreak_attempts == "off"
