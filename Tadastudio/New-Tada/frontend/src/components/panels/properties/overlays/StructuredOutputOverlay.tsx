"use client";

import { FileText, Sparkles, X } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import StructuredOutputBuilder, {
	type StructuredOutputSchema,
} from "../../../utils/StructuredOutputBuilder";

interface StructuredOutputOverlayProps {
	isOpen: boolean;
	onClose: () => void;
	enableStructuredOutput: boolean;
	onEnableStructuredOutputChange: (enabled: boolean) => void;
	structuredOutputs: StructuredOutputSchema[];
	onStructuredOutputsChange: (schemas: StructuredOutputSchema[]) => void;
}

export default function StructuredOutputOverlay({
	isOpen,
	onClose,
	enableStructuredOutput,
	onEnableStructuredOutputChange,
	structuredOutputs,
	onStructuredOutputsChange,
}: StructuredOutputOverlayProps) {
	// Click handler to stop propagation
	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	// Change handler for structured output enabled checkbox
	const handleEnableStructuredOutputChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onEnableStructuredOutputChange(e.target.checked);
		},
		[onEnableStructuredOutputChange],
	);

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-[100] p-6 animate-fadeIn"
			onClick={handleStopPropagation}
		>
			{/* Modal Shell */}
			<div
				className={`relative w-full max-w-6xl flex flex-col animate-scaleIn transition-all duration-300 rounded-[30px] border border-[color:var(--color-border)] bg-[color:var(--color-surface)] shadow-xl overflow-hidden ${
					enableStructuredOutput ? "h-[85vh]" : "h-auto"
				}`}
				onClick={handleStopPropagation}
			>
				{/* Glass Halo */}
				<div className="absolute -inset-[1px] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.3)] via-transparent to-[rgba(var(--color-primary-rgb),0.12)] rounded-[30px] pointer-events-none opacity-50" />

				{/* Header */}
				<div className="relative flex items-center justify-between p-8 border-b border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] z-10">
					<div className="flex items-center gap-5">
						<div className="p-4 bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.2)] to-[rgba(var(--color-primary-rgb),0.05)] rounded-2xl border border-[rgba(var(--color-primary-rgb),0.3)] shadow-[0_0_30px_rgba(var(--color-primary-rgb),0.15)]">
							<FileText className="w-8 h-8 text-[color:var(--color-primary)]" />
						</div>
						<div>
							<h2 className="text-2xl font-semibold text-[color:var(--color-text-primary)] flex items-center gap-4 tracking-tight">
								Structured Output
								{enableStructuredOutput && (
									<span className="text-[11px] font-medium px-3 py-1 bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary)] rounded-full border border-[rgba(var(--color-primary-rgb),0.45)] shadow-[0_0_15px_rgba(var(--color-primary-rgb),0.2)]">
										ACTIVE
									</span>
								)}
							</h2>
							<p className="text-sm text-[color:var(--color-text-secondary)] mt-1.5 font-light">
								Define the strict JSON schema that the agent must output
							</p>
						</div>
					</div>
					<button
						onClick={onClose}
						className="group p-2.5 hover:bg-[color:var(--color-surface-hover)] rounded-xl transition-all duration-200 border border-transparent hover:border-[color:var(--color-border)]"
					>
						<X className="w-6 h-6 text-[color:var(--color-text-muted)] group-hover:text-[color:var(--color-text-primary)] transition-colors" />
					</button>
				</div>

				{/* Content */}
				<div className="relative flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar z-10">
					{/* Enable Toggle Section */}
					<div
						className={`group relative overflow-hidden rounded-2xl border transition-all duration-300 ${
							enableStructuredOutput
								? "border-[color:var(--color-primary)]/40 bg-[rgba(var(--color-primary-rgb),0.03)]"
								: "border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 hover:border-[color:var(--color-primary)]/30"
						}`}
					>
						<div className="absolute inset-0 bg-gradient-to-r from-[rgba(var(--color-primary-rgb),0.05)] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

						<div className="relative p-6 flex items-center justify-between">
							<div className="flex items-start gap-4">
								<div
									className={`mt-1 p-2 rounded-lg transition-colors ${enableStructuredOutput ? "bg-[rgba(var(--color-primary-rgb),0.15)]" : "bg-[color:var(--color-surface)]"}`}
								>
									<Sparkles
										className={`w-5 h-5 ${enableStructuredOutput ? "text-[color:var(--color-primary)]" : "text-[color:var(--color-text-muted)]"}`}
									/>
								</div>
								<div>
									<h4 className="text-base font-medium text-slate-900">
										Enable Structured Output
									</h4>
									<p className="text-sm text-[color:var(--color-text-secondary)] mt-1 max-w-xl">
										Force the agent to respond with a valid JSON object matching
										your schema. This ensures consistent, programmatic access to
										the agent's response.
									</p>
								</div>
							</div>

							<label className="relative inline-flex items-center cursor-pointer">
								<input
									type="checkbox"
									checked={enableStructuredOutput}
									onChange={handleEnableStructuredOutputChange}
									className="sr-only peer"
								/>
								<div className="w-14 h-8 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[color:var(--color-primary)]/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-[color:var(--color-text-muted)] after:rounded-full after:h-6 after:w-6 after:transition-all after:shadow-sm peer-checked:bg-[color:var(--color-primary)]/20 peer-checked:border-[color:var(--color-primary)]/50 peer-checked:after:bg-[color:var(--color-primary-light)]"></div>
							</label>
						</div>
					</div>

					{enableStructuredOutput && (
						<div className="animate-fadeIn">
							<StructuredOutputBuilder
								schemas={structuredOutputs}
								onChange={onStructuredOutputsChange}
							/>
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="relative p-6 border-t border-[color:var(--color-border)]/30 bg-[color:var(--color-surface)]/30 backdrop-blur-sm z-10">
					<div className="flex justify-end">
						<button
							onClick={onClose}
							className="px-8 py-3 bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] text-[color:var(--button-primary-text)] rounded-xl font-medium shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)] hover:shadow-[0_20px_50px_rgba(var(--color-primary-rgb),0.45)] hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
						>
							Done
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
