"use client";

import { ArrowRightLeft, KeyRound, Lightbulb, SlidersHorizontal } from "lucide-react";
import React, { useState } from "react";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import FormTextarea from "@/components/ui/FormTextarea";
import Toggle from "@/components/ui/Toggle";
import type { PricingLookupResult } from "@/lib/model-deployment-api";
import AssignmentList from "@/components/core/guardrails/AssignmentList";
import EffectiveConfigPreview from "@/components/core/guardrails/EffectiveConfigPreview";
import GuardrailsPanel from "@/components/core/guardrails/GuardrailsPanel";
import PolicyPicker from "@/components/core/guardrails/PolicyPicker";

type ProviderKey = "azure_openai" | "azure_openai_ptu" | "gpu_con" | "openai" | "anthropic";

const LIGHT_FIELD =
	"!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15";
const DD_TRIGGER =
	"!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 hover:!border-orange-400";

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

interface FormErrors {
	name?: string;
	model_name?: string;
	endpoint?: string;
	api_version?: string;
	api_key?: string;
	token_url?: string;
	client_id?: string;
	client_secret?: string;
	dimensions?: string;
	default_max_tokens?: string;
	default_temperature?: string;
	default_top_p?: string;
}

interface ModelDeploymentFormContentProps {
	formState: ModelFormState;
	formErrors: FormErrors;
	apiKeyInput: string;
	maskedCredentialPreview: string | null;
	isEditing: boolean;
	pricingSuggestion: PricingLookupResult | null;
	onInputChange: (field: keyof ModelFormState, value: any) => void;
	onApiKeyChange: (value: string) => void;
	onApplyPricingSuggestion: () => void;
}

const providerOptions = [
	{ value: "azure_openai", label: "Azure OpenAI" },
	{ value: "azure_openai_ptu", label: "Azure OpenAI PTU" },
	{ value: "gpu_con", label: "GPU CON (OAuth Gateway)" },
	{ value: "openai", label: "OpenAI" },
	{ value: "anthropic", label: "Anthropic" },
];

const modelTypeOptions = [
	{ value: "llm", label: "Language Model (LLM)" },
	{ value: "embedding", label: "Embedding Model" },
];

const reasoningEffortOptions = [
	{ value: "", label: "Not set" },
	{ value: "low", label: "Low" },
	{ value: "medium", label: "Medium" },
	{ value: "high", label: "High" },
];

