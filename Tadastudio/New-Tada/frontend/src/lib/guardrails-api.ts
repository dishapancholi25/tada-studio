/**
 * API client for guardrail policy management endpoints.
 * Phase 3: Violations dashboard, compliance view, feedback.
 * Phase 4: Policy versioning, test sandbox, effectiveness metrics.
 */

import type {
	ComplianceSummary,
	CreateAssignmentRequest,
	CreatePolicyRequest,
	GuardrailAssignment,
	GuardrailPolicy,
	GuardrailPolicyVersion,
	GuardrailViolation,
	GuardrailViolationEventItem,
	PolicyMetricsResponse,
	PolicyTestResult,
	PolicyVersion,
	ResolvedConfig,
	SandboxPreviewResponse,
	SandboxTestResponse,
	UpdatePolicyRequest,
	ViolationsSummary,
} from "@/types/guardrail-policies";
import { runtimeConfig } from "./runtime-config";

// ── Fetch helper ───────────────────────────────────────────────

async function guardrailsFetch<T>(
	path: string,
	options?: RequestInit,
): Promise<T> {
	const baseUrl = await runtimeConfig.getApiBaseUrl();
	const response = await fetch(`${baseUrl}/api/guardrails${path}`, {
		...options,
		headers: {
			"Content-Type": "application/json",
			...(options?.headers || {}),
		},
		credentials: "include",
	});

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
		return text as unknown as T;
	}
}

// ── Policy CRUD ────────────────────────────────────────────────

export async function createPolicy(
	data: CreatePolicyRequest,
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch("/policies", {
		method: "POST",
		body: JSON.stringify(data),
	});
}

export async function listPolicies(params?: {
	scope?: string;
	tags?: string;
	applies_to?: string;
	is_template?: boolean;
	search?: string;
}): Promise<{ success: boolean; policies: GuardrailPolicy[] }> {
	const searchParams = new URLSearchParams();
	if (params?.scope) searchParams.set("scope", params.scope);
	if (params?.tags) searchParams.set("tags", params.tags);
	if (params?.applies_to) searchParams.set("applies_to", params.applies_to);
	if (params?.is_template !== undefined)
		searchParams.set("is_template", String(params.is_template));
	if (params?.search) searchParams.set("search", params.search);

	const qs = searchParams.toString();
	return guardrailsFetch(`/policies${qs ? `?${qs}` : ""}`);
}

export async function getPolicy(
	id: string,
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch(`/policies/${id}`);
}

export async function updatePolicy(
	id: string,
	data: UpdatePolicyRequest,
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch(`/policies/${id}`, {
		method: "PUT",
		body: JSON.stringify(data),
	});
}

export async function deletePolicy(
	id: string,
): Promise<{ success: boolean; message: string }> {
	return guardrailsFetch(`/policies/${id}`, { method: "DELETE" });
}

// ── Visibility (mirrors collections pattern) ──────────────────

export async function updatePolicyVisibility(
	id: string,
	visibleToGroups: string[],
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch(`/policies/${id}/visibility`, {
		method: "PATCH",
		body: JSON.stringify({ visible_to_groups: visibleToGroups }),
	});
}

/** @deprecated Use updatePolicyVisibility instead */
export async function sharePolicy(
	id: string,
	shareWith: string[],
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch(`/policies/${id}/share`, {
		method: "POST",
		body: JSON.stringify({ share_with: shareWith }),
	});
}

/** @deprecated Use updatePolicyVisibility instead */
export async function unsharePolicy(
	id: string,
	targetUser: string,
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch(`/policies/${id}/share/${targetUser}`, {
		method: "DELETE",
	});
}

// ── Clone ──────────────────────────────────────────────────────

export async function clonePolicy(
	id: string,
	name?: string,
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch(`/policies/${id}/clone`, {
		method: "POST",
		body: JSON.stringify({ name }),
	});
}

// ── Assignments ────────────────────────────────────────────────

export async function createAssignment(
	data: CreateAssignmentRequest,
): Promise<{ success: boolean; assignment: GuardrailAssignment }> {
	return guardrailsFetch("/assignments", {
		method: "POST",
		body: JSON.stringify(data),
	});
}

export async function updateAssignment(
	id: string,
	data: { priority?: number; override_mode?: string },
): Promise<{ success: boolean; assignment: GuardrailAssignment }> {
	return guardrailsFetch(`/assignments/${id}`, {
		method: "PATCH",
		body: JSON.stringify(data),
	});
}

export async function deleteAssignment(
	id: string,
): Promise<{ success: boolean; message: string }> {
	return guardrailsFetch(`/assignments/${id}`, { method: "DELETE" });
}

export async function listAssignments(params?: {
	target_type?: string;
	target_id?: string;
	workflow_id?: string;
	policy_id?: string;
}): Promise<{ success: boolean; assignments: GuardrailAssignment[] }> {
	const searchParams = new URLSearchParams();
	if (params?.target_type) searchParams.set("target_type", params.target_type);
	if (params?.target_id) searchParams.set("target_id", params.target_id);
	if (params?.workflow_id) searchParams.set("workflow_id", params.workflow_id);
	if (params?.policy_id) searchParams.set("policy_id", params.policy_id);

	const qs = searchParams.toString();
	return guardrailsFetch(`/assignments${qs ? `?${qs}` : ""}`);
}

