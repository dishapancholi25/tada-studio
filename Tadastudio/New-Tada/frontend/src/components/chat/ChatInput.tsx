"use client";

import { Paperclip, Send, Square, X } from "lucide-react";
import { forwardRef, useCallback, useImperativeHandle, useRef, useState } from "react";

interface ChatInputProps {
	onSend: (message: string, files?: File[]) => void;
	onStop?: () => void;
	disabled?: boolean;
	isExecuting?: boolean;
}

/** Imperative handle so parent can populate the input without sending */
export interface ChatInputHandle {
	setValue: (text: string) => void;
}

const ChatInput = forwardRef<ChatInputHandle, ChatInputProps>(
	function ChatInput({ onSend, onStop, disabled, isExecuting }, ref) {
		const [message, setMessage] = useState("");
		const [files, setFiles]     = useState<File[]>([]);
		const textareaRef           = useRef<HTMLTextAreaElement>(null);
		const fileInputRef          = useRef<HTMLInputElement>(null);

		useImperativeHandle(ref, () => ({
			setValue: (text: string) => {
				setMessage(text);
				// Focus and resize after state flush
				requestAnimationFrame(() => {
					const el = textareaRef.current;
					if (!el) return;
					el.focus();
					el.style.height = "auto";
					el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
				});
			},
		}));

		const handleSend = useCallback(() => {
			const trimmed = message.trim();
			if ((!trimmed && files.length === 0) || disabled) return;
			onSend(trimmed, files.length > 0 ? files : undefined);
			setMessage("");
			setFiles([]);
			if (textareaRef.current) textareaRef.current.style.height = "auto";
		}, [message, files, disabled, onSend]);

		const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
			if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
		};

		const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setMessage(e.target.value);
			const el = e.target;
			el.style.height = "auto";
			el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
		};

		const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
			const selected = Array.from(e.target.files ?? []);
			if (selected.length > 0) setFiles((prev) => [...prev, ...selected]);
			e.target.value = "";
		};

		const removeFile = (idx: number) => setFiles((prev) => prev.filter((_, i) => i !== idx));

		const hasContent = message.trim().length > 0 || files.length > 0;

		return (
			<div className="border-t border-slate-200 bg-white px-6 py-3">
				{files.length > 0 && (
					<div className="mb-2 flex flex-wrap gap-1.5">
						{files.map((f, idx) => (
							<div key={`${f.name}-${idx}`} className="flex items-center gap-1.5 rounded-lg border border-orange-200 bg-orange-50 px-3 py-1.5">
								<Paperclip className="h-3.5 w-3.5 shrink-0 text-orange-500" />
								<span className="max-w-[200px] truncate text-xs text-orange-700">{f.name}</span>
								<button type="button" onClick={() => removeFile(idx)} className="shrink-0 text-orange-400 hover:text-slate-800" aria-label="Remove">
									<X className="h-3.5 w-3.5" />
								</button>
							</div>
						))}
					</div>
				)}

				<div className="flex items-center gap-3">
					<input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileChange}
						accept=".txt,.pdf,.csv,.json,.yaml,.yml,.md,.docx,.xlsx,.png,.jpg,.jpeg" />

					<button type="button" onClick={() => fileInputRef.current?.click()} disabled={disabled || isExecuting}
						className="shrink-0 text-slate-400 hover:text-slate-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed" title="Attach files">
						<Paperclip className="h-5 w-5" />
					</button>

					<div className="flex-1 rounded-2xl border border-slate-200 bg-white">
						<textarea ref={textareaRef} value={message} onChange={handleInput} onKeyDown={handleKeyDown}
							placeholder={files.length > 0 ? "Add a message (optional)…" : "Type a message…"}
							disabled={disabled || isExecuting} rows={1}
							className="w-full resize-none bg-transparent px-[18px] py-[14px] text-sm text-slate-900 placeholder:text-slate-400 placeholder:italic disabled:cursor-not-allowed disabled:opacity-50"
							style={{ overflow: "hidden", border: "none", outline: "none", boxShadow: "none", backgroundColor: "transparent" }} />
					</div>

					{isExecuting ? (
						<button type="button" onClick={onStop}
							className="flex w-11 h-11 shrink-0 items-center justify-center rounded-full border border-red-500/40 bg-red-500/10 text-red-400 transition-all duration-200 hover:bg-red-500/20" title="Stop">
							<Square size={16} />
						</button>
					) : (
						<button type="button" onClick={handleSend} disabled={!hasContent || disabled}
							className={`flex w-11 h-11 shrink-0 items-center justify-center rounded-full transition-all duration-200 ${hasContent ? "bg-orange-500 text-white hover:bg-orange-600 hover:scale-[1.06] active:scale-95" : "bg-slate-100 text-slate-400 border border-slate-200"} disabled:cursor-not-allowed disabled:opacity-30`} title="Send">
							<Send size={16} />
						</button>
					)}
				</div>
			</div>
		);
	},
);

export default ChatInput;
