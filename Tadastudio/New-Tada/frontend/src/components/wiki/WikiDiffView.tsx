"use client";

import { diffWords } from "diff";
import { useMemo } from "react";

interface WikiDiffViewProps {
	oldContent: string;
	newContent: string;
}

export default function WikiDiffView({
	oldContent,
	newContent,
}: WikiDiffViewProps) {
	const { changes, additions, removals } = useMemo(() => {
		const result = diffWords(oldContent, newContent);
		let added = 0;
		let removed = 0;
		for (const part of result) {
			if (part.added) added++;
			if (part.removed) removed++;
		}
		return { changes: result, additions: added, removals: removed };
	}, [oldContent, newContent]);

	if (additions === 0 && removals === 0) {
		return (
			<p className="text-xs italic text-slate-600">
				Content unchanged — only metadata was modified
			</p>
		);
	}

	return (
		<div>
			{/* Summary */}
			<div className="mb-2 flex items-center gap-3">
				{additions > 0 && (
					<span className="flex items-center gap-1 text-[0.6rem] font-medium capitalize text-[#0DA931]">
						<span className="inline-block h-1.5 w-1.5 rounded-full bg-[#0DA931]" />
						{additions} {additions === 1 ? "addition" : "additions"}
					</span>
				)}
				{removals > 0 && (
					<span className="flex items-center gap-1 text-[0.6rem] font-medium capitalize text-red-700">
						<span className="inline-block h-1.5 w-1.5 rounded-full bg-red-600" />
						{removals} {removals === 1 ? "deletion" : "deletions"}
					</span>
				)}
			</div>

			{/* Diff content */}
			<pre className="whitespace-pre-wrap break-words rounded-lg border border-slate-200 bg-white p-3 font-mono text-xs text-slate-800">
				{changes.map((part, i) => {
					if (part.added) {
						return (
							<span
								key={i}
								className="rounded-sm bg-[#F1F8E9] px-0.5 text-[#0DA931]"
							>
								{part.value}
							</span>
						);
					}
					if (part.removed) {
						return (
							<span
								key={i}
								className="rounded-sm bg-red-100 px-0.5 text-red-800 line-through"
							>
								{part.value}
							</span>
						);
					}
					return (
						<span key={i} className="text-slate-600">
							{part.value}
						</span>
					);
				})}
			</pre>
		</div>
	);
}
