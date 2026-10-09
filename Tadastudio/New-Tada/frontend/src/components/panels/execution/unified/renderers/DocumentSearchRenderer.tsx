import { Brain, ChevronRight, Cpu, DollarSign, FileText, Zap } from "lucide-react";
import React from "react";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import ResultCard from "../../../../ui/ResultCard";
import TextModal from "../../../../ui/TextModal";
import {
	type DocumentSearchParsedResult,
	parseDocumentSearchResults,
} from "../../utils/parseDocumentSearchResults";
import type { DocumentSearchExecution } from "../types/execution.types";
import { BaseRenderer } from "./BaseRenderer";

export class DocumentSearchRenderer extends BaseRenderer<DocumentSearchExecution> {
	state = {
		expandedText: { open: false, text: "", title: "" },
	};

	getViewModes() {
		const modes: Array<{
			key: string;
			label: string;
			icon?: React.ReactNode;
		}> = [
			{
				key: "formatted",
				label: "Formatted Results",
				icon: <FileText className="w-4 h-4" />,
			},
		];

		// Show Model tab when we have embedding data
		const currentExecution = this.props.executions[this.props.selectedIndex];
		if (
			currentExecution?.embedding_tokens ||
			currentExecution?.embedding_model
		) {
			modes.push({
				key: "model",
				label: "Model",
				icon: <Brain className="w-4 h-4" />,
			});
		}

		modes.push({ key: "raw", label: "Raw Data" });
		return modes;
	}

