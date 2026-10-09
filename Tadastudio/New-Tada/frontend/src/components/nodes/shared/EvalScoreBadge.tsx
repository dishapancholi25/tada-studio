"use client";

/**
 * Shared evaluation score badge rendered as a 14px colored dot
 * on the top-right corner of a node.
 *
 * Green (>=80), Amber (>=60), Red (<60).
 */
export default function EvalScoreBadge({
	score,
}: { score: number | null | undefined }) {
	if (score === null || score === undefined) return null;

	return (
		<div
			style={{
				position: "absolute",
				top: -7,
				right: -7,
				width: 14,
				height: 14,
				borderRadius: "50%",
				backgroundColor:
					score >= 80
						? "#0DA931"
						: score >= 60
							? "#f59e0b"
							: "#ef4444",
				border: "1.5px solid #0f172a",
				zIndex: 10,
			}}
			title={`Eval score: ${Math.round(score)}`}
		/>
	);
}
