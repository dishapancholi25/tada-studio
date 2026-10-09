/**
 * OneDrive-specific result parsing utilities for MCP execution panel
 */

// Re-export shared utilities from SharePoint parser (DRY)
export {
	formatFileSize,
	formatSharePointDate,
	looksLikeMarkdown,
} from "./sharepointResultParser";

export interface OneDriveItem {
	id: string;
	name: string;
	type: "file" | "folder";
	size: number;
	url: string;
	last_modified: string;
	created: string;
	etag: string;
	drive_id: string;
	mime_type?: string;
	child_count?: number;
}

export interface OneDriveDrive {
	id: string;
	name: string;
	drive_type: string;
	total: number;
	used: number;
	url: string;
}

export interface OneDriveFileContent {
	name: string;
	size: number;
	mime_type: string;
	url: string;
	last_modified: string;
	content?: string;
	content_type: "text" | "binary";
	extraction_method?: string;
	page_count?: number;
	sheet_count?: number;
	message?: string;
}

// Tool name detection predicates
// Note: these only run inside the `provider === "onedrive"` dispatch block,
// so overlapping names like "list_drive_items" won't collide with SharePoint.

export function isOneDriveItemsListTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return (
		lower.includes("find_file") ||
		lower.includes("find_folder") ||
		lower.includes("list_drive_items")
	);
}

export function isOneDriveDriveListTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("list_drives") && !lower.includes("items");
}

export function isOneDriveFileContentTool(toolName: string): boolean {
	return toolName.toLowerCase().includes("get_file_content");
}

export function isOneDriveMetadataTool(toolName: string): boolean {
	return toolName.toLowerCase().includes("get_item_metadata");
}

// Parsing functions

export function parseOneDriveItems(result: any): {
	items: OneDriveItem[];
	query?: string;
} {
	if (!result || typeof result !== "object") return { items: [] };
	const raw = result?.items;
	if (!Array.isArray(raw)) return { items: [], query: result?.query };
	const items: OneDriveItem[] = raw
		.filter((item: any) => item && typeof item === "object")
		.map((item: any) => ({
			id: item.id || "",
			name: item.name || "",
			type: item.type === "folder" ? ("folder" as const) : ("file" as const),
			size: item.size || 0,
			url: item.url || "",
			last_modified: item.last_modified || "",
			created: item.created || "",
			etag: item.etag || "",
			drive_id: item.drive_id || "",
			mime_type: item.mime_type,
			child_count: item.child_count,
		}));
	return { items, query: result?.query };
}

export function parseOneDriveDrives(result: any): OneDriveDrive[] {
	const raw = result?.drives;
	if (!Array.isArray(raw)) return [];
	return raw
		.filter((d: any) => d && typeof d === "object")
		.map((d: any) => ({
			id: d.id || "",
			name: d.name || "Unknown Drive",
			drive_type: d.drive_type || d.driveType || "",
			total: d.total || d.quota?.total || 0,
			used: d.used || d.quota?.used || 0,
			url: d.url || d.webUrl || "",
		}));
}

export function parseOneDriveFileContent(
	result: any,
): OneDriveFileContent | null {
	if (!result || typeof result !== "object") return null;
	if (!result.name) return null;
	return {
		name: result.name || "",
		size: result.size || 0,
		mime_type: result.mime_type || "",
		url: result.url || "",
		last_modified: result.last_modified || "",
		content: result.content,
		content_type: result.content_type || "binary",
		extraction_method: result.extraction_method,
		page_count: result.page_count,
		sheet_count: result.sheet_count,
		message: result.message,
	};
}

export function parseOneDriveItemMetadata(result: any): OneDriveItem | null {
	if (!result || typeof result !== "object") return null;
	if (!result.id && !result.name) return null;
	return {
		id: result.id || "",
		name: result.name || "",
		type: result.type === "folder" ? ("folder" as const) : ("file" as const),
		size: result.size || 0,
		url: result.url || "",
		last_modified: result.last_modified || "",
		created: result.created || "",
		etag: result.etag || "",
		drive_id: result.drive_id || "",
		mime_type: result.mime_type,
		child_count: result.child_count,
	};
}
