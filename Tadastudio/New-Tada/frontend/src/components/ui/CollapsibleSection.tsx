"use client";

import { ChevronDown } from "lucide-react";
import type React from "react";
import { cn } from "@/lib/utils";
import Card from "./Card";

interface CollapsibleSectionProps {
	title: string;
	icon: React.ReactNode;
	description?: string;
	isOpen: boolean;
	onToggle: () => void;
	children: React.ReactNode;
	badge?: React.ReactNode;
	className?: string;
}

export default function CollapsibleSection({
	title,
	icon,
	description,
	isOpen,
	onToggle,
	children,
	badge,
	className,
}: CollapsibleSectionProps) {
	return (
		<Card
			glass={false}
			padding="none"
			className={cn(
				"overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-sm",
				className,
			)}
		>
			<button
				type="button"
				onClick={onToggle}
				className="group flex w-full items-center justify-between px-5 py-4 transition-colors duration-200 hover:bg-slate-50"
			>
				<div className="flex items-center gap-3">
					<div className="rounded-[4px] border border-gray-200 bg-white p-2 transition-colors group-hover:border-orange-300">
						{icon}
					</div>
					<div className="text-left">
						<h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900">
							{title}
							{badge}
						</h3>
						{description && (
							<p className="mt-0.5 text-xs text-gray-600">{description}</p>
						)}
					</div>
				</div>
				<div
					className={cn(
						"transition-transform duration-200",
						isOpen ? "rotate-180" : "",
					)}
				>
					<ChevronDown className="h-5 w-5 text-gray-500 transition-colors group-hover:text-slate-900" />
				</div>
			</button>
			{isOpen && (
				<div className="animate-slideUp border-t border-gray-200 px-5 pb-5 pt-2">
					{children}
				</div>
			)}
		</Card>
	);
}
