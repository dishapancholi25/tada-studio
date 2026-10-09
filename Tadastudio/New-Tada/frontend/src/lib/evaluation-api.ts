import { runtimeConfig } from "./runtime-config";

// ── Types ──────────────────────────────────────────────────────────

export interface EvaluationDataset {
	id: string;
	name: string;
	description?: string | null;
	target_type: string;
	target_id?: string | null;
	target_name?: string | null;
	workflow_id?: string | null;
	workflow_name?: string | null;
	tags?: string[] | null;
	test_case_count: number;
	run_count?: number;
	baseline_run_id?: string | null;
	created_by_user_id?: string | null;
	created_at?: string | null;
	visible_to_groups?: string[] | null;
	is_read_only?: boolean;
	created_by_name?: string | null;
	created_by_email?: string | null;
}

export interface EvaluationRun {
	id: string;
	name?: string | null;
	workflow_id?: string | null;
	workflow_name?: string | null;
	graph_definition_id?: string | null;
	graph_version?: number | null;
	dataset_id?: string | null;
	dataset_name?: string | null;
	target_id?: string | null;
	target_type?: string | null;
	status: string;
	trigger?: string | null;
	environment?: string | null;
	composite_score?: number | null;
	cost_score?: number | null;
	quality_score?: number | null;
	reliability_score?: number | null;
	latency_score?: number | null;
	total_cases: number;
	completed_cases: number;
	failed_cases: number;
	regression_flag?: boolean | null;
	regression_severity?: string | null;
	regression_ack_required: boolean;
	triggered_by_user_id?: string | null;
	triggered_by_name?: string | null;
	triggered_by_email?: string | null;
	external_eval_summary?: Record<string, any> | null;
	pillar_weights?: Record<string, number> | null;
	concurrency_limit?: number | null;
	judge_model_config?: Record<string, any> | null;
	judge_output_policy?: Record<string, any> | null;
	external_integration_config?: Record<string, any> | null;
	created_at?: string | null;
	completed_at?: string | null;
	results?: EvaluationResult[] | null;
}

export interface EvaluationResult {
	id: string;
	test_case_id?: string | null;
	graph_execution_id?: string | null;
	composite_score?: number | null;
	cost_score?: number | null;
	quality_score?: number | null;
	reliability_score?: number | null;
	latency_score?: number | null;
	trace_reference?: Record<string, any> | null;
	created_at?: string | null;
	guardrail_violation_count?: number | null;
	guardrail_status?: "blocked" | "warned" | null;
}

export interface EvaluationResultDetail extends EvaluationResult {
	run_id: string;
	quality_raw?: {
		judge_score?: number | null;
		reasoning?: string | null;
		criteria_scores?: Record<string, number> | null;
		diagnostics?: Record<string, any> | null;
		provider?: "builtin" | "phoenix" | null;
		fallback_reason?: string | null;
	} | null;
	cost_raw?: {
		total_cost?: number | null;
		input_tokens?: number | null;
		output_tokens?: number | null;
		diagnostics?: Record<string, any> | null;
	} | null;
	reliability_raw?: {
		status?: string | null;
		success_rate?: number | null;
		successful_nodes?: number | null;
		total_nodes?: number | null;
		retry_count?: number | null;
		diagnostics?: Record<string, any> | null;
	} | null;
	latency_raw?: {
		duration_seconds?: number | null;
		ttft_ms?: number | null;
		tokens_per_second?: number | null;
		diagnostics?: Record<string, any> | null;
	} | null;
	guardrail_signals?: {
		signals?: Array<{
			type?: string;
			severity?: string;
			message?: string;
			penalty?: number;
		}>;
		penalty?: number | null;
		total_violations?: number | null;
	} | null;
	test_case?: TestCase | null;
	execution_summary?: {
		id: string;
		status: string;
		duration_seconds?: number | null;
		input_data?: Record<string, any> | null;
		output_data?: Record<string, any> | null;
		error_message?: string | null;
		start_time?: string | null;
		end_time?: string | null;
	} | null;
}

export interface EvaluationRecommendation {
	id: string;
	run_id: string;
	recommendation_type: string;
	target_node_id?: string | null;
	title: string;
	rationale?: string | null;
	risk_tier: string;
	status: string;
	proposed_change?: Record<string, any> | null;
	expected_impact?: Record<string, any> | null;
	applied_by_user_id?: string | null;
	applied_version?: number | null;
	applied_graph_definition_id?: string | null;
	created_at?: string | null;
}

