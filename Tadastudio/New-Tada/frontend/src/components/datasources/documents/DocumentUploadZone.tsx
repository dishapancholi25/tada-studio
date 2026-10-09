"use client";

import {
	Eye,
	FileText,
	Folder,
	FolderPlus,
	Lock,
	Plus,
	Search,
	Trash2,
	Upload,
} from "lucide-react";
import { useRef, useState } from "react";
import Button from "@/components/ui/Button";

export interface ChunkingConfig {
	strategy: "recursive" | "character" | "token" | "semantic" | "whole_page";
	chunkSize: number | null;
	chunkOverlap: number;
	loaderMode: "single" | "elements";
	preset: "fast" | "balanced" | "precise" | "whole_page" | "custom";
}

interface DocumentUploadZoneProps {
	collectionName?: string;
	onUpload: (files: FileList) => Promise<void>;
	uploading: boolean;
	uploadConfig: ChunkingConfig;
	onConfigChange: (config: ChunkingConfig) => void;
	disabled?: boolean;
	disabledReason?: string;
	failedCount?: number;
	onClearFailed?: () => void;
	hasCollection: boolean;
	hasEmbeddingModels: boolean;
	onCreateCollection: () => void;
	onSelectCollection: () => void;
	hasCollections: boolean;
	compact?: boolean;
	isReadOnly?: boolean;
	creatorName?: string;
}

