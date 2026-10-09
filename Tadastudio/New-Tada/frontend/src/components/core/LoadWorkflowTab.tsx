"use client";

import { Download, FolderOpen, Pencil, Share2, Trash2 } from "lucide-react";
import React from "react";
import { api } from "@/lib/api";

interface Graph {
	name: string;
	workflow_id?: string; // UUID for unique workflow identification
	description?: string;
	created_at: string;
	updated_at?: string;
	workflow_role?: string;
	owner_name?: string;
	is_shared?: boolean;
}

interface LoadWorkflowTabProps {
	graphs: Graph[];
	loading: boolean;
	searchQuery: string;
	sortOption: "created" | "updated" | "alphabetical";
	sortDirection: "asc" | "desc";
	currentGraph: { name: string } | null;
	deletingGraph: string | null;
	onLoadGraph: (graph: Graph) => void;
	onEditGraph: (graph: Graph) => void;
	onDeleteGraph: (name: string) => void;
}

const LoadWorkflowTab = React.memo(function LoadWorkflowTab({
	graphs,
	loading,
	searchQuery,
	sortOption,
	sortDirection,
	currentGraph,
	deletingGraph,
	onLoadGraph,
	onEditGraph,
	onDeleteGraph,
}: LoadWorkflowTabProps) {
	if (loading) {
		return (
			<div className="space-y-4">
				<div className="text-center py-16 rounded-2xl bg-white">
					<div className="w-10 h-10 border-2 border-transparent border-t-orange-500 rounded-full animate-spin mx-auto mb-4"></div>
					<p className="text-sm text-slate-600">
						Loading workflows...
					</p>
				</div>
			</div>
		);
	}

	if (graphs.length === 0) {
		return (
			<div className="space-y-4">
				<div className="text-center py-16 rounded-2xl border-2 border-orange-400 bg-white">
					<div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-orange-500 mb-4">
						<FolderOpen className="w-7 h-7 text-white" />
					</div>
					<h3 className="text-base font-semibold text-slate-900 mb-2">
						No workflows yet
					</h3>
					<p className="text-sm text-slate-500 max-w-sm mx-auto">
						Create your first workflow to get started building AI-powered
						automation
					</p>
				</div>
			</div>
		);
	}

	// Filter and sort graphs
	const q = searchQuery.trim().toLowerCase();
	const filteredGraphs = q
		? graphs.filter(
				(g) =>
					g?.name?.toLowerCase().includes(q) ||
					g?.description?.toLowerCase().includes(q),
			)
		: graphs;

	const directionMultiplier = sortDirection === "asc" ? 1 : -1;
	const sortedGraphs = [...filteredGraphs].sort((a, b) => {
		// Active workflow always appears at top
		const aIsActive = currentGraph?.name === a.name;
		const bIsActive = currentGraph?.name === b.name;
		if (aIsActive) return -1;
		if (bIsActive) return 1;

		// Then apply user's chosen sort
		switch (sortOption) {
			case "created": {
				const cmp =
					new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
				return cmp * directionMultiplier;
			}
			case "updated": {
				const cmp =
					new Date(a.updated_at || 0).getTime() -
					new Date(b.updated_at || 0).getTime();
				return cmp * directionMultiplier;
			}
			case "alphabetical": {
				const cmp = a.name.localeCompare(b.name);
				return cmp * directionMultiplier;
			}
			default:
				return 0;
		}
	});

	const handleExportGraph = async (graphName: string) => {
		try {
			const response = await api.exportGraph(graphName, "full");
			const blob = new Blob([JSON.stringify(response.data, null, 2)], {
				type: "application/json",
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = `${graphName}.json`;
			a.click();
			URL.revokeObjectURL(url);
		} catch (err) {
			alert("Failed to export: " + (err as Error).message);
		}
	};

	return (
		<div className="space-y-4">
			{/* Summary Card */}
			<div className="rounded-2xl border border-slate-200 bg-white p-4">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-3">
						<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-50 border border-orange-100">
							<FolderOpen className="w-5 h-5 text-orange-600" />
						</div>
						<div>
							<p className="text-xs capitalize tracking-wider text-slate-500 font-semibold">
								Workflow Library
							</p>
							<p className="text-sm text-slate-700 font-medium">
								{sortedGraphs.length} workflow
								{sortedGraphs.length !== 1 ? "s" : ""} available
							</p>
						</div>
					</div>
					{currentGraph && (
						<span className="inline-flex items-center gap-2 rounded-full bg-orange-50 border border-orange-200 px-3 py-1.5 text-xs font-medium text-orange-800">
							<span className="h-1.5 w-1.5 rounded-full bg-orange-500 animate-pulse" />
							{currentGraph.name}
						</span>
					)}
				</div>
			</div>

			{/* Workflow Cards Grid */}
			<div className="grid gap-3">
				{sortedGraphs.map((graph) => {
					const isActive = currentGraph?.name === graph.name;
					const isDeleting = deletingGraph === graph.name;

					return (
						<div
							key={graph.name}
							className={`group relative overflow-hidden rounded-2xl border-2 transition-all duration-300 ${
								isActive
									? "border-orange-400 ring-2 ring-orange-200 ring-offset-2 ring-offset-white bg-orange-50 shadow-[0_25px_60px_rgba(249,115,22,0.18)]"
									: "border-slate-200 bg-white hover:border-slate-300 hover:shadow-[0_15px_35px_rgba(15,23,42,0.10)] hover:-translate-y-0.5"
							} ${
								isDeleting ? "opacity-50 scale-[0.98] pointer-events-none" : ""
							}`}
						>
							{/* Background gradient on hover */}
							{!isActive && (
								<div className="absolute inset-0 bg-gradient-to-br from-orange-50 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
							)}

							<div className="relative p-5">
								<div className="flex items-start justify-between gap-4">
									<div className="flex-1 min-w-0">
										{/* Workflow Title & Status */}
										<div className="flex items-start gap-3 mb-2">
											<div className="flex-1 min-w-0">
												<div className="flex flex-wrap items-center gap-2 mb-1">
													<h3 className="text-base font-semibold text-slate-900 truncate">
														{graph.name}
													</h3>
													{isActive && (
														<span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-medium capitalize tracking-wide text-orange-800 shrink-0">
															Active
														</span>
													)}
													{graph.workflow_role && graph.workflow_role !== "owner" && (
														<span className="inline-flex items-center gap-1.5 rounded-full bg-purple-500/15 border border-purple-500/30 px-2.5 py-0.5 text-xs font-medium text-purple-600 shrink-0">
															<Share2 className="w-3 h-3" />
															Shared by {graph.owner_name || "Unknown"}
														</span>
													)}
													{graph.is_shared && (!graph.workflow_role || graph.workflow_role === "owner") && (
														<span className="inline-flex items-center gap-1.5 rounded-full bg-blue-500/15 border border-blue-500/30 px-2.5 py-0.5 text-xs font-medium text-blue-600 shrink-0">
															<Share2 className="w-3 h-3" />
															Shared
														</span>
													)}
												</div>
												{graph.description && (
													<p className="text-sm text-slate-600 line-clamp-2 leading-relaxed">
														{graph.description}
													</p>
												)}
											</div>
										</div>

										{/* Metadata Badges */}
										<div className="flex flex-wrap items-center gap-2 mt-3">
											<div className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs">
												<span className="text-slate-500">
													Created
												</span>
												<span className="text-slate-700 font-medium">
													{new Date(graph.created_at).toLocaleDateString(
														"en-US",
														{ month: "short", day: "numeric", year: "numeric" },
													)}
												</span>
											</div>
											{graph.updated_at && (
												<div className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs">
													<span className="text-slate-500">
														Updated
													</span>
													<span className="text-slate-700 font-medium">
														{new Date(graph.updated_at).toLocaleDateString(
															"en-US",
															{
																month: "short",
																day: "numeric",
																year: "numeric",
															},
														)}
													</span>
												</div>
											)}
										</div>
									</div>

									{/* Action Buttons */}
									<div className="flex items-start gap-2 shrink-0">
										<button
											onClick={() => onLoadGraph(graph)}
											disabled={isActive}
											className="px-4 py-2 text-sm font-medium rounded-xl transition-all duration-200 border disabled:opacity-40 disabled:cursor-not-allowed bg-orange-500 border-orange-500 text-white hover:bg-orange-600 disabled:bg-slate-100 disabled:border-slate-200 disabled:text-slate-400 disabled:shadow-none"
											title={isActive ? "Already active" : "Load workflow"}
										>
											Load
										</button>
										<button
											onClick={() => onEditGraph(graph)}
											className="p-2.5 text-slate-500 hover:text-slate-900 hover:bg-slate-50 rounded-xl transition-all duration-200 border border-transparent hover:border-slate-200 hover:shadow-[0_10px_25px_rgba(15,23,42,0.10)] hover:-translate-y-0.5"
											title="Edit workflow"
										>
											<Pencil className="w-4 h-4" />
										</button>
										<button
											onClick={() => handleExportGraph(graph.name)}
											className="p-2.5 text-slate-500 hover:text-slate-900 hover:bg-slate-50 rounded-xl transition-all duration-200 border border-transparent hover:border-slate-200 hover:shadow-[0_10px_25px_rgba(15,23,42,0.10)] hover:-translate-y-0.5"
											title="Export workflow"
										>
											<Download className="w-5 h-5" />
										</button>
										<button
											onClick={() => onDeleteGraph(graph.name)}
											disabled={isDeleting}
											className={`p-2.5 rounded-xl transition-all duration-200 border ${
												isDeleting
													? "text-slate-400 bg-slate-50 border-transparent cursor-not-allowed opacity-50"
													: "text-slate-500 hover:text-red-600 hover:bg-red-50 border-transparent hover:border-red-200 hover:shadow-[0_10px_25px_rgba(239,68,68,0.12)] hover:-translate-y-0.5"
											}`}
											title="Delete workflow"
										>
											{isDeleting ? (
												<div className="w-5 h-5 border-2 border-slate-300 border-t-slate-500 rounded-full animate-spin" />
											) : (
												<Trash2 className="w-5 h-5" />
											)}
										</button>
									</div>
								</div>
							</div>
						</div>
					);
				})}
			</div>
		</div>
	);
});

export default LoadWorkflowTab;
