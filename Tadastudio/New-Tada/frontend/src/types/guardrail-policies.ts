/**
 * TypeScript types for guardrail policy management.
 *
 * Supports the first-class guardrails feature: shared policies,
 * assignments, resolution, and admin controls.
 */

/** Policy visibility scope */
export type PolicyScope = "global" | "organization" | "user";

/** Assignment target types */
export type AssignmentTargetType = "agent_node" | "model" | "tool" | "workflow";

/** How policies combine when multiple apply */
export type OverrideMode = "merge" | "replace" | "append";

/** Entity types a policy can apply to */
export type AppliesTo = "agent" | "model" | "tool" | "workflow";

/** A standalone, reusable guardrail policy */
export interface GuardrailPolicy {
	id: string;
	name: string;
	description?: string | null;
	config: Record<string, unknown>;
	scope: PolicyScope;
	is_compulsory: boolean;
	is_builtin: boolean;
	applies_to: AppliesTo[];
	created_by?: string | null;
	/** Group-based visibility: [] = private, ["__all__"] = everyone, ["grp"] = specific groups */
	visible_to_groups: string[];
	/** @deprecated Use visible_to_groups instead */
	shared_with?: string[];
	is_template: boolean;
	tags: string[];
	version: number;
	current_version?: number;
	version_count?: number;
	created_at?: string | null;
	updated_at?: string | null;
	creator_name?: string | null;
}

/** A guardrail violation event */
export interface GuardrailViolation {
	id: string;
	policy_id?: string | null;
	policy_name?: string | null;
	rule_name: string;
	category: string;
	severity: "block" | "warn" | "info";
	action_taken: string;
	message?: string | null;
	details?: Record<string, unknown> | null;
	graph_execution_id: string;
	node_execution_id?: string | null;
	workflow_id?: string | null;
	workflow_name?: string | null;
	agent_node_id?: string | null;
	agent_node_name?: string | null;
	user_id?: string | null;
	created_at: string;
	feedback_count: number;
	false_positive_count: number;
	feedbacks?: ViolationFeedback[];
}

/** Feedback on a violation */
export interface ViolationFeedback {
	id: string;
	violation_id: string;
	user_id: string;
	rating: "positive" | "negative";
	comment?: string | null;
	created_at: string;
	updated_at?: string | null;
}

/** A policy version snapshot */
export interface PolicyVersion {
	id: string;
	policy_id: string;
	version: number;
	config_snapshot: Record<string, unknown>;
	name_snapshot: string;
	description_snapshot?: string | null;
	changed_by: string;
	change_summary?: string | null;
	created_at: string;
}

/** A guardrail policy version (Phase 4 versioning) */
export interface GuardrailPolicyVersion {
	id: string;
	policy_id?: string | null;
	version: number;
	version_number: number;
	config_snapshot?: Record<string, unknown> | null;
	name_snapshot?: string | null;
	changed_by?: string | null;
	change_summary?: string | null;
	created_at: string;
	is_current?: boolean;
}

/** Criticality level for compliance items */
export type ComplianceCriticality = "critical" | "high" | "medium" | "low";

/** Workflow entry in a compliance report (shared between active and inactive lists) */
export interface ComplianceWorkflowEntry {
	workflow_id: string;
	workflow_name: string;
	workflow_description?: string | null;
	criticality?: ComplianceCriticality;
	has_compulsory_coverage?: boolean;
	unprotected_node_ids?: string[];
	is_published?: boolean;
	is_library?: boolean;
	owner_name?: string | null;
	owner_email?: string | null;
	created_at?: string | null;
	updated_at?: string | null;
	last_executed_at?: string | null;
	execution_count?: number;
	agent_node_count?: number;
	graph_version?: number | null;
}

/** Compliance summary response */
export interface ComplianceSummary {
	enforcement_breakdown: {
		enforce: number;
		audit: number;
		disabled: number;
		compulsory: number;
	};
	unprotected_workflows: ComplianceWorkflowEntry[];
	/** Never-executed workflows (tutorials, experiments, abandoned drafts) */
	inactive_workflows?: ComplianceWorkflowEntry[];
	unprotected_agent_nodes: Array<{
		workflow_id: string;
		node_id: string;
		node_name: string;
		workflow_name?: string;
		criticality?: ComplianceCriticality;
		has_compulsory_coverage?: boolean;
		guardrails_disabled?: boolean;
		is_published?: boolean;
		is_library?: boolean;
		owner_name?: string | null;
		owner_email?: string | null;
		model?: string | null;
		created_at?: string | null;
		last_executed_at?: string | null;
	}>;
}

/** Policy effectiveness metrics */
export interface PolicyMetrics {
	policy_id: string;
	window: string;
	total_violations: number;
	block_rate: number;
	warn_rate: number;
	top_rules: Array<{
		rule_name: string;
		hit_count: number;
		severity: string;
	}>;
	false_positive_rate: number;
	period_start: string;
	period_end: string;
}

/** Policy test result */
export interface PolicyTestResult {
	results: Array<{
		check_type: "input" | "output" | "behavioral";
		passed: boolean;
		violations: Array<Record<string, unknown>>;
		action_taken: string;
		sanitized_content?: string | null;
		passed_content?: string | null;
		llm_judge_called: boolean;
		error?: string;
	}>;
	total_violations: number;
	execution_cost_warning: string | null;
}