export interface AutoEvalConfig {
	enabled: boolean;
	trigger_on_publish?: boolean | null;
	trigger_on_modify?: boolean | null;
	debounce_window_seconds?: number | null;
	dataset_id?: string | null;
	environment?: string | null;
	pillar_weights?: Record<string, any> | null;
	concurrency_limit?: number | null;
	judge_model_config?: Record<string, any> | null;
	judge_output_policy?: Record<string, any> | null;
	quality_judge_provider?: "builtin" | "phoenix" | null;
}

export interface TargetContextResponse {
	target_type: string;
	target_id: string;
	display_name: string;
	purpose?: string | null;
	input_schema?: string | null;
	output_schema?: string | null;
	tools?: string[] | null;
	model_info?: string | null;
	suggested_judge_criteria?: Record<string, string> | null;
	suggested_tags?: string[] | null;
	context_summary: string;
	ai_seed_enrichment: string;
}

export interface RecommendationActionResponse {
	status: string;
	recommendation_id?: string | null;
	risk_tier?: string | null;
	expected_impact?: Record<string, any> | null;
	recommendation_type?: string | null;
	proposed_change?: Record<string, any> | null;
	guidance?: string | null;
	workflow_id?: string | null;
	reason?: string | null;
	detail?: string | null;
	applied_version?: number | null;
	applied_graph_definition_id?: string | null;
}

export interface RunCompareResponse {
	run_a: EvaluationRun;
	run_b: EvaluationRun;
	delta: Record<string, number | null>;
	winner?: string | null;
	winner_reason?: string | null;
}

export interface TestCaseFile {
	id: string;
	filename: string;
	mime_type: string;
	file_size: number;
}

export interface TestCase {
	id: string;
	input_data: string;
	expected_output?: string | null;
	judge_criteria?: Record<string, any> | null;
	tags?: string[] | null;
	files?: TestCaseFile[] | null;
}

// ── Request bodies ─────────────────────────────────────────────────

export interface CreateDatasetBody {
	name: string;
	description?: string;
	target_type: string;
	target_id?: string;
	workflow_id?: string;
	tags?: string[];
	visible_to_groups?: string[];
}

export interface AddTestCasesBody {
	manual?: { input_data: string; expected_output?: string; judge_criteria?: Record<string, any>; tags?: string[] }[];
	ai_generate?: {
		seed_prompt: string;
		count?: number;
		include_edge_cases?: boolean;
		include_adversarial?: boolean;
		generator_model?: Record<string, any>;
		example_execution_ids?: string[];
	};
}

export interface ImportFromExecutionsBody {
	execution_ids?: string[];
	workflow_id?: string;
	include_expected_output?: boolean;
	tags?: string[];
}

export interface UpdateDatasetBody {
	name?: string;
	description?: string | null;
	target_type?: string;
	target_id?: string | null;
	workflow_id?: string | null;
}

export interface UpdateTestCaseBody {
	input_data?: string;
	expected_output?: string | null;
	judge_criteria?: Record<string, any> | null;
	tags?: string[] | null;
}

export interface CreateRunBody {
	name?: string;
	workflow_id?: string;
	dataset_id: string;
	target_id?: string;
	target_type?: string;
	trigger?: string;
	environment?: string;
	pillar_weights?: Record<string, any>;
	concurrency_limit?: number;
	judge_model_config?: Record<string, any>;
	judge_output_policy?: {
		strategy: "final_node" | "specific_node" | "all_nodes";
		node_id?: string;
		max_output_chars?: number;
	};
	external_integration_config?: Record<string, any>;
	quality_judge_provider?: "builtin" | "phoenix";
}

export interface ApplyRecommendationBody {
	confirmed: boolean;
	impact_acknowledged: boolean;
	proposed_change_override?: Record<string, any> | null;
}

export interface RecommendationPreview {
	recommendation_id: string;
	recommendation_type?: string | null;
	target_node_id?: string | null;
	node_name?: string | null;
	field?: string | null;
	current_value?: any;
	proposed_value?: any;
	proposed_change?: Record<string, any> | null;
}

// ── Fetch helper ───────────────────────────────────────────────────

