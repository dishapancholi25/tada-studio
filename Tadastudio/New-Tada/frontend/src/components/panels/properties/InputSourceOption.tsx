import clsx from "clsx";
import type React from "react";
import type { ModeOption } from "./inputSourceTypes";

interface InputSourceOptionProps {
	option: ModeOption;
	isSelected: boolean;
	onSelect: () => void;
	children?: React.ReactNode;
}

export default function InputSourceOption({
	option,
	isSelected,
	onSelect,
	children,
}: InputSourceOptionProps) {
	return (
		<div
			role="radio"
			aria-checked={isSelected}
			tabIndex={0}
			onClick={onSelect}
			onKeyDown={(e) => {
				if (e.key === "Enter" || e.key === " ") {
					e.preventDefault();
					onSelect();
				}
			}}
			className={clsx(
				"relative cursor-pointer rounded-[4px] border px-4 py-3 transition-all duration-200",
				isSelected
					? "border-orange-500 bg-white shadow-sm"
					: "border-slate-200 bg-white hover:border-orange-400 hover:bg-slate-50",
				"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25",
			)}
		>
			<div className="flex items-start gap-3">
				{/* Radio circle */}
				<div
					className={clsx(
						"mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200",
						isSelected
							? "border-orange-500"
							: "border-slate-300",
					)}
				>
					{isSelected && (
						<div className="h-[10px] w-[10px] rounded-full bg-orange-500" />
					)}
				</div>

				{/* Content */}
				<div className="min-w-0 flex-1">
					<div className="flex items-center justify-between gap-2">
						<div className="flex items-center gap-2">
							<option.Icon className="h-4 w-4 text-slate-600" />
							<span className="text-sm font-semibold text-slate-900">
								{option.title}
							</span>
							{option.badge && (
								<span
									className={clsx(
										"rounded-full border px-2 py-0.5 text-[9px] font-medium capitalize",
										option.badgeVariant === "recommended" &&
											"border-orange-200 bg-white text-orange-800",
										option.badgeVariant === "advanced" &&
											"border-slate-200 bg-slate-50 text-slate-600",
									)}
								>
									{option.badge}
								</span>
							)}
						</div>
						{isSelected && (
							<span className="rounded-full border border-orange-500 bg-white px-2 py-0.5 text-[9px] font-medium capitalize text-orange-900">
								Active
							</span>
						)}
					</div>
					<p className="mt-1 text-xs leading-relaxed text-slate-600">
						{option.description}
					</p>
				</div>
			</div>

			{/* Inline expansion */}
			{isSelected && children && (
				<div className="ml-[30px] mt-3 animate-fadeIn border-t border-slate-200 pt-3">
					{children}
				</div>
			)}
		</div>
	);
}
