"""REST endpoints for managing LLM model deployments.

This module provides FastAPI routes for CRUD operations on model deployments,
including testing deployment connections.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.auth.dependencies import require_active_user, require_admin
from backend.models.workflow.configs.llm import LLMConfig
from backend.services.auth.rbac import _redact_email
from ...services.llm_models import LLMFactory
from ...services.model_deployment import ModelDeploymentService
from ...services.model_deployment.exceptions import (
    DefaultModelConflictError,
    DeploymentNotFoundError,
    ModelDeploymentError,
)
from .dependencies import get_llm_factory, get_model_deployment_service
from backend.services.token_counting.litellm_pricing import (
    get_model_limits,
    get_pricing,
)
from .schemas import (
    ModelDeploymentCreate,
    ModelDeploymentTestRequest,
    ModelDeploymentUpdate,
    ModelLimitsData,
    ModelLimitsResponse,
    PricingLookupData,
    PricingLookupResponse,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/model-deployments",
    tags=["model deployments"],
    dependencies=[Depends(require_active_user)],
)


@router.get("/default")
async def get_default_model_deployment(
    model_type: str = Query("llm", description="Model type: 'llm' or 'embedding'"),
    service: ModelDeploymentService = Depends(get_model_deployment_service),
    current_user: dict = Depends(require_admin),
):
    """Get the default model deployment for a specific model type.

    Admin-only: exposes full deployment configuration. Non-admin callers that
    only need selection metadata must use ``/select-options`` instead.

    Args:
        model_type: Model type filter ('llm' or 'embedding')
        service: Model deployment service (injected)
        current_user: Authenticated admin user (injected)

    Returns:
        JSON response with default deployment or null if none set

    Raises:
        HTTPException: On validation or service errors
    """
    try:
        deployment = service.get_default_deployment(model_type=model_type)
        return {"success": True, "data": deployment}
    except ModelDeploymentError as exc:
        logger.error("[MODEL-DEPLOYMENT-API] Get default error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Failed to get default deployment. Check server logs for details.",
        ) from exc


@router.get("/select-options")
async def list_model_deployment_options(
    model_type: Optional[str] = Query(
        None, description="Filter by model type: 'llm' or 'embedding'"
    ),
    service: ModelDeploymentService = Depends(get_model_deployment_service),
):
    """List active deployments as safe, non-sensitive selection options.

    Available to any active (non-admin) user. Returns only allow-listed
    selection metadata (id, name, provider, model, defaults) and never exposes
    credentials, settings, endpoints, or other sensitive configuration.

    Args:
        model_type: Optional filter by model type ('llm' or 'embedding')
        service: Model deployment service (injected)

    Returns:
        JSON response with a list of safe deployment options

    Raises:
        HTTPException: On validation or service errors
    """
    try:
        options = service.list_deployment_options(model_type=model_type)
        return {"success": True, "data": options}
    except ModelDeploymentError as exc:
        logger.error("[MODEL-DEPLOYMENT-API] List options error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Failed to list deployment options. Check server logs for details.",
        ) from exc


@router.get("")
@router.get("/")
async def list_model_deployments(
    model_type: Optional[str] = Query(
        None, description="Filter by model type: 'llm' or 'embedding'"
    ),
    service: ModelDeploymentService = Depends(get_model_deployment_service),
    current_user: dict = Depends(require_admin),
):
    """List all active model deployments (admin-only).

    Exposes full deployment metadata. Credentials are always masked in the
    response; the client cannot request decrypted credentials. Non-admin
    callers must use ``/select-options`` for selection metadata.

    Args:
        model_type: Optional filter by model type ('llm' or 'embedding')
        service: Model deployment service (injected)
        current_user: Authenticated admin user (injected)

    Returns:
        JSON response with list of deployments (credentials masked)

    Raises:
        HTTPException: On validation or service errors
    """
    try:
        deployments = service.list_deployments(
            include_credentials=False, model_type=model_type
        )
        return {"success": True, "data": deployments}
    except ModelDeploymentError as exc:
        logger.error("[MODEL-DEPLOYMENT-API] List error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Failed to list deployments. Check server logs for details.",
        ) from exc


@router.get("/pricing-lookup", response_model=PricingLookupResponse)
async def pricing_lookup(
    model: str = Query(..., description="Model name to look up pricing for"),
):
    """Look up LiteLLM pricing data for a model name.

    Returns suggested input/output costs per 1M tokens if the model is found
    in the LiteLLM pricing database.
    """
    result = get_pricing(model)
    if result:
        return PricingLookupResponse(
            success=True,
            data=PricingLookupData(
                model=model,
                input_cost_per_million=round(result["input"], 4),
                output_cost_per_million=round(result["output"], 4),
                source_model_name=result["source_model_name"],
                litellm_provider=result.get("litellm_provider"),
            ),
        )
    return PricingLookupResponse(success=False, data=None)


@router.get("/model-limits", response_model=ModelLimitsResponse)
async def model_limits_lookup(
    model: str = Query(..., description="Model name to look up limits for"),
):
    """Look up model parameter limits (max tokens, reasoning support) from LiteLLM data."""
    result = get_model_limits(model)
    if result:
        return ModelLimitsResponse(
            success=True,
            data=ModelLimitsData(
                model=model,
                max_output_tokens=result.get("max_output_tokens"),
                max_input_tokens=result.get("max_input_tokens"),
                supports_reasoning=result.get("supports_reasoning", False),
                source_model_name=result["source_model_name"],
            ),
        )
    return ModelLimitsResponse(success=False, data=None)


@router.get("/{deployment_id}")
async def get_model_deployment(
    deployment_id: str,
    service: ModelDeploymentService = Depends(get_model_deployment_service),
    current_user: dict = Depends(require_admin),
):
    """Get a single model deployment by ID (admin-only).

    Credentials are always masked in the response; the client cannot request
    decrypted credentials.

    Args:
        deployment_id: Deployment ID to retrieve
        service: Model deployment service (injected)
        current_user: Authenticated admin user (injected)

    Returns:
        JSON response with deployment data (credentials masked)

    Raises:
        HTTPException: If deployment not found or on errors
    """
    deployment = service.get_deployment(deployment_id, include_credentials=False)
    if not deployment:
        raise HTTPException(status_code=404, detail="Model deployment not found")
    return {"success": True, "data": deployment}


@router.post("")
@router.post("/")
async def create_model_deployment(
    payload: ModelDeploymentCreate,
    service: ModelDeploymentService = Depends(get_model_deployment_service),
    current_user: dict = Depends(require_admin),
):
    """Create a new model deployment.

    Args:
        payload: Deployment creation data
        service: Model deployment service (injected)

    Returns:
        JSON response with created deployment

    Raises:
        HTTPException: On validation or creation errors
    """
    try:
        deployment = service.create_deployment(payload.model_dump())

        # Audit logging for security events
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] Model deployment created by {_redact_email(user_email)}: "
            f"id={deployment.get('id')}, name={deployment.get('name')}, "
            f"provider={deployment.get('provider')}"
        )

        return {"success": True, "data": deployment}
    except DefaultModelConflictError as exc:
        logger.warning("[MODEL-DEPLOYMENT-API] Default conflict on create: %s", exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ModelDeploymentError as exc:
        logger.error("[MODEL-DEPLOYMENT-API] Create error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Failed to create deployment. Check server logs for details.",
        ) from exc


@router.put("/{deployment_id}")
async def update_model_deployment(
    deployment_id: str,
    payload: ModelDeploymentUpdate,
    service: ModelDeploymentService = Depends(get_model_deployment_service),
    current_user: dict = Depends(require_admin),
):
    """Update an existing model deployment.

    Args:
        deployment_id: Deployment ID to update
        payload: Update data (only provided fields are updated)
        service: Model deployment service (injected)

    Returns:
        JSON response with updated deployment

    Raises:
        HTTPException: If deployment not found or on errors
    """
    try:
        updated = service.update_deployment(
            deployment_id, payload.model_dump(exclude_unset=True)
        )
    except DefaultModelConflictError as exc:
        logger.warning("[MODEL-DEPLOYMENT-API] Default conflict on update: %s", exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ModelDeploymentError as exc:
        logger.error("[MODEL-DEPLOYMENT-API] Update error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Failed to update deployment. Check server logs for details.",
        ) from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Model deployment not found")

    # Audit logging for security events
    user_email = current_user.get("email", "unknown")
    updated_fields = ", ".join(payload.model_dump(exclude_unset=True).keys())
    logger.info(
        f"[AUDIT] Model deployment updated by {_redact_email(user_email)}: "
        f"id={deployment_id}, fields={updated_fields}"
    )

    return {"success": True, "data": updated}


@router.delete("/{deployment_id}")
async def delete_model_deployment(
    deployment_id: str,
    hard_delete: bool = Query(False, description="Permanently delete the record"),
    service: ModelDeploymentService = Depends(get_model_deployment_service),
    current_user: dict = Depends(require_admin),
):
    """Delete a model deployment (soft or hard delete).

    Args:
        deployment_id: Deployment ID to delete
        hard_delete: If True, permanently delete; if False, mark as inactive
        service: Model deployment service (injected)

    Returns:
        JSON response indicating success

    Raises:
        HTTPException: If deployment not found
    """
    deleted = service.delete_deployment(deployment_id, hard_delete=hard_delete)
    if not deleted:
        raise HTTPException(status_code=404, detail="Model deployment not found")

    # Audit logging for security events
    user_email = current_user.get("email", "unknown")
    delete_type = "hard" if hard_delete else "soft"
    logger.info(
        f"[AUDIT] Model deployment deleted by {_redact_email(user_email)}: "
        f"id={deployment_id}, type={delete_type}"
    )

    return {"success": True}


@router.post("/{deployment_id}/test")
async def test_model_deployment(
    deployment_id: str,
    payload: ModelDeploymentTestRequest | None = None,
    service: ModelDeploymentService = Depends(get_model_deployment_service),
    factory: LLMFactory = Depends(get_llm_factory),
    current_user: dict = Depends(require_admin),
):
    """Test a model deployment connection.

    Args:
        deployment_id: Deployment ID to test
        payload: Optional test configuration overrides
        service: Model deployment service (injected)
        factory: LLM factory for testing (injected)

    Returns:
        JSON response with test results

    Raises:
        HTTPException: If deployment not found or test fails
    """
    # Build base config with overrides
    overrides = payload.overrides if payload else {}
    base_config = LLMConfig(
        provider="",
        model_name="",
        temperature=overrides.get("temperature", 0.0),
        max_tokens=overrides.get("max_tokens"),
        top_p=overrides.get("top_p"),
        reasoning_effort=overrides.get("reasoning_effort"),
        model_deployment_id=deployment_id,
        config=overrides.get("config", {}),
    )

    try:
        # Enrich config with deployment settings
        enriched = service.enrich_llm_config(base_config)
        logger.info("[MODEL-DEPLOYMENT-API] Testing deployment %s", deployment_id)
        logger.debug(
            "[MODEL-DEPLOYMENT-API] Enriched test config: provider=%s, model=%s, "
            "temperature=%s, max_tokens=%s, top_p=%s, reasoning_effort=%s, "
            "deployment=%s, api_version=%s, config=%s",
            enriched.provider,
            enriched.model_name,
            enriched.temperature,
            enriched.max_tokens,
            enriched.top_p,
            enriched.reasoning_effort,
            enriched.deployment_name,
            enriched.api_version,
            enriched.config,
        )

        # Test connection
        test_result = factory.test_llm_connection(enriched)
        return {"success": test_result.get("success", False), "data": test_result}

    except DeploymentNotFoundError as exc:
        logger.error("[MODEL-DEPLOYMENT-API] Test error - not found: %s", exc)
        raise HTTPException(status_code=404, detail="Deployment not found.") from exc
    except Exception as exc:
        logger.error("[MODEL-DEPLOYMENT-API] Test error: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Deployment test failed. Check server logs for details.",
        ) from exc
