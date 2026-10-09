/**
 * User settings API client.
 *
 * This module provides API functions for managing user-specific settings,
 * including external service configurations like Tavily API keys.
 */

import { runtimeConfig } from "./runtime-config";

export interface ExternalServiceInfo {
  service_name: string;
  is_active: boolean;
  api_key_configured: boolean;
  api_key_masked?: string;
  settings: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  // Dual-tier fields (issue #217)
  service_url?: string;
  auth_type?: string;
  display_name?: string;
  system_default_configured?: boolean;
}

export interface SaveExternalServiceRequest {
  api_key?: string;
  settings?: Record<string, any>;
  // Dual-tier fields (issue #217)
  credentials?: Record<string, string>;
  service_url?: string;
  auth_type?: string;
  display_name?: string;
}

export interface ExternalServiceForNode {
  configured: boolean;
  api_key?: string;
  settings: Record<string, any>;
}

export interface McpServerConfigRequest {
  server_name: string;
  connection_type: "stdio" | "http";
  server_url?: string;
  command?: string;
  args?: string[];
  working_directory?: string;
  environment_variables?: Record<string, string>;
  auth_type:
    | "none"
    | "api_key"
    | "bearer"
    | "oauth2"
    | "oauth_host_identity"
    | "mcp_oauth"
    | "custom";
  auth_credentials?: Record<string, string>;
  timeout_seconds?: number;
  max_retries?: number;
  retry_delay?: number;
  description?: string;
  visibility?: "private" | "shared";
  shared_with_group_ids?: string[];
  ssl_config?: {
    verify?: boolean;
  };
}

export interface McpServerInfo {
  id?: string;
  service_name: string;
  server_name: string;
  connection_type: string;
  server_url?: string;
  command?: string;
  auth_type: string;
  credentials_configured: boolean;
  description?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  config_summary: Record<string, any>;
  visibility: "private" | "shared";
  shared_with_group_ids: string[];
  shared_with_group_names: string[];
  is_template: boolean;
  original_server_id?: string;
  clone_count: number;
  creator_name?: string;
  creator_id?: string;
  is_owned_by_current_user: boolean;
}

export interface McpToolInfo {
  name: string;
  description: string;
}

export interface TestMcpConnectionResponse {
  success: boolean;
  server_name: string;
  tool_count: number;
  tools: McpToolInfo[];
  error?: string;
  connection_type: string;
}

export interface StandardMcpServerConfig {
  type: "stdio" | "http" | "sse";
  command?: string;
  args?: string[];
  env?: Record<string, string>;
  cwd?: string;
  url?: string;
  headers?: Record<string, string>;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  description?: string;
}

export interface ExportMcpServersResponse {
  mcpServers: Record<string, StandardMcpServerConfig>;
}

export interface ImportMcpServersRequest {
  mcpServers: Record<string, StandardMcpServerConfig>;
  overwrite_existing: boolean;
}

export interface ImportMcpServersResponse {
  success: boolean;
  message: string;
  imported_count: number;
  skipped_count: number;
  failed_count: number;
  errors: Array<{ server: string; error: string }>;
}

export interface SaveMcpServerResponse {
  success: boolean;
  message: string;
  server: McpServerInfo;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.name = "ApiError";
  }
}

// ── MCP Integration (Official Provider) Types ──────────────────────────

export interface McpIntegrationSummary {
  provider: string;
  display_name: string;
  is_configured: boolean;
  is_active: boolean;
  has_system_default: boolean;
  has_group_default: boolean;
  group_names: string[];
  tool_count: number | null;
  tool_permissions: Record<string, boolean>;
}

export interface McpIntegrationConfig {
  provider: string;
  display_name: string;
  is_configured: boolean;
  is_active: boolean;
  has_system_default: boolean;
  has_group_default: boolean;
  group_names: string[];
  credentials_configured: boolean;
  settings: Record<string, any>;
  tool_permissions: Record<string, boolean>;
}

export interface SaveMcpIntegrationRequest {
  credentials?: Record<string, string>;
  settings?: Record<string, any>;
  is_active?: boolean;
}

