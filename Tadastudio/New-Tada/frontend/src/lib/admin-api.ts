/**
 * Admin API client for feature access management.
 *
 * Provides methods for managing feature access control settings.
 */

import { runtimeConfig } from "./runtime-config";

export interface FeatureAccess {
  id: string;
  feature_name: string;
  display_name: string;
  admin_only: boolean;
  description: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface FeatureAccessResponse {
  success: boolean;
  feature?: FeatureAccess;
  features?: FeatureAccess[];
  message?: string;
}

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

export class AdminAPI {
  private async getApiBaseUrl(): Promise<string> {
    return await runtimeConfig.getApiBaseUrl();
  }

  /**
   * List all feature access settings.
   *
   * @returns Promise with all feature access settings
   * @throws ApiError if the request fails
   */
  async listFeatureAccess(): Promise<FeatureAccess[]> {
    try {
      const baseUrl = await this.getApiBaseUrl();
      const response = await fetch(`${baseUrl}/api/admin/feature-access`, {
        method: "GET",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ApiError(
          error.detail || "Failed to list feature access settings",
          response.status,
          error,
        );
      }

      const data: FeatureAccessResponse = await response.json();
      return data.features || [];
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        "Network error while listing feature access settings",
        0,
        error,
      );
    }
  }

  /**
   * Get specific feature access setting.
   *
   * @param featureName - Feature identifier (e.g., "settings.database")
   * @returns Promise with the feature access setting
   * @throws ApiError if the request fails
   */
  async getFeatureAccess(featureName: string): Promise<FeatureAccess> {
    try {
      const baseUrl = await this.getApiBaseUrl();
      const response = await fetch(
        `${baseUrl}/api/admin/feature-access/${encodeURIComponent(featureName)}`,
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
          error.detail || "Failed to get feature access setting",
          response.status,
          error,
        );
      }

      const data: FeatureAccessResponse = await response.json();
      if (!data.feature) {
        throw new ApiError("Feature not found", 404);
      }
      return data.feature;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        "Network error while getting feature access setting",
        0,
        error,
      );
    }
  }

  /**
   * Update feature access setting.
   *
   * @param featureName - Feature identifier (e.g., "settings.database")
   * @param adminOnly - Whether the feature should be admin-only
   * @returns Promise with the updated feature access setting
   * @throws ApiError if the request fails
   */
  async updateFeatureAccess(
    featureName: string,
    adminOnly: boolean,
  ): Promise<FeatureAccess> {
    try {
      const baseUrl = await this.getApiBaseUrl();

      const response = await fetch(
        `${baseUrl}/api/admin/feature-access/${encodeURIComponent(featureName)}`,
        {
          method: "PUT",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": getCsrfToken(),
          },
          body: JSON.stringify({ admin_only: adminOnly }),
        },
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ApiError(
          error.detail || "Failed to update feature access setting",
          response.status,
          error,
        );
      }

      const data: FeatureAccessResponse = await response.json();
      if (!data.feature) {
        throw new ApiError("Update failed", 500);
      }
      return data.feature;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        "Network error while updating feature access setting",
        0,
        error,
      );
    }
  }

  /**
   * Reset all feature access settings to defaults.
   *
   * @returns Promise with success message
   * @throws ApiError if the request fails
   */
  async resetFeatureAccess(): Promise<string> {
    try {
      const baseUrl = await this.getApiBaseUrl();

      const response = await fetch(
        `${baseUrl}/api/admin/feature-access/reset`,
        {
          method: "POST",
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
          error.detail || "Failed to reset feature access settings",
          response.status,
          error,
        );
      }

      const data: FeatureAccessResponse = await response.json();
      return data.message || "Feature access settings reset successfully";
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError(
        "Network error while resetting feature access settings",
        0,
        error,
      );
    }
  }
}

// Export singleton instance
export const adminAPI = new AdminAPI();

// ---------------------------------------------------------------------------
// System External Services API  (issue #217 — org-tier admin-managed services)
// ---------------------------------------------------------------------------

export interface SystemExternalServiceMetadata {
  service_name: string;
  display_name: string | null;
  description: string | null;
  service_url: string | null;
  auth_type: string;
  credential_fields_configured: string[];
  credentials_configured: boolean;
  credentials_masked: Record<string, string>;
  settings: Record<string, unknown>;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface SystemExternalServiceResponse {
  success: boolean;
  service?: SystemExternalServiceMetadata;
  services?: SystemExternalServiceMetadata[];
  message?: string;
}

export interface UpsertSystemExternalServiceRequest {
  display_name?: string;
  description?: string;
  service_url?: string;
  auth_type?: string;
  /** Plaintext credential values. Omit to preserve existing credentials. */
  credentials?: Record<string, string>;
  settings?: Record<string, unknown>;
  is_active?: boolean;
}

export class SystemExternalServicesAPI {
  private async getApiBaseUrl(): Promise<string> {
    return await runtimeConfig.getApiBaseUrl();
  }

