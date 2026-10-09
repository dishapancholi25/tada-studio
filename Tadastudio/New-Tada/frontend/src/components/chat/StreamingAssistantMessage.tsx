"use client";

import {
	AlertTriangle,
	CheckCircle2,
	ChevronRight,
	Loader2,
	Wrench,
	XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import SimpleMarkdown from "@/components/utils/SimpleMarkdown";
import type {
	StreamingMessage,
	StreamingBlock,
	AgentDividerBlock,
	ToolCallBlock,
} from "@/hooks/useStreamingChat";
import InlineSubAgentCard from "./InlineSubAgentCard";
import InlineToolCallCard from "./InlineToolCallCard";
import SuggestionChips from "./SuggestionChips";
import ThinkingIndicator from "./ThinkingIndicator";
import { parseSuggestions } from "./utils/parseSuggestions";
import { summarizeToolGroup } from "./utils/toolCallDisplayUtils";

// ============================================================================
// Agent Color System
// ============================================================================

/** Distinct left accents + dark labels (no tinted panel backgrounds) */
const AGENT_COLORS = [
	{ border: "#2563eb", text: "#1e40af" },
	{ border: "#7c3aed", text: "#6d28d9" },
	{ border: "#db2777", text: "#9d174d" },
	{ border: "#059669", text: "#047857" },
	{ border: "#ea580c", text: "#9a3412" },
	{ border: "#0891b2", text: "#155e75" },
	{ border: "#dc2626", text: "#991b1b" },
	{ border: "#ca8a04", text: "#854d0e" },
];

function getAgentColor(name: string) {
	let hash = 0;
	for (const ch of name) hash = ((hash << 5) - hash + ch.charCodeAt(0)) | 0;
	return AGENT_COLORS[Math.abs(hash) % AGENT_COLORS.length];
}

// ============================================================================
// Main Component
// ============================================================================

interface StreamingAssistantMessageProps {
	streamingMessage: StreamingMessage;
	workflowName?: string;
	onSuggestionClick?: (text: string) => void;
}

export default function StreamingAssistantMessage({
	streamingMessage,
	workflowName,
	onSuggestionClick,
}: StreamingAssistantMessageProps) {
	const { blocks, isComplete } = streamingMessage;

	// Only show the last agent's text/thinking blocks — skip preamble node outputs
	// and agent section headers. Both tool cards and non-agent content are excluded.
	const displayBlocks = getDisplayBlocks(blocks);

	// Parse suggestions from completed text blocks so chips appear as soon as
	// streaming finishes — before the message moves into the static list.
	const suggestions = isComplete && onSuggestionClick
		? parseSuggestions(
			blocks
				.filter((b) => b.type === "text")
				.map((b) => (b as { type: "text"; content: string }).content)
				.join(""),
		  ).suggestions
		: [];

	return (
		<div
			className="flex flex-col items-start animate-fadeInUp"
			style={{ animationDuration: "0.35s" }}
		>
			{/* Role label */}
			<div className="mb-1.5 ml-[44px]">
				<span className="block max-w-[200px] truncate text-[0.6rem] font-semibold capitalize text-orange-800">
					{workflowName || "AGENT"}
				</span>
			</div>

			{/* Avatar + Bubble row */}
			<div className="flex max-w-[720px] gap-3">
				{/* Avatar */}
				<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] border border-gray-200 bg-white shadow-sm">
					<svg width="14" height="14" viewBox="0 0 14 14">
						<polygon
							points="7,1 13,7 7,13 1,7"
							fill="none"
							stroke="rgb(234 88 12)"
							strokeWidth="1.2"
						/>
						<circle cx="7" cy="7" r="2" fill="rgb(234 88 12)" />
					</svg>
				</div>

				{/* Bubble + chips column */}
				<div className="flex min-w-0 flex-col">
					<div className="chat-bubble-assistant min-w-[240px] rounded-[16px] border border-gray-200 bg-white px-[18px] py-[14px] shadow-[0_4px_16px_rgb(15_23_42_/_0.06)]">
						<GroupedBlockRenderer
							blocks={displayBlocks}
							allBlocks={displayBlocks}
							isMessageComplete={isComplete}
						/>
					</div>

					{/* Suggestion chips — shown only when streaming is complete */}
					{suggestions.length > 0 && onSuggestionClick && (
						<SuggestionChips suggestions={suggestions} onSelect={onSuggestionClick} />
					)}
				</div>
			</div>
		</div>
	);
}

