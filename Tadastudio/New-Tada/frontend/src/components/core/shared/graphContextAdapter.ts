"use client";

import type { Edge, Node } from "reactflow";
import type {
	CreateNodeRequest,
	CreateSubAgentRequest,
	GraphData,
} from "@/lib/api";
import type { GraphNode } from "@/types/api";
import type { BaseGraphOperations, GraphOperations } from "./graphOperations";

interface GraphContextType {
	currentGraph: GraphData | null;
	loading: boolean;
	error: string | null;
	graphs: GraphData[];

	// Graph operations
	createGraph: (name: string, description?: string) => Promise<void>;
	loadGraph: (name: string) => Promise<void>;
	deleteGraph: (name: string) => Promise<void>;
	exportGraph: (format?: "full" | "minimal" | "langgraph") => Promise<any>;
	saveGraph: () => Promise<void>;
	reloadGraph: () => Promise<void>;
	clearGraph: () => Promise<void>;

	// Node operations
	createNode: (nodeData: Omit<CreateNodeRequest, "graph_name">) => {
		tempId: string;
		promise: Promise<string | undefined>;
	};
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

	// Read-only state
	nodes: Node[];
	edges: Edge[];
}

/**
 * Adapter that wraps GraphContext to provide the GraphOperations interface.
 * This allows AgentBuilder to work with the shared abstractions while
 * keeping all its mutation capabilities intact.
 */
export class GraphContextAdapter implements GraphOperations {
	private graphContext: GraphContextType;

	constructor(graphContext: GraphContextType) {
		this.graphContext = graphContext;
	}

	// Read-only properties
	get isReadOnly(): boolean {
		return false;
	}

	get currentGraph(): any | null {
		return this.graphContext.currentGraph;
	}

	get nodes(): Node[] {
		return this.graphContext.nodes;
	}

	get edges(): Edge[] {
		return this.graphContext.edges;
	}

	get loading(): boolean {
		return this.graphContext.loading;
	}

	get error(): string | null {
		return this.graphContext.error;
	}

	// Graph operations - direct delegation to GraphContext
	async createGraph(name: string, description?: string): Promise<void> {
		return this.graphContext.createGraph(name, description);
	}

	async loadGraph(name: string): Promise<void> {
		return this.graphContext.loadGraph(name);
	}

	async deleteGraph(name: string): Promise<void> {
		return this.graphContext.deleteGraph(name);
	}

	async exportGraph(format?: "full" | "minimal" | "langgraph"): Promise<any> {
		return this.graphContext.exportGraph(format);
	}

	async saveGraph(): Promise<void> {
		return this.graphContext.saveGraph();
	}

	async reloadGraph(): Promise<void> {
		return this.graphContext.reloadGraph();
	}

	async clearGraph(): Promise<void> {
		return this.graphContext.clearGraph();
	}

	// Node operations - delegate to GraphContext and await the promise
	async createNode(
		nodeData: Omit<CreateNodeRequest, "graph_name">,
	): Promise<string | undefined> {
		const { promise } = this.graphContext.createNode(nodeData);
		return promise;
	}

	async createSubAgent(
		parentAgentId: string,
		data?: Partial<
			Omit<CreateSubAgentRequest, "graph_name" | "parent_agent_id">
		>,
	): Promise<void> {
		return this.graphContext.createSubAgent(parentAgentId, data);
	}

	async updateNode(
		nodeId: string,
		updates: Partial<GraphNode["data"]>,
	): Promise<void> {
		return this.graphContext.updateNode(nodeId, updates);
	}

	async deleteNode(nodeId: string): Promise<void> {
		return this.graphContext.deleteNode(nodeId);
	}

	// Connection operations - direct delegation to GraphContext
	async createConnection(
		sourceId: string,
		targetId: string,
		sourceHandle?: string,
		targetHandle?: string,
		label?: string,
		connectionType?: string,
	): Promise<void> {
		return this.graphContext.createConnection(
			sourceId,
			targetId,
			sourceHandle,
			targetHandle,
			label,
			connectionType,
		);
	}

	async deleteConnection(sourceId: string, targetId: string): Promise<void> {
		return this.graphContext.deleteConnection(sourceId, targetId);
	}
}

/**
 * Hook that creates a GraphContextAdapter from the provided GraphContext.
 * This provides a bridge between the new GraphOperations interface and
 * the existing GraphContext for AgentBuilder.
 */
export function createGraphContextAdapter(
	graphContext: GraphContextType,
): GraphOperations {
	return new GraphContextAdapter(graphContext);
}
