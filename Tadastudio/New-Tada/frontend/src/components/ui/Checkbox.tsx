"use client";

import { Check } from "lucide-react";
import type React from "react";
import { type ReactNode, useCallback } from "react";

interface CheckboxProps {
	checked: boolean;
	onChange: (checked: boolean) => void;
	label?: ReactNode;
	description?: string;
	disabled?: boolean;
	variant?: "default" | "purple" | "green" | "plum" | "amber" | "blue";
	size?: "sm" | "md" | "lg";
	className?: string;
}

export default function Checkbox({
	checked,
	onChange,
	label,
	description,
	disabled = false,
	variant = "default",
	size = "md",
	className = "",
}: CheckboxProps) {
	const sizes = {
		sm: {
			box: "w-4 h-4",
			check: "w-2.5 h-2.5",
			label: "text-sm",
			gap: "gap-2",
		},
		md: { box: "w-5 h-5", check: "w-3 h-3", label: "text-sm", gap: "gap-3" },
		lg: { box: "w-6 h-6", check: "w-4 h-4", label: "text-base", gap: "gap-3" },
	};

	const variants = {
		default: {
			unchecked:
				"bg-[color:var(--color-surface)] border-[color:var(--color-surface-hover)] hover:border-[color:var(--color-text-muted)]",
			checked:
				"bg-purple-500 border-purple-500 hover:bg-purple-600 hover:border-purple-600",
			focus: "focus:ring-purple-500/30",
		},
		purple: {
			unchecked:
				"bg-[color:var(--color-surface)] border-[color:var(--color-surface-hover)] hover:border-purple-400",
			checked:
				"bg-purple-500 border-purple-500 hover:bg-purple-600 hover:border-purple-600",
			focus: "focus:ring-purple-500/30",
		},
		green: {
			unchecked:
				"bg-[color:var(--color-surface)] border-[color:var(--color-surface-hover)] hover:border-[#0DA931]",
			checked:
				"bg-[#0DA931] border-[#0DA931] hover:bg-[#0DA931] hover:border-[#0a8f28]",
			focus: "focus:ring-[#0DA931]/30",
		},
		plum: {
			unchecked:
				"bg-[color:var(--color-surface)] border-[color:var(--color-surface-hover)] hover:border-[color:var(--color-border)]",
			checked:
				"bg-[color:var(--color-primary)] border-[color:var(--color-border)] hover:bg-[color:var(--color-primary-light)] hover:border-[color:var(--color-primary-light)]",
			focus: "focus:ring-[color:var(--color-accent)]/30",
		},
		amber: {
			unchecked:
				"bg-[color:var(--color-surface)] border-[color:var(--color-surface-hover)] hover:border-amber-400",
			checked:
				"bg-amber-500 border-amber-500 hover:bg-amber-600 hover:border-amber-600",
			focus: "focus:ring-amber-500/30",
		},
		blue: {
			unchecked:
				"bg-[color:var(--color-surface)] border-[color:var(--color-surface-hover)] hover:border-blue-400",
			checked:
				"bg-blue-500 border-blue-500 hover:bg-blue-600 hover:border-blue-600",
			focus: "focus:ring-blue-500/30",
		},
	};

	const sizeConfig = sizes[size];
	const variantConfig = variants[variant];
	const checkColors = {
		default: "text-white",
		purple: "text-white",
		green: "text-white",
		plum: "text-[color:var(--color-primary-light)]",
		amber: "text-white",
		blue: "text-white",
	} as const;
	const checkColorClass = checkColors[variant];

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			if (!disabled) {
				onChange(e.target.checked);
			}
		},
		[disabled, onChange],
	);

	return (
		<label
			className={`flex items-start ${sizeConfig.gap} cursor-pointer select-none ${
				disabled ? "opacity-50 cursor-not-allowed" : ""
			} ${className}`}
		>
			<div className="relative flex items-center justify-center">
				<input
					type="checkbox"
					checked={checked}
					onChange={handleChange}
					disabled={disabled}
					className="sr-only"
				/>

				{/* Custom Checkbox */}
				<div
					className={`
            ${sizeConfig.box} rounded-md border-2 transition-all duration-200
            flex items-center justify-center relative overflow-hidden
            ${checked ? variantConfig.checked : variantConfig.unchecked}
            ${!disabled ? variantConfig.focus : ""}
            focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-900
          `}
				>
					{/* Background Animation */}
					<div
						className={`absolute inset-0 bg-gradient-to-br from-white/10 to-transparent 
                       transition-transform duration-300 ${
													checked ? "scale-100" : "scale-0"
												}`}
					/>

					{/* Check Icon */}
					<Check
						className={`${sizeConfig.check} ${checkColorClass} stroke-[3] 
                       transition-all duration-200 relative z-10 ${
													checked
														? "scale-100 opacity-100"
														: "scale-0 opacity-0"
												}`}
					/>
				</div>
			</div>

			{/* Label and Description */}
			{(label || description) && (
				<div className="flex-1">
					{label && (
						<span
							className={`${sizeConfig.label} font-medium text-slate-700 
                           ${!disabled ? "group-hover:text-slate-900" : ""}`}
						>
							{label}
						</span>
					)}
					{description && (
						<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
							{description}
						</p>
					)}
				</div>
			)}
		</label>
	);
}
