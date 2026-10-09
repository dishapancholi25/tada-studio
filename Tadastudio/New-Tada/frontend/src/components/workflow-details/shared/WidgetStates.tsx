"use client";

import { AlertTriangle, Inbox } from "lucide-react";

/** Skeleton block used while a widget is loading. */
export function Skeleton({
	className = "",
	style,
}: {
	className?: string;
	style?: React.CSSProperties;
}) {
	return <div className={`animate-pulse rounded bg-[#EEEEEE] ${className}`} style={style} />;
}

/** Generic multi-line skeleton for card bodies. */
export function SkeletonBlock({ lines = 3, height = 12 }: { lines?: number; height?: number }) {
	return (
		<div className="space-y-2.5">
			{Array.from({ length: lines }).map((_, i) => (
				<Skeleton key={i} className="w-full" style={{ height }} />
			))}
		</div>
	);
}

export function ErrorState({
	message,
	onRetry,
}: {
	message?: string;
	onRetry?: () => void;
}) {
	return (
		<div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
			<AlertTriangle className="h-6 w-6 text-[#B00020]" />
			<p className="text-[13px] font-medium text-[#B00020]">
				{message ?? "Something went wrong"}
			</p>
			{onRetry && (
				<button
					type="button"
					onClick={onRetry}
					className="mt-1 rounded bg-[#FF5E00] px-3 py-1.5 text-[12px] font-semibold text-white transition-colors hover:bg-[#E05500]"
				>
					Retry
				</button>
			)}
		</div>
	);
}

export function EmptyState({ message }: { message?: string }) {
	return (
		<div className="flex flex-col items-center justify-center gap-2 py-8 text-center">
			<Inbox className="h-6 w-6 text-[#B0B0B0]" />
			<p className="text-[13px] font-medium text-[#8A8A8A]">
				{message ?? "No data available"}
			</p>
		</div>
	);
}
