"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { ImageOff } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

/**
 * Strict sanitization schema for wiki markdown content.
 * Blocks dangerous tags and attributes to prevent XSS attacks.
 *
 * Blocked tags: iframe, object, embed, script, style, form, input
 * Blocked attributes: on*, srcdoc, and other event handlers
 */
const wikiSanitizeSchema = {
	...defaultSchema,
	tagNames: (defaultSchema.tagNames ?? []).filter(
		(tag) => !["iframe", "object", "embed", "script", "style", "form", "input"].includes(tag),
	),
	attributes: {
		...defaultSchema.attributes,
		// Remove srcdoc and all on* event handlers from all elements
		"*": (defaultSchema.attributes?.["*"] ?? []).filter(
			(attr) => {
				if (typeof attr === "string") {
					return attr !== "srcdoc" && !attr.startsWith("on");
				}
				return true;
			},
		),
	},
	// Explicitly strip dangerous attributes that might slip through
	strip: ["script", "style", "iframe", "object", "embed", "form", "input"],
};

const _PROXY_DOMAINS = ["github.com", "githubusercontent.com"];

function WikiImage({ src, alt }: { src?: string; alt?: string }) {
	const [failed, setFailed] = useState(false);

	const proxiedSrc = (() => {
		if (!src) return src;
		try {
			const host = new URL(src).hostname.replace(/^www\./, "");
			if (_PROXY_DOMAINS.some((d) => host === d || host.endsWith(`.${d}`))) {
				return `/api/wiki/image-proxy?url=${encodeURIComponent(src)}`;
			}
		} catch {}
		return src;
	})();

	if (failed || !src) {
		return (
			<span
				className="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs"
				style={{
					background: "var(--color-surface)",
					border: "1px solid var(--color-border)",
					color: "var(--color-text-muted)",
				}}
			>
				<ImageOff className="w-3.5 h-3.5 flex-shrink-0" />
				{alt || "Image unavailable"}
			</span>
		);
	}
	return (
		// biome-ignore lint/a11y/useAltText: alt is passed through from markdown
		<img
			src={proxiedSrc}
			alt={alt}
			loading="lazy"
			className="max-w-full rounded my-2"
			onError={() => setFailed(true)}
		/>
	);
}

const toHeadingId = (children: React.ReactNode) =>
	String(children)
		.toLowerCase()
		.replace(/[^\w\s-]/g, "")
		.replace(/\s+/g, "-");

interface StyledMarkdownProps {
	content: string;
	className?: string;
	/** Light surfaces with dark text (e.g. wiki). Default preserves dark-panel styling. */
	variant?: "default" | "light";
}

