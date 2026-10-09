"use client";

import React, { useEffect } from "react";
import EnhancedExecutionViewer from "./EnhancedExecutionViewer";

interface EnhancedExecutionViewerModalProps {
	isOpen: boolean;
	executionId: string | null;
	onClose: () => void;
	workflowId?: string;
	returnParam?: string | null;
}

export default function EnhancedExecutionViewerModal({
	isOpen,
	executionId,
	onClose,
	workflowId,
	returnParam,
}: EnhancedExecutionViewerModalProps) {
	console.log("[EnhancedExecutionViewerModal] Render:", {
		isOpen,
		executionId,
	});

	// Prevent body scroll when modal is open
	useEffect(() => {
		if (isOpen) {
			console.log(
				"[EnhancedExecutionViewerModal] Opening modal, setting body overflow to hidden",
			);
			document.body.style.overflow = "hidden";
		} else {
			console.log(
				"[EnhancedExecutionViewerModal] Closing modal, resetting body overflow",
			);
			document.body.style.overflow = "unset";
		}

		// Cleanup on unmount
		return () => {
			document.body.style.overflow = "unset";
		};
	}, [isOpen]);

	if (!isOpen || !executionId) {
		return null;
	}

	return (
		<div className="fixed inset-0 z-[9999] bg-black/50 backdrop-blur-sm animate-fadeIn">
			{/* Modal container with padding for visual separation */}
			<div className="fixed inset-4 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl animate-slideUp">
				{/* Close button */}
				<button
					data-tutorial="enhanced-view-close-btn"
					onClick={onClose}
					className="absolute top-4 right-4 z-50 rounded-lg border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900 group"
					title="Close Execution Viewer"
				>
					<svg
						className="h-6 w-6 transition-colors"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							strokeLinecap="round"
							strokeLinejoin="round"
							strokeWidth={2}
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>

				{/* Enhanced Execution Viewer */}
				<div className="h-full overflow-auto">
					<EnhancedExecutionViewer
						executionId={executionId}
						onClose={onClose}
						workflowId={workflowId}
						returnParam={returnParam}
					/>
				</div>
			</div>
		</div>
	);
}
