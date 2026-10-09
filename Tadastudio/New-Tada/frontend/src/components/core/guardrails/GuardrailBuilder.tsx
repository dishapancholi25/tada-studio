"use client";

import { Plus, Shield, ShieldAlert, ShieldCheck, ShieldOff } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GuardrailItem } from "@/types/guardrail-items";
import { isLLMJudgeType } from "@/types/guardrail-items";
import type { LLMJudgeItemConfig } from "@/types/guardrail-items";
import type { EnforcementMode, GuardrailsConfig } from "@/types/guardrails";
import { DEFAULT_GUARDRAILS_CONFIG } from "@/types/guardrails";
import { configToItems, itemsToConfig } from "@/lib/guardrail-item-mapper";
import { modelDeploymentAPI } from "@/lib/model-deployment-api";
import Dropdown from "@/components/ui/Dropdown";
import GuardrailCard from "./GuardrailCard";
import GuardrailCatalogModal from "./GuardrailCatalogModal";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ModelOption {
	value: string;
	label: string;
	provider: string;
	providerKey: string;
	description: string;
	model: Record<string, unknown>;
}

interface GuardrailBuilderProps {
	config: GuardrailsConfig;
	onChange: (config: GuardrailsConfig) => void;
	readOnly?: boolean;
}

/**
 * Converts a raw policy config to a GuardrailsConfig with defaults.
 * Re-exported for backward compat with PolicyConfigEditor consumers.
 */
export function toPolicyConfig(
	raw: Record<string, unknown> | null | undefined,
): GuardrailsConfig {
	if (!raw) return { ...DEFAULT_GUARDRAILS_CONFIG };
	return { ...DEFAULT_GUARDRAILS_CONFIG, ...raw } as GuardrailsConfig;
}

// ---------------------------------------------------------------------------
// Enforcement options
// ---------------------------------------------------------------------------

