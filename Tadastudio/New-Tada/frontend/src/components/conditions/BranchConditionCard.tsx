"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import type { Node } from "reactflow";
import IconButton from "@/components/ui/IconButton";
import ConditionEditorTabs from "./ConditionEditorTabs";

interface SimpleCondition {
	input_source?: string;
	source_node_id?: string;
	field_path?: string;
	operator?: string;
	value?: any;
	value_type?: string;
	dynamic_source?: any;
	custom_template?: string;
}

interface BranchConditionCardProps {
	branchLabel: string;
	branchColor: string;
	condition: SimpleCondition;
	onConditionChange: (condition: SimpleCondition) => void;
	availableNodes: Node[];
	index: number;
}

export default function BranchConditionCard({
	branchLabel,
	branchColor,
	condition,
	onConditionChange,
	availableNodes,
	index,
}: BranchConditionCardProps) {
	const [expanded, setExpanded] = useState(false);

	return (
		<div
			className={`
        rounded-xl border-2 overflow-hidden transition-all duration-300
        ${
					expanded
						? "border-[color:var(--color-primary)]/40 bg-[color:var(--color-surface)]/60 shadow-[0_8px_32px_rgba(var(--color-primary-rgb),0.15)]"
						: "border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/40 hover:border-[color:var(--color-border)] hover:bg-[color:var(--color-surface)]/60 hover:shadow-[0_4px_16px_rgba(0,0,0,0.25)]"
				}
      `}
		>
			{/* Header */}
			<div
				className="p-4 cursor-pointer transition-all duration-200"
				onClick={() => setExpanded(!expanded)}
			>
				<div className="flex items-center justify-between gap-3">
					<div className="flex items-center gap-3 flex-1">
						<IconButton
							onClick={(e: React.MouseEvent) => {
								e.stopPropagation();
								setExpanded(!expanded);
							}}
							ariaLabel={expanded ? "Collapse condition" : "Expand condition"}
							variant="ghost"
							size="sm"
						>
							{expanded ? (
								<ChevronDown className="w-4 h-4" />
							) : (
								<ChevronRight className="w-4 h-4" />
							)}
						</IconButton>

						<div
							className="w-4 h-4 rounded-full border-2 border-white/30 flex-shrink-0 shadow-sm"
							style={{ backgroundColor: branchColor }}
						/>

						<span className="text-sm font-semibold text-slate-900">
							{branchLabel}
						</span>

						{condition.field_path && (
							<span className="text-xs px-2 py-1 bg-[color:var(--color-primary)]/15 text-[color:var(--color-primary)] rounded-md border border-[color:var(--color-primary)]/30 font-medium">
								{condition.field_path}
							</span>
						)}

						{condition.operator && (
							<span className="text-xs text-[color:var(--color-text-muted)]">
								{condition.operator}
							</span>
						)}
					</div>
				</div>
			</div>

			{/* Expanded Content */}
			{expanded && (
				<div className="border-t-2 border-[color:var(--color-border)]/40 px-4 py-5 bg-[color:var(--color-bg-secondary)]/30 animate-in slide-in-from-top-2 fade-in duration-200">
					<ConditionEditorTabs
						condition={condition}
						onConditionChange={onConditionChange}
						availableNodes={availableNodes}
						index={index}
					/>
				</div>
			)}
		</div>
	);
}
