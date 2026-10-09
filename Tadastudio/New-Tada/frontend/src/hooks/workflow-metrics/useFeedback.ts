"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { FeedbackList } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useFeedback(workflowId: string): AsyncState<FeedbackList> {
	return useAsyncData(
		() => workflowMetricsService.getFeedback(workflowId),
		[workflowId],
	);
}
