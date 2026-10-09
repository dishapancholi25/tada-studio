"use client";

import { Keyboard, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";

interface KeyboardShortcutsDialogProps {
	isOpen: boolean;
	onClose: () => void;
}

interface ShortcutItem {
	keys: string[];
	macKeys?: string[]; // Optional Mac-specific keys
	description: string;
}

interface ShortcutCategory {
	name: string;
	shortcuts: ShortcutItem[];
}

const shortcutCategories: ShortcutCategory[] = [
	{
		name: "History",
		shortcuts: [
			{ keys: ["Ctrl", "Z"], macKeys: ["⌘", "Z"], description: "Undo last action" },
			{ keys: ["Ctrl", "Y"], macKeys: ["⌘", "Shift", "Z"], description: "Redo last action" },
			{ keys: ["Ctrl", "Shift", "Z"], macKeys: ["⌘", "Shift", "Z"], description: "Redo last action (alternative)" },
		],
	},
	{
		name: "Canvas",
		shortcuts: [
			{ keys: ["Ctrl", "C"], macKeys: ["⌘", "C"], description: "Copy selected node(s)" },
			{ keys: ["Ctrl", "V"], macKeys: ["⌘", "V"], description: "Paste copied node(s)" },
				{ keys: ["Delete"], macKeys: ["⌫"], description: "Delete selected node(s) or connection(s)" },
				{ keys: ["Backspace"], macKeys: ["⌫"], description: "Delete selected node(s) or connection(s)" },
			{ keys: ["Escape"], macKeys: ["Esc"], description: "Deselect all nodes" },
			{ keys: ["Ctrl", "0"], macKeys: ["⌘", "0"], description: "Fit view to canvas" },
		],
	},
	{
		name: "Navigation",
		shortcuts: [
			{ keys: ["Scroll"], description: "Zoom in/out" },
			{ keys: ["Drag"], description: "Pan canvas" },
			{ keys: ["Ctrl", "Drag"], macKeys: ["⌘", "Drag"], description: "Move node with children" },
		],
	},
	{
		name: "Help",
		shortcuts: [
			{ keys: ["?"], description: "Show this help dialog" },
		],
	},
];

function KeyBadge({ children }: { children: string }) {
	return (
		<kbd
			className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 text-xs font-medium rounded"
			style={{
				background: "var(--color-surface)",
				border: "1px solid var(--color-border)",
				color: "var(--color-text-primary)",
				boxShadow: "0 1px 2px rgba(0, 0, 0, 0.2)",
			}}
		>
			{children}
		</kbd>
	);
}

export default function KeyboardShortcutsDialog({
	isOpen,
	onClose,
}: KeyboardShortcutsDialogProps) {
	const [mounted, setMounted] = useState(false);
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);

	// Detect if user is on Mac
	const isMac = useMemo(() => {
		if (typeof navigator !== "undefined") {
			return navigator.platform.toUpperCase().indexOf("MAC") >= 0 || 
				navigator.userAgent.toUpperCase().indexOf("MAC") >= 0;
		}
		return false;
	}, []);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, isOpen);

	// Prevent body scroll when modal is open
	useEffect(() => {
		if (isOpen) {
			document.body.style.overflow = "hidden";
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [isOpen]);

	// Get the appropriate keys based on platform
	const getKeys = (shortcut: ShortcutItem) => {
		if (isMac && shortcut.macKeys) {
			return shortcut.macKeys;
		}
		return shortcut.keys;
	};

	if (!mounted || !isOpen) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			{/* Backdrop */}
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

			{/* Dialog */}
			<div
				ref={dialogRef}
				className="relative w-full max-w-lg rounded-xl shadow-2xl animate-fadeIn"
				style={{
					background: "var(--color-bg-primary)",
					border: "1px solid var(--color-border)",
				}}
				onClick={(e) => e.stopPropagation()}
				role="dialog"
				aria-modal="true"
				aria-labelledby="shortcuts-dialog-title"
			>
				{/* Header */}
				<div className="flex items-center justify-between p-6 pb-4 border-b border-[var(--color-border)]">
					<div className="flex items-center gap-3">
						<div className="p-2 rounded-lg bg-[var(--color-primary)]/10">
							<Keyboard className="w-5 h-5 text-[var(--color-primary)]" />
						</div>
						<h2
							id="shortcuts-dialog-title"
							className="text-lg font-semibold text-[var(--color-text-primary)]"
						>
							Keyboard Shortcuts
						</h2>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="p-2 rounded-lg transition-colors hover:bg-[var(--color-surface)]"
						style={{ color: "var(--color-text-secondary)" }}
						aria-label="Close"
					>
						<X className="w-5 h-5" />
					</button>
				</div>

				{/* Body */}
				<div className="p-6 max-h-[60vh] overflow-y-auto">
					<div className="space-y-6">
						{shortcutCategories.map((category) => (
							<div key={category.name}>
								<h3 className="text-sm font-medium text-[var(--color-text-secondary)] capitalize tracking-wider mb-3">
									{category.name}
								</h3>
								<div className="space-y-2">
									{category.shortcuts.map((shortcut, index) => {
										const keys = getKeys(shortcut);
										return (
											<div
												key={index}
												className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-[var(--color-surface)]/50 transition-colors"
											>
												<span className="text-sm text-[var(--color-text-primary)]">
													{shortcut.description}
												</span>
												<div className="flex items-center gap-1">
													{keys.map((key, keyIndex) => (
														<span key={keyIndex} className="flex items-center gap-1">
															<KeyBadge>{key}</KeyBadge>
															{keyIndex < keys.length - 1 && (
																<span className="text-[var(--color-text-muted)] text-xs">+</span>
															)}
														</span>
													))}
												</div>
											</div>
										);
									})}
								</div>
							</div>
						))}
					</div>
				</div>

				{/* Footer */}
				<div className="p-4 border-t border-[var(--color-border)] text-center">
					<p className="text-xs text-[var(--color-text-muted)]">
						Press <KeyBadge>Esc</KeyBadge> or click outside to close
					</p>
				</div>
			</div>
		</div>,
		document.body,
	);
}
