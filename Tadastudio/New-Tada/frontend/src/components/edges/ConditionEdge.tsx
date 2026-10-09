"use client";

import { type FC, memo, useMemo } from "react";
import {
	BaseEdge,
	EdgeLabelRenderer,
	type EdgeProps,
	getBezierPath,
	getSmoothStepPath,
} from "reactflow";

interface ConditionEdgeData {
	label?: string;
	branchColor?: string;
	branchIndex?: number;
	branchLabel?: string;
	isExecutionMode?: boolean;
}

const ConditionEdge: FC<EdgeProps<ConditionEdgeData>> = ({
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
	// Use smooth step path for cleaner routing
	const [edgePath, labelX, labelY] = getSmoothStepPath({
		sourceX,
		sourceY,
		sourcePosition,
		targetX,
		targetY,
		targetPosition,
		borderRadius: 20,
	});

	// Determine colors and styling based on mode (memoized for performance)
	const branchColor = useMemo(() => {
		// In execution mode, use execution-based styling from the style prop
		if (data?.isExecutionMode && style?.stroke) {
			return style.stroke;
		}

		// In builder mode, use custom branch colors or defaults
		if (data?.branchColor) return data.branchColor;

		// Default colors based on common branch labels
		const label = (data?.label || data?.branchLabel)?.toLowerCase() || "";
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
		if (label.includes("default") || label.includes("else")) {
			return "#6b7280"; // gray-500
		}
		return "#8b5cf6"; // purple-500 for unknown
	}, [data?.isExecutionMode, style?.stroke, data?.branchColor, data?.label, data?.branchLabel]);

	// Merge custom style with branch color (memoized for performance)
	const edgeStyle = useMemo(() => ({
		...style,
		stroke: branchColor,
		strokeWidth: data?.isExecutionMode ? style?.strokeWidth || 2 : 2,
		opacity: data?.isExecutionMode ? style?.opacity || 0.8 : 0.8,
	}), [style, branchColor, data?.isExecutionMode]);

	return (
		<>
			<BaseEdge
				id={id}
				path={edgePath}
				markerEnd={markerEnd}
				style={edgeStyle}
			/>

			{(data?.label || data?.branchLabel) && (
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
							className="px-3 py-1.5 rounded-lg text-xs font-medium text-white shadow-lg backdrop-blur-sm transition-all duration-200 hover:scale-105"
							style={{
								backgroundColor: branchColor,
								border: `1px solid ${branchColor}`,
								boxShadow: `0 4px 12px ${branchColor}33`,
								opacity: data?.isExecutionMode ? style?.opacity || 0.8 : 1,
							}}
						>
							{data?.label || data?.branchLabel}
						</div>
					</div>
				</EdgeLabelRenderer>
			)}
		</>
	);
};

export default memo(ConditionEdge);
