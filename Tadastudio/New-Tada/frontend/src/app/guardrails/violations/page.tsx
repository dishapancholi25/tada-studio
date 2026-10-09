"use client";

import { Suspense } from "react";
import ViolationsDashboard from "@/components/core/guardrails/ViolationsDashboard";
import AppShell from "@/components/layout/AppShell";
import { PageLoading } from "@/components/utils/LazyLoad";

export default function ViolationsPage() {
	return (
		<AppShell>
			<main className="h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-white flex flex-col">
				<div className="flex-1 overflow-hidden">
					<Suspense fallback={<PageLoading message="Loading Violations..." />}>
						<ViolationsDashboard />
					</Suspense>
				</div>
			</main>
		</AppShell>
	);
}
