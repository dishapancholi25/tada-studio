"use client";

import {
	AlertCircle,
	Bot,
	Brain,
	CheckCircle,
	Clock,
	Database,
	DollarSign,
	FileText,
	GitBranch,
	Globe,
	Hash,
	HelpCircle,
	Layers,
	Mail,
	PlayCircle,
	Save,
	Search,
	Server,
	ShieldAlert,
	StopCircle,
	Users,
	Wrench,
	XCircle,
	Zap,
} from "lucide-react";
import React, { memo, useMemo } from "react";
import type { ExecutionGuardrailViolation } from "@/types/guardrail-policies";
import TraceGraphRail from "./TraceGraphRail";
import { traceStyles } from "./styles/traceStyles";

interface TraceNode {
	id: string;
	name: string;
	type:
		| "agent"
		| "tool"
		| "llm"
		| "condition"
		| "orchestrator"
		| "subgraph"
		| "human"
		| "start"
		| "end"
		| "checkpoint"
		| "unknown";
	status: "pending" | "running" | "completed" | "failed";
	startTime: string | null;
	endTime: string | null;
	duration: number | null;
	executionOrder: number;
	children: TraceNode[];
	metadata: any;
	input: any;
	output: any;
	error: string | null;
}

interface TraceTreeProps {
	nodes: TraceNode[];
	expandedNodes: Set<string>;
	selectedNode: TraceNode | null;
	onToggleNode: (nodeId: string) => void;
	onSelectNode: (node: TraceNode) => void;
	searchQuery: string;
	violationsByNodeId?: Map<string, ExecutionGuardrailViolation[]>;
}

const EMPTY_RAILS = new Set<number>();

// Find the deepest expanded last-child depth from a node.
function getDeepestExpandedDepth(
	node: TraceNode,
	nodeDepth: number,
	expandedNodes: Set<string>,
): number {
	if (node.children?.length > 0 && expandedNodes.has(node.id)) {
		const lastChild = node.children[node.children.length - 1];
		return getDeepestExpandedDepth(lastChild, nodeDepth + 1, expandedNodes);
	}
	return nodeDepth;
}


