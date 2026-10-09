"use client";

import { FileSearch, FolderOpen } from "lucide-react";
import { useCallback } from "react";

export interface Collection {
	id: string;
	name: string;
	documentCount?: number;
	isReadOnly?: boolean;
	createdByName?: string;
	createdByEmail?: string;
}

export interface DocumentItem {
	id: string;
	name: string;
	collection_id: string;
	size?: number;
	created_at?: string;
}

interface DocumentsSectionProps {
	documentSelectionMode: "collections" | "documents";
	onSelectionModeChange: (mode: "collections" | "documents") => void;
	selectedCollections: string[];
	onSelectedCollectionsChange: (ids: string[]) => void;
	selectedDocuments: string[];
	onSelectedDocumentsChange: (ids: string[]) => void;
	collections: Collection[];
	documents: DocumentItem[];
	loadingCollections: boolean;
	loadingDocuments: boolean;
}

export default function DocumentsSection({
	documentSelectionMode,
	onSelectionModeChange,
	selectedCollections,
	onSelectedCollectionsChange,
	selectedDocuments,
	onSelectedDocumentsChange,
	collections,
	documents,
	loadingCollections,
	loadingDocuments,
}: DocumentsSectionProps) {
	const handleCollectionToggle = useCallback(
		(collectionId: string) => {
			if (selectedCollections.includes(collectionId)) {
				onSelectedCollectionsChange(
					selectedCollections.filter((id) => id !== collectionId),
				);
			} else {
				onSelectedCollectionsChange([...selectedCollections, collectionId]);
			}
		},
		[selectedCollections, onSelectedCollectionsChange],
	);

	const handleDocumentToggle = useCallback(
		(documentId: string) => {
			if (selectedDocuments.includes(documentId)) {
				onSelectedDocumentsChange(
					selectedDocuments.filter((id) => id !== documentId),
				);
			} else {
				onSelectedDocumentsChange([...selectedDocuments, documentId]);
			}
		},
		[selectedDocuments, onSelectedDocumentsChange],
	);

	const handleSelectAllDocuments = useCallback(() => {
		onSelectedDocumentsChange(documents.map((d) => d.id));
	}, [documents, onSelectedDocumentsChange]);

	const handleClearAllDocuments = useCallback(() => {
		onSelectedDocumentsChange([]);
	}, [onSelectedDocumentsChange]);

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex min-w-0 items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<FileSearch className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div className="min-w-0">
							<h3 className="text-lg font-semibold text-gray-900">
								Document Selection
							</h3>
							<p className="text-sm text-gray-600">
								Choose collections or specific documents to search
							</p>
						</div>
					</div>
					<div className="flex items-center gap-1 rounded-[4px] border border-gray-200 bg-white p-1">
						<button
							type="button"
							onClick={() => onSelectionModeChange("collections")}
							className={`rounded-[4px] px-3 py-1.5 text-xs font-medium transition-colors ${
								documentSelectionMode === "collections"
									? "bg-orange-600 text-white shadow-sm"
									: "text-gray-700 hover:bg-slate-50 hover:text-slate-900"
							}`}
						>
							Collections
						</button>
						<button
							type="button"
							onClick={() => onSelectionModeChange("documents")}
							className={`rounded-[4px] px-3 py-1.5 text-xs font-medium transition-colors ${
								documentSelectionMode === "documents"
									? "bg-orange-600 text-white shadow-sm"
									: "text-gray-700 hover:bg-slate-50 hover:text-slate-900"
							}`}
						>
							Specific Documents
						</button>
					</div>
				</div>

				<div className="mt-6">
					{documentSelectionMode === "collections" ? (
						loadingCollections ? (
							<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
								<p className="text-sm text-gray-600">
									Loading collections...
								</p>
							</div>
						) : collections.length === 0 ? (
							<div className="rounded-[4px] border border-blue-200 bg-white p-4 shadow-sm">
								<p className="text-sm text-blue-900">
									No document collections found. Upload documents to create
									collections.
								</p>
							</div>
						) : (
							<>
								<div className="custom-scrollbar max-h-80 space-y-2 overflow-y-auto">
									{collections.map((collection) => {
										const isChecked = selectedCollections.includes(
											collection.id,
										);
										return (
											<button
												type="button"
												key={collection.id}
												onClick={() => handleCollectionToggle(collection.id)}
												className={`
													relative flex w-full cursor-pointer items-center gap-4 rounded-[4px] border p-4 text-left transition-colors
													${
														isChecked
															? "border-orange-500 bg-white shadow-sm"
															: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50"
													}
												`}
											>
												<div
													className={`
														relative flex h-5 w-5 shrink-0 items-center justify-center rounded-[4px] transition-colors
														${
															isChecked
																? "bg-orange-600 shadow-sm"
																: "border-2 border-gray-300 bg-white"
														}
													`}
												>
													{isChecked && (
														<svg
															className="h-3 w-3 animate-scaleIn text-white"
															viewBox="0 0 20 20"
															fill="currentColor"
														>
															<path
																fillRule="evenodd"
																d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
																clipRule="evenodd"
															/>
														</svg>
													)}
												</div>

												<div className="min-w-0 flex-1">
													<div className="flex items-center gap-2">
														<span className="text-sm font-medium text-gray-900">
															{collection.name}
														</span>
														{collection.isReadOnly && (
															<span className="rounded-[4px] bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-800">
																Shared
															</span>
														)}
													</div>
													<div className="mt-0.5 text-xs text-gray-600">
														{collection.documentCount !== undefined && (
															<span>
																{collection.documentCount} document
																{collection.documentCount !== 1 ? "s" : ""}
															</span>
														)}
														{collection.isReadOnly &&
															(collection.createdByName ||
																collection.createdByEmail) && (
																<span>
																	{collection.documentCount !== undefined &&
																		" · "}
																	{collection.createdByName ||
																		collection.createdByEmail}
																</span>
															)}
													</div>
												</div>

												{collection.documentCount !== undefined &&
													collection.documentCount > 0 && (
														<div
															className={`
																rounded-full px-2.5 py-1 text-xs font-medium
																${
																	isChecked
																		? "bg-slate-100 text-gray-900"
																		: "bg-slate-100 text-gray-700"
																}
															`}
														>
															{collection.documentCount}
														</div>
													)}
											</button>
										);
									})}
								</div>

								{selectedCollections.length > 0 && (
									<div className="mt-4 rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-orange-400">
										<div className="mb-1 flex items-center gap-2">
											<FileSearch className="h-4 w-4 text-orange-600" />
											<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
												{selectedCollections.length} Collection
												{selectedCollections.length !== 1 ? "s" : ""} Selected
											</span>
										</div>
										<p className="mt-1 text-sm text-gray-800">
											{collections
												.filter((c) => selectedCollections.includes(c.id))
												.map((c) => c.name)
												.join(", ")}
										</p>
									</div>
								)}
							</>
						)
					) : (
						<>
							<div className="mb-4">
								<p className="mb-2 text-xs text-gray-600">
									Step 1: Select collections to browse documents from
								</p>
								{loadingCollections ? (
									<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
										<p className="text-sm text-gray-600">
											Loading collections...
										</p>
									</div>
								) : (
									<div className="custom-scrollbar max-h-32 space-y-2 overflow-y-auto">
										{collections.map((collection) => {
											const isSelected = selectedCollections.includes(
												collection.id,
											);
											return (
												<button
													type="button"
													key={collection.id}
													onClick={() =>
														handleCollectionToggle(collection.id)
													}
													className={`
														flex w-full cursor-pointer items-center gap-3 rounded-[4px] border p-3 text-left transition-colors
														${
															isSelected
																? "border-orange-500 bg-white text-gray-900 shadow-sm"
																: "border-transparent bg-white text-gray-700 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
														}
													`}
												>
													<FolderOpen className="h-4 w-4 shrink-0 text-gray-700" />
													<div className="flex flex-1 items-center gap-1.5 text-sm">
														<span className="font-medium text-gray-900">
															{collection.name}
														</span>
														{collection.isReadOnly && (
															<span className="rounded-[4px] bg-blue-50 px-1 py-0.5 text-[9px] font-medium text-blue-800">
																Shared
															</span>
														)}
													</div>
													{collection.documentCount !== undefined && (
														<div className="text-xs text-gray-600">
															({collection.documentCount} docs)
														</div>
													)}
												</button>
											);
										})}
									</div>
								)}
							</div>

							<div>
								<div className="mb-2 flex items-center justify-between">
									<p className="text-xs text-gray-600">
										Step 2: Select specific documents
									</p>
									{documents.length > 0 && (
										<div className="flex gap-2">
											<button
												type="button"
												onClick={handleSelectAllDocuments}
												className="text-xs font-medium text-gray-700 transition-colors hover:text-slate-900"
											>
												Select All
											</button>
											<span className="text-xs text-gray-400">|</span>
											<button
												type="button"
												onClick={handleClearAllDocuments}
												className="text-xs font-medium text-gray-700 transition-colors hover:text-slate-900"
											>
												Clear All
											</button>
										</div>
									)}
								</div>

								{loadingDocuments ? (
									<div className="rounded-[4px] border border-gray-200 bg-white p-6 text-center">
										<p className="text-sm text-gray-600">
											Loading documents...
										</p>
									</div>
								) : documents.length === 0 ? (
									<div className="rounded-[4px] border border-gray-200 bg-white p-4">
										<p className="text-center text-xs text-gray-600">
											{selectedCollections.length === 0
												? "Select collections above to see documents"
												: "No documents found in selected collections"}
										</p>
									</div>
								) : (
									<>
										<div className="custom-scrollbar max-h-48 space-y-2 overflow-y-auto rounded-[4px] border border-gray-200 bg-slate-50 p-4">
											{collections
												.filter((col) =>
													selectedCollections.includes(col.id),
												)
												.map((collection) => {
													const collectionDocs = documents.filter(
														(doc) => doc.collection_id === collection.id,
													);
													if (collectionDocs.length === 0) return null;

													return (
														<div key={collection.id} className="space-y-1">
															<div className="px-2 py-1 text-xs font-medium text-gray-600">
																{collection.name}
															</div>
															{collectionDocs.map((doc) => {
																const isChecked = selectedDocuments.includes(
																	doc.id,
																);
																return (
																	<button
																		type="button"
																		key={doc.id}
																		onClick={() =>
																			handleDocumentToggle(doc.id)
																		}
																		className={`
																			relative ml-2 flex w-full cursor-pointer items-center gap-3 rounded-[4px] border p-3 text-left transition-colors
																			${
																				isChecked
																					? "border-orange-500 bg-white shadow-sm"
																					: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50"
																			}
																		`}
																	>
																		<div
																			className={`
																				relative flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] transition-colors
																				${
																					isChecked
																						? "bg-orange-600"
																						: "border-2 border-gray-300 bg-white"
																				}
																			`}
																		>
																			{isChecked && (
																				<svg
																					className="h-2.5 w-2.5 text-white"
																					viewBox="0 0 20 20"
																					fill="currentColor"
																				>
																					<path
																						fillRule="evenodd"
																						d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
																						clipRule="evenodd"
																					/>
																				</svg>
																			)}
																		</div>

																		<div className="min-w-0 flex-1">
																			<div className="text-sm font-medium text-gray-900">
																				{doc.name}
																			</div>
																			{doc.size && (
																				<div className="text-xs text-gray-600">
																					{(doc.size / 1024).toFixed(1)} KB
																				</div>
																			)}
																		</div>
																	</button>
																);
															})}
														</div>
													);
												})}
										</div>

										{selectedDocuments.length > 0 && (
											<div className="mt-4 rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-orange-400">
												<div className="mb-1 flex items-center gap-2">
													<FileSearch className="h-4 w-4 text-orange-600" />
													<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
														{selectedDocuments.length} Document
														{selectedDocuments.length !== 1 ? "s" : ""}{" "}
														Selected
													</span>
												</div>
												<p className="mt-1 text-sm text-gray-800">
													{documents
														.filter((d) =>
															selectedDocuments.includes(d.id),
														)
														.map((d) => d.name)
														.join(", ")}
												</p>
											</div>
										)}
									</>
								)}
							</div>
						</>
					)}
				</div>
			</div>
		</div>
	);
}
