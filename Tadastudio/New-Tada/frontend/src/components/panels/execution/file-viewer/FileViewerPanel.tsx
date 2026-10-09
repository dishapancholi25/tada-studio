"use client";

import { FileOutput, X } from "lucide-react";
import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import type { FileWriteExecution } from "../unified/types/execution.types";
import FileViewerContent from "./FileViewerContent";
import FileViewerSidebar from "./FileViewerSidebar";
import { useFileTypeDetection } from "./hooks/useFileTypeDetection";
import type { FileViewerPanelProps } from "./types/fileViewer.types";

export default function FileViewerPanel({
	nodeId,
	nodeName,
	executionId,
	fileExecution,
	onClose,
}: FileViewerPanelProps) {
	const [copiedField, setCopiedField] = useState<string | null>(null);
	const [isDownloading, setIsDownloading] = useState(false);

	const detectedFileType = useFileTypeDetection(
		fileExecution.filename,
		fileExecution.content_type,
	);

	const handleCopy = useCallback(async (field: string, value: string) => {
		try {
			await navigator.clipboard.writeText(value);
			setCopiedField(field);
			setTimeout(() => setCopiedField(null), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	}, []);

	const handleDownload = useCallback(async () => {
		if (!fileExecution.file_id) return;

		setIsDownloading(true);
		try {
			const url = await api.getFileUrl(fileExecution.file_id, true);
			window.open(url, "_blank");
		} catch (err) {
			console.error("Failed to get download URL:", err);
		} finally {
			setIsDownloading(false);
		}
	}, [fileExecution.file_id]);

	const handleCopyFileId = useCallback(() => {
		if (fileExecution.file_id) {
			handleCopy("file_id", fileExecution.file_id);
		}
	}, [handleCopy, fileExecution.file_id]);

	const handleCopyFilename = useCallback(() => {
		handleCopy("filename", fileExecution.filename);
	}, [handleCopy, fileExecution.filename]);

	// Handle escape key to close
	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Escape") {
				onClose();
			}
		},
		[onClose],
	);

	return (
		<>
		{/* Backdrop - below execution panel (z-40 < z-50) */}
		<div className="fixed inset-0 z-40 bg-black/40 animate-fadeIn" onClick={onClose} />

		{/* Dialog - above execution panel (z-[60] > z-50) */}
		<div
			className="fixed inset-0 z-[60] flex items-center justify-center pointer-events-none animate-fadeIn"
			onKeyDown={handleKeyDown}
			tabIndex={-1}
		>
			{/* Outer gradient frame - full page width */}
				<div className="w-full max-w-[98vw] mx-2 p-[1px] rounded-[30px] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.3)] via-transparent to-[rgba(var(--color-primary-rgb),0.12)] shadow-xl pointer-events-auto">
				{/* Inner modal shell */}
					<div className="rounded-[30px] border border-[color:var(--color-border)] bg-[color:var(--color-surface)] h-[92vh] flex flex-col overflow-hidden">
					{/* Header */}
						<header className="flex items-center justify-between px-6 py-4 border-b border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)]">
						<div className="flex items-center gap-4">
							{/* Icon capsule */}
							<div className="flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/30">
									<FileOutput className="w-6 h-6 text-amber-500" />
							</div>

							{/* Title and subtitle */}
							<div>
									<h1 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
									{fileExecution.filename}
								</h1>
								<p className="text-sm text-[color:var(--color-text-secondary)]">
									File Output from{" "}
									<span className="text-[color:var(--color-primary)]">
										{nodeName}
									</span>
								</p>
							</div>

							{/* Status badge */}
							<div
								className={`px-3 py-1.5 rounded-full text-xs font-medium ${
									fileExecution.status === "success"
											? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30"
											: "bg-red-500/15 text-red-600 border border-red-500/30"
								}`}
							>
								{fileExecution.status === "success"
									? "Written Successfully"
									: "Write Failed"}
							</div>
						</div>

						{/* Close button */}
						<button
							onClick={onClose}
								className="flex items-center justify-center w-10 h-10 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:bg-[color:var(--color-surface-hover)] transition-all duration-200 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
							aria-label="Close file viewer"
						>
								<X className="w-5 h-5 text-[color:var(--color-text-secondary)] group-hover:text-[color:var(--color-text-primary)] transition-colors" />
						</button>
					</header>

					{/* Two-column layout */}
					<div className="flex flex-1 overflow-hidden">
						{/* Left sidebar */}
						<aside className="w-[300px] min-w-[280px] max-w-[320px] border-r border-[color:var(--color-border)]/40 overflow-y-auto custom-scrollbar">
							<FileViewerSidebar
								filename={fileExecution.filename}
								fileId={fileExecution.file_id}
								fileSize={fileExecution.file_size}
								contentType={fileExecution.content_type}
								status={fileExecution.status}
								error={fileExecution.error}
								timestamp={fileExecution.timestamp}
								duration={fileExecution.duration}
								callId={fileExecution.call_id}
								onDownload={handleDownload}
								onCopyFileId={handleCopyFileId}
								onCopyFilename={handleCopyFilename}
								isDownloading={isDownloading}
							/>
						</aside>

						{/* Right content area */}
						<main className="flex-1 overflow-hidden">
							<FileViewerContent
								filename={fileExecution.filename}
								fileId={fileExecution.file_id}
								content={fileExecution.content || null}
								contentType={fileExecution.content_type}
								detectedFileType={detectedFileType}
								loading={false}
								error={fileExecution.error}
								onDownload={handleDownload}
							/>
						</main>
					</div>
				</div>
			</div>
		</div>
		</>
	);
}