const TraceTreeNode = memo(
	({
		node,
		depth = 0,
		isFirstSibling,
		isLastSibling,
		continuingRails,
		expandedNodes,
		selectedNode,
		onToggleNode,
		onSelectNode,
		searchQuery,
		mergeFromDepth,
		violationsByNodeId,
	}: {
		node: TraceNode;
		depth?: number;
		isFirstSibling: boolean;
		isLastSibling: boolean;
		continuingRails: Set<number>;
		expandedNodes: Set<string>;
		selectedNode: TraceNode | null;
		onToggleNode: (nodeId: string) => void;
		onSelectNode: (node: TraceNode) => void;
		searchQuery: string;
		mergeFromDepth?: number;
		violationsByNodeId?: Map<string, ExecutionGuardrailViolation[]>;
	}) => {
		const isExpanded = expandedNodes.has(node.id);
		const isSelected = selectedNode?.id === node.id;
		const hasChildren = node.children && node.children.length > 0;
		const hasExpandedChildren = hasChildren && isExpanded;

		const getNodeIcon = () => {
			const originalType = node.metadata?.nodeType;

			if (originalType) {
				switch (originalType) {
					case "HTTP_REQUEST":
					case "HTTP_REQUEST_ACTION":
						return <Globe className="w-4 h-4 text-blue-600" />;
					case "DATABASE_QUERY":
					case "DATABASE_INSERT":
					case "DATABASE_QUERY_ACTION":
						return <Database className="w-4 h-4 text-orange-600" />;
					case "DOCUMENT_SEARCH":
					case "WEB_SEARCH":
						return <Search className="w-4 h-4 text-purple-600" />;
					case "EMAIL_SEND":
						return <Mail className="w-4 h-4 text-red-600" />;
					case "FILE_READ":
						return <FileText className="w-4 h-4 text-[#0DA931]" />;
					case "MCP_SERVER":
						return <Server className="w-4 h-4 text-indigo-600" />;
					case "CHECKPOINT":
						return <Save className="w-4 h-4 text-cyan-600" />;
					case "START":
						return <PlayCircle className="w-4 h-4 text-[#0DA931]" />;
					case "END":
						return <StopCircle className="w-4 h-4 text-red-600" />;
				}
			}

			switch (node.type) {
				case "agent":
					return <Bot className="w-4 h-4 text-blue-600" />;
				case "tool":
					return (
						<Wrench className="w-4 h-4 text-[color:var(--color-warning)]" />
					);
				case "llm":
					return <Brain className="w-4 h-4 text-pink-600" />;
				case "condition":
					return (
						<GitBranch className="w-4 h-4 text-[color:var(--color-accent)]" />
					);
				case "orchestrator":
					return <Users className="w-4 h-4 text-purple-600" />;
				case "subgraph":
					return <Layers className="w-4 h-4 text-violet-600" />;
				case "human":
					return <HelpCircle className="w-4 h-4 text-teal-600" />;
				case "start":
					return <PlayCircle className="w-4 h-4 text-[#0DA931]" />;
				case "end":
					return <StopCircle className="w-4 h-4 text-red-600" />;
				case "checkpoint":
					return <Save className="w-4 h-4 text-cyan-600" />;
				default:
					return <Hash className="w-4 h-4 text-slate-500" />;
			}
		};

		const getStatusIcon = () => {
			switch (node.status) {
				case "completed":
					return (
						<CheckCircle className="w-3.5 h-3.5 text-[color:var(--color-success)]" />
					);
				case "failed":
					return (
						<XCircle className="w-3.5 h-3.5 text-[color:var(--color-error)]" />
					);
				case "running":
					return (
						<Clock className="w-3.5 h-3.5 text-[color:var(--color-info)] animate-spin" />
					);
				case "pending":
					return (
						<AlertCircle className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
					);
				default:
					return null;
			}
		};

		const formatDuration = (seconds: number | null) => {
			if (!seconds) return "";
			if (seconds < 1) return `${(seconds * 1000).toFixed(0)}ms`;
			if (seconds < 60) return `${seconds.toFixed(2)}s`;
			const minutes = Math.floor(seconds / 60);
			const remainingSeconds = seconds % 60;
			return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
		};

		const highlightMatch = (text: string) => {
			if (!searchQuery) return text;

			const parts = text.split(new RegExp(`(${searchQuery})`, "gi"));
			return (
				<>
					{parts.map((part, i) =>
						part.toLowerCase() === searchQuery.trim().toLowerCase() ? (
							<span
								key={`highlight-${part}-${i}`}
								className="font-semibold text-orange-800 underline decoration-orange-600 decoration-2 underline-offset-2"
							>
								{part}
							</span>
						) : (
							<span key={`text-${part}-${i}`}>{part}</span>
						),
					)}
				</>
			);
		};

		// Compute children's continuingRails: always include parent's depth
		// so the parent rail is visible through all children rows
		const childContinuingRails = useMemo(() => {
			if (!hasExpandedChildren) return EMPTY_RAILS;
			const rails = new Set(continuingRails);
			rails.add(depth);
			return rails;
		}, [hasExpandedChildren, continuingRails, depth]);

		const isMatch = useMemo(() => {
			if (!searchQuery) return true;
			const query = searchQuery.trim().toLowerCase();

			const nodeMatches =
				node.name.toLowerCase().includes(query) ||
				node.type.toLowerCase().includes(query);

			const hasMatchingChild = (n: TraceNode): boolean => {
				if (
					n.name.toLowerCase().includes(query) ||
					n.type.toLowerCase().includes(query)
				) {
					return true;
				}
				return n.children?.some(hasMatchingChild) || false;
			};

			return nodeMatches || hasMatchingChild(node);
		}, [node, searchQuery]);

		if (!isMatch) return null;

		return (
			<div className={`trace-tree-node ${node.type === "subgraph" ? "rounded-r-[4px] border-r border-slate-200 bg-slate-50" : ""}`}>
				{/* Row */}
				<div
					className={`
						group flex items-stretch cursor-pointer
						transition-all duration-150
						${
							isSelected
								? "border-l-[3px] border-l-orange-500 bg-slate-100"
								: "border-l-[3px] border-l-transparent hover:border-l-orange-400 hover:bg-slate-50"
						}
					`}
					style={{ minHeight: "34px" }}
					onClick={() => onSelectNode(node)}
					{...(node.type === "agent" ? { "data-tutorial": "trace-agent-node" } : {})}
				>
					<TraceGraphRail
						depth={depth}
						isFirstSibling={isFirstSibling}
						isLastSibling={isLastSibling}
						hasChildren={!!hasChildren}
						isExpanded={isExpanded}
						hasExpandedChildren={!!hasExpandedChildren}
						continuingRails={continuingRails}
						nodeStatus={node.status}
						icon={getNodeIcon()}
						onToggle={
							hasChildren
								? (e) => {
										e.stopPropagation();
										onToggleNode(node.id);
									}
								: undefined
						}
						mergeFromDepth={mergeFromDepth}
					/>

					{/* Row content */}
					<div className="flex items-center gap-1.5 min-w-0 flex-1 py-1.5 pr-3">
						<span
							className={`
								min-w-0 flex-1 text-[13px] text-gray-800 truncate
								${node.type === "agent" || node.type === "orchestrator" ? "font-semibold" : "font-medium"}
							`}
							title={node.name}
						>
							{highlightMatch(node.name)}
						</span>

						{node.metadata?.nodeType &&
							node.metadata.nodeType !== "AGENT" &&
							node.metadata.nodeType !== "START" &&
							node.metadata.nodeType !== "END" && (
								<span
									className={`shrink-0 ${traceStyles.badgeSmall} capitalize tracking-wide text-slate-700`}
								>
									{node.metadata.nodeType.replace(/_/g, " ")}
								</span>
							)}

						<div className="shrink-0 flex items-center gap-1">
							{violationsByNodeId?.has(node.id) && (() => {
								const nodeViolations = violationsByNodeId.get(node.id)!;
								const hasBlock = nodeViolations.some(v => v.severity === "block");
								return (
									<span
										className={`flex items-center gap-1 rounded-[4px] border px-1.5 py-0.5 text-[10px] font-medium ${
											hasBlock
												? "border-red-300 bg-white text-red-800"
												: "border-amber-500 bg-white text-amber-900"
										}`}
										title={`${nodeViolations.length} guardrail violation${nodeViolations.length !== 1 ? "s" : ""}`}
									>
										<ShieldAlert className="w-3 h-3" />
										<span className="font-mono">{nodeViolations.length}</span>
									</span>
								);
							})()}

							{(node.type === "agent" || node.type === "orchestrator") &&
								node.metadata?.tokens?.total && (
									<span
										className={`${traceStyles.badgeSmall} flex items-center gap-1 text-slate-700`}
									>
										<Zap className="h-3 w-3 text-orange-600" />
										<span className="font-mono">
											{node.metadata.tokens.total.toLocaleString()}
										</span>
									</span>
								)}

							{(node.type === "agent" || node.type === "orchestrator") &&
								node.metadata?.cost &&
								node.metadata.cost > 0 && (
									<span className="flex items-center gap-1 rounded-[4px] border border-orange-500 bg-white px-1.5 py-0.5 text-[10px] font-medium text-orange-800">
										<DollarSign className="h-3 w-3" />
										<span className="font-mono">
											{node.metadata.cost.toFixed(4)}
										</span>
									</span>
								)}

							{node.duration && (
								<span
									className={`${traceStyles.badgeSmall} font-mono text-slate-600`}
								>
									{formatDuration(node.duration)}
								</span>
							)}

							{getStatusIcon()}
						</div>
					</div>
				</div>

				{/* Children + closing rail */}
				{hasExpandedChildren && (
					<>
						{node.children.map((child, index) => {
							const isLastChild =
								index === node.children.length - 1;
							const prevChild =
								index > 0 ? node.children[index - 1] : null;
							const prevMergeDepth = prevChild
								? getDeepestExpandedDepth(
										prevChild,
										depth + 1,
										expandedNodes,
									)
								: depth + 1;
							return (
								<TraceTreeNode
									key={child.id}
									node={child}
									depth={depth + 1}
									isFirstSibling={index === 0}
									isLastSibling={isLastChild}
									continuingRails={childContinuingRails}
									expandedNodes={expandedNodes}
									selectedNode={selectedNode}
									onToggleNode={onToggleNode}
									onSelectNode={onSelectNode}
									searchQuery={searchQuery}
									mergeFromDepth={
										prevMergeDepth > depth + 1
											? prevMergeDepth
											: undefined
									}
									violationsByNodeId={violationsByNodeId}
								/>
							);
						})}
					</>
				)}
			</div>
		);
	},
);

