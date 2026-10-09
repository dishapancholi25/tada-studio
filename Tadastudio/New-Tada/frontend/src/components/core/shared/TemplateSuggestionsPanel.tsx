"use client";

import {
	Bot,
	Database,
	Globe,
	Layout,
	Sparkles,
	X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

interface WorkflowTemplate {
	id: string;
	name: string;
	description: string;
	icon: typeof Bot;
	iconColor: string;
	nodeCount: number;
	nodes: TemplateNode[];
	edges: TemplateEdge[];
}

interface TemplateNode {
	type: string;
	name: string;
	position: { x: number; y: number };
}

interface TemplateEdge {
	sourceIndex: number;
	targetIndex: number;
}

const STARTER_TEMPLATES: WorkflowTemplate[] = [
	{
		id: "api-integration",
		name: "API Integration",
		description: "Fetch data from an API and process the response",
		icon: Globe,
		iconColor: "59, 130, 246",
		nodeCount: 4,
		nodes: [
			{ type: "START", name: "Start", position: { x: 0, y: 0 } },
			{
				type: "AGENT",
				name: "Process Request",
				position: { x: 350, y: 0 },
			},
			{
				type: "HTTP_REQUEST_ACTION",
				name: "API Call",
				position: { x: 700, y: 0 },
			},
			{ type: "END", name: "End", position: { x: 1050, y: 0 } },
		],
		edges: [
			{ sourceIndex: 0, targetIndex: 1 },
			{ sourceIndex: 1, targetIndex: 2 },
			{ sourceIndex: 2, targetIndex: 3 },
		],
	},
	{
		id: "data-processing",
		name: "Data Processing",
		description: "Read data, transform with AI, and store results",
		icon: Database,
		iconColor: "16, 185, 129",
		nodeCount: 4,
		nodes: [
			{ type: "START", name: "Start", position: { x: 0, y: 0 } },
			{
				type: "FILE_READ",
				name: "Read Input",
				position: { x: 350, y: 0 },
			},
			{
				type: "AGENT",
				name: "Transform Data",
				position: { x: 700, y: 0 },
			},
			{ type: "END", name: "End", position: { x: 1050, y: 0 } },
		],
		edges: [
			{ sourceIndex: 0, targetIndex: 1 },
			{ sourceIndex: 1, targetIndex: 2 },
			{ sourceIndex: 2, targetIndex: 3 },
		],
	},
	{
		id: "ai-agent",
		name: "AI Agent",
		description: "Single agent with conditional branching logic",
		icon: Sparkles,
		iconColor: "168, 85, 247",
		nodeCount: 5,
		nodes: [
			{ type: "START", name: "Start", position: { x: 0, y: 0 } },
			{
				type: "AGENT",
				name: "AI Agent",
				position: { x: 350, y: 0 },
			},
			{
				type: "CONDITION",
				name: "Route",
				position: { x: 700, y: 0 },
			},
			{
				type: "AGENT",
				name: "Handle A",
				position: { x: 1050, y: -100 },
			},
			{
				type: "AGENT",
				name: "Handle B",
				position: { x: 1050, y: 100 },
			},
		],
		edges: [
			{ sourceIndex: 0, targetIndex: 1 },
			{ sourceIndex: 1, targetIndex: 2 },
			{ sourceIndex: 2, targetIndex: 3 },
			{ sourceIndex: 2, targetIndex: 4 },
		],
	},
];

const STORAGE_KEY = "agenticstudio-hide-template-suggestions";

interface TemplateSuggestionsPanelProps {
	onSelectTemplate?: (template: WorkflowTemplate) => void;
}

export default function TemplateSuggestionsPanel({
	onSelectTemplate,
}: TemplateSuggestionsPanelProps) {
	const [isDismissed, setIsDismissed] = useState(() => {
		if (typeof window !== "undefined") {
			return localStorage.getItem(STORAGE_KEY) === "true";
		}
		return false;
	});

	const handleDismiss = useCallback(() => {
		setIsDismissed(true);
		localStorage.setItem(STORAGE_KEY, "true");
	}, []);

	const handleSelect = useCallback(
		(template: WorkflowTemplate) => {
			onSelectTemplate?.(template);
		},
		[onSelectTemplate],
	);

	if (isDismissed) return null;

	return (
		<div className="absolute bottom-24 right-6 z-20 pointer-events-auto animate-fadeInUp">
			<div className="w-[280px] rounded-2xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/90 backdrop-blur-xl shadow-[0_16px_48px_rgba(0,0,0,0.4)]">
				{/* Header */}
				<div className="flex items-center justify-between px-4 pt-4 pb-2">
					<div className="flex items-center gap-2">
						<Layout className="w-4 h-4 text-[color:var(--color-primary)]" />
						<span className="text-sm font-semibold text-[color:var(--color-text-primary)]">
							Start from a template
						</span>
					</div>
					<button
						onClick={handleDismiss}
						className="p-1 rounded-lg text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)] hover:bg-[color:var(--color-surface)]/60 transition-all"
						aria-label="Dismiss templates"
					>
						<X className="w-3.5 h-3.5" />
					</button>
				</div>

				{/* Templates list */}
				<div className="px-3 pb-3 space-y-1.5">
					{STARTER_TEMPLATES.map((template) => {
						const Icon = template.icon;
						return (
							<button
								key={template.id}
								onClick={() => handleSelect(template)}
								className="w-full flex items-start gap-3 p-2.5 rounded-xl border border-transparent hover:border-[color:var(--color-border)]/40 hover:bg-[color:var(--color-surface)]/40 transition-all duration-200 text-left group"
							>
								<div
									className="h-8 w-8 rounded-lg border flex items-center justify-center flex-shrink-0 mt-0.5 transition-all group-hover:scale-105"
									style={{
										backgroundColor: `rgba(${template.iconColor}, 0.12)`,
										borderColor: `rgba(${template.iconColor}, 0.3)`,
									}}
								>
									<Icon
										className="w-4 h-4"
										style={{
											color: `rgba(${template.iconColor}, 0.9)`,
										}}
									/>
								</div>
								<div className="flex-1 min-w-0">
									<div className="flex items-center gap-2">
										<span className="text-sm font-medium text-[color:var(--color-text-primary)] group-hover:text-slate-900 transition-colors">
											{template.name}
										</span>
										<span className="text-[10px] px-1.5 py-0.5 rounded-full bg-[color:var(--color-surface)]/60 text-[color:var(--color-text-muted)] font-medium">
											{template.nodeCount} nodes
										</span>
									</div>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5 line-clamp-1">
										{template.description}
									</p>
								</div>
							</button>
						);
					})}
				</div>
			</div>
		</div>
	);
}

export { STARTER_TEMPLATES };
export type { WorkflowTemplate, TemplateNode, TemplateEdge };
