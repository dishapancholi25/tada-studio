import type { FileWriteExecution } from "../../unified/types/execution.types";

// File type categories for viewer selection
export type FileType =
	| "code"
	| "image"
	| "pdf"
	| "docx"
	| "markdown"
	| "csv"
	| "text"
	| "binary";

// File type detection result
export interface FileTypeDetectionResult {
	type: FileType;
	language: string | null;
	mimeType: string | null;
}

// Main panel props
export interface FileViewerPanelProps {
	nodeId: string;
	nodeName: string;
	executionId: string;
	fileExecution: FileWriteExecution;
	onClose: () => void;
}

// Sidebar props
export interface FileViewerSidebarProps {
	filename: string;
	fileId?: string;
	fileSize?: number;
	contentType: "text" | "base64";
	status: "success" | "failed";
	error?: string;
	timestamp?: string;
	duration?: number;
	callId: string;
	onDownload: () => void;
	onCopyFileId: () => void;
	onCopyFilename: () => void;
	isDownloading: boolean;
}

// Content orchestrator props
export interface FileViewerContentProps {
	filename: string;
	fileId?: string;
	content: string | null;
	contentType: "text" | "base64";
	detectedFileType: FileTypeDetectionResult;
	loading: boolean;
	error?: string;
	onDownload: () => void;
}

// Individual viewer props
export interface CodeViewerProps {
	content: string;
	language: string;
	filename: string;
}

export interface ImageViewerProps {
	src: string;
	alt: string;
	filename: string;
}

export interface PdfViewerProps {
	src: string;
	filename: string;
}

export interface MarkdownViewerProps {
	content: string;
	filename: string;
}

export interface CsvViewerProps {
	content: string;
	filename: string;
}

export interface TextViewerProps {
	content: string;
	filename: string;
}

export interface DocxViewerProps {
	src: string;
	filename: string;
}

export interface BinaryViewerProps {
	filename: string;
	fileId?: string;
	fileSize?: number;
	onDownload: () => void;
}
