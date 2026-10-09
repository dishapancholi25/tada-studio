"use client";

import { AlertTriangle, X } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import Button from "./Button";

interface ConfirmDialogProps {
	isOpen: boolean;
	onClose: () => void;
	onConfirm: () => void;
	title: string;
	message: string;
	confirmText?: string;
	cancelText?: string;
	variant?: "danger" | "warning" | "info";
	/** Light surface: white card, dark text, Workflow-style (settings tabs). */
	surface?: "theme" | "light";
	/** Render a single acknowledgment button instead of Cancel + Confirm. */
	hideCancel?: boolean;
}

export default function ConfirmDialog({
	isOpen,
	onClose,
	onConfirm,
	title,
	message,
	confirmText = "Confirm",
	cancelText = "Cancel",
	variant = "danger",
	surface = "theme",
	hideCancel = false,
}: ConfirmDialogProps) {
	const [mounted, setMounted] = useState(false);
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, isOpen);

	// Prevent body scroll when modal is open
	useEffect(() => {
		if (isOpen) {
			document.body.style.overflow = "hidden";
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [isOpen]);

	const handleConfirm = () => {
		onConfirm();
		onClose();
	};

	const variantStyles = {
		danger: {
			iconBg: "bg-red-500/10",
			iconColor: "text-red-500",
			buttonBg: "rgb(239, 68, 68)",
			buttonHoverBg: "rgb(220, 38, 38)",
		},
		warning: {
			iconBg: "bg-yellow-500/10",
			iconColor: "text-yellow-500",
			buttonBg: "rgb(245, 158, 11)",
			buttonHoverBg: "rgb(217, 119, 6)",
		},
		info: {
			iconBg: "bg-blue-500/10",
			iconColor: "text-blue-500",
			buttonBg: "var(--color-primary)",
			buttonHoverBg: "var(--color-accent)",
		},
	};

	const style = variantStyles[variant];
	const isLight = surface === "light";

	if (!mounted || !isOpen) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			{/* Backdrop */}
			<div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />

			{/* Dialog */}
			<div
				ref={dialogRef}
				className={`relative w-full max-w-md animate-fadeIn rounded-[4px] border shadow-[0_18px_50px_rgba(15,23,42,0.12)] ${
					isLight ? "border-slate-200 bg-white" : ""
				}`}
				style={
					isLight
						? undefined
						: {
								background: "var(--color-bg-primary)",
								border: "1px solid var(--color-border)",
							}
				}
				onClick={(e) => e.stopPropagation()}
			>
				{/* Header */}
				<div className="flex items-start justify-between p-6 pb-4">
					<div className="flex items-start gap-4">
					<div
						className={`rounded-[4px] p-3 ${isLight ? "border border-slate-200 bg-slate-50" : `rounded-full ${style.iconBg}`}`}
					>
						<AlertTriangle className={`h-6 w-6 ${style.iconColor}`} />
						</div>
						<div>
							<h2
								className={
									isLight
										? "text-xl font-semibold text-slate-900"
										: "text-xl font-semibold text-[var(--color-text-primary)]"
								}
							>
								{title}
							</h2>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className={
							isLight
								? "rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
								: "rounded-lg p-2 transition-colors hover:bg-[var(--color-surface)]"
						}
						style={isLight ? undefined : { color: "var(--color-text-secondary)" }}
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Body */}
				<div className="px-6 pb-6">
					<p
						className={
							isLight
								? "leading-relaxed text-slate-700"
								: "text-[var(--color-text-secondary)] leading-relaxed"
						}
					>
						{message}
					</p>
				</div>

				{/* Footer */}
				<div
					className={`flex items-center justify-end gap-3 border-t p-6 pt-4 ${
						isLight ? "border-slate-200" : "border-[var(--color-border)]"
					}`}
				>
					{!hideCancel && (
						<Button
							onClick={onClose}
							variant="secondary"
							className={
								isLight
									? "!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
									: undefined
							}
						>
							{cancelText}
						</Button>
					)}
					<button
						type="button"
						onClick={handleConfirm}
						className="rounded-[4px] px-4 py-2 font-medium transition-all"
						style={{
							background: style.buttonBg,
							color: "white",
						}}
						onMouseEnter={(e) => {
							e.currentTarget.style.background = style.buttonHoverBg;
						}}
						onMouseLeave={(e) => {
							e.currentTarget.style.background = style.buttonBg;
						}}
					>
						{confirmText}
					</button>
				</div>
			</div>
		</div>,
		document.body,
	);
}
