"use client";

import type React from "react";
import { cn } from "@/lib/utils";

type IconButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
	ariaLabel: string;
	variant?: "ghost" | "secondary" | "danger" | "primary";
	size?: "sm" | "md";
};

export default function IconButton({
	ariaLabel,
	className,
	variant = "ghost",
	size = "md",
	...props
}: IconButtonProps) {
	const base =
		"inline-flex items-center justify-center rounded-lg transition-colors focus:outline-none focus:ring-2";
	const sizes = {
		sm: "w-8 h-8",
		md: "w-9 h-9",
	} as const;
	const variants = {
		ghost:
			"bg-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)]",
		secondary:
			"bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)] border border-[var(--color-text-secondary)] hover:border-[var(--color-text-primary)]",
		primary:
			"bg-[var(--color-primary)] text-[var(--color-text-primary)] border border-[var(--color-primary-dark)]",
		danger:
			"bg-[rgba(211,47,47,0.08)] text-[#D32F2F] border border-[rgba(211,47,47,0.35)] hover:bg-[rgba(211,47,47,0.15)]",
	} as const;

	return (
		<button
			aria-label={ariaLabel}
			className={cn(base, sizes[size], variants[variant], className)}
			{...props}
		/>
	);
}
