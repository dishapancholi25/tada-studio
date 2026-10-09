"use client";

import { Activity, Shield } from "lucide-react";
import React from "react";

interface PauseInfo {
	prompt?:
		| string
		| {
				type?: string;
				inbox_address?: string;
				prompt?: string;
		  };
}

interface ExecutionPauseStatusProps {
	isPaused: boolean;
	isPausePending: boolean;
	isStopping: boolean;
	hasStopped: boolean;
	stoppedAt: string | null;
	pauseInfo: PauseInfo | null;
	isManualPause: boolean;
	manualPauseInfo: { prompt?: string } | null;
}

export default function ExecutionPauseStatus({
	isPaused,
	isPausePending,
	isStopping,
	hasStopped,
	stoppedAt,
	pauseInfo,
	isManualPause,
	manualPauseInfo,
}: ExecutionPauseStatusProps) {
	if (!isPaused && !isPausePending && !isStopping && !hasStopped) {
		return null;
	}

	if (hasStopped) {
		return (
			<div className="mx-6 my-4 rounded-2xl border border-red-500/50 bg-red-500/12 px-5 py-4 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
				<div className="flex items-start gap-3">
					<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-red-500/35 bg-red-500/12">
						<Activity className="h-4 w-4 text-red-600" />
					</div>
					<div className="flex-1 space-y-1">
						<div className="text-[0.6rem] capitalize text-red-600/70">
							Status
						</div>
						<div className="text-sm font-semibold text-red-600">
							Execution Stopped
						</div>
						{stoppedAt && (
							<div className="text-xs text-red-600/70">
								Stopped at {new Date(stoppedAt).toLocaleTimeString()}
							</div>
						)}
						<div className="text-xs text-red-600/70">
							Start a new workflow to run again.
						</div>
					</div>
				</div>
			</div>
		);
	}

	if (isStopping) {
		return (
			<div className="mx-6 my-4 rounded-2xl border border-red-500/50 bg-red-500/12 px-5 py-4 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
				<div className="flex items-start gap-3">
					<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-red-500/35 bg-red-500/12">
						<Activity className="h-4 w-4 animate-pulse text-red-600" />
					</div>
					<div className="flex-1 space-y-1">
						<div className="text-[0.6rem] capitalize text-red-600/70">
							Status
						</div>
						<div className="text-sm font-semibold text-red-600">
							Stopping Execution…
						</div>
						<div className="text-xs text-red-600/70">
							Cancelling any active nodes. This may take a moment.
						</div>
					</div>
				</div>
			</div>
		);
	}

	if (isPausePending && !isPaused) {
		return (
			<div className="mx-6 my-4 rounded-2xl border border-[color:var(--color-warning)]/50 bg-[color:var(--color-warning)]/12 px-5 py-4 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
				<div className="flex items-start gap-3">
					<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[color:var(--color-warning)]/35 bg-[color:var(--color-warning)]/12">
						<Activity className="h-4 w-4 animate-pulse text-[color:var(--color-warning)]" />
					</div>
					<div className="flex-1 space-y-1">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-warning)]/70">
							Status
						</div>
						<div className="text-sm font-semibold text-[color:var(--color-warning)]">
							Pause Requested
						</div>
						<div className="text-xs text-[color:var(--color-warning)]/70">
							The workflow will pause after the current node completes.
						</div>
					</div>
				</div>
			</div>
		);
	}

	if (!isPaused) return null;

	if (isManualPause) {
		return (
			<div className="mx-6 my-4 rounded-2xl border border-[rgba(var(--color-primary-rgb),0.50)] bg-[rgba(var(--color-primary-rgb),0.20)] px-5 py-4 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
				<div className="flex items-start gap-3">
					<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)]">
						<Activity className="h-4 w-4 text-[color:var(--color-accent)]" />
					</div>
					<div className="flex-1 space-y-1">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
							Checkpoint
						</div>
						<div className="text-sm font-semibold text-[color:var(--color-primary)]">
							Execution Paused
						</div>
						<div className="text-xs text-[color:var(--color-text-secondary)]">
							{manualPauseInfo?.prompt ||
								"Workflow paused by user. Press Resume to continue."}
						</div>
						<div className="text-xs text-[color:var(--color-text-secondary)]">
							The workflow will resume from the next node when you press Resume.
						</div>
					</div>
				</div>
			</div>
		);
	}

	const promptObj =
		typeof pauseInfo?.prompt === "object" ? pauseInfo.prompt : null;
	const isEmailCheckpoint =
		promptObj?.type === "email_checkpoint" || promptObj?.inbox_address;
	const isAgentReview = promptObj?.type === "agent_review";

	// Agent Review Banner - amber styling
	if (isAgentReview) {
		return (
			<div className="mx-6 my-4 rounded-2xl border border-amber-500/50 bg-amber-500/12 px-5 py-4 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
				<div className="flex items-start gap-3">
					<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-amber-500/35 bg-amber-500/12">
						<Shield className="h-4 w-4 text-amber-400" />
					</div>
					<div className="flex-1 space-y-1">
						<div className="text-[0.6rem] capitalize text-amber-400/70">
							Review
						</div>
						<div className="text-sm font-semibold text-amber-700">
							Awaiting Approval
						</div>
						<div className="text-xs text-amber-700/70">
							Review the agent output and approve or request revisions.
						</div>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="mx-6 my-4 rounded-2xl border border-[rgba(var(--color-primary-rgb),0.50)] bg-[rgba(var(--color-primary-rgb),0.20)] px-5 py-4 shadow-[0_20px_55px_rgba(0,0,0,0.35)]">
			<div className="flex items-start gap-3">
				<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)]">
					<Activity className="h-4 w-4 text-[color:var(--color-accent)]" />
				</div>
				<div className="flex-1 space-y-1">
					<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
						Checkpoint
					</div>
					<div className="text-sm font-semibold text-[color:var(--color-primary)]">
						Execution Paused
					</div>
					<div className="text-xs text-[color:var(--color-text-secondary)]">
						{isEmailCheckpoint ? (
							<div className="space-y-2">
								<div>Waiting for email response</div>
								{promptObj?.inbox_address && (
									<div className="font-mono text-[11px] rounded-lg border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.25)] px-3 py-2 break-all">
										{promptObj.inbox_address}
									</div>
								)}
							</div>
						) : typeof pauseInfo?.prompt === "string" ? (
							pauseInfo?.prompt
						) : (
							pauseInfo?.prompt?.prompt || ""
						)}
					</div>
					{!isEmailCheckpoint && (
						<div className="text-xs text-[color:var(--color-text-secondary)]">
							Enter a response below and choose Resume Workflow when you are
							ready.
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
