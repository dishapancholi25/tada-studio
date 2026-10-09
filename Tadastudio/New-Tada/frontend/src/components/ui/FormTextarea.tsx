"use client";

import React, { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface FormTextareaProps
	extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
	label?: string;
	labelClassName?: string;
	error?: string;
	hint?: string;
	hintClassName?: string;
	themeColor?: "plum" | "purple" | "emerald" | "green" | "red";
	resizable?: boolean;
}

const FormTextarea = forwardRef<HTMLTextAreaElement, FormTextareaProps>(
	(
		{
			className,
			label,
			labelClassName,
			error,
			hint,
			hintClassName,
			themeColor = "plum",
			resizable = false,
			disabled,
			id,
			...props
		},
		ref,
	) => {
		// Generate unique ID unconditionally (React Rules of Hooks)
		const generatedId = React.useId();
		const textareaId =
			id || (label ? `form-textarea-${generatedId}` : undefined);
		const themeClasses = {
			plum: "focus:border-[var(--color-primary)] focus:ring-[rgba(147,42,143,0.45)]",
			purple:
				"focus:border-[var(--color-primary)] focus:ring-[rgba(147,42,143,0.45)]",
			emerald:
				"focus:border-[var(--color-primary)] focus:ring-[rgba(147,42,143,0.45)]",
			green:
				"focus:border-[var(--color-primary)] focus:ring-[rgba(147,42,143,0.45)]",
			red: "focus:border-[var(--color-primary)] focus:ring-[rgba(147,42,143,0.45)]",
		} as const;

		return (
			<div className="space-y-2">
				{label && (
					<label
						htmlFor={textareaId}
						className={cn(
							"block text-sm font-medium text-[var(--color-text-primary)]",
							labelClassName,
						)}
					>
						{label}
					</label>
				)}
				<textarea
					ref={ref}
					id={textareaId}
					className={cn(
						"w-full px-4 py-2.5 rounded-lg border",
						"bg-[var(--color-surface)] text-[var(--color-text-primary)]",
						"placeholder-[var(--color-text-secondary)] border-[var(--color-border)]",
						"transition-all duration-200",
						"hover:border-[var(--color-border-hover)]",
						"focus:outline-none focus:ring-2",
						themeClasses[themeColor],
						!resizable && "resize-none",
						disabled && "opacity-60 cursor-not-allowed",
						error &&
							"border-[#D32F2F] focus:border-[#D32F2F] focus:ring-[rgba(211,47,47,0.2)]",
						className,
					)}
					disabled={disabled}
					{...props}
				/>
				{error && (
					<p className="text-xs text-[#D32F2F] animate-fadeIn">{error}</p>
				)}
				{hint && !error && (
					<p
						className={cn(
							"text-xs text-[var(--color-text-secondary)]",
							hintClassName,
						)}
					>
						{hint}
					</p>
				)}
			</div>
		);
	},
);

FormTextarea.displayName = "FormTextarea";

export default FormTextarea;
