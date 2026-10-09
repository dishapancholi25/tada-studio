import type {
	CollectionDependency,
	ExecuteGraphResponse,
	ExecutionStatusResponse,
	GraphDefinition,
	Group,
	GroupMember,
	GroupsListResponse,
	ScheduleRequest,
	UserInfo,
	WorkflowSchedule,
} from "@/types/api";
import type { ExecutionGuardrailViolation } from "@/types/guardrail-policies";
import { runtimeConfig } from "./runtime-config";

// Global authenticated API client
let authenticatedMainApiClient: any = null;

/**
 * Set the authenticated API client for main operations
 */
export function setAuthenticatedApiClientForMain(apiClient: any) {
	authenticatedMainApiClient = apiClient;
}

/**
 * Get the authenticated API client for main operations
 */
export function getAuthenticatedApiClientForMain() {
	return authenticatedMainApiClient;
}

// Document types
export interface DocumentCollection {
	id: string;
	name: string;
	description?: string;
	created_at: string;
	updated_at?: string;
	document_count?: number;
	unprocessed_count?: number;
	visible_to_groups: string[];
	user_id: string;
	created_by_name?: string;
	created_by_email?: string;
	is_read_only: boolean;
	embedding_deployment_id?: string | null;
	total_embedding_tokens?: number;
	total_embedding_cost?: number;
	search_count?: number;
}

export interface Document {
	id: string;
	collection_id: string;
	name: string;
	type: string;
	size: number;
	status: "pending" | "processing" | "processed" | "failed";
	chunk_count: number;
	upload_date: string;
	error_message?: string;
	embedding_tokens?: number | null;
	embedding_cost?: number | null;
	embedding_model?: string | null;
	collection_name?: string;
	owner_name?: string;
	owner_email?: string;
	is_read_only?: boolean;
}

export interface SearchResult {
	content: string;
	score: number;
	metadata: Record<string, any>;
}

export interface CreateGraphRequest {
	name: string;
	description?: string;
}

export interface CreateNodeRequest {
	graph_name: string;
	node_type:
		| "START"
		| "STEP"
		| "TOOL"
		| "AGENT"
		| "CONDITION"
		| "INFO"
		| "SUBGRAPH"
		| "SUBWORKFLOW"
		| "END"
		| "DOCUMENT_SEARCH"
		| "DATABASE_QUERY"
		| "DATABASE_INSERT"
		| "DATABASE_QUERY_ACTION"
		| "HTTP_REQUEST"
		| "HTTP_REQUEST_ACTION"
		| "WEB_SEARCH"
		| "MCP_SERVER"
		| "EMAIL_SEND"
		| "EMAIL_SEND_TOOL"
		| "FILE_READ"
		| "FILE_WRITE"
		| "CHECKPOINT"
		| "DOCUMENT_RETRIEVE"
		| "DOCUMENT_LOAD"
		| "FOR_EACH"
		| "CODE_EXECUTOR";
	name: string;
	position?: { x: number; y: number };
	tool_template?: string;
	agent_template?: string;
	description?: string;
	llm_type?: string;
	model_name?: string;
	document_search_config?: Record<string, any>;
	document_retrieve_config?: Record<string, any>;
	document_load_config?: Record<string, any>;
	database_query_config?: Record<string, any>;
	http_request_config?: Record<string, any>;
	web_search_config?: Record<string, any>;
	mcp_server_config?: Record<string, any>;
	subworkflow_config?: Record<string, any>;
	agent_config?: Record<string, any>;
	condition_config?: Record<string, any>;
	input_source_config?: Record<string, any>;
	email_send_config?: Record<string, any>;
	email_send_tool_config?: Record<string, any>;
	file_read_config?: Record<string, any>;
	file_write_config?: Record<string, any>;
	checkpoint_config?: Record<string, any>;
	database_insert_config?: Record<string, any>;
	database_query_action_config?: Record<string, any>;
	http_request_action_config?: Record<string, any>;
	end_node_config?: Record<string, any>;
	for_each_config?: Record<string, any>;
	code_executor_config?: Record<string, any>;
	prompt_template?: string;
}

export interface CreateSubAgentRequest {
	graph_name: string;
	parent_agent_id: string;
	name?: string;
	position?: { x: number; y: number };
	delegation_description?: string;
	agent_template?: string;
}

export interface CreateConnectionRequest {
	graph_name: string;
	source_id: string;
	target_id: string;
	source_handle?: string;
	target_handle?: string;
	label?: string;
	connection_type?: string;
}

export type WorkflowRole = "owner" | "editor" | "viewer";

export interface GraphData {
	name: string;
	workflow_id?: string;
	workflow_role?: WorkflowRole;
	description: string;
	nodes: any[];
	connections: any[];
	created_at: string;
	updated_at: string;
}

export interface ExecutionRequest {
	graph_name: string;
	initial_input: Record<string, any>;
	username?: string;
	async_execution?: boolean;
}

export interface ExecutionResult {
	node_id: string;
	node_name: string;
	node_type: string;
	timestamp: string;
	output: any;
	status: "completed" | "failed";
	is_sub_agent?: boolean;
	execution_order?: number;
	start_time?: string;
	duration_seconds?: number | null;
}

export interface ExecutionStatus {
	execution_id: string;
	status:
		| "pending"
		| "running"
		| "pause_pending"
		| "paused"
		| "stop_requested"
		| "stopping"
		| "stopped"
		| "completed"
		| "failed"
		| "cancelled"
		| "skipped";
	start_time: string;
	end_time?: string;
	current_node?: string | null;
	error?: string | null;
	partial_results?: ExecutionResult[];
}

