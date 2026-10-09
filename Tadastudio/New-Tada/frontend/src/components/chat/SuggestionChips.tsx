"use client";

import { ArrowRight } from "lucide-react";

interface SuggestionChipsProps {
	suggestions: string[];
	onSelect: (text: string) => void;
}

export default function SuggestionChips({ suggestions, onSelect }: SuggestionChipsProps) {
	if (suggestions.length === 0) return null;

	return (
		<div className="mt-3 flex flex-wrap gap-2">
			{suggestions.map((s, i) => (
				<button
					key={i}
					type="button"
					onClick={() => onSelect(s)}
					className="flex items-center gap-1.5 rounded-full border border-orange-200 bg-white px-3.5 py-1.5 text-xs font-medium text-orange-700 shadow-sm transition-all duration-150 hover:border-orange-400 hover:bg-orange-50 hover:shadow active:scale-[0.97]"
				>
					<span className="line-clamp-1 max-w-[280px] text-left">{s}</span>
					<ArrowRight className="h-3 w-3 shrink-0 opacity-50" />
				</button>
			))}
		</div>
	);
}
