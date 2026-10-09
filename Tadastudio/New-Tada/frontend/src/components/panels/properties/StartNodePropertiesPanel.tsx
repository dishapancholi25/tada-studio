"use client";

import { PlayCircle, X } from "lucide-react";
import { useCallback, useState } from "react";
import type { Node } from "reactflow";

import AssignmentList from "@/components/core/guardrails/AssignmentList";
import EffectiveConfigPreview from "@/components/core/guardrails/EffectiveConfigPreview";
import GuardrailsPanel from "@/components/core/guardrails/GuardrailsPanel";
import PolicyPicker from "@/components/core/guardrails/PolicyPicker";
import { useGraph } from "@/contexts/GraphContext";
import Button from "../../ui/Button";

interface StartNodePropertiesPanelProps {
	node: Node;
	onUpdate: (
		nodeId: string,
		updates: Record<string, unknown>,
	) => Promise<void> | void;
	onClose: () => void;
}

export default function StartNodePropertiesPanel({
	node: _node,
	onUpdate: _onUpdate,
	onClose,
}: StartNodePropertiesPanelProps) {
	const { currentGraph } = useGraph();
	const workflowId = currentGraph?.workflow_id;
	const [showPolicyPicker, setShowPolicyPicker] = useState(false);
	const [assignmentRefresh, setAssignmentRefresh] = useState(0);
	const [guardrailsEnabled, setGuardrailsEnabled] = useState(true);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleModalClick = useCallback((event: React.MouseEvent) => {
		event.stopPropagation();
	}, []);

	const handleClose = useCallback(() => {
		onClose();
	}, [onClose]);

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center overflow-y-auto bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="mb-8 w-full max-w-2xl sm:mb-16 lg:mb-20"
				onClick={handleModalClick}
			>
				<div className="flex max-h-[85vh] flex-col overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]">
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex flex-wrap items-start justify-between gap-4 px-6 pb-4 pt-5">
							<div className="flex min-w-0 items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<PlayCircle
										className="h-5 w-5 text-orange-600"
										aria-hidden
									/>
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Node configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										Start Node
									</h2>
									<p className="mt-0.5 text-sm text-gray-600">
										Workflow entry and guardrail policies
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={handleClose}
								className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					<div className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-6 py-6">
						<div className="space-y-6">
							<div className="rounded-[4px] border border-gray-200 bg-white p-5 shadow-sm">
								<p className="text-sm text-gray-800">
									Click on the node name in the workflow canvas to edit it
									inline.
								</p>
								<p className="mt-3 text-xs italic text-gray-600">
									This node marks the entry point of your workflow.
								</p>
							</div>

							{workflowId && (
								<GuardrailsPanel
									enabled={guardrailsEnabled}
									onToggle={setGuardrailsEnabled}
									onAssign={() => setShowPolicyPicker(true)}
									description="Policies assigned here apply to all nodes in this workflow."
								>
									<AssignmentList
										targetType="workflow"
										targetId={workflowId}
										onOpenPolicyPicker={() => setShowPolicyPicker(true)}
										refreshTrigger={assignmentRefresh}
										hideHeader
									/>
									<EffectiveConfigPreview workflowId={workflowId} />
									{showPolicyPicker && (
										<PolicyPicker
											targetType="workflow"
											targetId={workflowId}
											workflowId={workflowId}
											onAssigned={() => {
												setShowPolicyPicker(false);
												setAssignmentRefresh((c) => c + 1);
											}}
											onClose={() => setShowPolicyPicker(false)}
										/>
									)}
								</GuardrailsPanel>
							)}
						</div>
					</div>

					<div className="flex-none border-t border-gray-200 bg-white px-6 py-4">
						<div className="flex justify-end">
							<Button onClick={handleClose} variant="primary" size="md">
								Close
							</Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
