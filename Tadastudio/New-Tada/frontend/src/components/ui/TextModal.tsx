"use client";

import { X } from "lucide-react";
import React from "react";
import SimpleMarkdown from "../utils/SimpleMarkdown";

interface TextModalProps {
	isOpen: boolean;
	onClose: () => void;
	content?: string;
	text?: string; // Support both 'content' and 'text' props for backward compatibility
	title?: string;
}

function looksLikeMarkdown(text: string) {
	return (
		/^#{1,6}\s/.test(text) ||
		/\n#{1,6}\s/.test(text) ||
		/\n\s*[-*+]\s/.test(text) ||
		/\n\s*\d+\.\s/.test(text) ||
		/```/.test(text) ||
		/\*\*.*\*\*/.test(text) ||
		/__.*__/.test(text) ||
		/\[.*\]\(.*\)/.test(text)
	);
}

export default function TextModal({
	isOpen,
	onClose,
	content,
	text,
	title = "Full Content",
}: TextModalProps) {
	// Use content if provided, otherwise fall back to text prop
	const displayContent = content || text || "";
	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[110] p-4 animate-fadeIn">
			<div className="bg-gradient-to-b from-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)] rounded-xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden border border-[color:var(--color-border)]/50 animate-scaleIn">
				<div className="panel-header px-5 py-4 flex items-center justify-between">
					<div>
						<h3 className="text-lg font-semibold text-slate-900">{title}</h3>
						<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
							Viewing full content
						</p>
					</div>
					<button
						onClick={onClose}
						className="p-2 hover:bg-[color:var(--color-border)]/50 rounded-lg transition-all hover:rotate-90 duration-200"
					>
						<X className="w-5 h-5 text-[color:var(--color-text-muted)]" />
					</button>
				</div>
				<div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)] bg-[color:var(--color-bg-secondary)]/50">
					{looksLikeMarkdown(displayContent) ? (
						<div className="bg-[color:var(--color-bg-secondary)]/70 backdrop-blur-sm border border-[color:var(--color-border)]/50 rounded-lg p-5 shadow-inner">
							<SimpleMarkdown content={displayContent} />
						</div>
					) : (
						<pre className="text-sm text-slate-700 whitespace-pre-wrap bg-[color:var(--color-bg-secondary)]/70 backdrop-blur-sm border border-[color:var(--color-border)]/50 rounded-lg p-5 shadow-inner font-mono">
							{displayContent}
						</pre>
					)}
				</div>
			</div>
		</div>
	);
}
