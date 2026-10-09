"use client";

import type { ReactNode } from "react";
import { twMerge } from "tailwind-merge";

interface CardProps {
	children: ReactNode;
	className?: string;
	/** Removes default padding when a child needs to control its own spacing. */
	noPadding?: boolean;
}

/**
 * Reusable white card container matching the reference design:
 * white background, subtle 1px border, soft shadow, rounded corners.
 *
 * Uses twMerge so callers can override base classes (e.g. tinted backgrounds)
 * without Tailwind stylesheet-order conflicts.
 */
export default function Card({ children, className = "", noPadding = false }: CardProps) {
	return (
		<div
			className={twMerge(
				"rounded-xl border border-[#E0E0E0] bg-white shadow-[0px_8px_12px_rgba(0,0,0,0.1)]",
				noPadding ? "" : "p-4 sm:p-5",
				className,
			)}
		>
			{children}
		</div>
	);
}
