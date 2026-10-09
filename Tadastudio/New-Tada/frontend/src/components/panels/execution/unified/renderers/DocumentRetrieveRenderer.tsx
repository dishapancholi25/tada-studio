import {
	AlertCircle,
	BookOpen,
	Check,
	CheckCircle,
	Code,
	Copy,
	Eye,
	FileText,
	Hash,
	LetterText,
	Type,
	WrapText,
} from "lucide-react";
import React from "react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import remarkGfm from "remark-gfm";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import type { DocumentRetrieveExecution } from "../types/execution.types";
import { BaseRenderer } from "./BaseRenderer";

export class DocumentRetrieveRenderer extends BaseRenderer<DocumentRetrieveExecution> {
	state = {
		copiedField: null as string | null,
		wrapLines: true,
		viewMode: "preview" as "preview" | "source",
	};

	getViewModes() {
		return [
			{
				key: "document",
				label: "Document",
				icon: <BookOpen className="w-4 h-4" />,
			},
			{ key: "raw", label: "Raw Data" },
		];
	}

	renderViewMode(mode: string, execution: DocumentRetrieveExecution) {
		switch (mode) {
			case "document":
				return this.renderDocumentView(execution);
			default:
				return (
					<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	handleCopy = async (field: string, value: string) => {
		try {
			await navigator.clipboard.writeText(value);
			this.setState({ copiedField: field });
			setTimeout(() => this.setState({ copiedField: null }), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	};

	private looksLikeMarkdown(text: string): boolean {
		const mdPatterns = [
			/^#{1,6}\s/m,
			/\*\*.*\*\*/,
			/\[.*\]\(.*\)/,
			/^[-*]\s/m,
			/^>\s/m,
			/```/,
			/^\|.*\|$/m,
		];
		let matches = 0;
		for (const pat of mdPatterns) {
			if (pat.test(text)) matches++;
		}
		return matches >= 2;
	}

	private formatNumber(num: number): string {
		return num.toLocaleString();
	}

	renderDocumentView(execution: DocumentRetrieveExecution) {
		const isSuccess = execution.status === "success";
		const documentLabel =
			execution.document_name || execution.document_id || "Document";
		const isMarkdown = this.looksLikeMarkdown(execution.content);

		return (
			<div className="flex -mx-6 -mb-6" style={{ height: "calc(100% + 24px)" }}>
				{/* Left sidebar */}
				<aside className="w-[300px] min-w-[280px] max-w-[320px] border-r border-[color:var(--color-border)]/40 overflow-y-auto custom-scrollbar flex flex-col">
					{/* Status section */}
					<div className="p-5 border-b border-[color:var(--color-border)]/30">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-3">
							Status
						</div>
						<div
							className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl border ${
								isSuccess
									? "border-emerald-500/30 bg-emerald-500/5"
									: "border-red-500/30 bg-red-500/5"
							}`}
						>
							{isSuccess ? (
								<CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
							) : (
								<AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
							)}
							<span
								className={`text-sm font-medium ${isSuccess ? "text-emerald-400" : "text-red-400"}`}
							>
								{isSuccess ? "Retrieved Successfully" : "Retrieval Failed"}
							</span>
						</div>
						{execution.error && (
							<p className="text-xs text-red-400 mt-2 leading-relaxed">
								{execution.error}
							</p>
						)}
					</div>

					{/* Document info section */}
					<div className="p-5 border-b border-[color:var(--color-border)]/30">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-3">
							Document Info
						</div>
						<div className="space-y-3">
							{execution.document_name && (
								<div className="flex items-start gap-2.5">
									<FileText className="w-3.5 h-3.5 text-[color:var(--color-text-muted)] mt-0.5 shrink-0" />
									<div className="min-w-0 flex-1">
										<div className="text-[0.6rem] capitalize tracking-wider text-[color:var(--color-text-muted)]">
											Name
										</div>
										<div className="text-sm text-slate-700 font-medium break-words">
											{execution.document_name}
										</div>
									</div>
								</div>
							)}
							{execution.document_id && (
								<div className="flex items-start gap-2.5">
									<Hash className="w-3.5 h-3.5 text-[color:var(--color-text-muted)] mt-0.5 shrink-0" />
									<div className="min-w-0 flex-1">
										<div className="text-[0.6rem] capitalize tracking-wider text-[color:var(--color-text-muted)]">
											ID
										</div>
										<div className="flex items-center gap-1.5">
											<span className="text-xs text-slate-900 font-mono truncate">
												{execution.document_id}
											</span>
											<button
												onClick={() =>
													this.handleCopy(
														"doc_id",
														execution.document_id || "",
													)
												}
												className="p-1 rounded hover:bg-[color:var(--color-surface)] transition-colors shrink-0"
											>
												{this.state.copiedField === "doc_id" ? (
													<Check className="w-3 h-3 text-emerald-400" />
												) : (
													<Copy className="w-3 h-3 text-[color:var(--color-text-muted)]" />
												)}
											</button>
										</div>
									</div>
								</div>
							)}
							{execution.page_range && (
								<div className="flex items-start gap-2.5">
									<BookOpen className="w-3.5 h-3.5 text-[color:var(--color-text-muted)] mt-0.5 shrink-0" />
									<div className="min-w-0 flex-1">
										<div className="text-[0.6rem] capitalize tracking-wider text-[color:var(--color-text-muted)]">
											Page Range
										</div>
										<div className="text-sm text-slate-700">
											{execution.page_range}
										</div>
									</div>
								</div>
							)}
						</div>
					</div>

					{/* Content stats section */}
					{isSuccess && (
						<div className="p-5 border-b border-[color:var(--color-border)]/30">
							<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-3">
								Content Stats
							</div>
							<div className="space-y-2.5">
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-2 text-[color:var(--color-text-muted)]">
										<LetterText className="w-3.5 h-3.5" />
										<span className="text-xs">Characters</span>
									</div>
									<span className="text-xs text-slate-900 font-mono">
										{this.formatNumber(execution.content_length)}
									</span>
								</div>
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-2 text-[color:var(--color-text-muted)]">
										<Type className="w-3.5 h-3.5" />
										<span className="text-xs">Words</span>
									</div>
									<span className="text-xs text-slate-900 font-mono">
										{this.formatNumber(execution.word_count)}
									</span>
								</div>
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-2 text-[color:var(--color-text-muted)]">
										<Hash className="w-3.5 h-3.5" />
										<span className="text-xs">Lines</span>
									</div>
									<span className="text-xs text-slate-900 font-mono">
										{this.formatNumber(execution.line_count)}
									</span>
								</div>
							</div>
						</div>
					)}

					{/* Processing info section */}
					<div className="p-5 border-b border-[color:var(--color-border)]/30">
						<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-3">
							Processing
						</div>
						<div className="space-y-2.5">
							{execution.timestamp && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-[color:var(--color-text-muted)]">
										Timestamp
									</span>
									<span className="text-xs text-slate-900 font-mono">
										{new Date(execution.timestamp).toLocaleTimeString()}
									</span>
								</div>
							)}
							{execution.duration !== undefined && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-[color:var(--color-text-muted)]">
										Duration
									</span>
									<span className="text-xs text-slate-900 font-mono">
										{execution.duration.toFixed(2)}s
									</span>
								</div>
							)}
							{execution.call_id && (
								<div className="flex items-center justify-between">
									<span className="text-xs text-[color:var(--color-text-muted)]">
										Call ID
									</span>
									<span className="text-[0.65rem] text-slate-900 font-mono truncate max-w-[140px]">
										{execution.call_id}
									</span>
								</div>
							)}
						</div>
					</div>

					{/* Actions - sticky at bottom */}
					{isSuccess && (
						<div className="p-5 mt-auto sticky bottom-0 bg-gradient-to-t from-[rgba(10,10,10,1)] via-[rgba(10,10,10,0.95)] to-transparent pt-8">
							<button
								onClick={() =>
									this.handleCopy("content", execution.content)
								}
								className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium
									border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40
									hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:bg-[color:var(--color-surface-hover)]
									transition-all duration-200
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
							>
								{this.state.copiedField === "content" ? (
									<>
										<Check className="w-4 h-4 text-emerald-400" />
										<span className="text-emerald-400">Copied!</span>
									</>
								) : (
									<>
										<Copy className="w-4 h-4 text-[color:var(--color-text-secondary)]" />
										<span className="text-[color:var(--color-text-secondary)]">
											Copy Content
										</span>
									</>
								)}
							</button>
						</div>
					)}
				</aside>

				{/* Right content area */}
				<main className="flex-1 overflow-hidden flex flex-col">
					{/* Toolbar */}
					<div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--color-border)]/40 bg-[rgba(20,20,20,0.5)]">
						<div className="flex items-center gap-3">
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{documentLabel}
							</span>
							{isMarkdown && (
								<div className="flex rounded-lg border border-[color:var(--color-border)]/60 overflow-hidden">
									<button
										onClick={() => this.setState({ viewMode: "preview" })}
										className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all ${
											this.state.viewMode === "preview"
												? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)]"
												: "text-[color:var(--color-text-secondary)] hover:text-slate-900"
										}`}
									>
										<Eye className="w-3.5 h-3.5" />
										Preview
									</button>
									<button
										onClick={() => this.setState({ viewMode: "source" })}
										className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-all border-l border-[color:var(--color-border)]/60 ${
											this.state.viewMode === "source"
												? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)]"
												: "text-[color:var(--color-text-secondary)] hover:text-slate-900"
										}`}
									>
										<Code className="w-3.5 h-3.5" />
										Source
									</button>
								</div>
							)}
							{!isMarkdown && (
								<button
									onClick={() =>
										this.setState({ wrapLines: !this.state.wrapLines })
									}
									className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all
										border border-[color:var(--color-border)]/60
										${
											this.state.wrapLines
												? "bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary)] border-[rgba(var(--color-primary-rgb),0.3)]"
												: "text-[color:var(--color-text-secondary)] hover:text-slate-900"
										}`}
								>
									<WrapText className="w-3.5 h-3.5" />
									Wrap
								</button>
							)}
						</div>

						<div className="flex items-center gap-2">
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{this.formatNumber(execution.line_count)} lines
							</span>
							<button
								onClick={() =>
									this.handleCopy("content", execution.content)
								}
								className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
									border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)]
									hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
									transition-all"
							>
								{this.state.copiedField === "content" ? (
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
						{!isSuccess ? (
							<div className="flex flex-col items-center justify-center h-full text-center p-6">
								<AlertCircle className="w-12 h-12 text-red-400 mb-4" />
								<p className="text-red-400 font-medium mb-2">
									Document Retrieval Failed
								</p>
								<p className="text-sm text-[color:var(--color-text-muted)] max-w-md">
									{execution.error || "An unknown error occurred"}
								</p>
							</div>
						) : isMarkdown && this.state.viewMode === "preview" ? (
							<div className="p-6 prose prose-invert prose-sm max-w-none">
								<ReactMarkdown
									remarkPlugins={[remarkGfm]}
									components={{
										code({ className, children, ...props }) {
											const match = /language-(\w+)/.exec(
												className || "",
											);
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
										blockquote({ children }) {
											return (
												<blockquote className="border-l-4 border-[color:var(--color-primary)]/50 pl-4 italic text-[color:var(--color-text-secondary)]">
													{children}
												</blockquote>
											);
										},
									}}
								>
									{execution.content}
								</ReactMarkdown>
							</div>
						) : (
							<pre
								className={`p-4 font-mono text-sm text-[color:var(--color-text-secondary)] ${
									this.state.wrapLines
										? "whitespace-pre-wrap break-words"
										: "whitespace-pre"
								}`}
							>
								{execution.content}
							</pre>
						)}
					</div>
				</main>
			</div>
		);
	}

	renderEmptyState() {
		return (
			<div className="flex-1 flex items-center justify-center">
				<div className="text-center">
					<BookOpen className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
					<p className="text-[color:var(--color-text-muted)] font-medium">
						No Documents Retrieved
					</p>
					<p className="text-[color:var(--color-text-muted)] text-sm mt-2">
						This node hasn&apos;t been executed yet
					</p>
				</div>
			</div>
		);
	}
}
