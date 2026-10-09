"use client";

import {
	AlertCircle,
	CheckCircle,
	ChevronRight,
	Clock,
	Code,
	Database,
	FileText,
	Table,
	X,
} from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { NodeExecution } from "@/types/api";
import JsonViewerEnhanced from "../../JsonViewerEnhanced";
import ExecutionHeader from "../../ui/ExecutionHeader";
import ExecutionModal from "../../ui/ExecutionModal";
import ExecutionTabs from "../../ui/ExecutionTabs";

interface DatabaseInsertExecutionPanelProps {
	nodeId: string;
	nodeName: string;
	executionId: string;
	nodeExecution?: NodeExecution;
	onClose: () => void;
}

interface InsertResult {
	success: boolean;
	rows_inserted: number;
	data?: Record<string, any>[];
	error?: string;
}

function DatabaseInsertExecutionPanel({
	nodeId,
	nodeName,
	executionId,
	nodeExecution,
	onClose,
}: DatabaseInsertExecutionPanelProps) {
	const [nodeExecutionData, setNodeExecutionData] =
		useState<NodeExecution | null>(nodeExecution || null);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [viewMode, setViewMode] = useState<"result" | "raw">("result");

	// Fetch execution data if not provided
	useEffect(() => {
		if (!nodeExecution && executionId) {
			setLoading(true);
			setError(null);

			api
				.getNodeExecution(executionId, nodeId)
				.then((data) => {
					setNodeExecutionData(data);
				})
				.catch((err) => {
					setError(err.message || "Failed to fetch execution data");
				})
				.finally(() => {
					setLoading(false);
				});
		}
	}, [executionId, nodeId, nodeExecution]);

	const formatDuration = (seconds?: number | null) => {
		if (seconds === null || seconds === undefined) return "-";
		if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
		return `${seconds.toFixed(2)}s`;
	};

	const getStatusIcon = (status?: string) => {
		switch (status) {
			case "completed":
				return <CheckCircle className="w-5 h-5 text-[#0DA931]" />;
			case "failed":
				return <AlertCircle className="w-5 h-5 text-red-500" />;
			case "running":
				return (
					<Clock className="w-5 h-5 text-[color:var(--color-accent)] animate-spin" />
				);
			case "skipped":
				return (
					<Database className="w-5 h-5 text-[color:var(--color-text-muted)]" />
				);
			default:
				return (
					<Clock className="w-5 h-5 text-[color:var(--color-text-muted)]" />
				);
		}
	};

	const getInsertResult = (): InsertResult | null => {
		if (!nodeExecutionData?.output_data) return null;

		// Check if output_data contains the insert result
		const output = nodeExecutionData.output_data;
		if (output && typeof output === "object") {
			// Direct result format
			if ("success" in output) {
				return output as InsertResult;
			}
			// Nested in output property
			if (
				output.output &&
				typeof output.output === "object" &&
				"success" in output.output
			) {
				return output.output as InsertResult;
			}
		}

		return null;
	};

	const insertResult = getInsertResult();

	const handleViewModeChange = useCallback((k: string) => {
		setViewMode(k as "result" | "raw");
	}, []);

	return (
		<ExecutionModal onBackdropClick={onClose} maxWidthClass="max-w-6xl">
			<ExecutionHeader
				gradientFrom="from-emerald-600"
				gradientTo="to-[#0DA931]"
				icon={<Database className="w-6 h-6 text-white" />}
				title={`${nodeName || "Database Insert"} - Execution Details`}
				onClose={onClose}
				statusBar={
					<div className="flex items-center gap-4">
						<div className="flex items-center gap-2 text-slate-800 text-sm">
							{getStatusIcon(nodeExecutionData?.status)}
							<span className="capitalize">
								{nodeExecutionData?.status || "pending"}
							</span>
						</div>
						{nodeExecutionData?.duration_seconds && (
							<div className="flex items-center gap-2 text-slate-700 text-sm">
								<Clock className="w-4 h-4" />
								<span>
									{formatDuration(nodeExecutionData.duration_seconds)}
								</span>
							</div>
						)}
					</div>
				}
			/>

			{/* Content */}
			<div className="flex flex-col h-[calc(90vh-120px)] bg-[color:var(--color-bg-secondary)]">
				{loading ? (
					<div className="text-center py-12">
						<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400 mx-auto"></div>
						<p className="text-[color:var(--color-text-muted)] mt-2 text-sm">
							Loading insert execution data...
						</p>
					</div>
				) : error ? (
					<div className="text-center py-12">
						<AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
						<p className="text-red-400 mb-2 text-sm">
							Error loading execution data
						</p>
						<p className="text-[color:var(--color-text-muted)] text-xs">
							{error}
						</p>
					</div>
				) : nodeExecutionData ? (
					<>
						{/* Summary */}
						<div className="bg-[color:var(--color-surface)] rounded-lg p-4 m-4">
							<h3 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-3">
								Execution Summary
							</h3>
							<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
								<div>
									<p className="text-xs text-[color:var(--color-text-muted)]">
										Status
									</p>
									<p className="text-sm text-slate-700 capitalize flex items-center gap-2 mt-1">
										{getStatusIcon(nodeExecutionData.status)}
										{nodeExecutionData.status}
									</p>
								</div>
								<div>
									<p className="text-xs text-[color:var(--color-text-muted)]">
										Duration
									</p>
									<p className="text-sm text-slate-700 mt-1">
										{formatDuration(nodeExecutionData.duration_seconds)}
									</p>
								</div>
								{insertResult && (
									<>
										<div>
											<p className="text-xs text-[color:var(--color-text-muted)]">
												Rows Inserted
											</p>
											<p className="text-lg font-semibold text-emerald-400 mt-1">
												{insertResult.rows_inserted || 0}
											</p>
										</div>
										<div>
											<p className="text-xs text-[color:var(--color-text-muted)]">
												Result
											</p>
											<p className="text-sm mt-1">
												{insertResult.success ? (
													<span className="text-[#0DA931] flex items-center gap-1">
														<CheckCircle className="w-4 h-4" />
														Success
													</span>
												) : (
													<span className="text-red-400 flex items-center gap-1">
														<AlertCircle className="w-4 h-4" />
														Failed
													</span>
												)}
											</p>
										</div>
									</>
								)}
							</div>
						</div>

						{/* Error Message */}
						{(nodeExecutionData.error_message || insertResult?.error) && (
							<div className="mx-4 mb-4 p-4 bg-red-900/20 border border-red-500/20 rounded-lg">
								<div className="flex items-start gap-3">
									<AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
									<div className="flex-1">
										<p className="text-sm font-medium text-red-400 mb-1">
											Execution Error
										</p>
										<p className="text-sm text-red-600/90 font-mono">
											{nodeExecutionData.error_message || insertResult?.error}
										</p>
									</div>
								</div>
							</div>
						)}

						{/* Tabs */}
						<ExecutionTabs
							tabs={[
								{
									key: "result",
									label: "Result",
									icon: <Table className="w-4 h-4" />,
								},
								{
									key: "raw",
									label: "Raw Data",
									icon: <Code className="w-4 h-4" />,
								},
							]}
							active={viewMode}
							onChange={handleViewModeChange}
						/>

						{/* Content */}
						<div className="flex-1 overflow-y-auto p-6">
							{viewMode === "raw" ? (
								<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
									<JsonViewerEnhanced data={nodeExecutionData} />
								</div>
							) : (
								<div className="space-y-4">
									{insertResult ? (
										<>
											{/* Insert Configuration */}
											{nodeExecutionData.input_data && (
												<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
													<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-3 flex items-center gap-2">
														<FileText className="w-4 h-4" />
														Insert Configuration
													</h4>
													<div className="space-y-2 text-sm">
														{nodeExecutionData.node_metadata?.table_name && (
															<div className="flex items-center gap-2">
																<span className="text-[color:var(--color-text-muted)]">
																	Table:
																</span>
																<span className="text-slate-900 font-mono">
																	{nodeExecutionData.node_metadata.table_name}
																</span>
															</div>
														)}
														{nodeExecutionData.node_metadata
															?.connection_name && (
															<div className="flex items-center gap-2">
																<span className="text-[color:var(--color-text-muted)]">
																	Connection:
																</span>
																<span className="text-slate-900">
																	{
																		nodeExecutionData.node_metadata
																			.connection_name
																	}
																</span>
															</div>
														)}
													</div>
												</div>
											)}

											{/* Inserted Data */}
											{insertResult.data && insertResult.data.length > 0 && (
												<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
													<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-3 flex items-center gap-2">
														<Table className="w-4 h-4" />
														Inserted Data
													</h4>
													<div className="overflow-x-auto">
														<table className="min-w-full text-sm">
															<thead className="bg-[color:var(--color-bg-secondary)]">
																<tr className="border-b border-[color:var(--color-border)]">
																	{Object.keys(insertResult.data[0]).map(
																		(key) => (
																			<th
																				key={key}
																				className="px-3 py-2 text-left text-xs font-medium text-[color:var(--color-text-muted)] capitalize tracking-wider"
																			>
																				{key}
																			</th>
																		),
																	)}
																</tr>
															</thead>
															<tbody className="divide-y divide-gray-700">
																{insertResult.data.map((row, idx) => (
																	<tr
																		key={`insert-row-${JSON.stringify(row).substring(0, 50)}-${idx}`}
																		className="hover:bg-[color:var(--color-border)]/50 transition-colors"
																	>
																		{Object.entries(row).map(([key, value]) => (
																			<td
																				key={key}
																				className="px-3 py-2 text-[color:var(--color-text-secondary)]"
																			>
																				<div
																					className="max-w-xs truncate"
																					title={String(value)}
																				>
																					{value !== null &&
																					value !== undefined ? (
																						typeof value === "object" ? (
																							<span className="font-mono text-xs">
																								{JSON.stringify(value)}
																							</span>
																						) : (
																							String(value)
																						)
																					) : (
																						<span className="text-[color:var(--color-text-muted)] italic">
																							NULL
																						</span>
																					)}
																				</div>
																			</td>
																		))}
																	</tr>
																))}
															</tbody>
														</table>
													</div>
												</div>
											)}

											{/* Success Message (if no data returned) */}
											{insertResult.success &&
												(!insertResult.data ||
													insertResult.data.length === 0) && (
													<div className="bg-[#0DA931]/20 border border-[#0DA931]/20 rounded-lg p-6 text-center">
														<CheckCircle className="w-12 h-12 text-[#0DA931] mx-auto mb-3" />
														<p className="text-[#0DA931] text-lg font-medium mb-1">
															Insert Successful
														</p>
														<p className="text-[color:var(--color-text-muted)] text-sm">
															{insertResult.rows_inserted} row
															{insertResult.rows_inserted !== 1 ? "s" : ""}{" "}
															inserted successfully
														</p>
													</div>
												)}
										</>
									) : (
										<div className="bg-[color:var(--color-surface)] rounded-lg p-6 text-center">
											<Database className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
											<p className="text-[color:var(--color-text-muted)] text-sm">
												No insert result data available
											</p>
										</div>
									)}
								</div>
							)}
						</div>
					</>
				) : (
					<div className="text-center py-12">
						<p className="text-[color:var(--color-text-muted)] text-sm">
							This node has not been executed yet.
						</p>
					</div>
				)}
			</div>
		</ExecutionModal>
	);
}

export default DatabaseInsertExecutionPanel;
