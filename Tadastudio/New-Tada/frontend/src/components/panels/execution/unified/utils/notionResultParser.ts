/**
 * Notion-specific result parsing utilities for MCP execution panel
 */

export interface NotionSearchResult {
	id: string;
	title: string;
	url: string;
	type: "page" | "database" | "block";
	highlight?: string;
	timestamp?: string;
	icon?: string;
}

export interface NotionPageResult {
	id: string;
	title: string;
	url?: string;
	content?: string;
	properties?: Record<string, any>;
	created_time?: string;
	last_edited_time?: string;
	icon?: string;
	cover?: string;
}

export interface NotionDatabaseResult {
	id: string;
	title: string;
	url?: string;
	properties?: Record<string, { type: string; name: string }>;
	rows?: any[];
}

export type NotionResultType =
	| "search"
	| "page"
	| "database"
	| "block"
	| "list"
	| "raw";

/**
 * Detect the type of Notion result
 */
export function getNotionResultType(result: any): NotionResultType {
	if (!result) return "raw";

	// AI Search / Search results
	if (
		result?.type === "ai_search" ||
		(result?.results && Array.isArray(result.results))
	) {
		return "search";
	}

	// Single page
	if (result?.object === "page" || result?.page_id) {
		return "page";
	}

	// Database
	if (result?.object === "database" || result?.database_id) {
		return "database";
	}

	// Block
	if (result?.object === "block") {
		return "block";
	}

	// List of pages/blocks
	if (
		result?.object === "list" ||
		(Array.isArray(result?.results) && result?.results[0]?.object)
	) {
		return "list";
	}

	return "raw";
}

/**
 * Parse Notion search results into structured format
 */
export function parseNotionSearchResults(result: any): NotionSearchResult[] {
	if (!result?.results || !Array.isArray(result.results)) return [];

	return result.results.map((item: any) => ({
		id: item.id || "",
		title: item.title || "Untitled",
		url: item.url || "",
		type: (item.type || "page") as "page" | "database" | "block",
		highlight: item.highlight || undefined,
		timestamp: item.timestamp || undefined,
		icon: item.icon || undefined,
	}));
}

/**
 * Parse Notion page result
 */
export function parseNotionPageResult(result: any): NotionPageResult | null {
	if (!result) return null;

	// Handle different page result formats
	const page = result?.page || result;

	return {
		id: page.id || "",
		title: extractNotionTitle(page),
		url: page.url || undefined,
		content: page.content || undefined,
		properties: page.properties || undefined,
		created_time: page.created_time || undefined,
		last_edited_time: page.last_edited_time || undefined,
		icon: extractNotionIcon(page.icon),
		cover: page.cover?.external?.url || page.cover?.file?.url || undefined,
	};
}

/**
 * Parse Notion database result
 */
export function parseNotionDatabaseResult(
	result: any,
): NotionDatabaseResult | null {
	if (!result) return null;

	const db = result?.database || result;

	return {
		id: db.id || "",
		title: extractNotionTitle(db),
		url: db.url || undefined,
		properties: db.properties || undefined,
		rows: db.results || db.rows || undefined,
	};
}

/**
 * Extract title from various Notion object formats
 */
function extractNotionTitle(obj: any): string {
	if (!obj) return "Untitled";

	// Direct title string
	if (typeof obj.title === "string") return obj.title;

	// Title array format (rich text)
	if (Array.isArray(obj.title)) {
		return obj.title
			.map((t: any) => t.plain_text || t.text?.content || "")
			.join("");
	}

	// Properties with title
	if (obj.properties?.title) {
		const titleProp = obj.properties.title;
		if (Array.isArray(titleProp.title)) {
			return titleProp.title.map((t: any) => t.plain_text || "").join("");
		}
	}

	// Properties with Name
	if (obj.properties?.Name) {
		const nameProp = obj.properties.Name;
		if (Array.isArray(nameProp.title)) {
			return nameProp.title.map((t: any) => t.plain_text || "").join("");
		}
	}

	return "Untitled";
}

/**
 * Extract icon from Notion icon format
 */
function extractNotionIcon(icon: any): string | undefined {
	if (!icon) return undefined;

	if (icon.type === "emoji") return icon.emoji;
	if (icon.type === "external") return icon.external?.url;
	if (icon.type === "file") return icon.file?.url;

	return undefined;
}

/**
 * Format Notion timestamp to relative time
 */
export function formatNotionTimestamp(timestamp: string): string {
	if (!timestamp) return "";

	const date = new Date(timestamp);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

	if (diffDays === 0) return "Today";
	if (diffDays === 1) return "Yesterday";
	if (diffDays < 7) return `${diffDays} days ago`;
	if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
	if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;

	return `${Math.floor(diffDays / 365)} years ago`;
}
