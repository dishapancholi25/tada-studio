"use client";

import type {
	AssignmentTargetType,
	GuardrailAssignment,
	GuardrailPolicy,
	OverrideMode,
} from "@/types/guardrail-policies";
import * as guardrailsApi from "@/lib/guardrails-api";
import { invalidateGuardrailStatusCache } from "@/hooks/useNodeGuardrailStatus";
import { AlertTriangle, Check, Loader2, Search, Shield, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

interface PolicyPickerProps {
	targetType: AssignmentTargetType;
	targetId: string;
	workflowId?: string;
	onAssigned: (assignment: GuardrailAssignment) => void;
	onClose: () => void;
}

export default function PolicyPicker({
	targetType,
	targetId,
	workflowId,
	onAssigned,
	onClose,
}: PolicyPickerProps) {
	const [policies, setPolicies] = useState<GuardrailPolicy[]>([]);
	const [search, setSearch] = useState("");
	const [selectedPolicy, setSelectedPolicy] = useState<GuardrailPolicy | null>(
		null,
	);
	const [priority, setPriority] = useState(500);
	const [overrideMode, setOverrideMode] = useState<OverrideMode>("merge");
	const [loading, setLoading] = useState(true);
	const [submitting, setSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);

	// Map assignment target types to policy applies_to values
	const targetTypeToAppliesTo: Record<string, string> = {
		agent_node: "agent",
		workflow: "workflow",
		tool: "tool",
		model: "model",
	};
	const appliesToValue = targetTypeToAppliesTo[targetType] || targetType;

	const fetchPolicies = useCallback(async () => {
		setLoading(true);
		try {
			const result = await guardrailsApi.listPolicies({
				search: search || undefined,
				applies_to: appliesToValue,
			});
			setPolicies(result.policies || []);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to load policies");
		} finally {
			setLoading(false);
		}
	}, [search, appliesToValue]);

	useEffect(() => {
		const timer = setTimeout(fetchPolicies, 300);
		return () => clearTimeout(timer);
	}, [fetchPolicies]);

	const filteredPolicies = useMemo(() => {
		return policies;
	}, [policies]);

	const handleAssign = useCallback(async () => {
		if (!selectedPolicy) return;
		setSubmitting(true);
		setError(null);
		try {
			const result = await guardrailsApi.createAssignment({
				policy_id: selectedPolicy.id,
				target_type: targetType,
				target_id: targetId,
				workflow_id: workflowId || null,
				priority,
				override_mode: overrideMode,
			});
			invalidateGuardrailStatusCache(workflowId || undefined);
			onAssigned(result.assignment);
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to assign policy",
			);
		} finally {
			setSubmitting(false);
		}
	}, [
		selectedPolicy,
		targetType,
		targetId,
		workflowId,
		priority,
		overrideMode,
		onAssigned,
	]);

	return (
		<div
			className="absolute inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px] rounded-[4px]"
			onClick={onClose}
		>
			<div
				className="relative flex w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_20px_60px_rgba(4,7,17,0.2)] max-h-[90%] mx-6"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				{/* Header */}
				<div className="flex flex-none items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100 text-orange-600">
							<Shield className="h-5 w-5" />
						</div>
						<div>
							<h3 className="text-base font-semibold text-slate-900">
								Assign Policy
							</h3>
							<p className="mt-1 text-sm text-slate-500">
								Select a guardrail policy for this target.
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
					>
						<X className="h-4 w-4" />
					</button>
				</div>

				{/* Search */}
				<div className="flex-none border-b border-slate-200 bg-white px-6 py-4">
					<div className="relative">
						<Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
						<input
							type="text"
							placeholder="Search policies..."
							value={search}
							onChange={(e) => setSearch(e.target.value)}
							className="w-full rounded-[4px] border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 transition-all hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
						/>
					</div>
				</div>

				{/* Policy list */}
				<div className="max-h-[240px] overflow-y-auto bg-white px-6 py-3">
					{loading ? (
						<div className="flex items-center justify-center py-8 text-slate-500">
							<Loader2 className="mr-2 h-4 w-4 animate-spin text-orange-600" />
							Loading policies...
						</div>
					) : filteredPolicies.length === 0 ? (
						<div className="rounded-[4px] border border-slate-200 bg-white py-8 text-center text-sm text-slate-600">
							No policies found
						</div>
					) : (
						<div className="space-y-0.5">
							{filteredPolicies.map((policy) => (
								<button
									key={policy.id}
									onClick={() => setSelectedPolicy(policy)}
									className={`flex w-full items-center gap-3 rounded-[4px] border px-3 py-2 text-left transition-colors ${
										selectedPolicy?.id === policy.id
											? "border-orange-500 bg-white shadow-sm"
											: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50"
									}`}
								>
									<Shield
										className={`h-4 w-4 flex-shrink-0 ${
											selectedPolicy?.id === policy.id
												? "text-orange-600"
												: "text-slate-400"
										}`}
									/>
									<div className="min-w-0 flex-1">
										<div className="truncate text-sm font-medium text-slate-900">
											{policy.name}
										</div>
										{policy.description && (
											<div className="truncate text-xs text-slate-500">
												{policy.description}
											</div>
										)}
									</div>
									{selectedPolicy?.id === policy.id && (
										<Check className="h-4 w-4 flex-shrink-0 text-orange-600" />
									)}
								</button>
							))}
						</div>
					)}
				</div>

				{/* Options */}
				{selectedPolicy && (
					<div className="flex-none border-t border-slate-200 bg-white px-6 py-4">
						<div className="flex gap-4">
							<div className="flex-1">
								<label className="mb-1 block text-xs font-medium text-slate-600">
									Priority
								</label>
								<input
									type="number"
									min={0}
									max={9999}
									value={priority}
									onChange={(e) =>
										setPriority(
											Number.parseInt(e.target.value, 10) || 500,
										)
									}
									className="w-full rounded-[4px] border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
								/>
							</div>
							<div className="flex-1">
								<label className="mb-1 block text-xs font-medium text-slate-600">
									Override Mode
								</label>
								<select
									value={overrideMode}
									onChange={(e) =>
										setOverrideMode(e.target.value as OverrideMode)
									}
									className="w-full rounded-[4px] border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-900 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
								>
									<option value="merge">Merge</option>
									<option value="replace">Replace</option>
									<option value="append">Append</option>
								</select>
							</div>
						</div>
					</div>
				)}

				{/* Error */}
				{error && (
					<div className="px-6 pb-3">
						<div className="flex items-center gap-2 rounded-lg border border-red-200 bg-white px-3 py-2 text-sm text-red-600">
							<AlertTriangle className="h-4 w-4 flex-shrink-0" />
							{error}
						</div>
					</div>
				)}

				{/* Footer */}
				<div className="flex-none flex items-center justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleAssign}
						disabled={!selectedPolicy || submitting}
						className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:opacity-50"
					>
						{submitting && <Loader2 className="h-3.5 w-3.5 animate-spin text-orange-500" />}
						Assign Policy
					</button>
				</div>
			</div>
		</div>
	);
}
