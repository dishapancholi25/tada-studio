"use client";

import { AlertCircle, Clock, Info, Mail, Save, X } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import type { Node } from "reactflow";
import UnifiedInputSourcePicker, {
	type InputSourceConfig,
} from "@/components/ui/UnifiedInputSourcePicker";
import { useGraph } from "@/contexts/GraphContext";
import { cn } from "@/lib/utils";

interface CheckpointPropertiesPanelProps {
	nodeId: string;
	onClose: () => void;
	availableNodes?: Node[];
}

type CheckpointTabId = "manual" | "email";

export default function CheckpointPropertiesPanel({
	nodeId,
	onClose,
	availableNodes = [],
}: CheckpointPropertiesPanelProps) {
	const { nodes, updateNode } = useGraph();
	const node = nodes.find((n) => n.id === nodeId);

	const [saving, setSaving] = useState<boolean>(false);

	// Initialize activeTab from saved await_mode
	const initialMode = node?.data?.checkpoint_config?.await_mode || "manual";
	const [activeTab, setActiveTab] = useState<CheckpointTabId>(
		initialMode as CheckpointTabId,
	);

	// Checkpoint configuration
	const [prompt, setPrompt] = useState(
		node?.data?.checkpoint_config?.prompt ||
			"Please review and provide input to continue.",
	);

	// Get email config
	const emailConfig = node?.data?.checkpoint_config?.email_config || {};

	// Recipient email with source configuration
	const [recipientEmail, setRecipientEmail] = useState(
		emailConfig.recipient_email || "",
	);
	const [recipientEmailSourceMode, setRecipientEmailSourceMode] = useState(
		emailConfig.recipient_email_source_mode || "static",
	);
	const [recipientEmailSourceNodeId, setRecipientEmailSourceNodeId] = useState(
		emailConfig.recipient_email_source_node_id,
	);
	const [recipientEmailFieldPath, setRecipientEmailFieldPath] = useState(
		emailConfig.recipient_email_field_path,
	);

	// Email subject with source configuration
	const [emailSubject, setEmailSubject] = useState(
		emailConfig.email_subject || "",
	);
	const [emailSubjectSourceMode, setEmailSubjectSourceMode] = useState(
		emailConfig.email_subject_source_mode || "static",
	);
	const [emailSubjectSourceNodeId, setEmailSubjectSourceNodeId] = useState(
		emailConfig.email_subject_source_node_id,
	);
	const [emailSubjectFieldPath, setEmailSubjectFieldPath] = useState(
		emailConfig.email_subject_field_path,
	);

	// Email body template with source configuration
	const [emailBodyTemplate, setEmailBodyTemplate] = useState(
		emailConfig.email_body_template ||
			"Please respond to this email to continue the workflow.\n\nInput from previous step:\n{{input}}",
	);
	const [emailBodySourceMode, setEmailBodySourceMode] = useState(
		emailConfig.email_body_source_mode || "static",
	);
	const [emailBodySourceNodeId, setEmailBodySourceNodeId] = useState(
		emailConfig.email_body_source_node_id,
	);
	const [emailBodyFieldPath, setEmailBodyFieldPath] = useState(
		emailConfig.email_body_field_path,
	);

	const [extractMode, setExtractMode] = useState(
		node?.data?.checkpoint_config?.email_config?.extract_mode || "full_body",
	);
	const [extractionPattern, setExtractionPattern] = useState(
		node?.data?.checkpoint_config?.email_config?.extraction_pattern || "",
	);
	const [timeoutMinutes, setTimeoutMinutes] = useState(
		node?.data?.checkpoint_config?.email_config?.timeout_minutes || 60,
	);

	// Tab configuration
	const tabs = useMemo(
		() => [
			{
				id: "manual" as CheckpointTabId,
				label: "Manual",
				description: "Human review input",
				icon: <AlertCircle className="h-4 w-4" />,
				accent: "core" as const,
			},
			{
				id: "email" as CheckpointTabId,
				label: "Email (Coming Soon)",
				description: "Await email response - Coming Soon",
				icon: <Mail className="h-4 w-4" />,
				accent: "input" as const,
				disabled: true,
			},
		],
		[],
	);

	// Memoized callback functions
	const handlePromptChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setPrompt(e.target.value);
		},
		[],
	);

	const handleRecipientEmailChange = useCallback(
		(config: InputSourceConfig) => {
			setRecipientEmail(config.value || "");
			setRecipientEmailSourceMode(config.source_mode);
			setRecipientEmailSourceNodeId(config.source_node_id);
			setRecipientEmailFieldPath(config.field_path);
		},
		[],
	);

	const handleEmailSubjectChange = useCallback((config: InputSourceConfig) => {
		setEmailSubject(config.value || "");
		setEmailSubjectSourceMode(config.source_mode);
		setEmailSubjectSourceNodeId(config.source_node_id);
		setEmailSubjectFieldPath(config.field_path);
	}, []);

	const handleEmailBodyChange = useCallback((config: InputSourceConfig) => {
		setEmailBodyTemplate(config.value || "");
		setEmailBodySourceMode(config.source_mode);
		setEmailBodySourceNodeId(config.source_node_id);
		setEmailBodyFieldPath(config.field_path);
	}, []);

	const handleExtractModeChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			setExtractMode(e.target.value);
		},
		[],
	);

	const handleExtractionPatternChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setExtractionPattern(e.target.value);
		},
		[],
	);

	const handleTimeoutChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setTimeoutMinutes(parseInt(e.target.value) || 60);
		},
		[],
	);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleSave = async () => {
		setSaving(true);
		try {
			const checkpointConfig: any = {
				prompt,
				require_input: true,
				timeout_seconds: activeTab === "email" ? timeoutMinutes * 60 : null,
				default_value: "",
				await_mode: activeTab,
			};

			if (activeTab === "email") {
				checkpointConfig.email_config = {
					enabled: true,
					email_provider: "mailslurp",
					send_email: true,
					recipient_email: recipientEmail,
					recipient_email_source_mode: recipientEmailSourceMode,
					recipient_email_source_node_id: recipientEmailSourceNodeId,
					recipient_email_field_path: recipientEmailFieldPath,
					email_subject:
						emailSubject ||
						`Action Required: ${node?.data?.name || "Checkpoint"}`,
					email_subject_source_mode: emailSubjectSourceMode,
					email_subject_source_node_id: emailSubjectSourceNodeId,
					email_subject_field_path: emailSubjectFieldPath,
					email_body_template: emailBodyTemplate,
					email_body_source_mode: emailBodySourceMode,
					email_body_source_node_id: emailBodySourceNodeId,
					email_body_field_path: emailBodyFieldPath,
					await_reply: true,
					extract_mode: extractMode,
					extraction_pattern: extractionPattern,
					timeout_minutes: timeoutMinutes,
				};
			}

			await updateNode(nodeId, {
				checkpoint_config: checkpointConfig,
			} as any);
			onClose();
		} catch (e) {
			console.error("Failed to save checkpoint config", e);
		} finally {
			setSaving(false);
		}
	};

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center overflow-y-auto bg-black/50 p-4 pb-8 pt-[5vh] backdrop-blur-sm sm:pt-16"
			onClick={handleBackdropClick}
		>
			<div
				className="mb-8 flex max-h-[calc(100vh-4rem)] w-full max-w-5xl flex-col overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)] sm:max-h-[calc(100vh-8rem)]"
				onClick={handleStopPropagation}
			>
				<div className="flex-none border-b border-gray-200 bg-white">
					<div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between sm:p-6">
						<div className="flex min-w-0 flex-1 items-start gap-3">
							<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
								<AlertCircle className="h-5 w-5 text-orange-600" />
							</div>
							<div className="min-w-0">
								<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
									Tool configuration
								</p>
								<h2 className="text-lg font-semibold tracking-tight text-gray-900">
									Checkpoint Configuration
								</h2>
								<p className="mt-0.5 max-w-xl text-sm text-gray-600">
									Pause workflow execution for human review or external input
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

				<div className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-6 py-5 sm:px-8">
					<div className="space-y-6">
						<div className="flex flex-wrap gap-2 rounded-[4px] border border-gray-200 bg-white p-1 shadow-sm">
							{tabs.map((t: any) => {
								const isOn = activeTab === t.id;
								const isDisabled = t.disabled || false;
								return (
									<button
										key={t.id}
										type="button"
										onClick={() => !isDisabled && setActiveTab(t.id)}
										disabled={isDisabled}
										className={cn(
											"flex flex-1 items-center justify-center gap-2 rounded-[4px] px-4 py-2.5 text-left text-sm font-medium transition-colors sm:min-w-[140px]",
											isDisabled
												? "cursor-not-allowed border border-gray-200 bg-gray-50 text-gray-400"
												: isOn
													? "border-2 border-orange-500 bg-white text-gray-900 shadow-sm"
													: "border border-transparent text-gray-600 hover:bg-slate-50 hover:text-slate-900",
										)}
									>
										<span
											className={
												t.id === "manual" ? "text-orange-600" : "text-sky-700"
											}
										>
											{t.icon}
										</span>
										<span className="text-gray-900">{t.label}</span>
									</button>
								);
							})}
						</div>

						{activeTab === "manual" && (
							<div className="space-y-6">
								<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
									<label
										htmlFor="checkpoint-prompt-textarea"
										className="mb-3 block text-xs font-semibold capitalize tracking-wide text-gray-800"
									>
										Checkpoint Prompt
									</label>
									<textarea
										id="checkpoint-prompt-textarea"
										value={prompt}
										onChange={handlePromptChange}
										className="min-h-[120px] w-full resize-y rounded-[4px] border border-gray-200 bg-white px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
										placeholder="Enter the prompt to display when the checkpoint is reached..."
									/>
									<p className="mt-3 text-xs text-gray-600">
										This message will be shown to users when the workflow pauses
										at this checkpoint
									</p>
								</div>

								<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
									<div className="flex items-start gap-4">
										<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
											<Info className="h-5 w-5 text-orange-600" />
										</div>
										<div className="min-w-0 space-y-2">
											<h4 className="text-sm font-semibold text-gray-900">
												How Manual Checkpoints Work
											</h4>
											<p className="text-xs leading-relaxed text-gray-600">
												Checkpoints pause workflow execution and wait for human
												input before continuing. When the workflow reaches this
												checkpoint, it will pause and display a prompt in the
												execution panel.
											</p>
											<p className="text-xs leading-relaxed text-gray-600">
												The workflow will remain paused until you provide input
												through the execution panel&apos;s resume interface.
											</p>
										</div>
									</div>
								</div>
							</div>
						)}

						{activeTab === "email" && (
							<div className="space-y-6">
								{/* QUICK FIX: Email checkpoint feature disabled pending security review */}
								<div className="rounded-[4px] border border-amber-200 bg-amber-50 p-5 shadow-sm">
									<div className="flex items-start gap-3">
										<Clock className="h-5 w-5 shrink-0 text-amber-600 mt-0.5" />
										<div className="min-w-0 space-y-2">
											<h4 className="font-semibold text-amber-900">
												Email Checkpoints - Coming Soon
											</h4>
											<p className="text-sm text-amber-800 leading-relaxed">
												Email-based checkpoint approvals are temporarily disabled while we enhance security measures. We're working to add sender verification and authorization controls to ensure your workflows are protected.
											</p>
											<p className="text-sm text-amber-800 leading-relaxed">
												Please use Manual Checkpoints in the meantime. We'll notify you when Email Checkpoints are available.
											</p>
										</div>
									</div>
								</div>
							</div>
						)}
					</div>
				</div>

				<div className="border-t border-gray-200 bg-white px-6 py-4 sm:px-8">
					<div className="flex items-center justify-end gap-3">
						<button
							type="button"
							onClick={onClose}
							className="rounded-[4px] border border-gray-200 bg-white px-6 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleSave}
							disabled={saving}
							className="rounded-[4px] bg-orange-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						>
							{saving ? (
								<span className="inline-flex items-center gap-2">
									<span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
									Saving...
								</span>
							) : (
								<span className="inline-flex items-center gap-2">
									<Save className="h-4 w-4" />
									Save Changes
								</span>
							)}
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
