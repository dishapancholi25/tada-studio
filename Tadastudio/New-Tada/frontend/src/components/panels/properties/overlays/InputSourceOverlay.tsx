"use client";

import { ArrowDownToLine, Sparkles, X } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import type { Edge, Node } from "reactflow";
import InputSourceSelector from "../InputSourceSelector";

interface InputSourceOverlayProps {
	isOpen: boolean;
	onClose: () => void;
	node: Node;
	availableNodes: Node[];
	onUpdate: (config: any) => void;
	hasCustomConfig: boolean;
	currentConfig?: any;
	edges?: Edge[];
}

export default function InputSourceOverlay({
	isOpen,
	onClose,
	node,
	availableNodes,
	onUpdate,
	hasCustomConfig,
	currentConfig,
	edges,
}: InputSourceOverlayProps) {
	// Click handler to stop propagation
	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	if (!isOpen) return null;

	const nodeName =
		typeof node?.data?.name === "string" ? node.data.name : "Node";

	return (
		<div
			className="fixed inset-0 z-[110] flex items-start justify-center bg-black/45 backdrop-blur-2xl p-4 pt-8 sm:pt-16 lg:pt-20 animate-fadeIn overflow-y-auto"
			onClick={handleStopPropagation}
		>
			<div
				className="w-full max-w-4xl max-h-[calc(100vh-4rem)] sm:max-h-[calc(100vh-8rem)] lg:max-h-[calc(100vh-10rem)] mb-8 sm:mb-16 lg:mb-20 flex flex-col overflow-hidden rounded-3xl border border-[color:var(--color-border)]/60 bg-gradient-to-br from-[rgba(20,25,39,0.85)] via-[rgba(12,16,25,0.92)] to-[rgba(9,12,18,0.96)] shadow-[0_30px_80px_rgba(4,7,17,0.45)]"
				onClick={handleStopPropagation}
			>
				<div className="relative flex-none overflow-hidden border-b border-[color:var(--color-border)]/50">
					<div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(239,68,68,0.18),transparent_55%)]" />
					<div className="relative flex min-h-[7rem] flex-col gap-4 sm:gap-6 p-5 sm:p-7 lg:min-h-[8rem] lg:flex-row lg:items-start lg:justify-between">
						<div className="flex flex-1 items-start gap-4 lg:max-w-2xl">
							<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[rgba(239,68,68,0.16)] text-rose-600 shadow-[0_0_25px_rgba(239,68,68,0.22)]">
								<ArrowDownToLine className="h-6 w-6" />
							</div>
							<div className="min-w-0 space-y-2">
								<div className="flex flex-wrap items-center gap-3">
									<h2 className="text-xl sm:text-2xl font-semibold text-slate-900 tracking-tight">
										Input Source
									</h2>
									{hasCustomConfig && (
										<span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-3 py-1 text-xs font-medium text-rose-600">
											<Sparkles className="h-3.5 w-3.5" />
											Custom
										</span>
									)}
								</div>
								<p className="max-w-xl text-sm leading-relaxed text-[color:var(--color-text-muted)]">
									Choose what information{" "}
									<span className="text-[color:var(--color-text-secondary)]">
										{nodeName}
									</span>{" "}
									should listen to before it runs - anything from the previous
									step to handpicked teammates or a custom prompt.
								</p>
							</div>
						</div>
						<div className="flex flex-wrap items-center gap-3">
							<div className="hidden md:flex items-center gap-2 rounded-full border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/60 px-4 py-1.5 text-xs capitalize tracking-wide text-[color:var(--color-text-muted)]">
								<span className="h-2 w-2 rounded-full bg-[rgba(239,68,68,0.7)] shadow-[0_0_10px_rgba(239,68,68,0.4)]" />
								Configuration Panel
							</div>
							<button
								onClick={onClose}
								className="rounded-xl border border-transparent p-2 text-[color:var(--color-text-muted)] transition-all duration-150 hover:border-[color:var(--color-border)]/60 hover:text-slate-900 hover:shadow-[0_10px_25px_rgba(22,31,55,0.45)] hover:-translate-y-0.5"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>
				</div>

				<div className="flex-1 overflow-y-auto px-5 sm:px-7 py-4 sm:py-6 min-h-0">
					<InputSourceSelector
						node={node}
						availableNodes={availableNodes}
						onUpdate={onUpdate}
						initialConfig={currentConfig}
						edges={edges}
					/>
				</div>

				<div className="border-t border-[color:var(--color-border)]/50 bg-[linear-gradient(120deg,rgba(17,23,36,0.92),rgba(11,16,27,0.92))] px-5 sm:px-7 py-4 sm:py-5">
					<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
						<div className="text-xs text-[color:var(--color-text-muted)]">
							You can revisit this panel anytime to adjust how information flows
							into the node.
						</div>
						<button
							onClick={onClose}
							className="inline-flex items-center justify-center rounded-xl bg-[rgba(239,68,68,0.85)] px-6 py-2.5 text-sm font-medium text-slate-900 transition-all hover:shadow-[0_15px_35px_rgba(239,68,68,0.25)]"
						>
							Done
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
