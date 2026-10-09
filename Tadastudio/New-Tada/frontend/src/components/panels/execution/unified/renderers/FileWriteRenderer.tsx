import {
	AlertCircle,
	Check,
	CheckCircle,
	Copy,
	Download,
	Eye,
	File,
	FileCode,
	FileOutput,
	FileText,
	Folder,
	HardDrive,
} from "lucide-react";
import React from "react";
import { api } from "@/lib/api";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import type { FileWriteExecution } from "../types/execution.types";
import { BaseRenderer } from "./BaseRenderer";

// File extensions that should use syntax highlighting
const CODE_EXTENSIONS = [".json", ".yaml", ".yml", ".md", ".py", ".js", ".ts", ".tsx", ".css", ".html", ".xml"];

export class FileWriteRenderer extends BaseRenderer<FileWriteExecution> {
	state = {
		copiedField: null as string | null,
		downloadUrl: null as string | null,
		isDownloading: false,
	};

	getViewModes() {
		return [
			{
				key: "summary",
				label: "Summary",
				icon: <FileOutput className="w-4 h-4" />,
			},
			{
				key: "preview",
				label: "Preview",
				icon: <Eye className="w-4 h-4" />,
			},
			{
				key: "details",
				label: "Details",
				icon: <FileText className="w-4 h-4" />,
			},
			{ key: "raw", label: "Raw Data" },
		];
	}

