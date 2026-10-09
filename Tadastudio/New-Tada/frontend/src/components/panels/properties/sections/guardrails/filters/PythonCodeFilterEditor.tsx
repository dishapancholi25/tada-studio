import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, Maximize2, Minimize2, X } from "lucide-react";
import Editor, { type Monaco } from "@monaco-editor/react";
import type { editor } from "monaco-editor";

interface PythonCodeFilterEditorProps {
	pythonCode: string;
	onChange: (code: string) => void;
}

const DEFAULT_CODE = `def filter(content: str, direction: str, **context) -> dict:
    """
    Return a dict with:
      - "passed": bool (True = content is OK)
      - "message": str (description if triggered)
      - "content": str (modified content, for transform action)

    Args:
      - content: The text to filter
      - direction: "ingress" (before LLM) or "egress" (after LLM)
      - **context: Additional context (includes "action": "warn"/"block"/"transform")

    Available modules: re, json, math, datetime, hashlib, string,
    collections, llm_guard.
    Not available: file I/O, exec/eval, async
    """
    # Example: block content containing "forbidden"
    if "forbidden" in content.lower():
        return {"passed": False, "message": "Forbidden content detected"}
    return {"passed": True}
`;

function defineTheme(monaco: Monaco) {
	monaco.editor.defineTheme("pythonFilterDark", {
		base: "vs-dark",
		inherit: true,
		rules: [
			{ token: "keyword", foreground: "c586c0" },
			{ token: "string", foreground: "ce9178" },
			{ token: "comment", foreground: "6a9955" },
			{ token: "number", foreground: "b5cea8" },
			{ token: "type", foreground: "4ec9b0" },
			{ token: "identifier", foreground: "9cdcfe" },
		],
		colors: {
			"editor.background": "#00000000",
			"editor.lineHighlightBackground": "#ffffff08",
			"editorLineNumber.foreground": "#555555",
			"editorLineNumber.activeForeground": "#888888",
		},
	});
	monaco.editor.defineTheme("pythonFilterDarkModal", {
		base: "vs-dark",
		inherit: true,
		rules: [
			{ token: "keyword", foreground: "c586c0" },
			{ token: "string", foreground: "ce9178" },
			{ token: "comment", foreground: "6a9955" },
			{ token: "number", foreground: "b5cea8" },
			{ token: "type", foreground: "4ec9b0" },
			{ token: "identifier", foreground: "9cdcfe" },
		],
		colors: {
			"editor.background": "#161616",
			"editor.lineHighlightBackground": "#ffffff08",
			"editorLineNumber.foreground": "#555555",
			"editorLineNumber.activeForeground": "#888888",
		},
	});
}

const EDITOR_OPTIONS: editor.IStandaloneEditorConstructionOptions = {
	fontSize: 12,
	lineHeight: 20,
	fontFamily:
		"'SF Mono', Menlo, Monaco, Consolas, 'Liberation Mono', monospace",
	scrollBeyondLastLine: false,
	wordWrap: "on",
	tabSize: 4,
	insertSpaces: true,
	automaticLayout: true,
	lineNumbers: "on",
	lineNumbersMinChars: 3,
	folding: true,
	bracketPairColorization: { enabled: true },
	renderLineHighlight: "line",
	scrollbar: {
		vertical: "auto",
		horizontal: "auto",
		verticalScrollbarSize: 8,
		horizontalScrollbarSize: 8,
	},
	padding: { top: 8, bottom: 8 },
	suggest: {
		showKeywords: true,
		showSnippets: true,
		showFunctions: true,
		showVariables: true,
	},
	quickSuggestions: true,
};

// ── Fullscreen Modal ────────────────────────────────────────────────

