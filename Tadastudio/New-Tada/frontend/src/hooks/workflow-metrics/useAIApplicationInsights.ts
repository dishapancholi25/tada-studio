"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { AIApplicationInsights } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useAIApplicationInsights(workflowId: string): AsyncState<AIApplicationInsights> {
	return useAsyncData(
		() => workflowMetricsService.getAIApplicationInsights(workflowId),
		[workflowId],
	);
}
