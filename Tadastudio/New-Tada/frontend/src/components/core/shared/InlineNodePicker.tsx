"use client";

import {
	AlertCircle,
	Bot,
	CheckCircle,
	ChevronRight,
	Database,
	FileText,
	GitBranch,
	Globe,
	Layers,
	Mail,
	MoreHorizontal,
	X,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface InlineNodePickerProps {
	isOpen: boolean;
	position: { x: number; y: number };
	sourceNodeId: string | null;
	sourceBranchIndex?: number | null;
	onClose: () => void;
	onSelectNode: (
		nodeType: string,
		sourceNodeId: string | null,
		sourceBranchIndex?: number | null,
	) => void;
	onOpenFullPalette: () => void;
}

interface NodeCategory {
	id: string;
	label: string;
	icon: typeof Bot;
	colorRgb: string;
	nodes: CategoryNode[];
}

interface CategoryNode {
	type: string;
	name: string;
	icon: typeof Bot;
	available: boolean;
}

const categories: NodeCategory[] = [
	{
		id: "ai",
		label: "AI Agent",
		icon: Bot,
		colorRgb: "168, 85, 247",
		nodes: [
			{ type: "AGENT", name: "Agent Node", icon: Bot, available: true },
		],
	},
	{
		id: "actions",
		label: "Actions",
		icon: Zap,
		colorRgb: "13, 169, 49",
		nodes: [
			{
				type: "HTTP_REQUEST_ACTION",
				name: "HTTP Request",
				icon: Globe,
				available: true,
			},
			{
				type: "DATABASE_INSERT",
				name: "Database Insert",
				icon: Database,
				available: true,
			},
			{
				type: "DATABASE_QUERY_ACTION",
				name: "Database Query",
				icon: Database,
				available: true,
			},
			{
				type: "EMAIL_SEND",
				name: "Email Send",
				icon: Mail,
				available: false,
			},
			{
				type: "FILE_READ",
				name: "File Read",
				icon: FileText,
				available: true,
			},
		],
	},
	{
		id: "logic",
		label: "Logic",
		icon: GitBranch,
		colorRgb: "249, 115, 22",
		nodes: [
			{
				type: "CONDITION",
				name: "Condition",
				icon: GitBranch,
				available: true,
			},
			{
				type: "CHECKPOINT",
				name: "Checkpoint",
				icon: AlertCircle,
				available: true,
			},
		],
	},
	{
		id: "control",
		label: "End",
		icon: CheckCircle,
		colorRgb: "239, 68, 68",
		nodes: [
			{
				type: "END",
				name: "End Node",
				icon: CheckCircle,
				available: true,
			},
		],
	},
];

export default function InlineNodePicker({
	isOpen,
	position,
	sourceNodeId,
	sourceBranchIndex,
	onClose,
	onSelectNode,
	onOpenFullPalette,
}: InlineNodePickerProps) {
	const [expandedCategory, setExpandedCategory] = useState<string | null>(
		null,
	);
	const panelRef = useRef<HTMLDivElement>(null);
	const [mounted, setMounted] = useState(false);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	// Reset expanded category when picker opens
	useEffect(() => {
		if (isOpen) {
			setExpandedCategory(null);
		}
	}, [isOpen]);

	// Click outside to close
	useEffect(() => {
		if (!isOpen) return;

		const handleClickOutside = (e: MouseEvent) => {
			if (
				panelRef.current &&
				!panelRef.current.contains(e.target as Node)
			) {
				onClose();
			}
		};

		const handleEscape = (e: KeyboardEvent) => {
			if (e.key === "Escape") {
				onClose();
			}
		};

		// Delay to avoid closing immediately on the click that opened it
		const timer = setTimeout(() => {
			document.addEventListener("mousedown", handleClickOutside);
			document.addEventListener("keydown", handleEscape);
		}, 50);

		return () => {
			clearTimeout(timer);
			document.removeEventListener("mousedown", handleClickOutside);
			document.removeEventListener("keydown", handleEscape);
		};
	}, [isOpen, onClose]);

	const handleCategoryClick = useCallback(
		(category: NodeCategory) => {
			if (category.nodes.length === 1) {
				// Single node in category - add directly
				onSelectNode(
					category.nodes[0].type,
					sourceNodeId,
					sourceBranchIndex,
				);
			} else {
				// Multiple nodes - expand category
				setExpandedCategory(
					expandedCategory === category.id ? null : category.id,
				);
			}
		},
		[
			expandedCategory,
			onSelectNode,
			sourceNodeId,
			sourceBranchIndex,
		],
	);

	const handleNodeClick = useCallback(
		(nodeType: string) => {
			onSelectNode(nodeType, sourceNodeId, sourceBranchIndex);
		},
		[onSelectNode, sourceNodeId, sourceBranchIndex],
	);

	if (!isOpen || !mounted) return null;

	// Compute position to keep panel in viewport
	const panelWidth = 320;
	const panelHeight = expandedCategory ? 280 : 64;
	const adjustedX = Math.min(
		position.x - panelWidth / 2,
		window.innerWidth - panelWidth - 16,
	);
	const adjustedY = Math.min(
		position.y - 32,
		window.innerHeight - panelHeight - 16,
	);

	const expandedCategoryData = categories.find(
		(c) => c.id === expandedCategory,
	);

	return createPortal(
		<div
			ref={panelRef}
			className="fixed z-[9999] animate-scaleIn"
			style={{
				left: Math.max(16, adjustedX),
				top: Math.max(16, adjustedY),
			}}
		>
			<div className="rounded-2xl border border-[color:var(--color-primary)]/30 bg-[color:var(--color-bg-secondary)]/95 backdrop-blur-xl shadow-[0_20px_60px_rgba(0,0,0,0.6)]">
				{/* Category bar */}
				<div className="flex items-center gap-1 p-2">
					{categories.map((category) => {
						const Icon = category.icon;
						const isExpanded = expandedCategory === category.id;
						const hasMultiple = category.nodes.length > 1;

						return (
							<div key={category.id} className="relative group">
								<button
									onClick={() => handleCategoryClick(category)}
									className={`flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
										isExpanded
											? "bg-[color:var(--color-surface)] border border-[color:var(--color-border)]/50 text-slate-900"
											: "border border-transparent hover:bg-[color:var(--color-surface)]/60 text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)]"
									}`}
									aria-label={category.label}
								>
									<Icon
										className="w-4 h-4"
										style={{
											color: `rgb(${category.colorRgb})`,
										}}
									/>
									<span className="hidden sm:inline text-xs">
										{category.label}
									</span>
									{hasMultiple && (
										<ChevronRight
											className={`w-3 h-3 transition-transform duration-200 ${
												isExpanded ? "rotate-90" : ""
											}`}
										/>
									)}
								</button>

								{/* Tooltip (custom so we can color text) */}
								<div className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity z-50">
									<div className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 shadow-[0_10px_26px_rgba(0,0,0,0.14)]">
										<span
											className="text-[11px] font-medium whitespace-nowrap"
											style={{ color: `rgb(${category.colorRgb})` }}
										>
											{category.label}
										</span>
									</div>
								</div>
							</div>
						);
					})}

					{/* Divider */}
					<div className="w-px h-6 bg-[color:var(--color-border)]/40 mx-0.5" />

					{/* More button */}
					<div className="relative group">
						<button
							onClick={() => {
								onClose();
								onOpenFullPalette();
							}}
							className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)] hover:bg-[color:var(--color-surface)]/60 border border-transparent transition-all duration-200"
							aria-label="Open full node palette"
						>
							<MoreHorizontal className="w-4 h-4" />
							<span className="hidden sm:inline">More</span>
						</button>

						{/* Tooltip (text matches icon color) */}
						<div className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-2 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity z-50">
							<div className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 shadow-[0_10px_26px_rgba(0,0,0,0.14)]">
								<span className="text-[11px] font-medium whitespace-nowrap text-[color:var(--color-text-muted)]">
									Open full palette
								</span>
							</div>
						</div>
					</div>
				</div>

				{/* Expanded sub-nodes */}
				{expandedCategoryData && (
					<div className="border-t border-[color:var(--color-border)]/30 px-2 py-2 space-y-0.5 animate-fadeIn">
						{expandedCategoryData.nodes.map((node) => {
							const NodeIcon = node.icon;
							return (
								<button
									key={node.type}
									onClick={() =>
										node.available &&
										handleNodeClick(node.type)
									}
									disabled={!node.available}
									className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-200 ${
										node.available
											? "hover:bg-[color:var(--color-surface)]/60 cursor-pointer"
											: "opacity-50 cursor-not-allowed"
									}`}
								>
									<div
										className="h-7 w-7 rounded-lg border flex items-center justify-center flex-shrink-0"
										style={{
											backgroundColor: `rgba(${expandedCategoryData.colorRgb}, 0.12)`,
											borderColor: `rgba(${expandedCategoryData.colorRgb}, 0.3)`,
										}}
									>
										<NodeIcon
											className="w-3.5 h-3.5"
											style={{
												color: `rgba(${expandedCategoryData.colorRgb}, 0.9)`,
											}}
										/>
									</div>
									<span className="text-sm text-[color:var(--color-text-primary)]">
										{node.name}
									</span>
									{!node.available && (
										<span className="ml-auto rounded-full border border-[color:var(--color-border)] px-2 py-0.5 text-[10px] font-medium text-[color:var(--color-text-muted)]">
											Coming soon
										</span>
									)}
								</button>
							);
						})}
					</div>
				)}
			</div>
		</div>,
		document.body,
	);
}
