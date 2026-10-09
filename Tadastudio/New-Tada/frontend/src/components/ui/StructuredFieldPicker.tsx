"use client";

import {
	AlertCircle,
	Calendar,
	Check,
	ChevronDown,
	ChevronRight,
	Code,
	Hash,
	List,
	Search,
	Sparkles,
	ToggleLeft,
	Type,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface StructuredField {
	id: string;
	name: string;
	type: string;
	description?: string;
	required?: boolean;
	fields?: StructuredField[]; // For nested objects
}

interface StructuredFieldPickerProps {
	fields: StructuredField[];
	value?: string;
	onChange: (fieldPath: string) => void;
	placeholder?: string;
	allowManualInput?: boolean;
	nodeId?: string;
	nodeName?: string;
}

export default function StructuredFieldPicker({
	fields,
	value = "",
	onChange,
	placeholder = "Select a field or enter path",
	allowManualInput = true,
	nodeId,
	nodeName,
}: StructuredFieldPickerProps) {
	const [isOpen, setIsOpen] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");
	const [manualMode, setManualMode] = useState(false);
	const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
	const [dropdownPosition, setDropdownPosition] = useState({
		top: 0,
		left: 0,
		width: 0,
	});
	const containerRef = useRef<HTMLDivElement>(null);
	const buttonRef = useRef<HTMLDivElement>(null);
	const inputRef = useRef<HTMLInputElement>(null);

	// Memoized event handlers
	const toggleDropdown = useCallback(() => setIsOpen(!isOpen), [isOpen]);
	const enableManualMode = useCallback(() => {
		setManualMode(true);
		setIsOpen(false);
	}, []);
	const enableManualModeWithFocus = useCallback(() => {
		setManualMode(true);
		setIsOpen(false);
		setTimeout(() => inputRef.current?.focus(), 100);
	}, []);
	const disableManualMode = useCallback(() => setManualMode(false), []);
	const handleInputChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => onChange(e.target.value),
		[onChange],
	);
	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value),
		[],
	);
	const stopPropagation = useCallback(
		(e: React.MouseEvent | React.WheelEvent) => e.stopPropagation(),
		[],
	);

	const createFieldClickHandler = useCallback(
		(fullPath: string, hasNested: boolean, isExpanded: boolean) => () => {
			if (!hasNested || !isExpanded) {
				onChange(fullPath);
				setIsOpen(false);
				setSearchQuery("");
			}

			if (hasNested) {
				const newExpanded = new Set(expandedPaths);
				if (isExpanded) {
					newExpanded.delete(fullPath);
				} else {
					newExpanded.add(fullPath);
				}
				setExpandedPaths(newExpanded);
			}
		},
		[onChange, expandedPaths],
	);

	const createExpanderClickHandler = useCallback(
		(fullPath: string, isExpanded: boolean) => (e: React.MouseEvent) => {
			e.stopPropagation();
			const newExpanded = new Set(expandedPaths);
			if (isExpanded) {
				newExpanded.delete(fullPath);
			} else {
				newExpanded.add(fullPath);
			}
			setExpandedPaths(newExpanded);
		},
		[expandedPaths],
	);

	// Update dropdown position when opened
	useEffect(() => {
		if (isOpen && buttonRef.current) {
			const rect = buttonRef.current.getBoundingClientRect();
			setDropdownPosition({
				top: rect.bottom + 4,
				left: rect.left,
				width: rect.width,
			});
		}
	}, [isOpen]);

	// Close dropdown when clicking outside
	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			const target = event.target as Node;
			const dropdown = document.querySelector("[data-field-picker-dropdown]");

			if (
				containerRef.current &&
				!containerRef.current.contains(target) &&
				(!dropdown || !dropdown.contains(target))
			) {
				setIsOpen(false);
				setSearchQuery("");
			}
		};

		const handleScroll = (event: Event) => {
			// Only close if the scroll is not from the dropdown itself
			const target = event.target as Node;
			const dropdown = document.querySelector("[data-field-picker-dropdown]");

			if (isOpen && dropdown && !dropdown.contains(target)) {
				setIsOpen(false);
			}
		};

		document.addEventListener("mousedown", handleClickOutside);
		window.addEventListener("scroll", handleScroll, true);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
			window.removeEventListener("scroll", handleScroll, true);
		};
	}, [isOpen]);

	const getFieldIcon = (type: string) => {
		const lowerType = type.toLowerCase();
		if (lowerType === "string" || lowerType === "str")
			return <Type className="w-3.5 h-3.5 text-emerald-400" />;
		if (
			lowerType === "number" ||
			lowerType === "integer" ||
			lowerType === "float"
		)
			return <Hash className="w-3.5 h-3.5 text-purple-400" />;
		if (lowerType === "boolean" || lowerType === "bool")
			return <ToggleLeft className="w-3.5 h-3.5 text-[#0DA931]" />;
		if (lowerType === "date" || lowerType === "datetime")
			return (
				<Calendar className="w-3.5 h-3.5 text-[color:var(--color-accent)]" />
			);
		if (lowerType === "array" || lowerType === "list")
			return <List className="w-3.5 h-3.5 text-orange-400" />;
		if (lowerType === "object" || lowerType === "dict")
			return <Code className="w-3.5 h-3.5 text-[color:var(--color-accent)]" />;
		return (
			<Code className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
		);
	};

	const getTypeColor = (type: string) => {
		const lowerType = type.toLowerCase();
		if (lowerType === "string" || lowerType === "str")
			return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
		if (
			lowerType === "number" ||
			lowerType === "integer" ||
			lowerType === "float"
		)
			return "bg-purple-500/20 text-purple-400 border-purple-500/30";
		if (lowerType === "boolean" || lowerType === "bool")
			return "bg-[#0DA931]/20 text-[#0DA931] border-[#0DA931]/30";
		if (lowerType === "date" || lowerType === "datetime")
			return "bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] border-[color:var(--color-border)]/35";
		if (lowerType === "array" || lowerType === "list")
			return "bg-orange-500/20 text-orange-400 border-orange-500/30";
		if (lowerType === "object" || lowerType === "dict")
			return "bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] border-[color:var(--color-border)]/30";
		return "bg-gray-500/20 text-gray-400 border-gray-500/30";
	};

	const filterFields = (
		fields: StructuredField[],
		query: string,
		parentPath = "",
	): StructuredField[] => {
		if (!query) return fields;

		return fields.filter((field) => {
			const fullPath = parentPath ? `${parentPath}.${field.name}` : field.name;
			const matchesQuery =
				field.name.toLowerCase().includes(query.toLowerCase()) ||
				field.description?.toLowerCase().includes(query.toLowerCase()) ||
				fullPath.toLowerCase().includes(query.toLowerCase());

			if (matchesQuery) return true;

			// Check nested fields
			if (field.fields && field.fields.length > 0) {
				const nestedMatches = filterFields(field.fields, query, fullPath);
				return nestedMatches.length > 0;
			}

			return false;
		});
	};

	const toggleExpanded = (path: string) => {
		const newExpanded = new Set(expandedPaths);
		if (newExpanded.has(path)) {
			newExpanded.delete(path);
		} else {
			newExpanded.add(path);
		}
		setExpandedPaths(newExpanded);
	};

	const renderField = (field: StructuredField, parentPath = "", depth = 0) => {
		const fullPath = parentPath ? `${parentPath}.${field.name}` : field.name;
		const hasNested = Boolean(field.fields && field.fields.length > 0);
		const isExpanded = expandedPaths.has(fullPath);

		return (
			<div key={field.id || fullPath}>
				<div
					className={`flex items-center gap-2 px-3 py-2.5 hover:bg-[color:var(--color-surface)] rounded-lg cursor-pointer transition-all duration-200 group ${
						value === fullPath
							? "bg-emerald-900/30 border border-emerald-500/50 shadow-lg shadow-emerald-500/10"
							: "hover:bg-[color:var(--color-surface)]"
					}`}
					style={{ paddingLeft: `${12 + depth * 16}px` }}
					onClick={createFieldClickHandler(fullPath, hasNested, isExpanded)}
				>
					{hasNested && (
						<button
							onClick={createExpanderClickHandler(fullPath, isExpanded)}
							className="p-0.5 hover:bg-[color:var(--color-border)] rounded transition-colors"
						>
							<ChevronRight
								className={`w-3 h-3 text-[color:var(--color-text-muted)] transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`}
							/>
						</button>
					)}

					{getFieldIcon(field.type)}

					<span
						className={`flex-1 text-sm transition-colors ${
							value === fullPath
								? "text-emerald-400 font-medium"
								: "text-slate-700 group-hover:text-slate-900"
						}`}
					>
						{field.name}
					</span>

					{value === fullPath && (
						<Check className="w-3.5 h-3.5 text-emerald-400" />
					)}

					<span
						className={`text-xs px-1.5 py-0.5 rounded border ${getTypeColor(field.type)}`}
					>
						{field.type}
					</span>

					{field.required && (
						<span className="text-xs px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded border border-red-500/30">
							Required
						</span>
					)}
				</div>

				{field.description && (
					<div
						className={`px-4 py-1 text-xs text-[color:var(--color-text-muted)] transition-all duration-200 ${
							value === fullPath
								? "opacity-100 max-h-20"
								: "opacity-0 max-h-0 overflow-hidden"
						}`}
						style={{ paddingLeft: `${28 + depth * 16}px` }}
					>
						<div className="flex items-start gap-1">
							<AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
							{field.description}
						</div>
					</div>
				)}

				{hasNested && isExpanded && (
					<div className="border-l border-[color:var(--color-border)] ml-6">
						{field.fields!.map((nestedField) =>
							renderField(nestedField, fullPath, depth + 1),
						)}
					</div>
				)}
			</div>
		);
	};

	const filteredFields = filterFields(fields, searchQuery);

	if (manualMode && allowManualInput) {
		return (
			<div className="relative">
				<div className="flex gap-2">
					<input
						ref={inputRef}
						type="text"
						value={value}
						onChange={handleInputChange}
						aria-label="Manual field path input"
						className="flex-1 px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none font-mono"
						placeholder="e.g., customer.name or items[0].price"
					/>
					<button
						onClick={disableManualMode}
						className="px-3 py-2 bg-[color:var(--color-surface)] hover:bg-[color:var(--color-border)] border border-[color:var(--color-border)] rounded-lg text-[color:var(--color-text-secondary)] text-sm transition-colors"
					>
						Pick Field
					</button>
				</div>
				<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
					Enter field path manually. Use dot notation for nested fields.
				</p>
			</div>
		);
	}

	return (
		<div ref={containerRef} className="relative">
			<div
				ref={buttonRef}
				onClick={toggleDropdown}
				className="w-full px-3 py-2.5 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none cursor-pointer flex items-center justify-between hover:border-emerald-500/50 transition-all duration-200 group"
			>
				<div className="flex items-center gap-2 flex-1">
					{value && <Sparkles className="w-3.5 h-3.5 text-emerald-400" />}
					<span
						className={
							value
								? "font-mono text-emerald-400"
								: "text-[color:var(--color-text-muted)]"
						}
					>
						{value || placeholder}
					</span>
				</div>
				<ChevronDown
					className={`w-4 h-4 text-[color:var(--color-text-muted)] transition-transform duration-200 group-hover:text-emerald-400 ${isOpen ? "rotate-180" : ""}`}
				/>
			</div>

			{nodeName && (
				<div className="mt-1 flex items-center gap-1">
					<Code className="w-3 h-3 text-emerald-400" />
					<p className="text-xs text-[color:var(--color-text-muted)]">
						Source:{" "}
						<span className="text-emerald-400 font-medium">{nodeName}</span>
					</p>
				</div>
			)}

			{isOpen &&
				createPortal(
					<div
						className="fixed bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg shadow-xl overflow-hidden flex flex-col"
						style={{
							top: `${dropdownPosition.top}px`,
							left: `${dropdownPosition.left}px`,
							width: `${dropdownPosition.width}px`,
							maxHeight: "400px",
							zIndex: 99999,
						}}
						data-field-picker-dropdown
					>
						{/* Header with field count */}
						<div className="px-3 py-2 bg-[color:var(--color-surface)] border-b border-[color:var(--color-border)] flex items-center justify-between">
							<span className="text-xs font-medium text-emerald-400 flex items-center gap-1">
								<Sparkles className="w-3 h-3" />
								Structured Fields ({fields.length})
							</span>
							{fields.filter((f) => f.required).length > 0 && (
								<span className="text-xs text-red-400">
									{fields.filter((f) => f.required).length} required
								</span>
							)}
						</div>

						{/* Search bar */}
						<div className="p-2 border-b border-[color:var(--color-border)]">
							<div className="relative">
								<Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
								<input
									type="text"
									value={searchQuery}
									onChange={handleSearchChange}
									aria-label="Search fields"
									className="w-full pl-8 pr-3 py-1.5 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none placeholder-[color:var(--color-text-muted)]"
									placeholder="Search fields..."
									onClick={stopPropagation}
									autoFocus
								/>
							</div>
						</div>

						{/* Manual input option */}
						{allowManualInput && (
							<div className="px-2 py-1.5 border-b border-[color:var(--color-border)] flex-none">
								<button
									onClick={enableManualModeWithFocus}
									className="w-full px-3 py-1.5 bg-[color:var(--color-surface)] hover:bg-[color:var(--color-border)] rounded-lg text-xs text-[color:var(--color-text-secondary)] transition-colors flex items-center justify-center gap-2"
								>
									<Code className="w-3 h-3" />
									Enter Custom Path Manually
								</button>
							</div>
						)}

						{/* Fields list */}
						<div
							className="flex-1 min-h-0 overflow-y-auto py-2"
							onWheel={stopPropagation}
						>
							{filteredFields.length > 0 ? (
								<div className="px-2">
									{filteredFields.map((field) => renderField(field))}
								</div>
							) : (
								<div className="px-3 py-8 text-center">
									<AlertCircle className="w-8 h-8 text-[color:var(--color-text-muted)] mx-auto mb-2" />
									<div className="text-sm text-[color:var(--color-text-muted)]">
										{searchQuery
											? "No fields match your search"
											: "No structured fields available"}
									</div>
								</div>
							)}
						</div>
					</div>,
					document.body,
				)}
		</div>
	);
}
