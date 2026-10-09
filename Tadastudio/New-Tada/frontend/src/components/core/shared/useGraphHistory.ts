"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Edge, Node } from "reactflow";
import { diffGraphStates } from "@/utils/graphDiff";
import { useGraphStore } from "@/stores/graphStore";

interface HistoryEntry {
	nodes: Node[];
	edges: Edge[];
}

function cloneNodes(nodes: Node[]): Node[] {
	return nodes.map((node) => ({
		...node,
		data:
			typeof node.data === "object" && node.data !== null
				? { ...node.data }
				: node.data,
		position: node.position ? { ...node.position } : node.position,
	}));
}

function cloneEdges(edges: Edge[]): Edge[] {
	return edges.map((edge) => ({
		...edge,
		data:
			typeof edge.data === "object" && edge.data !== null
				? { ...edge.data }
				: edge.data,
	}));
}

interface UseGraphHistoryParams {
	reactFlowNodes: Node[];
	reactFlowEdges: Edge[];
	setReactFlowNodes: (value: Node[] | ((prev: Node[]) => Node[])) => void;
	setReactFlowEdges: (value: Edge[] | ((prev: Edge[]) => Edge[])) => void;
	applyGraphNodes?: (nodes: Node[]) => void;
	applyGraphEdges?: (edges: Edge[]) => void;
	showInfo?: (title: string, description: string) => void;
	maxHistorySize?: number;
	debounceMs?: number;
	resetKey?: string | number | null | undefined;
}

interface UseGraphHistoryResult {
	saveToHistory: () => void;
	handleUndo: () => void;
	handleRedo: () => void;
	historyIndex: number;
	canUndo: boolean;
	canRedo: boolean;
}

