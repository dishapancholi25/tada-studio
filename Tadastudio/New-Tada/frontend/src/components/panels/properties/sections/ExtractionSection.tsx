"use client";

import { AlignLeft, Check, FileText, Shield, Sparkles } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import NumberInput from "@/components/ui/NumberInput";

interface ExtractionSectionProps {
	extractionMode: "model_ocr" | "text_only" | "raw";
	onExtractionModeChange: (mode: "model_ocr" | "text_only" | "raw") => void;
	outputFormat: "markdown" | "json" | "plain" | "raw";
	onOutputFormatChange: (format: "markdown" | "json" | "plain" | "raw") => void;
	maxFileSizeMb: number;
	onMaxFileSizeMbChange: (size: number) => void;
	allowedExtensions: string[];
	onAllowedExtensionsChange: (extensions: string[]) => void;
	llmSafeOutput: boolean;
	onLlmSafeOutputChange: (enabled: boolean) => void;
	activeProvider?: string | null;
}

const EXTRACTION_MODE_OPTIONS = [
	{
		value: "model_ocr",
		label: "AI OCR",
		description: "AI-powered extraction with OCR",
		icon: <Sparkles className="w-4 h-4" />,
	},
	{
		value: "text_only",
		label: "Text Only",
		description: "Direct text extraction (no OCR)",
		icon: <AlignLeft className="w-4 h-4" />,
	},
	{
		value: "raw",
		label: "Disabled",
		description: "Pass file as-is to connected Node",
		icon: <FileText className="w-4 h-4" />,
	},
];

const OUTPUT_FORMAT_OPTIONS = [
	{
		value: "markdown",
		label: "Markdown",
		description: "Formatted text with structure",
	},
	{ value: "json", label: "JSON", description: "Structured data format" },
	{
		value: "plain",
		label: "Plain Text",
		description: "Simple unformatted text",
	},
	{
		value: "raw",
		label: "Raw",
		description: "Original content with no formatting",
	},
];

const FILE_EXTENSIONS = [
	{ ext: ".pdf", label: "PDF" },
	{ ext: ".png", label: "PNG" },
	{ ext: ".jpg", label: "JPG" },
	{ ext: ".jpeg", label: "JPEG" },
	{ ext: ".docx", label: "DOCX" },
	{ ext: ".txt", label: "TXT" },
	{ ext: ".xlsx", label: "XLSX" },
	{ ext: ".csv", label: "CSV" },
	{ ext: ".html", label: "HTML" },
	{ ext: ".pptx", label: "PPTX" },
];

const dropdownTrigger =
	"border border-slate-200 bg-white hover:border-orange-300 focus:border-orange-500";

