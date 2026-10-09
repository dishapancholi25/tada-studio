// Workflow metrics service.
//
// This is the single seam between the UI/hooks and the data source. Each method
// calls one of the four read-only analytics endpoints (see `analytics-api.ts`)
// and maps the backend response into the existing UI view-models declared in
// `@/types/workflow-metrics`. The hook and component contracts are unchanged.
//
// Mapping rules (per product requirements):
//   - Never fabricate a field the API does not return.
//   - Preserve 0 as a real value; never coerce null → 0.
//   - When a metric is null / insufficient_data, omit it rather than guessing.
//   - Never fall back to mock data on failure — errors propagate to the hooks'
//     existing error state.

import type {
	AIApplicationInsights,
	AIHealth,
	AIHealthMetric,
	FeedbackList,
	LatencyKpi,
	QualityMetrics,
	RunSummary,
	RunSummaryKpi,
	SatisfactionMetric,
	SummaryKpi,
	UserSatisfaction,
	WorkflowHeaderInfo,
	WorkflowPerformance,
	WorkflowSummary,
} from "@/types/workflow-metrics";
import {
	fetchApplicationInsights,
	fetchWorkflowMetrics,
	fetchWorkflowPerformance,
	fetchWorkflowRunMetrics,
	type MetricValue,
	type WorkflowMetricsResponse,
} from "./analytics-api";

// Chart accent colours (presentation only — not data).
const BRAND = "#FF5E00";
const BRAND_DARK = "#E05500";
const NAVY = "#1F2A44";
const AMBER = "#EF7413";
const RED = "#FF3E1D";

/** Format an ISO date (YYYY-MM-DD…) into a compact "MMM D" axis label. */
function formatDayLabel(iso: string): string {
	const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
	if (!match) return iso;
	const [, y, m, d] = match;
	const date = new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
	return date.toLocaleDateString(undefined, {
		month: "short",
		day: "numeric",
		timeZone: "UTC",
	});
}

// ── Mappers ─────────────────────────────────────────────────────────────────

function mapHeader(res: WorkflowMetricsResponse): WorkflowHeaderInfo {
	// The /metrics contract only carries identity. Metadata (category, owner,
	// status, version, last run) is intentionally left undefined so the header
	// renders a neutral placeholder instead of a fabricated value.
	return {
		id: res.workflow_id,
		name: res.workflow_name,
	};
}

function mapSummary(res: WorkflowMetricsResponse): WorkflowSummary {
	const m = res.metrics;
	const defs: Array<{ id: string; label: string; metric: MetricValue }> = [
		{ id: "active-sessions", label: "Active Sessions", metric: m.active_sessions },
		{ id: "query-responses", label: "Query Responses", metric: m.query_responses },
		{ id: "documents-ingested", label: "Documents Ingested", metric: m.documents_ingested },
	];
	// Counts are always available (0 is valid). A null value means the metric is
	// genuinely unavailable, so it is dropped rather than shown as 0.
	const kpis: SummaryKpi[] = defs
		.filter((d) => d.metric.value !== null)
		.map((d) => ({ id: d.id, label: d.label, value: d.metric.value as number }));
	return { kpis };
}

/** Maps the Groundedness / Hallucination Rate / Faithfulness quality cards.
 *
 * All three cards are always returned so they stay rendered even when the
 * backend has no value yet. `value` is null when the metric (or its numeric
 * value) is unavailable; the UI renders "--" in that case. */
function mapQualityMetrics(res: WorkflowMetricsResponse): QualityMetrics {
	const m = res.metrics;
	return {
		metrics: [
			{
				id: "groundedness",
				label: "Groundedness",
				description: "Average share of response claims supported by retrieved context.",
				tooltip:
					"Groundedness measures claim coverage: supported claims divided by total factual claims across grounded responses.",
				value: m.groundedness.value,
				unit: "%",
				threshold: "Threshold ≥ 80",
			},
			{
				id: "hallucination-rate",
				label: "Hallucination Rate",
				description: "Share of grounded responses judged not to be factually supported.",
				tooltip:
					"Derived as 100 minus Faithfulness, using the same grounded-response sample from the backend analytics API.",
				value: m.hallucination_rate.value,
				unit: "%",
				threshold: "Threshold ≤ 8",
			},
			{
				id: "faithfulness",
				label: "Faithfulness",
				description: "Share of grounded responses whose faithfulness judge score passes threshold.",
				tooltip:
					"Faithfulness is the percentage of grounded responses whose backend judge score meets the configured support threshold.",
				value: m.faithfulness.value,
				unit: "%",
				threshold: "Threshold ≥ 80",
			},
		],
	};
}


