"use client";

import ConditionEdge from "../../edges/ConditionEdge";
import LoopbackEdge from "../../edges/LoopbackEdge";
import AgentNode from "../../nodes/AgentNode";
import CodeExecutorNode from "../../nodes/CodeExecutorNode";
import ConditionNode from "../../nodes/ConditionNode";
import DatabaseInsertNode from "../../nodes/DatabaseInsertNode";
import DatabaseQueryActionNode from "../../nodes/DatabaseQueryActionNode";
import DocumentLoadNode from "../../nodes/DocumentLoadNode";
import EmailSendNode from "../../nodes/EmailSendNode";
// TEMPORARILY DISABLED: File Read feature disabled due to ISG security audit
// import FileReadNode from "../../nodes/FileReadNode";
import FlowNode from "../../nodes/FlowNode";
import ForEachNode from "../../nodes/ForEachNode";
import HttpRequestActionNode from "../../nodes/HttpRequestActionNode";
import McpServerNode from "../../nodes/McpServerNode";
import SubWorkflowNode from "../../nodes/SubWorkflowNode";
import DatabaseQueryNode from "../../nodes/tools/DatabaseQueryNode";
import DocumentRetrieveNode from "../../nodes/tools/DocumentRetrieveNode";
import DocumentSearchNode from "../../nodes/tools/DocumentSearchNode";
import EmailSendToolNode from "../../nodes/tools/EmailSendToolNode";
import FileWriteNode from "../../nodes/tools/FileWriteNode";
import HttpRequestNode from "../../nodes/tools/HttpRequestNode";
import WebSearchNode from "../../nodes/tools/WebSearchNode";

const sharedToolNodeTypes = {
	documentSearchNode: DocumentSearchNode,
	documentRetrieveNode: DocumentRetrieveNode,
	databaseQueryNode: DatabaseQueryNode,
	databaseInsertNode: DatabaseInsertNode,
	databaseQueryActionNode: DatabaseQueryActionNode,
	emailSendToolNode: EmailSendToolNode,
	httpRequestNode: HttpRequestNode,
	httpRequestActionNode: HttpRequestActionNode,
	webSearchNode: WebSearchNode,
	mcpServerNode: McpServerNode,
	emailSendNode: EmailSendNode,
	// fileReadNode: FileReadNode, // TEMPORARILY DISABLED: ISG security audit
	fileWriteNode: FileWriteNode,
};

export const builderNodeTypes = {
	agentNode: AgentNode,
	codeExecutorNode: CodeExecutorNode,
	flowNode: FlowNode,
	conditionNode: ConditionNode,
	subWorkflowNode: SubWorkflowNode,
	forEachNode: ForEachNode,
	documentLoadNode: DocumentLoadNode,
	...sharedToolNodeTypes,
};

export const builderEdgeTypes = {
	condition: ConditionEdge,
	loopback: LoopbackEdge,
};

export const executionNodeTypes = {
	agentNode: AgentNode,
	codeExecutorNode: CodeExecutorNode,
	conditionNode: ConditionNode,
	flowNode: FlowNode,
	forEachNode: ForEachNode,
	documentLoadNode: DocumentLoadNode,
	SubWorkflowNode: SubWorkflowNode,
	...sharedToolNodeTypes,
};
