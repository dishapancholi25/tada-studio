"""Financial Services built-in policy pack."""

from backend.models.workflow.configs.guardrails import (
    GuardrailsConfig,
    PatternEntry,
    PatternRule,
    ToolCallPolicy,
)

FINANCIAL_SERVICES_PACK = {
    "id": "00000000-0000-0000-0000-000000000003",
    "name": "Financial Services",
    "description": (
        "Guardrails for financial services workflows with SQL injection "
        "prevention and restricted database operations."
    ),
    "config": GuardrailsConfig(
        enabled=True,
        enforcement_mode="enforce",
        pattern_rules=[
            PatternRule(
                name="SQL Injection",
                patterns=[PatternEntry(label="SQL Keywords", regex=r"(?i)\b(DROP|DELETE|INSERT|UPDATE|EXEC|EXECUTE|UNION|ALTER|CREATE|TRUNCATE)\b")],
                action="block",
                applies_to="both",
                message="Potential SQL injection detected",
                preset_id="sql_injection",
            ),
        ],
        tool_call_policy=ToolCallPolicy(
            allowed_sql_operations=["SELECT"],
            blocked_tables=[],
        ),
    ).to_dict(),
}