const ModelDeploymentFormContent = React.memo(
	function ModelDeploymentFormContent({
		formState,
		formErrors,
		apiKeyInput,
		maskedCredentialPreview,
		isEditing,
		pricingSuggestion,
		onInputChange,
		onApiKeyChange,
		onApplyPricingSuggestion,
	}: ModelDeploymentFormContentProps) {
		const [guardrailsEnabled, setGuardrailsEnabled] = useState(true);
		const [showPolicyPicker, setShowPolicyPicker] = useState(false);
		const [assignmentRefresh, setAssignmentRefresh] = useState(0);

		const hasPricingValues =
			formState.input_cost_per_million !== "" ||
			formState.output_cost_per_million !== "";
		return (
			<div className="max-h-[70vh] space-y-6 overflow-y-auto bg-white px-6 py-6">
				{/* Basic Information */}
				<div className="grid gap-4 md:grid-cols-2">
					<FormInput
						label="Name"
						labelClassName="text-slate-900"
						className={LIGHT_FIELD}
						value={formState.name}
						onChange={(e) => onInputChange("name", e.target.value)}
						error={formErrors.name}
						placeholder="Finance GPT 4o"
					/>

					<FormInput
						label="Display Label"
						labelClassName="text-slate-900"
						className={LIGHT_FIELD}
						value={formState.display_name}
						onChange={(e) => onInputChange("display_name", e.target.value)}
						placeholder="Optional friendly label"
					/>
				</div>

				{/* Model Type and Provider */}
				<div className="grid gap-4 md:grid-cols-2">
					<div className="space-y-2">
						<label
							htmlFor="model-type-select"
							className="block text-sm font-medium text-slate-900"
						>
							Model Type
						</label>
						<Dropdown
							value={formState.model_type}
							onChange={(value) =>
								onInputChange("model_type", value as "llm" | "embedding")
							}
							options={modelTypeOptions}
							menuAppearance="light"
							triggerClassName={DD_TRIGGER}
						/>
					</div>
					<div className="space-y-2">
						<label
							htmlFor="provider-select"
							className="block text-sm font-medium text-slate-900"
						>
							Provider
						</label>
						<Dropdown
							value={formState.provider}
							onChange={(value) =>
								onInputChange("provider", value as ProviderKey)
							}
							options={providerOptions}
							menuAppearance="light"
							triggerClassName={DD_TRIGGER}
						/>
					</div>
				</div>

				{/* Model Identifier */}
				<FormInput
					label="Model Identifier"
					labelClassName="text-slate-900"
					className={LIGHT_FIELD}
					value={formState.model_name}
					onChange={(e) => onInputChange("model_name", e.target.value)}
					error={formErrors.model_name}
					placeholder={
						formState.model_type === "embedding"
							? "text-embedding-3-large"
							: formState.provider === "anthropic"
								? "claude-3-sonnet-20240229"
								: formState.provider === "azure_openai_ptu"
									? "gpt-4.1"
									: "gpt-4o-latest"
					}
				/>

				{/* Description */}
				<FormTextarea
					label="Description"
					labelClassName="text-slate-900"
					className={LIGHT_FIELD}
					hintClassName="text-slate-600"
					value={formState.description}
					onChange={(e) => onInputChange("description", e.target.value)}
					hint="Optional notes about this deployment (environment, usage, owner)."
					rows={3}
				/>

				{/* Azure OpenAI Specific Fields */}
				{formState.provider === "azure_openai" && (
					<>
						<div className="grid gap-4 md:grid-cols-2">
							<FormInput
								label="Endpoint"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.endpoint}
								onChange={(e) => onInputChange("endpoint", e.target.value)}
								error={formErrors.endpoint}
								placeholder="https://your-resource.openai.azure.com/"
							/>
							<FormInput
								label="Deployment Name"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.deployment_name}
								onChange={(e) =>
									onInputChange("deployment_name", e.target.value)
								}
								placeholder="gpt-4o-latest"
							/>
							<FormInput
								label="API Version"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.api_version}
								onChange={(e) => onInputChange("api_version", e.target.value)}
								error={formErrors.api_version}
								placeholder="2024-08-01-preview"
							/>
						</div>

						{/* Managed Identity Toggle for Azure */}
						<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-4">
							<Toggle
								checked={formState.use_managed_identity}
								onChange={(checked) =>
									onInputChange("use_managed_identity", checked)
								}
								label="Use Azure Managed Identity (DefaultAzureCredential)"
								labelClassName="!text-slate-900"
								activeColor="#f97316"
							/>
							<p className="ml-10 mt-2 text-xs text-slate-600">
								When enabled, authentication will use DefaultAzureCredential
								(via &apos;az login&apos; for local dev or managed identity in
								Azure). No API key required.
							</p>
						</div>
					</>
				)}

				{/* OpenAI Specific Fields */}
				{formState.provider === "openai" && (
					<FormInput
						label="Base URL"
						labelClassName="text-slate-900"
						className={LIGHT_FIELD}
						value={formState.base_url}
						onChange={(e) => onInputChange("base_url", e.target.value)}
						placeholder="https://api.openai.com/v1"
					/>
				)}

				{/* Azure OpenAI PTU (gateway + OAuth client credentials) */}
				{formState.provider === "azure_openai_ptu" && (
					<>
						<div className="grid gap-4 md:grid-cols-2">
							<FormInput
								label="Gateway Endpoint"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.endpoint}
								onChange={(e) => onInputChange("endpoint", e.target.value)}
								error={formErrors.endpoint}
								placeholder="https://internal.apigateway.example.com/.../azureopenai_msapi/v2"
							/>
							<FormInput
								label="Deployment Name"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.deployment_name}
								onChange={(e) =>
									onInputChange("deployment_name", e.target.value)
								}
								placeholder="gpt-4.1"
							/>
							<FormInput
								label="API Version"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.api_version}
								onChange={(e) => onInputChange("api_version", e.target.value)}
								error={formErrors.api_version}
								placeholder="2024-08-01-preview"
							/>
							<FormInput
								label="Token URL"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.token_url}
								onChange={(e) => onInputChange("token_url", e.target.value)}
								error={formErrors.token_url}
								placeholder="https://internal.apigateway.example.com/.../oauth2/token"
							/>
							<FormInput
								label="Client ID"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.client_id}
								onChange={(e) => onInputChange("client_id", e.target.value)}
								error={formErrors.client_id}
								placeholder="719c3ffed5467644df6a0bdaa8d28184"
								name="ptu_client_id"
								autoComplete="off"
							/>
							<FormInput
								label={
									isEditing
										? "Client Secret (leave blank to keep existing)"
										: "Client Secret"
								}
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								type="password"
								value={formState.client_secret}
								onChange={(e) =>
									onInputChange("client_secret", e.target.value)
								}
								error={formErrors.client_secret}
								placeholder="••••••••"
								name="ptu_client_secret"
								autoComplete="new-password"
							/>
							<FormInput
								label="OAuth Scope"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.oauth_scope}
								onChange={(e) => onInputChange("oauth_scope", e.target.value)}
								placeholder="CORP"
							/>
							<FormInput
								label="X-USER-ID Header"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.x_user_id}
								onChange={(e) => onInputChange("x_user_id", e.target.value)}
								placeholder="TADAUSER"
							/>
						</div>
						<p className="text-xs text-slate-600">
							Authentication uses an OAuth2 client-credentials token from the
							token URL, sent with the gateway headers (clientid, X-USER-ID).
						</p>
					</>
				)}

				{/* GPU CON (OpenAI-compatible OAuth gateway) */}
				{formState.provider === "gpu_con" && (
					<>
						<div className="grid gap-4 md:grid-cols-2">
							<FormInput
								label="Gateway Endpoint"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.endpoint}
								onChange={(e) => onInputChange("endpoint", e.target.value)}
								error={formErrors.endpoint}
								placeholder="https://internal.apigateway.example.com/.../deployments/model-name"
							/>
							<FormInput
								label="Token URL"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.token_url}
								onChange={(e) => onInputChange("token_url", e.target.value)}
								error={formErrors.token_url}
								placeholder="https://internal.apigateway.example.com/.../oauth2/token"
							/>
							<FormInput
								label="Client ID"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.client_id}
								onChange={(e) => onInputChange("client_id", e.target.value)}
								error={formErrors.client_id}
								placeholder="719c3ffed5467644df6a0bdaa8d28184"
								name="gpu_client_id"
								autoComplete="off"
							/>
							<FormInput
								label={isEditing ? "Client Secret (leave blank to keep existing)" : "Client Secret"}
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								type="password"
								value={formState.client_secret}
								onChange={(e) => onInputChange("client_secret", e.target.value)}
								error={formErrors.client_secret}
								placeholder="••••••••"
								name="gpu_client_secret"
								autoComplete="new-password"
							/>
							<FormInput
								label="OAuth Scope"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.oauth_scope}
								onChange={(e) => onInputChange("oauth_scope", e.target.value)}
								placeholder="CORP"
							/>
							<FormInput
								label="X-USER-ID Header"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								value={formState.x_user_id}
								onChange={(e) => onInputChange("x_user_id", e.target.value)}
								placeholder="TADAUSER"
							/>
							{formState.model_type === "embedding" && (
								<FormInput
									label="Dimensions"
									labelClassName="text-slate-900"
									className={LIGHT_FIELD}
									type="number"
									min="1"
									value={formState.dimensions}
									onChange={(e) => onInputChange("dimensions", e.target.value)}
									error={formErrors.dimensions}
									placeholder="e.g. 1536"
								/>
							)}
						</div>
						<p className="text-xs text-slate-600">
							OpenAI-compatible gateway with OAuth2 client-credentials auth. No API key required.
						</p>
					</>
				)}

				{/* API Key Section */}
				{formState.provider !== "azure_openai_ptu" && formState.provider !== "gpu_con" && (
					<div className="grid gap-4 md:grid-cols-2">
						<FormInput
							label={
								formState.provider === "azure_openai" &&
								formState.use_managed_identity
									? "API Key (optional when using managed identity)"
									: isEditing
										? "API Key (leave blank to keep existing)"
										: "API Key"
							}
							labelClassName="text-slate-900"
							className={LIGHT_FIELD}
							type="password"
							value={apiKeyInput}
							onChange={(e) => onApiKeyChange(e.target.value)}
							error={formErrors.api_key}
							placeholder="sk-..."
							disabled={
								formState.provider === "azure_openai" &&
								formState.use_managed_identity
							}
						/>
						{maskedCredentialPreview && (
							<div className="flex items-center gap-2 text-sm text-slate-600">
								<KeyRound className="h-4 w-4 shrink-0 text-slate-500" />
								<span>Current key: {maskedCredentialPreview}</span>
							</div>
						)}
					</div>
				)}

				{/* SSL Verification Toggle (not supported for Anthropic) */}
				{formState.provider !== "anthropic" && (
					<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-4">
						<Toggle
							checked={formState.verify_ssl}
							onChange={(checked) => onInputChange("verify_ssl", checked)}
							label="Verify SSL Certificates"
							labelClassName="!text-slate-900"
							activeColor="#f97316"
						/>
						{!formState.verify_ssl && (
							<p className="ml-10 mt-2 text-xs text-red-600">
								Security Warning: Disabling SSL verification is not
								recommended for production use and should only be used for
								development/testing with trusted internal endpoints.
							</p>
						)}
					</div>
				)}

				{/* Token Pricing (LLM only) */}
				{formState.model_type === "llm" && (
					<div className="space-y-3">
						<label className="block text-sm font-medium text-slate-900">
							Token Pricing (USD per 1M tokens)
						</label>
						<div className="grid gap-4 md:grid-cols-2">
							<FormInput
								label="Input Cost"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								type="number"
								min="0"
								step="0.01"
								value={formState.input_cost_per_million}
								onChange={(e) =>
									onInputChange("input_cost_per_million", e.target.value)
								}
								placeholder={
									pricingSuggestion
										? `${pricingSuggestion.input_cost_per_million} (LiteLLM)`
										: "e.g. 2.50"
								}
							/>
							<FormInput
								label="Output Cost"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								type="number"
								min="0"
								step="0.01"
								value={formState.output_cost_per_million}
								onChange={(e) =>
									onInputChange("output_cost_per_million", e.target.value)
								}
								placeholder={
									pricingSuggestion
										? `${pricingSuggestion.output_cost_per_million} (LiteLLM)`
										: "e.g. 10.00"
								}
							/>
						</div>
						{pricingSuggestion && !hasPricingValues && (
							<div className="flex flex-wrap items-center gap-2 text-xs text-orange-800">
								<Lightbulb className="h-3.5 w-3.5 shrink-0 text-orange-600" />
								<span>
									Suggested from LiteLLM (
									{pricingSuggestion.source_model_name}): Input $
									{pricingSuggestion.input_cost_per_million}, Output $
									{pricingSuggestion.output_cost_per_million}
								</span>
								<button
									type="button"
									onClick={onApplyPricingSuggestion}
									className="ml-1 underline transition-colors hover:text-slate-950"
								>
									Apply suggestion
								</button>
							</div>
						)}
						{pricingSuggestion &&
							hasPricingValues &&
							(String(pricingSuggestion.input_cost_per_million) !==
								formState.input_cost_per_million ||
								String(pricingSuggestion.output_cost_per_million) !==
									formState.output_cost_per_million) && (
								<div className="flex flex-wrap items-center gap-2 text-xs text-amber-900">
									<ArrowRightLeft className="h-3.5 w-3.5 shrink-0 text-amber-700" />
									<span>
										LiteLLM rate differs: Input $
										{pricingSuggestion.input_cost_per_million}, Output $
										{pricingSuggestion.output_cost_per_million}
									</span>
									<button
										type="button"
										onClick={onApplyPricingSuggestion}
										className="ml-1 underline transition-colors hover:text-amber-950"
									>
										Update to LiteLLM rate
									</button>
								</div>
							)}
						<p className="text-xs text-slate-600">
							Optional. Used for cost estimation in execution traces.
						</p>
					</div>
				)}

				{/* Model Parameter Defaults (LLM only) */}
				{formState.model_type === "llm" && (
					<div className="space-y-3">
						<div className="flex items-center gap-2">
							<SlidersHorizontal className="h-4 w-4 text-slate-500" />
							<label className="block text-sm font-medium text-slate-900">
								Default Model Parameters
							</label>
						</div>
						<p className="text-xs text-slate-600">
							Set default parameter values for agents using this deployment.
							Individual agents can override these in their configuration.
						</p>
						<div className="grid gap-4 md:grid-cols-2">
							<FormInput
								label="Temperature"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								type="number"
								min="0"
								max="2"
								step="0.1"
								value={formState.default_temperature}
								onChange={(e) =>
									onInputChange("default_temperature", e.target.value)
								}
								placeholder="0"
								error={formErrors.default_temperature}
							/>
							<FormInput
								label="Max Tokens"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								type="number"
								min="1"
								step="1"
								value={formState.default_max_tokens}
								onChange={(e) =>
									onInputChange("default_max_tokens", e.target.value)
								}
								placeholder="Unlimited"
								error={formErrors.default_max_tokens}
							/>
							<FormInput
								label="Top P"
								labelClassName="text-slate-900"
								className={LIGHT_FIELD}
								type="number"
								min="0"
								max="1"
								step="0.05"
								value={formState.default_top_p}
								onChange={(e) =>
									onInputChange("default_top_p", e.target.value)
								}
								placeholder="Not set"
								error={formErrors.default_top_p}
							/>
							<div className="space-y-2">
								<label
									htmlFor="reasoning-effort-select"
									className="block text-sm font-medium text-slate-900"
								>
									Reasoning Effort
								</label>
								<Dropdown
									value={formState.default_reasoning_effort}
									onChange={(value) =>
										onInputChange("default_reasoning_effort", value)
									}
									options={reasoningEffortOptions}
									placeholder="Not set"
									menuAppearance="light"
									triggerClassName={DD_TRIGGER}
								/>
								<p className="text-xs text-slate-600">For reasoning models</p>
							</div>
						</div>
					</div>
				)}

				{/* Default Toggle */}
				<div className="flex items-center justify-between">
					<Toggle
						checked={formState.is_default}
						onChange={(checked) => onInputChange("is_default", checked)}
						label={`Mark as default ${formState.model_type === "llm" ? "LLM" : "embedding"} model`}
						labelClassName="!text-slate-900"
						activeColor="#f97316"
					/>
				</div>

				{/* Guardrails — only for LLM models being edited */}
				{formState.model_type === "llm" && isEditing && formState.id && (
					<GuardrailsPanel
						theme="light"
						enabled={guardrailsEnabled}
						onToggle={setGuardrailsEnabled}
						onAssign={() => setShowPolicyPicker(true)}
						description="Enforce safety policies when this model is used by any agent."
					>
						<AssignmentList
							targetType="model"
							targetId={formState.id}
							onOpenPolicyPicker={() => setShowPolicyPicker(true)}
							refreshTrigger={assignmentRefresh}
							hideHeader
						/>
						<EffectiveConfigPreview
							nodeId={formState.id}
						/>
						{showPolicyPicker && (
							<PolicyPicker
								targetType="model"
								targetId={formState.id}
								onAssigned={() => {
									setShowPolicyPicker(false);
									setAssignmentRefresh((c) => c + 1);
								}}
								onClose={() => setShowPolicyPicker(false)}
							/>
						)}
					</GuardrailsPanel>
				)}
			</div>
		);
	},
);

export default ModelDeploymentFormContent;
