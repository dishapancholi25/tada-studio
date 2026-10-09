"use client";

import {
	ChevronLeft,
	Coins,
	Edit2,
	FileText,
	Folder,
	Globe,
	Lock,
	Plus,
	Save,
	Search,
	Settings,
	Trash2,
	Upload,
	X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { useToast } from "@/contexts/ToastContext";
import {
	type Document as ApiDocument,
	api,
	type DocumentCollection,
	type SearchResult,
} from "@/lib/api";
import {
	type ModelDeploymentOption,
	modelDeploymentAPI,
} from "@/lib/model-deployment-api";
import Button from "../../ui/Button";
import FormInput from "../../ui/FormInput";
import FormTextarea from "../../ui/FormTextarea";
import MetaChip from "../../ui/MetaChip";
import ConfirmDialog from "../../dialogs/ConfirmDialog";
import GroupSelector from "../../settings/groups/GroupSelector";
import DataSourceStatsBar from "../shared/DataSourceStatsBar";
import DataSourceFilterBar from "../shared/DataSourceFilterBar";
import LoadingSkeleton from "../shared/LoadingSkeleton";
import EmptyState from "../shared/EmptyState";
import DocumentDetailsPanel from "../documents/DocumentDetailsPanel";
import DocumentSearchModal from "../documents/DocumentSearchModal";
import DocumentTable from "../documents/DocumentTable";
import DocumentUploadZone, {
	type ChunkingConfig,
} from "../documents/DocumentUploadZone";
import EmbeddingModelSelector from "../documents/EmbeddingModelSelector";
import ReprocessModal from "../documents/ReprocessModal";
import type { CollectionFilterTab } from "../documents/CollectionSidebar";

type ViewMode = "grid" | "detail";

const FILTER_TABS = [
	{ key: "all", label: "All" },
	{ key: "my", label: "My Collections" },
	{ key: "shared", label: "Shared" },
];

export default function DocumentsTab() {
	const router = useRouter();
	const { showSuccess, showError, showWarning, showInfo } = useToast();

	// View State
	const [viewMode, setViewMode] = useState<ViewMode>("grid");
	const [selectedCollection, setSelectedCollection] = useState<string>("");
	const [isDraggingInline, setIsDraggingInline] = useState(false);
	const inlineFileInputRef = useRef<HTMLInputElement>(null);

	// Document & Collection State
	const [selectedDocument, setSelectedDocument] = useState<ApiDocument | null>(
		null,
	);
	const [searchTerm, setSearchTerm] = useState("");
	const [documents, setDocuments] = useState<ApiDocument[]>([]);
	const [collections, setCollections] = useState<DocumentCollection[]>([]);
	const [loading, setLoading] = useState(false);
	const [collectionsLoading, setCollectionsLoading] = useState(true);
	const [uploading, setUploading] = useState(false);

	// Filter State
	const [activeFilterTab, setActiveFilterTab] =
		useState<CollectionFilterTab>("all");
	const [collectionSearchTerm, setCollectionSearchTerm] = useState("");

	// Embedding Model State
	const [embeddingModels, setEmbeddingModels] = useState<
		ModelDeploymentOption[]
	>([]);
	const [selectedEmbeddingModel, setSelectedEmbeddingModel] =
		useState<string>("");
	const [loadingEmbeddings, setLoadingEmbeddings] = useState(true);

	// Dialog States
	const [deleteDocDialog, setDeleteDocDialog] = useState({
		isOpen: false,
		docId: "",
	});
	const [deleteCollDialog, setDeleteCollDialog] = useState({
		isOpen: false,
		collId: "",
	});
	const [visibilityConfirmDialog, setVisibilityConfirmDialog] = useState<{
		isOpen: boolean;
		action: () => void;
	}>({ isOpen: false, action: () => {} });

	// Upload Config State
	const [uploadConfig, setUploadConfig] = useState<ChunkingConfig>({
		strategy: "recursive",
		chunkSize: 1000,
		chunkOverlap: 200,
		loaderMode: "single",
		preset: "balanced",
	});

	// Collection Creation State
	const [isCreatingCollection, setIsCreatingCollection] = useState(false);
	const [newCollection, setNewCollection] = useState({
		name: "",
		description: "",
	});
	const [isGlobalVisibility, setIsGlobalVisibility] = useState(false);
	const [selectedVisibilityGroups, setSelectedVisibilityGroups] = useState<
		string[]
	>([]);

	// Collection Edit State
	const [editingCollectionId, setEditingCollectionId] = useState<string | null>(
		null,
	);
	const [editCollectionName, setEditCollectionName] = useState("");
	const [editCollectionDescription, setEditCollectionDescription] =
		useState("");
	const [isEditGlobalVisibility, setIsEditGlobalVisibility] = useState(false);
	const [editVisibilityGroups, setEditVisibilityGroups] = useState<string[]>(
		[],
	);

	// Search Modal State
	const [searchModal, setSearchModal] = useState({
		isOpen: false,
		documentId: undefined as string | undefined,
		documentName: undefined as string | undefined,
		collectionId: undefined as string | undefined,
	});

	// Reprocess Modal State
	const [reprocessModal, setReprocessModal] = useState({
		isOpen: false,
		documentId: "",
		documentName: "",
		chunkCount: 0,
	});

	// Embedding model change confirmation
	const [embeddingChangeConfirm, setEmbeddingChangeConfirm] = useState<{
		pendingModelId: string;
		collectionId: string;
		documentCount: number;
	} | null>(null);
	const [reprocessingCollection, setReprocessingCollection] = useState(false);

	// Derived State
	const hasEmbeddingModels = embeddingModels.length > 0;
	const selectedCol =
		collections.find((c) => c.id === selectedCollection) ?? null;
	const editingCol = editingCollectionId
		? (collections.find((c) => c.id === editingCollectionId) ?? null)
		: null;

	const stats = useMemo(
		() => ({
			processedCount: documents.filter((d) => d.status === "processed").length,
			failedCount: documents.filter((d) => d.status === "failed").length,
			totalSize: documents.reduce((sum, d) => sum + d.size, 0),
			totalTokens: documents.reduce(
				(sum, d) => sum + (d.embedding_tokens ?? 0),
				0,
			),
			totalCost: documents.reduce(
				(sum, d) => sum + (d.embedding_cost ?? 0),
				0,
			),
		}),
		[documents],
	);

	const filteredDocuments = useMemo(
		() =>
			documents.filter((doc) =>
				doc.name.toLowerCase().includes(searchTerm.trim().toLowerCase()),
			),
		[documents, searchTerm],
	);

	const filteredCollections = useMemo(
		() =>
			collections.filter((col) =>
				col.name.toLowerCase().includes(collectionSearchTerm.trim().toLowerCase()),
			),
		[collections, collectionSearchTerm],
	);

	// Data Loading
	useEffect(() => {
		void loadEmbeddingModels();
	}, []);

	useEffect(() => {
		setEditingCollectionId(null);
		setEditCollectionName("");
		setEditCollectionDescription("");
		setEditVisibilityGroups([]);

		const col = collections.find((c) => c.id === selectedCollection);
		if (col?.embedding_deployment_id) {
			setSelectedEmbeddingModel(col.embedding_deployment_id);
		} else {
			const defaultModel =
				embeddingModels.find((m) => m.is_default) ?? embeddingModels[0];
			if (defaultModel) {
				setSelectedEmbeddingModel(defaultModel.id);
			}
		}
	}, [selectedCollection]); // eslint-disable-line react-hooks/exhaustive-deps

	useEffect(() => {
		void loadCollections(activeFilterTab);
	}, [activeFilterTab]); // eslint-disable-line react-hooks/exhaustive-deps

	const loadCollections = async (filterType?: CollectionFilterTab) => {
		setCollectionsLoading(true);
		try {
			const data = await api.getCollections(filterType);
			setCollections(data);
			if (
				data.length > 0 &&
				!selectedCollection &&
				viewMode === "grid"
			) {
				// Don't auto-select in grid view
			} else if (
				selectedCollection &&
				!data.find((c) => c.id === selectedCollection)
			) {
				setSelectedCollection("");
				setViewMode("grid");
			}
		} catch (error) {
			console.error("Failed to load collections:", error);
		} finally {
			setCollectionsLoading(false);
		}
	};

	const loadEmbeddingModels = async () => {
		try {
			setLoadingEmbeddings(true);
			const models = await modelDeploymentAPI.listEmbeddingSelectOptions();
			setEmbeddingModels(models);

			const col = collections.find((c) => c.id === selectedCollection);
			if (
				col?.embedding_deployment_id &&
				models.find((m) => m.id === col.embedding_deployment_id)
			) {
				setSelectedEmbeddingModel(col.embedding_deployment_id);
			} else {
				const defaultModel = models.find((m) => m.is_default);
				const modelToSelect = defaultModel || models[0];
				if (modelToSelect) {
					setSelectedEmbeddingModel(modelToSelect.id);
				}
			}
		} catch (error) {
			console.error("Failed to load embedding models:", error);
			showError(
				"Failed to Load Models",
				"Could not load embedding models. Please try again.",
			);
		} finally {
			setLoadingEmbeddings(false);
		}
	};

	const loadDocuments = async () => {
		if (!selectedCollection) return;
		setLoading(true);
		try {
			const data = await api.getDocuments(selectedCollection);
			setDocuments(data);
		} catch (error) {
			console.error("Failed to load documents:", error);
		} finally {
			setLoading(false);
		}
	};

	// Navigation
	const handleDrillIntoCollection = async (col: DocumentCollection) => {
		setSelectedCollection(col.id);
		setViewMode("detail");
		setSearchTerm("");
		setSelectedDocument(null);
		setLoading(true);
		try {
			const data = await api.getDocuments(col.id);
			setDocuments(data);
		} catch (error) {
			console.error("Failed to load documents:", error);
		} finally {
			setLoading(false);
		}
	};

	const handleBackToCollections = () => {
		setViewMode("grid");
		setSearchTerm("");
		setSelectedDocument(null);
	};

	const openEditModal = (col: DocumentCollection) => {
		const groups = col.visible_to_groups ?? [];
		const isShared = groups.length > 0;
		setEditCollectionName(col.name);
		setEditCollectionDescription(col.description || "");
		setIsEditGlobalVisibility(isShared);
		setEditVisibilityGroups(
			isShared ? groups.filter((g) => g !== "__all__") : [],
		);
		setSelectedCollection(col.id);
		setEditingCollectionId(col.id);
	};

	const handleFilterChange = (filter: string) => {
		setActiveFilterTab(filter as CollectionFilterTab);
		setViewMode("grid");
		setCollectionSearchTerm("");
	};

	// Event Handlers
	const handleFileUpload = async (files: FileList) => {
		if (!selectedCollection || files.length === 0) return;

		if (!selectedEmbeddingModel && embeddingModels.length > 0) {
			showWarning(
				"No Embedding Model",
				"Please select an embedding model before uploading documents.",
			);
			return;
		}

		const col = collections.find((c) => c.id === selectedCollection);
		const embeddingId =
			col?.embedding_deployment_id || selectedEmbeddingModel || undefined;

		setUploading(true);
		try {
			const fileArray = Array.from(files);
			const result = await api.uploadDocuments(fileArray, selectedCollection, {
				chunkSize: uploadConfig.chunkSize ?? 1000,
				chunkOverlap: uploadConfig.chunkOverlap,
				loaderMode: uploadConfig.loaderMode,
				strategy: uploadConfig.strategy,
				embeddingDeploymentId: embeddingId,
			});

			await loadDocuments();
			await loadCollections(activeFilterTab);
			let costInfo = "";
			if (result.embedding_tokens > 0) {
				costInfo = ` (${result.embedding_tokens.toLocaleString()} tokens`;
				if (result.embedding_cost != null && result.embedding_cost > 0) {
					costInfo += `, $${result.embedding_cost.toFixed(4)}`;
				}
				costInfo += ")";
			}
			showSuccess(
				"Upload Complete",
				`Successfully uploaded ${result.documents.length} documents${costInfo}`,
			);
			setEditingCollectionId(null);
			setViewMode("detail");
		} catch (error) {
			const errorMessage =
				error instanceof Error
					? error.message
					: "Failed to upload documents. Please try again.";
			showError("Upload Failed", errorMessage);
		} finally {
			setUploading(false);
		}
	};

	const getVisibleToGroups = (): string[] | undefined => {
		if (!isGlobalVisibility) return undefined;
		if (selectedVisibilityGroups.length > 0) return selectedVisibilityGroups;
		return ["__all__"];
	};

	const handleCreateCollection = async () => {
		if (!newCollection.name.trim()) {
			showWarning(
				"Missing Name",
				"Please provide a name for the new collection.",
			);
			return;
		}

		const visibleToGroups = getVisibleToGroups();

		const doCreate = async () => {
			try {
				const createdCollection = await api.createCollection(
					newCollection.name,
					newCollection.description,
					visibleToGroups,
				);
				await loadCollections(activeFilterTab);
				setSelectedCollection(createdCollection.id);
				setIsCreatingCollection(false);
				setNewCollection({ name: "", description: "" });
				setIsGlobalVisibility(false);
				setSelectedVisibilityGroups([]);
				showSuccess(
					"Collection Created",
					`Collection "${newCollection.name}" has been created.`,
				);
			} catch (error) {
				const errorMessage =
					error instanceof Error
						? error.message
						: "Failed to create collection. Please try again.";
				showError("Creation Failed", errorMessage);
			}
		};

		if (
			isGlobalVisibility &&
			(!selectedVisibilityGroups.length ||
				selectedVisibilityGroups.includes("__all__"))
		) {
			setVisibilityConfirmDialog({ isOpen: true, action: doCreate });
		} else {
			await doCreate();
		}
	};

	const handleUpdateVisibility = async (
		collectionId: string,
		visibleToGroups: string[],
	) => {
		const doUpdate = async () => {
			try {
				await api.updateCollectionVisibility(collectionId, visibleToGroups);
				await loadCollections(activeFilterTab);
				showSuccess(
					"Visibility Updated",
					"Collection visibility has been updated.",
				);
			} catch (error: any) {
				if (error?.message?.includes("403")) {
					showError(
						"Permission Denied",
						"You don't have permission to modify this collection.",
					);
				} else if (error?.message?.includes("404")) {
					showError("Not Found", "Collection not found.");
				} else {
					showError(
						"Update Failed",
						"Failed to update collection visibility. Please try again.",
					);
				}
			}
		};

		if (visibleToGroups.includes("__all__")) {
			setVisibilityConfirmDialog({ isOpen: true, action: doUpdate });
		} else {
			await doUpdate();
		}
	};

	const isDocumentReadOnly = (documentId: string): boolean => {
		const doc = documents.find((d) => d.id === documentId);
		if (!doc) return false;
		const col = collections.find((c) => c.id === doc.collection_id);
		return col?.is_read_only ?? false;
	};

	const handleDeleteDocument = async (documentId: string) => {
		if (isDocumentReadOnly(documentId)) {
			showError(
				"Cannot Delete",
				"You cannot delete documents from a collection you don't own.",
			);
			return;
		}
		setDeleteDocDialog({ isOpen: true, docId: documentId });
	};

	const confirmDeleteDocument = async () => {
		try {
			await api.deleteDocument(deleteDocDialog.docId);
			await loadDocuments();
			setSelectedDocument(null);
			showSuccess(
				"Document Deleted",
				"Document has been successfully removed.",
			);
		} catch (error) {
			showError(
				"Delete Failed",
				"Failed to delete document. Please try again.",
			);
		}
	};

	const handleDeleteCollection = async (collectionId: string) => {
		const col = collections.find((c) => c.id === collectionId);
		if (col?.is_read_only) {
			showError(
				"Cannot Delete",
				"You cannot delete a shared collection you don't own.",
			);
			return;
		}
		setDeleteCollDialog({ isOpen: true, collId: collectionId });
	};

	const confirmDeleteCollection = async () => {
		try {
			await api.deleteCollection(deleteCollDialog.collId);
			await loadCollections(activeFilterTab);
			if (selectedCollection === deleteCollDialog.collId) {
				setSelectedCollection(collections[0]?.id || "");
			}
			setViewMode("grid");
			showSuccess(
				"Collection Deleted",
				"Collection has been successfully removed.",
			);
		} catch (error) {
			showError(
				"Delete Failed",
				"Failed to delete collection. Please try again.",
			);
		}
	};

	const handleClearFailedDocuments = async () => {
		if (!selectedCollection) return;
		if (stats.failedCount === 0) {
			showInfo(
				"No Failed Documents",
				"There are no failed documents to clear.",
			);
			return;
		}

		try {
			const result = await api.deleteFailedDocuments(selectedCollection);
			await loadDocuments();
			showSuccess(
				"Failed Documents Cleared",
				result.message ||
					`Removed ${stats.failedCount} failed document(s).`,
			);
		} catch (error) {
			showError(
				"Clear Failed",
				"Failed to clear failed documents. Please try again.",
			);
		}
	};

	const handleReprocess = async (config: {
		strategy: string;
		chunkSize: number | null;
		chunkOverlap: number;
	}) => {
		try {
			const result = await api.reprocessDocument(reprocessModal.documentId, {
				chunkSize: config.chunkSize,
				chunkOverlap: config.chunkOverlap,
				strategy: config.strategy,
				embeddingDeploymentId: selectedEmbeddingModel || undefined,
			});

			if (result.success) {
				showSuccess(
					"Document Reprocessed",
					`Document has been re-chunked with ${result.new_chunk_count} chunks.`,
				);
				await loadDocuments();

				if (selectedDocument?.id === reprocessModal.documentId) {
					const updatedDocs = await api.getDocuments(selectedCollection);
					const updatedDoc = updatedDocs.find(
						(d) => d.id === reprocessModal.documentId,
					);
					if (updatedDoc) setSelectedDocument(updatedDoc);
				}
			}
		} catch (error) {
			showError(
				"Reprocess Failed",
				"Failed to reprocess document. Please try again.",
			);
			throw error;
		}
	};

	const handleSearch = async (query: string): Promise<SearchResult[]> => {
		const collectionId = searchModal.collectionId ?? selectedCollection;
		if (!query.trim() || !collectionId) return [];

		const embeddingDeploymentId =
			collections.find((c) => c.id === collectionId)
				?.embedding_deployment_id ?? undefined;

		try {
			const result = await api.searchDocuments(query, [collectionId], {
				k: 5,
				documentIds: searchModal.documentId
					? [searchModal.documentId]
					: undefined,
				embeddingDeploymentId,
			});
			return result.results;
		} catch (error) {
			showError(
				"Search Failed",
				"Failed to search documents. Please try again.",
			);
			return [];
		}
	};

	const handleEmbeddingModelChange = (modelId: string) => {
		const targetId = editingCollectionId ?? selectedCollection;
		const col = collections.find((c) => c.id === targetId);
		if (
			col?.embedding_deployment_id &&
			modelId !== col.embedding_deployment_id
		) {
			setEmbeddingChangeConfirm({
				pendingModelId: modelId,
				collectionId: col.id,
				documentCount: col.document_count ?? 0,
			});
			return;
		}
		setSelectedEmbeddingModel(modelId);
	};

	const handleConfirmEmbeddingChange = async () => {
		if (!embeddingChangeConfirm) return;
		const { pendingModelId, collectionId } = embeddingChangeConfirm;
		setReprocessingCollection(true);
		try {
			await api.updateCollection(collectionId, {
				embedding_deployment_id: pendingModelId,
			});
			await api.reprocessCollection(collectionId, {
				embeddingDeploymentId: pendingModelId,
			});
			setSelectedEmbeddingModel(pendingModelId);
			await loadCollections(activeFilterTab);
			showSuccess(
				"Embedding Model Updated",
				"All documents have been reprocessed with the new embedding model.",
			);
		} catch {
			showError(
				"Update Failed",
				"Failed to update embedding model and reprocess documents.",
			);
		} finally {
			setReprocessingCollection(false);
			setEmbeddingChangeConfirm(null);
		}
	};

	const closeEditModal = () => {
		setEditingCollectionId(null);
		setIsEditGlobalVisibility(false);
		setEditVisibilityGroups([]);
	};

	// Tutorial event handlers
	useEffect(() => {
		const handler = () => {
			setEditingCollectionId(null);
			setIsEditGlobalVisibility(false);
			setEditVisibilityGroups([]);
			setViewMode("grid");
			setSearchTerm("");
			setSelectedDocument(null);
		};
		window.addEventListener("tutorialCloseCollectionEditor", handler);
		return () =>
			window.removeEventListener("tutorialCloseCollectionEditor", handler);
	}, []);

	useEffect(() => {
		const handler = async () => {
			const tutorialCol = collections.find(
				(c) => c.name === "Tutorial Collection",
			);
			if (tutorialCol) {
				await api.deleteCollection(tutorialCol.id).catch(() => {});
				await loadCollections(activeFilterTab);
			}
		};
		window.addEventListener("tutorialDeleteCollection", handler);
		return () =>
			window.removeEventListener("tutorialDeleteCollection", handler);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [collections, activeFilterTab]);

	return (
		<div className="space-y-5 bg-white p-6 text-slate-900">
			{/* Stats Bar */}
			<DataSourceStatsBar
				title="Document Collections"
				titleIcon={
					<Folder className="w-5 h-5 text-[color:var(--color-accent)]" />
				}
				actionSlot={
					<Button
						data-tutorial="new-collection-btn"
						onClick={() => setIsCreatingCollection(true)}
						variant="secondary"
						icon={<Plus className="w-4 h-4" />}
					className="border-[#ff6b00] bg-[#ff6b00] text-white shadow-md hover:border-[#e55f00] hover:bg-[#e55f00]"
					>
						Add Collection
					</Button>
				}
				stats={[
					{
						label: "Total Collections",
						value: collections.length,
						color: "primary",
						icon: <Folder className="w-6 h-6" />,
					},
					{
						label: "Total Documents",
						value: collections.reduce(
							(sum, c) => sum + (c.document_count ?? 0),
							0,
						),
						color: "green",
						icon: <FileText className="w-6 h-6" />,
					},
					{
						label: "Total Searches",
						value: collections.reduce(
							(sum, c) => sum + (c.search_count ?? 0),
							0,
						),
						icon: <Search className="w-6 h-6" />,
					},
					{
						label: "Embedding Cost",
						value: collections.reduce(
							(sum, c) => sum + (c.total_embedding_cost ?? 0),
							0,
						),
						icon: <Coins className="w-6 h-6" />,
						format: "currency",
					},
				]}
			/>

			{/* Filter + Search */}
			<DataSourceFilterBar
				filterTabs={FILTER_TABS}
				activeFilter={activeFilterTab}
				onFilterChange={handleFilterChange}
				searchTerm={collectionSearchTerm}
				onSearchChange={setCollectionSearchTerm}
				searchPlaceholder="Search collections..."
			/>

			{/* Main Content */}
			{viewMode === "grid" ? (
				/* ── Collection Grid ── */
				<div
					className="rounded-2xl border border-orange-300 bg-white p-5 shadow-md"
				>
					<div className="flex items-center justify-between gap-3 mb-4">
						<div>
							<h3 className="text-base font-semibold text-slate-900">
								Collections
							</h3>
							<p className="text-xs text-slate-500">
								{collections.length} collection
								{collections.length !== 1 ? "s" : ""}
							</p>
						</div>
					</div>

					{collectionsLoading ? (
						<LoadingSkeleton variant="card-grid" />
					) : filteredCollections.length === 0 ? (
						<EmptyState
							icon={<Folder className="w-10 h-10" />}
							title={
								collectionSearchTerm
									? "No collections found"
									: "No collections yet"
							}
							description={
								collectionSearchTerm
									? "No collections match your search"
									: activeFilterTab === "shared"
										? "No shared collections available"
										: activeFilterTab === "my"
											? "You haven't created any collections"
											: "Create your first collection to get started"
							}
							primaryAction={
								!collectionSearchTerm && activeFilterTab !== "shared"
									? {
											label: "Add Collection",
											icon: <Plus className="w-4 h-4" />,
											onClick: () => setIsCreatingCollection(true),
										}
									: undefined
							}
						/>
					) : (
						<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
							{filteredCollections.map((col, colIndex) => (
								<div
									key={col.id}
									onClick={() => handleDrillIntoCollection(col)}
									className="group cursor-pointer rounded-xl border border-orange-200 bg-white p-4 shadow-sm transition-all duration-200 hover:border-orange-500 hover:bg-white hover:shadow-md"
									style={{
										background: "white",
										borderColor: "rgba(254, 215, 170, 0.9)",
									}}
									onMouseEnter={(e) => {
										(e.currentTarget as HTMLElement).style.borderColor =
											"rgba(249, 115, 22, 0.65)";
									}}
									onMouseLeave={(e) => {
										(e.currentTarget as HTMLElement).style.borderColor =
											"rgba(254, 215, 170, 0.9)";
									}}
									{...(colIndex === 0
										? { "data-tutorial": "collection-card-first" }
										: {})}
								>
									{/* Row 1: Icon + Name + Actions */}
									<div className="flex items-start gap-3 mb-3">
										<div className="flex-shrink-0 rounded-lg border border-orange-200 bg-orange-500 p-2.5">
											<Folder className="h-5 w-5 text-white" />
										</div>
										<div className="flex-1 min-w-0">
											<div className="flex items-center gap-2">
												<h4 className="truncate text-sm font-semibold text-slate-900 transition-colors group-hover:text-slate-900">
													{col.name}
												</h4>
												{col.document_count !== undefined &&
													col.document_count !== null && (
														<span className="flex-shrink-0 rounded border border-orange-300 bg-white px-1.5 py-0.5 font-mono text-xs text-orange-700">
															{col.document_count}
														</span>
													)}
												{(col.unprocessed_count ?? 0) > 0 && (
													<span className="flex-shrink-0 w-2 h-2 rounded-full bg-amber-400 animate-[smoothPulse_2s_ease-in-out_infinite]" title={`${col.unprocessed_count} documents processing`} />
												)}
											</div>
											{col.description && (
												<p className="mt-0.5 line-clamp-1 text-xs text-slate-500">
													{col.description}
												</p>
											)}
										</div>
										<div className="flex items-center gap-1 flex-shrink-0">
											{!col.is_read_only && (
												<button
													type="button"
													onClick={(e) => {
														e.stopPropagation();
														openEditModal(col);
													}}
													className="rounded p-1.5 text-slate-500 transition-colors hover:bg-white hover:text-slate-900"
													title="Edit collection & upload documents"
												>
													<Edit2 className="w-3.5 h-3.5" />
												</button>
											)}
											{!col.is_read_only && (
												<button
													type="button"
													onClick={(e) => {
														e.stopPropagation();
														handleDeleteCollection(col.id);
													}}
													className="rounded p-1.5 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600"
													title="Delete collection"
													{...(col.name === "Tutorial Collection"
														? {
																"data-tutorial":
																	"collection-delete-btn",
															}
														: {})}
												>
													<Trash2 className="w-3.5 h-3.5" />
												</button>
											)}
										</div>
									</div>

									{/* Row 2: Metadata chips */}
									<div className="flex flex-wrap items-center gap-1.5 mb-2">
										{col.is_read_only && (
											<MetaChip label="Read-only" color="gray" />
										)}
										{col.visible_to_groups?.includes("__all__") ? (
											<MetaChip label="Everyone" color="accent" />
										) : (col.visible_to_groups?.length ?? 0) > 0 ? (
											<MetaChip
												label="Groups"
												value={(col.visible_to_groups?.length ?? 0).toString()}
												color="purpleDS"
											/>
										) : (
											<MetaChip label="Private" color="gray" />
										)}
										{col.embedding_deployment_id &&
											(() => {
												const m = embeddingModels.find(
													(em) =>
														em.id === col.embedding_deployment_id,
												);
												return (
													<MetaChip
														label={
															m
																? m.display_name || m.name
																: "Embedded"
														}
														color="plum"
													/>
												);
											})()}
									</div>

									{/* Row 3: Stats line */}
									<div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
										{col.created_by_name && (
											<span>{col.created_by_name}</span>
										)}
										{(col.search_count ?? 0) > 0 && (
											<span className="flex items-center gap-1">
												<Search className="w-3 h-3" />
												{col.search_count!.toLocaleString()} searches
											</span>
										)}
										{(col.total_embedding_tokens ?? 0) > 0 && (
											<span className="font-mono">
												{col.total_embedding_tokens!.toLocaleString()}{" "}
												tokens
											</span>
										)}
										{(col.total_embedding_cost ?? 0) > 0 && (
											<span className="inline-flex items-center gap-1 font-mono">
												<Coins className="w-3 h-3 text-amber-400" />$
												{col.total_embedding_cost!.toFixed(4)}
											</span>
										)}
									</div>
								</div>
							))}
						</div>
					)}
				</div>
			) : selectedCol ? (
				/* ── Collection Detail (drill-down) ── */
				<div
					className="flex max-h-[calc(100vh-200px)] min-h-[700px] flex-col gap-4 rounded-2xl border border-orange-300 bg-white p-5 shadow-md"
				>
					{/* Breadcrumb header */}
					{/* Desktop: 3-column (back | name+stats centered | actions) */}
					{/* Tablet/Mobile: 2 rows (back+actions / name+stats) */}
					<div className="relative flex flex-col gap-1 lg:flex-row lg:items-center lg:justify-between lg:gap-3">
						{/* Back button */}
						<button
							type="button"
							onClick={handleBackToCollections}
							className="group flex flex-shrink-0 items-center gap-1.5 rounded-lg border border-transparent px-2 py-1 transition-colors hover:border-orange-300 hover:bg-white self-start lg:self-auto"
						>
							<ChevronLeft className="h-4 w-4 text-slate-500 transition-colors group-hover:text-slate-900" />
							<span className="text-sm text-slate-500 transition-colors group-hover:text-slate-900">
								Collections
							</span>
						</button>

						{/* Name + stats: centered on desktop, left-aligned on mobile */}
						<div className="min-w-0 px-2 lg:flex-1 lg:text-center lg:px-0 order-last lg:order-none">
							<h3 className="truncate text-sm font-semibold text-slate-900">
								{selectedCol.name}
							</h3>
							<p className="flex flex-wrap items-center gap-x-2 text-xs text-slate-500 lg:justify-center">
								<span>{documents.length} doc{documents.length !== 1 ? "s" : ""}</span>
								{(selectedCol.search_count ?? 0) > 0 && (
									<span>{selectedCol.search_count!.toLocaleString()} search{selectedCol.search_count !== 1 ? "es" : ""}</span>
								)}
								{stats.failedCount > 0 && (
									<span className="text-red-400">{stats.failedCount} failed</span>
								)}
								{stats.totalTokens > 0 && (
									<span className="font-mono">{stats.totalTokens.toLocaleString()} tokens</span>
								)}
								{stats.totalCost > 0 && (
									<span className="inline-flex items-center gap-1 font-mono">
										<Coins className="w-3 h-3 text-amber-400 inline" />${stats.totalCost.toFixed(4)}
									</span>
								)}
							</p>
						</div>

						{/* Actions: absolute top-right on mobile/tablet, static on desktop */}
						<div className="absolute top-0 right-0 flex items-center gap-2 flex-shrink-0 lg:static">
							{!selectedCol.is_read_only && (
								<>
									<Button
										size="sm"
										variant="primary"
										icon={<Upload className="w-3.5 h-3.5" />}
										onClick={() => inlineFileInputRef.current?.click()}
										disabled={uploading}
										className="border-orange-500 bg-orange-500 text-white hover:border-orange-600 hover:bg-orange-600"
									>
										{uploading ? "Uploading\u2026" : "Upload"}
									</Button>
									<Button
										size="sm"
										variant="ghost"
										data-tutorial="collection-edit-upload-btn"
										icon={<Settings className="w-3.5 h-3.5" />}
										onClick={() => openEditModal(selectedCol)}
										title="Edit collection settings, chunking config & visibility"
										className="text-slate-700 hover:bg-white hover:text-slate-900"
									>
										Settings
									</Button>
								</>
							)}
						</div>
					</div>

					{/* Inline upload drop zone */}
					{!selectedCol.is_read_only && (
						<>
							<input
								ref={inlineFileInputRef}
								type="file"
								multiple
								accept=".pdf,.docx,.txt,.csv,.xlsx,.md"
								onChange={(e) => {
									if (e.target.files && e.target.files.length > 0) {
										handleFileUpload(e.target.files);
										e.target.value = "";
									}
								}}
								style={{ display: "none" }}
							/>
							<div
								className={`flex cursor-pointer items-center justify-center gap-3 rounded-xl border-2 border-dashed px-4 py-3 transition-all duration-200 ${
									isDraggingInline
										? "border-orange-500 bg-white"
										: "border-orange-200 bg-white hover:border-orange-400 hover:bg-white"
								} ${uploading ? "opacity-50 pointer-events-none" : ""}`}
								onDrop={async (e) => {
									e.preventDefault();
									setIsDraggingInline(false);
									if (e.dataTransfer.files.length > 0) {
										await handleFileUpload(e.dataTransfer.files);
									}
								}}
								onDragOver={(e) => {
									e.preventDefault();
									setIsDraggingInline(true);
								}}
								onDragLeave={() => setIsDraggingInline(false)}
								onClick={() => inlineFileInputRef.current?.click()}
							>
								<Upload className={`h-4 w-4 flex-shrink-0 ${isDraggingInline ? "text-orange-600" : "text-slate-500"}`} />
								<span className={`text-sm ${isDraggingInline ? "text-orange-700" : "text-slate-600"}`}>
									{uploading
										? "Processing files\u2026"
										: isDraggingInline
											? "Drop files to upload"
											: "Drop files here or click to upload"}
								</span>
								<span className="hidden text-xs text-slate-400 sm:inline">
									PDF, DOCX, TXT, CSV, XLSX, MD
								</span>
							</div>
						</>
					)}

					{/* Search + actions */}
					<div className="flex items-center gap-3">
						<div className="flex-1">
							<FormInput
								value={searchTerm}
								onChange={(e) => setSearchTerm(e.target.value)}
								placeholder={`Search in ${selectedCol.name}\u2026`}
								icon={<Search className="w-4 h-4" />}
							/>
						</div>
						<Button
							variant="secondary"
							className="border-orange-200 bg-white text-slate-800 hover:border-orange-400 hover:bg-white hover:text-slate-900"
							onClick={() =>
								setSearchModal({
									isOpen: true,
									documentId: selectedDocument?.id,
									documentName: selectedDocument?.name,
									collectionId: selectedCollection ?? undefined,
								})
							}
							icon={<Search className="w-4 h-4" />}
						>
							Test Retrieval
						</Button>
						{stats.failedCount > 0 && (
							<Button
								variant="ghost"
								onClick={handleClearFailedDocuments}
								className="text-red-600 hover:bg-red-50 hover:text-red-700"
							>
								Clear {stats.failedCount} Failed
							</Button>
						)}
					</div>

					{/* Document table */}
					<div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-orange-200/70 bg-white">
						<div className="flex-1 min-h-0 overflow-y-auto">
							<DocumentTable
								documents={filteredDocuments}
								selectedDocument={selectedDocument}
								onSelectDocument={setSelectedDocument}
								onDeleteDocument={handleDeleteDocument}
								loading={loading}
								isReadOnly={selectedCol.is_read_only}
								emptyMessage={`No documents in "${selectedCol.name}" yet. Click Edit & Upload to add some.`}
							/>
						</div>
					</div>
				</div>
			) : null}

			{/* Document Details Panel */}
			{selectedDocument && (
				<DocumentDetailsPanel
					document={selectedDocument}
					isReadOnly={isDocumentReadOnly(selectedDocument.id)}
					onClose={() => setSelectedDocument(null)}
					onDelete={() => handleDeleteDocument(selectedDocument.id)}
					onReprocess={() => {
						if (isDocumentReadOnly(selectedDocument.id)) {
							showError(
								"Cannot Reprocess",
								"You cannot reprocess documents in a collection you don't own.",
							);
							return;
						}
						setReprocessModal({
							isOpen: true,
							documentId: selectedDocument.id,
							documentName: selectedDocument.name,
							chunkCount: selectedDocument.chunk_count,
						});
					}}
					onSearchWithin={() =>
						setSearchModal({
							isOpen: true,
							documentId: selectedDocument.id,
							documentName: selectedDocument.name,
							collectionId: selectedDocument.collection_id,
						})
					}
				/>
			)}

			{/* Edit Collection Floating Modal */}
			{editingCol && (
				<div
					className="fixed inset-0 z-[120] flex items-center justify-center bg-slate-900/45 p-4"
					onClick={(e) => {
						if (e.target === e.currentTarget) closeEditModal();
					}}
				>
					<div className="relative flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
						<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/50" />
						{/* Modal Header */}
						<div className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
							<div className="flex items-center gap-2 min-w-0">
								<Edit2 className="h-4 w-4 flex-shrink-0 text-orange-600" />
								<h3 className="flex-shrink-0 text-sm font-semibold text-slate-900">
									Edit Collection
								</h3>
								<span className="truncate text-xs text-slate-500">
									{"\u2014"} {editingCol.name}
								</span>
							</div>
							<button
								type="button"
								onClick={closeEditModal}
								className="ml-3 flex-shrink-0 rounded-lg border border-transparent p-1.5 text-slate-500 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
								data-tutorial="collection-edit-close-btn"
							>
								<X className="w-4 h-4" />
							</button>
						</div>

						{/* Modal Body */}
						<div className="flex-1 space-y-5 overflow-y-auto p-6">
							<FormInput
								label="Name"
								value={editCollectionName}
								onChange={(e) =>
									setEditCollectionName(e.target.value)
								}
								placeholder="Collection name"
							/>
							<FormTextarea
								label="Description"
								rows={2}
								value={editCollectionDescription}
								onChange={(e) =>
									setEditCollectionDescription(e.target.value)
								}
								placeholder="Optional description"
							/>

							{/* Visibility toggle */}
							<div className="rounded-xl border border-slate-200 bg-white p-3">
								<div className="flex items-center justify-between">
									<div className="flex items-center gap-2">
										{isEditGlobalVisibility ? (
											<Globe className="h-4 w-4 text-orange-600" />
										) : (
											<Lock className="h-4 w-4 text-slate-500" />
										)}
										<div>
											<p className="text-sm font-medium text-slate-900">
												{isEditGlobalVisibility
													? "Shared"
													: "Private"}
											</p>
											<p className="text-xs text-slate-500">
												{isEditGlobalVisibility
													? "Visible to selected groups or everyone"
													: "Only visible to you"}
											</p>
										</div>
									</div>
									<button
										type="button"
										onClick={() => {
											setIsEditGlobalVisibility(
												!isEditGlobalVisibility,
											);
											if (isEditGlobalVisibility)
												setEditVisibilityGroups([]);
										}}
										className={`relative h-6 w-12 rounded-full transition-colors ${isEditGlobalVisibility ? "bg-orange-500" : "bg-slate-200"}`}
									>
										<span
											className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${isEditGlobalVisibility ? "left-7" : "left-1"}`}
										/>
									</button>
								</div>
								{isEditGlobalVisibility && (
									<div className="mt-3 border-t border-slate-200 pt-3">
										<GroupSelector
											selectedGroups={editVisibilityGroups}
											onChange={setEditVisibilityGroups}
											placeholder="Select groups (optional, defaults to everyone)"
										/>
									</div>
								)}
							</div>

							{/* Upload section divider */}
							<div
								data-tutorial="collection-upload-zone"
								className="flex items-center gap-3 pt-1"
							>
								<div className="h-px flex-1 bg-slate-200" />
								<span className="text-xs font-medium capitalize text-orange-700">
									Upload Documents
								</span>
								<div className="h-px flex-1 bg-slate-200" />
							</div>

							<DocumentUploadZone
								collectionName={editingCol.name}
								onUpload={handleFileUpload}
								uploading={uploading}
								uploadConfig={uploadConfig}
								onConfigChange={setUploadConfig}
								failedCount={stats.failedCount}
								onClearFailed={handleClearFailedDocuments}
								hasCollection={true}
								hasEmbeddingModels={hasEmbeddingModels}
								onCreateCollection={() => {}}
								onSelectCollection={() => {}}
								hasCollections={true}
								isReadOnly={false}
								creatorName={editingCol.created_by_name}
							/>

							<EmbeddingModelSelector
								models={embeddingModels}
								selectedModel={selectedEmbeddingModel}
								onModelChange={handleEmbeddingModelChange}
								loading={loadingEmbeddings}
								onNavigateToSettings={() =>
									router.push("/settings")
								}
								compact
								locked={false}
							/>
						</div>

						{/* Modal Footer */}
						<div className="flex flex-shrink-0 justify-end gap-2 border-t border-slate-200 bg-white px-6 py-5">
							<Button
								variant="ghost"
								size="sm"
								onClick={closeEditModal}
								className="text-slate-700 hover:bg-slate-50 hover:text-slate-900"
							>
								Cancel
							</Button>
							<Button
								size="sm"
								icon={<Save className="w-3.5 h-3.5" />}
								disabled={!editCollectionName.trim()}
								className="border-orange-500 bg-orange-500 text-white hover:border-orange-600 hover:bg-orange-600"
								onClick={async () => {
									const col = editingCol;
									const nameChanged =
										editCollectionName !== col.name;
									const descChanged =
										editCollectionDescription !==
										(col.description || "");
									const embeddingChanged =
										!col.embedding_deployment_id &&
										Boolean(selectedEmbeddingModel);
									if (
										nameChanged ||
										descChanged ||
										embeddingChanged
									) {
										try {
											await api.updateCollection(col.id, {
												...(nameChanged
													? {
															name: editCollectionName,
														}
													: {}),
												...(descChanged
													? {
															description:
																editCollectionDescription,
														}
													: {}),
												...(embeddingChanged
													? {
															embedding_deployment_id:
																selectedEmbeddingModel,
														}
													: {}),
											});
										} catch (error: any) {
											if (
												error?.message?.includes("403")
											) {
												showError(
													"Permission Denied",
													"You don't have permission to edit this collection.",
												);
											} else {
												showError(
													"Update Failed",
													error?.message ||
														"Failed to update collection.",
												);
											}
											return;
										}
									}

									const newGroups = isEditGlobalVisibility
										? editVisibilityGroups.length > 0
											? editVisibilityGroups
											: ["__all__"]
										: [];
									const oldGroups =
										col.visible_to_groups ?? [];
									const visibilityChanged =
										JSON.stringify(newGroups.sort()) !==
										JSON.stringify([...oldGroups].sort());
									if (visibilityChanged) {
										await handleUpdateVisibility(
											col.id,
											newGroups,
										);
									} else if (
										nameChanged ||
										descChanged ||
										embeddingChanged
									) {
										await loadCollections(activeFilterTab);
										showSuccess(
											"Collection Updated",
											"Collection has been updated.",
										);
									}

									closeEditModal();
								}}
							>
								Save
							</Button>
						</div>
					</div>
				</div>
			)}

			{/* Embedding model change confirmation dialog */}
			{embeddingChangeConfirm && (
				<div className="fixed inset-0 z-[130] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
					<div className="w-full max-w-md space-y-4 rounded-xl border border-orange-300 bg-white p-6 text-slate-900 shadow-2xl">
						<h3 className="text-base font-semibold text-slate-900">
							Change Embedding Model?
						</h3>
						<p className="text-sm text-slate-600">
							This collection has{" "}
							<span className="font-medium text-slate-900">
								{embeddingChangeConfirm.documentCount} document
								{embeddingChangeConfirm.documentCount !== 1
									? "s"
									: ""}
							</span>{" "}
							embedded with a different model. Changing the model
							will{" "}
							<span className="text-amber-400 font-medium">
								reprocess all documents
							</span>{" "}
							in this collection using the new embedding model.
							This may take a while.
						</p>
						<div className="flex justify-end gap-2 pt-2">
							<Button
								variant="ghost"
								size="sm"
								onClick={() => setEmbeddingChangeConfirm(null)}
								disabled={reprocessingCollection}
							>
								Cancel
							</Button>
							<Button
								size="sm"
								onClick={handleConfirmEmbeddingChange}
								loading={reprocessingCollection}
							>
								{reprocessingCollection
									? "Reprocessing\u2026"
									: "Change & Reprocess"}
							</Button>
						</div>
					</div>
				</div>
			)}

			{/* Modals */}
			<DocumentSearchModal
				isOpen={searchModal.isOpen}
				onClose={() =>
					setSearchModal({
						isOpen: false,
						documentId: undefined,
						documentName: undefined,
						collectionId: undefined,
					})
				}
				onSearch={handleSearch}
				documentName={searchModal.documentName}
			/>

			<ReprocessModal
				isOpen={reprocessModal.isOpen}
				onClose={() =>
					setReprocessModal({
						isOpen: false,
						documentId: "",
						documentName: "",
						chunkCount: 0,
					})
				}
				onReprocess={handleReprocess}
				documentName={reprocessModal.documentName}
				currentChunkCount={reprocessModal.chunkCount}
			/>

			<ConfirmDialog
				isOpen={deleteDocDialog.isOpen}
				title="Delete Document"
				message={`Are you sure you want to delete "${documents.find((d) => d.id === deleteDocDialog.docId)?.name || "this document"}"? This action cannot be undone.`}
				confirmText="Delete Document"
				cancelText="Cancel"
				type="danger"
				onConfirm={confirmDeleteDocument}
				onCancel={() => setDeleteDocDialog({ isOpen: false, docId: "" })}
			/>

			{/* Create Collection Modal */}
			{isCreatingCollection && (
				<div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
					<div
						data-tutorial="create-collection-modal"
						className="mx-4 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-orange-300 bg-white p-6 text-slate-900 shadow-2xl"
					>
						<h3 className="mb-6 text-lg font-semibold text-slate-900">
							Add Collection
						</h3>

						<div className="space-y-4">
							<FormInput
								label="Collection Name"
								data-tutorial="collection-name-input"
								value={newCollection.name}
								onChange={(e) =>
									setNewCollection({
										...newCollection,
										name: e.target.value,
									})
								}
								placeholder="Enter collection name..."
								required
							/>

							<FormTextarea
								label="Description"
								data-tutorial="collection-description-input"
								value={newCollection.description}
								onChange={(e) =>
									setNewCollection({
										...newCollection,
										description: e.target.value,
									})
								}
								placeholder="Optional description..."
								rows={3}
							/>

							{/* Visibility Settings */}
							<div className="space-y-3">
								<label
									className="block text-sm font-medium"
									style={{
										color: "#334155",
									}}
								>
									Visibility
								</label>
								<div className="flex items-center gap-3">
									<button
										type="button"
										onClick={() =>
											setIsGlobalVisibility(false)
										}
										className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all"
										style={{
											background: !isGlobalVisibility
												? "#f97316"
												: "#ffffff",
											border: !isGlobalVisibility
												? "1px solid var(--nav-link-active)"
												: "1px solid var(--color-border)",
											color: !isGlobalVisibility
												? "#ffffff"
												: "#0f172a",
										}}
									>
										<Lock className="w-4 h-4" />
										Private
									</button>
									<button
										type="button"
										onClick={() =>
											setIsGlobalVisibility(true)
										}
										className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all"
										style={{
											background: isGlobalVisibility
												? "#f97316"
												: "#ffffff",
											border: isGlobalVisibility
												? "1px solid var(--nav-link-active)"
												: "1px solid var(--color-border)",
											color: isGlobalVisibility
												? "#ffffff"
												: "#0f172a",
										}}
									>
										<Globe className="w-4 h-4" />
										Shared
									</button>
								</div>

								{isGlobalVisibility && (
									<div className="mt-2">
										<GroupSelector
											selectedGroups={
												selectedVisibilityGroups
											}
											onChange={
												setSelectedVisibilityGroups
											}
										/>
									</div>
								)}
							</div>
						</div>

						<div className="flex justify-end gap-3 mt-6">
							<Button
								variant="ghost"
								onClick={() => {
									setIsCreatingCollection(false);
									setNewCollection({
										name: "",
										description: "",
									});
									setIsGlobalVisibility(false);
									setSelectedVisibilityGroups([]);
								}}
							>
								Cancel
							</Button>
							<Button
								data-tutorial="create-collection-submit"
								onClick={handleCreateCollection}
								disabled={!newCollection.name.trim()}
								icon={<Plus className="w-4 h-4" />}
							>
								Create Collection
							</Button>
						</div>
					</div>
				</div>
			)}

			<ConfirmDialog
				isOpen={deleteCollDialog.isOpen}
				title="Delete Collection"
				message={`Are you sure you want to delete the collection "${collections.find((c) => c.id === deleteCollDialog.collId)?.name || "this collection"}" and all its documents? This action cannot be undone.`}
				confirmText="Delete Collection"
				cancelText="Cancel"
				type="danger"
				onConfirm={confirmDeleteCollection}
				onCancel={() =>
					setDeleteCollDialog({ isOpen: false, collId: "" })
				}
			/>

			<ConfirmDialog
				isOpen={visibilityConfirmDialog.isOpen}
				title="Change Collection Visibility"
				message="Make this collection visible to all users? Everyone will be able to view and use this collection in their workflows."
				confirmText="Make Global"
				cancelText="Cancel"
				type="warning"
				onConfirm={visibilityConfirmDialog.action}
				onCancel={() =>
					setVisibilityConfirmDialog({
						isOpen: false,
						action: () => {},
					})
				}
			/>
		</div>
	);
}
