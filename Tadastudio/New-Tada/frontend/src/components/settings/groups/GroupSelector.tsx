"use client";

import { Check, ChevronDown, Folder, Globe, Search, Shield, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "@/lib/api";
import type { Group } from "@/types/api";

interface GroupSelectorProps {
	selectedGroups: string[];
	onChange: (groups: string[]) => void;
	placeholder?: string;
	disabled?: boolean;
}

function getGroupIcon(name: string) {
	if (name === "__all__") return <Globe className="w-3.5 h-3.5" />;
	if (name === "admins") return <Shield className="w-3.5 h-3.5" />;
	return <Folder className="w-3.5 h-3.5" />;
}

function getGroupDisplayName(name: string) {
	if (name === "__all__") return "Everyone";
	if (name === "admins") return "Admins";
	return name;
}

export default function GroupSelector({
	selectedGroups,
	onChange,
	placeholder = "Select groups...",
	disabled = false,
}: GroupSelectorProps) {
	const [groups, setGroups] = useState<Group[]>([]);
	const [isOpen, setIsOpen] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");
	const triggerRef = useRef<HTMLButtonElement>(null);
	const dropdownRef = useRef<HTMLDivElement>(null);
	const [dropdownPos, setDropdownPos] = useState({ top: 0, left: 0, width: 0 });

	useEffect(() => {
		api.getGroups()
			.then((data) => setGroups(data.groups))
			.catch(() => {});
	}, []);

	useEffect(() => {
		if (isOpen && triggerRef.current) {
			const rect = triggerRef.current.getBoundingClientRect();
			setDropdownPos({
				top: rect.bottom + 4,
				left: rect.left,
				width: rect.width,
			});
		}
	}, [isOpen]);

	useEffect(() => {
		if (!isOpen) return;
		const handleClickOutside = (e: MouseEvent) => {
			if (
				dropdownRef.current &&
				!dropdownRef.current.contains(e.target as Node) &&
				triggerRef.current &&
				!triggerRef.current.contains(e.target as Node)
			) {
				setIsOpen(false);
			}
		};
		const handleScroll = (e: Event) => {
			// Don't close if scrolling inside the dropdown itself
			if (dropdownRef.current?.contains(e.target as Node)) return;
			setIsOpen(false);
		};
		document.addEventListener("mousedown", handleClickOutside);
		document.addEventListener("scroll", handleScroll, true);
		return () => {
			document.removeEventListener("mousedown", handleClickOutside);
			document.removeEventListener("scroll", handleScroll, true);
		};
	}, [isOpen]);

	const toggleGroup = (groupName: string) => {
		if (selectedGroups.includes(groupName)) {
			onChange(selectedGroups.filter((g) => g !== groupName));
		} else {
			onChange([...selectedGroups, groupName]);
		}
	};

	const removeGroup = (groupName: string, e: React.MouseEvent) => {
		e.stopPropagation();
		onChange(selectedGroups.filter((g) => g !== groupName));
	};

	// Always include an "Everyone" option so users can make items visible to all
	const hasAllGroup = groups.some((g) => g.name === "__all__");
	const everyoneGroup: Group = { id: "__all__", name: "__all__", is_system: true, member_count: 0, created_at: "" };
	const allGroups = hasAllGroup ? groups : [everyoneGroup, ...groups];

	const systemGroups = allGroups.filter((g) => g.is_system);
	const customGroups = allGroups.filter((g) => !g.is_system);

	const filterBySearch = (g: Group) => {
		if (!searchQuery) return true;
		const query = searchQuery.trim().toLowerCase();
		const displayName = getGroupDisplayName(g.name).toLowerCase();
		return displayName.includes(query) || g.name.toLowerCase().includes(query);
	};

	const filteredSystemGroups = systemGroups.filter(filterBySearch);
	const filteredCustomGroups = customGroups.filter(filterBySearch);

	return (
		<div className="relative">
			{/* Trigger Button */}
			<button
				ref={triggerRef}
				type="button"
				disabled={disabled}
				onClick={() => setIsOpen(!isOpen)}
				className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors min-h-[38px]"
				style={{
					background: "var(--color-bg-secondary)",
					border: "1px solid var(--color-border)",
					color: "var(--color-text-primary)",
					opacity: disabled ? 0.5 : 1,
					cursor: disabled ? "not-allowed" : "pointer",
				}}
			>
				<div className="flex flex-wrap items-center gap-1 flex-1 min-w-0">
					{selectedGroups.length === 0 ? (
						<span style={{ color: "var(--color-text-muted)" }}>
							{placeholder}
						</span>
					) : (
						selectedGroups.map((name) => (
							<span
								key={name}
								className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
								style={{
									background: "rgba(var(--color-primary-rgb), 0.15)",
									color: "var(--color-accent)",
									border: "1px solid rgba(var(--color-primary-rgb), 0.3)",
								}}
							>
								{getGroupIcon(name)}
								{getGroupDisplayName(name)}
								{!disabled && (
									<span
										role="button"
										tabIndex={0}
										onClick={(e) => removeGroup(name, e)}
										onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); removeGroup(name, e as unknown as React.MouseEvent); } }}
										className="ml-0.5 hover:opacity-70 cursor-pointer"
									>
										<X className="w-3 h-3" />
									</span>
								)}
							</span>
						))
					)}
				</div>
				<ChevronDown
					className="w-4 h-4 shrink-0 ml-2"
					style={{ color: "var(--color-text-muted)" }}
				/>
			</button>

			{/* Dropdown Portal */}
			{isOpen &&
				createPortal(
					<div
						ref={dropdownRef}
						className="fixed z-[9999] rounded-lg shadow-xl overflow-hidden"
						style={{
							top: dropdownPos.top,
							left: dropdownPos.left,
							width: dropdownPos.width,
							background: "var(--color-bg-primary)",
							border: "1px solid var(--color-border)",
						}}
					>
						{/* Search */}
						<div
							className="p-2"
							style={{
								borderBottom: "1px solid var(--color-border)",
							}}
						>
							<div className="relative">
								<Search
									className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5"
									style={{ color: "var(--color-text-muted)" }}
								/>
								<input
									type="text"
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									placeholder="Search groups..."
									className="w-full pl-8 pr-3 py-1.5 rounded text-xs outline-none"
									style={{
										background: "var(--color-bg-secondary)",
										border: "1px solid var(--color-border)",
										color: "var(--color-text-primary)",
									}}
									autoFocus
								/>
							</div>
						</div>

						{/* Groups List */}
						<div className="max-h-60 overflow-y-auto p-1">
							{/* System Groups */}
							{filteredSystemGroups.length > 0 && (
								<>
									<div
										className="px-3 py-1.5 text-[10px] font-semibold capitalize tracking-wider"
										style={{ color: "var(--color-text-muted)" }}
									>
										System Groups
									</div>
									{filteredSystemGroups.map((group) => {
										const isSelected = selectedGroups.includes(
											group.name,
										);
										return (
											<button
												key={group.id}
												type="button"
												className="w-full flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors"
												style={{
													color: "var(--color-text-primary)",
													background: isSelected
														? "rgba(var(--color-primary-rgb), 0.1)"
														: "transparent",
												}}
												onClick={() => toggleGroup(group.name)}
												onMouseEnter={(e) => {
													if (!isSelected) {
														e.currentTarget.style.background =
															"var(--color-bg-secondary)";
													}
												}}
												onMouseLeave={(e) => {
													if (!isSelected) {
														e.currentTarget.style.background =
															"transparent";
													}
												}}
											>
												{getGroupIcon(group.name)}
												<span className="flex-1 text-left">
													{getGroupDisplayName(group.name)}
												</span>
												{isSelected && (
													<Check
														className="w-4 h-4"
														style={{
															color: "var(--color-accent)",
														}}
													/>
												)}
											</button>
										);
									})}
								</>
							)}

							{/* Custom Groups */}
							{filteredCustomGroups.length > 0 && (
								<>
									<div
										className="px-3 py-1.5 text-[10px] font-semibold capitalize tracking-wider mt-1"
										style={{ color: "var(--color-text-muted)" }}
									>
										Custom Groups
									</div>
									{filteredCustomGroups.map((group) => {
										const isSelected = selectedGroups.includes(
											group.name,
										);
										return (
											<button
												key={group.id}
												type="button"
												className="w-full flex items-center gap-2.5 px-3 py-2 rounded text-sm transition-colors"
												style={{
													color: "var(--color-text-primary)",
													background: isSelected
														? "rgba(var(--color-primary-rgb), 0.1)"
														: "transparent",
												}}
												onClick={() => toggleGroup(group.name)}
												onMouseEnter={(e) => {
													if (!isSelected) {
														e.currentTarget.style.background =
															"var(--color-bg-secondary)";
													}
												}}
												onMouseLeave={(e) => {
													if (!isSelected) {
														e.currentTarget.style.background =
															"transparent";
													}
												}}
											>
												{getGroupIcon(group.name)}
												<span className="flex-1 text-left">
													{getGroupDisplayName(group.name)}
												</span>
												{isSelected && (
													<Check
														className="w-4 h-4"
														style={{
															color: "var(--color-accent)",
														}}
													/>
												)}
											</button>
										);
									})}
								</>
							)}

							{filteredSystemGroups.length === 0 &&
								filteredCustomGroups.length === 0 && (
									<p
										className="text-xs text-center py-4"
										style={{ color: "var(--color-text-muted)" }}
									>
										No groups found
									</p>
								)}
						</div>
					</div>,
					document.body,
				)}
		</div>
	);
}
