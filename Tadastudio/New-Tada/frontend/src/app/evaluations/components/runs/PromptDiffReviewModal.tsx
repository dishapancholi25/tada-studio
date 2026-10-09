"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Pencil, X } from "lucide-react";
import { DiffEditor, type Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";

// ── Types ───────────────────────────────────────────────────────────

interface PromptDiffReviewModalProps {
	currentValue: string;
	proposedValue: string;
	nodeName: string;
	fieldLabel?: string;
	onApply: (editedValue: string) => void;
	onCancel: () => void;
	applying?: boolean;
}

// ── Helpers ─────────────────────────────────────────────────────────

function countDiffStats(original: string, modified: string) {
	const aLines = original.split("\n");
	const bLines = modified.split("\n");
	const n = aLines.length;
	const m = bLines.length;

	// Simple LCS-based count
	const dp: number[][] = Array.from({ length: n + 1 }, () =>
		new Array(m + 1).fill(0),
	);
	for (let i = n - 1; i >= 0; i--) {
		for (let j = m - 1; j >= 0; j--) {
			dp[i][j] =
				aLines[i] === bLines[j]
					? dp[i + 1][j + 1] + 1
					: Math.max(dp[i + 1][j], dp[i][j + 1]);
		}
	}
	const common = dp[0][0];
	return { added: m - common, removed: n - common };
}

// ── Component ───────────────────────────────────────────────────────

export default function PromptDiffReviewModal({
	currentValue,
	proposedValue,
	nodeName,
	fieldLabel = "System Prompt",
	onApply,
	onCancel,
	applying = false,
}: PromptDiffReviewModalProps) {
	const [editedValue, setEditedValue] = useState(proposedValue);
	const [editing, setEditing] = useState(false);
	const editorRef = useRef<editor.IStandaloneDiffEditor | null>(null);

	const isModified = editedValue !== proposedValue;
	const stats = countDiffStats(currentValue, editedValue);

	// Keep the modified model in sync when editedValue changes externally (e.g. Reset)
	const updateModifiedModel = useCallback((value: string) => {
		const modifiedModel = editorRef.current?.getModifiedEditor().getModel();
		if (modifiedModel && modifiedModel.getValue() !== value) {
			modifiedModel.setValue(value);
		}
	}, []);

	// Toggle read-only on the modified side based on editing state
	useEffect(() => {
		const modifiedEditor = editorRef.current?.getModifiedEditor();
		if (modifiedEditor) {
			modifiedEditor.updateOptions({ readOnly: !editing });
		}
	}, [editing]);

	// Close on Escape
	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") {
				if (editing) {
					setEditing(false);
				} else {
					onCancel();
				}
			}
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, [onCancel, editing]);

	const handleEditorDidMount = useCallback(
		(diffEditor: editor.IStandaloneDiffEditor) => {
			editorRef.current = diffEditor;
			// Start read-only
			diffEditor.getModifiedEditor().updateOptions({ readOnly: !editing });

			// Listen for changes on the modified side
			diffEditor.getModifiedEditor().onDidChangeModelContent(() => {
				const value = diffEditor.getModifiedEditor().getValue();
				setEditedValue(value);
			});
		},
		[editing],
	);

	const handleBeforeMount = useCallback((monaco: Monaco) => {
		monaco.editor.defineTheme("promptDiffDark", {
			base: "vs-dark",
			inherit: true,
			rules: [],
			colors: {
				"editor.background": "#161616",
				"diffEditor.insertedTextBackground": "#0DA93118",
				"diffEditor.removedTextBackground": "#ef444418",
				"diffEditor.insertedLineBackground": "#0DA93110",
				"diffEditor.removedLineBackground": "#ef444410",
				"editorLineNumber.foreground": "#ffffff30",
				"editorGutter.background": "#161616",
			},
		});
	}, []);

	const handleReset = useCallback(() => {
		setEditedValue(proposedValue);
		updateModifiedModel(proposedValue);
	}, [proposedValue, updateModifiedModel]);

	return (
		<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm">
			<div
				data-tutorial="prompt-diff-modal"
				className="flex w-full max-w-6xl flex-col rounded-2xl border border-slate-200 bg-white shadow-[0_25px_60px_rgba(0,0,0,0.15)]"
				style={{ height: "85vh" }}
			>
				{/* Header */}
				<div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 shrink-0">
					<div>
						<h3 className="text-base font-semibold text-slate-900">
							Review Prompt Change
						</h3>
						<p className="mt-0.5 text-xs text-slate-500">
							<span className="text-slate-600">{nodeName}</span>
							{" \u2014 "}
							{fieldLabel}
							{isModified && (
								<span className="ml-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-1.5 py-0.5 text-[10px] text-amber-300">
									edited
								</span>
							)}
						</p>
					</div>
					<div className="flex items-center gap-4">
						<div className="flex items-center gap-3 text-xs text-slate-500">
							{stats.added > 0 && (
								<span className="text-emerald-400">
									+{stats.added} line{stats.added !== 1 ? "s" : ""}
								</span>
							)}
							{stats.removed > 0 && (
								<span className="text-red-400">
									&minus;{stats.removed} line
									{stats.removed !== 1 ? "s" : ""}
								</span>
							)}
							{stats.added === 0 && stats.removed === 0 && (
								<span>No changes</span>
							)}
						</div>
						<button
							type="button"
							onClick={onCancel}
							className="rounded-lg p-1.5 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
						>
							<X size={18} />
						</button>
					</div>
				</div>

				{/* Column headers */}
				<div className="flex shrink-0 border-b border-slate-200 bg-slate-50">
					<div className="w-1/2 px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-r border-slate-200">
						Current
					</div>
					<div className="w-1/2 px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
						<span>Proposed {isModified ? "(edited)" : ""}</span>
						<button
							type="button"
							onClick={() => setEditing(!editing)}
							className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium transition ${
								editing
									? "bg-amber-400/15 text-amber-300 border border-amber-400/30"
									: "text-slate-500 hover:text-slate-600 hover:bg-slate-100"
							}`}
						>
							<Pencil size={10} />
							{editing ? "Editing" : "Edit"}
						</button>
					</div>
				</div>

				{/* Monaco Diff Editor */}
				<div data-tutorial="prompt-diff-editor" className="flex-1 min-h-0 overflow-hidden">
					<DiffEditor
						original={currentValue}
						modified={editedValue}
						language="markdown"
						theme="promptDiffDark"
						beforeMount={handleBeforeMount}
						onMount={handleEditorDidMount}
						options={{
							readOnly: false,
							originalEditable: false,
							renderSideBySide: true,
							minimap: { enabled: true },
							fontSize: 13,
							lineHeight: 22,
							fontFamily:
								"ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace",
							wordWrap: "on",
							scrollBeyondLastLine: false,
							renderOverviewRuler: true,
							diffWordWrap: "on",
							scrollbar: {
								verticalScrollbarSize: 8,
								horizontalScrollbarSize: 8,
							},
							padding: { top: 8, bottom: 8 },
							overviewRulerBorder: false,
							ignoreTrimWhitespace: false,
							renderIndicators: true,
							useInlineViewWhenSpaceIsLimited: false,
						}}
					/>
				</div>

				{/* Footer */}
				<div className="flex items-center justify-between border-t border-slate-200 px-6 py-3.5 shrink-0">
					<div className="text-xs text-slate-400">
						{editing
							? "Editing proposed prompt. Press Escape to return to read-only view."
							: "Review the diff above. Click Edit to modify the proposed prompt."}
					</div>
					<div className="flex items-center gap-2">
						<button
							type="button"
							onClick={onCancel}
							disabled={applying}
							className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-4 py-2 text-sm text-slate-700 transition-all hover:border-[rgba(var(--color-primary-rgb),0.50)] hover:bg-[color:var(--color-surface)]/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40"
						>
							Cancel
						</button>
						{isModified && (
							<button
								type="button"
								onClick={handleReset}
								disabled={applying}
								className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-2 text-sm text-amber-300 transition-all hover:bg-amber-400/20 hover:border-amber-400/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/45 disabled:opacity-40"
							>
								Reset
							</button>
						)}
						<button
							type="button"
							data-tutorial="prompt-diff-apply-btn"
							onClick={() => onApply(editedValue)}
							disabled={applying}
							className="rounded-xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] px-5 py-2 text-sm font-semibold text-[color:var(--button-primary-text)] shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.25)] transition-all hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40 disabled:pointer-events-none"
						>
							{applying ? "Applying\u2026" : "Apply Change"}
						</button>
					</div>
				</div>
			</div>
		</div>
	);
}
