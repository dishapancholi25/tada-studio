import { useCallback } from "react";
import type { Edge } from "reactflow";
import { useShallow } from "zustand/react/shallow";

import { useGraphStore } from "@/stores/graphStore";

/**
 * Subscribe to the set of edges that originate from a given node.
 * Returns a stable array (shallow-compared) so components only re-render
 * when one of the node's outgoing edges actually changes.
 */
export function useNodeOutgoingEdges(nodeId: string): Edge[] {
	const selectOutgoingEdges = useCallback(
		(state: ReturnType<typeof useGraphStore.getState>) =>
			state.edges.filter((edge) => edge.source === nodeId),
		[nodeId],
	);

	return useGraphStore(useShallow(selectOutgoingEdges));
}
