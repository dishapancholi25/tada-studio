"use client";

import { ChevronLeft, ChevronRight, FileText, X } from "lucide-react";
import { useCallback, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface ChatPdfAttachmentProps {
	name: string;
	blobUrl: string;
	size?: number;
}

function formatBytes(bytes?: number): string | null {
	if (!bytes) return null;
	if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
	return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ChatPdfAttachment({
	name,
	blobUrl,
	size,
}: ChatPdfAttachmentProps) {
	const [modalOpen, setModalOpen] = useState(false);
	const [numPages, setNumPages] = useState(0);
	const [pageNumber, setPageNumber] = useState(1);

	const handlePrev = useCallback(
		() => setPageNumber((p) => Math.max(p - 1, 1)),
		[],
	);
	const handleNext = useCallback(
		() => setPageNumber((p) => Math.min(p + 1, numPages)),
		[numPages],
	);

	const sizeLabel = formatBytes(size);

	return (
		<>
			<button
				type="button"
				onClick={() => setModalOpen(true)}
				className="mt-2 flex w-full max-w-[280px] items-center gap-3 rounded-xl border border-gray-200 bg-white px-3 py-2.5 text-left transition-colors hover:border-orange-400 hover:bg-slate-50"
			>
				<div className="flex h-10 w-9 shrink-0 items-center justify-center rounded-lg border border-red-200 bg-white">
					<FileText className="h-[18px] w-[18px] text-red-500" />
				</div>
				<div className="min-w-0 flex-1">
					<p className="truncate text-xs font-semibold leading-tight text-slate-800">
						{name}
					</p>
					<p className="mt-0.5 text-[10px] text-slate-500">
						PDF{sizeLabel ? ` · ${sizeLabel}` : ""}
					</p>
				</div>
				<span className="shrink-0 rounded-lg bg-orange-600 px-2 py-1 text-[10px] font-semibold text-white transition-colors hover:bg-orange-700">
					View
				</span>
			</button>

			{modalOpen && (
				<div
					className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
					onClick={() => setModalOpen(false)}
				>
					<div
						className="relative flex h-[88vh] w-[90vw] max-w-3xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
						onClick={(e) => e.stopPropagation()}
					>
						<div className="flex-none border-b border-gray-200 bg-white">
							<div className="flex flex-wrap items-start justify-between gap-3 px-6 pb-4 pt-5">
								<div className="flex min-w-0 items-start gap-3">
									<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
										<FileText className="h-5 w-5 text-orange-600" aria-hidden />
									</div>
									<div className="min-w-0">
										<p className="text-xs font-semibold capitalize tracking-wide text-gray-500">
											PDF preview
										</p>
										<h2 className="truncate text-lg font-semibold tracking-tight text-gray-900">
											{name}
										</h2>
									</div>
								</div>
								<div className="flex shrink-0 items-center gap-2">
									{numPages > 1 && (
										<div className="flex items-center gap-1 text-gray-600">
											<button
												type="button"
												onClick={handlePrev}
												disabled={pageNumber <= 1}
												className="rounded-lg p-1 text-gray-600 transition-colors hover:bg-slate-100 hover:text-slate-900 disabled:opacity-30"
											>
												<ChevronLeft className="h-4 w-4" />
											</button>
											<span className="tabular-nums text-xs">
												{pageNumber} / {numPages}
											</span>
											<button
												type="button"
												onClick={handleNext}
												disabled={pageNumber >= numPages}
												className="rounded-lg p-1 text-gray-600 transition-colors hover:bg-slate-100 hover:text-slate-900 disabled:opacity-30"
											>
												<ChevronRight className="h-4 w-4" />
											</button>
										</div>
									)}
									<button
										type="button"
										onClick={() => setModalOpen(false)}
										className="rounded-lg border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900"
										aria-label="Close"
									>
										<X className="h-4 w-4" />
									</button>
								</div>
							</div>
						</div>

						<div className="flex flex-1 justify-center overflow-auto bg-slate-100 p-6">
							<Document
								file={blobUrl}
								onLoadSuccess={({ numPages: n }) => {
									setNumPages(n);
									setPageNumber(1);
								}}
								loading={
									<div className="flex h-40 items-center justify-center">
										<div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-orange-600" />
									</div>
								}
								error={
									<div className="flex h-40 items-center justify-center text-sm text-slate-600">
										Failed to load PDF
									</div>
								}
							>
								<Page
									pageNumber={pageNumber}
									renderTextLayer
									renderAnnotationLayer
									className="overflow-hidden rounded shadow-lg"
								/>
							</Document>
						</div>
					</div>
				</div>
			)}
		</>
	);
}
