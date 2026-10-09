"use client";

import {
	AlertCircle,
	Bot,
	Check,
	Clock,
	FileText,
	History,
	Loader2,
	MessageSquare,
	Shield,
	X,
	XCircle,
} from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import StyledMarkdown from "@/components/utils/StyledMarkdown";
import type {
	ReviewInterruptPayload,
	ReviewResumeResponse,
} from "@/types/review";

interface ReviewResumeDialogProps {
	execution: {
		execution_id: string;
		thread_id: string;
		graph_name: string;
	};
	reviewPayload: ReviewInterruptPayload;
	onClose: () => void;
	onResume: (executionId: string, response: ReviewResumeResponse) => void;
}

export default function ReviewResumeDialog({
	execution,
	reviewPayload,
	onClose,
	onResume,
}: ReviewResumeDialogProps) {
	const [feedback, setFeedback] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [activeTab, setActiveTab] = useState<"current" | "history">("current");
	const [validationError, setValidationError] = useState<string | null>(null);

	const hasFeedback = feedback.trim().length > 0;
	const hasHistory = reviewPayload.review_history.length > 0;

	const handleApprove = useCallback(() => {
		setValidationError(null);
		setIsLoading(true);
		onResume(execution.execution_id, { approved: true });
	}, [execution.execution_id, onResume]);

	const handleReject = useCallback(() => {
		if (!feedback.trim()) {
			setValidationError(
				"Please provide feedback explaining why the output was rejected.",
			);
			return;
		}
		setValidationError(null);
		setIsLoading(true);
		onResume(execution.execution_id, {
			approved: false,
			feedback: feedback.trim(),
		});
	}, [execution.execution_id, feedback, onResume]);

	const handleFeedbackChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setFeedback(e.target.value);
			// Clear validation error when user starts typing
			if (validationError) {
				setValidationError(null);
			}
		},
		[validationError],
	);

	return (
		<div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
			{/* Backdrop */}
			<div
				className="absolute inset-0 bg-black/50 backdrop-blur-sm"
				onClick={onClose}
				onKeyDown={(e) => e.key === "Escape" && onClose()}
			/>

			{/* Modal Container */}
			<div
				className="relative bg-[color:var(--color-surface)]
                     backdrop-blur-2xl rounded-[24px] border border-[color:var(--color-border)]
                     shadow-xl
                     max-w-5xl w-full h-[85vh] flex flex-col overflow-hidden"
			>
				{/* Header */}
				<div
					className="relative px-6 py-5 border-b border-[color:var(--color-border)]
                       bg-[color:var(--color-bg-secondary)]"
				>
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-4">
							<div
								className="p-2.5 bg-gradient-to-br from-amber-500/20 to-amber-600/20
                             rounded-xl border border-amber-500/30"
							>
								<Shield className="w-5 h-5 text-amber-500" />
							</div>
							<div>
								<h3 className="text-lg font-bold text-[color:var(--color-text-primary)] flex items-center gap-3">
									Review Agent Output
									<span
										className="px-2.5 py-0.5 text-[11px] font-medium whitespace-nowrap
                               bg-amber-500/18 text-amber-600 rounded-full border border-amber-500/30"
									>
										{reviewPayload.review_mode === "human"
											? "Human Review"
											: "LLM Review"}
									</span>
								</h3>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1 flex items-center gap-2">
									<span className="font-medium">{execution.graph_name}</span>
									<span className="text-[color:var(--color-text-muted)]">
										•
									</span>
									<span>{reviewPayload.node_name}</span>
									<span className="text-[color:var(--color-text-muted)]">
										•
									</span>
									<span className="flex items-center gap-1 font-mono">
										<Clock className="w-3 h-3" />
										Iteration {reviewPayload.current_iteration}/
										{reviewPayload.max_iterations}
									</span>
								</p>
							</div>
						</div>

						<button
							onClick={onClose}
							className="p-2 text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-slate-50
                       rounded-lg transition-all duration-200"
						>
							<X className="w-5 h-5" />
						</button>
					</div>
				</div>

				{/* Content */}
				<div className="flex-1 flex overflow-hidden">
					{/* Left Panel - Agent Output with Tabs */}
					<div className="flex-1 flex flex-col border-r border-[color:var(--color-border)]/50">
						{/* Tab Navigation */}
						<div className="px-6 py-3 border-b border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/30">
							<div className="flex items-center gap-2">
								<button
									onClick={() => setActiveTab("current")}
									className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200
										${
											activeTab === "current"
												? "border border-[rgba(var(--color-primary-rgb),0.6)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.18)] via-[rgba(var(--color-primary-rgb),0.08)] to-transparent text-[color:var(--color-primary)]"
												: "border border-transparent text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-slate-50"
										}`}
								>
									<Bot className="w-3.5 h-3.5" />
									Current Output
								</button>
								{hasHistory && (
									<button
										onClick={() => setActiveTab("history")}
										className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-all duration-200
											${
												activeTab === "history"
													? "border border-[rgba(var(--color-primary-rgb),0.6)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.18)] via-[rgba(var(--color-primary-rgb),0.08)] to-transparent text-[color:var(--color-primary)]"
													: "border border-transparent text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-slate-50"
											}`}
									>
										<History className="w-3.5 h-3.5" />
										History ({reviewPayload.review_history.length})
									</button>
								)}
							</div>
						</div>

						{/* Tab Content */}
						<div className="flex-1 p-6 overflow-auto bg-[color:var(--color-bg-secondary)]/20 custom-scrollbar">
							{activeTab === "current" ? (
								// Current Output
								reviewPayload.agent_output ? (
									<StyledMarkdown content={reviewPayload.agent_output} />
								) : (
									<div className="flex flex-col items-center justify-center h-full text-[color:var(--color-text-muted)]">
										<FileText className="w-12 h-12 mb-2 opacity-30" />
										<p className="text-sm">No output available</p>
									</div>
								)
							) : (
								// History List
								<div className="space-y-4">
									{reviewPayload.review_history.map((entry, idx) => (
										<div
											key={idx}
											className="rounded-xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/30 p-4 space-y-3"
										>
											{/* Header with iteration badge */}
											<div className="flex items-center justify-between">
												<span
													className="text-[11px] font-medium px-2.5 py-0.5 rounded-full whitespace-nowrap
																 border border-amber-500/30 bg-amber-500/12 text-amber-700"
												>
													Iteration {entry.iteration}
												</span>
												<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
													{entry.reviewer_type}
												</span>
											</div>

											{/* Output preview */}
											<div className="text-sm text-[color:var(--color-text-secondary)] border-l-2 border-[color:var(--color-border)]/50 pl-3">
												<p className="line-clamp-4">{entry.agent_output}</p>
											</div>

											{/* Feedback */}
											<div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3">
												<span className="text-[0.6rem] capitalize text-red-400 block mb-1">
													Feedback Given
												</span>
												<p className="text-sm text-red-600">{entry.feedback}</p>
											</div>
										</div>
									))}
								</div>
							)}
						</div>

						{/* Review Criteria */}
						{reviewPayload.review_prompt && (
							<div className="px-6 py-4 border-t border-[color:var(--color-border)]/30 bg-amber-500/5">
								<div className="flex items-start gap-3">
									<AlertCircle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
									<div>
										<h5 className="text-[0.6rem] capitalize text-amber-700 mb-1.5 font-semibold">
											Review Criteria
										</h5>
										<p className="text-xs text-[color:var(--color-text-secondary)]">
											{reviewPayload.review_prompt}
										</p>
									</div>
								</div>
							</div>
						)}
					</div>

					{/* Right Panel - Feedback Input */}
					<div className="w-2/5 flex flex-col">
						<div className="px-6 py-3 border-b border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/30">
							<div className="flex items-center gap-2">
								<MessageSquare className="w-4 h-4 text-amber-400" />
								<h4 className="text-xs capitalize text-[color:var(--color-text-secondary)] font-semibold">
									Revision Feedback
								</h4>
							</div>
						</div>

						<div className="flex-1 p-4 overflow-auto bg-[color:var(--color-bg-secondary)]/20">
							<textarea
								value={feedback}
								onChange={handleFeedbackChange}
								placeholder="Enter feedback to request changes from the agent..."
								className="w-full h-full p-4 bg-[color:var(--color-surface)]/50 border border-[color:var(--color-border)]/50
                           rounded-xl text-sm text-slate-700 placeholder-gray-500
                           focus:outline-none focus:border-amber-500/50 focus:bg-[color:var(--color-surface)]/70
                           focus:ring-2 focus:ring-amber-500/20 transition-all duration-200
                           resize-none custom-scrollbar"
							/>
						</div>

						<div className="px-4 py-3 border-t border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/30">
							{validationError ? (
								<p className="text-xs text-red-400 flex items-center gap-1.5">
									<AlertCircle className="w-3.5 h-3.5" />
									{validationError}
								</p>
							) : hasFeedback ? (
								<p className="text-xs text-amber-400">
									Click Reject to send feedback, or clear to approve
								</p>
							) : (
								<p className="text-xs text-[color:var(--color-text-muted)]">
									Leave empty to approve the output as-is
								</p>
							)}
						</div>
					</div>
				</div>

				{/* Footer Actions */}
				<div
					className="flex items-center justify-between px-6 py-4
                       bg-gradient-to-r from-[color:var(--color-bg-secondary)]/60 to-[color:var(--color-surface)]/60
                       backdrop-blur-sm border-t border-[color:var(--color-border)]/50"
				>
					<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
						Thread{" "}
						<span className="font-mono text-[color:var(--color-text-secondary)]">
							{execution.thread_id.slice(0, 8)}
						</span>
					</div>

					<div className="flex items-center gap-3">
						<button
							onClick={onClose}
							disabled={isLoading}
							className="px-4 py-2 bg-[color:var(--color-surface)]/40 hover:bg-[color:var(--color-surface)]/60
                       text-[color:var(--color-text-secondary)] hover:text-slate-900 rounded-lg
                       transition-all duration-200 font-medium text-sm
                       border border-[color:var(--color-border)]/60 hover:border-[color:var(--color-border)]
                       disabled:opacity-50 disabled:cursor-not-allowed"
						>
							Cancel
						</button>

						<button
							onClick={handleReject}
							disabled={isLoading || !hasFeedback}
							className="px-5 py-2 bg-red-500/20 hover:bg-red-500/30
                       text-red-600 rounded-lg transition-all duration-200
                       font-semibold text-sm flex items-center gap-2
                       border border-red-500/40 hover:border-red-500/60
                       disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-red-500/20 disabled:hover:border-red-500/40"
						>
							{isLoading ? (
								<Loader2 className="w-4 h-4 animate-spin" />
							) : (
								<XCircle className="w-4 h-4" />
							)}
							{isLoading ? "Submitting..." : "Reject"}
						</button>

						<button
							onClick={handleApprove}
							disabled={isLoading || hasFeedback}
							className={`px-5 py-2 rounded-lg transition-all duration-200
                       font-semibold text-sm flex items-center gap-2
                       ${
													hasFeedback
														? "bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-muted)] border border-[color:var(--color-border)]/60 cursor-not-allowed"
														: "bg-gradient-to-r from-emerald-500 to-[#0DA931] hover:from-emerald-400 hover:to-[#0DA931] text-white hover:shadow-[0_0_25px_rgba(16,185,129,0.5)] hover:scale-105"
												}
                       disabled:opacity-50 disabled:hover:scale-100`}
						>
							{isLoading ? (
								<Loader2 className="w-4 h-4 animate-spin" />
							) : (
								<Check className="w-4 h-4" />
							)}
							{isLoading ? "Submitting..." : "Approve"}
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
