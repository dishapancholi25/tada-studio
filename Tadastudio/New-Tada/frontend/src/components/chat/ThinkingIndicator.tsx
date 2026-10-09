"use client";

import { useEffect, useState } from "react";

interface ThinkingIndicatorProps {
	agentName?: string;
}

export default function ThinkingIndicator({ agentName }: ThinkingIndicatorProps) {
	const [showDelayedText, setShowDelayedText] = useState(false);
	const [showLongWaitText, setShowLongWaitText] = useState(false);

	useEffect(() => {
		const timer = setTimeout(() => setShowDelayedText(true), 5000);
		const longTimer = setTimeout(() => setShowLongWaitText(true), 60000);
		return () => {
			clearTimeout(timer);
			clearTimeout(longTimer);
		};
	}, []);

	const label = agentName ? `${agentName} is thinking` : "Thinking";

	return (
		<div className="flex flex-col gap-1 py-1.5 min-w-[160px]">
			<div className="flex items-center gap-2.5">
				<svg
					width="14"
					height="14"
					viewBox="0 0 14 14"
					className="shrink-0"
				>
					<polygon
						points="7,1 13,7 7,13 1,7"
						fill="none"
						stroke="rgb(234 88 12)"
						strokeWidth="1.2"
					/>
					<circle cx="7" cy="7" r="2" fill="rgb(234 88 12)" />
				</svg>
				<span className="text-xs text-gray-600">{label}</span>
				<span className="typing-dots inline-flex items-center">
					<span />
					<span />
					<span />
				</span>
			</div>
			{showDelayedText && (
				<span className="ml-[26px] animate-fadeInUp text-[10px] text-gray-500">
					Working on it...
				</span>
			)}
			{showLongWaitText && (
				<span className="ml-[26px] animate-fadeInUp text-[10px] text-gray-400">
					This is taking longer than usual. Please wait or refresh to see if the response is ready.
				</span>
			)}
		</div>
	);
}
