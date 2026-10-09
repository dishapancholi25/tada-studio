"use client";

import { Plus, X } from "lucide-react";
import { useCallback, useState } from "react";

interface StringListEditorProps {
	label: string;
	description?: string;
	values: string[];
	onChange: (values: string[]) => void;
	placeholder?: string;
	monospace?: boolean;
	readOnly?: boolean;
}

export default function StringListEditor({
	label,
	description,
	values,
	onChange,
	placeholder = "Add item...",
	monospace = false,
	readOnly = false,
}: StringListEditorProps) {
	const [inputValue, setInputValue] = useState("");

	const handleAdd = useCallback(() => {
		const trimmed = inputValue.trim();
		if (trimmed && !values.includes(trimmed)) {
			onChange([...values, trimmed]);
			setInputValue("");
		}
	}, [inputValue, values, onChange]);

	const handleKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLInputElement>) => {
			if (e.key === "Enter") {
				e.preventDefault();
				handleAdd();
			}
		},
		[handleAdd],
	);

	const handleRemove = useCallback(
		(index: number) => {
			onChange(values.filter((_, i) => i !== index));
		},
		[values, onChange],
	);

	return (
		<div>
			<label className="mb-2 block text-sm font-medium text-[color:var(--color-text-secondary)]">
				{label}
			</label>
			{!readOnly && (
				<div className="flex gap-2">
					<input
						type="text"
						value={inputValue}
						onChange={(e) => setInputValue(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder={placeholder}
						className={`flex-1 rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)] px-3 py-2 text-sm text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:border-[rgba(6,182,212,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(6,182,212,0.45)] ${monospace ? "font-mono" : ""}`}
					/>
					<button
						type="button"
						onClick={handleAdd}
						disabled={!inputValue.trim()}
						className="flex items-center gap-1 rounded-lg border border-[rgba(6,182,212,0.3)] bg-[rgba(6,182,212,0.1)] px-3 py-2 text-sm text-cyan-400 transition-colors hover:bg-[rgba(6,182,212,0.2)] disabled:opacity-40 disabled:cursor-not-allowed"
					>
						<Plus className="h-4 w-4" />
					</button>
				</div>
			)}
			{values.length > 0 && (
				<div className="mt-2 flex flex-wrap gap-1.5">
					{values.map((value, index) => (
						<span
							key={`${value}-${index}`}
							className={`inline-flex items-center gap-1 rounded-lg border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/60 px-2.5 py-1 text-xs text-[color:var(--color-text-secondary)] ${monospace ? "font-mono" : ""}`}
						>
							{value}
							{!readOnly && (
								<button
									type="button"
									onClick={() => handleRemove(index)}
									className="ml-0.5 rounded p-0.5 text-[color:var(--color-text-muted)] transition-colors hover:bg-[color:var(--color-border)]/50 hover:text-[color:var(--color-text-primary)]"
								>
									<X className="h-3 w-3" />
								</button>
							)}
						</span>
					))}
				</div>
			)}
			{description && (
				<p className="mt-1.5 text-xs text-[color:var(--color-text-muted)]">
					{description}
				</p>
			)}
		</div>
	);
}
