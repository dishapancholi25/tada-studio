"use client";

import {
	Bold,
	CheckSquare,
	Code,
	Edit,
	Eye,
	Heading1,
	Heading2,
	Heading3,
	Italic,
	Link,
	List,
	ListOrdered,
	Minus,
	Quote,
	Save,
	XCircle,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import SimpleMarkdown from "@/components/utils/SimpleMarkdown";
import { wikiApi, type WikiTreeNode } from "@/lib/wiki-api";

export interface WikiSaveData {
	title: string;
	content: string;
	tags: string[];
	changeSummary?: string;
	parentId?: string | null;
}

interface WikiPageEditorProps {
	mode: "create" | "edit";
	initialTitle?: string;
	initialContent?: string;
	initialTags?: string;
	initialParentId?: string | null;
	pageId?: string;
	onSave: (data: WikiSaveData) => void;
	onCancel: () => void;
	saving?: boolean;
	error?: string | null;
}

interface ToolbarButtonProps {
	icon: React.ReactNode;
	onClick: () => void;
	tooltip: string;
	shortcut?: string;
}

function ToolbarButton({ icon, onClick, tooltip, shortcut }: ToolbarButtonProps) {
	const [showTooltip, setShowTooltip] = useState(false);

	return (
		<div className="relative">
			<button
				type="button"
				onClick={onClick}
				onMouseEnter={() => setShowTooltip(true)}
				onMouseLeave={() => setShowTooltip(false)}
				className="group rounded-lg border border-transparent p-2 transition-colors hover:border-orange-400 hover:bg-slate-50"
			>
				<div className="h-4 w-4 text-slate-600 transition-colors group-hover:text-slate-900">
					{icon}
				</div>
			</button>
			{showTooltip && (
				<div className="absolute left-1/2 top-full z-50 mt-1 -translate-x-1/2 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-800 shadow-[0_8px_24px_rgba(15,23,42,0.12)]">
					{tooltip}
					{shortcut && (
						<span className="ml-2 text-slate-500">
							{shortcut}
						</span>
					)}
				</div>
			)}
		</div>
	);
}

/** Flatten a tree into a list of {id, title, depth} entries, excluding excludeIds. */
function flattenTree(
	nodes: WikiTreeNode[],
	excludeIds: Set<string>,
	depth = 0,
): { id: string; title: string; depth: number }[] {
	const result: { id: string; title: string; depth: number }[] = [];
	for (const node of nodes) {
		if (excludeIds.has(node.id)) continue;
		result.push({ id: node.id, title: node.title, depth });
		result.push(...flattenTree(node.children, excludeIds, depth + 1));
	}
	return result;
}

/** Collect all descendant IDs (inclusive) of a node by ID from a tree. */
function collectDescendantIds(
	nodes: WikiTreeNode[],
	targetId: string,
): Set<string> {
	const ids = new Set<string>();

	function collectChildren(node: WikiTreeNode) {
		ids.add(node.id);
		for (const child of node.children) {
			collectChildren(child);
		}
	}

	function find(nodeList: WikiTreeNode[]): boolean {
		for (const node of nodeList) {
			if (node.id === targetId) {
				collectChildren(node);
				return true;
			}
			if (find(node.children)) return true;
		}
		return false;
	}

	find(nodes);
	return ids;
}

export default function WikiPageEditor({
	mode,
	initialTitle = "",
	initialContent = "",
	initialTags = "",
	initialParentId,
	pageId,
	onSave,
	onCancel,
	saving = false,
	error = null,
}: WikiPageEditorProps) {
	const [title, setTitle] = useState(initialTitle);
	const [content, setContent] = useState(initialContent);
	const [tags, setTags] = useState(initialTags);
	const [parentId, setParentId] = useState<string | null | undefined>(initialParentId);
	const [changeSummary, setChangeSummary] = useState("");
	const [hasChanges, setHasChanges] = useState(false);
	const [showPreview, setShowPreview] = useState(true);
	const [uploading, setUploading] = useState(false);
	const [showDiscardConfirm, setShowDiscardConfirm] = useState(false);
	const [treeOptions, setTreeOptions] = useState<
		{ id: string; title: string; depth: number }[]
	>([]);
	const textareaRef = useRef<HTMLTextAreaElement>(null);

	useEffect(() => {
		// Focus title on mount
		// For edit mode the title input already has value so focus content
		if (mode === "create") {
			document.getElementById("wiki-title-input")?.focus();
		} else {
			setTimeout(() => textareaRef.current?.focus(), 100);
		}
	}, [mode]);

	useEffect(() => {
		(async () => {
			try {
				const tree = await wikiApi.getTree();
				const excludeIds =
					mode === "edit" && pageId
						? collectDescendantIds(tree, pageId)
						: new Set<string>();
				setTreeOptions(flattenTree(tree, excludeIds));
			} catch {
				// Tree fetch failed — parent selector will be empty
			}
		})();
	}, [mode, pageId]);

	const insertMarkdown = useCallback(
		(before: string, after = "", defaultText = "text") => {
			if (!textareaRef.current) return;
			const ta = textareaRef.current;
			const start = ta.selectionStart;
			const end = ta.selectionEnd;
			const selected = content.substring(start, end) || defaultText;
			const next =
				content.substring(0, start) + before + selected + after + content.substring(end);
			setContent(next);
			setHasChanges(true);
			setTimeout(() => {
				ta.focus();
				const pos = start + before.length + selected.length;
				ta.setSelectionRange(pos, pos);
			}, 0);
		},
		[content],
	);

	const insertAtCursor = useCallback(
		(text: string) => {
			if (!textareaRef.current) return;
			const ta = textareaRef.current;
			const start = ta.selectionStart;
			const end = ta.selectionEnd;
			const next = content.substring(0, start) + text + content.substring(end);
			setContent(next);
			setHasChanges(true);
			setTimeout(() => {
				ta.focus();
				ta.setSelectionRange(start + text.length, start + text.length);
			}, 0);
		},
		[content],
	);

	const handlePaste = useCallback(
		async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
			const imageItem = Array.from(e.clipboardData.items).find((item) =>
				item.type.startsWith("image/"),
			);
			if (!imageItem) return;

			e.preventDefault();
			const file = imageItem.getAsFile();
			if (!file) return;

			const placeholder = "![Uploading…]()";
			insertAtCursor(placeholder);
			setUploading(true);

			try {
				const result = await wikiApi.uploadImage(file);
				setContent((prev) => prev.replace(placeholder, `![image](/api/wiki/images/${result.id})`));
				setHasChanges(true);
			} catch {
				setContent((prev) => prev.replace(placeholder, ""));
			} finally {
				setUploading(false);
			}
		},
		[insertAtCursor],
	);

	// Keyboard shortcuts
	useEffect(() => {
		const handler = (e: KeyboardEvent) => {
			if (!(e.metaKey || e.ctrlKey)) return;
			if (e.key === "s") {
				e.preventDefault();
				handleSave();
			} else if (e.key === "b") {
				e.preventDefault();
				insertMarkdown("**", "**");
			} else if (e.key === "i") {
				e.preventDefault();
				insertMarkdown("*", "*");
			} else if (e.key === "e") {
				e.preventDefault();
				insertMarkdown("`", "`");
			}
		};
		window.addEventListener("keydown", handler);
		return () => window.removeEventListener("keydown", handler);
	}, []);

	const handleSave = () => {
		if (!title.trim()) return;
		onSave({
			title: title.trim(),
			content,
			tags: tags
				.split(",")
				.map((t) => t.trim())
				.filter(Boolean),
			changeSummary: changeSummary.trim() || undefined,
			parentId,
		});
	};

	const handleCancel = () => {
		if (hasChanges) {
			setShowDiscardConfirm(true);
			return;
		}
		onCancel();
	};

	const handleConfirmCancel = () => {
		setShowDiscardConfirm(false);
		onCancel();
	};

	const wordCount = content.trim().split(/\s+/).filter((w) => w.length > 0).length;
	const charCount = content.length;

	// Toolbar handlers (stable refs to avoid re-render cascade)
	const insertBold = useCallback(() => insertMarkdown("**", "**"), [insertMarkdown]);
	const insertItalic = useCallback(() => insertMarkdown("*", "*"), [insertMarkdown]);
	const insertH1 = useCallback(() => insertAtCursor("\n# "), [insertAtCursor]);
	const insertH2 = useCallback(() => insertAtCursor("\n## "), [insertAtCursor]);
	const insertH3 = useCallback(() => insertAtCursor("\n### "), [insertAtCursor]);
	const insertList = useCallback(() => insertAtCursor("\n- "), [insertAtCursor]);
	const insertOrderedList = useCallback(() => insertAtCursor("\n1. "), [insertAtCursor]);
	const insertCheckbox = useCallback(() => insertAtCursor("\n- [ ] "), [insertAtCursor]);
	const insertCode = useCallback(() => insertMarkdown("`", "`"), [insertMarkdown]);
	const insertCodeBlock = useCallback(() => insertMarkdown("```\n", "\n```"), [insertMarkdown]);
	const insertQuote = useCallback(() => insertAtCursor("\n> "), [insertAtCursor]);
	const insertLink = useCallback(() => insertMarkdown("[", "](url)"), [insertMarkdown]);
	const insertDivider = useCallback(() => insertAtCursor("\n---\n"), [insertAtCursor]);

	return (
		<div className="flex h-full flex-col bg-white">
			{/* Page metadata header */}
			<div className="flex-none space-y-3 border-b border-slate-200 bg-white px-6 py-4">
				{/* Title */}
				<input
					id="wiki-title-input"
					type="text"
					value={title}
					onChange={(e) => {
						setTitle(e.target.value);
						setHasChanges(true);
					}}
					placeholder="Page title…"
					className="w-full border-b border-transparent bg-transparent pb-1 text-2xl font-semibold text-slate-900 transition-colors placeholder:text-slate-400 hover:border-slate-200 focus:border-orange-500 focus:outline-none"
				/>

				{/* Tags + change summary row */}
				<div className="flex flex-wrap items-center gap-4">
					<div className="flex min-w-0 flex-1 items-center gap-2">
						<span className="shrink-0 text-[0.6rem] capitalize text-slate-500">
							Tags
						</span>
						<input
							type="text"
							value={tags}
							onChange={(e) => {
								setTags(e.target.value);
								setHasChanges(true);
							}}
							placeholder="e.g. tutorial, api, getting-started"
							className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-900 transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
						/>
					</div>

					{mode === "edit" && (
						<div className="flex min-w-0 flex-1 items-center gap-2">
							<span className="shrink-0 text-[0.6rem] capitalize text-slate-500">
								Summary
							</span>
							<input
								type="text"
								value={changeSummary}
								onChange={(e) => setChangeSummary(e.target.value)}
								placeholder="Briefly describe your changes…"
								className="flex-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-900 transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
							/>
						</div>
					)}
				</div>

				{/* Parent page selector */}
				{treeOptions.length > 0 && (
					<div className="flex items-center gap-2">
						<span className="shrink-0 text-[0.6rem] capitalize text-slate-500">
							Parent
						</span>
						<select
							value={parentId ?? ""}
							onChange={(e) => {
								setParentId(e.target.value || null);
								setHasChanges(true);
							}}
							className="flex-1 cursor-pointer appearance-none rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-900 transition-colors hover:border-orange-400 focus:border-orange-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
						>
							<option value="">None (root page)</option>
							{treeOptions.map((opt) => (
								<option key={opt.id} value={opt.id}>
									{"—".repeat(opt.depth)}{opt.depth > 0 ? " " : ""}
									{opt.title}
								</option>
							))}
						</select>
					</div>
				)}

				{error && (
					<div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
						{error}
					</div>
				)}
			</div>

			{/* Toolbar */}
			<div className="flex flex-none items-center gap-1 border-b border-slate-200 bg-slate-50 px-5 py-2">
				<ToolbarButton icon={<Bold />} onClick={insertBold} tooltip="Bold" shortcut="⌘B" />
				<ToolbarButton icon={<Italic />} onClick={insertItalic} tooltip="Italic" shortcut="⌘I" />
				<div className="mx-1 h-5 w-px bg-slate-200" />
				<ToolbarButton icon={<Heading1 />} onClick={insertH1} tooltip="Heading 1" />
				<ToolbarButton icon={<Heading2 />} onClick={insertH2} tooltip="Heading 2" />
				<ToolbarButton icon={<Heading3 />} onClick={insertH3} tooltip="Heading 3" />
				<div className="mx-1 h-5 w-px bg-slate-200" />
				<ToolbarButton icon={<List />} onClick={insertList} tooltip="Bullet list" />
				<ToolbarButton icon={<ListOrdered />} onClick={insertOrderedList} tooltip="Numbered list" />
				<ToolbarButton icon={<CheckSquare />} onClick={insertCheckbox} tooltip="Task list" />
				<div className="mx-1 h-5 w-px bg-slate-200" />
				<ToolbarButton icon={<Code />} onClick={insertCode} tooltip="Inline code" shortcut="⌘E" />
				<ToolbarButton icon={<Edit />} onClick={insertCodeBlock} tooltip="Code block" />
				<ToolbarButton icon={<Quote />} onClick={insertQuote} tooltip="Blockquote" />
				<ToolbarButton icon={<Link />} onClick={insertLink} tooltip="Link" />
				<ToolbarButton icon={<Minus />} onClick={insertDivider} tooltip="Divider" />
				<div className="ml-auto flex items-center gap-2">
					<button
						type="button"
						onClick={() => setShowPreview((p) => !p)}
						className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 transition-all hover:border-orange-400 hover:text-slate-900"
					>
						{showPreview ? (
							<>
								<Edit className="h-3.5 w-3.5" />
								Editor only
							</>
						) : (
							<>
								<Eye className="h-3.5 w-3.5" />
								Show preview
							</>
						)}
					</button>
				</div>
			</div>

			{/* Editor + Preview */}
			<div className="flex flex-1 overflow-hidden">
				{/* Editor pane */}
				<div
					className={`${showPreview ? "w-1/2" : "w-full"} flex flex-col border-r border-slate-200`}
				>
					<div className="flex items-center justify-between bg-slate-100 px-4 py-1.5 text-[0.6rem] capitalize text-slate-600">
						<span>Markdown</span>
						<span>⌘S to save</span>
					</div>
					<textarea
						ref={textareaRef}
						value={content}
						onChange={(e) => {
							setContent(e.target.value);
							setHasChanges(true);
						}}
						placeholder="Write your content here…&#10;&#10;Supports **bold**, *italic*, # headings, `code`, and more."
						className="flex-1 resize-none bg-white p-5 font-mono text-sm leading-relaxed text-slate-900 focus:outline-none"
						spellCheck={false}
						onPaste={handlePaste}
					/>
				</div>

				{/* Preview pane */}
				{showPreview && (
					<div className="flex w-1/2 flex-col">
						<div className="bg-slate-100 px-4 py-1.5 text-[0.6rem] capitalize text-slate-600">
							Preview
						</div>
						<div className="flex-1 overflow-y-auto bg-slate-50 p-5">
							{content ? (
								<div className="prose prose-slate max-w-none text-slate-800">
									<SimpleMarkdown content={content} variant="light" />
								</div>
							) : (
								<p className="text-sm italic text-slate-500">
									Nothing to preview yet…
								</p>
							)}
						</div>
					</div>
				)}
			</div>

			{/* Footer */}
			<div className="flex-none border-t border-slate-200 bg-white px-6 py-3">
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-4">
						<span className="text-xs text-slate-500">
							{wordCount} words · {charCount} chars
						</span>
						{uploading && (
							<span className="flex items-center gap-1.5 text-[11px] text-slate-600">
								<span className="h-1.5 w-1.5 animate-smoothPulse rounded-full bg-orange-500" />
								Uploading image…
							</span>
						)}
						{hasChanges && (
							<span className="flex items-center gap-1.5 text-[11px] text-slate-600">
								<span className="h-1.5 w-1.5 animate-smoothPulse rounded-full bg-orange-500" />
								Unsaved
							</span>
						)}
					</div>
					<div className="flex items-center gap-3">
						<button
							type="button"
							onClick={handleCancel}
							disabled={saving}
							className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs text-slate-700 transition-colors hover:border-orange-400 hover:text-slate-900 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						>
							<XCircle className="h-3.5 w-3.5" />
							Cancel
						</button>
						<button
							type="button"
							onClick={handleSave}
							disabled={saving || !title.trim()}
							className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-5 py-2 text-xs font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						>
							<Save className="h-3.5 w-3.5" />
							{saving
								? mode === "create"
									? "Creating…"
									: "Saving…"
								: mode === "create"
									? "Create page"
									: "Save changes"}
						</button>
					</div>
				</div>
			</div>
			<ConfirmDialog
				isOpen={showDiscardConfirm}
				onClose={() => setShowDiscardConfirm(false)}
				onConfirm={handleConfirmCancel}
				title="Discard Changes"
				message="You have unsaved changes. Discard them?"
				confirmText="Discard"
				cancelText="Cancel"
				variant="warning"
				surface="light"
			/>
		</div>
	);
}
