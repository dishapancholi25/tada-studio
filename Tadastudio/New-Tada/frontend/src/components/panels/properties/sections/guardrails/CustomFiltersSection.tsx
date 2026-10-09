import { AlertTriangle, Code, MessageSquare, Plus, Puzzle } from "lucide-react";
import { useMemo } from "react";
import type {
	CustomFilter,
	CustomFilterType,
} from "@/types/guardrails";
import { createDefaultCustomFilter } from "@/types/guardrails";
import FilterCard from "./filters/FilterCard";

const DEPRECATED_IMPORTS = [
	"presidio_analyzer",
	"presidio_anonymizer",
	"detoxify",
] as const;

/**
 * Check if a python_code filter imports any deprecated libraries.
 * Returns the list of matched deprecated import names.
 */
function detectDeprecatedImports(pythonCode: string): string[] {
	return DEPRECATED_IMPORTS.filter(
		(lib) =>
			pythonCode.includes(`import ${lib}`) ||
			pythonCode.includes(`from ${lib}`),
	);
}

const DEPRECATION_GUIDANCE: Record<string, string> = {
	presidio_analyzer:
		"Use the \"PII Detection\" guardrail in Behavioral Safety instead.",
	presidio_anonymizer:
		"Use the \"PII Detection\" guardrail in Behavioral Safety instead.",
	detoxify:
		"Enable the \"Detect Toxicity\" toggle in Behavioral Safety instead.",
};

interface CustomFiltersSectionProps {
	filters: CustomFilter[];
	onChange: (filters: CustomFilter[]) => void;
	modelOptions: Array<{
		value: string;
		label: string;
		description?: string;
		model?: Record<string, unknown>;
	}>;
	modelsLoading: boolean;
	readOnly?: boolean;
	onNavigateToBehavioral?: () => void;
}

const FILTER_TYPE_OPTIONS: Array<{
	type: CustomFilterType;
	label: string;
	description: string;
	icon: typeof Code;
}> = [
	{
		type: "python_code",
		label: "Python Code",
		description: "Write a custom filter function",
		icon: Code,
	},
	{
		type: "llm_judge",
		label: "LLM Judge",
		description: "Natural language policy prompt",
		icon: MessageSquare,
	},
	{
		type: "declarative",
		label: "Template",
		description: "Preconfigured filter template",
		icon: Puzzle,
	},
];

export default function CustomFiltersSection({
	filters,
	onChange,
	modelOptions,
	modelsLoading,
	readOnly = false,
	onNavigateToBehavioral,
}: CustomFiltersSectionProps) {
	// Detect deprecated imports in python_code filters
	const deprecatedFilterWarnings = useMemo(() => {
		const warnings: Array<{
			filterIndex: number;
			filterName: string;
			deprecatedLibs: string[];
		}> = [];
		for (let i = 0; i < filters.length; i++) {
			const filter = filters[i];
			if (filter.filter_type === "python_code" && filter.python_code) {
				const deprecated = detectDeprecatedImports(filter.python_code);
				if (deprecated.length > 0) {
					warnings.push({
						filterIndex: i,
						filterName: filter.name || `Filter ${i + 1}`,
						deprecatedLibs: deprecated,
					});
				}
			}
		}
		return warnings;
	}, [filters]);
	const handleAdd = (filterType: CustomFilterType) => {
		const newFilter = createDefaultCustomFilter(filterType);
		onChange([...filters, newFilter]);
	};

	const handleUpdate = (index: number, updates: Partial<CustomFilter>) => {
		const updated = [...filters];
		updated[index] = { ...updated[index], ...updates };
		onChange(updated);
	};

	const handleRemove = (index: number) => {
		onChange(filters.filter((_, i) => i !== index));
	};

	return (
		<div className="space-y-4">
			{/* Add filter buttons */}
			{!readOnly && (
				<div>
					<p className="mb-2 text-xs font-medium text-[color:var(--color-text-secondary)]">
						Add Filter
					</p>
					<div className="flex flex-wrap gap-2">
						{FILTER_TYPE_OPTIONS.map(
							({ type, label, description, icon: Icon }) => (
								<button
									key={type}
									type="button"
									onClick={() => handleAdd(type)}
									className="flex items-center gap-2 rounded-lg border border-dashed border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/20 px-3 py-2 text-xs text-[color:var(--color-text-secondary)] transition-colors hover:border-cyan-500/40 hover:bg-cyan-500/5 hover:text-cyan-400"
								>
									<Icon className="h-3.5 w-3.5" />
									<div className="text-left">
										<div className="font-medium">{label}</div>
										<div className="text-[10px] opacity-70">
											{description}
										</div>
									</div>
									<Plus className="ml-1 h-3 w-3" />
								</button>
							),
						)}
					</div>
				</div>
			)}

			{/* Deprecated import warnings */}
			{deprecatedFilterWarnings.length > 0 && (
				<div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3">
					<div className="mb-1 flex items-center gap-2 text-xs font-semibold text-amber-400">
						<AlertTriangle className="h-3.5 w-3.5" />
						Deprecated Libraries Detected
					</div>
					<ul className="space-y-1.5">
						{deprecatedFilterWarnings.map(
							({ filterIndex, filterName, deprecatedLibs }) => (
								<li
									key={filterIndex}
									className="text-xs text-amber-300/90"
								>
									<span className="font-medium">
										{filterName}
									</span>
									{" uses "}
									{deprecatedLibs.map((lib, i) => (
										<span key={lib}>
											{i > 0 && ", "}
											<code className="rounded bg-amber-500/15 px-1 py-0.5 text-[10px]">
												{lib}
											</code>
										</span>
									))}
									{" — "}
									{DEPRECATION_GUIDANCE[deprecatedLibs[0]]}
								</li>
							),
						)}
					</ul>
					{onNavigateToBehavioral && (
						<button
							type="button"
							onClick={onNavigateToBehavioral}
							className="mt-2 text-xs font-medium text-amber-400 underline decoration-amber-400/40 underline-offset-2 hover:text-amber-300"
						>
							Go to Behavioral Safety settings
						</button>
					)}
				</div>
			)}

			{/* Filter list */}
			{filters.length === 0 ? (
				<div className="rounded-xl border border-dashed border-[color:var(--color-border)]/40 p-6 text-center">
					<p className="text-xs text-[color:var(--color-text-secondary)]/70">
						No custom filters configured. Add a filter above to get
						started.
					</p>
				</div>
			) : (
				<div className="space-y-3">
					{filters.map((filter, index) => (
						<FilterCard
							key={filter.id}
							filter={filter}
							index={index}
							onChange={(updates) => handleUpdate(index, updates)}
							onDelete={() => handleRemove(index)}
							modelOptions={modelOptions}
							modelsLoading={modelsLoading}
						/>
					))}
				</div>
			)}

			{filters.length > 0 && (
				<p className="text-[10px] text-[color:var(--color-text-secondary)]/60">
					Filters execute in priority order (lower number = first).
					Transform results cascade through the chain.
				</p>
			)}
		</div>
	);
}
