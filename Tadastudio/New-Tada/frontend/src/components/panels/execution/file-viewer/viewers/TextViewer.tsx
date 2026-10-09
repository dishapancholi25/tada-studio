"use client";

import { Check, Copy, WrapText } from "lucide-react";
import { useState, useCallback } from "react";
import type { TextViewerProps } from "../types/fileViewer.types";

export default function TextViewer({ content, filename }: TextViewerProps) {
	const [copied, setCopied] = useState(false);
	const [wrapLines, setWrapLines] = useState(true);

	const handleCopy = useCallback(async () => {
		try {
			await navigator.clipboard.writeText(content);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	}, [content]);

	const lineCount = content.split("\n").length;

	return (
		<div className="h-full flex flex-col">
			{/* Toolbar */}
			<div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--color-border)]/40 bg-[rgba(20,20,20,0.5)]">
				<div className="flex items-center gap-3">
					<span className="text-xs text-[color:var(--color-text-muted)]">
						{lineCount.toLocaleString()} lines
					</span>
				</div>

				<div className="flex items-center gap-2">
					{/* Wrap lines toggle */}
					<button
						onClick={() => setWrapLines(!wrapLines)}
						className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
							wrapLines
								? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)] border border-[rgba(var(--color-primary-rgb),0.3)]"
								: "border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)] hover:border-[rgba(var(--color-primary-rgb),0.4)]"
						}`}
					>
						<WrapText className="w-3.5 h-3.5" />
						Wrap
					</button>

					{/* Copy button */}
					<button
						onClick={handleCopy}
						className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
							border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)]
							hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
							transition-all"
					>
						{copied ? (
							<>
								<Check className="w-3.5 h-3.5 text-emerald-400" />
								Copied!
							</>
						) : (
							<>
								<Copy className="w-3.5 h-3.5" />
								Copy
							</>
						)}
					</button>
				</div>
			</div>

			{/* Content */}
			<div className="flex-1 overflow-auto custom-scrollbar">
				<pre
					className={`p-4 font-mono text-sm text-[color:var(--color-text-secondary)] min-h-full ${
						wrapLines ? "whitespace-pre-wrap break-words" : "whitespace-pre"
					}`}
				>
					{content}
				</pre>
			</div>
		</div>
	);
}