export default function StyledMarkdown({
	content,
	className = "",
	variant = "default",
}: StyledMarkdownProps) {
	const light = variant === "light";
	// Check if content contains a References section
	const hasReferences =
		content.includes("\n\nReferences:\n") ||
		content.includes("\n\n**References:**\n");

	// Split content to handle References section specially
	let mainContent = content;
	let referencesContent = "";

	if (hasReferences) {
		const refPattern = /\n\n(References:|[*]{2}References:[*]{2})\n([\s\S]*)/;
		const match = content.match(refPattern);
		if (match) {
			mainContent = content.substring(0, match.index);
			referencesContent = match[2];
		}
	}
	// Function to highlight citations/references
	const highlightReferences = (text: string): React.ReactNode => {
		// Pattern to match citations like [Document.pdf, page 5] or [1]
		const citationPattern = /\[([^\]]+)\]/g;
		const parts = text.split(citationPattern);

		return parts.map((part, index) => {
			// Even indices are regular text, odd indices are citation content
			if (index % 2 === 0) {
				return part;
			} else {
				// This is citation content
				const isFootnote = /^\d+$/.test(part);
				return (
					<span
						key={`citation-${part}-${index}`}
						className={`inline-flex items-center px-2 py-0.5 mx-1 text-xs font-medium rounded-full ${
							isFootnote
								? light
									? "border border-slate-200 bg-slate-100 text-slate-800"
									: "bg-[color:var(--color-text-muted)]/10 text-[color:var(--color-text-muted)] border border-[color:var(--color-text-muted)]/50"
								: light
									? "border border-purple-200 bg-purple-100 text-purple-900"
									: "bg-purple-900/50 text-purple-600 border border-purple-700/50"
						} cursor-help transition-all hover:bg-opacity-70`}
						title={isFootnote ? "Reference footnote" : "Document citation"}
					>
						[{part}]
					</span>
				);
			}
		});
	};

	return (
		<div className={`styled-markdown ${className}`}>
			<ReactMarkdown
				remarkPlugins={[remarkGfm]}
				rehypePlugins={[[rehypeSanitize, wikiSanitizeSchema]]}
				components={{
					// Headings
					h1: ({ children }) => (
						<h1
							id={toHeadingId(children)}
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
							id={toHeadingId(children)}
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
							id={toHeadingId(children)}
							className={
								light
									? "mb-2 mt-4 text-lg font-semibold text-slate-900 first:mt-0"
									: "mb-2 mt-4 text-lg font-semibold text-slate-700 first:mt-0"
							}
						>
							{children}
						</h3>
					),

					// Images (proxied for external domains)
					img: ({ src, alt }) => <WikiImage src={typeof src === "string" ? src : undefined} alt={alt} />,

					// Paragraphs with citation highlighting
					p: ({ children }) => (
						<p
							className={
								light
									? "mb-4 text-slate-800 last:mb-0 leading-relaxed"
									: "mb-4 text-[color:var(--color-text-secondary)] last:mb-0 leading-relaxed"
							}
						>
							{React.Children.map(children, (child) => {
								if (typeof child === "string") {
									return highlightReferences(child);
								}
								return child;
							})}
						</p>
					),

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
						<li
							className={light ? "text-slate-800" : "text-[color:var(--color-text-secondary)]"}
						>
							{React.Children.map(children, (child) => {
								if (typeof child === "string") {
									return highlightReferences(child);
								}
								return child;
							})}
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
									: "border-l-4 border-[rgba(var(--color-primary-rgb),0.4)] pl-4 py-2 mb-4 bg-[color:var(--color-surface)]/50 rounded-r"
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
						<div className="custom-scrollbar mb-4 overflow-x-auto">
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
						<hr className={light ? "my-6 border-slate-200" : "border-[color:var(--color-border)] my-6"} />
					),

					// Strong/Bold with citation support
					strong: ({ children }) => (
						<strong className={light ? "font-semibold text-slate-900" : "font-semibold text-white"}>
							{React.Children.map(children, (child) => {
								if (typeof child === "string") {
									return highlightReferences(child);
								}
								return child;
							})}
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
				{mainContent}
			</ReactMarkdown>

			{hasReferences && referencesContent && (
				<div
					className={
						light
							? "mt-6 border-t border-slate-200 pt-4"
							: "mt-6 border-t border-[color:var(--color-border)] pt-4"
					}
				>
					<h3
						className={
							light
								? "mb-3 flex items-center gap-2 text-sm font-semibold capitalize tracking-wider text-slate-900"
								: "text-sm font-semibold text-[color:var(--color-text-secondary)] mb-3 capitalize tracking-wider flex items-center gap-2"
						}
					>
						<span className={`h-2 w-2 rounded-full ${light ? "bg-orange-500" : "bg-purple-500"}`} />
						References
					</h3>
					<div className="space-y-2 pl-4">
						{referencesContent
							.split("\n")
							.filter((line) => line.trim())
							.map((ref, index) => (
								<div
									key={`ref-${ref.substring(0, 50)}-${index}`}
									className={
										light
											? "flex items-start gap-2 text-sm text-slate-800"
											: "text-sm text-[color:var(--color-text-muted)] flex items-start gap-2"
									}
								>
									<span className={light ? "text-orange-600" : "text-purple-400"}>•</span>
									<span>{highlightReferences(ref)}</span>
								</div>
							))}
					</div>
				</div>
			)}

			<style jsx global>{`
        .styled-markdown {
          /* Smooth scrolling */
          scroll-behavior: smooth;
        }
        
        /* Custom scrollbar for markdown content */
        .styled-markdown::-webkit-scrollbar {
          width: 6px;
        }
        
        .styled-markdown::-webkit-scrollbar-track {
          background: rgba(31, 41, 55, 0.5);
          border-radius: 3px;
        }
        
        .styled-markdown::-webkit-scrollbar-thumb {
          background: rgba(75, 85, 99, 0.8);
          border-radius: 3px;
        }
        
        .styled-markdown::-webkit-scrollbar-thumb:hover {
          background: rgba(107, 114, 128, 0.8);
        }
        
        /* Add some animation to citation highlights */
        @keyframes pulse {
          0% {
            box-shadow: 0 0 0 0 rgba(147, 51, 234, 0.4);
          }
          70% {
            box-shadow: 0 0 0 4px rgba(147, 51, 234, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(147, 51, 234, 0);
          }
        }
        
        .styled-markdown span[title="Document citation"]:hover {
          animation: pulse 1s infinite;
        }
      `}</style>
		</div>
	);
}
