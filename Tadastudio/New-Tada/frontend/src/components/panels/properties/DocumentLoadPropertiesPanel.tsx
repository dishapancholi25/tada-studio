"use client";

import { Download, Save, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import DocumentsSection from "./sections/DocumentsSection";
import type { Collection, DocumentItem } from "./sections/DocumentsSection";

interface DocumentLoadConfig {
	collection_id?: string | null;
	document_ids?: string[];
	max_document_size_tokens?: number;
	truncation_strategy?: string;
	output_mode?: string;
	chunk_output_mode?: string;
	chunk_token_limit?: number;
	output_format?: string;
	include_metadata?: boolean;
}

interface DocumentLoadNodeData {
	id: string;
	name: string;
	document_load_config?: DocumentLoadConfig;
}

interface DocumentLoadPropertiesPanelProps {
	node: {
		id: string;
		data: DocumentLoadNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

export default function DocumentLoadPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: DocumentLoadPropertiesPanelProps) {
	const config = node.data.document_load_config || {};

	const [selectedCollections, setSelectedCollections] = useState<string[]>(
		config.collection_id ? [config.collection_id] : [],
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
	const [outputMode, setOutputMode] = useState(config.output_mode || "batch");
	const [chunkOutputMode, setChunkOutputMode] = useState(
		config.chunk_output_mode || "full",
	);
	const [chunkTokenLimit, setChunkTokenLimit] = useState(
		config.chunk_token_limit || 50000,
	);
	const [maxTokens, setMaxTokens] = useState(
		config.max_document_size_tokens || 100000,
	);
	const [truncationStrategy, setTruncationStrategy] = useState(
		config.truncation_strategy || "end",
	);

	const [collections, setCollections] = useState<Collection[]>([]);
	const [documents, setDocuments] = useState<DocumentItem[]>([]);
	const [loadingCollections, setLoadingCollections] = useState(false);
	const [loadingDocuments, setLoadingDocuments] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	const initialValues = useRef({
		selectedCollections: config.collection_id ? [config.collection_id] : [],
		selectedDocuments: config.document_ids || [],
		documentSelectionMode:
			config.document_ids && config.document_ids.length > 0
				? "documents"
				: ("collections" as string),
		outputMode: config.output_mode || "batch",
		chunkOutputMode: config.chunk_output_mode || "full",
		chunkTokenLimit: config.chunk_token_limit || 50000,
		maxTokens: config.max_document_size_tokens || 100000,
		truncationStrategy: config.truncation_strategy || "end",
	});

	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return (
			JSON.stringify(selectedCollections) !==
				JSON.stringify(init.selectedCollections) ||
			JSON.stringify(selectedDocuments) !==
				JSON.stringify(init.selectedDocuments) ||
			documentSelectionMode !== init.documentSelectionMode ||
			outputMode !== init.outputMode ||
			chunkOutputMode !== init.chunkOutputMode ||
			chunkTokenLimit !== init.chunkTokenLimit ||
			maxTokens !== init.maxTokens ||
			truncationStrategy !== init.truncationStrategy
		);
	}, [selectedCollections, selectedDocuments, documentSelectionMode, outputMode, chunkOutputMode, chunkTokenLimit, maxTokens, truncationStrategy]);

	useEffect(() => {
		loadCollections().catch(console.error);
	}, []);

	useEffect(() => {
		if (documentSelectionMode === "documents") {
			loadDocumentsList().catch(console.error);
		}
	}, [documentSelectionMode, selectedCollections]);

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

	const loadDocumentsList = async () => {
		setLoadingDocuments(true);
		try {
			const response = await api.getDocuments();
			if (response && Array.isArray(response)) {
				setDocuments(
					response.map((doc: any) => ({
						id: doc.id,
						name: doc.name,
						collection_id: doc.collection_id,
						size: doc.file_size,
						created_at: doc.uploaded_at,
					})),
				);
			}
		} catch (error) {
			console.error("Failed to load documents:", error);
		} finally {
			setLoadingDocuments(false);
		}
	};

	const handleSave = useCallback(() => {
		onUpdateNode(node.id, {
			document_load_config: {
				...config,
				collection_id:
					documentSelectionMode === "collections" && selectedCollections.length > 0
						? selectedCollections[0]
						: null,
				document_ids:
					documentSelectionMode === "documents" ? selectedDocuments : [],
				max_document_size_tokens: maxTokens,
				truncation_strategy: truncationStrategy,
				output_mode: outputMode,
				chunk_output_mode: chunkOutputMode,
				chunk_token_limit: chunkTokenLimit,
			},
		});
		initialValues.current = {
			selectedCollections: [...selectedCollections],
			selectedDocuments: [...selectedDocuments],
			documentSelectionMode,
			outputMode,
			chunkOutputMode,
			chunkTokenLimit,
			maxTokens,
			truncationStrategy,
		};
		onClose();
	}, [node.id, config, selectedCollections, selectedDocuments, documentSelectionMode, outputMode, chunkOutputMode, chunkTokenLimit, maxTokens, truncationStrategy, onUpdateNode, onClose]);

	const handleDelete = useCallback(() => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [node.id, onDeleteNode, onClose]);

	const fieldClass =
		"w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40";

	return (
		<div
			className="fixed inset-0 z-[100] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-8 pt-[5vh] backdrop-blur-sm"
			onClick={onClose}
		>
			<div
				className="max-h-[80vh] min-h-[320px] w-[90vw] max-w-2xl flex flex-col overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
				onClick={(e) => e.stopPropagation()}
			>
				<div className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6 py-5">
					<div className="flex items-start gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Download className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
								Tool configuration
							</p>
							<h2 className="text-lg font-semibold text-gray-900">Document Load</h2>
							<p className="mt-0.5 text-sm text-gray-600">
								Load documents from collections into the workflow
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<div className="flex-1 space-y-6 overflow-y-auto bg-slate-50 px-6 py-4">
					<div>
						<h3 className="mb-2 text-sm font-medium text-gray-900">Document Source</h3>
						<p className="mb-3 text-xs text-gray-600">
							Select a collection to load all documents from, or pick specific documents.
						</p>
						<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
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
						</div>
					</div>

					<div className="space-y-4 border-t border-gray-200 pt-4">
						<h3 className="text-sm font-medium text-gray-900">Output Settings</h3>

						<div className="grid grid-cols-2 gap-4">
							<div>
								<label className="mb-1.5 block text-xs font-medium text-gray-800">
									Output Mode
								</label>
								<select
									value={outputMode}
									onChange={(e) => setOutputMode(e.target.value)}
									className={fieldClass}
								>
									<option value="batch">Batch (for For Each)</option>
									<option value="single">Single Document</option>
								</select>
							</div>

							<div>
								<label className="mb-1.5 block text-xs font-medium text-gray-800">
									Chunk Mode
								</label>
								<select
									value={chunkOutputMode}
									onChange={(e) => setChunkOutputMode(e.target.value)}
									className={fieldClass}
								>
									<option value="full">Full Document</option>
									<option value="by_page">Split by Page</option>
									<option value="by_token_limit">Split by Token Limit</option>
								</select>
							</div>
						</div>

						{chunkOutputMode === "by_token_limit" && (
							<div>
								<label className="mb-1.5 block text-xs font-medium text-gray-800">
									Chunk Token Limit
								</label>
								<input
									type="number"
									value={chunkTokenLimit}
									onChange={(e) =>
										setChunkTokenLimit(Number.parseInt(e.target.value) || 50000)
									}
									className={fieldClass}
								/>
							</div>
						)}

						<div className="grid grid-cols-2 gap-4">
							<div>
								<label className="mb-1.5 block text-xs font-medium text-gray-800">
									Max Size (tokens)
								</label>
								<input
									type="number"
									value={maxTokens}
									onChange={(e) =>
										setMaxTokens(Number.parseInt(e.target.value) || 100000)
									}
									className={fieldClass}
								/>
							</div>

							<div>
								<label className="mb-1.5 block text-xs font-medium text-gray-800">
									Truncation
								</label>
								<select
									value={truncationStrategy}
									onChange={(e) => setTruncationStrategy(e.target.value)}
									className={fieldClass}
								>
									<option value="end">Truncate from end</option>
									<option value="start">Truncate from start</option>
								</select>
							</div>
						</div>
					</div>
				</div>

				<div className="flex shrink-0 items-center justify-between border-t border-gray-200 bg-white px-6 py-4">
					<button
						type="button"
						onClick={handleDelete}
						className="flex items-center gap-2 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
					>
						<Trash2 className="h-4 w-4" />
						Delete Node
					</button>
					<div className="flex items-center gap-3">
						<button
							type="button"
							onClick={onClose}
							className="text-sm font-medium text-gray-700 transition-colors hover:text-slate-900"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleSave}
							disabled={!hasUnsavedChanges}
							className="flex items-center gap-2 rounded-[4px] bg-orange-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40"
						>
							<Save className="h-4 w-4" />
							Save Changes
						</button>
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
