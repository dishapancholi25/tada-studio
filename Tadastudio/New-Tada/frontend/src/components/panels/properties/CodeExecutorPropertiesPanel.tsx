"use client";

import { Code2, Play, Save, Trash2, Variable, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Node } from "reactflow";
import { useToast } from "@/contexts/ToastContext";
import type { CodeExecutorConfig, InputVariableMapping } from "@/types/nodes";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ConfigSidebar from "./ConfigSidebar";
import CodeEditorSection from "./sections/CodeEditorSection";
import CodeExecutionSection from "./sections/CodeExecutionSection";
import CodeVariablesSection from "./sections/CodeVariablesSection";

interface CodeExecutorPropertiesPanelProps {
	node: Node;
	onUpdateNode: (nodeId: string, data: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

const DEFAULT_PYTHON_CODE = `# Your Python code here
# Input variables are available directly by name
# Set the output variable (default: result) with your return value

result = "Hello, World!"
`;

type CodeExecutorTabId = "code" | "variables" | "execution";

export default function CodeExecutorPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: CodeExecutorPropertiesPanelProps) {
	const { showSuccess, showError } = useToast();
	const [hasChanges, setHasChanges] = useState(false);
	const [saving, setSaving] = useState(false);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
	const [activeTab, setActiveTab] = useState<CodeExecutorTabId>("code");
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const contentRef = useRef<HTMLDivElement>(null);

	const [config, setConfig] = useState<CodeExecutorConfig>(
		node.data.code_executor_config || {
			language: "python",
			code: DEFAULT_PYTHON_CODE,
			timeout_seconds: 30,
			memory_limit_mb: 256,
			allow_network: true,
			allow_filesystem: true,
			allow_subprocess: false,
			allowed_packages: [],
			input_variables: [],
			output_variable: "result",
			working_directory: "",
			environment_variables: {},
			capture_stdout: true,
			capture_stderr: true,
		}
	);

	useEffect(() => {
		if (node.data.code_executor_config) {
			setConfig(node.data.code_executor_config);
		}
	}, [node.data.code_executor_config]);

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

	// Track changes
	useEffect(() => {
		const originalConfig = node.data.code_executor_config || {};
		const hasConfigChanges =
			JSON.stringify(config) !== JSON.stringify(originalConfig);
		setHasChanges(hasConfigChanges);
	}, [config, node.data.code_executor_config]);

	const handleSave = async () => {
		setSaving(true);
		try {
			await onUpdateNode(node.id, {
				...node.data,
				code_executor_config: config,
			});
			showSuccess("Code Executor configuration saved");
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

	const handleConfigChange = useCallback(
		<K extends keyof CodeExecutorConfig>(field: K, value: CodeExecutorConfig[K]) => {
			setConfig((prev) => ({ ...prev, [field]: value }));
		},
		[]
	);

	const handleDeleteAndClose = useCallback(() => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [node.id, onDeleteNode, onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const codeExecutorTabs = [
		{
			id: "code" as CodeExecutorTabId,
			label: "Code",
			description: "Language & editor",
			icon: <Code2 className="h-4 w-4" />,
		},
		{
			id: "variables" as CodeExecutorTabId,
			label: "Variables",
			description: "Input mappings",
			icon: <Variable className="h-4 w-4" />,
		},
		{
			id: "execution" as CodeExecutorTabId,
			label: "Execution",
			description: "Settings & permissions",
			icon: <Play className="h-4 w-4" />,
		},
	];

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
					<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-emerald-500/60" />

					{/* Header */}
					<div className="relative flex-none border-b border-slate-200 bg-white">
						<div className="flex items-center justify-between px-6 py-4">
							<div className="flex items-center gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-200 bg-emerald-100">
									<Code2 className="h-5 w-5 text-emerald-600" aria-hidden />
								</div>
								<div>
									<h2 className="text-lg font-semibold tracking-tight text-slate-900">
										Code Executor Configuration
									</h2>
									<p className="mt-0.5 text-sm text-slate-500">
										Run Python or JavaScript code in your workflow
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-emerald-400 hover:text-emerald-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/25"
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
							items={codeExecutorTabs}
							activeItem={activeTab}
							onChange={(id) => setActiveTab(id as CodeExecutorTabId)}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div className="custom-scrollbar flex-1 space-y-6 overflow-y-auto bg-white px-6 py-5">
							{activeTab === "code" && (
								<CodeEditorSection
									language={config.language || "python"}
									onLanguageChange={(lang) => handleConfigChange("language", lang)}
									code={config.code || ""}
									onCodeChange={(code) => handleConfigChange("code", code)}
									outputVariable={config.output_variable || "result"}
								/>
							)}

							{activeTab === "variables" && (
								<CodeVariablesSection
									variables={config.input_variables || []}
									onVariablesChange={(vars) =>
										handleConfigChange("input_variables", vars)
									}
								/>
							)}

							{activeTab === "execution" && (
								<CodeExecutionSection
									outputVariable={config.output_variable || "result"}
									onOutputVariableChange={(val) =>
										handleConfigChange("output_variable", val)
									}
									timeoutSeconds={config.timeout_seconds || 30}
									onTimeoutSecondsChange={(val) =>
										handleConfigChange("timeout_seconds", val)
									}
									memoryLimitMb={config.memory_limit_mb || 256}
									onMemoryLimitMbChange={(val) =>
										handleConfigChange("memory_limit_mb", val)
									}
									workingDirectory={config.working_directory || ""}
									onWorkingDirectoryChange={(val) =>
										handleConfigChange("working_directory", val)
									}
									allowNetwork={config.allow_network ?? true}
									onAllowNetworkChange={(val) =>
										handleConfigChange("allow_network", val)
									}
									allowFilesystem={config.allow_filesystem ?? true}
									onAllowFilesystemChange={(val) =>
										handleConfigChange("allow_filesystem", val)
									}
									allowSubprocess={config.allow_subprocess ?? false}
									onAllowSubprocessChange={(val) =>
										handleConfigChange("allow_subprocess", val)
									}
									captureStdout={config.capture_stdout ?? true}
									onCaptureStdoutChange={(val) =>
										handleConfigChange("capture_stdout", val)
									}
									captureStderr={config.capture_stderr ?? true}
									onCaptureStderrChange={(val) =>
										handleConfigChange("capture_stderr", val)
									}
								/>
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
										<span className="h-1.5 w-1.5 animate-smoothPulse rounded-full bg-emerald-500" />
										Unsaved
									</span>
								)}
								<span className="hidden text-[11px] text-slate-400 sm:inline">
									{"⌘"}S to save
								</span>
								<button
									type="button"
									onClick={onClose}
									className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs text-slate-700 transition-colors hover:border-emerald-400 hover:text-emerald-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/25"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleSave}
									disabled={saving || !hasChanges}
									className="inline-flex items-center gap-1.5 rounded-[4px] border border-emerald-500 bg-emerald-500 px-5 py-2 text-xs font-medium text-white transition-colors hover:border-emerald-600 hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/25"
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
}
