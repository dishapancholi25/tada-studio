"use client";

import {
	AlertCircle,
	CheckCircle,
	Clock,
	Copy,
	Download,
	ExternalLink,
	File,
	FileCode,
	FileText,
	HardDrive,
	Hash,
} from "lucide-react";
import { useState } from "react";
import type { FileViewerSidebarProps } from "./types/fileViewer.types";
import {
	formatFileSize,
	getFileExtension,
	getFileTypeLabel,
	detectFileType,
} from "./utils/fileTypeUtils";

export default function FileViewerSidebar({
	filename,
	fileId,
	fileSize,
	contentType,
	status,
	error,
	timestamp,
	duration,
	callId,
	onDownload,
	onCopyFileId,
	onCopyFilename,
	isDownloading,
}: FileViewerSidebarProps) {
	const [copiedField, setCopiedField] = useState<string | null>(null);
	const detectedType = detectFileType(filename, contentType);

	const handleCopy = async (field: string, value: string) => {
		try {
			await navigator.clipboard.writeText(value);
			setCopiedField(field);
			setTimeout(() => setCopiedField(null), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	};

	const formatTimestamp = (ts: string) => {
		try {
			const date = new Date(ts);
			return date.toLocaleString();
		} catch {
			return ts;
		}
	};

	const CopyButton = ({
		field,
		value,
	}: { field: string; value: string }) => (
		<button
			onClick={() => handleCopy(field, value)}
			className="p-1.5 rounded-lg hover:bg-[color:var(--color-surface)] transition-colors"
			aria-label={`Copy ${field}`}
		>
			{copiedField === field ? (
				<CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
			) : (
				<Copy className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
			)}
		</button>
	);

	return (
		<div className="h-full flex flex-col">
			{/* Status Section */}
			<div className="px-5 py-4 border-b border-[color:var(--color-border)]/40">
				<div
					className={`flex items-center gap-3 p-3 rounded-xl ${
						status === "success"
							? "bg-emerald-500/10 border border-emerald-500/25"
							: "bg-red-500/10 border border-red-500/25"
					}`}
				>
					{status === "success" ? (
						<CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
					) : (
						<AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
					)}
					<div className="min-w-0">
						<p
							className={`text-sm font-medium ${status === "success" ? "text-emerald-400" : "text-red-400"}`}
						>
							{status === "success" ? "File Written" : "Write Failed"}
						</p>
						{error && (
							<p className="text-xs text-red-300 mt-0.5 truncate">{error}</p>
						)}
					</div>
				</div>
			</div>

			{/* File Details Section */}
			<div className="px-5 py-4 border-b border-[color:var(--color-border)]/40">
				<h3 className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-3">
					File Details
				</h3>

				<div className="space-y-3">
					{/* Filename */}
					<div className="flex items-start justify-between gap-2">
						<div className="flex items-center gap-2 min-w-0">
							<FileText className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
							<div className="min-w-0">
								<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Name
								</p>
								<p className="text-sm text-slate-700 font-mono truncate">
									{filename}
								</p>
							</div>
						</div>
						<CopyButton field="filename" value={filename} />
					</div>

					{/* File ID */}
					{fileId && (
						<div className="flex items-start justify-between gap-2">
							<div className="flex items-center gap-2 min-w-0">
								<Hash className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
								<div className="min-w-0">
									<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
										File ID
									</p>
									<p
										className="text-sm text-[color:var(--color-text-secondary)] font-mono truncate"
										title={fileId}
									>
										{fileId}
									</p>
								</div>
							</div>
							<CopyButton field="fileId" value={fileId} />
						</div>
					)}

					{/* File Type */}
					<div className="flex items-center gap-2">
						<FileCode className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
						<div>
							<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
								Type
							</p>
							<p className="text-sm text-[color:var(--color-text-secondary)]">
								{getFileTypeLabel(detectedType.type)}
								{getFileExtension(filename) && (
									<span className="text-[color:var(--color-text-muted)] ml-1">
										({getFileExtension(filename)})
									</span>
								)}
							</p>
						</div>
					</div>

					{/* File Size */}
					{fileSize !== undefined && (
						<div className="flex items-center gap-2">
							<HardDrive className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
							<div>
								<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Size
								</p>
								<p className="text-sm text-slate-700 font-medium">
									{formatFileSize(fileSize)}
								</p>
							</div>
						</div>
					)}

					{/* Content Type */}
					<div className="flex items-center gap-2">
						<File className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
						<div>
							<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
								Content
							</p>
							<span
								className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
									contentType === "base64"
										? "bg-purple-500/20 text-purple-400"
										: "bg-blue-500/20 text-blue-400"
								}`}
							>
								{contentType === "base64" ? "Binary (Base64)" : "Text"}
							</span>
						</div>
					</div>
				</div>
			</div>

			{/* Processing Info Section */}
			<div className="px-5 py-4 border-b border-[color:var(--color-border)]/40">
				<h3 className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold mb-3">
					Processing Info
				</h3>

				<div className="space-y-3">
					{/* Timestamp */}
					{timestamp && (
						<div className="flex items-center gap-2">
							<Clock className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
							<div>
								<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Created
								</p>
								<p className="text-sm text-[color:var(--color-text-secondary)] font-mono">
									{formatTimestamp(timestamp)}
								</p>
							</div>
						</div>
					)}

					{/* Duration */}
					{duration !== undefined && (
						<div className="flex items-center gap-2">
							<Clock className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
							<div>
								<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Duration
								</p>
								<p className="text-sm text-slate-700 font-medium">
									{duration.toFixed(2)}s
								</p>
							</div>
						</div>
					)}

					{/* Call ID */}
					<div className="flex items-start justify-between gap-2">
						<div className="flex items-center gap-2 min-w-0">
							<Hash className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
							<div className="min-w-0">
								<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Call ID
								</p>
								<p
									className="text-xs text-[color:var(--color-text-secondary)] font-mono truncate"
									title={callId}
								>
									{callId}
								</p>
							</div>
						</div>
						<CopyButton field="callId" value={callId} />
					</div>
				</div>
			</div>

			{/* Actions Section - Sticky at bottom */}
			<div className="mt-auto px-5 py-4 border-t border-[color:var(--color-border)]/40 space-y-2">
				{/* Download Button - Primary CTA */}
				<button
					onClick={onDownload}
					disabled={isDownloading || status !== "success" || !fileId}
					className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm
						bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)]
						text-[color:var(--button-primary-text)]
						shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)]
						hover:shadow-[0_20px_50px_rgba(var(--color-primary-rgb),0.45)]
						transition-all duration-200
						disabled:opacity-50 disabled:cursor-not-allowed
						focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
				>
					<Download className="w-4 h-4" />
					{isDownloading ? "Opening..." : "Download File"}
				</button>

				{/* Copy File ID Button - Secondary */}
				{fileId && (
					<button
						onClick={onCopyFileId}
						className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-sm
							border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40
							text-[color:var(--color-text-secondary)]
							hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
							transition-all duration-200
							focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
					>
						<Copy className="w-4 h-4" />
						{copiedField === "file_id" ? "Copied!" : "Copy File ID"}
					</button>
				)}

				{/* Open in New Tab Button - Secondary */}
				<button
					onClick={onDownload}
					disabled={status !== "success" || !fileId}
					className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl font-medium text-sm
						border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40
						text-[color:var(--color-text-secondary)]
						hover:border-[rgba(var(--color-primary-rgb),0.4)] hover:text-slate-900
						transition-all duration-200
						disabled:opacity-50 disabled:cursor-not-allowed
						focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
				>
					<ExternalLink className="w-4 h-4" />
					Open in New Tab
				</button>
			</div>
		</div>
	);
}
