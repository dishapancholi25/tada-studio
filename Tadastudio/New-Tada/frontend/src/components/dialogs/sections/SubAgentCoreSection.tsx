"use client";

import { Bot, Info, Sparkles } from "lucide-react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";
import FormTextarea from "@/components/ui/FormTextarea";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

const fieldClass =
	"!border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-slate-300 focus:!border-orange-500 focus:!ring-orange-500/20";

interface SubAgentCoreSectionProps {
	name: string;
	onNameChange: (name: string) => void;
	delegationDescription: string;
	onDelegationDescriptionChange: (description: string) => void;
	parentAgentName: string;
}

const suggestedDescriptions = [
	"Expert in researching and gathering information on specific topics",
	"Specialist in analyzing data and providing insights",
	"Handles specific technical implementation tasks",
	"Manages communication and user interaction",
	"Performs validation and quality checks",
];

export default function SubAgentCoreSection({
	name,
	onNameChange,
	delegationDescription,
	onDelegationDescriptionChange,
	parentAgentName,
}: SubAgentCoreSectionProps) {
	const toolName = `delegate_to_${name.toLowerCase().replace(/\s+/g, "_") || "agent"}`;

	return (
		<div className="space-y-6">
			{/* Info Banner */}
			<div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-orange-300">
				<div className="flex items-start gap-3">
					<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-orange-200 bg-orange-100 text-orange-600">
						<Info className="h-5 w-5" />
					</div>
					<div className="min-w-0 flex-1">
						<p className="text-sm font-medium text-slate-800">
							Creating a sub-agent for{" "}
							<span className="font-semibold text-orange-800">
								{parentAgentName}
							</span>
						</p>
						<p className="mt-1 text-xs text-slate-600">
							Sub-agents can be called as tools by the orchestrator to handle
							specific tasks
						</p>
					</div>
				</div>
			</div>

			{/* Core Configuration Section */}
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-orange-200 bg-orange-100 text-orange-600">
							<Bot className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Agent Identity
							</h3>
							<p className="text-sm text-slate-600">
								Define the agent&apos;s name and purpose
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div>
						<div className="mb-3 flex items-center gap-2">
							<label
								htmlFor="sub-agent-name"
								className="block text-sm font-semibold text-slate-800"
							>
								Agent Name
							</label>
							<InfoTooltip text="A descriptive name for this sub-agent (e.g., 'Research Assistant', 'Data Analyzer')" />
						</div>
						<FormInput
							id="sub-agent-name"
							value={name}
							onChange={(e) => onNameChange(e.target.value)}
							placeholder="e.g., Research Assistant, Data Analyzer"
							required
							className={fieldClass}
						/>
					</div>

					<div>
						<div className="mb-3 flex items-center gap-2">
							<label
								htmlFor="delegation-description"
								className="block text-sm font-semibold text-slate-800"
							>
								Delegation Description
							</label>
							<InfoTooltip text="Describe what this sub-agent specializes in and when it should be called by the orchestrator" />
						</div>
						<FormTextarea
							id="delegation-description"
							value={delegationDescription}
							onChange={(e) => onDelegationDescriptionChange(e.target.value)}
							placeholder="Describe what this sub-agent specializes in and when it should be called..."
							rows={4}
							required
							className={fieldClass}
						/>

						<div className="mt-3">
							<div className="mb-2 flex items-center gap-2">
								<Sparkles className="h-3.5 w-3.5 text-amber-600" />
								<p className="text-xs font-medium text-slate-600">
									Quick suggestions (click to use):
								</p>
							</div>
							<div className="flex flex-wrap gap-2">
								{suggestedDescriptions.map((desc, index) => (
									<Button
										key={`suggestion-${index}`}
										type="button"
										onClick={() => onDelegationDescriptionChange(desc)}
										variant="secondary"
										size="sm"
										className="!border !border-slate-200 !bg-white !px-3 !py-1.5 !text-xs !font-normal !text-slate-700 transition-all hover:!border-orange-400 hover:!bg-slate-50 hover:!text-orange-900"
									>
										{desc.substring(0, 30)}...
									</Button>
								))}
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* Tool Preview Section */}
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start gap-3 border-b border-slate-200 pb-4">
					<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-orange-200 bg-orange-100 text-orange-600">
						<Sparkles className="h-5 w-5" />
					</div>
					<div>
						<h3 className="text-lg font-semibold text-slate-900">Tool Preview</h3>
						<p className="mt-0.5 text-xs text-slate-600">
							How this agent will appear as a tool
						</p>
					</div>
				</div>

				<div className="mt-4 space-y-3">
					<div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
						<div className="flex items-start gap-3">
							<span className="mt-0.5 flex-shrink-0 text-xs font-medium text-slate-500">
								Tool name:
							</span>
							<code className="flex-1 break-all font-mono text-sm text-blue-800">
								{toolName}
							</code>
						</div>
					</div>

					<div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
						<div className="flex items-start gap-3">
							<span className="mt-0.5 flex-shrink-0 text-xs font-medium text-slate-500">
								Description:
							</span>
							<span className="flex-1 text-sm text-slate-800">
								{delegationDescription || (
									<span className="italic text-slate-500">
										No description provided
									</span>
								)}
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
