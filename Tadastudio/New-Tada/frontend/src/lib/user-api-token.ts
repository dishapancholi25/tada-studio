/**
 * User API Token (Personal Access Token) management API client
 *
 * This module provides functions to interact with the User API Token endpoints
 * for creating, listing, revoking, and managing user-scoped API tokens.
 */

import { runtimeConfig } from "./runtime-config";

export interface UserAPIToken {
	id: string;
	name: string;
	prefix: string;
	description?: string;
	scopes: string[];
	is_active: boolean;
	created_at: string;
	expires_at?: string;
	last_used_at?: string;
	last_used_ip?: string;
	usage_count: number;
}

export interface CreateTokenRequest {
	name: string;
	scopes?: string[];
	description?: string;
	expires_in_days?: number;
}

export interface CreateTokenResponse {
	success: boolean;
	message: string;
	token: string; // Only shown once!
	token_id: string;
	token_name: string;
	token_prefix: string;
	created_at: string;
	expires_at?: string;
	scopes: string[];
}

export interface ListTokensResponse {
	success: boolean;
	tokens: UserAPIToken[];
	total_count: number;
}

export interface RevokeTokenResponse {
	success: boolean;
	message: string;
	token_id: string;
}

export interface ScopeDefinition {
	scope: string;
	label: string;
	description: string;
	resource: string;
	action: string;
	admin_only: boolean;
}

export interface AvailableScopesResponse {
	scopes: ScopeDefinition[];
	restrict_to_workflow: boolean;
	named_workflow_actions: string[];
}

class UserAPITokenAPI {
	private async getBaseUrl(): Promise<string> {
		return runtimeConfig.getApiBaseUrl();
	}

	private async request<T>(path: string, options?: RequestInit): Promise<T> {
		const baseUrl = await this.getBaseUrl();
		const response = await fetch(`${baseUrl}${path}`, {
			...options,
			headers: {
				"Content-Type": "application/json",
				...(options?.headers || {}),
			},
			credentials: "include", // Important for OAuth2Proxy authentication
		});

		if (!response.ok) {
			let detail = response.statusText;
			try {
				const payload = await response.json();
				detail = payload.detail || payload.message || detail;
			} catch (err) {
				// Ignore JSON parse errors and fall back to status text
			}
			throw new Error(detail || "Request failed");
		}

		const text = await response.text();
		if (!text || text.trim() === "") {
			console.warn("Empty response from API:", path);
			// Return a minimal valid response for list endpoints
			if (path.endsWith("/tokens")) {
				return { success: true, tokens: [], total_count: 0 } as T;
			}
			return {} as T;
		}

		try {
			const data = JSON.parse(text) as T;
			console.debug("API response:", path, data);
			return data;
		} catch (error) {
			console.error("Failed to parse JSON response:", text);
			throw new Error("Invalid JSON response");
		}
	}

	/**
	 * Create a new user API token (Personal Access Token)
	 *
	 * @param request - Token creation request
	 * @returns Token creation response including the plaintext token (only shown once!)
	 *
	 * @example
	 * const response = await userAPITokenService.createToken({
	 *   name: "My CI/CD Token",
	 *   scopes: ["workflow:*"],
	 *   expires_in_days: 90,
	 *   description: "Token for CI/CD pipeline"
	 * });
	 * console.log("Token:", response.token);  // Save this immediately!
	 */
	async createToken(request: CreateTokenRequest): Promise<CreateTokenResponse> {
		return this.request<CreateTokenResponse>("/api/auth/tokens", {
			method: "POST",
			body: JSON.stringify(request),
		});
	}

	/**
	 * List all API tokens for the authenticated user
	 *
	 * @returns List of user's tokens (without plaintext tokens)
	 *
	 * @example
	 * const response = await userAPITokenService.listTokens();
	 * console.log("Total tokens:", response.total_count);
	 * response.tokens.forEach(token => {
	 *   console.log(`${token.name} (${token.prefix}...)`);
	 * });
	 */
	async listTokens(): Promise<ListTokensResponse> {
		return this.request<ListTokensResponse>("/api/auth/tokens");
	}

	/**
	 * Get details of a specific API token
	 *
	 * @param tokenId - Token UUID
	 * @returns Token details
	 *
	 * @example
	 * const token = await userAPITokenService.getToken('token-uuid-here');
	 * console.log(`Token: ${token.name}, Last used: ${token.last_used_at}`);
	 */
	async getToken(tokenId: string): Promise<UserAPIToken> {
		return this.request<UserAPIToken>(`/api/auth/tokens/${tokenId}`);
	}

	/**
	 * Revoke (deactivate) an API token
	 *
	 * @param tokenId - Token UUID to revoke
	 * @returns Revocation confirmation
	 *
	 * @example
	 * const response = await userAPITokenService.revokeToken('token-uuid-here');
	 * console.log(response.message);  // "Token revoked successfully"
	 */
	async revokeToken(tokenId: string): Promise<RevokeTokenResponse> {
		return this.request<RevokeTokenResponse>(`/api/auth/tokens/${tokenId}`, {
			method: "DELETE",
		});
	}

	/**
	 * Update token scopes
	 *
	 * @param tokenId - Token UUID
	 * @param scopes - New list of scopes
	 * @returns Updated token details
	 *
	 * @example
	 * const token = await userAPITokenService.updateTokenScopes(
	 *   'token-uuid-here',
	 *   ['workflow:specific-workflow']
	 * );
	 * console.log("Updated scopes:", token.scopes);
	 */
	async updateTokenScopes(
		tokenId: string,
		scopes: string[],
	): Promise<UserAPIToken> {
		return this.request<UserAPIToken>(`/api/auth/tokens/${tokenId}/scopes`, {
			method: "PUT",
			body: JSON.stringify({ scopes }),
		});
	}

	/**
	 * Get available scopes the authenticated user may assign to their tokens.
	 */
	async getAvailableScopes(): Promise<AvailableScopesResponse> {
		return this.request<AvailableScopesResponse>("/api/auth/available-scopes");
	}
}

/**
 * User API Token management service
 */
export const userAPITokenService = new UserAPITokenAPI();