TraceTreeNode.displayName = "TraceTreeNode";

export default function TraceTree({
	nodes,
	expandedNodes,
	selectedNode,
	onToggleNode,
	onSelectNode,
	searchQuery,
	violationsByNodeId,
}: TraceTreeProps) {
	return (
		<div
			className={`trace-tree h-full overflow-auto custom-scrollbar py-1 ${traceStyles.panelGradient}`}
		>
			{nodes.length > 0 ? (
				nodes.map((node, index) => {
					const prevNode = index > 0 ? nodes[index - 1] : null;
					const prevMergeDepth = prevNode
						? getDeepestExpandedDepth(prevNode, 0, expandedNodes)
						: 0;
					return (
						<TraceTreeNode
							key={node.id}
							node={node}
							depth={0}
							isFirstSibling={index === 0}
							isLastSibling={index === nodes.length - 1}
							continuingRails={
								index < nodes.length - 1
									? new Set([0])
									: EMPTY_RAILS
							}
							expandedNodes={expandedNodes}
							selectedNode={selectedNode}
							onToggleNode={onToggleNode}
							onSelectNode={onSelectNode}
							searchQuery={searchQuery}
							mergeFromDepth={
								prevMergeDepth > 0
									? prevMergeDepth
									: undefined
							}
							violationsByNodeId={violationsByNodeId}
						/>
					);
				})
			) : (
				<div className="flex flex-col items-center justify-center h-full gap-3">
					<span className="text-sm text-[color:var(--color-text-muted)]">
						No nodes to display
					</span>
				</div>
			)}
		</div>
	);
}
