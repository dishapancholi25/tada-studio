"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

interface NodeFeedbackButtonsProps {
	executionId: string;
	nodeExecutionId: string;
}

export default function NodeFeedbackButtons({
	executionId,
	nodeExecutionId,
}: NodeFeedbackButtonsProps) {
	const [rating, setRating] = useState<"positive" | "negative" | null>(null);
	const [loading, setLoading] = useState(false);

	useEffect(() => {
		let cancelled = false;
		setRating(null);
		api
			.getExecutionFeedback(executionId, nodeExecutionId)
			.then((feedbacks) => {
				if (cancelled) return;
				if (feedbacks && feedbacks.length > 0) {
					setRating(feedbacks[0].rating as "positive" | "negative");
				}
			})
			.catch(() => {});
		return () => {
			cancelled = true;
		};
	}, [executionId, nodeExecutionId]);

	const handleFeedback = useCallback(
		async (value: "positive" | "negative", e: React.MouseEvent) => {
			e.stopPropagation();
			if (loading) return;

			setLoading(true);
			try {
				if (rating === value) {
					await api.deleteExecutionFeedback(executionId, nodeExecutionId);
					setRating(null);
				} else {
					await api.submitExecutionFeedback(
						executionId,
						value,
						undefined,
						nodeExecutionId,
					);
					setRating(value);
				}
			} catch {
				// Silently ignore feedback errors
			} finally {
				setLoading(false);
			}
		},
		[executionId, nodeExecutionId, rating, loading],
	);

	return (
		<div className="flex items-center gap-1">
			<button
				type="button"
				onClick={(e) => handleFeedback("positive", e)}
				disabled={loading}
				className={`rounded-lg border p-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0DA931]/35 ${
					rating === "positive"
						? "border-[#0DA931] bg-white text-[#0DA931] shadow-sm"
						: "border-transparent text-slate-600 hover:border-[#0DA931]/50 hover:bg-white hover:text-[#0DA931]"
				}`}
				title="Good result"
			>
				<ThumbsUp
					className={`h-3.5 w-3.5 ${rating === "positive" ? "fill-current" : ""}`}
				/>
			</button>
			<button
				type="button"
				onClick={(e) => handleFeedback("negative", e)}
				disabled={loading}
				className={`rounded-lg border p-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/35 ${
					rating === "negative"
						? "border-red-300 bg-white text-red-700 shadow-sm"
						: "border-transparent text-slate-600 hover:border-red-200 hover:bg-white hover:text-red-800"
				}`}
				title="Bad result"
			>
				<ThumbsDown
					className={`w-3.5 h-3.5 ${rating === "negative" ? "fill-current" : ""}`}
				/>
			</button>
		</div>
	);
}
