"use client";

import { ArrowLeft } from "lucide-react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import ExecutionGraphViewer from "@/components/utils/ExecutionGraphViewer";
import { PageLoading } from "@/components/utils/LazyLoad";
import { api } from "@/lib/api";
import type { GraphExecution } from "@/types/api";

export default function ExecutionGraphPage() {
	const params = useParams();
	const router = useRouter();
	const searchParams = useSearchParams();
	const workflowId = decodeURIComponent(params.workflowId as string);
	const executionId = params.executionId as string;
	const returnTo = searchParams.get("return");
	const [execution, setExecution] = useState<GraphExecution | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const fetchExecution = async () => {
			try {
				setLoading(true);
				const response = await api.getExecutionHistory(executionId);
				setExecution(response);
			} catch (err) {
				console.error("Failed to fetch execution:", err);
				setError("Failed to load execution details");
			} finally {
				setLoading(false);
			}
		};

		void fetchExecution();
	}, [executionId]);

	const handleClose = () => {
		// If return=executions, go back to executions page
		// Otherwise, go back to the workflow
		if (returnTo === "executions") {
			router.push("/executions");
		} else {
			router.push(`/workflow/${encodeURIComponent(workflowId)}`);
		}
	};

	if (loading) {
		return <PageLoading message="Loading Execution Graph..." />;
	}

	if (error || !execution) {
		return (
			<div className="h-screen flex items-center justify-center bg-[color:var(--color-bg-secondary)]">
				<div className="text-center">
					<h1 className="text-2xl font-bold text-red-400 mb-4">
						Error Loading Execution
					</h1>
					<p className="text-[color:var(--color-text-secondary)] mb-6">
						{error || "Execution not found"}
					</p>
					<button
						onClick={handleClose}
						className="px-4 py-2 bg-[color:var(--color-primary)] text-[color:var(--button-primary-text)] rounded-lg hover:bg-[color:var(--color-primary-light)] transition-colors"
					>
						{returnTo === "executions"
							? "Back to Executions"
							: "Back to Workflow"}
					</button>
				</div>
			</div>
		);
	}

	return (
		<div className="h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-white flex flex-col">
			<div className="p-4 border-b border-[color:var(--color-border)]/20">
				<button
					onClick={handleClose}
					className="flex items-center gap-2 px-4 py-2 text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)] transition-colors rounded-lg hover:bg-[color:var(--color-surface)]/40"
				>
					<ArrowLeft className="w-4 h-4" />
					<span>
						{returnTo === "executions"
							? "Back to Executions"
							: "Back to Workflow"}
					</span>
				</button>
			</div>

			<div className="flex-1 overflow-hidden">
				<ExecutionGraphViewer
					onClose={handleClose}
					execution={execution}
					workflowId={workflowId}
					returnParam={returnTo}
				/>
			</div>
		</div>
	);
}
