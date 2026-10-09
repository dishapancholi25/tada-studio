"use client";

import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import { ChevronRight, Code, FileText, Layers, Zap } from "lucide-react";
import type React from "react";

interface ModeOption {
	value: string;
	title: string;
	subtitle: string;
	description: string;
	Icon: LucideIcon;
	accentClass: string;
}

const MODE_OPTIONS: ModeOption[] = [
	{
		value: "previous",
		title: "Previous Node",
		subtitle: "Previous step",
		description: "Output from previous node",
		Icon: ChevronRight,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.08)] via-[rgba(var(--color-primary-rgb),0.02)] to-transparent",
	},
	{
		value: "specific",
		title: "Specific Node",
		subtitle: "Pick a node",
		description: "Choose a specific node",
		Icon: Layers,
		accentClass: "from-purple-500/8 via-purple-500/2 to-transparent",
	},
	{
		value: "start",
		title: "Start Input",
		subtitle: "Workflow start",
		description: "Original workflow input",
		Icon: Zap,
		accentClass: "from-emerald-500/8 via-emerald-500/2 to-transparent",
	},
	{
		value: "field",
		title: "Field Path",
		subtitle: "From state",
		description: "Extract from state field",
		Icon: Code,
		accentClass: "from-amber-500/8 via-amber-500/2 to-transparent",
	},
	{
		value: "custom",
		title: "Custom Template",
		subtitle: "Template",
		description: "Template with {node_id} substitution",
		Icon: FileText,
		accentClass: "from-rose-500/8 via-rose-500/2 to-transparent",
	},
];

interface ConditionInputModeSelectorProps {
	selectedMode: string;
	onModeChange: (mode: string) => void;
}

const ConditionInputModeSelector: React.FC<ConditionInputModeSelectorProps> = ({
	selectedMode,
	onModeChange,
}) => {
	return (
		<section className="rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 p-4 backdrop-blur-sm">
			<h3 className="mb-3 text-base font-semibold text-slate-900">Input Source</h3>
			<div className="grid gap-2 md:grid-cols-2">
				{MODE_OPTIONS.map((option) => {
					const isSelected = option.value === selectedMode;
					return (
						<button
							key={option.value}
							type="button"
							onClick={() => onModeChange(option.value)}
							aria-pressed={isSelected}
							className={clsx(
								"group relative overflow-hidden rounded-lg border px-3 py-2.5 text-left transition-all duration-200",
								"bg-[color:var(--color-surface)]/40 hover:bg-[color:var(--color-surface)]/60",
								isSelected
									? "border-[color:var(--color-accent)]/70 shadow-[0_8px_16px_rgba(var(--color-primary-rgb),0.12)]"
									: "border-[color:var(--color-border)]/60",
							)}
						>
							<div
								className={clsx(
									"pointer-events-none absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-200",
									option.accentClass,
									isSelected ? "opacity-90" : "group-hover:opacity-40",
								)}
							/>
							<div className="relative flex items-center justify-between gap-3">
								<div className="flex items-center gap-2.5">
									<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/15 bg-slate-100 text-slate-900/85 shadow-[0_4px_10px_rgba(8,12,24,0.25)]">
										<option.Icon className="h-4 w-4" />
									</div>
									<div>
										<div className="flex items-center gap-1.5 text-white">
											<span className="text-sm font-semibold">
												{option.title}
											</span>
										</div>
										<span className="text-xs capitalize tracking-wide text-slate-600">
											{option.subtitle}
										</span>
									</div>
								</div>
								<span
									className={clsx(
										"inline-flex h-5 min-w-[2.75rem] items-center justify-center rounded-full border px-2.5 text-[10px] font-medium capitalize tracking-wide transition-colors",
										isSelected
											? "border-[color:var(--color-accent)]/70 bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)]"
											: "border-[color:var(--color-border)]/60 text-[color:var(--color-text-muted)]/75",
									)}
								>
									{isSelected ? "Active" : "Select"}
								</span>
							</div>
							<p className="relative mt-2 text-xs leading-relaxed text-slate-600">
								{option.description}
							</p>
						</button>
					);
				})}
			</div>
		</section>
	);
};

export default ConditionInputModeSelector;
