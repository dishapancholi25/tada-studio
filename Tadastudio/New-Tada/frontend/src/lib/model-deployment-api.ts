import { runtimeConfig } from "./runtime-config";

/**
 * Error thrown for non-OK API responses. Preserves the HTTP status code so
 * callers can distinguish specific conditions (e.g. 409 default-model
 * conflicts) from generic failures without relying on message string
 * matching alone.
 */
export class ModelDeploymentApiError extends Error {
	status: number;

	constructor(message: string, status: number) {
		super(message);
		this.name = "ModelDeploymentApiError";
		this.status = status;
	}
}

export interface ModelDeployment {
	id: string;
	name: string;
	model_type: "llm" | "embedding";
	provider: string;
	model_name: string;
	display_name?: string;
	description?: string;
	settings: Record<string, any>;
	credentials?: Record<string, string | null> | null;
	has_credentials: boolean;
	is_default: boolean;
	is_active: boolean;
	input_cost_per_million?: number | null;
	output_cost_per_million?: number | null;
	created_at?: string | null;
	updated_at?: string | null;
}
/**
 * Safe, non-sensitive projection of a model deployment used for selection
 * (e.g. workflow builder dropdowns) by non-admin users. Never contains
 * credentials, settings, endpoints, or other sensitive configuration.
 */
export interface ModelDeploymentOption {
	id: string;
	name: string;
	model_type: "llm" | "embedding";
	provider: string;
	model_name: string;
	display_name?: string;
	is_default: boolean;
	is_active: boolean;
	default_temperature?: number | null;
	default_max_tokens?: number | null;
	default_top_p?: number | null;
	default_reasoning_effort?: string | null;
}

export interface ModelDeploymentPayload {
	name: string;
	model_type?: "llm" | "embedding";
	provider: string;
	model_name: string;
	display_name?: string;
	description?: string;
	settings?: Record<string, any>;
	credentials?: Record<string, string>;
	is_default?: boolean;
	input_cost_per_million?: number | null;
	output_cost_per_million?: number | null;
}

export type ModelDeploymentUpdatePayload = Partial<ModelDeploymentPayload> & {
	credentials?: Record<string, string | null>;
	is_active?: boolean;
};

export interface ModelDeploymentTestResult {
	success: boolean;
	data: {
		success: boolean;
		provider?: string;
		model?: string;
		error?: string;
		response?: string;
	};
}

export interface PricingLookupResult {
	input_cost_per_million: number;
	output_cost_per_million: number;
	source_model_name: string;
	litellm_provider: string | null;
}

export interface ModelLimitsResult {
	model: string;
	max_output_tokens: number | null;
	max_input_tokens: number | null;
	supports_reasoning: boolean;
	source_model_name: string;
}

class ModelDeploymentAPI {
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
		});

		if (!response.ok) {
			let detail = response.statusText;
			try {
				const payload = await response.json();
				detail = payload.detail || detail;
			} catch (err) {
				// Ignore JSON parse errors and fall back to status text
			}
			throw new ModelDeploymentApiError(
				detail || "Request failed",
				response.status,
			);
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

	async list(): Promise<ModelDeployment[]> {
		const data = await this.request<{
			success: boolean;
			data: ModelDeployment[];
		}>("/api/model-deployments");
		return data.data || [];
	}

	/**
	 * List active deployments as safe selection options (non-admin safe).
	 * Returns only non-sensitive metadata — no credentials or settings.
	 */
	async listSelectOptions(): Promise<ModelDeploymentOption[]> {
		const data = await this.request<{
			success: boolean;
			data: ModelDeploymentOption[];
		}>("/api/model-deployments/select-options");
		return data.data || [];
	}

	/**
	 * List active embedding deployments as safe selection options
	 * (non-admin safe). Returns only non-sensitive metadata.
	 */
	async listEmbeddingSelectOptions(): Promise<ModelDeploymentOption[]> {
		const data = await this.request<{
			success: boolean;
			data: ModelDeploymentOption[];
		}>("/api/model-deployments/select-options?model_type=embedding");
		return data.data || [];
	}

	async listEmbeddings(): Promise<ModelDeployment[]> {
		const data = await this.request<{
			success: boolean;
			data: ModelDeployment[];
		}>("/api/model-deployments?model_type=embedding");
		return data.data || [];
	}

	async create(payload: ModelDeploymentPayload): Promise<ModelDeployment> {
		const data = await this.request<{
			success: boolean;
			data: ModelDeployment;
		}>("/api/model-deployments", {
			method: "POST",
			body: JSON.stringify(payload),
		});
		return data.data;
	}

	async update(
		id: string,
		payload: ModelDeploymentUpdatePayload,
	): Promise<ModelDeployment> {
		const data = await this.request<{
			success: boolean;
			data: ModelDeployment;
		}>(`/api/model-deployments/${id}`, {
			method: "PUT",
			body: JSON.stringify(payload),
		});
		return data.data;
	}

	async remove(id: string, hardDelete = false): Promise<void> {
		await this.request<{ success: boolean }>(
			`/api/model-deployments/${id}?hard_delete=${hardDelete ? "true" : "false"}`,
			{ method: "DELETE" },
		);
	}

	async test(
		id: string,
		overrides?: Record<string, any>,
	): Promise<ModelDeploymentTestResult> {
		const data = await this.request<ModelDeploymentTestResult>(
			`/api/model-deployments/${id}/test`,
			{
				method: "POST",
				body: JSON.stringify({ overrides: overrides || {} }),
			},
		);
		return data;
	}

	async lookupPricing(
		modelName: string,
	): Promise<PricingLookupResult | null> {
		const data = await this.request<{
			success: boolean;
			data: PricingLookupResult | null;
		}>(
			`/api/model-deployments/pricing-lookup?model=${encodeURIComponent(modelName)}`,
		);
		return data.success ? data.data : null;
	}

	async lookupModelLimits(
		modelName: string,
	): Promise<ModelLimitsResult | null> {
		const data = await this.request<{
			success: boolean;
			data: ModelLimitsResult | null;
		}>(
			`/api/model-deployments/model-limits?model=${encodeURIComponent(modelName)}`,
		);
		return data.success ? data.data : null;
	}
}

export const modelDeploymentAPI = new ModelDeploymentAPI();
