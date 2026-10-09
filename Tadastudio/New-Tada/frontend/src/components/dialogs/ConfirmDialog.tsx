"use client";

import { AlertTriangle, X } from "lucide-react";
import React from "react";

interface ConfirmDialogProps {
	isOpen: boolean;
	title: string;
	message: string;
	confirmText?: string;
	cancelText?: string;
	onConfirm: () => void;
	onCancel: () => void;
	type?: "danger" | "warning" | "info";
}

export default function ConfirmDialog({
	isOpen,
	title,
	message,
	confirmText = "Confirm",
	cancelText = "Cancel",
	onConfirm,
	onCancel,
	type = "warning",
}: ConfirmDialogProps) {
	if (!isOpen) return null;

	const getIconColor = () => {
		switch (type) {
			case "danger":
				return "text-red-500";
			case "warning":
				return "text-[color:var(--color-accent)]";
			default:
				return "text-[color:var(--color-text-muted)]";
		}
	};

	const getButtonColor = () => {
		switch (type) {
			case "danger":
				return "bg-red-600 hover:bg-red-700";
			case "warning":
				return "bg-[color:var(--color-primary)] hover:bg-[color:var(--color-primary-light)]";
			default:
				return "bg-[color:var(--color-primary)] hover:bg-[color:var(--color-primary-light)] btn-primary-text";
		}
	};

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center">
			{/* Backdrop */}
			<div
				className="absolute inset-0 bg-black/60 backdrop-blur-sm"
				onClick={onCancel}
			/>

			{/* Dialog */}
			<div className="relative mx-4 w-full max-w-md overflow-hidden rounded-lg border border-orange-300 bg-white shadow-2xl">
				<div className="p-6">
					<div className="flex items-start gap-4">
						<div className={`flex-shrink-0 ${getIconColor()}`}>
							<AlertTriangle className="w-6 h-6" />
						</div>

						<div className="flex-1">
							<h3 className="mb-2 text-lg font-semibold text-slate-900">{title}</h3>
							<p className="text-sm text-slate-600">
								{message}
							</p>
						</div>

						<button
							onClick={onCancel}
							className="flex-shrink-0 text-slate-500 transition-colors hover:text-slate-900"
						>
							<X className="w-5 h-5" />
						</button>
					</div>
				</div>

				<div className="flex items-center gap-3 border-t border-orange-200 bg-white px-6 py-4">
					<button
						onClick={onCancel}
						className="flex-1 rounded-[4px] border border-orange-300 bg-white px-4 py-2 font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900"
					>
						{cancelText}
					</button>
					<button
						onClick={() => {
							onConfirm();
							onCancel(); // Close dialog after confirming
						}}
						className={`flex-1 rounded-[4px] px-4 py-2 font-medium text-white transition-colors ${getButtonColor()}`}
					>
						{confirmText}
					</button>
				</div>
			</div>
		</div>
	);
}
