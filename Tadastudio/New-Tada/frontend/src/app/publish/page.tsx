"use client";

import { Suspense } from "react";
import WorkflowPublisher from "@/components/core/WorkflowPublisher";
import AppShell from "@/components/layout/AppShell";
import { PageLoading } from "@/components/utils/LazyLoad";

export default function PublishPage() {
	return (
		<AppShell>
			<main className="h-screen bg-white flex flex-col">
				<div className="flex-1 overflow-hidden">
					<Suspense
						fallback={<PageLoading message="Loading Workflow Publisher..." />}
					>
						<WorkflowPublisher />
					</Suspense>
				</div>
			</main>
		</AppShell>
	);
}
