"use client";

import { ArrowLeft } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import EnhancedExecutionViewerModal from "@/components/execution/EnhancedExecutionViewerModal";

export default function ExecutionViewerPage() {
	const params = useParams();
	const router = useRouter();
	const searchParams = useSearchParams();
	const workflowId = decodeURIComponent(params.workflowId as string);
	const executionId = params.executionId as string;
	const returnTo = searchParams.get("return");

	console.log("[ExecutionViewerPage] Render:", {
		workflowId,
		executionId,
		returnTo,
	});

	const handleClose = () => {
		// If return=executions, go back to executions page
		// Otherwise, go back to the workflow
		if (returnTo === "executions") {
			router.push("/executions");
		} else {
			router.push(`/workflow/${encodeURIComponent(workflowId)}`);
		}
	};

	return (
		<div className="h-screen bg-white">
			<div className="p-4">
				<button
					onClick={handleClose}
					className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-slate-600 transition-colors hover:border-orange-400 hover:bg-white hover:text-slate-900"
				>
					<ArrowLeft className="w-4 h-4" />
					<span>
						{returnTo === "executions"
							? "Back to Executions"
							: "Back to Workflow"}
					</span>
				</button>
			</div>

			<EnhancedExecutionViewerModal
				isOpen={true}
				onClose={handleClose}
				executionId={executionId}
				workflowId={workflowId}
				returnParam={returnTo}
			/>
		</div>
	);
}
