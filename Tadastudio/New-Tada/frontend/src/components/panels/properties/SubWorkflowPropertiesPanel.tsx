import { GitBranch, Info, Save, Share2, Trash2, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Node } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import { api } from "@/lib/api";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import FormTextarea from "@/components/ui/FormTextarea";
import SearchablePicker, {
	type PickerOption,
} from "@/components/panels/properties/sections/SearchablePicker";
import type { SubWorkflowConfig } from "@/types/nodes";

interface SubWorkflowPropertiesPanelProps {
	node: Node;
	onUpdateNode: (nodeId: string, data: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

interface WorkflowOption {
	workflow_id: string;
	name: string;
	workflow_role?: string;
	owner_name?: string;
}

export default function SubWorkflowPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: SubWorkflowPropertiesPanelProps) {
	const { currentGraph } = useGraph();

	const emptyConfig: SubWorkflowConfig = {
		workflow_name: "",
		delegation_description: "",
		timeout: 600,
		share_context: true,
		max_retries: 1,
		allow_parallel_execution: false,
		cache_results: false,
		cache_ttl: 3600,
	};

	const [savedConfig, setSavedConfig] = useState<SubWorkflowConfig>(
		node.data.subworkflow_config || emptyConfig,
	);
	const [config, setConfig] = useState<SubWorkflowConfig>(
		node.data.subworkflow_config || emptyConfig,
	);
	const [workflowOptions, setWorkflowOptions] = useState<WorkflowOption[]>([]);
	const [loadingWorkflows, setLoadingWorkflows] = useState(false);
	const [isDirty, setIsDirty] = useState(false);

	useEffect(() => {
		const base = node.data.subworkflow_config || emptyConfig;
		setSavedConfig(base);
		setConfig(base);
		setIsDirty(false);
	}, [node.id, node.data.subworkflow_config]);

	useEffect(() => {
		let isActive = true;
		const loadWorkflows = async () => {
			try {
				setLoadingWorkflows(true);
				const response = await api.listGraphs();
				if (!response?.success || !Array.isArray(response.graphs)) return;

				const currentWorkflowId = currentGraph?.workflow_id || null;
				const options = response.graphs
					.filter(
						(wf: WorkflowOption) =>
							!!wf.workflow_id && wf.workflow_id !== currentWorkflowId,
					)
					.map((wf: WorkflowOption) => ({
						workflow_id: wf.workflow_id,
						name: wf.name,
						workflow_role: wf.workflow_role,
						owner_name: wf.owner_name,
					}));

				if (isActive) {
					setWorkflowOptions(options);
				}
			} finally {
				if (isActive) setLoadingWorkflows(false);
			}
		};

		loadWorkflows();
		return () => {
			isActive = false;
		};
	}, [currentGraph?.workflow_id]);

	const handleSave = () => {
		onUpdateNode(node.id, {
			...node.data,
			subworkflow_config: config,
		});
		setSavedConfig(config);
		setIsDirty(false);
		onClose();
	};

	const handleConfigChange = useCallback((field: keyof SubWorkflowConfig, value: any) => {
		setConfig((prev) => ({ ...prev, [field]: value }));
		setIsDirty(true);
	}, []);

	// Cancel — revert all unsaved changes back to last saved state
	const handleCancel = useCallback(() => {
		setConfig(savedConfig);
		setIsDirty(false);
		onClose();
	}, [savedConfig, onClose]);

	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	const handleDelete = () => {
		setShowDeleteConfirm(true);
	};

	const handleConfirmDelete = () => {
		onDeleteNode(node.id);
		onClose();
	};

	const handleBackdropClick = useCallback(() => {
		handleCancel();
	}, [handleCancel]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleDelegationDescriptionChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			handleConfigChange("delegation_description", e.target.value);
		},
		[handleConfigChange],
	);

	const handleWorkflowSelectionChange = useCallback(
		(selectedWorkflowId: string) => {
			const selectedWorkflow = workflowOptions.find(
				(wf) => wf.workflow_id === selectedWorkflowId,
			);
			setConfig((prev) => ({
				...prev,
				target_workflow_id: selectedWorkflowId || undefined,
				workflow_name: selectedWorkflow?.name || prev.workflow_name,
			}));
			setIsDirty(true);
		},
		[workflowOptions],
	);

