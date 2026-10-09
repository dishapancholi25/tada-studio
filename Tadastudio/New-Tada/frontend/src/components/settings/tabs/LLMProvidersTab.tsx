"use client";

import {
	AlertTriangle,
	Brain,
	CheckCircle2,
	ChevronRight,
	Cloud,
	Copy,
	DollarSign,
	Edit3,
	Globe,
	KeyRound,
	Loader2,
	Plus,
	Server,
	ShieldCheck,
	Sparkles,
	TestTube2,
	Trash2,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Tooltip from "@/components/ui/Tooltip";
import { useAuth } from "@/contexts/AuthContext";
import { useFeatureAccess } from "@/contexts/FeatureAccessContext";
import { useToast } from "@/contexts/ToastContext";
import {
	ModelDeploymentApiError,
	type ModelDeployment,
	type ModelDeploymentPayload,
	type ModelDeploymentUpdatePayload,
	type ModelLimitsResult,
	type PricingLookupResult,
	modelDeploymentAPI,
} from "@/lib/model-deployment-api";
import ModelDeploymentModal from "./ModelDeploymentModal";

type ProviderKey =
	| "azure_openai"
	| "azure_openai_ptu"
	| "gpu_con"
	| "openai"
	| "anthropic";
type PricingSource = "deployment" | "litellm" | "default";

interface ResolvedPricing {
	input_cost_per_million: number;
	output_cost_per_million: number;
	source: PricingSource;
}

const DEFAULT_TOKEN_COSTS: Record<string, { input: number; output: number }> = {
	"gpt-4o": { input: 2.5, output: 10.0 },
	"gpt-4o-latest": { input: 2.5, output: 10.0 },
	"gpt-4o-mini": { input: 0.15, output: 0.6 },
	"gpt-4-turbo": { input: 10.0, output: 30.0 },
	"gpt-4": { input: 30.0, output: 60.0 },
	"gpt-3.5-turbo": { input: 0.5, output: 1.5 },
	"claude-3-opus": { input: 15.0, output: 75.0 },
	"claude-3-sonnet": { input: 3.0, output: 15.0 },
	"claude-3-haiku": { input: 0.25, output: 1.25 },
	// Embedding models (input-only; output mirrors input for simplicity)
	"text-embedding-3-small": { input: 0.02, output: 0.02 },
	"text-embedding-3-large": { input: 0.13, output: 0.13 },
	"text-embedding-ada-002": { input: 0.10, output: 0.10 },
};
const DEFAULT_FALLBACK = { input: 2.5, output: 10.0 };

interface ModelFormState {
	id?: string;
	name: string;
	display_name: string;
	model_type: "llm" | "embedding";
	provider: ProviderKey;
	description: string;
	model_name: string;
	endpoint: string;
	deployment_name: string;
	api_version: string;
	base_url: string;
	token_url: string;
	client_id: string;
	client_secret: string;
	oauth_scope: string;
	x_user_id: string;
	dimensions: string;
	is_default: boolean;
	use_managed_identity: boolean;
	verify_ssl: boolean;
	input_cost_per_million: string;
	output_cost_per_million: string;
	default_temperature: string;
	default_max_tokens: string;
	default_top_p: string;
	default_reasoning_effort: string;
}

interface ProviderDefinition {
	label: string;
	icon: React.JSX.Element;
	accent: string;
	border: string;
}

const providerMeta: Record<ProviderKey, ProviderDefinition> = {
	azure_openai: {
		label: "Azure OpenAI",
		icon: <Cloud className="h-4 w-4 text-sky-600" />,
		accent: "text-sky-700",
		border: "border-slate-200",
	},
	azure_openai_ptu: {
		label: "Azure OpenAI PTU",
		icon: <Server className="h-4 w-4 text-orange-600" />,
		accent: "text-orange-700",
		border: "border-slate-200",
	},
	gpu_con: {
		label: "GPU CON",
		icon: <Server className="h-4 w-4 text-purple-600" />,
		accent: "text-purple-700",
		border: "border-slate-200",
	},
	openai: {
		label: "OpenAI",
		icon: <Globe className="h-4 w-4 text-emerald-700" />,
		accent: "text-emerald-800",
		border: "border-slate-200",
	},
	anthropic: {
		label: "Anthropic",
		icon: <ShieldCheck className="h-4 w-4 text-violet-600" />,
		accent: "text-violet-800",
		border: "border-slate-200",
	},
};

const initialFormState: ModelFormState = {
	name: "",
	display_name: "",
	model_type: "llm",
	provider: "azure_openai",
	description: "",
	model_name: "gpt-4o-latest",
	endpoint: "",
	deployment_name: "gpt-4o-latest",
	api_version: "2024-08-01-preview",
	base_url: "https://api.openai.com/v1",
	token_url: "",
	client_id: "",
	client_secret: "",
	oauth_scope: "CORP",
	x_user_id: "TADAUSER",
	dimensions: "",
	is_default: false,
	use_managed_identity: false,
	verify_ssl: true,
	input_cost_per_million: "",
	output_cost_per_million: "",
	default_temperature: "",
	default_max_tokens: "",
	default_top_p: "",
	default_reasoning_effort: "",
};

export default function LLMProvidersTab(): React.JSX.Element {
	const { showToast } = useToast();
	const { user } = useAuth();
	const { canAccessFeature } = useFeatureAccess();

	const [models, setModels] = useState<ModelDeployment[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	const [isFormOpen, setIsFormOpen] = useState(false);
	const [formState, setFormState] = useState<ModelFormState>(initialFormState);
	const [formErrors, setFormErrors] = useState<Record<string, string>>({});
	const [apiKeyInput, setApiKeyInput] = useState("");
	const [isSaving, setIsSaving] = useState(false);
	const [testingId, setTestingId] = useState<string | null>(null);
	const [pricingSuggestion, setPricingSuggestion] =
		useState<PricingLookupResult | null>(null);
	const [modelLimits, setModelLimits] = useState<ModelLimitsResult | null>(
		null,
	);
	const [pricingMap, setPricingMap] = useState<
		Record<string, ResolvedPricing>
	>({});
	const [pendingDeleteModel, setPendingDeleteModel] =
		useState<ModelDeployment | null>(null);
	const [showDefaultConflict, setShowDefaultConflict] = useState(false);
	const [defaultConflictMessage, setDefaultConflictMessage] = useState("");

	const isEditing = Boolean(formState.id);

	const providerSummary = useMemo(() => {
		const counts = models.reduce(
			(acc, model) => {
				acc.total += 1;
				acc.byProvider[model.provider as ProviderKey] =
					(acc.byProvider[model.provider as ProviderKey] || 0) + 1;
				if (model.is_default) {
					if (model.model_type === "llm") {
						acc.defaultLLM += 1;
					} else if (model.model_type === "embedding") {
						acc.defaultEmbedding += 1;
					}
				}
				return acc;
			},
			{
				total: 0,
				defaultLLM: 0,
				defaultEmbedding: 0,
				byProvider: {} as Record<ProviderKey, number>,
			},
		);

		return counts;
	}, [models]);

	useEffect(() => {
		void loadModels();
	}, []);

	// Debounced pricing + model limits lookup when model_name changes
	useEffect(() => {
		if (!isFormOpen || !formState.model_name.trim()) {
			setPricingSuggestion(null);
			setModelLimits(null);
			return;
		}

		const timer = setTimeout(async () => {
			const modelName = formState.model_name.trim();
			try {
				const [pricingResult, limitsResult] = await Promise.all([
					modelDeploymentAPI.lookupPricing(modelName),
					modelDeploymentAPI.lookupModelLimits(modelName),
				]);
				setPricingSuggestion(pricingResult);
				setModelLimits(limitsResult);
			} catch {
				setPricingSuggestion(null);
				setModelLimits(null);
			}
		}, 500);

		return () => clearTimeout(timer);
	}, [formState.model_name, formState.model_type, isFormOpen]);

	// Resolve pricing for all model cards (LLM and embedding)
	useEffect(() => {
		if (loading || models.length === 0) return;

		const immediateMap: Record<string, ResolvedPricing> = {};
		const modelsNeedingLookup: ModelDeployment[] = [];

		for (const model of models) {
			if (
				model.input_cost_per_million != null &&
				model.output_cost_per_million != null
			) {
				immediateMap[model.id] = {
					input_cost_per_million: model.input_cost_per_million,
					output_cost_per_million: model.output_cost_per_million,
					source: "deployment",
				};
			} else {
				modelsNeedingLookup.push(model);
			}
		}

		if (Object.keys(immediateMap).length > 0) {
			setPricingMap((prev) => ({ ...prev, ...immediateMap }));
		}

		if (modelsNeedingLookup.length === 0) return;

		let cancelled = false;

		const doLookups = async () => {
			const results = await Promise.allSettled(
				modelsNeedingLookup.map(async (model) => {
					const result = await modelDeploymentAPI.lookupPricing(
						model.model_name,
					);
					return { modelId: model.id, modelName: model.model_name, result };
				}),
			);

			if (cancelled) return;

			const asyncMap: Record<string, ResolvedPricing> = {};
			for (const settled of results) {
				if (settled.status === "fulfilled") {
					const { modelId, modelName, result } = settled.value;
					if (result) {
						asyncMap[modelId] = {
							input_cost_per_million: result.input_cost_per_million,
							output_cost_per_million: result.output_cost_per_million,
							source: "litellm",
						};
					} else {
						const fallback =
							DEFAULT_TOKEN_COSTS[modelName.toLowerCase()] ?? DEFAULT_FALLBACK;
						asyncMap[modelId] = {
							input_cost_per_million: fallback.input,
							output_cost_per_million: fallback.output,
							source: "default",
						};
					}
				}
			}

			setPricingMap((prev) => ({ ...prev, ...asyncMap }));
		};

		void doLookups();
		return () => {
			cancelled = true;
		};
	}, [models, loading]);

	const handleApplyPricingSuggestion = useCallback(() => {
		if (!pricingSuggestion) return;
		setFormState((prev) => ({
			...prev,
			input_cost_per_million: String(
				pricingSuggestion.input_cost_per_million,
			),
			output_cost_per_million: String(
				pricingSuggestion.output_cost_per_million,
			),
		}));
	}, [pricingSuggestion]);

	const loadModels = async () => {
		try {
			setLoading(true);
			setError(null);
			setPricingMap({});
			const data = await modelDeploymentAPI.list();
			setModels(data);
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to load model deployments",
			);
		} finally {
			setLoading(false);
		}
	};

	const openCreateForm = () => {
		setFormState({ ...initialFormState });
		setApiKeyInput("");
		setFormErrors({});
		setPricingSuggestion(null);
		setModelLimits(null);
		setIsFormOpen(true);
	};

	const openEditForm = useCallback((model: ModelDeployment) => {
		const settings = model.settings || {};
		setFormState({
			id: model.id,
			name: model.name,
			display_name: model.display_name || model.name,
			model_type: model.model_type || "llm",
			provider: model.provider as ProviderKey,
			description: model.description || "",
			model_name: model.model_name,
			endpoint: settings.endpoint || settings.azure_endpoint || "",
			deployment_name: settings.deployment_name || model.model_name,
			api_version: settings.api_version || initialFormState.api_version,
			base_url:
				settings.base_url || settings.api_base || initialFormState.base_url,
			token_url: settings.token_url || "",
			client_id: settings.client_id || "",
			client_secret: "",
			oauth_scope: settings.oauth_scope || settings.scope || "CORP",
			x_user_id: settings.x_user_id || "TADAUSER",
			is_default: model.is_default,
			use_managed_identity: settings.use_managed_identity || false,
			verify_ssl: settings.verify_ssl !== false,
			input_cost_per_million:
				model.input_cost_per_million != null
					? String(model.input_cost_per_million)
					: "",
			output_cost_per_million:
				model.output_cost_per_million != null
					? String(model.output_cost_per_million)
					: "",
			default_temperature:
				settings.default_temperature != null
					? String(settings.default_temperature)
					: "",
			default_max_tokens:
				settings.default_max_tokens != null
					? String(settings.default_max_tokens)
					: "",
			default_top_p:
				settings.default_top_p != null
					? String(settings.default_top_p)
					: "",
			default_reasoning_effort: settings.default_reasoning_effort || "",
			dimensions: settings.dimensions != null ? String(settings.dimensions) : "",
		});
		setApiKeyInput("");
		setFormErrors({});
		setIsFormOpen(true);
	}, []);

	const openCopyForm = useCallback((model: ModelDeployment) => {
		const settings = model.settings || {};
		setFormState({
			// Don't include the id, so it's treated as a new model
			name: `${model.name} (Copy)`,
			display_name: model.display_name
				? `${model.display_name} (Copy)`
				: `${model.name} (Copy)`,
			model_type: model.model_type || "llm",
			provider: model.provider as ProviderKey,
			description: model.description || "",
			model_name: model.model_name,
			endpoint: settings.endpoint || settings.azure_endpoint || "",
			deployment_name: settings.deployment_name || model.model_name,
			api_version: settings.api_version || initialFormState.api_version,
			base_url:
				settings.base_url || settings.api_base || initialFormState.base_url,
			token_url: settings.token_url || "",
			client_id: settings.client_id || "",
			client_secret: "",
			oauth_scope: settings.oauth_scope || settings.scope || "CORP",
			x_user_id: settings.x_user_id || "TADAUSER",
			is_default: false, // Don't copy the default flag
			use_managed_identity: settings.use_managed_identity || false,
			verify_ssl: settings.verify_ssl !== false,
			input_cost_per_million:
				model.input_cost_per_million != null
					? String(model.input_cost_per_million)
					: "",
			output_cost_per_million:
				model.output_cost_per_million != null
					? String(model.output_cost_per_million)
					: "",
			default_temperature:
				settings.default_temperature != null
					? String(settings.default_temperature)
					: "",
			default_max_tokens:
				settings.default_max_tokens != null
					? String(settings.default_max_tokens)
					: "",
			default_top_p:
				settings.default_top_p != null
					? String(settings.default_top_p)
					: "",
			default_reasoning_effort: settings.default_reasoning_effort || "",
			dimensions: settings.dimensions != null ? String(settings.dimensions) : "",
		});
		setApiKeyInput(""); // User needs to provide API key for the copy
		setFormErrors({});
		setIsFormOpen(true);
	}, []);

	const closeForm = () => {
		if (isSaving) return;
		setIsFormOpen(false);
		setFormErrors({});
		setApiKeyInput("");
		setFormState(initialFormState);
	};

	const handleInputChange = (
		field: keyof ModelFormState,
		value: string | boolean,
	) => {
		setFormState((prev) => ({ ...prev, [field]: value }));
	};

	const validateForm = () => {
		const errors: Record<string, string> = {};

		if (!formState.name.trim()) {
			errors.name = "Name is required";
		} else {
			// Check for duplicate names (only when creating or if name changed during edit)
			const isDuplicate = models.some(
				(m) =>
					m.name.toLowerCase() === formState.name.trim().toLowerCase() &&
					m.id !== formState.id,
			);
			if (isDuplicate) {
				errors.name =
					"A model with this name already exists. Please choose a different name.";
			}
		}

		if (!formState.model_name.trim()) {
			errors.model_name = "Model identifier is required";
		}

		if (formState.provider === "azure_openai") {
			if (!formState.endpoint.trim()) {
				errors.endpoint = "Endpoint is required for Azure deployments";
			}
			if (!formState.api_version.trim()) {
				errors.api_version = "API version is required for Azure deployments";
			}
		}

		if (formState.provider === "azure_openai_ptu" || formState.provider === "gpu_con") {
			if (!formState.endpoint.trim()) {
				errors.endpoint = "Gateway endpoint is required";
			}
			if (!formState.token_url.trim()) {
				errors.token_url = "Token URL is required";
			}
			if (!formState.client_id.trim()) {
				errors.client_id = "Client ID is required";
			}
			if (!isEditing && !formState.client_secret.trim()) {
				errors.client_secret = "Client secret is required";
			}
			if (formState.provider === "azure_openai_ptu") {
				if (!formState.api_version.trim()) {
					errors.api_version = "API version is required for Azure OpenAI PTU";
				}
			}
			if (formState.provider === "gpu_con" && formState.model_type === "embedding") {
				if (!formState.dimensions.trim()) {
					errors.dimensions = "Dimensions is required for GPU CON embedding models";
				} else if (Number.isNaN(Number.parseInt(formState.dimensions.trim(), 10)) || Number.parseInt(formState.dimensions.trim(), 10) <= 0) {
					errors.dimensions = "Dimensions must be a positive integer";
				}
			}
		}

		// API key is optional if using managed identity (Azure only).
		// PTU uses client credentials (validated separately) rather than an API key.
		const isAzureWithManagedIdentity =
			formState.provider === "azure_openai" && formState.use_managed_identity;
		const usesApiKey = formState.provider !== "azure_openai_ptu" && formState.provider !== "gpu_con";
		if (
			!isEditing &&
			usesApiKey &&
			!apiKeyInput.trim() &&
			!isAzureWithManagedIdentity
		) {
			errors.api_key =
				"API key is required (or enable managed identity for Azure)";
		}

		// Validate model parameters against known limits
		if (formState.default_max_tokens) {
			const maxTokens = Number(formState.default_max_tokens);
			if (maxTokens <= 0) {
				errors.default_max_tokens = "Max tokens must be a positive number";
			} else if (modelLimits?.max_output_tokens && maxTokens > modelLimits.max_output_tokens) {
				errors.default_max_tokens =
					`Exceeds model limit of ${modelLimits.max_output_tokens.toLocaleString()} output tokens`;
			}
		}

		if (formState.default_temperature) {
			const temp = Number(formState.default_temperature);
			if (temp < 0 || temp > 2) {
				errors.default_temperature = "Temperature must be between 0 and 2";
			}
		}

		if (formState.default_top_p) {
			const topP = Number(formState.default_top_p);
			if (topP < 0 || topP > 1) {
				errors.default_top_p = "Top P must be between 0 and 1";
			}
		}

		setFormErrors(errors);
		return Object.keys(errors).length === 0;
	};

	const buildPayload = (): ModelDeploymentPayload => {
		const settings: Record<string, any> = {};

		if (formState.provider === "azure_openai") {
			settings.endpoint = formState.endpoint.trim();
			settings.deployment_name = (
				formState.deployment_name || formState.model_name
			).trim();
			settings.api_version = formState.api_version.trim();
			settings.use_managed_identity = formState.use_managed_identity;
		} else if (formState.provider === "azure_openai_ptu") {
			settings.endpoint = formState.endpoint.trim();
			settings.deployment_name = (
				formState.deployment_name || formState.model_name
			).trim();
			settings.api_version = formState.api_version.trim();
			settings.token_url = formState.token_url.trim();
			settings.oauth_scope = formState.oauth_scope.trim() || "CORP";
			settings.x_user_id = formState.x_user_id.trim() || "TADAUSER";
			settings.client_id = formState.client_id.trim();
		} else if (formState.provider === "gpu_con") {
			settings.endpoint = formState.endpoint.trim();
			settings.token_url = formState.token_url.trim();
			settings.oauth_scope = formState.oauth_scope.trim() || "CORP";
			settings.x_user_id = formState.x_user_id.trim() || "TADAUSER";
			settings.client_id = formState.client_id.trim();
			if (formState.model_type === "embedding" && formState.dimensions.trim()) {
				settings.dimensions = Number.parseInt(formState.dimensions.trim(), 10);
			}
		} else if (formState.provider === "openai" && formState.base_url.trim()) {
			settings.base_url = formState.base_url.trim();
		}

		if (formState.provider !== "anthropic") {
			settings.verify_ssl = formState.verify_ssl;
		}

		// Model parameter defaults (LLM only)
		if (formState.model_type === "llm") {
			if (formState.default_temperature) {
				settings.default_temperature = Number.parseFloat(
					formState.default_temperature,
				);
			}
			if (formState.default_max_tokens) {
				settings.default_max_tokens = Number.parseInt(
					formState.default_max_tokens,
					10,
				);
			}
			if (formState.default_top_p) {
				settings.default_top_p = Number.parseFloat(formState.default_top_p);
			}
			if (formState.default_reasoning_effort) {
				settings.default_reasoning_effort =
					formState.default_reasoning_effort;
			}
		}

		const payload: ModelDeploymentPayload = {
			name: formState.name.trim(),
			provider: formState.provider,
			model_name: formState.model_name.trim(),
			model_type: formState.model_type,
			display_name: formState.display_name.trim() || undefined,
			description: formState.description.trim() || undefined,
			settings,
			is_default: formState.is_default,
			input_cost_per_million: formState.input_cost_per_million
				? Number.parseFloat(formState.input_cost_per_million)
				: null,
			output_cost_per_million: formState.output_cost_per_million
				? Number.parseFloat(formState.output_cost_per_million)
				: null,
		};

		if (formState.provider === "azure_openai_ptu" || formState.provider === "gpu_con") {
			if (formState.client_secret.trim()) {
				payload.credentials = {
					client_secret: formState.client_secret.trim(),
					client_id: formState.client_id.trim(),
				};
			}
		} else if (apiKeyInput.trim()) {
			payload.credentials = { api_key: apiKeyInput.trim() };
		}

		return payload;
	};

	const handleSubmit = async () => {
		if (isSaving) return;
		if (!validateForm()) return;

		try {
			setIsSaving(true);
			const payload = buildPayload();

			if (isEditing && formState.id) {
				const updatePayload: ModelDeploymentUpdatePayload = {
					...payload,
					credentials: payload.credentials,
				};
				if (!payload.credentials) {
					delete updatePayload.credentials;
				}
				console.log("[ModelDeployment] UPDATE payload:", {
					id: formState.id,
					provider: updatePayload.provider,
					model_name: updatePayload.model_name,
					settings: updatePayload.settings,
					has_credentials: !!updatePayload.credentials,
					credential_keys: updatePayload.credentials ? Object.keys(updatePayload.credentials) : [],
				});
				await modelDeploymentAPI.update(formState.id, updatePayload);
				showToast("success", "Model deployment updated");
			} else {
				// API key is required unless using Azure with managed identity
				// or Azure OpenAI PTU (which uses client-credentials).
				const isAzureWithManagedIdentity =
					formState.provider === "azure_openai" &&
					formState.use_managed_identity;
				const usesClientCredentials =
					formState.provider === "azure_openai_ptu" ||
					formState.provider === "gpu_con";
				if (
					!payload.credentials &&
					!isAzureWithManagedIdentity &&
					!usesClientCredentials
				) {
					throw new Error("API key is required");
				}
				console.log("[ModelDeployment] CREATE payload:", {
					provider: payload.provider,
					model_name: payload.model_name,
					settings: payload.settings,
					has_credentials: !!payload.credentials,
					credential_keys: payload.credentials ? Object.keys(payload.credentials) : [],
				});
				await modelDeploymentAPI.create(payload);
				showToast("success", "Model deployment added");
			}

			await loadModels();
			closeForm();
		} catch (err) {
			console.error("[ModelDeployment] Save error:", err);
			if (err instanceof ModelDeploymentApiError && err.status === 409) {
				// Backend rejected the request because another deployment of the
				// same model type is already marked as default. Surface a
				// blocking warning (including the conflicting model's name)
				// instead of silently switching the default.
				setDefaultConflictMessage(
					err.message ||
						"Only one model can be set as default for each model type. Please unset the existing default model before selecting a new one.",
				);
				setShowDefaultConflict(true);
				return;
			}
			showToast(
				"error",
				err instanceof Error ? err.message : "Failed to save model deployment",
			);
		} finally {
			setIsSaving(false);
		}
	};

	const handleDelete = useCallback(
		(model: ModelDeployment) => {
			setPendingDeleteModel(model);
		},
		[],
	);

	const handleConfirmDelete = useCallback(
		async () => {
			if (!pendingDeleteModel) return;
			const model = pendingDeleteModel;
			try {
				await modelDeploymentAPI.remove(model.id);
				await loadModels();
				showToast("success", "Model deployment removed");
			} catch (err) {
				showToast(
					"error",
					err instanceof Error
						? err.message
						: "Failed to delete model deployment",
				);
			} finally {
				setPendingDeleteModel(null);
			}
		},
		[loadModels, pendingDeleteModel, showToast],
	);

	const handleTest = useCallback(
		async (model: ModelDeployment) => {
			console.log("[ModelDeployment] TEST request:", {
				id: model.id,
				name: model.name,
				provider: model.provider,
				model_name: model.model_name,
			});
			try {
				setTestingId(model.id);
				const result = await modelDeploymentAPI.test(model.id);
					console.log("[ModelDeployment] TEST response (full):", JSON.stringify(result, null, 2));
					console.log("[ModelDeployment] TEST data:", result.data);
					if (result.data?.success) {
					showToast(
						"success",
						`${model.display_name || model.name} responded successfully`,
					);
				} else {
						console.warn("[ModelDeployment] TEST failed:", result.data?.error);
						showToast("error", result.data?.error || "Test failed");
				}
			} catch (err) {
				console.error("[ModelDeployment] TEST error:", err);
				showToast(
					"error",
					err instanceof Error ? err.message : "Failed to test model",
				);
			} finally {
				setTestingId(null);
			}
		},
		[showToast],
	);

	const handleModalTest = useCallback(async () => {
		if (!formState.id) return;
		console.log("[ModelDeployment] TEST (modal) request:", {
			id: formState.id,
			name: formState.name,
			provider: formState.provider,
			model_name: formState.model_name,
		});
		try {
			setTestingId(formState.id);
			const result = await modelDeploymentAPI.test(formState.id);
				console.log("[ModelDeployment] TEST (modal) response (full):", JSON.stringify(result, null, 2));
				console.log("[ModelDeployment] TEST (modal) data:", result.data);
				if (result.data?.success) {
				showToast(
					"success",
					`${formState.display_name || formState.name} responded successfully`,
				);
			} else {
					console.warn("[ModelDeployment] TEST (modal) failed:", result.data?.error);
					showToast("error", result.data?.error || "Test failed");
			}
		} catch (err) {
			console.error("[ModelDeployment] TEST (modal) error:", err);
			showToast(
				"error",
				err instanceof Error ? err.message : "Failed to test model",
			);
		} finally {
			setTestingId(null);
		}
	}, [formState.id, formState.display_name, formState.name, formState.provider, formState.model_name, showToast]);

	const renderStats = () => (
		<div className="mb-8 grid gap-4 md:grid-cols-3">
			<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				<div className="flex items-center justify-between">
					<span className="text-sm text-slate-600">Configured Models</span>
					<Sparkles className="h-4 w-4 text-orange-600" />
				</div>
				<p className="mt-2 text-2xl font-bold text-slate-900">{providerSummary.total}</p>
			</div>
			<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				<div className="flex items-center justify-between">
					<span className="text-sm text-slate-600">Azure Deployments</span>
					<Cloud className="h-4 w-4 text-sky-600" />
				</div>
				<p className="mt-2 text-2xl font-bold text-slate-900">
					{providerSummary.byProvider.azure_openai || 0}
				</p>
			</div>
			<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				<div className="flex items-center justify-between">
					<span className="text-sm text-slate-600">Default Models</span>
					<CheckCircle2 className="h-4 w-4 text-[#0DA931]" />
				</div>
				<div className="mt-2 space-y-1">
					<div className="flex items-center justify-between">
						<span className="text-sm text-slate-600">LLM:</span>
						<span className="text-lg font-bold text-slate-900">{providerSummary.defaultLLM}</span>
					</div>
					<div className="flex items-center justify-between">
						<span className="text-sm text-slate-600">Embedding:</span>
						<span className="text-lg font-bold text-slate-900">{providerSummary.defaultEmbedding}</span>
					</div>
				</div>
			</div>
		</div>
	);

	const renderModelCard = (model: ModelDeployment) => {
		const meta =
			providerMeta[model.provider as ProviderKey] || providerMeta.azure_openai;
		const settings = model.settings || {};

		return (
			<div
				key={model.id}
				className={`relative flex flex-col gap-4 rounded-[4px] border ${meta.border} bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400 overflow-hidden`}
			>
				<div className="flex items-start justify-between gap-4">
					<div className="flex items-center gap-3">
						<div className="flex items-center justify-center rounded-[4px] border border-slate-200 bg-slate-50 p-2">
							{meta.icon}
						</div>
						<div>
							<div className="flex flex-wrap items-center gap-2">
								<h3 className="text-lg font-semibold text-slate-900">
									{model.display_name || model.name}
								</h3>
								{model.model_type === "embedding" && (
									<span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-1 text-xs font-medium capitalize tracking-wide text-blue-700">
										Embedding
									</span>
								)}
								{model.is_default && (
									<span className="rounded-full border border-orange-200 bg-orange-50 px-2 py-1 text-xs font-medium capitalize tracking-wide text-orange-700">
										Default
									</span>
								)}
							</div>
							<div className={`text-sm ${meta.accent}`}>{meta.label}</div>
						</div>
					</div>
					<div className="flex items-center gap-2">
						<button
							onClick={createTestHandler(model)}
							className="rounded-[4px] border border-slate-200 bg-white p-2 text-slate-600 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
							title="Test connection"
							aria-label="Test connection for this model deployment"
						>
							{testingId === model.id ? (
								<Loader2 className="h-4 w-4 animate-spin text-orange-600" />
							) : (
								<TestTube2 className="h-4 w-4" />
							)}
						</button>
						<button
							onClick={createEditHandler(model)}
							className="rounded-[4px] border border-slate-200 bg-white p-2 text-slate-600 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
							title="Edit deployment"
							aria-label="Edit this model deployment"
						>
							<Edit3 className="h-4 w-4" />
						</button>
						<button
							onClick={createCopyHandler(model)}
							className="rounded-[4px] border border-slate-200 bg-white p-2 text-slate-600 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
							title="Copy deployment"
							aria-label="Copy this model deployment"
						>
							<Copy className="h-4 w-4" />
						</button>
						<button
							onClick={createDeleteHandler(model)}
							className="rounded-[4px] border border-slate-200 bg-white p-2 text-red-600 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-700"
							title="Delete deployment"
							aria-label="Delete this model deployment"
						>
							<Trash2 className="h-4 w-4" />
						</button>
					</div>
				</div>

				{model.description && (
					<p className="text-sm leading-relaxed text-slate-600">{model.description}</p>
				)}

				<div className="grid gap-3 text-sm text-slate-600 min-w-0">
					<div className="flex items-center gap-2 min-w-0">
						<Brain className="h-4 w-4 shrink-0 text-slate-500" />
						<span className="shrink-0 text-xs capitalize tracking-wide text-slate-500">Model</span>
						<ChevronRight className="h-3 w-3 shrink-0 text-slate-400" />
						<span className="truncate text-slate-900">{model.model_name}</span>
					</div>

					{settings.deployment_name && (
						<div className="flex items-center gap-2 min-w-0">
							<Server className="h-4 w-4 shrink-0 text-slate-500" />
							<span className="shrink-0 text-xs capitalize tracking-wide text-slate-500">Deployment</span>
							<ChevronRight className="h-3 w-3 shrink-0 text-slate-400" />
							<span className="truncate text-slate-900">{settings.deployment_name}</span>
						</div>
					)}

					{settings.endpoint && (
						<div className="flex items-center gap-2 min-w-0">
							<Globe className="h-4 w-4 shrink-0 text-slate-500" />
							<span className="shrink-0 text-xs capitalize tracking-wide text-slate-500">Endpoint</span>
							<ChevronRight className="h-3 w-3 shrink-0 text-slate-400" />
							<Tooltip content={settings.endpoint} position="top" display="block">
								<span className="truncate text-slate-900">
									{settings.endpoint}
								</span>
							</Tooltip>
						</div>
					)}

					{settings.api_version && (
						<div className="flex items-center gap-2 min-w-0">
							<KeyRound className="h-4 w-4 shrink-0 text-slate-500" />
							<span className="shrink-0 text-xs capitalize tracking-wide text-slate-500">API Version</span>
							<ChevronRight className="h-3 w-3 shrink-0 text-slate-400" />
							<span className="truncate text-slate-900">{settings.api_version}</span>
						</div>
					)}

					{model.credentials?.api_key && (
						<div className="flex items-center gap-2 min-w-0">
							<KeyRound className="h-4 w-4 shrink-0 text-slate-500" />
							<span className="text-slate-600">API key stored</span>
						</div>
					)}

					{(() => {
						const pricing = pricingMap[model.id];
						return (
							<div className="flex flex-wrap items-center gap-2 min-w-0">
								<DollarSign className="h-4 w-4 shrink-0 text-slate-500" />
								<span className="text-xs capitalize tracking-wide text-slate-500">Pricing</span>
								<ChevronRight className="h-3 w-3 shrink-0 text-slate-400" />
								{pricing ? (
									<>
										<span className="text-slate-900">
											${pricing.input_cost_per_million} in / ${pricing.output_cost_per_million} out per 1M
										</span>
										<span
											className={`rounded-full px-2 py-0.5 text-[10px] font-medium capitalize tracking-wide ${
												pricing.source === "deployment"
													? "border border-[#0DA931] bg-[#F1F8E9] text-[#0DA931]"
													: pricing.source === "litellm"
														? "border border-orange-200 bg-orange-50 text-orange-800"
														: "border border-slate-200 bg-slate-100 text-slate-700"
											}`}
										>
											{pricing.source === "deployment"
												? "Custom"
												: pricing.source === "litellm"
													? "LiteLLM"
													: "Default"}
										</span>
									</>
								) : (
									<span className="flex items-center gap-1.5 text-slate-600">
										<Loader2 className="h-3 w-3 animate-spin text-orange-500" />
										<span className="text-xs">Loading...</span>
									</span>
								)}
							</div>
						);
					})()}
				</div>

				<div className="flex items-center justify-between border-t border-slate-200 pt-2 text-xs text-slate-500">
					<span>
						Created{" "}
						{model.created_at
							? new Date(model.created_at).toLocaleString()
							: "recently"}
					</span>
					{model.updated_at && (
						<span>Updated {new Date(model.updated_at).toLocaleString()}</span>
					)}
				</div>
			</div>
		);
	};

	const maskedCredentialPreview = isEditing
		? (() => {
				const model = models.find((m) => m.id === formState.id);
				if (!model?.credentials) return null;
				if (formState.provider === "azure_openai_ptu" || formState.provider === "gpu_con") {
					return model.credentials.client_secret ? "••••••••" : null;
				}
				return model.credentials.api_key || null;
			})()
		: null;

	// Factory function for test handlers
	const createTestHandler = useCallback(
		(model: ModelDeployment) => () => {
			handleTest(model);
		},
		[handleTest],
	);

	// Factory function for edit handlers
	const createEditHandler = useCallback(
		(model: ModelDeployment) => () => {
			openEditForm(model);
		},
		[openEditForm],
	);

	// Factory function for copy handlers
	const createCopyHandler = useCallback(
		(model: ModelDeployment) => () => {
			openCopyForm(model);
		},
		[openCopyForm],
	);

	// Factory function for delete handlers
	const createDeleteHandler = useCallback(
		(model: ModelDeployment) => () => {
			handleDelete(model);
		},
		[handleDelete],
	);

	if (!canAccessFeature("settings.llm_providers")) {
		return (
			<div className="flex h-96 flex-col items-center justify-center gap-4 p-6">
				<div className="rounded-full border border-slate-200 bg-white p-6 shadow-sm">
					<ShieldCheck className="h-12 w-12 text-orange-600" />
				</div>
				<h3 className="text-xl font-semibold text-slate-900">Admin Access Required</h3>
				<p className="max-w-md text-center text-slate-600">
					This feature is restricted to administrators. Please contact your system administrator to request access.
				</p>
			</div>
		);
	}

	return (
		<div className="p-6">
			<div className="mb-6 flex flex-wrap items-center justify-between gap-4">
				<div className="flex items-center gap-3">
					<div className="flex items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 p-2">
						<Brain className="h-6 w-6 text-orange-600" />
					</div>
					<div>
						<h2 className="text-xl font-semibold tracking-tight text-slate-900">Model Deployments</h2>
						<p className="mt-1 text-sm text-slate-600">
							Configure reusable model endpoints across Azure, OpenAI, and Anthropic providers.
						</p>
					</div>
				</div>

				<Button onClick={openCreateForm} icon={<Plus className="h-4 w-4" />}>
					Add Model
				</Button>
			</div>

			{renderStats()}

			{loading ? (
				<div className="flex items-center gap-3 rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
					<Loader2 className="h-5 w-5 animate-spin text-orange-600" />
					<span className="text-sm text-slate-600">Loading model deployments...</span>
				</div>
			) : error ? (
				<div className="flex items-center gap-3 rounded-[4px] border border-red-200 bg-white p-6">
					<AlertTriangle className="h-5 w-5 text-red-600" />
					<span className="text-sm text-red-800">{error}</span>
				</div>
			) : models.length === 0 ? (
				<div className="flex flex-col items-center justify-center gap-3 rounded-[4px] border border-slate-200 bg-white p-12 text-center shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
					<Sparkles className="h-6 w-6 text-orange-600" />
					<h3 className="text-lg font-semibold text-slate-900">No models configured yet</h3>
					<p className="max-w-md text-sm text-slate-600">
						Add deployments from your preferred LLM providers. Agents will reference models configured here, keeping credentials secure and centrally managed.
					</p>
					<Button onClick={openCreateForm} icon={<Plus className="h-4 w-4" />}>
						Create your first deployment
					</Button>
				</div>
			) : (
				<div className="grid gap-6 lg:grid-cols-2">
					{models.map(renderModelCard)}
				</div>
			)}

			{/* Model Deployment Modal */}
			<ModelDeploymentModal
				isOpen={isFormOpen}
				isEditing={isEditing}
				isSaving={isSaving}
				isTesting={testingId === formState.id}
				formState={formState}
				formErrors={formErrors}
				apiKeyInput={apiKeyInput}
				maskedCredentialPreview={maskedCredentialPreview}
				pricingSuggestion={pricingSuggestion}
				onClose={closeForm}
				onSubmit={handleSubmit}
				onTest={isEditing ? handleModalTest : undefined}
				onInputChange={handleInputChange}
				onApiKeyChange={setApiKeyInput}
				onApplyPricingSuggestion={handleApplyPricingSuggestion}
			/>
			<ConfirmDialog
				isOpen={pendingDeleteModel !== null}
				onClose={() => setPendingDeleteModel(null)}
				onConfirm={handleConfirmDelete}
				title="Delete Model Deployment"
				message={
					pendingDeleteModel
						? `Delete model deployment "${pendingDeleteModel.display_name || pendingDeleteModel.name}"?`
						: ""
				}
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
			<ConfirmDialog
				isOpen={showDefaultConflict}
				onClose={() => setShowDefaultConflict(false)}
				onConfirm={() => setShowDefaultConflict(false)}
				title="Default Model Already Set"
				message={
					defaultConflictMessage ||
					"Only one model can be set as default for each model type. Please unset the existing default model before selecting a new one."
				}
				confirmText="OK"
				variant="warning"
				surface="light"
				hideCancel
			/>
		</div>
	);
}
