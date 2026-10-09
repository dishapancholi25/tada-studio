"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import Button from "./Button";

interface PaginationProps {
	currentPage: number;
	totalCount: number;
	pageSize: number;
	onPageChange: (page: number) => void;
	onPageSizeChange?: (size: number) => void;
	pageSizeOptions?: number[];
	showPageSizeSelector?: boolean;
	/** Light surfaces: dark text, slate borders, orange active page (settings tabs on white cards). */
	appearance?: "default" | "light";
}

export default function Pagination({
	currentPage,
	totalCount,
	pageSize,
	onPageChange,
	onPageSizeChange,
	pageSizeOptions = [20, 50, 100],
	showPageSizeSelector = true,
	appearance = "default",
}: PaginationProps) {
	const isLight = appearance === "light";
	const totalPages = Math.ceil(totalCount / pageSize);
	const startItem = totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1;
	const endItem = Math.min(currentPage * pageSize, totalCount);

	// Generate page numbers to show
	const getPageNumbers = () => {
		const pages: (number | string)[] = [];
		const maxVisible = 7; // Maximum page buttons to show

		if (totalPages <= maxVisible) {
			// Show all pages if total is small
			for (let i = 1; i <= totalPages; i++) {
				pages.push(i);
			}
		} else {
			// Always show first page
			pages.push(1);

			if (currentPage > 3) {
				pages.push("...");
			}

			// Show pages around current page
			const start = Math.max(2, currentPage - 1);
			const end = Math.min(totalPages - 1, currentPage + 1);

			for (let i = start; i <= end; i++) {
				pages.push(i);
			}

			if (currentPage < totalPages - 2) {
				pages.push("...");
			}

			// Always show last page
			if (totalPages > 1) {
				pages.push(totalPages);
			}
		}

		return pages;
	};

	const pageNumbers = getPageNumbers();

	const handlePageChange = (page: number) => {
		if (page >= 1 && page <= totalPages && page !== currentPage) {
			onPageChange(page);
		}
	};

	if (totalCount === 0) {
		return null;
	}

	return (
		<div
			className={cn(
				"flex flex-wrap items-center justify-between gap-4 px-4 py-3",
				isLight ? "bg-white" : "",
			)}
		>
			{/* Left: Showing X-Y of Z */}
			<div
				className={cn("text-sm", isLight ? "text-slate-600" : "")}
				style={!isLight ? { color: "var(--color-text-muted)" } : undefined}
			>
				Showing{" "}
				<span
					className={cn(isLight && "font-medium text-slate-900")}
					style={!isLight ? { color: "var(--color-text-primary)" } : undefined}
				>
					{startItem}-{endItem}
				</span>{" "}
				of{" "}
				<span
					className={cn(isLight && "font-medium text-slate-900")}
					style={!isLight ? { color: "var(--color-text-primary)" } : undefined}
				>
					{totalCount}
				</span>
			</div>

			{/* Center: Page navigation */}
			<div className="flex items-center gap-1">
				{/* First/Previous */}
				<Button
					variant="ghost"
					size="sm"
					onClick={() => handlePageChange(currentPage - 1)}
					disabled={currentPage === 1}
					aria-label="Previous page"
					className={
						isLight
							? "!text-slate-700 hover:!bg-slate-100 hover:!text-orange-800"
							: undefined
					}
				>
					<ChevronLeft className="h-4 w-4" />
				</Button>

				{/* Page numbers */}
				{pageNumbers.map((pageNum, idx) => {
					if (pageNum === "...") {
						return (
							<span
								key={`ellipsis-${idx}`}
								className={cn(
									"px-3 py-1 text-sm",
									isLight ? "text-slate-500" : "",
								)}
								style={!isLight ? { color: "var(--color-text-muted)" } : undefined}
							>
								...
							</span>
						);
					}

					const page = pageNum as number;
					const isActive = page === currentPage;

					if (isLight) {
						return (
							<button
								key={page}
								type="button"
								onClick={() => handlePageChange(page)}
								className={cn(
									"min-w-[36px] rounded-[4px] px-3 py-1 text-sm transition-colors",
									isActive
										? "bg-orange-500 font-medium text-white shadow-[0_4px_12px_rgba(15,23,42,0.12)] hover:bg-orange-600"
										: "text-slate-800 hover:bg-slate-100 hover:text-slate-900",
								)}
							>
								{page}
							</button>
						);
					}

					return (
						<button
							key={page}
							type="button"
							onClick={() => handlePageChange(page)}
							className="min-w-[36px] rounded px-3 py-1 text-sm transition-colors"
							style={{
								background: isActive ? "var(--color-primary)" : "transparent",
								color: isActive ? "white" : "var(--color-text-primary)",
							}}
							onMouseEnter={(e) => {
								if (!isActive) {
									e.currentTarget.style.background = "var(--color-bg-tertiary)";
								}
							}}
							onMouseLeave={(e) => {
								if (!isActive) {
									e.currentTarget.style.background = "transparent";
								}
							}}
						>
							{page}
						</button>
					);
				})}

				{/* Next/Last */}
				<Button
					variant="ghost"
					size="sm"
					onClick={() => handlePageChange(currentPage + 1)}
					disabled={currentPage === totalPages}
					aria-label="Next page"
					className={
						isLight
							? "!text-slate-700 hover:!bg-slate-100 hover:!text-orange-800"
							: undefined
					}
				>
					<ChevronRight className="h-4 w-4" />
				</Button>
			</div>

			{/* Right: Page size selector */}
			{showPageSizeSelector && onPageSizeChange && (
				<div className="flex items-center gap-2">
					<span
						className={cn("text-sm", isLight ? "text-slate-600" : "")}
						style={!isLight ? { color: "var(--color-text-muted)" } : undefined}
					>
						Per page:
					</span>
					<select
						value={pageSize}
						onChange={(e) => onPageSizeChange(Number(e.target.value))}
						className={cn(
							"cursor-pointer px-3 py-1 text-sm outline-none transition-colors",
							isLight
								? "rounded-[4px] border border-slate-200 bg-white text-slate-900 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15"
								: "rounded",
						)}
						style={
							!isLight
								? {
										background: "var(--color-bg-secondary)",
										border: "1px solid var(--color-border)",
										color: "var(--color-text-primary)",
									}
								: undefined
						}
						onFocus={
							!isLight
								? (e) => {
										e.currentTarget.style.borderColor = "var(--color-primary)";
									}
								: undefined
						}
						onBlur={
							!isLight
								? (e) => {
										e.currentTarget.style.borderColor = "var(--color-border)";
									}
								: undefined
						}
					>
						{pageSizeOptions.map((size) => (
							<option key={size} value={size} className={isLight ? "text-slate-900" : undefined}>
								{size}
							</option>
						))}
					</select>
				</div>
			)}
		</div>
	);
}
