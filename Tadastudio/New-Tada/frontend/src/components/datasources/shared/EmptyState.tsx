"use client";

import type React from "react";
import Button from "@/components/ui/Button";

interface EmptyStateAction {
	label: string;
	icon?: React.ReactNode;
	onClick: () => void;
	variant?: "primary" | "secondary" | "ghost";
}

interface EmptyStateProps {
	icon: React.ReactNode;
	title: string;
	description: string;
	primaryAction?: EmptyStateAction;
	secondaryAction?: EmptyStateAction;
	className?: string;
}

export default function EmptyState({
	icon,
	title,
	description,
	primaryAction,
	secondaryAction,
	className = "",
}: EmptyStateProps) {
	return (
		<div className={`flex flex-col items-center justify-center py-16 px-6 ${className}`}>
			<div
				className="mb-5 rounded-2xl p-5 text-orange-600"
				style={{
					background: "#f97316",
					border: "1px dashed rgba(249, 115, 22, 0.45)",
				}}
			>
				<div className="flex h-10 w-10 items-center justify-center text-white">
					{icon}
				</div>
			</div>
			<h4 className="mb-2 text-center text-lg font-semibold text-slate-900">{title}</h4>
			<p className="mb-6 max-w-sm text-center text-sm text-slate-600">
				{description}
			</p>
			{(primaryAction || secondaryAction) && (
				<div className="flex items-center gap-3">
					{primaryAction && (
						<Button
							onClick={primaryAction.onClick}
							variant={primaryAction.variant ?? "primary"}
							icon={primaryAction.icon}
						>
							{primaryAction.label}
						</Button>
					)}
					{secondaryAction && (
						<Button
							onClick={secondaryAction.onClick}
							variant={secondaryAction.variant ?? "ghost"}
							icon={secondaryAction.icon}
						>
							{secondaryAction.label}
						</Button>
					)}
				</div>
			)}
		</div>
	);
}
