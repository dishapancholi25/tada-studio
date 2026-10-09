"use client";

import React from "react";
import type { PricingLookupResult } from "@/lib/model-deployment-api";
import ModelDeploymentFormContent from "./ModelDeploymentFormContent";
import ModelDeploymentModalFooter from "./ModelDeploymentModalFooter";
import ModelDeploymentModalHeader from "./ModelDeploymentModalHeader";

type ProviderKey = "azure_openai" | "azure_openai_ptu" | "gpu_con" | "openai" | "anthropic";

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
	default_max_tokens?: string;
	default_temperature?: string;
	default_top_p?: string;
}

interface ModelDeploymentModalProps {
	isOpen: boolean;
	isEditing: boolean;
	isSaving: boolean;
	isTesting?: boolean;
	formState: ModelFormState;
	formErrors: FormErrors;
	apiKeyInput: string;
	maskedCredentialPreview: string | null;
	pricingSuggestion: PricingLookupResult | null;
	onClose: () => void;
	onSubmit: () => void;
	onTest?: () => void;
	onInputChange: (field: keyof ModelFormState, value: any) => void;
	onApiKeyChange: (value: string) => void;
	onApplyPricingSuggestion: () => void;
}

export default function ModelDeploymentModal({
	isOpen,
	isEditing,
	isSaving,
	isTesting,
	formState,
	formErrors,
	apiKeyInput,
	maskedCredentialPreview,
	pricingSuggestion,
	onClose,
	onSubmit,
	onTest,
	onInputChange,
	onApiKeyChange,
	onApplyPricingSuggestion,
}: ModelDeploymentModalProps) {
	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 z-[120] flex animate-fadeIn items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
			<div className="max-h-[92vh] w-full max-w-3xl overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]">
				<ModelDeploymentModalHeader isEditing={isEditing} onClose={onClose} />

				<ModelDeploymentFormContent
					formState={formState}
					formErrors={formErrors}
					apiKeyInput={apiKeyInput}
					maskedCredentialPreview={maskedCredentialPreview}
					isEditing={isEditing}
					pricingSuggestion={pricingSuggestion}
					onInputChange={onInputChange}
					onApiKeyChange={onApiKeyChange}
					onApplyPricingSuggestion={onApplyPricingSuggestion}
				/>

				<ModelDeploymentModalFooter
					isEditing={isEditing}
					isSaving={isSaving}
					isTesting={isTesting}
					onClose={onClose}
					onSubmit={onSubmit}
					onTest={onTest}
				/>
			</div>
		</div>
	);
}
