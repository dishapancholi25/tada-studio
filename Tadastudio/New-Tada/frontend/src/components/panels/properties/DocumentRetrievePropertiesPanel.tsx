"use client";

import { FileText, Save, ShieldCheck, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import ConfigSidebar from "./ConfigSidebar";
import DocumentsSection from "./sections/DocumentsSection";
import type { Collection, DocumentItem } from "./sections/DocumentsSection";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { cn } from "@/lib/utils";

interface DocumentRetrieveConfig {
	collection_ids?: string[];
	parent_agent_id?: string;
}

interface DocumentRetrieveNodeData {
	id: string;
	name: string;
	document_retrieve_config?: DocumentRetrieveConfig;
}

interface DocumentRetrievePropertiesPanelProps {
	node: {
		id: string;
		data: DocumentRetrieveNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

type DocumentRetrieveTabId = "documents" | "guardrails";

export default function DocumentRetrievePropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: DocumentRetrievePropertiesPanelProps) {
	const config = node.data.document_retrieve_config || {};

	const [selectedCollections, setSelectedCollections] = useState<string[]>(
		config.collection_ids || [],
	);
	const [collections, setCollections] = useState<Collection[]>([]);
	const [loadingCollections, setLoadingCollections] = useState(false);
	const [activeTab, setActiveTab] = useState<DocumentRetrieveTabId>("documents");
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	const initialCollections = useRef(config.collection_ids || []);
	const contentRef = useRef<HTMLDivElement>(null);

	const hasUnsavedChanges = useMemo(
		() =>
			JSON.stringify(selectedCollections) !==
			JSON.stringify(initialCollections.current),
		[selectedCollections],
	);

	useEffect(() => {
		loadCollections().catch(console.error);
	}, []);

	// Responsive sidebar collapse
	useEffect(() => {
		const el = contentRef.current;
		if (!el || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				setSidebarCollapsed(entry.contentRect.width < 400);
			}
		});
		observer.observe(el);
		return () => observer.disconnect();
	}, []);

	const loadCollections = async () => {
		setLoadingCollections(true);
		try {
			const collectionsWithDocs = await api.getCollectionsWithDocuments();
			if (collectionsWithDocs) {
				setCollections(
					collectionsWithDocs.map((col) => ({
						id: col.id,
						name: col.name,
						documentCount: col.document_count,
						isReadOnly: col.is_read_only,
						createdByName: col.created_by_name,
						createdByEmail: col.created_by_email,
					})),
				);
			}
		} catch (error) {
			console.error("Failed to load collections:", error);
		} finally {
			setLoadingCollections(false);
		}
	};

	const handleSave = useCallback(() => {
		onUpdateNode(node.id, {
			document_retrieve_config: {
				...config,
				collection_ids: selectedCollections,
			},
		});
		initialCollections.current = [...selectedCollections];
		onClose();
	}, [node.id, config, selectedCollections, onUpdateNode, onClose]);

	// Keyboard shortcut: Cmd/Ctrl+S to save
	const handleSaveRef = useRef(handleSave);
	handleSaveRef.current = handleSave;

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSaveRef.current();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	const handleDelete = useCallback(() => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [node.id, onDeleteNode, onClose]);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const panelTabs = useMemo(
		() => [
			{
				id: "documents" as const,
				label: "Documents",
				description: "Select sources",
				icon: <FileText className="h-4 w-4" />,
			},
			{
				id: "guardrails" as const,
				label: "Guardrails",
				description: "Safety policies",
				icon: <ShieldCheck className="h-4 w-4" />,
			},
		],
		[],
	);

	const isGuardrailsTab = activeTab === "guardrails";

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleStopPropagation}
			>
				<div
					className={cn(
						"flex min-h-[320px] flex-col rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]",
						isGuardrailsTab
							? "max-h-[90vh] overflow-visible"
							: "max-h-[80vh] overflow-hidden",
					)}
				>
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex flex-wrap items-start justify-between gap-4 px-6 pb-4 pt-5">
							<div className="flex min-w-0 items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<FileText className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										Document Retrieve
									</h2>
									<p className="mt-0.5 text-sm text-gray-600">
										Select collections the agent can retrieve documents from
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					<div
						ref={contentRef}
						className={cn(
							"flex min-h-0 flex-1",
							!isGuardrailsTab && "overflow-hidden",
						)}
					>
						<ConfigSidebar
							items={panelTabs}
							activeItem={activeTab}
							onChange={(id) =>
								setActiveTab(id as DocumentRetrieveTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"flex-1 min-h-0 bg-slate-50 px-6 py-4",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
							{activeTab === "documents" && (
								<DocumentsSection
									documentSelectionMode="collections"
									onSelectionModeChange={() => {}}
									selectedCollections={selectedCollections}
									onSelectedCollectionsChange={setSelectedCollections}
									selectedDocuments={[]}
									onSelectedDocumentsChange={() => {}}
									collections={collections}
									documents={[]}
									loadingCollections={loadingCollections}
									loadingDocuments={false}
								/>
							)}

							{activeTab === "guardrails" && (
								<ToolGuardrailsSection toolNodeId={node.id} />
							)}
						</div>
					</div>

					<div className="border-t border-gray-200 bg-white px-6 py-3">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<button
								type="button"
								onClick={handleDelete}
								className="flex items-center gap-1.5 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-xs text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
							>
								<Trash2 className="w-3.5 h-3.5" />
								Delete Node
							</button>

							<div className="flex items-center gap-3 sm:ml-auto">
								{hasUnsavedChanges && (
									<span className="flex items-center gap-1.5 text-[11px] text-gray-600">
										<span className="h-1.5 w-1.5 animate-smoothPulse rounded-[4px] bg-orange-500" />
										Unsaved
									</span>
								)}
								<span className="hidden text-[11px] text-gray-400 sm:inline">
									{"\u2318"}S to save
								</span>
								<button
									type="button"
									onClick={onClose}
									className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleSave}
									disabled={!hasUnsavedChanges}
									className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									<span className="inline-flex items-center gap-1.5">
										<Save className="w-3.5 h-3.5" />
										Save Changes
									</span>
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				onClose={() => setShowDeleteConfirm(false)}
				onConfirm={handleConfirmDelete}
				title="Delete Node?"
				message="Are you sure you want to delete this node? This action cannot be undone."
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>

		</div>
	);
}
