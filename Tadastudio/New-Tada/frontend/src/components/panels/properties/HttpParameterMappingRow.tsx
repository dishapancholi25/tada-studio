"use client";

import {
	AlertCircle,
	Check,
	ChevronDown,
	ChevronRight,
	Code,
	Hash,
	Trash2,
	Type,
} from "lucide-react";
import { useCallback, useState } from "react";
import type { Node } from "reactflow";
import Dropdown from "@/components/ui/Dropdown";
import StructuredFieldPicker from "@/components/ui/StructuredFieldPicker";

export interface HttpParameterMapping {
	parameter_name: string;
	parameter_type: "url_param" | "query_param" | "header" | "body_field";
	source_mode:
		| "static"
		| "previous"
		| "specific"
		| "start"
		| "field"
		| "template";
	static_value?: any;
	source_node_id?: string;
	source_field_path?: string;
	custom_template?: string;
	is_required?: boolean;
	data_type?: string;
}

interface HttpParameterMappingRowProps {
	mapping: HttpParameterMapping;
	onUpdate: (mapping: HttpParameterMapping) => void;
	onDelete?: () => void;
	availableNodes?: Node[];
	expandedByDefault?: boolean;
}

const sourceModeOptions = [
	{
		value: "static",
		label: "Static Value",
		description: "Enter a fixed value",
		icon: <Type className="w-4 h-4" />,
	},
	{
		value: "previous",
		label: "Previous Node",
		description: "Use output from the previous node in the flow",
		icon: <Code className="w-4 h-4" />,
	},
	{
		value: "specific",
		label: "Specific Node",
		description: "Select output from a specific node",
		icon: <Code className="w-4 h-4" />,
	},
	{
		value: "start",
		label: "Original Input",
		description: "Use the original workflow input",
		icon: <Code className="w-4 h-4" />,
	},
	{
		value: "field",
		label: "Specific Field",
		description: "Select a specific field from structured output",
		icon: <Hash className="w-4 h-4" />,
	},
	{
		value: "template",
		label: "Custom Template",
		description: "Use template syntax with variables",
		icon: <Code className="w-4 h-4" />,
	},
];

const getTypeColor = (type?: string) => {
	if (!type)
		return "text-[color:var(--color-text-muted)] bg-[color:var(--color-text-muted)]/10";
	const lowerType = type.toLowerCase();
	if (lowerType.includes("string") || lowerType.includes("text"))
		return "text-[color:var(--color-text-muted)] bg-[color:var(--color-text-muted)]/10";
	if (
		lowerType.includes("number") ||
		lowerType.includes("int") ||
		lowerType.includes("float")
	)
		return "text-purple-400 bg-purple-400/10";
	if (lowerType.includes("bool")) return "text-[#0DA931] bg-[#0DA931]/10";
	if (lowerType.includes("array") || lowerType.includes("list"))
		return "text-orange-400 bg-orange-400/10";
	if (lowerType.includes("object") || lowerType.includes("json"))
		return "text-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10";
	return "text-[color:var(--color-text-muted)] bg-[color:var(--color-text-muted)]/10";
};

const getParameterTypeLabel = (type: string) => {
	switch (type) {
		case "url_param":
			return "URL Parameter";
		case "query_param":
			return "Query Parameter";
		case "header":
			return "Header";
		case "body_field":
			return "Body Field";
		default:
			return type;
	}
};

