"use client";

import clsx from "clsx";
import { AlertTriangle, X } from "lucide-react";
import React from "react";
import { useGraphStore } from "@/stores/graphStore";
import { isStartNode } from "@/lib/nodeTypeUtils";

interface GraphCanvasOverlaysProps {
	showNodePalette: boolean;
	onShowNodePalette: () => void;
	onSetPaletteSourceNodeId: (id: string | null) => void;
	onSetPaletteSourceBranchIndex: (index: number | null) => void;
	validationMessage?: string | null;
	onDismissValidationMessage?: () => void;
}

const GraphCanvasOverlays = React.memo(function GraphCanvasOverlays({
	showNodePalette: _showNodePalette,
	onShowNodePalette: _onShowNodePalette,
	onSetPaletteSourceNodeId: _onSetPaletteSourceNodeId,
	onSetPaletteSourceBranchIndex: _onSetPaletteSourceBranchIndex,
	validationMessage,
	onDismissValidationMessage,
}: GraphCanvasOverlaysProps) {
	const nodes = useGraphStore((state) => state.nodes);
	const isFreshWorkflow = nodes.length === 1 && nodes.every(isStartNode);

	return (
		<>
			{/* Validation message toast */}
			{validationMessage && (
				<div className="absolute top-3 left-3 z-30">
					<div
						className={clsx(
							"flex max-w-sm items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 shadow-lg",
						)}
						role="alert"
					>
						<AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-600" />
						<span className="text-sm leading-snug">{validationMessage}</span>
						{onDismissValidationMessage && (
							<button
								onClick={onDismissValidationMessage}
								className="ml-auto rounded-full p-1 text-amber-600 transition-colors duration-200 hover:bg-amber-200 hover:text-amber-900"
								aria-label="Dismiss validation message"
							>
								<X className="h-3 w-3" />
							</button>
						)}
					</div>
				</div>
			)}

			{/* Fresh workflow hint */}
			{isFreshWorkflow && (
				<div className="pointer-events-none absolute inset-0 z-10 flex items-start justify-center pt-[8%]">
					<p className="animate-fadeInUp text-base text-[color:var(--color-text-muted)]">
						Click the{" "}
						<strong className="text-[color:var(--color-text-secondary)]">+</strong>{" "}
						button on the Start node to add your first step
					</p>
				</div>
			)}
		</>
	);
});

export default GraphCanvasOverlays;
