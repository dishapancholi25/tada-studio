/**
 * Types for the node output schema registry and input configuration.
 * Mirrors the backend Pydantic models in backend/services/io/schemas/registry.py
 */

export type FieldType =
	| "string"
	| "integer"
	| "float"
	| "boolean"
	| "object"
	| "array"
	| "any";

export interface OutputField {
	name: string;
	type: FieldType;
	description: string;
	nullable?: boolean;
	children?: OutputField[];
	items_type?: FieldType;
}

export interface NodeOutputSchema {
	node_type: string;
	description: string;
	fields: OutputField[];
	raw_description: string;
	supports_dynamic_schema: boolean;
	raw_is_redundant: boolean;
}

/** Map of node_type -> schema */
export type OutputSchemaRegistry = Record<string, NodeOutputSchema>;

/**
 * Resolved output info for a specific node instance.
 * Combines the static schema with any dynamic fields (e.g. AGENT structured outputs).
 */
export interface ResolvedNodeOutput {
	nodeId: string;
	nodeType: string;
	nodeLabel: string;
	schema: NodeOutputSchema;
	/** For AGENT nodes with structured outputs, overrides schema.fields */
	dynamicFields?: OutputField[];
}