function PythonEditorModal({
	code,
	onChange,
	onClose,
}: {
	code: string;
	onChange: (code: string) => void;
	onClose: () => void;
}) {
	const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (e.key === "Escape") onClose();
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, [onClose]);

	return createPortal(
		<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm">
			<div
				className="flex flex-col rounded-2xl border border-[color:var(--color-border)]/70 bg-gradient-to-br from-[rgba(28,28,28,0.98)] via-[rgba(20,20,20,0.98)] to-[rgba(14,14,14,0.99)] shadow-2xl"
				style={{ width: "90vw", height: "85vh", maxWidth: "1200px" }}
			>
				{/* Header */}
				<div className="flex shrink-0 items-center justify-between border-b border-slate-200 px-5 py-3">
					<div className="flex items-center gap-2.5">
						<div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/15">
							<span className="text-sm text-emerald-400">Py</span>
						</div>
						<div>
							<h3 className="text-sm font-semibold text-slate-900">
								Python Filter Editor
							</h3>
							<p className="text-[10px] text-slate-500">
								Define a filter(content, direction) function
							</p>
						</div>
					</div>
					<div className="flex items-center gap-2">
						<p className="mr-2 text-[10px] text-slate-400">
							Modules: re, json, math, datetime, hashlib, string, collections,
							llm_guard
						</p>
						<button
							type="button"
							onClick={onClose}
							className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
						>
							<X size={14} />
						</button>
					</div>
				</div>

				{/* Editor */}
				<div className="min-h-0 flex-1">
					<Editor
						height="100%"
						language="python"
						theme="pythonFilterDarkModal"
						value={code}
						onChange={(value) => onChange(value ?? "")}
						beforeMount={defineTheme}
						onMount={(ed) => {
							editorRef.current = ed;
							ed.focus();
						}}
						options={{
							...EDITOR_OPTIONS,
							fontSize: 13,
							lineHeight: 22,
							minimap: { enabled: true },
							padding: { top: 12, bottom: 12 },
						}}
					/>
				</div>

				{/* Footer */}
				<div className="flex shrink-0 items-center justify-between border-t border-slate-200 px-5 py-3">
					<p className="text-[10px] text-slate-400">
						No file I/O, exec/eval, or async
					</p>
					<button
						type="button"
						onClick={onClose}
						className="flex items-center gap-1.5 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-900 transition-colors hover:bg-slate-100"
					>
						<Minimize2 size={12} />
						Close
					</button>
				</div>
			</div>
		</div>,
		document.body,
	);
}

// ── Main Component ──────────────────────────────────────────────────

const DEPRECATED_IMPORT_PATTERN =
	/\b(?:from\s+(?:presidio_analyzer|presidio_anonymizer|detoxify)\b|import\s+(?:presidio_analyzer|presidio_anonymizer|detoxify)\b)/;

export default function PythonCodeFilterEditor({
	pythonCode,
	onChange,
}: PythonCodeFilterEditorProps) {
	const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
	const [expanded, setExpanded] = useState(false);

	const hasDeprecatedImports = useMemo(
		() => DEPRECATED_IMPORT_PATTERN.test(pythonCode),
		[pythonCode],
	);

	const handleMount = useCallback(
		(ed: editor.IStandaloneCodeEditor) => {
			editorRef.current = ed;
			if (!pythonCode) {
				onChange(DEFAULT_CODE);
			}
		},
		[pythonCode, onChange],
	);

	const codeValue = pythonCode || DEFAULT_CODE;

	return (
		<div>
			<div className="mb-1 flex items-center justify-between">
				<label className="block text-xs font-medium text-[color:var(--color-text-secondary)]">
					Python Filter Code
				</label>
				<button
					type="button"
					onClick={() => setExpanded(true)}
					className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-[color:var(--color-text-secondary)]/70 transition-colors hover:bg-[color:var(--color-bg-tertiary)] hover:text-[color:var(--color-text-secondary)]"
					title="Expand editor"
				>
					<Maximize2 size={10} />
					Expand
				</button>
			</div>
			{hasDeprecatedImports && (
				<div className="mb-2 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
					<AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
					<p className="text-[11px] leading-relaxed text-amber-300/90">
						This filter imports <code className="font-mono">presidio_analyzer</code>,{" "}
						<code className="font-mono">presidio_anonymizer</code>, or{" "}
						<code className="font-mono">detoxify</code> which have been removed.
						Use the built-in <strong>Toxicity Detection</strong> and{" "}
						<strong>PII Detection</strong> guardrails in the Behavioral section instead.
					</p>
				</div>
			)}
			<div className="overflow-hidden rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)]">
				<Editor
					height="280px"
					language="python"
					theme="pythonFilterDark"
					value={codeValue}
					onChange={(value) => onChange(value ?? "")}
					beforeMount={defineTheme}
					onMount={handleMount}
					options={{
						...EDITOR_OPTIONS,
						minimap: { enabled: false },
					}}
				/>
			</div>
			<p className="mt-1.5 text-[10px] text-[color:var(--color-text-secondary)]/70">
				Define a <code className="font-mono">filter(content, direction)</code>{" "}
				function. Available modules:{" "}
				<code className="font-mono">
					re, json, math, datetime, hashlib, string, collections,
					llm_guard
				</code>
				. No file I/O or exec/eval.
			</p>

			{expanded && (
				<PythonEditorModal
					code={codeValue}
					onChange={onChange}
					onClose={() => setExpanded(false)}
				/>
			)}
		</div>
	);
}
