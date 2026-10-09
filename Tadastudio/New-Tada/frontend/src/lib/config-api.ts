/**
 * Configuration API client for managing environment settings
 */

import { runtimeConfig } from "./runtime-config";

export interface LLMProviderConfig {
	enabled: boolean;
	api_key?: string;
	endpoint?: string;
	deployment_name?: string;
	api_version?: string;
	base_url?: string;
	model?: string;
	status: "connected" | "not_configured" | "error" | "coming_soon";
}

export interface DatabaseConfig {
	host: string;
	port: string;
	database: string;
	username: string;
	password?: string;
	sslmode: string;
	status: string;
	pool_size?: number;
	max_overflow?: number;
}

export interface ExternalServiceConfig {
	enabled: boolean;
	api_key?: string;
	status: string;
	[key: string]: any;
}

export interface PhoenixServiceConfig {
	enabled: boolean;
	endpoint?: string | null;
	project_name?: string | null;
	ui_url?: string | null;
	api_key?: string | null;
	eval_penalty_enabled?: boolean;
	eval_model_deployment_id?: string | null;
	eval_faithfulness_enabled?: boolean;
	eval_tool_selection_enabled?: boolean;
	eval_llm_judge_enabled?: boolean;
	status: string;
}

export interface McpSecretConfig {
	name: string;
	id: string;
	env_key: string;
	value: string;
}

export interface McpConfig {
	secrets: McpSecretConfig[];
}

export interface SystemConfig {
	version: string;
	environment: string;
	debug_mode: boolean;
	log_level: string;
	timezone: string;
	cloud_provider: "aws" | "azure" | "none";
	performance: {
		enable_caching: boolean;
		cache_ttl_seconds: number;
		max_workers: number;
	};
}

export interface DocumentExtractionConfig {
	provider: "model_ocr" | "tika" | "azure_document_intelligence";
	model_ocr_deployment_id?: string;
	model_ocr_detail?: string;
	tika: {
		server_url: string;
		timeout_seconds?: number;
		enabled: boolean;
		status: string;
	};
	azure_document_intelligence: {
		endpoint: string;
		api_key?: string;
		use_managed_identity: boolean;
		model_id?: string;
		enabled: boolean;
		status: string;
	};
}

export interface EnvironmentConfig {
	llm_providers: {
		azure_openai: LLMProviderConfig;
		openai: LLMProviderConfig;
		anthropic: LLMProviderConfig;
		google_gemini: LLMProviderConfig;
		mistral: LLMProviderConfig;
		cohere: LLMProviderConfig;
	};
	database: {
		postgresql: DatabaseConfig;
		pgvector: any;
		future_databases: any;
	};
	external_services: {
		document_extraction: DocumentExtractionConfig;
		tavily: ExternalServiceConfig;
		langchain: ExternalServiceConfig;
		phoenix?: PhoenixServiceConfig;
		embeddings: { dimensions?: number };
		future_services: any;
	};
	mcp: McpConfig;
	security: any;
	system: SystemConfig;
}

export interface ConnectionTestResult {
	success: boolean;
	status?: string;
	error?: string;
	response?: string;
	response_time_ms?: number;
	version?: string;
	pgvector_enabled?: boolean;
}

export interface ServiceStatus {
	llm_providers: Record<string, { status: string; error?: string }>;
	database: Record<
		string,
		{ status: string; error?: string; response_time_ms?: number }
	>;
	external_services: Record<string, { status: string }>;
}

class ConfigAPI {
	private async getApiBaseUrl(): Promise<string> {
		return await runtimeConfig.getApiBaseUrl();
	}

	/**
	 * Get current environment configuration
	 */
	async getEnvironmentConfig(sanitize = true): Promise<EnvironmentConfig> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(
			`${apiBaseUrl}/api/config/environment?sanitize=${sanitize}`,
			{
				method: "GET",
				headers: {
					"Content-Type": "application/json",
				},
			},
		);

		if (!response.ok) {
			throw new Error(
				`Failed to fetch environment config: ${response.statusText}`,
			);
		}

