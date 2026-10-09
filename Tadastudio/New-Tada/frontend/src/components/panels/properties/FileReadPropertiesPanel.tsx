"use client";

import { FileText, Save, Shield, ShieldCheck, Sliders, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Node } from "reactflow";
import { useToast } from "@/contexts/ToastContext";
import { configAPI } from "@/lib/config-api";
import {
	type ModelDeploymentOption,
	modelDeploymentAPI,
} from "@/lib/model-deployment-api";
import type { FileReadConfig } from "@/types/nodes";
import { ProviderLogo } from "../../ui/ProviderLogos";
import ConfigSidebar from "./ConfigSidebar";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import AdvancedFileReadSection from "./sections/AdvancedFileReadSection";
import ExtractionSection from "./sections/ExtractionSection";
import OcrSection from "./sections/OcrSection";

interface FileReadNodeData {
	id: string;
	type: "FILE_READ";
	name: string;
	position?: { x: number; y: number };
	file_read_config?: FileReadConfig;
}

interface FileReadPropertiesPanelProps {
	node: Node<FileReadNodeData>;
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

// Default OCR prompts for different document types
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

interface ModelOption {
	value: string;
	label: string;
	description: string;
	icon?: React.ReactNode;
	provider: string;
	providerKey: string;
	model: ModelDeploymentOption;
}

type FileReadTabId = "extraction" | "ocr" | "advanced" | "guardrails";

const FileReadPropertiesPanel: React.FC<FileReadPropertiesPanelProps> = ({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}) => {
	const { showSuccess, showError } = useToast();
	const [nodeName, setNodeName] = useState(node.data?.name || "File Reader");
	const [hasChanges, setHasChanges] = useState(false);
	const [saving, setSaving] = useState(false);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	// Global document extraction provider (from admin config)
	const [globalProvider, setGlobalProvider] = useState<string>("model_ocr");

	// Model deployment state
	const [modelOptions, setModelOptions] = useState<ModelOption[]>([]);
	const [selectedModelId, setSelectedModelId] = useState<string>("");
	const [loadingModels, setLoadingModels] = useState(true);

	const [config, setConfig] = useState<FileReadConfig>({
		extraction_mode: "model_ocr",
		output_format: "markdown",
		ocr_prompt: OCR_PROMPT_TEMPLATES.generic,
		doc_type: "auto",
		max_tokens_per_request: 4000,
		max_pages: undefined,
		chunk_by_page: false,
		include_metadata: true,
		preserve_formatting: true,
		extract_tables: true,
		extract_images: true,
		max_file_size_mb: 1024,
		allowed_extensions: [
			".pdf",
			".png",
			".jpg",
			".jpeg",
			".docx",
			".txt",
			".xlsx",
			".csv",
		],
		fallback_on_error: true,
		skip_on_error: false,
		use_cache: true,
		llm_safe_output: false,
		...node.data?.file_read_config,
	});

	// Tab navigation
	const [activeTab, setActiveTab] = useState<FileReadTabId>("extraction");
	const contentRef = useRef<HTMLDivElement>(null);

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

	// Fetch model deployments on mount
	useEffect(() => {
		const fetchModels = async () => {
			try {
				setLoadingModels(true);
				const deployments = await modelDeploymentAPI.listSelectOptions();

				// Filter to LLM models only
				const llmDeployments = deployments.filter(
					(d) => d.model_type === "llm",
				);

				const mapped: ModelOption[] = llmDeployments
					.map((deployment) => {
						const providerLabel =
							deployment.provider.charAt(0).toUpperCase() +
							deployment.provider.slice(1);
						const descriptionParts = [providerLabel, deployment.model_name];

						return {
							value: deployment.id,
							label: deployment.display_name || deployment.name,
							provider: providerLabel,
							providerKey: deployment.provider,
							description: descriptionParts.join(" • "),
							icon: (
								<ProviderLogo
									provider={deployment.provider}
									className="w-4 h-4"
								/>
							),
							model: deployment,
						};
					})
					.sort((a, b) => a.label.localeCompare(b.label));

				setModelOptions(mapped);

				// Set initial model ID from config or default
				const initialModelDeploymentId =
					node.data?.file_read_config?.model_deployment_id;

				if (
					initialModelDeploymentId &&
					mapped.some((m) => m.value === initialModelDeploymentId)
				) {
					setSelectedModelId(initialModelDeploymentId);
				} else if (mapped.length > 0) {
					// Use default model or first available
					const defaultOption =
						mapped.find((option) => option.model.is_default) || mapped[0];
					setSelectedModelId(defaultOption.value);

					// Update config with default model
					setConfig((prev) => ({
						...prev,
						model_deployment_id: defaultOption.value,
					}));
				}
			} catch (error) {
				console.error("Failed to load model deployments:", error);
				showError("Failed to load models", "Could not load model deployments");
			} finally {
				setLoadingModels(false);
			}
		};

		fetchModels();
	}, [node.data?.file_read_config?.model_deployment_id, showError]);

	// Fetch global document extraction provider on mount
	useEffect(() => {
		configAPI.getEnvironmentConfig().then((envConfig) => {
			const provider =
				envConfig.external_services?.document_extraction?.provider ?? "model_ocr";
			setGlobalProvider(provider);
		}).catch(() => {
			// Default to model_ocr if config fetch fails
		});
	}, []);

	// useCallback handlers for performance optimization
	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	// Track changes
	useEffect(() => {
		const originalConfig = node.data.file_read_config || {};
		const hasConfigChanges =
			JSON.stringify(config) !== JSON.stringify(originalConfig);
		const hasNameChange = nodeName !== node.data.name;
		setHasChanges(hasConfigChanges || hasNameChange);
	}, [nodeName, config, node.data]);

	const handleSave = async () => {
		// Only require model for AI OCR mode (not for text_only or raw)
		if (config.extraction_mode === "model_ocr" && !config.model_deployment_id) {
			showError("Model required", "Please select a model in the OCR tab for AI extraction.");
			setActiveTab("ocr");
			return;
		}
		setSaving(true);
		try {
			await onUpdateNode(node.id, {
				name: nodeName,
				file_read_config: config,
			});
			showSuccess("File Read configuration saved");
			onClose();
		} catch (error) {
			console.error("Failed to save configuration:", error);
			showError("Save failed", "Failed to save configuration");
		} finally {
			setSaving(false);
		}
	};

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

	const handleApplyTemplate = useCallback(
		(templateKey: string, templateText: string) => {
			setConfig({
				...config,
				ocr_prompt: templateText,
				doc_type: templateKey as
					| "auto"
					| "generic"
					| "resume"
					| "invoice"
					| "form"
					| "table"
					| "handwritten",
			});
			showSuccess("Template applied", `Applied ${templateKey} OCR template`);
		},
		[config, showSuccess],
	);

	const handleModelChange = useCallback((modelId: string) => {
		setSelectedModelId(modelId);
		setConfig((prev) => ({ ...prev, model_deployment_id: modelId }));
	}, []);

	const handleDeleteAndClose = useCallback(() => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [node.id, onDeleteNode, onClose]);

	// Estimate token usage based on file type and settings
	const estimatedTokens =
		config.extraction_mode === "model_ocr"
			? config.max_pages
				? config.max_pages * 1500 // Rough estimate per page
				: 3000 // Default estimate
			: 0;

	// Define sidebar tabs - only show OCR tab when using model_ocr
	const fileReadTabs = useMemo(() => {
		const tabs: Array<{
			id: FileReadTabId;
			label: string;
			description: string;
			icon: React.ReactNode;
		}> = [
			{
				id: "extraction" as FileReadTabId,
				label: "Extraction",
				description: "Core settings",
				icon: <FileText className="h-4 w-4" />,
			},
		];

		// Only show OCR tab when using GPT-4o AND the global provider is model_ocr
		if (config.extraction_mode === "model_ocr" && globalProvider === "model_ocr") {
			tabs.push({
				id: "ocr" as FileReadTabId,
				label: "OCR",
				description: "Vision settings",
				icon: <Shield className="h-4 w-4" />,
			});
		}

		// Only show Advanced tab when not using raw mode (raw mode doesn't need processing options)
		if (config.extraction_mode !== "raw") {
			tabs.push({
				id: "advanced" as FileReadTabId,
				label: "Advanced",
				description: "Processing options",
				icon: <Sliders className="h-4 w-4" />,
			});
		}

		tabs.push({
			id: "guardrails" as FileReadTabId,
			label: "Guardrails",
			description: "Safety policies",
			icon: <ShieldCheck className="h-4 w-4" />,
		});

		return tabs;
	}, [config.extraction_mode, globalProvider]);

	// If OCR/Advanced tab is active but mode changes, switch to extraction tab
	useEffect(() => {
		if (activeTab === "ocr" && (config.extraction_mode !== "model_ocr" || globalProvider !== "model_ocr")) {
			setActiveTab("extraction");
		}
		// Also switch away from advanced tab if raw mode is selected
		if (activeTab === "advanced" && config.extraction_mode === "raw") {
			setActiveTab("extraction");
		}
	}, [config.extraction_mode, globalProvider, activeTab]);

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/60 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={onClose}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleStopPropagation}
			>
				<div className="relative flex min-h-[320px] max-h-[80vh] flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
					<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />

