"use client";

import type React from "react";
import {
	type ConnectionLineComponentProps,
	getSmoothStepPath,
	Position,
} from "reactflow";

const CustomConnectionLine: React.FC<ConnectionLineComponentProps> = ({
	fromX,
	fromY,
	toX,
	toY,
	fromPosition,
	toPosition,
}) => {
	// Use smooth step path for consistent look with edges
	const [path] = getSmoothStepPath({
		sourceX: fromX,
		sourceY: fromY,
		sourcePosition: fromPosition,
		targetX: toX,
		targetY: toY,
		targetPosition: toPosition || Position.Left,
		borderRadius: 20,
	});

	return (
		<g>
			{/* Connection line path */}
			<path
				d={path}
				fill="none"
				stroke="#4a4a4a"
				strokeWidth={3}
				strokeDasharray="5,5"
				className="animated-dash"
			/>

			{/* Optional: Add a small circle at the cursor position */}
			<circle
				cx={toX}
				cy={toY}
				r={4}
				fill="#4a4a4a"
				stroke="#1f1f1f"
				strokeWidth={3}
			/>

			{/* Add CSS animation for the dashed line */}
			<style jsx>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -10;
          }
        }
        
        .animated-dash {
          animation: dash 0.5s linear infinite;
        }
      `}</style>
		</g>
	);
};

export default CustomConnectionLine;
