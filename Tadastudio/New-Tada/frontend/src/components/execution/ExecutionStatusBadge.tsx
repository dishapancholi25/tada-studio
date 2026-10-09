"use client";

import {
	CheckCircle,
	Clock,
	type LucideIcon,
	RefreshCw,
	XCircle,
} from "lucide-react";
import React from "react";

interface ExecutionStatusBadgeProps {
	status: string;
	isDarkMode: boolean;
}

export const getStatusInfo = (
	status: string,
): { color: string; icon: LucideIcon; bgColor: string } => {
	switch (status) {
		case "completed":
			return {
				color: "text-[#0DA931]",
				icon: CheckCircle,
				bgColor: "bg-[#0DA931]/10",
			};
		case "failed":
			return { color: "text-red-500", icon: XCircle, bgColor: "bg-red-500/10" };
		case "running":
			return {
				color: "text-[color:var(--color-accent)]",
				icon: RefreshCw,
				bgColor: "bg-[color:var(--color-accent)]/10",
			};
		default:
			return {
				color: "text-[color:var(--color-text-muted)]",
				icon: Clock,
				bgColor: "bg-[color:var(--color-text-muted)]/10",
			};
	}
};

export default function ExecutionStatusBadge({
	status,
	isDarkMode,
}: ExecutionStatusBadgeProps) {
	const statusInfo = getStatusInfo(status);
	const StatusIcon = statusInfo.icon;

	return (
		<span
			className={`flex items-center gap-1 px-2 py-1 rounded-full ${statusInfo.bgColor} ${statusInfo.color}`}
		>
			<StatusIcon className="w-4 h-4" />
			{status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()}
		</span>
	);
}