// ============================================================================
// Display Block Filter
// ============================================================================

/** Returns only the text/thinking/guardrail blocks from the last agent section.
 *  Skips preamble content from non-agent nodes (e.g. failed file reads)
 *  and all tool call / sub-agent cards. */
function getDisplayBlocks(blocks: StreamingBlock[]): StreamingBlock[] {
	let lastDividerIdx = -1;
	for (let i = blocks.length - 1; i >= 0; i--) {
		if (blocks[i].type === "agent_divider") {
			lastDividerIdx = i;
			break;
		}
	}
	const sectionBlocks =
		lastDividerIdx >= 0 ? blocks.slice(lastDividerIdx + 1) : blocks;
	return sectionBlocks.filter(
		(b) => b.type === "text" || b.type === "thinking" || b.type === "guardrail",
	);
}

// ============================================================================
// Grouped Block Renderer (handles tool call grouping)
// ============================================================================

interface GroupedBlockRendererProps {
	blocks: StreamingBlock[];
	allBlocks: StreamingBlock[];
	isMessageComplete: boolean;
}

function GroupedBlockRenderer({
	blocks,
	isMessageComplete,
}: GroupedBlockRendererProps) {
	return (
		<>
			{blocks.map((block, i) => (
				<BlockRenderer
					key={blockKey(block, i)}
					block={block}
					isLast={i === blocks.length - 1}
					isMessageComplete={isMessageComplete}
				/>
			))}
		</>
	);
}

// ============================================================================
// Tool Call Group
// ============================================================================

function ToolCallGroup({
	tools,
	isMessageComplete,
}: {
	tools: ToolCallBlock[];
	isMessageComplete: boolean;
}) {
	const hasRunning = tools.some((t) => t.status === "running");
	const [expanded, setExpanded] = useState(hasRunning);

	// Auto-expand when tools are running, auto-collapse when all done
	useEffect(() => {
		if (hasRunning) setExpanded(true);
	}, [hasRunning]);

	const completedCount = tools.filter((t) => t.status === "complete").length;
	const errorCount = tools.filter((t) => t.status === "error").length;
	const { label: groupLabel } = summarizeToolGroup(tools);

	return (
		<div className="animate-toolCardIn my-2 rounded-xl border border-gray-200 bg-white shadow-sm">
			<button
				type="button"
				onClick={() => setExpanded(!expanded)}
				className="flex w-full cursor-pointer items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-left text-gray-800 transition-colors hover:bg-slate-50"
			>
				<ChevronRight
					className={`h-3 w-3 shrink-0 text-gray-500 transition-transform duration-200 ${
						expanded ? "rotate-90" : ""
					}`}
				/>
				<Wrench className="h-3.5 w-3.5 shrink-0 text-gray-500" />
				<span className="flex-1 text-[13px] font-medium text-gray-800">
					{hasRunning ? `${groupLabel}...` : groupLabel}
				</span>
				{completedCount > 0 && !hasRunning && (
					<span className="flex items-center gap-1 text-[10px] text-emerald-700">
						<CheckCircle2 className="h-3 w-3" />
						{completedCount}
					</span>
				)}
				{errorCount > 0 && (
					<span className="flex items-center gap-1 text-[10px] text-red-700">
						<XCircle className="h-3 w-3" />
						{errorCount}
					</span>
				)}
				{hasRunning && (
					<Loader2 className="h-3.5 w-3.5 animate-spin text-orange-600" />
				)}
			</button>

			{expanded && (
				<div className="animate-expandContent border-t border-gray-100 px-2 py-1.5">
					<div className="max-h-[400px] overflow-y-auto custom-scrollbar">
						{tools.map((tc) => (
							<InlineToolCallCard
								key={tc.callId}
								callId={tc.callId}
								toolName={tc.toolName}
								status={tc.status}
								toolArgs={tc.toolArgs}
								resultPreview={tc.resultPreview}
								error={tc.error}
								durationMs={tc.durationMs}
								toolNodeType={tc.toolNodeType}
								toolNodeName={tc.toolNodeName}
							/>
						))}
					</div>
				</div>
			)}
		</div>
	);
}

