"use client";

import type React from "react";
import { cn } from "@/lib/utils";

interface CardProps {
	children: React.ReactNode;
	className?: string;
	glass?: boolean;
	hover?: boolean;
	glow?: boolean;
	padding?: "none" | "sm" | "md" | "lg";
}

export default function Card({
	children,
	className,
	glass = false,
	hover = false,
	glow = false,
	padding = "md",
}: CardProps) {
	const paddingClasses = {
		none: "",
		sm: "p-3",
		md: "p-5",
		lg: "p-6",
	};

	return (
		<div
			className={cn(
				"rounded-xl transition-all duration-200",
				glass
					? [
							"backdrop-blur-sm",
							"bg-[var(--glass-background)]",
							"border border-[var(--glass-border)]",
							"shadow-[var(--glass-shadow)]",
						]
					: [
							"bg-[var(--color-surface)]",
							"border border-[var(--color-border)]",
						],
				hover && "hover:shadow-lg hover:bg-[var(--color-surface-hover)]",
				glow && "shadow-[0_0_20px_var(--glow-primary)]",
				paddingClasses[padding],
				className,
			)}
		>
			{children}
		</div>
	);
}
