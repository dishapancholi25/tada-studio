"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { QualityMetrics } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useQualityMetrics(workflowId: string): AsyncState<QualityMetrics> {
	return useAsyncData(
		() => workflowMetricsService.getQualityMetrics(workflowId),
		[workflowId],
	);
}