	// Temporarily disabled (commented out per request):
	// const handleTimeoutChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		handleConfigChange("timeout", parseInt(e.target.value) || 600);
	// 	},
	// 	[handleConfigChange],
	// );
	//
	// const handleShareContextChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		handleConfigChange("share_context", e.target.checked);
	// 	},
	// 	[handleConfigChange],
	// );
	//
	// const handleMaxRetriesChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		handleConfigChange("max_retries", parseInt(e.target.value) || 1);
	// 	},
	// 	[handleConfigChange],
	// );
	//
	// const handleAllowParallelChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		handleConfigChange("allow_parallel_execution", e.target.checked);
	// 	},
	// 	[handleConfigChange],
	// );
	//
	// const handleCacheResultsChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		handleConfigChange("cache_results", e.target.checked);
	// 	},
	// 	[handleConfigChange],
	// );
	//
	// const handleCacheTtlChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		handleConfigChange("cache_ttl", parseInt(e.target.value) || 3600);
	// 	},
	// 	[handleConfigChange],
	// );

	const missingSelectedWorkflow =
		config.target_workflow_id &&
		!workflowOptions.some((wf) => wf.workflow_id === config.target_workflow_id);

	const workflowDropdownOptions = useMemo<PickerOption[]>(() => {
		const options: PickerOption[] = workflowOptions.map((wf) => {
			const sharedByOther = wf.workflow_role && wf.workflow_role !== "owner";
			const sharedTooltip = `Shared by ${wf.owner_name || "Unknown"}`;
			return {
				value: wf.workflow_id,
				label: wf.name,
				icon: sharedByOther ? <Share2 className="h-3.5 w-3.5" /> : undefined,
				iconTooltip: sharedByOther ? sharedTooltip : undefined,
				description: sharedByOther ? sharedTooltip : undefined,
			};
		});

		if (missingSelectedWorkflow && config.target_workflow_id) {
			options.unshift({
				value: config.target_workflow_id,
				label:
					config.workflow_name || "Previously selected workflow (no longer available)",
				description: "No longer available",
				disabled: true,
			});
		}

		return options;
	}, [
		workflowOptions,
		missingSelectedWorkflow,
		config.target_workflow_id,
		config.workflow_name,
	]);