const ENFORCEMENT_OPTIONS = [
	{
		value: "enforce",
		label: "Enforce",
		description: "Block violations and halt execution",
		icon: <ShieldAlert className="h-4 w-4" />,
	},
	{
		value: "audit",
		label: "Audit",
		description: "Log violations but allow execution to continue",
		icon: <ShieldCheck className="h-4 w-4" />,
	},
	{
		value: "disabled",
		label: "Disabled",
		description: "No checking performed",
		icon: <ShieldOff className="h-4 w-4" />,
	},
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GuardrailBuilder({
	config,
	onChange,
	readOnly = false,
}: GuardrailBuilderProps) {
	// Model options for behavioral judge + custom filter LLM pickers
	const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
	const [modelsLoading, setModelsLoading] = useState(false);

	// Catalog modal
	const [showCatalog, setShowCatalog] = useState(false);

	// Which card is expanded
	const [expandedId, setExpandedId] = useState<string | null>(null);

	// Items — derived from config, synced back on change
	const [items, setItems] = useState<GuardrailItem[]>(() =>
		configToItems(config),
	);
	const [enforcementMode, setEnforcementMode] = useState<EnforcementMode>(
		config.enforcement_mode,
	);

	// Track config identity to re-derive items on external config change
	const configHashRef = useRef("");
	useEffect(() => {
		const hash = JSON.stringify(config);
		if (hash !== configHashRef.current) {
			configHashRef.current = hash;
			setItems(configToItems(config));
			setEnforcementMode(config.enforcement_mode);
		}
	}, [config]);

	// Emit config changes upward
	const emitChange = useCallback(
		(newItems: GuardrailItem[], mode: EnforcementMode) => {
			const newConfig = itemsToConfig(newItems, mode);
			configHashRef.current = JSON.stringify(newConfig);
			onChange(newConfig);
		},
		[onChange],
	);

	// Fetch model deployments
	useEffect(() => {
		let cancelled = false;
		const fetchModels = async () => {
			try {
				setModelsLoading(true);
				const deployments = await modelDeploymentAPI.listSelectOptions();
				if (cancelled) return;
				const providerLabels: Record<string, string> = {
					azure_openai: "Azure OpenAI",
					openai: "OpenAI",
					anthropic: "Anthropic",
				};
				const mapped: ModelOption[] = deployments
					.filter((d) => d.model_type === "llm")
					.map((deployment) => {
						const providerLabel =
							providerLabels[deployment.provider] ??
							deployment.provider;
						return {
							value: deployment.id,
							label: deployment.display_name || deployment.name,
							provider: providerLabel,
							providerKey: deployment.provider,
							description: [
								providerLabel,
								deployment.model_name,
							]
								.filter(Boolean)
								.join(" \u2022 "),
							model: deployment as unknown as Record<string, unknown>,
						};
					})
					.sort((a, b) => a.label.localeCompare(b.label));
				setModelOptions(mapped);
			} catch (err) {
				console.error("Failed to load model deployments:", err);
			} finally {
				if (!cancelled) setModelsLoading(false);
			}
		};
		fetchModels();
		return () => {
			cancelled = true;
		};
	}, []);

	// --- Handlers ---

	const handleEnforcementChange = (value: string) => {
		const mode = value as EnforcementMode;
		setEnforcementMode(mode);
		emitChange(items, mode);
	};

	const handleAddItems = (newItems: GuardrailItem[]) => {
		const updated = [...items, ...newItems];
		setItems(updated);
		emitChange(updated, enforcementMode);
		setShowCatalog(false);
		// Expand the first new item
		if (newItems.length === 1) {
			setExpandedId(newItems[0].id);
		}
	};

	const handleUpdateItem = (updated: GuardrailItem) => {
		const newItems = items.map((i) => (i.id === updated.id ? updated : i));
		// Sync shared judge config across all LLM Judge items
		if (isLLMJudgeType(updated.type)) {
			const judgeCfg = updated.config as LLMJudgeItemConfig;
			for (let idx = 0; idx < newItems.length; idx++) {
				const it = newItems[idx];
				if (isLLMJudgeType(it.type) && it.id !== updated.id) {
					newItems[idx] = {
						...it,
						config: {
							...(it.config as LLMJudgeItemConfig),
							judge_llm_config: judgeCfg.judge_llm_config,
						},
					} as GuardrailItem;
				}
			}
		}
		setItems(newItems);
		emitChange(newItems, enforcementMode);
	};

	const handleRemoveItem = (id: string) => {
		const updated = items.filter((i) => i.id !== id);
		setItems(updated);
		emitChange(updated, enforcementMode);
		if (expandedId === id) setExpandedId(null);
	};

	// Simple model option adapter for card
	const cardModelOptions = useMemo(
		() =>
			modelOptions.map((o) => ({
				value: o.value,
				label: o.label,
				description: o.description,
				model: o.model,
			})),
		[modelOptions],
	);

	return (
		<div
			className={`space-y-4 ${readOnly ? "opacity-75" : ""}`}
		>
			{/* Enforcement Mode */}
			<div className="rounded-xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/20 p-4">
				<label className="mb-2 block text-xs font-semibold capitalize tracking-wider text-[color:var(--color-text-muted)]">
					Enforcement Mode
				</label>
				<Dropdown
					value={enforcementMode}
					onChange={handleEnforcementChange}
					options={ENFORCEMENT_OPTIONS}
					disabled={readOnly}
				/>
			</div>

			{/* Item list */}
			{items.length > 0 ? (
				<div className="space-y-2">
					{items.map((item) => (
						<GuardrailCard
							key={item.id}
							item={item}
							isExpanded={expandedId === item.id}
							onToggleExpand={() =>
								setExpandedId(
									expandedId === item.id ? null : item.id,
								)
							}
							onChange={handleUpdateItem}
							onRemove={() => handleRemoveItem(item.id)}
							readOnly={readOnly}
							modelOptions={cardModelOptions}
							modelsLoading={modelsLoading}
						/>
					))}
				</div>
			) : (
				<div className="rounded-xl border border-dashed border-[color:var(--color-border)]/40 py-10 text-center">
					<Shield className="mx-auto h-10 w-10 text-[color:var(--color-text-muted)]/30 mb-3" />
					<p className="text-sm text-[color:var(--color-text-muted)]">
						No guardrails added yet.
					</p>
					<p className="text-xs text-[color:var(--color-text-muted)]/60 mt-1">
						Add guardrails to define what this policy enforces.
					</p>
				</div>
			)}

			{/* Add button */}
			{!readOnly && (
				<button
					type="button"
					onClick={() => setShowCatalog(true)}
					className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-[color:var(--color-border)]/50 py-3 text-sm text-[color:var(--color-text-muted)] transition-colors hover:border-cyan-500/40 hover:text-cyan-400 hover:bg-cyan-500/5"
				>
					<Plus className="h-4 w-4" />
					Add Guardrail
				</button>
			)}

			{/* Catalog modal */}
			{showCatalog && (
				<GuardrailCatalogModal
					existingItems={items}
					onAdd={handleAddItems}
					onClose={() => setShowCatalog(false)}
				/>
			)}
		</div>
	);
}
