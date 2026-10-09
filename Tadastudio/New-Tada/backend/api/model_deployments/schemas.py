"""Pydantic schemas for model deployment API.

This module defines request and response models for the model deployment
API endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelDeploymentCreate(BaseModel):
    """Schema for creating a new model deployment."""

    name: str = Field(..., description="User friendly name for this deployment")
    model_type: str = Field("llm", description="Type of model: 'llm' or 'embedding'")
    provider: str = Field(..., description="Provider identifier (e.g. azure_openai)")
    model_name: str = Field(..., description="Underlying model or deployment name")
    display_name: Optional[str] = Field(None, description="Optional display label")
    description: Optional[str] = Field(None, description="Optional description")
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Provider specific settings"
    )
    credentials: Dict[str, str] = Field(
        default_factory=dict, description="Sensitive credential values"
    )
    is_default: bool = Field(False, description="Mark as default for the provider")
    input_cost_per_million: Optional[float] = Field(
        None, description="USD cost per 1M input tokens"
    )
    output_cost_per_million: Optional[float] = Field(
        None, description="USD cost per 1M output tokens"
    )


class ModelDeploymentUpdate(BaseModel):
    """Schema for updating an existing model deployment."""

    name: Optional[str] = Field(None, description="Updated display name")
    model_type: Optional[str] = Field(
        None, description="Updated model type: 'llm' or 'embedding'"
    )
    provider: Optional[str] = Field(None, description="Updated provider identifier")
    model_name: Optional[str] = Field(
        None, description="Updated model or deployment name"
    )
    display_name: Optional[str] = Field(None, description="Updated label")
    description: Optional[str] = Field(None, description="Updated description")
    settings: Optional[Dict[str, Any]] = Field(None, description="Updated settings")
    credentials: Optional[Dict[str, Optional[str]]] = Field(
        None, description="Updated credential values (empty string to clear)"
    )
    is_default: Optional[bool] = Field(None, description="Update default flag")
    is_active: Optional[bool] = Field(None, description="Enable/disable deployment")
    input_cost_per_million: Optional[float] = Field(
        None, description="Updated USD cost per 1M input tokens"
    )
    output_cost_per_million: Optional[float] = Field(
        None, description="Updated USD cost per 1M output tokens"
    )


class ModelDeploymentTestRequest(BaseModel):
    """Schema for testing a model deployment connection."""

    overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional runtime overrides (temperature, etc.)",
    )


class ModelDeploymentResponse(BaseModel):
    """Schema for a single model deployment response."""

    id: str
    name: str
    description: Optional[str]
    provider: str
    model_name: str
    model_type: str
    display_name: str
    settings: Dict[str, Any]
    credentials: Optional[Dict[str, Optional[str]]]
    has_credentials: bool
    is_default: bool
    is_active: bool
    input_cost_per_million: Optional[float]
    output_cost_per_million: Optional[float]
    created_at: Optional[str]
    updated_at: Optional[str]


class ModelDeploymentListResponse(BaseModel):
    """Schema for list of model deployments response."""

    success: bool
    data: list[ModelDeploymentResponse]


class ModelDeploymentSingleResponse(BaseModel):
    """Schema for single model deployment response."""

    success: bool
    data: ModelDeploymentResponse


class ModelDeploymentTestResponse(BaseModel):
    """Schema for model deployment test response."""

    success: bool
    data: Dict[str, Any]


class ModelDeploymentDeleteResponse(BaseModel):
    """Schema for model deployment deletion response."""

    success: bool


class PricingLookupData(BaseModel):
    """Pricing data returned from a LiteLLM lookup."""

    model: str = Field(..., description="The queried model name")
    input_cost_per_million: float = Field(
        ..., description="USD cost per 1M input tokens"
    )
    output_cost_per_million: float = Field(
        ..., description="USD cost per 1M output tokens"
    )
    source_model_name: str = Field(
        ..., description="Model key that matched in LiteLLM data"
    )
    litellm_provider: Optional[str] = Field(
        None, description="Provider from LiteLLM data"
    )


class PricingLookupResponse(BaseModel):
    """Response schema for pricing lookup endpoint."""

    success: bool
    data: Optional[PricingLookupData] = None


class ModelLimitsData(BaseModel):
    """Model parameter limits from LiteLLM data."""

    model: str = Field(..., description="The queried model name")
    max_output_tokens: Optional[int] = Field(None, description="Maximum output tokens")
    max_input_tokens: Optional[int] = Field(
        None, description="Maximum input/context tokens"
    )
    supports_reasoning: bool = Field(
        False, description="Whether the model supports reasoning effort"
    )
    source_model_name: str = Field(
        ..., description="Model key that matched in LiteLLM data"
    )


class ModelLimitsResponse(BaseModel):
    """Response schema for model limits lookup endpoint."""

    success: bool
    data: Optional[ModelLimitsData] = None
