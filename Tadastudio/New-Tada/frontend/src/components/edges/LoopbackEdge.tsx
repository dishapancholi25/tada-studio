"use client";

import { type FC, memo } from "react";
import {
	BaseEdge,
	EdgeLabelRenderer,
	type EdgeProps,
	getSmoothStepPath,
} from "reactflow";

interface LoopbackEdgeData {
	label?: string;
	branchColor?: string;
	branchIndex?: number;
}

const LoopbackEdge: FC<EdgeProps<LoopbackEdgeData>> = ({
	id,
	sourceX,
	sourceY,
	targetX,
	targetY,
	sourcePosition,
	targetPosition,
	data,
	markerEnd,
	style = {},
}) => {
	// Calculate if this is a backward connection (loopback)
	const isLoopback = sourceX > targetX;

	// Calculate the path for loopback connections
	let edgePath: string;
	let labelX: number;
	let labelY: number;
	const horizontalPadding = 30; // Padding from node edges (moved outside for reuse)

	if (isLoopback) {
		// Create a path that goes around the nodes
		// We'll route it below the nodes with adequate clearance
		const verticalOffset = 80; // Distance to go below/above nodes

		// Determine if we should go above or below based on Y positions
		const goBelow = sourceY <= targetY + 50; // If nodes are roughly aligned or source is higher, go below
		const yOffset = goBelow ? verticalOffset : -verticalOffset;

		// Create path segments
		const path = [];

		// Start from source
		path.push(`M ${sourceX},${sourceY}`);

		// Move right a bit from source
		path.push(`L ${sourceX + horizontalPadding},${sourceY}`);

		// Move vertically (down or up)
		const routingY = goBelow
			? Math.max(sourceY, targetY) + yOffset
			: Math.min(sourceY, targetY) + yOffset;
		path.push(`L ${sourceX + horizontalPadding},${routingY}`);

		// Move horizontally across to target X position
		path.push(`L ${targetX - horizontalPadding},${routingY}`);

		// Move vertically to target Y
		path.push(`L ${targetX - horizontalPadding},${targetY}`);

		// Connect to target
		path.push(`L ${targetX},${targetY}`);

		edgePath = path.join(" ");

		// Calculate label position (middle of the horizontal segment)
		labelX = (sourceX + targetX) / 2;
		labelY = routingY;
	} else {
		// For forward connections, use the standard smooth step path
		const [path, lx, ly] = getSmoothStepPath({
			sourceX,
			sourceY,
			sourcePosition,
			targetX,
			targetY,
			targetPosition,
			borderRadius: 20,
		});

		edgePath = path;
		labelX = lx;
		labelY = ly;
	}

	// Determine edge color
	const getEdgeColor = () => {
		if (data?.branchColor) return data.branchColor;

		// Special color for loopback edges
		if (isLoopback) {
			return "#932A8F"; // Plum accent for loopback edges
		}

		// Default colors based on branch labels (for condition nodes)
		const label = data?.label?.toLowerCase() || "";
		if (
			label.includes("approve") ||
			label.includes("success") ||
			label.includes("true")
		) {
			return "#0DA931"; // green-500
		}
		if (
			label.includes("review") ||
			label.includes("pending") ||
			label.includes("wait")
		) {
			return "#695DA8"; // indigo accent
		}
		if (
			label.includes("reject") ||
			label.includes("fail") ||
			label.includes("false")
		) {
			return "#ef4444"; // red-500
		}

		return "#4a4a4a"; // Default gray
	};

	const edgeColor = getEdgeColor();

	// Style the edge
	const edgeStyle = {
		...style,
		stroke: edgeColor,
		strokeWidth: isLoopback ? 2.5 : 2,
		opacity: isLoopback ? 0.7 : 0.8,
		strokeDasharray: isLoopback ? "8,4" : undefined, // Dashed line for loopback
	};

	return (
		<>
			<BaseEdge
				id={id}
				path={edgePath}
				markerEnd={markerEnd}
				style={edgeStyle}
			/>

			{/* Label */}
			{(data?.label || isLoopback) && (
				<EdgeLabelRenderer>
					<div
						style={{
							position: "absolute",
							transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
							pointerEvents: "all",
							zIndex: 10,
						}}
						className="nodrag nopan"
					>
						<div
							className={`px-2 py-1 rounded-lg text-xs font-medium text-white shadow-lg backdrop-blur-sm transition-all duration-200 hover:scale-105 ${
								isLoopback ? "bg-[color:var(--color-accent)]/90" : ""
							}`}
							style={{
								backgroundColor: isLoopback ? undefined : edgeColor,
								border: `1px solid ${edgeColor}`,
								boxShadow: `0 4px 12px ${edgeColor}33`,
							}}
						>
							{isLoopback && !data?.label && (
								<div className="flex items-center gap-1">
									<svg
										className="w-3 h-3"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
									>
										<path
											strokeLinecap="round"
											strokeLinejoin="round"
											strokeWidth={2}
											d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
										/>
									</svg>
									<span className="text-black">Loop</span>
								</div>
							)}
							{data?.label && (
								<span className={isLoopback ? "text-black" : ""}>
									{data.label}
								</span>
							)}
						</div>
					</div>
				</EdgeLabelRenderer>
			)}

			{/* Optional: Add an arrow indicator at the midpoint for loopback edges */}
			{isLoopback && (
				<EdgeLabelRenderer>
					<div
						style={{
							position: "absolute",
							transform: `translate(-50%, -50%) translate(${sourceX + horizontalPadding}px, ${(sourceY + labelY) / 2}px) rotate(90deg)`,
							pointerEvents: "none",
							zIndex: 9,
						}}
					>
						<svg
							width="12"
							height="12"
							viewBox="0 0 24 24"
							fill="none"
							stroke={edgeColor}
							strokeWidth="2"
						>
							<path d="M12 19l7-7-7-7" />
						</svg>
					</div>
				</EdgeLabelRenderer>
			)}
		</>
	);
};

export default memo(LoopbackEdge);
