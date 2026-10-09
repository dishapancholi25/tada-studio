"use client";

import {
	Bold,
	CheckSquare,
	Code,
	Edit,
	Eye,
	FileText,
	Heading1,
	Heading2,
	Italic,
	Link,
	List,
	ListOrdered,
	Maximize2,
	Minimize2,
	Minus,
	Quote,
	Save,
	X,
	XCircle,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import SimpleMarkdown from "../utils/SimpleMarkdown";
import { cn } from "@/lib/utils";

const VARIABLE_CHIPS = [
	{ label: "{{$today}}", value: "{{$today}}", hint: "Current date" },
	{
		label: "{{$now}}",
		value: "{{$now}}",
		hint: "Current date & time (UTC)",
	},
];

interface MarkdownEditorModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSave: (content: string) => void;
	initialContent: string;
	title?: string;
	placeholder?: string;
}

interface ToolbarButtonProps {
	icon: React.ReactNode;
	onClick: () => void;
	tooltip: string;
	shortcut?: string;
}

function ToolbarButton({
	icon,
	onClick,
	tooltip,
	shortcut,
}: ToolbarButtonProps) {
	const [showTooltip, setShowTooltip] = useState(false);

	const showTooltipHandler = useCallback(() => setShowTooltip(true), []);
	const hideTooltipHandler = useCallback(() => setShowTooltip(false), []);

	return (
		<div className="relative">
			<button
				onClick={onClick}
				onMouseEnter={showTooltipHandler}
				onMouseLeave={hideTooltipHandler}
				className="group rounded-[4px] border border-transparent p-2 transition-colors hover:border-orange-400 hover:bg-slate-50"
				type="button"
			>
				<div className="h-4 w-4 text-gray-600 transition-colors group-hover:text-slate-900">
					{icon}
				</div>
			</button>
			{showTooltip && (
				<div className="absolute left-1/2 top-full z-50 mt-1 -translate-x-1/2 whitespace-nowrap rounded-[4px] border border-gray-200 bg-white px-2 py-1 text-xs text-gray-900 shadow-sm">
					{tooltip}
					{shortcut && (
						<span className="ml-2 text-gray-500">{shortcut}</span>
					)}
					<div className="absolute bottom-full left-1/2 mb-1 -translate-x-1/2">
						<div className="h-0 w-0 border-x-4 border-b-4 border-x-transparent border-b-white drop-shadow-sm" />
					</div>
				</div>
			)}
		</div>
	);
}

