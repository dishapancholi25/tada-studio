"use client";

import React, { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
	label?: string;
	/** Merged with default label classes (e.g. `text-slate-900` on light surfaces). */
	labelClassName?: string;
	error?: string;
	hint?: string;
	icon?: React.ReactNode;
	themeColor?: "plum" | "purple" | "emerald" | "green" | "red";
}

const FormInput = forwardRef<HTMLInputElement, FormInputProps>(
	(
		{
			className,
			label,
			labelClassName,
			error,
			hint,
			icon,
			themeColor = "plum",
			disabled,
			id,
			...props
		},
		ref,
	) => {
		// Generate unique ID unconditionally (React Rules of Hooks)
		const generatedId = React.useId();
		const inputId = id || (label ? `form-input-${generatedId}` : undefined);
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
						htmlFor={inputId}
						className={cn(
							"block text-sm font-medium text-[var(--color-text-primary)]",
							labelClassName,
						)}
					>
						{label}
					</label>
				)}
				<div className="relative">
					{icon && (
						<div className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-secondary)]">
							{icon}
						</div>
					)}
					<input
						ref={ref}
						id={inputId}
						className={cn(
							"w-full px-4 py-2.5 rounded-lg border",
							"bg-[var(--color-surface)] text-[var(--color-text-primary)]",
							"placeholder-[var(--color-text-secondary)] border-[var(--color-border)]",
							"transition-all duration-200",
							"hover:border-[var(--color-border-hover)]",
							"focus:outline-none focus:ring-2",
							themeClasses[themeColor],
							icon && "pl-10",
							disabled && "opacity-60 cursor-not-allowed",
							error &&
								"border-[#D32F2F] focus:border-[#D32F2F] focus:ring-[rgba(211,47,47,0.2)]",
							className,
						)}
						disabled={disabled}
						{...props}
					/>
				</div>
				{error && (
					<p className="text-xs text-[#D32F2F] animate-fadeIn">{error}</p>
				)}
				{hint && !error && (
					<p className="text-xs text-[var(--color-text-secondary)]">{hint}</p>
				)}
			</div>
		);
	},
);

FormInput.displayName = "FormInput";

export default FormInput;
