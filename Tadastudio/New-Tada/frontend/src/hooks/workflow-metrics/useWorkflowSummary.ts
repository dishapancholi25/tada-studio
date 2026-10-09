"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { WorkflowSummary } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useWorkflowSummary(workflowId: string): AsyncState<WorkflowSummary> {
	return useAsyncData(
		() => workflowMetricsService.getSummary(workflowId),
		[workflowId],
	);
}
