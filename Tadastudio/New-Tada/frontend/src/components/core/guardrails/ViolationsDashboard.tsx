"use client";

import type {
	GuardrailViolation,
	GuardrailViolationEventItem,
} from "@/types/guardrail-policies";
import {
	AlertTriangle,
	ChevronDown,
	ExternalLink,
	Filter,
	MapPin,
	RefreshCw,
	ShieldAlert,
	ThumbsDown,
	ThumbsUp,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import * as guardrailsApi from "@/lib/guardrails-api";
import { formatViolationLocation } from "@/components/panels/execution/streaming/GuardrailViolationActivity";

type SeverityFilter = "all" | "block" | "warn" | "info";

const SEVERITY_COLORS: Record<string, string> = {
	block: "text-red-400 bg-red-400/10 border-red-400/30",
	warn: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
	info: "text-blue-400 bg-blue-400/10 border-blue-400/30",
};

export default function ViolationsDashboard() {
	const { user } = useAuth();
	const isAdmin = user?.is_admin ?? false;

	const [violations, setViolations] = useState<GuardrailViolationEventItem[]>([]);
	const [total, setTotal] = useState(0);
	const [loading, setLoading] = useState(true);
	const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
	const [policyFilter, setPolicyFilter] = useState("");
	const [executionFilter, setExecutionFilter] = useState("");
	const [selectedViolation, setSelectedViolation] =
		useState<GuardrailViolation | null>(null);
	const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
	const [offset, setOffset] = useState(0);

	const LIMIT = 50;

	const fetchViolations = useCallback(async () => {
		setLoading(true);
		try {
			const params: Parameters<typeof guardrailsApi.listViolations>[0] = {
				limit: LIMIT,
				offset,
			};
			if (severityFilter !== "all") params.severity = severityFilter;
			if (policyFilter) params.policy_id = policyFilter;
			if (executionFilter) params.execution_id = executionFilter;

			const resp = await guardrailsApi.listViolations(params);
			setViolations(resp.violations || []);
			setTotal(resp.total || 0);
		} catch (err) {
			console.error("Failed to load violations:", err);
			setViolations([]);
		} finally {
			setLoading(false);
		}
	}, [severityFilter, policyFilter, executionFilter, offset]);

	useEffect(() => {
		fetchViolations();
	}, [fetchViolations]);

	const handleSelectViolation = async (v: GuardrailViolationEventItem) => {
		try {
			const resp = await guardrailsApi.getViolation(v.id);
			setSelectedViolation(resp.violation);
		} catch (err) {
			console.error("Failed to load violation details:", err);
		}
	};

	const handleFeedback = async (
		violation: GuardrailViolation,
		rating: "positive" | "negative",
	) => {
		setFeedbackSubmitting(true);
		try {
			await guardrailsApi.submitViolationFeedback(violation.id, rating);
			fetchViolations();
			if (selectedViolation?.id === violation.id) {
				const resp = await guardrailsApi.getViolation(violation.id);
				setSelectedViolation(resp.violation);
			}
		} catch (err) {
			console.error("Failed to submit feedback:", err);
		} finally {
			setFeedbackSubmitting(false);
		}
	};

	return (
		<div className="flex flex-col h-full overflow-hidden">
			{/* Header */}
			<div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
				<div className="flex items-center gap-3">
					<ShieldAlert className="w-5 h-5 text-red-400" />
					<h1 className="text-lg font-semibold text-slate-900">
						Violations
						{total > 0 && (
							<span className="ml-2 text-sm text-slate-500">({total})</span>
						)}
					</h1>
				</div>
				<button
					type="button"
					onClick={fetchViolations}
					className="p-2 rounded-lg hover:bg-slate-50 text-slate-500 hover:text-slate-900 transition-colors"
				>
					<RefreshCw className="w-4 h-4" />
				</button>
			</div>

			{/* Filters */}
			<div className="flex items-center gap-3 px-6 py-3 border-b border-slate-200">
				<Filter className="w-4 h-4 text-slate-500" />
				<select
					value={severityFilter}
					onChange={(e) => {
						setSeverityFilter(e.target.value as SeverityFilter);
						setOffset(0);
					}}
					className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-700"
				>
					<option value="all">All Severities</option>
					<option value="block">Block</option>
					<option value="warn">Warn</option>
					<option value="info">Info</option>
				</select>
				<input
					type="text"
					value={executionFilter}
					onChange={(e) => {
						setExecutionFilter(e.target.value);
						setOffset(0);
					}}
					placeholder="Filter by execution ID..."
					className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-sm text-slate-900 placeholder-slate-400"
				/>
			</div>

			{/* Table */}
			<div className="flex-1 overflow-auto px-6 py-4">
				{loading ? (
					<div className="flex items-center justify-center h-40 text-slate-500">
						Loading violations...
					</div>
				) : violations.length === 0 ? (
					<div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
						<ShieldAlert className="w-8 h-8" />
						<p>No violations found</p>
					</div>
				) : (
					<div className="space-y-2">
						{violations.map((v) => (
							<button
								type="button"
								key={v.id}
								onClick={() => handleSelectViolation(v)}
								className="w-full text-left bg-slate-50 hover:bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 transition-colors"
							>
								<div className="flex items-start justify-between gap-4">
									<div className="flex items-center gap-3 min-w-0">
										<span
											className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded border ${SEVERITY_COLORS[v.severity] || "text-slate-600"}`}
										>
											{v.severity.charAt(0).toUpperCase() + v.severity.slice(1).toLowerCase()}
										</span>
										<div className="min-w-0">
											<p className="text-sm text-slate-800 font-medium truncate">
												{v.rule_name}
											</p>
											<div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
												{v.category && (
													<span className="truncate font-mono text-slate-500">
														{formatViolationLocation(v.category, v.agent_node_name, v.details?.tool_name as string)}
													</span>
												)}
												{v.category && (v.policy_name || v.workflow_name) && (
													<span className="text-slate-300">|</span>
												)}
												{v.policy_name && (
													<span className="truncate">{v.policy_name}</span>
												)}
												{v.policy_name && v.workflow_name && (
													<span className="text-slate-300">|</span>
												)}
												{v.workflow_name && (
													<span className="truncate">{v.workflow_name}</span>
												)}
											</div>
										</div>
									</div>
									<div className="shrink-0 flex items-center gap-3 text-xs text-slate-500">
										<span>
											{new Date(v.created_at).toLocaleString()}
										</span>
									</div>
								</div>
							</button>
						))}
					</div>
				)}

				{/* Pagination */}
				{!loading && total > LIMIT && (
					<div className="flex justify-center gap-3 mt-4">
						<button
							type="button"
							onClick={() => setOffset(Math.max(0, offset - LIMIT))}
							disabled={offset === 0}
							className="px-4 py-2 text-sm rounded-lg border border-slate-200 disabled:opacity-30 hover:bg-slate-50"
						>
							Previous
						</button>
						<span className="flex items-center text-sm text-slate-500">
							{offset + 1}–{Math.min(offset + LIMIT, total)} of {total}
						</span>
						<button
							type="button"
							onClick={() => setOffset(offset + LIMIT)}
							disabled={offset + LIMIT >= total}
							className="px-4 py-2 text-sm rounded-lg border border-slate-200 disabled:opacity-30 hover:bg-slate-50"
						>
							Next
						</button>
					</div>
				)}
			</div>

			{/* Detail drawer */}
			{selectedViolation && (
				<div className="fixed inset-y-0 right-0 w-96 bg-white border-l border-slate-200 shadow-2xl z-50 overflow-y-auto p-6">
					<div className="flex items-start justify-between mb-6">
						<div>
							<span
								className={`text-xs font-medium px-2 py-0.5 rounded border ${SEVERITY_COLORS[selectedViolation.severity] || ""}`}
							>
								{selectedViolation.severity.charAt(0).toUpperCase() + selectedViolation.severity.slice(1).toLowerCase()}
							</span>
							<h2 className="text-base font-semibold text-slate-900 mt-2">
								{selectedViolation.rule_name}
							</h2>
						</div>
						<button
							type="button"
							onClick={() => setSelectedViolation(null)}
							className="text-slate-400 hover:text-slate-900"
						>
							✕
						</button>
					</div>

					<dl className="space-y-3 text-sm">
						{selectedViolation.category && (
							<div>
								<dt className="text-slate-500 text-xs flex items-center gap-1">
									<MapPin className="w-3 h-3" />
									Location
								</dt>
								<dd className="text-slate-900 font-medium">
									{formatViolationLocation(
										selectedViolation.category,
										selectedViolation.agent_node_name,
										selectedViolation.details?.tool_name as string,
									)}
								</dd>
							</div>
						)}
						{selectedViolation.policy_name && (
							<div>
								<dt className="text-slate-500 text-xs">Policy</dt>
								<dd className="text-slate-700">{selectedViolation.policy_name}</dd>
							</div>
						)}
						{selectedViolation.workflow_name && (
							<div>
								<dt className="text-slate-500 text-xs">Workflow</dt>
								<dd className="text-slate-700">{selectedViolation.workflow_name}</dd>
							</div>
						)}
						<div>
							<dt className="text-slate-500 text-xs">Action Taken</dt>
							<dd className="text-slate-700">{selectedViolation.action_taken}</dd>
						</div>
						{selectedViolation.message && (
							<div>
								<dt className="text-slate-500 text-xs">Message</dt>
								<dd className="text-slate-700">{selectedViolation.message}</dd>
							</div>
						)}
						{selectedViolation.agent_node_name && (
							<div>
								<dt className="text-slate-500 text-xs">Agent Node</dt>
								<dd className="text-slate-700">{selectedViolation.agent_node_name}</dd>
							</div>
						)}
						<div>
							<dt className="text-slate-500 text-xs">Execution ID</dt>
							<dd className="text-slate-500 text-xs font-mono truncate">
								{selectedViolation.graph_execution_id}
							</dd>
						</div>
						<div>
							<dt className="text-slate-500 text-xs">Time</dt>
							<dd className="text-slate-700">
								{new Date(selectedViolation.created_at).toLocaleString()}
							</dd>
						</div>
					</dl>

					{/* Feedback */}
					<div className="mt-6 pt-6 border-t border-slate-200">
						<p className="text-xs text-slate-500 mb-3">
							Was this a legitimate violation or a false positive?
						</p>
						<div className="flex gap-3">
							<button
								type="button"
								onClick={() =>
									handleFeedback(selectedViolation, "positive")
								}
								disabled={feedbackSubmitting}
								className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#0DA931] text-[#0DA931] hover:bg-[#F1F8E9] text-sm transition-colors disabled:opacity-50"
							>
								<ThumbsUp className="w-4 h-4" />
								Legitimate
							</button>
							<button
								type="button"
								onClick={() =>
									handleFeedback(selectedViolation, "negative")
								}
								disabled={feedbackSubmitting}
								className="flex items-center gap-2 px-3 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50 text-sm transition-colors disabled:opacity-50"
							>
								<ThumbsDown className="w-4 h-4" />
								False Positive
							</button>
						</div>
						{selectedViolation.feedback_count > 0 && (
							<p className="mt-2 text-xs text-slate-400">
								{selectedViolation.feedback_count} feedback submitted
								{selectedViolation.false_positive_count > 0 &&
									` · ${selectedViolation.false_positive_count} flagged as false positive`}
							</p>
						)}
					</div>

					{/* Existing feedbacks */}
					{selectedViolation.feedbacks &&
						selectedViolation.feedbacks.length > 0 && (
							<div className="mt-4">
								<p className="text-xs text-slate-500 mb-2">Feedback history</p>
								<div className="space-y-2">
									{selectedViolation.feedbacks.map((f) => (
										<div
											key={f.id}
											className="flex items-start gap-2 text-xs"
										>
											{f.rating === "positive" ? (
												<ThumbsUp className="w-3 h-3 text-[#0DA931] mt-0.5" />
											) : (
												<ThumbsDown className="w-3 h-3 text-red-400 mt-0.5" />
											)}
											<div>
												<span className="text-slate-600">{f.user_id}</span>
												{f.comment && (
													<p className="text-slate-500">{f.comment}</p>
												)}
											</div>
										</div>
									))}
								</div>
							</div>
						)}
				</div>
			)}
		</div>
	);
}
