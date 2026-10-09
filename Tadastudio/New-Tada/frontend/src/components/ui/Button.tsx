"use client";

import { Loader2 } from "lucide-react";
import type React from "react";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
	variant?: "primary" | "secondary" | "ghost" | "danger" | "success";
	size?: "sm" | "md" | "lg";
	loading?: boolean;
	icon?: React.ReactNode;
	iconPosition?: "left" | "right";
	as?: React.ElementType;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
	(
		{
			className,
			variant = "primary",
			size = "md",
			loading = false,
			icon,
			iconPosition = "left",
			children,
			disabled,
			as: Component = "button",
			...props
		},
		ref,
	) => {
		const baseClasses =
			"inline-flex items-center justify-center font-medium rounded-[4px] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-orange-500/25";

		const variants = {
			// Primary: brand-orange button with white text/icons
			primary:
				"border border-orange-500 bg-orange-500 text-white shadow-md hover:border-orange-600 hover:bg-orange-600 hover:text-white",
			// Secondary: bg #F3F4F9, border #808080, text #242424, hover border #242424
			secondary:
				"bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)] border border-[var(--color-text-secondary)] hover:border-[var(--color-text-primary)]",
			// Ghost: subtle text-only button
			ghost:
				"bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]",
			// Danger/Success keep semantic hues
			danger:
				"bg-[rgba(211,47,47,0.08)] hover:bg-[rgba(211,47,47,0.15)] text-[#D32F2F] border border-[rgba(211,47,47,0.35)] hover:border-[rgba(211,47,47,0.55)]",
			success:
				"bg-[rgba(40,167,69,0.08)] hover:bg-[rgba(40,167,69,0.15)] text-[#28A745] border border-[rgba(40,167,69,0.35)] hover:border-[rgba(40,167,69,0.55)]",
		} as const;

		const sizes = {
			sm: "px-3 py-1.5 text-xs gap-1.5",
			md: "px-4 py-2 text-sm gap-2",
			lg: "px-6 py-3 text-base gap-2.5",
		} as const;

		const isDisabled = disabled || loading;

		const renderIcon = () => {
			if (loading) {
				return (
					<Loader2
						className="animate-spin"
						size={size === "sm" ? 14 : size === "lg" ? 18 : 16}
					/>
				);
			}
			return icon;
		};

		return (
			<Component
				ref={ref}
				className={cn(
					baseClasses,
					variants[variant],
					sizes[size],
					isDisabled && "opacity-50 cursor-not-allowed hover:scale-100",
					className,
				)}
				disabled={isDisabled}
				{...props}
			>
				{iconPosition === "left" && renderIcon()}
				{children}
				{iconPosition === "right" && renderIcon()}
			</Component>
		);
	},
);

Button.displayName = "Button";

export default Button;
