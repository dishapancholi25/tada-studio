"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { AIHealth } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useAIHealth(workflowId: string): AsyncState<AIHealth> {
	return useAsyncData(
		() => workflowMetricsService.getAIHealth(workflowId),
		[workflowId],
	);
}