class ApiClient {
	private async fetchJson<T = any>(
		url: string,
		options: RequestInit = {},
	): Promise<T> {
		const authenticatedClient = getAuthenticatedApiClientForMain();
		const { method: rawMethod = "GET", body, ...restOptions } = options;
		const method = rawMethod.toUpperCase();

		let parsedBody: any;
		let canUseAuthenticatedClient = true;

		if (body !== undefined && body !== null) {
			if (typeof body === "string") {
				if (body.length > 0) {
					try {
						parsedBody = JSON.parse(body);
					} catch {
						canUseAuthenticatedClient = false;
					}
				}
			} else {
				// Non-string bodies (e.g., FormData) are not handled by the authenticated client helper yet
				canUseAuthenticatedClient = false;
			}
		}

		if (authenticatedClient && canUseAuthenticatedClient) {
			try {
				switch (method) {
					case "GET":
						return await authenticatedClient.get(url, restOptions);
					case "POST":
						return await authenticatedClient.post(url, parsedBody, restOptions);
					case "PUT":
						return await authenticatedClient.put(url, parsedBody, restOptions);
					case "PATCH":
						return await authenticatedClient.patch(url, parsedBody, restOptions);
					case "DELETE": {
						const deleteOptions =
							parsedBody !== undefined
								? { ...restOptions, body: JSON.stringify(parsedBody) }
								: restOptions;
						return await authenticatedClient.delete(url, deleteOptions);
					}
					default:
						break;
				}
			} catch (clientError) {
				console.error(
					`[API] Authenticated client request failed for ${url}:`,
					clientError,
				);
				throw clientError;
			}
		}

		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const fullUrl = `${apiBaseUrl}${url}`;

			const response = await fetch(fullUrl, {
				...options,
				headers: {
					"Content-Type": "application/json",
					...options?.headers,
				},
			});

			if (!response.ok) {
				const error = await response
					.json()
					.catch(() => ({ detail: "Unknown error" }));
				throw new Error(
					error.detail || `HTTP error! status: ${response.status}`,
				);
			}

			const contentType = response.headers.get("content-type");
			if (!contentType || !contentType.includes("application/json")) {
				return {} as T;
			}

			const text = await response.text();
			if (!text) {
				return {} as T;
			}

			try {
				const data = JSON.parse(text);
				return data as T;
			} catch {
				throw new Error("Invalid JSON response from server");
			}
		} catch (err) {
			throw err;
		}
	}

	// Graph operations
	async createGraph(data: CreateGraphRequest) {
		return this.fetchJson("/api/graph/create", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async importRawWorkflow(data: {
		name: string;
		description: string;
		workflow_json: any;
	}) {
		return this.fetchJson("/api/graph/import-raw", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async duplicateWorkflow(
		graphName: string,
		newName: string,
	): Promise<{ success: boolean; workflow_id: string; message: string }> {
		return this.fetchJson(
			`/api/graph/${encodeURIComponent(graphName)}/duplicate`,
			{
				method: "POST",
				body: JSON.stringify({ new_name: newName }),
			},
		);
	}

	async getGraph(
		graphName: string,
	): Promise<{ success: boolean; graph: GraphDefinition }> {
		return this.fetchJson<{ success: boolean; graph: GraphDefinition }>(
			`/api/graph/${encodeURIComponent(graphName)}`,
		);
	}

	async getGraphByWorkflowId(
		workflowId: string,
		options?: { version?: number; graphDefinitionId?: string },
	): Promise<{
		success: boolean;
		graph: GraphDefinition;
		workflow_id: string;
		loaded_version?: number;
		is_latest?: boolean;
	}> {
		const params = new URLSearchParams();
		if (options?.version != null) params.set("version", String(options.version));
		if (options?.graphDefinitionId)
			params.set("graph_definition_id", options.graphDefinitionId);
		const qs = params.toString();
		return this.fetchJson<{
			success: boolean;
			graph: GraphDefinition;
			workflow_id: string;
			loaded_version?: number;
			is_latest?: boolean;
		}>(`/api/graph/by-id/${workflowId}${qs ? `?${qs}` : ""}`);
	}

	async getWorkflowVersions(workflowId: string): Promise<{
		success: boolean;
		versions: Array<{
			id: string;
			version: number;
			is_latest: boolean;
			created_by: string | null;
			created_at: string | null;
			file_hash: string | null;
			size_bytes: number | null;
		}>;
		workflow_id: string;
	}> {
		return this.fetchJson(`/api/graph/by-id/${workflowId}/versions`);
	}

	async listGraphs() {
		return this.fetchJson("/api/graph/list");
	}

	async exportGraph(
		graphName: string,
		format: "full" | "minimal" | "langgraph" = "full",
	) {
		return this.fetchJson(
			`/api/graph/export/${encodeURIComponent(graphName)}?format=${format}`,
		);
	}

	async exportGraphPython(graphName: string): Promise<string> {
		const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
		const url = `${apiBaseUrl}/api/graph/export/${encodeURIComponent(graphName)}/python`;
		const response = await fetch(url, {
			headers: { "Content-Type": "application/json" },
		});
		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ detail: "Export failed" }));
			throw new Error(
				error.detail || `HTTP error! status: ${response.status}`,
			);
		}
		return response.text();
	}

	async deleteGraph(graphName: string) {
		return this.fetchJson(`/api/graph/${encodeURIComponent(graphName)}`, {
			method: "DELETE",
		});
	}

	async reloadGraph(graphName: string) {
		return this.fetchJson(
			`/api/graph/reload/${encodeURIComponent(graphName)}`,
			{
				method: "POST",
			},
		);
	}

	async saveGraph(graphName: string, username = "default") {
		return this.fetchJson(
			`/api/graph/save/${encodeURIComponent(graphName)}?username=${username}`,
			{
				method: "POST",
			},
		);
	}

	async updateWorkflowName(graphName: string, newName: string) {
		return this.fetchJson(`/api/graph/${encodeURIComponent(graphName)}/name`, {
			method: "PUT",
			body: JSON.stringify({ new_name: newName }),
		});
	}

	async updateWorkflowDescription(graphName: string, description: string) {
		return this.fetchJson(
			`/api/graph/${encodeURIComponent(graphName)}/description`,
			{
				method: "PUT",
				body: JSON.stringify({ description }),
			},
		);
	}

	// Node operations
	async createNode(data: CreateNodeRequest) {
		return this.fetchJson("/api/graph/node/create", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async createSubAgent(data: CreateSubAgentRequest) {
		return this.fetchJson("/api/graph/node/create-sub-agent", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async updateNode(graphName: string, nodeId: string, updates: any) {
		const payload = {
			graph_name: graphName,
			node_id: nodeId,
			updates,
		};

		
		const result = await this.fetchJson("/api/graph/node/update", {
			method: "PUT",
			body: JSON.stringify(payload),
		});

		return result;
	}

	async deleteNode(graphName: string, nodeId: string) {
		return this.fetchJson(
			`/api/graph/node/${encodeURIComponent(graphName)}/${encodeURIComponent(nodeId)}`,
			{
				method: "DELETE",
			},
		);
	}

	// Connection operations
	async createConnection(data: CreateConnectionRequest) {
		return this.fetchJson("/api/graph/connection/create", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async deleteConnection(
		graphName: string,
		sourceId: string,
		targetId: string,
	) {
		return this.fetchJson("/api/graph/connection/delete", {
			method: "DELETE",
			body: JSON.stringify({
				graph_name: graphName,
				source_id: sourceId,
				target_id: targetId,
			}),
		});
	}

	// Template operations
	async getToolTemplates() {
		return this.fetchJson("/api/graph/templates/tools");
	}

	async getAgentTemplates() {
		return this.fetchJson("/api/graph/templates/agents");
	}

	// LLM operations
	async getLLMProviders() {
		return this.fetchJson("/api/graph/llm/providers");
	}

	async getLLMModels(provider: string) {
		return this.fetchJson(`/api/graph/llm/models/${provider}`);
	}

	// Validation
	async validateGraph(graphName: string) {
		return this.fetchJson(
			`/api/graph/validate/${encodeURIComponent(graphName)}`,
		);
	}

	// Workflow File Storage (Persistent)
	async getWorkflowFile(graphName: string, includeContent = false) {
		const params = includeContent ? "?include_content=true" : "";
		return this.fetchJson(
			`/api/graph/${encodeURIComponent(graphName)}/file${params}`,
		);
	}

	async uploadWorkflowFile(graphName: string, file: File) {
		const formData = new FormData();
		formData.append("file", file);
		const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
		return fetch(`${apiBaseUrl}/api/graph/${encodeURIComponent(graphName)}/file`, {
			method: "POST",
			body: formData,
			credentials: "include",
		}).then((res) => res.json());
	}

	async deleteWorkflowFile(graphName: string) {
		return this.fetchJson(
			`/api/graph/${encodeURIComponent(graphName)}/file`,
			{ method: "DELETE" },
		);
	}

	// Execution operations
	async executeGraph(data: ExecutionRequest): Promise<ExecuteGraphResponse> {
		return this.fetchJson<ExecuteGraphResponse>("/api/graph/execute", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async getExecutionStatus(
		executionId: string,
	): Promise<ExecutionStatusResponse> {
		return this.fetchJson<ExecutionStatusResponse>(
			`/api/graph/execution/${encodeURIComponent(executionId)}/status`,
		);
	}

	// HTTP Execution operations
	async getHttpExecutionInfo(graphName: string) {
		return this.fetchJson(
			`/api/http-execution/info/${encodeURIComponent(graphName)}`,
		);
	}

	async generateExecutionToken(graphName: string) {
		return this.fetchJson(
			`/api/http-execution/token/${encodeURIComponent(graphName)}`,
			{
				method: "POST",
			},
		);
	}

	async getExecutionToken(graphName: string) {
		return this.fetchJson(
			`/api/http-execution/token/${encodeURIComponent(graphName)}`,
		);
	}

	async revokeExecutionToken(graphName: string) {
		return this.fetchJson(
			`/api/http-execution/token/${encodeURIComponent(graphName)}`,
			{
				method: "DELETE",
			},
		);
	}

	async getLatestHttpExecution(graphName: string) {
		return this.fetchJson(
			`/api/http-execution/latest-execution/${encodeURIComponent(graphName)}`,
		);
	}

	// Memory operations
	async clearAgentMemory(agentId: string, graphExecutionId?: string) {
		const url = graphExecutionId
			? `/api/memory/agents/${agentId}/memories?graph_execution_id=${graphExecutionId}`
			: `/api/memory/agents/${agentId}/memories`;

		return this.fetchJson(url, {
			method: "DELETE",
		});
	}

	async getConversationHistory(
		agentId: string,
		graphExecutionId?: string,
		limit = 10,
	) {
		const params = new URLSearchParams();
		if (graphExecutionId) params.append("graph_execution_id", graphExecutionId);
		params.append("limit", limit.toString());

		return this.fetchJson<{
			agent_id: string;
			history: Array<{
				timestamp: string;
				type: string;
				content: string;
				role: string;
			}>;
		}>(`/api/memory/agents/${agentId}/conversation-history?${params}`);
	}

	async getExecutionHistory(executionId: string) {
		return this.fetchJson(
			`/api/execution-history/executions/${encodeURIComponent(executionId)}`,
		);
	}

	async getNodeExecution(executionId: string, nodeId: string) {
		return this.fetchJson(
			`/api/execution-history/executions/${encodeURIComponent(executionId)}/nodes/${encodeURIComponent(nodeId)}`,
		);
	}

	async deleteExecution(executionId: string) {
		return this.fetchJson(
			`/api/execution-history/executions/${encodeURIComponent(executionId)}`,
			{ method: "DELETE" },
		);
	}

	async getExecutionGuardrailViolations(executionId: string): Promise<ExecutionGuardrailViolation[]> {
		const res = await this.fetchJson<{ success: boolean; violations: Record<string, unknown>[]; count: number }>(
			`/api/execution-history/executions/${encodeURIComponent(executionId)}/guardrail-violations`,
		);
		return (res.violations ?? []).map((v) => ({
			id: v.id as string,
			rule_name: v.rule_name as string,
			policy_name: (v.policy_name as string) ?? "",
			severity: (v.severity as "block" | "warn" | "info") ?? "info",
			category: (v.category as string) ?? null,
			message: (v.message as string) ?? null,
			action_taken: (v.action_taken as string) ?? null,
			agent_node_name: (v.agent_node_name as string) ?? null,
			node_execution_id: (v.node_execution_id as string) ?? null,
			timestamp: (v.created_at as string) ?? null,
			details: (v.details as Record<string, unknown>) ?? null,
		}));
	}

	async getGraphExecutions(graphId?: string, limit = 100, offset = 0, feedbackRating?: "positive" | "negative", workflowId?: string) {
		const params = new URLSearchParams();
		if (graphId) params.append("graph_id", graphId);
		if (workflowId) params.append("workflow_id", workflowId);
		if (feedbackRating) params.append("feedback_rating", feedbackRating);
		params.append("limit", limit.toString());
		params.append("offset", offset.toString());

		return this.fetchJson(`/api/execution-history/executions?${params}`);
	}

	// Execution Feedback APIs
	async submitExecutionFeedback(
		executionId: string,
		rating: "positive" | "negative",
		comment?: string,
		nodeExecutionId?: string,
	) {
		return this.fetchJson<{
			id: string;
			graph_execution_id: string;
			node_execution_id: string | null;
			rating: string;
			comment: string | null;
			user_id: string;
			graph_definition_id: string | null;
			created_at: string | null;
		}>(
			`/api/execution-history/executions/${encodeURIComponent(executionId)}/feedback`,
			{
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					rating,
					comment,
					node_execution_id: nodeExecutionId,
				}),
			},
		);
	}

	async getExecutionFeedback(
		executionId: string,
		nodeExecutionId?: string,
	) {
		const params = new URLSearchParams();
		if (nodeExecutionId)
			params.append("node_execution_id", nodeExecutionId);
		const qs = params.toString();
		return this.fetchJson<
			Array<{
				id: string;
				graph_execution_id: string;
				node_execution_id: string | null;
				rating: string;
				comment: string | null;
				user_id: string;
				graph_definition_id: string | null;
				created_at: string | null;
			}>
		>(
			`/api/execution-history/executions/${encodeURIComponent(executionId)}/feedback${qs ? `?${qs}` : ""}`,
		);
	}

	async deleteExecutionFeedback(
		executionId: string,
		nodeExecutionId?: string,
	) {
		const params = new URLSearchParams();
		if (nodeExecutionId)
			params.append("node_execution_id", nodeExecutionId);
		const qs = params.toString();
		return this.fetchJson(
			`/api/execution-history/executions/${encodeURIComponent(executionId)}/feedback${qs ? `?${qs}` : ""}`,
			{ method: "DELETE" },
		);
	}

	async submitViolationFeedback(
		violationId: string,
		rating: "positive" | "negative",
	) {
		return this.fetchJson(
			`/api/guardrails/violations/${encodeURIComponent(violationId)}/feedback`,
			{
				method: "POST",
				body: JSON.stringify({ rating }),
			},
		);
	}

	async deleteViolationFeedback(violationId: string) {
		return this.fetchJson(
			`/api/guardrails/violations/${encodeURIComponent(violationId)}/feedback`,
			{ method: "DELETE" },
		);
	}

	async listExecutionFeedback(params?: {
		rating?: "positive" | "negative";
		workflow_id?: string;
		limit?: number;
		offset?: number;
	}) {
		const sp = new URLSearchParams();
		if (params?.rating) sp.append("rating", params.rating);
		if (params?.workflow_id) sp.append("workflow_id", params.workflow_id);
		if (params?.limit !== undefined)
			sp.append("limit", String(params.limit));
		if (params?.offset !== undefined)
			sp.append("offset", String(params.offset));
		return this.fetchJson<
			Array<{
				id: string;
				graph_execution_id: string;
				rating: string;
				comment: string | null;
				user_id: string;
				graph_definition_id: string | null;
				created_at: string | null;
			}>
		>(`/api/execution-history/feedback?${sp}`);
	}

	// Checkpoint APIs
	async listThreadCheckpoints(threadId: string) {
		return this.fetchJson(
			`/api/checkpoints/threads/${encodeURIComponent(threadId)}`,
		);
	}

	async resumeFromCheckpoint(payload: {
		graph_name: string;
		thread_id: string;
		checkpoint_id: string;
		new_input?: Record<string, any>;
	}) {
		return this.fetchJson(`/api/checkpoints/resume`, {
			method: "POST",
			body: JSON.stringify(payload),
		});
	}

	// Paused Executions APIs
	async getPausedExecutions(graphName: string, skip = 0, limit = 20) {
		const params = new URLSearchParams({
			skip: skip.toString(),
			limit: limit.toString(),
		});
		return this.fetchJson(
			`/api/executions/paused/${encodeURIComponent(graphName)}?${params}`,
		);
	}

	async getAllPausedExecutions() {
		return this.fetchJson(`/api/executions/paused`);
	}

	async getExecutionState(executionId: string) {
		return this.fetchJson(
			`/api/executions/${encodeURIComponent(executionId)}/state`,
		);
	}

	async getCheckpointData(executionId: string) {
		return this.fetchJson(
			`/api/executions/${encodeURIComponent(executionId)}/checkpoint-data`,
		);
	}

	async cancelPausedExecution(executionId: string) {
		return this.fetchJson(
			`/api/executions/${encodeURIComponent(executionId)}/cancel`,
			{
				method: "POST",
			},
		);
	}

	async pauseExecution(executionId: string) {
		return this.fetchJson(
			`/api/executions/${encodeURIComponent(executionId)}/pause`,
			{
				method: "POST",
			},
		);
	}

	async stopExecution(executionId: string) {
		return this.fetchJson(
			`/api/executions/${encodeURIComponent(executionId)}/stop`,
			{
				method: "POST",
			},
		);
	}

	async resumeManualExecution(executionId: string) {
		return this.fetchJson(
			`/api/executions/${encodeURIComponent(executionId)}/resume-manual`,
			{
				method: "POST",
			},
		);
	}

	async resumePausedExecution(executionId: string, userInput: string) {
		return this.fetchJson(
			`/api/executions/${encodeURIComponent(executionId)}/resume`,
			{
				method: "POST",
				body: JSON.stringify({ user_input: userInput }),
			},
		);
	}

	async cancelExecution(executionId: string) {
		return this.fetchJson(
			`/api/graph/execution/${encodeURIComponent(executionId)}/cancel`,
			{
				method: "POST",
			},
		);
	}

	async listExecutions(graphName?: string) {
		const query = graphName ? `?graph_name=${graphName}` : "";
		return this.fetchJson(`/api/graph/executions${query}`);
	}

	async get<T = any>(
		url: string,
		options?: { params?: Record<string, any> },
	): Promise<T> {
		const params = options?.params;
		const queryString = params
			? "?" +
				Object.entries(params)
					.filter(([, value]) => value !== undefined && value !== null)
					.map(
						([key, value]) =>
							`${encodeURIComponent(key)}=${encodeURIComponent(value)}`,
					)
					.join("&")
			: "";

		return this.fetchJson<T>(`${url}${queryString}`);
	}

	// Structured Output APIs
	async validateStructuredOutputSchema(schema: Record<string, unknown>) {
		return this.fetchJson("/api/graph/structured-outputs/validate", {
			method: "POST",
			body: JSON.stringify(schema),
		});
	}

	async previewStructuredOutputCode(schema: Record<string, unknown>) {
		return this.fetchJson("/api/graph/structured-outputs/preview", {
			method: "POST",
			body: JSON.stringify(schema),
		});
	}

	// Document Management APIs
	async uploadDocuments(
		files: File[],
		collectionId: string,
		options?: {
			chunkSize?: number;
			chunkOverlap?: number;
			loaderMode?: string;
			strategy?: string;
			embeddingDeploymentId?: string;
		},
	) {
		const formData = new FormData();
		files.forEach((file) => formData.append("files", file));
		formData.append("collection_id", collectionId);
		if (options?.chunkSize)
			formData.append("chunk_size", options.chunkSize.toString());
		if (options?.chunkOverlap)
			formData.append("chunk_overlap", options.chunkOverlap.toString());
		if (options?.loaderMode) formData.append("loader_mode", options.loaderMode);
		if (options?.strategy) formData.append("strategy", options.strategy);
		if (options?.embeddingDeploymentId)
			formData.append("embedding_deployment_id", options.embeddingDeploymentId);

		const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/documents/upload`, {
			method: "POST",
			body: formData,
		});

		if (!response.ok) {
			let errorDetail = response.statusText;
			try {
				const errorBody = await response.json();
				if (errorBody?.detail) {
					errorDetail = errorBody.detail;
				}
			} catch {
				// Could not parse error body, use statusText
			}
			throw new Error(errorDetail);
		}

		return response.json();
	}

	async getDocuments(
		collectionId?: string,
		status?: string,
		filterType?: "all" | "my" | "shared",
	): Promise<Document[]> {
		const params = new URLSearchParams();
		if (collectionId) params.append("collection_id", collectionId);
		if (status) params.append("status", status);
		if (filterType) params.append("filter_type", filterType);

		return this.fetchJson(`/api/documents?${params}`);
	}

	async deleteDocument(documentId: string) {
		return this.fetchJson(`/api/documents/${documentId}`, {
			method: "DELETE",
		});
	}

	async reprocessDocument(
		documentId: string,
		config: {
			chunkSize?: number | null;
			chunkOverlap?: number;
			strategy?: string;
			embeddingDeploymentId?: string;
		},
	): Promise<{
		success: boolean;
		document_id: string;
		name: string;
		new_chunk_count: number;
		message: string;
	}> {
		return this.fetchJson("/api/documents/reprocess", {
			method: "POST",
			body: JSON.stringify({
				document_id: documentId,
				chunk_size: config.chunkSize ?? 1000,
				chunk_overlap: config.chunkOverlap ?? 200,
				strategy: config.strategy ?? "recursive",
				embedding_deployment_id: config.embeddingDeploymentId,
			}),
		});
	}

	async getCollections(filterType?: 'all' | 'my' | 'shared'): Promise<DocumentCollection[]> {
		const params = filterType ? `?filter_type=${filterType}` : '';
		return this.fetchJson(`/api/documents/collections${params}`);
	}

	async getCollectionsWithDocuments(): Promise<
		Array<{
			id: string;
			name: string;
			description?: string;
			document_count: number;
			unprocessed_count?: number;
			is_read_only?: boolean;
			created_by_name?: string;
			created_by_email?: string;
			documents: Array<{
				id: string;
				name: string;
				type: string;
				size: number;
				status: string;
				chunk_count: number;
				upload_date: string;
				error_message?: string;
			}>;
		}>
	> {
		return this.fetchJson("/api/documents/collections-with-documents");
	}

	async createCollection(
		name: string,
		description?: string,
		visibleToGroups?: string[],
	): Promise<DocumentCollection> {
		return this.fetchJson("/api/documents/collections", {
			method: "POST",
			body: JSON.stringify({
				name,
				description,
				visible_to_groups: visibleToGroups,
			}),
		});
	}

	async updateCollection(
		collectionId: string,
		data: { name?: string; description?: string; embedding_deployment_id?: string },
	): Promise<DocumentCollection> {
		return this.fetchJson(`/api/documents/collections/${collectionId}`, {
			method: "PATCH",
			body: JSON.stringify(data),
		});
	}

	async reprocessCollection(
		collectionId: string,
		config: { embeddingDeploymentId?: string; chunkSize?: number; chunkOverlap?: number; strategy?: string },
	): Promise<{ success: boolean; reprocessed: number; failed: number; failures: Array<{ id: string; name: string; error: string }> }> {
		return this.fetchJson(`/api/documents/collections/${collectionId}/reprocess`, {
			method: "POST",
			body: JSON.stringify({
				document_id: "bulk",
				chunk_size: config.chunkSize ?? 1000,
				chunk_overlap: config.chunkOverlap ?? 200,
				strategy: config.strategy ?? "recursive",
				embedding_deployment_id: config.embeddingDeploymentId,
			}),
		});
	}

	async updateCollectionVisibility(
		collectionId: string,
		visibleToGroups: string[],
	): Promise<DocumentCollection> {
		return this.fetchJson(`/api/documents/collections/${collectionId}/visibility`, {
			method: "PATCH",
			body: JSON.stringify({ visible_to_groups: visibleToGroups }),
		});
	}

	async deleteCollection(collectionId: string) {
		return this.fetchJson(`/api/documents/collections/${collectionId}`, {
			method: "DELETE",
		});
	}

	async deleteFailedDocuments(
		collectionId: string,
	): Promise<{ message: string }> {
		return this.fetchJson(
			`/api/documents/collections/${collectionId}/failed-documents`,
			{
				method: "DELETE",
			},
		);
	}

	async searchDocuments(
		query: string,
		collectionIds: string[],
		options?: {
			k?: number;
			searchType?: string;
			includeMetadata?: boolean;
			hybridEnabled?: boolean;
			searchMode?: string;
			keywordWeight?: number;
			rrfK?: number;
			textConfig?: string;
			documentIds?: string[];
			embeddingDeploymentId?: string;
		},
	): Promise<{
		query: string;
		results: SearchResult[];
		total_results: number;
	}> {
		return this.fetchJson("/api/documents/search", {
			method: "POST",
			body: JSON.stringify({
				query,
				collection_ids: collectionIds,
				document_ids: options?.documentIds || null,
				embedding_deployment_id: options?.embeddingDeploymentId || null,
				k: options?.k || 4,
				search_type: options?.searchType || "similarity",
				include_metadata: options?.includeMetadata !== false,
				hybrid_enabled: options?.hybridEnabled || false,
				search_mode: options?.searchMode || "vector",
				keyword_weight: options?.keywordWeight || 0.3,
				rrf_k: options?.rrfK || 60,
				text_config: options?.textConfig || "english",
			}),
		});
	}

	async previewChunks(
		text: string,
		config: {
			strategy: string;
			chunkSize: number;
			chunkOverlap: number;
		},
	) {
		return this.fetchJson("/api/documents/preview-chunks", {
			method: "POST",
			body: JSON.stringify({
				text,
				strategy: config.strategy,
				chunk_size: config.chunkSize,
				chunk_overlap: config.chunkOverlap,
			}),
		});
	}

	// Database connection methods
	async getDatabaseConnections(
		activeOnly = true,
		skip = 0,
		limit = 100,
		filterType = "all",
	): Promise<any[]> {
		const params = new URLSearchParams({
			active_only: activeOnly.toString(),
			skip: skip.toString(),
			limit: limit.toString(),
			filter_type: filterType,
		});
		return this.fetchJson(`/api/datasources/connections?${params}`);
	}

	async updateDatabaseConnectionVisibility(
		connectionId: string,
		visibleToGroups: string[],
	): Promise<any> {
		return this.fetchJson(
			`/api/datasources/connections/${connectionId}/visibility`,
			{
				method: "PATCH",
				body: JSON.stringify({ visible_to_groups: visibleToGroups }),
			},
		);
	}

	async createDatabaseConnection(data: any): Promise<any> {
		return this.fetchJson("/api/datasources/connections", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async updateDatabaseConnection(
		connectionId: string,
		data: any,
	): Promise<any> {
		return this.fetchJson(`/api/datasources/connections/${connectionId}`, {
			method: "PUT",
			body: JSON.stringify(data),
		});
	}

	async deleteDatabaseConnection(connectionId: string): Promise<void> {
		return this.fetchJson(`/api/datasources/connections/${connectionId}`, {
			method: "DELETE",
		});
	}

	async testDatabaseConnection(connectionId: string): Promise<any> {
		return this.fetchJson(`/api/datasources/connections/${connectionId}/test`, {
			method: "POST",
		});
	}

	async testDatabaseConnectionConfig(data: any): Promise<any> {
		return this.fetchJson("/api/datasources/connections/test", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async getDatabaseTables(
		connectionId: string,
		forceRefresh = false,
	): Promise<{ tables: string[] }> {
		const params = forceRefresh ? "?force_refresh=true" : "";
		return this.fetchJson(
			`/api/datasources/connections/${connectionId}/tables${params}`,
		);
	}

	async getTableDetails(
		connectionId: string,
		tableName: string,
		forceRefresh = false,
	): Promise<any> {
		const params = forceRefresh ? "?force_refresh=true" : "";
		return this.fetchJson(
			`/api/datasources/connections/${connectionId}/tables/${encodeURIComponent(tableName)}/details${params}`,
		);
	}

	async getTableColumns(
		connectionId: string,
		tableName: string,
	): Promise<{
		table_name: string;
		columns: Array<{
			column_name: string;
			column_type: string;
			is_nullable: boolean;
			is_primary_key: boolean;
		}>;
	}> {
		return this.fetchJson(
			`/api/datasources/connections/${connectionId}/tables/${encodeURIComponent(tableName)}/columns`,
		);
	}

	async getDatabaseSchema(
		connectionId: string,
		forceRefresh = false,
	): Promise<any> {
		// Legacy method - use getDatabaseTables and getTableDetails for better performance
		const params = forceRefresh ? "?force_refresh=true" : "";
		return this.fetchJson(
			`/api/datasources/connections/${connectionId}/schema${params}`,
		);
	}

	async previewDatabaseTable(
		connectionId: string,
		tableName: string,
		limit = 100,
	): Promise<any> {
		return this.fetchJson(
			`/api/datasources/connections/${connectionId}/preview`,
			{
				method: "POST",
				body: JSON.stringify({ table_name: tableName, limit }),
			},
		);
	}

	// API Endpoints methods
	async getApiEndpoints(
		activeOnly = true,
		skip = 0,
		limit = 100,
		filterType = "all",
	) {
		const params = new URLSearchParams({
			active_only: activeOnly.toString(),
			skip: skip.toString(),
			limit: limit.toString(),
			filter_type: filterType,
		});
		return this.fetchJson(`/api/api-endpoints?${params}`);
	}

	async createApiEndpoint(data: Record<string, unknown>) {
		return this.fetchJson("/api/api-endpoints", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async updateApiEndpoint(
		endpointId: string,
		data: Record<string, unknown>,
	) {
		return this.fetchJson(`/api/api-endpoints/${endpointId}`, {
			method: "PUT",
			body: JSON.stringify(data),
		});
	}

	async deleteApiEndpoint(endpointId: string) {
		return this.fetchJson(`/api/api-endpoints/${endpointId}`, {
			method: "DELETE",
		});
	}

	async updateApiEndpointVisibility(
		endpointId: string,
		visibleToGroups: string[],
	) {
		return this.fetchJson(
			`/api/api-endpoints/${endpointId}/visibility`,
			{
				method: "PATCH",
				body: JSON.stringify({ visible_to_groups: visibleToGroups }),
			},
		);
	}

	async getApiEndpointTemplates() {
		return this.fetchJson("/api/api-endpoints/templates");
	}

	async testApiEndpoint(endpointId: string) {
		return this.fetchJson(`/api/api-endpoints/${endpointId}/test`, {
			method: "POST",
		});
	}

	// Workflow Publishing API methods
	async publishWorkflow(
		graphName: string,
		config: {
			custom_slug?: string;
			description?: string;
			require_authentication?: boolean;
			rate_limit?: { [key: string]: number };
			allowed_origins?: string[];
			webhook_url?: string;
			input_schema?: any;
		},
	) {
		return this.fetchJson(
			`/api/publish/workflow/${encodeURIComponent(graphName)}`,
			{
				method: "POST",
				body: JSON.stringify(config),
			},
		);
	}

	async unpublishWorkflow(graphName: string) {
		return this.fetchJson(
			`/api/publish/workflow/${encodeURIComponent(graphName)}`,
			{
				method: "DELETE",
			},
		);
	}

	async updateWorkflowPublication(
		graphName: string,
		config: {
			custom_slug?: string;
			description?: string;
			require_authentication?: boolean;
			rate_limit?: { [key: string]: number };
			allowed_origins?: string[];
			webhook_url?: string;
			input_schema?: any;
		},
	) {
		return this.fetchJson(
			`/api/publish/workflow/${encodeURIComponent(graphName)}`,
			{
				method: "PUT",
				body: JSON.stringify(config),
			},
		);
	}

	async getWorkflowPublication(graphName: string) {
		return this.fetchJson(
			`/api/publish/workflow/${encodeURIComponent(graphName)}`,
		);
	}

	async getWorkflowPublicationStatus(
		graphName: string,
	): Promise<{ graph_name: string; is_published: boolean }> {
		return this.fetchJson(
			`/api/publish/workflow/${encodeURIComponent(graphName)}/status`,
		);
	}

	async getPublishedWorkflows() {
		return this.fetchJson("/api/publish/workflows");
	}

	// Tool execution API methods
	async getAgentToolExecutions(
		executionId: string,
		agentId: string,
	): Promise<any> {
		return this.fetchJson(
			`/api/graph/execution/${encodeURIComponent(executionId)}/agent/${encodeURIComponent(agentId)}/tools`,
		);
	}

	// Local-first batch update API (for efficient sync)
	async batchUpdateGraph(data: {
		graphName: string;
		changes: Array<{
			type:
				| "ADD_NODE"
				| "UPDATE_NODE"
				| "DELETE_NODE"
				| "ADD_CONNECTION"
				| "DELETE_CONNECTION"
				| "UPDATE_NODE_POSITION";
			timestamp: number;
			data: any;
		}>;
	}): Promise<{ success: boolean; graph?: any; version?: number; error?: string }> {
		return this.fetchJson("/api/graph/batch-update", {
			method: "POST",
			body: JSON.stringify({
				graph_name: data.graphName,
				changes: data.changes,
			}),
		});
	}

	// Azure OAuth methods
	async startAzureLogin(): Promise<void> {
		// For OAuth, we need to redirect to the backend domain directly
		// since the frontend and backend are on separate domains
		window.location.href = `https://nexusagent-be.azurewebsites.net/auth/login`;
	}

	async getAzureAuthCallback(): Promise<{
		ok: boolean;
		has_refresh_token: boolean;
		me: {
			status: number;
			body: any;
		};
	}> {
		return this.fetchJson("/auth/callback");
	}

	// Library API methods
	async listTemplates(params?: {
		search?: string;
		category?: string;
		complexity?: string;
		tags?: string[];
		sort_by?: string;
		sort_order?: string;
		limit?: number;
	}): Promise<any> {
		const queryParams = new URLSearchParams();
		if (params?.search) queryParams.append("search", params.search);
		if (params?.category) queryParams.append("category", params.category);
		if (params?.complexity) queryParams.append("complexity", params.complexity);
		if (params?.tags)
			params.tags.forEach((tag) => queryParams.append("tags", tag));
		if (params?.sort_by) queryParams.append("sort_by", params.sort_by);
		if (params?.sort_order) queryParams.append("sort_order", params.sort_order);
		if (params?.limit) queryParams.append("limit", params.limit.toString());

		const query = queryParams.toString();
		return this.fetchJson(`/api/library/templates${query ? "?" + query : ""}`);
	}

	async listAgentTemplates(params?: {
		search?: string;
		category?: string;
		complexity?: string;
		tags?: string[];
		sort_by?: string;
		sort_order?: string;
		limit?: number;
	}): Promise<any> {
		const queryParams = new URLSearchParams();
		if (params?.search) queryParams.append("search", params.search);
		if (params?.category) queryParams.append("category", params.category);
		if (params?.complexity) queryParams.append("complexity", params.complexity);
		if (params?.tags)
			params.tags.forEach((tag) => queryParams.append("tags", tag));
		if (params?.sort_by) queryParams.append("sort_by", params.sort_by);
		if (params?.sort_order) queryParams.append("sort_order", params.sort_order);
		if (params?.limit) queryParams.append("limit", params.limit.toString());

		const query = queryParams.toString();
		return this.fetchJson(`/api/library/agents${query ? "?" + query : ""}`);
	}

	async listLibraryItems(params?: {
		search?: string;
		category?: string;
		complexity?: string;
		tags?: string[];
		sort_by?: string;
		sort_order?: string;
		limit?: number;
		count_only?: boolean;
	}): Promise<import("@/types/library").LibraryDiscoveryResponse> {
		const queryParams = new URLSearchParams();
		if (params?.search) queryParams.append("search", params.search);
		if (params?.category) queryParams.append("category", params.category);
		if (params?.complexity) queryParams.append("complexity", params.complexity);
		if (params?.tags)
			params.tags.forEach((tag) => queryParams.append("tags", tag));
		if (params?.sort_by) queryParams.append("sort_by", params.sort_by);
		if (params?.sort_order) queryParams.append("sort_order", params.sort_order);
		if (params?.limit) queryParams.append("limit", params.limit.toString());
		if (params?.count_only) queryParams.append("count_only", "true");

		const query = queryParams.toString();
		return this.fetchJson(`/api/library/discovery${query ? "?" + query : ""}`);
	}

	async getCategoryCounts(): Promise<
		import("@/types/library").CategoryCountsResponse
	> {
		return this.fetchJson("/api/library/discovery/category-counts");
	}

	async getTemplate(templateId: string): Promise<any> {
		try {
			return await this.fetchJson(
				`/api/library/template/${encodeURIComponent(templateId)}`,
			);
		} catch (primaryError) {
			console.warn(
				"[API] template alias lookup failed, retrying original route",
				primaryError,
			);
			return this.fetchJson(
				`/api/library/templates/${encodeURIComponent(templateId)}`,
			);
		}
	}

	async getAgentTemplate(agentId: string): Promise<any> {
		return this.fetchJson(`/api/library/agents/${encodeURIComponent(agentId)}`);
	}

	async findTemplateByWorkflowName(workflowName: string): Promise<{
		success: boolean;
		template: {
			id: string;
			name: string;
			description: string;
			category: string[];
			tags: string[];
			complexity?: string;
			icon_color?: string;
			version: number;
		} | null;
	}> {
		return this.fetchJson(
			`/api/library/templates/by-workflow-name/${encodeURIComponent(workflowName)}`,
		);
	}

	async addToLibrary(data: {
		workflow_id: string;
		name: string;
		description: string;
		category: string[];
		tags: string[];
		complexity?: string;
		icon_color?: string;
	}): Promise<any> {
		return this.fetchJson("/api/library/templates", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async addAgentToLibrary(data: {
		workflow_id: string;
		agent_node_id: string;
		name: string;
		description: string;
		category: string[];
		tags: string[];
		icon_color?: string;
	}): Promise<any> {
		return this.fetchJson("/api/library/agents", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async importAgentFromJSON(data: {
		agent_json: Record<string, any>;
		metadata_override?: {
			category?: string[];
			tags?: string[];
			complexity?: string;
			icon_color?: string;
		};
	}): Promise<any> {
		return this.fetchJson("/api/library/agents/import", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async importTemplatesFromCSV(files: {
		workflows_csv: File;
		graph_definitions_csv: File;
		workflow_templates_csv: File;
	}): Promise<any> {
		const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
		const formData = new FormData();
		formData.append("workflows_csv", files.workflows_csv);
		formData.append("graph_definitions_csv", files.graph_definitions_csv);
		formData.append("workflow_templates_csv", files.workflow_templates_csv);

		const response = await fetch(
			`${apiBaseUrl}/api/library/templates/import-csv`,
			{
				method: "POST",
				body: formData,
			},
		);

		if (!response.ok) {
			const error = await response
				.json()
				.catch(() => ({ detail: "Unknown error" }));
			throw new Error(
				error.detail || `HTTP error! status: ${response.status}`,
			);
		}

		return response.json();
	}

	async cloneTemplate(
		templateId: string,
		options?: { workspace_id?: string; target_name?: string },
	): Promise<any> {
		return this.fetchJson(
			`/api/library/templates/${encodeURIComponent(templateId)}/clone`,
			{
				method: "POST",
				body: JSON.stringify(options || {}),
			},
		);
	}

	async getTemplateDependencies(templateId: string): Promise<CollectionDependency[]> {
		const response = await this.fetchJson<{
			success: boolean;
			dependencies: CollectionDependency[];
			count: number;
		}>(`/api/library/templates/${encodeURIComponent(templateId)}/dependencies`);
		return response.dependencies;
	}

	async cloneAgentTemplate(
		agentId: string,
		options?: { workspace_id?: string; target_name?: string },
	): Promise<any> {
		return this.fetchJson(
			`/api/library/agents/${encodeURIComponent(agentId)}/clone`,
			{
				method: "POST",
				body: JSON.stringify(options || {}),
			},
		);
	}

	async updateTemplate(
		templateId: string,
		data: {
			description?: string;
			category?: string;
			tags?: string[];
			complexity?: string;
			estimated_time?: string;
			icon_color?: string;
		},
	): Promise<any> {
		return this.fetchJson(
			`/api/library/templates/${encodeURIComponent(templateId)}`,
			{
				method: "PATCH",
				body: JSON.stringify(data),
			},
		);
	}

	async deactivateTemplate(templateId: string): Promise<any> {
		return this.fetchJson(
			`/api/library/templates/${encodeURIComponent(templateId)}`,
			{
				method: "DELETE",
			},
		);
	}

	async deleteAgentTemplate(agentId: string): Promise<any> {
		return this.fetchJson(
			`/api/library/agents/${encodeURIComponent(agentId)}`,
			{
				method: "DELETE",
			},
		);
	}

	// Group Management APIs
	async getGroups(params?: {
		limit?: number;
		offset?: number;
		search?: string;
	}): Promise<GroupsListResponse> {
		const queryParams = new URLSearchParams();
		if (params?.limit !== undefined) {
			queryParams.append("limit", params.limit.toString());
		}
		if (params?.offset !== undefined) {
			queryParams.append("offset", params.offset.toString());
		}
		if (params?.search) {
			queryParams.append("search", params.search);
		}
		const url = `/api/groups${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;
		return this.fetchJson<GroupsListResponse>(url);
	}

	async createGroup(name: string, description?: string): Promise<Group> {
		return this.fetchJson<Group>("/api/groups", {
			method: "POST",
			body: JSON.stringify({ name, description }),
		});
	}

	async updateGroup(groupId: string, name: string, description?: string): Promise<Group> {
		return this.fetchJson<Group>(`/api/groups/${encodeURIComponent(groupId)}`, {
			method: "PATCH",
			body: JSON.stringify({ name, description }),
		});
	}

	async deleteGroup(groupId: string): Promise<void> {
		return this.fetchJson(`/api/groups/${encodeURIComponent(groupId)}`, {
			method: "DELETE",
		});
	}

	async getGroupMembers(groupId: string): Promise<GroupMember[]> {
		return this.fetchJson<GroupMember[]>(`/api/groups/${encodeURIComponent(groupId)}/members`);
	}

	async addGroupMember(groupId: string, userId: string): Promise<void> {
		return this.fetchJson(`/api/groups/${encodeURIComponent(groupId)}/members`, {
			method: "POST",
			body: JSON.stringify({ user_id: userId }),
		});
	}

	async removeGroupMember(groupId: string, userId: string): Promise<void> {
		return this.fetchJson(`/api/groups/${encodeURIComponent(groupId)}/members/${encodeURIComponent(userId)}`, {
			method: "DELETE",
		});
	}

	async getAllUsers(): Promise<UserInfo[]> {
		return this.fetchJson<UserInfo[]>("/api/groups/users");
	}

	async getUserGroups(userId: string): Promise<string[]> {
		return this.fetchJson<string[]>(`/api/groups/users/${encodeURIComponent(userId)}/groups`);
	}

	// File operations
	/**
	 * Get the URL for downloading a file from the database.
	 *
	 * @param fileId - The file UUID
	 * @param download - If true, forces download with Content-Disposition: attachment
	 * @returns Full URL to download the file
	 */
	async getFileUrl(fileId: string, download: boolean = true): Promise<string> {
		const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
		return `${apiBaseUrl}/api/files/${fileId}${download ? "?download=true" : ""}`;
	}

	// Access token
	/**
	 * Get the current user's Azure AD access token for HTTP execution.
	 * The token is extracted from the current OAuth session and typically
	 * expires within ~1 hour.
	 */
	async getAccessToken(): Promise<{
		token: string;
		expires_at: number | null;
		email: string | null;
	}> {
		return this.fetchJson("/api/auth/access-token");
	}

	// Workflow HTTP trigger token
	/**
	 * Get the auto-generated HTTP trigger token for a workflow.
	 * This persistent token is used in the Authorization: Bearer header
	 * when calling the HTTP execution endpoints.
	 */
	async getWorkflowHttpTriggerToken(
		graphName: string,
	): Promise<{ success: boolean; token: string; graph_name: string }> {
		return this.fetchJson(
			`/api/graph/${encodeURIComponent(graphName)}/http-trigger-token`,
		);
	}

	/**
	 * Regenerate the HTTP trigger token for a workflow.
	 * The previous token is immediately invalidated.
	 */
	async regenerateWorkflowHttpTriggerToken(
		graphName: string,
	): Promise<{
		success: boolean;
		token: string;
		graph_name: string;
		message: string;
	}> {
		return this.fetchJson(
			`/api/graph/${encodeURIComponent(graphName)}/http-trigger-token/regenerate`,
			{ method: "POST" },
		);
	}

	// Workflow Schedule APIs
	async getWorkflowSchedule(workflowId: string): Promise<WorkflowSchedule> {
		return this.fetchJson<WorkflowSchedule>(
			`/api/schedules/workflow/${encodeURIComponent(workflowId)}`,
		);
	}

	async updateWorkflowSchedule(
		workflowId: string,
		data: ScheduleRequest,
	): Promise<WorkflowSchedule> {
		return this.fetchJson<WorkflowSchedule>(
			`/api/schedules/workflow/${encodeURIComponent(workflowId)}`,
			{
				method: "PUT",
				body: JSON.stringify(data),
			},
		);
	}

	async deleteWorkflowSchedule(workflowId: string): Promise<void> {
		return this.fetchJson(
			`/api/schedules/workflow/${encodeURIComponent(workflowId)}`,
			{
				method: "DELETE",
			},
		);
	}

	async pauseWorkflowSchedule(workflowId: string): Promise<WorkflowSchedule> {
		return this.fetchJson<WorkflowSchedule>(
			`/api/schedules/workflow/${encodeURIComponent(workflowId)}/pause`,
			{
				method: "POST",
			},
		);
	}

	async resumeWorkflowSchedule(workflowId: string): Promise<WorkflowSchedule> {
		return this.fetchJson<WorkflowSchedule>(
			`/api/schedules/workflow/${encodeURIComponent(workflowId)}/resume`,
			{
				method: "POST",
			},
		);
	}

	async triggerWorkflowSchedule(workflowId: string): Promise<{ success: boolean; execution_id: string }> {
		return this.fetchJson<{ success: boolean; execution_id: string }>(
			`/api/schedules/workflow/${encodeURIComponent(workflowId)}/trigger`,
			{
				method: "POST",
			},
		);
	}

	// Workflow Sharing APIs
	async getWorkflowMembers(workflowId: string): Promise<{
		members: Array<{
			user_id: string;
			user_name: string | null;
			user_email: string | null;
			role: string;
			is_owner: boolean;
		}>;
		workflow_id: string;
		can_manage: boolean;
	}> {
		return this.fetchJson(
			`/api/sharing/${encodeURIComponent(workflowId)}/members`,
		);
	}

	async addWorkflowMember(
		workflowId: string,
		userId: string,
		role: string,
	): Promise<{ success: boolean; message: string }> {
		return this.fetchJson(
			`/api/sharing/${encodeURIComponent(workflowId)}/members`,
			{
				method: "POST",
				body: JSON.stringify({ user_id: userId, role }),
			},
		);
	}

	async removeWorkflowMember(
		workflowId: string,
		userId: string,
	): Promise<{ success: boolean; message: string }> {
		return this.fetchJson(
			`/api/sharing/${encodeURIComponent(workflowId)}/members/${encodeURIComponent(userId)}`,
			{ method: "DELETE" },
		);
	}

	async updateWorkflowMemberRole(
		workflowId: string,
		userId: string,
		role: string,
	): Promise<{ success: boolean; message: string }> {
		return this.fetchJson(
			`/api/sharing/${encodeURIComponent(workflowId)}/members/${encodeURIComponent(userId)}/role`,
			{
				method: "PUT",
				body: JSON.stringify({ role }),
			},
		);
	}

}

export const api = new ApiClient();
