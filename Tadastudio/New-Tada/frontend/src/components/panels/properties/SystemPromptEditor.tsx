"use client";

import { ChevronDown, Maximize2, Sparkles } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface SystemPromptEditorProps {
	prompt: string;
	onPromptChange: (value: string) => void;
	onOpenPromptStudio: () => void;
}

const PROMPTING_TIPS = [
	{
		label: "Define the agent's role",
		example: '"You are a customer support agent"',
	},
	{ label: "Set the tone", example: '"Be friendly but concise"' },
	{
		label: "List tools/data sources",
		example: '"Use the knowledge base first"',
	},
	{
		label: "Include example outputs",
		example: "Show the format you expect",
	},
];

const TIPS_STORAGE_KEY = "agent-panel-show-tips";

const MAX_HEIGHT = 500;

export default function SystemPromptEditor({
	prompt,
	onPromptChange,
	onOpenPromptStudio,
}: SystemPromptEditorProps) {
	const textareaRef = useRef<HTMLTextAreaElement>(null);
	const [showTips, setShowTips] = useState(false);

	useEffect(() => {
		setShowTips(localStorage.getItem(TIPS_STORAGE_KEY) === "true");
	}, []);

	const toggleTips = useCallback(() => {
		setShowTips((prev) => {
			const next = !prev;
			localStorage.setItem(TIPS_STORAGE_KEY, String(next));
			return next;
		});
	}, []);

	const adjustHeight = useCallback(() => {
		const textarea = textareaRef.current;
		if (!textarea) return;
		textarea.style.height = "auto";
		textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT)}px`;
	}, []);

	useEffect(() => {
		adjustHeight();
	}, [prompt, adjustHeight]);

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			onPromptChange(e.target.value);
		},
		[onPromptChange],
	);

	return (
		<div className="flex flex-col gap-3 rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
			{/* Section header */}
			<div className="flex flex-col gap-1.5 flex-none pb-3 border-b border-slate-200">
				<div className="flex items-center justify-between gap-2">
					<div className="flex items-center gap-2 min-w-0">
						<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Sparkles className="h-4 w-4 text-orange-600" />
						</div>
						<label className="text-base font-semibold tracking-tight text-slate-900 truncate">
							System Prompt
						</label>
					</div>
					<div className="flex items-center gap-2 shrink-0">
						<span className="text-[11px] tabular-nums rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-slate-600">
							{prompt.length} chars
						</span>
						<button
							type="button"
							onClick={onOpenPromptStudio}
							className="inline-flex items-center gap-1.5 rounded-[4px] border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-800 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						>
							<Maximize2 className="h-3.5 w-3.5 text-blue-600" />
							Prompt Studio
						</button>
					</div>
				</div>
				{/* Tips toggle — tucked under heading */}
				<button
					type="button"
					onClick={toggleTips}
					className="inline-flex items-center gap-1 self-start text-[11px] text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
				>
					{showTips ? "Hide tips" : "Show writing tips"}
					<ChevronDown
						className={cn(
							"h-3 w-3 transition-transform duration-150",
							showTips && "rotate-180",
						)}
					/>
				</button>
			</div>

			{/* Expandable tips section */}
			{showTips && (
				<div className="animate-slideDown rounded-[4px] border border-slate-200 bg-slate-50 px-4 py-3">
					<div className="text-[11px] font-semibold capitalize text-orange-700 mb-2">
						Writing effective prompts
					</div>
					<div className="flex flex-col gap-2">
						{PROMPTING_TIPS.map((tip) => (
							<div
								key={tip.label}
								className="flex items-start gap-3 text-xs"
							>
								<span className="text-orange-600 text-[10px] mt-0.5 shrink-0">
									✦
								</span>
								<span className="text-slate-900 min-w-[160px] shrink-0 font-medium">
									{tip.label}
								</span>
								<span className="text-slate-600 italic">
									{tip.example}
								</span>
							</div>
						))}
					</div>
				</div>
			)}

			{/* Textarea */}
			<textarea
				data-tutorial="system-prompt-field"
				ref={textareaRef}
				value={prompt}
				onChange={handleChange}
				className={cn(
					"min-h-[320px] w-full resize-y rounded-[4px]",
					"border border-slate-200 bg-white",
					"px-4 py-3 text-sm text-slate-900 leading-[1.75]",
					"placeholder:text-slate-400",
					"hover:border-orange-400",
					"focus:border-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20",
					"transition-colors",
				)}
				style={{ maxHeight: MAX_HEIGHT }}
				placeholder={`Define your agent's role, personality, and instructions...\n\nExample: "You are a helpful customer support agent for Acme Corp.\nBe friendly but concise. Always check the knowledge base before\nanswering product questions."`}
			/>
		</div>
	);
}