	renderViewMode(mode: string, execution: DocumentSearchExecution) {
		switch (mode) {
			case "formatted":
				return this.renderFormattedResults(execution);
			case "model":
				return this.renderModelDetails(execution);
			default:
				// Return raw JSON view
				return (
					<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	private renderModelDetails(execution: DocumentSearchExecution) {
		const hasTokens =
			execution.embedding_tokens != null && execution.embedding_tokens > 0;
		const hasCost =
			execution.embedding_cost != null && execution.embedding_cost > 0;
		const modelName = execution.embedding_model || "text-embedding-3-small";

		return (
			<div className="space-y-4">
				{/* Model Configuration */}
				<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
					<div className="flex items-center gap-3 mb-4 pb-3 border-b border-[color:var(--color-border)]/30">
						<div className="p-1.5 rounded-lg bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/20">
							<Cpu className="w-3 h-3 text-[color:var(--color-primary)]" />
						</div>
						<span className="text-xs font-semibold text-[color:var(--color-text-secondary)] capitalize tracking-wider">
							Embedding Model
						</span>
					</div>
					<div className="space-y-2.5 text-sm">
						<div className="flex justify-between">
							<span className="text-[color:var(--color-text-muted)]">
								Model
							</span>
							<span className="text-slate-900 font-mono">{modelName}</span>
						</div>
						<div className="flex justify-between">
							<span className="text-[color:var(--color-text-muted)]">
								Type
							</span>
							<span className="text-slate-900">Embedding</span>
						</div>
					</div>
				</div>

				{/* Token Usage */}
				{hasTokens && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="flex items-center gap-3 mb-4 pb-3 border-b border-[color:var(--color-border)]/30">
							<div className="p-1.5 rounded-lg bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/20">
								<Zap className="w-3 h-3 text-[color:var(--color-primary)]" />
							</div>
							<span className="text-xs font-semibold text-[color:var(--color-text-secondary)] capitalize tracking-wider">
								Token Usage
							</span>
						</div>
						<div className="space-y-2.5 text-sm">
							<div className="flex justify-between">
								<span className="text-[color:var(--color-text-muted)]">
									Query Tokens
								</span>
								<span className="text-slate-900 font-mono">
									{execution.embedding_tokens?.toLocaleString()}
								</span>
							</div>
						</div>
					</div>
				)}

				{/* Cost Breakdown */}
				{hasCost && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="flex items-center gap-3 mb-4 pb-3 border-b border-[color:var(--color-border)]/30">
							<div className="p-1.5 rounded-lg bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/20">
								<DollarSign className="w-3 h-3 text-[color:var(--color-primary)]" />
							</div>
							<span className="text-xs font-semibold text-[color:var(--color-text-secondary)] capitalize tracking-wider">
								Cost Breakdown
							</span>
						</div>
						<div className="space-y-2.5 text-sm">
							<div className="flex justify-between">
								<span className="text-[color:var(--color-text-muted)]">
									Embedding Cost
								</span>
								<span className="text-slate-900 font-mono">
									${execution.embedding_cost?.toFixed(6)}
								</span>
							</div>
							<div className="flex justify-between text-sm font-medium mt-3 pt-3 border-t border-[color:var(--color-border)]/30">
								<span className="text-[color:var(--color-text-secondary)]">
									Total
								</span>
								<span className="text-[color:var(--color-primary)] font-mono">
									${execution.embedding_cost?.toFixed(6)}
								</span>
							</div>
						</div>
					</div>
				)}

				{/* No data state */}
				{!hasTokens && !hasCost && (
					<div className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 p-5 shadow-[0_20px_55px_rgba(0,0,0,0.55)]">
						<div className="flex flex-col items-center justify-center h-24 gap-2">
							<Brain className="w-5 h-5 text-[color:var(--color-text-muted)]" />
							<span className="text-sm text-[color:var(--color-text-muted)]">
								No embedding cost data captured for this execution
							</span>
						</div>
					</div>
				)}
			</div>
		);
	}

	private getParsedResults(
		execution: DocumentSearchExecution,
	): DocumentSearchParsedResult[] {
		const baseResults =
			execution.parsed_results ?? parseDocumentSearchResults(execution.results);
		return baseResults.map((result) => this.enrichResult(result));
	}

	private enrichResult(
		result: DocumentSearchParsedResult,
	): DocumentSearchParsedResult {
		const raw = result.raw;
		if (!raw) {
			return result;
		}

		const rawMetadata = raw.metadata ?? {};
		const additionalData: string[] = [];

		const ticketId = raw.ticket_id ?? rawMetadata.ticket_id;
		const priority = raw.priority ?? rawMetadata.priority;
		const status = raw.status ?? rawMetadata.status;
		const category = raw.category ?? rawMetadata.category;

		if (ticketId) additionalData.push(`Ticket ID: ${ticketId}`);
		if (priority) additionalData.push(`Priority: ${priority}`);
		if (status) additionalData.push(`Status: ${status}`);
		if (category) additionalData.push(`Category: ${category}`);

		const steps = raw.resolution_steps ?? raw.steps;
		if (Array.isArray(steps) && steps.length > 0) {
			additionalData.push("\nResolution Steps:");
			steps.forEach((step: string, index: number) => {
				additionalData.push(`  ${index + 1}. ${step}`);
			});
		}

		if (raw.root_cause) {
			additionalData.push(`\nRoot Cause: ${raw.root_cause}`);
		}

		if (Array.isArray(raw.recommendations) && raw.recommendations.length > 0) {
			additionalData.push("\nRecommendations:");
			raw.recommendations.forEach((rec: string) => {
				additionalData.push(`  • ${rec}`);
			});
		}

		if (additionalData.length === 0) {
			return result;
		}

		return {
			...result,
			content: `${result.content}\n\n---\n${additionalData.join("\n")}`,
		};
	}

	renderFormattedResults(execution: DocumentSearchExecution) {
		const results = this.getParsedResults(execution);

		return (
			<div className="space-y-4">
				{/* Query Display */}
				<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
					<div className="flex items-start gap-3">
						<ChevronRight className="w-5 h-5 text-[color:var(--color-accent)] mt-0.5" />
						<div className="flex-1">
							<p className="text-xs text-[color:var(--color-text-muted)] capitalize tracking-wider mb-1">
								Search Query
							</p>
							<p className="text-slate-900 font-medium">{execution.query}</p>
						</div>
					</div>
				</div>

				{/* Embedding Cost */}
				{execution.embedding_tokens != null && execution.embedding_tokens > 0 && (
					<div className="flex items-center gap-2 text-xs text-[color:var(--color-text-muted)] px-4">
						<DollarSign className="w-3 h-3" />
						<span>
							Query embedding: {execution.embedding_tokens.toLocaleString()} tokens
							{execution.embedding_cost != null && execution.embedding_cost > 0 && ` ($${execution.embedding_cost.toFixed(6)})`}
						</span>
					</div>
				)}

				{/* Search Results */}
				{Array.isArray(results) && results.length > 0 ? (
					<div className="space-y-3">
						<h3 className="text-sm font-medium text-[color:var(--color-text-muted)] capitalize tracking-wider">
							Document Results ({results.length})
						</h3>
						{results.map((result, idx) => {
							const metadataArray: Array<{
								label: string;
								value: string | number;
								color: "green" | "plum" | "accent" | "purple" | "gray";
							}> = [];

							if (typeof result.metadata?.page === "number") {
								metadataArray.push({
									label: "Page",
									value: result.metadata.page,
									color: "plum",
								});
							}

							const relevance = result.metadata?.relevance;
							const confidence = result.metadata?.confidence;

							if (
								typeof relevance === "number" &&
								(!confidence || relevance !== confidence)
							) {
								metadataArray.push({
									label: "Relevance",
									value: `${Math.round(relevance * 100)}%`,
									color: "green",
								});
							} else if (typeof confidence === "number") {
								metadataArray.push({
									label: "Confidence",
									value: `${Math.round(confidence * 100)}%`,
									color: "purple",
								});
							}

							const sourceLabel = result.metadata?.source || result.source;
							if (sourceLabel) {
								metadataArray.push({
									label: "Source",
									value: sourceLabel,
									color: "accent",
								});
							}

							if (result.isStructured) {
								metadataArray.push({
									label: "Result",
									value: `#${idx + 1}`,
									color: "gray",
								});
							}

							return (
								<ResultCard
									key={`${sourceLabel || result.content.substring(0, 30)}-${idx}`}
									title={sourceLabel || `Result ${idx + 1}`}
									snippet={result.content}
									metadata={metadataArray}
									showCopy={false}
									clamp={true}
									onExpand={() => {
										// Format the content for expanded view with better structure
										let expandedContent = result.content;

										// Add metadata to expanded view
										const metaInfo: string[] = [];
										if (sourceLabel) metaInfo.push(`📄 Source: ${sourceLabel}`);
										if (typeof result.metadata?.page === "number")
											metaInfo.push(`📃 Page: ${result.metadata.page}`);
										if (typeof relevance === "number") {
											metaInfo.push(
												`📊 Relevance: ${Math.round(relevance * 100)}%`,
											);
										} else if (typeof confidence === "number") {
											metaInfo.push(
												`📊 Confidence: ${Math.round(confidence * 100)}%`,
											);
										}

										if (metaInfo.length > 0) {
											expandedContent =
												metaInfo.join("\n") + "\n\n---\n\n" + expandedContent;
										}

										this.setState({
											expandedText: {
												open: true,
												text: expandedContent,
												title: sourceLabel || "Document Content",
											},
										});
									}}
								/>
							);
						})}
					</div>
				) : (
					<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
						<pre className="text-[color:var(--color-text-secondary)] whitespace-pre-wrap text-sm">
							{typeof execution.results === "string"
								? execution.results
								: JSON.stringify(execution.results, null, 2)}
						</pre>
					</div>
				)}

				{this.state.expandedText.open && (
					<TextModal
						isOpen={this.state.expandedText.open}
						onClose={() =>
							this.setState({
								expandedText: { open: false, text: "", title: "" },
							})
						}
						text={this.state.expandedText.text}
						title={this.state.expandedText.title}
					/>
				)}
			</div>
		);
	}

	renderEmptyState() {
		return (
			<div className="flex-1 flex items-center justify-center">
				<div className="text-center">
					<FileText className="w-12 h-12 text-[color:var(--color-text-muted)] mx-auto mb-3" />
					<p className="text-[color:var(--color-text-muted)] font-medium">
						No Document Searches
					</p>
					<p className="text-[color:var(--color-text-muted)] text-sm mt-2">
						This node hasn&apos;t been executed yet
					</p>
				</div>
			</div>
		);
	}
}