// ============================================================================
// Block Key & Renderer
// ============================================================================

function blockKey(block: StreamingBlock, idx: number): string {
	switch (block.type) {
		case "text":
			return `text-${idx}`;
		case "tool_call":
			return `tc-${block.callId}`;
		case "subagent":
			return `sa-${block.subagentId}`;
		case "thinking":
			return `thinking-${idx}`;
		case "guardrail":
			return `gr-${idx}`;
		case "agent_divider":
			return `ad-${block.agentNodeId}`;
	}
}

interface BlockRendererProps {
	block: StreamingBlock;
	isLast: boolean;
	isMessageComplete: boolean;
}

function BlockRenderer({ block, isLast, isMessageComplete }: BlockRendererProps) {
	switch (block.type) {
		case "agent_divider":
			return null;

		case "thinking":
			return <ThinkingIndicator agentName={block.agentName} />;

		case "text":
			return (
				<StreamingTextBlock
					content={block.content}
					isStreaming={block.isStreaming}
					showCursor={isLast && block.isStreaming && !isMessageComplete}
				/>
			);

		case "tool_call":
			return (
				<InlineToolCallCard
					callId={block.callId}
					toolName={block.toolName}
					status={block.status}
					toolArgs={block.toolArgs}
					resultPreview={block.resultPreview}
					error={block.error}
					durationMs={block.durationMs}
					toolNodeType={block.toolNodeType}
					toolNodeName={block.toolNodeName}
				/>
			);

		case "subagent":
			return (
				<InlineSubAgentCard
					subagentId={block.subagentId}
					subagentName={block.subagentName}
					taskDescription={block.taskDescription}
					parentAgentName={block.parentAgentName}
					status={block.status}
					durationMs={block.durationMs}
					toolsUsed={block.toolsUsed}
					nestedToolCalls={block.nestedToolCalls}
				/>
			);

		case "guardrail":
			return (
				<div className="animate-toolCardIn my-2 flex items-start gap-2 rounded-lg border border-amber-300 bg-white px-3 py-2 shadow-sm">
					<AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
					<div>
						<span className="text-xs font-medium text-amber-900">
							{block.ruleName}
						</span>
						<p className="mt-0.5 text-[11px] text-gray-600">{block.message}</p>
					</div>
				</div>
			);
	}
}

// ============================================================================
// Multi-Agent Section Layout (Redesigned)
// ============================================================================

interface AgentSection {
	divider: AgentDividerBlock;
	blocks: StreamingBlock[];
}

interface GroupedBlocks {
	preamble: StreamingBlock[];
	sections: AgentSection[];
}

function groupBlocksByAgent(blocks: StreamingBlock[]): GroupedBlocks {
	const preamble: StreamingBlock[] = [];
	const sections: AgentSection[] = [];
	let currentSection: AgentSection | null = null;

	for (const block of blocks) {
		if (block.type === "agent_divider") {
			currentSection = { divider: block, blocks: [] };
			sections.push(currentSection);
		} else if (currentSection) {
			currentSection.blocks.push(block);
		} else {
			preamble.push(block);
		}
	}

	return { preamble, sections };
}

function formatElapsed(ms: number): string {
	if (ms < 1000) return `${Math.round(ms)}ms`;
	const s = ms / 1000;
	if (s < 60) return `${s.toFixed(1)}s`;
	const m = Math.floor(s / 60);
	const rem = Math.round(s % 60);
	return `${m}m ${rem}s`;
}

function AgentSectionedLayout({
	blocks,
	isComplete,
}: {
	blocks: StreamingBlock[];
	isComplete: boolean;
}) {
	const { preamble, sections } = groupBlocksByAgent(blocks);

	return (
		<div className="space-y-4">
			{preamble.map((block, idx) => (
				<BlockRenderer
					key={blockKey(block, idx)}
					block={block}
					isLast={block === blocks[blocks.length - 1]}
					isMessageComplete={isComplete}
				/>
			))}

			{sections.map((section, sIdx) => (
				<AgentSectionCard
					key={`agent-${section.divider.agentNodeId}`}
					section={section}
					allBlocks={blocks}
					isMessageComplete={isComplete}
					isFirst={sIdx === 0 && preamble.length === 0}
				/>
			))}
		</div>
	);
}