  async list(): Promise<SystemExternalServiceMetadata[]> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/external-services`,
      { credentials: "include" },
    );
    if (!response.ok) {
      throw new ApiError(
        "Failed to list system external services",
        response.status,
      );
    }
    const data: SystemExternalServiceResponse = await response.json();
    return data.services ?? [];
  }

  async get(
    serviceName: string,
  ): Promise<SystemExternalServiceMetadata | null> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/external-services/${encodeURIComponent(serviceName)}`,
      { credentials: "include" },
    );
    if (response.status === 404) return null;
    if (!response.ok) {
      throw new ApiError(
        `Failed to get system external service '${serviceName}'`,
        response.status,
      );
    }
    const data: SystemExternalServiceResponse = await response.json();
    return data.service ?? null;
  }

  async upsert(
    serviceName: string,
    body: UpsertSystemExternalServiceRequest,
  ): Promise<SystemExternalServiceMetadata> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/external-services/${encodeURIComponent(serviceName)}`,
      {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new ApiError(
        `Failed to save system external service '${serviceName}': ${detail}`,
        response.status,
      );
    }
    const data: SystemExternalServiceResponse = await response.json();
    if (!data.service) {
      throw new ApiError(
        `Unexpected response saving system external service '${serviceName}'`,
        0,
      );
    }
    return data.service;
  }

  async delete(serviceName: string): Promise<void> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/external-services/${encodeURIComponent(serviceName)}`,
      {
        method: "DELETE",
        credentials: "include",
        headers: { "X-CSRF-Token": getCsrfToken() },
      },
    );
    if (!response.ok) {
      throw new ApiError(
        `Failed to delete system external service '${serviceName}'`,
        response.status,
      );
    }
  }
}

export const systemExternalServicesAPI = new SystemExternalServicesAPI();

// ── MCP Integration (Official Provider) Admin API ──────────────────────

import type {
  McpIntegrationConfig,
  McpIntegrationSummary,
  SaveMcpIntegrationRequest,
} from "./user-settings-api";

export class SystemMcpIntegrationsAPI {
  private async getApiBaseUrl(): Promise<string> {
    return await runtimeConfig.getApiBaseUrl();
  }

