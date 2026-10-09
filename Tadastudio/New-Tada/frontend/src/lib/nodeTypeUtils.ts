import type { Node } from "reactflow";

type NodeTypeData = {
	type?: unknown;
	node_type?: unknown;
	[key: string]: unknown;
};

type NodeLike =
	| (Partial<Node> & { data?: NodeTypeData })
	| {
			type?: unknown;
			node_type?: unknown;
			data?: NodeTypeData;
			[key: string]: unknown;
	  }
	| null
	| undefined;

function toUpperCaseOrNull(value: unknown): string | null {
	if (typeof value === "string" && value.trim().length > 0) {
		return value.toUpperCase();
	}
	return null;
}

function extractTypeFromData(data?: NodeTypeData): string | null {
	if (!data) {
		return null;
	}

	const nodeType = toUpperCaseOrNull(data.node_type);
	if (nodeType) {
		return nodeType;
	}

	return toUpperCaseOrNull(data.type);
}

export function getNodeRole(node: NodeLike): string | null {
	if (!node) {
		return null;
	}

	if ("data" in (node as Record<string, unknown>)) {
		const fromData = extractTypeFromData(
			(node as { data?: NodeTypeData }).data,
		);
		if (fromData) {
			return fromData;
		}
	}

	const baseType = toUpperCaseOrNull((node as Partial<Node>).type);
	if (baseType) {
		return baseType;
	}

	return extractTypeFromData(node as NodeTypeData);
}

export function isStartNode(node: NodeLike): boolean {
	return getNodeRole(node) === "START";
}

export function isEndNode(node: NodeLike): boolean {
	return getNodeRole(node) === "END";
}
