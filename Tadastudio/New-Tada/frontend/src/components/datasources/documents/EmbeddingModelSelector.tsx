"use client";

import { AlertTriangle, Settings, Sparkles } from "lucide-react";
import Button from "@/components/ui/Button";
import Dropdown from "@/components/ui/Dropdown";

export interface EmbeddingModel {
	id: string;
	name: string;
	display_name?: string;
	provider: string;
	model_name: string;
	is_default?: boolean;
	settings?: {
		use_managed_identity?: boolean;
	};
}

interface EmbeddingModelSelectorProps {
	models: EmbeddingModel[];
	selectedModel: string | null;
	onModelChange: (modelId: string) => void;
	loading?: boolean;
	onNavigateToSettings: () => void;
	compact?: boolean;
	locked?: boolean;
}

export default function EmbeddingModelSelector({
	models,
	selectedModel,
	onModelChange,
	loading,
	onNavigateToSettings,
	compact = false,
	locked = false,
}: EmbeddingModelSelectorProps) {
	const hasModels = models.length > 0;

	if (loading) {
		return null;
	}

	const modelOptions = models.map((model) => {
		const usesManagedIdentity = model.settings?.use_managed_identity || false;
		const providerLabel =
			model.provider === "azure_openai"
				? "Azure"
				: model.provider === "openai"
					? "OpenAI"
					: model.provider;
		const badges = [];
		if (model.is_default) badges.push("Default");
		if (usesManagedIdentity) badges.push("Managed Identity");

		return {
			value: model.id,
			label: model.display_name || model.name,
			description: `${providerLabel} • ${model.model_name}${badges.length > 0 ? " • " + badges.join(" • ") : ""}`,
		};
	});

	// Compact mode: single row with icon + dropdown
	if (compact && hasModels) {
		return (
			<div
				className="flex items-start gap-3 rounded-xl border border-orange-300 bg-white px-4 py-3 shadow-sm"
				style={{ boxShadow: undefined }}
			>
				<Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-orange-600" />
				<div className="flex-1 min-w-0 space-y-1">
					<Dropdown
						value={selectedModel || ""}
						onChange={locked ? () => {} : onModelChange}
						options={modelOptions}
						placeholder="Select embedding model"
						disabled={locked}
						menuAppearance="light"
					/>
					{locked && (
						<p className="text-xs text-amber-700">
							Locked — all documents must use the same model to ensure consistent search results.
						</p>
					)}
				</div>
			</div>
		);
	}

	// Compact mode without models: show warning inline
	if (compact && !hasModels) {
		return (
			<button
				type="button"
				onClick={onNavigateToSettings}
				className="flex items-center gap-3 rounded-xl border border-amber-400 bg-white px-4 py-3 text-left transition-colors hover:border-orange-400 hover:bg-white"
			>
				<AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
				<span className="text-sm font-medium text-amber-800">
					Configure embedding model
				</span>
			</button>
		);
	}

	return (
		<div
			className="rounded-2xl border-2 bg-white p-5 shadow-md transition-all duration-200"
			style={{
				borderColor: hasModels
					? "rgba(249,115,22,0.24)"
					: "rgba(251, 191, 36, 0.5)",
				boxShadow: undefined,
			}}
		>
			{hasModels ? (
				<div className="space-y-3">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-2">
							<Sparkles className="h-5 w-5 text-orange-600" />
							<h3 className="text-base font-semibold text-slate-900">
								Embedding Model
							</h3>
						</div>
					</div>
					{locked ? (
						<p className="text-xs text-amber-700">
							This collection&apos;s embedding model is locked — all documents must use the same model to ensure consistent search results.
						</p>
					) : (
						<p className="text-xs text-slate-600">
							Select the embedding model to use for converting documents into
							searchable vectors
						</p>
					)}
					<div className="flex-1 min-w-[250px]">
						<Dropdown
							value={selectedModel || ""}
							onChange={locked ? () => {} : onModelChange}
							options={modelOptions}
							placeholder="Select an embedding model"
							disabled={locked}
							menuAppearance="light"
						/>
					</div>
				</div>
			) : (
				<div className="flex flex-col items-center gap-4 py-6 text-center">
					<div className="rounded-full border border-dashed border-amber-400 bg-white p-4">
						<AlertTriangle className="h-10 w-10 text-amber-600" />
					</div>
					<div className="max-w-md">
						<h3 className="mb-2 text-lg font-semibold text-slate-900">
							No Embedding Model Configured
						</h3>
						<p className="mb-4 text-sm text-slate-600">
							You need to add at least one embedding model before uploading
							documents. Embedding models convert your documents into searchable
							vectors.
						</p>
						<Button
							onClick={onNavigateToSettings}
							icon={<Settings className="w-4 h-4" />}
						>
							Configure Embedding Models
						</Button>
					</div>
				</div>
			)}
		</div>
	);
}
