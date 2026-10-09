"use client";

import { Bot, Info, Layers } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import type { Node } from "reactflow";
import InfoTooltip from "../../../ui/InfoTooltipPortal";

interface OrchestrationSectionProps {
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

export default function OrchestrationSection({
	isOrchestrator,
	isSubAgent,
	orchestratorMode = "supervisor",
	delegatedAgents,
	nodes,
	subAgentDelegationDescriptions,
	onSubAgentDelegationDescriptionsChange,
	delegationDescription,
	onDelegationDescriptionChange,
}: OrchestrationSectionProps) {
	const handleSubAgentDescriptionChange = useCallback(
		(agentId: string, description: string) => {
			onSubAgentDelegationDescriptionsChange({
				...subAgentDelegationDescriptions,
				[agentId]: description,
			});
		},
		[subAgentDelegationDescriptions, onSubAgentDelegationDescriptionsChange],
	);

	const createSubAgentDescriptionHandler = useCallback(
		(agentId: string) => (e: React.ChangeEvent<HTMLTextAreaElement>) => {
			handleSubAgentDescriptionChange(agentId, e.target.value);
		},
		[handleSubAgentDescriptionChange],
	);

	const handleDelegationDescriptionChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			onDelegationDescriptionChange(e.target.value);
		},
		[onDelegationDescriptionChange],
	);

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start gap-3">
					<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 text-orange-600">
						<Layers className="h-6 w-6" />
					</div>
					<div className="flex-1">
						<div className="flex flex-wrap items-center gap-3">
							<h3 className="text-xl font-semibold text-slate-900">
								Orchestration
							</h3>
							<span className="inline-flex items-center gap-2 rounded-[4px] border border-orange-400 bg-white px-3 py-1 text-xs font-semibold text-orange-800">
								{isOrchestrator ? "Orchestrator" : "Sub-agent"}
							</span>
						</div>
						<p className="mt-2 text-sm text-slate-600">
							{isOrchestrator
								? "Coordinate sub-agents and write guidance so delegation feels natural."
								: "Describe what your orchestrator should delegate to you."}
						</p>
					</div>
				</div>
			</div>

			{isOrchestrator && (
				<>
					<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-5 shadow-sm">
						<div className="flex items-start gap-3">
							<Info className="h-5 w-5 shrink-0 text-orange-600" />
							<div>
								<h4 className="text-sm font-semibold text-slate-900">
									Mode: {orchestratorMode}
								</h4>
								<p className="mt-1 text-xs text-slate-600">
									Manages {delegatedAgents.length} sub-agent
									{delegatedAgents.length === 1 ? "" : "s"} with dynamic
									delegation.
								</p>
							</div>
						</div>
					</div>

					{delegatedAgents.length > 0 && (
						<div className="space-y-4 rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
							<div>
								<h4 className="text-sm font-semibold text-slate-900">
									Sub-agent playbooks
								</h4>
								<p className="text-xs text-slate-600">
									Describe when each teammate should take ownership.
								</p>
							</div>
							<div className="space-y-4">
								{delegatedAgents.map((agentId) => {
									const subAgent = nodes.find((n) => n.id === agentId);
									if (!subAgent) return null;
									return (
										<div
											key={agentId}
											className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm"
										>
											<div className="mb-3 flex items-center gap-2">
												<Bot className="h-4 w-4 text-orange-600" />
												<span className="text-sm font-semibold text-slate-900">
													{subAgent.data.name || "Unnamed Agent"}
												</span>
											</div>
											<textarea
												value={subAgentDelegationDescriptions[agentId] || ""}
												onChange={createSubAgentDescriptionHandler(agentId)}
												rows={3}
												className="w-full rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-colors hover:border-orange-400 focus:border-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/15"
												placeholder={`When should ${subAgent.data.name || "this agent"} handle the task?`}
											/>
										</div>
									);
								})}
							</div>
						</div>
					)}
				</>
			)}

			{isSubAgent && (
				<div className="space-y-3 rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
					<div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
						Delegation guidance
						<InfoTooltip text="Help the orchestrator understand when to route work to this specialist." />
					</div>
					<textarea
						value={delegationDescription}
						onChange={handleDelegationDescriptionChange}
						rows={6}
						className="w-full rounded-[4px] border border-slate-200 bg-white px-4 py-3 font-mono text-sm text-slate-900 placeholder:text-slate-400 transition-colors hover:border-orange-400 focus:border-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/15"
						placeholder="Specializes in...

Example:
• Expert in researching and analyzing technical documentation
• Handles data processing and statistical analysis
• Manages customer inquiries and support tickets"
					/>
				</div>
			)}
		</div>
	);
}
