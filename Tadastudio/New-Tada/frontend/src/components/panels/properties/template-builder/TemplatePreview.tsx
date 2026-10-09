"use client";

import { useMemo } from "react";
import { Code } from "lucide-react";
import type { VariableInfo } from "./templateBuilderTypes";

interface TemplatePreviewProps {
	templateString: string;
	variables: VariableInfo[];
}

/** Replace variable keys (UUIDs) with human-readable display labels. */
function humanize(template: string, variables: VariableInfo[]): string {
	return template.replace(/\{([^}]+)\}/g, (_match, key: string) => {
		const v = variables.find((vi) => vi.key === key);
		return `{${v?.displayLabel ?? key}}`;
	});
}

export default function TemplatePreview({
	templateString,
	variables,
}: TemplatePreviewProps) {
	const display = useMemo(
		() => humanize(templateString, variables),
		[templateString, variables],
	);

	if (!templateString.trim()) {
		return (
			<div className="px-4 py-3 text-xs text-slate-500">
				Start building your template to see a preview here.
			</div>
		);
	}

	return (
		<div className="px-4 py-3">
			<div className="mb-2 flex items-center gap-1.5">
				<Code className="h-3 w-3 text-slate-500" />
				<span className="text-[0.6rem] font-semibold capitalize text-slate-600">
					Raw Template
				</span>
			</div>
			<div className="rounded-[4px] border border-slate-200 bg-slate-50 px-3 py-2">
				<p className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-800">
					{display}
				</p>
			</div>
		</div>
	);
}
