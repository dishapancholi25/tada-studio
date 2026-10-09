"use client";

import type { Edge, Node } from "reactflow";
import type { CreateNodeRequest, CreateSubAgentRequest } from "@/lib/api";
import type { GraphNode } from "@/types/api";

/**
 * Interface defining all graph operations that can be performed.
 * This allows both mutable (AgentBuilder) and read-only (ExecutionGraphViewer) implementations.
 */
export interface GraphOperations {
	// Read-only properties
	readonly isReadOnly: boolean;
	readonly currentGraph: any | null;
	readonly nodes: Node[];
	readonly edges: Edge[];
	readonly loading: boolean;
	readonly error: string | null;

	// Graph operations
	createGraph: (name: string, description?: string) => Promise<void>;
	loadGraph: (name: string) => Promise<void>;
	deleteGraph: (name: string) => Promise<void>;
	exportGraph: (format?: "full" | "minimal" | "langgraph") => Promise<any>;
	saveGraph: () => Promise<void>;
	reloadGraph: () => Promise<void>;
	clearGraph: () => Promise<void>;

	// Node operations
	createNode: (
		nodeData: Omit<CreateNodeRequest, "graph_name">,
	) => Promise<string | undefined>;
	createSubAgent: (
		parentAgentId: string,
		data?: Partial<
			Omit<CreateSubAgentRequest, "graph_name" | "parent_agent_id">
		>,
	) => Promise<void>;
	updateNode: (
		nodeId: string,
		updates: Partial<GraphNode["data"]>,
	) => Promise<void>;
	deleteNode: (nodeId: string) => Promise<void>;

	// Connection operations
	createConnection: (
		sourceId: string,
		targetId: string,
		sourceHandle?: string,
		targetHandle?: string,
		label?: string,
		connectionType?: string,
	) => Promise<void>;
	deleteConnection: (sourceId: string, targetId: string) => Promise<void>;
}

/**
 * Base implementation that provides no-op implementations for mutations.
 * Useful as a base for read-only implementations.
 */
export abstract class BaseGraphOperations implements GraphOperations {
	abstract readonly isReadOnly: boolean;
	abstract readonly currentGraph: any | null;
	abstract readonly nodes: Node[];
	abstract readonly edges: Edge[];
	abstract readonly loading: boolean;
	abstract readonly error: string | null;

	// Default no-op implementations for mutations
	async createGraph(name: string, description?: string): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to create graph in read-only mode");
			return;
		}
		throw new Error("createGraph not implemented");
	}

	async loadGraph(name: string): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to load graph in read-only mode");
			return;
		}
		throw new Error("loadGraph not implemented");
	}

	async deleteGraph(name: string): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to delete graph in read-only mode");
			return;
		}
		throw new Error("deleteGraph not implemented");
	}

	async exportGraph(format?: "full" | "minimal" | "langgraph"): Promise<any> {
		throw new Error("exportGraph not implemented");
	}

	async saveGraph(): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to save graph in read-only mode");
			return;
		}
		throw new Error("saveGraph not implemented");
	}

	async reloadGraph(): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to reload graph in read-only mode");
			return;
		}
		throw new Error("reloadGraph not implemented");
	}

	async clearGraph(): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to clear graph in read-only mode");
			return;
		}
		throw new Error("clearGraph not implemented");
	}

	async createNode(
		nodeData: Omit<CreateNodeRequest, "graph_name">,
	): Promise<string | undefined> {
		if (this.isReadOnly) {
			console.warn("Attempted to create node in read-only mode");
			return;
		}
		throw new Error("createNode not implemented");
	}

	async createSubAgent(
		parentAgentId: string,
		data?: Partial<
			Omit<CreateSubAgentRequest, "graph_name" | "parent_agent_id">
		>,
	): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to create sub-agent in read-only mode");
			return;
		}
		throw new Error("createSubAgent not implemented");
	}

	async updateNode(
		nodeId: string,
		updates: Partial<GraphNode["data"]>,
	): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to update node in read-only mode");
			return;
		}
		throw new Error("updateNode not implemented");
	}

	async deleteNode(nodeId: string): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to delete node in read-only mode");
			return;
		}
		throw new Error("deleteNode not implemented");
	}

	async createConnection(
		sourceId: string,
		targetId: string,
		sourceHandle?: string,
		targetHandle?: string,
		label?: string,
		connectionType?: string,
	): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to create connection in read-only mode");
			return;
		}
		throw new Error("createConnection not implemented");
	}

	async deleteConnection(sourceId: string, targetId: string): Promise<void> {
		if (this.isReadOnly) {
			console.warn("Attempted to delete connection in read-only mode");
			return;
		}
		throw new Error("deleteConnection not implemented");
	}
}