// ── Resolution ─────────────────────────────────────────────────

export async function resolveConfig(params: {
	workflow_id?: string;
	node_id?: string;
	model_id?: string;
	tool_names?: string;
}): Promise<{ success: boolean } & ResolvedConfig> {
	const searchParams = new URLSearchParams();
	if (params.workflow_id) searchParams.set("workflow_id", params.workflow_id);
	if (params.node_id) searchParams.set("node_id", params.node_id);
	if (params.model_id) searchParams.set("model_id", params.model_id);
	if (params.tool_names) searchParams.set("tool_names", params.tool_names);

	const qs = searchParams.toString();
	return guardrailsFetch(`/resolve${qs ? `?${qs}` : ""}`);
}

// ── Admin ──────────────────────────────────────────────────────

export async function listCompulsoryPolicies(): Promise<{
	success: boolean;
	policies: GuardrailPolicy[];
}> {
	return guardrailsFetch("/admin/compulsory");
}

export async function setCompulsoryPolicy(
	policyId: string,
	isCompulsory: boolean,
): Promise<{ success: boolean; policy: GuardrailPolicy }> {
	return guardrailsFetch("/admin/compulsory", {
		method: "POST",
		body: JSON.stringify({ policy_id: policyId, is_compulsory: isCompulsory }),
	});
}

export async function deactivateCompulsoryPolicy(
	policyId: string,
): Promise<{ success: boolean }> {
	return guardrailsFetch(`/admin/compulsory/${policyId}`, { method: "DELETE" });
}

// ── Templates ──────────────────────────────────────────────────

export async function listTemplates(): Promise<{
	success: boolean;
	templates: GuardrailPolicy[];
}> {
	return guardrailsFetch("/templates");
}

// ── Phase 3: Violations ────────────────────────────────────────

export async function listViolations(params?: {
	policy_id?: string;
	rule_name?: string;
	severity?: string;
	workflow_id?: string;
	agent_node_id?: string;
	execution_id?: string;
	from_ts?: string;
	to_ts?: string;
	limit?: number;
	offset?: number;
}): Promise<{
	violations: GuardrailViolationEventItem[];
	total: number;
	limit: number;
	offset: number;
	has_more?: boolean;
}> {
	const searchParams = new URLSearchParams();
	if (params?.policy_id) searchParams.set("policy_id", params.policy_id);
	if (params?.rule_name) searchParams.set("rule_name", params.rule_name);
	if (params?.severity) searchParams.set("severity", params.severity);
	if (params?.workflow_id) searchParams.set("workflow_id", params.workflow_id);
	if (params?.agent_node_id)
		searchParams.set("agent_node_id", params.agent_node_id);
	if (params?.execution_id)
		searchParams.set("execution_id", params.execution_id);
	if (params?.from_ts) searchParams.set("from_ts", params.from_ts);
	if (params?.to_ts) searchParams.set("to_ts", params.to_ts);
	if (params?.limit !== undefined)
		searchParams.set("limit", String(params.limit));
	if (params?.offset !== undefined)
		searchParams.set("offset", String(params.offset));

	const qs = searchParams.toString();
	return guardrailsFetch(`/violations${qs ? `?${qs}` : ""}`);
}

export async function getViolation(id: string): Promise<{
	success: boolean;
	violation: GuardrailViolation;
}> {
	return guardrailsFetch(`/violations/${id}`);
}

export async function submitViolationFeedback(
	violationId: string,
	rating: "positive" | "negative",
	comment?: string,
): Promise<{ success: boolean; feedback_id: string }> {
	return guardrailsFetch(`/violations/${violationId}/feedback`, {
		method: "POST",
		body: JSON.stringify({ rating, comment }),
	});
}

export async function getViolationsSummary(): Promise<ViolationsSummary> {
	const resp = await guardrailsFetch<{
		success: boolean;
		summary: {
			enforcement_breakdown: {
				enforce: number;
				audit: number;
				disabled: number;
				compulsory: number;
			};
			total_violations_24h: number;
			most_triggered_rules: Array<{ rule_name: string; count: number }>;
		};
	}>("/violations/summary");
	const { enforcement_breakdown, total_violations_24h, most_triggered_rules } =
		resp.summary;
	return {
		total_violations_24h,
		enforce_count: enforcement_breakdown.enforce,
		audit_count: enforcement_breakdown.audit,
		disabled_count: enforcement_breakdown.disabled,
		compulsory_count: enforcement_breakdown.compulsory,
		most_triggered_rules,
	};
}

// ── Phase 3: Compliance ────────────────────────────────────────

export async function getComplianceSummary(): Promise<
	{ success: boolean } & ComplianceSummary
