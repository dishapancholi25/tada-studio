"use client";

import { useCallback, useMemo, useState } from "react";
import type { Node } from "reactflow";

export type SelectionPanelKey =
	| "node"
	| "condition"
	| "subWorkflow"
	| "documentSearch"
	| "documentRetrieve"
	| "documentLoad"
	| "databaseQuery"
	| "databaseInsert"
	| "databaseQueryAction"
	| "httpRequest"
	| "httpRequestAction"
	| "emailSend"
	| "emailSendTool"
	| "fileRead"
	| "fileWrite"
	| "webSearch"
	| "mcpServer"
	| "checkpoint"
	| "end"
	| "forEach"
	| "codeExecutor"
	| "execution";

export type PanelData = Node | (Record<string, unknown> & { id: string });

export interface SelectionState {
	key: SelectionPanelKey;
	data: PanelData;
}

export interface UseSelectionPanelsResult {
	selectionMap: Record<SelectionPanelKey, PanelData | null>;
	openPanel: (key: SelectionPanelKey, data: PanelData) => void;
	closePanel: (key: SelectionPanelKey) => void;
	resetPanels: () => void;
	isAnyPanelOpen: boolean;
	selection: SelectionState | null;
}

export function useSelectionPanels(): UseSelectionPanelsResult {
	const [selectionMap, setSelectionMap] = useState<
		Record<SelectionPanelKey, PanelData | null>
	>({
		node: null,
		condition: null,
		subWorkflow: null,
		documentSearch: null,
		documentRetrieve: null,
		documentLoad: null,
		databaseQuery: null,
		databaseInsert: null,
		databaseQueryAction: null,
		httpRequest: null,
		httpRequestAction: null,
		emailSend: null,
		emailSendTool: null,
		fileRead: null,
		fileWrite: null,
		webSearch: null,
		mcpServer: null,
		checkpoint: null,
		end: null,
		forEach: null,
		codeExecutor: null,
		execution: null,
	});

	const [selection, setSelection] = useState<SelectionState | null>(null);

	const openPanel = useCallback((key: SelectionPanelKey, data: PanelData) => {
		setSelectionMap((prev) => ({
			...prev,
			[key]: data,
		}));
		setSelection({ key, data });
	}, []);

	const closePanel = useCallback((key: SelectionPanelKey) => {
		setSelectionMap((prev) => ({
			...prev,
			[key]: null,
		}));
		setSelection((current) => (current?.key === key ? null : current));
	}, []);

	const resetPanels = useCallback(() => {
		setSelectionMap({
			node: null,
			condition: null,
			subWorkflow: null,
			documentSearch: null,
			documentRetrieve: null,
			documentLoad: null,
			databaseQuery: null,
			databaseInsert: null,
			databaseQueryAction: null,
			httpRequest: null,
			httpRequestAction: null,
			emailSend: null,
			emailSendTool: null,
			fileRead: null,
			fileWrite: null,
			webSearch: null,
			mcpServer: null,
			checkpoint: null,
			end: null,
			forEach: null,
			codeExecutor: null,
			execution: null,
		});
		setSelection(null);
	}, []);

	const isAnyPanelOpen = useMemo(() => {
		return Object.values(selectionMap).some(Boolean);
	}, [selectionMap]);

	return {
		selectionMap,
		openPanel,
		closePanel,
		resetPanels,
		isAnyPanelOpen,
		selection,
	};
}
