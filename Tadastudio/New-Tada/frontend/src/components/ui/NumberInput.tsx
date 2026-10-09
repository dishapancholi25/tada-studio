"use client";

import { ChevronDown, ChevronUp } from "lucide-react";
import React, { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

interface NumberInputProps {
	value: number;
	onChange: (value: number) => void;
	min?: number;
	max?: number;
	step?: number;
	label?: string;
	description?: string;
	className?: string;
	disabled?: boolean;
	/** Light field for white/orange property panels */
	appearance?: "default" | "light";
}

export default function NumberInput({
	value,
	onChange,
	min = 0,
	max = 100,
	step = 1,
	label,
	description,
	className = "",
	disabled = false,
	appearance = "default",
}: NumberInputProps) {
	const isLight = appearance === "light";
	// Generate unique ID for accessibility
	const inputId = React.useId();
	const [localValue, setLocalValue] = useState(value.toString());

	useEffect(() => {
		setLocalValue(value.toString());
	}, [value]);

	const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const newValue = e.target.value;
		setLocalValue(newValue);

		const parsed = parseFloat(newValue);
		if (!isNaN(parsed)) {
			const clamped = Math.min(Math.max(parsed, min), max);
			onChange(clamped);
		}
	};

	const handleBlur = () => {
		const parsed = parseFloat(localValue);
		if (isNaN(parsed)) {
			setLocalValue(value.toString());
		} else {
			const clamped = Math.min(Math.max(parsed, min), max);
			setLocalValue(clamped.toString());
			onChange(clamped);
		}
	};

	const increment = () => {
		const newValue = Math.min(value + step, max);
		onChange(newValue);
	};

	const decrement = () => {
		const newValue = Math.max(value - step, min);
		onChange(newValue);
	};

	return (
		<div className={className}>
			{label && (
				<label
					htmlFor={inputId}
					className={cn(
						"mb-2 block text-sm font-medium",
						isLight ? "text-slate-700" : "text-[color:var(--color-text-secondary)]",
					)}
				>
					{label}
				</label>
			)}
			<div className="relative">
				<input
					id={inputId}
					type="text"
					value={localValue}
					onChange={handleInputChange}
					onBlur={handleBlur}
					disabled={disabled}
					className={
						isLight
							? "w-full rounded-[4px] border border-slate-200 bg-white px-3 py-2.5 pr-10 text-slate-900 transition-all duration-200 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15 disabled:cursor-not-allowed disabled:opacity-50"
							: "w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/50 px-3 py-2.5 pr-10 text-slate-900 transition-all duration-200 hover:bg-[color:var(--color-surface)] focus:border-[color:var(--color-border)] focus:outline-none focus:ring-1 focus:ring-[color:var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-50"
					}
				/>

				{/* Custom Arrow Controls */}
				<div
					className={
						isLight
							? "absolute bottom-1 right-1 top-1 flex flex-col rounded-md border border-slate-200 bg-slate-50"
							: "absolute bottom-1 right-1 top-1 flex flex-col rounded-md border border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/50"
					}
				>
					<button
						onClick={increment}
						disabled={disabled || value >= max}
						className={
							isLight
								? "group relative flex-1 rounded-t-md px-1.5 transition-all duration-200 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-30 active:scale-95"
								: "group relative flex-1 rounded-t-md px-1.5 transition-all duration-200 hover:bg-[color:var(--color-accent)]/20 disabled:cursor-not-allowed disabled:opacity-30 active:scale-95"
						}
						type="button"
					>
						<ChevronUp
							className={
								isLight
									? "h-3.5 w-3.5 text-slate-500 transition-colors group-hover:text-slate-900"
									: "h-3.5 w-3.5 text-[color:var(--color-text-muted)] transition-colors group-hover:text-[color:var(--color-accent)] group-active:text-[color:var(--color-border)]"
							}
						/>
						{!isLight && (
							<div className="pointer-events-none absolute inset-0 rounded-t-md bg-gradient-to-t from-transparent to-[color:var(--color-accent)]/10 opacity-0 transition-opacity group-hover:opacity-100" />
						)}
					</button>
					<div
						className={
							isLight
								? "h-px bg-slate-200"
								: "h-px bg-gradient-to-r from-transparent via-gray-600 to-transparent"
						}
					/>
					<button
						onClick={decrement}
						disabled={disabled || value <= min}
						className={
							isLight
								? "group relative flex-1 rounded-b-md px-1.5 transition-all duration-200 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-30 active:scale-95"
								: "group relative flex-1 rounded-b-md px-1.5 transition-all duration-200 hover:bg-[color:var(--color-accent)]/20 disabled:cursor-not-allowed disabled:opacity-30 active:scale-95"
						}
						type="button"
					>
						<ChevronDown
							className={
								isLight
									? "h-3.5 w-3.5 text-slate-500 transition-colors group-hover:text-slate-900"
									: "h-3.5 w-3.5 text-[color:var(--color-text-muted)] transition-colors group-hover:text-[color:var(--color-accent)] group-active:text-[color:var(--color-border)]"
							}
						/>
						{!isLight && (
							<div className="pointer-events-none absolute inset-0 rounded-b-md bg-gradient-to-b from-transparent to-[color:var(--color-accent)]/10 opacity-0 transition-opacity group-hover:opacity-100" />
						)}
					</button>
				</div>
			</div>
			{description && (
				<p
					className={cn(
						"mt-1 text-xs",
						isLight ? "text-slate-600" : "text-[color:var(--color-text-muted)]",
					)}
				>
					{description}
				</p>
			)}
		</div>
	);
}