/** Assignment of a policy to a target */
export interface GuardrailAssignment {
	id: string;
	policy_id: string;
	target_type: AssignmentTargetType;
	target_id: string;
	workflow_id?: string | null;
	priority: number;
	override_mode: OverrideMode;
	assigned_by?: string | null;
	created_at?: string | null;
	updated_at?: string | null;
	policy_name?: string | null;
}

/** Request to create a policy */
export interface CreatePolicyRequest {
	name: string;
	description?: string | null;
	config: Record<string, unknown>;
	scope?: PolicyScope;
	is_compulsory?: boolean;
	applies_to?: AppliesTo[];
	visible_to_groups?: string[];
	is_template?: boolean;
	tags?: string[];
}

/** Request to update a policy */
export interface UpdatePolicyRequest {
	name?: string;
	description?: string | null;
	config?: Record<string, unknown>;
	scope?: PolicyScope;
	is_compulsory?: boolean;
	applies_to?: AppliesTo[];
	visible_to_groups?: string[];
	is_template?: boolean;
	tags?: string[];
	change_summary?: string;
}

/** Request to create an assignment */
export interface CreateAssignmentRequest {
	policy_id: string;
	target_type: AssignmentTargetType;
	target_id: string;
	workflow_id?: string | null;
	priority?: number;
	override_mode?: OverrideMode;
}

/** A guardrail violation recorded during an execution */
export interface ExecutionGuardrailViolation {
	id: string;
	rule_name: string;
	policy_name: string;
	severity: "block" | "warn" | "info";
	category: string | null;
	message: string | null;
	action_taken: string | null;
	agent_node_name: string | null;
	node_execution_id: string | null;
	timestamp: string | null;
	details: Record<string, unknown> | null;
}

/** A violation event item for the violations list */
export interface GuardrailViolationEventItem {
	id: string;
	severity: "block" | "warn" | "info";
	rule_name: string;
	category?: string | null;
	action_taken?: string | null;
	policy_id: string;
	policy_name?: string | null;
	workflow_id?: string | null;
	workflow_name?: string | null;
	agent_node_id?: string | null;
	agent_node_name?: string | null;
	graph_execution_id?: string | null;
	node_execution_id?: string | null;
	details?: Record<string, unknown> | null;
	created_at: string;
}

/** Admin summary of violation stats */
export interface ViolationsSummary {
	total_violations_24h: number;
	enforce_count: number;
	audit_count: number;
	disabled_count: number;
	compulsory_count: number;
	most_triggered_rules?: Array<{ rule_name: string; count: number }>;
}

/** Compliance overview for admin page */
export interface ComplianceOverview {
	enforcement_breakdown: {
		enforce: number;
		audit: number;
		disabled: number;
		compulsory: number;
	};
	unprotected_workflows: Array<{
		workflow_id: string;
		workflow_name: string;
		unprotected_nodes: string[];
	}>;
	unprotected_agent_nodes: Array<{
		node_id: string;
		node_name: string;
		workflow_id: string;
		workflow_name: string;
	}>;
}

/** A single violation from a sandbox test run */
export interface SandboxViolation {
	category: string;
	rule_name: string;
	severity: string;
	message: string;
	details: Record<string, unknown>;
}

/** Result of checking input or output in a sandbox test */
export interface SandboxCheckResult {
	passed: boolean;
	violations: SandboxViolation[];
	action_taken: string;
	sanitized_content: string | null;
}

/** Response from POST /policies/{id}/test */
export interface SandboxTestResponse {
	success: boolean;
	input_result: SandboxCheckResult;
	output_result: SandboxCheckResult | null;
	static_only: boolean;
	llm_call_made: boolean;
	evaluation_ms: number;
}

/** Response from GET /policies/{id}/test/preview */
export interface SandboxPreviewResponse {
	success: boolean;
	will_use_llm: boolean;
}

/** A top-triggered rule in policy metrics */
export interface PolicyMetricsTopRule {
	rule_name: string;
	count: number;
}

/** Per-rule feedback breakdown in policy metrics */
export interface PolicyMetricsPerRuleFeedback {
	rule_name: string;
	positive_count: number;
	negative_count: number;
}

/** Response from GET /policies/{id}/metrics */
export interface PolicyMetricsResponse {
	success: boolean;
	total_violations: number;
	block_count: number;
	warn_count: number;
	block_rate: number;
	warn_rate: number;
	false_positive_count: number;
	false_positive_rate: number;
	top_rules: PolicyMetricsTopRule[];
	per_rule_feedback: PolicyMetricsPerRuleFeedback[];
}

/** A single decomposed guardrail within a policy */
export interface DecomposedGuardrail {
	guardrail_name: string;
	guardrail_config: Record<string, unknown>;
}

/** One policy entry in the decomposed pipeline */
export interface DecomposedPipelineEntry {
	policy_name: string;
	policy_id: string;
	enforcement_mode: string;
	priority: number;
	enabled: boolean;
	guardrails: DecomposedGuardrail[];
}

/** Resolved effective config response */
export interface ResolvedConfig {
	layers: Array<{
		source: string;
		policy_id: string;
		config: Record<string, unknown>;
	}>;
	effective_config: Record<string, unknown>;
	decomposed_pipeline?: DecomposedPipelineEntry[];
}