> {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const raw: any = await guardrailsFetch("/admin/compliance");

	// Normalize legacy enforcement_summary into enforcement_breakdown so
	// ComplianceView always consumes a consistent shape regardless of which
	// backend route (legacy guardrails_router vs guardrail_compliance_router) serves the request.
	if (!raw.enforcement_breakdown && raw.enforcement_summary) {
		const s = raw.enforcement_summary;
		raw.enforcement_breakdown = {
			enforce: s.enforce_count ?? s.enforce ?? 0,
			audit: s.audit_count ?? s.audit ?? 0,
			disabled: s.disabled_count ?? s.disabled ?? 0,
			compulsory: s.compulsory_count ?? s.compulsory ?? 0,
		};
	}

	return raw;
}

export async function getMyComplianceSummary(): Promise<
	{ success: boolean } & ComplianceSummary
> {
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	const raw: any = await guardrailsFetch("/compliance/my");

	if (!raw.enforcement_breakdown && raw.enforcement_summary) {
		const s = raw.enforcement_summary;
		raw.enforcement_breakdown = {
			enforce: s.enforce_count ?? s.enforce ?? 0,
			audit: s.audit_count ?? s.audit ?? 0,
			disabled: s.disabled_count ?? s.disabled ?? 0,
			compulsory: s.compulsory_count ?? s.compulsory ?? 0,
		};
	}

	return raw;
}

// ── Phase 4: Admin platform metrics ───────────────────────────

export async function getPlatformMetrics(window?: string): Promise<{
	success: boolean;
	window: string;
	total_violations: number;
	block_count: number;
	warn_count: number;
	top_rules: Array<{
		rule_name: string;
		policy_name: string;
		hit_count: number;
		severity: string;
	}>;
	period_start: string;
	period_end: string;
}> {
	const qs = window ? `?window=${window}` : "";
	return guardrailsFetch(`/admin/metrics${qs}`);
}

// ── Phase 4: Policy versioning ─────────────────────────────────

export async function listPolicyVersions(policyId: string): Promise<{
	success: boolean;
	versions: GuardrailPolicyVersion[];
}> {
	return guardrailsFetch(`/policies/${policyId}/versions`);
}

export async function getPolicyVersion(
	policyId: string,
	versionIdOrNumber: string | number,
	versionNumber?: number,
): Promise<{ success: boolean; version: GuardrailPolicyVersion }> {
	try {
		return await guardrailsFetch(
			`/policies/${policyId}/versions/${versionIdOrNumber}`,
		);
	} catch (err) {
		// Fallback: if UUID lookup hits the integer-typed legacy route (422) or
		// returns not-found, retry with version_number so the int-typed route
		// can serve the request correctly.
		if (versionNumber != null) {
			return guardrailsFetch(
				`/policies/${policyId}/versions/${versionNumber}`,
			);
		}
		throw err;
	}
}

export async function rollbackPolicy(
	policyId: string,
	targetVersion: number,
	changeSummary?: string,
): Promise<{
	success: boolean;
	policy: GuardrailPolicy;
	new_version: number;
}> {
	return guardrailsFetch(`/policies/${policyId}/rollback`, {
		method: "POST",
		body: JSON.stringify({
			target_version: targetVersion,
			change_summary: changeSummary,
		}),
	});
}

export async function rollbackPolicyVersion(
	policyId: string,
	versionId: string,
): Promise<{
	success: boolean;
	policy: GuardrailPolicy;
	new_version_number: number;
}> {
	return guardrailsFetch(`/policies/${policyId}/versions/${versionId}/rollback`, {
		method: "POST",
	});
}

// ── Phase 4: Policy testing ────────────────────────────────────

export async function testPolicy(
	policyId: string,
	params: {
		config_override?: Record<string, unknown>;
		sample_input?: string;
		sample_output?: string;
		include_behavioral?: boolean;
	},
): Promise<{ success: boolean } & PolicyTestResult> {
	return guardrailsFetch(`/policies/${policyId}/test`, {
		method: "POST",
		body: JSON.stringify(params),
	});
}

// ── Phase 4: Effectiveness metrics ────────────────────────────

export async function getPolicyMetrics(
	policyId: string,
	window?: string,
): Promise<PolicyMetricsResponse> {
	const qs = window ? `?window=${window}` : "";
	return guardrailsFetch(`/policies/${policyId}/metrics${qs}`);
}

// ── Phase 4: Sandbox testing ─────────────────────────────────

export async function getSandboxPreview(
	policyId: string,
): Promise<SandboxPreviewResponse> {
	return guardrailsFetch(`/policies/${policyId}/test/preview`);
}

export async function runSandboxTest(
	policyId: string,
	params: {
		input_text: string;
		output_text?: string;
		config_override?: Record<string, unknown>;
	},
): Promise<SandboxTestResponse> {
	// Temporary compatibility: send both new (input_text/output_text) and legacy
	// (sample_input/sample_output) keys so either backend handler (sandbox router
	// vs legacy guardrails_router /test) receives the intended sample text.
	// Remove this mapping once route de-duplication is complete.
	const compatPayload = {
		...params,
		sample_input: params.input_text,
		sample_output: params.output_text,
		// Always include behavioral checks
		include_behavioral: true,
	};
	return guardrailsFetch(`/policies/${policyId}/test`, {
		method: "POST",
		body: JSON.stringify(compatPayload),
	});
}