async function evalFetch<T>(path: string, options?: RequestInit): Promise<T> {
	const baseUrl = await runtimeConfig.getApiBaseUrl();
	const response = await fetch(`${baseUrl}/api/evaluation${path}`, {
		...options,
		headers: {
			"Content-Type": "application/json",
			...(options?.headers || {}),
		},
	});

	if (!response.ok) {
		let detail = response.statusText;
		try {
			const payload = await response.json();
			detail = payload.detail || detail;
		} catch {
			// Ignore JSON parse errors and fall back to status text
		}
		throw new Error(detail || "Request failed");
	}

	if (response.status === 204) {
		return null as T;
	}

	const text = await response.text();
	if (!text) {
		return {} as T;
	}

	try {
		return JSON.parse(text) as T;
	} catch {
		throw new Error("Invalid JSON response");
	}
}

// ── Dataset endpoints ──────────────────────────────────────────────

export async function listDatasets(targetType?: string, targetId?: string, filterType?: string, showAll?: boolean): Promise<EvaluationDataset[]> {
	const sp = new URLSearchParams();
	if (targetType) sp.set("target_type", targetType);
	if (targetId) sp.set("target_id", targetId);
	if (filterType) sp.set("filter_type", filterType);
	if (showAll) sp.set("show_all", "true");
	const qs = sp.toString();
	const data = await evalFetch<{ datasets: EvaluationDataset[] }>(`/datasets${qs ? `?${qs}` : ""}`);
	return data.datasets;
}

export async function createDataset(body: CreateDatasetBody): Promise<EvaluationDataset> {
	return evalFetch<EvaluationDataset>("/datasets", {
		method: "POST",
		body: JSON.stringify(body),
	});
}

export async function getDataset(id: string): Promise<EvaluationDataset> {
	return evalFetch<EvaluationDataset>(`/datasets/${id}`);
}

export async function deleteDataset(id: string): Promise<null> {
	return evalFetch<null>(`/datasets/${id}`, { method: "DELETE" });
}

export async function cloneDataset(id: string): Promise<EvaluationDataset> {
	return evalFetch<EvaluationDataset>(`/datasets/${id}/clone`, { method: "POST" });
}

export async function updateDataset(id: string, body: UpdateDatasetBody): Promise<EvaluationDataset> {
	return evalFetch<EvaluationDataset>(`/datasets/${id}`, {
		method: "PATCH",
		body: JSON.stringify(body),
	});
}

export async function updateDatasetVisibility(
	id: string,
	visibleToGroups: string[],
): Promise<EvaluationDataset> {
	return evalFetch<EvaluationDataset>(`/datasets/${id}/visibility`, {
		method: "PATCH",
		body: JSON.stringify({ visible_to_groups: visibleToGroups }),
	});
}

export async function addTestCases(datasetId: string, body: AddTestCasesBody): Promise<TestCase[]> {
	return evalFetch<TestCase[]>(`/datasets/${datasetId}/test-cases`, {
		method: "POST",
		body: JSON.stringify(body),
	});
}

export interface GenerateStreamEvent {
	event: "batch" | "error" | "done";
	saved?: TestCase[];
	saved_count?: number;
	total?: number;
	message?: string;
}

/**
 * Stream AI test case generation via SSE.  Each batch is persisted to the
 * database as soon as it is generated, so partial results survive failures.
 */
export async function generateTestCasesStream(
	datasetId: string,
	body: AddTestCasesBody["ai_generate"],
	onProgress: (event: GenerateStreamEvent) => void,
	signal?: AbortSignal,
): Promise<void> {
	const baseUrl = await runtimeConfig.getApiBaseUrl();
	const response = await fetch(
		`${baseUrl}/api/evaluation/datasets/${datasetId}/test-cases/generate-stream`,
		{
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
			signal,
		},
	);

	if (!response.ok) {
		let detail = response.statusText;
		try {
			const payload = await response.json();
			detail = payload.detail || detail;
		} catch {
			// ignore
		}
		throw new Error(detail || "Request failed");
	}

	const reader = response.body?.getReader();
	if (!reader) throw new Error("No response stream");

	const decoder = new TextDecoder();
	let buffer = "";

	while (true) {
		const { done, value } = await reader.read();
		if (done) break;

		buffer += decoder.decode(value, { stream: true });

		// SSE format: lines starting with "data: " separated by double newlines
		const parts = buffer.split("\n\n");
		// Keep the last (possibly incomplete) part in the buffer
		buffer = parts.pop() || "";

		for (const part of parts) {
			const line = part.trim();
			if (!line.startsWith("data: ")) continue;
			try {
				const event: GenerateStreamEvent = JSON.parse(line.slice(6));
				onProgress(event);
			} catch {
				// skip malformed events
			}
		}
	}
}