export default function HttpParameterMappingRow({
	mapping,
	onUpdate,
	onDelete,
	availableNodes = [],
	expandedByDefault = false,
}: HttpParameterMappingRowProps) {
	const [expanded, setExpanded] = useState(expandedByDefault);

	const handleExpandToggle = useCallback(() => {
		setExpanded(!expanded);
	}, [expanded]);

	const handleDeleteClick = useCallback(
		(e: React.MouseEvent) => {
			e.stopPropagation();
			if (onDelete) {
				onDelete();
			}
		},
		[onDelete],
	);

	const handleParameterNameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onUpdate({ ...mapping, parameter_name: e.target.value });
		},
		[mapping, onUpdate],
	);

	const handleSourceModeChange = useCallback(
		(value: string) => {
			onUpdate({ ...mapping, source_mode: value as any });
		},
		[mapping, onUpdate],
	);

	const handleStaticValueChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onUpdate({ ...mapping, static_value: e.target.value });
		},
		[mapping, onUpdate],
	);

	const handleSpecificNodeChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			onUpdate({
				...mapping,
				source_node_id: e.target.value,
				source_field_path: "",
			});
		},
		[mapping, onUpdate],
	);

	const handleFieldModeNodeChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			onUpdate({
				...mapping,
				source_node_id: e.target.value,
				source_field_path: "",
			});
		},
		[mapping, onUpdate],
	);

	const handleFieldPathChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onUpdate({ ...mapping, source_field_path: e.target.value });
		},
		[mapping, onUpdate],
	);

	const handleStructuredFieldChange = useCallback(
		(fieldPath: string) => {
			onUpdate({ ...mapping, source_field_path: fieldPath });
		},
		[mapping, onUpdate],
	);

	const handleCustomTemplateChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			onUpdate({ ...mapping, custom_template: e.target.value });
		},
		[mapping, onUpdate],
	);

	// Get the selected source node if in 'specific' or 'field' mode
	const sourceNode =
		(mapping.source_mode === "specific" || mapping.source_mode === "field") &&
		mapping.source_node_id
			? availableNodes.find((n) => n.id === mapping.source_node_id)
			: null;

	// Check if the source node has structured outputs
	const hasStructuredOutput =
		sourceNode?.data?.agent_config?.structured_outputs?.length > 0;
	const structuredFields = hasStructuredOutput
		? sourceNode?.data?.agent_config?.structured_outputs?.[0]?.fields || []
		: [];

	// Get display value for the current configuration
	const getDisplayValue = () => {
		switch (mapping.source_mode) {
			case "static":
				return mapping.static_value?.toString() || "Not set";
			case "previous":
				return "Previous node output";
			case "specific":
				if (sourceNode) {
					return `${sourceNode.data.name}${mapping.source_field_path ? ` → ${mapping.source_field_path}` : ""}`;
				}
				return "Select node";
			case "start":
				return "Workflow input";
			case "field":
				if (sourceNode && mapping.source_field_path) {
					return `${sourceNode.data.name} → ${mapping.source_field_path}`;
				}
				return "Select field";
			case "template":
				return mapping.custom_template || "Enter template";
			default:
				return "Not configured";
		}
	};

	return (
		<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)] overflow-hidden">
			{/* Header */}
			<div
				className="p-3 flex items-center justify-between cursor-pointer hover:bg-[color:var(--color-surface)]/70 transition-colors"
				onClick={handleExpandToggle}
			>
				<div className="flex items-center gap-3 flex-1">
					{expanded ? (
						<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
					) : (
						<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
					)}

					<div className="flex items-center gap-2 flex-1">
						<span className="font-medium text-slate-900">
							{mapping.parameter_name}
						</span>

						{mapping.is_required && (
							<span className="text-red-400 text-sm">*</span>
						)}

						<span
							className={`px-2 py-0.5 rounded text-xs ${getTypeColor(mapping.data_type)}`}
						>
							{getParameterTypeLabel(mapping.parameter_type)}
						</span>

						{mapping.data_type && (
							<span
								className={`px-2 py-0.5 rounded text-xs ${getTypeColor(mapping.data_type)}`}
							>
								{mapping.data_type}
							</span>
						)}
					</div>

					<div className="text-sm text-[color:var(--color-text-muted)]">
						→ {getDisplayValue()}
					</div>
				</div>

				{onDelete && (
					<button
						onClick={handleDeleteClick}
						className="p-1.5 text-red-400 hover:bg-red-400/10 rounded transition-colors"
					>
						<Trash2 className="w-4 h-4" />
					</button>
				)}
			</div>

			{/* Expanded Content */}
			{expanded && (
				<div className="border-t border-[color:var(--color-border)] p-4 space-y-4 bg-[color:var(--color-bg-secondary)]/30">
					{/* Parameter Name (url_param names come from the URL template) */}
					{mapping.parameter_type !== "url_param" && (
						<div>
							<label
								htmlFor="parameter-name-input"
								className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
							>
								{getParameterTypeLabel(mapping.parameter_type)} Name
							</label>
							<input
								id="parameter-name-input"
								type="text"
								value={mapping.parameter_name}
								onChange={handleParameterNameChange}
								className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
								placeholder={
									mapping.parameter_type === "header"
										? "e.g., client-id"
										: "Enter name"
								}
							/>
						</div>
					)}

					{/* Source Mode Selector */}
					<div>
						<label
							id="data-source-label"
							className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
						>
							Data Source
						</label>
						<Dropdown
							value={mapping.source_mode}
							onChange={handleSourceModeChange}
							options={sourceModeOptions}
							placeholder="Select source"
						/>
					</div>

					{/* Static Value Input */}
					{mapping.source_mode === "static" && (
						<div>
							<label
								htmlFor="static-value-input"
								className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
							>
								Static Value
							</label>
							<input
								id="static-value-input"
								type="text"
								value={mapping.static_value || ""}
								onChange={handleStaticValueChange}
								className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
								placeholder={`Enter ${mapping.parameter_name} value`}
							/>
						</div>
					)}

					{/* Node Selection for 'specific' mode */}
					{mapping.source_mode === "specific" && (
						<div>
							<label
								htmlFor="node-select"
								className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
							>
								Select Node
							</label>
							<select
								id="node-select"
								value={mapping.source_node_id || ""}
								onChange={handleSpecificNodeChange}
								className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 focus:outline-none focus:border-[#0DA931]"
							>
								<option value="">Select a node...</option>
								{availableNodes
									.filter(
										(n) => n.type === "agentNode" || n.data?.type === "AGENT",
									)
									.map((node) => (
										<option key={node.id} value={node.id}>
											{node.data.name}
											{node.data?.agent_config?.structured_outputs?.length >
												0 && " (Structured)"}
										</option>
									))}
							</select>

							{/* Field path input for non-structured nodes */}
							{sourceNode && !hasStructuredOutput && (
								<div className="mt-3">
									<label
										htmlFor="field-path-input"
										className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
									>
										Field Path (optional)
									</label>
									<input
										id="field-path-input"
										type="text"
										value={mapping.source_field_path || ""}
										onChange={handleFieldPathChange}
										className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
										placeholder="e.g., data.result or leave empty for full output"
									/>
								</div>
							)}

							{/* Structured field picker for structured nodes */}
							{sourceNode && hasStructuredOutput && (
								<div className="mt-3">
									<label
										id="field-select-label-1"
										className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
									>
										Select Field
									</label>
									<StructuredFieldPicker
										aria-labelledby="field-select-label-1"
										fields={structuredFields}
										value={mapping.source_field_path || ""}
										onChange={handleStructuredFieldChange}
										nodeId={sourceNode.id}
										nodeName={sourceNode.data.name}
									/>
								</div>
							)}
						</div>
					)}

					{/* Field selection for 'field' mode */}
					{mapping.source_mode === "field" && (
						<div>
							<label
								htmlFor="structured-node-select"
								className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
							>
								Select Node with Structured Output
							</label>
							<select
								id="structured-node-select"
								value={mapping.source_node_id || ""}
								onChange={handleFieldModeNodeChange}
								className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 focus:outline-none focus:border-[#0DA931]"
							>
								<option value="">Select a node...</option>
								{availableNodes
									.filter(
										(n) => n.data?.agent_config?.structured_outputs?.length > 0,
									)
									.map((node) => (
										<option key={node.id} value={node.id}>
											{node.data.name} (Structured)
										</option>
									))}
							</select>

							{sourceNode && hasStructuredOutput && (
								<div className="mt-3">
									<label
										id="field-select-label-2"
										className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
									>
										Select Field
									</label>
									<StructuredFieldPicker
										aria-labelledby="field-select-label-2"
										fields={structuredFields}
										value={mapping.source_field_path || ""}
										onChange={handleStructuredFieldChange}
										nodeId={sourceNode.id}
										nodeName={sourceNode.data.name}
									/>
								</div>
							)}
						</div>
					)}

					{/* Template input for 'template' mode */}
					{mapping.source_mode === "template" && (
						<div>
							<label
								htmlFor="template-input"
								className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
							>
								Template
							</label>
							<textarea
								id="template-input"
								value={mapping.custom_template || ""}
								onChange={handleCustomTemplateChange}
								className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931] font-mono text-sm"
								placeholder="e.g., {{node_name.field}} or {{start.data}}"
								rows={3}
							/>
							<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
								Use {"{{node_name}}"} to reference node outputs
							</p>
						</div>
					)}

					{/* Info messages */}
					{mapping.source_mode === "previous" && (
						<div className="flex items-start gap-2 p-3 bg-[color:var(--color-accent)]/10 border border-[color:var(--color-border)]/30 rounded-lg">
							<AlertCircle className="w-4 h-4 text-[color:var(--color-accent)] mt-0.5" />
							<p className="text-sm text-[color:var(--color-accent)]">
								This will use the output from the node that executes immediately
								before this one in the workflow.
							</p>
						</div>
					)}

					{mapping.source_mode === "start" && (
						<div className="flex items-start gap-2 p-3 bg-[#0DA931]/10 border border-[#0DA931]/30 rounded-lg">
							<Check className="w-4 h-4 text-[#0DA931] mt-0.5" />
							<p className="text-sm text-[#0DA931]">
								This will use the original input provided when the workflow was
								started.
							</p>
						</div>
					)}
				</div>
			)}
		</div>
	);
}
