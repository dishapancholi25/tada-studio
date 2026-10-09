"use client";

import { lazy, type ReactNode, Suspense } from "react";
import type { Edge, Node } from "reactflow";
import type { GraphOperations } from "./graphOperations";
import type {
	PanelData,
	SelectionPanelKey,
	UseSelectionPanelsResult,
} from "./useSelectionPanels";

// Lazy load all property panels for better performance
const NodePropertiesPanel = lazy(
	() => import("../../panels/properties/NodePropertiesPanelV2"),
);
const StartNodePropertiesPanel = lazy(
	() => import("../../panels/properties/StartNodePropertiesPanel"),
);
const ConditionPropertiesPanel = lazy(
	() => import("../../panels/properties/ConditionPropertiesPanelV2"),
);
const SubWorkflowPropertiesPanel = lazy(
	() => import("../../panels/properties/SubWorkflowPropertiesPanel"),
);
const ForEachPropertiesPanel = lazy(
	() => import("../../panels/properties/ForEachPropertiesPanel"),
);
const CodeExecutorPropertiesPanel = lazy(
	() => import("../../panels/properties/CodeExecutorPropertiesPanel"),
);
const DocumentSearchPropertiesPanel = lazy(
	() => import("../../panels/properties/DocumentSearchPropertiesPanel"),
);
const DocumentRetrievePropertiesPanel = lazy(
	() => import("../../panels/properties/DocumentRetrievePropertiesPanel"),
);
const DocumentLoadPropertiesPanel = lazy(
	() => import("../../panels/properties/DocumentLoadPropertiesPanel"),
);
const DatabaseQueryPropertiesPanel = lazy(
	() => import("../../panels/properties/DatabaseQueryPropertiesPanel"),
);
const DatabaseInsertPropertiesPanel = lazy(
	() => import("../../panels/properties/DatabaseInsertPropertiesPanel"),
);
const DatabaseQueryActionPropertiesPanel = lazy(
	() => import("../../panels/properties/DatabaseQueryActionPropertiesPanel"),
);
const HttpRequestPropertiesPanel = lazy(
	() => import("../../panels/properties/HttpRequestPropertiesPanel"),
);
const HttpRequestActionPropertiesPanel = lazy(
	() => import("../../panels/properties/HttpRequestActionPropertiesPanel"),
);
const EmailSendPropertiesPanel = lazy(
	() => import("../../panels/properties/EmailSendPropertiesPanel"),
);
const EmailSendToolPropertiesPanel = lazy(
	() => import("../../panels/properties/EmailSendToolPropertiesPanel"),
);
const FileReadPropertiesPanel = lazy(
	() => import("../../panels/properties/FileReadPropertiesPanel"),
);
const FileWritePropertiesPanel = lazy(
	() => import("../../panels/properties/FileWritePropertiesPanel"),
);
const WebSearchPropertiesPanel = lazy(
	() => import("../../panels/properties/WebSearchPropertiesPanel"),
);
const McpServerPropertiesPanel = lazy(
	() => import("../../panels/properties/McpServerPropertiesPanel"),
);
const EndNodePropertiesPanel = lazy(
	() => import("../../panels/properties/EndNodePropertiesPanel"),
);
const CheckpointPropertiesPanel = lazy(
	() => import("../../panels/properties/CheckpointPropertiesPanel"),
);

// Lazy load execution panels
const NodeExecutionPanel = lazy(
	() => import("../../panels/execution/NodeExecutionPanel"),
);
const UnifiedToolExecutionPanel = lazy(
	() => import("../../panels/execution/unified/UnifiedToolExecutionPanel"),
);
const DatabaseInsertExecutionPanel = lazy(
	() => import("../../panels/execution/DatabaseInsertExecutionPanel"),
);
const FileViewerPanel = lazy(
	() => import("../../panels/execution/file-viewer/FileViewerPanel"),
);

interface UsePropertyPanelsOptions {
	graphOperations: GraphOperations;
	selectionPanels: UseSelectionPanelsResult;
	nodes: Node[];
	edges: Edge[];
	mode?: "edit" | "evaluate" | "execution";
	currentExecution?: any;
}

interface PropertyPanelRenderOptions {
	showPropertiesPanels: boolean;
	showExecutionPanels: boolean;
	executionNodeData?: {
		nodeId: string;
		nodeName: string;
		nodeType: string;
	};
}