export async function deleteTestCase(datasetId: string, testCaseId: string): Promise<null> {
	return evalFetch<null>(`/datasets/${datasetId}/test-cases/${testCaseId}`, { method: "DELETE" });
}

export async function updateTestCase(datasetId: string, testCaseId: string, body: UpdateTestCaseBody): Promise<TestCase> {
	return evalFetch<TestCase>(`/datasets/${datasetId}/test-cases/${testCaseId}`, {
		method: "PATCH",
		body: JSON.stringify(body),
	});
}

export async function listTestCases(datasetId: string): Promise<TestCase[]> {
	const data = await evalFetch<{ test_cases: TestCase[] }>(`/datasets/${datasetId}/test-cases`);
	return data.test_cases;
}

// ── Test case file endpoints ───────────────────────────────────────

export async function uploadTestCaseFile(
	datasetId: string,
	testCaseId: string,
	file: File,
): Promise<TestCaseFile> {
	const baseUrl = await runtimeConfig.getApiBaseUrl();
	const formData = new FormData();
	formData.append("file", file);
	const response = await fetch(
		`${baseUrl}/api/evaluation/datasets/${datasetId}/test-cases/${testCaseId}/files`,
		{ method: "POST", body: formData },
	);
	if (!response.ok) {
		let detail = response.statusText;
		try {
			const payload = await response.json();
			detail = payload.detail || detail;
		} catch {
			// ignore
		}
		throw new Error(detail || "Upload failed");
	}
	return response.json();
}

export async function deleteTestCaseFile(
	datasetId: string,
	testCaseId: string,
	fileId: string,
): Promise<null> {
	return evalFetch<null>(
		`/datasets/${datasetId}/test-cases/${testCaseId}/files/${fileId}`,
		{ method: "DELETE" },
	);
}

export async function downloadTestCaseFileUrl(
	datasetId: string,
	testCaseId: string,
	fileId: string,
): Promise<string> {
	const baseUrl = await runtimeConfig.getApiBaseUrl();
	return `${baseUrl}/api/evaluation/datasets/${datasetId}/test-cases/${testCaseId}/files/${fileId}`;
}

// ── Import from executions ─────────────────────────────────────────

export async function importFromExecutions(datasetId: string, body: ImportFromExecutionsBody): Promise<TestCase[]> {
	return evalFetch<TestCase[]>(`/datasets/${datasetId}/import-from-executions`, {
		method: "POST",
		body: JSON.stringify(body),
	});
}

// ── Dataset export / import ───────────────────────────────────────

export interface DatasetExportTestCase {
	input_data: string;
	expected_output?: string | null;
	judge_criteria?: Record<string, any> | null;
	tags?: string[] | null;
	file_info?: {
		name: string;
		type: string;
		size: number;
		base64: string;
	} | null;
}

export interface DatasetExport {
	format: string;
	dataset: {
		name: string;
		description?: string | null;
		target_type: string;
		target_id?: string | null;
		target_name?: string | null;
		workflow_id?: string | null;
		workflow_name?: string | null;
		tags?: string[] | null;
	};
	test_cases: DatasetExportTestCase[];
}

export async function exportDataset(datasetId: string): Promise<DatasetExport> {
	return evalFetch<DatasetExport>(`/datasets/${datasetId}/export`);
}

export async function importDataset(payload: DatasetExport): Promise<EvaluationDataset> {
	return evalFetch<EvaluationDataset>("/datasets/import", {
		method: "POST",
		body: JSON.stringify(payload),
	});
}

// ── Run endpoints ──────────────────────────────────────────────────

export async function listRuns(params?: {
	workflow_id?: string;
	dataset_id?: string;
	status?: string;
	trigger?: string;
	target_type?: string;
	target_id?: string;
	limit?: number;
	offset?: number;
	show_all?: boolean;
}): Promise<EvaluationRun[]> {
	const sp = new URLSearchParams();
	if (params?.workflow_id) sp.set("workflow_id", params.workflow_id);
	if (params?.dataset_id) sp.set("dataset_id", params.dataset_id);
	if (params?.status) sp.set("status", params.status);
	if (params?.trigger) sp.set("trigger", params.trigger);
	if (params?.target_type) sp.set("target_type", params.target_type);
	if (params?.target_id) sp.set("target_id", params.target_id);
	if (params?.limit !== undefined) sp.set("limit", String(params.limit));
	if (params?.offset !== undefined) sp.set("offset", String(params.offset));
	if (params?.show_all) sp.set("show_all", "true");
	const qs = sp.toString();
	const data = await evalFetch<{ runs: EvaluationRun[] }>(`/runs${qs ? `?${qs}` : ""}`);
	return data.runs;
}

