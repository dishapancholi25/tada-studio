"use client";

import { CheckCircle, ChevronRight, StopCircle, XCircle } from "lucide-react";

interface ResultDrawerTriggerProps {
	isVisible: boolean;
	status?: string;
	onClick: () => void;
}

export default function ResultDrawerTrigger({
	isVisible,
	status,
	onClick,
}: ResultDrawerTriggerProps) {
	if (!isVisible) return null;

	const isFailed = status === "failed";
	const isStopped = status === "stopped";

	let Icon = CheckCircle;
	let label = "View Result";
	let iconColor = "text-emerald-600";

	if (isFailed) {
		Icon = XCircle;
		label = "View Error";
		iconColor = "text-red-600";
	} else if (isStopped) {
		Icon = StopCircle;
		label = "Execution Stopped";
		iconColor = "text-amber-700";
	}

	return (
		<button
			type="button"
			onClick={onClick}
			className="group animate-fadeInUp fixed bottom-24 left-1/2 z-40 flex -translate-x-1/2 cursor-pointer items-center gap-3 rounded-2xl border border-gray-200 bg-white px-7 py-4 shadow-[0_12px_40px_rgba(15,23,42,0.12)] transition-colors hover:border-orange-400 hover:bg-slate-50"
		>
			<Icon className={`h-6 w-6 ${iconColor}`} />
			<span className="text-base font-medium text-gray-900 transition-colors group-hover:text-slate-900">
				{label}
			</span>
			<ChevronRight className="h-5 w-5 text-gray-500 transition-colors group-hover:text-slate-900" />
		</button>
	);
}
