"use client";

import {
	Activity,
	Brain,
	Check,
	Clock,
	Copy,
	Cpu,
	Database,
	DollarSign,
	Gauge,
	GitBranch,
	Info,
	MessageSquare,
	Package,
	Server,
	Settings,
	Users,
	Zap,
} from "lucide-react";
import React, { useState } from "react";
import { traceStyles } from "./styles/traceStyles";

interface TraceNode {
	id: string;
	name: string;
	type: string;
	metadata: {
		nodeType?: string;
		llm?: any;
		tool?: any;
		orchestration?: any;
		memory?: any;
		environment?: any;
		embedding?: {
			tokens: number;
			cost: number;
			model: string;
		};
		tokens?: {
			input: number;
			output: number;
			total: number;
		};
		cost?: number;
		cost_estimated?: boolean;
	};
	messages?: any[];
}

interface TraceMetadataPanelProps {
	node: TraceNode;
}

export default function TraceMetadataPanel({ node }: TraceMetadataPanelProps) {
	const [activeTab, setActiveTab] = useState("overview");
	const [copiedField, setCopiedField] = useState<string | null>(null);

	const copyToClipboard = async (text: string, field: string) => {
		try {
			await navigator.clipboard.writeText(text);
			setCopiedField(field);
			setTimeout(() => setCopiedField(null), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	};

	const tabs = [
		{ id: "overview", label: "Overview", icon: Info },
		...(node.type === "agent" || node.type === "orchestrator"
			? [{ id: "llm", label: "Model", icon: Brain }]
			: []),
		...(node.metadata?.embedding
			? [{ id: "model", label: "Model", icon: Brain }]
			: []),
		...(node.metadata?.tool
			? [{ id: "tool", label: "Tool", icon: Settings }]
			: []),
		...(node.metadata?.orchestration
			? [{ id: "orchestration", label: "Orchestration", icon: Users }]
			: []),
		...(node.metadata?.memory
			? [{ id: "memory", label: "Memory", icon: Database }]
			: []),
		...(node.metadata?.environment
			? [{ id: "environment", label: "Environment", icon: Server }]
			: []),
	];

	const renderOverview = () => (
		<div className="space-y-4">
			{/* Token Usage */}
			{node.metadata?.tokens && (
				<div className={`${traceStyles.tertiaryCard} p-4`}>
					<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
						<div className={traceStyles.iconCapsuleSm}>
							<Zap className="w-3 h-3 text-orange-600" />
						</div>
						<span className={traceStyles.sectionHeader}>Token Usage</span>
					</div>
					<div className="space-y-2.5">
						<div className="flex justify-between text-sm">
							<span className={traceStyles.inlineLabel}>Input Tokens</span>
							<span className="text-slate-900 font-mono">
								{node.metadata.tokens.input?.toLocaleString() || 0}
							</span>
						</div>
						<div className="flex justify-between text-sm">
							<span className={traceStyles.inlineLabel}>Output Tokens</span>
							<span className="text-slate-900 font-mono">
								{node.metadata.tokens.output?.toLocaleString() || 0}
							</span>
						</div>
						<div
							className={`${traceStyles.highlightRow} flex justify-between text-sm font-medium mt-3 -mx-4 -mb-4 rounded-t-none`}
						>
							<span className="text-slate-700">
								Total
							</span>
							<span className="text-orange-800 font-mono">
								{node.metadata.tokens.total?.toLocaleString() || 0}
							</span>
						</div>
					</div>
				</div>
			)}

			{/* Cost Breakdown - Only for agents and orchestrators */}
			{(node.type === "agent" || node.type === "orchestrator") &&
				node.metadata?.llm &&
				(node.metadata.llm.prompt_cost || node.metadata.llm.completion_cost) && (
					<div className={`${traceStyles.tertiaryCard} p-4`}>
						<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
							<div className={traceStyles.iconCapsuleSm}>
								<DollarSign className="w-3 h-3 text-orange-600" />
							</div>
							<span className={traceStyles.sectionHeader}>Cost Breakdown</span>
						</div>
						<div className="space-y-2.5">
							<div className="flex justify-between text-sm">
								<span className={traceStyles.inlineLabel}>Prompt Cost</span>
								<span className="text-slate-900 font-mono">
									${node.metadata.llm.prompt_cost?.toFixed(6) || "0.000000"}
								</span>
							</div>
							<div className="flex justify-between text-sm">
								<span className={traceStyles.inlineLabel}>Completion Cost</span>
								<span className="text-slate-900 font-mono">
									${node.metadata.llm.completion_cost?.toFixed(6) || "0.000000"}
								</span>
							</div>
							<div
								className={`${traceStyles.highlightRow} flex justify-between text-sm font-medium mt-3 -mx-4 -mb-4 rounded-t-none`}
							>
								<span className="text-slate-700">
									Total
								</span>
								<span className="text-orange-800 font-mono">
									${(node.metadata.llm.total_cost || 0).toFixed(6)}
								</span>
							</div>
						</div>
						{node.metadata?.cost_estimated && (
							<div className="mt-2 text-xs text-[color:var(--color-warning,#f59e0b)] flex items-center gap-1.5 group/est relative">
								<span>Estimated</span>
								<Info className="w-3 h-3 flex-shrink-0 cursor-help" />
								<div className="absolute bottom-full left-0 z-10 mb-1 hidden w-52 rounded-[4px] border border-slate-200 bg-white p-2 text-xs text-slate-700 shadow-lg group-hover/est:block">
									Cost was not recorded at execution time. This estimate uses current model rates and may differ from the actual cost incurred.
								</div>
							</div>
						)}
					</div>
				)}

			{/* Node Type Info */}
			<div className={`${traceStyles.tertiaryCard} p-4`}>
				<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
					<div className={traceStyles.iconCapsuleSm}>
						<Activity className="w-3 h-3 text-orange-600" />
					</div>
					<span className={traceStyles.sectionHeader}>Node Information</span>
				</div>
				<div className="space-y-2.5">
					<div className="flex justify-between text-sm">
						<span className={traceStyles.inlineLabel}>Type</span>
						<span className="text-slate-900 font-medium capitalize tracking-wide">
							{node.type}
						</span>
					</div>
					<div className="flex justify-between text-sm">
						<span className={traceStyles.inlineLabel}>ID</span>
						<span className="text-slate-900 font-mono text-xs">
							{node.id.substring(0, 8)}...
						</span>
					</div>
				</div>
			</div>
		</div>
	);

	const renderLLMMetadata = () => {
		const llm = node.metadata?.llm;
		if (!llm)
			return (
				<div className="flex flex-col items-center justify-center h-32 gap-2">
					<Brain className="w-5 h-5 text-[color:var(--color-text-muted)]" />
					<span className="text-sm text-[color:var(--color-text-muted)]">
						No LLM metadata captured for this node
					</span>
				</div>
			);

		const messages = node.messages;

		return (
			<div className="space-y-4">
				{/* 1. Model Configuration */}
				<div className={`${traceStyles.tertiaryCard} p-4`}>
					<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
						<div className={traceStyles.iconCapsuleSm}>
							<Cpu className="w-3 h-3 text-orange-600" />
						</div>
						<span className={traceStyles.sectionHeader}>
							Model Configuration
						</span>
					</div>
					<div className="space-y-2.5 text-sm">
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Model</span>
							<span className="text-slate-900 font-mono">{llm.model || "N/A"}</span>
						</div>
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Provider</span>
							<span className="text-slate-900">{llm.provider || "N/A"}</span>
						</div>
						{llm.deployment_name && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Deployment</span>
								<span className="text-slate-900 font-mono text-xs">
									{llm.deployment_name}
								</span>
							</div>
						)}
						{llm.temperature !== undefined && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Temperature</span>
								<span className="text-slate-900 font-mono">{llm.temperature}</span>
							</div>
						)}
						{llm.max_tokens && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Max Tokens</span>
								<span className="text-slate-900 font-mono">{llm.max_tokens}</span>
							</div>
						)}
						{llm.finish_reason && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Finish Reason</span>
								<span className="text-slate-900 font-mono">
									{llm.finish_reason}
								</span>
							</div>
						)}
						{llm.model_version && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Model Version</span>
								<span className="text-slate-900 font-mono text-xs">
									{llm.model_version}
								</span>
							</div>
						)}
					</div>
				</div>

				{/* 2. Performance Metrics */}
				{(llm.tokens_per_second ||
					llm.time_to_first_token ||
					llm.total_latency_ms ||
					llm.request_start) && (
					<div className={`${traceStyles.tertiaryCard} p-4`}>
						<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
							<div className={traceStyles.iconCapsuleSm}>
								<Gauge className="w-3 h-3 text-orange-600" />
							</div>
							<span className={traceStyles.sectionHeader}>
								Performance Metrics
							</span>
						</div>
						<div className="space-y-2.5 text-sm">
							{llm.time_to_first_token && (
								<div className="flex justify-between">
									<span className={traceStyles.inlineLabel}>
										Time to First Token
									</span>
									<span className="text-slate-900 font-mono">
										{llm.time_to_first_token.toFixed(0)}ms
									</span>
								</div>
							)}
							{llm.tokens_per_second && (
								<div className="flex justify-between">
									<span className={traceStyles.inlineLabel}>
										Tokens/Second
									</span>
									<span className="text-slate-900 font-mono">
										{llm.tokens_per_second.toFixed(1)}
									</span>
								</div>
							)}
							{llm.total_latency_ms && (
								<div className="flex justify-between">
									<span className={traceStyles.inlineLabel}>
										Total Latency
									</span>
									<span className="text-slate-900 font-mono">
										{llm.total_latency_ms.toFixed(0)}ms
									</span>
								</div>
							)}
							{llm.request_start && (
								<div className="flex justify-between">
									<span className={traceStyles.inlineLabel}>
										Request Start
									</span>
									<span className="text-slate-900 font-mono text-xs">
										{new Date(
											llm.request_start * 1000,
										).toLocaleTimeString()}
									</span>
								</div>
							)}
							{llm.request_end && (
								<div className="flex justify-between">
									<span className={traceStyles.inlineLabel}>
										Request End
									</span>
									<span className="text-slate-900 font-mono text-xs">
										{new Date(
											llm.request_end * 1000,
										).toLocaleTimeString()}
									</span>
								</div>
							)}
							{llm.cache_hit !== undefined && (
								<div className="flex justify-between items-center">
									<span className={traceStyles.inlineLabel}>Cache Hit</span>
									<span
										className={`px-2 py-0.5 text-[10px] font-semibold capitalize tracking-wide rounded-full border ${
											llm.cache_hit
												? "bg-[color:var(--color-success)]/15 text-[color:var(--color-success)] border-[color:var(--color-success)]/35"
												: "bg-[color:var(--color-text-muted)]/10 text-[color:var(--color-text-muted)] border-[color:var(--color-border)]/40"
										}`}
									>
										{llm.cache_hit ? "Yes" : "No"}
									</span>
								</div>
							)}
						</div>
					</div>
				)}

				{/* Cost Breakdown */}
				{(llm.prompt_cost || llm.completion_cost) && (
					<div className={`${traceStyles.tertiaryCard} p-4`}>
						<h4 className={`${traceStyles.sectionHeader} mb-4`}>
							Cost Breakdown
						</h4>
						<div className="space-y-2.5 text-sm">
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Prompt Cost</span>
								<span className="text-slate-900 font-mono">
									${llm.prompt_cost?.toFixed(6) || "0.000000"}
								</span>
							</div>
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Completion Cost</span>
								<span className="text-slate-900 font-mono">
									${llm.completion_cost?.toFixed(6) || "0.000000"}
								</span>
							</div>
							{llm.pricing_source && (
								<div className="flex justify-between items-center">
									<span className={traceStyles.inlineLabel}>
										Pricing Source
									</span>
									<span
										className={`rounded-[4px] border px-2 py-0.5 text-xs font-medium ${
											llm.pricing_source === "deployment"
												? "border-emerald-300 bg-emerald-50 text-emerald-800"
												: llm.pricing_source === "litellm"
													? "border-blue-300 bg-blue-50 text-blue-800"
													: "border-slate-200 bg-slate-50 text-slate-700"
										}`}
									>
										{llm.pricing_source === "deployment"
											? "Custom deployment config"
											: llm.pricing_source === "litellm"
												? "LiteLLM data"
												: "Default estimate"}
									</span>
								</div>
							)}
							<div
								className={`${traceStyles.highlightRow} flex justify-between text-sm font-medium mt-3 -mx-4 -mb-4 rounded-t-none`}
							>
								<span className="text-slate-700">
									Total
								</span>
								<span className="text-orange-800 font-mono">
									${(llm.total_cost || 0).toFixed(6)}
								</span>
							</div>
						</div>
						{node.metadata?.cost_estimated && (
							<div className="mt-2 text-xs text-[color:var(--color-warning,#f59e0b)] flex items-center gap-1.5 group/est relative">
								<span>Estimated</span>
								<Info className="w-3 h-3 flex-shrink-0 cursor-help" />
								<div className="absolute bottom-full left-0 z-10 mb-1 hidden w-52 rounded-[4px] border border-slate-200 bg-white p-2 text-xs text-slate-700 shadow-lg group-hover/est:block">
									Cost was not recorded at execution time. This estimate uses current model rates and may differ from the actual cost incurred.
								</div>
							</div>
						)}
					</div>
				)}
			</div>
		);
	};

	const renderToolMetadata = () => {
		const tool = node.metadata?.tool;
		if (!tool) return null;

		return (
			<div className="space-y-4">
				<div className={`${traceStyles.tertiaryCard} p-4`}>
					<h4 className={`${traceStyles.sectionHeader} mb-4`}>
						Tool Execution
					</h4>
					<div className="space-y-2.5 text-sm">
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Tool Name</span>
							<span className="text-slate-900 font-mono">{tool.tool_name}</span>
						</div>
						{tool.execution_time_ms && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Execution Time</span>
								<span className="text-slate-900 font-mono">
									{tool.execution_time_ms?.toFixed(0) || "0"}ms
								</span>
							</div>
						)}
						{tool.error_details && (
							<div className="mt-3 p-3 bg-[color:var(--color-error)]/10 border border-[color:var(--color-error)]/30 rounded-lg">
								<span className="text-xs text-[color:var(--color-error)]">
									Error: {tool.error_details.error_message}
								</span>
							</div>
						)}
					</div>
				</div>
			</div>
		);
	};

	const renderOrchestrationMetadata = () => {
		const orch = node.metadata?.orchestration;
		if (!orch) return null;

		return (
			<div className="space-y-4">
				<div className={`${traceStyles.tertiaryCard} p-4`}>
					<h4 className={`${traceStyles.sectionHeader} mb-4`}>
						Subagent Statistics
					</h4>
					<div className="space-y-2.5 text-sm">
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Created</span>
							<span className="text-slate-900 font-mono">
								{orch.subagents_created || 0}
							</span>
						</div>
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Completed</span>
							<span className="text-[color:var(--color-success)] font-mono">
								{orch.subagents_completed || 0}
							</span>
						</div>
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Failed</span>
							<span className="text-[color:var(--color-error)] font-mono">
								{orch.subagents_failed || 0}
							</span>
						</div>
					</div>
				</div>
			</div>
		);
	};

	const renderEnvironmentMetadata = () => {
		const env = node.metadata?.environment;
		if (!env) return null;

		return (
			<div className="space-y-4">
				<div className={`${traceStyles.tertiaryCard} p-4`}>
					<h4 className={`${traceStyles.sectionHeader} mb-4`}>
						Runtime Environment
					</h4>
					<div className="space-y-2.5 text-sm">
						{env.python_version && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Python</span>
								<span className="text-slate-900 font-mono text-xs">
									{env.python_version.split(" ")[0]}
								</span>
							</div>
						)}
						{env.langchain_version && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>LangChain</span>
								<span className="text-slate-900 font-mono">
									{env.langchain_version}
								</span>
							</div>
						)}
						{env.langgraph_version && (
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>LangGraph</span>
								<span className="text-slate-900 font-mono">
									{env.langgraph_version}
								</span>
							</div>
						)}
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Environment</span>
							<span className="text-slate-900">
								{env.environment || "development"}
							</span>
						</div>
					</div>
				</div>

				{env.feature_flags && (
					<div className={`${traceStyles.tertiaryCard} p-4`}>
						<h4 className={`${traceStyles.sectionHeader} mb-4`}>
							Feature Flags
						</h4>
						<div className="space-y-2">
							{Object.entries(env.feature_flags).map(([flag, enabled]) => (
								<div
									key={flag}
									className="flex items-center justify-between text-sm"
								>
									<span className={`${traceStyles.inlineLabel} font-mono`}>
										{flag}
									</span>
									<span
										className={
											enabled
												? "text-[color:var(--color-success)]"
												: "text-[color:var(--color-text-muted)]"
										}
									>
										{enabled ? "✓" : "✗"}
									</span>
								</div>
							))}
						</div>
					</div>
				)}
			</div>
		);
	};

	const renderEmbeddingModelMetadata = () => {
		const embedding = node.metadata?.embedding;
		if (!embedding) return null;

		const hasTokens = embedding.tokens > 0;
		const hasCost = embedding.cost > 0;
		const modelName = embedding.model || "text-embedding-3-small";

		return (
			<div className="space-y-4">
				{/* Embedding Model Configuration */}
				<div className={`${traceStyles.tertiaryCard} p-4`}>
					<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
						<div className={traceStyles.iconCapsuleSm}>
							<Cpu className="w-3 h-3 text-orange-600" />
						</div>
						<span className={traceStyles.sectionHeader}>Embedding Model</span>
					</div>
					<div className="space-y-2.5 text-sm">
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Model</span>
							<span className="text-slate-900 font-mono">{modelName}</span>
						</div>
						<div className="flex justify-between">
							<span className={traceStyles.inlineLabel}>Type</span>
							<span className="text-slate-900">Embedding</span>
						</div>
					</div>
				</div>

				{/* Token Usage */}
				{hasTokens && (
					<div className={`${traceStyles.tertiaryCard} p-4`}>
						<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
							<div className={traceStyles.iconCapsuleSm}>
								<Zap className="w-3 h-3 text-orange-600" />
							</div>
							<span className={traceStyles.sectionHeader}>Token Usage</span>
						</div>
						<div className="space-y-2.5 text-sm">
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Query Tokens</span>
								<span className="text-slate-900 font-mono">
									{embedding.tokens.toLocaleString()}
								</span>
							</div>
						</div>
					</div>
				)}

				{/* Cost Breakdown */}
				{hasCost && (
					<div className={`${traceStyles.tertiaryCard} p-4`}>
						<div className="flex items-center gap-3 mb-4 pb-3 border-b border-slate-200">
							<div className={traceStyles.iconCapsuleSm}>
								<DollarSign className="w-3 h-3 text-orange-600" />
							</div>
							<span className={traceStyles.sectionHeader}>Cost Breakdown</span>
						</div>
						<div className="space-y-2.5 text-sm">
							<div className="flex justify-between">
								<span className={traceStyles.inlineLabel}>Embedding Cost</span>
								<span className="text-slate-900 font-mono">
									${embedding.cost.toFixed(6)}
								</span>
							</div>
							<div
								className={`${traceStyles.highlightRow} flex justify-between text-sm font-medium mt-3 -mx-4 -mb-4 rounded-t-none`}
							>
								<span className="text-slate-700">
									Total
								</span>
								<span className="text-orange-800 font-mono">
									${embedding.cost.toFixed(6)}
								</span>
							</div>
						</div>
					</div>
				)}

				{/* No data state */}
				{!hasTokens && !hasCost && (
					<div className={`${traceStyles.tertiaryCard} p-4`}>
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
	};

	const renderContent = () => {
		switch (activeTab) {
			case "overview":
				return renderOverview();
			case "llm":
				return renderLLMMetadata();
			case "model":
				return renderEmbeddingModelMetadata();
			case "tool":
				return renderToolMetadata();
			case "orchestration":
				return renderOrchestrationMetadata();
			case "environment":
				return renderEnvironmentMetadata();
			default:
				return renderOverview();
		}
	};

	return (
		<div
			className={`trace-metadata-panel h-full flex flex-col ${traceStyles.panelGradient}`}
		>
			{/* Tab Navigation */}
			<div className="flex overflow-x-auto border-b border-slate-200 bg-white">
				{tabs.map((tab) => (
					<button
						key={tab.id}
						onClick={() => setActiveTab(tab.id)}
						className={`flex items-center gap-2 px-4 py-3 text-sm whitespace-nowrap transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30 ${
							activeTab === tab.id
								? traceStyles.tabActive
								: `${traceStyles.tabInactive} hover:bg-slate-50`
						}`}
					>
						<tab.icon className="w-4 h-4" />
						{tab.label}
					</button>
				))}
			</div>

			{/* Tab Content */}
			<div className="flex-1 overflow-auto p-4 custom-scrollbar">
				{renderContent()}
			</div>
		</div>
	);
}
