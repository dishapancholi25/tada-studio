"use client";

import { Check, Copy, WrapText } from "lucide-react";
import { useState, useCallback } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { CodeViewerProps } from "../types/fileViewer.types";

export default function CodeViewer({
	content,
	language,
	filename,
}: CodeViewerProps) {
	const [copied, setCopied] = useState(false);
	const [wrapLines, setWrapLines] = useState(false);

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

	// Custom style overrides to match design system
	const customStyle = {
		...vscDarkPlus,
		'pre[class*="language-"]': {
			...vscDarkPlus['pre[class*="language-"]'],
			background: "transparent",
			margin: 0,
			padding: "1rem",
			fontSize: "0.875rem",
		},
		'code[class*="language-"]': {
			...vscDarkPlus['code[class*="language-"]'],
			background: "transparent",
			fontSize: "0.875rem",
		},
	};

	return (
		<div className="h-full flex flex-col">
			{/* Toolbar */}
			<div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--color-border)]/40 bg-[rgba(20,20,20,0.5)]">
				<div className="flex items-center gap-3">
					{/* Language badge */}
					<span className="px-2 py-1 rounded-md bg-[rgba(var(--color-primary-rgb),0.12)] border border-[rgba(var(--color-primary-rgb),0.25)] text-xs font-medium text-[color:var(--color-primary)]">
						{language}
					</span>
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

			{/* Code content */}
			<div className="flex-1 overflow-auto custom-scrollbar bg-[rgba(15,15,15,0.5)]">
				<SyntaxHighlighter
					language={language}
					style={customStyle}
					showLineNumbers
					wrapLines={wrapLines}
					wrapLongLines={wrapLines}
					lineNumberStyle={{
						color: "var(--color-text-muted)",
						opacity: 0.5,
						minWidth: "3em",
						paddingRight: "1em",
						textAlign: "right",
						userSelect: "none",
					}}
					customStyle={{
						margin: 0,
						background: "transparent",
						minHeight: "100%",
					}}
				>
					{content}
				</SyntaxHighlighter>
			</div>
		</div>
	);
}
