export type JsonPrimitive = string | number | boolean | null;

export type JsonValue = JsonPrimitive | JsonObject | JsonArray;

export interface JsonObject {
	[key: string]: JsonValue;
}

export type JsonArray = Array<JsonValue>;

export type NodeType =
	| "object"
	| "array"
	| "string"
	| "number"
	| "boolean"
	| "null";

export interface TreeNodeMeta {
	id: string; // stable id based on path
	path: string; // $.a[0].b
	key?: string; // object key or index label
	type: NodeType;
	depth: number;
	size: number; // keys length or array length; 1 for primitives
	preview: string; // short preview string
	children?: string[]; // child ids
}

export interface FlattenedTree {
	nodes: Record<string, TreeNodeMeta>;
	rootId: string;
}
