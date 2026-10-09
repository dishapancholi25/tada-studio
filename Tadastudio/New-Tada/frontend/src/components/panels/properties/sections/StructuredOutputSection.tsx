"use client";

import { FileText } from "lucide-react";
import type React from "react";
import { useCallback } from "react";
import StructuredOutputBuilder, {
	type StructuredOutputSchema,
} from "../../../utils/StructuredOutputBuilder";

interface StructuredOutputSectionProps {
	enableStructuredOutput: boolean;
	onEnableStructuredOutputChange: (enabled: boolean) => void;
	structuredOutputs: StructuredOutputSchema[];
	onStructuredOutputsChange: (schemas: StructuredOutputSchema[]) => void;
}

export default function StructuredOutputSection({
	enableStructuredOutput,
	onEnableStructuredOutputChange,
	structuredOutputs,
	onStructuredOutputsChange,
}: StructuredOutputSectionProps) {
	const handleEnableChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onEnableStructuredOutputChange(e.target.checked);
		},
		[onEnableStructuredOutputChange],
	);

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 text-orange-600">
							<FileText className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Structured Output
							</h3>
							<p className="text-sm text-slate-600">
								Force consistent JSON shapes so downstream systems can rely on
								the agent&apos;s reply.
							</p>
						</div>
					</div>
					<label className="relative inline-flex items-center cursor-pointer">
						<input
							type="checkbox"
							checked={enableStructuredOutput}
							onChange={handleEnableChange}
							className="peer sr-only"
						/>
						<div className="h-7 w-12 rounded-full border border-slate-300 bg-slate-200 transition-colors duration-200 peer-checked:bg-orange-500 peer-checked:border-orange-500 peer-focus-visible:ring-2 peer-focus-visible:ring-orange-500/30" />
						<span className="absolute left-1 top-1 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 peer-checked:translate-x-5" />
					</label>
				</div>
				<p className="mt-4 text-sm text-slate-600">
					Enable structured output to guarantee the agent responds in a
					predictable schema. Perfect when API consumers parse the response.
				</p>
			</div>

			{enableStructuredOutput && (
				<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
					<StructuredOutputBuilder
						schemas={structuredOutputs}
						onChange={onStructuredOutputsChange}
					/>
				</div>
			)}
		</div>
	);
}