		const data = await response.json();
		return data.data;
	}

	/**
	 * Update environment configuration
	 */
	async updateEnvironmentConfig(updates: Record<string, any>): Promise<any> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/config/environment`, {
			method: "PUT",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(updates),
		});

		if (!response.ok) {
			throw new Error(
				`Failed to update environment config: ${response.statusText}`,
			);
		}

		return response.json();
	}

	/**
	 * Test connection to a service
	 */
	async testConnection(
		serviceType: "llm" | "database",
		provider?: string,
	): Promise<ConnectionTestResult> {
		const body: any = { service_type: serviceType };
		if (provider) {
			body.provider = provider;
		}

		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/config/test-connection`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(body),
		});

		const data = await response.json();
		return data.data || data;
	}

	/**
	 * Get .env file content
	 */
	async getEnvFileContent(): Promise<string> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/config/env-file`, {
			method: "GET",
			headers: {
				"Content-Type": "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(`Failed to fetch env file: ${response.statusText}`);
		}

		const data = await response.json();
		return data.content;
	}

	/**
	 * Export configuration for backup
	 */
	async exportConfiguration(): Promise<any> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/config/export`, {
			method: "GET",
			headers: {
				"Content-Type": "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(`Failed to export configuration: ${response.statusText}`);
		}

		return response.json();
	}

	/**
	 * Import configuration from backup
	 */
	async importConfiguration(configData: any): Promise<any> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/config/import`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(configData),
		});

		if (!response.ok) {
			throw new Error(`Failed to import configuration: ${response.statusText}`);
		}

		return response.json();
	}

	/**
	 * Get status of all configured services
	 */
	async getServicesStatus(): Promise<ServiceStatus> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/config/services/status`, {
			method: "GET",
			headers: {
				"Content-Type": "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(
				`Failed to fetch services status: ${response.statusText}`,
			);
		}

		const data = await response.json();
		return data.data;
	}

	/**
	 * Get available models for a provider
	 */
	async getAvailableModels(provider: string): Promise<string[]> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(
			`${apiBaseUrl}/api/config/available-models/${provider}`,
			{
				method: "GET",
				headers: {
					"Content-Type": "application/json",
				},
			},
		);

		if (!response.ok) {
			throw new Error(
				`Failed to fetch available models: ${response.statusText}`,
			);
		}

		const data = await response.json();
		return data.models;
	}

	/**
	 * Generate a new encryption key
	 */
	async generateEncryptionKey(): Promise<{ key: string; message: string }> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(
			`${apiBaseUrl}/api/config/generate-encryption-key`,
			{
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
			},
		);

		if (!response.ok) {
			throw new Error(
				`Failed to generate encryption key: ${response.statusText}`,
			);
		}

		const data = await response.json();
		return { key: data.key, message: data.message };
	}

	/**
	 * Get system information
	 */
	async getSystemInfo(): Promise<any> {
		const apiBaseUrl = await this.getApiBaseUrl();
		const response = await fetch(`${apiBaseUrl}/api/config/system-info`, {
			method: "GET",
			headers: {
				"Content-Type": "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(`Failed to fetch system info: ${response.statusText}`);
		}

		const data = await response.json();
		return data.data;
	}

	/**
	 * Resolve a Phoenix project name to its UI URL (using project ID).
	 * Results are cached client-side for 5 minutes.
	 */
	private phoenixProjectUrlCache: Map<string, { url: string | null; ts: number }> = new Map();

	async getPhoenixProjectUrl(projectName: string): Promise<string | null> {
		const cached = this.phoenixProjectUrlCache.get(projectName);
		if (cached && Date.now() - cached.ts < 300_000) return cached.url;

		try {
			const apiBaseUrl = await this.getApiBaseUrl();
			const response = await fetch(
				`${apiBaseUrl}/api/config/phoenix/project-url?project_name=${encodeURIComponent(projectName)}`,
				{ method: "GET", headers: { "Content-Type": "application/json" } },
			);
			if (!response.ok) return null;
			const data = await response.json();
			const url = data.url ?? null;
			this.phoenixProjectUrlCache.set(projectName, { url, ts: Date.now() });
			return url;
		} catch {
			return null;
		}
	}
}

export const configAPI = new ConfigAPI();

// Global authenticated API client
let authenticatedConfigApiClient: any = null;

/**
 * Set the authenticated API client for config operations
 */
export function setAuthenticatedApiClient(apiClient: any) {
	authenticatedConfigApiClient = apiClient;
}
