"use client";

import { ChevronDown, ChevronRight, Link, Search, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

interface EndpointItem {
	id: string;
	name: string;
	method: string;
	url_template: string;
	description?: string;
	auth_type?: string;
}

interface EndpointPickerProps {
	value: string;
	onChange: (endpointId: string) => void;
	endpoints: EndpointItem[];
	placeholder?: string;
	/** Light styling for orange/white property modals */
	variant?: "default" | "light";
}

const METHOD_COLORS: Record<string, string> = {
	GET: "rgba(13, 169, 49, 0.15)",
	POST: "rgba(59, 130, 246, 0.15)",
	PUT: "rgba(245, 158, 11, 0.15)",
	PATCH: "rgba(168, 85, 247, 0.15)",
	DELETE: "rgba(239, 68, 68, 0.15)",
};

const METHOD_TEXT_COLORS: Record<string, string> = {
	GET: "rgb(74, 222, 128)",
	POST: "rgb(96, 165, 250)",
	PUT: "rgb(251, 191, 36)",
	PATCH: "rgb(192, 132, 252)",
	DELETE: "rgb(248, 113, 113)",
};

const METHOD_BORDERS: Record<string, string> = {
	GET: "rgba(13, 169, 49, 0.3)",
	POST: "rgba(59, 130, 246, 0.3)",
	PUT: "rgba(245, 158, 11, 0.3)",
	PATCH: "rgba(168, 85, 247, 0.3)",
	DELETE: "rgba(239, 68, 68, 0.3)",
};

const METHOD_ORDER = ["GET", "POST", "PUT", "PATCH", "DELETE"];

const EndpointPicker: React.FC<EndpointPickerProps> = ({
	value,
	onChange,
	endpoints,
	placeholder = "Select a saved API endpoint...",
	variant = "default",
}) => {
	const isLight = variant === "light";
	const [isOpen, setIsOpen] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");
	const [dropdownPosition, setDropdownPosition] = useState({
		top: 0,
		left: 0,
		width: 0,
	});
	const [hoveredId, setHoveredId] = useState<string | null>(null);

	const containerRef = useRef<HTMLDivElement>(null);
	const buttonRef = useRef<HTMLDivElement>(null);
	const searchInputRef = useRef<HTMLInputElement>(null);

	const selectedEndpoint = useMemo(
		() => endpoints.find((ep) => ep.id === value),
		[value, endpoints],
	);

	const toggleDropdown = useCallback(() => setIsOpen((prev) => !prev), []);
	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) =>
			setSearchQuery(e.target.value),
		[],
	);
	const clearSearch = useCallback(() => setSearchQuery(""), []);

	const handleSelect = useCallback(
		(endpointId: string) => {
			onChange(endpointId);
			setIsOpen(false);
			setSearchQuery("");
		},
		[onChange],
	);

	const createHoverHandler = useCallback(
		(id: string) => () => setHoveredId(id),
		[],
	);
	const clearHover = useCallback(() => setHoveredId(null), []);

	// Filter and group endpoints by method
	const groupedEndpoints = useMemo(() => {
		const filtered = endpoints.filter((ep) => {
			if (!searchQuery) return true;
			const q = searchQuery.trim().toLowerCase();
			return (
				ep.name.toLowerCase().includes(q) ||
				ep.url_template.toLowerCase().includes(q) ||
				ep.method.toLowerCase().includes(q) ||
				(ep.description?.toLowerCase().includes(q) ?? false)
			);
		});

		const groups: Record<string, EndpointItem[]> = {};
		for (const ep of filtered) {
			const method = ep.method.toUpperCase();
			if (!groups[method]) groups[method] = [];
			groups[method].push(ep);
		}

		// Sort by standard method order, unknown methods at end
		const sortedMethods = Object.keys(groups).sort((a, b) => {
			const ia = METHOD_ORDER.indexOf(a);
			const ib = METHOD_ORDER.indexOf(b);
			return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
		});

		return { groups, sortedMethods, totalCount: filtered.length };
	}, [endpoints, searchQuery]);

	// Position dropdown below trigger
	useEffect(() => {
		if (isOpen && buttonRef.current) {
			const rect = buttonRef.current.getBoundingClientRect();
			setDropdownPosition({
				top: rect.bottom + 4,
				left: rect.left,
				width: rect.width,
			});
			setTimeout(() => searchInputRef.current?.focus(), 100);
		}
	}, [isOpen]);

	// Close on click outside
	useEffect(() => {
		if (!isOpen) return;
		const handleClickOutside = (event: MouseEvent) => {
			const target = event.target as HTMLElement;
			const dropdown = document.querySelector(
				"[data-endpoint-picker-dropdown]",
			);
			if (
				containerRef.current &&
				!containerRef.current.contains(target) &&
				(!dropdown || !dropdown.contains(target))
			) {
				setIsOpen(false);
				setSearchQuery("");
			}
		};
		document.addEventListener("mousedown", handleClickOutside);
		return () =>
			document.removeEventListener("mousedown", handleClickOutside);
	}, [isOpen]);

	const renderMethodBadge = (method: string, size: "sm" | "md" = "sm") => (
		<span
			className={`${size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-0.5 text-xs"} rounded-[4px] font-bold capitalize flex-shrink-0`}
			style={{
				background: METHOD_COLORS[method] || "var(--color-surface)",
				color:
					METHOD_TEXT_COLORS[method] || "var(--color-text-primary)",
				border: `1px solid ${METHOD_BORDERS[method] || "var(--color-border)"}`,
			}}
		>
			{method}
		</span>
	);

	const renderEndpointItem = (ep: EndpointItem) => {
		const isSelected = value === ep.id;
		const isHovered = hoveredId === ep.id;

		return (
			<div
				key={ep.id}
				className={cn(
					"cursor-pointer rounded-[4px] px-3 py-2.5 transition-colors duration-150",
					isSelected
						? isLight
							? "border border-gray-200 bg-white"
							: "border border-[color:var(--color-primary)]/50 bg-[rgba(var(--color-primary-rgb),0.15)]"
						: isHovered
							? isLight
								? "border border-gray-200 bg-white shadow-sm"
								: "border border-[color:var(--color-border)] bg-[color:var(--color-surface)]"
							: isLight
								? "border border-transparent hover:border-gray-200 hover:bg-white"
								: "border border-transparent hover:bg-[color:var(--color-surface)]",
				)}
				onClick={() => handleSelect(ep.id)}
				onMouseEnter={createHoverHandler(ep.id)}
				onMouseLeave={clearHover}
			>
				<div className="flex items-center gap-3">
					{renderMethodBadge(ep.method)}
					<div className="min-w-0 flex-1">
						<span
							className={cn(
								"block truncate text-sm font-medium",
								isSelected
									? isLight
										? "text-gray-900"
										: "text-[color:var(--color-primary-light)]"
									: isLight
										? "text-gray-900"
										: "text-slate-900",
							)}
						>
							{ep.name}
						</span>
						<span className="mt-0.5 block truncate font-mono text-xs text-gray-500">
							{ep.url_template}
						</span>
					</div>
					{isSelected && (
						<ChevronRight
							className={cn(
								"h-4 w-4 shrink-0",
								isLight ? "text-gray-700" : "text-[color:var(--color-primary)]",
							)}
						/>
					)}
				</div>
			</div>
		);
	};

	const renderSection = (method: string, items: EndpointItem[]) => {
		if (items.length === 0) return null;
		return (
			<div key={method} className="mb-2">
				<div className="px-3 py-2 text-xs font-medium flex items-center gap-2 text-[color:var(--color-text-muted)]">
					{renderMethodBadge(method)}
					<span className="text-[#606060]">({items.length})</span>
				</div>
				<div className="space-y-1">{items.map(renderEndpointItem)}</div>
			</div>
		);
	};

	return (
		<div ref={containerRef} className="relative">
			{/* Trigger Button */}
			<div
				ref={buttonRef}
				onClick={toggleDropdown}
				className={cn(
					"group flex w-full cursor-pointer items-center justify-between rounded-[4px] border px-3 py-2.5 text-sm transition-colors duration-200",
					isLight
								? "border-gray-200 bg-white text-gray-900 hover:border-gray-300 hover:bg-white"
						: "border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-slate-900 hover:border-[color:var(--color-primary)]/50",
				)}
			>
				<div className="flex items-center gap-2 flex-1 min-w-0">
					{selectedEndpoint ? (
						<>
							{renderMethodBadge(selectedEndpoint.method, "md")}
							<div className="flex-1 min-w-0">
								<span className="font-medium truncate block">
									{selectedEndpoint.name}
								</span>
								<span className="text-xs text-[color:var(--color-text-muted)] font-mono truncate block">
									{selectedEndpoint.url_template}
								</span>
							</div>
						</>
					) : (
						<span className="text-[color:var(--color-text-muted)]">
							{placeholder}
						</span>
					)}
				</div>
				<ChevronDown
					className={cn(
						"ml-2 h-4 w-4 shrink-0 transition-transform duration-200",
						isLight
							? "text-gray-500 group-hover:text-slate-900"
							: "text-[color:var(--color-text-muted)] group-hover:text-[color:var(--color-primary)]",
						isOpen ? "rotate-180" : "",
					)}
				/>
			</div>

			{/* Dropdown Portal */}
			{isOpen &&
				createPortal(
					<div
						className={cn(
							"fixed overflow-hidden rounded-[4px] border",
							isLight
								? "border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
								: "border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] shadow-2xl",
						)}
						style={{
							top: `${dropdownPosition.top}px`,
							left: `${dropdownPosition.left}px`,
							width: `${dropdownPosition.width}px`,
							maxHeight: "420px",
							zIndex: 99999,
						}}
						data-endpoint-picker-dropdown
					>
						{/* Search Bar */}
						<div
							className={cn(
								"border-b p-3",
								isLight
									? "border-gray-200 bg-white"
									: "border-[color:var(--color-border)] bg-[color:var(--color-surface)]/50",
							)}
						>
							<div className="relative">
								<Search
									className={cn(
										"absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2",
										isLight ? "text-gray-500" : "text-[color:var(--color-text-muted)]",
									)}
								/>
								<input
									ref={searchInputRef}
									type="text"
									value={searchQuery}
									onChange={handleSearchChange}
									placeholder="Search endpoints..."
									aria-label="Search endpoints"
									className={cn(
										"w-full rounded-[4px] border py-2 pl-10 pr-8 text-sm focus:outline-none",
										isLight
											? "border-gray-200 bg-white text-gray-900 placeholder:text-gray-400 focus:border-orange-400 focus:ring-1 focus:ring-orange-400/40"
											: "border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] text-white placeholder-[#606060] focus:border-[color:var(--color-primary)] focus:ring-1 focus:ring-[color:var(--color-primary)]",
									)}
								/>
								{searchQuery && (
									<button
										type="button"
										onClick={clearSearch}
										className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-[color:var(--color-border)] rounded-[4px] transition-colors"
									>
										<X className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
									</button>
								)}
							</div>
						</div>

						{/* Options List */}
						<div className="overflow-y-auto max-h-[340px] py-2">
							{/* None option */}
							<div
								className={cn(
									"mx-1 mb-1 cursor-pointer rounded-[4px] px-3 py-2.5 transition-colors duration-150",
									!value
										? isLight
												? "border border-gray-200 bg-white"
											: "border border-[color:var(--color-primary)]/50 bg-[rgba(var(--color-primary-rgb),0.15)]"
										: isLight
												? "border border-transparent hover:bg-white"
											: "border border-transparent hover:bg-[color:var(--color-surface)]",
								)}
								onClick={() => handleSelect("")}
							>
								<div className="flex items-center gap-2">
									<Link
										className={cn(
											"h-4 w-4",
											isLight ? "text-gray-500" : "text-[color:var(--color-text-muted)]",
										)}
									/>
									<span
										className={cn(
											"text-sm",
											!value
												? isLight
													? "font-medium text-gray-900"
													: "font-medium text-[color:var(--color-primary-light)]"
												: isLight
													? "text-gray-700"
													: "text-[color:var(--color-text-secondary)]",
										)}
									>
										None (configure manually)
									</span>
									{!value && (
										<ChevronRight
											className={cn(
												"ml-auto h-4 w-4 shrink-0",
												isLight ? "text-gray-700" : "text-[color:var(--color-primary)]",
											)}
										/>
									)}
								</div>
							</div>

							{/* Separator */}
							{endpoints.length > 0 && (
								<div className="mx-3 my-1 border-t border-[color:var(--color-border)]/50" />
							)}

							{/* Grouped Endpoints */}
							{groupedEndpoints.totalCount === 0 &&
							endpoints.length > 0 ? (
								<div className="px-3 py-6 text-center">
									<p className="text-sm text-[color:var(--color-text-muted)]">
										No endpoints match &ldquo;{searchQuery}
										&rdquo;
									</p>
								</div>
							) : (
								groupedEndpoints.sortedMethods.map((method) =>
									renderSection(
										method,
										groupedEndpoints.groups[method],
									),
								)
							)}
						</div>
					</div>,
					document.body,
				)}
		</div>
	);
};

export default EndpointPicker;