	return (
		<div
			className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-start justify-center z-[100] animate-fadeIn pt-[5vh]"
			onClick={handleBackdropClick}
		>
			<div
				className="bg-[color:var(--color-bg-secondary)] rounded-xl shadow-2xl max-w-2xl w-full mx-4 min-h-[320px] max-h-[85vh] overflow-hidden flex flex-col animate-scaleIn"
				onClick={handleStopPropagation}
			>
				{/* Header */}
				<div className="flex-none p-4 border-b border-[color:var(--color-border)] bg-gradient-to-r from-teal-600/10 to-cyan-600/10">
					<div className="flex items-center justify-between">
						<div className="flex items-center gap-3">
							<div className="p-2 bg-teal-500/20 rounded-lg">
								<GitBranch className="w-5 h-5 text-teal-400" />
							</div>
							<div>
								<h2 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
									Sub-Workflow Properties
								</h2>
								<p className="text-sm text-[color:var(--color-text-muted)]">
									Configure workflow execution settings
								</p>
							</div>
						</div>
						<button
								onClick={handleCancel}
							className="p-1.5 hover:bg-[color:var(--color-border)] rounded-lg transition-colors"
						>
							<X className="w-4 h-4 text-[color:var(--color-text-muted)]" />
						</button>
					</div>
				</div>

				{/* Content */}
				<div className="flex-1 overflow-y-auto p-4 min-h-0">
					<div className="space-y-4">
						{/* Basic Information */}
						<div className="bg-[color:var(--color-surface)]/50 rounded-lg p-4 border border-[color:var(--color-border)]">
							<h3 className="text-sm font-medium text-[color:var(--color-text-primary)] mb-3 flex items-center gap-2">
								<Info className="w-4 h-4 text-teal-400" />
								Basic Information
							</h3>

							<div className="space-y-3">
								<div>
									<label className="block text-xs font-medium text-[color:var(--color-text-secondary)] mb-1">
										Workflow Name
									</label>
									<SearchablePicker
										variant="dark"
										value={config.target_workflow_id || ""}
										onChange={handleWorkflowSelectionChange}
										options={workflowDropdownOptions}
										placeholder={
											loadingWorkflows
												? "Loading workflows..."
													: "No workflow selected"
										}
										searchPlaceholder="Search workflow..."
										emptyMessage="No workflows found"
											disabled={loadingWorkflows}
										maxVisibleOptions={10}
										accentColor="#14b8a6"
									/>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
										Shows workflows from Manage; excludes current workflow.
										Dropdown shows up to 10 items at once with scroll.
									</p>
								</div>

								<FormTextarea
									label="Delegation Description"
									value={config.delegation_description || ""}
									onChange={handleDelegationDescriptionChange}
									placeholder="Describe when the agent should trigger this workflow..."
									rows={3}
								/>
							</div>

							{/* Temporarily disabled (commented out per request):
							<div className="bg-[color:var(--color-surface)]/50 rounded-lg p-4 border border-[color:var(--color-border)]">
								<h3 className="text-sm font-medium text-slate-900 mb-3 flex items-center gap-2">
									Execution Settings
								</h3>

								<div className="space-y-3">
									<div>
										<label className="block text-xs font-medium text-[color:var(--color-text-secondary)] mb-1">
											Timeout (seconds)
										</label>
										<input
											type="number"
											value={config.timeout || 600}
											onChange={handleTimeoutChange}
											min="60"
											max="3600"
											className="w-full px-3 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-teal-500 focus:outline-none"
										/>
									</div>

									<div>
										<label className="block text-xs font-medium text-[color:var(--color-text-secondary)] mb-1">
											Max Retries
										</label>
										<input
											type="number"
											value={config.max_retries || 1}
											onChange={handleMaxRetriesChange}
											min="0"
											max="5"
											className="w-full px-3 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-teal-500 focus:outline-none"
										/>
									</div>

									<label className="flex items-center gap-2 cursor-pointer">
										<input
											type="checkbox"
											checked={config.share_context !== false}
											onChange={handleShareContextChange}
											className="w-4 h-4 text-teal-500 bg-[color:var(--color-bg-secondary)] border-[color:var(--color-border)] rounded focus:ring-teal-500"
										/>
										<span className="text-sm text-[color:var(--color-text-secondary)]">
											Share Execution Context
										</span>
									</label>

									<label className="flex items-center gap-2 cursor-pointer">
										<input
											type="checkbox"
											checked={config.allow_parallel_execution || false}
											onChange={handleAllowParallelChange}
											className="w-4 h-4 text-teal-500 bg-[color:var(--color-bg-secondary)] border-[color:var(--color-border)] rounded focus:ring-teal-500"
										/>
										<span className="text-sm text-[color:var(--color-text-secondary)]">
											Allow parallel execution
										</span>
									</label>
								</div>
							</div>

							<div className="bg-[color:var(--color-surface)]/50 rounded-lg p-4 border border-[color:var(--color-border)]">
								<h3 className="text-sm font-medium text-slate-900 mb-3">
									Caching Settings
								</h3>
								<label className="flex items-center gap-2 cursor-pointer">
									<input
										type="checkbox"
										checked={config.cache_results || false}
										onChange={handleCacheResultsChange}
										className="w-4 h-4 text-teal-500 bg-[color:var(--color-bg-secondary)] border-[color:var(--color-border)] rounded focus:ring-teal-500"
									/>
									<span className="text-sm text-[color:var(--color-text-secondary)]">
										Cache results for identical inputs
									</span>
								</label>
								{config.cache_results && (
									<input
										type="number"
										value={config.cache_ttl || 3600}
										onChange={handleCacheTtlChange}
										min="60"
										max="86400"
										className="w-full mt-2 px-3 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-teal-500 focus:outline-none"
									/>
								)}
							</div>

							<div className="bg-cyan-500/5 border border-cyan-500/20 rounded-lg p-4">
								<h3 className="text-sm font-medium text-cyan-600 mb-2">
									Workflow Structure
								</h3>
								<ul className="text-xs text-cyan-600/80 space-y-1">
									<li>• This node acts as the START point for the workflow</li>
									<li>• Connect workflow nodes from the bottom handle</li>
									<li>• The workflow must end with an END node</li>
									<li>• The agent will receive the END node&apos;s output</li>
								</ul>
							</div>
							*/}
						</div>
					</div>
				</div>

				{/* Footer */}
				<div className="flex-none p-4 border-t border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)] flex items-center justify-between">
					<Button
						onClick={handleDelete}
						variant="danger"
						icon={<Trash2 className="w-4 h-4" />}
					>
						Delete
					</Button>

					<div className="flex items-center gap-2">
							<Button onClick={handleCancel} variant="secondary">
							Cancel
						</Button>
						<Button
							onClick={handleSave}
							icon={<Save className="w-4 h-4" />}
								disabled={!isDirty || !config.target_workflow_id}
								title={!config.target_workflow_id ? "Select a workflow before saving" : undefined}
							>
								Save Changes
							</Button>
						</div>
				</div>
			</div>

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				onClose={() => setShowDeleteConfirm(false)}
				onConfirm={handleConfirmDelete}
				title="Delete Sub-Workflow?"
				message={`Are you sure you want to delete the sub-workflow "${node.data?.name || "Sub-Workflow"}"? This action cannot be undone.`}
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
