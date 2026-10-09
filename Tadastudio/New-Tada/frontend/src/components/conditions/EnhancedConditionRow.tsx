"use client";

import {
	AlertCircle,
	CheckCircle2,
	ChevronDown,
	ChevronRight,
	Copy,
	GripVertical,
	Trash2,
} from "lucide-react";
import { useCallback, useState } from "react";
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

interface EnhancedConditionRowProps {
	condition: SimpleCondition;
	index: number;
	onUpdate: (condition: SimpleCondition) => void;
	onRemove: () => void;
	onDuplicate?: () => void;
	availableNodes: Node[];
	showDragHandle?: boolean;
}

const operatorOptions = [
	{ value: "==", label: "Equals" },
	{ value: "!=", label: "Not Equals" },
	{ value: ">", label: "Greater Than" },
	{ value: "<", label: "Less Than" },
	{ value: ">=", label: "Greater or Equal" },
	{ value: "<=", label: "Less or Equal" },
	{ value: "contains", label: "Contains" },
	{ value: "starts_with", label: "Starts With" },
	{ value: "ends_with", label: "Ends With" },
	{ value: "is_empty", label: "Is Empty" },
	{ value: "is_not_empty", label: "Is Not Empty" },
];

export default function EnhancedConditionRow({
	condition,
	index,
	onUpdate,
	onRemove,
	onDuplicate,
	availableNodes,
	showDragHandle = false,
}: EnhancedConditionRowProps) {
	const [expanded, setExpanded] = useState(false);

	const getOperatorLabel = (op: string) => {
		return operatorOptions.find((o) => o.value === op)?.label || op;
	};

	// Validate condition completeness
	const isComplete = () => {
		if (!condition.operator) return false;
		if (!condition.input_source && !condition.field_path) return false;
		if (
			!["is_empty", "is_not_empty"].includes(condition.operator) &&
			(condition.value === undefined || condition.value === "")
		) {
			return false;
		}
		return true;
	};

	const complete = isComplete();

	// Get source display text
	const getSourceText = () => {
		if (condition.input_source === "static") return "Static";
		if (condition.input_source === "previous") return "Previous Node";
		if (condition.input_source === "start") return "Start Input";
		if (condition.input_source === "specific" && condition.source_node_id) {
			const node = availableNodes.find(
				(n) => n.id === condition.source_node_id,
			);
			return node?.data.name || "Unknown Node";
		}
		if (condition.input_source === "custom") return "Template";
		if (condition.field_path) return "Field";
		return "Not Set";
	};

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
			{/* Header - Always Visible */}
			<div
				className="p-4 cursor-pointer transition-all duration-200"
				onClick={() => setExpanded(!expanded)}
			>
				<div className="flex items-center justify-between gap-3">
					{/* Left Side - Drag Handle + Expand + Label */}
					<div className="flex items-center gap-3 flex-1 min-w-0">
						{showDragHandle && (
							<div
								className="cursor-grab active:cursor-grabbing text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)] transition-colors"
								onClick={(e) => e.stopPropagation()}
							>
								<GripVertical className="w-4 h-4" />
							</div>
						)}

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

						{/* Status Icon */}
						<div className="flex-shrink-0">
							{complete ? (
								<CheckCircle2 className="w-4 h-4 text-[color:var(--color-primary)]" />
							) : (
								<AlertCircle className="w-4 h-4 text-amber-500" />
							)}
						</div>

						{/* Condition Summary */}
						<div className="flex items-center gap-2 flex-wrap flex-1 min-w-0">
							<span className="text-sm font-semibold text-slate-900">
								Condition {index + 1}
							</span>

							{/* Source Badge */}
							<span className="text-xs px-2 py-1 bg-[rgba(56,189,248,0.15)] text-sky-600 rounded-md border border-[rgba(56,189,248,0.25)] font-medium">
								{getSourceText()}
							</span>

							{/* Field Path Badge */}
							{condition.field_path && (
								<span className="text-xs px-2 py-1 bg-[color:var(--color-primary)]/15 text-[color:var(--color-primary)] rounded-md border border-[color:var(--color-primary)]/30 font-medium truncate max-w-[150px]">
									{condition.field_path}
								</span>
							)}

							{/* Operator */}
							{condition.operator && (
								<>
									<span className="text-xs text-[color:var(--color-text-muted)]">
										→
									</span>
									<span className="text-xs px-2 py-1 bg-[rgba(168,85,247,0.15)] text-purple-600 rounded-md border border-[rgba(168,85,247,0.25)] font-medium">
										{getOperatorLabel(condition.operator)}
									</span>
								</>
							)}

							{/* Value */}
							{condition.value !== undefined &&
								condition.value !== "" &&
								!["is_empty", "is_not_empty"].includes(
									condition.operator || "",
								) && (
									<>
										<span className="text-xs text-[color:var(--color-text-muted)]">
											→
										</span>
										<span className="text-xs px-2 py-1 bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary-light)] rounded-md border border-[rgba(var(--color-primary-rgb),0.25)] font-medium truncate max-w-[150px]">
											{String(condition.value)}
										</span>
									</>
								)}
						</div>
					</div>

					{/* Right Side - Action Buttons */}
					<div className="flex items-center gap-2 flex-shrink-0">
						{onDuplicate && (
							<IconButton
								onClick={(e: React.MouseEvent) => {
									e.stopPropagation();
									onDuplicate();
								}}
								ariaLabel="Duplicate condition"
								variant="ghost"
								size="sm"
							>
								<Copy className="w-4 h-4" />
							</IconButton>
						)}

						<IconButton
							onClick={(e: React.MouseEvent) => {
								e.stopPropagation();
								onRemove();
							}}
							ariaLabel="Remove condition"
							variant="danger"
							size="sm"
						>
							<Trash2 className="w-4 h-4" />
						</IconButton>
					</div>
				</div>
			</div>

			{/* Expanded Content */}
			{expanded && (
				<div className="border-t-2 border-[color:var(--color-border)]/40 px-4 py-5 bg-[color:var(--color-bg-secondary)]/30 animate-in slide-in-from-top-2 fade-in duration-200">
					<ConditionEditorTabs
						condition={condition}
						onConditionChange={onUpdate}
						availableNodes={availableNodes}
						index={index}
					/>
				</div>
			)}
		</div>
	);
}
