"use client";

import {
	AlertCircle,
	Calendar,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	Code,
	Copy,
	Cpu,
	Database,
	FileText,
	GitBranch,
	Globe,
	Hash,
	Info,
	Layers,
	List,
	Mail,
	Search,
	Server,
	Settings,
	Shield,
	Sparkles,
	ToggleLeft,
	Type,
	Zap,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Node } from "reactflow";
import EnhancedNodeSelector from "./EnhancedNodeSelector";
import InfoTooltip from "./InfoTooltipPortal";
import StructuredFieldPicker from "./StructuredFieldPicker";

// Type definitions
export interface InputSourceConfig {
	source_mode: "static" | "previous" | "specific" | "start" | "field";
	source_node_id?: string;
	field_path?: string;
	value?: any;
	value_type?: "static" | "dynamic";
}

interface UnifiedInputSourcePickerProps {
	label: string;
	value?: any;
	sourceMode?: string;
	sourceNodeId?: string;
	fieldPath?: string;
	onChange: (config: InputSourceConfig) => void;
	availableNodes: Node[];
	placeholder?: string;
	isTextArea?: boolean;
	required?: boolean;
	allowedModes?: InputSourceConfig["source_mode"][];
	helpText?: string;
	showPreview?: boolean;
}

// Node type icon mapping
const getNodeIcon = (nodeType?: string, nodeData?: any) => {
	// Check for specific node configurations first
	if (nodeData?.email_send_config)
		return <Mail className="w-4 h-4 text-gray-400" />;
	if (nodeData?.file_read_config)
		return <FileText className="w-4 h-4 text-orange-400" />;
	if (nodeData?.database_query_config)
		return <Database className="w-4 h-4 text-blue-400" />;
	if (nodeData?.http_request_config)
		return <Globe className="w-4 h-4 text-[color:var(--color-primary)]" />;

	// Check by node type
	switch (nodeType) {
		case "AGENT":
			return <Cpu className="w-4 h-4 text-purple-400" />;
		case "TOOL":
			return <Settings className="w-4 h-4 text-blue-400" />;
		case "CONDITION":
			return <GitBranch className="w-4 h-4 text-[color:var(--color-accent)]" />;
		case "HUMAN":
			return <AlertCircle className="w-4 h-4 text-orange-400" />;
		case "START":
			return <Zap className="w-4 h-4 text-[color:var(--color-primary)]" />;
		case "END":
			return <CheckCircle className="w-4 h-4 text-red-400" />;
		default:
			return <Layers className="w-4 h-4 text-gray-400" />;
	}
};

// Get node type label with color
const getNodeTypeLabel = (nodeType?: string, nodeData?: any) => {
	let label = nodeType || "Unknown";
	let colorClass = "bg-gray-500/20 text-gray-400 border-gray-500/30";

	// Check for specific configurations
	if (nodeData?.email_send_config) {
		label = "Email";
		colorClass = "bg-gray-500/20 text-gray-400 border-gray-500/30";
	} else if (nodeData?.file_read_config) {
		label = "File";
		colorClass = "bg-orange-500/20 text-orange-400 border-orange-500/30";
	} else if (nodeData?.database_query_config) {
		label = "Database";
		colorClass = "bg-blue-500/20 text-blue-400 border-blue-500/30";
	} else if (nodeData?.http_request_config) {
		label = "HTTP";
		colorClass =
			"bg-[rgba(var(--color-primary-rgb),0.2)] text-[color:var(--color-primary)] border-[rgba(var(--color-primary-rgb),0.3)]";
	} else {
		// Use node type
		switch (nodeType) {
			case "AGENT":
				label = "Agent";
				colorClass = "bg-purple-500/20 text-purple-400 border-purple-500/30";
				break;
			case "TOOL":
				label = "Tool";
				colorClass = "bg-blue-500/20 text-blue-400 border-blue-500/30";
				break;
			case "CONDITION":
				label = "Condition";
				colorClass =
					"bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] border-[color:var(--color-border)]/35";
				break;
			case "HUMAN":
				label = "Human";
				colorClass = "bg-orange-500/20 text-orange-400 border-orange-500/30";
				break;
		}
	}

	return { label, colorClass };
};

