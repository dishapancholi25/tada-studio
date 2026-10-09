"use client";

import { Plus, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface GuardrailsPanelProps {
	children: ReactNode;
	/** Whether guardrails are enabled. */
	enabled: boolean;
	/** Callback when the toggle is clicked. */
	onToggle: (enabled: boolean) => void;
	/** Callback for the "+ Assign" button. */
	onAssign: () => void;
	/** Optional subtitle shown under the title. */
	description?: string;
	/** Light orange/white card (agent properties panel). Default matches settings/tools surfaces. */
	theme?: "default" | "light";
}

export default function GuardrailsPanel({
	children,
	enabled,
	onToggle,
	onAssign,
	description = "Assign and manage guardrail policies for safety, compliance, and cost control.",
	theme = "default",
}: GuardrailsPanelProps) {
	const isLight = theme === "light";

	return (
		<div
			className={cn(
				"rounded-[4px] p-6 shadow-sm",
				isLight
					? "border border-slate-200 bg-white"
					: "rounded-2xl border-2 border-orange-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]",
			)}
		>
			{/* Header */}
			<div
				className={cn(
					"flex flex-wrap items-start justify-between gap-4 border-b pb-5",
					isLight ? "border-slate-200" : "border-orange-100",
				)}
			>
				<div className="flex items-center gap-3">
					<div
						className={cn(
							"flex h-12 w-12 items-center justify-center rounded-[4px] border",
							isLight
								? "border-orange-200 bg-orange-100 text-orange-600"
								: "border-orange-200 bg-orange-50 text-orange-600",
						)}
					>
						<ShieldCheck className="h-6 w-6" />
					</div>
					<div>
						<h3
							className={cn(
								"text-xl font-semibold",
								isLight ? "text-slate-900" : "text-slate-900",
							)}
						>
							Guardrails
						</h3>
						<p
							className={cn(
								"text-sm",
								isLight ? "text-slate-600" : "text-slate-600",
							)}
						>
							{description}
						</p>
					</div>
				</div>
				<div className="flex items-center gap-3">
					<button
						type="button"
						onClick={onAssign}
						className="flex items-center gap-1.5 rounded-[4px] px-2.5 py-1.5 text-xs font-medium text-orange-700 transition-colors hover:bg-orange-50 hover:text-orange-900"
					>
						<Plus className="h-3.5 w-3.5" />
						Assign
					</button>
					<label className="relative inline-flex items-center cursor-pointer">
						<input
							type="checkbox"
							checked={enabled}
							onChange={(e) => onToggle(e.target.checked)}
							className="peer sr-only"
						/>
						<div className="h-7 w-12 rounded-full border border-slate-300 bg-slate-200 transition-colors duration-200 peer-checked:bg-orange-500 peer-checked:border-orange-500 peer-focus-visible:ring-2 peer-focus-visible:ring-orange-500/30" />
						<span className="absolute left-1 top-1 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 peer-checked:translate-x-5" />
					</label>
				</div>
			</div>

			{/* Disabled notice */}
			{!enabled && (
				<div
					className={cn(
						"mt-4 rounded-[4px] border px-3 py-2 text-xs",
						isLight
							? "border-amber-300 bg-amber-50 text-amber-900"
							: "border-amber-300 bg-amber-50 text-amber-900",
					)}
				>
					Guardrails are disabled. Assigned policies will not be enforced during
					execution.
				</div>
			)}

			{/* Body */}
			<div className="mt-4 space-y-4">{children}</div>
		</div>
	);
}
