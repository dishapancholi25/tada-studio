"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import WorkflowLibrary from "@/components/core/WorkflowLibrary";
import AppShell from "@/components/layout/AppShell";
import { PageLoading } from "@/components/utils/LazyLoad";

export default function LibraryPage() {
	const searchParams = useSearchParams();
	const agentInsertMode = searchParams?.get("mode") === "agent-template";

	return (
		<AppShell>
			<main className="h-full bg-white flex flex-col">
				<div className="flex-1 overflow-auto">
					<Suspense
						fallback={<PageLoading message="Loading Workflow Library..." />}
					>
						<WorkflowLibrary agentInsertMode={agentInsertMode} />
					</Suspense>
				</div>
			</main>
		</AppShell>
	);
}