export default function ExtractionSection({
	extractionMode,
	onExtractionModeChange,
	outputFormat,
	onOutputFormatChange,
	maxFileSizeMb,
	onMaxFileSizeMbChange,
	allowedExtensions,
	onAllowedExtensionsChange,
	llmSafeOutput,
	onLlmSafeOutputChange,
	activeProvider,
}: ExtractionSectionProps) {
	const handleExtensionToggle = (ext: string) => {
		if (allowedExtensions.includes(ext)) {
			onAllowedExtensionsChange(allowedExtensions.filter((e) => e !== ext));
		} else {
			onAllowedExtensionsChange([...allowedExtensions, ext]);
		}
	};

	return (
		<div className="space-y-6">
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-orange-200 bg-orange-100 text-orange-600">
							<FileText className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Extraction Settings
							</h3>
							<p className="text-sm text-slate-600">
								Core file reading and extraction options
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					{activeProvider && activeProvider !== "model_ocr" && (
						<div className="flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
							<div className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-blue-500" />
							<p className="text-sm text-blue-900">
								Extraction is handled by{" "}
								<span className="font-semibold text-blue-950">
									{activeProvider === "tika"
										? "Apache Tika"
										: "Azure Document Intelligence"}
								</span>
								. OCR-specific options are hidden. Select{" "}
								<span className="font-semibold text-blue-950">Text Only</span>{" "}
								below to skip extraction entirely for plain text files.
							</p>
						</div>
					)}

					<div
						className={`grid grid-cols-1 gap-4 ${extractionMode !== "raw" ? "md:grid-cols-2" : ""}`}
					>
						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Extraction Mode
								</label>
								<InfoTooltip text="AI OCR uses the configured extraction service. Text Only reads the file directly. Disabled passes file content as-is to connected Nodes without processing." />
							</div>
							<Dropdown
								value={extractionMode}
								onChange={(val) => onExtractionModeChange(val as any)}
								options={EXTRACTION_MODE_OPTIONS}
								placeholder="Select extraction mode"
								triggerClassName={dropdownTrigger}
								menuAppearance="light"
							/>
						</div>

						{extractionMode !== "raw" && (
							<div>
								<div className="mb-2 flex items-center gap-2">
									<label className="text-sm font-semibold text-slate-800">
										Output Format
									</label>
									<InfoTooltip text="Format for the extracted content output" />
								</div>
								<Dropdown
									value={outputFormat}
									onChange={(val) => onOutputFormatChange(val as any)}
									options={OUTPUT_FORMAT_OPTIONS}
									placeholder="Select output format"
									triggerClassName={dropdownTrigger}
									menuAppearance="light"
								/>
							</div>
						)}
					</div>

					{extractionMode === "raw" && (
						<div className="space-y-3">
							<div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 transition-colors hover:border-orange-200">
								<div className="h-2 w-2 shrink-0 rounded-full bg-amber-600" />
								<p className="text-sm text-amber-950">
									File will be passed directly without any processing.
								</p>
							</div>

							<label className="flex cursor-pointer items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 transition-colors hover:border-blue-300">
								<input
									type="checkbox"
									checked={llmSafeOutput}
									onChange={(event) =>
										onLlmSafeOutputChange(event.target.checked)
									}
									className="mt-0.5 h-4 w-4 rounded border-blue-300 text-blue-600 focus:ring-blue-500"
								/>
								<span className="space-y-1">
									<span className="block text-sm font-semibold text-blue-950">
										Use LLM-safe file reference
									</span>
									<span className="block text-xs leading-relaxed text-blue-800">
										Agents see a compact reference instead of the full base64
										payload. Runtime delegation and HTTP tools can still resolve
										the original file content when needed.
									</span>
								</span>
							</label>
						</div>
					)}

					<div className="rounded-xl border border-slate-200 bg-white p-5">
						<div className="mb-4 flex items-start gap-3">
							<div className="rounded-lg border border-orange-200 bg-orange-100 p-2 text-orange-700">
								<Shield className="h-4 w-4" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-slate-900">
										Maximum File Size
									</h5>
									<InfoTooltip text="Maximum allowed file size in megabytes (1-1024 MB / 1 GB)" />
								</div>
								<p className="mt-1 text-xs text-slate-600">
									Files larger than this will be rejected
								</p>
							</div>
						</div>
						<NumberInput
							value={maxFileSizeMb}
							onChange={onMaxFileSizeMbChange}
							min={1}
							max={1024}
							step={1}
							label=""
							description=""
						/>
						<div className="mt-2 flex items-center justify-between text-xs text-slate-500">
							<span>Min: 1 MB</span>
							<span>Max: 1 GB (1024 MB)</span>
						</div>
					</div>

					<div>
						<div className="mb-3 flex items-center gap-2">
							<label className="text-sm font-semibold text-slate-800">
								Allowed File Types
							</label>
							<InfoTooltip text="Select which file types can be processed" />
						</div>
						<div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">
							{FILE_EXTENSIONS.map(({ ext, label }) => {
								const isSelected = allowedExtensions.includes(ext);
								return (
									<button
										key={ext}
										type="button"
										onClick={() => handleExtensionToggle(ext)}
										className={`rounded-lg border px-3 py-2 transition-all duration-200 ${
											isSelected
												? "border-orange-500 bg-orange-50 text-slate-900"
												: "border-slate-200 bg-white text-slate-700 hover:border-orange-300 hover:text-slate-900"
										}`}
									>
										<div className="flex items-center justify-center gap-1">
											{isSelected && <Check className="h-3 w-3 text-orange-700" />}
											<span className="text-sm font-medium">{label}</span>
										</div>
									</button>
								);
							})}
						</div>
						{allowedExtensions.length > 0 && (
							<div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
								<p className="text-xs text-slate-700">
									<span className="font-semibold text-orange-900">
										{allowedExtensions.length} file type
										{allowedExtensions.length !== 1 ? "s" : ""} selected
									</span>{" "}
									— {allowedExtensions.join(", ")}
								</p>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
