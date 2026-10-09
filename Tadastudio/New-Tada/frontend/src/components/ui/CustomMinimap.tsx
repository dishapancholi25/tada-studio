"use client";

import clsx from "clsx";
import {
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
	type MouseEvent,
} from "react";
import {
	useEdges,
	useNodes,
	useReactFlow,
	useStore,
	useViewport,
	type Edge,
	type Node,
} from "reactflow";
import {
	calculateNodesBoundingBox,
	getMinimapEdgeColor,
	getMinimapNodeColor,
} from "@/components/core/shared/minimapUtils";

interface CustomMinimapProps {
	className?: string;
	style?: React.CSSProperties;
	maskColor?: string;
	maskStrokeColor?: string;
	maskStrokeWidth?: number;
	nodeStrokeWidth?: number;
	nodeBorderRadius?: number;
	width?: number;
	height?: number;
	/** Optional callback to override node colors (e.g., for execution status) */
	nodeColor?: (node: Node) => string;
}

/**
 * Custom minimap component that renders both nodes and edges.
 * Provides click-to-pan and drag-to-navigate functionality.
 */
export default function CustomMinimap({
	className = "",
	style,
	maskColor = "rgba(30, 30, 30, 0.4)",
	maskStrokeColor = "rgba(var(--color-primary-rgb), 0.5)",
	maskStrokeWidth = 2,
	nodeStrokeWidth = 1,
	nodeBorderRadius = 4,
	width = 200,
	height = 150,
	nodeColor,
}: CustomMinimapProps) {
	const nodes = useNodes();
	const edges = useEdges();
	const viewport = useViewport();
	const { setViewport } = useReactFlow();
	const svgRef = useRef<SVGSVGElement>(null);
	const [isDragging, setIsDragging] = useState(false);

	// Get React Flow canvas dimensions from internal store
	const canvasWidth = useStore((state) => state.width) || 800;
	const canvasHeight = useStore((state) => state.height) || 600;

	// Calculate the bounding box of all nodes
	const boundingBox = useMemo(
		() => calculateNodesBoundingBox(nodes),
		[nodes],
	);

	// Calculate scale to fit the graph in the minimap
	const scale = useMemo(() => {
		const scaleX = width / boundingBox.width;
		const scaleY = height / boundingBox.height;
		return Math.min(scaleX, scaleY, 1); // Don't scale up, only down
	}, [width, height, boundingBox]);

	// Calculate offset to center the graph in the minimap
	const offset = useMemo(() => {
		const scaledWidth = boundingBox.width * scale;
		const scaledHeight = boundingBox.height * scale;
		return {
			x: (width - scaledWidth) / 2 - boundingBox.minX * scale,
			y: (height - scaledHeight) / 2 - boundingBox.minY * scale,
		};
	}, [width, height, boundingBox, scale]);

	// Transform a point from graph coordinates to minimap coordinates
	const graphToMinimap = useCallback(
		(x: number, y: number) => ({
			x: x * scale + offset.x,
			y: y * scale + offset.y,
		}),
		[scale, offset],
	);

	// Transform a point from minimap coordinates to graph coordinates
	const minimapToGraph = useCallback(
		(x: number, y: number) => ({
			x: (x - offset.x) / scale,
			y: (y - offset.y) / scale,
		}),
		[scale, offset],
	);

	// Calculate the viewport rectangle in minimap coordinates
	const viewportRect = useMemo(() => {
		// The viewport shows what's visible on screen
		// viewport.x and viewport.y are the position of the viewport (negative values mean we've panned right/down)
		// We need to convert the visible area bounds to minimap coordinates

		// Visible area in graph coordinates (using React Flow canvas dimensions)
		const visibleX = -viewport.x / viewport.zoom;
		const visibleY = -viewport.y / viewport.zoom;
		const visibleWidth = canvasWidth / viewport.zoom;
		const visibleHeight = canvasHeight / viewport.zoom;

		// Convert to minimap coordinates
		const topLeft = graphToMinimap(visibleX, visibleY);
		return {
			x: topLeft.x,
			y: topLeft.y,
			width: visibleWidth * scale,
			height: visibleHeight * scale,
		};
	}, [viewport, canvasWidth, canvasHeight, graphToMinimap, scale]);

	// Handle click on minimap to pan to that location
	const handleClick = useCallback(
		(e: MouseEvent<SVGSVGElement>) => {
			if (isDragging) return;

			const svg = svgRef.current;
			if (!svg) return;

			const rect = svg.getBoundingClientRect();
			const clickX = e.clientX - rect.left;
			const clickY = e.clientY - rect.top;

			// Convert click position to graph coordinates
			const graphPos = minimapToGraph(clickX, clickY);

			// Calculate the center of the current viewport in graph coords
			const visibleWidth = canvasWidth / viewport.zoom;
			const visibleHeight = canvasHeight / viewport.zoom;

			// Set viewport to center on the clicked position
			setViewport({
				x: -(graphPos.x - visibleWidth / 2) * viewport.zoom,
				y: -(graphPos.y - visibleHeight / 2) * viewport.zoom,
				zoom: viewport.zoom,
			});
		},
		[isDragging, minimapToGraph, canvasWidth, canvasHeight, viewport.zoom, setViewport],
	);

	// Handle drag on viewport rectangle
	const handleMouseDown = useCallback(
		(e: MouseEvent) => {
			e.stopPropagation();
			setIsDragging(true);
		},
		[],
	);

	// Handle drag movement
	useEffect(() => {
		if (!isDragging) return;

		const handleMouseMove = (e: globalThis.MouseEvent) => {
			const svg = svgRef.current;
			if (!svg) return;

			const rect = svg.getBoundingClientRect();
			const mouseX = e.clientX - rect.left;
			const mouseY = e.clientY - rect.top;

			// Convert mouse position to graph coordinates
			const graphPos = minimapToGraph(mouseX, mouseY);

			// Calculate the visible area dimensions
			const visibleWidth = canvasWidth / viewport.zoom;
			const visibleHeight = canvasHeight / viewport.zoom;

			// Set viewport to center on the mouse position
			setViewport({
				x: -(graphPos.x - visibleWidth / 2) * viewport.zoom,
				y: -(graphPos.y - visibleHeight / 2) * viewport.zoom,
				zoom: viewport.zoom,
			});
		};

		const handleMouseUp = () => {
			setIsDragging(false);
		};

		window.addEventListener("mousemove", handleMouseMove);
		window.addEventListener("mouseup", handleMouseUp);

		return () => {
			window.removeEventListener("mousemove", handleMouseMove);
			window.removeEventListener("mouseup", handleMouseUp);
		};
	}, [isDragging, minimapToGraph, canvasWidth, canvasHeight, viewport.zoom, setViewport]);

	// Render an edge as a simple line
	const renderEdge = useCallback(
		(edge: Edge) => {
			const sourceNode = nodes.find((n) => n.id === edge.source);
			const targetNode = nodes.find((n) => n.id === edge.target);

			if (!sourceNode || !targetNode) return null;

			// Get node dimensions (cast data to Record for flexible property access)
			const sourceData = sourceNode.data as Record<string, unknown> | undefined;
			const targetData = targetNode.data as Record<string, unknown> | undefined;
			const sourceWidth = sourceNode.width || (sourceData?.width as number) || 200;
			const sourceHeight = sourceNode.height || (sourceData?.height as number) || 100;
			const targetWidth = targetNode.width || (targetData?.width as number) || 200;
			const targetHeight = targetNode.height || (targetData?.height as number) || 100;

			// Calculate center points (or handle positions)
			const sourceCenter = {
				x: sourceNode.position.x + sourceWidth / 2,
				y: sourceNode.position.y + sourceHeight / 2,
			};
			const targetCenter = {
				x: targetNode.position.x + targetWidth / 2,
				y: targetNode.position.y + targetHeight / 2,
			};

			// Determine edge points based on relative positions
			const sourcePoint = { ...sourceCenter };
			const targetPoint = { ...targetCenter };

			// Adjust to connect from edge of source to edge of target
			const dx = targetCenter.x - sourceCenter.x;
			const dy = targetCenter.y - sourceCenter.y;

			if (Math.abs(dx) > Math.abs(dy)) {
				// Horizontal connection
				if (dx > 0) {
					sourcePoint.x = sourceNode.position.x + sourceWidth;
					targetPoint.x = targetNode.position.x;
				} else {
					sourcePoint.x = sourceNode.position.x;
					targetPoint.x = targetNode.position.x + targetWidth;
				}
			} else {
				// Vertical connection
				if (dy > 0) {
					sourcePoint.y = sourceNode.position.y + sourceHeight;
					targetPoint.y = targetNode.position.y;
				} else {
					sourcePoint.y = sourceNode.position.y;
					targetPoint.y = targetNode.position.y + targetHeight;
				}
			}

			// Transform to minimap coordinates
			const start = graphToMinimap(sourcePoint.x, sourcePoint.y);
			const end = graphToMinimap(targetPoint.x, targetPoint.y);

			const edgeColor = getMinimapEdgeColor(edge);

			return (
				<line
					key={edge.id}
					x1={start.x}
					y1={start.y}
					x2={end.x}
					y2={end.y}
					stroke={edgeColor}
					strokeWidth={1.5}
					strokeOpacity={0.7}
					strokeLinecap="round"
				/>
			);
		},
		[nodes, graphToMinimap],
	);

	// Render a node as a rectangle
	const renderNode = useCallback(
		(node: Node) => {
			const nodeData = node.data as Record<string, unknown> | undefined;
			const nodeWidth = node.width || (nodeData?.width as number) || 200;
			const nodeHeight = node.height || (nodeData?.height as number) || 100;

			const pos = graphToMinimap(node.position.x, node.position.y);
			const scaledWidth = nodeWidth * scale;
			const scaledHeight = nodeHeight * scale;

			// Use custom nodeColor callback if provided, otherwise use default
			const fillColor = nodeColor ? nodeColor(node) : getMinimapNodeColor(node);

			return (
				<rect
					key={node.id}
					x={pos.x}
					y={pos.y}
					width={scaledWidth}
					height={scaledHeight}
					rx={nodeBorderRadius}
					ry={nodeBorderRadius}
					fill={fillColor}
					stroke={fillColor}
					strokeWidth={nodeStrokeWidth}
					strokeOpacity={0.5}
				/>
			);
		},
		[graphToMinimap, scale, nodeBorderRadius, nodeStrokeWidth, nodeColor],
	);

	return (
		<div
			className={clsx(
				"absolute bottom-6 right-6 z-20 overflow-hidden",
				className,
			)}
			style={style}
		>
			<svg
				ref={svgRef}
				width={width}
				height={height}
				className="cursor-pointer"
				onClick={handleClick}
			>
				{/* Background */}
				<rect
					x={0}
					y={0}
					width={width}
					height={height}
					fill="transparent"
				/>

				{/* Edges (rendered behind nodes) */}
				<g className="minimap-edges">
					{edges.map(renderEdge)}
				</g>

				{/* Nodes */}
				<g className="minimap-nodes">
					{nodes.map(renderNode)}
				</g>

				{/* Viewport mask (darkens area outside viewport) */}
				<defs>
					<mask id="viewport-mask">
						<rect x={0} y={0} width={width} height={height} fill="white" />
						<rect
							x={viewportRect.x}
							y={viewportRect.y}
							width={viewportRect.width}
							height={viewportRect.height}
							fill="black"
						/>
					</mask>
				</defs>

				{/* Dark overlay outside viewport */}
				<rect
					x={0}
					y={0}
					width={width}
					height={height}
					fill={maskColor}
					mask="url(#viewport-mask)"
					pointerEvents="none"
				/>

				{/* Viewport rectangle */}
				<rect
					x={viewportRect.x}
					y={viewportRect.y}
					width={viewportRect.width}
					height={viewportRect.height}
					fill="transparent"
					stroke={maskStrokeColor}
					strokeWidth={maskStrokeWidth}
					className="cursor-move"
					onMouseDown={handleMouseDown}
					style={{ cursor: isDragging ? "grabbing" : "grab" }}
				/>
			</svg>
		</div>
	);
}
