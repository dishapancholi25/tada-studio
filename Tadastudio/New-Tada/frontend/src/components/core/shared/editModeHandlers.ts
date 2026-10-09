"use client";

import type { MutableRefObject } from "react";
import type { EdgeChange, NodeChange, XYPosition } from "reactflow";

interface OnNodesChangeOptions {
	mode: "edit" | "evaluate" | "execution";
	onNodesChange: (changes: NodeChange[]) => void;
	saveToHistory?: () => void;
	updateNodePosition?: (
		nodeId: string,
		position: XYPosition,
	) => void | Promise<void>;
	positionUpdateTimeoutRef?: MutableRefObject<NodeJS.Timeout | null>;
	debounceMs?: number;
}

interface OnEdgesChangeOptions {
	mode: "edit" | "evaluate" | "execution";
	onEdgesChange: (changes: EdgeChange[]) => void;
	saveToHistory?: () => void;
}

function callSafely<T>(
	fn: ((...args: any[]) => T) | undefined,
	...args: any[]
) {
	if (!fn) return;
	try {
		const result = fn(...args);
		if (
			result &&
			typeof result === "object" &&
			result !== null &&
			"then" in result &&
			typeof (result as any).then === "function"
		) {
			(result as unknown as Promise<unknown>).catch(() => {
				/* swallow update errors */
			});
		}
	} catch (error) {
		// Swallow errors to match previous behaviour where failures were only logged
	}
}

export function createOnNodesChangeHandler({
	mode,
	onNodesChange,
	saveToHistory,
	updateNodePosition,
	positionUpdateTimeoutRef,
	debounceMs = 500,
}: OnNodesChangeOptions) {
	return (changes: NodeChange[]) => {
		onNodesChange(changes);

		const inEditMode = mode === "edit";

		if (inEditMode && saveToHistory) {
			const significantChange = changes.some(
				(change) =>
					change.type === "add" ||
					change.type === "remove" ||
					(change.type === "position" && !change.dragging),
			);

			if (significantChange) {
				saveToHistory();
			}
		}

		if (!updateNodePosition) {
			return;
		}

		changes.forEach((change) => {
			if (change.type !== "position" || !change.position) {
				return;
			}

			if (!change.dragging) {
				callSafely(updateNodePosition, change.id, change.position);
			} else if (positionUpdateTimeoutRef) {
				if (positionUpdateTimeoutRef.current) {
					clearTimeout(positionUpdateTimeoutRef.current);
				}
				positionUpdateTimeoutRef.current = setTimeout(() => {
					callSafely(
						updateNodePosition,
						change.id,
						change.position as XYPosition,
					);
				}, debounceMs);
			}
		});
	};
}

export function createOnEdgesChangeHandler({
	mode,
	onEdgesChange,
	saveToHistory,
}: OnEdgesChangeOptions) {
	return (changes: EdgeChange[]) => {
		onEdgesChange(changes);

		if (mode !== "edit" || !saveToHistory) {
			return;
		}

		const significantChange = changes.some(
			(change) => change.type === "add" || change.type === "remove",
		);

		if (significantChange) {
			saveToHistory();
		}
	};
}
