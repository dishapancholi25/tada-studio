"use client";

import {
	BookOpen,
	ChevronDown,
	ChevronRight,
	Menu,
	Plus,
	Search,
	X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
	useEscapeKey,
	useFocusTrap,
	useTreeNavigation,
} from "@/hooks/useAccessibility";
import { useAuth } from "@/contexts/AuthContext";
import { wikiApi, type WikiTreeNode } from "@/lib/wiki-api";

interface WikiSidebarProps {
	/** Optional external refresh trigger (increment to force a reload). */
	refreshKey?: number;
}

function TreeNode({
	node,
	depth,
	activePath,
	expandedIds,
	onToggle,
	treeItemRefs,
	getTreeItemProps,
}: {
	node: WikiTreeNode;
	depth: number;
	activePath: string;
	expandedIds: Set<string>;
	onToggle: (id: string) => void;
	treeItemRefs: React.MutableRefObject<Map<string, HTMLElement>>;
	getTreeItemProps: (id: string) => { tabIndex: number; onFocus: () => void };
}) {
	const hasChildren = node.children.length > 0;
	const open = expandedIds.has(node.id);
	const isActive = activePath === `/wiki/${node.slug}`;

	return (
		<li
			role="treeitem"
			aria-selected={isActive}
			aria-expanded={hasChildren ? open : undefined}
			aria-current={isActive ? "page" : undefined}
			ref={(el) => {
				if (el) treeItemRefs.current.set(node.id, el);
				else treeItemRefs.current.delete(node.id);
			}}
			{...getTreeItemProps(node.id)}
		>
			<div
				className="flex items-center gap-1 group"
				style={{ paddingLeft: `${depth * 12}px` }}
			>
				{hasChildren ? (
					<button
						type="button"
						onClick={() => onToggle(node.id)}
						aria-label={open ? "Collapse" : "Expand"}
						aria-expanded={open}
						tabIndex={-1}
						className="flex-shrink-0 rounded p-0.5 text-slate-500 transition-colors hover:text-slate-900"
					>
						{open ? (
							<ChevronDown className="w-3 h-3" />
						) : (
							<ChevronRight className="w-3 h-3" />
						)}
					</button>
				) : (
					<span className="w-4 flex-shrink-0" />
				)}

				<Link
					href={`/wiki/${node.slug}`}
					tabIndex={-1}
					className={`flex-1 truncate rounded-lg px-2 py-1 text-sm transition-all duration-150 ${
						isActive
							? "border border-orange-500 bg-white font-medium text-slate-900 shadow-[0_6px_18px_rgba(15,23,42,0.06)]"
							: "border border-transparent text-slate-700 hover:border-orange-400 hover:bg-white hover:text-slate-900"
					}`}
					title={node.title}
				>
					{node.title}
				</Link>
			</div>

			{hasChildren && open && (
				<ul role="group" className="mt-0.5">
					{node.children.map((child) => (
						<TreeNode
							key={child.id}
							node={child}
							depth={depth + 1}
							activePath={activePath}
							expandedIds={expandedIds}
							onToggle={onToggle}
							treeItemRefs={treeItemRefs}
							getTreeItemProps={getTreeItemProps}
						/>
					))}
				</ul>
			)}
		</li>
	);
}

