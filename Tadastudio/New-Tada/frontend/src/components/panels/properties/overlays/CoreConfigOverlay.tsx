"use client";

import { Loader2, Maximize2, Sparkles, X } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import Dropdown from "../../../ui/Dropdown";
import InfoTooltip from "../../../ui/InfoTooltipPortal";

interface CoreConfigOverlayProps {
	isOpen: boolean;
	onClose: () => void;
	selectedModelId: string;
	onModelChange: (model: string) => void;
	prompt: string;
	onPromptChange: (prompt: string) => void;
	onExpandMarkdownEditor: () => void;
	modelOptions: Array<{
		value: string;
		label: string;
		provider: string;
		description: string;
	}>;
	modelsLoading: boolean;
	modelLoadError: string | null;
	legacyModelName: string;
}

export default function CoreConfigOverlay({
	isOpen,
	onClose,
	selectedModelId,
	onModelChange,
	prompt,
	onPromptChange,
	onExpandMarkdownEditor,
	modelOptions,
	modelsLoading,
	modelLoadError,
	legacyModelName,
}: CoreConfigOverlayProps) {
	// Click handler to stop propagation
	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-start justify-center z-[110] p-4 pt-8 sm:pt-16 lg:pt-20 animate-fadeIn overflow-y-auto"
			onClick={handleStopPropagation}
		>
			<div
				className="bg-gradient-to-b from-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)] border border-[color:var(--color-primary)]/60 rounded-xl shadow-2xl w-full max-w-4xl max-h-[calc(100vh-4rem)] sm:max-h-[calc(100vh-8rem)] lg:max-h-[calc(100vh-10rem)] mb-8 sm:mb-16 lg:mb-20 flex flex-col animate-scaleIn overflow-hidden"
				onClick={handleStopPropagation}
			>
				{/* Header */}
				<div className="flex items-center justify-between p-5 sm:p-6 bg-[color:var(--color-surface)]/50 border-b border-[color:var(--color-border)]/30">
					<div className="flex items-center gap-3">
						<div className="p-3 bg-[color:var(--color-accent)]/15 rounded-xl">
							<Sparkles className="w-6 h-6 text-[color:var(--color-accent)]" />
						</div>
						<div>
							<h2 className="text-lg sm:text-xl font-bold text-slate-900">
								Core Configuration
							</h2>
							<p className="text-sm text-[color:var(--color-text-muted)] mt-0.5">
								Essential agent settings
							</p>
						</div>
					</div>
					<button
						onClick={onClose}
						className="p-2 hover:bg-[color:var(--color-border)]/50 rounded-lg transition-all hover:rotate-90 duration-200"
					>
						<X className="w-5 h-5 text-[color:var(--color-text-muted)]" />
					</button>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 min-h-0">
					{/* Model Selection */}
					<div>
						<label
							htmlFor="ai-model-select"
							className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2 flex items-center gap-2"
						>
							AI Model
							<InfoTooltip text="Choose the AI model that best fits your use case. Different models excel at different tasks." />
						</label>
						{modelsLoading ? (
							<div className="flex items-center gap-3 rounded-lg border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/50 px-4 py-3 text-sm text-[color:var(--color-text-muted)]">
								<Loader2 className="w-4 h-4 animate-spin text-[color:var(--color-accent)]" />
								Loading available models...
							</div>
						) : modelOptions.length > 0 ? (
							<Dropdown
								value={selectedModelId || ""}
								onChange={onModelChange}
								options={modelOptions.map((model) => ({
									value: model.value,
									label: `${model.label} • ${model.provider}`,
									description: model.description,
								}))}
								placeholder="Select a model deployment"
							/>
						) : (
							<div className="rounded-lg border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40 px-4 py-3 text-sm text-[color:var(--color-text-secondary)]">
								No models configured. Visit{" "}
								<span className="text-[color:var(--color-accent)]">
									Settings → LLM Providers
								</span>{" "}
								to add deployments.
							</div>
						)}
						{modelLoadError && (
							<p className="mt-2 text-xs text-red-300">{modelLoadError}</p>
						)}
						{legacyModelName && !selectedModelId && (
							<p className="mt-2 text-xs text-amber-300">
								This agent still references the legacy model{" "}
								<span className="font-medium">{legacyModelName}</span>. Select a
								managed deployment to migrate.
							</p>
						)}
					</div>

					{/* System Prompt */}
					<div>
						<div className="flex items-center justify-between mb-2">
							<label className="text-sm font-medium text-[color:var(--color-text-secondary)] flex items-center gap-2">
								System Prompt
								<InfoTooltip text="Define your agent's role, personality, and instructions. Be specific about what you want the agent to do." />
							</label>
							<button
								onClick={onExpandMarkdownEditor}
								className="flex items-center gap-1.5 px-2.5 py-1 bg-[color:var(--color-border)] hover:bg-[color:var(--color-surface-hover)] rounded-lg transition-colors text-xs"
								title="Open in full editor with markdown preview"
							>
								<Maximize2 className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
								<span className="text-[color:var(--color-text-secondary)]">
									Expand Editor
								</span>
							</button>
						</div>
						<textarea
							value={prompt}
							onChange={(e) => onPromptChange(e.target.value)}
							rows={8}
							className="w-full px-4 py-3 rounded-lg text-slate-900 placeholder-slate-400 bg-white border border-slate-200 resize-none font-mono text-sm"
							placeholder="You are a helpful AI assistant specialized in...

Example instructions:
• Analyze documents and extract key insights
• Always provide accurate, factual information
• Cite your sources when referencing documents
• Be concise but thorough in your responses"
						/>
						<div className="mt-2 flex justify-between text-xs text-[color:var(--color-text-muted)]">
							<span>{prompt.length} characters</span>
							<span>Press Shift+Enter for new line</span>
						</div>

						{/* Prompting Tips */}
						<div className="mt-4 rounded-lg border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/30 p-4">
							<h4 className="text-sm font-semibold text-[color:var(--color-text-secondary)] mb-3 flex items-center gap-2">
								<Sparkles className="w-4 h-4 text-[color:var(--color-accent)]" />
								Prompting Tips
							</h4>
							<ul className="space-y-2 text-sm text-[color:var(--color-text-secondary)]">
								<li className="flex items-start gap-2">
									<span className="text-[color:var(--color-accent)] mt-1">
										•
									</span>
									<span>
										Be specific about what you want your agent to do and define
										its role clearly
									</span>
								</li>
								<li className="flex items-start gap-2">
									<span className="text-[color:var(--color-accent)] mt-1">
										•
									</span>
									<span>
										If you&apos;ve given your agent tools, provide instructions
										on when to use them (e.g., &quot;Use your document search
										tool to answer questions about our documentation&quot;)
									</span>
								</li>
								<li className="flex items-start gap-2">
									<span className="text-[color:var(--color-accent)] mt-1">
										•
									</span>
									<span>
										Include examples of good responses to guide the agent&apos;s
										output style
									</span>
								</li>
								<li className="flex items-start gap-2">
									<span className="text-[color:var(--color-accent)] mt-1">
										•
									</span>
									<span>
										Structure your prompt with clear sections for role, context,
										and instructions
									</span>
								</li>
							</ul>
						</div>
					</div>
				</div>

				{/* Footer */}
				<div className="p-6 border-t border-[color:var(--color-border)]/30 bg-[color:var(--color-surface)]/50">
					<div className="flex justify-end">
						<button
							onClick={onClose}
							className="px-6 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-all border border-[color:var(--color-surface-hover)]"
						>
							Done
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
