"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { WorkflowHeaderInfo } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useWorkflowHeader(workflowId: string): AsyncState<WorkflowHeaderInfo> {
	return useAsyncData(
		() => workflowMetricsService.getWorkflowHeader(workflowId),
		[workflowId],
	);
}
