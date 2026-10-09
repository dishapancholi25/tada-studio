// TypeScript interfaces for the Workflow Details / drill-down page.
// These describe the shape of data returned by the (currently mocked) workflow
// metrics service. Real API responses should conform to these interfaces so the
// service implementation can be swapped without touching the UI or hooks.

export type TrendDirection = "up" | "down" | "flat";

export interface DeltaMetric {
	/** Percentage change vs the previous period, e.g. 10.6 means +10.6%. */
	changePct: number;
	direction: TrendDirection;
}

/** 1. Workflow header — identity, metadata and available actions.
 *
 * Only `id` and `name` are guaranteed by the analytics `/metrics` contract.
 * The remaining metadata fields are optional because the backend does not
 * currently return them; the UI renders a neutral placeholder when absent
 * rather than fabricating a value. */
export interface WorkflowHeaderInfo {
	id: string;
	name: string;
	category?: string;
	description?: string;
	status?: "active" | "paused" | "draft";
	owner?: string;
	department?: string;
	lastRunAt?: string; // ISO timestamp
	version?: string;
}

/** 2. KPI summary cards. */
export interface SummaryKpi {
	id: string;
	label: string;
	value: number;
	/** Optional unit or suffix, e.g. "%". */
	unit?: string;
	delta?: DeltaMetric;
}

export interface WorkflowSummary {
	kpis: SummaryKpi[];
}

/** 3. Documents ingested — donut chart with legend + total. */
export interface DocumentsIngestedSlice {
	label: string;
	value: number;
	color: string;
	[key: string]: string | number;
}

export interface DocumentsIngested {
	total: number;
	totalLabel: string;
	slices: DocumentsIngestedSlice[];
}

/** 3b. Quality metrics — Groundedness / Hallucination Rate / Faithfulness cards.
 *
 * These replace the former "Documents Ingested" chart. Values may be null when
 * the backend has not yet computed them; the UI renders "--" in that case and
 * keeps the card visible. */
export interface QualityMetric {
	id: string;
	label: string;
	/** Short supporting description shown under the label. */
	description: string;
	/** Optional tooltip copy shown from the info icon. */
	tooltip?: string;
	/** Numeric value (0..100 percentage) or null when unavailable. */
	value: number | null;
	/** Value unit. Defaults to "%". */
	unit?: string;
	/** Human-readable threshold text, e.g. "Threshold ≥ 80". */
	threshold?: string;
}

export interface QualityMetrics {
	metrics: QualityMetric[];
}

/** 4. AI application insights — grouped bar chart. */
export interface AIApplicationInsightSeries {
	key: string;
	label: string;
	color: string;
}

export interface AIApplicationInsightPoint {
	label: string;
	[seriesKey: string]: string | number;
}

export interface AIApplicationInsights {
	series: AIApplicationInsightSeries[];
	points: AIApplicationInsightPoint[];
}

/** 5. AI health — per-metric horizontal bars + overall score. */
export interface AIHealthMetric {
	id: string;
	label: string;
	/** Numeric value. A 0..100 percentage when `unit` is "%" (drives the
	 *  progress bar); otherwise a raw measurement expressed in `unit`
	 *  (e.g. seconds for response time), rendered as a value row without a bar. */
	score: number;
	/** Bar / indicator accent colour. */
	color: string;
	/** Value unit. Defaults to "%". */
	unit?: string;
	/** Number of samples used to compute this metric. */
	sampleSize?: number;
	/** "available" | "insufficient_data" */
	status?: string;
	/** Human-readable threshold text, e.g. "Threshold ≥ 85" */
	threshold?: string;
}

export interface AIHealth {
	overallScore: number;
	metrics: AIHealthMetric[];
}

/** 6. Workflow performance & latency — KPI cards + highlights. */
export interface LatencyKpi {
	id: string;
	label: string;
	/** Latency value in seconds. */
	valueSeconds: number;
	caption?: string;
	tone?: "good" | "warning" | "critical" | "neutral";
}

export interface WorkflowPerformance {
	kpis: LatencyKpi[];
	highlights: string[];
	slaTarget?: string;
}

/** 7. Latency trend — removed. The "Latency Trend Over Time" chart and its
 * supporting types were deleted; latency is now summarised via the KPI cards
 * and coverage indicator in the Workflow Performance section. */

/** 8. Run summary & volume — trend chart + KPI cards. */
export interface RunSummaryPoint {
	label: string;
	runs: number;
	/** Successful runs for this period — populated when the backend returns the breakdown. */
	successful?: number;
	/** Failed runs for this period — populated when the backend returns the breakdown. */
	failed?: number;
}

export interface RunSummaryKpi {
	id: string;
	label: string;
	value: number;
	unit?: string;
	tone?: "good" | "warning" | "critical" | "neutral";
}

export interface RunSummary {
	rangeLabel: string;
	trend: RunSummaryPoint[];
	/** Monthly-aggregated trend — present when the backend returns monthly data. */
	monthlyTrend?: RunSummaryPoint[];
	kpis: RunSummaryKpi[];
}

/** 9. User satisfaction — metrics + feedback summary. */
export interface SatisfactionMetric {
	id: string;
	label: string;
	/** Percentage 0..100. */
	value: number;
	tone: "positive" | "negative" | "neutral";
	/** Optional description derived from sample size, e.g. "48 of 71 responses". */
	description?: string;
}

export interface UserSatisfaction {
	metrics: SatisfactionMetric[];
	summary: string;
}

/** 10. Feedback section — feedback list/table. */
export type FeedbackSentiment = "positive" | "negative" | "neutral";

export interface FeedbackItem {
	id: string;
	author: string;
	message: string;
	sentiment: FeedbackSentiment;
	createdAt: string; // ISO timestamp
	tag?: string;
}

export interface FeedbackList {
	items: FeedbackItem[];
}
