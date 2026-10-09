"use client";

import {
	ChevronDown,
	ChevronRight,
	Folder,
	FolderOpen,
	Loader2,
} from "lucide-react";
import { useCallback, useState } from "react";
import { runtimeConfig } from "@/lib/runtime-config";

function updateNodeInTree(
	nodes: FolderNode[],
	targetId: string,
	updater: (node: FolderNode) => FolderNode,
): FolderNode[] {
	return nodes.map((node) => {
		if (node.id === targetId) return updater(node);
		if (node.children) {
			return { ...node, children: updateNodeInTree(node.children, targetId, updater) };
		}
		return node;
	});
}

export interface FolderNode {
	id: string;
	name: string;
	childCount: number;
	webUrl: string;
	children?: FolderNode[];
	isLoaded?: boolean;
	isLoading?: boolean;
}

interface SharePointFolderTreeProps {
	driveId: string;
	selectedFolderIds: Set<string>;
	onSelectionChange: (selectedIds: Set<string>, selectedPaths: string[]) => void;
	/** API path prefix for the browsing endpoint. Defaults to sharepoint. */
	apiBasePath?: string;
}

/**
 * Lazily-loaded folder tree for browsing a document library.
 * Fetches children on expand via the browsing API endpoints.
 * Works for both SharePoint and OneDrive via the apiBasePath prop.
 */
