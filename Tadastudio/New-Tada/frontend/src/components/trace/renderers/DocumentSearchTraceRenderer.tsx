"use client";

import { ChevronDown, ChevronUp, DollarSign, FileText } from "lucide-react";
import React, { useMemo, useState } from "react";

interface DocumentSearchResult {
	content: string;
	metadata?: {
		page?: number;
		relevance?: number;
		confidence?: number;
		source?: string;
	};
	isStructured?: boolean;
}

interface DocumentSearchTraceRendererProps {
	input: any;
	output: any;
	metadata?: any;
}

/**
 * Parse document search results from JSON array format
 */
function parseJSONResults(jsonData: any[]): DocumentSearchResult[] {
	const parsedResults: DocumentSearchResult[] = [];

	jsonData.forEach((item, idx) => {
		const content = item.content || item.text || "";
		const metadata = item.metadata || {};

		// Extract structured data if available
		let enrichedContent = content;
		const additionalData: string[] = [];

		// Look for ticket information
		if (item.ticket_id || metadata.ticket_id) {
			additionalData.push(`Ticket ID: ${item.ticket_id || metadata.ticket_id}`);
		}
		if (item.priority || metadata.priority) {
			additionalData.push(`Priority: ${item.priority || metadata.priority}`);
		}
		if (item.status || metadata.status) {
			additionalData.push(`Status: ${item.status || metadata.status}`);
		}
		if (item.category || metadata.category) {
			additionalData.push(`Category: ${item.category || metadata.category}`);
		}

		// Look for resolution steps
		if (item.resolution_steps || item.steps) {
			const steps = item.resolution_steps || item.steps;
			if (Array.isArray(steps)) {
				additionalData.push("\nResolution Steps:");
				steps.forEach((step: any, i: number) => {
					additionalData.push(`  ${i + 1}. ${step}`);
				});
			}
		}

		// Look for root cause
		if (item.root_cause) {
			additionalData.push(`\nRoot Cause: ${item.root_cause}`);
		}

		// Look for recommendations
		if (item.recommendations) {
			if (Array.isArray(item.recommendations)) {
				additionalData.push("\nRecommendations:");
				item.recommendations.forEach((rec: any) => {
					additionalData.push(`  • ${rec}`);
				});
			}
		}

		// Combine content with additional data
		if (additionalData.length > 0) {
			enrichedContent = content + "\n\n---\n" + additionalData.join("\n");
		}

		parsedResults.push({
			content: enrichedContent,
			metadata: {
				page: metadata.page || metadata.Page,
				relevance: metadata.relevance || metadata.score || metadata.Relevance,
				confidence: metadata.confidence,
				source: item.source || metadata.source || `Document ${idx + 1}`,
			},
			isStructured: true,
		});
	});

	return parsedResults;
}

/**
 * Parse document search results from formatted text
 * Format: "## Retrieved Context\n[1] content...\n## References\n[1] source, Page X, Score: Y"
 */
