"use client";

import { FileSearch, Save, Search, ShieldCheck, Sliders, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import ConfigSidebar from "./ConfigSidebar";
import AdvancedSettingsSection from "./sections/AdvancedSettingsSection";
import DocumentsSection from "./sections/DocumentsSection";
import type { Collection, DocumentItem } from "./sections/DocumentsSection";
import SearchConfigSection from "./sections/SearchConfigSection";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";

interface DocumentSearchConfig {
	document_collections?: string[];
	document_ids?: string[];
	search_k?: number;
	search_type?: string;
	similarity_threshold?: number;
	distance_strategy?: string;
	include_metadata?: boolean;
	citation_format?: string;
	hybrid_search_enabled?: boolean;
	search_mode?: string;
	keyword_weight?: number;
	rrf_k?: number;
	full_text_config?: string;
	min_keyword_relevance?: number;
	use_reranking?: boolean;
	rerank_top_k?: number;
	parent_agent_id?: string;
	prompt_template?: string;
	include_confidence_scores?: boolean;
	max_context_tokens?: number;
	return_full_document?: boolean;
}

interface DocumentSearchNodeData {
	id: string;
	name: string;
	document_search_config?: DocumentSearchConfig;
}

interface DocumentSearchPropertiesPanelProps {
	node: {
		id: string;
		data: DocumentSearchNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

type DocumentSearchTabId = "documents" | "search" | "advanced" | "guardrails";

export default function DocumentSearchPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: DocumentSearchPropertiesPanelProps) {
	const config = node.data.document_search_config || {};

	// Document search configuration state
	const [selectedCollections, setSelectedCollections] = useState<string[]>(
		config.document_collections || [],
	);
	const [selectedDocuments, setSelectedDocuments] = useState<string[]>(
		config.document_ids || [],
	);
	const [documentSelectionMode, setDocumentSelectionMode] = useState<
		"collections" | "documents"
	>(
		config.document_ids && config.document_ids.length > 0
			? "documents"
			: "collections",
	);
	const [searchK, setSearchK] = useState(
		typeof config.search_k === "number" ? config.search_k : 3,
	);
	const [searchMode, setSearchMode] = useState(config.search_mode || "hybrid");
	const [citationFormat, setCitationFormat] = useState(
		config.citation_format || "structured",
	);
	const [similarityThreshold, setSimilarityThreshold] = useState(
		config.similarity_threshold || 0.55,
	);
	const [hybridSearchEnabled, setHybridSearchEnabled] = useState(
		config.hybrid_search_enabled !== false,
	);
	const [keywordWeight, setKeywordWeight] = useState(
		config.keyword_weight || 0.5,
	);
	const [returnFullDocument] = useState(
		config.return_full_document || false,
	);

	// Advanced settings
	const [rrfK, setRrfK] = useState(config.rrf_k || 60);
	const [includeMetadata, setIncludeMetadata] = useState(
		config.include_metadata !== false,
	);
	const [includeConfidenceScores, setIncludeConfidenceScores] = useState(
		config.include_confidence_scores !== false,
	);
	const [maxContextTokens, setMaxContextTokens] = useState(
		config.max_context_tokens || 2000,
	);

	const [collections, setCollections] = useState<Collection[]>([]);
	const [documents, setDocuments] = useState<DocumentItem[]>([]);
	const [loadingCollections, setLoadingCollections] = useState(false);
	const [loadingDocuments, setLoadingDocuments] = useState(false);

	// Tab navigation
	const [activeTab, setActiveTab] = useState<DocumentSearchTabId>("documents");

	// Track initial values for unsaved changes detection
	const initialValues = useRef({
		selectedCollections: config.document_collections || [],
		selectedDocuments: config.document_ids || [],
		documentSelectionMode:
			config.document_ids && config.document_ids.length > 0
				? "documents"
				: "collections",
		searchK: typeof config.search_k === "number" ? config.search_k : 3,
		searchMode: config.search_mode || "hybrid",
		citationFormat: config.citation_format || "structured",
		similarityThreshold: config.similarity_threshold || 0.55,
		hybridSearchEnabled: config.hybrid_search_enabled !== false,
		keywordWeight: config.keyword_weight || 0.5,
		rrfK: config.rrf_k || 60,
		includeMetadata: config.include_metadata !== false,
		includeConfidenceScores: config.include_confidence_scores !== false,
		maxContextTokens: config.max_context_tokens || 2000,
	});

	// Unsaved changes detection
	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return (
			JSON.stringify(selectedCollections) !==
				JSON.stringify(init.selectedCollections) ||
			JSON.stringify(selectedDocuments) !==
				JSON.stringify(init.selectedDocuments) ||
			documentSelectionMode !== init.documentSelectionMode ||
			searchK !== init.searchK ||
			searchMode !== init.searchMode ||
			citationFormat !== init.citationFormat ||
			similarityThreshold !== init.similarityThreshold ||
			hybridSearchEnabled !== init.hybridSearchEnabled ||
			keywordWeight !== init.keywordWeight ||
			rrfK !== init.rrfK ||
			includeMetadata !== init.includeMetadata ||
			includeConfidenceScores !== init.includeConfidenceScores ||
			maxContextTokens !== init.maxContextTokens
		);
	}, [
		selectedCollections,
		selectedDocuments,
		documentSelectionMode,
		searchK,
		searchMode,
		citationFormat,
		similarityThreshold,
		hybridSearchEnabled,
		keywordWeight,
		rrfK,
		includeMetadata,
		includeConfidenceScores,
		maxContextTokens,
	]);

	// Load collections on mount
	useEffect(() => {
		loadCollections().catch((error) => {
			console.error("Failed to load collections:", error);
		});
	}, []);

	// Load documents when selection mode changes or collections change
	useEffect(() => {
		if (documentSelectionMode === "documents") {
			loadDocuments().catch((error) => {
				console.error("Failed to load documents:", error);
			});
		}
	}, [documentSelectionMode, selectedCollections]);

	const loadCollections = async () => {
		setLoadingCollections(true);
		try {
			const collectionsWithDocs = await api.getCollectionsWithDocuments();
			if (collectionsWithDocs) {
				const loadedCollections = collectionsWithDocs.map((col) => ({
					id: col.id,
					name: col.name,
					documentCount: col.document_count,
					isReadOnly: col.is_read_only,
					createdByName: col.created_by_name,
					createdByEmail: col.created_by_email,
				}));
				setCollections(loadedCollections);
				// Prune selected collections to only include accessible ones
				const accessibleIds = new Set(loadedCollections.map((c) => c.id));
				setSelectedCollections((prev) =>
					prev.filter((id) => accessibleIds.has(id)),
				);
			}
		} catch (error) {
			// Silent fail
		} finally {
			setLoadingCollections(false);
		}
	};

	const loadDocuments = async () => {
		if (selectedCollections.length === 0) {
			setDocuments([]);
			return;
		}

		setLoadingDocuments(true);
		try {
			const allDocuments: DocumentItem[] = [];

			for (const collectionId of selectedCollections) {
				const docs = await api.getDocuments(collectionId);
				if (docs) {
					allDocuments.push(
						...docs.map((doc) => ({
							id: doc.id,
							name: doc.name,
							collection_id: collectionId,
							size: doc.size,
							created_at: doc.upload_date || new Date().toISOString(),
						})),
					);
				}
			}

			setDocuments(allDocuments);
		} catch (error) {
			// Silent fail
		} finally {
			setLoadingDocuments(false);
		}
	};

	const handleSave = useCallback(() => {
		const updatedConfig: DocumentSearchConfig = {
			...config,
			document_collections:
				documentSelectionMode === "collections" ? selectedCollections : [],
			document_ids:
				documentSelectionMode === "documents" ? selectedDocuments : [],
			search_k: searchK,
			search_type: "similarity",
			similarity_threshold: similarityThreshold,
			include_metadata: includeMetadata,
			citation_format: citationFormat,
			hybrid_search_enabled: hybridSearchEnabled,
			search_mode: searchMode,
			keyword_weight: keywordWeight,
			rrf_k: rrfK,
			full_text_config: "english",
			include_confidence_scores: includeConfidenceScores,
			max_context_tokens: maxContextTokens,
			prompt_template:
				citationFormat === "structured" ? "structured" : "default",
			return_full_document: returnFullDocument,
		};

		const updateData: any = {
			...node.data,
			document_search_config: updatedConfig,
		};

		if (node.position) {
			updateData.position = node.position;
		}

		onUpdateNode(node.id, updateData);
		onClose();
	}, [
		config,
		documentSelectionMode,
		selectedCollections,
		selectedDocuments,
		searchK,
		similarityThreshold,
		includeMetadata,
		citationFormat,
		hybridSearchEnabled,
		searchMode,
		keywordWeight,
		rrfK,
		includeConfidenceScores,
		maxContextTokens,
		returnFullDocument,
		node,
		onUpdateNode,
		onClose,
	]);

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

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleDeleteAndClose = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [onDeleteNode, node.id, onClose]);

	// Responsive sidebar collapse
	const contentRef = useRef<HTMLDivElement>(null);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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

	// Sidebar tab configuration
	const panelTabs = useMemo(
		() => [
			{
				id: "documents" as const,
				label: "Documents",
				description: "Select sources",
				icon: <FileSearch className="h-4 w-4" />,
			},
			{
				id: "search" as const,
				label: "Search",
				description: "Search config",
				icon: <Search className="h-4 w-4" />,
			},
			{
				id: "advanced" as const,
				label: "Advanced",
				description: "Relevance & output",
				icon: <Sliders className="h-4 w-4" />,
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

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/40 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleStopPropagation}
			>
				<div className="relative flex max-h-[80vh] min-h-[320px] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
					<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />

					{/* Header — Workflow Management style */}
					<div className="flex-none border-b border-slate-200 bg-white">
						<div className="flex items-center justify-between px-6 pb-4 pt-5">
							<div className="flex items-center gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
									<FileSearch className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<h2 className="text-lg font-semibold tracking-tight text-slate-900">
									Document Search Configuration
								</h2>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
								aria-label="Close"
							>
								<X className="h-4 w-4" />
							</button>
						</div>
					</div>

					<div
						ref={contentRef}
						className="flex min-h-0 flex-1 overflow-hidden"
					>
						<ConfigSidebar
							items={panelTabs}
							activeItem={activeTab}
							onChange={(id) =>
								setActiveTab(id as DocumentSearchTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div className="flex-1 overflow-y-auto bg-white px-6 py-4">
							{activeTab === "documents" && (
								<DocumentsSection
									documentSelectionMode={documentSelectionMode}
									onSelectionModeChange={setDocumentSelectionMode}
									selectedCollections={selectedCollections}
									onSelectedCollectionsChange={setSelectedCollections}
									selectedDocuments={selectedDocuments}
									onSelectedDocumentsChange={setSelectedDocuments}
									collections={collections}
									documents={documents}
									loadingCollections={loadingCollections}
									loadingDocuments={loadingDocuments}
								/>
							)}

							{activeTab === "search" && (
								<SearchConfigSection
									searchK={searchK}
									onSearchKChange={setSearchK}
									hybridSearchEnabled={hybridSearchEnabled}
									onHybridSearchEnabledChange={setHybridSearchEnabled}
									searchMode={searchMode}
									onSearchModeChange={setSearchMode}
									keywordWeight={keywordWeight}
									onKeywordWeightChange={setKeywordWeight}
									citationFormat={citationFormat}
									onCitationFormatChange={setCitationFormat}
								/>
							)}

							{activeTab === "advanced" && (
								<AdvancedSettingsSection
									similarityThreshold={similarityThreshold}
									onSimilarityThresholdChange={setSimilarityThreshold}
									hybridSearchEnabled={hybridSearchEnabled}
									searchMode={searchMode}
									rrfK={rrfK}
									onRrfKChange={setRrfK}
									includeMetadata={includeMetadata}
									onIncludeMetadataChange={setIncludeMetadata}
									includeConfidenceScores={includeConfidenceScores}
									onIncludeConfidenceScoresChange={
										setIncludeConfidenceScores
									}
									maxContextTokens={maxContextTokens}
									onMaxContextTokensChange={setMaxContextTokens}
								/>
							)}

							{activeTab === "guardrails" && (
								<ToolGuardrailsSection
									toolNodeId={node.id}
									guardrailsPanelTheme="light"
								/>
							)}
						</div>
					</div>

					<div className="flex-none border-t border-slate-200 bg-white px-6 py-3">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<button
								type="button"
								onClick={handleDeleteAndClose}
								className="flex items-center gap-1.5 rounded-[4px] border border-red-200 bg-white px-3 py-2 text-xs font-medium text-red-800 transition-colors hover:border-red-300 hover:bg-red-50"
							>
								<Trash2 className="h-3.5 w-3.5" />
								Delete Node
							</button>

							<div className="flex items-center gap-3 sm:ml-auto">
								{hasUnsavedChanges && (
									<span className="flex items-center gap-1.5 text-[11px] text-slate-600">
										<span className="h-1.5 w-1.5 animate-smoothPulse rounded-full bg-orange-500" />
										Unsaved
									</span>
								)}
								<span className="hidden text-[11px] text-slate-500 sm:inline">
									{"\u2318"}S to save
								</span>
								<button
									type="button"
									onClick={onClose}
									className="rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleSave}
									className="inline-flex items-center gap-1.5 rounded-[4px] border border-orange-500 bg-orange-500 px-5 py-2 text-xs font-semibold text-white transition-colors hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
								>
									<Save className="h-3.5 w-3.5" />
									Save Changes
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