	renderViewMode(mode: string, execution: FileWriteExecution) {
		switch (mode) {
			case "summary":
				return this.renderSummaryView(execution);
			case "preview":
				return this.renderPreviewView(execution);
			case "details":
				return this.renderDetailsView(execution);
			default:
				return (
					<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	handleCopy = async (field: string, value: string) => {
		try {
			await navigator.clipboard.writeText(value);
			this.setState({ copiedField: field });
			setTimeout(() => this.setState({ copiedField: null }), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	};

	handleDownload = async (execution: FileWriteExecution) => {
		if (!execution.file_id) return;

		this.setState({ isDownloading: true });
		try {
			const url = await api.getFileUrl(execution.file_id, true);
			// Open in new tab or trigger download
			window.open(url, "_blank");
		} catch (err) {
			console.error("Failed to get download URL:", err);
		} finally {
			this.setState({ isDownloading: false });
		}
	};

	formatFileSize(bytes?: number): string {
		if (!bytes) return "Unknown";
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
	}

	getFileExtension(filename: string): string {
		const match = filename.match(/\.[^.]+$/);
		return match ? match[0].toLowerCase() : "";
	}

	isCodeFile(filename: string): boolean {
		const ext = this.getFileExtension(filename);
		return CODE_EXTENSIONS.includes(ext);
	}

	getLanguageFromExtension(filename: string): string {
		const ext = this.getFileExtension(filename);
		const langMap: Record<string, string> = {
			".json": "json",
			".yaml": "yaml",
			".yml": "yaml",
			".md": "markdown",
			".py": "python",
			".js": "javascript",
			".ts": "typescript",
			".tsx": "tsx",
			".css": "css",
			".html": "html",
			".xml": "xml",
		};
		return langMap[ext] || "text";
	}

	renderSummaryView(execution: FileWriteExecution) {
		const isSuccess = execution.status === "success";

		return (
			<div className="space-y-6">
				{/* Status Card with Download Button */}
				<div
					className={`bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden border ${
						isSuccess
							? "border-amber-500/30 bg-amber-500/5"
							: "border-red-500/30 bg-red-500/5"
					}`}
				>
					<div className="px-6 py-4 flex items-center justify-between">
						<div className="flex items-center gap-3">
							{isSuccess ? (
								<CheckCircle className="w-6 h-6 text-amber-400" />
							) : (
								<AlertCircle className="w-6 h-6 text-red-400" />
							)}
							<div>
								<h3
									className={`font-semibold ${isSuccess ? "text-amber-400" : "text-red-400"}`}
								>
									{isSuccess ? "File Written Successfully" : "File Write Failed"}
								</h3>
								{execution.filename && (
									<p className="text-sm text-[color:var(--color-text-muted)]">
										{execution.filename}
									</p>
								)}
								{execution.error && (
									<p className="text-sm text-red-400 mt-1">{execution.error}</p>
								)}
							</div>
						</div>

						{/* Download Button - Primary CTA per design system */}
						{isSuccess && execution.file_id && (
							<button
								onClick={() => this.handleDownload(execution)}
								disabled={this.state.isDownloading}
								className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm
									bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)]
									text-[color:var(--button-primary-text)]
									shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)]
									hover:shadow-[0_20px_50px_rgba(var(--color-primary-rgb),0.45)]
									transition-all duration-200
									disabled:opacity-50 disabled:cursor-not-allowed
									focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
							>
								<Download className="w-4 h-4" />
								{this.state.isDownloading ? "Opening..." : "Download"}
							</button>
						)}
					</div>
				</div>

				{/* File Details Card */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden">
					<div className="bg-amber-500/5 border-b border-[color:var(--color-border)]/20 px-6 py-4">
						<h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
							<File className="w-4 h-4 text-amber-400" />
							File Details
						</h3>
					</div>

					<div className="divide-y divide-[color:var(--color-border)]/20">
						{/* Filename */}
						<div className="px-6 py-4 flex items-center justify-between">
							<div className="flex items-center gap-3">
								<FileText className="w-4 h-4 text-[color:var(--color-text-muted)]" />
								<span className="text-sm text-[color:var(--color-text-secondary)]">
									Filename:
								</span>
							</div>
							<div className="flex items-center gap-2">
								<span className="text-sm text-slate-700 font-medium font-mono">
									{execution.filename}
								</span>
								<button
									onClick={() => this.handleCopy("filename", execution.filename)}
									className="p-1.5 rounded-lg hover:bg-[color:var(--color-surface)] transition-colors"
								>
									{this.state.copiedField === "filename" ? (
										<Check className="w-3.5 h-3.5 text-amber-400" />
									) : (
										<Copy className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
									)}
								</button>
							</div>
						</div>

						{/* File ID */}
						{execution.file_id && (
							<div className="px-6 py-4 flex items-center justify-between">
								<div className="flex items-center gap-3">
									<Folder className="w-4 h-4 text-[color:var(--color-text-muted)]" />
									<span className="text-sm text-[color:var(--color-text-secondary)]">
										File ID:
									</span>
								</div>
								<div className="flex items-center gap-2">
									<span className="text-sm text-slate-700 font-mono text-right max-w-[300px] truncate">
										{execution.file_id}
									</span>
									<button
										onClick={() => this.handleCopy("file_id", execution.file_id || "")}
										className="p-1.5 rounded-lg hover:bg-[color:var(--color-surface)] transition-colors"
									>
										{this.state.copiedField === "file_id" ? (
											<Check className="w-3.5 h-3.5 text-amber-400" />
										) : (
											<Copy className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
										)}
									</button>
								</div>
							</div>
						)}

						{/* Content Type */}
						<div className="px-6 py-4 flex items-center justify-between">
							<div className="flex items-center gap-3">
								<FileOutput className="w-4 h-4 text-[color:var(--color-text-muted)]" />
								<span className="text-sm text-[color:var(--color-text-secondary)]">
									Content Type:
								</span>
							</div>
							<span
								className={`px-2 py-1 rounded text-xs font-medium ${
									execution.content_type === "base64"
										? "bg-purple-500/20 text-purple-400"
										: "bg-blue-500/20 text-blue-400"
								}`}
							>
								{execution.content_type === "base64" ? "Binary (Base64)" : "Text"}
							</span>
						</div>

						{/* File Size */}
						{execution.file_size !== undefined && (
							<div className="px-6 py-4 flex items-center justify-between">
								<div className="flex items-center gap-3">
									<HardDrive className="w-4 h-4 text-[color:var(--color-text-muted)]" />
									<span className="text-sm text-[color:var(--color-text-secondary)]">
										File Size:
									</span>
								</div>
								<span className="text-sm text-slate-700 font-medium">
									{this.formatFileSize(execution.file_size)}
								</span>
							</div>
						)}

						{/* Subdirectory */}
						{execution.subdirectory && (
							<div className="px-6 py-4 flex items-center justify-between">
								<div className="flex items-center gap-3">
									<Folder className="w-4 h-4 text-[color:var(--color-text-muted)]" />
									<span className="text-sm text-[color:var(--color-text-secondary)]">
										Subdirectory:
									</span>
								</div>
								<span className="text-sm text-slate-700 font-mono">
									{execution.subdirectory}
								</span>
							</div>
						)}
					</div>
				</div>
			</div>
		);
	}

	renderPreviewView(execution: FileWriteExecution) {
		const isCodeFile = this.isCodeFile(execution.filename);
		const hasContent = execution.content && execution.content_type === "text";

		return (
			<div className="space-y-4">
				{/* Preview Header */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden">
					<div className="bg-amber-500/5 border-b border-[color:var(--color-border)]/20 px-6 py-4 flex items-center justify-between">
						<h3 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
							{isCodeFile ? (
								<FileCode className="w-4 h-4 text-amber-400" />
							) : (
								<FileText className="w-4 h-4 text-amber-400" />
							)}
							File Preview
							{execution.filename && (
								<span className="text-[color:var(--color-text-muted)] font-normal ml-2">
									({execution.filename})
								</span>
							)}
						</h3>
						<div className="flex items-center gap-2">
							{hasContent && (
								<button
									onClick={() => this.handleCopy("content", execution.content || "")}
									className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
										border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40
										hover:border-[rgba(var(--color-primary-rgb),0.4)]
										transition-colors"
								>
									{this.state.copiedField === "content" ? (
										<>
											<Check className="w-3.5 h-3.5 text-amber-400" />
											Copied!
										</>
									) : (
										<>
											<Copy className="w-3.5 h-3.5" />
											Copy
										</>
									)}
								</button>
							)}
							{execution.file_id && (
								<button
									onClick={() => this.handleDownload(execution)}
									disabled={this.state.isDownloading}
									className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium
										bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)]
										text-[color:var(--button-primary-text)]
										shadow-[0_10px_25px_rgba(var(--color-primary-rgb),0.25)]
										hover:shadow-[0_15px_35px_rgba(var(--color-primary-rgb),0.35)]
										transition-all duration-200
										disabled:opacity-50"
								>
									<Download className="w-3.5 h-3.5" />
									Download
								</button>
							)}
						</div>
					</div>

					{/* Content Preview */}
					<div className="p-4">
						{execution.content_type === "base64" ? (
							<div className="flex flex-col items-center justify-center py-12 text-center">
								<File className="w-12 h-12 text-[color:var(--color-text-muted)] mb-4" />
								<p className="text-[color:var(--color-text-secondary)] mb-2">
									Binary file
								</p>
								<p className="text-sm text-[color:var(--color-text-muted)]">
									Open the file viewer for a full preview, or download to view in an external app
								</p>
							</div>
						) : hasContent ? (
							<div
								className="rounded-2xl border border-[color:var(--color-border)]/70
									bg-[color:var(--color-surface)]/40
									shadow-[0_20px_55px_rgba(0,0,0,0.55)]
									overflow-hidden"
							>
								<pre
									className="p-4 font-mono text-sm text-[color:var(--color-text-secondary)]
										whitespace-pre-wrap break-words
										overflow-auto custom-scrollbar max-h-[500px]"
								>
									{execution.content}
								</pre>
							</div>
						) : (
							<div className="flex flex-col items-center justify-center py-12 text-center">
								<Eye className="w-12 h-12 text-[color:var(--color-text-muted)] mb-4" />
								<p className="text-[color:var(--color-text-secondary)] mb-2">
									Content preview not available
								</p>
								<p className="text-sm text-[color:var(--color-text-muted)]">
									{execution.file_id ? "Download the file to view its contents" : "File not available"}
								</p>
							</div>
						)}
					</div>
				</div>
			</div>
		);
	}

	renderDetailsView(execution: FileWriteExecution) {
		return (
			<div className="space-y-4">
				{/* Metadata */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden">
					<div className="bg-amber-500/5 border-b border-[color:var(--color-border)]/20 px-6 py-4">
						<h3 className="text-sm font-semibold text-slate-900">Execution Details</h3>
					</div>
					<div className="p-6">
						<dl className="grid grid-cols-2 gap-4 text-sm">
							<div>
								<dt className="text-[color:var(--color-text-muted)]">Status</dt>
								<dd
									className={`font-medium mt-1 ${
										execution.status === "success"
											? "text-amber-400"
											: "text-red-400"
									}`}
								>
									{execution.status === "success" ? "Success" : "Failed"}
								</dd>
							</div>
							<div>
								<dt className="text-[color:var(--color-text-muted)]">
									Content Type
								</dt>
								<dd className="text-slate-900 font-medium mt-1">
									{execution.content_type === "base64" ? "Binary" : "Text"}
								</dd>
							</div>
							{execution.file_size !== undefined && (
								<div>
									<dt className="text-[color:var(--color-text-muted)]">
										File Size
									</dt>
									<dd className="text-slate-900 font-medium mt-1">
										{this.formatFileSize(execution.file_size)}
									</dd>
								</div>
							)}
							{execution.timestamp && (
								<div>
									<dt className="text-[color:var(--color-text-muted)]">
										Timestamp
									</dt>
									<dd className="text-slate-900 font-mono text-xs mt-1">
										{execution.timestamp}
									</dd>
								</div>
							)}
							{execution.duration !== undefined && (
								<div>
									<dt className="text-[color:var(--color-text-muted)]">
										Duration
									</dt>
									<dd className="text-slate-900 font-medium mt-1">
										{execution.duration.toFixed(2)}s
									</dd>
								</div>
							)}
							<div>
								<dt className="text-[color:var(--color-text-muted)]">Call ID</dt>
								<dd className="text-slate-900 font-mono text-xs mt-1">
									{execution.call_id}
								</dd>
							</div>
						</dl>
					</div>
				</div>

				{/* Error Details (if any) */}
				{execution.error && (
					<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden border border-red-500/30">
						<div className="bg-red-500/5 border-b border-[color:var(--color-border)]/20 px-6 py-4">
							<h3 className="text-sm font-semibold text-red-400 flex items-center gap-2">
								<AlertCircle className="w-4 h-4" />
								Error Details
							</h3>
						</div>
						<div className="p-6">
							<pre className="text-sm text-red-400 whitespace-pre-wrap font-mono">
								{execution.error}
							</pre>
						</div>
					</div>
				)}
			</div>
		);
	}
}
