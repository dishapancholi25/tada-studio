"""PII Protection built-in policy pack."""

from backend.models.workflow.configs.guardrails import GuardrailsConfig

PII_PROTECTION_PACK = {
    "id": "00000000-0000-0000-0000-000000000002",
    "name": "PII Protection",
    "description": (
        "Detects personally identifiable information using LLM Guard's "
        "ML-based PII scanner. Default action: anonymize with vault-based round-trip restoration."
    ),
    "config": GuardrailsConfig(
        enabled=True,
        enforcement_mode="enforce",
        anonymize_pii="anonymize",
    ).to_dict(),
}
