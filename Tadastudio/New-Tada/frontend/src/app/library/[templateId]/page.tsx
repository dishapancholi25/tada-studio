"use client";

import { useParams } from "next/navigation";
import { Suspense } from "react";
import AppShell from "@/components/layout/AppShell";
import WorkflowTemplatePreview from "@/components/library/WorkflowTemplatePreview";
import { PageLoading } from "@/components/utils/LazyLoad";

export default function LibraryTemplatePreviewPage() {
	const params = useParams();
	const paramValue = params?.templateId;
	const templateId = Array.isArray(paramValue) ? paramValue[0] : paramValue;

	return (
		<AppShell>
		<main className="flex h-screen flex-col bg-white">
			<div className="flex flex-1 flex-col overflow-hidden bg-white">
				{templateId ? (
					<Suspense
						fallback={<PageLoading message="Preparing template preview..." />}
					>
						<WorkflowTemplatePreview
							templateId={decodeURIComponent(templateId)}
						/>
					</Suspense>
				) : (
					<div className="flex h-full flex-col items-center justify-center gap-4 text-center text-[color:var(--color-text-muted)]">
						<p className="text-sm uppercase tracking-wide">
							No template selected
						</p>
						<p className="text-xs text-[color:var(--color-text-secondary)]">
							Return to the library to choose a workflow template.
						</p>
					</div>
				)}
			</div>
		</main>
		</AppShell>
	);
}
