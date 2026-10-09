"use client";

import type React from "react";
import { useCallback } from "react";
import { cn } from "@/lib/utils";

interface ToggleProps {
	checked: boolean;
	onChange: (checked: boolean) => void;
	label?: string;
	/** Extra classes for the label text (e.g. `text-slate-900` on light surfaces). */
	labelClassName?: string;
	disabled?: boolean;
	size?: "sm" | "md" | "lg";
	activeColor?: string;
}

export default function Toggle({
	checked,
	onChange,
	label,
	labelClassName,
	disabled = false,
	size = "md",
	activeColor,
}: ToggleProps) {
	const sizes = {
		sm: { toggle: "w-8 h-4", dot: "w-3 h-3", translate: "translate-x-4" },
		md: { toggle: "w-11 h-6", dot: "w-5 h-5", translate: "translate-x-5" },
		lg: { toggle: "w-14 h-7", dot: "w-6 h-6", translate: "translate-x-7" },
	};

	const sizeConfig = sizes[size];

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
			className={`flex items-center gap-2 cursor-pointer ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
		>
			<div className="relative">
				<input
					type="checkbox"
					className="sr-only"
					checked={checked}
					onChange={handleChange}
					disabled={disabled}
				/>
				<div
					className={`${sizeConfig.toggle} rounded-full transition-all duration-200 relative ${
						checked && !activeColor
							? "bg-gradient-to-r from-[color:var(--color-primary)] to-[color:var(--color-accent)]"
							: !checked
								? "bg-[color:var(--color-border)]"
								: ""
					}`}
					style={checked && activeColor ? { backgroundColor: activeColor } : undefined}
				>
					<div
						className={`${sizeConfig.dot} bg-white rounded-full shadow-lg transform transition-transform duration-200 absolute top-1/2 -translate-y-1/2 ${
							checked ? sizeConfig.translate : "translate-x-0.5"
						}`}
					/>
				</div>
			</div>
			{label && (
				<span
					className={cn(
						"select-none text-sm text-[color:var(--color-text-secondary)]",
						labelClassName,
					)}
				>
					{label}
				</span>
			)}
		</label>
	);
}
