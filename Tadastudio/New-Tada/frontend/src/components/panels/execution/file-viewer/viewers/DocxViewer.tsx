"use client";

import {
	ChevronLeft,
	ChevronRight,
	Download,
	Minus,
	Plus,
	RotateCcw,
} from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import mammoth from "mammoth";
import { api } from "@/lib/api";
import "./docxViewer.css";
import type { DocxViewerProps } from "../types/fileViewer.types";

// A4 page dimensions at 96 DPI (pixels)
const PAGE_WIDTH = 816;
const PAGE_HEIGHT = 1056;
const PAGE_PADDING = 72; // ~0.75 inch margins
const PAGE_GAP = 24;

export default function DocxViewer({ src }: DocxViewerProps) {
	const [html, setHtml] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [numPages, setNumPages] = useState(0);
	const [pageNumber, setPageNumber] = useState(1);
	const [scale, setScale] = useState(1);

	const scrollContainerRef = useRef<HTMLDivElement>(null);
	const measureRef = useRef<HTMLDivElement>(null);

	const MIN_SCALE = 0.5;
	const MAX_SCALE = 3;
	const ZOOM_STEP = 0.25;

	// Load and convert DOCX
	useEffect(() => {
		let cancelled = false;

		async function loadDocx() {
			try {
				const url = await api.getFileUrl(src, false);
				const response = await fetch(url);
				if (!response.ok) {
					throw new Error(`Failed to fetch file: ${response.statusText}`);
				}
				const arrayBuffer = await response.arrayBuffer();
				const result = await mammoth.convertToHtml({ arrayBuffer });

				if (!cancelled) {
					setHtml(result.value);
					setLoading(false);
				}
			} catch (err) {
				if (!cancelled) {
					setError(
						err instanceof Error ? err.message : "Failed to load document",
					);
					setLoading(false);
				}
			}
		}

		loadDocx();
		return () => {
			cancelled = true;
		};
	}, [src]);

	// Calculate page count after HTML renders using hidden measurement div
	useEffect(() => {
		if (!html || !measureRef.current) return;

		const observer = new ResizeObserver(() => {
			if (measureRef.current) {
				const contentHeight = measureRef.current.scrollHeight;
				const usableHeight = PAGE_HEIGHT - PAGE_PADDING * 2;
				const pages = Math.max(1, Math.ceil(contentHeight / usableHeight));
				setNumPages(pages);
			}
		});

		observer.observe(measureRef.current);
		return () => observer.disconnect();
	}, [html]);

	// Track current page from scroll position
	useEffect(() => {
		const container = scrollContainerRef.current;
		if (!container || numPages <= 0) return;

		const handleScroll = () => {
			const scrollTop = container.scrollTop;
			const pageWithGap = (PAGE_HEIGHT + PAGE_GAP) * scale;
			const current = Math.floor(scrollTop / pageWithGap) + 1;
			setPageNumber(Math.min(Math.max(1, current), numPages));
		};

		container.addEventListener("scroll", handleScroll, { passive: true });
		return () => container.removeEventListener("scroll", handleScroll);
	}, [numPages, scale]);

	const scrollToPage = useCallback(
		(page: number) => {
			const container = scrollContainerRef.current;
			if (!container) return;
			const pageWithGap = (PAGE_HEIGHT + PAGE_GAP) * scale;
			container.scrollTo({
				top: (page - 1) * pageWithGap,
				behavior: "smooth",
			});
		},
		[scale],
	);

	const handlePrevPage = useCallback(() => {
		const prev = Math.max(pageNumber - 1, 1);
		setPageNumber(prev);
		scrollToPage(prev);
	}, [pageNumber, scrollToPage]);

	const handleNextPage = useCallback(() => {
		const next = Math.min(pageNumber + 1, numPages);
		setPageNumber(next);
		scrollToPage(next);
	}, [pageNumber, numPages, scrollToPage]);

	const handleZoomIn = useCallback(() => {
		setScale((prev) => Math.min(prev + ZOOM_STEP, MAX_SCALE));
	}, []);

	const handleZoomOut = useCallback(() => {
		setScale((prev) => Math.max(prev - ZOOM_STEP, MIN_SCALE));
	}, []);

	const handleReset = useCallback(() => {
		setScale(1);
		setPageNumber(1);
		scrollContainerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
	}, []);

	const handleDownload = useCallback(async () => {
		try {
			const url = await api.getFileUrl(src, true);
			window.open(url, "_blank");
		} catch (err) {
			console.error("Failed to download DOCX:", err);
		}
	}, [src]);

	// Keyboard navigation
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === "ArrowLeft" || e.key === "PageUp") {
				handlePrevPage();
			} else if (e.key === "ArrowRight" || e.key === "PageDown") {
				handleNextPage();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [handlePrevPage, handleNextPage]);

	if (loading) {
		return (
			<div className="h-full flex items-center justify-center">
				<div className="flex flex-col items-center gap-4 text-center">
					<div className="w-12 h-12 rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.35)] border-t-[color:var(--color-primary)] animate-spin" />
					<div>
						<p className="text-sm font-medium text-slate-900">
							Loading document...
						</p>
						<p className="text-xs text-[color:var(--color-text-muted)]">
							Converting to preview
						</p>
					</div>
				</div>
			</div>
		);
	}

	if (error) {
		return (
			<div className="h-full flex items-center justify-center p-8">
				<div className="flex flex-col items-center gap-4 text-center max-w-md">
					<div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center">
						<Download className="w-8 h-8 text-red-400" />
					</div>
					<div>
						<p className="text-lg font-semibold text-slate-900 mb-2">
							Document Preview Unavailable
						</p>
						<p className="text-sm text-[color:var(--color-text-secondary)] mb-4">
							{error}
						</p>
						<button
							onClick={handleDownload}
							className="flex items-center gap-2 px-4 py-2 rounded-xl font-medium text-sm
								bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)]
								text-[color:var(--button-primary-text)]
								shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)]
								hover:shadow-[0_20px_50px_rgba(var(--color-primary-rgb),0.45)]
								transition-all duration-200"
						>
							<Download className="w-4 h-4" />
							Download Document
						</button>
					</div>
				</div>
			</div>
		);
	}

	const usableHeight = PAGE_HEIGHT - PAGE_PADDING * 2;

	// Generate page containers
	const pages = Array.from({ length: numPages }, (_, i) => i);

	return (
		<div className="h-full flex flex-col">
			{/* Toolbar — mirrors PdfViewer */}
			<div className="flex items-center justify-between px-4 py-2 border-b border-[color:var(--color-border)]/40 bg-[rgba(20,20,20,0.5)]">
				<div className="flex items-center gap-3">
					{/* Page navigation */}
					<div className="flex items-center gap-1 rounded-lg border border-[color:var(--color-border)]/60 overflow-hidden">
						<button
							onClick={handlePrevPage}
							disabled={pageNumber <= 1}
							className="p-1.5 text-[color:var(--color-text-secondary)] hover:text-slate-900 hover:bg-[color:var(--color-surface)]/50 transition-colors disabled:opacity-30"
							aria-label="Previous page"
						>
							<ChevronLeft className="w-4 h-4" />
						</button>
						<span className="px-2 text-xs font-mono text-[color:var(--color-text-secondary)] min-w-[5rem] text-center">
							{pageNumber} / {numPages || "..."}
						</span>
						<button
							onClick={handleNextPage}
							disabled={pageNumber >= numPages}
							className="p-1.5 text-[color:var(--color-text-secondary)] hover:text-slate-900 hover:bg-[color:var(--color-surface)]/50 transition-colors disabled:opacity-30"
							aria-label="Next page"
						>
							<ChevronRight className="w-4 h-4" />
						</button>
					</div>

					{/* Zoom controls */}
					<div className="flex items-center gap-1 rounded-lg border border-[color:var(--color-border)]/60 overflow-hidden">
						<button
							onClick={handleZoomOut}
							disabled={scale <= MIN_SCALE}
							className="p-1.5 text-[color:var(--color-text-secondary)] hover:text-slate-900 hover:bg-[color:var(--color-surface)]/50 transition-colors disabled:opacity-30"
							aria-label="Zoom out"
						>
							<Minus className="w-4 h-4" />
						</button>
						<span className="px-2 text-xs font-mono text-[color:var(--color-text-secondary)] min-w-[4rem] text-center">
							{Math.round(scale * 100)}%
						</span>
						<button
							onClick={handleZoomIn}
							disabled={scale >= MAX_SCALE}
							className="p-1.5 text-[color:var(--color-text-secondary)] hover:text-slate-900 hover:bg-[color:var(--color-surface)]/50 transition-colors disabled:opacity-30"
							aria-label="Zoom in"
						>
							<Plus className="w-4 h-4" />
						</button>
					</div>

					{/* Reset button */}
					<button
						onClick={handleReset}
						className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
							border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)]
							hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
							transition-all"
					>
						<RotateCcw className="w-3.5 h-3.5" />
						Reset
					</button>
				</div>

				{/* Download button */}
				<button
					onClick={handleDownload}
					className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
						border border-[color:var(--color-border)]/60 text-[color:var(--color-text-secondary)]
						hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
						transition-all"
				>
					<Download className="w-3.5 h-3.5" />
					Download
				</button>
			</div>

			{/* Hidden measurement div — always rendered so ResizeObserver can measure content height */}
			{html && (
				<div
					ref={measureRef}
					className="docx-page-content"
					style={{
						position: "absolute",
						visibility: "hidden",
						width: `${PAGE_WIDTH - PAGE_PADDING * 2}px`,
						pointerEvents: "none",
					}}
					dangerouslySetInnerHTML={{ __html: html }}
				/>
			)}

			{/* Document pages container */}
			<div
				ref={scrollContainerRef}
				className="flex-1 overflow-auto custom-scrollbar bg-[rgba(15,15,15,0.5)]"
			>
				<div
					className="flex flex-col items-center py-4"
					style={{ gap: `${PAGE_GAP * scale}px` }}
				>
					{pages.map((pageIndex) => (
						<div
							key={pageIndex}
							className="bg-white shadow-[0_20px_60px_rgba(0,0,0,0.5)] rounded-sm overflow-hidden"
							style={{
								width: `${PAGE_WIDTH * scale}px`,
								height: `${PAGE_HEIGHT * scale}px`,
							}}
						>
							<div
								style={{
									width: `${PAGE_WIDTH}px`,
									height: `${PAGE_HEIGHT}px`,
									padding: `${PAGE_PADDING}px`,
									transform: `scale(${scale})`,
									transformOrigin: "top left",
								}}
							>
								<div
									style={{
										height: `${usableHeight}px`,
										overflow: "hidden",
									}}
								>
									<div
										style={{
											marginTop: `-${pageIndex * usableHeight}px`,
										}}
										className="docx-page-content"
										dangerouslySetInnerHTML={{ __html: html || "" }}
									/>
								</div>
							</div>
						</div>
					))}
				</div>
			</div>

		</div>
	);
}
