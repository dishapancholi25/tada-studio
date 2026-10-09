"use client";

import clsx from "clsx";
import { Code, FileText, GitBranch, Link, Play, Sparkles } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import type { Node } from "reactflow";

interface DataSourceSectionProps {
	inputSource: string;
	sourceNodeId?: string;
	availableNodes: Node[];
	connectedSourceNode?: Node;
	onInputSourceChange: (source: string) => void;
	onSourceNodeIdChange: (nodeId?: string) => void;
}

const SOURCE_MODES = [
	{
		id: "previous",
		label: "Previous Node",
		description: "Output from the node directly before this one",
		icon: Link,
	},
	{
		id: "specific",
		label: "Specific Node",
		description: "Choose which node to pull data from",
		icon: GitBranch,
	},
	{
		id: "start",
		label: "Workflow Input",
		description: "The initial data that triggered this workflow",
		icon: Play,
	},
] as const;

const getNodeIcon = (nodeType: string) => {
	const baseClass =
		"flex h-7 w-7 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-gray-700 shadow-sm";
	const iconClass = "h-3.5 w-3.5";

	switch (nodeType) {
		case "START":
			return (
				<div
					className={clsx(
						baseClass,
						"border-emerald-300 bg-white text-emerald-800",
					)}
				>
					<FileText className={iconClass} />
				</div>
			);
		case "AGENT":
			return (
				<div
					className={clsx(
						baseClass,
						"border-blue-300 bg-white text-blue-800",
					)}
				>
					<GitBranch className={iconClass} />
				</div>
			);
		default:
			return (
				<div
					className={clsx(
						baseClass,
						"border-orange-300 bg-white text-orange-800",
					)}
				>
					<Code className={iconClass} />
				</div>
			);
	}
};

export default function DataSourceSection({
	inputSource,
	sourceNodeId,
	availableNodes,
	connectedSourceNode,
	onInputSourceChange,
	onSourceNodeIdChange,
}: DataSourceSectionProps) {
	const [nodePickerOpen, setNodePickerOpen] = useState(false);

	const selectedNode = useMemo(() => {
		if (inputSource === "specific" && sourceNodeId) {
			return availableNodes.find((n) => n.id === sourceNodeId);
		}
		return undefined;
	}, [inputSource, sourceNodeId, availableNodes]);

	const resolvedSourceLabel = useMemo(() => {
		if (inputSource === "previous") {
			return connectedSourceNode?.data?.name || "Previous node";
		}
		if (inputSource === "specific" && selectedNode) {
			return selectedNode.data?.name || "Selected node";
		}
		if (inputSource === "start") {
			return "Workflow input";
		}
		return "Not configured";
	}, [inputSource, connectedSourceNode, selectedNode]);

	const handleModeChange = useCallback(
		(mode: string) => {
			onInputSourceChange(mode);
			if (mode !== "specific") {
				onSourceNodeIdChange(undefined);
				setNodePickerOpen(false);
			} else {
				setNodePickerOpen(true);
			}
		},
		[onInputSourceChange, onSourceNodeIdChange],
	);

	const handleNodeSelect = useCallback(
		(nodeId: string) => {
			onSourceNodeIdChange(nodeId);
			setNodePickerOpen(false);
		},
		[onSourceNodeIdChange],
	);

	return (
		<div className="space-y-4">
			<div>
				<h3 className="mb-1 text-sm font-semibold text-gray-900">Data Source</h3>
				<p className="text-xs text-gray-600">
					Where does this condition get its data?
					{inputSource && (
						<>
							{" "}
							<span className="font-medium text-orange-700">
								{resolvedSourceLabel}
							</span>
						</>
					)}
				</p>
			</div>

			<div className="grid grid-cols-3 gap-2">
				{SOURCE_MODES.map((mode) => {
					const Icon = mode.icon;
					const isActive = inputSource === mode.id;
					return (
						<button
							key={mode.id}
							type="button"
							onClick={() => handleModeChange(mode.id)}
							className={clsx(
								"rounded-[4px] px-3 py-3 text-left transition-colors duration-200",
								isActive
									? "border-2 border-orange-500 bg-white text-gray-900 shadow-sm"
									: "border border-gray-200 bg-white text-gray-600 hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900",
							)}
						>
							<div className="mb-1 flex items-center gap-2">
								<Icon
									className={clsx(
										"h-3.5 w-3.5",
										isActive ? "text-orange-600" : "text-gray-500",
									)}
								/>
								<span className="text-xs font-semibold">{mode.label}</span>
							</div>
							<p
								className={clsx(
									"text-[10px] leading-tight",
									isActive ? "text-gray-600" : "text-gray-500",
								)}
							>
								{mode.description}
							</p>
						</button>
					);
				})}
			</div>

			{inputSource === "specific" && (
				<div className="mt-3 animate-in fade-in slide-in-from-top-1 duration-200">
					{selectedNode ? (
						<div className="flex items-center justify-between rounded-[4px] border border-gray-200 bg-white px-3 py-2.5 shadow-sm">
							<div className="flex items-center gap-2.5">
								{getNodeIcon(selectedNode.data?.type ?? "AGENT")}
								<div>
									<span className="block text-sm font-medium text-gray-900">
										{selectedNode.data?.name}
									</span>
									<span className="text-[10px] text-gray-600">
										{selectedNode.data?.type}
										{selectedNode.data?.agent_config?.structured_outputs
											?.length > 0 && (
											<span className="ml-1.5 inline-flex items-center gap-0.5 text-blue-800">
												<Sparkles className="h-2.5 w-2.5" />
												Structured
											</span>
										)}
									</span>
								</div>
							</div>
							<button
								type="button"
								onClick={() => setNodePickerOpen(!nodePickerOpen)}
								className="rounded-[4px] border border-gray-200 bg-white px-2.5 py-1 text-[10px] font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
							>
								Change
							</button>
						</div>
					) : (
						<div className="rounded-[4px] border border-dashed border-gray-300 bg-white px-3 py-2.5 text-xs text-gray-600">
							Select a source node below
						</div>
					)}

					{(nodePickerOpen || !selectedNode) && (
						<div className="mt-2 grid gap-1.5 sm:grid-cols-2">
							{availableNodes.map((n) => {
								const isActive = sourceNodeId === n.id;
								const isStructured = Boolean(
									n.data?.agent_config?.structured_outputs?.length,
								);
								return (
									<button
										key={n.id}
										type="button"
										onClick={() => handleNodeSelect(n.id)}
										className={clsx(
											"flex items-center gap-2.5 rounded-[4px] border px-3 py-2 text-left transition-colors duration-200",
											isActive
												? "border-2 border-orange-500 bg-white text-gray-900 shadow-sm"
												: "border border-gray-200 bg-white hover:border-orange-400 hover:bg-slate-50",
										)}
									>
										{getNodeIcon(n.data?.type)}
										<div className="min-w-0 flex-1">
											<div className="flex items-center gap-1.5 truncate text-sm font-medium text-gray-900">
												{n.data?.name}
												{isStructured && (
													<Sparkles className="h-2.5 w-2.5 flex-shrink-0 text-blue-700" />
												)}
											</div>
											<p className="truncate text-[10px] text-gray-600">
												{n.data?.type}
											</p>
										</div>
									</button>
								);
							})}
						</div>
					)}
				</div>
			)}
		</div>
	);
}
