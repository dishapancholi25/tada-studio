"use client";

import { AlertTriangle, ArrowLeft, Save } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { syncService } from "@/services/graphSyncService";
import { useGraphStore } from "@/stores/graphStore";
import type { TypedGraphChange } from "@/types/graphChanges";

interface HistoricalVersionBannerProps {
	workflowId?: string;
}

export function HistoricalVersionBanner({
	workflowId,
}: HistoricalVersionBannerProps) {
	const isHistorical = useGraphStore((s) => s.isHistoricalVersion);
	const loadedVersion = useGraphStore((s) => s.loadedVersion);
	const router = useRouter();
	const [showSaveConfirm, setShowSaveConfirm] = useState(false);

	if (!isHistorical) return null;

	const handleReturnToLatest = () => {
		if (!workflowId) return;
		// Navigate without version params to load latest
		router.push(`/workflow/${encodeURIComponent(workflowId)}`);
	};

	const handleSaveAsLatest = async () => {
		// Exit historical mode so sync can run
		useGraphStore.getState().exitHistoricalVersion();
		// Mark store as dirty so sync picks it up
		useGraphStore.getState().setIsDirty(true);
		const store = useGraphStore.getState();
		if (store.localChanges.length === 0) {
			// Push a synthetic change so sync has something to send
			const syntheticChange: TypedGraphChange = {
				type: "UPDATE_NODE",
				timestamp: Date.now(),
				data: {
					nodeId: "__version_restore__",
					updates: {},
				},
			};
			store.localChanges.push(syntheticChange);
		}
		await syncService.forceSync();
		setShowSaveConfirm(false);
	};

	return (
		<>
			<div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_62%,#f59e0b_175%)] px-4 py-2.5 text-slate-900">
				<div className="flex items-center gap-2.5">
					<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-orange-600">
						<AlertTriangle className="h-4 w-4" />
					</div>
					<span className="text-sm font-medium">
						Viewing version {loadedVersion} — Auto-save is disabled.
					</span>
				</div>
				<div className="flex items-center gap-2">
					<button
						onClick={handleReturnToLatest}
						className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900"
					>
						<ArrowLeft className="h-3.5 w-3.5" />
						Return to latest
					</button>
					<button
						onClick={() => setShowSaveConfirm(true)}
						className="flex items-center gap-1.5 rounded-lg border border-orange-500 bg-orange-500 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
					>
						<Save className="h-3.5 w-3.5" />
						Save as latest
					</button>
				</div>
			</div>

			{showSaveConfirm && (
				<div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="relative mx-4 w-full max-w-md overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
						<div className="mb-4 flex items-center gap-3">
							<div className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_58%,#f59e0b_170%)] text-orange-600">
								<AlertTriangle className="h-5 w-5" />
							</div>
							<h3 className="text-lg font-semibold text-slate-900">
								Overwrite latest version?
							</h3>
						</div>
						<p className="mb-6 text-sm leading-relaxed text-slate-600">
							This will save version {loadedVersion} as the new latest version
							of this workflow. The current latest version will become a
							historical version. This action cannot be undone.
						</p>
						<div className="flex justify-end gap-3">
							<button
								onClick={() => setShowSaveConfirm(false)}
								className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900"
							>
								Cancel
							</button>
							<button
								onClick={handleSaveAsLatest}
								className="rounded-lg border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
							>
								Save as latest
							</button>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
