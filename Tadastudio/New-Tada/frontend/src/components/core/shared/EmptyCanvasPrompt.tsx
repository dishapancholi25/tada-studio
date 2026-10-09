"use client";

import { Calendar, Mail, Play, Webhook } from "lucide-react";
import { useCallback } from "react";

interface EmptyCanvasPromptProps {
	onAddNode?: (nodeType: string) => void;
}

interface TriggerOption {
	id: string;
	label: string;
	icon: typeof Play;
	available: boolean;
	nodeType: string;
}

const triggerOptions: TriggerOption[] = [
	{
		id: "manual",
		label: "Manual Run",
		icon: Play,
		available: true,
		nodeType: "AGENT",
	},
	{
		id: "webhook",
		label: "API Webhook",
		icon: Webhook,
		available: false,
		nodeType: "WEBHOOK",
	},
	{
		id: "schedule",
		label: "Schedule",
		icon: Calendar,
		available: false,
		nodeType: "SCHEDULE",
	},
	{
		id: "email",
		label: "Email",
		icon: Mail,
		available: false,
		nodeType: "EMAIL",
	},
];

export default function EmptyCanvasPrompt({
	onAddNode,
}: EmptyCanvasPromptProps) {
	const handleTriggerClick = useCallback(
		(option: TriggerOption) => {
			if (option.available && onAddNode) {
				onAddNode(option.nodeType);
			}
		},
		[onAddNode],
	);

	return (
		<div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10 animate-fadeInUp">
			<div className="mt-48 flex flex-col items-center gap-4 pointer-events-auto">
				{/* Heading */}
				<h3 className="text-lg font-semibold text-[color:var(--color-text-secondary)]">
					What triggers this workflow?
				</h3>

				{/* Quick-add pills */}
				<div className="flex items-center gap-2">
					{triggerOptions.map((option) => {
						const Icon = option.icon;
						return (
							<button
								key={option.id}
								onClick={() => handleTriggerClick(option)}
								disabled={!option.available}
								className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium border transition-all duration-200 ${
									option.available
										? "border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)]/80 text-[color:var(--color-text-primary)] hover:border-[color:var(--color-primary)]/60 hover:bg-[color:var(--color-surface)]/60 hover:shadow-[0_0_16px_rgba(var(--color-primary-rgb),0.2)] backdrop-blur-sm cursor-pointer"
										: "border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/40 text-[color:var(--color-text-disabled)] cursor-not-allowed"
								}`}
								title={
									option.available
										? `Start with ${option.label}`
										: "Coming soon"
								}
							>
								<Icon className="w-3.5 h-3.5" />
								<span>{option.label}</span>
								{!option.available && (
									<span className="text-[10px] capitalize tracking-wider text-[color:var(--color-text-disabled)]/70">
										Soon
									</span>
								)}
							</button>
						);
					})}
				</div>

				{/* Keyboard hint */}
				<p className="text-xs text-[color:var(--color-text-muted)]/50 mt-1">
					Press{" "}
					<kbd className="px-1.5 py-0.5 rounded border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-muted)]/70 text-[11px] font-mono">
						N
					</kbd>{" "}
					to add a node
				</p>
			</div>
		</div>
	);
}
