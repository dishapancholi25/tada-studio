"use client";

import {
	ChevronLeft,
	ChevronRight,
	Download,
	Minus,
	Plus,
	RotateCcw,
} from "lucide-react";
import { useState, useCallback, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { api } from "@/lib/api";
import type { PdfViewerProps } from "../types/fileViewer.types";

// Set up the worker for PDF.js
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export default function PdfViewer({ src, filename }: PdfViewerProps) {
	const [numPages, setNumPages] = useState<number>(0);
	const [pageNumber, setPageNumber] = useState<number>(1);
	const [scale, setScale] = useState<number>(1);
	const [loading, setLoading] = useState<boolean>(true);
	const [error, setError] = useState<string | null>(null);
	const [pdfUrl, setPdfUrl] = useState<string | null>(null);

	const MIN_SCALE = 0.5;
	const MAX_SCALE = 3;
	const ZOOM_STEP = 0.25;

	console.log("[PdfViewer] Initializing with:", { src, filename });

	// Fetch the PDF URL on mount
	useEffect(() => {
		async function fetchUrl() {
			console.log("[PdfViewer] Fetching URL for file_id:", src);
			try {
				const url = await api.getFileUrl(src, false);
				console.log("[PdfViewer] Got URL:", url);
				setPdfUrl(url);
			} catch (err) {
				console.error("[PdfViewer] Failed to get PDF URL:", err);
				setError("Failed to load PDF URL");
			}
		}
		fetchUrl();
	}, [src]);

	const onDocumentLoadSuccess = useCallback(
		({ numPages }: { numPages: number }) => {
			setNumPages(numPages);
			setLoading(false);
		},
		[],
	);

	const onDocumentLoadError = useCallback(
		(err: Error) => {
			console.error("[PdfViewer] Document load error:", {
				message: err.message,
				name: err.name,
				pdfUrl,
				src,
			});
			setError(`Failed to load PDF: ${err.message}`);
			setLoading(false);
		},
		[pdfUrl, src],
	);

	const handlePrevPage = useCallback(() => {
		setPageNumber((prev) => Math.max(prev - 1, 1));
	}, []);

	const handleNextPage = useCallback(() => {
		setPageNumber((prev) => Math.min(prev + 1, numPages));
	}, [numPages]);

	const handleZoomIn = useCallback(() => {
		setScale((prev) => Math.min(prev + ZOOM_STEP, MAX_SCALE));
	}, []);

	const handleZoomOut = useCallback(() => {
		setScale((prev) => Math.max(prev - ZOOM_STEP, MIN_SCALE));
	}, []);

	const handleReset = useCallback(() => {
		setScale(1);
		setPageNumber(1);
	}, []);

	const handleDownload = useCallback(async () => {
		try {
			const url = await api.getFileUrl(src, true);
			window.open(url, "_blank");
		} catch (err) {
			console.error("Failed to download PDF:", err);
		}
	}, [src]);

	// Handle keyboard navigation
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

	if (error) {
		return (
			<div className="h-full flex items-center justify-center p-8">
				<div className="flex flex-col items-center gap-4 text-center max-w-md">
					<div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center">
						<Download className="w-8 h-8 text-red-400" />
					</div>
					<div>
						<p className="text-lg font-semibold text-slate-900 mb-2">
							PDF Preview Unavailable
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
							Download PDF
						</button>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="h-full flex flex-col">
			{/* Toolbar */}
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

			{/* PDF container */}
			<div className="flex-1 overflow-auto custom-scrollbar bg-[rgba(15,15,15,0.5)]">
				<div className="flex justify-center p-4 min-h-full">
					{pdfUrl && (
						<Document
							file={pdfUrl}
							onLoadSuccess={onDocumentLoadSuccess}
							onLoadError={onDocumentLoadError}
							loading={
								<div className="flex items-center justify-center py-20">
									<div className="flex flex-col items-center gap-4">
										<div className="w-10 h-10 rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.35)] border-t-[color:var(--color-primary)] animate-spin" />
										<p className="text-sm text-[color:var(--color-text-muted)]">
											Loading PDF...
										</p>
									</div>
								</div>
							}
							className="flex flex-col items-center gap-4"
						>
							<Page
								pageNumber={pageNumber}
								scale={scale}
								className="shadow-[0_20px_60px_rgba(0,0,0,0.5)] rounded-lg overflow-hidden"
								renderTextLayer={true}
								renderAnnotationLayer={true}
							/>
						</Document>
					)}
				</div>
			</div>
		</div>
	);
}
