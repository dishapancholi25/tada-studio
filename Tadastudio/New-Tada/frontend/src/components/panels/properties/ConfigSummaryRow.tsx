"use client";

import { ChevronDown, Loader2 } from "lucide-react";
import { useMemo, useState } from "react";
import Dropdown, { type DropdownOption } from "../../ui/Dropdown";
import InfoTooltip from "../../ui/InfoTooltipPortal";
import { ProviderLogo } from "../../ui/ProviderLogos";
import { cn } from "@/lib/utils";

interface ModelOption {
	value: string;
	label: string;
	provider: string;
	providerKey: string;
	description: string;
}

interface ConfigSummaryRowProps {
	agentName: string;
	onAgentNameChange: (name: string) => void;
	selectedModelId: string;
	onModelChange: (model: string) => void;
	modelOptions: ModelOption[];
	modelsLoading: boolean;
	modelLoadError: string | null;
	legacyModelName: string;
}

export default function ConfigSummaryRow({
	agentName,
	onAgentNameChange,
	selectedModelId,
	onModelChange,
	modelOptions,
	modelsLoading,
	modelLoadError,
	legacyModelName,
}: ConfigSummaryRowProps) {
	const [expanded, setExpanded] = useState(false);

	const selectedModel = modelOptions.find(
		(o) => o.value === selectedModelId,
	);

	const summaryText = useMemo(() => {
		const parts = [
			agentName || "Unnamed Agent",
			selectedModel?.label || (modelsLoading ? "Loading..." : "No model"),
			selectedModel?.provider || "",
		].filter(Boolean);
		return parts.join(" \u00B7 ");
	}, [agentName, selectedModel, modelsLoading]);

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

	return (
		<div className="flex-none">
			{/* Summary toggle row */}
			<button
				type="button"
				onClick={() => setExpanded(!expanded)}
				aria-expanded={expanded}
				className={cn(
					"flex w-full items-center justify-between rounded-xl px-4 py-3.5 text-left transition-colors",
					"border border-[color:var(--color-border)]/30 bg-gradient-to-r from-[color:var(--color-surface)]/50 via-[color:var(--color-surface)]/35 to-[color:var(--color-surface)]/50",
					"hover:bg-[color:var(--color-surface)]/60 hover:border-[rgba(var(--color-primary-rgb),0.3)]",
					"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]",
				)}
			>
				<span className="text-xs text-[color:var(--color-text-secondary)] truncate">
					{summaryText}
				</span>
				<ChevronDown
					className={cn(
						"h-3.5 w-3.5 shrink-0 text-[color:var(--color-text-muted)] transition-transform duration-200",
						expanded && "rotate-180",
					)}
				/>
			</button>

			{/* Expanded config fields */}
			{expanded && (
				<div className="animate-slideDown mt-2 space-y-4 rounded-xl border border-[color:var(--color-border)]/30 bg-gradient-to-b from-[rgba(31,31,31,0.50)] to-[rgba(16,16,16,0.65)] p-4 shadow-[0_12px_30px_rgba(0,0,0,0.3)]">
					{/* Agent Name */}
					<div>
						<label
							htmlFor="agent-name-input"
							className="mb-1.5 flex items-center gap-2 text-[0.6rem] capitalize text-[color:var(--color-text-muted)]"
						>
							Agent Name
							<InfoTooltip text="A descriptive name for this agent that appears on the canvas." />
						</label>
						<input
							id="agent-name-input"
							type="text"
							value={agentName}
							onChange={(e) => onAgentNameChange(e.target.value)}
							className={cn(
								"w-full rounded-lg border border-[color:var(--color-border)]/15 bg-[color:var(--color-surface)]/60",
								"px-3 py-2 text-[13px] text-[color:var(--color-text-primary)]",
								"placeholder:text-[color:var(--color-text-muted)]/50",
								"hover:border-[color:var(--color-border)]/30",
								"focus:border-[rgba(var(--color-primary-rgb),0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]",
								"transition-colors",
							)}
							placeholder="e.g., Research Assistant, Data Analyzer"
						/>
					</div>

					{/* Model Selector */}
					<div>
						<label
							htmlFor="ai-model-select"
							className="mb-1.5 flex items-center gap-2 text-[0.6rem] capitalize text-[color:var(--color-text-muted)]"
						>
							AI Model
							<InfoTooltip text="Choose the managed deployment this agent should use." />
						</label>
						{modelsLoading ? (
							<div className="flex items-center gap-2 rounded-lg border border-[color:var(--color-border)]/15 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
								<Loader2 className="h-3.5 w-3.5 animate-spin text-[color:var(--color-primary)]" />
								Loading models...
							</div>
						) : modelOptions.length > 0 ? (
							<Dropdown
								value={selectedModelId || ""}
								onChange={onModelChange}
								options={dropdownOptions}
								placeholder="Select a model deployment"
								className="w-full"
								triggerClassName="border border-[color:var(--color-border)]/15 bg-[color:var(--color-surface)]/60 hover:bg-[color:var(--color-surface)]/80 hover:border-[color:var(--color-border)]/30 text-[color:var(--color-text-primary)]"
								dropdownClassName="border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]"
								optionClassName="hover:bg-[color:var(--color-surface-hover)]"
							/>
						) : (
							<div className="rounded-lg border border-[color:var(--color-border)]/15 bg-[color:var(--color-surface)]/60 px-3 py-2 text-xs text-[color:var(--color-text-secondary)]">
								No models configured. Visit{" "}
								<span className="text-[color:var(--color-primary)]">
									Settings &rarr; LLM Providers
								</span>{" "}
								to add deployments.
							</div>
						)}
						{modelLoadError && (
							<p className="mt-1 text-[11px] text-red-300">
								{modelLoadError}
							</p>
						)}
						{legacyModelName && !selectedModelId && (
							<p className="mt-1 text-[11px] text-amber-300">
								This agent still references the legacy model{" "}
								<span className="font-medium">{legacyModelName}</span>.
								Select a managed deployment to migrate.
							</p>
						)}
					</div>
				</div>
			)}
		</div>
	);
}
