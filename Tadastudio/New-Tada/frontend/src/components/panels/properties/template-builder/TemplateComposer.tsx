"use client";

import clsx from "clsx";
import {
	useCallback,
	useEffect,
	useImperativeHandle,
	useRef,
	useState,
	forwardRef,
} from "react";
import { getNodeColorRgb } from "../inputSourceTypes";
import type {
	TemplateSegment,
	VariableInfo,
	VariableSegment,
} from "./templateBuilderTypes";

export interface TemplateComposerHandle {
	insertAtCursor: (variable: VariableInfo) => void;
}

interface TemplateComposerProps {
	segments: TemplateSegment[];
	onSegmentsChange: (segments: TemplateSegment[]) => void;
	variables: VariableInfo[];
}

const VARIABLE_ATTR = "data-variable-key";

function checkEmpty(segs: TemplateSegment[]): boolean {
	return !segs.some(
		(s) =>
			(s.type === "text" && s.value.length > 0) ||
			s.type === "variable",
	);
}

const TemplateComposer = forwardRef<
	TemplateComposerHandle,
	TemplateComposerProps
>(function TemplateComposer({ segments, onSegmentsChange, variables }, ref) {
	const editorRef = useRef<HTMLDivElement>(null);
	// Tracks the last segments array WE emitted via onSegmentsChange.
	// If the incoming `segments` prop is the same reference, the change came
	// from user typing and we skip the DOM rebuild (the DOM already reflects it).
	// External changes (modal reopen, variable insert via hook) produce a
	// different reference, so buildDOM runs.
	const lastEmittedRef = useRef<TemplateSegment[] | null>(null);
	const [isDragOver, setIsDragOver] = useState(false);
	const [isEmpty, setIsEmpty] = useState(checkEmpty(segments));

	// ── Build DOM from segments (parameter-based, no closure on segments) ──
	const buildDOM = useCallback((segs: TemplateSegment[]) => {
		const editor = editorRef.current;
		if (!editor) return;

		// Save cursor position
		const selection = window.getSelection();
		let savedNodeIndex = -1;
		let savedOffset = 0;
		if (
			selection &&
			selection.rangeCount > 0 &&
			editor.contains(selection.anchorNode)
		) {
			const range = selection.getRangeAt(0);
			const walker = document.createTreeWalker(
				editor,
				NodeFilter.SHOW_TEXT,
			);
			let idx = 0;
			let node: globalThis.Node | null;
			while ((node = walker.nextNode())) {
				if (node === range.startContainer) {
					savedNodeIndex = idx;
					savedOffset = range.startOffset;
					break;
				}
				idx++;
			}
		}

		editor.innerHTML = "";

		for (const segment of segs) {
			if (segment.type === "text") {
				const textNode = document.createTextNode(
					segment.value || "\u200B",
				);
				editor.appendChild(textNode);
			} else {
				const chip = createChipElement(segment);
				editor.appendChild(chip);
				// Zero-width space after chip for cursor placement
				editor.appendChild(document.createTextNode("\u200B"));
			}
		}

		setIsEmpty(checkEmpty(segs));

		// Restore cursor position
		if (savedNodeIndex >= 0) {
			requestAnimationFrame(() => {
				try {
					const walker = document.createTreeWalker(
						editor,
						NodeFilter.SHOW_TEXT,
					);
					let idx = 0;
					let node: globalThis.Node | null;
					while ((node = walker.nextNode())) {
						if (idx === savedNodeIndex) {
							const sel = window.getSelection();
							const r = document.createRange();
							r.setStart(
								node,
								Math.min(
									savedOffset,
									node.textContent?.length ?? 0,
								),
							);
							r.collapse(true);
							sel?.removeAllRanges();
							sel?.addRange(r);
							break;
						}
						idx++;
					}
				} catch {
					// Cursor restore can fail safely
				}
			});
		}
	}, []); // No dependencies — stable function

	// ── Sync DOM from segments only on external changes ──
	useEffect(() => {
		// If we emitted these segments ourselves, the DOM already matches — skip.
		if (
			lastEmittedRef.current !== null &&
			segments === lastEmittedRef.current
		) {
			return;
		}
		buildDOM(segments);
		lastEmittedRef.current = segments;
	}, [segments, buildDOM]);

	// ── Parse DOM back into segments ──
	const parseDOMToSegments = useCallback((): TemplateSegment[] => {
		const editor = editorRef.current;
		if (!editor) return [{ type: "text", value: "" }];

		const result: TemplateSegment[] = [];

		for (const child of Array.from(editor.childNodes)) {
			if (child.nodeType === Node.TEXT_NODE) {
				const text = (child.textContent ?? "").replace(/\u200B/g, "");
				const last = result[result.length - 1];
				if (last?.type === "text") {
					last.value += text;
				} else {
					result.push({ type: "text", value: text });
				}
			} else if (child instanceof HTMLBRElement) {
				// Handle <br> elements (browser may insert these)
				const last = result[result.length - 1];
				if (last?.type === "text") {
					last.value += "\n";
				} else {
					result.push({ type: "text", value: "\n" });
				}
			} else if (child instanceof HTMLElement) {
				const varKey = child.getAttribute(VARIABLE_ATTR);
				if (varKey) {
					const varInfo = variables.find((v) => v.key === varKey);
					result.push({
						type: "variable",
						variableKey: varKey,
						displayLabel: varInfo?.displayLabel ?? varKey,
						nodeType: varInfo?.nodeType,
					});
				} else {
					// Unknown element — extract text content
					const text = (child.textContent ?? "").replace(
						/\u200B/g,
						"",
					);
					const last = result[result.length - 1];
					if (last?.type === "text") {
						last.value += text;
					} else {
						result.push({ type: "text", value: text });
					}
				}
			}
		}

		if (result.length === 0) {
			result.push({ type: "text", value: "" });
		}

		return result;
	}, [variables]);

	// ── Notify parent of DOM changes ──
	const handleInput = useCallback(() => {
		const newSegments = parseDOMToSegments();
		lastEmittedRef.current = newSegments;
		onSegmentsChange(newSegments);
		setIsEmpty(checkEmpty(newSegments));
	}, [parseDOMToSegments, onSegmentsChange]);

	// ── Paste: strip HTML, insert plain text via Selection API ──
	const handlePaste = useCallback(
		(e: React.ClipboardEvent) => {
			e.preventDefault();
			const text = e.clipboardData.getData("text/plain");
			const sel = window.getSelection();
			if (sel?.rangeCount) {
				const range = sel.getRangeAt(0);
				range.deleteContents();
				const textNode = document.createTextNode(text);
				range.insertNode(textNode);
				range.setStartAfter(textNode);
				range.collapse(true);
				sel.removeAllRanges();
				sel.addRange(range);
				handleInput();
			}
		},
		[handleInput],
	);

	// ── Chip removal ──
	const handleChipRemove = useCallback(
		(varKey: string) => {
			const editor = editorRef.current;
			if (!editor) return;

			const chip = editor.querySelector(
				`[${VARIABLE_ATTR}="${varKey}"]`,
			);
			if (chip) {
				const next = chip.nextSibling;
				if (
					next?.nodeType === Node.TEXT_NODE &&
					next.textContent === "\u200B"
				) {
					next.remove();
				}
				chip.remove();
				handleInput();
			}
		},
		[handleInput],
	);

	// ── Insert variable at cursor ──
	const insertAtCursor = useCallback(
		(variable: VariableInfo) => {
			const editor = editorRef.current;
			if (!editor) return;

			editor.focus();
			const selection = window.getSelection();

			const chip = createChipElement({
				type: "variable",
				variableKey: variable.key,
				displayLabel: variable.displayLabel,
				nodeType: variable.nodeType,
			});

			if (
				selection &&
				selection.rangeCount > 0 &&
				editor.contains(selection.anchorNode)
			) {
				const range = selection.getRangeAt(0);
				range.deleteContents();
				const space = document.createTextNode("\u200B");
				range.insertNode(space);
				range.insertNode(chip);

				const newRange = document.createRange();
				newRange.setStartAfter(space);
				newRange.collapse(true);
				selection.removeAllRanges();
				selection.addRange(newRange);
			} else {
				editor.appendChild(chip);
				editor.appendChild(document.createTextNode("\u200B"));

				const sel = window.getSelection();
				const range = document.createRange();
				range.selectNodeContents(editor);
				range.collapse(false);
				sel?.removeAllRanges();
				sel?.addRange(range);
			}

			handleInput();
		},
		[handleInput],
	);

	useImperativeHandle(ref, () => ({ insertAtCursor }), [insertAtCursor]);

	// ── Drag-and-drop ──
	const handleDragOver = useCallback((e: React.DragEvent) => {
		if (e.dataTransfer.types.includes("application/x-template-variable")) {
			e.preventDefault();
			e.dataTransfer.dropEffect = "copy";
			setIsDragOver(true);
		}
	}, []);

	const handleDragLeave = useCallback(() => {
		setIsDragOver(false);
	}, []);

	const handleDrop = useCallback(
		(e: React.DragEvent) => {
			e.preventDefault();
			setIsDragOver(false);

			const data = e.dataTransfer.getData(
				"application/x-template-variable",
			);
			if (!data) return;

			try {
				const variable: VariableInfo = JSON.parse(data);
				const editor = editorRef.current;
				if (!editor) return;

				// eslint-disable-next-line @typescript-eslint/no-explicit-any
				const caretPos = (
					document as Record<string, any>
				).caretPositionFromPoint?.(e.clientX, e.clientY);
				const caretRange =
					document.caretRangeFromPoint?.(e.clientX, e.clientY) ??
					caretPos;

				if (caretRange) {
					const selection = window.getSelection();
					let range: Range;

					if (caretRange instanceof Range) {
						range = caretRange;
					} else {
						range = document.createRange();
						range.setStart(
							caretRange.offsetNode,
							caretRange.offset,
						);
						range.collapse(true);
					}

					selection?.removeAllRanges();
					selection?.addRange(range);
				}

				insertAtCursor(variable);
			} catch {
				// Invalid JSON, ignore
			}
		},
		[insertAtCursor],
	);

	// ── Keyboard shortcuts ──
	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			// Enter: insert newline + cursor placeholder (prevents <div> creation)
			if (e.key === "Enter") {
				e.preventDefault();
				const sel = window.getSelection();
				if (sel?.rangeCount) {
					const range = sel.getRangeAt(0);
					range.deleteContents();
					const nl = document.createTextNode("\n");
					const cursor = document.createTextNode("\u200B");
					// insertNode inserts at range start, so insert cursor first,
					// then newline (which goes before cursor)
					range.insertNode(cursor);
					range.insertNode(nl);
					range.setStart(cursor, 0);
					range.collapse(true);
					sel.removeAllRanges();
					sel.addRange(range);
					handleInput();
				}
			}
			// Backspace on chip
			if (e.key === "Backspace") {
				const selection = window.getSelection();
				if (
					selection &&
					selection.isCollapsed &&
					selection.anchorNode
				) {
					const prev =
						selection.anchorOffset === 0
							? selection.anchorNode.previousSibling
							: null;
					if (
						prev instanceof HTMLElement &&
						prev.hasAttribute(VARIABLE_ATTR)
					) {
						e.preventDefault();
						const varKey = prev.getAttribute(VARIABLE_ATTR);
						if (varKey) handleChipRemove(varKey);
					}
				}
			}
		},
		[handleChipRemove, handleInput],
	);

	return (
		<div className="flex h-full flex-col">
			<div className="mb-2 flex items-center gap-1.5">
				<span className="text-[0.6rem] font-semibold capitalize text-slate-600">
					Template
				</span>
				<span className="text-[10px] text-slate-500">
					Type text and drag or click variables to insert
				</span>
			</div>

			<div
				className={clsx(
					"relative flex-1 rounded-[4px] border bg-white p-1 transition-colors",
					isDragOver
						? "border-orange-500 ring-2 ring-orange-500/15"
						: "border-slate-200",
				)}
			>
				{isEmpty && (
					<div className="pointer-events-none absolute inset-0 flex px-4 py-2.5 font-mono text-sm text-slate-400">
						Type your template here, or click a variable from the
						sidebar to insert it...
					</div>
				)}
				<div
					ref={editorRef}
					contentEditable
					suppressContentEditableWarning
					role="textbox"
					aria-multiline="true"
					aria-label="Template editor"
					onInput={handleInput}
					onPaste={handlePaste}
					onKeyDown={handleKeyDown}
					onDragOver={handleDragOver}
					onDragLeave={handleDragLeave}
					onDrop={handleDrop}
					className="relative min-h-[200px] w-full whitespace-pre-wrap break-words rounded-[4px] px-3 py-2 font-mono text-sm leading-relaxed text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
					style={{ wordBreak: "break-word" }}
				/>
			</div>
		</div>
	);
});

