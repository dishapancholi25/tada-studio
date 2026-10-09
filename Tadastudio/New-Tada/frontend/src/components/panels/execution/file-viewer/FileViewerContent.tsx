"use client";

import { AlertCircle, Loader2 } from "lucide-react";
import type { FileViewerContentProps } from "./types/fileViewer.types";
import BinaryViewer from "./viewers/BinaryViewer";
import CodeViewer from "./viewers/CodeViewer";
import CsvViewer from "./viewers/CsvViewer";
import DocxViewer from "./viewers/DocxViewer";
import ImageViewer from "./viewers/ImageViewer";
import MarkdownViewer from "./viewers/MarkdownViewer";
import PdfViewer from "./viewers/PdfViewer";
import TextViewer from "./viewers/TextViewer";

export default function FileViewerContent({
	filename,
	fileId,
	content,
	contentType,
	detectedFileType,
	loading,
	error,
	onDownload,
}: FileViewerContentProps) {
	// Loading state
	if (loading) {
		return (
			<div className="h-full flex items-center justify-center">
				<div className="flex flex-col items-center gap-4 text-center">
					<div className="w-12 h-12 rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.35)] border-t-[color:var(--color-primary)] animate-spin" />
					<div>
						<p className="text-sm font-medium text-slate-900">Loading file...</p>
						<p className="text-xs text-[color:var(--color-text-muted)]">
							Preparing preview
						</p>
					</div>
				</div>
			</div>
		);
	}

	// Error state (for failed file writes)
	if (error && !content) {
		return (
			<div className="h-full flex items-center justify-center p-8">
				<div className="flex flex-col items-center gap-4 text-center max-w-md">
					<div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center">
						<AlertCircle className="w-8 h-8 text-red-400" />
					</div>
					<div>
						<p className="text-lg font-semibold text-slate-900 mb-2">
							File Write Failed
						</p>
						<p className="text-sm text-[color:var(--color-text-secondary)]">
							{error}
						</p>
					</div>
				</div>
			</div>
		);
	}

	// Render appropriate viewer based on file type
	const renderViewer = () => {
		const { type, language } = detectedFileType;

		switch (type) {
			case "code":
				if (!content) {
					return (
						<BinaryViewer
							filename={filename}
							fileId={fileId}
							onDownload={onDownload}
						/>
					);
				}
				return (
					<CodeViewer
						content={content}
						language={language || "text"}
						filename={filename}
					/>
				);

			case "image":
				// For images, content should be base64 or we need to use the file API
				if (content) {
					const imageSrc = content.startsWith("data:")
						? content
						: `data:image/${filename.split(".").pop()};base64,${content}`;
					return <ImageViewer src={imageSrc} alt={filename} filename={filename} />;
				}
				// No content available - show binary viewer for download
				return (
					<BinaryViewer
						filename={filename}
						fileId={fileId}
						onDownload={onDownload}
					/>
				);

			case "pdf":
				// PDFs need file_id to fetch from the API
				if (fileId) {
					return <PdfViewer src={fileId} filename={filename} />;
				}
				return (
					<BinaryViewer
						filename={filename}
						fileId={fileId}
						onDownload={onDownload}
					/>
				);

			case "docx":
				if (fileId) {
					return <DocxViewer src={fileId} filename={filename} />;
				}
				return (
					<BinaryViewer
						filename={filename}
						fileId={fileId}
						onDownload={onDownload}
					/>
				);

			case "markdown":
				if (!content) {
					return (
						<BinaryViewer
							filename={filename}
							fileId={fileId}
							onDownload={onDownload}
						/>
					);
				}
				return <MarkdownViewer content={content} filename={filename} />;

			case "csv":
				if (!content) {
					return (
						<BinaryViewer
							filename={filename}
							fileId={fileId}
							onDownload={onDownload}
						/>
					);
				}
				return <CsvViewer content={content} filename={filename} />;

			case "text":
				if (!content) {
					return (
						<BinaryViewer
							filename={filename}
							fileId={fileId}
							onDownload={onDownload}
						/>
					);
				}
				return <TextViewer content={content} filename={filename} />;

			case "binary":
			default:
				return (
					<BinaryViewer
						filename={filename}
						fileId={fileId}
						onDownload={onDownload}
					/>
				);
		}
	};

	return (
		<div className="h-full overflow-hidden flex flex-col">{renderViewer()}</div>
	);
}
