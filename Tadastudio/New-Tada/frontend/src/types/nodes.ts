// Node type definitions

export interface SubWorkflowConfig {
	// Core workflow configuration
	workflow_name?: string; // Display name for the workflow
	delegation_description?: string; // When agent should trigger this workflow

	// Input/Output configuration
	input_schema?: Record<string, any>; // Expected inputs from agent
	output_schema?: Record<string, any>; // Expected outputs to agent
	input_description?: string; // Human-readable description of expected inputs
	output_description?: string; // Human-readable description of outputs

	// Execution configuration
	timeout?: number; // Timeout in seconds for workflow execution
	share_context?: boolean; // Share parent execution context with workflow
	max_retries?: number; // Number of retry attempts on failure

	// Advanced configuration
	allow_parallel_execution?: boolean; // Allow multiple instances to run in parallel
	cache_results?: boolean; // Cache results for identical inputs
	cache_ttl?: number; // Cache time-to-live in seconds

	// Connection to parent agent
	parent_agent_id?: string; // ID of the agent this workflow belongs to

	// Workflow structure tracking
	workflow_nodes?: string[]; // Node IDs that are part of this workflow
	end_node_id?: string; // ID of the END node for this workflow
	target_workflow_id?: string; // Saved workflow UUID to execute
}

export interface ForEachConfig {
	source_mode?: "previous" | "specific" | "start";
	source_node_id?: string;
	field_path?: string;
	concurrency_limit?: number;
	rate_limit_per_second?: number | null;
	/** Process only the first N items and skip the rest (testing subsets). */
	item_limit?: number | null;
	max_iterations?: number;
	allowed_fields?: string[] | null;
	max_item_bytes?: number | null;
	error_strategy?: "continue_on_error" | "fail_fast";
	max_retries_per_item?: number;
}

export interface InputVariableMapping {
	variable_name: string;
	source_mode: "previous" | "specific" | "static" | "current_item";
	source_node_id?: string;
	source_field_path?: string;
	static_value?: any;
	default_value?: any;
}

export interface CodeExecutorConfig {
	language: "python" | "javascript";
	code: string;
	timeout_seconds?: number;
	memory_limit_mb?: number;
	allow_network?: boolean;
	allow_filesystem?: boolean;
	allow_subprocess?: boolean;
	allowed_packages?: string[];
	input_variables?: InputVariableMapping[];
	output_variable?: string;
	working_directory?: string;
	environment_variables?: Record<string, string>;
	capture_stdout?: boolean;
	capture_stderr?: boolean;
}

export interface FileReadConfig {
	// File input (from previous nodes only)
	file_path?: string;
	file_base64?: string;
	file_content?: string;
	file_type?: string;

	// Extraction settings
	extraction_mode?: "model_ocr" | "text_only" | "raw";
	output_format?: "markdown" | "json" | "plain" | "raw";
	llm_safe_output?: boolean;

	// GPT-4o OCR settings
	model_deployment_id?: string; // Model deployment to use for AI OCR
	ocr_prompt?: string;
	doc_type?:
		| "auto"
		| "generic"
		| "resume"
		| "invoice"
		| "form"
		| "table"
		| "handwritten";
	max_tokens_per_request?: number;

	// Document processing
	max_pages?: number; // Maximum pages for PDFs
	chunk_by_page?: boolean; // Return results separated by page
	include_metadata?: boolean;
	preserve_formatting?: boolean;

	// Processing options
	extract_tables?: boolean;
	extract_images?: boolean; // For DOCX embedded images

	// Validation
	allowed_extensions?: string[];
	max_file_size_mb?: number;

	// Error handling
	fallback_on_error?: boolean;
	skip_on_error?: boolean;
	use_cache?: boolean;
}

export interface DocumentRetrieveConfig {
	collection_ids?: string[];
	parent_agent_id?: string;
}

export interface DocumentLoadConfig {
	collection_id?: string;
	document_ids?: string[];
	max_document_size_tokens?: number;
	truncation_strategy?: "end" | "start";
	output_mode?: "single" | "batch";
	chunk_output_mode?: "full" | "by_page" | "by_token_limit";
	chunk_token_limit?: number;
	output_format?: "markdown" | "plain" | "json";
	include_metadata?: boolean;
}
