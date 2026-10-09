import type { FileType, FileTypeDetectionResult } from "../types/fileViewer.types";

// Code file extensions with their language mappings
export const CODE_EXTENSIONS: Record<string, string> = {
	".py": "python",
	".js": "javascript",
	".ts": "typescript",
	".tsx": "tsx",
	".jsx": "jsx",
	".json": "json",
	".yaml": "yaml",
	".yml": "yaml",
	".html": "html",
	".htm": "html",
	".css": "css",
	".scss": "scss",
	".sass": "sass",
	".less": "less",
	".xml": "xml",
	".sql": "sql",
	".sh": "bash",
	".bash": "bash",
	".zsh": "bash",
	".go": "go",
	".rs": "rust",
	".java": "java",
	".kt": "kotlin",
	".kts": "kotlin",
	".c": "c",
	".cpp": "cpp",
	".cc": "cpp",
	".h": "c",
	".hpp": "cpp",
	".cs": "csharp",
	".rb": "ruby",
	".php": "php",
	".swift": "swift",
	".r": "r",
	".lua": "lua",
	".toml": "toml",
	".ini": "ini",
	".conf": "ini",
	".dockerfile": "dockerfile",
	".graphql": "graphql",
	".gql": "graphql",
	".vue": "vue",
	".svelte": "svelte",
};

// Image extensions
export const IMAGE_EXTENSIONS = [
	".png",
	".jpg",
	".jpeg",
	".gif",
	".webp",
	".svg",
	".ico",
	".bmp",
	".tiff",
	".tif",
];

// PDF extensions
export const PDF_EXTENSIONS = [".pdf"];

// DOCX extensions
export const DOCX_EXTENSIONS = [".docx"];

// Markdown extensions
export const MARKDOWN_EXTENSIONS = [".md", ".markdown", ".mdx"];

// CSV/TSV extensions
export const CSV_EXTENSIONS = [".csv", ".tsv"];

// Plain text extensions
export const TEXT_EXTENSIONS = [
	".txt",
	".log",
	".env",
	".gitignore",
	".dockerignore",
	".editorconfig",
	".prettierrc",
	".eslintrc",
	".nvmrc",
];

// MIME type mappings
export const MIME_TYPES: Record<string, string> = {
	".png": "image/png",
	".jpg": "image/jpeg",
	".jpeg": "image/jpeg",
	".gif": "image/gif",
	".webp": "image/webp",
	".svg": "image/svg+xml",
	".ico": "image/x-icon",
	".bmp": "image/bmp",
	".pdf": "application/pdf",
	".json": "application/json",
	".xml": "application/xml",
	".html": "text/html",
	".css": "text/css",
	".js": "text/javascript",
	".ts": "text/typescript",
	".md": "text/markdown",
	".txt": "text/plain",
	".csv": "text/csv",
	".docx":
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

/**
 * Extract file extension from filename
 */
export function getFileExtension(filename: string): string {
	const match = filename.match(/\.[^.]+$/);
	return match ? match[0].toLowerCase() : "";
}

/**
 * Get MIME type from filename
 */
export function getMimeType(filename: string): string | null {
	const ext = getFileExtension(filename);
	return MIME_TYPES[ext] || null;
}

/**
 * Detect file type from filename and content type
 */
export function detectFileType(
	filename: string,
	contentType: "text" | "base64",
): FileTypeDetectionResult {
	const extension = getFileExtension(filename).toLowerCase();
	const mimeType = getMimeType(filename);

	// PDFs and images should always be detected by extension, regardless of content type
	// This handles cases where backend marks binary files as "text" incorrectly
	if (PDF_EXTENSIONS.includes(extension)) {
		return { type: "pdf", language: null, mimeType };
	}
	if (IMAGE_EXTENSIONS.includes(extension)) {
		return { type: "image", language: null, mimeType };
	}
	if (DOCX_EXTENSIONS.includes(extension)) {
		return { type: "docx", language: null, mimeType };
	}

	// If content is base64, likely binary
	if (contentType === "base64") {
		return { type: "binary", language: null, mimeType };
	}

	// Text content detection
	if (CODE_EXTENSIONS[extension]) {
		return { type: "code", language: CODE_EXTENSIONS[extension], mimeType };
	}
	if (MARKDOWN_EXTENSIONS.includes(extension)) {
		return { type: "markdown", language: null, mimeType };
	}
	if (CSV_EXTENSIONS.includes(extension)) {
		return { type: "csv", language: null, mimeType };
	}
	if (TEXT_EXTENSIONS.includes(extension)) {
		return { type: "text", language: null, mimeType };
	}

	// Check for special filenames without extension
	const lowercaseFilename = filename.toLowerCase();
	if (
		lowercaseFilename === "dockerfile" ||
		lowercaseFilename.startsWith("dockerfile.")
	) {
		return { type: "code", language: "dockerfile", mimeType };
	}
	if (lowercaseFilename === "makefile") {
		return { type: "code", language: "makefile", mimeType };
	}

	// Default to text for unknown text files
	return { type: "text", language: null, mimeType };
}

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes?: number): string {
	if (bytes === undefined || bytes === null) return "Unknown";
	if (bytes === 0) return "0 B";
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	if (bytes < 1024 * 1024 * 1024)
		return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
	return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

/**
 * Get icon name for file type
 */
export function getFileTypeIcon(type: FileType): string {
	switch (type) {
		case "code":
			return "FileCode";
		case "image":
			return "Image";
		case "pdf":
			return "FileText";
		case "docx":
			return "FileText";
		case "markdown":
			return "FileText";
		case "csv":
			return "Table";
		case "text":
			return "FileText";
		case "binary":
			return "File";
		default:
			return "File";
	}
}

/**
 * Get human-readable file type label
 */
export function getFileTypeLabel(type: FileType): string {
	switch (type) {
		case "code":
			return "Code File";
		case "image":
			return "Image";
		case "pdf":
			return "PDF Document";
		case "docx":
			return "Word Document";
		case "markdown":
			return "Markdown";
		case "csv":
			return "Spreadsheet";
		case "text":
			return "Text File";
		case "binary":
			return "Binary File";
		default:
			return "File";
	}
}
