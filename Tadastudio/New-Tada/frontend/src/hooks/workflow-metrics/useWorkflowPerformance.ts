"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { WorkflowPerformance } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useWorkflowPerformance(workflowId: string): AsyncState<WorkflowPerformance> {
	return useAsyncData(
		() => workflowMetricsService.getWorkflowPerformance(workflowId),
		[workflowId],
	);
}
