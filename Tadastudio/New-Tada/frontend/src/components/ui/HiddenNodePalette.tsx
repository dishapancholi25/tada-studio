"use client";

import {
	AlertCircle,
	BookOpen,
	Bot,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	Code,
	Database,
	Download,
	FileText,
	GitBranch,
	Globe,
	Layers,
	List,
	Mail,
	RefreshCw,
	Repeat,
	Webhook,
	X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useFocusTrap, useKeyboardNavigation } from "@/hooks/useAccessibility";

interface HiddenNodePaletteProps {
	isOpen: boolean;
	onClose: () => void;
	onAddNode: (nodeType: string, sourceNodeId?: string) => void;
	sourceNodeId?: string;
}

const colorClasses = {
	plum: "from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/18 border-[color:var(--color-border)]/45 hover:border-[color:var(--color-border)] hover:from-[color:var(--color-primary)]/30 hover:to-[color:var(--color-accent)]/25",
	gray: "from-[color:var(--color-text-muted)]/20 to-[color:var(--color-text-muted)]/10 border-[color:var(--color-text-muted)]/50 hover:border-[color:var(--color-text-muted)] hover:from-[color:var(--color-text-muted)]/30 hover:to-[color:var(--color-text-muted)]/20",
	green: "from-[#0DA931]/20 to-emerald-600/20 border-[#0DA931]/50 hover:border-[#0DA931] hover:from-[#0DA931]/30 hover:to-emerald-600/30",
	emerald:
		"from-emerald-500/20 to-[#0DA931]/20 border-emerald-500/50 hover:border-emerald-400 hover:from-emerald-500/30 hover:to-[#0DA931]/30",
	purple:
		"from-purple-500/20 to-pink-600/20 border-purple-500/50 hover:border-purple-400 hover:from-purple-500/30 hover:to-pink-600/30",
	orange:
		"from-orange-500/20 to-[color:var(--color-warning)]/18 border-orange-500/50 hover:border-orange-400 hover:from-orange-500/30 hover:to-[color:var(--color-warning)]/26",
	red: "from-red-500/20 to-rose-600/20 border-red-500/50 hover:border-red-400 hover:from-red-500/30 hover:to-rose-600/30",
	blue: "from-sky-500/20 to-blue-700/20 border-sky-500/50 hover:border-sky-400 hover:from-sky-500/30 hover:to-blue-700/30",
	amber: "from-amber-500/20 to-yellow-600/20 border-amber-500/50 hover:border-amber-400 hover:from-amber-500/30 hover:to-yellow-600/30",
	default:
		"from-[color:var(--color-surface-hover)]/10 to-[color:var(--color-border)]/10 border-[color:var(--color-surface-hover)]/30 hover:border-[color:var(--color-text-muted)]/30",
};

const iconColorClasses = {
	plum: "text-[color:var(--color-accent)]",
	gray: "text-[color:var(--color-text-muted)]",
	green: "text-[#0DA931]",
	emerald: "text-emerald-400",
	purple: "text-purple-400",
	orange: "text-orange-400",
	red: "text-red-400",
	blue: "text-sky-400",
	amber: "text-amber-400",
	default: "text-[color:var(--color-text-muted)]",
};

type ColorKey = keyof typeof colorClasses;

const cardAccentClasses: Record<ColorKey, { border: string; iconBg: string; iconBorder: string; iconText: string }> = {
	plum: {
		border: "border-l-orange-400",
		iconBg: "bg-orange-50",
		iconBorder: "border-orange-100",
		iconText: "text-orange-600",
	},
	blue: {
		border: "border-l-sky-400",
		iconBg: "bg-sky-50",
		iconBorder: "border-sky-100",
		iconText: "text-sky-600",
	},
	green: {
		border: "border-l-[#0DA931]",
		iconBg: "bg-[#F1F8E9]",
		iconBorder: "border-[#F1F8E9]",
		iconText: "text-[#0DA931]",
	},
	emerald: {
		border: "border-l-emerald-400",
		iconBg: "bg-emerald-50",
		iconBorder: "border-emerald-100",
		iconText: "text-emerald-600",
	},
	purple: {
		border: "border-l-purple-400",
		iconBg: "bg-purple-50",
		iconBorder: "border-purple-100",
		iconText: "text-purple-600",
	},
	orange: {
		border: "border-l-orange-400",
		iconBg: "bg-orange-50",
		iconBorder: "border-orange-100",
		iconText: "text-orange-600",
	},
	red: {
		border: "border-l-red-400",
		iconBg: "bg-red-50",
		iconBorder: "border-red-100",
		iconText: "text-red-600",
	},
	amber: {
		border: "border-l-amber-400",
		iconBg: "bg-amber-50",
		iconBorder: "border-amber-100",
		iconText: "text-amber-700",
	},
	gray: {
		border: "border-l-slate-300",
		iconBg: "bg-slate-50",
		iconBorder: "border-slate-200",
		iconText: "text-slate-500",
	},
	default: {
		border: "border-l-slate-300",
		iconBg: "bg-slate-50",
		iconBorder: "border-slate-200",
		iconText: "text-slate-600",
	},
};

