"use client";

import { workflowMetricsService } from "@/lib/workflow-metrics/service";
import type { UserSatisfaction } from "@/types/workflow-metrics";
import { type AsyncState, useAsyncData } from "./useAsyncData";

export function useUserSatisfaction(workflowId: string): AsyncState<UserSatisfaction> {
	return useAsyncData(
		() => workflowMetricsService.getUserSatisfaction(workflowId),
		[workflowId],
	);
}
