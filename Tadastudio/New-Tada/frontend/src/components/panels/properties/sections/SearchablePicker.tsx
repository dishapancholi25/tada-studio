"use client";

import { Check, ChevronDown, Search, X } from "lucide-react";
import {
	type ReactNode,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";

export interface PickerOption {
	value: string;
	label: string;
	description?: string;
	icon?: ReactNode;
	iconTooltip?: string;
	disabled?: boolean;
}

interface SearchablePickerProps {
	value: string;
	onChange: (value: string, option?: PickerOption) => void;
	options: PickerOption[];
	placeholder?: string;
	searchPlaceholder?: string;
	emptyMessage?: string;
	loading?: boolean;
	loadingMessage?: string;
	disabled?: boolean;
	clearable?: boolean;
	/** Accent color for selection highlight (default: #0078D4) */
	accentColor?: string;
	/** Limit visible rows before scrolling */
	maxVisibleOptions?: number;
	/** Approximate row height used with maxVisibleOptions */
	optionRowHeightPx?: number;
	/**
	 * "dark" (default) — dark-theme CSS vars; for properties panels.
	 * "light" — white background, slate borders; for white dialogs/modals.
	 */
	variant?: "dark" | "light";
}

/**
 * Searchable dropdown picker with filtering, keyboard navigation.
 * Supports dark (properties panels) and light (white dialogs) variants.
 */
export default function SearchablePicker({
	value,
	onChange,
	options,
	placeholder = "Select...",
	searchPlaceholder = "Search...",
	emptyMessage = "No results found",
	loading = false,
	loadingMessage = "Loading...",
	disabled = false,
	clearable = true,
	accentColor = "#0078D4",
	maxVisibleOptions,
	optionRowHeightPx = 36,
	variant = "dark",
}: SearchablePickerProps) {
	const [isOpen, setIsOpen] = useState(false);
	const [search, setSearch] = useState("");
	const [focusedIndex, setFocusedIndex] = useState(0);
	const containerRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLInputElement>(null);
	const listRef = useRef<HTMLDivElement>(null);

	const selectedOption = options.find((o) => o.value === value);

	const filtered = useMemo(() => {
		if (!search.trim()) return options;
		const q = search.toLowerCase();
		return options.filter(
			(o) =>
				o.label.toLowerCase().includes(q) ||
				o.description?.toLowerCase().includes(q),
		);
	}, [options, search]);

	const listMaxHeight = useMemo(() => {
		if (maxVisibleOptions && maxVisibleOptions > 0) {
			return maxVisibleOptions * optionRowHeightPx;
		}
		return 240;
	}, [maxVisibleOptions, optionRowHeightPx]);

	// Reset focused index when filtered list changes
	useEffect(() => {
		setFocusedIndex(0);
	}, [filtered.length]);

	// Close on click outside
	useEffect(() => {
		if (!isOpen) return;
		const handler = (e: MouseEvent) => {
			if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
				setIsOpen(false);
				setSearch("");
			}
		};
		document.addEventListener("mousedown", handler);
		return () => document.removeEventListener("mousedown", handler);
	}, [isOpen]);

	// Focus input when opened
	useEffect(() => {
		if (isOpen) {
			setTimeout(() => inputRef.current?.focus(), 0);
		}
	}, [isOpen]);

	// Scroll focused item into view
	useEffect(() => {
		if (!isOpen || !listRef.current) return;
		const focused = listRef.current.children[focusedIndex] as HTMLElement;
		focused?.scrollIntoView({ block: "nearest" });
	}, [focusedIndex, isOpen]);

	const handleSelect = useCallback(
		(opt: PickerOption) => {
			if (opt.disabled) return;
			onChange(opt.value, opt);
			setIsOpen(false);
			setSearch("");
		},
		[onChange],
	);

	const handleClear = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			onChange("", undefined);
		},
		[onChange],
	);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			switch (e.key) {
				case "ArrowDown":
					e.preventDefault();
					setFocusedIndex((i) => Math.min(i + 1, filtered.length - 1));
					break;
				case "ArrowUp":
					e.preventDefault();
					setFocusedIndex((i) => Math.max(i - 1, 0));
					break;
				case "Enter":
					e.preventDefault();
					if (filtered[focusedIndex] && !filtered[focusedIndex].disabled) {
						handleSelect(filtered[focusedIndex]);
					}
					break;
				case "Escape":
					e.preventDefault();
					setIsOpen(false);
					setSearch("");
					break;
			}
		},
		[filtered, focusedIndex, handleSelect],
	);

	const isLight = variant === "light";

	// When open, input shows the live search query; when closed, shows selected label
	const triggerDisplayValue = isOpen ? search : (selectedOption?.label ?? "");

	return (
		<div ref={containerRef} className="relative">
			{/* Trigger — doubles as the search input when open */}
			<div
				className={[
					"w-full flex items-center gap-2 px-3 py-2.5 rounded-[4px] border text-sm transition-colors",
					disabled || loading ? "opacity-50 cursor-not-allowed" : "",
					isOpen
						? isLight
							? "border-orange-400 ring-2 ring-orange-400/20"
							: "border-[rgba(var(--color-primary-rgb),0.5)]"
						: isLight
							? "bg-white border-slate-200 hover:border-slate-300"
							: "bg-[color:var(--color-bg-secondary)] border-[color:var(--color-border)]/60",
				].join(" ")}
			>
				{isOpen && (
					<Search
						className={[
							"w-3.5 h-3.5 shrink-0",
							isLight ? "text-slate-400" : "text-[color:var(--color-text-muted)]",
						].join(" ")}
					/>
				)}

				<input
					ref={inputRef}
					type="text"
					value={triggerDisplayValue}
					onChange={(e) => {
						if (!isOpen) setIsOpen(true);
						setSearch(e.target.value);
					}}
					onFocus={() => {
						if (!isOpen) { setSearch(""); setIsOpen(true); }
					}}
					onKeyDown={handleKeyDown}
					placeholder={loading ? loadingMessage : placeholder}
					disabled={disabled || loading}
					className={[
						"input-inline flex-1 min-w-0 bg-transparent text-sm",
						disabled || loading ? "cursor-not-allowed" : "cursor-pointer",
						triggerDisplayValue
							? "text-slate-900"
							: isLight ? "text-slate-400" : "text-[color:var(--color-text-muted)]",
					].join(" ")}
				/>

				<div className="flex items-center gap-1 shrink-0">
					{clearable && value && !loading && !isOpen && (
						<span
							role="button"
							tabIndex={-1}
							onClick={handleClear}
							onKeyDown={() => {}}
							className={[
								"p-0.5 rounded transition-colors",
								isLight
									? "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
									: "text-[color:var(--color-text-muted)] hover:text-slate-900 hover:bg-slate-100",
							].join(" ")}
						>
							<X className="w-3 h-3" />
						</span>
					)}
					{isOpen && search && (
						<button
							type="button"
							onClick={(e) => { e.stopPropagation(); setSearch(""); inputRef.current?.focus(); }}
							className={isLight ? "text-slate-400 hover:text-slate-700" : "text-[color:var(--color-text-muted)] hover:text-slate-900"}
						>
							<X className="w-3 h-3" />
						</button>
					)}
					<ChevronDown
						className={[
							"w-4 h-4 transition-transform shrink-0",
							isOpen ? "rotate-180" : "",
							isLight ? "text-slate-400" : "text-[color:var(--color-text-muted)]",
						].join(" ")}
					/>
				</div>
			</div>

			{/* Dropdown — options list only, no separate search bar */}
			{isOpen && (
				<div
					className={[
						"absolute z-50 mt-1 w-full rounded-lg border overflow-hidden shadow-xl",
						isLight
							? "bg-white border-slate-200 shadow-[0_8px_30px_rgba(0,0,0,0.12)]"
							: "bg-[color:var(--color-bg-secondary)] border-[color:var(--color-border)]/60 shadow-[0_20px_55px_rgba(0,0,0,0.55)]",
					].join(" ")}
				>
					{/* Options list */}
					<div
						ref={listRef}
						className="overflow-y-auto py-1"
						style={{ maxHeight: `${listMaxHeight}px` }}
					>
						{filtered.length === 0 ? (
							<div
								className={[
									"px-4 py-3 text-xs text-center",
									isLight ? "text-slate-400" : "text-[color:var(--color-text-muted)]",
								].join(" ")}
							>
								{emptyMessage}
							</div>
						) : (
							filtered.map((opt, i) => {
								const isSelected = opt.value === value;
								const isFocused = i === focusedIndex;
								const hoverBg = isLight ? "hover:bg-orange-50" : "hover:bg-slate-50";
								const focusBg = isLight ? "bg-orange-50" : "bg-slate-50";
								const selectedBg = isLight ? "bg-orange-50" : "bg-slate-50";
								return (
									<button
										type="button"
										key={opt.value}
										disabled={opt.disabled}
										onClick={() => handleSelect(opt)}
										onMouseEnter={() => setFocusedIndex(i)}
										className={[
											"w-full text-left px-3 py-2 flex items-center gap-2.5 transition-colors",
											opt.disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
											isSelected ? selectedBg : isFocused ? focusBg : hoverBg,
										].join(" ")}
									>
										{opt.icon && (
											<span
												className={[
													"shrink-0",
													isLight ? "text-slate-400" : "text-[color:var(--color-text-muted)]",
												].join(" ")}
												title={opt.iconTooltip}
												aria-label={opt.iconTooltip}
											>
												{opt.icon}
											</span>
										)}
										<div className="flex-1 min-w-0">
											<div
												className={[
													"text-sm truncate",
													isSelected
														? "font-medium text-slate-900"
														: isLight ? "text-slate-700" : "text-[color:var(--color-text-secondary)]",
												].join(" ")}
											>
												{opt.label}
											</div>
											{opt.description && (
												<div
													className={[
														"text-[10px] truncate mt-0.5",
														isLight ? "text-slate-400" : "text-[color:var(--color-text-muted)]",
													].join(" ")}
												>
													{opt.description}
												</div>
											)}
										</div>
										{isSelected && (
											<Check
												className="w-3.5 h-3.5 shrink-0"
												style={{ color: accentColor }}
											/>
										)}
									</button>
								);
							})
						)}
					</div>

					{/* Result count footer */}
					{search && filtered.length > 0 && (
						<div
							className={[
								"px-3 py-1.5 border-t text-[10px]",
								isLight
									? "border-slate-100 text-slate-400"
									: "border-[color:var(--color-border)]/30 text-[color:var(--color-text-muted)]",
							].join(" ")}
						>
							{filtered.length} of {options.length} results
						</div>
					)}
				</div>
			)}
		</div>
	);
}
