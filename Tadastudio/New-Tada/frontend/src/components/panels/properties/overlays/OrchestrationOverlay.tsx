"use client";

import { Bot, Info, Layers, X } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import type { Node } from "reactflow";
import InfoTooltip from "../../../ui/InfoTooltipPortal";

interface OrchestrationOverlayProps {
	isOpen: boolean;
	onClose: () => void;
	isOrchestrator: boolean;
	isSubAgent: boolean;
	orchestratorMode?: string;
	delegatedAgents: string[];
	nodes: Node[];
	subAgentDelegationDescriptions: Record<string, string>;
	onSubAgentDelegationDescriptionsChange: (
		descriptions: Record<string, string>,
	) => void;
	delegationDescription: string;
	onDelegationDescriptionChange: (description: string) => void;
}

export default function OrchestrationOverlay({
	isOpen,
	onClose,
	isOrchestrator,
	isSubAgent,
	orchestratorMode = "supervisor",
	delegatedAgents,
	nodes,
	subAgentDelegationDescriptions,
	onSubAgentDelegationDescriptionsChange,
	delegationDescription,
	onDelegationDescriptionChange,
}: OrchestrationOverlayProps) {
	// Define helper function before hooks
	const handleSubAgentDescriptionChange = (
		agentId: string,
		description: string,
	) => {
		onSubAgentDelegationDescriptionsChange({
			...subAgentDelegationDescriptions,
			[agentId]: description,
		});
	};

	// All hooks must be called before any early returns (React Rules of Hooks)
	// Click handler to stop propagation
	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	// Factory function for sub-agent description handlers
	const createSubAgentDescriptionHandler = useCallback(
		(agentId: string) => (e: React.ChangeEvent<HTMLTextAreaElement>) => {
			handleSubAgentDescriptionChange(agentId, e.target.value);
		},
		[subAgentDelegationDescriptions, onSubAgentDelegationDescriptionsChange],
	);

	// Change handler for delegation description
	const handleDelegationDescriptionChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			onDelegationDescriptionChange(e.target.value);
		},
		[onDelegationDescriptionChange],
	);

	// Early return after all hooks have been called
	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-start justify-center z-[110] p-4 pt-8 sm:pt-16 lg:pt-20 animate-fadeIn overflow-y-auto"
			onClick={handleStopPropagation}
		>
			<div
				className="bg-gradient-to-b from-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)] border border-orange-400/50 rounded-xl shadow-2xl w-full max-w-5xl max-h-[calc(100vh-4rem)] sm:max-h-[calc(100vh-8rem)] lg:max-h-[calc(100vh-10rem)] mb-8 sm:mb-16 lg:mb-20 flex flex-col animate-scaleIn overflow-hidden"
				onClick={handleStopPropagation}
			>
				{/* Header */}
				<div className="flex items-center justify-between p-5 sm:p-6 bg-[color:var(--color-surface)]/50 border-b border-orange-400/30">
					<div className="flex items-center gap-3">
						<div className="p-3 bg-orange-400/10 rounded-xl">
							<Layers className="w-6 h-6 text-orange-400" />
						</div>
						<div>
							<h2 className="text-lg sm:text-xl font-bold text-slate-900 flex items-center gap-2">
								Orchestration
								<span className="text-xs px-2 py-0.5 bg-orange-400/20 text-orange-300 rounded-full">
									{isOrchestrator ? "Active" : "Sub-agent"}
								</span>
							</h2>
							<p className="text-sm text-[color:var(--color-text-muted)] mt-0.5">
								{isOrchestrator
									? "Manage sub-agents and delegation"
									: "Sub-agent delegation settings"}
							</p>
						</div>
					</div>
					<button
						onClick={onClose}
						className="p-2 hover:bg-[color:var(--color-border)]/50 rounded-lg transition-all hover:rotate-90 duration-200"
					>
						<X className="w-5 h-5 text-[color:var(--color-text-muted)]" />
					</button>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 min-h-0">
					{isOrchestrator && (
						<>
							{/* Orchestrator Info */}
							<div className="p-4 bg-orange-400/10 border border-orange-400/30 rounded-lg">
								<div className="flex items-start gap-3">
									<Info className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
									<div>
										<h4 className="text-sm font-medium text-orange-300">
											Orchestrator Mode: {orchestratorMode}
										</h4>
										<p className="text-xs text-orange-600/80 mt-1">
											This agent manages {delegatedAgents.length} sub-agent
											{delegatedAgents.length !== 1 ? "s" : ""}
										</p>
									</div>
								</div>
							</div>

							{/* Sub-Agent Delegation Descriptions */}
							{delegatedAgents.length > 0 && (
								<div className="space-y-4">
									<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)]">
										Sub-Agent Delegation Descriptions
									</h4>
									<p className="text-xs text-[color:var(--color-text-muted)]">
										Define when each sub-agent should be called by this
										orchestrator
									</p>
									<div className="space-y-3">
										{delegatedAgents.map((agentId) => {
											const subAgent = nodes.find((n) => n.id === agentId);
											return subAgent ? (
												<div
													key={agentId}
													className="border border-[color:var(--color-border)] rounded-lg p-4 bg-[color:var(--color-surface)]/30"
												>
													<div className="flex items-center gap-3 mb-3">
														<Bot className="w-4 h-4 text-orange-400" />
														<span className="text-sm font-medium text-slate-900">
															{subAgent.data.name || "Unnamed Agent"}
														</span>
													</div>
													<textarea
														value={
															subAgentDelegationDescriptions[agentId] || ""
														}
														onChange={createSubAgentDescriptionHandler(agentId)}
														rows={3}
														className="w-full px-3 py-2 input-dark rounded text-sm resize-none"
														placeholder={`When should ${subAgent.data.name || "this agent"} be called?\n\nExample: "Handle all requests related to..."`}
													/>
												</div>
											) : null;
										})}
									</div>
								</div>
							)}
						</>
					)}

					{/* Delegation Description - For sub-agents */}
					{isSubAgent && (
						<div className="space-y-4">
							<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] flex items-center gap-2">
								Delegation Description
								<InfoTooltip text="Describe when and how the orchestrator should delegate tasks to this sub-agent" />
							</h4>
							<div className="mb-2 p-3 bg-orange-400/10 border border-orange-400/30 rounded-lg">
								<p className="text-xs text-orange-300">
									This description helps the orchestrator understand when to use
									this sub-agent
								</p>
							</div>
							<textarea
								value={delegationDescription}
								onChange={handleDelegationDescriptionChange}
								rows={6}
								className="w-full px-4 py-3 rounded-lg text-slate-900 placeholder-slate-400 bg-white border border-slate-200 resize-none font-mono text-sm"
								placeholder="Specializes in...

Example:
• Expert in researching and analyzing technical documentation
• Handles data processing and statistical analysis
• Manages customer inquiries and support tickets"
							/>
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="p-6 border-t border-orange-400/30 bg-[color:var(--color-surface)]/50">
					<div className="flex justify-end">
						<button
							onClick={onClose}
							className="px-6 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-all border border-[color:var(--color-surface-hover)]"
						>
							Done
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