function createChipElement(segment: VariableSegment): HTMLSpanElement {
	const chip = document.createElement("span");
	chip.setAttribute(VARIABLE_ATTR, segment.variableKey);
	chip.contentEditable = "false";

	const colorRgb = segment.nodeType
		? getNodeColorRgb(segment.nodeType)
		: "var(--color-primary-rgb)";

	const isBuiltin =
		segment.variableKey === "original" ||
		segment.variableKey === "previous";
	const chipColor = isBuiltin ? "var(--color-primary-rgb)" : colorRgb;

	chip.className =
		"inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-mono cursor-default select-none align-middle mx-0.5 border transition-colors";
	chip.style.backgroundColor = `rgba(${chipColor}, 0.12)`;
	chip.style.borderColor = `rgba(${chipColor}, 0.35)`;
	chip.style.color = `rgba(${chipColor}, 0.9)`;

	const labelSpan = document.createElement("span");
	labelSpan.textContent = segment.displayLabel;
	chip.appendChild(labelSpan);

	const removeBtn = document.createElement("button");
	removeBtn.type = "button";
	removeBtn.className =
		"ml-0.5 rounded-full p-0.5 transition-colors hover:bg-red-50 hover:text-red-700";
	removeBtn.setAttribute("aria-label", `Remove ${segment.displayLabel}`);
	removeBtn.innerHTML =
		'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
	removeBtn.addEventListener("mousedown", (e) => {
		e.preventDefault();
		e.stopPropagation();
		const next = chip.nextSibling;
		if (
			next?.nodeType === Node.TEXT_NODE &&
			next.textContent === "\u200B"
		) {
			next.remove();
		}
		chip.remove();
		const editor =
			chip.closest("[contenteditable]") || chip.parentElement;
		editor?.dispatchEvent(new Event("input", { bubbles: true }));
	});

	chip.appendChild(removeBtn);

	return chip;
}

export default TemplateComposer;
