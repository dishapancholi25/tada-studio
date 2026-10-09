"use client";

import React from "react";
import type { Edge, Node } from "reactflow";
import InputSourceSelector from "../InputSourceSelector";

interface InputSourceSectionProps {
	node: Node;
	availableNodes: Node[];
	onUpdate: (config: any) => void;
	hasCustomConfig: boolean;
	currentConfig?: any;
	edges?: Edge[];
}

export default function InputSourceSection({
	node,
	availableNodes,
	onUpdate,
	currentConfig,
	edges,
}: InputSourceSectionProps) {
	return (
		<InputSourceSelector
			node={node}
			availableNodes={availableNodes}
			onUpdate={onUpdate}
			initialConfig={currentConfig}
			edges={edges}
		/>
	);
}
