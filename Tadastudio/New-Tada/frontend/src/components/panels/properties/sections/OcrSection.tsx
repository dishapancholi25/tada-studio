"use client";

import {
	ClipboardList,
	FileCode,
	FileText,
	PenTool,
	Receipt,
	Sparkles,
	Table as TableIcon,
	User,
	Zap,
} from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import NumberInput from "@/components/ui/NumberInput";
import Toggle from "@/components/ui/Toggle";

interface ModelOption {
	value: string;
	label: string;
	description: string;
	icon?: React.ReactNode;
}

interface OcrSectionProps {
	ocrPrompt: string;
	onOcrPromptChange: (prompt: string) => void;
	docType:
		| "auto"
		| "generic"
		| "resume"
		| "invoice"
		| "form"
		| "table"
		| "handwritten";
	onDocTypeChange: (
		docType:
			| "auto"
			| "generic"
			| "resume"
			| "invoice"
			| "form"
			| "table"
			| "handwritten",
	) => void;
	maxTokensPerRequest: number;
	onMaxTokensPerRequestChange: (tokens: number) => void;
	maxPages?: number;
	onMaxPagesChange: (pages: number | undefined) => void;
	chunkByPage: boolean;
	onChunkByPageChange: (chunk: boolean) => void;
	estimatedTokens: number;
	onApplyTemplate: (templateKey: string, templateText: string) => void;
	modelOptions: ModelOption[];
	selectedModelId: string;
	onModelChange: (modelId: string) => void;
}

const OCR_PROMPT_TEMPLATES = {
	generic: `Extract all text from this document image. Preserve the original formatting including:
- Headers and sections
- Lists and bullet points
- Tables (use markdown table format)
- Bold and italic text
- Page numbers if visible

Output as clean, well-structured markdown.`,

	resume: `Extract all information from this resume/CV. Structure the output with these sections:
- Personal Information (name, contact)
- Professional Summary
- Work Experience (company, role, dates, responsibilities)
- Education (degree, institution, dates)
- Skills (categorized if applicable)
- Certifications and Awards

Format as structured markdown with clear headers.`,

	invoice: `Extract all data from this invoice/receipt. Include:
- Document number and date
- Vendor/seller information
- Buyer/customer information
- Line items (description, quantity, price, total)
- Subtotal, tax, and total amounts
- Payment terms and notes

Format as structured data with a markdown table for line items.`,

	form: `Extract all fields and values from this form. For each field:
- Field name/label
- Field value or response
- Checkbox/radio button selections
- Signatures or stamps if present

Maintain the form's logical structure and group related fields.`,

	table: `Extract the table data from this image.
- Preserve all column headers
- Extract all row data accurately
- Maintain cell alignment and structure
- Handle merged cells appropriately

Output as a clean markdown table.`,

	handwritten: `Extract all handwritten text from this image.
- Transcribe as accurately as possible
- Note any unclear or ambiguous text with [unclear]
- Preserve line breaks and paragraph structure
- Indicate any drawings or diagrams

Focus on accuracy over formatting.`,
};

const DOC_TYPE_OPTIONS = [
	{ value: "auto", label: "Auto Detect", description: "Automatically detect document type" },
	{ value: "generic", label: "Generic", description: "General purpose document" },
	{ value: "resume", label: "Resume/CV", description: "Resume or CV document" },
	{ value: "invoice", label: "Invoice/Receipt", description: "Invoice or receipt" },
	{ value: "form", label: "Form", description: "Form or application" },
	{ value: "table", label: "Table", description: "Table data" },
	{ value: "handwritten", label: "Handwritten", description: "Handwritten text" },
];

