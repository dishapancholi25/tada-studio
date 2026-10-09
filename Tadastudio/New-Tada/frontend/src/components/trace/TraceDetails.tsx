"use client";

import {
	AlertCircle,
	Check,
	ChevronDown,
	ChevronRight,
	Code,
	Copy,
	FileJson,
	MessageSquare,
	ShieldAlert,
	Terminal,
} from "lucide-react";
import React, { useEffect, useMemo, useState } from "react";
import type { ExecutionGuardrailViolation } from "@/types/guardrail-policies";
import { formatViolationLocation } from "@/components/panels/execution/streaming/GuardrailViolationActivity";
import NodeFeedbackButtons from "../shared/NodeFeedbackButtons";
import DatabaseQueryTraceRenderer from "./renderers/DatabaseQueryTraceRenderer";
import DocumentSearchTraceRenderer from "./renderers/DocumentSearchTraceRenderer";
import WebSearchTraceRenderer from "./renderers/WebSearchTraceRenderer";
import SmartDataViewer from "./SmartDataViewer";
import { statusColors, traceStyles } from "./styles/traceStyles";

interface TraceNode {
	id: string;
	name: string;
	type: string;
	status: string;
	startTime: string | null;
	endTime: string | null;
	duration: number | null;
	executionOrder: number;
	children?: TraceNode[];
	metadata: any;
	input: any;
	output: any;
	error: string | null;
	messages?: any[];
}

interface TraceDetailsProps {
	node: TraceNode;
	executionId?: string;
	violations?: ExecutionGuardrailViolation[];
}

const normalizeForComparison = (value: any): string => {
	if (value === null || value === undefined) return "";
	if (typeof value === "string") return value.trim();
	if (typeof value === "number" || typeof value === "boolean")
		return String(value);
	if (Array.isArray(value)) {
		return value.map((item) => normalizeForComparison(item)).join("|");
	}
	if (typeof value === "object") {
		const keys = Object.keys(value).sort();
		return keys
			.map((key) => `${key}:${normalizeForComparison(value[key])}`)
			.join(",");
	}
	return "";
};

const hasRenderableData = (value: any): boolean => {
	if (value === null || value === undefined) return false;
	if (typeof value === "string") return value.trim().length > 0;
	if (typeof value === "number" || typeof value === "boolean") return true;
	if (Array.isArray(value))
		return value.some((item) => hasRenderableData(item));
	if (typeof value === "object")
		return Object.values(value).some((item) => hasRenderableData(item));
	return false;
};

const areMessagesEquivalent = (a: any[], b: any[]): boolean => {
	if (!Array.isArray(a) || !Array.isArray(b)) return false;
	if (a.length !== b.length) return false;
	return a.every((msg, idx) => {
		const other = b[idx];
		const roleA = (msg?.role ?? "").toLowerCase();
		const roleB = (other?.role ?? "").toLowerCase();
		if (roleA !== roleB) return false;
		return (
			normalizeForComparison(msg?.content) ===
			normalizeForComparison(other?.content)
		);
	});
};

const stringifyContent = (value: any): string => {
	if (value === null || value === undefined) return "";
	if (typeof value === "string") return value;
	if (typeof value === "number" || typeof value === "boolean")
		return String(value);
	try {
		return JSON.stringify(value, null, 2);
	} catch (error) {
		console.warn("Could not stringify message content", error);
		return String(value);
	}
};

const parseMaybeJson = (value: any): any => {
	if (typeof value !== "string") return value;
	try {
		return JSON.parse(value);
	} catch {
		return value;
	}
};

const formatMessageTimestamp = (timestamp?: string) => {
	if (!timestamp) return null;
	const dt = new Date(timestamp);
	if (Number.isNaN(dt.getTime())) return null;
	return dt.toLocaleTimeString();
};

const deepClone = (value: any) => {
	try {
		return JSON.parse(JSON.stringify(value));
	} catch {
		return value;
	}
};

const toNumberOrNull = (value: any): number | null => {
	if (typeof value === "number" && Number.isFinite(value)) return value;
	if (typeof value === "string") {
		const parsed = parseFloat(value);
		return Number.isFinite(parsed) ? parsed : null;
	}
	return null;
};