export async function createRun(body: CreateRunBody): Promise<EvaluationRun> {
	return evalFetch<EvaluationRun>("/runs", {
		method: "POST",
		body: JSON.stringify(body),
	});
}

export async function getRun(id: string): Promise<EvaluationRun> {
	return evalFetch<EvaluationRun>(`/runs/${id}`);
}

export async function deleteRun(id: string): Promise<null> {
	return evalFetch<null>(`/runs/${id}`, { method: "DELETE" });
}

export async function setBaselineRun(datasetId: string, runId: string): Promise<EvaluationDataset> {
	return evalFetch<EvaluationDataset>(`/datasets/${datasetId}/baseline-run`, {
		method: "PUT",
		body: JSON.stringify({ run_id: runId }),
	});
}

export async function getResultDetail(resultId: string): Promise<EvaluationResultDetail> {
	return evalFetch<EvaluationResultDetail>(`/results/${resultId}`);
}

export async function compareRuns(runId: string, peerId: string): Promise<RunCompareResponse> {
	return evalFetch<RunCompareResponse>(`/runs/${runId}/compare/${peerId}`);
}

// ── Recommendation endpoints ───────────────────────────────────────

export async function getRunRecommendations(runId: string): Promise<EvaluationRecommendation[]> {
	const data = await evalFetch<{ recommendations: EvaluationRecommendation[] }>(
		`/runs/${runId}/recommendations`,
	);
	return data.recommendations;
}

export async function applyRecommendation(
	runId: string,
	recId: string,
	body: ApplyRecommendationBody,
): Promise<RecommendationActionResponse> {
	return evalFetch<RecommendationActionResponse>(
		`/runs/${runId}/recommendations/${recId}/apply`,
		{
			method: "POST",
			body: JSON.stringify(body),
		},
	);
}

export async function previewRecommendation(
	runId: string,
	recId: string,
): Promise<RecommendationPreview> {
	return evalFetch<RecommendationPreview>(
		`/runs/${runId}/recommendations/${recId}/preview`,
	);
}

export async function dismissRecommendation(
	runId: string,
	recId: string,
): Promise<RecommendationActionResponse> {
	return evalFetch<RecommendationActionResponse>(
		`/runs/${runId}/recommendations/${recId}/dismiss`,
		{ method: "POST" },
	);
}

// ── Workflow-scoped endpoints ──────────────────────────────────────

export async function getLatestRun(workflowId: string): Promise<EvaluationRun> {
	return evalFetch<EvaluationRun>(`/workflows/${workflowId}/latest-run`);
}

export async function getAutoEvalConfig(workflowId: string): Promise<AutoEvalConfig> {
	return evalFetch<AutoEvalConfig>(`/workflows/${workflowId}/auto-eval-config`);
}

export async function updateAutoEvalConfig(
	workflowId: string,
	config: AutoEvalConfig,
): Promise<AutoEvalConfig> {
	return evalFetch<AutoEvalConfig>(`/workflows/${workflowId}/auto-eval-config`, {
		method: "PUT",
		body: JSON.stringify(config),
	});
}

// ── Target context endpoints ──────────────────────────────────────

export async function getTargetContext(
	targetType: string,
	targetId: string,
	workflowId?: string,
): Promise<TargetContextResponse> {
	let path = `/targets/${encodeURIComponent(targetType)}/${encodeURIComponent(targetId)}/context`;
	if (workflowId) {
		path += `?workflow_id=${encodeURIComponent(workflowId)}`;
	}
	return evalFetch<TargetContextResponse>(path);
}

export async function getWorkflows(): Promise<{ id: string; name: string }[]> {
	const baseUrl = await runtimeConfig.getApiBaseUrl();
	const response = await fetch(`${baseUrl}/api/graph/list`, {
		headers: { "Content-Type": "application/json" },
	});
	if (!response.ok) {
		throw new Error("Failed to fetch workflows");
	}
	const data = await response.json();
	const graphs: { workflow_id: string; name: string }[] = data.graphs || [];
	return graphs.map((wf) => ({ id: wf.workflow_id, name: wf.name }));
}
