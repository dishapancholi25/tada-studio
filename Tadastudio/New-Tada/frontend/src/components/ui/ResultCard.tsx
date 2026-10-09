"use client";

import { Copy, ExternalLink } from "lucide-react";
import React, { memo } from "react";
import MetaChip from "./MetaChip";

interface ResultCardProps {
	title?: string;
	snippet: string;
	url?: string;
	metadata?: Array<{
		label: string;
		value?: string | number;
		color?: "plum" | "purple" | "gray" | "green" | "red" | "accent";
	}>;
	onExpand?: () => void;
	onOpen?: () => void;
	onCopy?: (text: string) => void;
	showCopy?: boolean;
	showExpand?: boolean;
	clamp?: boolean; // truncate body text with line clamp
}

const ResultCard = memo(function ResultCard({
	title,
	snippet,
	url,
	metadata = [],
	onExpand,
	onOpen,
	onCopy,
	showCopy = true,
	showExpand = true,
	clamp = true,
}: ResultCardProps) {
	const handleCopy = () => {
		const text = snippet;
		if (onCopy) onCopy(text);
		else if (navigator?.clipboard?.writeText) {
			navigator.clipboard.writeText(text).catch((error) => {
				console.error("Failed to copy text:", error);
			});
		}
	};

	const handleOpen = () => {
		if (onOpen) onOpen();
		else if (url) window.open(url, "_blank");
	};

	return (
		<div className="bg-[color:var(--color-surface)]/50 backdrop-blur rounded-lg p-4 hover:bg-[color:var(--color-surface)]/70 transition-all duration-300 border border-[color:var(--color-border)]/50 hover:border-[color:var(--color-surface-hover)]/50 hover:shadow-lg hover:scale-[1.01] transform">
			<div className="flex flex-col gap-3">
				{/* Header row */}
				<div className="flex items-start justify-between gap-3">
					<div className="flex-1 min-w-0">
						{title && (
							<h4
								className="text-slate-900 font-medium text-base mb-1 truncate"
								title={title}
							>
								{title}
							</h4>
						)}
						{url && (
							<a
								href={url}
								target="_blank"
								rel="noopener noreferrer"
								className="text-[color:var(--color-accent)] hover:text-[color:var(--color-border)] text-sm mb-2 block break-all"
							>
								{url}
							</a>
						)}
					</div>
					<div className="flex gap-2 items-center">
						{showCopy && (
							<button
								onClick={handleCopy}
								className="px-2 py-1 rounded bg-[color:var(--color-border)]/60 hover:bg-[color:var(--color-surface-hover)]/60 text-slate-700 text-xs inline-flex items-center gap-1 transition-all duration-200 hover:scale-105 active:scale-95"
								title="Copy snippet"
							>
								<Copy className="w-3 h-3" /> Copy
							</button>
						)}
						{(url || onOpen) && (
							<button
								onClick={handleOpen}
								className="px-2 py-1 rounded bg-[color:var(--color-border)]/60 hover:bg-[color:var(--color-surface-hover)]/60 text-slate-700 text-xs inline-flex items-center gap-1 transition-all duration-200 hover:scale-105 active:scale-95"
								title="Open source"
							>
								<ExternalLink className="w-3 h-3" /> Open
							</button>
						)}
						{onExpand && showExpand && (
							<button
								onClick={onExpand}
								className="px-2.5 py-1 rounded border border-[color:var(--color-border)]/40 text-[color:var(--color-accent)] hover:bg-[color:var(--color-accent)]/10 text-xs font-medium transition-colors"
							>
								Expand
							</button>
						)}
					</div>
				</div>

				{/* Body */}
				<p
					className={`text-[color:var(--color-text-secondary)] text-sm leading-relaxed whitespace-pre-wrap ${clamp ? "line-clamp-6" : ""}`}
				>
					{snippet}
				</p>

				{/* Meta row */}
				{metadata.length > 0 && (
					<div className="flex flex-wrap gap-2 items-center">
						{metadata.map((m, idx) => (
							<MetaChip
								key={`${m.label}-${m.value}-${idx}`}
								label={m.label}
								value={m.value}
								color={m.color || "gray"}
								wrap={m.label === "Source"}
							/>
						))}
					</div>
				)}
			</div>
		</div>
	);
});

export default ResultCard;
