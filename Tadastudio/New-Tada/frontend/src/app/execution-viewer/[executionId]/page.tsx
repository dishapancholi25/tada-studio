"use client";

import { Suspense, use } from "react";
import EnhancedExecutionViewer from "@/components/execution/EnhancedExecutionViewer";

interface PageProps {
	params: Promise<{
		executionId: string;
	}>;
}

export default function ExecutionViewerPage({ params }: PageProps) {
	const unwrappedParams = use(params);

	return (
		<Suspense fallback={<LoadingState />}>
			<EnhancedExecutionViewer executionId={unwrappedParams.executionId} />
		</Suspense>
	);
}

function LoadingState() {
	return (
		<div className="min-h-screen bg-[#F3F4F9] flex items-center justify-center">
			<div className="text-center">
				<div className="w-16 h-16 border-4 border-[color:var(--color-border)] border-t-[color:var(--color-primary)] rounded-full animate-spin mx-auto mb-4"></div>
				<p className="text-[color:var(--color-text-muted)] text-lg">
					Loading execution data...
				</p>
			</div>
		</div>
	);
}
