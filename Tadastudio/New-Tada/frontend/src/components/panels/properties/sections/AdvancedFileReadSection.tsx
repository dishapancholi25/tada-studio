"use client";

import {
	AlertTriangle,
	FileCheck,
	FileImage,
	Sliders,
	Table as TableIcon,
	Zap,
} from "lucide-react";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import Toggle from "@/components/ui/Toggle";

interface AdvancedFileReadSectionProps {
	includeMetadata: boolean;
	onIncludeMetadataChange: (include: boolean) => void;
	preserveFormatting: boolean;
	onPreserveFormattingChange: (preserve: boolean) => void;
	extractTables: boolean;
	onExtractTablesChange: (extract: boolean) => void;
	extractImages: boolean;
	onExtractImagesChange: (extract: boolean) => void;
	useCache: boolean;
	onUseCacheChange: (use: boolean) => void;
	fallbackOnError: boolean;
	onFallbackOnErrorChange: (fallback: boolean) => void;
	skipOnError: boolean;
	onSkipOnErrorChange: (skip: boolean) => void;
}

const chipIconBox =
	"rounded-lg border border-orange-200 bg-orange-100 p-2 text-orange-700";

const rowCard =
	"rounded-xl border border-slate-200 bg-white p-5 transition-colors hover:border-orange-200";

export default function AdvancedFileReadSection({
	includeMetadata,
	onIncludeMetadataChange,
	preserveFormatting,
	onPreserveFormattingChange,
	extractTables,
	onExtractTablesChange,
	extractImages,
	onExtractImagesChange,
	useCache,
	onUseCacheChange,
	fallbackOnError,
	onFallbackOnErrorChange,
	skipOnError,
	onSkipOnErrorChange,
}: AdvancedFileReadSectionProps) {
	return (
		<div className="space-y-6">
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-orange-200 bg-orange-100 text-orange-600">
							<Sliders className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Advanced Options
							</h3>
							<p className="text-sm text-slate-600">
								Processing and error handling settings
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div className="space-y-4">
						<div className="flex items-center gap-2">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-slate-800">
								Processing Options
							</h4>
						</div>

						<div className={rowCard}>
							<div className="flex items-center justify-between gap-4">
								<div className="flex flex-1 items-start gap-3">
									<div className={chipIconBox}>
										<FileCheck className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Include Metadata
											</h5>
											<InfoTooltip text="Include file metadata like creation date, author, and file properties" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Add file properties and metadata to extraction results
										</p>
									</div>
								</div>
								<Toggle
									checked={includeMetadata}
									onChange={onIncludeMetadataChange}
									size="md"
								/>
							</div>
						</div>

						<div className={rowCard}>
							<div className="flex items-center justify-between gap-4">
								<div className="flex flex-1 items-start gap-3">
									<div className={chipIconBox}>
										<FileCheck className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Preserve Formatting
											</h5>
											<InfoTooltip text="Maintain original text formatting like bold, italic, and headings" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Keep text styling and structure from original document
										</p>
									</div>
								</div>
								<Toggle
									checked={preserveFormatting}
									onChange={onPreserveFormattingChange}
									size="md"
								/>
							</div>
						</div>

						<div className={rowCard}>
							<div className="flex items-center justify-between gap-4">
								<div className="flex flex-1 items-start gap-3">
									<div className={chipIconBox}>
										<TableIcon className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Extract Tables
											</h5>
											<InfoTooltip text="Detect and extract tabular data into structured format" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Convert tables to markdown or structured format
										</p>
									</div>
								</div>
								<Toggle
									checked={extractTables}
									onChange={onExtractTablesChange}
									size="md"
								/>
							</div>
						</div>

						<div className={rowCard}>
							<div className="flex items-center justify-between gap-4">
								<div className="flex flex-1 items-start gap-3">
									<div className={chipIconBox}>
										<FileImage className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Extract Embedded Images
											</h5>
											<InfoTooltip text="Extract images embedded in documents (DOCX files only)" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Save embedded images separately (DOCX only)
										</p>
									</div>
								</div>
								<Toggle
									checked={extractImages}
									onChange={onExtractImagesChange}
									size="md"
								/>
							</div>
						</div>
					</div>

					<div className="space-y-4">
						<div className="flex items-center gap-2">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-slate-800">
								Performance & Caching
							</h4>
						</div>

						<div className={rowCard}>
							<div className="flex items-center justify-between gap-4">
								<div className="flex flex-1 items-start gap-3">
									<div className={chipIconBox}>
										<Zap className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Use Cache
											</h5>
											<InfoTooltip text="Cache extraction results to speed up repeated processing of the same files" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Faster processing for previously extracted files
										</p>
									</div>
								</div>
								<Toggle checked={useCache} onChange={onUseCacheChange} size="md" />
							</div>
						</div>
					</div>

					<div className="space-y-4">
						<div className="flex items-center gap-2">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-slate-800">
								Error Handling
							</h4>
						</div>

						<div className={rowCard}>
							<div className="flex items-center justify-between gap-4">
								<div className="flex flex-1 items-start gap-3">
									<div className="rounded-lg border border-slate-200 bg-white p-2 text-amber-700">
										<AlertTriangle className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Fallback on Error
											</h5>
											<InfoTooltip text="Try alternative extraction methods if primary method fails" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Attempt text-only extraction if AI model OCR extraction fails
										</p>
									</div>
								</div>
								<Toggle
									checked={fallbackOnError}
									onChange={onFallbackOnErrorChange}
									size="md"
								/>
							</div>
						</div>

						<div className={rowCard}>
							<div className="flex items-center justify-between gap-4">
								<div className="flex flex-1 items-start gap-3">
									<div className="rounded-lg border border-slate-200 bg-white p-2 text-amber-700">
										<AlertTriangle className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Skip on Error
											</h5>
											<InfoTooltip text="Continue workflow execution even if file extraction fails" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Don&apos;t stop workflow if this file fails to process
										</p>
									</div>
								</div>
								<Toggle checked={skipOnError} onChange={onSkipOnErrorChange} size="md" />
							</div>
						</div>
					</div>

					<div className="rounded-lg border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-orange-200">
						<div className="mb-2 flex items-center gap-2">
							<Sliders className="h-4 w-4 text-orange-700" />
							<span className="text-xs font-semibold capitalize tracking-wide text-slate-800">
								Current Settings
							</span>
						</div>
						<div className="flex flex-wrap gap-2">
							{includeMetadata && (
								<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
									✓ Metadata
								</span>
							)}
							{preserveFormatting && (
								<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
									✓ Formatting
								</span>
							)}
							{extractTables && (
								<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
									✓ Tables
								</span>
							)}
							{extractImages && (
								<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
									✓ Images
								</span>
							)}
							{useCache && (
								<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
									✓ Cache
								</span>
							)}
							{fallbackOnError && (
								<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
									✓ Fallback
								</span>
							)}
							{skipOnError && (
								<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-800">
									✓ Skip Errors
								</span>
							)}
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
