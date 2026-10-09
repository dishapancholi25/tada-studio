"use client";

import type { Edge, Node } from "reactflow";
import { BaseGraphOperations } from "./graphOperations";

/**
 * Read-only implementation of GraphOperations for ExecutionGraphViewer.
 * This provides a safe interface that prevents mutations while allowing
 * the same UI components to be used for both editing and viewing.
 */
export class ReadOnlyGraphAdapter extends BaseGraphOperations {
	private _nodes: Node[] = [];
	private _edges: Edge[] = [];
	private _currentGraph: any | null = null;
	private _loading = false;
	private _error: string | null = null;
	private _onNodesChange?: (nodes: Node[]) => void;
	private _onEdgesChange?: (edges: Edge[]) => void;

	constructor(options?: {
		initialNodes?: Node[];
		initialEdges?: Edge[];
		currentGraph?: any;
		onNodesChange?: (nodes: Node[]) => void;
		onEdgesChange?: (edges: Edge[]) => void;
	}) {
		super();
		if (options?.initialNodes) {
			this._nodes = options.initialNodes;
		}
		if (options?.initialEdges) {
			this._edges = options.initialEdges;
		}
		if (options?.currentGraph) {
			this._currentGraph = options.currentGraph;
		}
		this._onNodesChange = options?.onNodesChange;
		this._onEdgesChange = options?.onEdgesChange;
	}

	// Read-only properties
	get isReadOnly(): boolean {
		return true;
	}

	get currentGraph(): any | null {
		return this._currentGraph;
	}

	get nodes(): Node[] {
		return this._nodes;
	}

	get edges(): Edge[] {
		return this._edges;
	}

	get loading(): boolean {
		return this._loading;
	}

	get error(): string | null {
		return this._error;
	}

	// Allow external updates to state (for execution data updates)
	updateNodes(nodes: Node[]): void {
		this._nodes = nodes;
		this._onNodesChange?.(nodes);
	}

	updateEdges(edges: Edge[]): void {
		this._edges = edges;
		this._onEdgesChange?.(edges);
	}

	updateCurrentGraph(graph: any): void {
		this._currentGraph = graph;
	}

	updateLoading(loading: boolean): void {
		this._loading = loading;
	}

	updateError(error: string | null): void {
		this._error = error;
	}

	// Export operations are allowed in read-only mode
	async exportGraph(format?: "full" | "minimal" | "langgraph"): Promise<any> {
		if (!this._currentGraph) {
			throw new Error("No graph available to export");
		}
		// Return the current graph data in the requested format
		// This could be enhanced to transform the data based on the format parameter
		return this._currentGraph;
	}

	// UI state operations that notify external listeners but don't persist
	setNodes(nodes: Node[]): void {
		this._nodes = nodes;
		this._onNodesChange?.(nodes);
	}

	setEdges(edges: Edge[]): void {
		this._edges = edges;
		this._onEdgesChange?.(edges);
	}
}

/**
 * Factory function to create a ReadOnlyGraphAdapter for ExecutionGraphViewer.
 * This provides a clean interface for creating read-only graph operations.
 */
export function createReadOnlyGraphAdapter(options?: {
	initialNodes?: Node[];
	initialEdges?: Edge[];
	currentGraph?: any;
	onNodesChange?: (nodes: Node[]) => void;
	onEdgesChange?: (edges: Edge[]) => void;
}): ReadOnlyGraphAdapter {
	return new ReadOnlyGraphAdapter(options);
}
