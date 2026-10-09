"use client";

import { Suspense } from "react";
import { ExecutionHistory } from "@/components/execution-history";
import AppShell from "@/components/layout/AppShell";
import { PageLoading } from "@/components/utils/LazyLoad";

export default function ExecutionsPage() {
	return (
		<AppShell>
			<div className="h-screen bg-white flex flex-col">
				<div className="flex-1 overflow-hidden">
					<Suspense
						fallback={<PageLoading message="Loading Execution History..." />}
					>
						<ExecutionHistory />
					</Suspense>
				</div>
			</div>
		</AppShell>
	);
}
