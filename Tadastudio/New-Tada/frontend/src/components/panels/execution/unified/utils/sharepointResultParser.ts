/**
 * SharePoint-specific result parsing utilities for MCP execution panel
 */

export interface SharePointSite {
	id: string;
	name: string;
	url: string;
	description: string;
	created: string;
	last_modified: string;
}

export interface SharePointDrive {
	id: string;
	name: string;
	description: string;
	url: string;
	total_size: number;
	used_size: number;
}

export interface SharePointList {
	id: string;
	name: string;
	description: string;
	url: string;
	item_count: boolean | number;
}

export interface SharePointSiteInfo {
	id: string;
	name: string;
	url: string;
	description: string;
	created: string;
	last_modified: string;
	drives: SharePointDrive[];
	drive_count: number;
	lists: SharePointList[];
	list_count: number;
}

export interface SharePointDriveItem {
	id: string;
	name: string;
	type: "file" | "folder";
	size: number;
	url: string;
	last_modified: string;
	created: string;
	mime_type?: string;
	child_count?: number;
	drive_id?: string;
}

export interface SharePointFileContent {
	name: string;
	size: number;
	mime_type: string;
	url: string;
	last_modified: string;
	created_by: string;
	content?: string;
	content_type: "text" | "binary";
	extraction_method?: string;
	page_count?: number;
	sheet_count?: number;
	message?: string;
}

export interface SharePointSearchResult {
	id: string;
	name: string;
	url: string;
	last_modified: string;
	created_by: string;
	site_id: string;
	entity_type: "driveItem" | "listItem";
	size?: number;
	drive_id?: string;
	list_id?: string;
	snippet: string;
}

export interface SharePointSearchFacet {
	value: string;
	count: number;
}

export interface SharePointSearchContentResult {
	results: SharePointSearchResult[];
	total: number;
	count: number;
	page: number;
	page_size: number;
	more_results_available: boolean;
	query: string;
	facets: Record<string, SharePointSearchFacet[]>;
	scope_filtered: boolean;
	scope_drives: string[];
}

// Tool name detection predicates

export function isSharePointListSitesTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("list_sites") || lower === "listsites";
}

export function isSharePointSiteInfoTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("get_site_info") || lower === "getsiteinfo";
}

export function isSharePointDriveItemsTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("list_drive_items") || lower === "listdriveitems";
}

export function isSharePointFileContentTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("get_file_content") || lower === "getfilecontent";
}

export function isSharePointSearchContentTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("search_content") || lower === "searchcontent";
}

export function isSharePointSearchFilesTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("search_files") || lower === "searchfiles";
}

// Parsing functions

export function parseSharePointSites(result: any): SharePointSite[] {
	const sites = result?.sites;
	if (!Array.isArray(sites)) return [];
	return sites
		.filter((s: any) => s && typeof s === "object")
		.map((s: any) => ({
			id: s.id || "",
			name: s.name || "Unknown Site",
			url: s.url || "",
			description: s.description || "",
			created: s.created || "",
			last_modified: s.last_modified || "",
		}));
}

export function parseSharePointSiteInfo(
	result: any,
): SharePointSiteInfo | null {
	if (!result || typeof result !== "object") return null;
	if (!result.id && !result.name) return null;
	return {
		id: result.id || "",
		name: result.name || "",
		url: result.url || "",
		description: result.description || "",
		created: result.created || "",
		last_modified: result.last_modified || "",
		drives: Array.isArray(result.drives) ? result.drives : [],
		drive_count: result.drive_count ?? 0,
		lists: Array.isArray(result.lists) ? result.lists : [],
		list_count: result.list_count ?? 0,
	};
}

export function parseSharePointDriveItems(result: any): SharePointDriveItem[] {
	const items = result?.items;
	if (!Array.isArray(items)) return [];
	return items
		.filter((item: any) => item && typeof item === "object")
		.map((item: any) => ({
			id: item.id || "",
			name: item.name || "",
			type: item.type === "folder" ? ("folder" as const) : ("file" as const),
			size: item.size || 0,
			url: item.url || "",
			last_modified: item.last_modified || "",
			created: item.created || "",
			mime_type: item.mime_type,
			child_count: item.child_count,
			drive_id: item.drive_id,
		}));
}

