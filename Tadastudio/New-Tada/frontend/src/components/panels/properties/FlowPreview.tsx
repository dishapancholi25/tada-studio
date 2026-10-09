import clsx from "clsx";
import {
	ArrowRight,
	Code,
	FileText,
	GitMerge,
	Sparkles,
} from "lucide-react";
import type { Edge, Node } from "reactflow";
import type { InputSourceConfig } from "./inputSourceTypes";
import { getNodeColorRgb, getNodeIcon } from "./inputSourceTypes";

interface FlowPreviewProps {
	config: InputSourceConfig;
	availableNodes: Node[];
	currentNodeName: string;
	edges?: Edge[];
	nodeId?: string;
}

interface SourceInfo {
	name: string;
	icon: React.ReactElement;
	nodeType?: string;
}

function getSourceInfo(
	config: InputSourceConfig,
	availableNodes: Node[],
	edges?: Edge[],
	nodeId?: string,
): SourceInfo[] {
	const iconClass = "h-4 w-4";

	switch (config.source_mode) {
		case "previous": {
			if (edges && nodeId) {
				const incomingIds = edges
					.filter((e) => e.target === nodeId)
					.map((e) => e.source);
				const results: SourceInfo[] = [];
				for (const id of incomingIds) {
					const node = availableNodes.find((n) => n.id === id);
					if (node) {
						results.push({
							name: node.data.name,
							icon: <FileText className={iconClass} />,
							nodeType: node.data.type,
						});
					}
				}
				if (results.length > 0) return results;
			}
			return [
				{
					name: "Previous Node",
					icon: <FileText className={iconClass} />,
				},
			];
		}
		case "start":
			return [
				{
					name: "Workflow Input",
					icon: <FileText className={iconClass} />,
				},
			];
		case "custom":
			return [
				{
					name: "Custom Template",
					icon: <Code className={iconClass} />,
				},
			];
		case "specific": {
			const ids = config.source_node_ids ?? [];
			if (ids.length === 0) return [];
			const results: SourceInfo[] = [];
			for (const id of ids) {
				const node = availableNodes.find((n) => n.id === id);
				if (node) {
					results.push({
						name: node.data.name,
						icon: <GitMerge className={iconClass} />,
						nodeType: node.data.type,
					});
				}
			}
			return results;
		}
		default:
			return [];
	}
}

function getDescriptionText(
	config: InputSourceConfig,
	sources: SourceInfo[],
): string {
	if (config.source_mode === "previous") {
		if (sources.length === 1) {
			return `This agent will receive output from "${sources[0].name}"`;
		}
		if (sources.length > 1) {
			const names = sources.map((s) => s.name);
			return `This agent will receive output from ${names.join(", ")}`;
		}
		return "This agent will receive output from the previous node";
	}
	if (config.source_mode === "start") {
		return "This agent will receive the initial workflow input";
	}
	if (config.source_mode === "custom") {
		return "This agent will receive a custom-formatted input";
	}
	if (config.source_mode === "specific") {
		if (sources.length === 0) return "Select a source node above";
		if (sources.length === 1) {
			return `This agent will receive output from "${sources[0].name}"`;
		}
		const names = sources.map((s) => s.name);
		return `This agent will receive merged output from ${names.join(", ")}`;
	}
	return "";
}

export default function FlowPreview({
	config,
	availableNodes,
	currentNodeName,
	edges,
	nodeId,
}: FlowPreviewProps) {
	const sources = getSourceInfo(config, availableNodes, edges, nodeId);
	const description = getDescriptionText(config, sources);
	const isMulti = sources.length > 1;

	return (
		<div className="rounded-[4px] border border-slate-200 bg-white p-5 shadow-sm">
			<span className="text-[0.6rem] font-semibold capitalize text-slate-600">
				Preview
			</span>

			{/* Flow diagram */}
			<div className="mt-4 flex items-center justify-center gap-4">
				{/* Source side */}
				{sources.length === 0 ? (
					<div className="flex flex-col items-center gap-2 rounded-[4px] border border-dashed border-slate-300 bg-slate-50 px-4 py-3">
						<span className="text-xs text-slate-600">No source</span>
					</div>
				) : isMulti ? (
					<div className="flex flex-col gap-2">
						{sources.map((source, i) => (
							<SourcePill key={`${source.name}-${i}`} source={source} />
						))}
					</div>
				) : (
					<SourcePill source={sources[0]} />
				)}

				{/* Arrow */}
				<div className="flex flex-col items-center gap-1">
					{isMulti && (
						<GitMerge className="h-4 w-4 text-slate-500" />
					)}
					<div className="flow-arrow-pulse text-orange-600">
						<ArrowRight className="h-5 w-5" />
					</div>
				</div>

				{/* Destination */}
				<div
					className={clsx(
						"flex flex-col items-center gap-2 rounded-[4px] border px-4 py-3",
						"border-orange-500 bg-white shadow-sm",
					)}
				>
					<div className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-500 text-white">
						<Sparkles className="h-4 w-4" />
					</div>
					<span className="text-xs font-medium text-slate-900">
						{currentNodeName}
					</span>
				</div>
			</div>

			{/* Description */}
			<p className="mt-4 text-center text-xs text-slate-600">{description}</p>

			{/* Original input annotation */}
			{config.include_original_input && config.source_mode !== "start" && (
				<div className="mt-2 flex justify-center">
					<span className="inline-flex items-center gap-1.5 rounded-full border border-orange-400 bg-white px-3 py-1 text-[11px] font-medium text-orange-900">
						+ Original input
					</span>
				</div>
			)}

			{/* CSS for the subtle arrow animation */}
			<style>{`
				.flow-arrow-pulse {
					animation: flowPulse 2s ease-in-out infinite;
				}
				@keyframes flowPulse {
					0%, 100% { opacity: 0.5; transform: translateX(0); }
					50% { opacity: 1; transform: translateX(3px); }
				}
			`}</style>
		</div>
	);
}

function SourcePill({ source }: { source: SourceInfo }) {
	const colorRgb = source.nodeType
		? getNodeColorRgb(source.nodeType)
		: null;

	return (
		<div
			className="flex flex-col items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-4 py-3 shadow-sm"
			style={
				colorRgb
					? {
							borderColor: `rgba(${colorRgb}, 0.45)`,
						}
					: undefined
			}
		>
			{source.nodeType ? (
				getNodeIcon(source.nodeType)
			) : (
				<div className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-600">
					{source.icon}
				</div>
			)}
			<span className="text-xs font-medium text-slate-900">{source.name}</span>
		</div>
	);
}
