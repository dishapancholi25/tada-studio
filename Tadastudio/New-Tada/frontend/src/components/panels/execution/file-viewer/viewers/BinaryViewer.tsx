"use client";

import { Download, File, FileQuestion } from "lucide-react";
import type { BinaryViewerProps } from "../types/fileViewer.types";
import { formatFileSize, getFileExtension } from "../utils/fileTypeUtils";

export default function BinaryViewer({
	filename,
	fileId,
	fileSize,
	onDownload,
}: BinaryViewerProps) {
	const extension = getFileExtension(filename);

	return (
		<div className="h-full flex items-center justify-center p-8">
			<div className="flex flex-col items-center gap-6 text-center max-w-md">
				{/* Large file icon */}
				<div className="relative">
					<div className="w-24 h-24 rounded-3xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.15)] to-[rgba(var(--color-primary-rgb),0.05)] border border-[rgba(var(--color-primary-rgb),0.25)] flex items-center justify-center">
						<File className="w-12 h-12 text-[color:var(--color-primary)]" />
					</div>
					{extension && (
						<div className="absolute -bottom-2 -right-2 px-2 py-1 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)]/70 text-xs font-mono text-[color:var(--color-text-secondary)]">
							{extension}
						</div>
					)}
				</div>

				{/* File info */}
				<div>
					<h3 className="text-lg font-semibold text-slate-900 mb-2">{filename}</h3>
					<p className="text-sm text-[color:var(--color-text-secondary)] mb-1">
						Binary file — preview not available
					</p>
					{fileSize !== undefined && (
						<p className="text-sm text-[color:var(--color-text-muted)]">
							{formatFileSize(fileSize)}
						</p>
					)}
				</div>

				{/* Download button */}
				<button
					onClick={onDownload}
					disabled={!fileId}
					className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-sm
						bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)]
						text-[color:var(--button-primary-text)]
						shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)]
						hover:shadow-[0_20px_50px_rgba(var(--color-primary-rgb),0.45)]
						hover:-translate-y-0.5
						transition-all duration-200
						disabled:opacity-50 disabled:cursor-not-allowed
						focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
				>
					<Download className="w-4 h-4" />
					Download File
				</button>

				<p className="text-xs text-[color:var(--color-text-muted)]">
					{fileId ? "Download the file to view its contents" : "File not available for download"}
				</p>
			</div>
		</div>
	);
}
