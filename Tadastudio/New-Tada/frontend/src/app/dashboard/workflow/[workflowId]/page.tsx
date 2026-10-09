"use client";

import { ArrowLeft } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import AIApplicationInsights from "@/components/workflow-details/AIApplicationInsights";
import AIHealth from "@/components/workflow-details/AIHealth";
import FeedbackSection from "@/components/workflow-details/FeedbackSection";
import QualityMetrics from "@/components/workflow-details/QualityMetrics";
import RunSummary from "@/components/workflow-details/RunSummary";
import SummaryCards from "@/components/workflow-details/SummaryCards";
import UserSatisfaction from "@/components/workflow-details/UserSatisfaction";
import WorkflowHeader from "@/components/workflow-details/WorkflowHeader";
import WorkflowPerformance from "@/components/workflow-details/WorkflowPerformance";
import Card from "@/components/workflow-details/shared/Card";

function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
	return (
		<div>
			<h2 className="flex items-center gap-2 text-[16px] font-semibold text-[#333333]">
				<span className="h-4 w-1 shrink-0 rounded-full bg-[#FF5E00]" />
				{title}
			</h2>
			{subtitle && (
				<p className="mt-0.5 pl-3 text-[12px] text-[#8A8A8A]">{subtitle}</p>
			)}
		</div>
	);
}

export default function WorkflowDetailsPage() {
	const params = useParams();
	const router = useRouter();
	const rawId = params.workflowId as string;
	const workflowId = decodeURIComponent(rawId ?? "");

	return (
		<AppShell>
			<main className="h-full overflow-y-auto" style={{ background: "#F5F5F9" }}>
				<div className="mx-auto w-full max-w-screen-2xl space-y-6 px-4 py-4 sm:px-6 sm:py-6 lg:px-8">
					{/* Back link */}
					<button
						type="button"
						onClick={() => router.push("/")}
						className="flex items-center gap-1.5 text-[12px] font-medium text-[#8A8A8A] transition-colors hover:text-[#FF5E00]"
					>
						<ArrowLeft className="h-3.5 w-3.5" />
						Back to Dashboard
					</button>

					{/* 1. Workflow header */}
					<WorkflowHeader workflowId={workflowId} />

					{/* 2. KPI summary cards */}
					<SummaryCards workflowId={workflowId} />

					{/* 3 + 4. Quality metrics (Groundedness / Hallucination / Faithfulness) + AI application insights */}
					<div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
						<QualityMetrics workflowId={workflowId} />
						<AIApplicationInsights workflowId={workflowId} />
					</div>

					{/* 5. AI health */}
					<AIHealth workflowId={workflowId} />

					{/* 6. Workflow performance — component owns its header with coverage top-right */}
					<Card>
						<WorkflowPerformance workflowId={workflowId} />
					</Card>

					{/* 8. Run summary & volume */}
					<Card>
						<section className="space-y-4">
							<SectionTitle
								title="Run Summary & Volume"
								subtitle="Monitor execution volumes, success rates, failures, and activity trends for this workflow."
							/>
							<RunSummary workflowId={workflowId} />
						</section>
					</Card>

					{/* 9 + 10. User Satisfaction header spans full width; metric cards + feedback are side-by-side below */}
					<Card>
						{/* Section header — sits above both columns so feedback aligns with metric cards */}
						<div className="mb-5">
							<h2 className="flex items-center gap-2 text-[15px] font-semibold text-[#333333]">
								<span className="h-4 w-1 shrink-0 rounded-full bg-[#FF5E00]" />
								User Satisfaction
							</h2>
							<p className="mt-0.5 pl-3 text-[12px] text-[#8A8A8A]">User experience and satisfaction across workflows</p>
						</div>

						{/* Two columns: pinned-width metric cards on left, flex feedback panel on right */}
						<div className="flex flex-col gap-6 xl:flex-row xl:items-start">
							{/* Left: metric cards only — no nested header */}
							<div className="w-full overflow-hidden xl:w-[320px] xl:flex-none">
								<UserSatisfaction workflowId={workflowId} contentOnly />
							</div>
							{/* Right: Recent Feedback fills remaining space */}
							<div className="min-w-0 flex-1">
								<div className="h-full rounded-xl border border-[#E0E0E0] bg-white p-4 sm:p-5 shadow-[0px_8px_12px_rgba(0,0,0,0.1)]">
									<FeedbackSection workflowId={workflowId} bare />
								</div>
							</div>
						</div>
					</Card>
				</div>
			</main>
		</AppShell>
	);
}
