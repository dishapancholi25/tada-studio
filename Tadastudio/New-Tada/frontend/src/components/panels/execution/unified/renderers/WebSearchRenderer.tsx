import {
	Building,
	Calendar,
	Check,
	ChevronRight,
	Copy,
	ExternalLink,
	FileText,
	Globe,
	Image,
	Search,
	Sparkles,
	User,
} from "lucide-react";
import React, { useState } from "react";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import ResultCard from "../../../../ui/ResultCard";
import type { WebSearchExecution } from "../types/execution.types";
import { BaseRenderer, BaseRendererProps } from "./BaseRenderer";

export class WebSearchRenderer extends BaseRenderer<WebSearchExecution> {
	state = {
		copiedQuery: false,
		expandedResults: new Set<number>(),
	};

	getViewModes() {
		const { executions, selectedIndex } = this.props;
		const currentExecution = executions[selectedIndex];

		const modes = [
			{
				key: "formatted",
				label: "Results",
				icon: <FileText className="w-4 h-4" />,
			},
			{ key: "query", label: "Query", icon: <Search className="w-4 h-4" /> },
			{ key: "raw", label: "Raw Data" },
		];

		// Add images tab if available
		if (
			currentExecution?.results?.images &&
			currentExecution.results.images.length > 0
		) {
			modes.splice(2, 0, {
				key: "images",
				label: `Images (${currentExecution.results.images.length})`,
				icon: <Image className="w-4 h-4" />,
			});
		}

		return modes;
	}

