"use client";

import {
	Check,
	ChevronDown,
	ChevronRight,
	Clock,
	Loader2,
	MessageSquare,
	Shield,
} from "lucide-react";
import { useState } from "react";
import type { ReviewInterruptPayload } from "@/types/review";

interface AgentReviewSectionProps {
	reviewPayload: ReviewInterruptPayload;
	executionId: string;
	threadId: string;
	graphName: string;
	onApprove: () => void;
	onOpenReviewDialog: () => void;
	isLoading: boolean;
}

export default function AgentReviewSection({
	reviewPayload,
	onApprove,
	onOpenReviewDialog,
	isLoading,
}: AgentReviewSectionProps) {
	const [isExpanded, setIsExpanded] = useState(true);
	const [isOutputExpanded, setIsOutputExpanded] = useState(false);

	// Truncate output for preview (3 lines / ~200 chars)
	const maxPreviewLength = 200;
	const outputPreview =
		reviewPayload.agent_output.length > maxPreviewLength
			? `${reviewPayload.agent_output.slice(0, maxPreviewLength)}...`
			: reviewPayload.agent_output;
	const hasMoreOutput = reviewPayload.agent_output.length > maxPreviewLength;

	return (
		<div className="px-6 py-4">
			<div className="overflow-hidden rounded-2xl border border-amber-500/30 bg-amber-500/5 shadow-[0_20px_55px_rgba(0,0,0,0.55)] backdrop-blur-sm">
				{/* Header */}
				<button
					onClick={() => setIsExpanded(!isExpanded)}
					className="flex w-full items-center gap-3 px-5 py-4 text-left transition-colors focus-visible:outline-none bg-amber-500/8"
					type="button"
				>
					<div className="flex flex-1 items-center justify-between">
						<div className="flex items-center gap-3">
							<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-amber-500/35 bg-amber-500/12 text-amber-400">
								<Shield className="h-4 w-4" />
							</div>
							<div className="flex flex-col gap-0.5">
								<span className="text-[0.6rem] capitalize text-amber-400/80">
									Review Required
								</span>
								<span className="text-sm font-semibold text-amber-300">
									Agent Output Awaiting Review
								</span>
								<div className="flex items-center gap-2 text-xs text-[color:var(--color-text-secondary)]">
									<span>{reviewPayload.node_name}</span>
									<span className="text-[color:var(--color-text-muted)]">
										•
									</span>
									<span className="flex items-center gap-1 text-amber-400/70">
										<Clock className="h-3 w-3" />
										Iteration {reviewPayload.current_iteration}/
										{reviewPayload.max_iterations}
									</span>
								</div>
							</div>
						</div>
						{isExpanded ? (
							<ChevronDown className="h-4 w-4 text-amber-400/60" />
						) : (
							<ChevronRight className="h-4 w-4 text-amber-400/60" />
						)}
					</div>
				</button>

				{/* Expanded Content */}
				{isExpanded && (
					<div className="space-y-4 px-5 pb-5 bg-amber-500/3">
						{/* Review Criteria */}
						{reviewPayload.review_prompt && (
							<div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
								<p className="text-[0.6rem] capitalize text-amber-400/60 mb-1">
									Review Criteria
								</p>
								<p className="text-sm text-[color:var(--color-text-secondary)]">
									{reviewPayload.review_prompt}
								</p>
							</div>
						)}

						{/* Output Preview */}
						<div className="rounded-xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/30">
							<button
								onClick={() => setIsOutputExpanded(!isOutputExpanded)}
								className="flex w-full items-center justify-between px-4 py-3 text-left focus-visible:outline-none"
								type="button"
							>
								<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Agent Output
								</span>
								{hasMoreOutput && (
									<span className="flex items-center gap-1 text-xs text-amber-400/70">
										{isOutputExpanded ? "Collapse" : "Expand"}
										{isOutputExpanded ? (
											<ChevronDown className="h-3 w-3" />
										) : (
											<ChevronRight className="h-3 w-3" />
										)}
									</span>
								)}
							</button>
							<div className="px-4 pb-4">
								<p
									className={`text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap ${
										!isOutputExpanded && hasMoreOutput ? "line-clamp-3" : ""
									}`}
								>
									{isOutputExpanded
										? reviewPayload.agent_output
										: outputPreview}
								</p>
							</div>
						</div>

						{/* Action Buttons */}
						<div className="flex items-center gap-3">
							<button
								onClick={onApprove}
								disabled={isLoading}
								className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
									bg-gradient-to-r from-emerald-500 to-[#0DA931]
									hover:from-emerald-400 hover:to-[#0DA931]
									disabled:from-[color:var(--color-border)] disabled:to-[color:var(--color-border)]
									text-white font-semibold text-sm
									transition-all duration-200
									hover:shadow-[0_0_25px_rgba(16,185,129,0.5)]
									disabled:opacity-50 disabled:cursor-not-allowed
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50"
								type="button"
							>
								{isLoading ? (
									<>
										<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
										Approving...
									</>
								) : (
									<>
										<Check className="h-4 w-4" />
										Approve
									</>
								)}
							</button>

							<button
								onClick={onOpenReviewDialog}
								disabled={isLoading}
								className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
									border border-amber-500/40 bg-amber-500/10
									hover:bg-amber-500/20 hover:border-amber-500/60
									text-amber-300 font-semibold text-sm
									transition-all duration-200
									disabled:opacity-50 disabled:cursor-not-allowed
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500/50"
								type="button"
							>
								<MessageSquare className="h-4 w-4" />
								Review & Revise
							</button>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}
