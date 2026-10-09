"use client";

import { ExternalLink, Radio, X } from "lucide-react";
import React from "react";

interface ExecutionPanelHeaderProps {
	graphName: string;
	dbExecutionId: string | null;
	onClose: () => void;
	onOpenEnhancedViewer: () => void;
}

export default function ExecutionPanelHeader({
	graphName,
	dbExecutionId,
	onClose,
	onOpenEnhancedViewer,
}: ExecutionPanelHeaderProps) {
	return (
		<div className="border-b border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)]/70 px-4 py-3 backdrop-blur-sm">
			<div className="flex items-center justify-between gap-3">
				<div className="flex items-center gap-2.5 min-w-0">
					<div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-accent)]">
						<Radio className="h-3.5 w-3.5" />
					</div>
					<div className="min-w-0">
						<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
							Execution
						</p>
						<h2 className="text-sm font-semibold text-[color:var(--color-text-primary)] truncate">
							{graphName || "Workflow Execution"}
						</h2>
					</div>
				</div>
				<div className="flex items-center gap-2 shrink-0">
					{dbExecutionId && (
						<button
							data-tutorial="enhanced-view-btn"
							onClick={onOpenEnhancedViewer}
							className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/50 px-2.5 text-xs font-semibold text-[color:var(--color-text-muted)] transition-colors hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-[color:var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
							title="Open in Enhanced Viewer"
							type="button"
						>
							<ExternalLink className="h-3.5 w-3.5" />
							Enhanced View
						</button>
					)}
					<button
						onClick={onClose}
						className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-muted)] transition-all hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-[color:var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
						type="button"
					>
						<X className="h-4 w-4" />
					</button>
				</div>
			</div>
		</div>
	);
}
