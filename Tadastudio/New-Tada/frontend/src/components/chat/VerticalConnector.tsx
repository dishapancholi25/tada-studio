import clsx from "clsx";
import type { CSSProperties } from "react";
import type { ProgressNodeStatus } from "./workflowProgressUtils";

interface VerticalConnectorProps {
	topStatus: ProgressNodeStatus;
	bottomStatus: ProgressNodeStatus;
	/** Optional branch label to display (for CONDITION nodes) */
	branchLabel?: string;
	/** Whether the entire workflow has completed (for sweep animation) */
	workflowComplete?: boolean;
	/** Index in the connector sequence (for staggered sweep delay) */
	connectorIndex?: number;
	/** Whether panel is in collapsed mode */
	collapsed?: boolean;
	/** Light chat panel: slate/orange connector lines instead of dark-theme stripes */
	tone?: "default" | "light";
}

export default function VerticalConnector({
	topStatus,
	bottomStatus,
	branchLabel,
	workflowComplete,
	connectorIndex = 0,
	collapsed,
	tone = "default",
}: VerticalConnectorProps) {
	const bothCompleted = topStatus === "completed" && bottomStatus === "completed";
	const topDone = topStatus === "completed" || topStatus === "failed" || topStatus === "stopped";
	const bottomRunning = bottomStatus === "running";
	const bothIdle = topStatus === "idle" && bottomStatus === "idle";

	// Determine connector visual state
	let connectorClass: string;
	let showPulseDot = false;

	if (workflowComplete || bothCompleted) {
		connectorClass = workflowComplete
			? "wp-connector-completed animate-wpCompletionSweep"
			: "wp-connector-completed";
	} else if (topDone && bottomRunning) {
		connectorClass = "wp-connector-active";
		showPulseDot = true;
	} else if (bothIdle || (!topDone && !bottomRunning)) {
		connectorClass = "wp-connector-pending";
	} else {
		// topDone but bottom is pending/idle
		connectorClass = "wp-connector-pending";
	}

	const lightConnectorClass =
		tone === "light"
			? workflowComplete || bothCompleted
				? workflowComplete
					? "bg-orange-400/70 shadow-[0_0_10px_rgba(249,115,22,0.24)]"
					: "bg-orange-400/70 shadow-[0_0_10px_rgba(249,115,22,0.24)]"
				: topDone && bottomRunning
					? "relative overflow-hidden bg-orange-300/90 shadow-[0_0_10px_rgba(249,115,22,0.2)]"
					: "bg-[repeating-linear-gradient(to_bottom,rgba(249,115,22,0.5)_0px,rgba(249,115,22,0.5)_4px,transparent_4px,transparent_8px)]"
			: null;

	const lineClass = lightConnectorClass ?? connectorClass;

	const connectorHeight = collapsed ? "h-2" : branchLabel ? "h-2" : "h-6";

	// Collapsed mode — thin simple connector
	const sweepStyle: CSSProperties | undefined = workflowComplete
		? ({ "--connector-index": connectorIndex } as CSSProperties)
		: undefined;

	if (collapsed) {
		return (
			<div className="flex justify-center py-0">
				<div className={clsx("h-2 w-px rounded-full", lineClass)} style={sweepStyle} />
			</div>
		);
	}

	return (
		<div
			className="flex flex-col items-center gap-0 py-0 ml-[17px]"
		>
			<div
				className={clsx(
					"w-[2px] rounded-full transition-all duration-500",
					connectorHeight,
					lineClass,
				)}
				style={sweepStyle}
			>
				{showPulseDot && tone === "light" && (
					<div className="absolute left-0 top-0 h-2 w-full animate-pulse rounded-sm bg-orange-500/70 shadow-[0_0_6px_rgba(249,115,22,0.45)]" />
				)}
				{showPulseDot && tone !== "light" && <div className="wp-pulse-dot" />}
			</div>

			{branchLabel && (
				<span
					className={clsx(
						"px-1.5 py-0.5 text-[10px] font-medium",
						tone === "light" ? "text-orange-700/80" : "text-[color:var(--color-text-disabled)]",
					)}
				>
					{branchLabel}
				</span>
			)}

			{branchLabel && (
				<div className={clsx("h-2 w-[2px] rounded-full transition-all duration-500", lineClass)} style={sweepStyle}>
					{showPulseDot && tone === "light" && (
						<div className="absolute left-0 top-0 h-2 w-full animate-pulse rounded-sm bg-orange-500/70 shadow-[0_0_6px_rgba(249,115,22,0.45)]" />
					)}
					{showPulseDot && tone !== "light" && <div className="wp-pulse-dot" />}
				</div>
			)}
		</div>
	);
}