export function parseSharePointFileContent(
	result: any,
): SharePointFileContent | null {
	if (!result || typeof result !== "object") return null;
	if (!result.name) return null;
	return {
		name: result.name || "",
		size: result.size || 0,
		mime_type: result.mime_type || "",
		url: result.url || "",
		last_modified: result.last_modified || "",
		created_by: result.created_by || "",
		content: result.content,
		content_type: result.content_type || "binary",
		extraction_method: result.extraction_method,
		page_count: result.page_count,
		sheet_count: result.sheet_count,
		message: result.message,
	};
}

// Utility functions

export function formatFileSize(bytes: number): string {
	if (bytes === 0) return "0 B";
	const units = ["B", "KB", "MB", "GB", "TB"];
	const k = 1024;
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	const val = bytes / Math.pow(k, i);
	return `${val < 10 ? val.toFixed(1) : Math.round(val)} ${units[i]}`;
}

export function formatSharePointDate(isoDate: string): string {
	if (!isoDate) return "";
	try {
		const date = new Date(isoDate);
		return date.toLocaleDateString(undefined, {
			year: "numeric",
			month: "short",
			day: "numeric",
		});
	} catch {
		return isoDate;
	}
}

export function looksLikeMarkdown(text: string): boolean {
	if (!text || text.length < 20) return false;
	return /^#{1,6}\s|\*\*|^\s*[-*]\s|^\s*\d+\.\s|```|^\|/m.test(text);
}

export function parseSharePointSearchContent(
	result: any,
): SharePointSearchContentResult | null {
	if (!result || typeof result !== "object") return null;
	// Support both search_content (results[]) and search_files (files[])
	const items = Array.isArray(result.results)
		? result.results
		: Array.isArray(result.files)
			? result.files
			: null;
	if (!items) return null;
	if (result.query === undefined && result.total === undefined) return null;

	return {
		results: items
			.filter((r: any) => r && typeof r === "object")
			.map((r: any) => ({
				id: r.id || "",
				name: r.name || "",
				url: r.url || "",
				last_modified: r.last_modified || "",
				created_by: r.created_by || "",
				site_id: r.site_id || "",
				entity_type:
					r.entity_type === "listItem" ? ("listItem" as const) : ("driveItem" as const),
				size: r.size,
				drive_id: r.drive_id,
				list_id: r.list_id,
				snippet: r.snippet || "",
			})),
		total: result.total ?? 0,
		count: result.count ?? items.length,
		page: result.page ?? 0,
		page_size: result.page_size ?? 10,
		more_results_available: result.more_results_available ?? false,
		query: result.query || "",
		facets: result.facets || {},
		scope_filtered: result.scope_filtered ?? false,
		scope_drives: Array.isArray(result.scope_drives) ? result.scope_drives : [],
	};
}

/**
 * Parse SharePoint search snippet markup into segments for rendering.
 * <c0>text</c0> marks highlighted/matched text.
 * <ddd/> marks truncated content (rendered as ellipsis).
 */
export interface SnippetSegment {
	text: string;
	highlighted: boolean;
}

export function parseSearchSnippet(snippet: string): SnippetSegment[] {
	if (!snippet) return [];

	const normalized = snippet.replace(/<ddd\s*\/>/g, "\u2026");

	const segments: SnippetSegment[] = [];
	const regex = /<c\d+>(.*?)<\/c\d+>/g;
	let lastIndex = 0;
	let match: RegExpExecArray | null;

	while ((match = regex.exec(normalized)) !== null) {
		if (match.index > lastIndex) {
			segments.push({
				text: normalized.slice(lastIndex, match.index),
				highlighted: false,
			});
		}
		segments.push({
			text: match[1],
			highlighted: true,
		});
		lastIndex = match.index + match[0].length;
	}

	if (lastIndex < normalized.length) {
		segments.push({
			text: normalized.slice(lastIndex),
			highlighted: false,
		});
	}

	return segments;
}
