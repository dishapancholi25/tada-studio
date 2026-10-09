"use client";

import type { CSSProperties, ReactNode, Ref } from "react";
import type {
	ConnectionLineComponent,
	DefaultEdgeOptions,
	Edge,
	Node,
	ReactFlowInstance,
	ReactFlowProps,
} from "reactflow";
import ReactFlow from "reactflow";

interface GraphCanvasProps
	extends Omit<
		ReactFlowProps,
		"nodes" | "edges" | "nodeTypes" | "edgeTypes" | "children"
	> {
	nodes: Node[];
	edges: Edge[];
	nodeTypes: ReactFlowProps["nodeTypes"];
	edgeTypes?: ReactFlowProps["edgeTypes"];
	defaultEdgeOptions?: DefaultEdgeOptions;
	connectionLineComponent?: ConnectionLineComponent;
	connectionLineStyle?: CSSProperties;
	wrapperClassName?: string;
	wrapperStyle?: CSSProperties;
	overlays?: ReactNode;
	flowExtras?: ReactNode;
	/**
	 * When true the canvas disables drag/connect interactions unless overridden via props.
	 */
	isReadOnly?: boolean;
	/**
	 * Optional ref to the wrapping div (used by AgentBuilder for drag helpers).
	 */
	wrapperRef?: Ref<HTMLDivElement>;
	/**
	 * Optional ref targeting the underlying ReactFlow DOM element.
	 */
	reactFlowRef?: Ref<HTMLDivElement>;
}
function GraphCanvas({
	nodes,
	edges,
	nodeTypes,
	edgeTypes,
	defaultEdgeOptions,
	connectionLineComponent,
	connectionLineStyle,
	className,
	overlays,
	flowExtras,
	isReadOnly = false,
	wrapperClassName,
	wrapperStyle,
	wrapperRef,
	reactFlowRef,
	proOptions,
	nodesDraggable,
	nodesConnectable,
	elementsSelectable,
	panOnScroll,
	zoomOnScroll,
	zoomOnDoubleClick,
	...flowProps
}: GraphCanvasProps) {
	const readOnlyProps = isReadOnly
		? {
				nodesDraggable: nodesDraggable ?? false,
				nodesConnectable: nodesConnectable ?? false,
				elementsSelectable: elementsSelectable ?? true,
				panOnScroll: panOnScroll ?? false,
				zoomOnScroll: zoomOnScroll ?? true,
				zoomOnDoubleClick: zoomOnDoubleClick ?? false,
			}
		: {
				nodesDraggable,
				nodesConnectable,
				elementsSelectable,
				panOnScroll,
				zoomOnScroll,
				zoomOnDoubleClick,
			};

	const mergedProOptions = proOptions ?? { hideAttribution: true };

	return (
		<div
			data-tutorial="canvas-area"
			className={wrapperClassName ?? "relative h-full w-full"}
			style={wrapperStyle}
			ref={wrapperRef}
		>
			<ReactFlow
				ref={reactFlowRef}
				nodes={nodes}
				edges={edges}
				nodeTypes={nodeTypes}
				edgeTypes={edgeTypes}
				defaultEdgeOptions={defaultEdgeOptions}
				connectionLineComponent={connectionLineComponent}
				connectionLineStyle={connectionLineStyle}
				className={className}
				proOptions={mergedProOptions}
				// Performance: Only render visible elements (virtualization)
				onlyRenderVisibleElements={true}
				minZoom={0.1}
				maxZoom={2}
				{...readOnlyProps}
				{...flowProps}
			>
				{flowExtras}
			</ReactFlow>
			{overlays}
		</div>
	);
}

export default GraphCanvas;