function mapAIHealth(res: WorkflowMetricsResponse): AIHealth {
	const m = res.metrics;
	const metrics: AIHealthMetric[] = [];

	// Always push all 4 metrics — null value means insufficient_data and is
	// handled by the UI with muted/placeholder styling. Never filter here.
	const pushPctFull = (
		id: string,
		label: string,
		metric: MetricValue,
		color: string,
		threshold: string,
	) => {
		metrics.push({
			id,
			label,
			score: metric.value ?? 0,
			color,
			unit: "%",
			sampleSize: metric.sample_size,
			status: metric.status,
			threshold,
		});
	};

	// Order mirrors the design: Accuracy, Correctness, Response Time, Confidence.
	pushPctFull("accuracy", "Accuracy", m.accuracy, BRAND, "Threshold ≥ 90");
	pushPctFull("correctness", "Correctness", m.correctness, NAVY, "Threshold ≥ 85");

	// Response time is a real latency measurement in seconds, not a 0..100 score.
	const rt = m.response_time;
	metrics.push({
		id: "response-time",
		label: "Response Time",
		score: rt.value ?? 0,
		color: RED,
		unit: rt.unit === "seconds" || rt.unit === "second" ? "sec" : rt.unit || "sec",
		sampleSize: rt.sample_size,
		status: rt.status,
		threshold: "Threshold < 5 sec",
	});

	// Success Rate is backed by the confidence_score_reliability metric — the
	// underlying calculation is unchanged; only the display label was renamed.
	pushPctFull("confidence", "Success Rate", m.confidence_score_reliability, BRAND_DARK, "Threshold ≥ 85");

	// Overall score: mean of percentage metrics that have real data (not insufficient).
	const pctScores = metrics
		.filter((x) => (x.unit ?? "%") === "%" && x.status !== "insufficient_data")
		.map((x) => x.score);
	const overallScore =
		pctScores.length > 0
			? Math.round(pctScores.reduce((sum, x) => sum + x, 0) / pctScores.length)
			: 0;

	return { overallScore, metrics };
}

function mapUserSatisfaction(res: WorkflowMetricsResponse): UserSatisfaction {
	const metric = res.metrics.user_satisfaction;
	if (metric.value === null) {
		return { metrics: [], summary: "" };
	}

	// `extra` carries the positive/negative breakdown; fall back to deriving the
	// positive count from `value` if an older API response omits it.
	const extra = metric.extra as
		| { positive_count?: number; negative_count?: number; negative_percentage?: number }
		| null
		| undefined;
	const positiveCount = extra?.positive_count ?? Math.round((metric.value * metric.sample_size) / 100);
	const negativeCount = extra?.negative_count ?? metric.sample_size - positiveCount;
	const negativePercentage = extra?.negative_percentage ?? 100 - metric.value;

	const metrics: SatisfactionMetric[] = [
		{
			id: "positive",
			label: "Positive Feedback",
			value: metric.value,
			tone: "positive" as const,
			description: metric.sample_size > 0 ? `${positiveCount} of ${metric.sample_size} responses` : undefined,
		},
		{
			id: "negative",
			label: "Negative Feedback",
			value: negativePercentage,
			tone: "negative" as const,
			description: metric.sample_size > 0 ? `${negativeCount} of ${metric.sample_size} responses` : undefined,
		},
	];
	return { metrics, summary: "" };
}

// ── Service ──────────────────────────────────────────────────────────────────

export interface WorkflowMetricsService {
	getWorkflowHeader(workflowId: string): Promise<WorkflowHeaderInfo>;
	getSummary(workflowId: string): Promise<WorkflowSummary>;
	getQualityMetrics(workflowId: string): Promise<QualityMetrics>;
	getAIApplicationInsights(workflowId: string): Promise<AIApplicationInsights>;
	getAIHealth(workflowId: string): Promise<AIHealth>;
	getWorkflowPerformance(workflowId: string): Promise<WorkflowPerformance>;
	getRunSummary(workflowId: string): Promise<RunSummary>;
	getUserSatisfaction(workflowId: string): Promise<UserSatisfaction>;
	getFeedback(workflowId: string): Promise<FeedbackList>;
}

