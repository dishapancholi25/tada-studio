"use client";

import { useState } from "react";
import { useGraph } from "@/contexts/GraphContext";
import AssignmentList from "./AssignmentList";
import EffectiveConfigPreview from "./EffectiveConfigPreview";
import GuardrailsPanel from "./GuardrailsPanel";
import PolicyPicker from "./PolicyPicker";

interface ToolGuardrailsSectionProps {
	toolNodeId: string;
	guardrailsEnabled?: boolean;
	onGuardrailsEnabledChange?: (enabled: boolean) => void;
	/** Light card (orange/white property modals). Default matches dark tool panels. */
	guardrailsPanelTheme?: "default" | "light";
}

export default function ToolGuardrailsSection({
	toolNodeId,
	guardrailsEnabled = false,
	onGuardrailsEnabledChange,
	guardrailsPanelTheme = "default",
}: ToolGuardrailsSectionProps) {
	const { currentGraph } = useGraph();
	const workflowId = currentGraph?.workflow_id;
	const [showPicker, setShowPicker] = useState(false);
	const [refreshTrigger, setRefreshTrigger] = useState(0);
	const [localEnabled, setLocalEnabled] = useState(guardrailsEnabled);

	const enabled = onGuardrailsEnabledChange ? guardrailsEnabled : localEnabled;
	const guardrailsAppearance = guardrailsPanelTheme === "light" ? "light" : "default";
	const handleToggle = (val: boolean) => {
		if (onGuardrailsEnabledChange) {
			onGuardrailsEnabledChange(val);
		} else {
			setLocalEnabled(val);
		}
	};

	return (
		<GuardrailsPanel
			enabled={enabled}
			onToggle={handleToggle}
			onAssign={() => setShowPicker(true)}
			description="Enforce safety policies on this tool's inputs and outputs."
			theme={guardrailsPanelTheme}
		>
			<AssignmentList
				targetType="tool"
				targetId={toolNodeId}
				workflowId={workflowId}
				onOpenPolicyPicker={() => setShowPicker(true)}
				refreshTrigger={refreshTrigger}
				hideHeader
				appearance={guardrailsAppearance}
			/>
			<EffectiveConfigPreview
				workflowId={workflowId}
				nodeId={toolNodeId}
				appearance={guardrailsAppearance}
			/>
			{showPicker && (
				<PolicyPicker
					targetType="tool"
					targetId={toolNodeId}
					workflowId={workflowId}
					onAssigned={() => {
						setShowPicker(false);
						setRefreshTrigger((c) => c + 1);
					}}
					onClose={() => setShowPicker(false)}
				/>
			)}
		</GuardrailsPanel>
	);
}
