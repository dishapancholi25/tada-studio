import { GitBranch, Info, Share2, Workflow, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useGraph } from "@/contexts/GraphContext";
import { api } from "@/lib/api";
import Button from "@/components/ui/Button";
import FormTextarea from "@/components/ui/FormTextarea";
import SearchablePicker, {
	type PickerOption,
} from "@/components/panels/properties/sections/SearchablePicker";
import { cn } from "@/lib/utils";

interface CreateSubWorkflowDialogProps {
	isOpen: boolean;
	onClose: () => void;
	onConfirm: (
		name: string,
		delegationDescription: string,
		targetWorkflowId?: string,
	) => void;
	parentAgentName: string;
}

const fieldClass =
	"!border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-slate-300 focus:!border-orange-500 focus:!ring-orange-500/20";

interface WorkflowOption {
	workflow_id: string;
	name: string;
	workflow_role?: string;
	owner_name?: string;
}

export default function CreateSubWorkflowDialog({
	isOpen,
	onClose,
	onConfirm,
	parentAgentName,
}: CreateSubWorkflowDialogProps) {
	const { currentGraph } = useGraph();
	const [selectedWorkflowId, setSelectedWorkflowId] = useState("");
	const [delegationDescription, setDelegationDescription] = useState("");
	const [workflowOptions, setWorkflowOptions] = useState<WorkflowOption[]>([]);
	const [loadingWorkflows, setLoadingWorkflows] = useState(false);
	// Temporarily disabled (commented out per request):
	// const [timeout, setTimeout] = useState(600);
	// const [shareContext, setShareContext] = useState(true);
	const [mounted, setMounted] = useState(false);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEffect(() => {
		if (!isOpen) return;

		let isActive = true;
		const loadWorkflows = async () => {
			try {
				setLoadingWorkflows(true);
				const response = await api.listGraphs();
				if (!response?.success || !Array.isArray(response.graphs)) return;

				const currentWorkflowId = currentGraph?.workflow_id || null;
				const options: WorkflowOption[] = response.graphs
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
					// Do not auto-select — user must explicitly choose a workflow
				}
			} finally {
				if (isActive) setLoadingWorkflows(false);
			}
		};

		loadWorkflows();
		return () => {
			isActive = false;
		};
	}, [isOpen, currentGraph?.workflow_id]);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		const selectedWorkflow = workflowOptions.find(
			(wf) => wf.workflow_id === selectedWorkflowId,
		);
		if (selectedWorkflow && delegationDescription.trim()) {
			onConfirm(
				selectedWorkflow.name,
				delegationDescription.trim(),
				selectedWorkflow.workflow_id,
			);
			// State reset is handled by the useEffect watching isOpen
		}
	};

	const suggestedDescriptions = [
		"Execute a multi-step data processing workflow",
		"Run a complex validation and verification process",
		"Perform sequential operations with conditional logic",
		"Handle document processing and extraction pipeline",
		"Execute parallel tasks and aggregate results",
		"Run a complete end-to-end business process",
	];

	const resetForm = useCallback(() => {
		setSelectedWorkflowId("");
		setDelegationDescription("");
	}, []);

	// Reset form whenever dialog closes
	useEffect(() => {
		if (!isOpen) resetForm();
	}, [isOpen, resetForm]);

	const handleClose = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleDialogClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleWorkflowChange = useCallback((value: string) => {
		setSelectedWorkflowId(value);
	}, []);

	const handleDescriptionChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setDelegationDescription(e.target.value);
		},
		[],
	);

	const createSuggestionHandler = useCallback(
		(desc: string) => () => {
			setDelegationDescription(desc);
		},
		[],
	);

	// Temporarily disabled (commented out per request):
	// const handleTimeoutChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		setTimeout(Math.max(60, parseInt(e.target.value) || 600));
	// 	},
	// 	[],
	// );
	//
	// const handleShareContextChange = useCallback(
	// 	(e: React.ChangeEvent<HTMLInputElement>) => {
	// 		setShareContext(e.target.checked);
	// 	},
	// 	[],
	// );

	const workflowDropdownOptions = useMemo<PickerOption[]>(
		() =>
			workflowOptions.map((wf) => {
				const sharedByOther = wf.workflow_role && wf.workflow_role !== "owner";
				const sharedTooltip = `Shared by ${wf.owner_name || "Unknown"}`;
				return {
					value: wf.workflow_id,
					label: wf.name,
					icon: sharedByOther ? <Share2 className="h-3.5 w-3.5" /> : undefined,
					iconTooltip: sharedByOther ? sharedTooltip : undefined,
					description: sharedByOther ? sharedTooltip : undefined,
				};
			}),
		[workflowOptions],
	);

	if (!isOpen || !mounted) {
		return null;
	}

	return createPortal(
		<div
			className="fixed inset-0 z-[120] flex animate-fadeIn items-center justify-center bg-black/60 backdrop-blur-sm"
			onClick={handleClose}
			role="presentation"
		>
			<div
				className="relative mx-4 flex max-h-[90vh] w-full max-w-2xl animate-scaleIn flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]"
				onClick={handleDialogClick}
				role="dialog"
				aria-modal="true"
				aria-labelledby="sub-workflow-dialog-title"
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />

				{/* Header — Workflow Management style */}
				<div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<GitBranch className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div>
							<h2
								id="sub-workflow-dialog-title"
								className="text-lg font-semibold tracking-tight text-slate-900"
							>
								Create Sub-Workflow
							</h2>
							<p className="mt-0.5 text-sm text-slate-500">
								Add a workflow that{" "}
								<span className="font-medium text-orange-800">
									{parentAgentName}
								</span>{" "}
								can execute
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						aria-label="Close dialog"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto">
					<form
						id="create-sub-workflow-form"
						onSubmit={handleSubmit}
						className="space-y-6 p-6"
					>
						{/* Info Banner */}
						<div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-orange-200">
							<div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl border border-orange-200 bg-orange-100 text-orange-600">
								<Info className="h-5 w-5" />
							</div>
							<div>
								<p className="text-sm text-slate-800">
									Creating a sub-workflow for{" "}
									<span className="font-semibold text-orange-800">
										{parentAgentName}
									</span>
								</p>
								<p className="mt-1 text-xs text-slate-600">
									Sub-workflows are complete processes that agents can trigger as
									tools. Select an available workflow to execute.
								</p>
							</div>
						</div>

						<div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
							<label
								htmlFor="workflow-selection"
								className="mb-2 block text-xs font-semibold capitalize text-slate-600"
							>
								Workflow Name
							</label>
							<SearchablePicker
								variant="light"
								value={selectedWorkflowId}
								onChange={handleWorkflowChange}
								options={workflowDropdownOptions}
								placeholder={
									loadingWorkflows
										? "Loading workflows..."
											: "Select workflow..."
								}
								searchPlaceholder="Search workflow..."
								emptyMessage="No workflows found"
								disabled={loadingWorkflows || workflowDropdownOptions.length === 0}
								maxVisibleOptions={10}
								accentColor="#f97316"
							/>
							<p className="mt-2 text-xs text-slate-600">
								Shows workflows from Manage; excludes current workflow. Dropdown
								shows up to 10 items at once with scroll.
							</p>
						</div>

						<div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
							<FormTextarea
								label="Delegation Description"
								id="description"
								value={delegationDescription}
								onChange={handleDescriptionChange}
								placeholder="Describe what this workflow does and when the agent should trigger it..."
								rows={4}
								required
								className={fieldClass}
							/>
							<div className="mt-3">
								<p className="mb-2 text-[0.6rem] font-semibold capitalize text-slate-600">
									Suggestions
								</p>
								<div className="flex flex-wrap gap-2">
									{suggestedDescriptions.map((desc, index) => (
										<button
											key={`suggestion-${desc.substring(0, 30)}-${index}`}
											type="button"
											onClick={createSuggestionHandler(desc)}
											className={cn(
												"rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 transition-all duration-200",
												"hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900",
											)}
										>
											{desc.substring(0, 40)}...
										</button>
									))}
								</div>
							</div>
						</div>

						{/* Temporarily disabled (commented out per request):
						<div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
							<label
								htmlFor="timeout"
								className="mb-3 block text-xs font-semibold capitalize text-slate-600"
							>
								Execution Timeout
							</label>
							<div className="flex flex-wrap items-center gap-3">
								<input
									type="number"
									id="timeout"
									value={timeout}
									onChange={handleTimeoutChange}
									min="60"
									max="3600"
									step="60"
									className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-900 transition-all hover:border-slate-300 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/20"
								/>
								<span className="text-sm text-slate-600">seconds</span>
							</div>
						</div>

						<div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
							<label
								htmlFor="share-context-checkbox"
								className="group flex cursor-pointer items-center gap-4"
							>
								<div className="relative shrink-0">
									<input
										id="share-context-checkbox"
										type="checkbox"
										checked={shareContext}
										onChange={handleShareContextChange}
										className="sr-only"
									/>
								</div>
								<div>
									<span className="text-sm font-medium text-slate-800 transition-colors group-hover:text-slate-900">
										Share Execution Context
									</span>
								</div>
							</label>
						</div>
						*/}

						{/* Preview */}
						<div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
							<div className="mb-4 flex items-center gap-2 border-b border-slate-200 pb-3">
								<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-orange-200 bg-orange-100 text-orange-600">
									<Workflow className="h-4 w-4" />
								</div>
								<h3 className="text-xs font-semibold capitalize text-slate-700">
									Preview
								</h3>
							</div>
							<div className="space-y-3 text-sm">
								<div className="flex items-start gap-2">
									<span className="min-w-[80px] text-slate-500">Tool name:</span>
									<span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 font-mono text-xs text-blue-800">
										execute_
										{(workflowOptions.find((wf) => wf.workflow_id === selectedWorkflowId)?.name || "workflow")
											.toLowerCase()
											.replace(/\s+/g, "_")}
										_workflow
									</span>
								</div>
								<div className="flex items-start gap-2">
									<span className="min-w-[80px] text-slate-500">Description:</span>
									<span className="text-slate-800">
										{delegationDescription || "No description provided"}
									</span>
								</div>
							</div>
						</div>

						{/* Temporarily disabled (commented out per request):
						<div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
							<h3 className="mb-3 text-xs font-semibold capitalize text-slate-800">
								Workflow Structure
							</h3>
							<ul className="space-y-2 text-xs text-slate-700">
								<li className="flex items-start gap-2">
									<span className="mt-0.5 text-orange-600">•</span>
									<span>This node acts as the START point for the workflow</span>
								</li>
								<li className="flex items-start gap-2">
									<span className="mt-0.5 text-orange-600">•</span>
									<span>
										Connect workflow nodes (agents, tools, conditions) from the
										bottom handle
									</span>
								</li>
								<li className="flex items-start gap-2">
									<span className="mt-0.5 text-orange-600">•</span>
									<span>The workflow must end with an END node</span>
								</li>
								<li className="flex items-start gap-2">
									<span className="mt-0.5 text-orange-600">•</span>
									<span>
										The END node&apos;s output will be returned to the calling
										agent
									</span>
								</li>
							</ul>
						</div>
						*/}
					</form>
				</div>

				{/* Footer */}
				<div className="flex shrink-0 items-center justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
					<Button
						type="button"
						onClick={onClose}
						variant="ghost"
						className="!rounded-xl !border !border-slate-200 !bg-white !text-slate-700 hover:!border-orange-400 hover:!text-orange-800"
					>
						Cancel
					</Button>
					<Button
						type="submit"
						form="create-sub-workflow-form"
						onClick={handleSubmit}
						variant="primary"
						className="!rounded-[4px] !border !border-orange-500 !bg-orange-500 !text-white !shadow-md hover:!border-orange-600 hover:!bg-orange-600"
						icon={<GitBranch className="h-4 w-4" />}
						disabled={
							!selectedWorkflowId ||
							!delegationDescription.trim() ||
							workflowOptions.length === 0
						}
					>
						Create Sub-Workflow
					</Button>
				</div>
			</div>
		</div>,
		document.body,
	);
}
