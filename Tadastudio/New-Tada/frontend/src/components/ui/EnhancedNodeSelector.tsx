"use client";

import {
	AlertCircle,
	ChevronDown,
	ChevronRight,
	Clock,
	Cpu,
	Database,
	FileText,
	GitBranch,
	Globe,
	Mail,
	Search,
	Settings,
	Sparkles,
	Star,
	X,
	Zap,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Node } from "reactflow";

interface EnhancedNodeSelectorProps {
	value?: string;
	onChange: (nodeId: string) => void;
	nodes: Node[];
	placeholder?: string;
	className?: string;
	showStructuredIndicator?: boolean;
}

// Get icon for node type
const getNodeIcon = (nodeType?: string, nodeData?: any) => {
	// Check for specific node configurations first
	if (nodeData?.email_send_config)
		return <Mail className="w-4 h-4 text-gray-400" />;
	if (nodeData?.file_read_config)
		return <FileText className="w-4 h-4 text-orange-400" />;
	if (nodeData?.database_query_config)
		return <Database className="w-4 h-4 text-blue-400" />;
	if (nodeData?.http_request_config)
		return <Globe className="w-4 h-4 text-[#0DA931]" />;

	// Check by node type
	switch (nodeType) {
		case "AGENT":
			return <Cpu className="w-4 h-4 text-purple-400" />;
		case "TOOL":
			return <Settings className="w-4 h-4 text-blue-400" />;
		case "CONDITION":
			return <GitBranch className="w-4 h-4 text-[color:var(--color-accent)]" />;
		case "HUMAN":
			return <AlertCircle className="w-4 h-4 text-orange-400" />;
		case "START":
			return <Zap className="w-4 h-4 text-[#0DA931]" />;
		default:
			return <Settings className="w-4 h-4 text-gray-400" />;
	}
};

// Get node type label
const getNodeTypeLabel = (nodeType?: string, nodeData?: any) => {
	// Check for specific configurations
	if (nodeData?.email_send_config) return "Email";
	if (nodeData?.file_read_config) return "File";
	if (nodeData?.database_query_config) return "Database";
	if (nodeData?.http_request_config) return "HTTP";

	switch (nodeType) {
		case "AGENT":
			return "Agent";
		case "TOOL":
			return "Tool";
		case "CONDITION":
			return "Condition";
		case "HUMAN":
			return "Human";
		case "START":
			return "Start";
		default:
			return "Node";
	}
};

// Get type color class
const getTypeColorClass = (nodeType?: string, nodeData?: any) => {
	if (nodeData?.email_send_config)
		return "bg-gray-500/20 text-gray-400 border-gray-500/30";
	if (nodeData?.file_read_config)
		return "bg-orange-500/20 text-orange-400 border-orange-500/30";
	if (nodeData?.database_query_config)
		return "bg-blue-500/20 text-blue-400 border-blue-500/30";
	if (nodeData?.http_request_config)
		return "bg-[#0DA931]/20 text-[#0DA931] border-[#0DA931]/30";

	switch (nodeType) {
		case "AGENT":
			return "bg-purple-500/20 text-purple-400 border-purple-500/30";
		case "TOOL":
			return "bg-blue-500/20 text-blue-400 border-blue-500/30";
		case "CONDITION":
			return "bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] border-[color:var(--color-border)]/35";
		case "HUMAN":
			return "bg-orange-500/20 text-orange-400 border-orange-500/30";
		case "START":
			return "bg-[#0DA931]/20 text-[#0DA931] border-[#0DA931]/30";
		default:
			return "bg-gray-500/20 text-gray-400 border-gray-500/30";
	}
};