const HERO_TYPES = ["AGENT"];
const SECONDARY_TYPES = ["AGENT_TEMPLATE_LIBRARY", "ACTION"];
const UTILITY_TYPES = ["CONDITION", "FOR_EACH", "CHECKPOINT", "END"];

export default function HiddenNodePalette({
	isOpen,
	onClose,
	onAddNode,
	sourceNodeId,
}: HiddenNodePaletteProps) {
	const panelRef = useFocusTrap<HTMLDivElement>(isOpen);
	const searchInputRef = useRef<HTMLInputElement>(null);
	const [expandedActions, setExpandedActions] = useState(false);
	const [expandedUpcoming, setExpandedUpcoming] = useState(false);
	const [mounted, setMounted] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	const toggleExpandedActions = useCallback(
		() => setExpandedActions(!expandedActions),
		[expandedActions],
	);
	const toggleExpandedUpcoming = useCallback(
		() => setExpandedUpcoming(!expandedUpcoming),
		[expandedUpcoming],
	);
	const createNodeHandler = useCallback(
		(nodeType: string) => () => onAddNode(nodeType, sourceNodeId),
		[onAddNode, sourceNodeId],
	);
	const createSubNodeHandler = useCallback(
		(subNode: any) => () => {
			if (subNode.available && subNode.onClick) {
				subNode.onClick();
				onClose();
			}
		},
		[onClose],
	);
	const createMainNodeHandler = useCallback(
		(nodeType: any) => () => {
			if (nodeType.available && nodeType.onClick) {
				nodeType.onClick();
				onClose();
			}
		},
		[onClose],
	);

	const actionNodes = [
		{
			type: "DATABASE_INSERT",
			name: "Database Insert",
			description: "Insert data into database",
			icon: Database,
			color: "emerald",
			available: true,
			onClick: createNodeHandler("DATABASE_INSERT"),
		},
		{
			type: "DATABASE_QUERY_ACTION",
			name: "Database Query",
			description: "Query database sequentially in the workflow",
			icon: Database,
			color: "emerald",
			available: true,
			onClick: createNodeHandler("DATABASE_QUERY_ACTION"),
		},
		{
			type: "HTTP_REQUEST_ACTION",
			name: "HTTP Request",
			description: "Make HTTP API calls",
			icon: Globe,
			color: "green",
			available: true,
			onClick: createNodeHandler("HTTP_REQUEST_ACTION"),
		},
		{
			type: "EMAIL_SEND",
			name: "Email Send",
			description: "Send email notifications",
			icon: Mail,
			color: "gray",
			available: false,
			comingSoon: true,
		},
		{
			type: "FILE_READ",
			name: "File Read",
			description: "Read and extract content from files",
			icon: FileText,
			color: "emerald",
			// TEMPORARILY DISABLED: due to ISG security audit
			// Will be re-enabled after fixes are implemented
			available: false,
			comingSoon: true,
			// available: true,
			// onClick: createNodeHandler("FILE_READ"),
		},
		{
			type: "DOCUMENT_LOAD",
			name: "Document Load",
			description: "Load full documents from collections",
			icon: Download,
			color: "purple",
			available: true,
			onClick: createNodeHandler("DOCUMENT_LOAD"),
		},
		{
			type: "FILE_WRITE",
			name: "File Write",
			description: "Write to files",
			icon: FileText,
			color: "gray",
			available: false,
			comingSoon: true,
		},
		{
			type: "WEBHOOK",
			name: "Webhook",
			description: "Trigger webhook endpoints",
			icon: Webhook,
			color: "gray",
			available: false,
			comingSoon: true,
		},
		{
			type: "CODE_EXECUTOR",
			name: "Code Executor",
			description: "Run Python or JavaScript code",
			icon: Code,
			color: "emerald",
			available: false,
			comingSoon: true,
		},
		{
			type: "DATA_TRANSFORM",
			name: "Data Transform",
			description: "Transform and process data",
			icon: RefreshCw,
			color: "gray",
			available: false,
			comingSoon: true,
		},
		{
			type: "SCRIPT_EXECUTE",
			name: "Script Execute",
			description: "Execute custom scripts",
			icon: Code,
			color: "gray",
			available: false,
			comingSoon: true,
		},
	];

	const availableActionNodes = actionNodes.filter((n) => n.available);
	const upcomingActionNodes = actionNodes.filter((n) => !n.available);

	const nodeTypes = [
		{
			type: "AGENT",
			name: "Agent Node",
			description: "AI agent with custom prompt",
			icon: Bot,
			color: "plum",
			available: true,
			onClick: createNodeHandler("AGENT"),
		},
		{
			type: "AGENT_TEMPLATE_LIBRARY",
			name: "Agent Templates",
			description: "Insert published agents from the library",
			icon: BookOpen,
			color: "blue",
			available: true,
			onClick: createNodeHandler("AGENT_TEMPLATE_LIBRARY"),
		},
		{
			type: "ACTION",
			name: "Action Node",
			description: "Perform specific actions",
			icon: Layers,
			color: "green",
			available: true,
			isCategory: true,
			subNodes: availableActionNodes,
		},
		{
			type: "CONDITION",
			name: "Condition Node",
			description: "Branching logic",
			icon: GitBranch,
			color: "orange",
			available: true,
			onClick: createNodeHandler("CONDITION"),
		},
		{
			type: "CHECKPOINT",
			name: "Checkpoint",
			description: "Pause for human review/input",
			icon: AlertCircle,
			color: "purple",
			available: true,
			onClick: createNodeHandler("CHECKPOINT"),
		},
		{
			type: "FOR_EACH",
			name: "For Each",
			description: "Iterate over arrays with bounded concurrency",
			icon: Repeat,
			color: "amber",
			available: true,
			onClick: createNodeHandler("FOR_EACH"),
		},
		{
			type: "END",
			name: "End Node",
			description: "Workflow endpoint",
			icon: CheckCircle,
			color: "red",
			available: true,
			onClick: createNodeHandler("END"),
		},
	];

	// Filter node types per tier based on search query
	const query = searchQuery.toLowerCase().trim();

	const filteredHeroNodes = useMemo(() => {
		const heroes = nodeTypes.filter((n) => HERO_TYPES.includes(n.type));
		if (!query) return heroes;
		return heroes.filter(
			(n) =>
				n.name.toLowerCase().includes(query) ||
				n.description.toLowerCase().includes(query),
		);
	}, [nodeTypes, query]);

	const filteredSecondaryNodes = useMemo(() => {
		const secondary = nodeTypes.filter((n) =>
			SECONDARY_TYPES.includes(n.type),
		);
		if (!query) return secondary;
		return secondary.filter((node) => {
			const nameMatch = node.name.toLowerCase().includes(query);
			const descMatch = node.description.toLowerCase().includes(query);
			const subMatch =
				"subNodes" in node &&
				(node as any).subNodes?.some(
					(sub: any) =>
						sub.name.toLowerCase().includes(query) ||
						sub.description.toLowerCase().includes(query),
				);
			// Also check upcoming action nodes for search
			const upcomingMatch =
				node.type === "ACTION" &&
				upcomingActionNodes.some(
					(sub) =>
						sub.name.toLowerCase().includes(query) ||
						sub.description.toLowerCase().includes(query),
				);
			return nameMatch || descMatch || subMatch || upcomingMatch;
		});
	}, [nodeTypes, query, upcomingActionNodes]);

	const filteredUtilityNodes = useMemo(() => {
		const utility = nodeTypes.filter((n) => UTILITY_TYPES.includes(n.type));
		if (!query) return utility;
		return utility.filter(
			(n) =>
				n.name.toLowerCase().includes(query) ||
				n.description.toLowerCase().includes(query),
		);
	}, [nodeTypes, query]);

	const filteredUpcomingNodes = useMemo(() => {
		if (!query) return upcomingActionNodes;
		return upcomingActionNodes.filter(
			(n) =>
				n.name.toLowerCase().includes(query) ||
				n.description.toLowerCase().includes(query),
		);
	}, [upcomingActionNodes, query]);

	const allNavigableCount =
		filteredHeroNodes.length +
		filteredSecondaryNodes.length +
		filteredUtilityNodes.length;

	const noResults =
		allNavigableCount === 0 && filteredUpcomingNodes.length === 0;

	// Auto-focus search input when opened
	useEffect(() => {
		if (isOpen) {
			setSearchQuery("");
			// Slight delay to wait for portal mount
			const timer = setTimeout(() => {
				searchInputRef.current?.focus();
			}, 100);
			return () => clearTimeout(timer);
		}
	}, [isOpen]);

	const { selectedIndex, handleKeyDown } = useKeyboardNavigation(
		allNavigableCount,
		(index) => {
			// Focus the button at the selected index
			const buttons = panelRef.current?.querySelectorAll(
				"button[data-node-button]",
			);
			if (buttons?.[index]) {
				(buttons[index] as HTMLElement).focus();
			}
		},
	);

	// Close on escape key
	useEffect(() => {
		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape" && isOpen) {
				onClose();
			}
		};

		document.addEventListener("keydown", handleEscape);
		return () => document.removeEventListener("keydown", handleEscape);
	}, [isOpen, onClose]);

	if (!isOpen || !mounted) return null;

	// Track global button index across sections for keyboard navigation
	let globalButtonIndex = 0;

	return createPortal(
		<>
			{/* Backdrop */}
			<div
				className="fixed inset-0 bg-black/30 backdrop-blur-sm z-[110] transition-opacity duration-300"
				onClick={onClose}
			/>

			{/* Glass Halo Wrapper */}
			<div
				className={`fixed left-4 top-[5%] bottom-[5%] w-[360px] z-[120] transform transition-all duration-300 ease-out ${
					isOpen ? "translate-x-0" : "-translate-x-full"
				}`}
			>
				{/* Outer gradient frame for glass halo effect */}
				<div className="absolute -inset-[1px] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.5)] via-transparent to-[rgba(var(--color-primary-rgb),0.18)] rounded pointer-events-none" />

				{/* Main Panel */}
				<div
					ref={panelRef}
					data-tutorial="node-picker"
					className="relative h-full bg-white border border-slate-200 rounded shadow-[0_35px_120px_rgba(0,0,0,0.18)] flex flex-col max-h-[90vh]"
					role="dialog"
					aria-modal="true"
					aria-label="Add Node Panel"
					onKeyDown={handleKeyDown}
				>
					{/* Header */}
					<div className="flex-shrink-0 flex items-center justify-between p-6 border-b border-black/10 bg-white rounded-t">
						<h2 className="text-2xl font-semibold text-[rgb(249,115,22)] flex items-center gap-3">
							<span className="w-2.5 h-2.5 bg-[rgb(249,115,22)] rounded-full animate-pulse shadow-[0_0_12px_rgba(255,255,255,0.45)]"></span>
							Add Node
						</h2>
						<button
							onClick={onClose}
							className="p-2.5 border border-slate-300 bg-slate-100 hover:bg-white/20 rounded-xl transition-all duration-200 text-slate-600 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
						>
							<X className="w-5 h-5" />
						</button>
					</div>

					{/* Search input */}
					<div className="flex-shrink-0 px-6 pt-4 pb-2">
						<input
							ref={searchInputRef}
							type="text"
							placeholder="Search nodes... (press / to focus)"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-500/20 transition-all duration-200"
						/>
					</div>

					{/* Content - scrollable area */}
					<div className="flex-1 overflow-y-auto p-6 pt-2 min-h-0 custom-scrollbar">
						<div className="space-y-4 pb-6">
							{/* No results */}
							{noResults && (
								<div className="text-center py-8 text-[color:var(--color-text-muted)]/60 text-sm">
									No nodes match &ldquo;{searchQuery}&rdquo;
								</div>
							)}

							{/* Tier 1 - Hero: Agent Node */}
							{filteredHeroNodes.map((nodeType) => {
								const Icon = nodeType.icon;
								const btnIndex = globalButtonIndex++;
								return (
									<button
										key={nodeType.type}
										data-node-button
										data-tutorial={nodeType.type === "AGENT" ? "node-picker-agent" : undefined}
										onClick={createMainNodeHandler(nodeType)}
										className="group relative w-full p-5 bg-white border border-slate-200 border-l-[3px] border-l-orange-400 rounded-2xl transition-all duration-300 hover:border-slate-300 hover:shadow-[0_24px_65px_rgba(15,23,42,0.10)] hover:scale-[1.01] overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
										aria-label={`Add ${nodeType.name}: ${nodeType.description}`}
										tabIndex={btnIndex === selectedIndex ? 0 : -1}
									>
										{/* Glow veneer on hover */}
										<div className="absolute -inset-[1px] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.15)] to-transparent rounded-2xl opacity-0 group-hover:opacity-40 blur-xl transition-opacity duration-300 pointer-events-none" />

										{/* Shimmer effect on hover */}
										<div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
											<div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
										</div>

										<div className="flex items-center gap-4 relative">
											<div className="p-3 bg-orange-50 rounded-xl border border-orange-100">
												<Icon className="w-7 h-7 text-orange-600" />
											</div>
											<div className="text-left flex-1">
												<div className="font-semibold text-slate-900">
													{nodeType.name}
												</div>
												<div className="text-sm text-slate-600 mt-1">
													{nodeType.description}
												</div>
											</div>
										</div>
									</button>
								);
							})}

							{/* Tier 2 - Secondary: Agent Templates + Action Node */}
							{filteredSecondaryNodes.map((nodeType) => {
								const Icon = nodeType.icon;
								const color = nodeType.color as ColorKey;
								const accent = cardAccentClasses[color] || cardAccentClasses.default;

								if (nodeType.isCategory) {
									const btnIndex = globalButtonIndex++;
									return (
										<div key={nodeType.type} className="space-y-3">
											<button
												data-node-button
												onClick={toggleExpandedActions}
												className={`group relative w-full p-4 bg-white border border-slate-200 border-l-[3px] ${accent.border} rounded-2xl transition-all duration-300 hover:border-slate-300 hover:shadow-[0_24px_65px_rgba(15,23,42,0.10)] hover:scale-[1.01] overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25`}
												aria-label={`${expandedActions ? "Collapse" : "Expand"} ${nodeType.name}: ${nodeType.description}`}
												tabIndex={btnIndex === selectedIndex ? 0 : -1}
											>
												<div className="flex items-center gap-4 relative">
													<div className={`p-2.5 rounded-xl border ${accent.iconBg} ${accent.iconBorder}`}>
														<Icon className={`w-6 h-6 ${accent.iconText}`} />
													</div>
													<div className="text-left flex-1">
														<div className="font-semibold text-slate-900 flex items-center gap-2">
															{nodeType.name}
															{expandedActions ? (
																<ChevronDown className="w-4 h-4 text-slate-500 transition-transform duration-200" />
															) : (
																<ChevronRight className="w-4 h-4 text-slate-500 transition-transform duration-200" />
															)}
														</div>
														<div className="text-sm text-slate-600 mt-1">
															{nodeType.description}
														</div>
													</div>
												</div>
											</button>

											{/* Available sub-nodes */}
											{expandedActions && (
												<div className="ml-6 space-y-2 animate-fadeIn">
													{nodeType.subNodes?.map((subNode) => {
														const SubIcon = subNode.icon;
														const subColor = subNode.color as ColorKey;

														return (
															<button
																key={subNode.type}
																onClick={createSubNodeHandler(subNode)}
																className={`group relative w-full p-3 bg-gradient-to-br ${colorClasses[subColor]} border rounded-xl transition-all duration-300 hover:shadow-[0_20px_55px_rgba(0,0,0,0.55)] hover:scale-[1.01] overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]`}
															>
																<div className="flex items-center gap-3 relative">
																	<div className="p-2 bg-[color:var(--color-bg-secondary)]/50 rounded-lg border border-[color:var(--color-border)]/20">
																		<SubIcon
																			className={`w-5 h-5 ${iconColorClasses[subColor]}`}
																		/>
																	</div>
																	<div className="text-left flex-1">
																		<div className="font-medium text-sm text-slate-900">
																			{subNode.name}
																		</div>
																		<div className="text-xs mt-1 text-[color:var(--color-text-secondary)]">
																			{subNode.description}
																		</div>
																	</div>
																</div>
															</button>
														);
													})}

													{/* Upcoming action nodes - collapsible */}
													{filteredUpcomingNodes.length > 0 && (
														<div className="mt-3">
															<button
																onClick={toggleExpandedUpcoming}
																className="flex items-center gap-2 text-xs capitalize text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)] transition-colors mb-2 px-1"
																aria-label={`${expandedUpcoming ? "Collapse" : "Expand"} upcoming action nodes`}
															>
																{expandedUpcoming ? (
																	<ChevronDown className="w-3 h-3" />
																) : (
																	<ChevronRight className="w-3 h-3" />
																)}
																Upcoming ({filteredUpcomingNodes.length})
															</button>
															{expandedUpcoming && (
																<div className="space-y-2 animate-fadeIn">
																	{filteredUpcomingNodes.map((subNode) => {
																		const SubIcon = subNode.icon;
																		return (
																			<button
																				key={subNode.type}
																				disabled
																				className="group relative w-full p-3 bg-gradient-to-br from-[color:var(--color-border)]/20 to-[color:var(--color-surface)]/20 border-[color:var(--color-surface-hover)]/30 cursor-not-allowed opacity-60 border rounded-xl overflow-hidden"
																			>
																				<div className="flex items-center gap-3 relative">
																					<div className="p-2 bg-[color:var(--color-bg-secondary)]/50 rounded-lg border border-[color:var(--color-border)]/20">
																						<SubIcon className="w-5 h-5 text-[color:var(--color-text-muted)]" />
																					</div>
																					<div className="text-left flex-1">
																						<div className="font-medium text-sm text-[color:var(--color-text-muted)] flex items-center gap-2">
																							{subNode.name}
																							<span className="text-[11px] font-medium px-2 py-0.5 rounded-full border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-muted)]">
																								Coming Soon
																							</span>
																						</div>
																						<div className="text-xs mt-1 text-[color:var(--color-text-muted)]">
																							{subNode.description}
																						</div>
																					</div>
																				</div>
																			</button>
																		);
																	})}
																</div>
															)}
														</div>
													)}
												</div>
											)}
										</div>
									);
								}

								const btnIndex = globalButtonIndex++;
								return (
									<button
										key={nodeType.type}
										data-node-button
										onClick={createMainNodeHandler(nodeType)}
										className={`group relative w-full p-4 bg-white border border-slate-200 border-l-[3px] ${accent.border} rounded-2xl transition-all duration-300 hover:border-slate-300 hover:shadow-[0_24px_65px_rgba(15,23,42,0.10)] hover:scale-[1.01] overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25`}
										aria-label={`Add ${nodeType.name}: ${nodeType.description}`}
										tabIndex={btnIndex === selectedIndex ? 0 : -1}
									>
										<div className="flex items-center gap-4 relative">
											<div className={`p-2.5 rounded-xl border ${accent.iconBg} ${accent.iconBorder}`}>
												<Icon className={`w-6 h-6 ${accent.iconText}`} />
											</div>
											<div className="text-left flex-1">
												<div className="font-semibold text-slate-900">
													{nodeType.name}
												</div>
												<div className="text-sm text-slate-600 mt-1">
													{nodeType.description}
												</div>
											</div>
										</div>
									</button>
								);
							})}

							{/* Tier 3 - Flow Control: Compact horizontal row */}
							{filteredUtilityNodes.length > 0 && (
								<div className="mt-2">
									<h3 className="text-xs capitalize text-slate-500 font-semibold mb-3 px-1">
										Flow Control
									</h3>
									<div className="grid grid-cols-3 gap-2">
										{filteredUtilityNodes.map((nodeType) => {
											const Icon = nodeType.icon;
											const color = nodeType.color as ColorKey;
											const btnIndex = globalButtonIndex++;
											return (
												<button
													key={nodeType.type}
													data-node-button
													data-tutorial={nodeType.type === "END" ? "node-picker-end" : undefined}
													onClick={createMainNodeHandler(nodeType)}
													className={`group relative p-3 bg-gradient-to-br ${colorClasses[color]} border rounded-xl transition-all duration-300 hover:shadow-[0_18px_40px_rgba(15,23,42,0.10)] hover:scale-[1.02] overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 text-center`}
													aria-label={`Add ${nodeType.name}: ${nodeType.description}`}
													title={nodeType.description}
													tabIndex={btnIndex === selectedIndex ? 0 : -1}
												>
													{/* Glow veneer on hover */}
													<div className="absolute -inset-[1px] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.15)] to-transparent rounded-xl opacity-0 group-hover:opacity-40 blur-xl transition-opacity duration-300 pointer-events-none" />

													<div className="flex flex-col items-center gap-2 relative">
														<div className="p-2 bg-white/70 rounded-lg border border-black/5">
															<Icon
																className={`w-5 h-5 ${iconColorClasses[color]}`}
															/>
														</div>
														<span className="text-xs font-medium text-slate-900 truncate w-full">
															{nodeType.name.replace(" Node", "")}
														</span>
													</div>
												</button>
											);
										})}
									</div>
								</div>
							)}
						</div>
					</div>
				</div>
			</div>
		</>,
		document.body,
	);
}
