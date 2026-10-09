"use client";

import clsx from "clsx";
import { Check, ChevronDown, Plus, Trash2 } from "lucide-react";
import type React from "react";
import {
	useCallback,
	useEffect,
	useId,
	useMemo,
	useRef,
	useState,
} from "react";
import { FloatingPortal } from "@floating-ui/react";
import { useDropdown } from "@/hooks/useDropdown";

export interface DropdownOption {
	value: string;
	label: string;
	description?: string;
	icon?: React.ReactNode;
	disabled?: boolean;
	customContent?: React.ReactNode;
}

export interface DropdownGroup {
	label: string;
	icon?: React.ReactNode;
	options: DropdownOption[];
}

export interface DropdownProps {
	// Core
	value?: string;
	onChange: (value: string) => void;
	options?: DropdownOption[];
	groups?: DropdownGroup[];

	// UI
	placeholder?: string;
	trigger?: React.ReactNode;
	showSelectedIndicator?: boolean;

	// Positioning
	align?: "start" | "end" | "center";
	side?: "bottom" | "top" | "auto";
	maxHeight?: number;
	width?: number | "trigger" | "auto";

	// Styling
	className?: string;
	dropdownClassName?: string;
	optionClassName?: string;
	triggerClassName?: string;
	/** Light menus: dark text, white/orange surfaces (e.g. chat on orange header). Default keeps dark-theme list styling. */
	menuAppearance?: "default" | "light";
	/** Minimum floating menu width when width mode is "trigger" (long labels). */
	menuMinWidthPx?: number;

	// Behavior
	closeOnSelect?: boolean;
	portal?: boolean;
	disabled?: boolean;

	// Actions
	onAdd?: () => void;
	addLabel?: string;
	onDelete?: (value: string) => void;

	// Callbacks
	onOpen?: () => void;
	onClose?: () => void;
}

