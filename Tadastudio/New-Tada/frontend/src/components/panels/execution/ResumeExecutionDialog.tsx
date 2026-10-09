"use client";

import {
	Bot,
	Code,
	Eye,
	FileText,
	Send,
	Sparkles,
	ToggleLeft,
	ToggleRight,
	User,
	X,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import JsonViewerEnhanced from "@/components/JsonViewerEnhanced";
import StyledMarkdown from "@/components/utils/StyledMarkdown";
import { api } from "@/lib/api";

interface ResumeExecutionDialogProps {
	execution: {
		execution_id: string;
		thread_id: string;
		graph_name: string;
		checkpoint: {
			node_id: string;
			node_name: string;
			checkpoint_id: string;
			last_input: any;
			last_output?: any;
		} | null;
	};
	onClose: () => void;
	onResume: (executionId: string, userInput: string) => void;
}

export default function ResumeExecutionDialog({
	execution,
	onClose,
	onResume,
}: ResumeExecutionDialogProps) {
	const [userInput, setUserInput] = useState("");
	const [isMarkdownMode, setIsMarkdownMode] = useState(false);
	const [isLoading, setIsLoading] = useState(false);
	const [lastOutput, setLastOutput] = useState<any>(null);
	const [fetchingOutput, setFetchingOutput] = useState(true);

	useEffect(() => {
		// Fetch the last output if not provided
		const fetchLastOutput = async () => {
			if (execution.checkpoint?.last_output) {
				setLastOutput(execution.checkpoint.last_output);
				setFetchingOutput(false);
				return;
			}

			try {
				// Try to fetch from execution state
				const state = await api.getExecutionState(execution.execution_id);
				if (state?.checkpoint_state?.last_output) {
					setLastOutput(state.checkpoint_state.last_output);
				} else if (state?.nodes?.length > 0) {
					// Get the output from the last completed node
					const lastNode = state.nodes
						.filter((n: any) => n.output_data)
						.sort((a: any, b: any) => b.execution_order - a.execution_order)[0];
					if (lastNode?.output_data) {
						setLastOutput(lastNode.output_data);
					}
				}
			} catch (error) {
				console.error("Failed to fetch last output:", error);
				// Use last input as fallback
				setLastOutput(
					execution.checkpoint?.last_input || "No output available",
				);
			} finally {
				setFetchingOutput(false);
			}
		};

		fetchLastOutput().catch((error) => {
			console.error("Failed to fetch last output:", error);
		});
	}, [execution]);

	const handleResume = useCallback(() => {
		if (!userInput.trim()) {
			alert("Please enter a response");
			return;
		}
		setIsLoading(true);
		onResume(execution.execution_id, userInput);
	}, [userInput, execution.execution_id, onResume]);

	const handleMarkdownToggle = useCallback(() => {
		setIsMarkdownMode(!isMarkdownMode);
	}, [isMarkdownMode]);

	const handleUserInputChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setUserInput(e.target.value);
		},
		[],
	);

	const renderContent = (content: any, title: string) => {
		if (!content) {
			return (
				<div className="flex flex-col items-center justify-center h-full text-[color:var(--color-text-muted)]">
					<FileText className="w-12 h-12 mb-2 opacity-30" />
					<p className="text-sm">No {title.toLowerCase()} available</p>
				</div>
			);
		}

		// Check if content is a string
		if (typeof content === "string") {
			// Check for markdown indicators
			const hasMarkdown =
				content.includes("#") ||
				content.includes("**") ||
				content.includes("*") ||
				content.includes("```") ||
				content.includes("[") ||
				content.includes("](") ||
				content.includes("\n");

			if (hasMarkdown || content.length > 100) {
				return (
					<div className="h-full overflow-auto">
						<StyledMarkdown content={content} />
					</div>
				);
			}

			// Short plain text
			return (
				<div className="p-4">
					<p className="text-[color:var(--color-text-secondary)]">{content}</p>
				</div>
			);
		}

		// For objects/arrays, use the JSON viewer
		return (
			<div className="h-full overflow-auto">
				<JsonViewerEnhanced data={content} />
			</div>
		);
	};

	return (
		<div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
			{/* Backdrop with stronger blur */}
			<div
				className="absolute inset-0 bg-black/80 backdrop-blur-lg"
				onClick={onClose}
			/>

			{/* Modal Container - Premium split view design */}
			<div
				className="relative bg-gradient-to-br from-[color:var(--color-bg-secondary)]/98 via-[color:var(--color-surface)]/98 to-[color:var(--color-bg-secondary)]/98 
                     backdrop-blur-2xl rounded-2xl shadow-2xl border border-[color:var(--color-border)]/60 
                     max-w-6xl w-full h-[85vh] flex flex-col overflow-hidden
                     ring-1 ring-white/10"
			>
				{/* Header with context */}
				<div
					className="relative px-6 py-5 border-b border-[color:var(--color-border)]/50 
                       bg-gradient-to-r from-[color:var(--color-primary)]/5 to-[color:var(--color-accent)]/5"
				>
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-4">
							<div
								className="p-2.5 bg-gradient-to-br from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/20 
                             rounded-xl border border-[color:var(--color-border)]/20"
							>
								<Sparkles className="w-5 h-5 text-[color:var(--color-accent)]" />
							</div>
							<div>
								<h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
									Resume Execution
									<span
										className="px-2 py-0.5 text-xs font-medium bg-[color:var(--color-warning)]/18 
                               text-[color:var(--color-warning)] rounded-full border border-[color:var(--color-warning)]/30"
									>
										Interactive
									</span>
								</h3>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5 flex items-center gap-2">
									<span className="font-medium">{execution.graph_name}</span>
									<span className="text-[color:var(--color-text-muted)]">
										•
									</span>
									<span>
										{execution.checkpoint?.node_name || "Unknown Node"}
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

				{/* Split View Content */}
				<div className="flex-1 flex overflow-hidden">
					{/* Left Panel - Last Output */}
					<div className="flex-1 flex flex-col border-r border-[color:var(--color-border)]/50">
						<div className="px-6 py-4 border-b border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/30">
							<div className="flex items-center gap-2">
								<Bot className="w-4 h-4 text-[color:var(--color-accent)]" />
								<h4 className="text-sm font-semibold text-slate-700">
									Last Output
								</h4>
								<span className="ml-auto text-xs text-[color:var(--color-text-muted)]">
									From: {execution.checkpoint?.node_name}
								</span>
							</div>
						</div>

						<div className="flex-1 p-6 overflow-auto bg-[color:var(--color-bg-secondary)]/20">
							{fetchingOutput ? (
								<div className="flex items-center justify-center h-full">
									<div className="animate-spin rounded-full h-8 w-8 border-2 border-[color:var(--color-border)] border-t-[color:var(--color-primary)]"></div>
								</div>
							) : (
								renderContent(lastOutput, "Output")
							)}
						</div>
					</div>

					{/* Right Panel - User Input */}
					<div className="flex-1 flex flex-col">
						<div className="px-6 py-4 border-b border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/30">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<User className="w-4 h-4 text-[#0DA931]" />
									<h4 className="text-sm font-semibold text-slate-700">
										Your Response
									</h4>
								</div>

								{/* Markdown Mode Toggle */}
								<button
									onClick={handleMarkdownToggle}
									className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium
                           bg-[color:var(--color-surface)]/50 hover:bg-[color:var(--color-surface)]/70 border border-[color:var(--color-border)]/50
                           rounded-lg transition-all duration-200 text-[color:var(--color-text-muted)] hover:text-slate-700"
								>
									{isMarkdownMode ? (
										<>
											<Eye className="w-3 h-3" />
											Preview
										</>
									) : (
										<>
											<Code className="w-3 h-3" />
											Edit
										</>
									)}
									{isMarkdownMode ? (
										<ToggleRight className="w-4 h-4 text-[#0DA931]" />
									) : (
										<ToggleLeft className="w-4 h-4" />
									)}
								</button>
							</div>
						</div>

						<div className="flex-1 p-6 overflow-auto bg-[color:var(--color-bg-secondary)]/20">
							{isMarkdownMode ? (
								<div className="h-full">
									{userInput ? (
										<StyledMarkdown content={userInput} />
									) : (
										<div className="flex items-center justify-center h-full text-[color:var(--color-text-muted)]">
											<p className="text-sm">Enter text to see preview</p>
										</div>
									)}
								</div>
							) : (
								<textarea
									value={userInput}
									onChange={handleUserInputChange}
									placeholder="Enter your response here... You can use Markdown formatting."
									className="w-full h-full p-4 bg-[color:var(--color-surface)]/50 border border-[color:var(--color-border)]/50 
                           rounded-xl text-sm text-slate-700 placeholder-gray-500 
                           focus:outline-none focus:border-[color:var(--color-border)]/50 focus:bg-[color:var(--color-surface)]/70
                           focus:ring-2 focus:ring-[color:var(--color-accent)]/20 transition-all duration-200
                           resize-none font-mono"
									autoFocus
								/>
							)}
						</div>

						{/* Input Help Text */}
						<div className="px-6 py-3 border-t border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/30">
							<p className="text-xs text-[color:var(--color-text-muted)]">
								Tip: You can use **bold**, *italic*, `code`, and other Markdown
								formatting. Toggle preview mode to see how it will look.
							</p>
						</div>
					</div>
				</div>

				{/* Footer Actions */}
				<div
					className="flex items-center justify-between px-6 py-4 
                       bg-gradient-to-r from-[color:var(--color-bg-secondary)]/60 to-[color:var(--color-surface)]/60 
                       backdrop-blur-sm border-t border-[color:var(--color-border)]/50"
				>
					<div className="text-xs text-[color:var(--color-text-muted)]">
						Thread ID:{" "}
						<span className="font-mono text-[color:var(--color-text-muted)]">
							{execution.thread_id}
						</span>
					</div>

					<div className="flex items-center gap-3">
						<button
							onClick={onClose}
							className="px-4 py-2 bg-[color:var(--color-border)]/50 hover:bg-[color:var(--color-border)]/70 
                       text-[color:var(--color-text-secondary)] hover:text-slate-900 rounded-lg 
                       transition-all duration-200 font-medium text-sm
                       border border-[color:var(--color-surface-hover)]/50 hover:border-[color:var(--color-text-muted)]"
						>
							Cancel
						</button>

						<button
							onClick={handleResume}
							disabled={!userInput.trim() || isLoading}
							className="px-5 py-2 bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent)] 
                       hover:from-[color:var(--color-primary-light)] hover:to-[color:var(--color-accent)]
                       disabled:from-[color:var(--color-border)] disabled:to-[color:var(--color-border)]
                       text-white rounded-lg transition-all duration-200 
                       font-semibold text-sm flex items-center gap-2
                       hover:shadow-[0_0_25px_rgba(99,102,241,0.5)]
                       disabled:opacity-50 disabled:cursor-not-allowed
                       hover:scale-105 disabled:hover:scale-100"
						>
							<Send className="w-4 h-4" />
							Resume Execution
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
