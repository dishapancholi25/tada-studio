"use client";

import {
	FileOutput,
	FileText,
	Save,
	ShieldCheck,
	Trash2,
	Upload,
	X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Node } from "reactflow";
import Button from "../../ui/Button";
import ConfigSidebar from "./ConfigSidebar";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { useGraph } from "@/contexts/GraphContext";
import { runtimeConfig } from "@/lib/runtime-config";
import { cn } from "@/lib/utils";

interface FileWriteConfig {
	output_directory: string;
	allowed_extensions: string[];
	max_file_size_mb: number;
	create_directories: boolean;
	default_template?: string;
	custom_template_asset_id?: string;
	custom_template_variables?: string[];
	custom_template_filename?: string;
}

interface FileWriteNodeData {
	id: string;
	name: string;
	file_write_config?: FileWriteConfig;
}

interface FileWritePropertiesPanelProps {
	node: {
		id: string;
		data: FileWriteNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
	availableNodes?: Node[];
}

const DEFAULT_EXTENSIONS = [
	".txt",
	".md",
	".json",
	".csv",
	".yaml",
	".yml",
	".pdf",
	".docx",
	".xlsx",
	".pptx",
];
const BINARY_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif"];

const TEMPLATE_OPTIONS = [
	{ value: "", label: "Default (Modern)" },
	{ value: "modern", label: "Modern" },
	{ value: "executive", label: "Executive" },
	{ value: "report", label: "Report" },
	{ value: "invoice", label: "Invoice" },
	{ value: "minimal", label: "Minimal" },
];

const DEFAULT_CONFIG: FileWriteConfig = {
	output_directory: "outputs",
	allowed_extensions: [...DEFAULT_EXTENSIONS],
	max_file_size_mb: 1024,
	create_directories: true,
};

type FileWriteTabId = "output" | "templates" | "guardrails";

export default function FileWritePropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: FileWritePropertiesPanelProps) {
	const [saving, setSaving] = useState(false);
	const [uploading, setUploading] = useState(false);
	const [uploadError, setUploadError] = useState<string | null>(null);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const fileInputRef = useRef<HTMLInputElement>(null);
	const { currentGraph } = useGraph();

	const [activeTab, setActiveTab] = useState<FileWriteTabId>("output");

	const [config, setConfig] = useState<FileWriteConfig>(() => {
		const nodeConfig = node.data.file_write_config;
		if (!nodeConfig) return DEFAULT_CONFIG;
		return {
			...DEFAULT_CONFIG,
			...nodeConfig,
		};
	});

	const [extensionInput, setExtensionInput] = useState("");

	// Track initial config for unsaved changes detection
	const initialConfig = useRef(
		JSON.stringify(node.data.file_write_config || DEFAULT_CONFIG),
	);

	const hasUnsavedChanges = useMemo(
		() => JSON.stringify(config) !== initialConfig.current,
		[config],
	);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleConfigChange = useCallback(
		(field: keyof FileWriteConfig, value: any) => {
			setConfig((prev) => ({
				...prev,
				[field]: value,
			}));
		},
		[],
	);

	const handleAddExtension = useCallback(() => {
		const ext = extensionInput.trim().toLowerCase();
		if (!ext) return;

		const formatted = ext.startsWith(".") ? ext : `.${ext}`;
		if (!config.allowed_extensions.includes(formatted)) {
			handleConfigChange("allowed_extensions", [
				...config.allowed_extensions,
				formatted,
			]);
		}
		setExtensionInput("");
	}, [extensionInput, config.allowed_extensions, handleConfigChange]);

	const handleRemoveExtension = useCallback(
		(ext: string) => {
			handleConfigChange(
				"allowed_extensions",
				config.allowed_extensions.filter((e) => e !== ext),
			);
		},
		[config.allowed_extensions, handleConfigChange],
	);

	const handleToggleBinarySupport = useCallback(() => {
		const hasBinary = BINARY_EXTENSIONS.some((ext) =>
			config.allowed_extensions.includes(ext),
		);

		if (hasBinary) {
			handleConfigChange(
				"allowed_extensions",
				config.allowed_extensions.filter(
					(ext) => !BINARY_EXTENSIONS.includes(ext),
				),
			);
		} else {
			handleConfigChange("allowed_extensions", [
				...config.allowed_extensions,
				...BINARY_EXTENSIONS.filter(
					(ext) => !config.allowed_extensions.includes(ext),
				),
			]);
		}
	}, [config.allowed_extensions, handleConfigChange]);

	const handleTemplateUpload = useCallback(
		async (e: React.ChangeEvent<HTMLInputElement>) => {
			const file = e.target.files?.[0];
			if (!file || !currentGraph?.name) return;

			setUploading(true);
			setUploadError(null);

			try {
				const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
				const formData = new FormData();
				formData.append("file", file);

				const response = await fetch(
					`${apiBaseUrl}/api/graph/node/${encodeURIComponent(currentGraph.name)}/${node.id}/template`,
					{
						method: "POST",
						body: formData,
						credentials: "include",
					},
				);

				const result = await response.json();

				if (result.success) {
					setConfig((prev) => ({
						...prev,
						custom_template_asset_id: result.asset_id,
						custom_template_variables: result.variables,
						custom_template_filename: result.filename,
					}));
				} else {
					setUploadError(result.error || "Upload failed");
				}
			} catch (err) {
				setUploadError(
					err instanceof Error ? err.message : "Upload failed",
				);
			} finally {
				setUploading(false);
				if (fileInputRef.current) {
					fileInputRef.current.value = "";
				}
			}
		},
		[currentGraph?.name, node.id],
	);

	const handleRemoveTemplate = useCallback(async () => {
		if (!currentGraph?.name) return;

		try {
			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			await fetch(
				`${apiBaseUrl}/api/graph/node/${encodeURIComponent(currentGraph.name)}/${node.id}/template`,
				{
					method: "DELETE",
					credentials: "include",
				},
			);
		} catch (err) {
			console.error("Failed to delete template:", err);
		}

		setConfig((prev) => {
			const updated = { ...prev };
			delete updated.custom_template_asset_id;
			delete updated.custom_template_variables;
			delete updated.custom_template_filename;
			return updated;
		});
	}, [currentGraph?.name, node.id]);

	const handleDeleteAndClose = useCallback(() => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [node.id, onDeleteNode, onClose]);

	const handleSave = useCallback(() => {
		setSaving(true);
		try {
			onUpdateNode(node.id, {
				file_write_config: config,
			});
			onClose();
		} catch (error) {
			console.error("Failed to save file write configuration:", error);
		} finally {
			setSaving(false);
		}
	}, [config, node.id, onUpdateNode, onClose]);

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

	const hasBinarySupport = BINARY_EXTENSIONS.some((ext) =>
		config.allowed_extensions.includes(ext),
	);

	const hasCustomTemplate = Boolean(config.custom_template_asset_id);

	const panelTabs = useMemo(
		() => [
			{
				id: "output" as const,
				label: "Output",
				description: "File settings",
				icon: <FileOutput className="h-4 w-4" />,
			},
			{
				id: "templates" as const,
				label: "Templates",
				description: "Document styles",
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
										File Write Tool
									</h2>
									<p className="mt-0.5 text-sm text-gray-600">
										Configure file output settings
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
								setActiveTab(id as FileWriteTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"flex-1 min-h-0 space-y-6 bg-slate-50 px-6 py-5",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
								{/* Output Tab */}
								{activeTab === "output" && (
									<>
										{/* Output Directory */}
										<div className="space-y-2">
											<label className="text-sm font-medium text-gray-900">
												Output Directory
											</label>
											<input
												type="text"
												value={config.output_directory}
												onChange={(e) =>
													handleConfigChange(
														"output_directory",
														e.target.value,
													)
												}
												placeholder="outputs"
												className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
											/>
											<p className="text-xs text-gray-600">
												Relative path within the
												workspace directory
											</p>
										</div>

										{/* Max File Size */}
										<div className="space-y-2">
											<label className="text-sm font-medium text-gray-900">
												Max File Size (MB)
											</label>
											<input
												type="number"
												min="1"
												max="100"
												value={config.max_file_size_mb}
												onChange={(e) =>
													handleConfigChange(
														"max_file_size_mb",
														parseInt(
															e.target.value,
														) || 10,
													)
												}
												className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
											/>
										</div>

										{/* Create Directories */}
										<div className="flex items-center justify-between">
											<div>
												<label className="text-sm font-medium text-gray-900">
													Create Subdirectories
												</label>
												<p className="text-xs text-gray-600">
													Allow agent to create
													subdirectories within output
													directory
												</p>
											</div>
											<button
												type="button"
												onClick={() =>
													handleConfigChange(
														"create_directories",
														!config.create_directories,
													)
												}
												className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
													config.create_directories
														? "bg-orange-600"
														: "bg-gray-300"
												}`}
											>
												<span
													className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
														config.create_directories
															? "translate-x-6"
															: "translate-x-1"
													}`}
												/>
											</button>
										</div>

										{/* Binary Support Toggle */}
										<div className="flex items-center justify-between">
											<div>
												<label className="text-sm font-medium text-gray-900">
													Binary File Support
												</label>
												<p className="text-xs text-gray-600">
													Enable .png, .jpg, .gif
													(via base64)
												</p>
											</div>
											<button
												type="button"
												onClick={
													handleToggleBinarySupport
												}
												className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
													hasBinarySupport
														? "bg-orange-600"
														: "bg-gray-300"
												}`}
											>
												<span
													className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
														hasBinarySupport
															? "translate-x-6"
															: "translate-x-1"
													}`}
												/>
											</button>
										</div>

										{/* Allowed Extensions */}
										<div className="space-y-2">
											<label className="text-sm font-medium text-gray-900">
												Allowed Extensions
											</label>
											<div className="flex gap-2">
												<input
													type="text"
													value={extensionInput}
													onChange={(e) =>
														setExtensionInput(
															e.target.value,
														)
													}
													onKeyDown={(e) =>
														e.key === "Enter" &&
														handleAddExtension()
													}
													placeholder=".ext"
													className="flex-1 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
												/>
												<Button
													onClick={
														handleAddExtension
													}
													size="sm"
													variant="ghost"
												>
													Add
												</Button>
											</div>
											<div className="flex flex-wrap gap-2">
												{config.allowed_extensions.map(
													(ext) => (
														<span
															key={ext}
															className="inline-flex items-center gap-1 rounded-[4px] border border-gray-200 bg-slate-50 px-2 py-1 text-xs text-gray-800"
														>
															{ext}
															<button
																type="button"
																onClick={() =>
																	handleRemoveExtension(
																		ext,
																	)
																}
																className="text-gray-700 hover:text-red-700"
															>
																<X className="w-3 h-3" />
															</button>
														</span>
													),
												)}
											</div>
										</div>
									</>
								)}

								{/* Templates Tab */}
								{activeTab === "templates" && (
									<>
										{/* Info Banner */}
										<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
											<p className="text-sm text-gray-800">
												The AI agent can write files to
												the configured output directory.
												Supports professional document
												generation for PDF, DOCX, XLSX,
												and PPTX.
											</p>
										</div>

										{/* Custom Word Template */}
										<div className="space-y-3">
											<label className="text-sm font-medium text-gray-900">
												Custom Word Template
											</label>
											<p className="text-xs text-gray-600">
												Upload a .docx template with
												Jinja2 placeholders (
												{"{{ variable }}"}, {"{%"} for
												{"% }"} loops). The agent will
												output JSON data to fill the
												template.
											</p>

											{hasCustomTemplate ? (
												<div className="space-y-3 rounded-[4px] border border-emerald-300 bg-white p-4 shadow-sm">
													<div className="flex items-center justify-between">
														<div className="flex items-center gap-2">
															<FileOutput className="h-4 w-4 text-emerald-700" />
															<span className="text-sm font-medium text-emerald-900">
																{
																	config.custom_template_filename
																}
															</span>
														</div>
														<button
															type="button"
															onClick={
																handleRemoveTemplate
															}
															className="text-xs font-medium text-red-700 transition-colors hover:text-red-900"
														>
															Remove
														</button>
													</div>

													{config.custom_template_variables &&
														config
															.custom_template_variables
															.length > 0 && (
															<div className="space-y-1.5">
																<p className="text-xs text-gray-600">
																	Template
																	variables
																	(agent will
																	populate
																	these):
																</p>
																<div className="flex flex-wrap gap-1.5">
																	{config.custom_template_variables.map(
																		(v) => (
																			<span
																				key={
																					v
																				}
																				className="rounded-[4px] border border-emerald-300 bg-white px-2 py-0.5 font-mono text-xs text-emerald-900"
																			>
																				{
																					v
																				}
																			</span>
																		),
																	)}
																</div>
															</div>
														)}

													{config.custom_template_variables &&
														config
															.custom_template_variables
															.length === 0 && (
															<p className="text-xs text-amber-900">
																No template
																variables
																detected. Add{" "}
																{
																	"{{ variable }}"
																}{" "}
																placeholders to
																your template.
															</p>
														)}
												</div>
											) : (
												<div>
													<input
														ref={fileInputRef}
														type="file"
														accept=".docx"
														onChange={
															handleTemplateUpload
														}
														className="hidden"
													/>
													<Button
														onClick={() =>
															fileInputRef.current?.click()
														}
														size="sm"
														variant="ghost"
														icon={
															<Upload className="w-4 h-4" />
														}
														disabled={uploading}
														loading={uploading}
													>
														{uploading
															? "Uploading..."
															: "Upload Template (.docx)"}
													</Button>
												</div>
											)}

											{uploadError && (
												<p className="text-xs text-red-700">
													{uploadError}
												</p>
											)}
										</div>

										{/* Default Template Style */}
										{!hasCustomTemplate && (
											<div className="space-y-2">
												<label className="text-sm font-medium text-gray-900">
													Default Style Template
												</label>
												<select
													value={
														config.default_template ||
														""
													}
													onChange={(e) =>
														handleConfigChange(
															"default_template",
															e.target.value ||
																undefined,
														)
													}
													className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
												>
													{TEMPLATE_OPTIONS.map(
														(opt) => (
															<option
																key={opt.value}
																value={
																	opt.value
																}
															>
																{opt.label}
															</option>
														),
													)}
												</select>
												<p className="text-xs text-gray-600">
													Applied to PDF, DOCX, XLSX,
													and PPTX when no custom
													template is set
												</p>
											</div>
										)}
									</>
								)}

								{/* Guardrails Tab */}
								{activeTab === "guardrails" && (
									<ToolGuardrailsSection
										toolNodeId={node.id}
									/>
								)}
							</div>
						</div>

					<div className="border-t border-gray-200 bg-white px-6 py-3">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<button
								type="button"
								onClick={handleDeleteAndClose}
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
									disabled={saving}
									className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
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