  async list(): Promise<McpIntegrationSummary[]> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/mcp-integrations`,
      { credentials: "include" },
    );
    if (!response.ok) {
      throw new ApiError(
        "Failed to list system MCP integrations",
        response.status,
      );
    }
    const data = await response.json();
    return data.integrations ?? [];
  }

  async save(
    provider: string,
    request: SaveMcpIntegrationRequest,
  ): Promise<McpIntegrationConfig> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/mcp-integrations/${encodeURIComponent(provider)}`,
      {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify(request),
      },
    );
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new ApiError(
        `Failed to save system integration '${provider}': ${detail}`,
        response.status,
      );
    }
    const data = await response.json();
    return data.integration;
  }

  async delete(provider: string): Promise<void> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/mcp-integrations/${encodeURIComponent(provider)}`,
      {
        method: "DELETE",
        credentials: "include",
        headers: { "X-CSRF-Token": getCsrfToken() },
      },
    );
    if (!response.ok) {
      throw new ApiError(
        `Failed to delete system integration '${provider}'`,
        response.status,
      );
    }
  }
}

export const systemMcpIntegrationsAPI = new SystemMcpIntegrationsAPI();

// ── Group MCP Configurations API ─────────────────────────────────────────

export interface GroupMcpConfig {
  id: string;
  service_name: string;
  display_name: string | null;
  description: string | null;
  service_url: string | null;
  auth_type: string;
  settings: Record<string, unknown>;
  is_active: boolean;
  credentials_configured: boolean;
  group_ids: string[];
  group_names: string[];
  created_at: string | null;
  updated_at: string | null;
}

export interface GroupMcpConfigResponse {
  success: boolean;
  config?: GroupMcpConfig;
  configs?: GroupMcpConfig[];
  message?: string;
}

export interface CreateGroupMcpConfigRequest {
  service_name: string;
  display_name?: string;
  description?: string;
  service_url?: string;
  auth_type?: string;
  /** Plaintext primary credential (will be encrypted). */
  api_key?: string;
  /** Structured credentials dict (each value encrypted). */
  credentials?: Record<string, string>;
  settings?: Record<string, unknown>;
  group_ids: string[];
  is_active?: boolean;
}

export class GroupMcpConfigsAPI {
  private async getApiBaseUrl(): Promise<string> {
    return await runtimeConfig.getApiBaseUrl();
  }

  async list(): Promise<GroupMcpConfig[]> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/group-mcp-configs`,
      { credentials: "include" },
    );
    if (!response.ok) {
      throw new ApiError("Failed to list group MCP configs", response.status);
    }
    const data: GroupMcpConfigResponse = await response.json();
    return data.configs ?? [];
  }

  async create(body: CreateGroupMcpConfigRequest): Promise<GroupMcpConfig> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/group-mcp-configs`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new ApiError(
        `Failed to create group MCP config: ${detail}`,
        response.status,
      );
    }
    const data: GroupMcpConfigResponse = await response.json();
    if (!data.config) {
      throw new ApiError("Unexpected response creating group MCP config", 0);
    }
    return data.config;
  }

  async update(
    configId: string,
    body: CreateGroupMcpConfigRequest,
  ): Promise<GroupMcpConfig> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/group-mcp-configs/${encodeURIComponent(configId)}`,
      {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify(body),
      },
    );
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new ApiError(
        `Failed to update group MCP config: ${detail}`,
        response.status,
      );
    }
    const data: GroupMcpConfigResponse = await response.json();
    if (!data.config) {
      throw new ApiError("Unexpected response updating group MCP config", 0);
    }
    return data.config;
  }

  async delete(configId: string): Promise<void> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/settings/group-mcp-configs/${encodeURIComponent(configId)}`,
      {
        method: "DELETE",
        credentials: "include",
        headers: { "X-CSRF-Token": getCsrfToken() },
      },
    );
    if (!response.ok) {
      throw new ApiError(
        `Failed to delete group MCP config '${configId}'`,
        response.status,
      );
    }
  }
}

export const groupMcpConfigsAPI = new GroupMcpConfigsAPI();

// ── SSRF / Network Security Policy API ───────────────────────────────────

export interface SSRFPolicy {
  tool_id: string;
  allowed_ip_ranges: string[];
  fixed_ips: string[];
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface SSRFPolicyResponse {
  success: boolean;
  policy?: SSRFPolicy;
  policies?: SSRFPolicy[];
  message?: string;
}

export class SSRFPolicyAPI {
  private async getApiBaseUrl(): Promise<string> {
    return await runtimeConfig.getApiBaseUrl();
  }

  async list(): Promise<SSRFPolicy[]> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(`${baseUrl}/api/admin/ssrf-policies`, {
      credentials: "include",
    });
    if (!response.ok) {
      throw new ApiError("Failed to list SSRF policies", response.status);
    }
    const data: SSRFPolicyResponse = await response.json();
    return data.policies ?? [];
  }

  async get(toolId: string): Promise<SSRFPolicy | null> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/ssrf-policies/${encodeURIComponent(toolId)}`,
      { credentials: "include" },
    );
    if (response.status === 404) return null;
    if (!response.ok) {
      throw new ApiError(
        `Failed to get SSRF policy for '${toolId}'`,
        response.status,
      );
    }
    const data: SSRFPolicyResponse = await response.json();
    return data.policy ?? null;
  }

  async update(
    toolId: string,
    blockedIpRanges: string[],
    enabled: boolean,
  ): Promise<SSRFPolicy> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/ssrf-policies/${encodeURIComponent(toolId)}`,
      {
        method: "PUT",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify({ allowed_ip_ranges: blockedIpRanges, enabled }),
      },
    );
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new ApiError(
        `Failed to update SSRF policy: ${detail}`,
        response.status,
      );
    }
    const data: SSRFPolicyResponse = await response.json();
    if (!data.policy) {
      throw new ApiError("Unexpected response updating SSRF policy", 0);
    }
    return data.policy;
  }

  async addIp(toolId: string, ip: string): Promise<SSRFPolicy> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/ssrf-policies/${encodeURIComponent(toolId)}/ips`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF-Token": getCsrfToken(),
        },
        body: JSON.stringify({ ip }),
      },
    );
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new ApiError(`Failed to add IP: ${detail}`, response.status);
    }
    const data: SSRFPolicyResponse = await response.json();
    if (!data.policy) {
      throw new ApiError("Unexpected response adding IP", 0);
    }
    return data.policy;
  }

  async removeIp(toolId: string, ip: string): Promise<SSRFPolicy> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/ssrf-policies/${encodeURIComponent(toolId)}/ips?ip=${encodeURIComponent(ip)}`,
      {
        method: "DELETE",
        credentials: "include",
        headers: { "X-CSRF-Token": getCsrfToken() },
      },
    );
    if (!response.ok) {
      const detail = await response.text().catch(() => response.statusText);
      throw new ApiError(`Failed to remove IP: ${detail}`, response.status);
    }
    const data: SSRFPolicyResponse = await response.json();
    if (!data.policy) {
      throw new ApiError("Unexpected response removing IP", 0);
    }
    return data.policy;
  }

  async delete(toolId: string): Promise<void> {
    const baseUrl = await this.getApiBaseUrl();
    const response = await fetch(
      `${baseUrl}/api/admin/ssrf-policies/${encodeURIComponent(toolId)}`,
      {
        method: "DELETE",
        credentials: "include",
        headers: { "X-CSRF-Token": getCsrfToken() },
      },
    );
    if (!response.ok) {
      throw new ApiError(
        `Failed to delete SSRF policy '${toolId}'`,
        response.status,
      );
    }
  }
}

export const ssrfPolicyAPI = new SSRFPolicyAPI();