export default function Dropdown({
	value,
	onChange,
	options = [],
	groups,
	placeholder = "Select an option",
	trigger,
	showSelectedIndicator = true,
	align = "start",
	side = "auto",
	maxHeight = 400,
	width = "trigger",
	className = "",
	dropdownClassName = "",
	optionClassName = "",
	triggerClassName = "",
	menuAppearance = "default",
	menuMinWidthPx,
	closeOnSelect = true,
	portal = true,
	disabled = false,
	onAdd,
	addLabel = "Add New",
	onDelete,
	onOpen,
	onClose,
}: DropdownProps) {
	const [isOpen, setIsOpen] = useState(false);
	const [focusedIndex, setFocusedIndex] = useState<number>(-1);
	const [hoveredValue, setHoveredValue] = useState<string | null>(null);
	const triggerRef = useRef<HTMLElement | null>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const optionRefs = useRef<(HTMLDivElement | null)[]>([]);

	const dropdownId = useId();
	const listboxId = `${dropdownId}-listbox`;

	// Flatten all options for keyboard navigation
	const allOptions = useMemo(() => {
		if (groups) {
			return groups.flatMap((group) => group.options);
		}
		return options;
	}, [options, groups]);

	// Filter out disabled options for navigation
	const navigableOptions = useMemo(() => {
		return allOptions.filter((opt) => !opt.disabled);
	}, [allOptions]);

	const selectedOption = allOptions.find((opt) => opt.value === value);

	// Get dropdown position and merged ref callbacks
	const { position, setTriggerRef, setDropdownRef } = useDropdown({
		isOpen,
		onClose: useCallback(() => {
			setIsOpen(false);
			setFocusedIndex(-1);
			onClose?.();
		}, [onClose]),
		triggerRef,
		dropdownRef,
		align,
		side,
		maxHeight,
		width,
		menuMinWidthPx,
	});

	// Handle toggle
	const handleToggle = useCallback(() => {
		if (disabled) return;

		const newIsOpen = !isOpen;
		setIsOpen(newIsOpen);

		if (newIsOpen) {
			onOpen?.();
			// Focus the selected option or first option
			const selectedIndex = navigableOptions.findIndex(
				(opt) => opt.value === value,
			);
			setFocusedIndex(selectedIndex >= 0 ? selectedIndex : 0);
		} else {
			setFocusedIndex(-1);
			onClose?.();
		}
	}, [disabled, isOpen, onOpen, onClose, navigableOptions, value]);

	// Handle option selection
	const handleSelect = useCallback(
		(optionValue: string) => {
			onChange(optionValue);
			if (closeOnSelect) {
				setIsOpen(false);
				setFocusedIndex(-1);
				onClose?.();
				triggerRef.current?.focus();
			}
		},
		[onChange, closeOnSelect, onClose],
	);

	// Handle delete
	const handleDelete = useCallback(
		(e: React.MouseEvent, optionValue: string) => {
			e.stopPropagation();
			onDelete?.(optionValue);
		},
		[onDelete],
	);

	// Handle add
	const handleAdd = useCallback(() => {
		onAdd?.();
		setIsOpen(false);
	}, [onAdd]);

	// Keyboard navigation
	const handleKeyDown = useCallback(
		(event: React.KeyboardEvent) => {
			if (disabled) return;

			switch (event.key) {
				case "Enter":
				case " ":
					event.preventDefault();
					if (!isOpen) {
						handleToggle();
					} else if (
						focusedIndex >= 0 &&
						focusedIndex < navigableOptions.length
					) {
						handleSelect(navigableOptions[focusedIndex].value);
					}
					break;

				case "ArrowDown":
					event.preventDefault();
					if (!isOpen) {
						handleToggle();
					} else {
						setFocusedIndex((prev) =>
							prev < navigableOptions.length - 1 ? prev + 1 : prev,
						);
					}
					break;

				case "ArrowUp":
					event.preventDefault();
					if (isOpen) {
						setFocusedIndex((prev) => (prev > 0 ? prev - 1 : prev));
					}
					break;

				case "Home":
					if (isOpen) {
						event.preventDefault();
						setFocusedIndex(0);
					}
					break;

				case "End":
					if (isOpen) {
						event.preventDefault();
						setFocusedIndex(navigableOptions.length - 1);
					}
					break;

				case "Escape":
					if (isOpen) {
						event.preventDefault();
						setIsOpen(false);
						setFocusedIndex(-1);
						onClose?.();
						triggerRef.current?.focus();
					}
					break;
			}
		},
		[
			disabled,
			isOpen,
			focusedIndex,
			navigableOptions,
			handleToggle,
			handleSelect,
			onClose,
		],
	);

	// Scroll focused option into view
	useEffect(() => {
		if (isOpen && focusedIndex >= 0 && optionRefs.current[focusedIndex]) {
			optionRefs.current[focusedIndex]?.scrollIntoView({
				block: "nearest",
				behavior: "smooth",
			});
		}
	}, [focusedIndex, isOpen]);

	const lightMenu = menuAppearance === "light";

	// Render option
	const renderOption = useCallback(
		(option: DropdownOption, globalIndex: number) => {
			const isSelected = option.value === value;
			const isFocused = globalIndex === focusedIndex;
			const isHovered = hoveredValue === option.value;

			return (
				<div
					key={option.value}
					ref={(el) => {
						optionRefs.current[globalIndex] = el;
					}}
					role="option"
					aria-selected={isSelected}
					aria-disabled={option.disabled}
					id={`${listboxId}-option-${globalIndex}`}
					onClick={() => !option.disabled && handleSelect(option.value)}
					onMouseEnter={() => setHoveredValue(option.value)}
					onMouseLeave={() => setHoveredValue(null)}
					className={clsx(
						"group relative min-w-0 cursor-pointer px-4 py-2.5 transition-all duration-150",
						"flex items-center gap-3 overflow-hidden",
						lightMenu
							? clsx(
									isSelected &&
										"bg-slate-100 text-slate-900 ring-1 ring-inset ring-orange-500",
									!isSelected &&
										isFocused &&
										"bg-slate-100 text-slate-900",
									!isSelected &&
										!isFocused &&
										"text-slate-700 hover:bg-slate-100 hover:text-slate-900",
								)
							: clsx(
									isSelected &&
										"bg-[rgba(var(--color-primary-rgb),0.15)] text-white",
									!isSelected &&
										isFocused &&
										"bg-[color:var(--color-surface-hover)] text-slate-900",
									!isSelected &&
										!isFocused &&
										"text-[color:var(--color-text-secondary)] hover:bg-[rgba(var(--color-primary-rgb),0.08)] hover:text-slate-700",
								),
						option.disabled && "cursor-not-allowed opacity-40",
						optionClassName,
					)}
				>
					{/* Icon */}
					{option.icon && (
						<span
							className={clsx(
								"shrink-0",
								lightMenu
									? isSelected
										? "text-orange-600"
										: "text-slate-500"
									: isSelected
										? "text-[color:var(--color-primary-light)]"
										: "text-[color:var(--color-text-muted)]",
							)}
						>
							{option.icon}
						</span>
					)}

					{/* Custom content or default layout */}
					{option.customContent ? (
						option.customContent
					) : (
						<div className="min-w-0 flex-1 overflow-hidden">
							<div
								className={clsx(
									"truncate text-sm font-medium",
									lightMenu
										? "!text-slate-900"
										: isSelected && "text-slate-900",
								)}
							>
								{option.label}
							</div>
							{option.description && (
								<div
									className={clsx(
										"mt-0.5 truncate text-xs",
										lightMenu
											? "text-slate-500"
											: "text-[color:var(--color-text-muted)]",
									)}
								>
									{option.description}
								</div>
							)}
						</div>
					)}

					{/* Right side: selected indicator or delete button */}
					<div className="flex shrink-0 items-center gap-1.5">
						{showSelectedIndicator && isSelected && (
							<Check
								className={clsx(
									"h-4 w-4",
									lightMenu ? "text-orange-600" : "text-[color:var(--color-primary-light)]",
								)}
							/>
						)}
						{onDelete &&
							!isSelected &&
							isHovered &&
							!option.disabled && (
								<div
									onClick={(e) => handleDelete(e, option.value)}
									className="p-1 rounded-md transition-colors hover:bg-red-500/20"
									title="Delete"
								>
									<Trash2 className="w-3 h-3 text-red-400" />
								</div>
							)}
					</div>
				</div>
			);
		},
		[
			value,
			focusedIndex,
			hoveredValue,
			listboxId,
			handleSelect,
			handleDelete,
			showSelectedIndicator,
			onDelete,
			optionClassName,
			lightMenu,
		],
	);

	// Render dropdown content
	const renderDropdownContent = () => {
		let globalIndex = 0;

		return (
			<div
				ref={setDropdownRef}
				role="listbox"
				id={listboxId}
				aria-activedescendant={
					focusedIndex >= 0 ? `${listboxId}-option-${focusedIndex}` : undefined
				}
				tabIndex={-1}
				className={clsx(
					"overflow-hidden rounded-xl flex flex-col",
					!lightMenu && "bg-[color:var(--color-surface)] backdrop-blur-2xl",
					!lightMenu && "border border-[color:var(--color-border)]/70",
					!lightMenu && "shadow-[0_20px_55px_rgba(0,0,0,0.55)]",
					lightMenu &&
						"rounded-[4px] border border-slate-200 bg-white text-slate-900 shadow-[0_12px_40px_rgba(15,23,42,0.12)] backdrop-blur-xl",
					"animate-fadeIn",
					dropdownClassName,
				)}
				style={{
					position: "fixed",
					top: `${position.top}px`,
					left: `${position.left}px`,
					width: `${position.width}px`,
					maxWidth: lightMenu ? "min(calc(100vw - 16px), 420px)" : undefined,
					maxHeight: `${position.maxHeight}px`,
					zIndex: 9999,
				}}
			>
				{/* Add New button */}
				{onAdd && (
					<div
						onClick={handleAdd}
						className={clsx(
							"flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm font-medium transition-colors duration-150",
							lightMenu
								? "border-b border-slate-200 text-orange-600 hover:bg-orange-50"
								: "border-b border-[color:var(--color-border)]/50 text-[color:var(--color-primary-light)] hover:bg-[rgba(var(--color-primary-rgb),0.08)]",
						)}
					>
						<Plus
							className={clsx(
								"h-4 w-4",
								lightMenu ? "text-orange-500" : "text-[color:var(--color-primary)]",
							)}
						/>
						{addLabel}
					</div>
				)}

				<div className="overflow-y-auto flex-1 min-h-0">
					{groups ? (
						// Render grouped options
						groups.map((group, groupIdx) => (
							<div key={groupIdx}>
								{/* Group label */}
								<div
									className={clsx(
										"flex items-center gap-2 px-4 py-2 text-xs font-semibold capitalize tracking-wider",
										lightMenu ? "text-orange-700" : "text-[color:var(--color-primary)]",
									)}
								>
									{group.icon && <span>{group.icon}</span>}
									{group.label}
								</div>
								{/* Group options */}
								{group.options.map((option) => {
									const rendered = renderOption(option, globalIndex);
									globalIndex++;
									return rendered;
								})}
							</div>
						))
					) : (
						// Render flat options
						<div className="py-1">
							{options.map((option) => {
								const rendered = renderOption(option, globalIndex);
								globalIndex++;
								return rendered;
							})}
						</div>
					)}

					{/* Empty state */}
					{allOptions.length === 0 && (
						<div
							className={clsx(
								"px-4 py-8 text-center text-sm",
								lightMenu ? "text-slate-500" : "text-[color:var(--color-text-muted)]",
							)}
						>
							No options available
						</div>
					)}
				</div>
			</div>
		);
	};

	// Render trigger
	const renderTrigger = () => {
		if (trigger) {
			return trigger;
		}

		return (
			<button
				ref={setTriggerRef}
				type="button"
				onClick={handleToggle}
				onKeyDown={handleKeyDown}
				disabled={disabled}
				aria-haspopup="listbox"
				aria-expanded={isOpen}
				aria-controls={isOpen ? listboxId : undefined}
				className={clsx(
					"w-full rounded-[4px] px-4 py-2.5",
					"flex items-center justify-between gap-3",
					lightMenu
						? "rounded-[4px] border border-slate-200 bg-white text-slate-900 transition-all duration-200 hover:border-orange-400 hover:bg-slate-50"
						: "border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-primary)] transition-all duration-200 hover:border-[color:var(--color-border-hover)] hover:bg-[color:var(--color-surface)]/60",
					"focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.7)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.25)]",
					"disabled:cursor-not-allowed disabled:opacity-40",
					triggerClassName,
				)}
			>
				<div className="flex min-w-0 flex-1 items-center gap-3 text-left">
					{selectedOption?.icon && (
						<span
							className={clsx(
								"shrink-0",
								lightMenu ? "text-orange-600" : "text-[color:var(--color-primary-light)]",
							)}
						>
							{selectedOption.icon}
						</span>
					)}
					<div className="min-w-0 flex-1 overflow-hidden">
						<div
							className={clsx(
								"truncate text-sm font-medium",
								lightMenu ? "text-slate-900" : "text-[color:var(--color-text-primary)]",
							)}
						>
							{selectedOption?.label || (
								<span className={lightMenu ? "text-slate-500" : "text-[color:var(--color-text-muted)]"}>
									{placeholder}
								</span>
							)}
						</div>
						{selectedOption?.description && (
							<div
								className={clsx(
									"mt-0.5 truncate text-xs",
									lightMenu ? "text-slate-500" : "text-[color:var(--color-text-muted)]",
								)}
							>
								{selectedOption.description}
							</div>
						)}
					</div>
				</div>
				<ChevronDown
					className={clsx(
						"h-4 w-4 shrink-0 transition-transform duration-200",
						lightMenu ? "text-slate-500" : "text-[color:var(--color-text-muted)]",
						isOpen && "rotate-180",
					)}
				/>
			</button>
		);
	};

	return (
		<div className={clsx("relative", className)}>
			{renderTrigger()}

			{/* Render dropdown in portal or inline */}
			{isOpen &&
				(portal ? (
					<FloatingPortal>{renderDropdownContent()}</FloatingPortal>
				) : (
					renderDropdownContent()
				))}
		</div>
	);
}