export default function DocumentUploadZone({
	collectionName,
	onUpload,
	uploading,
	uploadConfig,
	onConfigChange,
	failedCount = 0,
	onClearFailed,
	hasCollection,
	hasEmbeddingModels,
	onCreateCollection,
	onSelectCollection,
	hasCollections,
	isReadOnly = false,
	creatorName,
}: DocumentUploadZoneProps) {
	const [isDragging, setIsDragging] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);

	const isDisabled = !hasCollection || !hasEmbeddingModels || uploading;
	const isWholePageMode = uploadConfig.strategy === "whole_page";

	const handleBrowseFiles = () => {
		if (!isDisabled) {
			fileInputRef.current?.click();
		}
	};

	const handleDrop = async (e: React.DragEvent) => {
		e.preventDefault();
		setIsDragging(false);
		if (!isDisabled && e.dataTransfer.files.length > 0) {
			await onUpload(e.dataTransfer.files);
		}
	};

	const handleDragOver = (e: React.DragEvent) => {
		e.preventDefault();
		if (!isDisabled) {
			setIsDragging(true);
		}
	};

	const handleDragLeave = () => {
		setIsDragging(false);
	};

	const toggleWholePageMode = () => {
		if (isWholePageMode) {
			// Switch to recursive (default chunking)
			onConfigChange({
				...uploadConfig,
				strategy: "recursive",
				chunkSize: 1000,
				chunkOverlap: 200,
				preset: "balanced",
			});
		} else {
			// Switch to whole page mode
			onConfigChange({
				...uploadConfig,
				strategy: "whole_page",
				chunkSize: null,
				chunkOverlap: 0,
				preset: "whole_page",
			});
		}
	};

	// Read-only collection state
	if (isReadOnly && hasCollection) {
		return (
			<div
				className="rounded-2xl border-2 border-dashed border-orange-300 bg-white p-5 opacity-90 shadow-md"
				style={{
					boxShadow: undefined,
				}}
			>
				<div className="flex flex-col items-center gap-5 py-8 px-6 text-center">
					<div className="rounded-full border border-orange-300 bg-orange-500 p-4">
						<Lock className="h-10 w-10 text-white" />
					</div>
					<div className="max-w-lg space-y-2">
						<h3 className="text-lg font-semibold text-slate-900">
							Shared Collection
						</h3>
						<p className="text-sm text-slate-600">
							This is a shared collection{creatorName ? ` created by ${creatorName}` : ''}. Only the collection creator can add or remove documents.
						</p>
					</div>
					<div className="w-full max-w-md rounded-lg border border-orange-200 bg-white p-4 text-left">
						<p className="mb-2 text-xs font-semibold text-slate-900">You can still:</p>
						<ul className="space-y-1.5 text-xs text-slate-600">
							<li className="flex items-center gap-2">
								<Eye className="h-3.5 w-3.5 text-orange-600" />
								View all documents in this collection
							</li>
							<li className="flex items-center gap-2">
								<Search className="h-3.5 w-3.5 text-orange-600" />
								Search within the collection
							</li>
							<li className="flex items-center gap-2">
								<Folder className="h-3.5 w-3.5 text-orange-600" />
								Use this collection in your workflows
							</li>
						</ul>
					</div>
				</div>
			</div>
		);
	}

	// No collection selected - show empty state
	if (!hasCollection) {
		return (
			<div
				className="rounded-2xl border-2 border-orange-300 bg-white p-5 shadow-md"
				style={{
					boxShadow: undefined,
				}}
			>
				<div className="flex flex-col items-center gap-6 py-10 px-6 text-center">
					<div className="flex flex-col items-center gap-4 max-w-lg">
						<div className="rounded-full border border-orange-300 bg-orange-500 p-4">
							<FolderPlus className="h-10 w-10 text-white" />
						</div>
						<h3 className="text-lg font-semibold text-slate-900">
							Start with a collection
						</h3>
						<p className="text-sm text-slate-600">
							Uploads live inside document collections. Create a new collection
							or choose an existing one to start adding files.
						</p>
					</div>
					<div className="flex flex-wrap justify-center gap-3">
						<Button
							onClick={onCreateCollection}
							icon={<Plus className="w-4 h-4" />}
						>
							New collection
						</Button>
						{hasCollections && (
							<Button
								variant="secondary"
								icon={<Folder className="w-4 h-4" />}
								onClick={onSelectCollection}
							>
								Choose existing
							</Button>
						)}
					</div>
				</div>
			</div>
		);
	}

	const FILE_TYPES = [
		{ ext: "PDF", color: "#ffffff", textColor: "rgb(194, 65, 12)" },
		{ ext: "DOCX", color: "#ffffff", textColor: "rgb(194, 65, 12)" },
		{ ext: "TXT", color: "#ffffff", textColor: "rgb(180, 83, 9)" },
		{ ext: "CSV", color: "#ffffff", textColor: "rgb(180, 83, 9)" },
		{ ext: "XLSX", color: "#ffffff", textColor: "rgb(180, 83, 9)" },
		{ ext: "MD", color: "#ffffff", textColor: "rgb(194, 65, 12)" },
	];

	return (
		<div
			className="rounded-2xl border-2 border-orange-300 bg-white p-5 shadow-md"
			style={{
				boxShadow: undefined,
			}}
		>
			<input
				ref={fileInputRef}
				type="file"
				multiple
				accept=".pdf,.docx,.txt,.csv,.xlsx,.md"
				onChange={(e) => {
					if (e.target.files && e.target.files.length > 0) {
						onUpload(e.target.files);
					}
				}}
				style={{ display: "none" }}
			/>

			<div className="space-y-4">
				{/* Header */}
				<div className="flex flex-wrap items-start justify-between gap-4">
					<div>
						<div className="flex items-center gap-2">
							<Upload className="h-5 w-5 text-orange-600" />
							<h3 className="text-base font-semibold text-slate-900">
								Upload documents
							</h3>
						</div>
						<p className="mt-1 text-xs text-slate-600">
							Files will be added to {collectionName}
						</p>
					</div>
					<div className="flex flex-wrap items-center gap-2">
						{failedCount > 0 && onClearFailed && (
							<Button
								onClick={onClearFailed}
								variant="danger"
								size="sm"
								icon={<Trash2 className="w-4 h-4" />}
							>
								Clear failed
							</Button>
						)}
					</div>
				</div>

				{/* Dropzone */}
				<div
					className={`rounded-xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden ${
						isDragging
							? "border-orange-500 bg-white"
							: "border-orange-200 border-slate-2000"
					} ${isDisabled ? "cursor-not-allowed opacity-50" : "hover:border-orange-400 hover:bg-white"}`}
					onDrop={handleDrop}
					onDragOver={handleDragOver}
					onDragLeave={handleDragLeave}
					onClick={isDisabled ? undefined : handleBrowseFiles}
				>
					{uploading ? (
						<div className="flex flex-col items-center justify-center py-10 gap-3">
							<div className="h-10 w-10 animate-spin rounded-full border-b-2 border-orange-500" />
							<p className="text-sm font-semibold text-slate-900">
								Processing files...
							</p>
							<p className="text-xs text-slate-500">
								Analyzing, chunking, and embedding documents
							</p>
						</div>
					) : (
						<div className="flex flex-col items-center py-8 px-6 gap-4">
							{/* Upload icon with accent ring */}
							<div
								className={`rounded-full p-4 transition-all duration-300 ${
									isDragging
										? "scale-110 bg-orange-500"
										: "bg-orange-500"
								}`}
							>
								<Upload
									className={`w-8 h-8 transition-colors ${
										isDragging
											? "text-white"
											: "text-white"
									}`}
								/>
							</div>

							{/* Main text */}
							<div className="text-center">
								<p className="text-sm font-semibold text-slate-900">
									{isDragging ? "Drop to upload" : "Drag and drop files here"}
								</p>
								<p className="mt-1 text-xs text-slate-500">
									or click anywhere to browse
								</p>
								<p className="mt-1 text-xs text-slate-400">
									Max: 1 GB per file
								</p>
							</div>

							{/* Browse button */}
							<Button
								variant="primary"
								size="sm"
								icon={<Upload className="w-4 h-4" />}
								onClick={(e) => {
									e.stopPropagation();
									handleBrowseFiles();
								}}
								disabled={isDisabled}
							>
								Browse Files
							</Button>

							{/* File type badges */}
							<div className="flex flex-wrap justify-center gap-1.5 mt-1">
								{FILE_TYPES.map((ft) => (
									<span
										key={ft.ext}
										className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wide"
										style={{
											background: ft.color,
											color: ft.textColor,
											border: `1px solid ${ft.textColor}33`,
										}}
									>
										{ft.ext}
									</span>
								))}
							</div>
						</div>
					)}
				</div>

				{/* Processing Mode Toggle */}
				<div className="rounded-xl border border-orange-200 border-slate-2000 p-4">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-3">
							<FileText className={`h-5 w-5 ${isWholePageMode ? "text-orange-600" : "text-slate-500"}`} />
							<div>
								<p className="text-sm font-semibold text-slate-900">Whole Page Mode</p>
								<p className="text-xs text-slate-600">
									{isWholePageMode
										? "Each PDF page is kept as a single chunk"
										: "Documents are split into smaller chunks for better search"}
								</p>
							</div>
						</div>
						<button
							type="button"
							onClick={toggleWholePageMode}
							className={`relative w-12 h-6 rounded-full transition-colors ${
								isWholePageMode
									? "bg-orange-500"
									: "bg-slate-200"
							}`}
						>
							<span
								className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
									isWholePageMode ? "left-7" : "left-1"
								}`}
							/>
						</button>
					</div>

					{/* Chunk settings when not in whole page mode */}
					{!isWholePageMode && (
						<div className="mt-4 grid grid-cols-2 gap-4 border-t border-orange-200/70 pt-4">
							<div>
								<div className="flex items-center justify-between mb-2">
									<label className="text-xs text-slate-600">
										Chunk Size
									</label>
									<span className="font-mono text-xs text-orange-700">
										{uploadConfig.chunkSize} chars
									</span>
								</div>
								<input
									type="range"
									min="200"
									max="4000"
									step="100"
									value={uploadConfig.chunkSize ?? 1000}
									onChange={(e) =>
										onConfigChange({
											...uploadConfig,
											chunkSize: Number.parseInt(e.target.value),
											preset: "custom",
										})
									}
									className="w-full"
									style={{ accentColor: "var(--color-primary)" }}
								/>
							</div>
							<div>
								<div className="flex items-center justify-between mb-2">
									<label className="text-xs text-slate-600">
										Chunk Overlap
									</label>
									<span className="font-mono text-xs text-orange-700">
										{uploadConfig.chunkOverlap} chars
									</span>
								</div>
								<input
									type="range"
									min="0"
									max="500"
									step="50"
									value={uploadConfig.chunkOverlap}
									onChange={(e) =>
										onConfigChange({
											...uploadConfig,
											chunkOverlap: Number.parseInt(e.target.value),
											preset: "custom",
										})
									}
									className="w-full"
									style={{ accentColor: "var(--color-primary)" }}
								/>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
