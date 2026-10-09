"use client";

import { ExternalLink, Search, Star } from "lucide-react";
import React, { useMemo } from "react";

interface WebSearchResult {
	position: number;
	title: string;
	url: string;
	snippet: string;
	score: number | null;
}

interface WebSearchTraceRendererProps {
	input: any;
	output: any;
}

/**
 * Parse web search results from formatted text string.
 * Reuses logic from executionParser.ts
 */
function parseWebSearchResultsString(
	text: string,
): { results: WebSearchResult[] } | null {
	if (!text || typeof text !== "string") return null;

	// Check if this looks like a formatted search results string
	if (!text.includes("Search Results") && !text.match(/^\d+\./m)) {
		return null;
	}

	const results: WebSearchResult[] = [];
	const lines = text.split("\n");
	let currentResult: any = null;
	let currentContent = "";

	for (let i = 0; i < lines.length; i++) {
		const line = lines[i];

		// Check for result number (e.g., "1. Title")
		const resultMatch = line.match(/^(\d+)\.\s+(.+)$/);
		if (resultMatch) {
			// Save previous result if exists
			if (currentResult) {
				currentResult.snippet = currentContent.trim();
				results.push(currentResult);
			}

			// Start new result
			currentResult = {
				position: parseInt(resultMatch[1]),
				title: resultMatch[2],
				url: "",
				snippet: "",
				score: null,
			};
			currentContent = "";
			continue;
		}

		// Check for URL
		const urlMatch = line.match(/^\s+URL:\s+(.+)$/);
		if (urlMatch && currentResult) {
			currentResult.url = urlMatch[1];
			continue;
		}

		// Check for Relevance/Score
		const relevanceMatch = line.match(/^\s+Relevance:\s+([\d.]+)$/);
		if (relevanceMatch && currentResult) {
			currentResult.score = parseFloat(relevanceMatch[1]);
			continue;
		}

		// Otherwise, it's content for the snippet
		if (currentResult && line.trim() && !line.startsWith("Search Results")) {
			currentContent += line.trim() + " ";
		}
	}

	// Save last result
	if (currentResult) {
		currentResult.snippet = currentContent.trim();
		results.push(currentResult);
	}

	return results.length > 0 ? { results } : null;
}

export default function WebSearchTraceRenderer({
	input,
	output,
}: WebSearchTraceRendererProps) {
	// Extract query from input
	const query = useMemo(() => {
		if (!input) return "";
		if (typeof input === "string") return input;
		if (input.query) return input.query;
		return JSON.stringify(input);
	}, [input]);

	// Extract and parse results from output
	const parsedResults = useMemo((): WebSearchResult[] | null => {
		if (!output) return null;

		// Check if output has results or result field
		const resultsText = output.results || output.result || output;

		// If it's a string, try to parse it
		if (typeof resultsText === "string") {
			const parsed = parseWebSearchResultsString(resultsText);
			if (parsed) return parsed.results;
		}

		// If it's already an object with results array
		if (
			resultsText &&
			typeof resultsText === "object" &&
			Array.isArray(resultsText.results)
		) {
			return resultsText.results as WebSearchResult[];
		}

		return null;
	}, [output]);

	if (!query && !parsedResults) {
		return (
			<div className="text-[color:var(--color-text-muted)] text-sm">
				No web search data available
			</div>
		);
	}

	return (
		<div className="space-y-4">
			{/* Query Section */}
			{query && (
				<div className="bg-[rgba(var(--color-primary-rgb),0.08)] border border-[rgba(var(--color-primary-rgb),0.3)] rounded-xl p-4">
					<div className="flex items-start gap-3">
						<div className="w-8 h-8 rounded-lg border border-[rgba(var(--color-primary-rgb),0.3)] bg-[rgba(var(--color-primary-rgb),0.08)] flex items-center justify-center flex-shrink-0">
							<Search className="w-4 h-4 text-[color:var(--color-primary)]" />
						</div>
						<div className="flex-1 min-w-0">
							<div className="text-[0.65rem] capitalize text-[color:var(--color-primary-light)] font-semibold mb-1.5">
								Search Query
							</div>
							<div className="text-slate-900">{query}</div>
						</div>
					</div>
				</div>
			)}

			{/* Results Section */}
			{parsedResults && parsedResults.length > 0 && (
				<div className="space-y-3">
					<div className="text-xs capitalize font-semibold text-[color:var(--color-text-secondary)]">
						Results ({parsedResults.length})
					</div>
					<div className="space-y-3">
						{parsedResults.map((result, index) => (
							<div
								key={index}
								className="bg-[color:var(--color-surface)]/40 border border-[color:var(--color-border)]/50 rounded-xl p-4 hover:border-[rgba(var(--color-primary-rgb),0.3)] transition-all duration-200"
							>
								{/* Title and Position */}
								<div className="flex items-start gap-3 mb-2">
									<div className="flex items-center justify-center w-6 h-6 bg-[color:var(--color-surface)] border border-[color:var(--color-border)]/60 rounded-lg text-xs text-[color:var(--color-text-secondary)] flex-shrink-0 font-mono">
										{result.position}
									</div>
									<h4 className="text-slate-900 font-medium flex-1 line-clamp-2">
										{result.title}
									</h4>
									{result.score !== null && (
										<div className="flex items-center gap-1 text-xs text-[color:var(--color-warning)] flex-shrink-0">
											<Star className="w-3 h-3 fill-current" />
											<span className="font-mono">
												{(result.score * 100).toFixed(0)}%
											</span>
										</div>
									)}
								</div>

								{/* URL */}
								{result.url && (
									<a
										href={result.url}
										target="_blank"
										rel="noopener noreferrer"
										className="flex items-center gap-1.5 text-sm text-[color:var(--color-primary)] hover:text-[color:var(--color-primary-light)] mb-2 group transition-colors"
									>
										<span className="truncate">{result.url}</span>
										<ExternalLink className="w-3 h-3 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
									</a>
								)}

								{/* Snippet */}
								{result.snippet && (
									<p className="text-sm text-[color:var(--color-text-muted)] line-clamp-3">
										{result.snippet}
									</p>
								)}
							</div>
						))}
					</div>
				</div>
			)}

			{/* No Results Message */}
			{parsedResults && parsedResults.length === 0 && (
				<div className="text-[color:var(--color-text-muted)] text-sm">
					No search results found
				</div>
			)}
		</div>
	);
}
