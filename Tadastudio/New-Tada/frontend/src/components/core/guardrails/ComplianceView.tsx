"use client";

import type {
	ComplianceCriticality,
	ComplianceSummary,
	ComplianceWorkflowEntry,
} from "@/types/guardrail-policies";
import {
	AlertTriangle,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	RefreshCw,
	Search,
	Shield,
	ShieldAlert,
	ShieldCheck,
	ShieldOff,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import * as guardrailsApi from "@/lib/guardrails-api";
import Dropdown from "@/components/ui/Dropdown";

// ── Criticality badge config ─────────────────────────────────

const CRITICALITY_CONFIG: Record<
	ComplianceCriticality,
	{ label: string; className: string; dotColor: string }
> = {
	critical: {
		label: "Critical",
		className: "border-transparent bg-[#B00020] text-white",
		dotColor: "bg-white",
	},
	high: {
		label: "High",
		className: "bg-orange-400/15 text-orange-300 border-orange-400/30",
		dotColor: "bg-orange-400",
	},
	medium: {
		label: "Medium",
		className: "bg-yellow-400/15 text-yellow-300 border-yellow-400/30",
		dotColor: "bg-yellow-400",
	},
	low: {
		label: "Low",
		className: "bg-blue-400/15 text-blue-600 border-blue-400/30",
		dotColor: "bg-blue-400",
	},
};

const dropdownTriggerClass = "px-3 py-2 text-sm rounded-lg bg-white border border-slate-200 text-slate-700 hover:border-orange-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 transition-colors";

function CriticalityBadge({
	criticality,
}: { criticality: ComplianceCriticality }) {
	const config = CRITICALITY_CONFIG[criticality];
	return (
		<span
			className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border ${config.className}`}
		>
			<span className={`w-1.5 h-1.5 rounded-full ${config.dotColor}`} />
			{config.label}
		</span>
	);
}

function formatDate(iso: string | null | undefined): string {
	if (!iso) return "Never";
	return new Date(iso).toLocaleDateString("en-GB", {
		day: "numeric",
		month: "short",
		year: "numeric",
	});
}

// ── Main component ───────────────────────────────────────────

export default function ComplianceView({ isAdmin = false }: { isAdmin?: boolean } = {}) {
	const [data, setData] = useState<ComplianceSummary | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
	const [now, setNow] = useState(Date.now());
	const [searchQuery, setSearchQuery] = useState("");
	const [criticalityFilter, setCriticalityFilter] =
		useState<ComplianceCriticality | "all">("all");
	const [statusFilter, setStatusFilter] = useState<
		"all" | "published" | "library" | "draft"
	>("all");
	const [showWorkflows, setShowWorkflows] = useState(true);
	const [showNodes, setShowNodes] = useState(true);
	const [showInactive, setShowInactive] = useState(false);

	useEffect(() => {
		const tickId = setInterval(() => setNow(Date.now()), 60_000);
		return () => clearInterval(tickId);
	}, []);

	const fetch = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const resp = isAdmin
				? await guardrailsApi.getComplianceSummary()
				: await guardrailsApi.getMyComplianceSummary();
			setData(resp);
			setLastUpdated(new Date());
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to load compliance data",
			);
		} finally {
			setLoading(false);
		}
	}, [isAdmin]);

	useEffect(() => {
		fetch();
	}, [fetch]);

	useEffect(() => {
		const intervalId = setInterval(() => {
			fetch();
		}, 300_000);
		return () => clearInterval(intervalId);
	}, [fetch]);

	if (loading) {
		return (
			<div className="flex items-center justify-center h-full text-slate-500">
				Loading compliance data...
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex flex-col items-center justify-center h-full gap-2">
				<AlertTriangle className="w-8 h-8 text-yellow-400" />
				<p className="text-slate-600">{error}</p>
				<button
					type="button"
					onClick={fetch}
					className="text-sm text-orange-700 hover:text-slate-900 hover:underline"
				>
					Retry
				</button>
			</div>
		);
	}

	if (!data) return null;

	const summary = data.enforcement_breakdown;

	// Sort by: published/library first, then criticality (critical → low)
	const critOrder: Record<string, number> = {
		critical: 0,
		high: 1,
		medium: 2,
		low: 3,
	};
	const sharedWeight = (item: {
		is_published?: boolean;
		is_library?: boolean;
	}) => (item.is_published || item.is_library ? 0 : 1);

	const query = searchQuery.toLowerCase().trim();

	const matchesSearch = (fields: (string | null | undefined)[]) =>
		!query || fields.some((f) => f?.toLowerCase().includes(query));

	const matchesCriticality = (c: ComplianceCriticality | undefined) =>
		criticalityFilter === "all" || (c || "low") === criticalityFilter;

	const matchesStatus = (item: {
		is_published?: boolean;
		is_library?: boolean;
	}) => {
		if (statusFilter === "all") return true;
		if (statusFilter === "published") return item.is_published;
		if (statusFilter === "library") return item.is_library;
		return !item.is_published && !item.is_library;
	};

	const sortedWorkflows = [...data.unprotected_workflows]
		.filter(
			(wf) =>
				matchesSearch([
					wf.workflow_name,
					wf.workflow_id,
					wf.owner_name,
					wf.owner_email,
				]) &&
				matchesCriticality(wf.criticality) &&
				matchesStatus(wf),
		)
		.sort(
			(a, b) =>
				sharedWeight(a) - sharedWeight(b) ||
				(critOrder[a.criticality || "low"] ?? 2) -
					(critOrder[b.criticality || "low"] ?? 2),
		);

	const sortedNodes = [...data.unprotected_agent_nodes]
		.filter(
			(node) =>
				matchesSearch([
					node.node_name,
					node.node_id,
					node.workflow_name,
					node.owner_name,
					node.owner_email,
					node.model,
				]) &&
				matchesCriticality(node.criticality) &&
				matchesStatus(node),
		)
		.sort(
			(a, b) =>
				sharedWeight(a) - sharedWeight(b) ||
				(critOrder[a.criticality || "low"] ?? 2) -
					(critOrder[b.criticality || "low"] ?? 2),
		);

	const totalUnfiltered =
		data.unprotected_workflows.length + data.unprotected_agent_nodes.length;
	const hasAnyItems = sortedWorkflows.length > 0 || sortedNodes.length > 0;
	const hasActiveFilters =
		query !== "" || criticalityFilter !== "all" || statusFilter !== "all";

	return (
		<div className="flex flex-col h-full overflow-auto p-6 gap-8">
			{/* Header */}
			<div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
				<div className="flex items-center gap-3">
					<ShieldCheck className="w-5 h-5 text-[#0DA931]" />
					<div>
						<h1 className="text-lg font-semibold text-slate-900">
							Compliance Overview
						</h1>
						<p className="text-xs text-slate-500">
							{lastUpdated
								? `Last updated: ${Math.floor((now - lastUpdated.getTime()) / 60000) < 1 ? "just now" : `${Math.floor((now - lastUpdated.getTime()) / 60000)} minutes ago`} · Auto-refreshes every 5 minutes`
								: "Auto-refreshes every 5 minutes"}
						</p>
					</div>
				</div>
				<button
					type="button"
					onClick={fetch}
					className="p-2 rounded-lg border border-slate-200 bg-white text-slate-500 hover:border-orange-400 hover:text-slate-900 transition-colors"
				>
					<RefreshCw className="w-4 h-4" />
				</button>
			</div>

			{/* Summary cards */}
			<div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
				<SummaryCard
					icon={<ShieldCheck className="w-5 h-5 text-[#0DA931]" />}
					label="Enforce"
					value={summary.enforce}
					color="green"
				/>
				<SummaryCard
					icon={<Shield className="w-5 h-5 text-yellow-400" />}
					label="Audit"
					value={summary.audit}
					color="yellow"
				/>
				<SummaryCard
					icon={<ShieldOff className="w-5 h-5 text-slate-400" />}
					label="Disabled"
					value={summary.disabled}
					color="gray"
				/>
				<SummaryCard
					icon={<ShieldAlert className="w-5 h-5 text-purple-400" />}
					label="Compulsory"
					value={summary.compulsory}
					color="purple"
				/>
			</div>

			{/* Search & filters */}
			{totalUnfiltered > 0 && (
				<div className="grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
					<div className="relative">
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
						<input
							type="text"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							placeholder="Search by name, owner, model..."
							className="w-full pl-9 pr-8 py-2 text-sm rounded-lg bg-white border border-slate-200 text-slate-900 placeholder:text-slate-400 hover:border-orange-400 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15 transition-colors"
						/>
						{searchQuery && (
							<button
								type="button"
								onClick={() => setSearchQuery("")}
								className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-900"
							>
								<X className="w-3.5 h-3.5" />
							</button>
						)}
					</div>
					<div className="flex gap-3">
						<div className="w-full lg:w-[180px]">
							<Dropdown
								value={criticalityFilter}
								onChange={(value) =>
									setCriticalityFilter(
										value as ComplianceCriticality | "all",
									)
								}
								menuAppearance="light"
								width="trigger"
								triggerClassName={dropdownTriggerClass}
								options={[
									{ value: "all", label: "All Criticalities" },
									{ value: "critical", label: "Critical" },
									{ value: "high", label: "High" },
									{ value: "medium", label: "Medium" },
									{ value: "low", label: "Low" },
								]}
							/>
						</div>
						<div className="w-full lg:w-[180px]">
							<Dropdown
								value={statusFilter}
								onChange={(value) =>
									setStatusFilter(
										value as
											| "all"
											| "published"
											| "library"
											| "draft"
									)
								}
								menuAppearance="light"
								width="trigger"
								triggerClassName={dropdownTriggerClass}
								options={[
									{ value: "all", label: "All Statuses" },
									{ value: "published", label: "Published" },
									{ value: "library", label: "Library" },
									{ value: "draft", label: "Draft" },
								]}
							/>
						</div>
					</div>
					{hasActiveFilters && (
						<button
							type="button"
							onClick={() => {
								setSearchQuery("");
								setCriticalityFilter("all");
								setStatusFilter("all");
							}}
							className="px-3 py-2 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg hover:border-orange-400 transition-colors whitespace-nowrap"
						>
							Clear filters
						</button>
					)}
				</div>
			)}

			{/* No results after filtering */}
			{hasActiveFilters && !hasAnyItems && totalUnfiltered > 0 && (
				<div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-8 text-slate-500 gap-2 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
					<Search className="w-6 h-6" />
					<p className="text-sm">No results match your filters</p>
					<button
						type="button"
						onClick={() => {
							setSearchQuery("");
							setCriticalityFilter("all");
							setStatusFilter("all");
						}}
						className="text-xs text-orange-700 hover:text-slate-900 hover:underline"
					>
						Clear all filters
					</button>
				</div>
			)}

			{/* Workflows without specific guardrails */}
			{sortedWorkflows.length > 0 && (
				<section>
					<button
						type="button"
						onClick={() => setShowWorkflows(!showWorkflows)}
						className="flex items-center gap-2 mb-3 group"
					>
						{showWorkflows ? (
							<ChevronDown className="w-3.5 h-3.5 text-slate-500" />
						) : (
							<ChevronRight className="w-3.5 h-3.5 text-slate-500" />
						)}
						<h2 className="text-sm font-medium text-slate-700 group-hover:text-slate-900 transition-colors">
							Workflows Without Specific Guardrails ({sortedWorkflows.length})
						</h2>
					</button>
					{showWorkflows && <div className="space-y-2">
						{sortedWorkflows.map((wf) => (
							<div
								key={wf.workflow_id}
								className="p-3 rounded-2xl bg-white border border-slate-200 space-y-2 shadow-[0_10px_28px_rgba(15,23,42,0.06)]"
							>
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-2 flex-wrap">
										<p className="text-sm font-medium text-slate-900">
											{wf.workflow_name || wf.workflow_id}
										</p>
										{wf.is_published ? (
											<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border border-transparent bg-[#00A63E] text-white">
												Published
											</span>
										) : wf.is_library ? (
											<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border bg-blue-400/15 text-blue-700 border-blue-400/30">
												Library
											</span>
										) : (
											<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border bg-white text-slate-500 border-slate-200">
												Draft
											</span>
										)}
										<CriticalityBadge
											criticality={wf.criticality || "low"}
										/>
									</div>
									<button
										type="button"
										onClick={() =>
											window.open(
												`/guardrails?assign=workflow&id=${wf.workflow_id}`,
												"_self",
											)
										}
										className="text-xs text-orange-700 hover:text-slate-900 hover:underline shrink-0"
									>
										Assign Policy
									</button>
								</div>
								{wf.has_compulsory_coverage && (
									<p className="text-[11px] text-slate-600">
										Covered by compulsory policies
									</p>
								)}
								<div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1 text-[11px] text-slate-500">
									<span>
										Owner:{" "}
										<span className="text-slate-700">
											{wf.owner_name || wf.owner_email || "Unassigned"}
										</span>
									</span>
									<span>
										Created:{" "}
										<span className="text-slate-700">
											{formatDate(wf.created_at)}
										</span>
									</span>
									<span>
										Last executed:{" "}
										<span className="text-slate-700">
											{formatDate(wf.last_executed_at)}
										</span>
									</span>
									<span>
										Executions:{" "}
										<span className="text-slate-700">
											{wf.execution_count ?? 0}
										</span>
									</span>
									<span>
										Agent nodes:{" "}
										<span className="text-slate-700">
											{wf.agent_node_count ?? 0}
										</span>
									</span>
									<span>
										Version:{" "}
										<span className="text-slate-700">
											{wf.graph_version ?? "—"}
										</span>
									</span>
									<span>
										Last modified:{" "}
										<span className="text-slate-700">
											{formatDate(wf.updated_at)}
										</span>
									</span>
								</div>
							</div>
						))}
					</div>}
				</section>
			)}

			{/* Agent nodes without specific guardrails */}
			{sortedNodes.length > 0 && (
				<section>
					<button
						type="button"
						onClick={() => setShowNodes(!showNodes)}
						className="flex items-center gap-2 mb-3 group"
					>
						{showNodes ? (
							<ChevronDown className="w-3.5 h-3.5 text-slate-500" />
						) : (
							<ChevronRight className="w-3.5 h-3.5 text-slate-500" />
						)}
						<h2 className="text-sm font-medium text-slate-700 group-hover:text-slate-900 transition-colors">
							Agent Nodes Without Specific Guardrails ({sortedNodes.length})
						</h2>
					</button>
					{showNodes && <div className="space-y-2">
						{sortedNodes.map((node) => (
							<div
								key={`${node.workflow_id}-${node.node_id}`}
								className="p-3 rounded-2xl bg-white border border-slate-200 space-y-2 shadow-[0_10px_28px_rgba(15,23,42,0.06)]"
							>
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-2 flex-wrap">
										<p className="text-sm font-medium text-slate-900">
											{node.node_name || node.node_id}
										</p>
										{node.is_published ? (
											<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border border-transparent bg-[#00A63E] text-white">
												Published
											</span>
										) : node.is_library ? (
											<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border bg-blue-400/15 text-blue-700 border-blue-400/30">
												Library
											</span>
										) : (
											<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border bg-white text-slate-500 border-slate-200">
												Draft
											</span>
										)}
										<CriticalityBadge
											criticality={node.criticality || "low"}
										/>
										{node.guardrails_disabled && (
											<span className="text-[11px] text-slate-700">
												Guardrails disabled
											</span>
										)}
									</div>
									<button
										type="button"
										onClick={() =>
											window.open(
												`/guardrails?assign=agent_node&id=${node.node_id}`,
												"_self",
											)
										}
										className="text-xs text-orange-700 hover:text-slate-900 hover:underline shrink-0"
									>
										Assign Policy
									</button>
								</div>
								{node.has_compulsory_coverage &&
									!node.guardrails_disabled && (
										<p className="text-[11px] text-slate-600">
											Compulsory coverage
										</p>
									)}
								<div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1 text-[11px] text-slate-500">
									<span>
										Workflow:{" "}
										<span className="text-slate-700 break-words">
											{node.workflow_name || "—"}
										</span>
									</span>
									<span>
										Owner:{" "}
										<span className="text-slate-700 break-words">
											{node.owner_name || node.owner_email || "Unassigned"}
										</span>
									</span>
									{node.model && (
										<span>
											Model:{" "}
											<span className="text-slate-700">{node.model}</span>
										</span>
									)}
									<span>
										Created:{" "}
										<span className="text-slate-700">
											{formatDate(node.created_at)}
										</span>
									</span>
									<span>
										Last executed:{" "}
										<span className="text-slate-700">
											{formatDate(node.last_executed_at)}
										</span>
									</span>
								</div>
							</div>
						))}
					</div>}
				</section>
			)}

			{/* Inactive workflows — never executed or stale, collapsed by default */}
			{(data.inactive_workflows?.length ?? 0) > 0 && (
				<section>
					<button
						type="button"
						onClick={() => setShowInactive(!showInactive)}
						className="flex items-center gap-2 mb-3 group"
					>
						{showInactive ? (
							<ChevronDown className="w-3.5 h-3.5 text-slate-500" />
						) : (
							<ChevronRight className="w-3.5 h-3.5 text-slate-500" />
						)}
						<h2 className="text-sm font-medium text-slate-500 group-hover:text-slate-900 transition-colors">
							Inactive Workflows — Never Executed or Stale (
							{data.inactive_workflows?.length})
						</h2>
					</button>
					{showInactive && (
						<div className="space-y-2">
							{data.inactive_workflows?.map((wf) => (
								<InactiveWorkflowCard key={wf.workflow_id} wf={wf} />
							))}
						</div>
					)}
				</section>
			)}

			{/* All clear */}
			{!hasAnyItems && (data.inactive_workflows?.length ?? 0) === 0 && (
				<div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-12 text-slate-500 gap-2 shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
					<CheckCircle className="w-8 h-8 text-[#0DA931]" />
					<p className="text-sm">
						All workflows have specific guardrail coverage
					</p>
				</div>
			)}
		</div>
	);
}

function InactiveWorkflowCard({ wf }: { wf: ComplianceWorkflowEntry }) {
	const isStale = (wf.execution_count ?? 0) > 0;
	return (
		<div className="p-3 rounded-2xl bg-white border border-slate-200 space-y-1.5 opacity-70">
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2 flex-wrap">
					<p className="text-sm text-slate-600">
						{wf.workflow_name || wf.workflow_id}
					</p>
					<span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border bg-white text-slate-500 border-slate-200">
						{isStale
							? `Stale — last run ${formatDate(wf.last_executed_at)}`
							: "Never executed"}
					</span>
				</div>
			</div>
			<div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1 text-[11px] text-slate-500">
				<span>
					Owner:{" "}
					<span className="text-slate-600">
						{wf.owner_name || wf.owner_email || "Unassigned"}
					</span>
				</span>
				<span>
					Created:{" "}
					<span className="text-slate-600">{formatDate(wf.created_at)}</span>
				</span>
				<span>
					Agent nodes:{" "}
					<span className="text-slate-600">{wf.agent_node_count ?? 0}</span>
				</span>
				<span>
					Last modified:{" "}
					<span className="text-slate-600">{formatDate(wf.updated_at)}</span>
				</span>
			</div>
		</div>
	);
}

function SummaryCard({
	icon,
	label,
	value,
	color,
}: {
	icon: React.ReactNode;
	label: string;
	value: number;
	color: string;
}) {
	const borderColors: Record<string, string> = {
		green: "border-[#0DA931]/20",
		yellow: "border-yellow-400/20",
		gray: "border-slate-200",
		purple: "border-purple-400/20",
	};
	return (
		<div
			className={`bg-white border ${borderColors[color] || "border-slate-200"} rounded-2xl p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)]`}
		>
			<div className="flex items-center gap-2 mb-2">
				{icon}
				<span className="text-xs text-slate-500">{label}</span>
			</div>
			<p className="text-2xl font-bold text-slate-900">{value}</p>
		</div>
	);
}
