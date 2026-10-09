import type { Node } from "reactflow";
import type { OutputField, OutputSchemaRegistry } from "@/types/io";

// --- Segment types for the visual editor ---

export interface TextSegment {
	type: "text";
	value: string;
}

export interface VariableSegment {
	type: "variable";
	variableKey: string;
	displayLabel: string;
	nodeType?: string;
}

export type TemplateSegment = TextSegment | VariableSegment;

// --- Variable metadata for the source panel ---

export interface VariableInfo {
	key: string;
	displayLabel: string;
	description: string;
	category: "builtin" | "node" | "field";
	nodeType?: string;
	parentNodeId?: string;
	fieldType?: string;
}

// --- Variable group for the sidebar ---

export interface VariableGroup {
	id: string;
	label: string;
	nodeType?: string;
	variables: VariableInfo[];
}

// --- Shared utility: build flat variable list from available nodes ---

export function buildVariableList(
	availableNodes: Node[],
	schemaRegistry: OutputSchemaRegistry | null,
): VariableInfo[] {
	const variables: VariableInfo[] = [
		{
			key: "original",
			displayLabel: "Original Input",
			description: "The original workflow input",
			category: "builtin",
		},
		{
			key: "previous",
			displayLabel: "Previous Output",
			description: "Output from the previous node",
			category: "builtin",
		},
	];

	for (const n of availableNodes) {
		const nodeId = n.id;
		const nodeName = n.data.name || nodeId;
		const nodeType = (
			n.data.node_type ||
			n.data.type ||
			""
		).toUpperCase();

		variables.push({
			key: nodeId,
			displayLabel: nodeName,
			description: `Raw output from "${nodeName}"`,
			category: "node",
			nodeType,
		});

		const schema = schemaRegistry?.[nodeType];
		if (schema) {
			const agentStructuredFields =
				n.data.agent_config?.structured_outputs?.[0]?.fields;
			const fields =
				schema.supports_dynamic_schema && agentStructuredFields
					? agentStructuredFields.map(
							(f: { name: string; type: string; description?: string }) => ({
								name: f.name,
								type: mapFieldType(f.type),
								description: f.description || "",
							}),
						)
					: schema.fields;

			addFieldVariables(variables, nodeId, nodeName, nodeType, fields, nodeId);
		}
	}

	return variables;
}

function addFieldVariables(
	variables: VariableInfo[],
	nodeId: string,
	nodeName: string,
	nodeType: string,
	fields: OutputField[],
	prefix: string,
) {
	for (const field of fields) {
		const path = `${prefix}.${field.name}`;
		variables.push({
			key: path,
			displayLabel: `${nodeName}.${field.name}`,
			description: field.description || `Field from "${nodeName}"`,
			category: "field",
			nodeType,
			parentNodeId: nodeId,
			fieldType: field.type,
		});

		if (field.children) {
			addFieldVariables(
				variables,
				nodeId,
				nodeName,
				nodeType,
				field.children,
				path,
			);
		}
	}
}

/** Build grouped variable list for the sidebar. */
export function buildVariableGroups(
	availableNodes: Node[],
	schemaRegistry: OutputSchemaRegistry | null,
): VariableGroup[] {
	const allVars = buildVariableList(availableNodes, schemaRegistry);

	const builtins = allVars.filter((v) => v.category === "builtin");
	const groups: VariableGroup[] = [
		{ id: "__builtin__", label: "Built-in Variables", variables: builtins },
	];

	for (const n of availableNodes) {
		const nodeId = n.id;
		const nodeName = n.data.name || nodeId;
		const nodeType = (
			n.data.node_type ||
			n.data.type ||
			""
		).toUpperCase();

		const nodeVars = allVars.filter(
			(v) =>
				(v.category === "node" && v.key === nodeId) ||
				(v.category === "field" && v.parentNodeId === nodeId),
		);

		if (nodeVars.length > 0) {
			groups.push({
				id: nodeId,
				label: nodeName,
				nodeType,
				variables: nodeVars,
			});
		}
	}

	return groups;
}

function mapFieldType(agentType: string): string {
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
