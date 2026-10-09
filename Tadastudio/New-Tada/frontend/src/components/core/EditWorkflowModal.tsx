"use client";

import { Pencil } from "lucide-react";
import React, { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";
import FormTextarea from "@/components/ui/FormTextarea";

interface EditWorkflowModalProps {
	isOpen: boolean;
	workflowName: string;
	workflowDescription: string;
	saving: boolean;
	onSave: (name: string, description: string) => void;
	onCancel: () => void;
}

const EditWorkflowModal = React.memo(function EditWorkflowModal({
	isOpen,
	workflowName,
	workflowDescription,
	saving,
	onSave,
	onCancel,
}: EditWorkflowModalProps) {
	const [name, setName] = useState(workflowName);
	const [description, setDescription] = useState(workflowDescription);

	useEffect(() => {
		if (isOpen) {
			setName(workflowName);
			setDescription(workflowDescription);
		}
	}, [isOpen, workflowName, workflowDescription]);

	useEffect(() => {
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape" && !saving) {
				onCancel();
			}
		};

		if (isOpen) {
			document.addEventListener("keydown", handleEscape);
			return () => document.removeEventListener("keydown", handleEscape);
		}
	}, [isOpen, saving, onCancel]);

	if (!isOpen) return null;

	const hasChanges =
		name.trim() !== workflowName ||
		description.trim() !== workflowDescription;
	const canSave = name.trim().length > 0 && hasChanges && !saving;

	return (
		<div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-[60] p-4 animate-fadeIn">
			<div className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(15,23,42,0.18)] animate-scaleIn">
				{/* Accent gradient */}
				<div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(249,115,22,0.12),transparent_55%)] pointer-events-none" />

				{/* Top glow line */}
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/60 to-transparent" />

				<div className="relative p-6 space-y-6">
					{/* Header */}
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-orange-50 border border-orange-200 shadow-[0_0_25px_rgba(249,115,22,0.16)]">
							<Pencil className="w-6 h-6 text-orange-600" />
						</div>
						<div className="flex-1 min-w-0 space-y-1">
							<h3 className="text-xl font-semibold text-slate-900 tracking-tight">
								Edit Workflow
							</h3>
							<p className="text-sm text-slate-600 leading-relaxed">
								Update the name and description
							</p>
						</div>
					</div>

					{/* Form Fields */}
					<div className="space-y-4">
						<div className="space-y-2">
							<div className="flex items-center gap-2">
								<label className="text-xs font-semibold capitalize tracking-wider text-slate-600">
									Workflow Name
								</label>
								<span className="text-xs text-orange-600">
									*
								</span>
							</div>
							<FormInput
								value={name}
								onChange={(e) => setName(e.target.value)}
								placeholder="My AI Workflow"
								disabled={saving}
								className="!bg-white !border-slate-200 !text-slate-900 placeholder:!text-slate-400 hover:!border-slate-300 focus:!border-orange-400 focus:!ring-orange-500/20 !transition-all !duration-200"
							/>
						</div>

						<div className="space-y-2">
							<div className="flex items-center gap-2">
								<label className="text-xs font-semibold capitalize tracking-wider text-slate-600">
									Description
								</label>
								<span className="text-xs text-slate-400 font-normal lowercase">
									(optional)
								</span>
							</div>
							<FormTextarea
								value={description}
								onChange={(e) => setDescription(e.target.value)}
								rows={4}
								placeholder="Describe what this workflow does..."
								disabled={saving}
								className="!bg-white !border-slate-200 !text-slate-900 placeholder:!text-slate-400 hover:!border-slate-300 focus:!border-orange-400 focus:!ring-orange-500/20 !transition-all !duration-200"
							/>
						</div>
					</div>

					{/* Action Buttons */}
					<div className="flex flex-col-reverse sm:flex-row gap-3">
						<Button
							onClick={onCancel}
							variant="secondary"
							disabled={saving}
							className="flex-1 !bg-white !border-slate-200 !text-slate-700 hover:!bg-slate-50 hover:!border-slate-300 hover:!shadow-[0_10px_30px_rgba(15,23,42,0.12)] hover:!-translate-y-0.5 !transition-all !duration-200"
						>
							Cancel
						</Button>
						<Button
							onClick={() => onSave(name.trim(), description.trim())}
							disabled={!canSave}
							loading={saving}
							className="flex-1 !bg-orange-500 !border-orange-500 !text-white hover:!bg-orange-600 hover:!border-orange-600 hover:!-translate-y-0.5 !transition-all !duration-200 disabled:!opacity-40 disabled:!cursor-not-allowed"
						>
							{saving ? "Saving..." : "Save Changes"}
						</Button>
					</div>
				</div>
			</div>
		</div>
	);
});

export default EditWorkflowModal;
