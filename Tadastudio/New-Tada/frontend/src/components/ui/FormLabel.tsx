"use client";

import type React from "react";
import { cn } from "@/lib/utils";
import InfoTooltip from "./InfoTooltipPortal";

interface FormLabelProps {
	children: React.ReactNode;
	required?: boolean;
	tooltip?: string;
	className?: string;
	htmlFor?: string;
}

export default function FormLabel({
	children,
	required,
	tooltip,
	className,
	htmlFor,
}: FormLabelProps) {
	return (
		<label
			htmlFor={htmlFor}
			className={cn(
				"block text-sm font-medium text-[var(--color-text-primary)] mb-2",
				"flex items-center gap-2",
				className,
			)}
		>
			<span>
				{children}
				{required && <span className="text-[#D32F2F] ml-1">*</span>}
			</span>
			{tooltip && <InfoTooltip text={tooltip} />}
		</label>
	);
}
