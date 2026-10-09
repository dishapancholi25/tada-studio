"use client";

import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { useWorkflowHeader } from "@/hooks/workflow-metrics/useWorkflowHeader";
import Card from "./shared/Card";
import { ErrorState, Skeleton } from "./shared/WidgetStates";

// Same lazy-loaded dialog the Dashboard uses for "Create New Workflow".
const GraphManagementDialog = lazy(() => import("@/components/core/GraphManagementDialog"));

export default function WorkflowHeader({ workflowId }: { workflowId: string }) {
	const { data, loading, error, refetch } = useWorkflowHeader(workflowId);
	const [showGraphDialog, setShowGraphDialog] = useState(false);

	if (loading) {
		return (
			<div className="space-y-3">
				<Skeleton className="h-7 w-72" />
				<Skeleton className="h-3 w-32" />
				<Skeleton className="mt-1 h-9 w-44 rounded" />
			</div>
		);
	}

	if (error || !data) {
		return (
			<Card>
				<ErrorState message={error ?? "Failed to load workflow"} onRetry={refetch} />
			</Card>
		);
	}

	return (
		<div>
			{/* Title */}
			<h1 className="text-[20px] font-semibold text-[#333333] sm:text-[22px]">
				{data.name}
				{data.category && <span className="text-[#8A8A8A]"> — {data.category}</span>}
			</h1>

			{/* Subtitle — description when available, matches "3 workflows" in reference */}
			{data.description && (
				<p className="mt-0.5 text-[13px] text-[#8A8A8A]">{data.description}</p>
			)}

			{/* Primary action below title block — identical to Dashboard "Create New Workflow" */}
			<div className="mt-3 flex items-center justify-start">
				<motion.button
					type="button"
					onClick={() => setShowGraphDialog(true)}
					whileHover={{ y: -2, scale: 1.02 }}
					whileTap={{ scale: 0.98 }}
					transition={{ type: "spring", stiffness: 300, damping: 20 }}
					className="flex items-center gap-2 rounded bg-[#FF5E00] px-4 py-2 text-[12px] font-semibold text-white transition-colors hover:bg-[#E05500]"
					style={{ boxShadow: "0px 16px 42px rgba(0,0,0,0.06)" }}
				>
					<Plus className="h-4 w-4" />
					Create New Workflow
				</motion.button>
			</div>

			<Suspense fallback={<div />}>
				<GraphManagementDialog
					isOpen={showGraphDialog}
					onClose={() => setShowGraphDialog(false)}
					initialTab="create"
				/>
			</Suspense>
		</div>
	);
}