export interface McpIntegrationForWorkflow {
  success: boolean;
  configured: boolean;
  mcp_server_config?: Record<string, any>;
}

class UserSettingsAPI {
  private async getBaseUrl(): Promise<string> {
    return runtimeConfig.getApiBaseUrl();
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const baseUrl = await this.getBaseUrl();

    // Add CSRF token for state-changing requests
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options?.headers as Record<string, string>) || {}),
    };

    // For POST, PUT, PATCH, and DELETE requests, add CSRF token
    if (
      options?.method === "POST" ||
      options?.method === "PUT" ||
      options?.method === "PATCH" ||
      options?.method === "DELETE"
    ) {
      headers["X-CSRF-Token"] = "1"; // Simple token presence check
    }

    const response = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const payload = await response.json();

        // Handle FastAPI validation errors (422) which return detail as an array
        if (Array.isArray(payload.detail)) {
          // Extract validation error messages
          const errorMessages = payload.detail.map((err: any) => {
            // Pydantic v2 error format
            if (err.msg) {
              return err.msg;
            }
            // Fallback to string representation
            return String(err);
          });
          detail = errorMessages.join("; ");
        } else if (payload.detail) {
          // Regular error detail (string)
          detail = payload.detail;
        }
      } catch {
        // Ignore JSON parse errors and fall back to status text
      }
      throw new ApiError(response.status, detail || "Request failed");
    }

    const text = await response.text();
    if (!text) {
      return {} as T;
    }

    try {
      return JSON.parse(text) as T;
    } catch {
      throw new Error("Invalid JSON response");
    }
  }

  /**
   * List all external services configured for the current user.
   */
  async listExternalServices(): Promise<ExternalServiceInfo[]> {
    const data = await this.request<{
      success: boolean;
      services: ExternalServiceInfo[];
    }>("/api/user/settings/external-services");
    return data.services || [];
  }

  /**
   * Get information about a specific external service.
   * Returns null if the service is not configured.
   */
  async getExternalService(
    serviceName: string,
  ): Promise<ExternalServiceInfo | null> {
    try {
      const data = await this.request<ExternalServiceInfo>(
        `/api/user/settings/external-services/${serviceName}`,
      );
      return data;
    } catch (error: any) {
      // Return null if service is not configured (404)
      if (error.status === 404 || error.message?.includes("not configured")) {
        return null;
      }
      throw error;
    }
  }

  /**
   * Save or update external service configuration.
   */
  async saveExternalService(
    serviceName: string,
    request: SaveExternalServiceRequest,
  ): Promise<ExternalServiceInfo> {
    const data = await this.request<{
      success: boolean;
      message: string;
      service: ExternalServiceInfo;
    }>(`/api/user/settings/external-services/${serviceName}`, {
      method: "PUT",
      body: JSON.stringify(request),
    });
    return data.service;
  }

  /**
   * Delete external service configuration.
   */
  async deleteExternalService(serviceName: string): Promise<void> {
    await this.request<{ success: boolean; message: string }>(
      `/api/user/settings/external-services/${serviceName}`,
      { method: "DELETE" },
    );
  }

  /**
   * Get external service configuration for node creation.
   * This returns the decrypted API key for use when creating nodes.
   */
  async getExternalServiceForNode(
    serviceName: string,
  ): Promise<ExternalServiceForNode> {
    const data = await this.request<ExternalServiceForNode>(
      `/api/user/settings/external-services/${serviceName}/for-node`,
    );
    return data;
  }

  /**
   * Convenience method to get Tavily configuration for node creation.
   */
  async getTavilyConfigForNode(): Promise<ExternalServiceForNode> {
    return this.getExternalServiceForNode("tavily");
  }

  /**
   * Convenience method to save Tavily API key.
   */
  async saveTavilyApiKey(apiKey: string): Promise<ExternalServiceInfo> {
    return this.saveExternalService("tavily", {
      api_key: apiKey,
      credentials: { api_key: apiKey },
    });
  }

  /**
   * Convenience method to check if Tavily is configured.
   */
  async isTavilyConfigured(): Promise<boolean> {
    const config = await this.getTavilyConfigForNode();
    return config.configured;
  }

  /**
   * List all MCP servers configured for the current user.
   */
  async listMcpServers(): Promise<McpServerInfo[]> {
    const data = await this.request<{
      success: boolean;
      servers: McpServerInfo[];
    }>("/api/user/settings/mcp-servers");
    return data.servers || [];
  }

  /**
   * Get information about a specific MCP server.
   * Returns null if the server is not configured.
   */
  async getMcpServer(serverName: string): Promise<McpServerInfo | null> {
    try {
      const data = await this.request<McpServerInfo>(
        `/api/user/settings/mcp-servers/${encodeURIComponent(serverName)}`,
      );
      return data;
    } catch (error: any) {
      // Return null if not found (404)
      if (error.message?.includes("not configured")) {
        return null;
      }
      throw error;
    }
  }

  /**
   * Save or update MCP server configuration.
   */
  async saveMcpServer(
    serverName: string,
    config: McpServerConfigRequest,
  ): Promise<McpServerInfo> {
    const data = await this.request<{
      success: boolean;
      message: string;
      server: McpServerInfo;
    }>(`/api/user/settings/mcp-servers/${encodeURIComponent(serverName)}`, {
      method: "PUT",
      body: JSON.stringify(config),
    });
    return data.server;
  }

  /**
   * Toggle MCP server active status.
   */
  async toggleMcpServer(serverName: string): Promise<McpServerInfo> {
    const data = await this.request<SaveMcpServerResponse>(
      `/api/user/settings/mcp-servers/${encodeURIComponent(serverName)}/toggle`,
      { method: "PATCH" },
    );
    return data.server;
  }

  /**
   * Delete MCP server configuration by ID.
   */
  async deleteMcpServer(serverId: string): Promise<void> {
    await this.request<{ success: boolean; message: string }>(
      `/api/user/settings/mcp-servers/by-id/${encodeURIComponent(serverId)}`,
      { method: "DELETE" },
    );
  }

  /**
   * Test MCP server connection without saving configuration.
   * This validates connectivity and retrieves available tools.
   */
  async testMcpConnection(
    config: McpServerConfigRequest,
  ): Promise<TestMcpConnectionResponse> {
    const data = await this.request<TestMcpConnectionResponse>(
      "/api/user/settings/mcp-servers/test-connection",
      {
        method: "POST",
        body: JSON.stringify(config),
      },
    );
    return data;
  }

  /**
   * Export selected MCP servers in standard .mcp.json format.
   * This returns specific servers by their IDs in the format compatible with Anthropic's Claude Code.
   */
  async exportSelectedMcpServers(
    serverIds: string[],
  ): Promise<ExportMcpServersResponse> {
    const data = await this.request<ExportMcpServersResponse>(
      "/api/user/settings/mcp-servers/export-selected",
      {
        method: "POST",
        body: JSON.stringify({ server_ids: serverIds }),
      },
    );
    return data;
  }

  /**
   * Import MCP servers from standard .mcp.json format.
   * This accepts servers in the format compatible with Anthropic's Claude Code.
   */
  async importMcpServers(
    request: ImportMcpServersRequest,
  ): Promise<ImportMcpServersResponse> {
    const data = await this.request<ImportMcpServersResponse>(
      "/api/user/settings/mcp-servers/import",
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    );
    return data;
  }

  /**
   * List all public MCP servers from other users.
   */
  async listPublicMcpServers(): Promise<McpServerInfo[]> {
    const data = await this.request<{
      success: boolean;
      servers: McpServerInfo[];
    }>("/api/user/settings/mcp-servers/public");
    return data.servers || [];
  }

  /**
   * Clone a public MCP server to the current user's account.
   */
  async cloneMcpServer(
    sourceServerId: string,
    newServerName: string,
  ): Promise<McpServerInfo> {
    const data = await this.request<{
      success: boolean;
      message: string;
      server: McpServerInfo;
    }>("/api/user/settings/mcp-servers/clone", {
      method: "POST",
      body: JSON.stringify({
        source_server_id: sourceServerId,
        new_server_name: newServerName,
      }),
    });
    return data.server;
  }

  /**
   * Update MCP server visibility and sharing.
   */
  async updateMcpServerVisibility(
    serverName: string,
    visibility: "private" | "shared",
    sharedWithGroupIds?: string[],
  ): Promise<McpServerInfo> {
    const data = await this.request<{
      success: boolean;
      message: string;
      server: McpServerInfo;
    }>(
      `/api/user/settings/mcp-servers/${encodeURIComponent(serverName)}/visibility`,
      {
        method: "PATCH",
        body: JSON.stringify({
          visibility,
          shared_with_group_ids: sharedWithGroupIds || [],
        }),
      },
    );
    return data.server;
  }

  // --- MCP OAuth Methods ---

  /**
   * Initiate MCP OAuth flow for a server.
   * Returns an authorization URL to open in a popup.
   */
  async initiateMcpOAuth(
    serverUrl: string,
    serverName: string,
  ): Promise<{
    authorization_url: string;
    state: string;
    server_name: string;
  }> {
    return this.request<{
      authorization_url: string;
      state: string;
      server_name: string;
    }>("/api/mcp-oauth/initiate", {
      method: "POST",
      body: JSON.stringify({ server_url: serverUrl, server_name: serverName }),
    });
  }

  /**
   * Get MCP OAuth status for a server.
   */
  async getMcpOAuthStatus(serverName: string): Promise<{
    is_authenticated: boolean;
    has_token: boolean;
    has_client_registration: boolean;
    token_expired: boolean;
    expires_at: string | null;
    scope: string | null;
    server_name: string | null;
  }> {
    return this.request(
      `/api/mcp-oauth/status?server_name=${encodeURIComponent(serverName)}`,
    );
  }

  /**
   * Revoke MCP OAuth access for a server.
   */
  async revokeMcpOAuth(
    serverName: string,
  ): Promise<{ status: string; message: string }> {
    return this.request(
      `/api/mcp-oauth/revoke?server_name=${encodeURIComponent(serverName)}`,
      { method: "DELETE" },
    );
  }

  // --- MCP Integration (Official Provider) Methods ---

  async listMcpIntegrations(): Promise<McpIntegrationSummary[]> {
    const data = await this.request<{
      success: boolean;
      integrations: McpIntegrationSummary[];
    }>("/api/user/settings/mcp-integrations");
    return data.integrations;
  }

  async getMcpIntegration(provider: string): Promise<McpIntegrationConfig> {
    const data = await this.request<{
      success: boolean;
      integration: McpIntegrationConfig;
    }>(`/api/user/settings/mcp-integrations/${encodeURIComponent(provider)}`);
    return data.integration;
  }

  async saveMcpIntegration(
    provider: string,
    request: SaveMcpIntegrationRequest,
  ): Promise<McpIntegrationConfig> {
    const data = await this.request<{
      success: boolean;
      message: string;
      integration: McpIntegrationConfig;
    }>(`/api/user/settings/mcp-integrations/${encodeURIComponent(provider)}`, {
      method: "PUT",
      body: JSON.stringify(request),
    });
    return data.integration;
  }

  async deleteMcpIntegration(provider: string): Promise<void> {
    await this.request(
      `/api/user/settings/mcp-integrations/${encodeURIComponent(provider)}`,
      { method: "DELETE" },
    );
  }

  async toggleMcpIntegration(provider: string): Promise<McpIntegrationConfig> {
    const data = await this.request<{
      success: boolean;
      message: string;
      integration: McpIntegrationConfig;
    }>(
      `/api/user/settings/mcp-integrations/${encodeURIComponent(provider)}/toggle`,
      { method: "PATCH" },
    );
    return data.integration;
  }

  async getMcpIntegrationForWorkflow(
    provider: string,
  ): Promise<McpIntegrationForWorkflow> {
    return this.request<McpIntegrationForWorkflow>(
      `/api/user/settings/mcp-integrations/${encodeURIComponent(provider)}/for-workflow`,
    );
  }
}

export const userSettingsAPI = new UserSettingsAPI();
