"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import AppShell from "@/components/layout/AppShell";
import WorkflowTemplatePreview from "@/components/library/WorkflowTemplatePreview";
import { PageLoading } from "@/components/utils/LazyLoad";

export default function LibraryAgentPreviewPage() {
	const params = useParams();
	const searchParams = useSearchParams();
	const paramValue = params?.agentId;
	const agentId = Array.isArray(paramValue) ? paramValue[0] : paramValue;
	const agentInsertMode = searchParams?.get("mode") === "agent-template";

	return (
		<AppShell>
		<main className="flex h-screen flex-col bg-white">
			<div className="flex flex-1 flex-col overflow-hidden bg-white">
				{agentId ? (
					<Suspense
						fallback={<PageLoading message="Preparing agent preview..." />}
					>
						<WorkflowTemplatePreview
							templateId={decodeURIComponent(agentId)}
							templateKind="agent"
							agentInsertMode={agentInsertMode}
						/>
					</Suspense>
				) : (
					<div className="flex h-full flex-col items-center justify-center gap-4 text-center text-[color:var(--color-text-muted)]">
						<p className="text-sm uppercase tracking-wide">No agent selected</p>
						<p className="text-xs text-[color:var(--color-text-secondary)]">
							Return to the library to choose an agent template.
						</p>
					</div>
				)}
			</div>
		</main>
		</AppShell>
	);
}
