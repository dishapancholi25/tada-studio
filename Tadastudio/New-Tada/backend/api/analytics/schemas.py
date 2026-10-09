"""Pydantic response schemas for the analytics metrics endpoint."""

from typing import Any

from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    """A single metric with honest availability reporting (never a fabricated number)."""

    value: float | None = None
    unit: str
    sample_size: int
    status: str = Field(description="available | insufficient_data")
    source: str = Field(
        description="Table/column (or JSON path) the value was computed from"
    )
    note: str | None = None
    extra: dict[str, Any] | None = None


class EvaluationProvenance(BaseModel):
    """Identifies which evaluation run backed the judge-derived metrics."""

    run_id: str
    completed_at: str | None = None


class WorkflowMetricSet(BaseModel):
    accuracy: MetricValue
    correctness: MetricValue
    response_time: MetricValue
    faithfulness: MetricValue
    hallucination_rate: MetricValue
    groundedness: MetricValue
    user_satisfaction: MetricValue
    confidence_score_reliability: MetricValue
    total_users: MetricValue
    active_sessions: MetricValue
    query_responses: MetricValue
    monthly_new_users: MetricValue
    documents_ingested: MetricValue


class WorkflowMetricsResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    evaluation: EvaluationProvenance | None = None
    metrics: WorkflowMetricSet


class MonthlyInsightRow(BaseModel):
    """One month's Documents/Queries/Sessions counts for the insights chart."""

    month: str = Field(description="Abbreviated month label, e.g. 'Jan'")
    documents: int
    queries: int
    sessions: int


class ApplicationInsightsResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    data: list[MonthlyInsightRow]


class LatencySummary(BaseModel):
    """Latency stats computed only from node_executions.status = 'completed' rows."""

    total_rows: int
    rows_with_duration: int
    coverage_pct: float
    avg_seconds: float | None
    p50_seconds: float | None
    p95_seconds: float | None
    p99_seconds: float | None


class DailyLatencyTrendRow(BaseModel):
    execution_date: str
    samples: int
    avg_seconds: float | None
    p50_seconds: float | None
    p95_seconds: float | None


class ReliabilitySummary(BaseModel):
    """Execution reliability computed from ALL node_executions statuses (unfiltered)."""

    total_executions: int
    completed: int
    stopped: int
    failed: int
    other: int = Field(description="Statuses outside completed/stopped/failed, e.g. running/cancelled/paused")
    success_rate_pct: float | None


class WorkflowPerformanceResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    window_days: int
    ref_time_mode: str = Field(description="'now' or 'max_row' — see ANALYTICS_USAGE_REF_TIME")
    latency: LatencySummary
    daily_trend: list[DailyLatencyTrendRow]
    reliability: ReliabilitySummary


class SuccessRateSummary(BaseModel):
    """Null fields mean zero runs in that window (NULLIF avoided a div-by-zero), not an error."""

    success_rate_30d: float | None
    success_rate_recent_7d: float | None
    success_rate_prior_7d: float | None
    delta_vs_last_7d: float | None


class RunVolumeRow(BaseModel):
    period_start: str
    successful: int
    failed: int
    total: int


class RunVolumeTrend(BaseModel):
    weekly: list[RunVolumeRow] = Field(description="Last 30 days, grouped by week")
    monthly: list[RunVolumeRow] = Field(description="Last 12 months, grouped by month")


class WorkflowRunMetricsResponse(BaseModel):
    workflow_id: str
    workflow_name: str
    runs_today: int
    active_runs: int
    failed_runs_30d: int
    success_rate: SuccessRateSummary
    run_volume_trend: RunVolumeTrend
