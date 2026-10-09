"use client";

import { MessageSquare } from "lucide-react";
import { useFeedback } from "@/hooks/workflow-metrics/useFeedback";
import ChartContainer from "./shared/ChartContainer";

const SENTIMENT_BADGE: Record<string, { bg: string; text: string; label: string }> = {
	positive: { bg: "bg-[#F1F8E9]", text: "text-[#1B5E20]", label: "Positive" },
	negative: { bg: "bg-[#FFEBEE]", text: "text-[#B00020]", label: "Negative" },
	neutral: { bg: "bg-[#FFF8E1]", text: "text-[#F57C00]", label: "Neutral" },
};

function initials(name: string): string {
	return name
		.split(" ")
		.map((p) => p[0])
		.slice(0, 2)
		.join("")
		.toUpperCase();
}

function formatDate(iso: string): string {
	try {
		return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
	} catch {
		return "";
	}
}

export default function FeedbackSection({
	workflowId,
	bare = false,
}: {
	workflowId: string;
	bare?: boolean;
}) {
	const { data, loading, error, refetch } = useFeedback(workflowId);

	return (
		<ChartContainer
			bare={bare}
			title="Recent Feedback"
			tooltip="Latest user feedback captured for this workflow."
			loading={loading}
			error={error}
			onRetry={refetch}
			skeletonHeight={200}
			action={
				data && data.items.length > 0 ? (
					<button
						type="button"
						className="rounded border border-[#FF5E00] px-3 py-1 text-[12px] font-semibold text-[#FF5E00] transition-colors hover:bg-[#FFF1E8]"
					>
						Export
					</button>
				) : null
			}
		>
			{data && data.items.length > 0 ? (
				<ul className="divide-y divide-[#F2F2F2]">
					{data.items.map((item) => {
						const badge = SENTIMENT_BADGE[item.sentiment] ?? SENTIMENT_BADGE.neutral;
						return (
							<li key={item.id} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
								<span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#FFF1E8] text-[11px] font-bold text-[#FF5E00]">
									{initials(item.author)}
								</span>
								<div className="min-w-0 flex-1">
									<div className="flex items-center justify-between gap-2">
										<span className="truncate text-[13px] font-semibold text-[#333333]">
											{item.author}
										</span>
										<span className="shrink-0 text-[11px] text-[#9A9A9A]">
											{formatDate(item.createdAt)}
										</span>
									</div>
									<p className="mt-0.5 text-[12px] leading-snug text-[#8A8A8A]">{item.message}</p>
								</div>
								<span
									className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold ${badge.bg} ${badge.text}`}
								>
									{item.tag ?? badge.label}
								</span>
							</li>
						);
					})}
				</ul>
			) : (
				<div className="flex min-h-[160px] flex-col items-center justify-center gap-2 py-4">
					<MessageSquare className="h-7 w-7 text-[#D0D0D0]" />
					<p className="text-[13px] font-medium text-[#8A8A8A]">No feedback yet</p>
					<p className="text-[11px] text-[#B0B0B0]">
						Feedback will appear here once users interact with this workflow.
					</p>
				</div>
			)}
		</ChartContainer>
	);
}