// Type guard to check if PanelData is a Node
const isNode = (data: PanelData | null): data is Node => {
	return data !== null && "position" in data && "data" in data;
};

export function usePropertyPanels({
	graphOperations,
	selectionPanels,
	nodes,
	edges,
	mode = "edit",
	currentExecution,
}: UsePropertyPanelsOptions) {
	const { selectionMap, closePanel } = selectionPanels;

	// Resolve the selected agent node from the live nodes array so the panel
	// always reflects the current store state (e.g. is_sub_agent set by a
	// drag-connect that happened after the panel was opened or the event fired).
	const selectedNode = (() => {
		if (!selectionMap.node || !isNode(selectionMap.node)) return null;
		const storedId = (selectionMap.node as Node).id;
		return nodes.find((n) => n.id === storedId) ?? (selectionMap.node as Node);
	})();
	const selectedConditionNode =
		selectionMap.condition && isNode(selectionMap.condition)
			? selectionMap.condition
			: null;
	const selectedSubWorkflowNode =
		selectionMap.subWorkflow && isNode(selectionMap.subWorkflow)
			? selectionMap.subWorkflow
			: null;
	const selectedForEachNode =
		selectionMap.forEach && isNode(selectionMap.forEach)
			? selectionMap.forEach
			: null;
	const selectedCodeExecutorNode =
		selectionMap.codeExecutor && isNode(selectionMap.codeExecutor)
			? selectionMap.codeExecutor
			: null;
	const selectedDocumentSearchNode =
		selectionMap.documentSearch && isNode(selectionMap.documentSearch)
			? selectionMap.documentSearch
			: null;
	const selectedDocumentRetrieveNode =
		selectionMap.documentRetrieve && isNode(selectionMap.documentRetrieve)
			? selectionMap.documentRetrieve
			: null;
	const selectedDocumentLoadNode =
		selectionMap.documentLoad && isNode(selectionMap.documentLoad)
			? selectionMap.documentLoad
			: null;
	const selectedDatabaseQueryNode =
		selectionMap.databaseQuery && isNode(selectionMap.databaseQuery)
			? selectionMap.databaseQuery
			: null;
	const selectedDatabaseInsertNode =
		selectionMap.databaseInsert && isNode(selectionMap.databaseInsert)
			? selectionMap.databaseInsert
			: null;
	const selectedDatabaseQueryActionNode =
		selectionMap.databaseQueryAction && isNode(selectionMap.databaseQueryAction)
			? selectionMap.databaseQueryAction
			: null;
	const selectedHttpRequestNode =
		selectionMap.httpRequest && isNode(selectionMap.httpRequest)
			? selectionMap.httpRequest
			: null;
	const selectedHttpRequestActionNode =
		selectionMap.httpRequestAction && isNode(selectionMap.httpRequestAction)
			? selectionMap.httpRequestAction
			: null;
	const selectedEmailSendNode =
		selectionMap.emailSend && isNode(selectionMap.emailSend)
			? selectionMap.emailSend
			: null;
	const selectedEmailSendToolNode =
		selectionMap.emailSendTool && isNode(selectionMap.emailSendTool)
			? selectionMap.emailSendTool
			: null;
	const selectedFileReadNode =
		selectionMap.fileRead && isNode(selectionMap.fileRead)
			? selectionMap.fileRead
			: null;
	const selectedFileWriteNode =
		selectionMap.fileWrite && isNode(selectionMap.fileWrite)
			? selectionMap.fileWrite
			: null;
	const selectedWebSearchNode =
		selectionMap.webSearch && isNode(selectionMap.webSearch)
			? selectionMap.webSearch
			: null;
	const selectedMcpServerNode =
		selectionMap.mcpServer && isNode(selectionMap.mcpServer)
			? selectionMap.mcpServer
			: null;
	const selectedCheckpointNode =
		selectionMap.checkpoint && isNode(selectionMap.checkpoint)
			? selectionMap.checkpoint
			: null;
	const selectedEndNode =
		selectionMap.end && isNode(selectionMap.end) ? selectionMap.end : null;

	// Get execution panel data
	const selectedExecutionData = (
		selectionMap.execution && typeof selectionMap.execution === "object"
			? selectionMap.execution
			: null
	) as {
		id: string;
		nodeName: string;
		nodeType: string;
	} | null;

	// Common update functions that work with both mutable and read-only operations
	const updateNodeData = async (nodeId: string, updates: any) => {
		if (graphOperations.isReadOnly) {
			console.warn("Cannot update node in read-only mode");
			return;
		}
		try {
			await graphOperations.updateNode(nodeId, updates);
		} catch (error) {
			console.error("Failed to update node:", error);
		}
	};

	const deleteNode = async (nodeId: string) => {
		if (graphOperations.isReadOnly) {
			console.warn("Cannot delete node in read-only mode");
			return;
		}
		try {
			await graphOperations.deleteNode(nodeId);
			// Close any open panels for the deleted node
			Object.keys(selectionMap).forEach((key) => {
				const data = selectionMap[key as SelectionPanelKey];
				if (
					data &&
					typeof data === "object" &&
					"id" in data &&
					data.id === nodeId
				) {
					closePanel(key as SelectionPanelKey);
				}
			});
		} catch (error) {
			console.error("Failed to delete node:", error);
		}
	};

	// Create loading fallback that matches modal-style panels
	const createPanelFallback = (
		variant: "properties" | "execution" = "properties",
	) => {
		const maxWidth = variant === "execution" ? "max-w-5xl" : "max-w-4xl";
		const label =
			variant === "execution" ? "Loading execution..." : "Loading panel...";

		return (
			<div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fadeIn">
				<div
					className={`w-full ${maxWidth} mx-4 rounded-2xl border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)]/95 shadow-2xl animate-scaleIn`}
				>
					<div className="flex flex-col items-center justify-center gap-4 py-12">
						<div className="h-12 w-12 rounded-full border-2 border-[color:var(--color-border)]/50 border-t-[color:var(--color-accent)] animate-spin" />
						<p className="text-sm text-[color:var(--color-text-muted)]">
							{label}
						</p>
					</div>
				</div>
			</div>
		);
	};

	// Render property panels (edit mode)
	const renderPropertyPanels = (): ReactNode[] => {
		const panels: ReactNode[] = [];

		if (mode !== "edit") return panels;

		if (selectedNode && !graphOperations.isReadOnly) {
			const isStartNode =
				selectedNode.data?.node_type === "START" ||
				selectedNode.data?.type === "START";

			panels.push(
				<div key="node-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						{isStartNode ? (
							<StartNodePropertiesPanel
								node={selectedNode}
								onUpdate={updateNodeData}
								onClose={() => closePanel("node")}
							/>
						) : (
							<NodePropertiesPanel
								node={selectedNode}
								onUpdateNode={updateNodeData}
								onDeleteNode={deleteNode}
								onClose={() => closePanel("node")}
								nodes={nodes}
								edges={edges}
							/>
						)}
					</Suspense>
				</div>,
			);
		}

		if (selectedDocumentSearchNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="document-search-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<DocumentSearchPropertiesPanel
							node={selectedDocumentSearchNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("documentSearch")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedDocumentRetrieveNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="document-retrieve-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<DocumentRetrievePropertiesPanel
							node={selectedDocumentRetrieveNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("documentRetrieve")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedDocumentLoadNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="document-load-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<DocumentLoadPropertiesPanel
							node={selectedDocumentLoadNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("documentLoad")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedDatabaseQueryNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="database-query-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<DatabaseQueryPropertiesPanel
							node={selectedDatabaseQueryNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("databaseQuery")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedDatabaseInsertNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="database-insert-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<DatabaseInsertPropertiesPanel
							node={selectedDatabaseInsertNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("databaseInsert")}
							availableNodes={nodes}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedDatabaseQueryActionNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="database-query-action-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
							<DatabaseQueryActionPropertiesPanel
								node={selectedDatabaseQueryActionNode}
								onUpdateNode={updateNodeData}
								onDeleteNode={deleteNode}
								onClose={() => closePanel("databaseQueryAction")}
							/>
					</Suspense>
				</div>,
			);
		}

		if (selectedConditionNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="condition-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<ConditionPropertiesPanel
							nodeId={selectedConditionNode.id}
							onClose={() => closePanel("condition")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedSubWorkflowNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="subworkflow-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<SubWorkflowPropertiesPanel
							node={selectedSubWorkflowNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("subWorkflow")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedForEachNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="foreach-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<ForEachPropertiesPanel
							node={selectedForEachNode}
							nodes={nodes}
							edges={edges}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("forEach")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedCodeExecutorNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="code-executor-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<CodeExecutorPropertiesPanel
							node={selectedCodeExecutorNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("codeExecutor")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedEndNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="end-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<EndNodePropertiesPanel
							nodeId={selectedEndNode.id}
							onClose={() => closePanel("end")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedCheckpointNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="checkpoint-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<CheckpointPropertiesPanel
							nodeId={selectedCheckpointNode.id}
							onClose={() => closePanel("checkpoint")}
							availableNodes={nodes}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedHttpRequestActionNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="http-request-action-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<HttpRequestActionPropertiesPanel
							nodeId={selectedHttpRequestActionNode.id}
							onClose={() => closePanel("httpRequestAction")}
							availableNodes={nodes}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedEmailSendNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="email-send-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<EmailSendPropertiesPanel
							node={selectedEmailSendNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("emailSend")}
							availableNodes={nodes}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedEmailSendToolNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="email-send-tool-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<EmailSendToolPropertiesPanel
							node={selectedEmailSendToolNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("emailSendTool")}
							availableNodes={nodes}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedFileReadNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="file-read-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<FileReadPropertiesPanel
							node={selectedFileReadNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("fileRead")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedFileWriteNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="file-write-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<FileWritePropertiesPanel
							node={selectedFileWriteNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("fileWrite")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedHttpRequestNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="http-request-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<HttpRequestPropertiesPanel
							node={selectedHttpRequestNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("httpRequest")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedWebSearchNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="web-search-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<WebSearchPropertiesPanel
							node={selectedWebSearchNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("webSearch")}
						/>
					</Suspense>
				</div>,
			);
		}

		if (selectedMcpServerNode && !graphOperations.isReadOnly) {
			panels.push(
				<div key="mcp-server-properties" className="animate-fadeIn">
					<Suspense fallback={createPanelFallback()}>
						<McpServerPropertiesPanel
							node={selectedMcpServerNode}
							onUpdateNode={updateNodeData}
							onDeleteNode={deleteNode}
							onClose={() => closePanel("mcpServer")}
						/>
					</Suspense>
				</div>,
			);
		}

		return panels;
	};

	// Render execution panels
	const renderExecutionPanels = (): ReactNode[] => {
		const panels: ReactNode[] = [];

		if (mode !== "execution" || !selectedExecutionData) return panels;

		const { id: nodeId, nodeName, nodeType } = selectedExecutionData;
		const executionId =
			(currentExecution as any)?.db_execution_id || currentExecution?.id || "";
		const isExecuting = currentExecution?.status === "running";

		// Helper: extract streaming node executions for a given nodeId.
		// Returns a combined node with all_tool_nodes when multiple entries exist,
		// so parseToolExecutions can iterate all tool calls (not just the latest).
		const getStreamingNodeExecution = (targetNodeId: string) => {
			const allExecutions =
				currentExecution?.node_executions?.filter(
					(ne: any) => ne.node_id === targetNodeId,
				) || [];
			if (allExecutions.length === 0) return undefined;
			if (allExecutions.length === 1) return allExecutions[0];
			// Multiple entries: combine into CombinedNodeExecution with all_tool_nodes
			return {
				...allExecutions[0],
				all_tool_nodes: allExecutions,
			};
		};

		panels.push(
			<Suspense
				key="execution-panel"
				fallback={createPanelFallback("execution")}
			>
				{(() => {
					if (nodeType === "document_search") {
						return (
							<UnifiedToolExecutionPanel
								toolType="document_search"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={getStreamingNodeExecution(nodeId)}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "document_retrieve") {
						return (
							<UnifiedToolExecutionPanel
								toolType="document_retrieve"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={getStreamingNodeExecution(nodeId)}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "database_query") {
						return (
							<UnifiedToolExecutionPanel
								toolType="database_query"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={getStreamingNodeExecution(nodeId)}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "database_insert") {
						const nodeExecution = (() => {
							const allExecutions =
								currentExecution?.node_executions?.filter(
									(ne: any) => ne.node_id === nodeId,
								) || [];
							return allExecutions.length > 0
								? allExecutions.reduce((latest: any, current: any) => {
										const latestOrder = latest.execution_order ?? 0;
										const currentOrder = current.execution_order ?? 0;
										return currentOrder > latestOrder ? current : latest;
									})
								: undefined;
						})();

						return (
							<DatabaseInsertExecutionPanel
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={nodeExecution}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "http_request") {
						return (
							<UnifiedToolExecutionPanel
								toolType="http_request"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={getStreamingNodeExecution(nodeId)}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "web_search") {
						return (
							<UnifiedToolExecutionPanel
								toolType="web_search"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={getStreamingNodeExecution(nodeId)}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "mcp_server") {
						// Find parent agent from graph connections for correct tool execution filtering
						const graphDef = (currentExecution as any)
							?.graph_definition;
						const mcpConnections =
							graphDef?.connections || graphDef?.edges || [];
						const parentEdge = mcpConnections.find(
							(conn: any) =>
								(conn.target_id || conn.target) === nodeId,
						);
						const parentAgentNodeId = parentEdge
							? parentEdge.source_id || parentEdge.source
							: undefined;

						return (
							<UnifiedToolExecutionPanel
								toolType="mcp_server"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								parentAgentNodeId={parentAgentNodeId}
								nodeExecution={getStreamingNodeExecution(nodeId)}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "email_send" || nodeType === "email_send_tool") {
						const emailStreamingExec = getStreamingNodeExecution(nodeId);
						console.log("[DEBUG EMAIL_SEND] Panel opening:", {
							nodeId,
							nodeType,
							executionId,
							isExecuting,
							streamingExecResult: emailStreamingExec ? {
								node_id: emailStreamingExec.node_id,
								node_type: emailStreamingExec.node_type,
								status: emailStreamingExec.status,
								hasOutputData: !!emailStreamingExec.output_data,
							} : null,
							allNodeExecutions: currentExecution?.node_executions?.map((ne: any) => ({
								node_id: ne.node_id,
								node_type: ne.node_type,
								node_name: ne.node_name,
							})),
						});
						return (
							<UnifiedToolExecutionPanel
								toolType="email_send"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={emailStreamingExec}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					if (nodeType === "file_write") {
						// Extract file write execution from node execution data
						const nodeExecution = (() => {
							const allExecutions =
								currentExecution?.node_executions?.filter(
									(ne: any) => ne.node_id === nodeId,
								) || [];
							return allExecutions.length > 0
								? allExecutions.reduce((latest: any, current: any) => {
										const latestOrder = latest.execution_order ?? 0;
										const currentOrder = current.execution_order ?? 0;
										return currentOrder > latestOrder ? current : latest;
									})
								: undefined;
						})();

						// Extract file write execution from node data
						// Data structure: input_data has filename/content_type, output_data.result has filepath/file_size
						const fileExecution = (() => {
							if (!nodeExecution) {
								console.log(
									"[FileViewerPanel Routing] No nodeExecution found for file_write node",
									{ nodeId },
								);
								return null;
							}

							console.log(
								"[FileViewerPanel Routing] Extracting file execution data",
								{
									nodeId,
									hasInputData: !!nodeExecution.input_data,
									hasOutputData: !!nodeExecution.output_data,
									inputDataType: typeof nodeExecution.input_data,
									outputDataType: typeof nodeExecution.output_data,
								},
							);

							// Parse input_data if it's a JSON string
							let inputData = nodeExecution.input_data as any;
							if (typeof inputData === "string") {
								try {
									inputData = JSON.parse(inputData);
								} catch {
									// Keep as-is if not valid JSON
								}
							}

							// Parse output_data if it's a JSON string
							let outputData = nodeExecution.output_data as any;
							console.log("[FileViewerPanel DEBUG] RAW output_data:", nodeExecution.output_data);
							if (typeof outputData === "string") {
								try {
									outputData = JSON.parse(outputData);
								} catch {
									// Keep as-is if not valid JSON
								}
							}
							console.log("[FileViewerPanel DEBUG] PARSED outputData:", outputData);
							console.log("[FileViewerPanel DEBUG] outputData keys:", outputData ? Object.keys(outputData) : "null");

							// Output may be nested in 'result' or 'raw' field
							let resultData = outputData?.result || outputData?.raw || outputData;
							if (typeof resultData === "string") {
								try {
									resultData = JSON.parse(resultData);
								} catch {
									// Keep as-is if not valid JSON
								}
							}

							// DEBUG: Log the data structure
							console.log("[FileViewerPanel DEBUG] outputData:", outputData);
							console.log("[FileViewerPanel DEBUG] resultData (initial):", resultData);
							console.log("[FileViewerPanel DEBUG] has tool_executions?:", !!outputData?.tool_executions);
							if (outputData?.tool_executions) {
								console.log("[FileViewerPanel DEBUG] tool_executions:", outputData.tool_executions);
							}

							// Also check tool_executions for file_write results (when used as agent tool)
							if (!resultData?.file_id && outputData?.tool_executions) {
								const fileWriteExec = (
									outputData.tool_executions as any[]
								).find(
									(exec: any) =>
										exec.tool?.includes("file_write") ||
										exec.tool?.includes("write_file"),
								);
								if (fileWriteExec?.results) {
									try {
										const parsedResult =
											typeof fileWriteExec.results === "string"
												? JSON.parse(fileWriteExec.results)
												: fileWriteExec.results;
										resultData = { ...resultData, ...parsedResult };
									} catch {
										// Keep resultData as-is if parse fails
									}
								}
							}

							// DEBUG: Log after tool_executions processing
							console.log("[FileViewerPanel DEBUG] resultData (after tool_executions check):", resultData);
							console.log("[FileViewerPanel DEBUG] resultData.file_id:", resultData?.file_id);

							// Extract file execution fields
							const filename =
								inputData?.filename || resultData?.filename || "";
							if (!filename) {
								console.log(
									"[FileViewerPanel Routing] No filename found, falling back to UnifiedPanel",
									{ inputData, resultData },
								);
								return null;
							}

							const fileId = resultData?.file_id;
							console.log("[FileViewerPanel DEBUG] Extracted values - filename:", filename, "fileId:", fileId);
							const fileUrl = resultData?.file_url;
							const contentType =
								inputData?.content_type || resultData?.content_type || "text";
							const fileSize = resultData?.file_size || resultData?.size;
							const subdirectory =
								inputData?.subdirectory || resultData?.subdirectory;
							const status: "failed" | "success" =
								resultData?.error || resultData?.success === false
									? "failed"
									: "success";
							const error = resultData?.error;
							const content = resultData?.content;

							// Build FileWriteExecution object
							return {
								tool: "file_write",
								filename,
								file_id: fileId,
								file_url: fileUrl,
								content_type: contentType,
								file_size: fileSize,
								subdirectory,
								status,
								error,
								content,
								timestamp: nodeExecution.created_at || new Date().toISOString(),
								call_id: nodeExecution.id || "direct_execution",
								duration: nodeExecution.duration_seconds || undefined,
							};
						})();

						// If we have file execution data, use the new FileViewerPanel
						if (fileExecution) {
							console.log(
								"[FileViewerPanel Routing] SUCCESS - Rendering FileViewerPanel",
								{
									nodeId,
									filename: fileExecution.filename,
									file_id: fileExecution.file_id,
									status: fileExecution.status,
								},
							);
							return (
								<FileViewerPanel
									nodeId={nodeId}
									nodeName={nodeName}
									executionId={executionId}
									fileExecution={fileExecution}
									onClose={() => closePanel("execution")}
								/>
							);
						}

						// Fallback to unified panel if no file execution data
						console.log(
							"[FileViewerPanel Routing] FALLBACK - Rendering UnifiedToolExecutionPanel",
							{ nodeId, nodeName },
						);
						return (
							<UnifiedToolExecutionPanel
								toolType="file_write"
								nodeId={nodeId}
								nodeName={nodeName}
								executionId={executionId}
								nodeExecution={getStreamingNodeExecution(nodeId)}
								isExecuting={isExecuting}
								onClose={() => closePanel("execution")}
							/>
						);
					}

					// Default node execution panel
					const allNodeExecutions = (() => {
						const allExecutions =
							currentExecution?.node_executions?.filter(
								(ne: any) => ne.node_id === nodeId,
							) || [];
						return allExecutions.sort((a: any, b: any) => {
							const orderA = a.execution_order ?? 0;
							const orderB = b.execution_order ?? 0;
							return orderA - orderB;
						});
					})();

					return (
						<NodeExecutionPanel
							nodeId={nodeId}
							nodeName={nodeName}
							executionId={executionId}
							allNodeExecutions={allNodeExecutions}
							onClose={() => closePanel("execution")}
						/>
					);
				})()}
			</Suspense>,
		);

		return panels;
	};

	return {
		renderPropertyPanels,
		renderExecutionPanels,
		isExecutionDetailOpen: mode === "execution" && !!selectedExecutionData,
		updateNodeData,
		deleteNode,
	};
}