export default function WikiSidebar({ refreshKey }: WikiSidebarProps) {
	const pathname = usePathname();
	const router = useRouter();
	const { user } = useAuth();
	const isAdmin = user?.is_admin === true;
	const [tree, setTree] = useState<WikiTreeNode[]>([]);
	const [searchQuery, setSearchQuery] = useState("");
	const [searchResults, setSearchResults] = useState<WikiTreeNode[]>([]);
	const [loading, setLoading] = useState(true);
	const [mobileOpen, setMobileOpen] = useState(false);
	const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
	const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
	const mobileToggleRef = useRef<HTMLButtonElement>(null);
	const treeItemRefs = useRef<Map<string, HTMLElement>>(new Map());

	// Focus trap + escape for mobile drawer
	const mobileDrawerRef = useFocusTrap<HTMLElement>(mobileOpen);
	const closeMobileDrawer = useCallback(() => {
		setMobileOpen(false);
		requestAnimationFrame(() => mobileToggleRef.current?.focus());
	}, []);
	useEscapeKey(closeMobileDrawer, mobileOpen);

	const fetchTree = useCallback(async () => {
		try {
			const data = await wikiApi.getTree();
			setTree(data);
		} catch {
			// silent fail — sidebar is non-critical
		} finally {
			setLoading(false);
		}
	}, []);

	// Initialize all parent nodes as expanded when tree loads
	useEffect(() => {
		const allParentIds = new Set<string>();
		const collectIds = (nodes: WikiTreeNode[]) => {
			for (const n of nodes) {
				if (n.children.length > 0) allParentIds.add(n.id);
				collectIds(n.children);
			}
		};
		collectIds(tree);
		setExpandedIds(allParentIds);
	}, [tree]);

	// Reload when refreshKey changes or on custom wiki:refresh event
	useEffect(() => {
		fetchTree();
	}, [fetchTree, refreshKey]);

	useEffect(() => {
		const handler = () => fetchTree();
		window.addEventListener("wiki:refresh", handler);
		return () => window.removeEventListener("wiki:refresh", handler);
	}, [fetchTree]);

	// Debounced search
	useEffect(() => {
		if (searchTimeout.current) clearTimeout(searchTimeout.current);

		if (!searchQuery.trim()) {
			setSearchResults([]);
			return;
		}

		searchTimeout.current = setTimeout(async () => {
			try {
				const data = await wikiApi.searchPages(searchQuery.trim());
				// Map flat results to minimal tree-node shape for rendering
				setSearchResults(
					data.map((p) => ({
						id: p.id,
						slug: p.slug,
						title: p.title,
						parent_id: null,
						order_index: 0,
						children: [],
					})),
				);
			} catch {
				// silent
			}
		}, 300);

		return () => {
			if (searchTimeout.current) clearTimeout(searchTimeout.current);
		};
	}, [searchQuery]);

	// Close mobile sidebar on navigation
	useEffect(() => {
		setMobileOpen(false);
	}, [pathname]);

	const handleToggle = useCallback((id: string) => {
		setExpandedIds((prev) => {
			const next = new Set(prev);
			if (next.has(id)) next.delete(id);
			else next.add(id);
			return next;
		});
	}, []);

	// Maps for tree navigation
	const nodeMap = useMemo(() => {
		const map = new Map<string, WikiTreeNode>();
		const walk = (nodes: WikiTreeNode[]) => {
			for (const n of nodes) {
				map.set(n.id, n);
				walk(n.children);
			}
		};
		walk(tree);
		return map;
	}, [tree]);

	const parentMap = useMemo(() => {
		const map = new Map<string, string | null>();
		const walk = (nodes: WikiTreeNode[], parentId: string | null) => {
			for (const n of nodes) {
				map.set(n.id, parentId);
				walk(n.children, n.id);
			}
		};
		walk(tree, null);
		return map;
	}, [tree]);

	const activeNodes = searchQuery.trim() ? searchResults : tree;

	const treeNavCallbacks = useMemo(
		() => ({
			onToggle: handleToggle,
			onActivate: (id: string) => {
				const node = nodeMap.get(id);
				if (node) router.push(`/wiki/${node.slug}`);
			},
			getParentId: (id: string) => parentMap.get(id) ?? null,
		}),
		[handleToggle, nodeMap, parentMap, router],
	);

	const { focusedId, handleTreeKeyDown, getTreeItemProps } =
		useTreeNavigation(activeNodes, expandedIds, treeNavCallbacks);

	// Move DOM focus when focusedId changes
	useEffect(() => {
		if (focusedId) {
			treeItemRefs.current.get(focusedId)?.focus();
		}
	}, [focusedId]);

	const sidebarContent = (
		<div className="flex flex-col h-full">
			{/* Header */}
			<div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3">
				<Link
					href="/wiki"
					className="flex items-center gap-2 text-slate-900 transition-colors hover:text-slate-900"
				>
					<BookOpen className="h-4 w-4 text-orange-600" />
					<span className="text-sm font-semibold capitalize">
						Wiki
					</span>
				</Link>
				{isAdmin && (
					<Link
						href="/wiki/new"
						title="New page"
						aria-label="New page"
						className="rounded-[4px] border border-orange-500 bg-orange-500 p-1.5 text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
					>
						<Plus className="h-3.5 w-3.5" />
					</Link>
				)}
			</div>

			{/* Search */}
			<div className="border-b border-slate-200 bg-white px-3 py-2">
				<div className="relative">
					<Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
					<input
						type="text"
						value={searchQuery}
						onChange={(e) => setSearchQuery(e.target.value)}
						placeholder="Search pages…"
						aria-label="Search wiki pages"
						className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-xs text-slate-900 transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
					/>
					{searchQuery && (
						<button
							type="button"
							onClick={() => setSearchQuery("")}
							aria-label="Clear search"
							className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 transition-colors hover:text-slate-900"
						>
							<X className="w-3 h-3" />
						</button>
					)}
				</div>
			</div>

			{/* Page tree / search results */}
			<div className="custom-scrollbar flex-1 overflow-y-auto bg-white px-2 py-2">
				{loading ? (
					<div className="animate-pulse px-3 py-4 text-center text-xs text-slate-500">
						Loading…
					</div>
				) : searchQuery.trim() ? (
					searchResults.length === 0 ? (
						<p className="px-3 py-4 text-center text-xs text-slate-500">
							No results
						</p>
					) : (
						<ul
							role="tree"
							aria-label="Search results"
							className="space-y-0.5"
							onKeyDown={handleTreeKeyDown}
						>
							{searchResults.map((node) => (
								<TreeNode
									key={node.id}
									node={node}
									depth={0}
									activePath={pathname ?? ""}
									expandedIds={expandedIds}
									onToggle={handleToggle}
									treeItemRefs={treeItemRefs}
									getTreeItemProps={getTreeItemProps}
								/>
							))}
						</ul>
					)
				) : tree.length === 0 ? (
					<p className="px-3 py-4 text-center text-xs text-slate-500">
						No pages yet
					</p>
				) : (
					<ul
						role="tree"
						aria-label="Wiki pages"
						className="space-y-0.5"
						onKeyDown={handleTreeKeyDown}
					>
						{tree.map((node) => (
							<TreeNode
								key={node.id}
								node={node}
								depth={0}
								activePath={pathname ?? ""}
								expandedIds={expandedIds}
								onToggle={handleToggle}
								treeItemRefs={treeItemRefs}
								getTreeItemProps={getTreeItemProps}
							/>
						))}
					</ul>
				)}
			</div>
		</div>
	);

	return (
		<>
			{/* Mobile toggle button */}
			<button
				ref={mobileToggleRef}
				type="button"
				onClick={() => setMobileOpen(true)}
				aria-label="Open wiki navigation"
				className="fixed bottom-20 left-4 z-40 rounded-full border border-slate-200 bg-white p-3 text-slate-700 shadow-[0_8px_24px_rgba(15,23,42,0.12)] transition-colors hover:border-orange-400 hover:text-slate-900 lg:hidden"
			>
				<Menu className="w-5 h-5" />
			</button>

			{/* Mobile overlay */}
			{mobileOpen && (
				<div
					className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
					aria-hidden="true"
					onClick={closeMobileDrawer}
				/>
			)}

			{/* Mobile drawer */}
			<aside
				ref={mobileDrawerRef}
				role="dialog"
				aria-modal="true"
				aria-label="Wiki navigation"
				className={`fixed bottom-0 left-0 top-0 z-50 w-64 border-r border-slate-200 bg-white transition-transform duration-300 lg:hidden ${
					mobileOpen ? "translate-x-0" : "-translate-x-full"
				}`}
			>
				<div className="absolute top-3 right-3">
					<button
						type="button"
						onClick={closeMobileDrawer}
						aria-label="Close wiki navigation"
						className="rounded-lg p-1.5 text-slate-500 transition-colors hover:text-slate-900"
					>
						<X className="w-4 h-4" />
					</button>
				</div>
				{sidebarContent}
			</aside>

			{/* Desktop sidebar */}
			<aside
				aria-label="Wiki navigation"
				className="hidden h-full w-64 flex-shrink-0 flex-col overflow-hidden border-r border-slate-200 bg-white lg:flex"
			>
				{sidebarContent}
			</aside>
		</>
	);
}
