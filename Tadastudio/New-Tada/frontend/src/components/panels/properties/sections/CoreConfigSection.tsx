"use client";

import { ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import Dropdown, { type DropdownOption } from "../../../ui/Dropdown";
import InfoTooltip from "../../../ui/InfoTooltipPortal";
import { ProviderLogo } from "../../../ui/ProviderLogos";
import SystemPromptEditor from "../SystemPromptEditor";

interface ModelParams {
	temperature: string;
	maxTokens: string;
	topP: string;
	reasoningEffort: string;
}

interface CoreConfigSectionProps {
	selectedModelId: string;
	onModelChange: (model: string) => void;
	prompt: string;
	onPromptChange: (prompt: string) => void;
	onExpandMarkdownEditor: () => void;
	modelOptions: Array<{
		value: string;
		label: string;
		provider: string;
		providerKey: string;
		description: string;
	}>;
	modelsLoading: boolean;
	modelLoadError: string | null;
	legacyModelName: string;
	modelParams: ModelParams;
	onModelParamsChange: (params: ModelParams) => void;
	deploymentDefaults?: {
		temperature?: number | null;
		maxTokens?: number | null;
		topP?: number | null;
		reasoningEffort?: string | null;
	};
	validationErrors?: {
		temperature?: string;
		maxTokens?: string;
		topP?: string;
	};
	/** Dropdown list styling for model/reasoning pickers. */
	dropdownMenuAppearance?: "default" | "light";
}

const reasoningOptions: DropdownOption[] = [
	{ value: "", label: "Not set" },
	{ value: "low", label: "Low" },
	{ value: "medium", label: "Medium" },
	{ value: "high", label: "High" },
];

export default function CoreConfigSection({
	selectedModelId,
	onModelChange,
	prompt,
	onPromptChange,
	onExpandMarkdownEditor,
	modelOptions,
	modelsLoading,
	modelLoadError,
	legacyModelName,
	modelParams,
	onModelParamsChange,
	deploymentDefaults,
	validationErrors,
	dropdownMenuAppearance = "light",
}: CoreConfigSectionProps) {
	const [paramsExpanded, setParamsExpanded] = useState(false);

	const dropdownOptions: DropdownOption[] = useMemo(() => {
		return modelOptions.map((model) => {
			const prefix = `${model.provider} \u2022 `;
			const tail = model.description.startsWith(prefix)
				? model.description.slice(prefix.length)
				: model.description;
			return {
				value: model.value,
				label: model.label,
				description: `${model.provider} \u2022 ${tail}`,
				icon: (
					<ProviderLogo
						provider={model.providerKey}
						className="h-5 w-5"
					/>
				),
			};
		});
	}, [modelOptions]);

	const handleParamChange = (field: keyof ModelParams, value: string) => {
		onModelParamsChange({ ...modelParams, [field]: value });
	};

	const hasCustomParams =
		modelParams.temperature !== "" ||
		modelParams.maxTokens !== "" ||
		modelParams.topP !== "" ||
		modelParams.reasoningEffort !== "";

	// Resolve effective defaults for placeholder display
	const tempPlaceholder = deploymentDefaults?.temperature != null
		? String(deploymentDefaults.temperature)
		: "0";
	const maxTokensPlaceholder = deploymentDefaults?.maxTokens != null
		? String(deploymentDefaults.maxTokens)
		: "Unlimited";
	const topPPlaceholder = deploymentDefaults?.topP != null
		? String(deploymentDefaults.topP)
		: "Not set";
	const reasoningPlaceholder = deploymentDefaults?.reasoningEffort
		? `${deploymentDefaults.reasoningEffort.charAt(0).toUpperCase()}${deploymentDefaults.reasoningEffort.slice(1)}`
		: "Not set";

	return (
		<div className="flex flex-col gap-4" data-tutorial="tools-section">
			<SystemPromptEditor
				prompt={prompt}
				onPromptChange={onPromptChange}
				onOpenPromptStudio={onExpandMarkdownEditor}
			/>

			{/* Section divider */}
			<div className="my-2 h-px bg-slate-200" />

			{/* Model Selector */}
			<div
				data-tutorial="model-selector"
				className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm"
			>
				<label
					htmlFor="ai-model-select"
					className="mb-1.5 flex items-center gap-2 text-[0.6rem] capitalize text-slate-600"
				>
					AI Model
					<InfoTooltip text="Choose the managed deployment this agent should use." />
				</label>
				{modelsLoading ? (
					<div className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
						<Loader2 className="h-3.5 w-3.5 animate-spin text-orange-600" />
						Loading models...
					</div>
				) : modelOptions.length > 0 ? (
					<Dropdown
						value={selectedModelId || ""}
						onChange={onModelChange}
						options={dropdownOptions}
						placeholder="Select a model deployment"
						className="w-full"
						menuAppearance={dropdownMenuAppearance}
						triggerClassName="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 hover:!border-orange-400 hover:!bg-slate-50"
						dropdownClassName="!border-slate-200 !bg-white"
						optionClassName="!text-slate-900 hover:!bg-slate-100 hover:!text-orange-800"
					/>
				) : (
					<div className="rounded-[4px] border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
						No models configured. Visit{" "}
						<span className="font-medium text-orange-700">
							Settings &rarr; LLM Providers
						</span>{" "}
						to add deployments.
					</div>
				)}
				{modelLoadError && (
					<p className="mt-1 text-[11px] text-red-600">
						{modelLoadError}
					</p>
				)}
				{legacyModelName && !selectedModelId && (
					<p className="mt-1 text-[11px] text-amber-800">
						This agent still references the legacy model{" "}
						<span className="font-medium">{legacyModelName}</span>.
						Select a managed deployment to migrate.
					</p>
				)}
			</div>

			{/* Model Parameters */}
			<div
				data-tutorial="model-params-section"
				className="rounded-[4px] border border-slate-200 bg-white overflow-hidden shadow-sm"
			>
				<button
					data-tutorial="model-params-toggle"
					type="button"
					onClick={() => setParamsExpanded(!paramsExpanded)}
					className="w-full flex items-center justify-between px-3 py-2.5 text-left transition-colors hover:bg-slate-50"
				>
					<div className="flex items-center gap-2">
						{paramsExpanded ? (
							<ChevronDown className="h-3.5 w-3.5 text-slate-500" />
						) : (
							<ChevronRight className="h-3.5 w-3.5 text-slate-500" />
						)}
						<span className="text-xs text-slate-700 font-semibold">
							Model parameters
						</span>
						{hasCustomParams && (
							<span className="text-[9px] px-1.5 py-0.5 rounded-full border border-orange-400 bg-white text-orange-700 font-medium">
								Custom
							</span>
						)}
					</div>
					<InfoTooltip text="Override deployment defaults for this agent. Leave blank to use deployment defaults." />
				</button>

				{paramsExpanded && (
					<div className="px-3 pb-3 pt-1 space-y-3 border-t border-slate-200">
						<div className="grid grid-cols-2 gap-3">
							{/* Temperature */}
							<div>
								<label className="mb-1 flex items-center gap-1.5 text-[10px] capitalize text-slate-600">
									Temperature
								</label>
								<input
									type="number"
									min="0"
									max="2"
									step="0.1"
									value={modelParams.temperature}
									onChange={(e) =>
										handleParamChange("temperature", e.target.value)
									}
									placeholder={tempPlaceholder}
									className={`w-full rounded-[4px] border bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors ${validationErrors?.temperature ? "border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-500/20" : "border-slate-200 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15"}`}
								/>
								{validationErrors?.temperature && (
									<p className="mt-1 text-[10px] text-red-600">{validationErrors.temperature}</p>
								)}
							</div>

							{/* Max Tokens */}
							<div>
								<label className="mb-1 flex items-center gap-1.5 text-[10px] capitalize text-slate-600">
									Max Tokens
								</label>
								<input
									type="number"
									min="1"
									step="1"
									value={modelParams.maxTokens}
									onChange={(e) =>
										handleParamChange("maxTokens", e.target.value)
									}
									placeholder={maxTokensPlaceholder}
									className={`w-full rounded-[4px] border bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors ${validationErrors?.maxTokens ? "border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-500/20" : "border-slate-200 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15"}`}
								/>
								{validationErrors?.maxTokens && (
									<p className="mt-1 text-[10px] text-red-600">{validationErrors.maxTokens}</p>
								)}
							</div>

							{/* Top P */}
							<div>
								<label className="mb-1 flex items-center gap-1.5 text-[10px] capitalize text-slate-600">
									Top P
								</label>
								<input
									type="number"
									min="0"
									max="1"
									step="0.05"
									value={modelParams.topP}
									onChange={(e) =>
										handleParamChange("topP", e.target.value)
									}
									placeholder={topPPlaceholder}
									className={`w-full rounded-[4px] border bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none transition-colors ${validationErrors?.topP ? "border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-500/20" : "border-slate-200 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15"}`}
								/>
								{validationErrors?.topP && (
									<p className="mt-1 text-[10px] text-red-600">{validationErrors.topP}</p>
								)}
							</div>

							{/* Reasoning Effort */}
							<div>
								<label className="mb-1 flex items-center gap-1.5 text-[10px] capitalize text-slate-600">
									Reasoning Effort
									<InfoTooltip text="For reasoning models. Controls how much reasoning the model does." />
								</label>
								<Dropdown
									value={modelParams.reasoningEffort}
									onChange={(value) =>
										handleParamChange("reasoningEffort", value)
									}
									options={reasoningOptions}
									placeholder={reasoningPlaceholder}
									className="w-full"
									menuAppearance={dropdownMenuAppearance}
									triggerClassName="!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 !text-xs !px-2.5 !py-1.5 hover:!border-orange-400 hover:!bg-slate-50"
									dropdownClassName="!border-slate-200 !bg-white"
									optionClassName="!text-slate-900 hover:!bg-slate-100 hover:!text-orange-800"
								/>
							</div>
						</div>
					</div>
				)}
			</div>
		</div>
	);
}