const EnhancedNodeSelector: React.FC<EnhancedNodeSelectorProps> = ({
	value,
	onChange,
	nodes,
	placeholder = "Select a node...",
	className = "",
	showStructuredIndicator = true,
}) => {
	const [isOpen, setIsOpen] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");
	const [dropdownPosition, setDropdownPosition] = useState({
		top: 0,
		left: 0,
		width: 0,
	});
	const [recentNodes, setRecentNodes] = useState<string[]>([]);
	const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

	const containerRef = useRef<HTMLDivElement>(null);
	const buttonRef = useRef<HTMLDivElement>(null);
	const searchInputRef = useRef<HTMLInputElement>(null);

	// Get selected node
	const selectedNode = useMemo(() => {
		return nodes.find((n) => n.id === value);
	}, [value, nodes]);

	// Memoized event handlers
	const toggleDropdown = useCallback(() => setIsOpen(!isOpen), [isOpen]);
	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value),
		[],
	);
	const clearSearch = useCallback(() => setSearchQuery(""), []);
	const createNodeSelectHandler = useCallback(
		(nodeId: string) => () => {
			onChange(nodeId);
			setIsOpen(false);
			setSearchQuery("");
		},
		[onChange],
	);
	const createHoverHandler = useCallback(
		(nodeId: string) => () => setHoveredNodeId(nodeId),
		[],
	);
	const clearHover = useCallback(() => setHoveredNodeId(null), []);

	// Load recent nodes from localStorage
	useEffect(() => {
		const stored = localStorage.getItem("recentNodeSelections");
		if (stored) {
			try {
				setRecentNodes(JSON.parse(stored));
			} catch (e) {
				// Ignore parse errors
			}
		}
	}, []);

	// Save selected node to recent
	useEffect(() => {
		if (value && !recentNodes.includes(value)) {
			const newRecent = [value, ...recentNodes.slice(0, 4)];
			setRecentNodes(newRecent);
			localStorage.setItem("recentNodeSelections", JSON.stringify(newRecent));
		}
	}, [value]);

	// Group and sort nodes
	const groupedNodes = useMemo(() => {
		// Filter nodes based on search
		const filtered = nodes.filter((node) => {
			if (!searchQuery) return true;
			const searchLower = searchQuery.trim().toLowerCase();
			return (
				node.data.name?.toLowerCase().includes(searchLower) ||
				node.data.type?.toLowerCase().includes(searchLower) ||
				getNodeTypeLabel(node.data.type, node.data)
					.toLowerCase()
					.includes(searchLower)
			);
		});

		// Separate nodes by category
		const structured = filtered.filter(
			(n) => n.data?.agent_config?.structured_outputs?.length > 0,
		);
		const agents = filtered.filter(
			(n) =>
				n.data.type === "AGENT" &&
				!n.data?.agent_config?.structured_outputs?.length,
		);
		const tools = filtered.filter(
			(n) =>
				n.data.type === "TOOL" ||
				n.data?.database_query_config ||
				n.data?.email_send_config ||
				n.data?.file_read_config ||
				n.data?.http_request_config,
		);
		const conditions = filtered.filter((n) => n.data.type === "CONDITION");
		const others = filtered.filter(
			(n) =>
				n.data.type !== "AGENT" &&
				n.data.type !== "TOOL" &&
				n.data.type !== "CONDITION" &&
				!n.data?.database_query_config &&
				!n.data?.email_send_config &&
				!n.data?.file_read_config &&
				!n.data?.http_request_config,
		);

		// Get recent nodes that are in the filtered list
		const recentFiltered = recentNodes
			.map((id) => filtered.find((n) => n.id === id))
			.filter(Boolean)
			.slice(0, 3);

		return {
			recent: recentFiltered as Node[],
			structured,
			agents,
			tools,
			conditions,
			others,
			totalCount: filtered.length,
		};
	}, [nodes, searchQuery, recentNodes]);

	// Update dropdown position
	useEffect(() => {
		if (isOpen && buttonRef.current) {
			const rect = buttonRef.current.getBoundingClientRect();
			const spaceBelow = window.innerHeight - rect.bottom;
			const dropdownHeight = Math.min(500, spaceBelow - 20);

			setDropdownPosition({
				top: rect.bottom + 4,
				left: rect.left,
				width: rect.width,
			});

			// Focus search input when opened
			setTimeout(() => searchInputRef.current?.focus(), 100);
		}
	}, [isOpen]);

	// Close dropdown when clicking outside
	useEffect(() => {
		const handleClickOutside = (event: MouseEvent) => {
			const target = event.target as HTMLElement;
			const dropdown = document.querySelector("[data-enhanced-node-selector]");

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
		return () => document.removeEventListener("mousedown", handleClickOutside);
	}, []);

	// Handle node selection
	const handleNodeSelect = (nodeId: string) => {
		onChange(nodeId);
		setIsOpen(false);
		setSearchQuery("");
	};

	// Render node item
	const renderNodeItem = (node: Node, showType = true) => {
		const hasStructured =
			node.data?.agent_config?.structured_outputs?.length > 0;
		const typeLabel = getNodeTypeLabel(node.data.type, node.data);
		const isHovered = hoveredNodeId === node.id;
		const isSelected = value === node.id;

		return (
			<div
				key={node.id}
				className={`px-3 py-2.5 cursor-pointer transition-all duration-150 rounded-lg group ${
					isSelected
						? "bg-emerald-500/20 border border-emerald-500/50"
						: isHovered
							? "bg-[color:var(--color-surface)] border border-[color:var(--color-border)]"
							: "hover:bg-[color:var(--color-surface)] border border-transparent"
				}`}
				onClick={createNodeSelectHandler(node.id)}
				onMouseEnter={createHoverHandler(node.id)}
				onMouseLeave={clearHover}
			>
				<div className="flex items-center gap-3">
					{/* Node Icon */}
					<div className="flex-shrink-0">
						{getNodeIcon(node.data.type, node.data)}
					</div>

					{/* Node Info */}
					<div className="flex-1 min-w-0">
						<div className="flex items-center gap-2">
							<span
								className={`font-medium text-sm truncate ${
									isSelected ? "text-emerald-400" : "text-white"
								}`}
							>
								{node.data.name}
							</span>
							{hasStructured && showStructuredIndicator && (
								<Sparkles className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
							)}
						</div>
						{showType && (
							<div className="flex items-center gap-2 mt-1">
								<span
									className={`text-xs px-1.5 py-0.5 rounded border ${getTypeColorClass(node.data.type, node.data)}`}
								>
									{typeLabel}
								</span>
								{hasStructured && (
									<span className="text-xs text-emerald-400">
										Structured Output
									</span>
								)}
							</div>
						)}
					</div>

					{/* Selection indicator */}
					{isSelected && (
						<ChevronRight className="w-4 h-4 text-emerald-400 flex-shrink-0" />
					)}
				</div>
			</div>
		);
	};

	// Render section
	const renderSection = (
		title: string,
		nodes: Node[],
		icon?: React.ReactNode,
		highlight = false,
	) => {
		if (nodes.length === 0) return null;

		return (
			<div className="mb-2">
				<div
					className={`px-3 py-2 text-xs font-medium flex items-center gap-2 ${
						highlight
							? "text-emerald-400"
							: "text-[color:var(--color-text-muted)]"
					}`}
				>
					{icon}
					{title}
					<span className="text-[#606060]">({nodes.length})</span>
				</div>
				<div className="space-y-1">
					{nodes.map((node) => renderNodeItem(node))}
				</div>
			</div>
		);
	};

	return (
		<div ref={containerRef} className={`relative ${className}`}>
			{/* Trigger Button */}
			<div
				ref={buttonRef}
				onClick={toggleDropdown}
				className="w-full px-3 py-2.5 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm cursor-pointer flex items-center justify-between hover:border-emerald-500/50 transition-all duration-200 group"
			>
				<div className="flex items-center gap-2 flex-1 min-w-0">
					{selectedNode ? (
						<>
							{getNodeIcon(selectedNode.data.type, selectedNode.data)}
							<span className="truncate font-medium">
								{selectedNode.data.name}
							</span>
							{selectedNode.data?.agent_config?.structured_outputs?.length >
								0 && (
								<Sparkles className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
							)}
						</>
					) : (
						<span className="text-[color:var(--color-text-muted)]">
							{placeholder}
						</span>
					)}
				</div>
				<ChevronDown
					className={`w-4 h-4 text-[color:var(--color-text-muted)] transition-transform duration-200 group-hover:text-emerald-400 ${
						isOpen ? "rotate-180" : ""
					}`}
				/>
			</div>

			{/* Dropdown */}
			{isOpen &&
				createPortal(
					<div
						className="fixed bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg shadow-2xl overflow-hidden animate-fadeInDropdown"
						style={{
							top: `${dropdownPosition.top}px`,
							left: `${dropdownPosition.left}px`,
							width: `${dropdownPosition.width}px`,
							maxHeight: "500px",
							zIndex: 99999,
						}}
						data-enhanced-node-selector
					>
						{/* Search Bar */}
						<div className="p-3 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)]/50">
							<div className="relative">
								<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
								<input
									ref={searchInputRef}
									type="text"
									value={searchQuery}
									onChange={handleSearchChange}
									placeholder="Search nodes..."
									aria-label="Search nodes"
									className="w-full pl-10 pr-8 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm placeholder-[#606060] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
								/>
								{searchQuery && (
									<button
										onClick={clearSearch}
										className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-[color:var(--color-border)] rounded transition-colors"
									>
										<X className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
									</button>
								)}
							</div>
						</div>

						{/* Node List */}
						<div className="overflow-y-auto max-h-[400px] py-2">
							{groupedNodes.totalCount === 0 ? (
								<div className="px-3 py-8 text-center">
									<AlertCircle className="w-8 h-8 text-[#606060] mx-auto mb-2" />
									<p className="text-sm text-[color:var(--color-text-muted)]">
										{searchQuery
											? "No nodes match your search"
											: "No nodes available"}
									</p>
								</div>
							) : (
								<>
									{/* Recent Nodes */}
									{!searchQuery &&
										groupedNodes.recent.length > 0 &&
										renderSection(
											"RECENT",
											groupedNodes.recent,
											<Clock className="w-3.5 h-3.5" />,
										)}

									{/* Structured Output Nodes (Priority) */}
									{groupedNodes.structured.length > 0 &&
										renderSection(
											"STRUCTURED OUTPUT",
											groupedNodes.structured,
											<Star className="w-3.5 h-3.5" />,
											true,
										)}

									{/* Agents */}
									{groupedNodes.agents.length > 0 &&
										renderSection(
											"AGENTS",
											groupedNodes.agents,
											<Cpu className="w-3.5 h-3.5" />,
										)}

									{/* Tools */}
									{groupedNodes.tools.length > 0 &&
										renderSection(
											"TOOLS",
											groupedNodes.tools,
											<Settings className="w-3.5 h-3.5" />,
										)}

									{/* Conditions */}
									{groupedNodes.conditions.length > 0 &&
										renderSection(
											"CONDITIONS",
											groupedNodes.conditions,
											<GitBranch className="w-3.5 h-3.5" />,
										)}

									{/* Others */}
									{groupedNodes.others.length > 0 &&
										renderSection("OTHER", groupedNodes.others)}
								</>
							)}
						</div>
					</div>,
					document.body,
				)}
		</div>
	);
};

export default EnhancedNodeSelector;
