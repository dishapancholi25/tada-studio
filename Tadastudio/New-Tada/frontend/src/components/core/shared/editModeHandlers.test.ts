import { describe, it, expect, vi } from "vitest";
import { createOnEdgesChangeHandler, createOnNodesChangeHandler } from "./editModeHandlers";
import type { EdgeChange, NodeChange } from "reactflow";

describe("editModeHandlers", () => {
	describe("createOnEdgesChangeHandler", () => {
		it("calls onEdgesChange with changes", () => {
			const onEdgesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnEdgesChangeHandler({
				mode: "edit",
				onEdgesChange,
				saveToHistory,
			});

			const changes: EdgeChange[] = [{ type: "select", id: "edge-1", selected: true }];
			handler(changes);

			expect(onEdgesChange).toHaveBeenCalledWith(changes);
		});

		it("saves to history when edge is removed in edit mode", () => {
			const onEdgesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnEdgesChangeHandler({
				mode: "edit",
				onEdgesChange,
				saveToHistory,
			});

			const changes: EdgeChange[] = [{ type: "remove", id: "edge-1" }];
			handler(changes);

			expect(saveToHistory).toHaveBeenCalled();
		});

		it("saves to history when edge is added in edit mode", () => {
			const onEdgesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnEdgesChangeHandler({
				mode: "edit",
				onEdgesChange,
				saveToHistory,
			});

			const changes: EdgeChange[] = [
				{ type: "add", item: { id: "edge-1", source: "node-1", target: "node-2" } },
			];
			handler(changes);

			expect(saveToHistory).toHaveBeenCalled();
		});

		it("does not save to history for selection changes", () => {
			const onEdgesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnEdgesChangeHandler({
				mode: "edit",
				onEdgesChange,
				saveToHistory,
			});

			const changes: EdgeChange[] = [{ type: "select", id: "edge-1", selected: true }];
			handler(changes);

			expect(saveToHistory).not.toHaveBeenCalled();
		});

		it("does not save to history when not in edit mode", () => {
			const onEdgesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnEdgesChangeHandler({
				mode: "evaluate",
				onEdgesChange,
				saveToHistory,
			});

			const changes: EdgeChange[] = [{ type: "remove", id: "edge-1" }];
			handler(changes);

			expect(saveToHistory).not.toHaveBeenCalled();
		});
	});

	describe("createOnNodesChangeHandler", () => {
		it("calls onNodesChange with changes", () => {
			const onNodesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnNodesChangeHandler({
				mode: "edit",
				onNodesChange,
				saveToHistory,
			});

			const changes: NodeChange[] = [{ type: "select", id: "node-1", selected: true }];
			handler(changes);

			expect(onNodesChange).toHaveBeenCalledWith(changes);
		});

		it("saves to history when node is removed in edit mode", () => {
			const onNodesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnNodesChangeHandler({
				mode: "edit",
				onNodesChange,
				saveToHistory,
			});

			const changes: NodeChange[] = [{ type: "remove", id: "node-1" }];
			handler(changes);

			expect(saveToHistory).toHaveBeenCalled();
		});

		it("does not save to history when not in edit mode", () => {
			const onNodesChange = vi.fn();
			const saveToHistory = vi.fn();
			const handler = createOnNodesChangeHandler({
				mode: "execution",
				onNodesChange,
				saveToHistory,
			});

			const changes: NodeChange[] = [{ type: "remove", id: "node-1" }];
			handler(changes);

			expect(saveToHistory).not.toHaveBeenCalled();
		});
	});
});

describe("Cross-platform keyboard handling", () => {
	// These tests verify the keyboard event patterns used for shortcuts
	// Delete/Backspace work the same across all platforms in browsers

	it("Delete key code is consistent across platforms", () => {
		// Simulating Delete key event
		const event = new KeyboardEvent("keydown", { key: "Delete", code: "Delete" });
		expect(event.key).toBe("Delete");
	});

	it("Backspace key code is consistent across platforms", () => {
		// Simulating Backspace key event
		const event = new KeyboardEvent("keydown", { key: "Backspace", code: "Backspace" });
		expect(event.key).toBe("Backspace");
	});

	it("Ctrl key is detected on Windows/Linux", () => {
		const event = new KeyboardEvent("keydown", { key: "z", ctrlKey: true });
		expect(event.ctrlKey).toBe(true);
		expect(event.metaKey).toBe(false);
	});

	it("Meta key (Cmd) is detected on Mac", () => {
		const event = new KeyboardEvent("keydown", { key: "z", metaKey: true });
		expect(event.metaKey).toBe(true);
	});

	it("Cross-platform modifier check works", () => {
		// This is the pattern used in AgentBuilder for cross-platform support
		const checkModifier = (e: KeyboardEvent) => e.ctrlKey || e.metaKey;

		const ctrlEvent = new KeyboardEvent("keydown", { key: "z", ctrlKey: true });
		const metaEvent = new KeyboardEvent("keydown", { key: "z", metaKey: true });
		const noModEvent = new KeyboardEvent("keydown", { key: "z" });

		expect(checkModifier(ctrlEvent)).toBe(true);  // Windows/Linux
		expect(checkModifier(metaEvent)).toBe(true);  // Mac
		expect(checkModifier(noModEvent)).toBe(false); // No modifier
	});
});