export default function MarkdownEditorModal({
	isOpen,
	onClose,
	onSave,
	initialContent,
	title = "Markdown Editor",
	placeholder = "Enter your content here...\n\nSupports **markdown** formatting!",
}: MarkdownEditorModalProps) {
	const [content, setContent] = useState(initialContent);
	const [hasChanges, setHasChanges] = useState(false);
	const [showPreview, setShowPreview] = useState(true);
	const [isFullscreen, setIsFullscreen] = useState(false);
	const [showCloseConfirm, setShowCloseConfirm] = useState(false);
	const textareaRef = useRef<HTMLTextAreaElement>(null);

	useEffect(() => {
		if (isOpen) {
			setContent(initialContent);
			setHasChanges(false);
			setTimeout(() => textareaRef.current?.focus(), 100);
		}
	}, [isOpen, initialContent]);

	useEffect(() => {
		if (!isOpen) return;

		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSave();
			}
			if (e.key === "Escape") {
				if (showCloseConfirm) return;
				handleClose();
			}
			if ((e.metaKey || e.ctrlKey) && e.key === "b") {
				e.preventDefault();
				insertMarkdown("**", "**");
			}
			if ((e.metaKey || e.ctrlKey) && e.key === "i") {
				e.preventDefault();
				insertMarkdown("*", "*");
			}
			if ((e.metaKey || e.ctrlKey) && e.key === "e") {
				e.preventDefault();
				insertMarkdown("`", "`");
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [isOpen, content, showCloseConfirm]);

	const insertMarkdown = (before: string, after = "", defaultText = "text") => {
		if (!textareaRef.current) return;

		const textarea = textareaRef.current;
		const start = textarea.selectionStart;
		const end = textarea.selectionEnd;
		const selectedText = content.substring(start, end) || defaultText;

		const newContent =
			content.substring(0, start) +
			before +
			selectedText +
			after +
			content.substring(end);

		setContent(newContent);
		setHasChanges(true);

		setTimeout(() => {
			textarea.focus();
			const newCursorPos = start + before.length + selectedText.length;
			textarea.setSelectionRange(newCursorPos, newCursorPos);
		}, 0);
	};

	const insertAtCursor = (text: string) => {
		if (!textareaRef.current) return;

		const textarea = textareaRef.current;
		const start = textarea.selectionStart;
		const end = textarea.selectionEnd;

		const newContent =
			content.substring(0, start) + text + content.substring(end);

		setContent(newContent);
		setHasChanges(true);

		setTimeout(() => {
			textarea.focus();
			const newCursorPos = start + text.length;
			textarea.setSelectionRange(newCursorPos, newCursorPos);
		}, 0);
	};

	const handleSave = () => {
		onSave(content);
		setHasChanges(false);
		onClose();
	};

	const handleClose = () => {
		if (hasChanges) {
			setShowCloseConfirm(true);
		} else {
			onClose();
		}
	};

	const handleConfirmClose = () => {
		setShowCloseConfirm(false);
		onClose();
	};

	const wordCount = content
		.trim()
		.split(/\s+/)
		.filter((word) => word.length > 0).length;
	const charCount = content.length;

	const togglePreview = useCallback(
		() => setShowPreview(!showPreview),
		[showPreview],
	);
	const toggleFullscreen = useCallback(
		() => setIsFullscreen(!isFullscreen),
		[isFullscreen],
	);
	const stopPropagation = useCallback(
		(e: React.MouseEvent) => e.stopPropagation(),
		[],
	);
	const handleContentChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setContent(e.target.value);
			setHasChanges(true);
		},
		[],
	);

	const insertBold = useCallback(() => insertMarkdown("**", "**"), []);
	const insertItalic = useCallback(() => insertMarkdown("*", "*"), []);
	const insertH1 = useCallback(() => insertAtCursor("\n# "), []);
	const insertH2 = useCallback(() => insertAtCursor("\n## "), []);
	const insertList = useCallback(() => insertAtCursor("\n- "), []);
	const insertOrderedList = useCallback(() => insertAtCursor("\n1. "), []);
	const insertCheckbox = useCallback(() => insertAtCursor("\n- [ ] "), []);
	const insertCode = useCallback(() => insertMarkdown("`", "`"), []);
	const insertQuote = useCallback(() => insertAtCursor("\n> "), []);
	const insertLink = useCallback(() => insertMarkdown("[", "](url)"), []);
	const insertDivider = useCallback(() => insertAtCursor("\n---\n"), []);
	const tokenEstimate = Math.ceil(charCount / 4);

	if (!isOpen) return null;

	return (
		<div
			className="fixed inset-0 z-[9999] flex animate-fadeIn items-center justify-center bg-slate-900/20 p-4 backdrop-blur-[5px]"
			onClick={stopPropagation}
		>
			<div
				className={cn(
					"flex flex-col overflow-hidden rounded-[4px] border border-slate-200/80 bg-slate-50/90 shadow-[0_24px_80px_rgba(15,23,42,0.1)] backdrop-blur-md transition-all duration-300",
					isFullscreen ? "h-full w-full" : "max-h-[90vh] w-full max-w-7xl",
				)}
				onClick={stopPropagation}
			>
				<div className="relative flex-none border-b border-gray-200 bg-white px-6 py-4">
					<div className="flex flex-wrap items-start justify-between gap-4">
						<div className="flex min-w-0 items-start gap-3">
							<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
								<FileText
									className="h-5 w-5 text-orange-600"
									aria-hidden
								/>
							</div>
							<div className="min-w-0">
								<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
									Content
								</p>
								<h3 className="text-lg font-semibold tracking-tight text-gray-900">
									{title}
								</h3>
								<p className="mt-0.5 text-xs text-gray-600">
									{wordCount} words · {charCount} chars · ~{tokenEstimate}{" "}
									tokens
								</p>
							</div>
						</div>
						<div className="flex flex-shrink-0 flex-wrap items-center gap-2">
							<button
								type="button"
								onClick={togglePreview}
								className={cn(
									"flex items-center gap-2 rounded-[4px] border bg-white px-3 py-1.5 text-sm transition-colors",
									showPreview
										? "border-blue-200 text-blue-900 hover:border-blue-400 hover:bg-slate-50"
										: "border-transparent text-gray-800 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900",
								)}
							>
								{showPreview ? (
									<Edit className="h-4 w-4 text-blue-700" />
								) : (
									<Eye className="h-4 w-4 text-gray-600" />
								)}
								<span
									className={
										showPreview ? "text-blue-900" : "text-gray-800"
									}
								>
									{showPreview ? "Editor Only" : "Show Preview"}
								</span>
							</button>
							<button
								type="button"
								onClick={toggleFullscreen}
								className="rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
								aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
							>
								{isFullscreen ? (
									<Minimize2 className="h-4 w-4" />
								) : (
									<Maximize2 className="h-4 w-4" />
								)}
							</button>
							<button
								type="button"
								onClick={handleClose}
								className="rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>
				</div>

				<div className="flex flex-wrap items-center gap-1 border-b border-gray-200 bg-slate-50 px-4 py-2">
					<ToolbarButton
						icon={<Bold />}
						onClick={insertBold}
						tooltip="Bold"
						shortcut="⌘B"
					/>
					<ToolbarButton
						icon={<Italic />}
						onClick={insertItalic}
						tooltip="Italic"
						shortcut="⌘I"
					/>
					<div className="mx-1 h-6 w-px bg-gray-200" />
					<ToolbarButton
						icon={<Heading1 />}
						onClick={insertH1}
						tooltip="Heading 1"
					/>
					<ToolbarButton
						icon={<Heading2 />}
						onClick={insertH2}
						tooltip="Heading 2"
					/>
					<div className="mx-1 h-6 w-px bg-gray-200" />
					<ToolbarButton
						icon={<List />}
						onClick={insertList}
						tooltip="Bullet List"
					/>
					<ToolbarButton
						icon={<ListOrdered />}
						onClick={insertOrderedList}
						tooltip="Numbered List"
					/>
					<ToolbarButton
						icon={<CheckSquare />}
						onClick={insertCheckbox}
						tooltip="Task List"
					/>
					<div className="mx-1 h-6 w-px bg-gray-200" />
					<ToolbarButton
						icon={<Code />}
						onClick={insertCode}
						tooltip="Inline Code"
					/>
					<ToolbarButton
						icon={<Quote />}
						onClick={insertQuote}
						tooltip="Quote"
					/>
					<ToolbarButton icon={<Link />} onClick={insertLink} tooltip="Link" />
					<div className="mx-1 h-6 w-px bg-gray-200" />
					<ToolbarButton
						icon={<Minus />}
						onClick={insertDivider}
						tooltip="Horizontal Rule"
					/>
				</div>

				<div className="flex flex-wrap items-center gap-3 border-b border-gray-200 bg-white px-4 py-2.5">
					<span className="text-[11px] font-semibold capitalize tracking-wide text-gray-600">
						Variables
					</span>
					{VARIABLE_CHIPS.map((chip) => (
						<button
							key={chip.value}
							type="button"
							onClick={() => insertAtCursor(chip.value)}
							title={chip.hint}
							className="inline-flex items-center gap-1.5 rounded-[4px] border border-transparent bg-white px-3 py-1 font-mono text-xs text-gray-900 transition-colors hover:border-orange-400 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						>
							{chip.label}
							<span className="font-sans text-[10px] font-normal text-gray-600">
								{chip.hint}
							</span>
						</button>
					))}
				</div>

				<div className="flex min-h-0 flex-1 overflow-hidden">
					<div
						className={cn(
							"flex flex-col",
							showPreview ? "w-1/2" : "w-full",
							showPreview && "border-r border-gray-200",
						)}
					>
						<div className="flex items-center justify-between bg-slate-100 px-4 py-2 text-xs text-gray-700">
							<span className="font-medium text-emerald-800">
								Markdown Editor
							</span>
							<span className="text-gray-600">
								Ctrl/⌘ + S to save · ESC to close
							</span>
						</div>
						<textarea
							ref={textareaRef}
							value={content}
							onChange={handleContentChange}
							placeholder={placeholder}
							className="min-h-[200px] flex-1 resize-none border-0 bg-white p-5 font-mono text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-orange-400/35"
							spellCheck={false}
						/>
					</div>

					{showPreview && (
						<div className="flex w-1/2 flex-col">
							<div className="bg-slate-100 px-4 py-2 text-xs font-medium text-gray-700">
								Live Preview
							</div>
							<div className="flex-1 overflow-y-auto bg-slate-50 p-5">
								<SimpleMarkdown
									variant="light"
									content={content || "*No content to preview*"}
								/>
							</div>
						</div>
					)}
				</div>

				<div className="flex-none border-t border-gray-200 bg-white px-6 py-3">
					<div className="flex items-center justify-between gap-3">
						<div className="text-xs text-gray-600">
							{hasChanges && (
								<span className="flex items-center gap-1.5 text-[11px] text-gray-700">
									<span className="h-1.5 w-1.5 animate-smoothPulse rounded-[4px] bg-orange-500" />
									Unsaved
								</span>
							)}
						</div>
						<div className="flex items-center gap-3">
							<span className="hidden text-[11px] text-gray-400 sm:inline">
								Ctrl/⌘ + S to save
							</span>
							<button
								type="button"
								onClick={handleClose}
								className="flex items-center gap-2 rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							>
								<XCircle className="h-3.5 w-3.5" />
								Cancel
							</button>
							<button
								type="button"
								onClick={handleSave}
								className="inline-flex items-center gap-2 rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
							>
								<Save className="h-3.5 w-3.5" />
								Save Changes
							</button>
						</div>
					</div>
				</div>
			</div>
			<ConfirmDialog
				isOpen={showCloseConfirm}
				onClose={() => setShowCloseConfirm(false)}
				onConfirm={handleConfirmClose}
				title="Discard Changes"
				message="You have unsaved changes. Are you sure you want to close?"
				confirmText="Discard"
				cancelText="Cancel"
				variant="warning"
				surface="light"
			/>
		</div>
	);
}
