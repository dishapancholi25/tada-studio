// Thin client for the backend analytics endpoints that power the Workflow
// Details page. These four read-only endpoints are the single source of truth
// for the drill-down metrics:
//
//   GET /api/analytics/workflows/{id}/metrics       -> WorkflowMetricsResponse
//   GET /api/analytics/workflows/{id}/insights      -> ApplicationInsightsResponse
//   GET /api/analytics/workflows/{id}/performance   -> WorkflowPerformanceResponse
//   GET /api/analytics/workflows/{id}/run-metrics   -> WorkflowRunMetricsResponse
//
// The response shapes below mirror the Pydantic models in
// `backend/api/analytics/schemas.py` exactly. The mapping from these raw
// responses to the UI view-models lives in `service.ts`.

import { runtimeConfig } from "../runtime-config";

// ── Raw response shapes (mirror backend/api/analytics/schemas.py) ──────────

export interface MetricValue {
	value: number | null;
	unit: string;
	sample_size: number;
	status: string; // "available" | "insufficient_data"
	source: string;
	note?: string | null;
	extra?: Record<string, unknown> | null;
}

export interface WorkflowMetricSet {
	accuracy: MetricValue;
	correctness: MetricValue;
	response_time: MetricValue;
	faithfulness: MetricValue;
	hallucination_rate: MetricValue;
	groundedness: MetricValue;
	user_satisfaction: MetricValue;
	confidence_score_reliability: MetricValue;
	total_users: MetricValue;
	active_sessions: MetricValue;
	query_responses: MetricValue;
	monthly_new_users: MetricValue;
	documents_ingested: MetricValue;
}

export interface WorkflowMetricsResponse {
	workflow_id: string;
	workflow_name: string;
	evaluation?: { run_id: string; completed_at?: string | null } | null;
	metrics: WorkflowMetricSet;
}

export interface MonthlyInsightRow {
	month: string;
	documents: number;
	queries: number;
	sessions: number;
}

export interface ApplicationInsightsResponse {
	workflow_id: string;
	workflow_name: string;
	data: MonthlyInsightRow[];
}

export interface LatencySummary {
	total_rows: number;
	rows_with_duration: number;
	coverage_pct: number;
	avg_seconds: number | null;
	p50_seconds: number | null;
	p95_seconds: number | null;
	p99_seconds: number | null;
}

export interface DailyLatencyTrendRow {
	execution_date: string;
	samples: number;
	avg_seconds: number | null;
	p50_seconds: number | null;
	p95_seconds: number | null;
}

export interface ReliabilitySummary {
	total_executions: number;
	completed: number;
	stopped: number;
	failed: number;
	other: number;
	success_rate_pct: number | null;
}

export interface WorkflowPerformanceResponse {
	workflow_id: string;
	workflow_name: string;
	window_days: number;
	ref_time_mode: string;
	latency: LatencySummary;
	daily_trend: DailyLatencyTrendRow[];
	reliability: ReliabilitySummary;
}

export interface SuccessRateSummary {
	success_rate_30d: number | null;
	success_rate_recent_7d: number | null;
	success_rate_prior_7d: number | null;
	delta_vs_last_7d: number | null;
}

export interface RunVolumeRow {
	period_start: string;
	successful: number;
	failed: number;
	total: number;
}

export interface RunVolumeTrend {
	weekly: RunVolumeRow[];
	monthly: RunVolumeRow[];
}

export interface WorkflowRunMetricsResponse {
	workflow_id: string;
	workflow_name: string;
	runs_today: number;
	active_runs: number;
	failed_runs_30d: number;
	success_rate: SuccessRateSummary;
	run_volume_trend: RunVolumeTrend;
}

// ── Fetch helper ───────────────────────────────────────────────────────────

async function analyticsFetch<T>(path: string): Promise<T> {
	const baseUrl = await runtimeConfig.getApiBaseUrl();
	const response = await fetch(`${baseUrl}/api/analytics${path}`, {
		headers: { "Content-Type": "application/json" },
	});

	if (!response.ok) {
		let detail = response.statusText;
		try {
			const payload = await response.json();
			detail = payload.detail || detail;
		} catch {
			// Ignore JSON parse errors and fall back to status text.
		}
		throw new Error(detail || "Request failed");
	}

	return (await response.json()) as T;
}

// The Workflow Details page mounts every widget at once, so several hooks ask
// for the same endpoint (e.g. summary, documents, AI health and satisfaction
// all derive from `metrics`) simultaneously. Dedupe concurrent in-flight
// requests per endpoint+workflow so the browser only issues one network call.
const inFlight = new Map<string, Promise<unknown>>();

function dedupe<T>(key: string, run: () => Promise<T>): Promise<T> {
	const existing = inFlight.get(key) as Promise<T> | undefined;
	if (existing) return existing;
	const promise = run().finally(() => inFlight.delete(key));
	inFlight.set(key, promise);
	return promise;
}

export function fetchWorkflowMetrics(workflowId: string): Promise<WorkflowMetricsResponse> {
	return dedupe(`metrics:${workflowId}`, () =>
		analyticsFetch<WorkflowMetricsResponse>(`/workflows/${encodeURIComponent(workflowId)}/metrics`),
	);
}

export function fetchApplicationInsights(workflowId: string): Promise<ApplicationInsightsResponse> {
	return dedupe(`insights:${workflowId}`, () =>
		analyticsFetch<ApplicationInsightsResponse>(
			`/workflows/${encodeURIComponent(workflowId)}/insights`,
		),
	);
}

export function fetchWorkflowPerformance(workflowId: string): Promise<WorkflowPerformanceResponse> {
	return dedupe(`performance:${workflowId}`, () =>
		analyticsFetch<WorkflowPerformanceResponse>(
			`/workflows/${encodeURIComponent(workflowId)}/performance`,
		),
	);
}

export function fetchWorkflowRunMetrics(workflowId: string): Promise<WorkflowRunMetricsResponse> {
	return dedupe(`run-metrics:${workflowId}`, () =>
		analyticsFetch<WorkflowRunMetricsResponse>(
			`/workflows/${encodeURIComponent(workflowId)}/run-metrics`,
		),
	);
}
