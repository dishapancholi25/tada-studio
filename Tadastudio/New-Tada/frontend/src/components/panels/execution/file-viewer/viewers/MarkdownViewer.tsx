"use client";

import { Check, Code, Copy, Eye } from "lucide-react";
import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import remarkGfm from "remark-gfm";
import type { MarkdownViewerProps } from "../types/fileViewer.types";

export default function MarkdownViewer({
	content,
	filename,
}: MarkdownViewerProps) {
	const [copied, setCopied] = useState(false);
	const [viewMode, setViewMode] = useState<"preview" | "source">("preview");

	const handleCopy = useCallback(async () => {
		try {
			await navigator.clipboard.writeText(content);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	}, [content]);

	return (
		<div className="h-full flex flex-col">
			{/* Toolbar */}
			<div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--color-border)]/40 bg-[rgba(20,20,20,0.5)]">
				<div className="flex items-center gap-2">
					{/* View mode toggle */}
					<div className="flex rounded-lg border border-[color:var(--color-border)]/60 overflow-hidden">
						<button
							onClick={() => setViewMode("preview")}
							className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all ${
								viewMode === "preview"
									? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)]"
									: "text-[color:var(--color-text-secondary)] hover:text-slate-900"
							}`}
						>
							<Eye className="w-3.5 h-3.5" />
							Preview
						</button>
						<button
							onClick={() => setViewMode("source")}
							className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all border-l border-[color:var(--color-border)]/60 ${
								viewMode === "source"
									? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)]"
									: "text-[color:var(--color-text-secondary)] hover:text-slate-900"
							}`}
						>
							<Code className="w-3.5 h-3.5" />
							Source
						</button>
					</div>
				</div>

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

			{/* Content */}
			<div className="flex-1 overflow-auto custom-scrollbar">
				{viewMode === "preview" ? (
					<div className="p-6 prose prose-invert prose-sm max-w-none">
						<ReactMarkdown
							remarkPlugins={[remarkGfm]}
							components={{
								code({ node, className, children, ...props }) {
									const match = /language-(\w+)/.exec(className || "");
									const isInline = !match;
									return !isInline && match ? (
										<SyntaxHighlighter
											style={vscDarkPlus}
											language={match[1]}
											PreTag="div"
											customStyle={{
												margin: 0,
												borderRadius: "0.5rem",
												fontSize: "0.8125rem",
											}}
										>
											{String(children).replace(/\n$/, "")}
										</SyntaxHighlighter>
									) : (
										<code
											className="px-1.5 py-0.5 rounded bg-[color:var(--color-surface)] text-[color:var(--color-primary)] text-sm"
											{...props}
										>
											{children}
										</code>
									);
								},
								a({ href, children }) {
									return (
										<a
											href={href}
											target="_blank"
											rel="noopener noreferrer"
											className="text-[color:var(--color-primary)] hover:underline"
										>
											{children}
										</a>
									);
								},
								table({ children }) {
									return (
										<div className="overflow-x-auto">
											<table className="min-w-full border border-[color:var(--color-border)]/50 rounded-lg overflow-hidden">
												{children}
											</table>
										</div>
									);
								},
								th({ children }) {
									return (
										<th className="px-4 py-2 bg-[color:var(--color-surface)]/50 text-left text-sm font-semibold text-slate-900 border-b border-[color:var(--color-border)]/50">
											{children}
										</th>
									);
								},
								td({ children }) {
									return (
										<td className="px-4 py-2 text-sm text-[color:var(--color-text-secondary)] border-b border-[color:var(--color-border)]/30">
											{children}
										</td>
									);
								},
								img({ src, alt }) {
									return (
										<img
											src={src}
											alt={alt || ""}
											className="max-w-full h-auto rounded-lg border border-[color:var(--color-border)]/30"
										/>
									);
								},
								blockquote({ children }) {
									return (
										<blockquote className="border-l-4 border-[color:var(--color-primary)]/50 pl-4 italic text-[color:var(--color-text-secondary)]">
											{children}
										</blockquote>
									);
								},
							}}
						>
							{content}
						</ReactMarkdown>
					</div>
				) : (
					<pre className="p-4 font-mono text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap">
						{content}
					</pre>
				)}
			</div>
		</div>
	);
}
