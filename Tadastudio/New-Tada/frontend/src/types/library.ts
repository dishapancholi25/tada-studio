/**
 * Type definitions for workflow library and templates
 */

export interface WorkflowTemplateGraphDefinition {
	name?: string;
	description?: string;
	nodes: any[];
	edges?: any[];
	connections?: any[];
	metadata?: Record<string, any>;
	[key: string]: any;
}

export interface WorkflowTemplateDetail extends WorkflowTemplate {
	graph_definition: {
		id: string;
		name: string;
		workspace_id: string;
		workflow_id?: string | null;
		description?: string | null;
		version?: number | null;
		is_latest?: boolean | null;
		definition: WorkflowTemplateGraphDefinition;
		created_at?: string | null;
		updated_at?: string | null;
	};
}

export interface AgentTemplate extends WorkflowTemplate {
	primary_agent_node_id?: string | null;
	primary_agent_label?: string | null;
	agent_metadata?: Record<string, any>;
}

export interface AgentTemplateDetail extends AgentTemplate {
	graph_definition: WorkflowTemplateDetail["graph_definition"];
}

/**
 * Workflow template metadata
 */
export interface WorkflowTemplate {
	id: string;
	workflow_id: string;
	graph_definition_id: string;
	name: string;
	description: string;
	category: string[];
	tags: string[];
	complexity?: "beginner" | "intermediate" | "advanced";
	icon_color?: string;
	usage_count: number;
	version: number;
	created_at: string;
	creator_name: string;
	creator_email?: string;
	node_count: number;
	agent_count: number;
	tool_count: number;
}

/**
 * Request to add a workflow to the library
 */
export interface AddToLibraryRequest {
	workflow_id: string;
	name: string;
	description: string;
	category: string[];
	tags: string[];
	complexity?: "beginner" | "intermediate" | "advanced";
	icon_color?: string;
}

export interface AddAgentTemplateRequest {
	workflow_id: string;
	agent_node_id: string;
	name: string;
	description: string;
	category: string[];
	tags: string[];
	icon_color?: string;
}

/**
 * Request to clone a template
 */
export interface CloneTemplateRequest {
	workspace_id?: string;
	target_name?: string;
}

/**
 * Request to update template metadata
 */
export interface UpdateTemplateRequest {
	name?: string;
	description?: string;
	category?: string[];
	tags?: string[];
	complexity?: "beginner" | "intermediate" | "advanced";
	icon_color?: string;
}

/**
 * Query parameters for listing templates
 */
export interface ListTemplatesParams {
	search?: string;
	category?: string;
	complexity?: "beginner" | "intermediate" | "advanced";
	tags?: string[];
	sort_by?: "created_at" | "name" | "category" | "complexity" | "usage_count";
	sort_order?: "asc" | "desc";
	limit?: number;
}

/**
 * Response from listing templates
 */
export interface ListTemplatesResponse {
	success: boolean;
	templates: WorkflowTemplate[];
	count: number;
}

export interface ListAgentsResponse {
	success: boolean;
	agents: AgentTemplate[];
	count: number;
}

export interface LibraryDiscoveryResponse {
	success: boolean;
	workflows: WorkflowTemplate[];
	agents: AgentTemplate[];
	counts: {
		workflows: number;
		agents: number;
	};
}

export interface CategoryCounts {
	agents: number;
	workflows: number;
}

export interface CategoryCountsResponse {
	success: boolean;
	category_counts: Record<string, CategoryCounts>;
}

/**
 * Response from adding to library
 */
export interface AddToLibraryResponse {
	success: boolean;
	template_id: string;
	message: string;
}

export interface AddAgentTemplateResponse {
	success: boolean;
	template_id: string;
	message: string;
}

/**
 * Response from cloning a template
 */
export interface CloneTemplateResponse {
	success: boolean;
	workflow_id: string;
	message: string;
}

/**
 * Predefined categories/areas for templates
 */
export const TEMPLATE_CATEGORIES = [
	"Finance",
	"Sales",
	"Recruitment",
	"Marketing",
	"Customer Service",
	"Education",
	"Operations",
	"Analytics",
	"Technology",
	"Risk & Compliance",
	"Human Resources",
	"Cybersecurity",
	"General",
] as const;

export type TemplateCategory = (typeof TEMPLATE_CATEGORIES)[number];

/**
 * Category area with display information
 */
export interface CategoryArea {
	name: TemplateCategory;
	imageUrl?: string;
	imageQuery?: string;
}

/**
 * Complexity levels
 */
export const COMPLEXITY_LEVELS = [
	"beginner",
	"intermediate",
	"advanced",
] as const;

export type ComplexityLevel = (typeof COMPLEXITY_LEVELS)[number];
