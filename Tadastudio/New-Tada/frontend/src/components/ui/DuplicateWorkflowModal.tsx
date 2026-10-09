"use client";

import { Copy } from "lucide-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";

interface DuplicateWorkflowModalProps {
	isOpen: boolean;
	currentName: string;
	onConfirm: (newName: string) => void;
	onCancel: () => void;
	isSubmitting?: boolean;
}

const DuplicateWorkflowModal = React.memo(function DuplicateWorkflowModal({
	isOpen,
	currentName,
	onConfirm,
	onCancel,
	isSubmitting = false,
}: DuplicateWorkflowModalProps) {
	const [name, setName] = useState("");
	const inputRef = useRef<HTMLInputElement>(null);

	// Reset and pre-populate name when modal opens
	useEffect(() => {
		if (isOpen) {
			setName(`${currentName} (Copy)`);
			// Auto-focus after render
			requestAnimationFrame(() => inputRef.current?.select());
		}
	}, [isOpen, currentName]);

	const isValid = name.trim().length > 0 && name.trim() !== currentName;

	const handleSubmit = useCallback(
		(e: React.FormEvent) => {
			e.preventDefault();
			if (isValid && !isSubmitting) {
				onConfirm(name.trim());
			}
		},
		[isValid, isSubmitting, name, onConfirm],
	);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Escape") {
				onCancel();
			}
		},
		[onCancel],
	);

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 z-[60] flex animate-fadeIn items-center justify-center bg-slate-900/45 p-4"
			onKeyDown={handleKeyDown}
		>
			<div className="relative w-full max-w-md animate-scaleIn overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
				{/* Top glow line */}
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />

				<form onSubmit={handleSubmit} className="relative p-6 space-y-6">
					{/* Header */}
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-orange-200 bg-white">
							<Copy className="w-6 h-6 text-orange-600" />
						</div>
						<div className="flex-1 min-w-0 space-y-1">
							<h3 className="text-xl font-semibold tracking-tight text-slate-900">
								Duplicate Workflow
							</h3>
							<p className="text-sm leading-relaxed text-slate-500">
								Create an identical copy with a new name
							</p>
						</div>
					</div>

					{/* Name Input */}
					<div className="space-y-2">
						<label
							htmlFor="duplicate-name"
							className="block text-sm font-medium text-slate-700"
						>
							Workflow Name
						</label>
						<input
							ref={inputRef}
							id="duplicate-name"
							type="text"
							value={name}
							onChange={(e) => setName(e.target.value)}
							placeholder="Enter a name for the copy"
							className="w-full rounded-xl border-2 border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-orange-500 focus:ring-4 focus:ring-orange-500/15"
							autoComplete="off"
						/>
						{name.trim().length > 0 && name.trim() === currentName && (
							<p className="text-xs text-amber-700">
								Name must differ from the current workflow
							</p>
						)}
					</div>

					{/* Action Buttons */}
					<div className="flex flex-col-reverse sm:flex-row gap-3">
						<Button
							type="button"
							onClick={onCancel}
							variant="secondary"
							disabled={isSubmitting}
							className="flex-1 !border-slate-200 !bg-white !text-slate-700 hover:!border-slate-300 hover:!bg-slate-50 hover:!text-slate-900"
						>
							Cancel
						</Button>
						<Button
							type="submit"
							variant="primary"
							disabled={!isValid || isSubmitting}
							loading={isSubmitting}
							className="flex flex-1 items-center justify-center gap-2 !border-orange-500 !bg-orange-500 !text-white hover:!border-orange-600 hover:!bg-orange-600 hover:!text-white"
							icon={<Copy className="w-4 h-4" />}
						>
							Duplicate
						</Button>
					</div>
				</form>
			</div>
		</div>
	);
});

export default DuplicateWorkflowModal;
