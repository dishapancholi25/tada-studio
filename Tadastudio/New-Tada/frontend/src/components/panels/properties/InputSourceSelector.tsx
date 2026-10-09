import { Check, Database, Maximize2, Sparkles } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Edge, Node } from "reactflow";
import { useOutputSchemas } from "@/contexts/OutputSchemaContext";
import type { NodeOutputSchema, OutputField } from "@/types/io";
import FlowPreview from "./FlowPreview";
import InputSourceOption from "./InputSourceOption";
import InputTemplateBuilderModal from "./InputTemplateBuilderModal";
import OutputSchemaViewer from "./OutputSchemaViewer";
import SpecificNodeConfig from "./SpecificNodeConfig";
import type { InputSourceConfig, StructuredField } from "./inputSourceTypes";
import {
	MODE_OPTIONS,
	configsEqual,
	normalizeConfig,
} from "./inputSourceTypes";

interface InputSourceSelectorProps {
	node: Node;
	availableNodes: Node[];
	onUpdate: (config: InputSourceConfig) => void;
	initialConfig?: Partial<InputSourceConfig> | null;
	edges?: Edge[];
}

const InputSourceSelector: React.FC<InputSourceSelectorProps> = ({
	node,
	availableNodes,
	onUpdate,
	initialConfig,
	edges,
}) => {
	const [config, setConfig] = useState<InputSourceConfig>(() =>
		normalizeConfig(initialConfig ?? node.data.input_source_config),
	);

	const [showTemplateBuilder, setShowTemplateBuilder] = useState(false);
	const [availableFields, setAvailableFields] = useState<StructuredField[]>(
		[],
	);
	const [multiSelectMode, setMultiSelectMode] = useState(
		() =>
			config.source_mode === "specific" &&
			(config.source_node_ids?.length ?? 0) > 1,
	);

	useEffect(() => {
		const nextConfig = normalizeConfig(
			initialConfig ?? node.data.input_source_config,
		);
		if (!configsEqual(nextConfig, config)) {
			setConfig(nextConfig);
			setMultiSelectMode(
				nextConfig.source_mode === "specific" &&
					(nextConfig.source_node_ids?.length ?? 0) > 1,
			);
		}
	}, [initialConfig, node.id, config]);

	// Load available fields when a source node with structured output is selected
	useEffect(() => {
		if (
			config.source_mode === "specific" &&
			config.source_node_ids &&
			config.source_node_ids.length === 1
		) {
			const sourceNode = availableNodes.find(
				(n) => n.id === config.source_node_ids![0],
			);
			if (sourceNode?.data?.agent_config?.structured_outputs?.[0]) {
				const fields =
					sourceNode.data.agent_config.structured_outputs[0].fields || [];
				setAvailableFields(
					fields.map((f: any) => ({
						id: f.id,
						name: f.name,
						type: f.type,
						description: f.description,
						required: f.required,
					})),
				);
			} else {
				setAvailableFields([]);
			}
		} else {
			setAvailableFields([]);
		}
	}, [config.source_mode, config.source_node_ids, availableNodes]);

	const updateConfig = useCallback(
		(updates: Partial<InputSourceConfig>) => {
			setConfig((prev) => {
				const merged = normalizeConfig({ ...prev, ...updates });
				onUpdate(merged);
				return merged;
			});
		},
		[onUpdate],
	);

	const handleSourceModeChange = useCallback(
		(mode: string) => {
			updateConfig({
				source_mode: mode as InputSourceConfig["source_mode"],
				source_node_ids: [],
				selected_fields: [],
				use_structured_field: false,
			});
			setMultiSelectMode(false);
		},
		[updateConfig],
	);

	const handleToggleMultiSelectMode = useCallback(() => {
		setMultiSelectMode((prev) => !prev);
	}, []);

	const handleSingleSelectChoose = useCallback(
		(nodeId: string) => {
			updateConfig({
				source_node_ids: [nodeId],
				source_node_id: nodeId,
				selected_fields: [],
				use_structured_field: false,
			});
		},
		[updateConfig],
	);

	const handleClearSingleSelection = useCallback(() => {
		updateConfig({
			source_node_ids: [],
			source_node_id: null,
			selected_fields: [],
			use_structured_field: false,
		});
	}, [updateConfig]);

	const handleNodeToggle = useCallback(
		(nodeId: string, checked: boolean) => {
			const currentIds = config.source_node_ids || [];
			const newIds = checked
				? [...currentIds, nodeId]
				: currentIds.filter((id) => id !== nodeId);

			updateConfig({
				source_node_ids: newIds,
				source_node_id: newIds.length === 1 ? newIds[0] : null,
				selected_fields: [],
				use_structured_field: false,
			});
		},
		[config.source_node_ids, updateConfig],
	);

	const handleIncludeNodeLabelsChange = useCallback(
		(checked: boolean) => {
			updateConfig({ include_node_labels: checked });
		},
		[updateConfig],
	);

	const handleFieldToggle = useCallback(
		(fieldName: string, checked: boolean) => {
			const newFields = checked
				? [...config.selected_fields, fieldName]
				: config.selected_fields.filter((f) => f !== fieldName);

			updateConfig({
				selected_fields: newFields,
				use_structured_field: newFields.length > 0,
			});
		},
		[config.selected_fields, updateConfig],
	);

	const handleUseCompleteOutputChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			if (e.target.checked) {
				updateConfig({
					selected_fields: [],
					use_structured_field: false,
				});
			}
		},
		[updateConfig],
	);

	const handleIncludeOriginalInputChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			updateConfig({ include_original_input: e.target.checked });
		},
		[updateConfig],
	);

	const handleCustomTemplateChange = useCallback(
		(value: string) => {
			updateConfig({ custom_template: value });
		},
		[updateConfig],
	);

	const createFieldToggleHandler = useCallback(
		(fieldName: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
			handleFieldToggle(fieldName, e.target.checked);
		},
		[handleFieldToggle],
	);

	// Derived values
	const structuredSourceNode =
		config.source_mode === "specific" && config.source_node_ids?.length === 1
			? availableNodes.find((n) => n.id === config.source_node_ids?.[0])
			: undefined;

	const hasStructuredOutput = Boolean(
		structuredSourceNode?.data?.agent_config?.structured_outputs?.length,
	);

	// Output schema registry
	const { schemas: schemaRegistry } = useOutputSchemas();

	// Resolve schema for a selected specific-mode source node (non-AGENT or AGENT without structured outputs)
	const selectedNodeSchema = useMemo((): {
		schema: NodeOutputSchema;
		dynamicFields?: OutputField[];
	} | null => {
		if (!schemaRegistry || !structuredSourceNode) return null;
		const nodeType =
			structuredSourceNode.data.node_type ||
			structuredSourceNode.data.type ||
			"";
		const schema = schemaRegistry[nodeType.toUpperCase()];
		if (!schema) return null;

		// For AGENT nodes with structured outputs, build dynamic fields from agent_config
		if (
			schema.supports_dynamic_schema &&
			structuredSourceNode.data.agent_config?.structured_outputs?.[0]
		) {
			const agentFields =
				structuredSourceNode.data.agent_config.structured_outputs[0].fields ||
				[];
			const dynamicFields: OutputField[] = agentFields.map(
				(f: { name: string; type: string; description?: string }) => ({
					name: f.name,
					type: mapAgentFieldType(f.type),
					description: f.description || "",
				}),
			);
			return { schema, dynamicFields };
		}

		return { schema };
	}, [schemaRegistry, structuredSourceNode]);

	// Resolve schema for previous node (find incoming connected node)
	const previousNodeSchema = useMemo((): {
		schema: NodeOutputSchema;
		nodeLabel: string;
		dynamicFields?: OutputField[];
	} | null => {
		if (!schemaRegistry || !edges || config.source_mode !== "previous")
			return null;
		// Find the node connected to this node's input
		const incomingEdge = edges.find((e) => e.target === node.id);
		if (!incomingEdge) return null;
		const prevNode = availableNodes.find(
			(n) => n.id === incomingEdge.source,
		);
		if (!prevNode) return null;
		const nodeType =
			prevNode.data.node_type || prevNode.data.type || "";
		const schema = schemaRegistry[nodeType.toUpperCase()];
		if (!schema) return null;

		// For AGENT with structured outputs
		if (
			schema.supports_dynamic_schema &&
			prevNode.data.agent_config?.structured_outputs?.[0]
		) {
			const agentFields =
				prevNode.data.agent_config.structured_outputs[0].fields || [];
			const dynamicFields: OutputField[] = agentFields.map(
				(f: { name: string; type: string; description?: string }) => ({
					name: f.name,
					type: mapAgentFieldType(f.type),
					description: f.description || "",
				}),
			);
			return {
				schema,
				nodeLabel: prevNode.data.name || prevNode.id,
				dynamicFields,
			};
		}

		return { schema, nodeLabel: prevNode.data.name || prevNode.id };
	}, [schemaRegistry, edges, node.id, availableNodes, config.source_mode]);

	return (
		<div className="space-y-4">
			{/* Input Source Selection */}
			<section className="rounded-[4px] border border-slate-200 bg-white p-5 shadow-sm">
				<h3 className="mb-1 text-xs font-semibold capitalize text-slate-700">
					Node Input
				</h3>
				<p className="mb-4 text-sm text-slate-600">
					Where should this agent receive its input from?
				</p>

				<div
					className="space-y-2"
					role="radiogroup"
					aria-label="Input source selection"
				>
					{MODE_OPTIONS.map((option) => (
						<InputSourceOption
							key={option.value}
							option={option}
							isSelected={config.source_mode === option.value}
							onSelect={() => handleSourceModeChange(option.value)}
						>
							{/* Inline: Specific Node config */}
							{option.value === "specific" &&
								config.source_mode === "specific" && (
									<SpecificNodeConfig
										config={config}
										availableNodes={availableNodes}
										multiSelectMode={multiSelectMode}
										onToggleMultiSelect={handleToggleMultiSelectMode}
										onSingleSelect={handleSingleSelectChoose}
										onClearSelection={handleClearSingleSelection}
										onNodeToggle={handleNodeToggle}
										onIncludeNodeLabelsChange={handleIncludeNodeLabelsChange}
									/>
								)}

							{/* Custom Template config */}
							{option.value === "custom" &&
								config.source_mode === "custom" && (
									<>
										<button
											type="button"
											onClick={(e) => {
												e.stopPropagation();
												setShowTemplateBuilder(true);
											}}
											className="flex items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-800 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
										>
											<Maximize2 className="h-3 w-3" />
											Open Template Builder
										</button>
										{config.custom_template && (
											<p className="truncate rounded-[4px] border border-slate-200 bg-slate-50 px-2.5 py-1.5 font-mono text-xs text-slate-700">
												{config.custom_template}
											</p>
										)}
										<InputTemplateBuilderModal
											isOpen={showTemplateBuilder}
											onClose={() => setShowTemplateBuilder(false)}
											template={config.custom_template ?? ""}
											availableNodes={availableNodes}
											onApply={(newTemplate) => {
												handleCustomTemplateChange(newTemplate);
												setShowTemplateBuilder(false);
											}}
										/>
									</>
								)}
						</InputSourceOption>
					))}
				</div>
			</section>

			{/* Output Schema Preview for Previous mode */}
			{config.source_mode === "previous" && previousNodeSchema && (
				<section className="rounded-[4px] border border-slate-200 bg-white p-5 shadow-sm">
					<h3 className="mb-3 flex items-center gap-2 text-xs font-semibold capitalize text-slate-700">
						<Database className="h-3.5 w-3.5" />
						Output from {previousNodeSchema.nodeLabel}
					</h3>
					<OutputSchemaViewer
						schema={previousNodeSchema.schema}
						dynamicFields={previousNodeSchema.dynamicFields}
						compact
					/>
				</section>
			)}

			{/* Output Schema Preview for Specific mode (non-AGENT nodes or AGENT without structured outputs) */}
			{config.source_mode === "specific" &&
				selectedNodeSchema &&
				!hasStructuredOutput &&
				config.source_node_ids?.length === 1 && (
					<section className="rounded-[4px] border border-slate-200 bg-white p-5 shadow-sm">
						<h3 className="mb-3 flex items-center gap-2 text-xs font-semibold capitalize text-slate-700">
							<Database className="h-3.5 w-3.5" />
							Available Output Fields
						</h3>
						<OutputSchemaViewer
							schema={selectedNodeSchema.schema}
							dynamicFields={selectedNodeSchema.dynamicFields}
							selectable
							selectedFields={config.selected_fields}
							onFieldToggle={(fieldPath) => {
								const isSelected =
									config.selected_fields.includes(fieldPath);
								handleFieldToggle(fieldPath, !isSelected);
							}}
						/>
						{config.selected_fields.length > 0 && (
							<p className="mt-2 text-[11px] text-slate-600">
								Only selected fields will be passed to this node.
								Deselect all to pass the complete output.
							</p>
						)}
					</section>
				)}

			{/* Structured Fields (unchanged logic, only when applicable) */}
			{config.source_mode === "specific" &&
				hasStructuredOutput &&
				availableFields.length > 0 &&
				config.source_node_ids?.length === 1 && (
					<section className="rounded-[4px] border border-slate-200 bg-white p-5 shadow-sm">
						<h3 className="mb-3 flex items-center gap-2 text-xs font-semibold capitalize text-slate-700">
							<Sparkles className="h-3.5 w-3.5" />
							Structured Fields
						</h3>
						<div className="space-y-3">
							<label
								className={`flex items-center justify-between gap-3 rounded-[4px] border px-3 py-2 transition-all duration-200 ${
									config.selected_fields.length === 0
										? "border-orange-500 bg-white shadow-sm"
										: "border-slate-200 bg-white hover:border-orange-400 hover:bg-slate-50"
								}`}
							>
								<div>
									<p className="text-sm font-semibold text-slate-900">
										Send every field
									</p>
									<p className="text-xs text-slate-600">
										Keep the structured response exactly as it was produced.
									</p>
								</div>
								<div className="relative inline-flex items-center">
									<input
										type="checkbox"
										checked={config.selected_fields.length === 0}
										onChange={handleUseCompleteOutputChange}
										className="peer sr-only"
									/>
									<div className="h-5 w-9 rounded-full bg-slate-200 transition-colors duration-200 peer-checked:bg-orange-500" />
									<div className="absolute left-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm transition-transform duration-200 peer-checked:translate-x-4" />
								</div>
							</label>

							<div className="grid gap-2 sm:grid-cols-2">
								{availableFields.map((field) => {
									const isChecked = config.selected_fields.includes(field.name);
									const isDisabled =
										config.selected_fields.length === 0 && !isChecked;
									return (
										<label
											key={field.id}
											className={`group relative flex h-full flex-col gap-1.5 rounded-[4px] border px-3 py-2 transition-all duration-200 ${
												isChecked
													? "border-orange-500 bg-white shadow-sm"
													: "border-slate-200 bg-white hover:border-orange-400 hover:bg-slate-50"
											} ${isDisabled ? "opacity-60 hover:opacity-100" : ""}`}
										>
											<input
												type="checkbox"
												checked={isChecked}
												onChange={createFieldToggleHandler(field.name)}
												className="sr-only"
											/>
											<div className="flex items-start justify-between gap-2">
												<div>
													<p className="text-sm font-semibold text-slate-900">
														{field.name}
													</p>
													<span className="text-xs capitalize tracking-wide text-slate-600">
														{field.type}
													</span>
												</div>
												<span
													className={`flex h-5 w-5 items-center justify-center rounded-full border transition-colors ${
														isChecked
															? "border-orange-500 bg-orange-500 text-white"
															: "border-slate-300 text-transparent"
													}`}
												>
													<Check className="h-3.5 w-3.5" />
												</span>
											</div>
											{field.description && (
												<p className="text-xs leading-relaxed text-slate-600">
													{field.description}
												</p>
											)}
											{field.required && (
												<span className="w-fit rounded-full border border-orange-300 bg-white px-1.5 py-0.5 text-[9px] font-medium capitalize tracking-wide text-orange-800">
													Required
												</span>
											)}
										</label>
									);
								})}
							</div>

							{config.selected_fields.length > 1 && (
								<div className="rounded-[4px] border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-800">
									We will bundle the chosen fields into one JSON object.
								</div>
							)}
						</div>
					</section>
				)}

			{/* Flow Preview */}
			<FlowPreview
				config={config}
				availableNodes={availableNodes}
				currentNodeName={node.data.name || "This Agent"}
				edges={edges}
				nodeId={node.id}
			/>

			{/* Footer: Include original workflow input */}
			{config.source_mode !== "start" && (
				<section className="rounded-[4px] border border-slate-200 bg-white px-4 py-3 shadow-sm">
					<label className="group flex cursor-pointer items-center justify-between gap-3">
						<div>
							<p className="text-sm font-medium text-slate-900 transition-colors group-hover:text-slate-900">
								Include original workflow input
							</p>
							<p className="text-xs text-slate-600">
								Add the initial request alongside the selected content.
							</p>
						</div>
						<div className="relative inline-flex items-center">
							<input
								type="checkbox"
								checked={config.include_original_input}
								onChange={handleIncludeOriginalInputChange}
								className="peer sr-only"
							/>
							<div className="h-5 w-9 rounded-full bg-slate-200 transition-colors duration-200 peer-checked:bg-orange-500" />
							<div className="absolute left-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm transition-transform duration-200 peer-checked:translate-x-4" />
						</div>
					</label>
				</section>
			)}
		</div>
	);
};

/** Map agent structured output field types to schema FieldType values. */
function mapAgentFieldType(agentType: string): string {
	const mapping: Record<string, string> = {
		str: "string",
		string: "string",
		int: "integer",
		integer: "integer",
		float: "float",
		bool: "boolean",
		boolean: "boolean",
		"List[str]": "array",
		"List[int]": "array",
		"List[float]": "array",
		"Dict[str, Any]": "object",
		"List[Dict[str, Any]]": "array",
		dict: "object",
		list: "array",
	};
	return mapping[agentType] || "any";
}

export default InputSourceSelector;
