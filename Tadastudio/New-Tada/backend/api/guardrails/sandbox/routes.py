"""API routes for guardrail policy sandbox testing.

Provides endpoints to preview sandbox behaviour and run test evaluations
against a policy without persisting any violation events.
"""

import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.guardrails import get_guardrails_engine
from backend.services.guardrails.policy_service import GuardrailPolicyService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/guardrails/policies/{policy_id}/test",
    tags=["guardrail-sandbox"],
    dependencies=[Depends(require_active_user)],
)


def _get_user_id(current_user: Dict[str, Any]) -> str:
    return current_user.get("sub") or current_user.get("email", "")


def _is_admin(current_user: Dict[str, Any]) -> bool:
    return bool(current_user.get("is_admin"))


class SandboxTestRequest(BaseModel):
    input_text: str
    output_text: Optional[str] = None
    config_override: Optional[Dict[str, Any]] = None


@router.get("/preview")
async def get_sandbox_preview(
    policy_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return metadata about what a sandbox test will do (e.g. whether an LLM call is required)."""
    user_id = _get_user_id(current_user)

    policy = GuardrailPolicyService.get_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    config = GuardrailsConfig.from_dict(policy["config"])

    # Check if behavioral checks are enabled
    has_behavioral = config.has_behavioral_checks
    
    # Behavioral detection always uses the LLM judge as the default path
    # when no LLM Guard scanner flags are set.
    will_use_llm = has_behavioral

    return {"success": True, "will_use_llm": will_use_llm}


@router.post("/")
async def run_sandbox_test(
    policy_id: str,
    request: SandboxTestRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Run a sandbox evaluation against a policy without persisting violations."""
    user_id = _get_user_id(current_user)

    policy = GuardrailPolicyService.get_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    if request.config_override is not None:
        try:
            config = GuardrailsConfig.from_dict(request.config_override)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    else:
        config = GuardrailsConfig.from_dict(policy["config"])

    static_only = not config.has_behavioral_checks

    start_time = time.monotonic()

    engine = get_guardrails_engine()

    input_result = await engine.check_input(request.input_text, config)
    input_result_dict = input_result.to_dict()
    # Add original content and what would be passed through
    input_result_dict["original_content"] = request.input_text
    input_result_dict["passed_content"] = input_result.sanitized_content or request.input_text

    output_result_dict = None
    if request.output_text is not None:
        output_result = await engine.check_output(request.output_text, config, prompt=request.input_text)
        output_result_dict = output_result.to_dict()
        # Add original content and what would be passed through
        output_result_dict["original_content"] = request.output_text
        output_result_dict["passed_content"] = output_result.sanitized_content or request.output_text

    evaluation_ms = (time.monotonic() - start_time) * 1000
    llm_call_made = not static_only

    return {
        "success": True,
        "input_result": input_result_dict,
        "output_result": output_result_dict,
        "static_only": static_only,
        "llm_call_made": llm_call_made,
        "evaluation_ms": evaluation_ms,
    }
