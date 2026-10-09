"""Pydantic request / response schemas for the evaluation API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


# ── Dataset ──────────────────────────────────────────────────────────


class CreateDatasetRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    target_type: str = Field(..., pattern="^(workflow|agent|model|tool)$")
    target_id: Optional[str] = None
    workflow_id: Optional[str] = None
    tags: Optional[List[str]] = None
    visible_to_groups: Optional[List[str]] = None


class DatasetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    target_type: str
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    tags: Optional[List[str]] = None
    test_case_count: int = 0
    run_count: int = 0
    baseline_run_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    created_by_name: Optional[str] = None
    created_by_email: Optional[str] = None
    visible_to_groups: Optional[List[str]] = None
    is_read_only: bool = False
    created_at: Optional[str] = None


class UpdateDatasetRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    target_type: Optional[str] = Field(None, pattern="^(workflow|agent|model|tool)$")
    target_id: Optional[str] = None
    workflow_id: Optional[str] = None


class UpdateDatasetVisibilityRequest(BaseModel):
    visible_to_groups: List[str]


class DatasetListResponse(BaseModel):
    datasets: List[DatasetResponse]


# ── Test cases ───────────────────────────────────────────────────────


class ManualTestCase(BaseModel):
    input_data: str
    expected_output: Optional[str] = None
    judge_criteria: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class AIGenerateRequest(BaseModel):
    seed_prompt: str = Field(..., min_length=1)
    count: int = Field(10, ge=1, le=200)
    include_edge_cases: bool = False
    include_adversarial: bool = False
    generator_model: Optional[Dict[str, Any]] = None
    example_execution_ids: Optional[List[str]] = None


class ImportFromExecutionsRequest(BaseModel):
    execution_ids: Optional[List[str]] = None
    workflow_id: Optional[str] = None
    include_expected_output: bool = True
    tags: Optional[List[str]] = None


class ImportDatasetMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    target_type: str = Field("workflow", pattern="^(workflow|agent|model|tool)$")
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    tags: Optional[List[str]] = None


class ImportDatasetTestCase(BaseModel):
    input_data: str
    expected_output: Optional[str] = None
    judge_criteria: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    file_info: Optional[Dict[str, Any]] = None


class ImportDatasetRequest(BaseModel):
    format: str = Field(..., description="Must be 'nexus-dataset-v1'")
    dataset: ImportDatasetMeta
    test_cases: Optional[List[ImportDatasetTestCase]] = None


class AddTestCasesRequest(BaseModel):
    manual: Optional[List[ManualTestCase]] = None
    ai_generate: Optional[AIGenerateRequest] = None


class UpdateTestCaseRequest(BaseModel):
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    judge_criteria: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class TestCaseFileResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    file_size: int


class TestCaseResponse(BaseModel):
    id: str
    input_data: str
    expected_output: Optional[str] = None
    judge_criteria: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    files: Optional[List[TestCaseFileResponse]] = None


class TestCaseListResponse(BaseModel):
    test_cases: List[TestCaseResponse]


# ── Run ──────────────────────────────────────────────────────────────


class CreateRunRequest(BaseModel):
    name: Optional[str] = None
    workflow_id: Optional[str] = None
    dataset_id: str
    target_id: Optional[str] = None
    target_type: str = Field("workflow", pattern="^(workflow|agent|model|tool)$")
    trigger: str = Field("manual", pattern="^(manual|on_publish|on_modify|scheduled)$")
    environment: Optional[str] = None
    pillar_weights: Optional[Dict[str, Any]] = None
    concurrency_limit: Optional[int] = Field(None, ge=1, le=50)
    judge_model_config: Optional[Dict[str, Any]] = None
    judge_output_policy: Optional[Dict[str, Any]] = None
    external_integration_config: Optional[Dict[str, Any]] = None
    quality_judge_provider: Optional[str] = Field(None, pattern="^(builtin|phoenix)$")

    @model_validator(mode="after")
    def validate_target_fields(self) -> "CreateRunRequest":
        tt = self.target_type
        if tt == "workflow":
            if not self.workflow_id:
                raise ValueError(
                    "workflow_id is required when target_type is 'workflow'"
                )
        elif tt == "agent":
            if not self.workflow_id:
                raise ValueError("workflow_id is required when target_type is 'agent'")
            if not self.target_id:
                raise ValueError(
                    "target_id (agent node ID) is required when target_type is 'agent'"
                )
        elif tt == "tool":
            if not self.workflow_id:
                raise ValueError("workflow_id is required when target_type is 'tool'")
            if not self.target_id:
                raise ValueError(
                    "target_id (tool node ID) is required when target_type is 'tool'"
                )
        elif tt == "model":
            if not self.target_id:
                raise ValueError(
                    "target_id (model deployment ID) is required when target_type is 'model'"
                )
        return self


class ResultResponse(BaseModel):
    id: str
    test_case_id: Optional[str] = None
    graph_execution_id: Optional[str] = None
    composite_score: Optional[float] = None
    cost_score: Optional[float] = None
    quality_score: Optional[float] = None
    reliability_score: Optional[float] = None
    latency_score: Optional[float] = None
    trace_reference: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


class ResultDetailResponse(ResultResponse):
    """Extended result with raw pillar breakdowns, linked test case, and execution summary."""

    run_id: str
    quality_raw: Optional[Dict[str, Any]] = None
    cost_raw: Optional[Dict[str, Any]] = None
    reliability_raw: Optional[Dict[str, Any]] = None
    latency_raw: Optional[Dict[str, Any]] = None
    guardrail_signals: Optional[Dict[str, Any]] = None
    external_eval_raw: Optional[Dict[str, Any]] = None
    trace_reference: Optional[Dict[str, Any]] = None
    test_case: Optional[TestCaseResponse] = None
    execution_summary: Optional[Dict[str, Any]] = None


class RunResponse(BaseModel):
    id: str
    name: Optional[str] = None
    workflow_id: Optional[str] = None
    graph_definition_id: Optional[str] = None
    graph_version: Optional[int] = None
    dataset_id: Optional[str] = None
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    status: str
    trigger: Optional[str] = None
    environment: Optional[str] = None
    composite_score: Optional[float] = None
    cost_score: Optional[float] = None
    quality_score: Optional[float] = None
    reliability_score: Optional[float] = None
    latency_score: Optional[float] = None
    total_cases: int = 0
    completed_cases: int = 0
    failed_cases: int = 0
    regression_flag: bool = False
    regression_severity: Optional[str] = None
    regression_ack_required: bool = False
    triggered_by_user_id: Optional[str] = None
    triggered_by_name: Optional[str] = None
    triggered_by_email: Optional[str] = None
    external_eval_summary: Optional[Dict[str, Any]] = None
    pillar_weights: Optional[Dict[str, Any]] = None
    concurrency_limit: Optional[int] = None
    judge_model_config: Optional[Dict[str, Any]] = None
    judge_output_policy: Optional[Dict[str, Any]] = None
    external_integration_config: Optional[Dict[str, Any]] = None
    workflow_name: Optional[str] = None
    dataset_name: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Optional[List[ResultResponse]] = None


class RunListResponse(BaseModel):
    runs: List[RunResponse]


class RunCompareResponse(BaseModel):
    run_a: RunResponse
    run_b: RunResponse
    delta: Dict[str, Optional[float]]
    winner: Optional[str] = None
    winner_reason: Optional[str] = None


# ── Recommendation ───────────────────────────────────────────────────


class RecommendationResponse(BaseModel):
    id: str
    run_id: str
    recommendation_type: str
    target_node_id: Optional[str] = None
    title: str
    rationale: Optional[str] = None
    risk_tier: str
    status: str
    proposed_change: Optional[Dict[str, Any]] = None
    expected_impact: Optional[Dict[str, Any]] = None
    applied_by_user_id: Optional[str] = None
    applied_version: Optional[int] = None
    applied_graph_definition_id: Optional[str] = None
    created_at: Optional[str] = None


class ApplyRecommendationRequest(BaseModel):
    confirmed: bool = False
    impact_acknowledged: bool = False
    proposed_change_override: Optional[Dict[str, Any]] = None


class RecommendationPreviewResponse(BaseModel):
    """Response model for recommendation preview (before/after comparison)."""

    recommendation_id: str
    recommendation_type: Optional[str] = None
    target_node_id: Optional[str] = None
    node_name: Optional[str] = None
    field: Optional[str] = None
    current_value: Optional[Any] = None
    proposed_value: Optional[Any] = None
    proposed_change: Optional[Dict[str, Any]] = None


class RecommendationActionResponse(BaseModel):
    """Response model for apply/dismiss recommendation actions."""

    status: str
    recommendation_id: Optional[str] = None
    risk_tier: Optional[str] = None
    expected_impact: Optional[Dict[str, Any]] = None
    recommendation_type: Optional[str] = None
    proposed_change: Optional[Dict[str, Any]] = None
    guidance: Optional[str] = None
    workflow_id: Optional[str] = None
    reason: Optional[str] = None
    detail: Optional[str] = None
    applied_version: Optional[int] = None
    applied_graph_definition_id: Optional[str] = None


class RecommendationListResponse(BaseModel):
    recommendations: List[RecommendationResponse]


# ── Auto-eval config ─────────────────────────────────────────────────


class AutoEvalConfig(BaseModel):
    enabled: bool = False
    dataset_id: Optional[str] = None
    environment: Optional[str] = None
    pillar_weights: Optional[Dict[str, Any]] = None
    concurrency_limit: Optional[int] = None
    judge_model_config: Optional[Dict[str, Any]] = None
    judge_output_policy: Optional[Dict[str, Any]] = None
    trigger_on_publish: bool = False
    trigger_on_modify: bool = False
    debounce_window_seconds: Optional[int] = None
    quality_judge_provider: Optional[str] = Field(None, pattern="^(builtin|phoenix)$")


# ── Target context ──────────────────────────────────────────────────


class TargetContextResponse(BaseModel):
    target_type: str
    target_id: str
    display_name: str
    purpose: Optional[str] = None
    input_schema: Optional[str] = None
    output_schema: Optional[str] = None
    tools: Optional[List[str]] = None
    model_info: Optional[str] = None
    suggested_judge_criteria: Optional[Dict[str, Any]] = None
    suggested_tags: Optional[List[str]] = None
    context_summary: str
    ai_seed_enrichment: str