export const workflowMetricsService: WorkflowMetricsService = {
	getWorkflowHeader: (workflowId) => fetchWorkflowMetrics(workflowId).then(mapHeader),

	getSummary: (workflowId) => fetchWorkflowMetrics(workflowId).then(mapSummary),

	getQualityMetrics: (workflowId) => fetchWorkflowMetrics(workflowId).then(mapQualityMetrics),

	getAIHealth: (workflowId) => fetchWorkflowMetrics(workflowId).then(mapAIHealth),

	getUserSatisfaction: (workflowId) => fetchWorkflowMetrics(workflowId).then(mapUserSatisfaction),

	getAIApplicationInsights: (workflowId) =>
		fetchApplicationInsights(workflowId).then((res) => ({
			series: [
				{ key: "documents", label: "Documents", color: BRAND },
				{ key: "queries", label: "Queries", color: AMBER },
				{ key: "sessions", label: "Sessions", color: NAVY },
			],
			points: res.data.map((row) => ({
				label: row.month,
				documents: row.documents,
				queries: row.queries,
				sessions: row.sessions,
			})),
		})),

	getWorkflowPerformance: (workflowId) =>
		fetchWorkflowPerformance(workflowId).then((res) => {
			const l = res.latency;
			// Semantic colour coding per the design: average / median latency are
			// "healthy" (green); high-percentile tails (p95 / p99) are "warning"
			// (orange). Tone drives the tinted card background, border and value.
			const defs: Array<{
				id: string;
				label: string;
				caption: string;
				value: number | null;
				tone: "good" | "warning";
			}> = [
				{ id: "avg", label: "Avg Latency", caption: "30-day mean", value: l.avg_seconds, tone: "good" },
				{
					id: "p50",
					label: "P50 Latency",
					caption: "median execution",
					value: l.p50_seconds,
					tone: "good",
				},
				{
					id: "p95",
					label: "P95 Latency",
					caption: "high-end tail",
					value: l.p95_seconds,
					tone: "warning",
				},
				{
					id: "p99",
					label: "P99 Latency",
					caption: "worst-case tail",
					value: l.p99_seconds,
					tone: "warning",
				},
			];
			const kpis: LatencyKpi[] = defs
				.filter((d) => d.value !== null)
				.map((d) => ({
					id: d.id,
					label: d.label,
					valueSeconds: d.value as number,
					caption: d.caption,
					tone: d.tone,
				}));
			// Map coverage from the performance contract when available.
			// coverage_pct and rows_with_duration live on LatencySummary.
			const slaTarget =
				l.coverage_pct != null && l.coverage_pct > 0
					? `${l.coverage_pct.toFixed(2)}% Coverage`
					: undefined;
			const highlights =
				slaTarget && l.rows_with_duration != null && l.rows_with_duration > 0
					? ["duration_seconds from node executions"]
					: [];
			return { kpis, highlights, slaTarget };
		}),

	getRunSummary: (workflowId) =>
		fetchWorkflowRunMetrics(workflowId).then((res) => {
			const kpis: RunSummaryKpi[] = [
				{ id: "runs-today", label: "Runs Today", value: res.runs_today, tone: "neutral" },
				{ id: "failed-runs", label: "Failed Runs", value: res.failed_runs_30d, tone: "critical" },
			];
			// success_rate_30d is null when there were zero runs in the window; omit
			// the card in that case rather than showing 0%.
			if (res.success_rate.success_rate_30d !== null) {
				kpis.push({
					id: "success-rate",
					label: "Success Rate",
					value: res.success_rate.success_rate_30d,
					unit: "%",
					tone: "good",
				});
			}
			return {
				rangeLabel: "Last 30 Days",
				trend: res.run_volume_trend.weekly.map((row) => ({
					label: formatDayLabel(row.period_start),
					runs: row.total,
					successful: row.successful,
					failed: row.failed,
				})),
				monthlyTrend: res.run_volume_trend.monthly.map((row) => ({
					label: formatDayLabel(row.period_start),
					runs: row.total,
					successful: row.successful,
					failed: row.failed,
				})),
				kpis,
			};
		}),

	// No feedback API contract exists yet — return an empty list so the existing
	// "No feedback yet" empty state is shown. Mock feedback is never displayed.
	getFeedback: () => Promise.resolve({ items: [] }),
};
