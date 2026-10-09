"use client";

import { Code, Mail, Save, Send, Settings, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import type { Node } from "reactflow";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import CollapsibleSection from "../../ui/CollapsibleSection";
import UnifiedInputSourcePicker, {
	type InputSourceConfig,
} from "../../ui/UnifiedInputSourcePicker";

interface EmailFieldConfig {
	value: string;
	source_mode: "static" | "previous" | "specific" | "field" | "start";
	source_node_id?: string;
	source_field_path?: string;
}

interface EmailSendConfig {
	// Main fields
	to_address: string;
	to_source_mode: string;
	to_source_node_id?: string;
	to_source_field_path?: string;

	subject: string;
	subject_source_mode: string;
	subject_source_node_id?: string;
	subject_source_field_path?: string;

	body: string;
	body_source_mode: string;
	body_source_node_id?: string;
	body_source_field_path?: string;

	// Optional fields
	from_address: string;
	from_source_mode: string;
	from_source_node_id?: string;
	from_source_field_path?: string;

	reply_to: string;
	reply_to_source_mode: string;
	reply_to_source_node_id?: string;
	reply_to_source_field_path?: string;

	cc_addresses: string[];
	bcc_addresses: string[];

	// HTML body
	use_html: boolean;
	html_body: string;
	html_body_source_mode: string;
	html_body_source_node_id?: string;
	html_body_source_field_path?: string;

	// Template
	use_template: boolean;
	template_variables: Record<string, any>;

	// Settings
	timeout_seconds: number;
	track_opens: boolean;
	track_clicks: boolean;
}

interface EmailSendNodeData {
	id: string;
	name: string;
	email_send_config?: EmailSendConfig;
}

interface EmailSendPropertiesPanelProps {
	node: {
		id: string;
		data: EmailSendNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
	availableNodes: Node[];
}

function EmailFieldSection({
	label,
	fieldName,
	value,
	sourceMode,
	sourceNodeId,
	sourceFieldPath,
	onChange,
	availableNodes,
	placeholder = "",
	isTextArea = false,
	required = false,
}: {
	label: string;
	fieldName: string;
	value: string;
	sourceMode: string;
	sourceNodeId?: string;
	sourceFieldPath?: string;
	onChange: (field: string, updates: Partial<EmailFieldConfig>) => void;
	availableNodes: Node[];
	placeholder?: string;
	isTextArea?: boolean;
	required?: boolean;
}) {
	const handleInputSourceChange = useCallback(
		(config: InputSourceConfig) => {
			onChange(fieldName, {
				value: config.value,
				source_mode: config.source_mode,
				source_node_id: config.source_node_id,
				source_field_path: config.field_path,
			});
		},
		[onChange, fieldName],
	);

	return (
		<UnifiedInputSourcePicker
			label={label}
			value={value}
			sourceMode={sourceMode}
			sourceNodeId={sourceNodeId}
			fieldPath={sourceFieldPath}
			onChange={handleInputSourceChange}
			availableNodes={availableNodes}
			placeholder={placeholder}
			isTextArea={isTextArea}
			required={required}
			allowedModes={["static", "previous", "specific", "field"]}
			showPreview={true}
		/>
	);
}

export default function EmailSendPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
	availableNodes,
}: EmailSendPropertiesPanelProps) {
	const [saving, setSaving] = useState(false);
	const [hasChanges, setHasChanges] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	// Email configuration
	const [config, setConfig] = useState<EmailSendConfig>({
		to_address: "",
		to_source_mode: "static",
		subject: "",
		subject_source_mode: "static",
		body: "",
		body_source_mode: "static",
		from_address: "",
		from_source_mode: "static",
		reply_to: "",
		reply_to_source_mode: "static",
		cc_addresses: [],
		bcc_addresses: [],
		use_html: false,
		html_body: "",
		html_body_source_mode: "static",
		use_template: false,
		template_variables: {},
		timeout_seconds: 30,
		track_opens: false,
		track_clicks: false,
		...node.data.email_send_config,
	});

	const [advancedOpen, setAdvancedOpen] = useState(false);
	const [htmlOpen, setHtmlOpen] = useState(config.use_html);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleModalClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleClose = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleUseHtmlChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, use_html: e.target.checked });
		},
		[config],
	);

	const handleTimeoutChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, timeout_seconds: parseInt(e.target.value) || 30 });
		},
		[config],
	);

	const handleTrackOpensChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, track_opens: e.target.checked });
		},
		[config],
	);

	const handleTrackClicksChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, track_clicks: e.target.checked });
		},
		[config],
	);

	const handleDeleteClick = useCallback(() => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [node.id, onDeleteNode, onClose]);

	const handleSaveClick = useCallback(() => {
		setSaving(true);
		try {
			onUpdateNode(node.id, {
				email_send_config: config,
			});
			onClose();
		} catch (error) {
			console.error("Failed to save email send configuration:", error);
		} finally {
			setSaving(false);
		}
	}, [config, node.id, onUpdateNode, onClose]);

	const handleHtmlToggle = useCallback(() => {
		setHtmlOpen(!htmlOpen);
	}, [htmlOpen]);

	const handleAdvancedToggle = useCallback(() => {
		setAdvancedOpen(!advancedOpen);
	}, [advancedOpen]);

	// Track changes
	useEffect(() => {
		const originalConfig = node.data.email_send_config || {};
		const hasConfigChanges =
			JSON.stringify(config) !== JSON.stringify(originalConfig);
		setHasChanges(hasConfigChanges);
	}, [config, node.data]);

	const handleFieldChange = (field: string, updates: any) => {
		const fieldMap: Record<string, string[]> = {
			to: [
				"to_address",
				"to_source_mode",
				"to_source_node_id",
				"to_source_field_path",
			],
			subject: [
				"subject",
				"subject_source_mode",
				"subject_source_node_id",
				"subject_source_field_path",
			],
			body: [
				"body",
				"body_source_mode",
				"body_source_node_id",
				"body_source_field_path",
			],
			from: [
				"from_address",
				"from_source_mode",
				"from_source_node_id",
				"from_source_field_path",
			],
			reply_to: [
				"reply_to",
				"reply_to_source_mode",
				"reply_to_source_node_id",
				"reply_to_source_field_path",
			],
			html_body: [
				"html_body",
				"html_body_source_mode",
				"html_body_source_node_id",
				"html_body_source_field_path",
			],
		};

		const newConfig: any = { ...config };

		if (updates.value !== undefined) {
			newConfig[fieldMap[field][0]] = updates.value;
		}
		if (updates.source_mode !== undefined) {
			newConfig[fieldMap[field][1]] = updates.source_mode;
		}
		if (updates.source_node_id !== undefined) {
			newConfig[fieldMap[field][2]] = updates.source_node_id;
		}
		if (updates.source_field_path !== undefined) {
			newConfig[fieldMap[field][3]] = updates.source_field_path;
		}

		setConfig(newConfig);
	};

	return (
		<div
			className="fixed inset-0 z-[100] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-8 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="max-h-[80vh] min-h-[320px] w-[90vw] max-w-2xl flex flex-col overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]"
				onClick={handleModalClick}
			>
				<div className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white px-6 py-5">
					<div className="flex items-start gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
							<Mail className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div>
							<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
								Tool configuration
							</p>
							<h2 className="text-lg font-semibold text-gray-900">Email Send</h2>
							<p className="mt-0.5 text-sm text-gray-600">
								Configure email delivery settings
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={handleClose}
						className="rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<div className="custom-scrollbar flex-1 space-y-6 overflow-y-auto bg-slate-50 px-6 py-5">
					<div className="space-y-4">
						<div className="flex items-center gap-2">
							<Send className="h-4 w-4 text-orange-600" />
							<span className="text-xs font-semibold capitalize tracking-wide text-gray-800">
								Required Fields
							</span>
						</div>

						<EmailFieldSection
							label="To Address"
							fieldName="to"
							value={config.to_address}
							sourceMode={config.to_source_mode}
							sourceNodeId={config.to_source_node_id}
							sourceFieldPath={config.to_source_field_path}
							onChange={handleFieldChange}
							availableNodes={availableNodes}
							placeholder="recipient@example.com"
							required
						/>

						<EmailFieldSection
							label="Subject"
							fieldName="subject"
							value={config.subject}
							sourceMode={config.subject_source_mode}
							sourceNodeId={config.subject_source_node_id}
							sourceFieldPath={config.subject_source_field_path}
							onChange={handleFieldChange}
							availableNodes={availableNodes}
							placeholder="Email subject line"
							required
						/>

						<EmailFieldSection
							label="Body"
							fieldName="body"
							value={config.body}
							sourceMode={config.body_source_mode}
							sourceNodeId={config.body_source_node_id}
							sourceFieldPath={config.body_source_field_path}
							onChange={handleFieldChange}
							availableNodes={availableNodes}
							placeholder="Email body content..."
							isTextArea
							required
						/>
					</div>

					<CollapsibleSection
						title="HTML Content"
						isOpen={htmlOpen}
						onToggle={handleHtmlToggle}
						icon={<Code className="h-4 w-4 text-gray-600" />}
					>
						<div className="space-y-4">
							<div className="flex items-center gap-2">
								<input
									type="checkbox"
									id="use-html"
									checked={config.use_html}
									onChange={handleUseHtmlChange}
									className="h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-400/40"
								/>
								<label htmlFor="use-html" className="text-sm text-gray-800">
									Send as HTML email
								</label>
							</div>

							{config.use_html && (
								<EmailFieldSection
									label="HTML Body"
									fieldName="html_body"
									value={config.html_body}
									sourceMode={config.html_body_source_mode}
									sourceNodeId={config.html_body_source_node_id}
									sourceFieldPath={config.html_body_source_field_path}
									onChange={handleFieldChange}
									availableNodes={availableNodes}
									placeholder="<html>...</html>"
									isTextArea
								/>
							)}
						</div>
					</CollapsibleSection>

					<CollapsibleSection
						title="Advanced Settings"
						icon={<Settings className="h-4 w-4 text-gray-600" />}
						isOpen={advancedOpen}
						onToggle={handleAdvancedToggle}
					>
						<div className="space-y-4">
							<EmailFieldSection
								label="From Address"
								fieldName="from"
								value={config.from_address}
								sourceMode={config.from_source_mode}
								sourceNodeId={config.from_source_node_id}
								sourceFieldPath={config.from_source_field_path}
								onChange={handleFieldChange}
								availableNodes={availableNodes}
								placeholder="sender@example.com (optional)"
							/>

							<EmailFieldSection
								label="Reply To"
								fieldName="reply_to"
								value={config.reply_to}
								sourceMode={config.reply_to_source_mode}
								sourceNodeId={config.reply_to_source_node_id}
								sourceFieldPath={config.reply_to_source_field_path}
								onChange={handleFieldChange}
								availableNodes={availableNodes}
								placeholder="reply@example.com (optional)"
							/>

							<div>
								<label
									htmlFor="email-timeout-input"
									className="mb-2 block text-sm font-medium text-gray-800"
								>
									Timeout (seconds)
								</label>
								<input
									id="email-timeout-input"
									type="number"
									value={config.timeout_seconds}
									onChange={handleTimeoutChange}
									min={1}
									max={300}
									className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								/>
							</div>

							<div className="space-y-2">
								<div className="flex items-center gap-2">
									<input
										type="checkbox"
										id="track-opens"
										checked={config.track_opens}
										onChange={handleTrackOpensChange}
										className="h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-400/40"
									/>
									<label htmlFor="track-opens" className="text-sm text-gray-800">
										Track email opens
									</label>
								</div>

								<div className="flex items-center gap-2">
									<input
										type="checkbox"
										id="track-clicks"
										checked={config.track_clicks}
										onChange={handleTrackClicksChange}
										className="h-4 w-4 rounded border-gray-300 text-orange-600 focus:ring-orange-400/40"
									/>
									<label htmlFor="track-clicks" className="text-sm text-gray-800">
										Track link clicks
									</label>
								</div>
							</div>
						</div>
					</CollapsibleSection>
				</div>

				<div className="flex shrink-0 items-center justify-between border-t border-gray-200 bg-white px-6 py-4">
					<button
						type="button"
						onClick={handleDeleteClick}
						className="inline-flex items-center gap-2 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
					>
						<Trash2 className="h-4 w-4" />
						Delete Node
					</button>
					<div className="flex items-center gap-3">
						<button
							type="button"
							onClick={handleClose}
							className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleSaveClick}
							disabled={saving || !hasChanges}
							className="inline-flex items-center gap-2 rounded-[4px] bg-orange-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40"
						>
							<Save className="h-4 w-4" />
							{saving ? "Saving…" : "Save Changes"}
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
