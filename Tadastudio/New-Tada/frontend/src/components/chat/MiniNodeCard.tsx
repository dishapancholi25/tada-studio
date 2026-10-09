"use client";

import { forwardRef, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import {
	AlertCircle,
	Bot,
	Code,
	Database,
	FileText,
	GitBranch,
	Globe,
	Layers,
	Mail,
	Play,
	Search,
	Square,
	Zap,
} from "lucide-react";

import {
	detectProviderFromNodeName,
	getProviderVisuals,
} from "@/components/icons/McpProviderIcons";
import type { ProgressNode, ProgressNodeStatus } from "./workflowProgressUtils";

/* ── Types ─────────────────────────────────────────── */

interface MiniNodeCardProps {
	node: ProgressNode;
	/** Whether the panel is in collapsed (icon-only) mode */
	collapsed?: boolean;
}

interface NodeTypeConfig {
	Icon: LucideIcon;
	/** RGB triplet string, e.g. "13, 169, 49" */
	rgb: string;
}

/* ── Node type → icon + colour mapping ─────────────── */

function getNodeTypeConfig(nodeType: string): NodeTypeConfig {
	switch (nodeType) {
		case "START":
			return { Icon: Play, rgb: "13, 169, 49" };
		case "END":
			return { Icon: Square, rgb: "156, 163, 175" };
		case "AGENT":
			return { Icon: Bot, rgb: "200, 162, 0" };
		case "CONDITION":
		case "CONDITIONAL":
			return { Icon: GitBranch, rgb: "168, 85, 247" };
		case "CHECKPOINT":
			return { Icon: AlertCircle, rgb: "168, 85, 247" };
		case "HTTP_REQUEST":
		case "HTTP_REQUEST_ACTION":
			return { Icon: Globe, rgb: "59, 130, 246" };
		case "DATABASE_QUERY":
		case "DATABASE_INSERT":
		case "DATABASE_QUERY_ACTION":
			return { Icon: Database, rgb: "59, 130, 246" };
		case "EMAIL_SEND":
			return { Icon: Mail, rgb: "59, 130, 246" };
		case "WEB_SEARCH":
			return { Icon: Search, rgb: "59, 130, 246" };
		case "DOCUMENT_SEARCH":
			return { Icon: FileText, rgb: "59, 130, 246" };
		case "FILE_READ":
		case "FILE_WRITE":
			return { Icon: FileText, rgb: "59, 130, 246" };
		case "SUBWORKFLOW":
			return { Icon: Layers, rgb: "59, 130, 246" };
		case "MCP_SERVER":
			return { Icon: Zap, rgb: "59, 130, 246" };
		default:
			return { Icon: Code, rgb: "200, 162, 0" };
	}
}

/* ── Status badge (small dot) ──────────────────────── */

export function StatusDot({ status }: { status: ProgressNodeStatus }) {
	if (status === "idle") return null;

	const base = "h-2 w-2 rounded-full shrink-0";

	switch (status) {
		case "completed":
			return <span className={clsx(base, "bg-[rgb(var(--wp-color-start))]")} />;
		case "running":
			return <span className={clsx(base, "bg-[#EAB308] animate-wpPulseDot")} />;
		case "pending":
			return <span className={clsx(base, "bg-slate-400/55")} />;
		case "failed":
			return <span className={clsx(base, "bg-[rgb(var(--wp-color-error))]")} />;
		case "stopped":
			return <span className={clsx(base, "bg-orange-400")} />;
		case "skipped":
			return <span className={clsx(base, "bg-slate-400/35")} />;
		default:
			return null;
	}
}

/* ── Duration formatter ────────────────────────────── */

export function formatDuration(seconds: number): string {
	if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
	if (seconds < 60) return `${seconds.toFixed(1)}s`;
	return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
}

/* ── Live elapsed timer hook ───────────────────────── */

function useElapsedTimer(isRunning: boolean): number {
	const [elapsed, setElapsed] = useState(0);
	const startRef = useRef<number>(Date.now());

	useEffect(() => {
		if (!isRunning) {
			setElapsed(0);
			return;
		}
		startRef.current = Date.now();
		const id = setInterval(() => {
			setElapsed((Date.now() - startRef.current) / 1000);
		}, 100);
		return () => clearInterval(id);
	}, [isRunning]);

	return elapsed;
}

/* ── Main component ────────────────────────────────── */

const MiniNodeCard = forwardRef<HTMLDivElement, MiniNodeCardProps>(
	({ node, collapsed }, ref) => {
		const { nodeType, nodeName, status, durationSeconds, forEachProgress, mcpProvider } = node;
		const isRunning = status === "running";

		const { Icon: BaseIcon, rgb: baseRgb } = getNodeTypeConfig(nodeType);

		// MCP provider icon override
		let colorRgb = baseRgb;
		let useProviderStyles = false;
		let ProviderIcon: React.ComponentType<{ className?: string; size?: number; style?: React.CSSProperties }> | null = null;

		if (nodeType === "MCP_SERVER") {
			const provider = mcpProvider || detectProviderFromNodeName(nodeName);
			if (provider) {
				const visuals = getProviderVisuals(provider);
				ProviderIcon = visuals.icon;
				colorRgb = visuals.colorRgb;
				useProviderStyles = true;
			}
		}

		// Live elapsed timer for running steps
		const elapsed = useElapsedTimer(isRunning);

		// Collapsed mode — icon only
		if (collapsed) {
			return (
				<div
					ref={ref}
					className="flex items-center justify-center"
				>
					<div
						className="flex h-6 w-6 items-center justify-center rounded-md"
						style={{
							backgroundColor: `rgba(${colorRgb}, 0.1)`,
						}}
					>
						{useProviderStyles && ProviderIcon ? (
							<ProviderIcon className="h-3 w-3" size={12} style={{ color: `rgb(${colorRgb})` }} />
						) : (
							<BaseIcon className="h-3 w-3" style={{ color: `rgba(${colorRgb}, 0.6)` }} />
						)}
					</div>
				</div>
			);
		}

		// Card background & border per state
		const cardStyle: React.CSSProperties = {};
		let stateClasses = "";

		switch (status) {
			case "running":
				cardStyle.backgroundColor = "var(--wp-card-running-bg)";
				cardStyle.borderColor = "var(--wp-card-running-border)";
				stateClasses = "animate-wpBreathe";
				break;
			case "completed":
				cardStyle.backgroundColor = "var(--wp-card-completed-bg)";
				cardStyle.borderColor = "var(--wp-card-completed-border)";
				break;
			case "failed":
				cardStyle.backgroundColor = "var(--wp-card-error-bg)";
				cardStyle.borderColor = "var(--wp-card-error-border)";
				break;
			case "pending":
				cardStyle.backgroundColor = "var(--wp-card-pending-bg)";
				cardStyle.borderColor = "var(--wp-card-pending-border)";
				break;
			default:
				cardStyle.backgroundColor = "var(--wp-card-pending-bg)";
				cardStyle.borderColor = "var(--wp-card-pending-border)";
				break;
		}

		// Duration / subtitle text
		let subtitle = "";
		let subtitleColor = "var(--color-text-disabled)";

		if (isRunning) {
			subtitle = `${elapsed.toFixed(1)}s · running`;
			subtitleColor = `rgba(${colorRgb}, 0.7)`;
		} else if (status === "completed" && durationSeconds != null) {
			subtitle = `${formatDuration(durationSeconds)} · completed`;
		} else if (status === "failed") {
			subtitle = "failed";
			subtitleColor = "rgba(239, 68, 68, 0.7)";
		} else if (status === "stopped") {
			subtitle = "stopped";
			subtitleColor = "rgba(251, 146, 60, 0.7)";
		} else if (status === "skipped") {
			subtitle = "skipped";
		} else if (status === "pending") {
			subtitle = "pending";
		}

		return (
			<div
				ref={ref}
				className={clsx(
					"flex items-center gap-3 rounded-xl border px-3.5 py-3 transition-all duration-300 cursor-pointer",
					"hover:brightness-110",
					stateClasses,
					status === "pending" && "opacity-[0.35]",
					status === "idle" && "opacity-50",
					status === "skipped" && "opacity-[0.35]",
				)}
				style={cardStyle}
			>
				{/* Icon square */}
				<div className="shrink-0">
					{useProviderStyles && ProviderIcon ? (
						<div
							className="flex h-9 w-9 items-center justify-center rounded-lg"
							style={{ backgroundColor: `rgba(${colorRgb}, 0.1)` }}
						>
							<ProviderIcon
								className="h-[18px] w-[18px]"
								size={18}
								style={{ color: `rgba(${colorRgb}, 0.6)` }}
							/>
						</div>
					) : (
						<div
							className="flex h-9 w-9 items-center justify-center rounded-lg"
							style={{ backgroundColor: `rgba(${colorRgb}, 0.1)` }}
						>
							<BaseIcon
								className="h-[18px] w-[18px]"
								style={{ color: `rgba(${colorRgb}, 0.6)` }}
							/>
						</div>
					)}
				</div>

				{/* Text area */}
				<div className="flex-1 min-w-0">
					<p className={clsx(
						"text-sm font-medium truncate",
						status === "idle" || status === "skipped" || status === "pending"
							? "text-[color:var(--color-text-disabled)]"
							: "text-[color:var(--color-text-primary)]",
					)}>
						{nodeName}
					</p>

					{subtitle && (
						<p className="text-xs mt-0.5 truncate" style={{ color: subtitleColor }}>
							{subtitle}
						</p>
					)}

					{isRunning && forEachProgress && (
						<p className="text-xs mt-0.5" style={{ color: `rgba(${colorRgb}, 0.8)` }}>
							{forEachProgress.completed}/{forEachProgress.total}
							{forEachProgress.failed > 0 && (
								<span className="text-red-400"> ({forEachProgress.failed} failed)</span>
							)}
						</p>
					)}
				</div>

				{/* Status dot */}
				<StatusDot status={status} />
			</div>
		);
	},
);

MiniNodeCard.displayName = "MiniNodeCard";

export default MiniNodeCard;
