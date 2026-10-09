"use client";

import { Loader2, Play, RefreshCw } from "lucide-react";
import React from "react";

interface ExecutionControlButtonsProps {
	isPaused: boolean;
	isExecuting: boolean;
	isResumingCheckpoint: boolean;
	hasFileReadNode: boolean;
	inputMessage: string;
	inputFile: File | null;
	onStartExecution: () => void;
	onResume: () => void;
	onStartNewWorkflow: () => void;
}

export default function ExecutionControlButtons({
	isPaused,
	isExecuting,
	isResumingCheckpoint,
	hasFileReadNode,
	inputMessage,
	inputFile,
	onStartExecution,
	onResume,
	onStartNewWorkflow,
}: ExecutionControlButtonsProps) {
	const isInputValid = hasFileReadNode
		? inputMessage.trim() || inputFile
		: inputMessage.trim();

	if (isPaused) {
		return (
			<div className="mt-4 flex flex-col gap-3 md:flex-row">
				<button
					onClick={onResume}
					disabled={isResumingCheckpoint}
					className={`inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl px-6 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0DA931]/50 ${
						isResumingCheckpoint
							? "cursor-not-allowed border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-muted)]"
							: "bg-gradient-to-br from-[#0DA931] to-[#0DA931] text-white shadow-[0_15px_40px_rgba(13,169,49,0.35)] hover:from-[#0DA931] hover:to-[#0DA931] hover:-translate-y-0.5"
					}`}
					type="button"
				>
					{isResumingCheckpoint ? (
						<>
							<Loader2 className="w-4 h-4 animate-spin" />
							Resuming…
						</>
					) : (
						<>
							<Play className="w-4 h-4" />
							Resume Workflow
						</>
					)}
				</button>
				<button
					onClick={onStartNewWorkflow}
					disabled={isResumingCheckpoint}
					className={`inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl px-6 border text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.50)] ${
						isResumingCheckpoint
							? "cursor-not-allowed border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-muted)]"
							: "border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 text-slate-700 hover:border-[rgba(var(--color-primary-rgb),0.50)] hover:bg-[color:var(--color-surface)]/50"
					}`}
					type="button"
				>
					<RefreshCw className="w-4 h-4" />
					Start New Workflow
				</button>
			</div>
		);
	}

	return (
		<button
			data-tutorial="execution-start-btn"
			onClick={onStartExecution}
			disabled={!isInputValid || isExecuting}
			className={`mt-4 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl px-6 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] ${
				!isInputValid || isExecuting
					? "cursor-not-allowed border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-muted)]"
					: "bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] text-[color:var(--button-primary-text)] shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)] hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] hover:-translate-y-0.5"
			}`}
			type="button"
		>
			{isExecuting ? (
				<>
					<Loader2 className="w-4 h-4 animate-spin" />
					Executing…
				</>
			) : (
				<>
					<Play className="w-4 h-4" />
					Run Workflow
				</>
			)}
		</button>
	);
}
