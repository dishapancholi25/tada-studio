"use client";

import type {
	GuardrailPolicy,
	GuardrailViolationEventItem,
	ViolationsSummary,
} from "@/types/guardrail-policies";
import { Shield, Zap, ChevronDown } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import * as guardrailsApi from "@/lib/guardrails-api";
import Dropdown from "@/components/ui/Dropdown";
import ViolationFeedbackControl from "./ViolationFeedbackControl";
import { formatDistanceToNow } from "date-fns";

function severityBadge(severity: string) {
	const base = "rounded-md text-[10px] font-semibold px-1.5 py-0.5";
	switch (severity) {
		case "block":
			return (
				<span
					className={`${base} bg-red-500/20 text-red-400 border border-red-500/40`}
				>
					BLOCK
				</span>
			);
		case "warn":
			return (
				<span
					className={`${base} bg-yellow-500/20 text-yellow-400 border border-yellow-500/40`}
				>
					WARN
				</span>
			);
		default:
			return (
				<span
					className={`${base} bg-white text-slate-600 border border-slate-200`}
				>
					INFO
				</span>
			);
	}
}

function relativeTime(dateStr: string) {
	try {
		return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
	} catch {
		return dateStr;
	}
}

export default function ViolationDashboard() {
	const { user } = useAuth();
	const isAdmin = user?.is_admin ?? false;

	const [violations, setViolations] = useState<GuardrailViolationEventItem[]>(
		[],
	);
	const [summary, setSummary] = useState<ViolationsSummary | null>(null);
	const [loading, setLoading] = useState(true);
	const [page, setPage] = useState(1);
	const [hasMore, setHasMore] = useState(false);

	const [severityFilter, setSeverityFilter] = useState("");
	const [policyFilter, setPolicyFilter] = useState("");
	const [workflowFilter, setWorkflowFilter] = useState("");
	const [timeRange, setTimeRange] = useState("7d");

	const [policies, setPolicies] = useState<GuardrailPolicy[]>([]);

	// Fetch policies for the dropdown once
	useEffect(() => {
		guardrailsApi
			.listPolicies()
			.then((resp) => setPolicies(resp.policies || []))
			.catch(() => {});
	}, []);

	const fetchViolations = useCallback(
		async (pageNum: number, append: boolean) => {
			if (!append) setLoading(true);
			try {
				const params: Parameters<typeof guardrailsApi.listViolations>[0] = {
					limit: 25,
					offset: (pageNum - 1) * 25,
				};
				if (timeRange && timeRange !== "all") {
					const now = new Date();
					const days = timeRange === "30d" ? 30 : 7;
					const from = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
					params.from_ts = from.toISOString();
				}
				if (severityFilter) params.severity = severityFilter;
				if (policyFilter) params.policy_id = policyFilter;
				if (workflowFilter) params.workflow_id = workflowFilter;

				const resp = await guardrailsApi.listViolations(params);
				const items = resp.violations || [];
				if (append) {
					setViolations((prev) => [...prev, ...items]);
				} else {
					setViolations(items);
				}
				const computedHasMore =
					typeof resp.has_more === "boolean"
						? resp.has_more
						: typeof resp.limit === "number" && typeof resp.offset === "number"
							? resp.offset + resp.limit < resp.total
							: false;
				setHasMore(computedHasMore);
			} catch (err) {
				console.error("Failed to load violations:", err);
				if (!append) setViolations([]);
			} finally {
				setLoading(false);
			}
		},
		[severityFilter, policyFilter, workflowFilter, timeRange],
	);

	// Fetch on mount / filter change
	useEffect(() => {
		setPage(1);
		fetchViolations(1, false);
		if (isAdmin) {
			guardrailsApi
				.getViolationsSummary()
				.then((resp) => setSummary(resp))
				.catch(() => {});
		}
	}, [fetchViolations, isAdmin]);

	const loadMore = () => {
		const nextPage = page + 1;
		setPage(nextPage);
		fetchViolations(nextPage, true);
	};

	const dropdownTriggerClass =
		"w-full !rounded-lg !border-slate-200 !bg-white !px-3 !py-2 !text-sm !text-slate-700 hover:!border-orange-400";

	return (
		<div className="space-y-6">
			{/* Admin summary cards */}
			{isAdmin && summary && (
				<div className="flex flex-wrap gap-4">
					<SummaryCard
						label="Violations (24h)"
						value={summary.total_violations_24h}
						color="text-red-400"
					/>
					<SummaryCard
						label="Enforce"
						value={summary.enforce_count}
						color="text-slate-900"
					/>
					<SummaryCard
						label="Audit"
						value={summary.audit_count}
						color="text-amber-600"
					/>
					<SummaryCard
						label="Compulsory"
						value={summary.compulsory_count}
						color="text-red-400"
					/>
					<SummaryCard
						label="Disabled"
						value={summary.disabled_count}
						color="text-slate-400"
					/>
				</div>
			)}

			{/* Filter bar */}
			<div className="flex flex-col sm:flex-row sm:flex-wrap items-stretch sm:items-center gap-3">
				<div className="w-full sm:w-[180px]">
					<Dropdown
						value={severityFilter}
						onChange={setSeverityFilter}
						menuAppearance="light"
						width="trigger"
						triggerClassName={dropdownTriggerClass}
						options={[
							{ value: "", label: "All Severities" },
							{ value: "block", label: "Block" },
							{ value: "warn", label: "Warn" },
							{ value: "info", label: "Info" },
						]}
					/>
				</div>
				<div className="w-full sm:w-[180px]">
					<Dropdown
						value={policyFilter}
						onChange={setPolicyFilter}
						menuAppearance="light"
						width="trigger"
						menuMinWidthPx={220}
						triggerClassName={dropdownTriggerClass}
						options={[
							{ value: "", label: "All Policies" },
							...policies.map((p) => ({ value: p.id, label: p.name })),
						]}
					/>
				</div>
				<div className="w-full sm:w-[180px]">
					<Dropdown
						value={workflowFilter}
						onChange={setWorkflowFilter}
						menuAppearance="light"
						width="trigger"
						triggerClassName={dropdownTriggerClass}
						options={[{ value: "", label: "All Workflows" }]}
					/>
				</div>
				<div className="w-full sm:w-[180px]">
					<Dropdown
						value={timeRange}
						onChange={setTimeRange}
						menuAppearance="light"
						width="trigger"
						triggerClassName={dropdownTriggerClass}
						options={[
							{ value: "7d", label: "Last 7 days" },
							{ value: "30d", label: "Last 30 days" },
							{ value: "all", label: "All time" },
						]}
					/>
				</div>
			</div>

			{/* Table */}
			{loading ? (
				<div className="flex flex-col items-center justify-center gap-4 py-20">
					<div className="animate-spin rounded-full h-10 w-10 border-2 border-transparent border-t-orange-500" />
					<p className="text-sm text-slate-600">Loading violations...</p>
				</div>
			) : violations.length === 0 ? (
				<div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-20 text-slate-500 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
					<Shield className="w-12 h-12 mb-4 text-orange-600 opacity-80" />
					<p className="text-sm">No violations found</p>
				</div>
			) : (
				<>
					<div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
					<div className="overflow-x-auto">
					<table className="w-full border-collapse">
						<thead>
							<tr>
								<th className="text-[11px] text-slate-500 font-medium capitalize tracking-wider px-4 py-3 text-left border-b border-slate-200">
									Severity
								</th>
								<th className="text-[11px] text-slate-500 font-medium capitalize tracking-wider px-4 py-3 text-left border-b border-slate-200">
									Rule
								</th>
								<th className="text-[11px] text-slate-500 font-medium capitalize tracking-wider px-4 py-3 text-left border-b border-slate-200">
									Policy
								</th>
								<th className="text-[11px] text-slate-500 font-medium capitalize tracking-wider px-4 py-3 text-left border-b border-slate-200 hidden md:table-cell">
									Workflow / Node
								</th>
								<th className="text-[11px] text-slate-500 font-medium capitalize tracking-wider px-4 py-3 text-left border-b border-slate-200">
									Time
								</th>
								<th className="text-[11px] text-slate-500 font-medium capitalize tracking-wider px-4 py-3 text-left border-b border-slate-200">
									Feedback
								</th>
							</tr>
						</thead>
						<tbody>
							{violations.map((v) => (
								<tr
									key={v.id}
									className="hover:bg-white transition-colors"
								>
									<td className="px-4 py-3 text-sm border-b border-slate-100">
										{severityBadge(v.severity)}
									</td>
									<td className="px-4 py-3 text-sm text-slate-700 border-b border-slate-100">
										{v.rule_name}
									</td>
									<td className="px-4 py-3 text-sm text-slate-700 border-b border-slate-100">
										{v.policy_name || v.policy_id}
									</td>
									<td className="px-4 py-3 text-sm border-b border-slate-100 hidden md:table-cell">
										{v.graph_execution_id ? (
											<a
												href={`/execution-history?execution_id=${v.graph_execution_id}`}
												className="text-orange-700 hover:text-slate-900 text-xs"
											>
												{v.workflow_name || v.workflow_id || "—"}{" "}
												{v.agent_node_name && `/ ${v.agent_node_name}`}
											</a>
										) : (
											<span className="text-slate-500 text-xs">
												{v.workflow_name || v.workflow_id || "—"}{" "}
												{v.agent_node_name && `/ ${v.agent_node_name}`}
											</span>
										)}
									</td>
									<td className="px-4 py-3 text-xs text-slate-500 border-b border-slate-100">
										{relativeTime(v.created_at)}
									</td>
									<td className="px-4 py-3 border-b border-slate-100">
										<ViolationFeedbackControl
											violationId={v.id}
											size="sm"
										/>
									</td>
								</tr>
							))}
						</tbody>
					</table>
					</div>
					</div>

					{hasMore && (
						<div className="flex justify-center pt-4">
							<button
								type="button"
								onClick={loadMore}
								className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-orange-400 hover:text-slate-900"
							>
								<ChevronDown className="w-4 h-4" />
								Load More
							</button>
						</div>
					)}
				</>
			)}
		</div>
	);
}

function SummaryCard({
	label,
	value,
	color,
}: {
	label: string;
	value: number;
	color: string;
}) {
	return (
		<div className="rounded-2xl border border-slate-200 bg-white p-4 min-w-[110px] shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
			<div className="text-[11px] text-slate-500 capitalize tracking-wider mb-1">
				{label}
			</div>
			<div className={`text-3xl font-bold ${color}`}>{value}</div>
		</div>
	);
}
