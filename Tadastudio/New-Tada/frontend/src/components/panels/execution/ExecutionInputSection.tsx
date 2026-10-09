"use client";

import {
	ChevronDown,
	ChevronRight,
	Maximize2,
	MessageSquare,
	Minimize2,
	RefreshCw,
} from "lucide-react";
import React from "react";
import ExecutionControlButtons from "./ExecutionControlButtons";
import ExecutionFileUpload from "./ExecutionFileUpload";
import ExecutionTextInput from "./ExecutionTextInput";

interface PauseInfo {
	prompt?:
		| string
		| {
				type?: string;
				inbox_address?: string;
				prompt?: string;
		  };
}

interface ExecutionInputSectionProps {
	isPaused: boolean;
	isManualPause: boolean;
	isInputSectionExpanded: boolean;
	isInputExpanded: boolean;
	isExecuting: boolean;
	isResumingCheckpoint: boolean;
	hasFileReadNode: boolean;
	hasRawFileReadNode: boolean;
	hasMCPServerNode: boolean;
	inputMessage: string;
	inputFile: File | null;
	textareaRows: number;
	pauseInfo: PauseInfo | null;
	graphName: string;
	onToggleInputSection: () => void;
	onToggleInputExpanded: () => void;
	onMessageChange: (message: string) => void;
	onFileSelect: (file: File | null) => void;
	onStartExecution: () => void;
	onResume: () => void;
	onStartNewWorkflow: () => void;
}

export default function ExecutionInputSection({
	isPaused,
	isManualPause,
	isInputSectionExpanded,
	isInputExpanded,
	isExecuting,
	isResumingCheckpoint,
	hasFileReadNode,
	hasRawFileReadNode,
	hasMCPServerNode,
	inputMessage,
	inputFile,
	textareaRows,
	pauseInfo,
	graphName,
	onToggleInputSection,
	onToggleInputExpanded,
	onMessageChange,
	onFileSelect,
	onStartExecution,
	onResume,
	onStartNewWorkflow,
}: ExecutionInputSectionProps) {
	// Check if this is an email checkpoint or agent review and hide input section if so
	const promptObj =
		typeof pauseInfo?.prompt === "object" ? pauseInfo.prompt : null;
	const isEmailCheckpoint =
		promptObj?.type === "email_checkpoint" || promptObj?.inbox_address;
	const isAgentReview = promptObj?.type === "agent_review";

	// Hide input section for email checkpoints, manual pauses, and agent reviews when paused
	// Agent reviews are handled by AgentReviewSection component
	if (
		(isPaused && isEmailCheckpoint) ||
		(isPaused && isManualPause) ||
		(isPaused && isAgentReview)
	) {
		return null;
	}

	const handleMessageChange = (message: string) => {
		onMessageChange(message);
		// Clear file if message is entered (except when MCP server or FILE_READ is present - allow both)
		if (message && inputFile && !hasMCPServerNode && !hasFileReadNode) {
			onFileSelect(null);
		}
	};

	const handleFileSelect = (file: File | null) => {
		onFileSelect(file);
		// Clear message if file is selected (except when MCP server or FILE_READ is present - allow both)
		if (file && inputMessage && !hasMCPServerNode && !hasFileReadNode) {
			onMessageChange("");
		}
	};

	return (
		<div data-tutorial="execution-input" className="px-4 py-3 border-b border-[color:var(--color-border)]/50">
			<div className="overflow-hidden rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 backdrop-blur-sm">
				<div
					className={`flex items-center gap-3 px-4 py-3 ${isPaused ? "bg-[color:var(--color-warning-dark)]/20" : "bg-transparent"}`}
				>
					<button
						onClick={onToggleInputSection}
						className="flex flex-1 items-center justify-between text-left transition-colors focus-visible:outline-none"
						type="button"
					>
						<div className="flex items-center gap-2.5">
							<div
								className={`flex h-7 w-7 items-center justify-center rounded-lg border ${
									isPaused
										? "border-[color:var(--color-warning)]/35 bg-[color:var(--color-warning)]/12 text-[color:var(--color-warning)]"
										: "border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-accent)]"
								}`}
							>
								{isPaused ? (
									<RefreshCw className="h-3.5 w-3.5" />
								) : (
									<MessageSquare className="h-3.5 w-3.5" />
								)}
							</div>
							<div className="flex flex-col">
								<span
									className={`text-sm font-semibold ${isPaused ? "text-[color:var(--color-warning)]" : "text-[color:var(--color-text-primary)]"}`}
								>
									{isPaused
										? "Response Required"
										: hasFileReadNode || hasMCPServerNode
											? "Input Message or File"
											: "Input Message"}
								</span>
								{(isPaused || isInputSectionExpanded) && (
									<span className="text-xs text-[color:var(--color-text-secondary)]">
										{isPaused
											? "Provide context to resume the workflow."
											: "Send instructions or upload supporting context."}
									</span>
								)}
							</div>
						</div>
						{isInputSectionExpanded ? (
							<ChevronDown className="h-4 w-4 text-[color:var(--color-text-muted)]" />
						) : (
							<ChevronRight className="h-4 w-4 text-[color:var(--color-text-muted)]" />
						)}
					</button>
					{isInputSectionExpanded && (
						<button
							onClick={onToggleInputExpanded}
							className="flex h-7 w-7 items-center justify-center rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-muted)] transition-all hover:text-[color:var(--color-text-primary)] hover:border-[rgba(var(--color-primary-rgb),0.35)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.50)]"
							title={isInputExpanded ? "Minimize input" : "Maximize input"}
							type="button"
						>
							{isInputExpanded ? (
								<Minimize2 className="h-4 w-4" />
							) : (
								<Maximize2 className="h-4 w-4" />
							)}
						</button>
					)}
				</div>

				{isInputSectionExpanded && (
					<div
						className={`space-y-4 px-5 pb-5 ${
							isPaused
								? "bg-[color:var(--color-warning-dark)]/10"
								: "bg-[color:var(--color-bg-secondary)]/50"
						}`}
					>
						{!isPaused && (
							<ExecutionFileUpload
								inputFile={inputFile}
								isExecuting={isExecuting}
								hasFileReadNode={hasFileReadNode}
								usePersistentStorage={hasRawFileReadNode || hasMCPServerNode}
								graphName={graphName}
								onFileSelectAction={handleFileSelect}
							/>
						)}

						<ExecutionTextInput
							inputMessage={inputMessage}
							isInputExpanded={isInputExpanded}
							isExecuting={isResumingCheckpoint || (isExecuting && !isPaused)}
							textareaRows={textareaRows}
							onMessageChange={handleMessageChange}
							onStartExecution={onStartExecution}
							onToggleExpanded={onToggleInputExpanded}
						/>

						<ExecutionControlButtons
							isPaused={isPaused}
							isExecuting={isExecuting}
							isResumingCheckpoint={isResumingCheckpoint}
							hasFileReadNode={hasFileReadNode}
							inputMessage={inputMessage}
							inputFile={inputFile}
							onStartExecution={onStartExecution}
							onResume={onResume}
							onStartNewWorkflow={onStartNewWorkflow}
						/>
					</div>
				)}
			</div>
		</div>
	);
}
