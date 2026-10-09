import type { ExecutionStatusType } from "@/types/api";

export interface AgentNodeData {
	id: string;
	name: string;
	description?: string;
	prompt: string;
	model?: string;
	type: "agent" | "condition" | "tool";
	position: { x: number; y: number };
	isExecuting?: boolean;
	executionStatus?: ExecutionStatusType;
	executionDuration?: number;
	isSubAgent?: boolean;
	parentAgentId?: string;
	delegationDescription?: string;
	delegation_description?: string;
	isOrchestrator?: boolean;
	nexts?: string[];
	agent_config?: any;
	node_type?: string;
	is_sub_agent?: boolean;
	input_source_config?: any;
}