					{/* Header — Workflow Management style */}
					<div className="relative flex-none border-b border-slate-200 bg-white">
						<div className="flex items-center justify-between px-6 py-4">
							<div className="flex items-center gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
									<FileText className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div>
									<h2 className="text-lg font-semibold tracking-tight text-slate-900">
										File Read Configuration
									</h2>
									<p className="mt-0.5 text-sm text-slate-500">
										{globalProvider === "tika"
											? "Document extraction via Apache Tika"
											: globalProvider === "azure_document_intelligence"
												? "Document extraction via Azure Document Intelligence"
												: "AI Model OCR extraction"}
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					{/* Content: Sidebar + Section */}
					<div
						ref={contentRef}
						className="flex min-h-0 flex-1 overflow-hidden"
					>
							<ConfigSidebar
								items={fileReadTabs}
								activeItem={activeTab}
								onChange={(id) =>
									setActiveTab(id as FileReadTabId)
								}
								collapsed={sidebarCollapsed}
								variant="light"
							/>

							<div className="custom-scrollbar flex-1 space-y-6 overflow-y-auto bg-white px-6 py-5">
								{activeTab === "extraction" && (
									<ExtractionSection
										extractionMode={config.extraction_mode || "model_ocr"}
										onExtractionModeChange={(mode) =>
											setConfig({ ...config, extraction_mode: mode })
										}
										outputFormat={config.output_format || "markdown"}
										onOutputFormatChange={(format) =>
											setConfig({ ...config, output_format: format })
										}
										maxFileSizeMb={config.max_file_size_mb || 10}
										onMaxFileSizeMbChange={(size) =>
											setConfig({ ...config, max_file_size_mb: size })
										}
										allowedExtensions={config.allowed_extensions || []}
										onAllowedExtensionsChange={(extensions) =>
											setConfig({ ...config, allowed_extensions: extensions })
										}
										llmSafeOutput={Boolean(config.llm_safe_output)}
										onLlmSafeOutputChange={(enabled) =>
											setConfig({ ...config, llm_safe_output: enabled })
										}
										activeProvider={globalProvider}
									/>
								)}

