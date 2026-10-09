"use client";

import type { GuardrailPolicyVersion } from "@/types/guardrail-policies";
import { useToast } from "@/contexts/ToastContext";
import * as guardrailsApi from "@/lib/guardrails-api";
import {
	Clock,
	Eye,
	History,
	RotateCcw,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface PolicyVersionHistoryProps {
	policyId: string;
	onPolicyRestored?: (updatedPolicy: import("@/types/guardrail-policies").GuardrailPolicy) => void;
}

export default function PolicyVersionHistory({
	policyId,
	onPolicyRestored,
}: PolicyVersionHistoryProps) {
	const { showSuccess, showError } = useToast();

	const [versions, setVersions] = useState<GuardrailPolicyVersion[]>([]);
	const [loading, setLoading] = useState(true);
	const [previewVersion, setPreviewVersion] =
		useState<GuardrailPolicyVersion | null>(null);
	const [restoreTarget, setRestoreTarget] =
		useState<GuardrailPolicyVersion | null>(null);
	const [restoring, setRestoring] = useState(false);

	const fetchVersions = useCallback(async () => {
		setLoading(true);
		try {
			const resp = await guardrailsApi.listPolicyVersions(policyId);
			setVersions(resp.versions || []);
		} catch (err) {
			console.error("Failed to load versions:", err);
			setVersions([]);
		} finally {
			setLoading(false);
		}
	}, [policyId]);

	useEffect(() => {
		fetchVersions();
	}, [fetchVersions]);

	const handlePreview = async (version: GuardrailPolicyVersion) => {
		try {
			const resp = await guardrailsApi.getPolicyVersion(
				policyId,
				version.id,
				version.version_number,
			);
			setPreviewVersion(resp.version);
		} catch (err) {
			console.error("Failed to load version detail:", err);
			showError("Failed to load version", "Could not fetch version details.");
		}
	};

	const handleRestore = async () => {
		if (!restoreTarget) return;
		setRestoring(true);
		try {
			const result = await guardrailsApi.rollbackPolicyVersion(policyId, restoreTarget.id);
			showSuccess(
				"Version restored",
				`Policy restored to v${restoreTarget.version_number}.`,
			);
			setRestoreTarget(null);
			fetchVersions();
			if (onPolicyRestored && result.policy) {
				onPolicyRestored(result.policy);
			}
		} catch (err) {
			console.error("Failed to rollback version:", err);
			showError("Restore failed", "Could not restore the selected version.");
		} finally {
			setRestoring(false);
		}
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center py-20">
				<div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500" />
			</div>
		);
	}

	if (versions.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-20 text-slate-500">
				<History className="mb-4 h-12 w-12 text-orange-600 opacity-80" />
				<p className="text-sm">No version history yet.</p>
				<p className="mt-1 text-xs text-slate-400">
					Save changes to create the first version.
				</p>
			</div>
		);
	}

	return (
		<div className="relative">
			{/* Versions table */}
			<div className="overflow-x-auto">
				<table className="w-full text-left text-sm">
					<thead>
						<tr className="border-b border-slate-200 bg-white text-xs text-slate-500">
							<th className="py-3 px-4 font-medium">Version</th>
							<th className="py-3 px-4 font-medium">Changed By</th>
							<th className="py-3 px-4 font-medium">Date</th>
							<th className="py-3 px-4 font-medium">Change Note</th>
							<th className="py-3 px-4 font-medium">Status</th>
							<th className="py-3 px-4 font-medium text-right">Actions</th>
						</tr>
					</thead>
					<tbody>
						{versions.map((v) => (
							<tr
								key={v.id}
								className="border-b border-slate-100 transition-colors hover:bg-white"
							>
								<td className="py-3 px-4 font-medium text-slate-900">
									v{v.version_number}
								</td>
								<td className="py-3 px-4 text-slate-600">
									{v.changed_by || "Unknown"}
								</td>
								<td className="py-3 px-4 text-slate-600">
									<span className="inline-flex items-center gap-1">
										<Clock className="w-3 h-3" />
										{v.created_at
											? new Date(v.created_at).toLocaleDateString(
													undefined,
													{
														year: "numeric",
														month: "short",
														day: "numeric",
														hour: "2-digit",
														minute: "2-digit",
													},
												)
											: "—"}
									</span>
								</td>
								<td className="max-w-[200px] truncate px-4 py-3 text-slate-500">
									{v.change_summary || "—"}
								</td>
								<td className="py-3 px-4">
									{v.is_current ? (
										<span className="inline-flex items-center rounded-full border border-[#0DA931] bg-white px-2 py-0.5 text-[10px] font-medium text-[#0DA931]">
											Current
										</span>
									) : (
										<span className="text-xs text-slate-400">—</span>
									)}
								</td>
								<td className="py-3 px-4">
									<div className="flex items-center justify-end gap-1">
										<button
											type="button"
											onClick={() => handlePreview(v)}
											className="rounded-md border border-transparent p-1.5 text-slate-400 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900"
											title="Preview config"
										>
											<Eye className="w-3.5 h-3.5" />
										</button>
										{!v.is_current && (
											<button
												type="button"
												onClick={() => setRestoreTarget(v)}
												className="rounded-md border border-transparent p-1.5 text-slate-400 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900"
												title="Restore this version"
											>
												<RotateCcw className="w-3.5 h-3.5" />
											</button>
										)}
									</div>
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>

			{/* Preview side panel */}
			{previewVersion && (
				<div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
					<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
					<div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
						<h3 className="text-sm font-semibold text-slate-900">
							Version {previewVersion.version_number} Config
						</h3>
						<button
							type="button"
							onClick={() => setPreviewVersion(null)}
							className="rounded-md border border-transparent p-1.5 text-slate-500 hover:border-orange-400 hover:bg-white hover:text-slate-900"
						>
							<X className="w-4 h-4" />
						</button>
					</div>
					{previewVersion.change_summary && (
						<div className="border-b border-slate-100 px-5 py-3 text-xs text-slate-500">
							{previewVersion.change_summary}
						</div>
					)}
					<div className="flex-1 overflow-y-auto p-5">
						<pre className="whitespace-pre-wrap rounded-lg border border-slate-200 bg-white p-4 font-mono text-xs text-slate-700">
							{previewVersion.config_snapshot
								? JSON.stringify(
										previewVersion.config_snapshot,
										null,
										2,
									)
								: "No config snapshot available."}
						</pre>
					</div>
				</div>
			)}

			{/* Restore confirmation dialog */}
			{restoreTarget && (
				<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<h2 className="mb-3 text-lg font-semibold text-slate-900">
							Restore Version
						</h2>
						<p className="mb-6 text-sm text-slate-600">
							This will create a new version with the configuration from v
							{restoreTarget.version_number}. The current version will remain
							in history.
						</p>
						<div className="flex justify-end gap-3">
							<button
								type="button"
								onClick={() => setRestoreTarget(null)}
								disabled={restoring}
								className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 hover:border-orange-400 hover:text-slate-900"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={handleRestore}
								disabled={restoring}
								className="rounded-lg border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-40"
							>
								{restoring ? "Restoring..." : "Restore"}
							</button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
