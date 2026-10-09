"use client";

import { X } from "lucide-react";
import type React from "react";

interface ExecutionHeaderProps {
	gradientFrom?: string;
	gradientTo?: string;
	gradientStyle?: React.CSSProperties; // For dynamic color gradients
	icon?: React.ReactNode;
	title: string;
	onClose: () => void;
	statusBar?: React.ReactNode;
}

export default function ExecutionHeader({
	gradientFrom = "from-[color:var(--color-primary)]",
	gradientTo = "to-[color:var(--color-accent)]",
	gradientStyle,
	icon,
	title,
	onClose,
	statusBar,
}: ExecutionHeaderProps) {
	// Use inline style for dynamic gradients, otherwise use Tailwind classes
	// rounded-t-[28px] sits inside the modal's rounded-[30px] border
	const headerClassName = gradientStyle
		? "px-8 py-5 rounded-t-[28px]"
		: `bg-gradient-to-r ${gradientFrom} ${gradientTo} px-8 py-5 rounded-t-[28px]`;

	return (
		<div className={headerClassName} style={gradientStyle}>
			<div className="flex items-center justify-between mb-3">
				<div className="flex items-center gap-4">
					{/* Icon container with subtle background */}
					{icon && (
						<div className="p-2 rounded-xl bg-slate-100 backdrop-blur-sm">
							{icon}
						</div>
					)}
					<h2 className="text-2xl font-semibold text-slate-900 tracking-tight">
						{title}
					</h2>
				</div>
				<button
					onClick={onClose}
					className="p-2 rounded-xl text-slate-700 hover:text-slate-900 hover:bg-slate-100 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
				>
					<X className="w-5 h-5" />
				</button>
			</div>
			{statusBar && (
				<div className="text-slate-700 text-sm flex items-center gap-4 font-medium">
					{statusBar}
				</div>
			)}
		</div>
	);
}
