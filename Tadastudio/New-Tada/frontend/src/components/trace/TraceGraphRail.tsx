import React, { memo } from "react";

const RAIL_SPACING = 20;
const LINE_WIDTH = 1.5;
const VB_H = 100;
const VB_MID = 50;

// Container size for node indicators on the rail
const CTR_SIZE = 20;
export const CTR_HALF = CTR_SIZE / 2;

export const RAIL_COLORS = [
	"#0085d9",
	"#d9008f",
	"#00d90a",
	"#d98500",
	"#a300d9",
	"#ff0000",
	"#00d9cc",
	"#e138e8",
	"#85d900",
	"#dc5b23",
	"#6f24d6",
	"#ffcc00",
];

const NS = "non-scaling-stroke" as const;

interface TraceGraphRailProps {
	depth: number;
	isFirstSibling: boolean;
	isLastSibling: boolean;
	hasChildren: boolean;
	isExpanded: boolean;
	hasExpandedChildren: boolean;
	continuingRails: Set<number>;
	nodeStatus: string;
	icon?: React.ReactNode;
	onToggle?: (e: React.MouseEvent) => void;
	mergeFromDepth?: number;
}

export function getRailColor(railIndex: number): string {
	return RAIL_COLORS[railIndex % RAIL_COLORS.length];
}

export function getRailX(railIndex: number): number {
	return railIndex * RAIL_SPACING + RAIL_SPACING / 2;
}

export function getSvgWidth(depth: number): number {
	return (depth + 1) * RAIL_SPACING + 14;
}