function AgentSectionCard({
	section,
	allBlocks,
	isMessageComplete,
	isFirst,
}: {
	section: AgentSection;
	allBlocks: StreamingBlock[];
	isMessageComplete: boolean;
	isFirst: boolean;
}) {
	const { divider, blocks: sectionBlocks } = section;
	const color = getAgentColor(divider.agentName);

	const statusBadge = {
		running: (
			<span className="inline-flex items-center gap-1.5 text-[11px] text-orange-600">
				<Loader2 className="h-3 w-3 animate-spin text-orange-500" />
				Running...
			</span>
		),
		complete: (
			<span className="inline-flex items-center gap-1 text-[11px] text-[#0DA931]">
				<CheckCircle2 className="h-3 w-3" />
				{formatElapsed(Date.now() - divider.startedAt)}
			</span>
		),
		error: (
			<span className="inline-flex items-center gap-1 text-[11px] text-red-600">
				<XCircle className="h-3 w-3" />
				Failed
			</span>
		),
	}[divider.status];

	const initial = divider.agentName.charAt(0).toUpperCase();

	return (
		<div
			className="animate-agentSectionIn overflow-hidden rounded-xl border border-y border-r border-gray-200 bg-white shadow-sm"
			style={{ borderLeft: `4px solid ${color.border}` }}
		>
			{/* Agent header */}
			<div className="flex items-center gap-3 border-b border-gray-100 px-4 py-3">
				{/* Agent avatar */}
				<div
					className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border-2 bg-white text-xs font-bold"
					style={{ borderColor: color.border, color: color.text }}
				>
					{initial}
				</div>

				{/* Agent name */}
				<span
					className="flex-1 text-sm font-semibold tracking-wide"
					style={{ color: color.text }}
				>
					{divider.agentName}
				</span>

				{/* Status badge */}
				{statusBadge}
			</div>

			{/* Agent content blocks */}
			{sectionBlocks.length > 0 && (
				<div className="px-4 py-3">
					<GroupedBlockRenderer
						blocks={sectionBlocks}
						allBlocks={allBlocks}
						isMessageComplete={isMessageComplete}
					/>
				</div>
			)}
		</div>
	);
}

// ============================================================================
// Streaming Text Block (throttled markdown re-render)
// ============================================================================

interface StreamingTextBlockProps {
	content: string;
	isStreaming: boolean;
	showCursor: boolean;
}

function StreamingTextBlock({
	content,
	isStreaming,
	showCursor,
}: StreamingTextBlockProps) {
	const [renderedContent, setRenderedContent] = useState(content);
	const rafRef = useRef<number | null>(null);
	const lastUpdateRef = useRef(Date.now());

	useEffect(() => {
		if (!isStreaming) {
			if (rafRef.current !== null) {
				cancelAnimationFrame(rafRef.current);
				rafRef.current = null;
			}
			setRenderedContent(content);
			return;
		}

		const elapsed = Date.now() - lastUpdateRef.current;
		if (elapsed >= 50) {
			setRenderedContent(content);
			lastUpdateRef.current = Date.now();
		} else if (rafRef.current === null) {
			rafRef.current = requestAnimationFrame(() => {
				rafRef.current = null;
				setRenderedContent(content);
				lastUpdateRef.current = Date.now();
			});
		}
	}, [content, isStreaming]);

	useEffect(() => {
		return () => {
			if (rafRef.current !== null) {
				cancelAnimationFrame(rafRef.current);
			}
		};
	}, []);

	if (!renderedContent && !showCursor) {
		return null;
	}

	return (
		<div className="text-sm text-slate-900">
			{renderedContent && <SimpleMarkdown content={renderedContent} variant="light" />}
			{showCursor && (
				<span className="-mb-[2px] ml-0.5 inline-block h-[1.1em] w-[2px] animate-typingCursor bg-gray-400 transition-opacity duration-300" />
			)}
		</div>
	);
}
