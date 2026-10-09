"use client";

import { AlertTriangle, Download, GitMerge, Upload } from "lucide-react";
import { useGraphStore } from "@/stores/graphStore";

/**
 * PHASE 5: Conflict Resolution Dialog
 *
 * Displays when a conflict is detected between local changes and server state.
 * Allows user to choose resolution strategy:
 * - Keep Local: Overwrite server with local changes
 * - Use Server: Discard local changes, use server state
 * - Merge: Attempt automatic merge (simple implementation)
 */
export function ConflictResolutionDialog() {
	const hasConflict = useGraphStore((state) => state.hasConflict);
	const conflictData = useGraphStore((state) => state.conflictData);
	const resolveConflict = useGraphStore((state) => state.resolveConflict);
	const clearConflict = useGraphStore((state) => state.clearConflict);

	if (!hasConflict || !conflictData) {
		return null;
	}

	const handleResolve = (strategy: "keep-local" | "use-server" | "merge") => {
		resolveConflict(strategy);
	};

	return (
		<div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] flex items-center justify-center p-4">
			<div className="bg-[color:var(--color-bg-secondary)] border-2 border-[color:var(--color-border)] rounded-lg shadow-2xl max-w-2xl w-full p-6 animate-in fade-in duration-200">
				{/* Header */}
				<div className="flex items-start gap-4 mb-6">
					<div className="flex-shrink-0 w-12 h-12 rounded-full bg-yellow-500/20 flex items-center justify-center">
						<AlertTriangle className="w-6 h-6 text-yellow-500" />
					</div>
					<div>
						<h2 className="text-xl font-semibold text-[color:var(--color-text)] mb-1">
							Sync Conflict Detected
						</h2>
						<p className="text-sm text-[color:var(--color-text-muted)]">
							The graph has been modified both locally and on the server. Choose
							how to resolve:
						</p>
					</div>
				</div>

				{/* Conflict Details */}
				<div className="bg-[color:var(--color-surface)] rounded-lg p-4 mb-6 border border-[color:var(--color-border)]/30">
					<div className="grid grid-cols-2 gap-4 text-sm">
						<div>
							<div className="text-[color:var(--color-text-muted)] mb-1">
								Local Version
							</div>
							<div className="text-[color:var(--color-text)] font-mono">
								v{conflictData.localVersion}
							</div>
							<div className="text-[color:var(--color-accent)] mt-1">
								{conflictData.localChanges.length} unsaved change
								{conflictData.localChanges.length !== 1 ? "s" : ""}
							</div>
						</div>
						<div>
							<div className="text-[color:var(--color-text-muted)] mb-1">
								Server Version
							</div>
							<div className="text-[color:var(--color-text)] font-mono">
								v{conflictData.serverVersion}
							</div>
							<div className="text-[color:var(--color-text-muted)] mt-1">
								{conflictData.serverState?.nodes.length || 0} nodes,{" "}
								{conflictData.serverState?.edges.length || 0} edges
							</div>
						</div>
					</div>
				</div>

				{/* Resolution Options */}
				<div className="space-y-3 mb-6">
					{/* Keep Local */}
					<button
						onClick={() => handleResolve("keep-local")}
						className="w-full p-4 rounded-lg border-2 border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] bg-[color:var(--color-surface)] hover:bg-[color:var(--color-bg-secondary)] transition-all group text-left"
					>
						<div className="flex items-start gap-3">
							<div className="flex-shrink-0 w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
								<Upload className="w-5 h-5 text-blue-500" />
							</div>
							<div className="flex-1">
								<div className="font-semibold text-[color:var(--color-text)] mb-1 flex items-center gap-2">
									Keep Local Changes
									<span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-500">
										Recommended
									</span>
								</div>
								<div className="text-sm text-[color:var(--color-text-muted)]">
									Overwrite server with your local changes. Best if you made
									recent edits.
								</div>
							</div>
						</div>
					</button>

					{/* Use Server */}
					<button
						onClick={() => handleResolve("use-server")}
						className="w-full p-4 rounded-lg border-2 border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] bg-[color:var(--color-surface)] hover:bg-[color:var(--color-bg-secondary)] transition-all group text-left"
					>
						<div className="flex items-start gap-3">
							<div className="flex-shrink-0 w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
								<Download className="w-5 h-5 text-orange-500" />
							</div>
							<div className="flex-1">
								<div className="font-semibold text-[color:var(--color-text)] mb-1">
									Use Server State
								</div>
								<div className="text-sm text-[color:var(--color-text-muted)]">
									Discard local changes and use server version. Best if someone
									else made updates.
								</div>
								<div className="text-xs text-orange-500 mt-1">
									⚠️ Warning: Your {conflictData.localChanges.length} local
									change{conflictData.localChanges.length !== 1 ? "s" : ""} will
									be lost
								</div>
							</div>
						</div>
					</button>

					{/* Merge */}
					<button
						onClick={() => handleResolve("merge")}
						className="w-full p-4 rounded-lg border-2 border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] bg-[color:var(--color-surface)] hover:bg-[color:var(--color-bg-secondary)] transition-all group text-left"
					>
						<div className="flex items-start gap-3">
							<div className="flex-shrink-0 w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
								<GitMerge className="w-5 h-5 text-purple-500" />
							</div>
							<div className="flex-1">
								<div className="font-semibold text-[color:var(--color-text)] mb-1 flex items-center gap-2">
									Attempt Merge
									<span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-500">
										Experimental
									</span>
								</div>
								<div className="text-sm text-[color:var(--color-text-muted)]">
									Try to combine local and server changes automatically. May
									require manual review.
								</div>
							</div>
						</div>
					</button>
				</div>

				{/* Cancel */}
				<button
					onClick={() => clearConflict()}
					className="w-full py-2 text-sm text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] transition-colors"
				>
					Cancel (conflict will persist)
				</button>
			</div>
		</div>
	);
}
