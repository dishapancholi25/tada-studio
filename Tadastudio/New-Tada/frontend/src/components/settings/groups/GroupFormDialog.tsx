"use client";

import { Users, X } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import Button from "@/components/ui/Button";
import type { Group } from "@/types/api";

interface GroupFormDialogProps {
	open: boolean;
	group?: Group | null;
	onClose: () => void;
	onSave: (name: string, description?: string) => Promise<void>;
}

const INPUT =
	"w-full rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15";

export default function GroupFormDialog({
	open,
	group,
	onClose,
	onSave,
}: GroupFormDialogProps) {
	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [errors, setErrors] = useState<{ name?: string }>({});
	const [saveError, setSaveError] = useState<string | null>(null);
	const [saving, setSaving] = useState(false);
	const [mounted, setMounted] = useState(false);
	const dialogRef = useFocusTrap<HTMLDivElement>(open);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, open);

	useEffect(() => {
		if (open) {
			document.body.style.overflow = "hidden";
			if (group) {
				setName(group.name);
				setDescription(group.description || "");
			} else {
				setName("");
				setDescription("");
			}
			setErrors({});
			setSaveError(null);
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [open, group]);

	const validate = (): boolean => {
		const newErrors: { name?: string } = {};
		const trimmedName = name.trim();

		if (!trimmedName) {
			newErrors.name = "Group name is required";
		} else if (!/^[a-zA-Z0-9\s-]+$/.test(trimmedName)) {
			newErrors.name =
				"Name can only contain letters, numbers, spaces, and hyphens";
		}

		setErrors(newErrors);
		return Object.keys(newErrors).length === 0;
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!validate()) return;

		setSaving(true);
		setSaveError(null);
		try {
			await onSave(name.trim(), description.trim() || undefined);
			onClose();
		} catch (error) {
			setSaveError(
				error instanceof Error ? error.message : "Failed to save group. Please try again.",
			);
		} finally {
			setSaving(false);
		}
	};

	if (!mounted || !open) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			{/* Backdrop */}
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

			{/* Dialog */}
			<div
				ref={dialogRef}
				className="relative w-full max-w-md animate-fadeIn rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]"
				onClick={(e) => e.stopPropagation()}
			>
				{/* Header — Workflow Management style */}
				<div className="flex shrink-0 items-start justify-between border-b border-slate-200 px-6 pb-4 pt-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Users className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">
								{group ? "Edit Group" : "Create Group"}
							</h2>
							<p className="mt-0.5 text-sm text-slate-600">
								{group ? "Update name and description" : "Add a new group for your organization"}
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Form */}
				<form onSubmit={handleSubmit}>
					<div className="space-y-4 px-6 pb-6">
						{saveError && (
							<div className="rounded-[4px] border border-red-200 bg-white px-3 py-2 text-sm text-red-800">
								{saveError}
							</div>
						)}
						{/* Name field */}
						<div>
							<label className="mb-1.5 block text-sm font-medium text-slate-900">
								Name <span className="text-red-600">*</span>
							</label>
							<input
								type="text"
								value={name}
								onChange={(e) => {
									setName(e.target.value);
									if (errors.name) setErrors({});
								}}
								placeholder="Enter group name"
								className={`${INPUT} ${errors.name ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : ""}`}
								autoFocus
							/>
							{errors.name && (
								<p className="mt-1 text-xs text-red-700">{errors.name}</p>
							)}
						</div>

						{/* Description field */}
						<div>
							<label className="mb-1.5 block text-sm font-medium text-slate-900">
								Description
							</label>
							<textarea
								value={description}
								onChange={(e) => setDescription(e.target.value)}
								placeholder="Enter group description (optional)"
								rows={3}
								className={`${INPUT} resize-none`}
							/>
						</div>
					</div>

					{/* Footer */}
					<div className="flex items-center justify-end gap-3 border-t border-slate-200 px-6 py-4">
						<Button
							onClick={onClose}
							variant="secondary"
							type="button"
							className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
						>
							Cancel
						</Button>
						<Button
							type="submit"
							variant="primary"
							loading={saving}
							disabled={saving}
							className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
						>
							{group ? "Save Changes" : "Create Group"}
						</Button>
					</div>
				</form>
			</div>
		</div>,
		document.body,
	);
}
