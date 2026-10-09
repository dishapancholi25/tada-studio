"use client";

import { Info } from "lucide-react";
import type { ReactNode } from "react";
import Card from "./Card";
import { EmptyState, ErrorState, SkeletonBlock } from "./WidgetStates";

interface ChartContainerProps {
	title: string;
	/** Renders the design's orange vertical accent bar before the title. */
	titleAccent?: boolean;
	subtitle?: string;
	tooltip?: string;
	/** Optional element rendered on the right of the header (e.g. legend, toggle). */
	action?: ReactNode;
	loading?: boolean;
	error?: string | null;
	/** When true, renders the empty state instead of children. */
	isEmpty?: boolean;
	emptyMessage?: string;
	onRetry?: () => void;
	className?: string;
	/** Height reserved for the skeleton while loading. */
	skeletonHeight?: number;
	/** When true, renders a plain div instead of a Card — for embedding inside
	 *  an outer Card without nesting two white bordered surfaces. */
	bare?: boolean;
	children: ReactNode;
}

/**
 * Standard wrapper for every widget/chart: a titled Card that transparently
 * renders loading (skeleton), error and empty states, and otherwise shows its
 * children. Keeps the section components focused on their content.
 */
export default function ChartContainer({
	title,
	titleAccent = false,
	subtitle,
	tooltip,
	action,
	loading = false,
	error = null,
	isEmpty = false,
	emptyMessage,
	onRetry,
	className = "",
	skeletonHeight = 180,
	bare = false,
	children,
}: ChartContainerProps) {
	const inner = (
		<>
			<div className="mb-3 flex items-start justify-between gap-3">
				<div className="min-w-0">
					<div className="flex items-center gap-1.5">
						{titleAccent && (
							<span className="h-4 w-1 shrink-0 rounded-full bg-[#FF5E00]" />
						)}
						<h3 className="truncate text-[15px] font-semibold text-[#333333]">{title}</h3>
						{tooltip && (
							<span
								className="group/tt relative flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-[#D7D7D7] bg-[#FBFBFB] text-[#4C4C4C]"
								aria-label={tooltip}
							>
								<Info className="h-2.5 w-2.5" />
								<span className="pointer-events-none absolute left-1/2 top-full z-30 mt-2 w-52 -translate-x-1/2 rounded bg-[#252525] px-2.5 py-1.5 text-[11px] font-medium leading-snug text-white opacity-0 shadow-md transition-all duration-200 group-hover/tt:translate-y-1 group-hover/tt:opacity-100">
									{tooltip}
								</span>
							</span>
						)}
					</div>
					{subtitle && <p className="mt-0.5 text-[12px] text-[#8A8A8A]">{subtitle}</p>}
				</div>
				{action && <div className="shrink-0">{action}</div>}
			</div>

			{loading ? (
				<div style={{ minHeight: skeletonHeight }} className="flex items-center">
					<div className="w-full">
						<SkeletonBlock lines={4} height={14} />
					</div>
				</div>
			) : error ? (
				<div style={{ minHeight: skeletonHeight }} className="flex items-center justify-center">
					<ErrorState message={error} onRetry={onRetry} />
				</div>
			) : isEmpty ? (
				<div style={{ minHeight: skeletonHeight }} className="flex items-center justify-center">
					<EmptyState message={emptyMessage} />
				</div>
			) : (
				children
			)}
		</>
	);

	if (bare) {
		return <div className={className}>{inner}</div>;
	}
	return <Card className={className}>{inner}</Card>;
}
