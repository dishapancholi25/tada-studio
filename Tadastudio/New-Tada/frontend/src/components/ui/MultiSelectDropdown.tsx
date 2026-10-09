"use client";

import { Check, ChevronDown, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

export interface MultiSelectOption {
	value: string;
	label: string;
	description?: string;
}

interface MultiSelectDropdownProps {
	value: string[];
	options: MultiSelectOption[];
	onChange: (selected: string[]) => void;
	placeholder?: string;
	disabled?: boolean;
	label?: string;
	description?: string;
	className?: string;
	allLabel?: string;  // Label for "select all" option (e.g., "All PII Types")
}

export default function MultiSelectDropdown({
	value,
	options,
	onChange,
	placeholder = "Select options...",
	disabled = false,
	label,
	description,
	className = "",
	allLabel = "All Options",
}: MultiSelectDropdownProps) {
	const [isOpen, setIsOpen] = useState(false);
	const dropdownRef = useRef<HTMLDivElement>(null);

	// Close dropdown when clicking outside
	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			if (
				dropdownRef.current &&
				!dropdownRef.current.contains(event.target as Node)
			) {
				setIsOpen(false);
			}
		};

		if (isOpen) {
			document.addEventListener("mousedown", handleClickOutside);
			return () => {
				document.removeEventListener("mousedown", handleClickOutside);
			};
		}
	}, [isOpen]);

	const toggleOption = useCallback(
		(optionValue: string) => {
			if (value.includes(optionValue)) {
				onChange(value.filter((v) => v !== optionValue));
			} else {
				onChange([...value, optionValue]);
			}
		},
		[value, onChange],
	);

	const selectAll = useCallback(() => {
		onChange(options.map((opt) => opt.value));
	}, [options, onChange]);

	const clearAll = useCallback(() => {
		onChange([]);
	}, [onChange]);

	const allSelected = value.length === options.length;
	const noneSelected = value.length === 0;

	const displayText = noneSelected
		? placeholder
		: allSelected
			? allLabel
			: `${value.length} selected`;

	return (
		<div className={`space-y-1.5 ${className}`}>
			{label && (
				<label className="block text-xs font-medium text-[color:var(--color-text-primary)]">
					{label}
				</label>
			)}
			{description && (
				<p className="text-xs text-[color:var(--color-text-muted)]">
					{description}
				</p>
			)}
			<div className="relative" ref={dropdownRef}>
				<button
					type="button"
					onClick={() => !disabled && setIsOpen(!isOpen)}
					disabled={disabled}
					className={`
						w-full flex items-center justify-between gap-2
						px-3 py-2 rounded-lg
						bg-[color:var(--color-surface)]
						border border-[color:var(--color-border)]
						text-sm text-[color:var(--color-text-primary)]
						transition-all duration-200
						${
							disabled
								? "opacity-50 cursor-not-allowed"
								: "hover:border-[color:var(--color-accent)]/50 hover:bg-[color:var(--color-surface-hover)] cursor-pointer"
						}
						${isOpen ? "border-[color:var(--color-accent)] ring-2 ring-[color:var(--color-accent)]/20" : ""}
					`}
				>
					<span
						className={noneSelected ? "text-[color:var(--color-text-muted)]" : ""}
					>
						{displayText}
					</span>
					<ChevronDown
						className={`w-4 h-4 text-[color:var(--color-text-muted)] transition-transform ${isOpen ? "rotate-180" : ""}`}
					/>
				</button>

				{isOpen && !disabled && (
					<div className="absolute z-50 w-full mt-1 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] shadow-xl max-h-64 overflow-y-auto">
						{/* Select All / Clear All Controls */}
						<div className="sticky top-0 bg-[color:var(--color-surface)] border-b border-[color:var(--color-border)] px-3 py-2 flex items-center justify-between">
							<button
								type="button"
								onClick={selectAll}
								className="text-xs font-medium text-[color:var(--color-accent)] hover:text-[color:var(--color-accent-hover)] transition-colors"
							>
								Select All
							</button>
							<button
								type="button"
								onClick={clearAll}
								className="text-xs font-medium text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)] transition-colors"
							>
								Clear All
							</button>
						</div>

						{/* Options */}
						<div className="py-1">
							{options.map((option) => {
								const isSelected = value.includes(option.value);
								return (
									<button
										key={option.value}
										type="button"
										onClick={() => toggleOption(option.value)}
										className={`
											w-full flex items-start gap-2 px-3 py-2
											text-sm text-left transition-colors
											${
												isSelected
													? "bg-[color:var(--color-accent)]/10 text-[color:var(--color-text-primary)]"
													: "text-[color:var(--color-text-secondary)] hover:bg-[color:var(--color-surface-hover)]"
											}
										`}
									>
										<div
											className={`
												flex-shrink-0 w-4 h-4 mt-0.5 rounded border transition-all
												${
													isSelected
														? "bg-[color:var(--color-accent)] border-[color:var(--color-accent)]"
														: "border-[color:var(--color-border)]"
												}
												flex items-center justify-center
											`}
										>
											{isSelected && (
												<Check className="w-3 h-3 text-white" strokeWidth={3} />
											)}
										</div>
										<div className="flex-1 min-w-0">
											<div className="font-medium">{option.label}</div>
											{option.description && (
												<div className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
													{option.description}
												</div>
											)}
										</div>
									</button>
								);
							})}
						</div>
					</div>
				)}
			</div>
		</div>
	);
}
