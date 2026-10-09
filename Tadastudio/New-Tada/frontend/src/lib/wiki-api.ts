import { runtimeConfig } from "./runtime-config";

// ── Response Types ──────────────────────────────────────────────────────

export interface WikiPageResponse {
	id: string;
	slug: string;
	title: string;
	content: string;
	parent_id: string | null;
	order_index: number;
	is_published: boolean;
	tags: string[] | null;
	created_by: string | null;
	updated_by: string | null;
	created_at: string;
	updated_at: string | null;
	version: number;
}

export interface WikiPageListItem {
	id: string;
	slug: string;
	title: string;
	parent_id: string | null;
	order_index: number;
	is_published: boolean;
	tags: string[] | null;
	created_at: string;
	updated_at: string | null;
}

export interface WikiRevision {
	id: string;
	page_id: string;
	title: string;
	content: string;
	version: number;
	created_by: string | null;
	change_summary: string | null;
	created_at: string;
}

export interface WikiTreeNode {
	id: string;
	slug: string;
	title: string;
	parent_id: string | null;
	order_index: number;
	children: WikiTreeNode[];
}

// ── Request Types ───────────────────────────────────────────────────────

export interface WikiPageCreate {
	title: string;
	content?: string;
	slug?: string;
	parent_id?: string;
	tags?: string[];
	is_published?: boolean;
}

export interface WikiPageUpdate {
	title?: string;
	content?: string;
	parent_id?: string;
	tags?: string[];
	is_published?: boolean;
	change_summary?: string;
}

export interface WikiImageUploadResponse {
	id: string;
	url: string;
}

// ── Error ───────────────────────────────────────────────────────────────

export class WikiApiError extends Error {
	status: number;
	detail: string;

	constructor(status: number, detail: string) {
		super(detail);
		this.status = status;
		this.detail = detail;
		this.name = "WikiApiError";
	}
}

// ── Service ─────────────────────────────────────────────────────────────

class WikiApi {
	private async getBaseUrl(): Promise<string> {
		return runtimeConfig.getApiBaseUrl();
	}

	private async handleResponse<T>(response: Response): Promise<T> {
		if (!response.ok) {
			let detail = response.statusText;
			try {
				const payload = await response.json();
				if (Array.isArray(payload.detail)) {
					detail = payload.detail
						.map((err: { msg?: string }) => err.msg ?? String(err))
						.join("; ");
				} else if (payload.detail) {
					detail = payload.detail;
				}
			} catch {
				// Fall back to statusText
			}
			throw new WikiApiError(response.status, detail || "Request failed");
		}

		const text = await response.text();
		if (!text) return {} as T;

		try {
			return JSON.parse(text) as T;
		} catch {
			throw new Error("Invalid JSON response");
		}
	}

	private async request<T>(path: string, options?: RequestInit): Promise<T> {
		const baseUrl = await this.getBaseUrl();

		const headers: Record<string, string> = {
			"Content-Type": "application/json",
			...((options?.headers as Record<string, string>) || {}),
		};

		if (
			options?.method === "POST" ||
			options?.method === "PUT" ||
			options?.method === "PATCH" ||
			options?.method === "DELETE"
		) {
			headers["X-CSRF-Token"] = "1";
		}

		const response = await fetch(`${baseUrl}${path}`, {
			...options,
			headers,
		});

		return this.handleResponse<T>(response);
	}

	private async uploadFormData<T>(
		path: string,
		formData: FormData,
	): Promise<T> {
		const baseUrl = await this.getBaseUrl();

		const response = await fetch(`${baseUrl}${path}`, {
			method: "POST",
			headers: { "X-CSRF-Token": "1" },
			body: formData,
		});

		return this.handleResponse<T>(response);
	}

	// ── Pages ─────────────────────────────────────────────────────────

	async listPages(
		options?: {
			includeUnpublished?: boolean;
			parentId?: string;
			tag?: string;
		},
	): Promise<WikiPageListItem[]> {
		const params = new URLSearchParams();
		if (options?.includeUnpublished)
			params.set("include_unpublished", "true");
		if (options?.parentId) params.set("parent_id", options.parentId);
		if (options?.tag) params.set("tag", options.tag);
		const qs = params.toString();
		return this.request<WikiPageListItem[]>(
			`/api/wiki/pages${qs ? `?${qs}` : ""}`,
		);
	}

	async getPage(slug: string): Promise<WikiPageResponse> {
		return this.request<WikiPageResponse>(
			`/api/wiki/pages/${encodeURIComponent(slug)}`,
		);
	}

	async createPage(data: WikiPageCreate): Promise<WikiPageResponse> {
		return this.request<WikiPageResponse>("/api/wiki/pages", {
			method: "POST",
			body: JSON.stringify(data),
		});
	}

	async updatePage(
		slug: string,
		data: WikiPageUpdate,
	): Promise<WikiPageResponse> {
		return this.request<WikiPageResponse>(
			`/api/wiki/pages/${encodeURIComponent(slug)}`,
			{
				method: "PUT",
				body: JSON.stringify(data),
			},
		);
	}

	async deletePage(slug: string): Promise<void> {
		await this.request<{ success: boolean; message: string }>(
			`/api/wiki/pages/${encodeURIComponent(slug)}`,
			{ method: "DELETE" },
		);
	}

	// ── Revisions ─────────────────────────────────────────────────────

	async getRevisions(slug: string): Promise<WikiRevision[]> {
		return this.request<WikiRevision[]>(
			`/api/wiki/pages/${encodeURIComponent(slug)}/revisions`,
		);
	}

	async restoreRevision(
		slug: string,
		version: number,
	): Promise<WikiPageResponse> {
		return this.request<WikiPageResponse>(
			`/api/wiki/pages/${encodeURIComponent(slug)}/restore/${version}`,
			{ method: "POST" },
		);
	}

	// ── Tree & Search ─────────────────────────────────────────────────

	async getTree(): Promise<WikiTreeNode[]> {
		return this.request<WikiTreeNode[]>("/api/wiki/tree");
	}

	async searchPages(
		query: string,
		options?: { limit?: number },
	): Promise<WikiPageListItem[]> {
		const params = new URLSearchParams();
		params.set("q", query);
		if (options?.limit) params.set("limit", String(options.limit));
		return this.request<WikiPageListItem[]>(
			`/api/wiki/search?${params.toString()}`,
		);
	}

	// ── Images ────────────────────────────────────────────────────────

	async uploadImage(file: File): Promise<WikiImageUploadResponse> {
		const formData = new FormData();
		formData.append("file", file);
		return this.uploadFormData<WikiImageUploadResponse>(
			"/api/wiki/images",
			formData,
		);
	}
}

export const wikiApi = new WikiApi();
