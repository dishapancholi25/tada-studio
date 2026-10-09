"""General Safety built-in policy pack."""

from backend.models.workflow.configs.guardrails import GuardrailsConfig

GENERAL_SAFETY_PACK = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "General Safety",
    "description": (
        "Baseline safety guardrails for all AI workflows. Includes prompt injection "
        "detection, jailbreak prevention, and AI-powered toxicity filtering via LLM Guard."
    ),
    "config": GuardrailsConfig(
        enabled=True,
        enforcement_mode="enforce",
        detect_prompt_injection="block",
        detect_jailbreak_attempts="block",
        detect_toxicity="block",
    ).to_dict(),
}
