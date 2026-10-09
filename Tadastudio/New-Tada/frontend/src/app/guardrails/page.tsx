"use client";

import { Suspense } from "react";
import GuardrailPolicies from "@/components/core/GuardrailPolicies";
import AppShell from "@/components/layout/AppShell";
import { PageLoading } from "@/components/utils/LazyLoad";

export default function GuardrailsPage() {
	return (
		<AppShell>
			<main className="h-screen bg-white flex flex-col">
				<div className="flex-1 overflow-hidden">
					<Suspense
						fallback={<PageLoading message="Loading Guardrail Policies..." />}
					>
						<GuardrailPolicies />
					</Suspense>
				</div>
			</main>
		</AppShell>
	);
}
