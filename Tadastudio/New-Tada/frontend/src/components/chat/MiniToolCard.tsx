"use client";

import { forwardRef } from "react";
import clsx from "clsx";
import { Zap } from "lucide-react";

import { getNodeColorRgb } from "@/components/panels/properties/inputSourceTypes";
import {
	detectProviderFromNodeName,
	getProviderVisuals,
} from "@/components/icons/McpProviderIcons";
import type { ProgressNode } from "./workflowProgressUtils";
import { StatusDot, formatDuration } from "./MiniNodeCard";

interface MiniToolCardProps {
	node: ProgressNode;
}

const MiniToolCard = forwardRef<HTMLDivElement, MiniToolCardProps>(
	({ node }, ref) => {
		const { nodeType, nodeName, status, durationSeconds, mcpProvider } = node;

		// Determine icon and color — prefer native MCP provider visuals
		let colorRgb = getNodeColorRgb(nodeType);
		let IconComponent: React.ComponentType<{ className?: string; size?: number; style?: React.CSSProperties }> = Zap;

		if (nodeType === "MCP_SERVER") {
			const provider = mcpProvider || detectProviderFromNodeName(nodeName);
			if (provider) {
				const visuals = getProviderVisuals(provider);
				IconComponent = visuals.icon;
				colorRgb = visuals.colorRgb;
			}
		}

		// Card background & border per state
		const cardStyle: React.CSSProperties = {};

		switch (status) {
			case "running":
				cardStyle.backgroundColor = "var(--wp-card-running-bg)";
				cardStyle.borderColor = "var(--wp-card-running-border)";
				break;
			case "completed":
				cardStyle.backgroundColor = "var(--wp-card-completed-bg)";
				cardStyle.borderColor = "var(--wp-card-completed-border)";
				break;
			case "failed":
				cardStyle.backgroundColor = "var(--wp-card-error-bg)";
				cardStyle.borderColor = "var(--wp-card-error-border)";
				break;
			default:
				cardStyle.backgroundColor = "var(--wp-card-pending-bg)";
				cardStyle.borderColor = "var(--wp-card-pending-border)";
				break;
		}

		// Subtitle
		let subtitle = "";
		let subtitleColor = "var(--color-text-disabled)";

		if (status === "completed" && durationSeconds != null) {
			subtitle = formatDuration(durationSeconds);
		} else if (status === "failed") {
			subtitle = "failed";
			subtitleColor = "rgba(239, 68, 68, 0.7)";
		}

		return (
			<div
				ref={ref}
				className={clsx(
					"flex items-center gap-2 px-2.5 py-2 rounded-lg border transition-all duration-300 cursor-pointer",
					"hover:brightness-110",
					status === "completed" && "opacity-85",
					status === "idle" && "opacity-45",
					status === "pending" && "opacity-[0.35]",
					status === "skipped" && "opacity-[0.35]",
				)}
				style={cardStyle}
			>
				{/* Compact icon */}
				<div className="shrink-0">
					<div
						className="flex h-7 w-7 items-center justify-center rounded-md"
						style={{ backgroundColor: `rgba(${colorRgb}, 0.1)` }}
					>
						<IconComponent
							className="h-3.5 w-3.5"
							size={14}
							style={{ color: `rgba(${colorRgb}, 0.6)` }}
						/>
					</div>
				</div>

				{/* Name + duration */}
				<div className="flex-1 min-w-0">
					<p
						className={clsx(
							"text-xs font-medium truncate",
							status === "idle" || status === "skipped" || status === "pending"
								? "text-[color:var(--color-text-disabled)]"
								: "text-[color:var(--color-text-secondary)]",
						)}
					>
						{nodeName}
					</p>
					{subtitle && (
						<p className="text-xs mt-0.5 truncate" style={{ color: subtitleColor }}>
							{subtitle}
						</p>
					)}
				</div>

				{/* Status dot */}
				<StatusDot status={status} />
			</div>
		);
	},
);

MiniToolCard.displayName = "MiniToolCard";

export default MiniToolCard;
