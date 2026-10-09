"use client";

import { FileText, Loader2, Trash2, Upload, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import { api } from "@/lib/api";

interface WorkflowFileInfo {
	filename: string;
	file_size: number;
	file_size_kb: number;
	file_extension: string;
	content_type: string;
	uploaded_at: string;
	uploaded_by?: string;
}

interface ExecutionFileUploadProps {
	inputFile: File | null;
	isExecuting: boolean;
	hasFileReadNode: boolean;
	usePersistentStorage: boolean; // true for raw/disabled extraction mode OR when MCP server is connected
	graphName: string;
	onFileSelectAction: (file: File | null) => void;
}

export default function ExecutionFileUpload({
	inputFile,
	isExecuting,
	hasFileReadNode,
	usePersistentStorage,
	graphName,
	onFileSelectAction,
}: ExecutionFileUploadProps) {
	const [isDragging, setIsDragging] = useState(false);
	const [persistentFile, setPersistentFile] = useState<WorkflowFileInfo | null>(null);
	const [isLoadingFile, setIsLoadingFile] = useState(false);
	const [isUploading, setIsUploading] = useState(false);
	const [isDeleting, setIsDeleting] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	// Load persistent file info on mount (only when persistent storage is enabled)
	const loadPersistentFile = useCallback(async () => {
		if (!graphName || !usePersistentStorage) return;

		setIsLoadingFile(true);
		try {
			const response = await api.getWorkflowFile(graphName);
			if (response.success && response.has_file) {
				setPersistentFile(response.file_info);
			} else {
				setPersistentFile(null);
			}
		} catch (error) {
			console.error("Failed to load workflow file:", error);
			setPersistentFile(null);
		} finally {
			setIsLoadingFile(false);
		}
	}, [graphName, usePersistentStorage]);

	useEffect(() => {
		if (usePersistentStorage) {
			loadPersistentFile();
		}
	}, [loadPersistentFile, usePersistentStorage]);

	// Show dropzone if FILE_READ node exists OR if using persistent storage (MCP server)
	if (!hasFileReadNode && !usePersistentStorage) return null;

	const handleBrowseFiles = () => {
		if (!isExecuting && !isUploading) {
			fileInputRef.current?.click();
		}
	};

	// For persistent storage mode - upload to server
	const handleFileChangeWithPersistence = async (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (file) {
			await uploadFile(file);
			e.target.value = "";
		}
	};

	// For non-persistent mode - just set local file
	const handleFileChangeLocal = (e: React.ChangeEvent<HTMLInputElement>) => {
		const file = e.target.files?.[0];
		if (file) {
			onFileSelectAction(file);
			e.target.value = "";
		}
	};

	const uploadFile = async (file: File) => {
		setIsUploading(true);
		try {
			const response = await api.uploadWorkflowFile(graphName, file);
			if (response.success) {
				setPersistentFile(response.file_info);
				onFileSelectAction(file);
			} else {
				console.error("Upload failed:", response.message);
			}
		} catch (error) {
			console.error("Failed to upload file:", error);
		} finally {
			setIsUploading(false);
		}
	};

	// For persistent storage mode
	const handleDropWithPersistence = async (e: React.DragEvent) => {
		e.preventDefault();
		setIsDragging(false);
		if (!isExecuting && !isUploading && e.dataTransfer.files.length > 0) {
			await uploadFile(e.dataTransfer.files[0]);
		}
	};

	// For non-persistent mode
	const handleDropLocal = (e: React.DragEvent) => {
		e.preventDefault();
		setIsDragging(false);
		if (!isExecuting && e.dataTransfer.files.length > 0) {
			onFileSelectAction(e.dataTransfer.files[0]);
		}
	};

	const handleDragOver = (e: React.DragEvent) => {
		e.preventDefault();
		if (!isExecuting && !isUploading) setIsDragging(true);
	};

	const handleDragLeave = () => setIsDragging(false);

	const handleDeleteFile = async (e: React.MouseEvent) => {
		e.stopPropagation();
		setIsDeleting(true);
		try {
			const response = await api.deleteWorkflowFile(graphName);
			if (response.success) {
				setPersistentFile(null);
				onFileSelectAction(null);
			}
		} catch (error) {
			console.error("Failed to delete file:", error);
		} finally {
			setIsDeleting(false);
		}
	};

	const handleRemoveLocalFile = (e: React.MouseEvent) => {
		e.stopPropagation();
		onFileSelectAction(null);
	};

	const formatDate = (isoString: string) => {
		const date = new Date(isoString);
		return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
	};

	// ========================================================================
	// PERSISTENT STORAGE MODE (for FILE_READ with raw/disabled extraction)
	// ========================================================================
	if (usePersistentStorage) {
		// Show loading state
		if (isLoadingFile) {
			return (
				<div className="mb-3">
					<div className="rounded-xl border-2 border-dashed border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-6 text-center">
						<Loader2 className="w-6 h-6 animate-spin mx-auto text-[color:var(--color-text-muted)]" />
						<p className="text-sm text-[color:var(--color-text-muted)] mt-2">Loading file info...</p>
					</div>
				</div>
			);
		}

		// Show persistent file if exists
		if (persistentFile) {
			return (
				<div className="mb-3">
					<input
						ref={fileInputRef}
						type="file"
						accept=".pdf,.png,.jpg,.jpeg,.docx,.txt,.xlsx,.csv,.md,.json,.xml,.html"
						onChange={handleFileChangeWithPersistence}
						style={{ display: "none" }}
						disabled={isExecuting || isUploading}
					/>

					<div className="rounded-xl border-2 border-[color:var(--color-accent)]/60 bg-[color:var(--color-surface)] p-4">
						<div className="flex items-start gap-3">
							<div className="flex-shrink-0 p-2 rounded-lg bg-[color:var(--color-accent)]/10">
								<FileText className="w-6 h-6 text-[color:var(--color-accent)]" />
							</div>
							<div className="flex-1 min-w-0">
								<p className="text-sm font-medium text-slate-900 truncate">
									{persistentFile.filename}
								</p>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
									{persistentFile.file_size_kb} KB · Uploaded {formatDate(persistentFile.uploaded_at)}
								</p>
							</div>
							<div className="flex items-center gap-2">
								<button
									type="button"
									onClick={handleBrowseFiles}
									disabled={isExecuting || isUploading || isDeleting}
									className="px-2 py-1 rounded text-xs bg-[color:var(--color-surface-hover)] text-[color:var(--color-text-secondary)] hover:text-slate-900 transition-colors disabled:opacity-50"
									title="Replace file"
								>
									{isUploading ? (
										<Loader2 className="w-3 h-3 animate-spin" />
									) : (
										"Replace"
									)}
								</button>
								<button
									type="button"
									onClick={handleDeleteFile}
									disabled={isExecuting || isDeleting || isUploading}
									className="p-1.5 rounded hover:bg-red-500/20 text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
									title="Delete file"
								>
									{isDeleting ? (
										<Loader2 className="w-4 h-4 animate-spin" />
									) : (
										<Trash2 className="w-4 h-4" />
									)}
								</button>
							</div>
						</div>
						<p className="text-xs text-[color:var(--color-text-muted)] mt-3 pt-3 border-t border-[color:var(--color-border)]/30">
							This file is saved with the workflow. You can query it directly or replace/delete it.
						</p>
					</div>
				</div>
			);
		}

		// Show upload dropzone for persistent storage (no file yet)
		return (
			<div className="mb-3">
				<input
					ref={fileInputRef}
					type="file"
					accept=".pdf,.png,.jpg,.jpeg,.docx,.txt,.xlsx,.csv,.md,.json,.xml,.html"
					onChange={handleFileChangeWithPersistence}
					style={{ display: "none" }}
					disabled={isExecuting || isUploading}
				/>

				<div
					className={`rounded-xl border-2 border-dashed p-6 text-center transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-3 ${
						isDragging
							? "border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.05)]"
							: "border-[color:var(--color-border)] bg-[color:var(--color-surface)]"
					} ${isExecuting || isUploading ? "opacity-50 cursor-not-allowed" : "hover:border-[color:var(--color-primary)]/50"}`}
					onDrop={handleDropWithPersistence}
					onDragOver={handleDragOver}
					onDragLeave={handleDragLeave}
					onClick={handleBrowseFiles}
				>
					{isUploading ? (
						<>
							<Loader2 className="w-8 h-8 animate-spin text-[color:var(--color-primary)]" />
							<p className="text-sm font-medium text-slate-900">Uploading...</p>
						</>
					) : (
						<>
							<Upload
								className={`w-10 h-10 transition-all ${
									isDragging
										? "text-[color:var(--color-primary)] scale-110"
										: "text-[color:var(--color-text-muted)]"
								}`}
							/>
							<div>
								<p className="text-sm font-medium text-slate-900">
									Drop a file here or click to browse
								</p>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									PDF, DOCX, TXT, CSV, XLSX, images and more
								</p>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
									Max: 1 GB per file
								</p>
							</div>
							<Button
								size="sm"
								icon={<Upload className="w-4 h-4" />}
								onClick={(e) => {
									e.stopPropagation();
									handleBrowseFiles();
								}}
								disabled={isExecuting}
							>
								Select File
							</Button>
						</>
					)}
				</div>
			</div>
		);
	}

	// ========================================================================
	// NON-PERSISTENT MODE (original behavior for regular FILE_READ with OCR)
	// ========================================================================
	return (
		<div className="mb-3">
			<input
				ref={fileInputRef}
				type="file"
				accept=".pdf,.png,.jpg,.jpeg,.docx,.txt,.xlsx,.csv,.md"
				onChange={handleFileChangeLocal}
				style={{ display: "none" }}
				disabled={isExecuting}
			/>

			<div
				className={`rounded-xl border-2 border-dashed p-6 text-center transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-3 ${
					isDragging
						? "border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.05)]"
						: inputFile
							? "border-[color:var(--color-accent)]/60 bg-[color:var(--color-surface)]"
							: "border-[color:var(--color-border)] bg-[color:var(--color-surface)]"
				} ${isExecuting ? "opacity-50 cursor-not-allowed" : "hover:border-[color:var(--color-primary)]/50"}`}
				onDrop={handleDropLocal}
				onDragOver={handleDragOver}
				onDragLeave={handleDragLeave}
				onClick={inputFile ? undefined : handleBrowseFiles}
			>
				{inputFile ? (
					<>
						<FileText className="w-8 h-8 text-[color:var(--color-accent)]" />
						<div className="flex items-center gap-2">
							<span className="text-sm font-medium text-slate-900 truncate max-w-[200px]">
								{inputFile.name}
							</span>
							<button
								type="button"
								onClick={handleRemoveLocalFile}
								disabled={isExecuting}
								className="p-1 rounded hover:bg-[color:var(--color-surface-hover)] text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
								aria-label="Remove file"
							>
								<X className="w-4 h-4" />
							</button>
						</div>
						<p className="text-xs text-[color:var(--color-text-muted)]">
							{(inputFile.size / 1024).toFixed(0)} KB · click the X to change
						</p>
					</>
				) : (
					<>
						<Upload
							className={`w-10 h-10 transition-all ${
								isDragging
									? "text-[color:var(--color-primary)] scale-110"
									: "text-[color:var(--color-text-muted)]"
							}`}
						/>
						<div>
							<p className="text-sm font-medium text-slate-900">
								Drop a file here or click to browse
							</p>
							<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
								PDF, DOCX, TXT, CSV, XLSX, images and more
							</p>
						</div>
						<Button
							size="sm"
							icon={<Upload className="w-4 h-4" />}
							onClick={(e) => {
								e.stopPropagation();
								handleBrowseFiles();
							}}
							disabled={isExecuting}
						>
							Select File
						</Button>
					</>
				)}
			</div>
		</div>
	);
}