export default function SharePointFolderTree({
	driveId,
	selectedFolderIds,
	onSelectionChange,
	apiBasePath = "/api/microsoft-oauth/sharepoint",
}: SharePointFolderTreeProps) {
	const [roots, setRoots] = useState<FolderNode[]>([]);
	const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
	const [isLoadingRoot, setIsLoadingRoot] = useState(false);
	const [hasLoadedRoot, setHasLoadedRoot] = useState(false);
	// Track folder paths: id -> webUrl path
	const [folderPaths, setFolderPaths] = useState<Map<string, string>>(new Map());

	const fetchChildren = useCallback(
		async (folderId: string): Promise<FolderNode[]> => {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resp = await fetch(
				`${apiBaseUrl}${apiBasePath}/drives/${driveId}/children?folder_id=${folderId}`,
				{ credentials: "include" },
			);
			if (!resp.ok) throw new Error("Failed to load folders");
			const data = await resp.json();
			return (data.folders || []).map(
				(f: { id: string; name: string; child_count: number; web_url: string }) => ({
					id: f.id,
					name: f.name,
					childCount: f.child_count,
					webUrl: f.web_url,
					children: undefined,
					isLoaded: false,
					isLoading: false,
				}),
			);
		},
		[driveId, apiBasePath],
	);

	// Load root folders on first render
	const loadRoot = useCallback(async () => {
		if (hasLoadedRoot || isLoadingRoot) return;
		setIsLoadingRoot(true);
		try {
			const children = await fetchChildren("root");
			setRoots(children);
			// Track paths
			const paths = new Map<string, string>();
			for (const c of children) {
				paths.set(c.id, c.webUrl);
			}
			setFolderPaths(paths);
			setHasLoadedRoot(true);
		} catch (err) {
			console.error("Failed to load root folders:", err);
		} finally {
			setIsLoadingRoot(false);
		}
	}, [hasLoadedRoot, isLoadingRoot, fetchChildren]);

	// Load on mount-like behavior
	if (!hasLoadedRoot && !isLoadingRoot && driveId) {
		loadRoot();
	}

	const handleToggle = useCallback(
		async (node: FolderNode) => {
			const isExpanded = expandedIds.has(node.id);

			if (isExpanded) {
				// Collapse
				setExpandedIds((prev) => {
					const next = new Set(prev);
					next.delete(node.id);
					return next;
				});
				return;
			}

			// Expand
			setExpandedIds((prev) => new Set(prev).add(node.id));

			if (!node.isLoaded && node.childCount > 0) {
				// Mark loading
				setRoots((prev) =>
					updateNodeInTree(prev, node.id, (n) => ({ ...n, isLoading: true })),
				);

				try {
					const children = await fetchChildren(node.id);
					setRoots((prev) =>
						updateNodeInTree(prev, node.id, (n) => ({
							...n,
							children,
							isLoaded: true,
							isLoading: false,
						})),
					);
					// Track paths for children
					setFolderPaths((prev) => {
						const next = new Map(prev);
						for (const c of children) {
							next.set(c.id, c.webUrl);
						}
						return next;
					});
				} catch {
					setRoots((prev) =>
						updateNodeInTree(prev, node.id, (n) => ({ ...n, isLoading: false })),
					);
				}
			}
		},
		[expandedIds, fetchChildren],
	);

	const handleCheckbox = useCallback(
		(node: FolderNode) => {
			const next = new Set(selectedFolderIds);
			if (next.has(node.id)) {
				next.delete(node.id);
			} else {
				next.add(node.id);
			}
			// Build paths array from selected IDs
			const paths = Array.from(next)
				.map((id) => folderPaths.get(id))
				.filter((p): p is string => !!p);
			onSelectionChange(next, paths);
		},
		[selectedFolderIds, onSelectionChange, folderPaths],
	);

	const renderNode = (node: FolderNode, depth: number) => {
		const isExpanded = expandedIds.has(node.id);
		const isSelected = selectedFolderIds.has(node.id);
		const hasChildren = node.childCount > 0;

		return (
			<div key={node.id}>
				<div
					className="flex items-center gap-1.5 py-1 px-1 rounded-lg hover:bg-slate-50 cursor-pointer group transition-colors"
					style={{ paddingLeft: `${depth * 16 + 4}px` }}
				>
					{/* Expand/collapse toggle */}
					<button
						type="button"
						className="w-4 h-4 flex items-center justify-center shrink-0 text-[color:var(--color-text-muted)]"
						onClick={() => handleToggle(node)}
						disabled={!hasChildren}
					>
						{node.isLoading ? (
							<Loader2 className="w-3 h-3 animate-spin" />
						) : hasChildren ? (
							isExpanded ? (
								<ChevronDown className="w-3 h-3" />
							) : (
								<ChevronRight className="w-3 h-3" />
							)
						) : null}
					</button>

					{/* Checkbox */}
					<input
						type="checkbox"
						checked={isSelected}
						onChange={() => handleCheckbox(node)}
						className="w-3.5 h-3.5 rounded border-[color:var(--color-border)] bg-transparent accent-[#0078D4] cursor-pointer shrink-0"
					/>

					{/* Folder icon + name */}
					<button
						type="button"
						className="flex items-center gap-1.5 flex-1 min-w-0"
						onClick={() => handleToggle(node)}
					>
						{isExpanded ? (
							<FolderOpen className="w-3.5 h-3.5 text-[#0078D4] shrink-0" />
						) : (
							<Folder className="w-3.5 h-3.5 text-[#0078D4]/70 shrink-0" />
						)}
						<span className="text-xs text-[color:var(--color-text-secondary)] truncate">
							{node.name}
						</span>
						{hasChildren && (
							<span className="text-[10px] text-[color:var(--color-text-muted)]">
								({node.childCount})
							</span>
						)}
					</button>
				</div>

				{/* Children */}
				{isExpanded && node.children && (
					<div>
						{node.children.map((child) => renderNode(child, depth + 1))}
					</div>
				)}
			</div>
		);
	};

	if (isLoadingRoot) {
		return (
			<div className="flex items-center gap-2 py-3 px-2">
				<Loader2 className="w-4 h-4 animate-spin text-[color:var(--color-text-muted)]" />
				<span className="text-xs text-[color:var(--color-text-muted)]">
					Loading folders...
				</span>
			</div>
		);
	}

	if (hasLoadedRoot && roots.length === 0) {
		return (
			<div className="py-3 px-2">
				<span className="text-xs text-[color:var(--color-text-muted)]">
					No folders found in this library.
				</span>
			</div>
		);
	}

	return (
		<div className="max-h-[280px] overflow-y-auto">
			{roots.map((node) => renderNode(node, 0))}
		</div>
	);
}
