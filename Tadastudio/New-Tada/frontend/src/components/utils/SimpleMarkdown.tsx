"use client";

import React, { useCallback, useState } from "react";
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface SimpleMarkdownProps {
	content: string;
	className?: string;
	/** Dark text on light background (e.g. wiki preview). Default matches dark panels. */
	variant?: "default" | "light";
}

export default function SimpleMarkdown({
	content,
	className = "",
	variant = "default",
}: SimpleMarkdownProps) {
	const light = variant === "light";
	const [failedImages, setFailedImages] = useState<Set<string>>(new Set());

	const handleImageClick = useCallback((src: string | undefined) => {
		if (typeof window !== "undefined" && src) {
			window.open(src, "_blank");
		}
	}, []);

	const handleImageError = useCallback((src?: string) => {
		if (src) {
			setFailedImages((prev) => new Set(prev).add(src));
		}
	}, []);

	return (
		<div className={`simple-markdown ${className}`}>
			<ReactMarkdown
				remarkPlugins={[remarkGfm]}
				urlTransform={(url) => {
					// Pass through data: URLs untouched (for base64 images)
					if (!url) return url;

					// Handle data URIs (base64 images)
					if (url.startsWith("data:")) {
						return url;
					}

					// Handle blob URLs
					if (url.startsWith("blob:")) {
						return url;
					}

					// Use default sanitizer for everything else
					return defaultUrlTransform(url);
				}}
				components={{
					// Headings
					h1: ({ children }) => (
						<h1
							className={
								light
									? "mb-4 mt-6 text-2xl font-bold text-slate-900 first:mt-0"
									: "mb-4 mt-6 text-2xl font-bold text-white first:mt-0"
							}
						>
							{children}
						</h1>
					),
					h2: ({ children }) => (
						<h2
							className={
								light
									? "mb-3 mt-5 text-xl font-semibold text-slate-900 first:mt-0"
									: "mb-3 mt-5 text-xl font-semibold text-white first:mt-0"
							}
						>
							{children}
						</h2>
					),
					h3: ({ children }) => (
						<h3
							className={
								light
									? "mb-2 mt-4 text-lg font-semibold text-slate-900 first:mt-0"
									: "mb-2 mt-4 text-lg font-semibold text-slate-700 first:mt-0"
							}
						>
							{children}
						</h3>
					),

					// Paragraphs - NO citation highlighting
					p: ({ children }) => {
						// Check if children contains any block-level elements (divs)
						// If so, render as div instead of p to avoid hydration errors
						const hasBlockContent = React.Children.toArray(children).some(
							(child) => React.isValidElement(child) && child.type === "div",
						);

						if (hasBlockContent) {
							return (
								<div
									className={
										light
											? "mb-4 text-slate-800 last:mb-0 leading-relaxed"
											: "mb-4 text-[color:var(--color-text-secondary)] last:mb-0 leading-relaxed"
									}
								>
									{children}
								</div>
							);
						}

						return (
							<p
								className={
									light
										? "mb-4 text-slate-800 last:mb-0 leading-relaxed"
										: "mb-4 text-[color:var(--color-text-secondary)] last:mb-0 leading-relaxed"
								}
							>
								{children}
							</p>
						);
					},

					// Lists
					ul: ({ children }) => (
						<ul
							className={
								light
									? "mb-4 list-inside list-disc space-y-1 pl-4 text-slate-800"
									: "mb-4 list-inside list-disc space-y-1 pl-4 text-[color:var(--color-text-secondary)]"
							}
						>
							{children}
						</ul>
					),
					ol: ({ children }) => (
						<ol
							className={
								light
									? "mb-4 list-inside list-decimal space-y-1 pl-4 text-slate-800"
									: "mb-4 list-inside list-decimal space-y-1 pl-4 text-[color:var(--color-text-secondary)]"
							}
						>
							{children}
						</ol>
					),
					li: ({ children }) => (
						<li className={light ? "text-slate-800" : "text-[color:var(--color-text-secondary)]"}>
							{children}
						</li>
					),

					// Links
					a: ({ href, children }) => (
						<a
							href={href}
							className={
								light
									? "text-orange-700 underline transition-colors hover:text-slate-900"
									: "text-[color:var(--color-accent)] transition-colors hover:text-[color:var(--color-border)] underline"
							}
							target="_blank"
							rel="noopener noreferrer"
						>
							{children}
						</a>
					),

					// Images - support both regular URLs and base64 data URIs
					img: ({ src, alt, ...props }) => {
						const strSrc = typeof src === "string" ? src : "";
						if (!strSrc) return null;

						if (failedImages.has(strSrc)) {
							return (
								<span
									className={
										light
											? "inline-block rounded border border-slate-200 bg-slate-100 p-2 text-sm text-slate-700"
											: "inline-block bg-[color:var(--color-surface)] rounded p-2 text-sm text-[color:var(--color-text-muted)]"
									}
								>
									Failed to load image{alt ? `: ${alt}` : ""}
								</span>
							);
						}

						return (
							<span className="block my-4">
								<img
									{...props}
									src={strSrc}
									alt={alt || "Image"}
									loading="lazy"
									decoding="async"
									className={
										light
											? "h-auto max-w-full cursor-pointer rounded-lg border border-slate-200 shadow-md transition-all hover:border-orange-300"
											: "max-w-full h-auto rounded-lg border border-[color:var(--color-border)] shadow-lg cursor-pointer hover:border-[color:var(--color-surface-hover)] transition-all"
									}
									style={{
										maxHeight: "500px",
										objectFit: "contain",
										display: "block",
									}}
									onClick={() => handleImageClick(strSrc)}
									onError={() => handleImageError(strSrc)}
									title="Click to view full size"
								/>
								{alt && (
									<span
										className={
											light
												? "mt-2 block text-center text-xs italic text-slate-600"
												: "mt-2 block text-center text-xs italic text-[color:var(--color-text-muted)]"
										}
									>
										{alt}
									</span>
								)}
							</span>
						);
					},

					// Code
					code: ({ inline, className, children, ...props }: any) => {
						const match = /language-(\w+)/.exec(className || "");
						return !inline && match ? (
							<SyntaxHighlighter
								style={vscDarkPlus}
								language={match[1]}
								PreTag="div"
								className="rounded-lg mb-4 text-sm"
								{...props}
							>
								{String(children).replace(/\n$/, "")}
							</SyntaxHighlighter>
						) : (
							<code
								className={
									light
										? "rounded bg-slate-100 px-1.5 py-0.5 font-mono text-sm text-slate-900"
										: "bg-[color:var(--color-surface)] text-pink-400 px-1.5 py-0.5 rounded text-sm font-mono"
								}
								{...props}
							>
								{children}
							</code>
						);
					},

					// Blockquotes
					blockquote: ({ children }) => (
						<blockquote
							className={
								light
									? "mb-4 rounded-r border-l-4 border-orange-400 bg-slate-50 py-2 pl-4"
									: "border-l-4 border-[color:var(--color-border)] pl-4 py-2 mb-4 bg-[color:var(--color-surface)]/50 rounded-r"
							}
						>
							<div
								className={
									light
										? "italic text-slate-800"
										: "text-[color:var(--color-text-secondary)] italic"
								}
							>
								{children}
							</div>
						</blockquote>
					),

					// Tables
					table: ({ children }) => (
						<div className="mb-4 overflow-x-auto">
							<table
								className={
									light ? "min-w-full divide-y divide-slate-200" : "min-w-full divide-y divide-gray-700"
								}
							>
								{children}
							</table>
						</div>
					),
					thead: ({ children }) => (
						<thead className={light ? "bg-slate-100" : "bg-[color:var(--color-surface)]"}>
							{children}
						</thead>
					),
					tbody: ({ children }) => (
						<tbody
							className={
								light
									? "divide-y divide-slate-200 bg-white"
									: "bg-[color:var(--color-bg-secondary)] divide-y divide-gray-700"
							}
						>
							{children}
						</tbody>
					),
					tr: ({ children }) => (
						<tr
							className={
								light ? "transition-colors hover:bg-slate-50" : "hover:bg-[color:var(--color-surface)] transition-colors"
							}
						>
							{children}
						</tr>
					),
					th: ({ children }) => (
						<th
							className={
								light
									? "px-4 py-2 text-left text-xs font-medium capitalize tracking-wider text-slate-800"
									: "px-4 py-2 text-left text-xs font-medium text-[color:var(--color-text-muted)] capitalize tracking-wider"
							}
						>
							{children}
						</th>
					),
					td: ({ children }) => (
						<td
							className={
								light
									? "px-4 py-2 text-sm text-slate-800"
									: "px-4 py-2 text-sm text-[color:var(--color-text-secondary)]"
							}
						>
							{children}
						</td>
					),

					// Horizontal rule
					hr: () => (
						<hr className={light ? "my-6 border-slate-200" : "my-6 border-[color:var(--color-border)]"} />
					),

					// Strong/Bold - NO citation highlighting
					strong: ({ children }) => (
						<strong className={light ? "font-semibold text-slate-900" : "font-semibold text-white"}>
							{children}
						</strong>
					),

					// Emphasis/Italic
					em: ({ children }) => (
						<em className={light ? "italic text-slate-800" : "italic text-[color:var(--color-text-secondary)]"}>
							{children}
						</em>
					),
				}}
			>
				{content}
			</ReactMarkdown>
		</div>
	);
}
