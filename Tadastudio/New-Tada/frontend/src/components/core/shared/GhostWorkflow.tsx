"use client";

import { Bot, CheckCircle, Play } from "lucide-react";
import { useCallback, useState } from "react";

interface GhostWorkflowProps {
	onAddNode?: (nodeType: string) => void;
	onDismiss?: () => void;
}

interface GhostNodeConfig {
	id: string;
	label: string;
	subtitle: string;
	icon: typeof Play;
	colorRgb: string;
	nodeType: string;
	isClickable: boolean;
}

const ghostNodes: GhostNodeConfig[] = [
	{
		id: "ghost-start",
		label: "Trigger",
		subtitle: "Entry point",
		icon: Play,
		colorRgb: "13, 169, 49",
		nodeType: "START",
		isClickable: false, // START already exists
	},
	{
		id: "ghost-agent",
		label: "Process",
		subtitle: "AI Agent",
		icon: Bot,
		colorRgb: "168, 85, 247",
		nodeType: "AGENT",
		isClickable: true,
	},
	{
		id: "ghost-end",
		label: "Output",
		subtitle: "End node",
		icon: CheckCircle,
		colorRgb: "239, 68, 68",
		nodeType: "END",
		isClickable: true,
	},
];

export default function GhostWorkflow({
	onAddNode,
	onDismiss,
}: GhostWorkflowProps) {
	const [hoveredNode, setHoveredNode] = useState<string | null>(null);

	const handleNodeClick = useCallback(
		(node: GhostNodeConfig) => {
			if (node.isClickable && onAddNode) {
				onAddNode(node.nodeType);
			}
		},
		[onAddNode],
	);

	return (
		<div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[5] animate-fadeInUp">
			<div className="flex items-center gap-6">
				{ghostNodes.map((node, index) => {
					const Icon = node.icon;
					const isHovered = hoveredNode === node.id;
					const isClickable = node.isClickable;

					return (
						<div key={node.id} className="flex items-center gap-6">
							{/* Ghost Node */}
							<div
								className={`relative flex flex-col items-center gap-2 transition-all duration-200 ${
									isClickable
										? "pointer-events-auto cursor-pointer"
										: "pointer-events-none"
								}`}
								style={{
									opacity: isHovered ? 0.5 : 0.3,
								}}
								onMouseEnter={
									isClickable
										? () => setHoveredNode(node.id)
										: undefined
								}
								onMouseLeave={
									isClickable
										? () => setHoveredNode(null)
										: undefined
								}
								onClick={
									isClickable
										? () => handleNodeClick(node)
										: undefined
								}
							>
								{/* Node card */}
								<div
									className={`relative w-[180px] rounded-2xl border-2 border-dashed p-4 transition-all duration-200 ${
										isHovered
											? "border-[color:var(--color-primary)]/50 bg-[color:var(--color-surface)]/30"
											: "border-[color:var(--color-border)]/40 bg-[color:var(--color-bg-secondary)]/20"
									}`}
								>
									{/* Header */}
									<div className="flex items-center gap-2 mb-2">
										<div
											className="h-7 w-7 rounded-lg border flex items-center justify-center"
											style={{
												backgroundColor: `rgba(${node.colorRgb}, 0.12)`,
												borderColor: `rgba(${node.colorRgb}, 0.35)`,
											}}
										>
											<Icon
												className="w-3.5 h-3.5"
												style={{
													color: `rgba(${node.colorRgb}, 0.8)`,
												}}
											/>
										</div>
										<span className="text-xs font-semibold capitalize tracking-wider text-[color:var(--color-text-muted)]">
											{node.label}
										</span>
									</div>
									{/* Subtitle */}
									<p className="text-xs text-[color:var(--color-text-muted)]/70">
										{node.subtitle}
									</p>

									{/* Hover tooltip */}
									{isHovered && isClickable && (
										<div className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap text-xs text-[color:var(--color-primary)] font-medium animate-fadeIn">
											Click to add
										</div>
									)}
								</div>
							</div>

							{/* Connector line (except after last node) */}
							{index < ghostNodes.length - 1 && (
								<svg
									width="60"
									height="2"
									className="flex-shrink-0"
									style={{ opacity: 0.2 }}
								>
									<line
										x1="0"
										y1="1"
										x2="60"
										y2="1"
										stroke="var(--color-border)"
										strokeWidth="2"
										strokeDasharray="6 4"
									/>
								</svg>
							)}
						</div>
					);
				})}
			</div>

			{/* Dismiss link */}
			{onDismiss && (
				<button
					onClick={onDismiss}
					className="pointer-events-auto absolute bottom-[30%] text-xs text-[color:var(--color-text-muted)]/40 hover:text-[color:var(--color-text-muted)]/70 transition-colors"
				>
					Dismiss
				</button>
			)}
		</div>
	);
}
