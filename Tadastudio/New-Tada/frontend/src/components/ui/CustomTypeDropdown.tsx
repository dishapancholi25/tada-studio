"use client";

import { Database, Hash, List, ToggleLeft, Type } from "lucide-react";
import type React from "react";
import { useId, useMemo } from "react";

export interface FieldTypeOption {
	value: string;
	label: string;
	description: string;
	category: "basic" | "collections";
	icon: React.ReactNode;
}

const TYPE_OPTIONS: FieldTypeOption[] = [
	// Basic Types
	{
		value: "str",
		label: "String",
		description: "Text value",
		category: "basic",
		icon: <Type className="w-4 h-4" />,
	},
	{
		value: "int",
		label: "Integer",
		description: "Whole number",
		category: "basic",
		icon: <Hash className="w-4 h-4" />,
	},
	{
		value: "float",
		label: "Float",
		description: "Decimal number",
		category: "basic",
		icon: <Hash className="w-4 h-4" />,
	},
	{
		value: "bool",
		label: "Boolean",
		description: "True/False value",
		category: "basic",
		icon: <ToggleLeft className="w-4 h-4" />,
	},

	// Collections
	{
		value: "List[str]",
		label: "List of Strings",
		description: "Array of text values",
		category: "collections",
		icon: <List className="w-4 h-4" />,
	},
	{
		value: "List[int]",
		label: "List of Integers",
		description: "Array of numbers",
		category: "collections",
		icon: <List className="w-4 h-4" />,
	},
	{
		value: "List[float]",
		label: "List of Floats",
		description: "Array of decimal numbers",
		category: "collections",
		icon: <List className="w-4 h-4" />,
	},
	{
		value: "Dict[str, Any]",
		label: "Dictionary",
		description: "Key-value pairs",
		category: "collections",
		icon: <Database className="w-4 h-4" />,
	},
	{
		value: "List[Dict[str, Any]]",
		label: "List of Dictionaries",
		description: "Array of objects (e.g. tabular rows)",
		category: "collections",
		icon: <List className="w-4 h-4" />,
	},
];

interface CustomTypeDropdownProps {
	value: string;
	onChange: (value: string) => void;
	className?: string;
	id?: string;
	labelId?: string;
}

const CATEGORY_LABELS: Record<FieldTypeOption["category"], string> = {
	basic: "Basic Types",
	collections: "Collection Types",
};

const getCategoryIcon = (category: FieldTypeOption["category"]) => {
	switch (category) {
		case "basic":
			return <Type className="w-3.5 h-3.5" />;
		case "collections":
			return <List className="w-3.5 h-3.5" />;
		default:
			return null;
	}
};

const getCategoryColor = (category: FieldTypeOption["category"]) => {
	switch (category) {
		case "basic":
			return "text-[color:var(--color-primary)]";
		case "collections":
			return "text-emerald-800";
		default:
			return "text-slate-600";
	}
};

const CustomTypeDropdown: React.FC<CustomTypeDropdownProps> = ({
	value,
	onChange,
	className = "",
	id,
	labelId,
}) => {
	const generatedName = useId();
	const radioGroupName = `${id || "field-type"}-${generatedName}`;

	const groupedOptions = useMemo(
		() => ({
			basic: TYPE_OPTIONS.filter((opt) => opt.category === "basic"),
			collections: TYPE_OPTIONS.filter((opt) => opt.category === "collections"),
		}),
		[],
	);

	return (
		<div
			id={id}
			role="radiogroup"
			aria-labelledby={labelId}
			className={`bg-[color:var(--color-surface)] border border-[color:var(--color-border)]/70 rounded-2xl p-4 text-slate-900 ${className}`}
		>
			<div className="grid gap-4 md:grid-cols-2">
				{(
					Object.keys(groupedOptions) as Array<FieldTypeOption["category"]>
				).map((category) => (
					<div
						key={category}
						className="flex flex-col gap-2 bg-[color:var(--color-surface-hover)]/30 border border-[color:var(--color-border)]/40 rounded-xl p-3"
					>
						<div className="flex items-center justify-between mb-1">
							<div
								className={`flex items-center gap-2 text-[10px] font-semibold capitalize ${getCategoryColor(category)}`}
							>
								{getCategoryIcon(category)}
								{CATEGORY_LABELS[category]}
							</div>
							<div className="h-px flex-1 bg-[color:var(--color-border)]/40 ml-3"></div>
						</div>

						<div className="space-y-2">
							{groupedOptions[category].map((option) => {
								const isSelected = option.value === value;
								return (
									<label
										key={option.value}
										className={`flex items-start gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
											isSelected
												? "border-[color:var(--color-primary)]/60 bg-[rgba(var(--color-primary-rgb),0.08)] shadow-[0_4px_20px_rgba(0,0,0,0.25)]"
												: "border-[color:var(--color-border)]/60 hover:border-[color:var(--color-primary)]/40 hover:bg-[color:var(--color-surface)]/40"
										}`}
									>
										<input
											type="radio"
											name={radioGroupName}
											value={option.value}
											checked={isSelected}
											onChange={() => onChange(option.value)}
											className="sr-only"
										/>
										<div
											className={`mt-1 w-4 h-4 rounded-full border-2 flex items-center justify-center transition-all ${
												isSelected
													? "border-[color:var(--color-primary)] bg-[rgba(var(--color-primary-rgb),0.12)]"
													: "border-[color:var(--color-border)] bg-[color:var(--color-surface)]"
											}`}
										>
											{isSelected && (
												<div className="w-2 h-2 rounded-full bg-[color:var(--color-primary)]"></div>
											)}
										</div>

										<div className="flex items-start gap-3 flex-1 min-w-0">
											<span
												className={`${getCategoryColor(option.category)} mt-0.5`}
											>
												{option.icon}
											</span>
											<div className="flex-1 min-w-0">
												<div className="text-sm font-medium !text-slate-900">
													{option.label}
												</div>
												<div className="text-xs !text-slate-600">
													{option.description}
												</div>
											</div>
											<span className="text-[10px] capitalize tracking-wide !text-slate-600">
												{option.value}
											</span>
										</div>
									</label>
								);
							})}
						</div>
					</div>
				))}
			</div>
		</div>
	);
};

export default CustomTypeDropdown;
