"use client";

import React from "react";
import type { McpServerInfo } from "@/lib/user-settings-api";
import CreateSubAgentDialog from "../dialogs/CreateSubAgentDialog";
import CreateSubWorkflowDialog from "../dialogs/CreateSubWorkflowDialog";
import CreateToolNodeDialog from "../dialogs/CreateToolNodeDialog";
import EnhancedExecutionViewerModal from "../execution/EnhancedExecutionViewerModal";
import HiddenNodePalette from "../ui/HiddenNodePalette";

interface CreateDialogState {
	isOpen: boolean;
	parentAgentId: string;
	parentAgentName: string;
}

interface AgentBuilderModalsProps {
	// Create dialogs state
	createSubAgentDialog: CreateDialogState;
	createSubWorkflowDialog: CreateDialogState;
	createToolNodeDialog: CreateDialogState;

	// Create dialog handlers
	onCloseSubAgentDialog: () => void;
	onCloseSubWorkflowDialog: () => void;
	onCloseToolNodeDialog: () => void;
	onCreateSubAgent: (
		name: string,
		delegationDescription: string,
		agentTemplate?: string,
	) => void;
	onCreateSubWorkflow: (
		name: string,
		delegationDescription: string,
		targetWorkflowId?: string,
	) => void;
	onCreateToolNode: (
		toolType: string,
		toolName: string,
		metadata?: { provider?: string; customConfig?: McpServerInfo },
	) => void;

	// Node palette state
	showNodePalette: boolean;
	paletteSourceNodeId: string | null;
	onCloseNodePalette: () => void;
	onAddNodeFromPalette: (nodeType: string, sourceNodeId?: string) => void;

	// Enhanced execution viewer state
	showEnhancedExecutionViewer: boolean;
	enhancedExecutionViewerId: string | null;
	onCloseEnhancedViewer: () => void;
}

const AgentBuilderModals = React.memo(function AgentBuilderModals({
	createSubAgentDialog,
	createSubWorkflowDialog,
	createToolNodeDialog,
	onCloseSubAgentDialog,
	onCloseSubWorkflowDialog,
	onCloseToolNodeDialog,
	onCreateSubAgent,
	onCreateSubWorkflow,
	onCreateToolNode,
	showNodePalette,
	paletteSourceNodeId,
	onCloseNodePalette,
	onAddNodeFromPalette,
	showEnhancedExecutionViewer,
	enhancedExecutionViewerId,
	onCloseEnhancedViewer,
}: AgentBuilderModalsProps) {
	return (
		<>
			{/* Create Sub-Agent Dialog */}
			<CreateSubAgentDialog
				isOpen={createSubAgentDialog.isOpen}
				onClose={onCloseSubAgentDialog}
				onConfirm={onCreateSubAgent}
				parentAgentName={createSubAgentDialog.parentAgentName}
			/>

			{/* Create Sub-Workflow Dialog */}
			<CreateSubWorkflowDialog
				isOpen={createSubWorkflowDialog.isOpen}
				onClose={onCloseSubWorkflowDialog}
				onConfirm={onCreateSubWorkflow}
				parentAgentName={createSubWorkflowDialog.parentAgentName}
			/>

			{/* Create Tool Node Dialog */}
			<CreateToolNodeDialog
				isOpen={createToolNodeDialog.isOpen}
				onClose={onCloseToolNodeDialog}
				onConfirm={onCreateToolNode}
				parentAgentName={createToolNodeDialog.parentAgentName}
			/>

			{/* Hidden Node Palette */}
			<HiddenNodePalette
				isOpen={showNodePalette}
				onClose={onCloseNodePalette}
				onAddNode={onAddNodeFromPalette}
				sourceNodeId={paletteSourceNodeId || undefined}
			/>

			{/* Enhanced Execution Viewer Modal */}
			{showEnhancedExecutionViewer && enhancedExecutionViewerId && (
				<EnhancedExecutionViewerModal
					isOpen={showEnhancedExecutionViewer}
					executionId={enhancedExecutionViewerId}
					onClose={onCloseEnhancedViewer}
				/>
			)}
		</>
	);
});

export default AgentBuilderModals;