								{activeTab === "ocr" && (
									<OcrSection
										ocrPrompt={config.ocr_prompt || ""}
										onOcrPromptChange={(prompt) =>
											setConfig({ ...config, ocr_prompt: prompt })
										}
										docType={config.doc_type || "auto"}
										onDocTypeChange={(docType) =>
											setConfig({ ...config, doc_type: docType })
										}
										maxTokensPerRequest={config.max_tokens_per_request || 4000}
										onMaxTokensPerRequestChange={(tokens) =>
											setConfig({ ...config, max_tokens_per_request: tokens })
										}
										maxPages={config.max_pages}
										onMaxPagesChange={(pages) =>
											setConfig({ ...config, max_pages: pages })
										}
										chunkByPage={config.chunk_by_page || false}
										onChunkByPageChange={(chunk) =>
											setConfig({ ...config, chunk_by_page: chunk })
										}
										estimatedTokens={estimatedTokens}
										onApplyTemplate={handleApplyTemplate}
										modelOptions={modelOptions}
										selectedModelId={selectedModelId}
										onModelChange={handleModelChange}
									/>
								)}

								{activeTab === "advanced" && (
									<AdvancedFileReadSection
										includeMetadata={config.include_metadata ?? true}
										onIncludeMetadataChange={(include) =>
											setConfig({ ...config, include_metadata: include })
										}
										preserveFormatting={config.preserve_formatting ?? true}
										onPreserveFormattingChange={(preserve) =>
											setConfig({ ...config, preserve_formatting: preserve })
										}
										extractTables={config.extract_tables ?? true}
										onExtractTablesChange={(extract) =>
											setConfig({ ...config, extract_tables: extract })
										}
										extractImages={config.extract_images ?? true}
										onExtractImagesChange={(extract) =>
											setConfig({ ...config, extract_images: extract })
										}
										useCache={config.use_cache ?? true}
										onUseCacheChange={(use) =>
											setConfig({ ...config, use_cache: use })
										}
										fallbackOnError={config.fallback_on_error ?? true}
										onFallbackOnErrorChange={(fallback) =>
											setConfig({ ...config, fallback_on_error: fallback })
										}
										skipOnError={config.skip_on_error || false}
										onSkipOnErrorChange={(skip) =>
											setConfig({ ...config, skip_on_error: skip })
										}
									/>
								)}

								{activeTab === "guardrails" && (
									<ToolGuardrailsSection toolNodeId={node.id} />
								)}
							</div>
						</div>

						{/* Footer */}
						<div className="border-t border-slate-200 bg-white px-6 py-3">
							<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
								<button
									type="button"
									onClick={handleDeleteAndClose}
									className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-2 text-xs text-red-800 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-950"
								>
									<Trash2 className="h-3.5 w-3.5" />
									Delete Node
								</button>

								<div className="flex items-center gap-3 sm:ml-auto">
									{hasChanges && (
										<span className="flex items-center gap-1.5 text-[11px] text-slate-600">
											<span className="h-1.5 w-1.5 animate-smoothPulse rounded-full bg-orange-500" />
											Unsaved
										</span>
									)}
									<span className="hidden text-[11px] text-slate-400 sm:inline">
										{"\u2318"}S to save
									</span>
									<button
										type="button"
										onClick={onClose}
										className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs text-slate-700 transition-colors hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
									>
										Cancel
									</button>
									<button
										type="button"
										onClick={handleSave}
										disabled={saving || !hasChanges}
										className="inline-flex items-center gap-1.5 rounded-[4px] border border-orange-500 bg-orange-500 px-5 py-2 text-xs font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
									>
										<Save className="h-3.5 w-3.5" />
										Save Changes
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
};

export default FileReadPropertiesPanel;
