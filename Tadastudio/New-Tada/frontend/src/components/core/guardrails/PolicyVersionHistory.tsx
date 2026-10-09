"use client";

import type { GuardrailPolicy, GuardrailPolicyVersion } from "@/types/guardrail-policies";
import {
	AlertTriangle,
	ChevronDown,
	Clock,
	History,
	RefreshCw,
	RotateCcw,
	Shield,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import * as guardrailsApi from "@/lib/guardrails-api";

interface PolicyVersionHistoryProps {
	policy: GuardrailPolicy;
	onRollback?: (policy: GuardrailPolicy) => void;
}

export default function PolicyVersionHistory({
	policy,
	onRollback,
}: PolicyVersionHistoryProps) {
	const [versions, setVersions] = useState<GuardrailPolicyVersion[]>([]);
	const [loading, setLoading] = useState(true);
	const [previewVersion, setPreviewVersion] = useState<GuardrailPolicyVersion | null>(
		null,
	);
	const [rollbackTarget, setRollbackTarget] = useState<GuardrailPolicyVersion | null>(
		null,
	);
	const [rolling, setRolling] = useState(false);
	const [rollbackNote, setRollbackNote] = useState("");
	const [previewLoading, setPreviewLoading] = useState(false);

	const fetchVersions = useCallback(async () => {
		setLoading(true);
		try {
			const resp = await guardrailsApi.listPolicyVersions(policy.id);
			setVersions(resp.versions || []);
		} catch (err) {
			console.error("Failed to load versions:", err);
		} finally {
			setLoading(false);
		}
	}, [policy.id]);

	useEffect(() => {
		fetchVersions();
	}, [fetchVersions]);

	const handlePreview = async (v: GuardrailPolicyVersion) => {
		if (previewVersion?.id === v.id) {
			setPreviewVersion(null);
			return;
		}
		// If config_snapshot already present from list, use it directly
		if (v.config_snapshot) {
			setPreviewVersion(v);
			return;
		}
		// Fetch full version data with fallback (UUID -> version_number)
		setPreviewLoading(true);
		try {
			const resp = await guardrailsApi.getPolicyVersion(
				policy.id,
				v.id,
				v.version_number,
			);
			setPreviewVersion(resp.version);
		} catch (err) {
			console.error("Failed to load version preview:", err);
		} finally {
			setPreviewLoading(false);
		}
	};

	const handleRollback = async () => {
		if (!rollbackTarget) return;
		setRolling(true);
		try {
			const resp = await guardrailsApi.rollbackPolicy(
				policy.id,
				rollbackTarget.version,
				rollbackNote || undefined,
			);
			setRollbackTarget(null);
			setRollbackNote("");
			fetchVersions();
			onRollback?.(resp.policy);
		} catch (err) {
			console.error("Rollback failed:", err);
		} finally {
			setRolling(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-12 text-slate-500">
				Loading version history...
			</div>
		);
	}

	return (
		<div className="flex flex-col gap-4">
			{/* Header */}
			<div className="flex items-center justify-between">
				<div className="flex items-center gap-2 text-slate-600">
					<History className="w-4 h-4" />
					<span className="text-sm">{versions.length} versions</span>
				</div>
				<button
					type="button"
					onClick={fetchVersions}
					className="p-1.5 rounded hover:bg-slate-50 text-slate-500 hover:text-slate-900"
				>
					<RefreshCw className="w-4 h-4" />
				</button>
			</div>

			{/* Version list */}
			<div className="space-y-2">
				{versions.map((v, i) => {
					const isCurrent = i === 0;
					return (
						<div
							key={v.id}
							className={`p-3 rounded-lg border ${
								isCurrent
									? "border-blue-400/30 bg-blue-400/5"
									: "border-slate-200 bg-slate-50"
							}`}
						>
							<div className="flex items-start justify-between gap-4">
								<div className="flex items-center gap-3 min-w-0">
									<div
										className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
											isCurrent
												? "bg-blue-400/20 text-blue-400"
												: "bg-slate-100 text-slate-500"
										}`}
									>
										{v.version}
									</div>
									<div className="min-w-0">
										<p className="text-sm text-slate-700 truncate">
											{v.name_snapshot}
											{isCurrent && (
												<span className="ml-2 text-xs text-blue-400">
													(current)
												</span>
											)}
										</p>
										{v.change_summary && (
											<p className="text-xs text-slate-500 truncate">
												{v.change_summary}
											</p>
										)}
									</div>
								</div>
								<div className="shrink-0 flex items-center gap-2">
									<span className="text-xs text-slate-400">
										{new Date(v.created_at).toLocaleDateString()}
									</span>
									<button
										type="button"
										onClick={() => handlePreview(v)}
										disabled={previewLoading}
										className="text-xs text-slate-500 hover:text-slate-700 px-2 py-1 rounded hover:bg-slate-50 disabled:opacity-50"
									>
										{previewLoading && previewVersion?.id !== v.id ? "Loading..." : "Preview"}
									</button>
									{!isCurrent && !policy.is_builtin && (
										<button
											type="button"
											onClick={() => setRollbackTarget(v)}
											className="flex items-center gap-1 text-xs text-yellow-400 hover:text-yellow-300 px-2 py-1 rounded hover:bg-yellow-400/5"
										>
											<RotateCcw className="w-3 h-3" />
											Restore
										</button>
									)}
								</div>
							</div>

							{/* Preview */}
							{previewVersion?.id === v.id && (
								<div className="mt-3 pt-3 border-t border-slate-200">
									<p className="text-xs text-slate-500 mb-2">
										Config snapshot at v{v.version}
									</p>
									<pre className="text-xs text-slate-600 bg-slate-100 rounded p-2 overflow-auto max-h-40">
										{JSON.stringify(v.config_snapshot, null, 2)}
									</pre>
								</div>
							)}
						</div>
					);
				})}

				{versions.length === 0 && (
					<p className="text-sm text-slate-500 text-center py-8">
						No version history available
					</p>
				)}
			</div>

			{/* Rollback confirmation dialog */}
			{rollbackTarget && (
				<div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
					<div className="bg-white border border-slate-200 rounded-xl p-6 w-full max-w-md mx-4">
						<div className="flex items-center gap-3 mb-4">
							<AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0" />
							<h3 className="text-base font-semibold text-slate-900">
								Restore Version {rollbackTarget.version}?
							</h3>
						</div>
						<p className="text-sm text-slate-600 mb-4">
							This will restore the policy config from version{" "}
							<strong className="text-slate-900">
								{rollbackTarget.version}
							</strong>{" "}
							as the new current version. A new version entry will be created.
						</p>
						{policy.is_compulsory && (
							<div className="mb-4 p-3 rounded-lg bg-red-400/10 border border-red-400/20 text-xs text-red-300">
								This is a compulsory policy. Admins only.
							</div>
						)}
						<input
							type="text"
							value={rollbackNote}
							onChange={(e) => setRollbackNote(e.target.value)}
							placeholder="Optional: reason for rollback..."
							className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder-slate-400 mb-4"
						/>
						<div className="flex justify-end gap-3">
							<button
								type="button"
								onClick={() => {
									setRollbackTarget(null);
									setRollbackNote("");
								}}
								className="px-4 py-2 text-sm rounded-lg border border-slate-200 hover:bg-slate-50"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={handleRollback}
								disabled={rolling}
								className="px-4 py-2 text-sm rounded-lg bg-yellow-500/20 border border-yellow-500/40 text-yellow-300 hover:bg-yellow-500/30 disabled:opacity-50"
							>
								{rolling ? "Restoring..." : "Restore Version"}
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
