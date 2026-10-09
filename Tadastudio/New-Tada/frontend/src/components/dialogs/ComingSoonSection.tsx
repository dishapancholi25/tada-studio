"use client";

import { ChevronRight } from "lucide-react";
import React, { useState } from "react";
import type { ComingSoonTool } from "./ComingSoonToolCard";

interface ComingSoonSectionProps {
	tools: ComingSoonTool[];
}

export default function ComingSoonSection({ tools }: ComingSoonSectionProps) {
	const [isExpanded, setIsExpanded] = useState(false);

	return (
		<div className="space-y-3">
			<button
				type="button"
				onClick={() => setIsExpanded(!isExpanded)}
				className="group flex w-full cursor-pointer items-center justify-between rounded-2xl border border-transparent bg-white p-3.5 text-left shadow-sm transition-all hover:border-orange-400 hover:shadow-md"
			>
				<div className="flex items-center gap-3">
					<div className="text-xs font-semibold capitalize text-slate-600 group-hover:text-slate-900">
						Enterprise Integrations
					</div>
					<span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-0.5 text-[10px] font-medium text-slate-600">
						{tools.length} Coming Soon
					</span>
				</div>
				<ChevronRight
					className={`h-4 w-4 text-slate-500 transition-transform duration-200 group-hover:text-slate-900 ${isExpanded ? "rotate-90" : ""}`}
				/>
			</button>

			<div
				className={`grid grid-cols-2 gap-2 overflow-hidden transition-all duration-200 md:grid-cols-3 ${
					isExpanded
						? "max-h-[300px] opacity-100"
						: "max-h-0 opacity-0"
				}`}
			>
				{tools.map((tool) => (
					<CompactComingSoonCard key={tool.value} tool={tool} />
				))}
			</div>
		</div>
	);
}

function CompactComingSoonCard({ tool }: { tool: ComingSoonTool }) {
	return (
		<div className="flex cursor-not-allowed items-center gap-2.5 rounded-xl border border-slate-200 bg-white p-3 opacity-70 shadow-sm">
			<div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 p-1.5">
				{tool.logo.startsWith("http") ? (
					<img
						src={tool.logo}
						alt={tool.label}
						className="h-4 w-4 opacity-60"
						onError={(e) => {
							const target = e.target as HTMLImageElement;
							target.style.display = "none";
							if (target.parentElement) {
								target.parentElement.innerHTML = `<span class="text-sm">${tool.fallbackEmoji}</span>`;
							}
						}}
					/>
				) : (
					<span className="text-sm opacity-60">{tool.fallbackEmoji}</span>
				)}
			</div>

			<div className="min-w-0 flex-1">
				<div className="truncate text-xs font-medium text-slate-700">
					{tool.label}
				</div>
			</div>

			<span className="flex-shrink-0 rounded-full border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[9px] font-medium text-slate-600">
				Soon
			</span>
		</div>
	);
}