const UnifiedInputSourcePicker: React.FC<UnifiedInputSourcePickerProps> = ({
	label,
	value = "",
	sourceMode = "static",
	sourceNodeId,
	fieldPath,
	onChange,
	availableNodes,
	placeholder = "Enter value...",
	isTextArea = false,
	required = false,
	allowedModes = ["static", "previous", "specific", "start", "field"],
	helpText,
	showPreview = true,
}) => {
	const [expanded, setExpanded] = useState(required || sourceMode !== "static");
	const [searchQuery, setSearchQuery] = useState("");

	// Filter available nodes (exclude END nodes)
	const selectableNodes = useMemo(() => {
		return availableNodes.filter((n) => n.data?.type !== "END");
	}, [availableNodes]);

	// Source mode options based on allowed modes
	const sourceModeOptions = useMemo(() => {
		const allOptions = [
			{
				value: "static",
				label: "Static Value",
				description: "Enter a fixed value",
				icon: <Type className="w-4 h-4" />,
			},
			{
				value: "previous",
				label: "Previous Node",
				description: "Output from previous node",
				icon: <ChevronRight className="w-4 h-4" />,
			},
			{
				value: "specific",
				label: "Specific Node",
				description: "Choose a specific node",
				icon: <Layers className="w-4 h-4" />,
			},
			{
				value: "start",
				label: "Start Input",
				description: "Original workflow input",
				icon: <Zap className="w-4 h-4" />,
			},
			{
				value: "field",
				label: "Field Path",
				description: "Extract from state",
				icon: <Code className="w-4 h-4" />,
			},
		];

		return allOptions.filter((opt) => allowedModes.includes(opt.value as any));
	}, [allowedModes]);

	// Get selected node details
	const selectedNode = useMemo(() => {
		if (sourceMode === "specific" && sourceNodeId) {
			return selectableNodes.find((n) => n.id === sourceNodeId);
		}
		return null;
	}, [sourceMode, sourceNodeId, selectableNodes]);

	// Check if selected node has structured output
	const hasStructuredOutput = useMemo(() => {
		return selectedNode?.data?.agent_config?.structured_outputs?.length > 0;
	}, [selectedNode]);

	// Get structured fields
	const structuredFields = useMemo(() => {
		if (hasStructuredOutput) {
			return (
				selectedNode?.data?.agent_config?.structured_outputs?.[0]?.fields || []
			);
		}
		return [];
	}, [hasStructuredOutput, selectedNode]);

	// Generate input preview
	const generatePreview = () => {
		switch (sourceMode) {
			case "static":
				return value ? `"${value}"` : "No value set";

			case "previous":
				return "Output from the previous node in the workflow";

			case "specific":
				if (!selectedNode) return "Select a node to see preview";
				if (fieldPath) {
					return `${selectedNode.data.name}.${fieldPath}`;
				}
				return `Complete output from "${selectedNode.data.name}"`;

			case "start":
				return "Original input that started the workflow";

			case "field":
				return fieldPath
					? `State field: ${fieldPath}`
					: "Enter field path to see preview";

			default:
				return "Unknown source mode";
		}
	};

	// Handle source mode change
	const handleSourceModeChange = useCallback(
		(mode: string) => {
			onChange({
				source_mode: mode as InputSourceConfig["source_mode"],
				source_node_id: undefined,
				field_path: undefined,
				value: mode === "static" ? value : undefined,
			});
		},
		[onChange, value],
	);

	// Handle node selection
	const handleNodeSelect = (nodeId: string) => {
		onChange({
			source_mode: "specific",
			source_node_id: nodeId,
			field_path: undefined,
			value: undefined,
		});
	};

	// Handle field path change
	const handleFieldPathChange = useCallback(
		(path: string) => {
			onChange({
				source_mode: sourceMode as InputSourceConfig["source_mode"],
				source_node_id: sourceNodeId,
				field_path: path,
				value: sourceMode === "static" ? value : undefined,
			});
		},
		[onChange, sourceMode, sourceNodeId, value],
	);

	// Handle static value change
	const handleValueChange = useCallback(
		(newValue: string) => {
			onChange({
				source_mode: "static",
				source_node_id: undefined,
				field_path: undefined,
				value: newValue,
			});
		},
		[onChange],
	);

	const toggleExpanded = useCallback(
		() => !required && setExpanded(!expanded),
		[expanded, required],
	);
	const createSourceModeHandler = useCallback(
		(mode: string) => () => handleSourceModeChange(mode),
		[handleSourceModeChange],
	);
	const createValueChangeHandler = useCallback(
		(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
			handleValueChange(e.target.value),
		[handleValueChange],
	);
	const createFieldPathHandler = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) =>
			handleFieldPathChange(e.target.value),
		[handleFieldPathChange],
	);

	return (
		<div className="border border-[color:var(--color-border)] rounded-lg bg-[color:var(--color-surface)]/50 overflow-hidden transition-all duration-200 hover:border-[color:var(--color-surface-hover)]">
			{/* Header - Always visible */}
			<div
				className={`flex items-center gap-3 p-3 ${!required ? "cursor-pointer hover:bg-[color:var(--color-surface)]/70" : ""} transition-colors`}
				onClick={toggleExpanded}
			>
				{!required && (
					<ChevronDown
						className={`w-4 h-4 text-[color:var(--color-text-muted)] transition-transform ${expanded ? "rotate-180" : ""}`}
					/>
				)}

				<div className="flex-1 flex items-center gap-2">
					<span className="text-sm font-medium text-slate-900 flex items-center gap-1">
						{label}
						{required && <span className="text-red-400">*</span>}
						{helpText && <InfoTooltip text={helpText} />}
					</span>

					{/* Quick preview when collapsed */}
					{!expanded && (
						<div className="flex items-center gap-2">
							{sourceMode === "static" && value && (
								<span className="text-xs text-[color:var(--color-text-muted)] truncate max-w-[200px]">
									{`"${value}"`}
								</span>
							)}
							{sourceMode !== "static" && (
								<span className="text-xs px-2 py-0.5 bg-[rgba(var(--color-primary-rgb),0.2)] text-[color:var(--color-primary)] rounded border border-[rgba(var(--color-primary-rgb),0.3)]">
									{sourceMode === "previous"
										? "Previous"
										: sourceMode === "specific" && selectedNode
											? selectedNode.data.name
											: sourceMode === "start"
												? "Start"
												: sourceMode === "field"
													? "Field"
													: sourceMode}
								</span>
							)}
							{hasStructuredOutput && fieldPath && (
								<span className="text-xs px-2 py-0.5 bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] rounded border border-[color:var(--color-border)]/30">
									.{fieldPath}
								</span>
							)}
						</div>
					)}
				</div>
			</div>

			{/* Expanded Content */}
			{expanded && (
				<div className="px-3 pb-3 space-y-3 border-t border-[color:var(--color-border)]">
					{/* Source Mode Selection */}
					<div className="pt-3">
						<label className="block text-xs font-medium text-[color:var(--color-text-muted)] mb-2 flex items-center gap-1">
							<Info className="w-3 h-3" />
							Input Source
						</label>
						<div className="grid grid-cols-2 gap-2">
							{sourceModeOptions.map((option) => (
								<button
									key={option.value}
									onClick={createSourceModeHandler(option.value)}
									className={`relative p-2 rounded-lg border transition-all duration-200 ${
										sourceMode === option.value
											? "bg-[rgba(var(--color-primary-rgb),0.2)] border-[rgba(var(--color-primary-rgb),0.7)] text-[color:var(--color-primary)] shadow-lg shadow-[rgba(var(--color-primary-rgb),0.2)]"
											: "bg-[color:var(--color-surface)]/50 border-[color:var(--color-border)] text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-surface-hover)] hover:bg-[color:var(--color-surface)]/70"
									}`}
								>
									<div className="flex items-center gap-2">
										{option.icon}
										<div className="text-left">
											<div className="text-xs font-medium">{option.label}</div>
											<div className="text-[10px] opacity-75">
												{option.description}
											</div>
										</div>
									</div>
								</button>
							))}
						</div>
					</div>

					{/* Static Value Input */}
					{sourceMode === "static" && (
						<div>
							<label
								htmlFor={
									isTextArea ? "static-value-textarea" : "static-value-input"
								}
								className="block text-xs font-medium text-[color:var(--color-text-muted)] mb-2"
							>
								Value
							</label>
							{isTextArea ? (
								<textarea
									id="static-value-textarea"
									value={value || ""}
									onChange={createValueChangeHandler}
									placeholder={placeholder}
									className="w-full px-3 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-[rgba(var(--color-primary-rgb),0.7)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.25)] focus:outline-none resize-none"
									rows={4}
								/>
							) : (
								<input
									id="static-value-input"
									type="text"
									value={value || ""}
									onChange={createValueChangeHandler}
									placeholder={placeholder}
									className="w-full px-3 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-[rgba(var(--color-primary-rgb),0.7)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.25)] focus:outline-none"
								/>
							)}
						</div>
					)}

					{/* Specific Node Selection */}
					{sourceMode === "specific" && (
						<div>
							<label
								id="select-node-label"
								className="block text-xs font-medium text-[color:var(--color-text-muted)] mb-2"
							>
								Select Node
							</label>
							<EnhancedNodeSelector
								value={sourceNodeId}
								onChange={handleNodeSelect}
								nodes={selectableNodes}
								placeholder="Choose a node..."
								showStructuredIndicator={true}
							/>

							{/* Node info badges */}
							{selectedNode && (
								<div className="mt-2 flex flex-wrap gap-2">
									{(() => {
										const { label: typeLabel, colorClass } = getNodeTypeLabel(
											selectedNode.data?.type,
											selectedNode.data,
										);
										return (
											<span
												className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded border ${colorClass}`}
											>
												{getNodeIcon(
													selectedNode.data?.type,
													selectedNode.data,
												)}
												{typeLabel}
											</span>
										);
									})()}

									{hasStructuredOutput && (
										<span className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-[rgba(var(--color-primary-rgb),0.2)] text-[color:var(--color-primary)] rounded border border-[rgba(var(--color-primary-rgb),0.3)]">
											<Sparkles className="w-3 h-3" />
											Structured Output
										</span>
									)}
								</div>
							)}
						</div>
					)}

					{/* Field Path Input */}
					{(sourceMode === "specific" || sourceMode === "field") && (
						<div>
							<label className="block text-xs font-medium text-[color:var(--color-text-muted)] mb-2 flex items-center gap-1">
								Field Path
								<InfoTooltip text="Use dot notation to access nested fields, e.g., user.email" />
							</label>

							{hasStructuredOutput && structuredFields.length > 0 ? (
								<StructuredFieldPicker
									fields={structuredFields}
									value={fieldPath || ""}
									onChange={handleFieldPathChange}
									placeholder="Select a field or enter path"
									allowManualInput={true}
									nodeId={selectedNode?.id}
									nodeName={selectedNode?.data.name}
								/>
							) : (
								<input
									type="text"
									value={fieldPath || ""}
									onChange={createFieldPathHandler}
									placeholder={
										sourceMode === "field"
											? "e.g., state.user.email"
											: "e.g., result.data"
									}
									className="w-full px-3 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg text-slate-900 text-sm focus:border-[rgba(var(--color-primary-rgb),0.7)] focus:ring-2 focus:ring-[rgba(var(--color-primary-rgb),0.25)] focus:outline-none font-mono"
								/>
							)}
						</div>
					)}

					{/* Preview Section */}
					{showPreview && (
						<div className="pt-2">
							<label className="block text-xs font-medium text-[color:var(--color-text-muted)] mb-2 flex items-center gap-1">
								<Code className="w-3 h-3" />
								Input Preview
							</label>
							<div className="p-3 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded-lg">
								<code className="text-xs text-[color:var(--color-primary)] font-mono break-all">
									{generatePreview()}
								</code>
							</div>
						</div>
					)}
				</div>
			)}
		</div>
	);
};

export default UnifiedInputSourcePicker;
