"use client";

import { ChevronDown, ExternalLink, Search, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	PII_CATEGORY_LABELS,
	PII_ENTITY_TYPES,
	PII_ENTITY_TYPE_MAP,
	type PIIEntityCategory,
	type PIIEntityType,
} from "@/constants/pii-entity-types";
import {
	COMPLIANCE_PRESETS,
	RECOMMENDED_ENTITY_TYPES,
	type CompliancePreset,
} from "@/constants/pii-compliance-presets";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PIIEntitySelectorProps {
	value: string[];
	onChange: (selected: string[]) => void;
	disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Detect which compliance preset (if any) exactly matches the current selection. */
function detectActivePreset(selected: string[]): CompliancePreset | null {
	if (selected.length === 0) return null;
	const set = new Set(selected);
	for (const preset of COMPLIANCE_PRESETS) {
		if (
			preset.entityTypes.length === set.size &&
			preset.entityTypes.every((t) => set.has(t))
		) {
			return preset;
		}
	}
	return null;
}

function isRecommended(selected: string[]): boolean {
	if (selected.length !== RECOMMENDED_ENTITY_TYPES.length) return false;
	const set = new Set(selected);
	return RECOMMENDED_ENTITY_TYPES.every((t) => set.has(t));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PIIEntitySelector({
	value,
	onChange,
	disabled = false,
}: PIIEntitySelectorProps) {
	const [search, setSearch] = useState("");
	const [isDropdownOpen, setIsDropdownOpen] = useState(false);
	const [presetMenuOpen, setPresetMenuOpen] = useState(false);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const presetRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLInputElement>(null);

	const selectedSet = useMemo(() => new Set(value), [value]);
	const activePreset = useMemo(() => detectActivePreset(value), [value]);
	const isRec = useMemo(() => isRecommended(value), [value]);

	// Close dropdowns on outside click
	useEffect(() => {
		const handler = (e: MouseEvent) => {
			if (
				dropdownRef.current &&
				!dropdownRef.current.contains(e.target as Node)
			) {
				setIsDropdownOpen(false);
			}
			if (
				presetRef.current &&
				!presetRef.current.contains(e.target as Node)
			) {
				setPresetMenuOpen(false);
			}
		};
		document.addEventListener("mousedown", handler);
		return () => document.removeEventListener("mousedown", handler);
	}, []);

	// Filter entity types by search
	const filteredTypes = useMemo(() => {
		if (!search.trim()) return PII_ENTITY_TYPES;
		const q = search.toLowerCase();
		return PII_ENTITY_TYPES.filter(
			(t) =>
				t.value.toLowerCase().includes(q) ||
				t.label.toLowerCase().includes(q) ||
				t.description.toLowerCase().includes(q) ||
				PII_CATEGORY_LABELS[t.category].toLowerCase().includes(q),
		);
	}, [search]);

	// Group filtered types by category
	const groupedTypes = useMemo(() => {
		const groups: Partial<Record<PIIEntityCategory, PIIEntityType[]>> = {};
		for (const t of filteredTypes) {
			if (!groups[t.category]) groups[t.category] = [];
			groups[t.category]!.push(t);
		}
		return groups;
	}, [filteredTypes]);

	const addType = useCallback(
		(typeValue: string) => {
			if (!selectedSet.has(typeValue)) {
				onChange([...value, typeValue]);
			}
			setSearch("");
		},
		[value, onChange, selectedSet],
	);

	const removeType = useCallback(
		(typeValue: string) => {
			onChange(value.filter((v) => v !== typeValue));
		},
		[value, onChange],
	);

	const applyPreset = useCallback(
		(entityTypes: string[]) => {
			onChange([...entityTypes]);
			setPresetMenuOpen(false);
		},
		[onChange],
	);

	return (
		<div className="space-y-2.5">
			<label className="block text-xs font-medium text-[color:var(--color-text-primary)]">
				PII Entity Types to Detect
			</label>

			{/* ── Quick actions + Compliance presets ─────────────────────── */}
			{!disabled && (
				<div className="flex flex-wrap items-center gap-1.5">
					<span className="text-[10px] font-medium capitalize tracking-wider text-[color:var(--color-text-muted)]/60 mr-0.5">
						Quick:
					</span>
					<QuickButton
						active={isRec}
						onClick={() => applyPreset(RECOMMENDED_ENTITY_TYPES)}
					>
						<Sparkles className="h-3 w-3" />
						Recommended
					</QuickButton>
					<QuickButton
						active={value.length === PII_ENTITY_TYPES.length}
						onClick={() =>
							applyPreset(PII_ENTITY_TYPES.map((t) => t.value))
						}
					>
						All Types
					</QuickButton>
					<QuickButton
						active={value.length === 0}
						onClick={() => onChange([])}
					>
						Clear All
					</QuickButton>

					{/* Compliance preset dropdown */}
					<div className="relative ml-1" ref={presetRef}>
						<button
							type="button"
							onClick={() => setPresetMenuOpen((o) => !o)}
							className={`
								flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors
								${
									activePreset
										? "border-purple-500/50 bg-purple-500/15 text-purple-600"
										: "border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)] hover:border-purple-500/30 hover:text-purple-400"
								}
							`}
						>
							{activePreset
								? activePreset.shortLabel
								: "Compliance Preset"}
							<ChevronDown
								className={`h-3 w-3 transition-transform ${presetMenuOpen ? "rotate-180" : ""}`}
							/>
						</button>

						{presetMenuOpen && (
							<div className="absolute left-0 z-50 mt-1 w-72 rounded-xl border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)] py-1 shadow-xl">
								<div className="px-3 py-1.5 text-[10px] font-semibold capitalize tracking-wider text-[color:var(--color-text-muted)]/60">
									Compliance Frameworks
								</div>
								{COMPLIANCE_PRESETS.map((preset) => {
									const isActive =
										activePreset?.id === preset.id;
									return (
										<button
											key={preset.id}
											type="button"
											onClick={() =>
												applyPreset(preset.entityTypes)
											}
											className={`flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors ${
												isActive
													? "bg-purple-500/10"
													: "hover:bg-[rgba(168,85,247,0.08)]"
											}`}
										>
											<div className="min-w-0 flex-1">
												<div className="text-sm font-medium text-[color:var(--color-text-primary)]">
													{preset.label}
												</div>
												<div className="text-[11px] text-[color:var(--color-text-muted)]/70">
													{preset.entityTypes.length}{" "}
													entity types
												</div>
											</div>
											{isActive && (
												<span className="mt-0.5 shrink-0 rounded bg-purple-500/20 px-1.5 py-0.5 text-[10px] font-medium text-purple-400">
													Active
												</span>
											)}
										</button>
									);
								})}
							</div>
						)}
					</div>
				</div>
			)}

			{/* ── Search input ────────────────────────────────────────── */}
			{!disabled && (
				<div className="relative" ref={dropdownRef}>
					<div className="relative">
						<Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--color-text-muted)]/50" />
						<input
							ref={inputRef}
							type="text"
							value={search}
							onChange={(e) => {
								setSearch(e.target.value);
								setIsDropdownOpen(true);
							}}
							onFocus={() => setIsDropdownOpen(true)}
							placeholder="Search all 38+ entity types..."
							className={`
								w-full rounded-lg border py-2 pl-8 pr-3 text-xs
								bg-[color:var(--color-bg-secondary)]
								text-[color:var(--color-text-primary)]
								placeholder-[color:var(--color-text-muted)]/50
								transition-colors
								focus-visible:outline-none
								${
									isDropdownOpen
										? "border-[rgba(6,182,212,0.5)] ring-2 ring-[rgba(6,182,212,0.2)]"
										: "border-[color:var(--color-border)]/70 focus:border-[rgba(6,182,212,0.5)] focus:ring-2 focus:ring-[rgba(6,182,212,0.2)]"
								}
							`}
						/>
					</div>

					{/* ── Autocomplete dropdown ─────────────────────────── */}
					{isDropdownOpen && (
						<div className="absolute z-50 mt-1 w-full max-h-64 overflow-y-auto rounded-xl border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)] shadow-xl">
							{filteredTypes.length === 0 ? (
								<div className="px-3 py-4 text-center text-xs text-[color:var(--color-text-muted)]">
									No entity types match &quot;{search}&quot;
								</div>
							) : (
								Object.entries(groupedTypes).map(
									([category, types]) => (
										<div key={category}>
											<div className="sticky top-0 z-10 bg-[color:var(--color-bg-secondary)] px-3 py-1.5 text-[10px] font-semibold capitalize tracking-wider text-[color:var(--color-text-muted)]/60 border-b border-[color:var(--color-border)]/30">
												{PII_CATEGORY_LABELS[category as PIIEntityCategory]}
											</div>
											{types!.map((t) => {
												const isSelected =
													selectedSet.has(t.value);
												return (
													<button
														key={t.value}
														type="button"
														onClick={() =>
															isSelected
																? removeType(t.value)
																: addType(t.value)
														}
														className={`flex w-full items-center gap-2.5 px-3 py-1.5 text-left transition-colors ${
															isSelected
																? "bg-purple-500/10 text-purple-600"
																: "text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]"
														}`}
													>
														<div className="min-w-0 flex-1">
															<div className="text-xs font-medium">
																{t.label}
															</div>
															<div className="text-[10px] text-[color:var(--color-text-muted)]/70 truncate">
																{t.description}
															</div>
														</div>
														<span className="shrink-0 text-[10px] font-mono text-[color:var(--color-text-muted)]/40">
															{t.value}
														</span>
														{isSelected && (
															<span className="shrink-0 rounded bg-purple-500/20 px-1.5 py-0.5 text-[9px] font-medium text-purple-400">
																Added
															</span>
														)}
													</button>
												);
											})}
										</div>
									),
								)
							)}
						</div>
					)}
				</div>
			)}

			{/* ── Selected tags ───────────────────────────────────────── */}
			{value.length > 0 && (
				<div
					className={`
						flex flex-wrap gap-1.5 rounded-lg border px-2.5 py-2 max-h-32 overflow-y-auto
						bg-[color:var(--color-bg-secondary)]
						border-[color:var(--color-border)]/70
						${disabled ? "opacity-50" : ""}
					`}
				>
					{value.map((v) => {
						const entity = PII_ENTITY_TYPE_MAP[v];
						return (
							<span
								key={v}
								className="inline-flex items-center gap-1 rounded-md bg-purple-500/15 border border-purple-500/30 px-2 py-0.5 text-[11px] font-medium text-purple-600"
							>
								{entity?.label ?? v}
								{!disabled && (
									<button
										type="button"
										onClick={() => removeType(v)}
										className="rounded-sm p-0.5 transition-colors hover:bg-purple-500/30 hover:text-purple-200"
									>
										<X className="h-2.5 w-2.5" />
									</button>
								)}
							</span>
						);
					})}
				</div>
			)}

			{/* ── Compliance reference + help text ────────────────────── */}
			<div className="flex items-center justify-between text-[10px] text-[color:var(--color-text-muted)]/60">
				<div>
					{activePreset?.references && (
						<span className="text-purple-400/80">
							Covers: {activePreset.references}
						</span>
					)}
					{!activePreset && value.length === 0 && (
						<span>Empty = scan all types</span>
					)}
					{!activePreset && value.length > 0 && (
						<span>
							{value.length} type{value.length !== 1 ? "s" : ""}{" "}
							selected (custom)
						</span>
					)}
				</div>
				<a
					href="https://microsoft.github.io/presidio/supported_entities/"
					target="_blank"
					rel="noopener noreferrer"
					className="inline-flex items-center gap-0.5 text-[color:var(--color-text-muted)]/50 transition-colors hover:text-cyan-400"
				>
					Presidio docs
					<ExternalLink className="h-2.5 w-2.5" />
				</a>
			</div>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function QuickButton({
	active,
	onClick,
	children,
}: {
	active: boolean;
	onClick: () => void;
	children: React.ReactNode;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			className={`
				flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors
				${
					active
						? "border-cyan-500/50 bg-cyan-500/15 text-cyan-600"
						: "border-[color:var(--color-border)]/50 text-[color:var(--color-text-muted)] hover:border-cyan-500/30 hover:text-cyan-400"
				}
			`}
		>
			{children}
		</button>
	);
}
