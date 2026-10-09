import { AlertCircle } from "lucide-react";
import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { ConversationMessage, NodeExecution } from "@/types/api";
import JsonViewerEnhanced from "../../JsonViewerEnhanced";
import ConversationHistoryTab from "./components/ConversationHistoryTab";
import ExecutionIOView from "./components/ExecutionIOView";
import ExecutionModalHeader from "./components/ExecutionModalHeader";
import ExecutionSelector from "./components/ExecutionSelector";
import ExecutionTabNavigation from "./components/ExecutionTabNavigation";

interface NodeExecutionPanelProps {
	nodeId: string;
	nodeName: string;
	executionId: string;
	nodeExecution?: NodeExecution;
	allNodeExecutions?: NodeExecution[]; // All executions for this node (for re-executions)
	onClose: () => void;
	isDatabaseQuery?: boolean;
}

function NodeExecutionPanel({
	nodeId,
	nodeName,
	executionId,
	nodeExecution,
	allNodeExecutions,
	onClose,
	isDatabaseQuery = false,
}: NodeExecutionPanelProps) {
	const [selectedExecutionIndex, setSelectedExecutionIndex] =
		useState<number>(0);
	const [nodeExecutionData, setNodeExecutionData] =
		useState<NodeExecution | null>(nodeExecution || null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [activeTab, setActiveTab] = useState<"io" | "history">("io");

	// Use all executions if provided, otherwise fall back to single execution
	const executions =
		allNodeExecutions && allNodeExecutions.length > 0
			? allNodeExecutions
			: nodeExecution
				? [nodeExecution]
				: [];

	// Set initial selection to the latest execution
	useEffect(() => {
		if (executions.length > 0 && selectedExecutionIndex === 0) {
			setSelectedExecutionIndex(executions.length - 1); // Default to latest
			setNodeExecutionData((prev) => {
				const next = executions[executions.length - 1];
				if (!next) return prev;
				// Preserve fields that streaming (WebSocket) updates don't populate,
				// such as CONDITION node input_data. Otherwise a later WS-driven
				// executions update would overwrite the richer API-fetched entry
				// and blank out the Input panel.
				return {
					...next,
					input_data: next.input_data !== undefined ? next.input_data : prev?.input_data || null,
					output_data: next.output_data !== undefined ? next.output_data : prev?.output_data || null,
				} as NodeExecution;
			});
		}
	}, [executions]);

	// Fetch execution data if not provided
	useEffect(() => {
		if (!nodeExecution && executionId && nodeId) {
			setLoading(true);
			setError(null);

			api
				.getNodeExecution(executionId, nodeId)
				.then((data) => {
					setNodeExecutionData(data);
				})
				.catch((err) => {
					console.error(
						"[NodeExecutionPanel] Failed to fetch node execution data:",
						err,
					);
					setError(err.message || "Failed to load node execution data");
				})
				.finally(() => {
					setLoading(false);
				});
		} else {
			// console.log('[NodeExecutionPanel] Using provided node execution data or missing required parameters');
		}
	}, [executionId, nodeId, nodeExecution]);

	const handleExecutionSelection = (index: number) => {
		setSelectedExecutionIndex(index);
		setNodeExecutionData(executions[index]);
	};

	return (
		<>
		{/* Backdrop - below execution panel (z-40 < z-50) */}
		<div className="fixed inset-0 z-40 bg-black/40 animate-fadeIn" onClick={onClose} />

		{/* Dialog - above execution panel (z-[60] > z-50) */}
		<div className="fixed inset-0 z-[60] flex items-center justify-center pointer-events-none px-4 py-8 animate-fadeIn">
			<div className="w-full max-w-[90vw] pointer-events-auto">
				<div className="overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]">
						<ExecutionModalHeader
							nodeExecution={nodeExecutionData}
							nodeName={nodeName}
							nodeId={nodeId}
							executionId={executionId}
							onClose={onClose}
						/>

						{/* Content */}
						<div className="custom-scrollbar max-h-[calc(92vh-64px)] overflow-y-auto bg-slate-50 px-6 pb-6 pt-4">
							{loading ? (
								<div className="flex flex-col items-center gap-4 rounded-2xl border border-gray-200 bg-white px-6 py-12 text-center shadow-sm">
									<div className="h-12 w-12 animate-spin rounded-full border-2 border-gray-200 border-t-orange-600" />
									<div>
										<p className="text-sm font-medium text-gray-900">
											Fetching execution details
										</p>
										<p className="text-xs text-gray-500">
											Loading node execution data...
										</p>
									</div>
								</div>
							) : error ? (
								<div className="flex flex-col items-center gap-3 rounded-2xl border border-red-200 bg-white px-6 py-10 text-center shadow-sm">
									<AlertCircle className="h-10 w-10 text-red-600" />
									<p className="text-sm font-semibold text-gray-900">
										Unable to load node execution data
									</p>
									<p className="text-xs text-red-700">{error}</p>
								</div>
							) : nodeExecutionData ? (
								<div className="space-y-5">
									<ExecutionSelector
										executions={executions}
										selectedIndex={selectedExecutionIndex}
										onSelectExecution={handleExecutionSelection}
										currentExecution={nodeExecutionData}
									/>

									<ExecutionTabNavigation
										activeTab={activeTab}
										onTabChange={setActiveTab}
										conversationHistory={
											nodeExecutionData.output_data
												?.conversation_history as ConversationMessage[]
										}
									/>

									{/* Tab content */}
									{activeTab === "io" ? (
										<ExecutionIOView
											nodeExecution={nodeExecutionData}
											isDatabaseQuery={isDatabaseQuery}
										/>
									) : activeTab === "history" &&
										nodeExecutionData.output_data?.conversation_history ? (
										<ConversationHistoryTab
											messages={
												nodeExecutionData.output_data
													.conversation_history as ConversationMessage[]
											}
										/>
									) : null}

									{/* Metadata (only show in io tab) */}
									{activeTab === "io" &&
										nodeExecutionData.node_metadata &&
										Object.keys(nodeExecutionData.node_metadata).length > 0 && (
											<div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
												<div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
													<div>
														<p className="text-[0.65rem] capitalize text-gray-500">
															Additional Metadata
														</p>
														<p className="text-sm text-gray-700">
															Raw node telemetry
														</p>
													</div>
												</div>
												<div className="p-4">
													<JsonViewerEnhanced
														data={nodeExecutionData.node_metadata}
													/>
												</div>
											</div>
										)}
								</div>
							) : (
								<div className="rounded-2xl border border-gray-200 bg-white px-6 py-10 text-center text-sm text-gray-600 shadow-sm">
									This node has not been executed yet.
								</div>
							)}
						</div>
					</div>
				</div>
			</div>
		</>
	);
}

export default NodeExecutionPanel;