const TraceGraphRail = memo(
	({
		depth,
		isFirstSibling,
		hasChildren,
		isExpanded,
		hasExpandedChildren,
		continuingRails,
		nodeStatus,
		icon,
		onToggle,
		mergeFromDepth,
	}: TraceGraphRailProps) => {
		const drawDepth =
			mergeFromDepth !== undefined
				? Math.max(depth, mergeFromDepth)
				: depth;
		const svgDrawWidth = getSvgWidth(drawDepth);
		// Layout width: use own depth, but push out past closing rails to avoid overlap
		const layoutDepth =
			mergeFromDepth !== undefined && mergeFromDepth > depth + 1
				? mergeFromDepth - 1
				: depth;
		const layoutWidth = getSvgWidth(layoutDepth);
		const nodeX = getRailX(depth);

		const elements: React.ReactElement[] = [];
		let key = 0;

		// 1. Continuing ancestor rails
		continuingRails.forEach((rail) => {
			const x = getRailX(rail);
			const color = getRailColor(rail);

			if (rail === depth && isFirstSibling) {
				elements.push(
					<line
						key={key++}
						x1={x}
						y1={VB_MID}
						x2={x}
						y2={VB_H}
						stroke={color}
						strokeWidth={LINE_WIDTH}
						vectorEffect={NS}
					/>,
				);
			} else {
				elements.push(
					<line
						key={key++}
						x1={x}
						y1={0}
						x2={x}
						y2={VB_H}
						stroke={color}
						strokeWidth={LINE_WIDTH}
						vectorEffect={NS}
					/>,
				);
			}
		});

		// 2. Branch connector for child nodes (vertical on own rail)
		if (depth > 0) {
			const branchColor = getRailColor(depth);

			elements.push(
				<line
					key={key++}
					x1={nodeX}
					y1={0}
					x2={nodeX}
					y2={VB_MID}
					stroke={branchColor}
					strokeWidth={LINE_WIDTH}
					vectorEffect={NS}
				/>,
			);

			elements.push(
				<line
					key={key++}
					x1={nodeX}
					y1={VB_MID}
					x2={nodeX}
					y2={VB_H}
					stroke={branchColor}
					strokeWidth={LINE_WIDTH}
					vectorEffect={NS}
				/>,
			);
		} else {
			if (!continuingRails.has(0) && !isFirstSibling) {
				elements.push(
					<line
						key={key++}
						x1={nodeX}
						y1={0}
						x2={nodeX}
						y2={VB_MID}
						stroke={getRailColor(0)}
						strokeWidth={LINE_WIDTH}
						vectorEffect={NS}
					/>,
				);
			}

			if (hasExpandedChildren && !continuingRails.has(0)) {
				elements.push(
					<line
						key={key++}
						x1={nodeX}
						y1={VB_MID}
						x2={nodeX}
						y2={VB_H}
						stroke={getRailColor(0)}
						strokeWidth={LINE_WIDTH}
						vectorEffect={NS}
					/>,
				);
			}
		}

		// 3. Branch-out arc from icon right edge to child rail (drawn in parent row)
		if (hasExpandedChildren) {
			const childRailX = getRailX(depth + 1);
			const childColor = getRailColor(depth + 1);
			elements.push(
				<path
					key={key++}
					d={`M ${nodeX + CTR_HALF} ${VB_MID} Q ${childRailX} ${VB_MID} ${childRailX} ${VB_H}`}
					fill="none"
					stroke={childColor}
					strokeWidth={LINE_WIDTH}
					vectorEffect={NS}
				/>,
			);
		}

		// 4. Merge-back arcs from all closing branch rails into this node's icon
		if (mergeFromDepth !== undefined) {
			for (let d = depth + 1; d <= mergeFromDepth; d++) {
				const mergeRailX = getRailX(d);
				const mergeColor = getRailColor(d);
				elements.push(
					<path
						key={key++}
						d={`M ${mergeRailX} 0 Q ${mergeRailX} ${VB_MID} ${nodeX + CTR_HALF} ${VB_MID}`}
						fill="none"
						stroke={mergeColor}
						strokeWidth={LINE_WIDTH}
						vectorEffect={NS}
					/>,
				);
			}
		}

		// Node indicator — solid background circle with icon, masks rail lines
		// Expandable nodes are clickable; collapsed shows a chevron badge to the right
		const showChevron = hasChildren && !isExpanded;
		const nodeIndicator = hasChildren ? (
			<>
				<button
					type="button"
					onClick={onToggle}
					className="absolute flex items-center justify-center rounded-full hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300"
					style={{
						width: CTR_SIZE,
						height: CTR_SIZE,
						left: nodeX - CTR_HALF,
						top: -CTR_HALF,
						backgroundColor: "#f8fafc",
						opacity: nodeStatus === "pending" ? 0.5 : 1,
						pointerEvents: "auto",
						cursor: "pointer",
						padding: 0,
						border: "1px solid #e2e8f0",
						boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
					}}
				>
					{icon}
				</button>
				{showChevron && (
					<button
						type="button"
						onClick={onToggle}
						className="absolute flex items-center justify-center rounded-sm hover:bg-slate-100 focus-visible:outline-none"
						style={{
							width: 10,
							height: 12,
							left: nodeX + CTR_HALF + 1,
							top: -6,
							backgroundColor: "#f8fafc",
							pointerEvents: "auto",
							cursor: "pointer",
							padding: 0,
							border: "1px solid #e2e8f0",
						}}
					>
						<svg viewBox="0 0 6 9" width="6" height="9" fill="none">
							<path
								d="M1.5 1L5 4.5L1.5 8"
								stroke="#64748b"
								strokeWidth="1.5"
								strokeLinecap="round"
								strokeLinejoin="round"
							/>
						</svg>
					</button>
				)}
			</>
		) : (
			<div
				className="absolute flex items-center justify-center rounded-full"
				style={{
					width: CTR_SIZE,
					height: CTR_SIZE,
					left: nodeX - CTR_HALF,
					top: -CTR_HALF,
					backgroundColor: "#f8fafc",
					border: "1px solid #e2e8f0",
					boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
					opacity: nodeStatus === "pending" ? 0.5 : 1,
				}}
			>
				{icon}
			</div>
		);

		return (
			<div
				className="shrink-0 self-stretch relative overflow-visible"
				style={{ width: layoutWidth, minWidth: layoutWidth }}
			>
				{/* SVG layer — lines and curves (may overflow for merge arcs) */}
				<svg
					width={svgDrawWidth}
					viewBox={`0 0 ${svgDrawWidth} ${VB_H}`}
					preserveAspectRatio="none"
					style={{
						height: "100%",
						width: svgDrawWidth,
						display: "block",
						position: "absolute",
						top: 0,
						left: 0,
						overflow: "visible",
					}}
					xmlns="http://www.w3.org/2000/svg"
				>
					{elements}
				</svg>

				{/* Node indicator overlay */}
				<div
					className="absolute left-0 top-1/2 -translate-y-1/2"
					style={{ width: layoutWidth, pointerEvents: "none" }}
				>
					{nodeIndicator}
				</div>
			</div>
		);
	},
);

TraceGraphRail.displayName = "TraceGraphRail";

export default TraceGraphRail;
