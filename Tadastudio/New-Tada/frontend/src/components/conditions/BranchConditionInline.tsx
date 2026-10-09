"use client";

import clsx from "clsx";
import {
	ArrowDown,
	ArrowUp,
	ChevronDown,
	ChevronRight,
	Palette,
	Trash2,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import type { Node } from "reactflow";
import type { DropdownOption } from "@/components/ui/Dropdown";
import Dropdown from "@/components/ui/Dropdown";
import StructuredFieldPicker from "@/components/ui/StructuredFieldPicker";
import { useNodeOutputSchema } from "@/contexts/OutputSchemaContext";
import type { OutputField } from "@/types/io";

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

interface BranchConditionInlineProps {
	branchLabel: string;
	branchColor: string;
	condition: SimpleCondition;
	onConditionChange: (condition: SimpleCondition) => void;
	onLabelChange: (label: string) => void;
	onColorChange: (color: string) => void;
	onRemove: () => void;
	onMove: (direction: "up" | "down") => void;
	canMoveUp: boolean;
	canMoveDown: boolean;
	connectedSourceNode?: Node;
}

const operatorOptions: DropdownOption[] = [
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

const operatorLabels: Record<string, string> = {
	"==": "equals",
	"!=": "not equals",
	">": ">",
	"<": "<",
	">=": ">=",
	"<=": "<=",
	contains: "contains",
	starts_with: "starts with",
	ends_with: "ends with",
	is_empty: "is empty",
	is_not_empty: "is not empty",
};

export default function BranchConditionInline({
	branchLabel,
	branchColor,
	condition,
	onConditionChange,
	onLabelChange,
	onColorChange,
	onRemove,
	onMove,
	canMoveUp,
	canMoveDown,
	connectedSourceNode,
}: BranchConditionInlineProps) {
	const [expanded, setExpanded] = useState(false);

	// Resolve available fields from connected source node
	const sourceNodeType = connectedSourceNode?.data?.type;
	const outputSchema = useNodeOutputSchema(sourceNodeType);
	const structuredOutputs =
		connectedSourceNode?.data?.agent_config?.structured_outputs;
	const hasStructuredOutputs = Boolean(
		structuredOutputs && structuredOutputs.length > 0,
	);

	const availableFields = useMemo(() => {
		if (hasStructuredOutputs) {
			return structuredOutputs?.[0]?.fields || [];
		}
		if (outputSchema?.fields) {
			return outputSchema.fields.map(function mapField(f: OutputField): {
				id: string;
				name: string;
				type: string;
				description?: string;
				fields?: {
					id: string;
					name: string;
					type: string;
					description?: string;
				}[];
			} {
				return {
					id: f.name,
					name: f.name,
					type: f.type,
					description: f.description,
					fields: f.children?.map(mapField),
				};
			});
		}
		return [];
	}, [hasStructuredOutputs, structuredOutputs, outputSchema]);

	const hasAvailableFields = availableFields.length > 0;

	const conditionPreview = useMemo(() => {
		if (!condition.field_path && !condition.operator) return "No condition set";
		const op = condition.operator || "==";
		const parts: string[] = [];
		if (condition.field_path) parts.push(condition.field_path);
		parts.push(operatorLabels[op] || op);
		if (
			condition.value !== undefined &&
			condition.value !== "" &&
			!["is_empty", "is_not_empty"].includes(op)
		) {
			parts.push(`"${String(condition.value)}"`);
		}
		return parts.join(" ");
	}, [condition]);

	const handleFieldPathChange = useCallback(
		(path: string) => {
			const updated: SimpleCondition = { ...condition, field_path: path };
			if (connectedSourceNode) {
				updated.input_source = "specific";
				updated.source_node_id = connectedSourceNode.id;
			}
			onConditionChange(updated);
		},
		[condition, onConditionChange, connectedSourceNode],
	);

	const handleOperatorChange = useCallback(
		(value: string) => {
			onConditionChange({ ...condition, operator: value });
		},
		[condition, onConditionChange],
	);

	const handleValueChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onConditionChange({ ...condition, value: e.target.value });
		},
		[condition, onConditionChange],
	);

	const effectiveOperator = condition.operator || "==";
	const needsValue = !["is_empty", "is_not_empty"].includes(effectiveOperator);

	return (
		<div
			className={clsx(
				"group overflow-hidden rounded-[4px] border bg-white transition-all duration-300 shadow-sm",
				expanded
					? "border-orange-400"
					: "border-gray-200 hover:border-orange-300",
			)}
		>
			<div
				className="flex cursor-pointer items-center gap-2.5 px-3.5 py-3"
				onClick={() => setExpanded(!expanded)}
			>
				<div className="flex flex-shrink-0 flex-col gap-0.5">
					<button
						type="button"
						onClick={(e) => {
							e.stopPropagation();
							onMove("up");
						}}
						disabled={!canMoveUp}
						className="rounded p-0.5 text-gray-500 transition-all hover:bg-slate-100 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-20"
					>
						<ArrowUp className="h-2.5 w-2.5" />
					</button>
					<button
						type="button"
						onClick={(e) => {
							e.stopPropagation();
							onMove("down");
						}}
						disabled={!canMoveDown}
						className="rounded p-0.5 text-gray-500 transition-all hover:bg-slate-100 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-20"
					>
						<ArrowDown className="h-2.5 w-2.5" />
					</button>
				</div>

				{expanded ? (
					<ChevronDown className="h-3.5 w-3.5 flex-shrink-0 text-gray-500" />
				) : (
					<ChevronRight className="h-3.5 w-3.5 flex-shrink-0 text-gray-500" />
				)}

				<div
					className="h-4 w-4 flex-shrink-0 rounded-full border-2 border-gray-200"
					style={{ backgroundColor: branchColor }}
				/>

				<span className="flex-shrink-0 text-sm font-semibold text-gray-900">
					{branchLabel}
				</span>

				{condition.field_path && (
					<span className="truncate rounded-[4px] border border-orange-400 bg-white px-2 py-0.5 text-[10px] font-medium text-orange-900">
						{conditionPreview}
					</span>
				)}
				{!condition.field_path && !condition.operator && (
					<span className="text-[10px] italic text-gray-500">
						No condition set
					</span>
				)}

				<div className="flex-1" />

				<button
					type="button"
					onClick={(e) => {
						e.stopPropagation();
						onRemove();
					}}
					className="flex-shrink-0 rounded-lg p-1 text-gray-500 opacity-0 transition-all duration-200 hover:bg-red-50 hover:text-red-700 group-hover:opacity-100"
				>
					<Trash2 className="h-3 w-3" />
				</button>
			</div>

			{expanded && (
				<div className="animate-in fade-in slide-in-from-top-1 space-y-4 border-t border-gray-200 bg-slate-50 px-4 py-4 duration-200">
					<div className="flex items-center gap-3">
						<div className="flex-1">
							<label className="mb-1.5 block text-[10px] capitalize text-gray-600">
								Branch Label
							</label>
							<input
								type="text"
								value={branchLabel}
								onChange={(e) => onLabelChange(e.target.value)}
								className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								placeholder="Branch name"
							/>
						</div>
						<div>
							<label className="mb-1.5 block text-[10px] capitalize text-gray-600">
								Color
							</label>
							<div className="relative">
								<input
									type="color"
									value={branchColor}
									onChange={(e) => onColorChange(e.target.value)}
									className="h-[38px] w-10 cursor-pointer rounded-[4px] border border-gray-200 transition-colors hover:border-orange-400"
									style={{ backgroundColor: branchColor }}
								/>
								<Palette className="pointer-events-none absolute bottom-1 right-1 h-2.5 w-2.5 text-gray-800" />
							</div>
						</div>
					</div>

					<div>
						<label className="mb-1.5 block text-[10px] capitalize text-gray-600">
							Field to evaluate
						</label>
						{hasAvailableFields ? (
							<StructuredFieldPicker
								fields={availableFields}
								value={condition.field_path || ""}
								onChange={handleFieldPathChange}
								placeholder="Select a field"
								nodeName={connectedSourceNode?.data?.name}
								allowManualInput={true}
							/>
						) : (
							<input
								type="text"
								value={condition.field_path || ""}
								onChange={(e) => handleFieldPathChange(e.target.value)}
								placeholder="e.g., result.is_approved or columns.status"
								className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 font-mono text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							/>
						)}
					</div>

					<div className="flex items-start gap-3">
						<div className="flex-1">
							<label className="mb-1.5 block text-[10px] capitalize text-gray-600">
								Operator
							</label>
							<Dropdown
								value={condition.operator || "=="}
								onChange={handleOperatorChange}
								options={operatorOptions}
								placeholder="Select operator"
								menuAppearance="light"
							/>
						</div>
						{needsValue && (
							<div className="flex-1">
								<label className="mb-1.5 block text-[10px] capitalize text-gray-600">
									Compare value
								</label>
								<input
									type="text"
									value={condition.value || ""}
									onChange={handleValueChange}
									placeholder="Enter value..."
									className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								/>
							</div>
						)}
					</div>
				</div>
			)}
		</div>
	);
}
