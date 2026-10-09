import type React from "react";
import {
	extractResponseContent,
	processContentForRendering,
	shouldRenderAsMarkdown,
} from "@/lib/markdown-utils";
import type { NodeExecution } from "@/types/api";
import JsonViewerEnhanced from "../../../JsonViewerEnhanced";
import SimpleMarkdown from "../../../utils/SimpleMarkdown";
import ExecutionDetailsPanel from "./ExecutionDetailsPanel";

interface ExecutionIOViewProps {
	nodeExecution: NodeExecution;
	isDatabaseQuery?: boolean;
}

const ExecutionIOView: React.FC<ExecutionIOViewProps> = ({
	nodeExecution,
	isDatabaseQuery = false,
}) => {
	const renderOutput = () => {
		if (nodeExecution.status === "failed" && nodeExecution.error_message) {
			return (
				<div className="text-red-700">
					<p className="mb-2 text-sm font-medium">Error:</p>
					<pre className="text-xs">{nodeExecution.error_message}</pre>
				</div>
			);
		}

		if (!nodeExecution.output_data) {
			return <span className="text-xs text-gray-500">No output data</span>;
		}

		let processedOutput = nodeExecution.output_data;

		if (
			processedOutput &&
			typeof processedOutput === "object" &&
			"response" in processedOutput
		) {
			const response = (processedOutput as Record<string, unknown>).response;
			if (typeof response === "string") {
				const trimmed = response.trim();
				if (
					(trimmed.startsWith("{") && trimmed.endsWith("}")) ||
					(trimmed.startsWith("[") && trimmed.endsWith("]"))
				) {
					try {
						processedOutput = {
							...processedOutput,
							response: JSON.parse(trimmed),
						};
					} catch {
						try {
							const unescaped = trimmed
								.replace(/\\n/g, "\n")
								.replace(/\\"/g, '"')
								.replace(/\\\\/g, "\\");
							processedOutput = {
								...processedOutput,
								response: JSON.parse(unescaped),
							};
						} catch {
							// Keep original if parsing fails
						}
					}
				}
			}
		}

		if (isDatabaseQuery && processedOutput?.messages?.[0]?.content) {
			return (
				<div className="space-y-3">
					{typeof processedOutput.messages[0].content === "string" &&
					processedOutput.messages[0].content.includes("rows") ? (
						<div className="rounded-lg bg-slate-50 p-3">
							<pre className="whitespace-pre-wrap text-xs text-gray-800">
								{processedOutput.messages[0].content}
							</pre>
						</div>
					) : (
						<JsonViewerEnhanced data={processedOutput} />
					)}
				</div>
			);
		}
		const responseContent = extractResponseContent(processedOutput);

		if (
			responseContent &&
			(shouldRenderAsMarkdown(responseContent) ||
				responseContent.includes("data:image/"))
		) {
			const processedContent = processContentForRendering(responseContent);
			if (processedContent) {
				return <SimpleMarkdown content={processedContent} variant="light" />;
			}
		}

		if (nodeExecution.node_type === "AGENT" && responseContent) {
			const processedContent = processContentForRendering(responseContent);
			if (processedContent) {
				return <SimpleMarkdown content={processedContent} variant="light" />;
			}
		}

		return <JsonViewerEnhanced data={processedOutput} />;
	};

	return (
		<div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(260px,310px)_minmax(0,1fr)]">
			<section className="relative h-full rounded-2xl border border-gray-200 bg-white shadow-sm">
				<div className="flex items-center justify-between border-b border-gray-200 px-5 py-4">
					<div>
						<p className="text-[0.7rem] font-semibold capitalize text-gray-500">
							Input
						</p>
						<p className="text-xs text-gray-600">Incoming context</p>
					</div>
					<span className="rounded-full border border-orange-300 bg-white px-3 py-1 text-[11px] font-medium text-orange-800">
						JSON
					</span>
				</div>
				<div className="custom-scrollbar max-h-[calc(90vh-260px)] space-y-3 overflow-y-auto px-5 py-4 text-sm text-gray-800">
					{!nodeExecution.input_data ? (
						<span className="text-xs text-gray-500">No input data</span>
					) : (
						<JsonViewerEnhanced data={nodeExecution.input_data} />
					)}
				</div>
			</section>

			<div className="relative rounded-2xl">
				<ExecutionDetailsPanel nodeExecution={nodeExecution} />
			</div>

			<section className="relative h-full rounded-2xl border border-gray-200 bg-white shadow-sm">
				<div className="border-b border-gray-200 px-5 py-4">
					<p className="text-[0.7rem] font-semibold capitalize text-gray-500">
						Output
					</p>
					<p className="text-xs text-gray-600">Model response</p>
				</div>
				<div className="custom-scrollbar max-h-[calc(90vh-260px)] space-y-3 overflow-y-auto px-5 py-4 text-sm text-gray-800">
					{renderOutput()}
				</div>
			</section>
		</div>
	);
};

export default ExecutionIOView;
