/**
 * Types for tracking graph changes in local-first architecture
 */

export interface AddNodeChange {
	type: "ADD_NODE";
	timestamp: number;
	data: {
		node: any; // NodeData
		tempId: string; // Temporary ID before backend assigns real ID
	};
}

export interface UpdateNodeChange {
	type: "UPDATE_NODE";
	timestamp: number;
	data: {
		nodeId: string;
		updates: Record<string, any>;
	};
}

export interface DeleteNodeChange {
	type: "DELETE_NODE";
	timestamp: number;
	data: {
		nodeId: string;
	};
}

export interface AddConnectionChange {
	type: "ADD_CONNECTION";
	timestamp: number;
	data: {
		sourceId: string;
		targetId: string;
		sourceHandle?: string;
		targetHandle?: string;
		label?: string;
		connectionType?: string;
		tempId: string;
	};
}

export interface DeleteConnectionChange {
	type: "DELETE_CONNECTION";
	timestamp: number;
	data: {
		sourceId: string;
		targetId: string;
	};
}

export interface UpdateNodePositionChange {
	type: "UPDATE_NODE_POSITION";
	timestamp: number;
	data: {
		nodeId: string;
		position: { x: number; y: number };
	};
}

export type TypedGraphChange =
	| AddNodeChange
	| UpdateNodeChange
	| DeleteNodeChange
	| AddConnectionChange
	| DeleteConnectionChange
	| UpdateNodePositionChange;

export type SyncStatus = "saved" | "saving" | "unsaved" | "offline" | "error";
