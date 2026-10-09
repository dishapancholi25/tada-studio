"use client";

import { formatDistanceToNow } from "date-fns";
import { Check, Clock, History, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useGraphStore } from "@/stores/graphStore";

interface VersionEntry {
	id: string;
	version: number;
	is_latest: boolean;
	created_by: string | null;
	created_at: string | null;
	file_hash: string | null;
	size_bytes: number | null;
}

interface VersionHistoryPanelProps {
	workflowId: string;
	isOpen: boolean;
	onClose: () => void;
}

export function VersionHistoryPanel({
	workflowId,
	isOpen,
	onClose,
}: VersionHistoryPanelProps) {
	const [versions, setVersions] = useState<VersionEntry[]>([]);
	const [loading, setLoading] = useState(false);
	const router = useRouter();
	const loadedVersion = useGraphStore((s) => s.loadedVersion);
	const isHistorical = useGraphStore((s) => s.isHistoricalVersion);

	const fetchVersions = useCallback(async () => {
		if (!workflowId || !isOpen) return;
		setLoading(true);
		try {
			const res = await api.getWorkflowVersions(workflowId);
			if (res.success) {
				setVersions(res.versions);
			}
		} catch {
			// Silently ignore
		} finally {
			setLoading(false);
		}
	}, [workflowId, isOpen]);

	useEffect(() => {
		fetchVersions();
	}, [fetchVersions]);

	const handleLoadVersion = (v: VersionEntry) => {
		if (v.is_latest) {
			router.push(`/workflow/${encodeURIComponent(workflowId)}`);
		} else {
			router.push(
				`/workflow/${encodeURIComponent(workflowId)}?version=${v.version}&graph_definition_id=${v.id}`,
			);
		}
		onClose();
	};

	if (!isOpen) return null;

	const currentVersion = isHistorical ? loadedVersion : null;

	return (
		<div className="fixed inset-0 z-[9998] flex items-start justify-end">
			<div className="h-full w-full" onClick={onClose} />
			<div className="absolute right-0 top-12 z-[9999] flex h-[calc(100vh-3rem)] w-80 flex-col border-l border-slate-200 bg-white shadow-[0_22px_56px_rgba(15,23,42,0.14)]">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				<div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
					<div className="flex items-center gap-2">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<History className="h-5 w-5 text-orange-600" />
						</div>
						<h3 className="text-sm font-semibold text-slate-900">
							Version History
						</h3>
					</div>
					<button
						onClick={onClose}
						className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white hover:text-slate-900"
					>
						<X className="h-4 w-4" />
					</button>
				</div>

				<div className="flex-1 overflow-y-auto">
					{loading ? (
						<div className="flex items-center justify-center py-12">
							<div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500" />
						</div>
					) : versions.length === 0 ? (
						<div className="px-4 py-8 text-center text-sm text-slate-500">
							No versions found
						</div>
					) : (
						<div className="space-y-2 p-3">
							{versions.map((v) => {
								const isActive =
									(currentVersion === v.version && !v.is_latest) ||
									(v.is_latest && !isHistorical);

								return (
									<button
										key={v.id}
										onClick={() => handleLoadVersion(v)}
										className={`group flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left transition-all hover:border-orange-400 hover:bg-white ${
											isActive
												? "border-orange-400 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_72%,#f59e0b_185%)]"
												: "border-slate-200 bg-white"
										}`}
									>
										<div
											className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border text-xs font-mono font-semibold ${
												v.is_latest
													? "border-[#0DA931] bg-white text-[#0DA931]"
													: isActive
														? "border-orange-400 bg-white text-orange-700"
														: "border-slate-200 bg-white text-slate-600 group-hover:border-orange-400 group-hover:text-slate-900"
											}`}
										>
											{v.version}
										</div>
										<div className="min-w-0 flex-1">
											<div className="flex items-center gap-2">
												<span className="text-sm font-medium text-slate-900 group-hover:text-slate-900">
													v{v.version}
												</span>
												{v.is_latest && (
													<span className="flex items-center gap-1 rounded-full border border-[#0DA931] bg-white px-1.5 py-0.5 text-[10px] font-medium text-[#0DA931]">
														<Check className="h-2.5 w-2.5" />
														Latest
													</span>
												)}
												{isActive && !v.is_latest && (
													<span className="rounded-full border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-orange-700">
														Viewing
													</span>
												)}
											</div>
											<div className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
												<Clock className="h-3 w-3" />
												{v.created_at
													? formatDistanceToNow(new Date(v.created_at), {
															addSuffix: true,
														})
													: "Unknown"}
											</div>
											{v.created_by && (
												<div className="mt-0.5 truncate text-xs text-slate-500">
													by {v.created_by}
												</div>
											)}
										</div>
									</button>
								);
							})}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
