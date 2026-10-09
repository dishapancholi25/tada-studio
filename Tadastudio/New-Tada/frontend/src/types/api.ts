/**
 * TypeScript interfaces for API responses and data structures
 */

// Execution Status Types
export type ExecutionStatusType =
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
export type NodeType =
	| "START"
	| "END"
	| "AGENT"
	| "TOOL"
	| "CONDITIONAL"
	| "CONDITION"
	| "DOCUMENT_SEARCH"
	| "DOCUMENT_RETRIEVE"
	| "DOCUMENT_LOAD"
	| "DATABASE_QUERY"
	| "DATABASE_QUERY_ACTION"
	| "HTTP_REQUEST"
	| "HTTP_REQUEST_ACTION"
	| "WEB_SEARCH"
	| "MCP_SERVER"
	| "EMAIL_SEND"
	| "EMAIL_SEND_TOOL"
	| "FILE_WRITE"
	| "DATABASE_INSERT"
	| "CHECKPOINT";

// Conversation History Interface
export interface ConversationMessage {
	role: "user" | "assistant";
	content: string;
	timestamp?: string;
}

// Node Execution Interface
export interface NodeExecution {
	id: string;
	node_id: string;
	node_name: string;
	node_type: NodeType;
	execution_order: number;
	status: ExecutionStatusType;
	start_time: string | null;
	end_time: string | null;
	duration_seconds: number | null;
	input_data: Record<string, any> | null;
	output_data: Record<string, any> | null;
	error_message: string | null;
	node_metadata: Record<string, any> | null;
	is_sub_agent: boolean;
	parent_agent_id?: string | null;
	parent_agent_name?: string | null;
	input_tokens: number | null;
	output_tokens: number | null;
	total_tokens: number | null;
	token_metadata: Record<string, any> | null;
	// Cost tracking
	prompt_cost?: number | null;
	completion_cost?: number | null;
	total_cost?: number | null;
	created_at: string | null;
	// Review iteration for agent review tracking
	review_iteration?: number | null;
}

// Graph Execution Interface
export interface GraphExecution {
	id: string;
	graph_id: string;
	graph_name: string;
	graph_definition?: GraphDefinition;
	workflow_id?: string;
	graph_definition_id?: string | null;
	graph_version?: number | null;
	status: ExecutionStatusType;
	start_time: string | null;
	end_time: string | null;
	duration_seconds: number | null;
	input_data?: Record<string, any> | null;
	output_data?: Record<string, any> | null;
	error_message: string | null;
	user_id: string | null;
	created_at: string | null;
	node_executions?: NodeExecution[];
	trigger_type?: string | null;
	// Node counts for list view (when node_executions not loaded)
	node_count?: number;
	completed_node_count?: number;
	// Pre-fetched feedback rating for list view (avoids per-card API calls)
	feedback_rating?: "positive" | "negative" | null;
}

// Response from executions list endpoint
export interface ExecutionsListResponse {
	executions: GraphExecution[];
	total_count: number;
	has_more: boolean;
}

// Execution Status Response
export interface ExecutionStatusResponse {
	success: boolean;
	execution_status: {
		execution_id: string;
		status: ExecutionStatusType;
		start_time: string;
		graph_name: string;
		current_node: string | null;
		current_node_name: string | null;
		error: string | null;
		db_execution_id: string | null;
		node_execution_map: Record<string, string>;
		running_nodes: Record<string, string>;
		node_executions?: Record<string, NodeExecution>;
	};
}

export interface ExecuteGraphResponse {
	success: boolean;
	message: string;
	execution_id: string;
	async: boolean;
	status_endpoint: string;
}

// Graph Definition Types
export interface GraphDefinition {
	name: string;
	workflow_id?: string; // UUID for unique workflow identification
	description?: string;
	nodes: GraphNode[];
	edges: GraphEdge[];
	metadata?: Record<string, any>;
}

export interface GraphNode {
	id: string;
	name: string;
	type: NodeType;
	position: { x: number; y: number };
	data: {
		llm?: string;
		model?: string;
		prompt?: string;
		tools?: string[];
		is_sub_agent?: boolean;
		agent_config?: AgentConfig;
		[key: string]: any;
	};
}

export interface GraphEdge {
	id: string;
	source: string;
	target: string;
	type?: string;
	data?: Record<string, any>;
}

export interface AgentConfig {
	is_orchestrator?: boolean;
	delegated_agents?: string[];
	llm_config?: {
		llm_type: string;
		model: string;
		temperature?: number;
		api_key?: string;
	};
	tools?: string[];
	system_message?: string;
}

// Group Management Types
export interface Group {
	id: string;
	name: string;
	description?: string;
	is_system: boolean;
	created_by_user_id?: string;
	created_by_name?: string;
	member_count: number;
	created_at: string;
}

export interface GroupsListResponse {
	groups: Group[];
	total_count: number;
}

export interface GroupMember {
	user_id: string;
	user_name?: string;
	user_email?: string;
	added_at: string;
	is_protected?: boolean;
}

export interface UserInfo {
	id: string;
	email?: string;
	name?: string;
}

// Workflow Schedule Types
export interface WorkflowSchedule {
	published_workflow_id: string;
	workflow_id: string;
	cron_expression: string | null;
	timezone: string;
	is_active: boolean;
	input?: string | null;
	last_run_at: string | null;
	next_run_at: string | null;
	run_count: number;
	failure_count: number;
}

export interface ScheduleRequest {
	cron_expression: string;
	timezone: string;
	is_active: boolean;
	input: string;
}

export interface CollectionDependency {
	collection_id: string | null;
	collection_name: string;
	visible_to_groups: string[];
	has_access: boolean;
	access_reason: string;  // "owner", "global", "group: <name>", "no access"
	created_by_name?: string | null;
}

// User Management Types
export type UserRole = "PENDING" | "USER" | "ADMIN" | "SYSTEM";

export interface UserListItem {
	id: string;
	email: string | null;
	name: string | null;
	role: UserRole;
	last_login_at: string | null;
	created_at: string;
	group_count: number;
}

export interface UserDetail extends UserListItem {
	groups: Group[];
}

export interface UsersListResponse {
	users: UserListItem[];
	total_count: number;
}

// Type guard functions
export function isUserAdmin(user: UserListItem | UserDetail): boolean {
	return user.role === "ADMIN";
}

export function isUserPending(user: UserListItem | UserDetail): boolean {
	return user.role === "PENDING";
}

export function canUserAccess(user: UserListItem | UserDetail): boolean {
	return user.role !== "PENDING";
}