const TEMPLATE_OPTIONS = [
	{
		value: "generic",
		label: "Generic Document",
		description: "General purpose extraction",
		icon: <FileText className="w-4 h-4" />,
	},
	{
		value: "resume",
		label: "Resume/CV",
		description: "Extract CV/resume data",
		icon: <User className="w-4 h-4" />,
	},
	{
		value: "invoice",
		label: "Invoice/Receipt",
		description: "Extract invoice/receipt data",
		icon: <Receipt className="w-4 h-4" />,
	},
	{
		value: "form",
		label: "Form/Application",
		description: "Extract form fields and values",
		icon: <ClipboardList className="w-4 h-4" />,
	},
	{
		value: "table",
		label: "Table",
		description: "Focus on table extraction",
		icon: <TableIcon className="w-4 h-4" />,
	},
	{
		value: "handwritten",
		label: "Handwritten",
		description: "Extract handwritten text",
		icon: <PenTool className="w-4 h-4" />,
	},
];

const dropdownTrigger =
	"border border-slate-200 bg-white hover:border-orange-300 focus:border-orange-500";

export default function OcrSection({
	ocrPrompt,
	onOcrPromptChange,
	docType,
	onDocTypeChange,
	maxTokensPerRequest,
	onMaxTokensPerRequestChange,
	maxPages,
	onMaxPagesChange,
	chunkByPage,
	onChunkByPageChange,
	estimatedTokens,
	onApplyTemplate,
	modelOptions,
	selectedModelId,
	onModelChange,
}: OcrSectionProps) {
	const handleTemplateChange = (templateKey: string) => {
		const templateText =
			OCR_PROMPT_TEMPLATES[templateKey as keyof typeof OCR_PROMPT_TEMPLATES];
		onApplyTemplate(templateKey, templateText);
	};

	return (
		<div className="space-y-6">
			<div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-orange-200 bg-orange-100 text-orange-600">
							<Sparkles className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								OCR Configuration
							</h3>
							<p className="text-sm text-slate-600">
								AI Model OCR extraction settings
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									AI Model
								</label>
								<InfoTooltip text="Select which model deployment to use for OCR extraction" />
							</div>
							<Dropdown
								value={selectedModelId}
								onChange={onModelChange}
								options={modelOptions}
								placeholder="Select a model"
								triggerClassName={dropdownTrigger}
								menuAppearance="light"
							/>
						</div>
						<div>
							<div className="mb-2 flex items-center gap-2">
								<label className="text-sm font-semibold text-slate-800">
									Document Type
								</label>
								<InfoTooltip text="Hint to improve extraction quality for specific document types" />
							</div>
							<Dropdown
								value={docType}
								onChange={(val) => onDocTypeChange(val as typeof docType)}
								options={DOC_TYPE_OPTIONS}
								placeholder="Select document type"
								triggerClassName={dropdownTrigger}
								menuAppearance="light"
							/>
						</div>
					</div>

					<div>
						<div className="mb-2 flex items-center gap-2">
							<label className="text-sm font-semibold text-slate-800">
								OCR Prompt Template
							</label>
							<InfoTooltip text="Select a pre-configured template or customize the prompt below" />
						</div>
						<Dropdown
							value={docType === "auto" ? "generic" : docType}
							onChange={handleTemplateChange}
							options={TEMPLATE_OPTIONS}
							placeholder="Select a template"
							triggerClassName={dropdownTrigger}
							menuAppearance="light"
						/>
					</div>

					<div>
						<div className="mb-2 flex items-center gap-2">
							<label className="text-sm font-semibold text-slate-800">
								Custom OCR Prompt
							</label>
							<InfoTooltip text="Customize the instructions for the AI model on how to extract text from the document" />
						</div>
						<textarea
							value={ocrPrompt}
							onChange={(e) => onOcrPromptChange(e.target.value)}
							className="w-full resize-none rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 transition-colors placeholder:text-slate-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/20 font-mono"
							rows={10}
							placeholder="Enter OCR extraction prompt..."
						/>
						<p className="mt-2 text-xs text-slate-600">
							Use markdown formatting. Be specific about what information to
							extract and how to structure the output.
						</p>
					</div>

					<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
						<div className="rounded-xl border border-slate-200 bg-white p-5">
							<div className="mb-4 flex items-start gap-3">
								<div className="rounded-lg border border-orange-200 bg-orange-100 p-2 text-orange-700">
									<FileCode className="h-4 w-4" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-slate-900">
											Max Tokens per Request
										</h5>
										<InfoTooltip text="Maximum tokens the AI model can use per extraction request" />
									</div>
									<p className="mt-1 text-xs text-slate-600">
										Higher values allow more detailed extraction
									</p>
								</div>
							</div>
							<NumberInput
								value={maxTokensPerRequest}
								onChange={onMaxTokensPerRequestChange}
								min={500}
								max={8000}
								step={100}
								label=""
								description=""
							/>
							<div className="mt-2 flex items-center justify-between text-xs text-slate-500">
								<span>Min: 500</span>
								<span>Max: 8000</span>
							</div>
						</div>

						<div className="flex flex-col justify-center rounded-xl border border-slate-200 bg-slate-50 p-5">
							<div className="mb-2 flex items-center gap-3">
								<div className="rounded-lg border border-orange-200 bg-orange-100 p-2 text-orange-700">
									<Zap className="h-4 w-4" />
								</div>
								<h5 className="text-sm font-semibold text-slate-900">
									Estimated Usage
								</h5>
							</div>
							<div className="mb-1 text-3xl font-bold text-orange-700">
								~{estimatedTokens.toLocaleString()}
							</div>
							<p className="text-xs text-slate-700">tokens per document</p>
							<p className="mt-2 text-xs text-slate-600">
								Based on document complexity and page count
							</p>
						</div>
					</div>

					<div className="space-y-4">
						<div className="flex items-center gap-2">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-slate-800">
								PDF Processing Options
							</h4>
						</div>

						<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
							<div className="rounded-xl border border-slate-200 bg-white p-5">
								<div className="mb-4 flex items-start gap-3">
									<div className="rounded-lg border border-orange-200 bg-orange-100 p-2 text-orange-700">
										<FileText className="h-4 w-4" />
									</div>
									<div className="flex-1">
										<div className="flex items-center gap-2">
											<h5 className="text-sm font-semibold text-slate-900">
												Maximum Pages
											</h5>
											<InfoTooltip text="Limit how many pages to process from PDF files (leave empty for all pages)" />
										</div>
										<p className="mt-1 text-xs text-slate-600">
											Optional limit (empty = all pages)
										</p>
									</div>
								</div>
								<input
									type="number"
									value={maxPages || ""}
									onChange={(e) =>
										onMaxPagesChange(
											e.target.value ? parseInt(e.target.value, 10) : undefined,
										)
									}
									placeholder="All pages"
									min="1"
									className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-900 transition-colors focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/20"
								/>
							</div>

							<div className="rounded-xl border border-slate-200 bg-white p-5">
								<div className="flex items-center justify-between gap-4">
									<div className="flex flex-1 items-start gap-3">
										<div className="rounded-lg border border-orange-200 bg-orange-100 p-2 text-orange-700">
											<FileCode className="h-4 w-4" />
										</div>
										<div className="flex-1">
											<div className="flex items-center gap-2">
												<h5 className="text-sm font-semibold text-slate-900">
													Chunk by Page
												</h5>
												<InfoTooltip text="Return results separated by page instead of as one combined result" />
											</div>
											<p className="mt-1 text-xs text-slate-600">
												Process and return each page separately
											</p>
										</div>
									</div>
									<Toggle
										checked={chunkByPage}
										onChange={onChunkByPageChange}
										size="md"
									/>
								</div>
							</div>
						</div>
					</div>

					<div className="rounded-lg border border-slate-200 bg-white p-4 transition-colors hover:border-orange-200">
						<div className="flex items-start gap-3">
							<Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-orange-600" />
							<div>
								<h4 className="mb-2 text-sm font-semibold text-slate-900">
									AI Model OCR Tips
								</h4>
								<ul className="space-y-1 text-xs text-slate-700">
									<li>
										• AI model provides context-aware extraction with high
										accuracy
									</li>
									<li>
										• Customize prompts for specific document types for best
										results
									</li>
									<li>• PDFs are processed page-by-page for optimal quality</li>
									<li>• Token usage depends on document complexity and size</li>
								</ul>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
