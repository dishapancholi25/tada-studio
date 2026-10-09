/**
 * Admin API client for user management.
 *
 * Provides methods for managing users and their group memberships.
 */

import { runtimeConfig } from "./runtime-config";
import type { UserListItem, UserDetail, UsersListResponse } from "@/types/api";

export class ApiError extends Error {
	constructor(
		message: string,
		public status: number,
		public details?: unknown,
	) {
		super(message);
		this.name = "ApiError";
	}
}

/**
 * Get CSRF token for requests.
 * The backend only requires the header to be present, not a specific value.
 */
function getCsrfToken(): string {
	return "1";
}

export class AdminUsersAPI {
	private async getApiBaseUrl(): Promise<string> {
		return await runtimeConfig.getApiBaseUrl();
	}

	/**
	 * List all users with pagination and search.
	 *
	 * @param params - Optional query parameters (limit, offset, search, role)
	 * @returns Promise with paginated users list
	 * @throws ApiError if the request fails
	 */
	async listUsers(params?: {
		limit?: number;
		offset?: number;
		search?: string;
		role?: string;
	}): Promise<UsersListResponse> {
		try {
			const baseUrl = await this.getApiBaseUrl();
			const queryParams = new URLSearchParams();

			if (params?.limit !== undefined) {
				queryParams.append("limit", params.limit.toString());
			}
			if (params?.offset !== undefined) {
				queryParams.append("offset", params.offset.toString());
			}
			if (params?.search) {
				queryParams.append("search", params.search);
			}
			if (params?.role) {
				queryParams.append("role", params.role);
			}

			const url = `${baseUrl}/api/admin/users${queryParams.toString() ? `?${queryParams.toString()}` : ""}`;

			const response = await fetch(url, {
				method: "GET",
				credentials: "include",
				headers: {
					"Content-Type": "application/json",
				},
			});

			if (!response.ok) {
				const error = await response.json().catch(() => ({}));
				throw new ApiError(
					error.detail || "Failed to list users",
					response.status,
					error,
				);
			}

			return await response.json();
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError("Network error while listing users", 0, error);
		}
	}

	/**
	 * Get detailed user information.
	 *
	 * @param userId - The user's ID
	 * @returns Promise with detailed user information
	 * @throws ApiError if the request fails
	 */
	async getUserDetail(userId: string): Promise<UserDetail> {
		try {
			const baseUrl = await this.getApiBaseUrl();
			const response = await fetch(
				`${baseUrl}/api/admin/users/${encodeURIComponent(userId)}`,
				{
					method: "GET",
					credentials: "include",
					headers: {
						"Content-Type": "application/json",
					},
				},
			);

			if (!response.ok) {
				const error = await response.json().catch(() => ({}));
				throw new ApiError(
					error.detail || "Failed to get user detail",
					response.status,
					error,
				);
			}

			return await response.json();
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(
				"Network error while getting user detail",
				0,
				error,
			);
		}
	}

	/**
	 * Update user's group memberships.
	 *
	 * @param userId - The user's ID
	 * @param groupIds - List of group IDs to assign
	 * @returns Promise with success message
	 * @throws ApiError if the request fails
	 */
	async updateUserGroups(userId: string, groupIds: string[]): Promise<void> {
		try {
			const baseUrl = await this.getApiBaseUrl();
			const response = await fetch(
				`${baseUrl}/api/admin/users/${encodeURIComponent(userId)}/groups`,
				{
					method: "PUT",
					credentials: "include",
					headers: {
						"Content-Type": "application/json",
						"X-CSRF-Token": getCsrfToken(),
					},
					body: JSON.stringify({ group_ids: groupIds }),
				},
			);

			if (!response.ok) {
				const error = await response.json().catch(() => ({}));
				throw new ApiError(
					error.detail || "Failed to update user groups",
					response.status,
					error,
				);
			}
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(
				"Network error while updating user groups",
				0,
				error,
			);
		}
	}

	/**
	 * Delete a user permanently.
	 *
	 * @param userId - The user's ID
	 * @returns Promise that resolves on success
	 * @throws ApiError if the request fails
	 */
	async deleteUser(userId: string): Promise<void> {
		try {
			const baseUrl = await this.getApiBaseUrl();
			const response = await fetch(
				`${baseUrl}/api/admin/users/${encodeURIComponent(userId)}`,
				{
					method: "DELETE",
					credentials: "include",
					headers: {
						"Content-Type": "application/json",
						"X-CSRF-Token": getCsrfToken(),
					},
				},
			);

			if (!response.ok) {
				const error = await response.json().catch(() => ({}));
				throw new ApiError(
					error.detail || "Failed to delete user",
					response.status,
					error,
				);
			}
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError("Network error while deleting user", 0, error);
		}
	}

	/**
	 * Update user's role.
	 *
	 * @param userId - The user's ID
	 * @param role - New role ('PENDING', 'USER', or 'ADMIN')
	 * @returns Promise with success message
	 * @throws ApiError if the request fails
	 */
	async updateUserRole(userId: string, role: string): Promise<void> {
		try {
			const baseUrl = await this.getApiBaseUrl();
			const response = await fetch(
				`${baseUrl}/api/admin/users/${encodeURIComponent(userId)}/role`,
				{
					method: "PUT",
					credentials: "include",
					headers: {
						"Content-Type": "application/json",
						"X-CSRF-Token": getCsrfToken(),
					},
					body: JSON.stringify({ role }),
				},
			);

			if (!response.ok) {
				const error = await response.json().catch(() => ({}));
				throw new ApiError(
					error.detail || "Failed to update user role",
					response.status,
					error,
				);
			}
		} catch (error) {
			if (error instanceof ApiError) {
				throw error;
			}
			throw new ApiError(
				"Network error while updating user role",
				0,
				error,
			);
		}
	}
}

// Export singleton instance
export const adminUsersAPI = new AdminUsersAPI();
