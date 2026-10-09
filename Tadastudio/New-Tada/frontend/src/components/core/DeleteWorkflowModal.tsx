"use client";

import { Trash2 } from "lucide-react";
import React from "react";
import Button from "@/components/ui/Button";

interface DeleteWorkflowModalProps {
	isOpen: boolean;
	workflowName: string | null;
	onConfirm: () => void;
	onCancel: () => void;
}

const DeleteWorkflowModal = React.memo(function DeleteWorkflowModal({
	isOpen,
	workflowName,
	onConfirm,
	onCancel,
}: DeleteWorkflowModalProps) {
	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-[60] p-4 animate-fadeIn">
			<div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_25px_60px_rgba(0,0,0,0.15)] animate-scaleIn">
				{/* Danger gradient accent */}
				<div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(239,68,68,0.06),transparent_50%)] pointer-events-none" />

				{/* Top glow line */}
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-red-400/30 to-transparent" />

				<div className="relative p-6 space-y-6">
					{/* Header */}
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-red-50 border border-red-200">
							<Trash2 className="w-6 h-6 text-red-500" />
						</div>
						<div className="flex-1 min-w-0 space-y-1">
							<h3 className="text-xl font-semibold text-slate-900 tracking-tight">
								Delete Workflow
							</h3>
							<p className="text-sm text-slate-500 leading-relaxed">
								This action cannot be undone
							</p>
						</div>
					</div>

					{/* Warning Message */}
					<div className="rounded-2xl border border-red-200 bg-red-50 p-4 space-y-2">
						<p className="text-sm text-slate-700 leading-relaxed">
							Are you sure you want to delete{" "}
							<span className="font-semibold text-red-600">
								&quot;{workflowName}&quot;
							</span>
							?
						</p>
						<p className="text-xs text-slate-500 leading-relaxed">
							All nodes, connections, and configurations will be permanently
							removed from your library.
						</p>
					</div>

					{/* Action Buttons */}
					<div className="flex flex-col-reverse sm:flex-row gap-3">
						<Button
							onClick={onCancel}
							variant="secondary"
							className="flex-1 !bg-slate-50 !border-slate-200 !text-slate-700 hover:!bg-slate-100 hover:!border-slate-300 !transition-all !duration-200"
						>
							Cancel
						</Button>
						<Button
							onClick={onConfirm}
							variant="danger"
							className="flex-1 !bg-red-500 !border-red-500 !text-white hover:!bg-red-600 hover:!shadow-md !transition-all !duration-200 flex items-center justify-center gap-2"
							icon={<Trash2 className="w-4 h-4" />}
						>
							Delete Workflow
						</Button>
					</div>
				</div>
			</div>
		</div>
	);
});

export default DeleteWorkflowModal;
