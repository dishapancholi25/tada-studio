import type { CSSProperties } from "react";
import {
	CONDITION_SKIPPED_STYLE,
	CONDITION_TAKEN_STYLE,
} from "@/components/core/shared/defaultEdgeOptions";
import type { NodeExecution } from "@/types/api";

interface ConditionNodeDefinition {
	type?: string;
	condition_config?: {
		branch_mode?: "binary" | "multi" | string;
	} | null;
}

interface ConditionPathStyleParams {
	conditionNode?: ConditionNodeDefinition | null;
	sourceHandle?: string | null;
	execution?: NodeExecution;
}

/**
 * Normalize handle names to the branch-N format used by edges.
 * Binary conditions use "true"/"false" in execution data but edges use "branch-0"/"branch-1".
 */
function normalizeHandle(handle: string): string {
	if (handle === "true") return "branch-0";
	if (handle === "false") return "branch-1";
	return handle;
}

function resolveTakenHandle({
	execution,
	conditionNode,
}: {
	execution: NodeExecution;
	conditionNode?: ConditionNodeDefinition | null;
}) {
	const conditionOutput = execution.output_data;
	if (!conditionOutput) {
		return undefined;
	}

	if (conditionOutput.source_handle) {
		// Normalize handle to match edge format (branch-N)
		return normalizeHandle(conditionOutput.source_handle as string);
	}

	if (conditionOutput.branch_taken === undefined) {
		return undefined;
	}

	const branchMode = conditionNode?.condition_config?.branch_mode;

	if (branchMode === "multi") {
		return `branch-${conditionOutput.branch_taken}`;
	}

	return conditionOutput.branch_taken === 0 ? "true" : "false";
}

export function getConditionPathEdgeStyle({
	conditionNode,
	execution,
	sourceHandle,
}: ConditionPathStyleParams): CSSProperties | undefined {
	if (
		!conditionNode ||
		conditionNode.type !== "CONDITION" ||
		!execution ||
		!sourceHandle
	) {
		return undefined;
	}

	const takenHandle = resolveTakenHandle({ execution, conditionNode });

	if (!takenHandle) {
		return undefined;
	}

	if (sourceHandle === takenHandle) {
		return CONDITION_TAKEN_STYLE;
	}

	if (
		sourceHandle.startsWith("branch-") ||
		sourceHandle === "true" ||
		sourceHandle === "false"
	) {
		return CONDITION_SKIPPED_STYLE;
	}

	return undefined;
}
