"use client";

import type React from "react";

interface LoadingSkeletonProps {
	variant: "card-grid" | "table" | "stats";
	columns?: number;
	rows?: number;
	className?: string;
}

function SkeletonPulse({
	className = "",
	style,
}: { className?: string; style?: React.CSSProperties }) {
	return (
		<div
			className={`rounded shimmer ${className}`}
			style={{ background: "var(--color-surface)", ...style }}
		/>
	);
}

function StatsSkeletons() {
	return (
		<div className="grid grid-cols-1 md:grid-cols-4 gap-4">
			{Array.from({ length: 4 }).map((_, i) => (
				<div
					key={i}
					className="p-4 rounded-lg"
					style={{
						background: "var(--color-surface)",
						border: "1px solid var(--color-border)",
					}}
				>
					<SkeletonPulse className="h-3 w-20 mb-2" />
					<SkeletonPulse className="h-7 w-16" />
				</div>
			))}
		</div>
	);
}

function CardGridSkeletons({ columns = 3 }: { columns?: number }) {
	const gridClass =
		columns === 2
			? "grid-cols-1 md:grid-cols-2"
			: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3";

	return (
		<div className={`grid ${gridClass} gap-4`}>
			{Array.from({ length: 6 }).map((_, i) => (
				<div
					key={i}
					className="p-4 rounded-lg"
					style={{
						background: "var(--color-surface)",
						border: "1px solid var(--color-border)",
					}}
				>
					<div className="flex items-start gap-3 mb-3">
						<SkeletonPulse className="w-10 h-10 rounded-lg flex-shrink-0" />
						<div className="flex-1 min-w-0">
							<SkeletonPulse className="h-4 w-32 mb-2" />
							<SkeletonPulse className="h-3 w-48" />
						</div>
					</div>
					<div className="flex items-center gap-3 mt-3">
						<SkeletonPulse className="h-5 w-16 rounded-full" />
						<SkeletonPulse className="h-5 w-14 rounded-full" />
						<SkeletonPulse className="h-5 w-12 rounded-full" />
					</div>
				</div>
			))}
		</div>
	);
}

function TableSkeletons({ rows = 5 }: { rows?: number }) {
	return (
		<div>
			{/* Header */}
			<div
				className="flex gap-4 px-5 py-3"
				style={{
					background: "var(--color-surface)",
					borderBottom: "1px solid var(--color-border)",
				}}
			>
				{[120, 60, 60, 50, 50, 50, 80].map((w, i) => (
					<SkeletonPulse key={i} className="h-3" style={{ width: w }} />
				))}
			</div>
			{/* Rows */}
			{Array.from({ length: rows }).map((_, i) => (
				<div
					key={i}
					className="flex items-center gap-4 px-5 py-3"
					style={{ borderBottom: "1px solid var(--color-border)" }}
				>
					<div className="flex items-center gap-3 flex-1">
						<SkeletonPulse className="w-9 h-9 rounded-md flex-shrink-0" />
						<SkeletonPulse className="h-4 w-36" />
					</div>
					<SkeletonPulse className="h-3 w-12" />
					<SkeletonPulse className="h-3 w-14" />
					<SkeletonPulse className="h-3 w-10" />
					<SkeletonPulse className="h-3 w-10" />
					<SkeletonPulse className="h-5 w-16 rounded-full" />
					<SkeletonPulse className="h-3 w-24" />
				</div>
			))}
		</div>
	);
}

export default function LoadingSkeleton({
	variant,
	columns,
	rows,
	className = "",
}: LoadingSkeletonProps) {
	return (
		<div className={className}>
			{variant === "stats" && <StatsSkeletons />}
			{variant === "card-grid" && <CardGridSkeletons columns={columns} />}
			{variant === "table" && <TableSkeletons rows={rows} />}
		</div>
	);
}