	renderViewMode(mode: string, execution: WebSearchExecution) {
		switch (mode) {
			case "formatted":
				return this.renderFormattedResults(execution);
			case "query":
				return this.renderQueryView(execution);
			case "images":
				return this.renderImages(execution);
			default:
				// Return raw JSON view
				return (
					<div className="bg-slate-50 rounded-lg p-4">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	handleCopyQuery = async (query: string) => {
		try {
			await navigator.clipboard.writeText(query);
			this.setState({ copiedQuery: true });
			setTimeout(() => this.setState({ copiedQuery: false }), 2000);
		} catch (err) {
			console.error("Failed to copy query:", err);
		}
	};

	toggleResultExpanded = (index: number) => {
		const expanded = new Set(this.state.expandedResults);
		if (expanded.has(index)) {
			expanded.delete(index);
		} else {
			expanded.add(index);
		}
		this.setState({ expandedResults: expanded });
	};

	renderQueryView(execution: WebSearchExecution) {
		return (
			<div className="space-y-4">
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden">
					<div className="bg-orange-50 border-b border-slate-200 px-6 py-4">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-3">
								<div className="p-2 rounded-lg bg-orange-100">
									<Search className="w-5 h-5 text-[color:var(--color-primary)]" />
								</div>
								<h4 className="text-[color:var(--color-primary)] font-medium">
									Search Query
								</h4>
							</div>
							<button
								onClick={() => this.handleCopyQuery(execution.query)}
								className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded-lg transition-colors"
							>
								{this.state.copiedQuery ? (
									<>
										<Check className="w-4 h-4 text-[#0DA931]" />
										<span className="text-sm">Copied!</span>
									</>
								) : (
									<>
										<Copy className="w-4 h-4" />
										<span className="text-sm">Copy</span>
									</>
								)}
							</button>
						</div>
					</div>

					<div className="p-6">
						<p className="text-lg text-slate-700 font-medium">
							{execution.query}
						</p>

						{/* Search metadata if available */}
						{execution.search_engine && (
							<div className="mt-4 pt-4 border-t border-slate-200">
								<div className="flex items-center gap-4 text-sm">
									<div className="flex items-center gap-2">
										<Globe className="w-4 h-4 text-slate-500" />
										<span className="text-slate-500">
											Engine:
										</span>
										<span className="text-[color:var(--color-primary)]">
											{execution.search_engine}
										</span>
									</div>
									{execution.timestamp && (
										<div className="flex items-center gap-2">
											<Calendar className="w-4 h-4 text-slate-500" />
											<span className="text-slate-500">
												Searched:
											</span>
											<span className="text-slate-600">
												{new Date(execution.timestamp).toLocaleString()}
											</span>
										</div>
									)}
								</div>
							</div>
						)}
					</div>
				</div>
			</div>
		);
	}

	renderFormattedResults(execution: WebSearchExecution) {
		const results = execution.results?.results || execution.raw_results;
		const hasResults = Array.isArray(results) && results.length > 0;

		return (
			<div className="space-y-4">
				{/* Summary Stats */}
				{hasResults && (
					<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4 bg-orange-50 border border-slate-200">
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-4">
								<div className="p-2 rounded-lg bg-orange-100">
									<Search className="w-5 h-5 text-[color:var(--color-primary)]" />
								</div>
								<div>
									<div className="text-[color:var(--color-primary)] font-medium">
										{results.length} result{results.length !== 1 ? "s" : ""}{" "}
										found
									</div>
									<div className="text-sm text-slate-500">
										for &quot;{execution.query}&quot;
									</div>
								</div>
							</div>
						</div>
					</div>
				)}

				{/* AI Answer (Tavily) */}
				{execution.results?.answer && (
					<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden border border-slate-200">
						<div className="bg-gradient-to-r from-[color:var(--color-primary)]/10 to-[color:var(--color-accent)]/10 px-6 py-4 border-b border-slate-200">
							<h3 className="text-[color:var(--color-primary)] font-medium flex items-center gap-2">
								<Sparkles className="w-5 h-5" />
								AI-Generated Answer
							</h3>
						</div>
						<div className="p-6">
							<p className="text-slate-700 whitespace-pre-wrap leading-relaxed">
								{execution.results.answer}
							</p>
						</div>
					</div>
				)}

				{/* Search Results */}
				{hasResults && (
					<div className="space-y-3">
						<h3 className="text-sm font-medium text-slate-500 capitalize tracking-wider px-1">
							Search Results
						</h3>
						{results.map((result: any, idx: number) =>
							this.renderEnhancedResultCard(result, idx),
						)}
					</div>
				)}

				{/* Formatted Text Fallback */}
				{!hasResults &&
					(execution.formatted_results || execution.formatted_output) && (
						<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-6">
							<pre className="text-slate-600 whitespace-pre-wrap text-sm font-sans leading-relaxed">
								{execution.formatted_results || execution.formatted_output}
							</pre>
						</div>
					)}

				{/* No Results */}
				{!hasResults &&
					!execution.formatted_results &&
					!execution.formatted_output &&
					!execution.results?.answer && (
						<div className="flex-1 flex items-center justify-center">
							<div className="text-center">
								<Search className="w-12 h-12 text-slate-500 mx-auto mb-3" />
								<p className="text-slate-500">
									No results found
								</p>
							</div>
						</div>
					)}
			</div>
		);
	}

	renderEnhancedResultCard(result: any, idx: number) {
		const isExpanded = this.state.expandedResults.has(idx);
		const snippet =
			result.snippet || result.body || result.content || "No snippet available";
		const displaySnippet = isExpanded
			? snippet
			: snippet.substring(0, 200) + (snippet.length > 200 ? "..." : "");

		return (
			<div
				key={result.url || `result-${idx}`}
				className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden hover:border-slate-300 transition-all"
			>
				<div className="p-6">
					{/* Title and URL */}
					<div className="mb-3">
						<h4 className="text-lg font-medium text-slate-700 mb-1">
							{result.title || `Result ${idx + 1}`}
						</h4>
						{result.url && (
							<a
								href={result.url}
								target="_blank"
								rel="noopener noreferrer"
								className="flex items-center gap-1 text-sm text-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] transition-colors"
							>
								<Globe className="w-3 h-3" />
								<span className="truncate">{new URL(result.url).hostname}</span>
								<ExternalLink className="w-3 h-3" />
							</a>
						)}
					</div>

					{/* Snippet */}
					<p className="text-slate-600 text-sm leading-relaxed mb-3">
						{displaySnippet}
					</p>

					{snippet.length > 200 && (
						<button
							onClick={() => this.toggleResultExpanded(idx)}
							className="text-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] text-sm"
						>
							{isExpanded ? "Show less" : "Show more"}
						</button>
					)}

					{/* Metadata */}
					{(result.score ||
						result.position ||
						result.date ||
						result.author) && (
						<div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-slate-200">
							{result.score && (
								<div className="flex items-center gap-1.5 text-xs">
									<span className="text-slate-500">
										Score:
									</span>
									<span className="px-2 py-0.5 bg-orange-100 text-[color:var(--color-primary)] rounded font-medium">
										{result.score.toFixed(2)}
									</span>
								</div>
							)}
							{result.position && (
								<div className="flex items-center gap-1.5 text-xs">
									<span className="text-slate-500">
										Rank:
									</span>
									<span className="px-2 py-0.5 bg-purple-500/10 text-purple-400 rounded font-medium">
										#{result.position}
									</span>
								</div>
							)}
							{result.date && (
								<div className="flex items-center gap-1.5 text-xs">
									<Calendar className="w-3 h-3 text-slate-500" />
									<span className="text-slate-500">
										{result.date}
									</span>
								</div>
							)}
							{result.author && (
								<div className="flex items-center gap-1.5 text-xs">
									<User className="w-3 h-3 text-slate-500" />
									<span className="text-slate-500">
										{result.author}
									</span>
								</div>
							)}
							{result.source && (
								<div className="flex items-center gap-1.5 text-xs">
									<Building className="w-3 h-3 text-slate-500" />
									<span className="text-slate-500">
										{result.source}
									</span>
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		);
	}

	renderImages(execution: WebSearchExecution) {
		const images = execution.results?.images;

		if (!images || images.length === 0) {
			return (
				<div className="flex-1 flex items-center justify-center">
					<div className="text-center">
						<Image className="w-12 h-12 text-slate-500 mx-auto mb-3" />
						<p className="text-slate-500">
							No images found
						</p>
					</div>
				</div>
			);
		}

		return (
			<div className="space-y-4">
				{/* Image count header */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4 bg-orange-50 border border-slate-200">
					<div className="flex items-center gap-3">
						<div className="p-2 rounded-lg bg-orange-100">
							<Image className="w-5 h-5 text-[color:var(--color-primary)]" />
						</div>
						<div>
							<div className="text-[color:var(--color-primary)] font-medium">
								{images.length} image{images.length !== 1 ? "s" : ""} found
							</div>
							<div className="text-sm text-slate-500">
								for &quot;{execution.query}&quot;
							</div>
						</div>
					</div>
				</div>

				{/* Image grid */}
				<div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
					{images.map((image: any, idx: number) => (
						<div
							key={image.image_url || `image-${idx}`}
							className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden hover:border-slate-300 transition-all group"
						>
							<div className="aspect-video bg-slate-100 relative">
								<img
									src={image.thumbnail || image.image_url}
									alt={image.title}
									className="w-full h-full object-cover"
									loading="lazy"
								/>
								<div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
							</div>
							<div className="p-3">
								<p className="text-slate-700 text-sm font-medium truncate mb-1">
									{image.title || `Image ${idx + 1}`}
								</p>
								<a
									href={image.url}
									target="_blank"
									rel="noopener noreferrer"
									className="flex items-center gap-1 text-[color:var(--color-primary)] hover:text-[color:var(--color-primary)] text-xs transition-colors"
								>
									<ExternalLink className="w-3 h-3" />
									View Source
								</a>
							</div>
						</div>
					))}
				</div>
			</div>
		);
	}

	renderEmptyState() {
		return (
			<div className="flex-1 flex items-center justify-center">
				<div className="text-center">
					<div className="p-4 rounded-full bg-orange-100 inline-block mb-4">
						<Globe className="w-12 h-12 text-[color:var(--color-primary)]" />
					</div>
					<p className="text-slate-600 font-medium text-lg">
						No Search Executions
					</p>
					<p className="text-slate-500 text-sm mt-2">
						This web search hasn&apos;t been executed yet
					</p>
				</div>
			</div>
		);
	}
}
