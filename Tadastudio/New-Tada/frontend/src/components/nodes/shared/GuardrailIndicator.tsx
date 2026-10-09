"use client";

import { Shield } from "lucide-react";
import { useGraph } from "@/contexts/GraphContext";
import { useNodeGuardrailStatus } from "@/hooks/useNodeGuardrailStatus";

/**
 * Compact guardrail shield indicator for non-agent nodes.
 *
 * Renders a small yellow shield icon when the node has guardrail policies
 * assigned (either directly or via workflow-level policies).
 * Returns null when no guardrails are active.
 *
 * @param nodeId - The ReactFlow node ID
 */
export default function GuardrailIndicator({
	nodeId,
}: { nodeId: string }) {
	const { currentGraph } = useGraph();
	const { hasGuardrails } = useNodeGuardrailStatus(
		currentGraph?.workflow_id,
		nodeId,
	);

	if (!hasGuardrails) return null;

	return (
		<div
			className="flex h-5 w-5 items-center justify-center rounded-full border border-white/30"
			style={{
				backgroundColor: "rgba(255, 255, 255, 0.2)",
			}}
			title="Guardrails active"
		>
			<Shield className="h-3 w-3 text-white" />
		</div>
	);
}
