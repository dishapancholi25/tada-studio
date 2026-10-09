"use client";

import {
	ArrowRight,
	CheckCircle2,
	Code,
	Plus,
	Sparkles,
	XCircle,
	Zap,
} from "lucide-react";
import { useCallback, useMemo } from "react";
import type { Node } from "reactflow";
import BranchConditionInline from "@/components/conditions/BranchConditionInline";
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

interface BranchConfig {
	label: string;
	color: string;
	handle_id: string;
	condition: SimpleCondition;
}

interface EvaluationRulesSectionProps {
	branchMode: string;
	onBranchModeChange: (mode: "binary" | "multi") => void;

	// Binary mode
	branchLabels: string[];
	onBranchLabelsChange: (labels: string[]) => void;
	fieldPath: string;
	onFieldPathChange: (path: string) => void;
	connectedSourceNode?: Node;

	// Multi-branch mode
	branches: BranchConfig[];
	onBranchesChange: (branches: BranchConfig[]) => void;
}

export default function EvaluationRulesSection({
	branchMode,
	onBranchModeChange,
	branchLabels,
	onBranchLabelsChange,
	fieldPath,
	onFieldPathChange,
	connectedSourceNode,
	branches,
	onBranchesChange,
}: EvaluationRulesSectionProps) {
	// Resolve available fields for binary mode field picker
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

	// Branch management handlers
	const handleAddBranch = useCallback(() => {
		const newBranch: BranchConfig = {
			label: `Branch ${branches.length + 1}`,
			color: "#8b5cf6",
			handle_id: `branch-${branches.length}`,
			condition: {},
		};
		onBranchesChange([...branches, newBranch]);
	}, [branches, onBranchesChange]);

	const handleBranchConditionChange = useCallback(
		(index: number, condition: SimpleCondition) => {
			const updated = [...branches];
			updated[index] = { ...updated[index], condition };
			onBranchesChange(updated);
		},
		[branches, onBranchesChange],
	);

	const handleBranchLabelChange = useCallback(
		(index: number, label: string) => {
			const updated = [...branches];
			updated[index] = { ...updated[index], label };
			onBranchesChange(updated);
		},
		[branches, onBranchesChange],
	);

	const handleBranchColorChange = useCallback(
		(index: number, color: string) => {
			const updated = [...branches];
			updated[index] = { ...updated[index], color };
			onBranchesChange(updated);
		},
		[branches, onBranchesChange],
	);

	const handleRemoveBranch = useCallback(
		(index: number) => {
			onBranchesChange(branches.filter((_, i) => i !== index));
		},
		[branches, onBranchesChange],
	);

	const handleMoveBranch = useCallback(
		(index: number, direction: "up" | "down") => {
			const newIndex = direction === "up" ? index - 1 : index + 1;
			if (newIndex < 0 || newIndex >= branches.length) return;
			const updated = [...branches];
			const temp = updated[index];
			updated[index] = updated[newIndex];
			updated[newIndex] = temp;
			onBranchesChange(updated);
		},
		[branches, onBranchesChange],
	);

	const handleBinaryLabelChange = useCallback(
		(index: number, value: string) => {
			const labels = [...branchLabels];
			labels[index] = value;
			onBranchLabelsChange(labels);
		},
		[branchLabels, onBranchLabelsChange],
	);

	return (
		<div className="space-y-5">
			{/* Mode Toggle */}
			<div className="grid grid-cols-2 gap-2 mb-6">
				<button
					type="button"
					onClick={() => onBranchModeChange("binary")}
					className={`rounded-[4px] px-3 py-3 text-left transition-colors duration-200 ${
						branchMode === "binary"
							? "border-2 border-orange-500 bg-white text-gray-900 shadow-sm"
							: "border border-gray-200 bg-white text-gray-600 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
					}`}
				>
					<div className="mb-1 flex items-center gap-2">
						<Code
							className={`h-4 w-4 ${branchMode === "binary" ? "text-orange-600" : "text-gray-500"}`}
						/>
						<span className="text-sm font-semibold text-gray-900">True / False</span>
					</div>
					<p className="pl-6 text-[10px] leading-tight text-gray-600">
						Simple boolean evaluation from a field value
					</p>
				</button>
				<button
					type="button"
					onClick={() => onBranchModeChange("multi")}
					className={`rounded-[4px] px-3 py-3 text-left transition-colors duration-200 ${
						branchMode === "multi"
							? "border-2 border-orange-500 bg-white text-gray-900 shadow-sm"
							: "border border-gray-200 bg-white text-gray-600 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
					}`}
				>
					<div className="mb-1 flex items-center gap-2">
						<Zap
							className={`h-4 w-4 ${branchMode === "multi" ? "text-orange-600" : "text-gray-500"}`}
						/>
						<span className="text-sm font-semibold text-gray-900">First Match</span>
					</div>
					<p className="pl-6 text-[10px] leading-tight text-gray-600">
						Routes to the first branch whose condition is true
					</p>
				</button>
			</div>

			{/* Binary Mode Content */}
			{branchMode === "binary" && (
				<div className="space-y-4">
					{/* Routing Explanation */}
					<div className="grid grid-cols-2 gap-2">
						<div className="flex items-start gap-2.5 rounded-[4px] border border-[#0DA931] bg-white p-3 shadow-sm">
							<CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#0DA931]" />
							<div>
								<div className="mb-1 flex items-center gap-2">
									<span className="text-sm font-medium text-[#0DA931]">
										{branchLabels[0] || "True"}
									</span>
									<input
										type="text"
										value={branchLabels[0] || "True"}
										onChange={(e) => handleBinaryLabelChange(0, e.target.value)}
										className="w-20 rounded-[4px] border border-transparent bg-white px-1.5 py-0.5 text-xs text-[#0DA931] transition-all hover:border-[#0DA931] focus:border-[#0DA931] focus:outline-none"
										title="Edit label"
									/>
								</div>
								<p className="text-[10px] leading-relaxed text-gray-600">
									<code className="font-mono text-[#0DA931]">true</code>, non-empty
									strings, non-zero numbers
								</p>
							</div>
						</div>
						<div className="flex items-start gap-2.5 rounded-[4px] border border-red-200 bg-white p-3 shadow-sm">
							<XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-red-700" />
							<div>
								<div className="mb-1 flex items-center gap-2">
									<span className="text-sm font-medium text-red-800">
										{branchLabels[1] || "False"}
									</span>
									<input
										type="text"
										value={branchLabels[1] || "False"}
										onChange={(e) => handleBinaryLabelChange(1, e.target.value)}
										className="w-20 rounded-[4px] border border-transparent bg-white px-1.5 py-0.5 text-xs text-red-900 transition-all hover:border-red-300 focus:border-red-500 focus:outline-none"
										title="Edit label"
									/>
								</div>
								<p className="text-[10px] leading-relaxed text-gray-600">
									<code className="font-mono text-red-800">false</code>,{" "}
									<code className="font-mono text-red-800">null</code>,{" "}
									<code className="font-mono text-red-800">0</code>,{" "}
									<code className="font-mono text-red-800">{`""`}</code>
								</p>
							</div>
						</div>
					</div>

					{/* Field Picker */}
					<div className="rounded-[4px] border border-gray-200 bg-white p-4 shadow-sm">
						<div className="mb-3 flex items-center gap-2">
							<Sparkles className="h-3.5 w-3.5 text-blue-700" />
							<span className="text-xs font-semibold capitalize text-gray-700">
								Field to Evaluate
							</span>
							{hasAvailableFields && (
								<span className="text-[10px] text-gray-500">
									({availableFields.length} available)
								</span>
							)}
						</div>
						{hasAvailableFields ? (
							<StructuredFieldPicker
								fields={availableFields}
								value={fieldPath}
								onChange={onFieldPathChange}
								placeholder="Select a field to evaluate"
								nodeName={connectedSourceNode?.data?.name}
								allowManualInput={true}
							/>
						) : (
							<input
								type="text"
								value={fieldPath}
								onChange={(e) => onFieldPathChange(e.target.value)}
								placeholder="e.g., result.is_approved"
								className="w-full rounded-[4px] border border-gray-200 bg-white px-3 py-2.5 font-mono text-sm text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							/>
						)}
						<p className="mt-2 text-[10px] text-gray-600">
							The value of this field determines the routing path (truthy vs
							falsy)
						</p>
					</div>
				</div>
			)}

			{/* Multi-Branch Mode Content */}
			{branchMode === "multi" && (
				<div className="space-y-3">
					{/* Branch Header */}
					<div className="flex items-center justify-between">
						<span className="text-xs font-semibold capitalize text-gray-700">
							Branches ({branches.length}/4)
						</span>
						{branches.length < 4 && (
							<button
								type="button"
								onClick={handleAddBranch}
								className="flex items-center gap-1.5 rounded-[4px] border border-orange-600 bg-orange-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:border-orange-700 hover:bg-orange-700"
							>
								<Plus className="h-3 w-3" />
								Add Branch
							</button>
						)}
					</div>

					{/* Branch List */}
					{branches.length > 0 ? (
						<div className="space-y-2">
							{branches.map((branch, index) => (
								<div
									key={branch.handle_id || `branch-${index}`}
									className="relative group"
								>
									{/* IF / ELSE IF label */}
									<div className="absolute -top-2 left-4 z-10">
										<span className="rounded-[4px] border border-gray-200 bg-white px-2 py-0.5 text-[9px] font-semibold capitalize text-gray-700 shadow-sm">
											{index === 0 ? "IF" : "ELSE IF"}
										</span>
									</div>

									<div className="pt-1.5">
										<BranchConditionInline
											branchLabel={branch.label}
											branchColor={branch.color}
											condition={branch.condition || {}}
											onConditionChange={(condition) =>
												handleBranchConditionChange(index, condition)
											}
											onLabelChange={(label) =>
												handleBranchLabelChange(index, label)
											}
											onColorChange={(color) =>
												handleBranchColorChange(index, color)
											}
											onRemove={() => handleRemoveBranch(index)}
											onMove={(dir) => handleMoveBranch(index, dir)}
											canMoveUp={index > 0}
											canMoveDown={index < branches.length - 1}
											connectedSourceNode={connectedSourceNode}
										/>
									</div>

									{/* Route indicator */}
									<div className="ml-12 mt-1.5 flex items-center gap-2">
										<ArrowRight className="h-2.5 w-2.5 text-gray-500" />
										<span className="flex items-center gap-1.5">
											<span
												className="inline-block h-2 w-2 rounded-full"
												style={{ backgroundColor: branch.color }}
											/>
											<span className="text-[10px] font-medium text-gray-800">
												{branch.label}
											</span>
										</span>
									</div>
								</div>
							))}

							{/* ELSE fallback */}
							<div className="mt-3 border-t border-gray-200 pt-3">
								<div className="ml-4 flex items-center gap-2">
									<span className="rounded-[4px] border border-gray-200 bg-slate-50 px-2 py-0.5 text-[9px] font-semibold capitalize text-gray-700">
										ELSE
									</span>
									<ArrowRight className="h-2.5 w-2.5 text-gray-500" />
									<span className="text-[10px] italic text-gray-600">
										Configure fallback in Settings tab
									</span>
								</div>
							</div>
						</div>
					) : (
						<div className="rounded-[4px] border border-dashed border-gray-300 bg-white p-8 text-center">
							<Zap className="mx-auto mb-2 h-8 w-8 text-gray-400" />
							<p className="mb-3 text-sm text-gray-600">
								No branches configured yet
							</p>
							<button
								type="button"
								onClick={handleAddBranch}
								className="rounded-[4px] bg-orange-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-orange-700"
							>
								Add First Branch
							</button>
						</div>
					)}
				</div>
			)}
		</div>
	);
}
