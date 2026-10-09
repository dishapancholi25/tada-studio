/**
 * Review configuration and types for agent output gating.
 *
 * Supports both human-in-the-loop review and automated LLM review.
 */

/**
 * Review mode - either human or LLM review
 */
export type ReviewMode = "human" | "llm";

/**
 * LLM configuration for reviewer
 * Simplified structure - uses model_deployment_id for selection
 */
export interface ReviewerLLMConfig {
	/** Model deployment ID from model deployments */
	model_deployment_id?: string;
	/** Provider (azure_openai, openai, anthropic) */
	provider?: string;
	/** Model name */
	model_name?: string;
	/** Temperature for generation */
	temperature?: number;
	/** Display name for UI */
	display_name?: string;
}

/**
 * Configuration for agent output review gating.
 */
export interface ReviewConfig {
	/** Enable/disable review for this agent */
	review_enabled: boolean;
	/** Review type - "human" or "llm" */
	review_mode: ReviewMode;
	/** Guidance for human reviewers OR prompt for LLM reviewer */
	review_prompt: string;
	/** Maximum feedback cycles before auto-approve */
	max_iterations: number;
	/** Timeout for human review in seconds (null = no timeout) */
	timeout_seconds: number | null;
	/** If true, auto-approve on timeout; else auto-fail */
	auto_approve_on_timeout: boolean;
	/** If true, auto-approve when max iterations reached */
	auto_approve_on_max_iterations: boolean;
	/** LLM configuration for LLM review mode */
	reviewer_llm_config?: ReviewerLLMConfig | null;
}

/**
 * Default review configuration
 */
export const DEFAULT_REVIEW_CONFIG: ReviewConfig = {
	review_enabled: false,
	review_mode: "human",
	review_prompt:
		"Please review the agent's output and provide feedback if needed.",
	max_iterations: 3,
	timeout_seconds: null,
	auto_approve_on_timeout: false,
	auto_approve_on_max_iterations: true,
	reviewer_llm_config: null,
};

/**
 * LLM review metadata returned by the reviewer
 */
export interface LLMReviewMetadata {
	/** Whether the output passes review */
	proceed: boolean;
	/** Feedback to pass back to agent if not proceeding */
	feedback: string;
	/** 0.0-1.0 confidence in the review decision */
	confidence_score: number;
	/** List of identified issue categories */
	issue_categories: string[];
	/** LLM's reasoning for the decision */
	reasoning: string;
}

/**
 * A single entry in the review history
 */
export interface ReviewFeedbackEntry {
	/** The iteration number (1-indexed) */
	iteration: number;
	/** The agent's response for this iteration */
	agent_output: string;
	/** The feedback provided (human or LLM) */
	feedback: string;
	/** Either "human" or "llm" */
	reviewer_type: ReviewMode;
	/** ISO timestamp of when feedback was given */
	timestamp: string;
	/** For LLM review - additional metadata */
	llm_metadata?: LLMReviewMetadata;
}

/**
 * Payload sent via interrupt for human review
 */
export interface ReviewInterruptPayload {
	/** Always "agent_review" */
	type: "agent_review";
	/** Node ID of the agent being reviewed */
	node_id: string;
	/** Display name of the agent */
	node_name: string;
	/** The agent's output to review */
	agent_output: string;
	/** Review prompt/criteria */
	review_prompt: string;
	/** Review mode */
	review_mode: ReviewMode;
	/** Current iteration number */
	current_iteration: number;
	/** Maximum allowed iterations */
	max_iterations: number;
	/** History of previous review iterations */
	review_history: ReviewFeedbackEntry[];
	/** Timeout in seconds (if configured) */
	timeout_seconds?: number | null;
}

/**
 * Response format for resuming from human review
 */
export interface ReviewResumeResponse {
	/** Whether the output is approved */
	approved: boolean;
	/** Feedback if not approved */
	feedback?: string;
}
