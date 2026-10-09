"use client";

import { ThumbsDown, ThumbsUp } from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import { api } from "@/lib/api";

interface ViolationFeedbackControlProps {
	violationId: string | null | undefined;
	size?: "sm" | "md";
}

export default function ViolationFeedbackControl({
	violationId,
	size = "md",
}: ViolationFeedbackControlProps) {
	const [rating, setRating] = useState<"positive" | "negative" | null>(null);
	const [loading, setLoading] = useState(false);

	const iconClass = size === "sm" ? "w-3.5 h-3.5" : "w-4 h-4";
	const buttonPadding = size === "sm" ? "p-1.5" : "p-2";

	const handleFeedback = useCallback(
		async (value: "positive" | "negative", e: React.MouseEvent) => {
			e.stopPropagation();
			if (loading || !violationId) return;

			const previousRating = rating;
			setLoading(true);

			try {
				if (rating === value) {
					// Toggle off — optimistic update
					setRating(null);
					await api.deleteViolationFeedback(violationId);
				} else {
					// Set new rating — optimistic update
					setRating(value);
					await api.submitViolationFeedback(violationId, value);
				}
			} catch {
				// Revert on error
				setRating(previousRating);
			} finally {
				setLoading(false);
			}
		},
		[violationId, rating, loading],
	);

	const isDisabled = !violationId || loading;

	return (
		<div className="flex items-center gap-1">
			<button
				onClick={(e) => handleFeedback("positive", e)}
				disabled={isDisabled}
				aria-label="Mark as legitimate block"
				className={`${buttonPadding} rounded-lg border transition-all focus-visible:outline-none focus-visible:ring-2
					${
						rating === "positive"
							? "text-[#0DA931] bg-[#0DA931]/15 border-[#0DA931]/45"
							: "text-[color:var(--color-text-muted)] hover:text-[#0DA931] hover:bg-[#0DA931]/10 border-transparent hover:border-[#0DA931]/35"
					}
					focus-visible:ring-[#0DA931]/45
					${isDisabled ? "opacity-50 cursor-not-allowed" : ""}`}
				title="Legitimate block"
			>
				<ThumbsUp
					className={`${iconClass} ${rating === "positive" ? "fill-current" : ""}`}
				/>
			</button>
			<button
				onClick={(e) => handleFeedback("negative", e)}
				disabled={isDisabled}
				aria-label="Mark as false positive"
				className={`${buttonPadding} rounded-lg border transition-all focus-visible:outline-none focus-visible:ring-2
					${
						rating === "negative"
							? "text-red-400 bg-red-400/15 border-red-400/45"
							: "text-[color:var(--color-text-muted)] hover:text-red-400 hover:bg-red-400/10 border-transparent hover:border-red-400/35"
					}
					focus-visible:ring-red-400/45
					${isDisabled ? "opacity-50 cursor-not-allowed" : ""}`}
				title="False positive"
			>
				<ThumbsDown
					className={`${iconClass} ${rating === "negative" ? "fill-current" : ""}`}
				/>
			</button>
		</div>
	);
}
