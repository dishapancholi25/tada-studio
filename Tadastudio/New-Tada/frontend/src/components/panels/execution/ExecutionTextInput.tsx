"use client";

import type React from "react";
import { useCallback } from "react";

interface ExecutionTextInputProps {
	inputMessage: string;
	isInputExpanded: boolean;
	isExecuting: boolean;
	textareaRows: number;
	onMessageChange: (message: string) => void;
	onStartExecution: () => void;
	onToggleExpanded: () => void;
}

export default function ExecutionTextInput({
	inputMessage,
	isInputExpanded,
	isExecuting,
	textareaRows,
	onMessageChange,
	onStartExecution,
	onToggleExpanded,
}: ExecutionTextInputProps) {
	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
			// Ctrl/Cmd + Enter to submit
			if (
				e.key === "Enter" &&
				(e.ctrlKey || e.metaKey) &&
				!isExecuting &&
				inputMessage.trim()
			) {
				e.preventDefault();
				onStartExecution();
			}
			// Escape to collapse when expanded
			if (e.key === "Escape" && isInputExpanded) {
				e.preventDefault();
				onToggleExpanded();
			}
		},
		[
			isExecuting,
			inputMessage,
			isInputExpanded,
			onStartExecution,
			onToggleExpanded,
		],
	);

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			onMessageChange(e.target.value);
		},
		[onMessageChange],
	);

	return (
		<div className="relative">
			<textarea
				data-tutorial="execution-textarea"
				value={inputMessage}
				onChange={handleChange}
				onKeyDown={handleKeyDown}
				className={`w-full p-3 bg-[color:var(--color-border)] border border-[color:var(--color-surface-hover)] rounded-lg text-slate-900
                   resize-vertical focus:border-[color:var(--color-border)] focus:ring-1 focus:ring-[color:var(--color-accent)]/50
                   transition-all duration-200 overflow-auto
                   [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:bg-transparent
                   [&::-webkit-scrollbar-thumb]:bg-[color:var(--color-text-muted)] [&::-webkit-scrollbar-thumb]:rounded-full
                   [&::-webkit-scrollbar-corner]:bg-transparent
                   ${isInputExpanded ? "min-h-[300px]" : "min-h-[80px]"} max-h-[500px]`}
				rows={isInputExpanded ? 15 : textareaRows}
				placeholder={`Enter your message...${!isExecuting ? " (Ctrl+Enter to run)" : ""}`}
				disabled={isExecuting}
				style={{ fontFamily: "inherit", fontSize: "14px", lineHeight: "1.5" }}
			/>

			{/* Character count */}
			{inputMessage.length > 0 && (
				<div className="absolute bottom-2 right-2 text-xs text-[color:var(--color-text-muted)] bg-[color:var(--color-surface)]/80 px-2 py-1 rounded">
					{inputMessage.length} chars
				</div>
			)}
		</div>
	);
}