function parseFormattedText(text: string): DocumentSearchResult[] {
	const parsedResults: DocumentSearchResult[] = [];

	const contextMatch = text.match(
		/## Retrieved Context\n+([\s\S]*?)(?=\n## References|$)/,
	);
	const referencesMatch = text.match(/## References\n+([\s\S]*?)(?=\n## |$)/);

	if (!contextMatch) return parsedResults;

	const contextSection = contextMatch[1];
	const references = new Map<
		string,
		{ source: string; page?: string; score?: number }
	>();

	// Parse references
	if (referencesMatch) {
		const refLines = referencesMatch[1].trim().split("\n");
		refLines.forEach((line) => {
			const refMatch = line.match(
				/\[(\d+)\]\s+([^,]+)(?:,\s*Page\s+(\d+))?(?:,\s*Chunk\s+\d+)?(?:,\s*Score:\s*([\d.]+))?/,
			);
			if (refMatch) {
				references.set(refMatch[1], {
					source: refMatch[2].trim(),
					page: refMatch[3],
					score: refMatch[4] ? parseFloat(refMatch[4]) : undefined,
				});
			}
		});
	}

	// Split by chunk markers
	const chunks = contextSection.split(/(?=\[\d+(?:\.\d+)?\])/);

	chunks.forEach((chunk) => {
		if (!chunk.trim()) return;

		const chunkMatch = chunk.match(/^\[(\d+)(?:\.(\d+))?\]\s*([\s\S]+)/);
		if (chunkMatch) {
			const refNum = chunkMatch[1];
			let content = chunkMatch[3].trim();

			// Extract confidence
			let confidence: number | undefined;
			const confidenceMatch = content.match(/\s*\*Confidence:\s*(\d+)%\*/);
			if (confidenceMatch) {
				confidence = parseInt(confidenceMatch[1]) / 100;
				content = content.replace(confidenceMatch[0], "").trim();
			}

			const ref = references.get(refNum);
			parsedResults.push({
				content,
				metadata: {
					page: ref?.page ? parseInt(ref.page) : undefined,
					relevance: ref?.score || confidence,
					confidence,
					source: ref?.source,
				},
				isStructured: true,
			});
		}
	});

	return parsedResults;
}

/**
 * Parse document search results from various formats
 */
function parseSearchResults(output: any): DocumentSearchResult[] {
	if (!output) return [];

	// Check if output has a 'result' or 'results' field
	let resultData = output;
	if (typeof output === "object") {
		if (output.result) resultData = output.result;
		else if (output.results) resultData = output.results;
	}

	// Try to parse as JSON array
	if (typeof resultData === "string") {
		try {
			const parsed = JSON.parse(resultData);
			if (Array.isArray(parsed)) {
				return parseJSONResults(parsed);
			}
		} catch {
			// Not JSON, try formatted text parsing
		}

		// Try formatted text parsing
		if (
			resultData.includes("## Retrieved Context") ||
			resultData.includes("## Document Search Results")
		) {
			const formatted = parseFormattedText(resultData);
			if (formatted.length > 0) return formatted;
		}

		// Fallback: return as single result
		return [{ content: resultData, isStructured: false }];
	}

	// If already an array
	if (Array.isArray(resultData)) {
		return parseJSONResults(resultData);
	}

	return [];
}

/**
 * Individual result card component
 */
function ResultCard({
	result,
	index,
}: {
	result: DocumentSearchResult;
	index: number;
}) {
	const [expanded, setExpanded] = useState(false);
	const title = result.metadata?.source || `Result ${index + 1}`;
	const shouldClamp = result.content.length > 300;

	return (
		<div className="bg-[color:var(--color-surface)]/40 border border-[color:var(--color-border)]/50 rounded-xl p-4 hover:border-[rgba(var(--color-primary-rgb),0.3)] transition-all duration-200">
			{/* Header */}
			<div className="flex items-start justify-between gap-3 mb-3">
				<h4 className="text-slate-900 font-medium flex-1">{title}</h4>
				{shouldClamp && (
					<button
						onClick={() => setExpanded(!expanded)}
						className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-[color:var(--color-primary)] hover:text-[color:var(--color-primary-light)] bg-[rgba(var(--color-primary-rgb),0.08)] hover:bg-[rgba(var(--color-primary-rgb),0.15)] border border-[rgba(var(--color-primary-rgb),0.2)] rounded-lg transition-all duration-200"
					>
						{expanded ? (
							<>
								<ChevronUp className="w-3 h-3" />
								Collapse
							</>
						) : (
							<>
								<ChevronDown className="w-3 h-3" />
								Expand
							</>
						)}
					</button>
				)}
			</div>

			{/* Content */}
			<p
				className={`text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap leading-relaxed ${
					!expanded && shouldClamp ? "line-clamp-6" : ""
				}`}
			>
				{result.content}
			</p>

			{/* Metadata */}
			{result.metadata && (
				<div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-[color:var(--color-border)]/30">
					{result.metadata.page && (
						<span className="px-2.5 py-1 rounded-lg text-xs bg-[rgba(var(--color-accent-rgb),0.1)] text-[color:var(--color-accent)] border border-[rgba(var(--color-accent-rgb),0.3)] font-medium">
							Page {result.metadata.page}
						</span>
					)}
					{result.metadata.relevance &&
						(!result.metadata.confidence ||
							result.metadata.relevance !== result.metadata.confidence) && (
							<span className="px-2.5 py-1 rounded-lg text-xs bg-[color:var(--color-success)]/10 text-[color:var(--color-success)] border border-[color:var(--color-success)]/30 font-medium font-mono">
								Relevance: {Math.round(result.metadata.relevance * 100)}%
							</span>
						)}
					{result.metadata.confidence && (
						<span className="px-2.5 py-1 rounded-lg text-xs bg-[rgba(var(--color-primary-rgb),0.1)] text-[color:var(--color-primary-light)] border border-[rgba(var(--color-primary-rgb),0.3)] font-medium font-mono">
							Confidence: {Math.round(result.metadata.confidence * 100)}%
						</span>
					)}
				</div>
			)}
		</div>
	);
}

export default function DocumentSearchTraceRenderer({
	input,
	output,
	metadata,
}: DocumentSearchTraceRendererProps) {
	// Extract query from input
	const query = useMemo(() => {
		if (!input) return "";
		if (typeof input === "string") return input;
		if (input.query) return input.query;
		// Sometimes the query is in a nested structure
		if (input.item && input.item.query) return input.item.query;
		return "";
	}, [input]);

	// Extract and parse results from output
	const parsedResults = useMemo((): DocumentSearchResult[] => {
		return parseSearchResults(output);
	}, [output]);

	if (!query && parsedResults.length === 0) {
		return (
			<div className="text-[color:var(--color-text-muted)] text-sm">
				No document search data available
			</div>
		);
	}

	// Extract embedding data from metadata
	const embeddingData = useMemo(() => {
		if (!metadata?.embedding) return null;
		const { tokens, cost, model } = metadata.embedding;
		if (!tokens && !model) return null;
		return { tokens: tokens || 0, cost: cost || 0, model: model || "" };
	}, [metadata]);

	return (
		<div className="space-y-4">
			{/* Query Section */}
			{query && (
				<div className="bg-[rgba(var(--color-primary-rgb),0.08)] border border-[rgba(var(--color-primary-rgb),0.3)] rounded-xl overflow-hidden">
					<div className="px-4 py-3 bg-[rgba(var(--color-primary-rgb),0.15)] border-b border-[rgba(var(--color-primary-rgb),0.3)]">
						<div className="flex items-center gap-2.5">
							<div className="w-6 h-6 rounded-lg border border-[rgba(var(--color-primary-rgb),0.3)] bg-[rgba(var(--color-primary-rgb),0.08)] flex items-center justify-center">
								<FileText className="w-3 h-3 text-[color:var(--color-primary)]" />
							</div>
							<span className="text-xs capitalize font-semibold text-[color:var(--color-primary-light)]">
								Search Query
							</span>
						</div>
					</div>
					<div className="p-4">
						<p className="text-slate-900">{query}</p>
					</div>
				</div>
			)}

			{/* Embedding Cost */}
			{embeddingData && embeddingData.tokens > 0 && (
				<div className="flex items-center gap-2 text-xs text-[color:var(--color-text-muted)] px-4">
					<DollarSign className="w-3 h-3" />
					<span>
						Query embedding: {embeddingData.tokens.toLocaleString()} tokens
						{embeddingData.cost > 0 && ` ($${embeddingData.cost.toFixed(6)})`}
					</span>
				</div>
			)}

			{/* Results Section */}
			{parsedResults.length > 0 && (
				<div className="space-y-3">
					<div className="flex items-center justify-between">
						<h4 className="text-xs capitalize font-semibold text-[color:var(--color-text-secondary)]">
							Document Results ({parsedResults.length})
						</h4>
					</div>
					<div className="space-y-3">
						{parsedResults.map((result, idx) => (
							<ResultCard key={`result-${idx}`} result={result} index={idx} />
						))}
					</div>
				</div>
			)}

			{/* No Results Message */}
			{parsedResults.length === 0 && query && (
				<div className="text-[color:var(--color-text-muted)] text-sm">
					Search executed - no results found
				</div>
			)}
		</div>
	);
}
