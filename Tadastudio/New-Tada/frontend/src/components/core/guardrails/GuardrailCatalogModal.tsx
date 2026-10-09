"use client";

import { Check, Package, Plus, Search, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { GuardrailItem, GuardrailItemType } from "@/types/guardrail-items";
import { SINGLETON_TYPES } from "@/types/guardrail-items";
import {
	CATALOG_BUNDLES,
	CATALOG_CATEGORIES,
	type CatalogBundle,
	type CatalogEntry,
} from "./catalog";
import {
	createAdversarialItem,
	createCustomFilterItem,
	createGeneralSafetyItem,
	createInputContentItem,
	createInputPolicyItem,
	createLLMJudgeItem,
	createOutputContentItem,
	createOutputPolicyItem,
	createOutputQualityItem,
	createPIIItem,
	createPatternRuleItem,
	createProviderContentFilterItem,
	createTokenBudgetItem,
	createToolDatabaseItem,
	createToolExecutionLimitsItem,
	createToolFilesystemItem,
	createToolNetworkItem,
} from "@/lib/guardrail-item-mapper";

interface GuardrailCatalogModalProps {
	existingItems: GuardrailItem[];
	onAdd: (items: GuardrailItem[]) => void;
	onClose: () => void;
}

export default function GuardrailCatalogModal({
	existingItems,
	onAdd,
	onClose,
}: GuardrailCatalogModalProps) {
	const [search, setSearch] = useState("");

	// Track what's already added (for singleton disable and preset checks)
	const existingTypes = useMemo(
		() => new Set(existingItems.map((i) => i.type)),
		[existingItems],
	);
	const isEntryAdded = (entry: CatalogEntry): boolean => {
		if (entry.comingSoon) return true;
		if (entry.singleton && existingTypes.has(entry.type)) return true;
		return false;
	};

	const isBundleFullyAdded = (bundle: CatalogBundle): boolean => {
		return bundle.items.every((bi) => {
			if (SINGLETON_TYPES.includes(bi.type) && existingTypes.has(bi.type))
				return true;
			return false;
		});
	};

	// Filter categories by search
	const filteredCategories = useMemo(() => {
		if (!search.trim()) return CATALOG_CATEGORIES;
		const q = search.toLowerCase();
		return CATALOG_CATEGORIES.map((cat) => ({
			...cat,
			entries: cat.entries.filter(
				(e) =>
					e.label.toLowerCase().includes(q) ||
					e.description.toLowerCase().includes(q),
			),
		})).filter((cat) => cat.entries.length > 0);
	}, [search]);

	const handleAddEntry = (entry: CatalogEntry) => {
		if (isEntryAdded(entry)) return;
		const item = createItemFromEntry(entry);
		if (item) onAdd([item]);
	};

	const handleAddBundle = (bundle: CatalogBundle) => {
		const items: GuardrailItem[] = [];
		for (const bi of bundle.items) {
			// Skip already-added singletons
			if (SINGLETON_TYPES.includes(bi.type) && existingTypes.has(bi.type))
				continue;

			const entry = findEntryForBundleItem(bi);
			if (entry) {
				const item = createItemFromEntry(entry);
				if (item) items.push(item);
			}
		}
		if (items.length > 0) onAdd(items);
	};

	return (
		<div className="fixed inset-0 z-[120] flex items-center justify-center bg-[#213C81]/45 backdrop-blur-sm">
			<div className="relative flex max-h-[calc(100vh-80px)] w-full max-w-4xl animate-scaleIn flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				{/* Header */}
				<div className="flex items-center justify-between border-b border-slate-200 bg-white px-8 py-6">
					<div className="flex items-center gap-4">
						<div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-orange-600 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
							<Package className="h-5 w-5" />
						</div>
						<div>
							<h2 className="text-xl font-semibold text-slate-900">
								Add Guardrail
							</h2>
							<p className="mt-1 text-sm text-slate-500">
								Choose a guardrail or quick-start bundle for this policy.
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-all hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						<X className="w-5 h-5" />
					</button>
				</div>

				{/* Search */}
				<div className="border-b border-slate-200 bg-white px-8 py-4">
					<div className="relative">
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
						<input
							type="text"
							value={search}
							onChange={(e) => setSearch(e.target.value)}
							placeholder="Search guardrails..."
							className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 transition-all hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
							autoFocus
						/>
					</div>
				</div>

				{/* Scrollable content */}
				<div className="min-h-0 flex-1 space-y-8 overflow-y-auto bg-white p-8">
					{/* Bundles — only show when no search */}
					{!search.trim() && (
						<div>
							<h3 className="mb-3 text-xs font-semibold capitalize tracking-wider text-slate-500">
								Quick Start Bundles
							</h3>
							<div className="grid grid-cols-2 gap-3">
								{CATALOG_BUNDLES.map((bundle) => {
									const fullyAdded = isBundleFullyAdded(bundle);
									const BIcon = bundle.icon;
									return (
										<button
											key={bundle.id}
											type="button"
											onClick={() => handleAddBundle(bundle)}
											disabled={fullyAdded}
											className={`flex items-start gap-3 rounded-2xl border p-4 text-left shadow-[0_10px_28px_rgba(15,23,42,0.06)] transition-all ${
												fullyAdded
													? "border-slate-200 bg-white opacity-60 cursor-default"
													: "border-slate-200 bg-white hover:border-orange-400 hover:bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_82%,#f59e0b_180%)]"
											}`}
										>
											<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white">
												{fullyAdded ? (
													<Check className="h-4 w-4 text-orange-600" />
												) : (
													<BIcon className="h-4 w-4 text-orange-600" />
												)}
											</div>
											<div className="min-w-0">
												<div className="text-sm font-medium text-slate-900">
													{bundle.label}
												</div>
												<div className="text-xs text-slate-500 mt-0.5">
													{bundle.description}
												</div>
											</div>
										</button>
									);
								})}
							</div>
						</div>
					)}

					{/* Categories */}
					{filteredCategories.map((category) => {
						const CatIcon = category.icon;
						return (
							<div key={category.id}>
								<h3 className="mb-2 flex items-center gap-2 text-xs font-semibold capitalize tracking-wider text-slate-500">
									<CatIcon className="h-3.5 w-3.5" />
									{category.label}
								</h3>
								<div className="space-y-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_10px_28px_rgba(15,23,42,0.06)]">
									{category.entries.map((entry, idx) => {
										const added = isEntryAdded(entry);
										const comingSoon = Boolean(entry.comingSoon);
										const EIcon = entry.icon;
										return (
											<button
												key={`${entry.type}-${entry.templateId ?? idx}`}
												type="button"
												onClick={() =>
													handleAddEntry(entry)
												}
												disabled={added}
												className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-all ${
													added
														? "border border-transparent bg-white opacity-60 cursor-default"
														: "border border-transparent hover:border-orange-400 hover:bg-white hover:text-slate-900"
												}`}
											>
												<EIcon
													className={`h-4 w-4 shrink-0 ${added ? "text-orange-600" : "text-slate-400"}`}
												/>
												<div className="min-w-0 flex-1">
													<div className="flex items-center gap-2 text-sm text-slate-900">
														{entry.label}
														{comingSoon && (
															<span className="rounded-full border border-orange-300 bg-orange-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-orange-600">
																Coming soon
															</span>
														)}
													</div>
													<div className="text-xs text-slate-500">
														{entry.description}
													</div>
												</div>
												{comingSoon ? null : added ? (
													<Check className="h-4 w-4 shrink-0 text-orange-600" />
												) : (
													<Plus className="h-4 w-4 shrink-0 text-slate-400" />
												)}
											</button>
										);
									})}
								</div>
							</div>
						);
					})}
				</div>
			</div>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createItemFromEntry(entry: CatalogEntry): GuardrailItem | null {
	switch (entry.type) {
		case "pattern_rule":
			return createPatternRuleItem();
		case "llm_judge":
			return createLLMJudgeItem();
		case "general_safety":
			return createGeneralSafetyItem();
		case "provider_content_filter":
			return createProviderContentFilterItem();
		case "tool_network":
			return createToolNetworkItem();
		case "tool_database":
			return createToolDatabaseItem();
		case "tool_filesystem":
			return createToolFilesystemItem();
		case "tool_execution_limits":
			return createToolExecutionLimitsItem();
		case "token_budget":
			return createTokenBudgetItem();
		case "llm_guard_adversarial":
			return createAdversarialItem();
		case "llm_guard_pii":
			return createPIIItem();
		case "llm_guard_input_content":
			return createInputContentItem();
		case "llm_guard_input_policy":
			return createInputPolicyItem();
		case "llm_guard_output_quality":
			return createOutputQualityItem();
		case "llm_guard_output_content":
			return createOutputContentItem();
		case "llm_guard_output_policy":
			return createOutputPolicyItem();
		case "custom_filter": {
			if (entry.templateId) {
				return createCustomFilterItem("declarative", entry.templateId);
			}
			// Determine filter type from label
			if (entry.label.includes("Python"))
				return createCustomFilterItem("python_code");
			if (entry.label.includes("LLM"))
				return createCustomFilterItem("llm_judge");
			return createCustomFilterItem("python_code");
		}
		default:
			return null;
	}
}

function findEntryForBundleItem(bi: {
	type: GuardrailItemType;
	templateId?: string;
}): CatalogEntry | null {
	for (const cat of CATALOG_CATEGORIES) {
		for (const entry of cat.entries) {
			if (entry.type !== bi.type) continue;
			if (bi.templateId && entry.templateId === bi.templateId) return entry;
			if (!bi.templateId) return entry;
		}
	}
	return null;
}
