"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { RunSummary } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useRunSummary(workflowId: string): AsyncState<RunSummary> {
	return useAsyncData(
		() => workflowMetricsService.getRunSummary(workflowId),
		[workflowId],
	);
}
