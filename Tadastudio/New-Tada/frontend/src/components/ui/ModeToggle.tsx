import clsx from "clsx";
import { Edit, FlaskConical, Play } from "lucide-react";
import React, { useCallback } from "react";

interface ModeToggleProps {
	mode: "edit" | "evaluate" | "execution";
	onModeChange: (mode: "edit" | "evaluate" | "execution") => void;
	isExecuting?: boolean;
	className?: string;
	workflowId?: string;
	compact?: boolean;
}

export default function ModeToggle({
	mode,
	onModeChange,
	isExecuting,
	className,
	compact = false,
}: ModeToggleProps) {
	const handleEdit = useCallback(() => onModeChange("edit"), [onModeChange]);
	const handleEvaluate = useCallback(() => onModeChange("evaluate"), [onModeChange]);
	const handleExecute = useCallback(() => onModeChange("execution"), [onModeChange]);

	// Light-mode tab strip (used in the white CanvasTopBar)
	if (compact) {
		const tabBase =
			"relative flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors duration-150 focus-visible:outline-none";

		const active = (check: boolean) =>
			check
				? "text-[#ff6b00]"
				: "text-gray-500 hover:text-gray-800";

		const underline = (check: boolean) =>
			check
				? "absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-[#ff6b00]"
				: "";

		return (
			<div
				data-tutorial="mode-toggle"
				className={clsx(
					"flex items-center rounded-lg border border-gray-200 bg-gray-50",
					className,
				)}
			>
				<button
					data-tutorial="mode-edit"
					type="button"
					onClick={handleEdit}
					disabled={isExecuting}
					className={clsx(
						tabBase,
						active(mode === "edit"),
						isExecuting && "cursor-not-allowed opacity-50",
						"rounded-l-lg",
					)}
				>
					<Edit className="h-4 w-4" />
					<span>Edit</span>
					<span className={underline(mode === "edit")} />
				</button>

				<div className="h-5 w-px bg-gray-200" />

				<button
					data-tutorial="mode-evaluate"
					type="button"
					onClick={handleEvaluate}
					className={clsx(tabBase, active(mode === "evaluate"))}
				>
					<FlaskConical className="h-4 w-4" />
					<span>Evaluate</span>
					<span className={underline(mode === "evaluate")} />
				</button>

				<div className="h-5 w-px bg-gray-200" />

				<button
					data-tutorial="mode-execute"
					type="button"
					onClick={handleExecute}
					className={clsx(tabBase, active(mode === "execution"), "rounded-r-lg")}
				>
					<Play className="h-4 w-4" />
					<span>Execute</span>
					<span className={underline(mode === "execution")} />
				</button>
			</div>
		);
	}

	// Full-size variant (used standalone outside the topbar)
	const btnBase =
		"flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-primary)]/60";

	const editActive =
		mode === "edit"
			? "border-[color:var(--color-primary)]/50 bg-[color:var(--color-primary)]/15 text-[color:var(--color-primary-light)] shadow-[0_6px_14px_rgba(var(--color-primary-rgb),0.28)]"
			: "border-transparent text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary-light)] hover:border-[color:var(--color-primary)]/35 hover:bg-[color:var(--color-primary)]/8";

	const evaluateClasses =
		mode === "evaluate"
			? "border-violet-400/60 bg-violet-500/15 text-violet-600 shadow-[0_6px_14px_rgba(139,92,246,0.28)]"
			: "border-transparent text-violet-600/70 hover:text-violet-600 hover:border-violet-400/40 hover:bg-violet-500/10";

	const executeActive =
		mode === "execution"
			? "border-emerald-400/60 bg-emerald-500/15 text-emerald-600 shadow-[0_6px_14px_rgba(16,185,129,0.28)]"
			: "border-transparent text-emerald-600/70 hover:text-emerald-600 hover:border-emerald-400/40 hover:bg-emerald-500/10";

	return (
		<div
			data-tutorial="mode-toggle"
			className={clsx(
				"flex min-h-[3.5rem] items-center gap-2 rounded-xl border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)]/80 px-4 py-3 shadow-[0_12px_24px_rgba(0,0,0,0.35)] backdrop-blur-xl transition-all duration-200",
				className,
			)}
		>
			<button
				data-tutorial="mode-edit"
				type="button"
				onClick={handleEdit}
				disabled={isExecuting}
				className={clsx(btnBase, editActive, isExecuting && "cursor-not-allowed opacity-50")}
			>
				<Edit size={16} className={clsx("transition-transform duration-200", mode === "edit" && "scale-105")} />
				<span className="tracking-wide">Edit</span>
			</button>

			<button
				data-tutorial="mode-evaluate"
				type="button"
				onClick={handleEvaluate}
				className={clsx(btnBase, evaluateClasses)}
			>
				<FlaskConical size={16} className={clsx("transition-transform duration-200", mode === "evaluate" && "scale-105")} />
				<span className="tracking-wide">Evaluate</span>
			</button>

			<button
				data-tutorial="mode-execute"
				type="button"
				onClick={handleExecute}
				className={clsx(btnBase, executeActive)}
			>
				<Play size={16} className={clsx("transition-transform duration-200", mode === "execution" && "scale-105")} />
				<span className="tracking-wide">Execute</span>
			</button>
		</div>
	);
}
