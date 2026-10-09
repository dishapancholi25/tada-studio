"use client";

import { Mail, Save, ShieldCheck, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Node } from "reactflow";
import ConfigSidebar from "./ConfigSidebar";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { cn } from "@/lib/utils";

interface EmailFieldConfig {
	mode: "ai" | "static";
	static_value: string;
	ai_description: string;
}

interface EmailSendToolConfig {
	to_address: EmailFieldConfig;
	subject: EmailFieldConfig;
	body: EmailFieldConfig;
}

interface EmailSendToolNodeData {
	id: string;
	name: string;
	email_send_tool_config?: EmailSendToolConfig;
}

interface EmailSendToolPropertiesPanelProps {
	node: {
		id: string;
		data: EmailSendToolNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
	availableNodes?: Node[];
}

const DEFAULT_FIELD_CONFIG: EmailFieldConfig = {
	mode: "ai",
	static_value: "",
	ai_description: "",
};

const DEFAULT_CONFIG: EmailSendToolConfig = {
	to_address: { ...DEFAULT_FIELD_CONFIG },
	subject: { ...DEFAULT_FIELD_CONFIG },
	body: { ...DEFAULT_FIELD_CONFIG },
};

interface EmailToolFieldSectionProps {
	label: string;
	fieldConfig: EmailFieldConfig;
	onChange: (updates: Partial<EmailFieldConfig>) => void;
	placeholder: string;
	aiPlaceholder: string;
	isTextArea?: boolean;
}

function EmailToolFieldSection({
	label,
	fieldConfig,
	onChange,
	placeholder,
	aiPlaceholder,
	isTextArea = false,
}: EmailToolFieldSectionProps) {
	const handleModeChange = (newMode: "ai" | "static") => {
		onChange({ mode: newMode });
	};

	return (
		<div className="space-y-3">
			<div className="flex items-center justify-between">
				<label className="text-sm font-medium text-gray-900">
					{label}
				</label>
				<div className="flex rounded-[4px] border border-gray-200 bg-white p-0.5">
					<button
						type="button"
						onClick={() => handleModeChange("ai")}
						className={`rounded-[4px] px-3 py-1 text-xs font-medium transition-all ${
							fieldConfig.mode === "ai"
								? "border border-emerald-500 bg-white text-emerald-700 shadow-sm"
								: "text-gray-600 hover:bg-gray-50 hover:text-slate-900"
						}`}
					>
						AI Mode
					</button>
					<button
						type="button"
						onClick={() => handleModeChange("static")}
						className={`rounded-[4px] px-3 py-1 text-xs font-medium transition-all ${
							fieldConfig.mode === "static"
								? "border border-blue-500 bg-white text-blue-800 shadow-sm"
								: "text-gray-600 hover:bg-gray-50 hover:text-slate-900"
						}`}
					>
						Static
					</button>
				</div>
			</div>

			{fieldConfig.mode === "ai" ? (
				<div className="space-y-1">
					<label className="text-xs text-gray-600">
						Describe how the AI should populate this field:
					</label>
					<textarea
						value={fieldConfig.ai_description}
						onChange={(e) => onChange({ ai_description: e.target.value })}
						placeholder={aiPlaceholder}
						rows={2}
						className="w-full resize-none rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
					/>
				</div>
			) : isTextArea ? (
				<textarea
					value={fieldConfig.static_value}
					onChange={(e) => onChange({ static_value: e.target.value })}
					placeholder={placeholder}
					rows={4}
					className="w-full resize-none rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
				/>
			) : (
				<input
					type="text"
					value={fieldConfig.static_value}
					onChange={(e) => onChange({ static_value: e.target.value })}
					placeholder={placeholder}
					className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
				/>
			)}
		</div>
	);
}

type EmailSendTabId = "email" | "guardrails";

export default function EmailSendToolPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: EmailSendToolPropertiesPanelProps) {
	const [saving, setSaving] = useState(false);
	const [activeTab, setActiveTab] = useState<EmailSendTabId>("email");
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	// Initialize config from node data
	const [config, setConfig] = useState<EmailSendToolConfig>(() => {
		const nodeConfig = node.data.email_send_tool_config;
		if (!nodeConfig) return DEFAULT_CONFIG;

		return {
			to_address: { ...DEFAULT_FIELD_CONFIG, ...nodeConfig.to_address },
			subject: { ...DEFAULT_FIELD_CONFIG, ...nodeConfig.subject },
			body: { ...DEFAULT_FIELD_CONFIG, ...nodeConfig.body },
		};
	});

	const initialConfig = useRef(
		JSON.stringify(node.data.email_send_tool_config || DEFAULT_CONFIG),
	);
	const contentRef = useRef<HTMLDivElement>(null);

	const hasUnsavedChanges = useMemo(
		() => JSON.stringify(config) !== initialConfig.current,
		[config],
	);

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

	const handleFieldChange = useCallback(
		(field: keyof EmailSendToolConfig, updates: Partial<EmailFieldConfig>) => {
			setConfig((prev) => ({
				...prev,
				[field]: { ...prev[field], ...updates },
			}));
		},
		[],
	);

	const handleDeleteClick = useCallback(() => {
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
				email_send_tool_config: config,
			});
			onClose();
		} catch (error) {
			console.error("Failed to save email send tool configuration:", error);
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

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const panelTabs = useMemo(
		() => [
			{
				id: "email" as const,
				label: "Email",
				description: "Field config",
				icon: <Mail className="h-4 w-4" />,
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
									<Mail className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										Email Send Tool
									</h2>
									<p className="mt-0.5 text-sm text-gray-600">
										Configure how the AI sends emails
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
								setActiveTab(id as EmailSendTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"flex-1 min-h-0 bg-slate-50 px-6 py-4",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
							<div className="space-y-6">
								{activeTab === "email" && (
									<>
										<div className="rounded-[4px] border border-emerald-200 bg-white p-4 shadow-sm">
											<p className="text-sm text-gray-800">
												Configure each field as either{" "}
												<strong className="text-emerald-800">AI Mode</strong> (the AI
												determines the value based on your description) or{" "}
												<strong className="text-blue-800">Static</strong> (a fixed value
												you provide).
											</p>
										</div>

										<div className="space-y-6">
											<EmailToolFieldSection
												label="To Address"
												fieldConfig={config.to_address}
												onChange={(updates) => handleFieldChange("to_address", updates)}
												placeholder="recipient@example.com"
												aiPlaceholder="e.g., Use the customer's email from the context"
											/>

											<EmailToolFieldSection
												label="Subject"
												fieldConfig={config.subject}
												onChange={(updates) => handleFieldChange("subject", updates)}
												placeholder="Email subject line"
												aiPlaceholder="e.g., Create a relevant subject based on the email content"
											/>

											<EmailToolFieldSection
												label="Body"
												fieldConfig={config.body}
												onChange={(updates) => handleFieldChange("body", updates)}
												placeholder="Email body content..."
												aiPlaceholder="e.g., Write a professional response addressing the customer's inquiry"
												isTextArea
											/>
										</div>
									</>
								)}

								{activeTab === "guardrails" && (
									<ToolGuardrailsSection toolNodeId={node.id} />
								)}
							</div>
						</div>
					</div>

					<div className="border-t border-gray-200 bg-white px-6 py-3">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<button
								type="button"
								onClick={handleDeleteClick}
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
									disabled={saving || !hasUnsavedChanges}
									className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
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