export default function TraceDetails({ node, executionId, violations }: TraceDetailsProps) {
	const [copiedField, setCopiedField] = useState<string | null>(null);
	const [expandedSections, setExpandedSections] = useState<Set<string>>(
		new Set(["overview"]),
	);

	const copyToClipboard = async (text: string, field: string) => {
		try {
			await navigator.clipboard.writeText(text);
			setCopiedField(field);
			setTimeout(() => setCopiedField(null), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	};

	const toggleSection = (section: string) => {
		setExpandedSections((prev) => {
			const next = new Set(prev);
			if (next.has(section)) {
				next.delete(section);
			} else {
				next.add(section);
			}
			return next;
		});
	};

	const formatDuration = (seconds: number | null) => {
		if (!seconds) return "N/A";
		if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
		if (seconds < 60) return `${seconds.toFixed(2)}s`;
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
	};

	const roleDisplayLabels: Record<string, string> = {
		human: "Agent",
		user: "Agent",
		assistant: "Model",
		system: "System",
		tool: "Tool",
	};

	const roleVisuals: Record<string, { container: string; badge: string }> = {
		system: {
			container: "rounded-[4px] border border-slate-200 bg-white",
			badge:
				"rounded-[4px] border border-purple-300 bg-white px-2.5 py-1 font-semibold text-purple-900",
		},
		human: {
			container: "rounded-[4px] border border-slate-200 bg-white",
			badge:
				"rounded-[4px] border border-orange-500 bg-white px-2.5 py-1 font-semibold text-orange-800",
		},
		user: {
			container: "rounded-[4px] border border-slate-200 bg-white",
			badge:
				"rounded-[4px] border border-orange-500 bg-white px-2.5 py-1 font-semibold text-orange-800",
		},
		assistant: {
			container: "rounded-[4px] border border-emerald-300 bg-white",
			badge:
				"rounded-[4px] border border-emerald-500 bg-white px-2.5 py-1 font-semibold text-emerald-800",
		},
		tool: {
			container: "rounded-[4px] border border-slate-200 bg-white",
			badge:
				"rounded-[4px] border border-amber-600 bg-white px-2.5 py-1 font-semibold text-amber-900",
		},
		default: {
			container: "rounded-[4px] border border-slate-200 bg-white",
			badge:
				"rounded-[4px] border border-slate-300 bg-white px-2.5 py-1 font-semibold text-slate-800",
		},
	};

	const isAgentNode = useMemo(
		() => node.type === "agent" || node.metadata?.nodeType === "AGENT",
		[node.type, node.metadata?.nodeType],
	);

	const agentActivityCounts = useMemo(() => {
		if (!isAgentNode) return null;

		// Count LLM iterations from assistant messages
		const llmIterations = (node.messages ?? []).filter(
			(msg: any) => (msg?.role ?? "").toLowerCase() === "assistant",
		).length;

		let toolCalls = 0;
		let subAgentCalls = 0;

		if (node.children?.length) {
			const countChildren = (children: TraceNode[]) => {
				for (const child of children) {
					if (child.type === "tool") toolCalls++;
					else if (child.type === "agent" || child.type === "subgraph")
						subAgentCalls++;

					if (child.children?.length) countChildren(child.children);
				}
			};
			countChildren(node.children);
		}

		return { llmIterations, toolCalls, subAgentCalls };
	}, [isAgentNode, node.messages, node.children]);

	const conversationMessages = useMemo(
		() => node.messages ?? [],
		[node.messages],
	);

	const assistantMessages = useMemo(
		() =>
			conversationMessages.filter(
				(msg) => (msg?.role ?? "").toLowerCase() === "assistant",
			),
		[conversationMessages],
	);

	const lastAssistantMessage =
		assistantMessages.length > 0
			? assistantMessages[assistantMessages.length - 1]
			: null;

	const firstUserMessage = useMemo(
		() =>
			conversationMessages.find(
				(msg) => (msg?.role ?? "").toLowerCase() === "user",
			) ?? null,
		[conversationMessages],
	);

	const agentContextData = useMemo(() => {
		if (!isAgentNode || !node.input) return null;

		if (typeof node.input === "string") {
			if (
				firstUserMessage &&
				normalizeForComparison(node.input) ===
					normalizeForComparison(firstUserMessage.content)
			) {
				return null;
			}
			return node.input.trim();
		}

		if (typeof node.input !== "object") {
			return node.input;
		}

		const cloned: any = deepClone(node.input);

		if (cloned === node.input) {
			// Deep clone failed, avoid mutating original data
			return node.input;
		}

		const scrub = (value: any) => {
			if (Array.isArray(value)) {
				for (let i = value.length - 1; i >= 0; i -= 1) {
					const item = value[i];
					if (
						Array.isArray(item) &&
						areMessagesEquivalent(item, conversationMessages)
					) {
						value.splice(i, 1);
						continue;
					}
					if (typeof item === "object" && item !== null) {
						scrub(item);
						if (!hasRenderableData(item)) {
							value.splice(i, 1);
						}
						continue;
					}
					if (
						typeof item === "string" &&
						firstUserMessage &&
						normalizeForComparison(item) ===
							normalizeForComparison(firstUserMessage.content)
					) {
						value.splice(i, 1);
					}
				}
				return;
			}

			if (typeof value === "object" && value !== null) {
				Object.keys(value).forEach((key) => {
					const current = value[key];

					if (Array.isArray(current)) {
						if (areMessagesEquivalent(current, conversationMessages)) {
							delete value[key];
							return;
						}
						scrub(current);
						if (!hasRenderableData(current)) {
							delete value[key];
						}
						return;
					}

					if (typeof current === "object" && current !== null) {
						if (
							Array.isArray(current.messages) &&
							areMessagesEquivalent(current.messages, conversationMessages)
						) {
							delete current.messages;
						}
						scrub(current);
						if (!hasRenderableData(current)) {
							delete value[key];
						}
						return;
					}

					if (
						typeof current === "string" &&
						firstUserMessage &&
						normalizeForComparison(current) ===
							normalizeForComparison(firstUserMessage.content)
					) {
						delete value[key];
						return;
					}

					if (current === null || current === undefined) {
						delete value[key];
					}
				});
			}
		};

		scrub(cloned);

		return hasRenderableData(cloned) ? cloned : null;
	}, [isAgentNode, node.input, conversationMessages, firstUserMessage]);

	const agentContextHasData = hasRenderableData(agentContextData);

	const agentOutputData = useMemo(() => {
		if (!isAgentNode || !hasRenderableData(node.output)) return null;
		const agentOutputNormalized = normalizeForComparison(node.output);
		const assistantNormalized = lastAssistantMessage
			? normalizeForComparison(lastAssistantMessage.content)
			: "";
		if (
			agentOutputNormalized &&
			agentOutputNormalized === assistantNormalized
		) {
			return null;
		}
		return node.output;
	}, [isAgentNode, node.output, lastAssistantMessage]);

	const agentOutputHasData = hasRenderableData(agentOutputData);

	const defaultInputHasData = hasRenderableData(node.input);
	const defaultOutputHasData = hasRenderableData(node.output);
	const hasMessages = conversationMessages.length > 0;

	const conversationChips = (() => {
		if (!isAgentNode) return [] as { key: string; content: string }[];
		const llmMeta = node.metadata?.llm;
		const tokensMeta = node.metadata?.tokens;
		const costValue = toNumberOrNull(
			node.metadata?.cost ?? llmMeta?.total_cost,
		);

		const chips: { key: string; content: string }[] = [];

		const modelLabel = llmMeta?.model || llmMeta?.model_version;
		if (modelLabel) {
			chips.push({ key: "model", content: modelLabel });
		}

		if (
			tokensMeta &&
			(tokensMeta.input || tokensMeta.output || tokensMeta.total)
		) {
			const parts: string[] = [];
			if (tokensMeta.input) parts.push(`in ${tokensMeta.input}`);
			if (tokensMeta.output) parts.push(`out ${tokensMeta.output}`);
			const totalLabel = tokensMeta.total
				? `Tok ${tokensMeta.total}`
				: "Tokens";
			const label = parts.length
				? `${totalLabel} • ${parts.join(" / ")}`
				: totalLabel;
			chips.push({ key: "tokens", content: label });
		}

		if (costValue !== null) {
			const formatted =
				costValue < 0.01 ? costValue.toFixed(4) : costValue.toFixed(2);
			chips.push({ key: "cost", content: `$${formatted}` });
		}

		return chips;
	})();

	useEffect(() => {
		const defaults = new Set<string>(["overview"]);

		if (violations && violations.length > 0) {
			defaults.add("violations");
		}

		if (isAgentNode) {
			if (agentOutputHasData) defaults.add("agentResult");
		} else {
			// Special handling for WEB_SEARCH nodes
			if (node.metadata?.nodeType === "WEB_SEARCH") {
				// For web search, expand the combined webSearch section
				if (defaultInputHasData || defaultOutputHasData) {
					defaults.add("webSearch");
				}
			} else if (node.metadata?.nodeType === "DATABASE_QUERY") {
				// For database query, expand the combined databaseQuery section
				if (defaultInputHasData || defaultOutputHasData) {
					defaults.add("databaseQuery");
				}
			} else if (node.metadata?.nodeType === "DOCUMENT_SEARCH") {
				// For document search, expand the combined documentSearch section
				if (defaultInputHasData || defaultOutputHasData) {
					defaults.add("documentSearch");
				}
			} else {
				// For other nodes, use standard input/output sections
				if (hasMessages) defaults.add("messages");
				if (defaultInputHasData) defaults.add("input");
				if (defaultOutputHasData) defaults.add("output");
			}
		}

		setExpandedSections(defaults);
	}, [
		node.id,
		isAgentNode,
		hasMessages,
		agentContextHasData,
		agentOutputHasData,
		defaultInputHasData,
		defaultOutputHasData,
		node.metadata?.nodeType,
		violations,
	]);

	const renderConversationMessages = (
		messages: any[],
		options: {
			highlightFinalAssistant?: boolean;
			messageKeyPrefix?: string;
		} = {},
	) => {
		if (!messages || messages.length === 0) {
			return (
				<div className="text-sm text-slate-600">
					No conversation data captured for this node.
				</div>
			);
		}

		const { highlightFinalAssistant = false, messageKeyPrefix = "message" } =
			options;
		const finalAssistant = highlightFinalAssistant
			? lastAssistantMessage
			: null;

		return (
			<div className="space-y-3">
				{messages.map((msg: any, idx: number) => {
					const role = (msg?.role ?? "unknown").toLowerCase();
					const visuals = roleVisuals[role] ?? roleVisuals.default;
					const messageKey = `${messageKeyPrefix}-${idx}`;
					const timestampLabel = formatMessageTimestamp(msg?.timestamp);
					const isFinal = highlightFinalAssistant && finalAssistant === msg;

					return (
							<div
							key={messageKey}
							className={`group relative border p-4 ${visuals.container} transition-all duration-200`}
						>
							<div className="flex flex-wrap items-start justify-between gap-3">
								<div className="flex flex-wrap items-center gap-2">
									<span
										className={`text-[10px] capitalize font-semibold px-2.5 py-1 rounded-[4px] border ${visuals.badge}`}
									>
										{roleDisplayLabels[role] ?? role}
									</span>
									{isFinal && (
										<span className="rounded-[4px] border border-emerald-500 bg-white px-2.5 py-1 text-[10px] font-semibold capitalize tracking-wide text-emerald-800">
											Final Response
										</span>
									)}
									{timestampLabel && (
										<span className="text-[10px] font-mono text-slate-600">
											{timestampLabel}
										</span>
									)}
								</div>

								<div className="flex items-center gap-2">
									{typeof msg?.token_count === "number" && (
										<span
											className={`${traceStyles.badgeSmall} font-mono text-slate-600`}
										>
											{msg.token_count} tok
										</span>
									)}
									<button
										type="button"
										onClick={async (event) => {
											event.stopPropagation();
											await copyToClipboard(
												stringifyContent(msg?.content),
												messageKey,
											);
										}}
										className={traceStyles.iconButton}
										title="Copy message"
									>
										{copiedField === messageKey ? (
											<Check className="w-4 h-4 text-[color:var(--color-success)]" />
										) : (
											<Copy className="w-4 h-4" />
										)}
									</button>
								</div>
							</div>

							<div className="mt-3">
								<SmartDataViewer
									data={msg?.content}
									className="border-0"
									maxHeight="320px"
								/>
							</div>

							{msg?.tool_calls && msg.tool_calls.length > 0 && (
								<div className="mt-4 space-y-2 rounded-[4px] border border-dashed border-slate-300 bg-white p-3">
									<span className={`${traceStyles.inlineLabel} text-slate-700`}>
										Tool Calls
									</span>
									{msg.tool_calls.map((call: any, toolIdx: number) => (
										<div
											key={`${messageKey}-tool-${toolIdx}`}
											className="rounded-[4px] border border-slate-200 bg-white p-3"
										>
											<div className="flex items-center justify-between gap-2">
												<span className="text-xs font-medium text-slate-900">
													{call?.name ||
														call?.function?.name ||
														`Tool ${toolIdx + 1}`}
												</span>
												{call?.id && (
													<span className="font-mono text-[10px] text-slate-600">
														{call.id}
													</span>
												)}
											</div>
											{call?.function?.arguments && (
												<div className="mt-2">
													<SmartDataViewer
														data={parseMaybeJson(call.function.arguments)}
														className="border-0"
														maxHeight="260px"
													/>
												</div>
											)}
										</div>
									))}
								</div>
							)}
						</div>
					);
				})}
			</div>
		);
	};

	// Get status styling
	const getStatusStyle = () => {
		switch (node.status) {
			case "completed":
				return statusColors.completed;
			case "failed":
				return statusColors.failed;
			case "running":
				return statusColors.running;
			default:
				return statusColors.pending;
		}
	};

	const statusStyle = getStatusStyle();

	return (
		<div
			className={`trace-details h-full flex flex-col ${traceStyles.panelGradient}`}
		>
			<div className="flex-1 overflow-auto p-5 custom-scrollbar">
				<div className="space-y-5">
					{/* Node Header */}
					<div className="group relative">
						<div className={`relative ${traceStyles.primaryCard} p-5`}>
							<div className="mb-4 flex items-start justify-between gap-4">
								<h3 className="text-lg font-semibold text-slate-900">
									{node.name}
								</h3>
								<span
									className={`px-3 py-1 text-[11px] font-medium rounded-full ${statusStyle.combined}`}
								>
									{node.status.toUpperCase()}
								</span>
							</div>

							<div className={`grid grid-cols-2 ${agentActivityCounts ? "sm:grid-cols-3" : "sm:grid-cols-3"} gap-4`}>
								<div className="flex flex-col gap-1">
									<span className={traceStyles.inlineLabel}>Type</span>
									<span className="text-sm font-medium capitalize tracking-wide text-slate-900">
										{node.type === "tool" && node.metadata?.nodeType
											? node.metadata.nodeType.replace(/_/g, " ")
											: node.type}
									</span>
								</div>

								<div className="flex flex-col gap-1">
									<span className={traceStyles.inlineLabel}>Duration</span>
									<span className="font-mono text-sm text-slate-900">
										{formatDuration(node.duration)}
									</span>
								</div>

								<div className="flex flex-col gap-1">
									<span className={traceStyles.inlineLabel}>Order</span>
									<span className="font-mono text-sm text-slate-900">
										#{node.executionOrder}
									</span>
								</div>

								{agentActivityCounts && (
									<>
										<div className="flex flex-col gap-1">
											<span className={traceStyles.inlineLabel}>LLM Iterations</span>
											<span className="font-mono text-sm text-slate-900">
												{agentActivityCounts.llmIterations}
											</span>
										</div>

										<div className="flex flex-col gap-1">
											<span className={traceStyles.inlineLabel}>Tool Calls</span>
											<span className="font-mono text-sm text-slate-900">
												{agentActivityCounts.toolCalls}
											</span>
										</div>

										<div className="flex flex-col gap-1">
											<span className={traceStyles.inlineLabel}>Sub-Agent Calls</span>
											<span className="font-mono text-sm text-slate-900">
												{agentActivityCounts.subAgentCalls}
											</span>
										</div>
									</>
								)}

								{node.metadata?.tokens?.total > 0 && (
									<div className="flex flex-col gap-1">
										<span className={traceStyles.inlineLabel}>Tokens</span>
										<span className="font-mono text-sm text-slate-900">
											{node.metadata.tokens.total.toLocaleString()}
										</span>
									</div>
								)}

								{node.metadata?.cost > 0 && (
									<div className="flex flex-col gap-1">
										<span className={traceStyles.inlineLabel}>Cost</span>
										<span className="font-mono text-sm text-orange-800">
											${node.metadata.cost < 0.01 ? node.metadata.cost.toFixed(4) : node.metadata.cost.toFixed(2)}
										</span>
									</div>
								)}
							</div>
						</div>
					</div>

					{/* Error Section */}
					{node.error && (
						<div className="rounded-[4px] border border-red-200 bg-white p-5 shadow-sm">
							<div className="mb-3 flex items-center gap-3">
								<div className="flex h-8 w-8 items-center justify-center rounded-[4px] border border-red-200 bg-red-50">
									<AlertCircle className="h-4 w-4 text-red-600" />
								</div>
								<span
									className={`${traceStyles.sectionHeader} text-red-800`}
								>
									Error
								</span>
							</div>
							<pre className="font-mono text-sm leading-relaxed whitespace-pre-wrap text-red-800">
								{node.error}
							</pre>
						</div>
					)}

					{/* Guardrail Violations Section */}
					{violations && violations.length > 0 && (
						<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
							<button
								onClick={() => toggleSection("violations")}
								className={traceStyles.sectionToggle}
							>
								<div className="flex items-center gap-3">
									<div className="flex h-8 w-8 items-center justify-center rounded-[4px] border border-red-200 bg-red-50">
										<ShieldAlert className="h-4 w-4 text-red-600" />
									</div>
									<div className="flex flex-col gap-0.5">
										<span className="text-sm font-medium text-slate-900">
											Guardrail Violations
										</span>
										<span className={traceStyles.inlineLabel}>
											{violations.length} violation{violations.length !== 1 ? "s" : ""} detected
										</span>
									</div>
								</div>
								<ChevronDown
									className={`h-4 w-4 text-slate-600 transition-transform duration-200 ${
										expandedSections.has("violations") ? "" : "-rotate-90"
									}`}
								/>
							</button>
							{expandedSections.has("violations") && (
								<div className={`p-5 border-t ${traceStyles.divider} space-y-3`}>
									{violations.map((v) => {
										const isBlock = v.severity === "block";
										const isWarn = v.severity === "warn";
										return (
											<div
												key={v.id}
												className={`rounded-[4px] border bg-white p-4 ${
													isBlock
														? "border-red-300"
														: isWarn
															? "border-amber-500"
															: "border-blue-300"
												}`}
											>
												<div className="mb-2 flex items-center gap-2">
													<span
														className={`rounded-[4px] border px-2 py-0.5 text-[10px] font-semibold capitalize ${
															isBlock
																? "border-red-400 bg-white text-red-800"
																: isWarn
																	? "border-amber-500 bg-white text-amber-900"
																	: "border-blue-400 bg-white text-blue-800"
														}`}
													>
														{v.severity}
													</span>
													{v.action_taken && (
														<span className="rounded-[4px] border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium capitalize text-slate-700">
															{v.action_taken}
														</span>
													)}
													{v.category && (
														<span className="font-mono text-[10px] text-slate-600">
															{formatViolationLocation(v.category, v.agent_node_name, v.details?.tool_name as string)}
														</span>
													)}
												</div>
												<div className="flex flex-col gap-1">
													<span className="text-xs font-medium text-slate-900">
														{v.rule_name}
													</span>
													{v.policy_name && (
														<span className="text-[11px] text-slate-600">
															Policy: {v.policy_name}
														</span>
													)}
												</div>
												{v.message && (
													<p className="mt-2 text-xs leading-relaxed text-slate-700">
														{v.message}
													</p>
												)}
												{v.details && (() => {
													const meta = v.details?.scanner_metadata as Record<string, unknown> | undefined;
													const lines: string[] = [];
													if (meta) {
														if (Array.isArray(meta.entity_types)) {
															const count = (meta.entity_count as number) ?? meta.entity_types.length;
															lines.push(`Entity types: ${(meta.entity_types as string[]).join(", ")} (${count} total)`);
														}
														if (Array.isArray(meta.topics_checked)) {
															lines.push(`Topics checked: ${(meta.topics_checked as string[]).join(", ")}`);
														}
														if (Array.isArray(meta.valid_languages)) {
															lines.push(`Valid languages: ${(meta.valid_languages as string[]).join(", ")}`);
														}
														if (Array.isArray(meta.matched_patterns)) {
															const count = (meta.match_count as number) ?? meta.matched_patterns.length;
															lines.push(`Matched patterns: ${(meta.matched_patterns as string[]).join(", ")} (${count} matches)`);
														}
														if (meta.threshold != null) lines.push(`Threshold: ${meta.threshold}`);
														if (meta.limit != null) lines.push(`Limit: ${meta.limit}`);
													}
													if (typeof v.details?.reasoning === "string") lines.push(`Reasoning: ${v.details.reasoning}`);
													if (typeof v.details?.summary === "string") lines.push(`Summary: ${v.details.summary}`);
													return lines.length > 0 ? (
														<div className="mt-2 space-y-0.5">
															{lines.map((line) => (
																<p key={line} className="font-mono text-[11px] text-slate-600">
																	{line}
																</p>
															))}
														</div>
													) : null;
												})()}
											</div>
										);
									})}
								</div>
							)}
						</div>
					)}

					{/* Conversation Section */}
					{hasMessages && (
						<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
							<button
								onClick={() =>
									toggleSection(isAgentNode ? "conversation" : "messages")
								}
								className={traceStyles.sectionToggle}
							>
								<div className="flex items-center gap-3">
									<div className={traceStyles.iconCapsule}>
										<MessageSquare className="h-4 w-4 text-orange-600" />
									</div>
									<div className="flex flex-col gap-0.5">
										<span className="text-sm font-medium text-slate-900">
											{isAgentNode ? "Conversation" : "Messages"}
										</span>
										<span className={traceStyles.inlineLabel}>
											{conversationMessages.length} message
											{conversationMessages.length !== 1 ? "s" : ""}
										</span>
									</div>
								</div>
								<div className="flex items-center gap-3">
									{isAgentNode && conversationChips.length > 0 && (
										<div className="hidden sm:flex flex-wrap items-center gap-2">
											{conversationChips.map((chip) => (
												<span
													key={chip.key}
													className={`${traceStyles.badgeSmall} text-slate-700`}
												>
													{chip.content}
												</span>
											))}
										</div>
									)}
									<ChevronDown
										className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
											expandedSections.has(
												isAgentNode ? "conversation" : "messages",
											)
												? ""
												: "-rotate-90"
										}`}
									/>
								</div>
							</button>
							{expandedSections.has(
								isAgentNode ? "conversation" : "messages",
							) && (
								<div className={`p-5 border-t ${traceStyles.divider}`}>
									{renderConversationMessages(conversationMessages, {
										highlightFinalAssistant: isAgentNode,
										messageKeyPrefix: isAgentNode ? "agent-message" : "message",
									})}
								</div>
							)}
						</div>
					)}

					{/* Agent Context Section */}
					{isAgentNode && agentContextHasData && (
						<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
							<button
								onClick={() => toggleSection("agentContext")}
								className={traceStyles.sectionToggle}
							>
								<div className="flex items-center gap-3">
									<div className={traceStyles.iconCapsule}>
										<FileJson className="w-4 h-4 text-orange-600" />
									</div>
									<div className="flex flex-col gap-0.5">
										<span className="text-sm font-medium text-slate-900">
											Agent Context
										</span>
										<span className={traceStyles.inlineLabel}>Input data</span>
									</div>
								</div>
								<ChevronDown
									className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
										expandedSections.has("agentContext") ? "" : "-rotate-90"
									}`}
								/>
							</button>
							{expandedSections.has("agentContext") && (
								<div className={`p-5 border-t ${traceStyles.divider}`}>
									<SmartDataViewer data={agentContextData} maxHeight="400px" />
								</div>
							)}
						</div>
					)}

					{/* Agent Result Section */}
					{isAgentNode && agentOutputHasData && (
						<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
							<div className="flex items-center">
								<button
									onClick={() => toggleSection("agentResult")}
									className={`${traceStyles.sectionToggle} flex-1`}
								>
									<div className="flex items-center gap-3">
										<div className={traceStyles.iconCapsule}>
											<Terminal className="w-4 h-4 text-orange-600" />
										</div>
										<div className="flex flex-col gap-0.5">
											<span className="text-sm font-medium text-slate-900">
												Agent Result
											</span>
											<span className={traceStyles.inlineLabel}>Output data</span>
										</div>
									</div>
									<ChevronDown
										className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
											expandedSections.has("agentResult") ? "" : "-rotate-90"
										}`}
									/>
								</button>
								{executionId && node.id && (
									<div className="pr-4">
										<NodeFeedbackButtons
											executionId={executionId}
											nodeExecutionId={node.id}
										/>
									</div>
								)}
							</div>
							{expandedSections.has("agentResult") && (
								<div className={`p-5 border-t ${traceStyles.divider}`}>
									<SmartDataViewer data={agentOutputData} maxHeight="400px" />
								</div>
							)}
						</div>
					)}

					{/* Default Input/Output for non-agent nodes */}
					{/* Special handling for WEB_SEARCH nodes - show combined query and results */}
					{!isAgentNode &&
						node.metadata?.nodeType === "WEB_SEARCH" &&
						(defaultInputHasData || defaultOutputHasData) && (
							<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
								<div className="flex items-center">
									<button
										onClick={() => toggleSection("webSearch")}
										className={`${traceStyles.sectionToggle} flex-1`}
									>
										<div className="flex items-center gap-3">
											<div className={traceStyles.iconCapsule}>
												<Terminal className="w-4 h-4 text-orange-600" />
											</div>
											<div className="flex flex-col gap-0.5">
												<span className="text-sm font-medium text-slate-900">
													Web Search Results
												</span>
												<span className={traceStyles.inlineLabel}>
													Query and results
												</span>
											</div>
										</div>
										<ChevronDown
											className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
												expandedSections.has("webSearch") ? "" : "-rotate-90"
											}`}
										/>
									</button>
									{executionId && node.id && (
										<div className="pr-4">
											<NodeFeedbackButtons
												executionId={executionId}
												nodeExecutionId={node.id}
											/>
										</div>
									)}
								</div>
								{expandedSections.has("webSearch") && (
									<div className={`p-5 border-t ${traceStyles.divider}`}>
										<WebSearchTraceRenderer
											input={node.input}
											output={node.output}
										/>
									</div>
								)}
							</div>
						)}

					{/* Special handling for DATABASE_QUERY nodes - show combined query and results */}
					{!isAgentNode &&
						node.metadata?.nodeType === "DATABASE_QUERY" &&
						(defaultInputHasData || defaultOutputHasData) && (
							<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
								<div className="flex items-center">
									<button
										onClick={() => toggleSection("databaseQuery")}
										className={`${traceStyles.sectionToggle} flex-1`}
									>
										<div className="flex items-center gap-3">
											<div className={traceStyles.iconCapsule}>
												<Terminal className="w-4 h-4 text-orange-600" />
											</div>
											<div className="flex flex-col gap-0.5">
												<span className="text-sm font-medium text-slate-900">
													Database Query Results
												</span>
												<span className={traceStyles.inlineLabel}>
													SQL query and results
												</span>
											</div>
										</div>
										<ChevronDown
											className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
												expandedSections.has("databaseQuery") ? "" : "-rotate-90"
											}`}
										/>
									</button>
									{executionId && node.id && (
										<div className="pr-4">
											<NodeFeedbackButtons
												executionId={executionId}
												nodeExecutionId={node.id}
											/>
										</div>
									)}
								</div>
								{expandedSections.has("databaseQuery") && (
									<div className={`p-5 border-t ${traceStyles.divider}`}>
										<DatabaseQueryTraceRenderer
											input={node.input}
											output={node.output}
											metadata={node.metadata}
										/>
									</div>
								)}
							</div>
						)}

					{/* Special handling for DOCUMENT_SEARCH nodes - show combined query and results */}
					{!isAgentNode &&
						node.metadata?.nodeType === "DOCUMENT_SEARCH" &&
						(defaultInputHasData || defaultOutputHasData) && (
							<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
								<div className="flex items-center">
									<button
										onClick={() => toggleSection("documentSearch")}
										className={`${traceStyles.sectionToggle} flex-1`}
									>
										<div className="flex items-center gap-3">
											<div className={traceStyles.iconCapsule}>
												<Terminal className="w-4 h-4 text-orange-600" />
											</div>
											<div className="flex flex-col gap-0.5">
												<span className="text-sm font-medium text-slate-900">
													Document Search Results
												</span>
												<span className={traceStyles.inlineLabel}>
													Search query and documents
												</span>
											</div>
										</div>
										<ChevronDown
											className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
												expandedSections.has("documentSearch") ? "" : "-rotate-90"
											}`}
										/>
									</button>
									{executionId && node.id && (
										<div className="pr-4">
											<NodeFeedbackButtons
												executionId={executionId}
												nodeExecutionId={node.id}
											/>
										</div>
									)}
								</div>
								{expandedSections.has("documentSearch") && (
									<div className={`p-5 border-t ${traceStyles.divider}`}>
										<DocumentSearchTraceRenderer
											input={node.input}
											output={node.output}
											metadata={node.metadata}
										/>
									</div>
								)}
							</div>
						)}

					{/* Standard Input/Output for non-WEB_SEARCH, non-DATABASE_QUERY, and non-DOCUMENT_SEARCH nodes */}
					{!isAgentNode &&
						node.metadata?.nodeType !== "WEB_SEARCH" &&
						node.metadata?.nodeType !== "DATABASE_QUERY" &&
						node.metadata?.nodeType !== "DOCUMENT_SEARCH" &&
						defaultInputHasData && (
							<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
								<button
									onClick={() => toggleSection("input")}
									className={traceStyles.sectionToggle}
								>
									<div className="flex items-center gap-3">
										<div className={traceStyles.iconCapsule}>
											<FileJson className="w-4 h-4 text-orange-600" />
										</div>
										<div className="flex flex-col gap-0.5">
											<span className="text-sm font-medium text-slate-900">
												Input
											</span>
											<span className={traceStyles.inlineLabel}>
												Input data
											</span>
										</div>
									</div>
									<ChevronDown
										className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
											expandedSections.has("input") ? "" : "-rotate-90"
										}`}
									/>
								</button>
								{expandedSections.has("input") && (
									<div className={`p-5 border-t ${traceStyles.divider}`}>
										<SmartDataViewer data={node.input} maxHeight="400px" />
									</div>
								)}
							</div>
						)}

					{!isAgentNode &&
						node.metadata?.nodeType !== "WEB_SEARCH" &&
						node.metadata?.nodeType !== "DATABASE_QUERY" &&
						node.metadata?.nodeType !== "DOCUMENT_SEARCH" &&
						defaultOutputHasData && (
							<div className={`${traceStyles.secondaryCard} overflow-hidden`}>
								<div className="flex items-center">
									<button
										onClick={() => toggleSection("output")}
										className={`${traceStyles.sectionToggle} flex-1`}
									>
										<div className="flex items-center gap-3">
											<div className={traceStyles.iconCapsule}>
												<Terminal className="w-4 h-4 text-orange-600" />
											</div>
											<div className="flex flex-col gap-0.5">
												<span className="text-sm font-medium text-slate-900">
													Output
												</span>
												<span className={traceStyles.inlineLabel}>
													Output data
												</span>
											</div>
										</div>
										<ChevronDown
											className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
												expandedSections.has("output") ? "" : "-rotate-90"
											}`}
										/>
									</button>
									{executionId && node.id && (
										<div className="pr-4">
											<NodeFeedbackButtons
												executionId={executionId}
												nodeExecutionId={node.id}
											/>
										</div>
									)}
								</div>
								{expandedSections.has("output") && (
									<div className={`p-5 border-t ${traceStyles.divider}`}>
										<SmartDataViewer data={node.output} maxHeight="400px" />
									</div>
								)}
							</div>
						)}

					{/* Raw Metadata Section */}
					{node.metadata && Object.keys(node.metadata).length > 0 && (
						<div className={`${traceStyles.tertiaryCard} overflow-hidden`}>
							<button
								onClick={() => toggleSection("rawMetadata")}
								className={traceStyles.sectionToggle}
							>
								<div className="flex items-center gap-3">
									<div className={traceStyles.iconCapsuleSm}>
										<Code className="w-3 h-3 text-orange-600" />
									</div>
									<div className="flex flex-col gap-0.5">
										<span className="text-sm font-medium text-slate-900">
											Raw Metadata
										</span>
										<span className={traceStyles.inlineLabel}>
											Full metadata object
										</span>
									</div>
								</div>
								<ChevronDown
									className={`w-4 h-4 text-slate-600 transition-transform duration-200 ${
										expandedSections.has("rawMetadata") ? "" : "-rotate-90"
									}`}
								/>
							</button>
							{expandedSections.has("rawMetadata") && (
								<div className={`p-5 border-t ${traceStyles.divider}`}>
									<SmartDataViewer
										data={node.metadata}
										className=""
										defaultViewMode="raw"
										maxHeight="400px"
									/>
								</div>
							)}
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