export function useGraphHistory({
	reactFlowNodes,
	reactFlowEdges,
	setReactFlowNodes,
	setReactFlowEdges,
	applyGraphNodes,
	applyGraphEdges,
	showInfo,
	maxHistorySize = 50,
	debounceMs = 300,
	resetKey = "__default__",
}: UseGraphHistoryParams): UseGraphHistoryResult {
	const [history, setHistory] = useState<HistoryEntry[]>([]);
	const [historyIndex, setHistoryIndex] = useState(-1);
	const historyTimeoutRef = useRef<NodeJS.Timeout | null>(null);
	const historyIndexRef = useRef(-1);

	useEffect(() => {
		historyIndexRef.current = historyIndex;
	}, [historyIndex]);

	useEffect(() => {
		const hasInitialState =
			reactFlowNodes.length > 0 || reactFlowEdges.length > 0;
		if (hasInitialState) {
			const initialEntry: HistoryEntry = {
				nodes: cloneNodes(reactFlowNodes),
				edges: cloneEdges(reactFlowEdges),
			};
			setHistory([initialEntry]);
			setHistoryIndex(0);
			historyIndexRef.current = 0;
		} else {
			setHistory([]);
			setHistoryIndex(-1);
			historyIndexRef.current = -1;
		}
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [resetKey]);

	useEffect(() => {
		if (historyIndexRef.current !== -1) {
			return;
		}
		if (reactFlowNodes.length === 0 && reactFlowEdges.length === 0) {
			return;
		}
		const initialEntry: HistoryEntry = {
			nodes: cloneNodes(reactFlowNodes),
			edges: cloneEdges(reactFlowEdges),
		};
		setHistory([initialEntry]);
		setHistoryIndex(0);
		historyIndexRef.current = 0;
	}, [reactFlowNodes, reactFlowEdges]);

	useEffect(
		() => () => {
			if (historyTimeoutRef.current) {
				clearTimeout(historyTimeoutRef.current);
			}
		},
		[],
	);

	const saveToHistory = useCallback(() => {
		if (historyTimeoutRef.current) {
			clearTimeout(historyTimeoutRef.current);
		}

		historyTimeoutRef.current = setTimeout(() => {
			setHistory((prev) => {
				const currentIndex = historyIndexRef.current;
				const trimmed =
					currentIndex >= 0 ? prev.slice(0, currentIndex + 1) : [];
				trimmed.push({
					nodes: cloneNodes(reactFlowNodes),
					edges: cloneEdges(reactFlowEdges),
				});

				if (trimmed.length > maxHistorySize) {
					trimmed.shift();
				}

				const newIndex = trimmed.length - 1;
				historyIndexRef.current = newIndex;
				setHistoryIndex(newIndex);
				return trimmed;
			});
		}, debounceMs);
	}, [reactFlowNodes, reactFlowEdges, maxHistorySize, debounceMs]);

	const handleUndo = useCallback(() => {
		const currentIndex = historyIndexRef.current;
		if (currentIndex <= 0) {
			return;
		}
		const newIndex = currentIndex - 1;
		const entry = history[newIndex];
		if (!entry) {
			return;
		}

		const nodesSnapshot = cloneNodes(entry.nodes);
		const edgesSnapshot = cloneEdges(entry.edges);

		// Compute diff BEFORE applying changes (current state -> target state)
		// This generates the changes needed to sync to the database
		const { changes, summary } = diffGraphStates(
			reactFlowNodes,
			reactFlowEdges,
			nodesSnapshot,
			edgesSnapshot,
		);

		// Apply the visual state changes
		setReactFlowNodes(nodesSnapshot);
		setReactFlowEdges(edgesSnapshot);
		applyGraphNodes?.(nodesSnapshot);
		applyGraphEdges?.(edgesSnapshot);

		// Track changes for sync (persists undo to database)
		if (changes.length > 0) {
			useGraphStore.getState().applyUndoRedoChanges(changes);
			console.log("[History] Undo changes:", summary);
		}

		historyIndexRef.current = newIndex;
		setHistoryIndex(newIndex);
		showInfo?.("Undo", "Action undone");
	}, [
		history,
		reactFlowNodes,
		reactFlowEdges,
		setReactFlowNodes,
		setReactFlowEdges,
		applyGraphNodes,
		applyGraphEdges,
		showInfo,
	]);

	const handleRedo = useCallback(() => {
		const currentIndex = historyIndexRef.current;
		if (currentIndex >= history.length - 1) {
			return;
		}
		const newIndex = currentIndex + 1;
		const entry = history[newIndex];
		if (!entry) {
			return;
		}

		const nodesSnapshot = cloneNodes(entry.nodes);
		const edgesSnapshot = cloneEdges(entry.edges);

		// Compute diff BEFORE applying changes (current state -> target state)
		// This generates the changes needed to sync to the database
		const { changes, summary } = diffGraphStates(
			reactFlowNodes,
			reactFlowEdges,
			nodesSnapshot,
			edgesSnapshot,
		);

		// Apply the visual state changes
		setReactFlowNodes(nodesSnapshot);
		setReactFlowEdges(edgesSnapshot);
		applyGraphNodes?.(nodesSnapshot);
		applyGraphEdges?.(edgesSnapshot);

		// Track changes for sync (persists redo to database)
		if (changes.length > 0) {
			useGraphStore.getState().applyUndoRedoChanges(changes);
			console.log("[History] Redo changes:", summary);
		}

		historyIndexRef.current = newIndex;
		setHistoryIndex(newIndex);
		showInfo?.("Redo", "Action redone");
	}, [
		history,
		reactFlowNodes,
		reactFlowEdges,
		setReactFlowNodes,
		setReactFlowEdges,
		applyGraphNodes,
		applyGraphEdges,
		showInfo,
	]);

	const canUndo = historyIndex > 0;
	const canRedo = historyIndex >= 0 && historyIndex < history.length - 1;

	return {
		saveToHistory,
		handleUndo,
		handleRedo,
		historyIndex,
		canUndo,
		canRedo,
	};
}
