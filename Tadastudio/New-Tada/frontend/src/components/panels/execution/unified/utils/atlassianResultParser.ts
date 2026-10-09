/**
 * Atlassian-specific result parsing utilities for MCP execution panel
 */

export interface AtlassianResource {
	id: string;
	name: string;
	url: string;
	scopes: string[];
	avatarUrl?: string;
}

export interface JiraIssueResult {
	id: string;
	key: string;
	selfUrl: string;
}

/**
 * Parse accessible Atlassian resources from a list result
 */
export function parseAtlassianResources(result: any): AtlassianResource[] {
	if (!Array.isArray(result)) return [];

	return result
		.filter((item: any) => item && typeof item === "object")
		.map((item: any) => ({
			id: item.id || "",
			name: item.name || "Unknown",
			url: item.url || "",
			scopes: Array.isArray(item.scopes) ? item.scopes : [],
			avatarUrl: item.avatarUrl || undefined,
		}));
}

/**
 * Parse Jira issue creation/fetch result
 */
export function parseJiraIssueResult(result: any): JiraIssueResult | null {
	if (!result || typeof result !== "object") return null;
	if (!result.key && !result.id) return null;

	return {
		id: result.id || "",
		key: result.key || "",
		selfUrl: result.self || "",
	};
}

/**
 * Check if the tool name relates to Jira issue operations
 */
export function isJiraIssueTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return (
		lower.includes("jiraissue") ||
		lower.includes("jira_issue") ||
		lower === "createjiraissue" ||
		lower === "getjiraissue" ||
		lower === "updatejiraissue"
	);
}

/**
 * Check if the tool fetches accessible Atlassian resources
 */
export function isAtlassianResourcesTool(toolName: string): boolean {
	const lower = toolName.toLowerCase();
	return lower.includes("getaccessibleatlassianresources");
}

/**
 * Categorize scopes by product (Confluence vs Jira)
 */
export function categorizeScopes(scopes: string[]): Record<string, string[]> {
	const categories: Record<string, string[]> = {};
	for (const scope of scopes) {
		const parts = scope.split(":");
		const product = parts.length >= 2 ? parts[parts.length - 1] : "other";
		const label = product.charAt(0).toUpperCase() + product.slice(1);
		if (!categories[label]) categories[label] = [];
		categories[label].push(scope);
	}
	return categories;
}
