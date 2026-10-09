"use client";

import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import {
	CheckCircle2,
	ChevronDown,
	ChevronRight,
	Database,
	FileCode,
	FileJson,
	Filter,
	GitBranch,
	GitMerge,
	Layers,
	Layout,
	Plus,
	Save,
	Settings,
	Target,
	X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Node } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import Button from "../../ui/Button";
import FormInput from "../../ui/FormInput";

interface EndNodeConfig {
	input_source?: string;
	source_node_ids?: string[];
	output_structure?: string;
	include_metadata?: boolean;
	include_node_names?: boolean;
	custom_output_template?: string;
	include_fields?: string[];
	exclude_fields?: string[];
	wrap_response?: boolean;
	response_key?: string;
}

interface EndNodePropertiesPanelProps {
	nodeId: string;
	onClose: () => void;
}

interface InputSourceOption {
	value: string;
	title: string;
	subtitle: string;
	description: string;
	Icon: LucideIcon;
	accentClass: string;
}

interface OutputStructureOption {
	value: string;
	title: string;
	subtitle: string;
	description: string;
	Icon: LucideIcon;
	accentClass: string;
	badge?: string;
}

const INPUT_SOURCE_OPTIONS: InputSourceOption[] = [
	{
		value: "all",
		title: "All Nodes",
		subtitle: "Complete workflow",
		description: "Outputs from all nodes",
		Icon: GitMerge,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.05)] to-transparent",
	},
	{
		value: "previous",
		title: "Previous Node Only",
		subtitle: "Last step",
		description: "Output from the preceding node",
		Icon: GitBranch,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.05)] to-transparent",
	},
	{
		value: "specific",
		title: "Specific Node",
		subtitle: "Pick one",
		description: "Choose one node",
		Icon: Target,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.05)] to-transparent",
	},
	{
		value: "multiple",
		title: "Multiple Nodes",
		subtitle: "Combine many",
		description: "Combine outputs from selected nodes",
		Icon: Layers,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.05)] to-transparent",
	},
];

const OUTPUT_STRUCTURE_OPTIONS: OutputStructureOption[] = [
	{
		value: "full",
		title: "Full Output",
		subtitle: "Complete data",
		description: "All data with metadata",
		Icon: Database,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.05)] to-transparent",
	},
	{
		value: "compact",
		title: "Compact",
		subtitle: "Essential only",
		description: "Essential data only",
		Icon: Layout,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.05)] to-transparent",
	},
	{
		value: "summary",
		title: "Summary",
		subtitle: "Brief overview",
		description: "Brief summary",
		Icon: FileJson,
		accentClass:
			"from-[rgba(var(--color-primary-rgb),0.2)] via-[rgba(var(--color-primary-rgb),0.05)] to-transparent",
	},
	{
		value: "custom",
		title: "Custom Template",
		subtitle: "Your format",
		description: "Your JSON template",
		Icon: FileCode,
		accentClass: "from-amber-500/20 via-amber-500/5 to-transparent",
		badge: "Advanced",
	},
];

export default function EndNodePropertiesPanel({
	nodeId,
	onClose,
}: EndNodePropertiesPanelProps) {
	const { nodes, updateNode } = useGraph();
	const node = nodes.find((n) => n.id === nodeId);

	const [config, setConfig] = useState<EndNodeConfig>({
		input_source: "all",
		source_node_ids: [],
		output_structure: "full",
		include_metadata: true,
		include_node_names: true,
		custom_output_template: "",
		include_fields: [],
		exclude_fields: [],
		wrap_response: true,
		response_key: "result",
	});

	const [saving, setSaving] = useState(false);
	const [selectedNodes, setSelectedNodes] = useState<string[]>([]);
	const [includeField, setIncludeField] = useState("");
	const [excludeField, setExcludeField] = useState("");
	const [showAdvanced, setShowAdvanced] = useState(false);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleModalClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleClose = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleInputSourceChange = useCallback(
		(value: string) => {
			console.log(
				"[END-NODE-DEBUG] Input source changing from:",
				config.input_source,
				"to:",
				value,
			);
			setConfig((prev) => {
				const newConfig = {
					...prev,
					input_source: value,
					source_node_ids:
						value === "all" || value === "previous" ? [] : prev.source_node_ids,
				};
				console.log(
					"[END-NODE-DEBUG] New config after input source change:",
					newConfig,
				);
				return newConfig;
			});
			if (value === "all" || value === "previous") {
				setSelectedNodes([]);
			}
		},
		[config.input_source],
	);

	const handleNodeSelectionChange = useCallback(
		(nodeId: string) => {
			setSelectedNodes((prev) => {
				if (config.input_source === "specific") {
					return [nodeId];
				} else {
					if (prev.includes(nodeId)) {
						return prev.filter((id) => id !== nodeId);
					} else {
						return [...prev, nodeId];
					}
				}
			});
		},
		[config.input_source],
	);

	const handleOutputStructureChange = useCallback((value: string) => {
		console.log("[END-NODE-DEBUG] Output structure changing to:", value);
		setConfig((prev) => {
			const newConfig = { ...prev, output_structure: value };
			console.log(
				"[END-NODE-DEBUG] New config after output structure change:",
				newConfig,
			);
			return newConfig;
		});
	}, []);

	const handleCustomTemplateChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setConfig((prev) => ({
				...prev,
				custom_output_template: e.target.value,
			}));
		},
		[],
	);

	const handleToggle = useCallback((field: keyof EndNodeConfig) => {
		setConfig((prev) => ({ ...prev, [field]: !prev[field] }));
	}, []);

	const handleShowAdvancedToggle = useCallback(() => {
		setShowAdvanced(!showAdvanced);
	}, [showAdvanced]);

	const handleResponseKeyChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig((prev) => ({ ...prev, response_key: e.target.value }));
		},
		[],
	);

	const handleIncludeFieldChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setIncludeField(e.target.value);
		},
		[],
	);

	const handleAddIncludeField = useCallback(() => {
		if (includeField && !config.include_fields?.includes(includeField)) {
			setConfig((prev) => ({
				...prev,
				include_fields: [...(prev.include_fields || []), includeField],
			}));
			setIncludeField("");
		}
	}, [includeField, config.include_fields]);

	const handleRemoveIncludeField = useCallback((field: string) => {
		setConfig((prev) => ({
			...prev,
			include_fields: prev.include_fields?.filter((f) => f !== field),
		}));
	}, []);

	const handleExcludeFieldChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setExcludeField(e.target.value);
		},
		[],
	);

	const handleAddExcludeField = useCallback(() => {
		if (excludeField && !config.exclude_fields?.includes(excludeField)) {
			setConfig((prev) => ({
				...prev,
				exclude_fields: [...(prev.exclude_fields || []), excludeField],
			}));
			setExcludeField("");
		}
	}, [excludeField, config.exclude_fields]);

	const handleRemoveExcludeField = useCallback((field: string) => {
		setConfig((prev) => ({
			...prev,
			exclude_fields: prev.exclude_fields?.filter((f) => f !== field),
		}));
	}, []);

	// Factory functions for handlers with parameters
	const createNodeSelectionChangeHandler = useCallback(
		(nodeId: string) => () => {
			handleNodeSelectionChange(nodeId);
		},
		[handleNodeSelectionChange],
	);

	const createRemoveIncludeFieldHandler = useCallback(
		(field: string) => () => {
			handleRemoveIncludeField(field);
		},
		[handleRemoveIncludeField],
	);

	const createRemoveExcludeFieldHandler = useCallback(
		(field: string) => () => {
			handleRemoveExcludeField(field);
		},
		[handleRemoveExcludeField],
	);

	// Get all available nodes for input selection (excluding current end node)
	const availableNodes = useMemo(() => {
		if (!node) return [];
		return nodes.filter(
			(n) =>
				n.id !== nodeId && n.data?.type !== "START" && n.data?.type !== "END",
		);
	}, [nodes, node, nodeId]);

	// Initialize with existing config - only run once when nodeId changes
	useEffect(() => {
		console.log("[END-NODE-DEBUG] useEffect triggered - nodeId:", nodeId);
		const currentNode = nodes.find((n) => n.id === nodeId);
		console.log("[END-NODE-DEBUG] Current node data:", currentNode?.data);
		if (currentNode?.data) {
			if (currentNode.data.end_node_config) {
				const existingConfig = currentNode.data.end_node_config;
				console.log(
					"[END-NODE-DEBUG] Loading existing config from node:",
					existingConfig,
				);
				const newConfig = {
					...existingConfig,
					source_node_ids: existingConfig.source_node_ids || [],
					include_fields: existingConfig.include_fields || [],
					exclude_fields: existingConfig.exclude_fields || [],
				};
				console.log("[END-NODE-DEBUG] Setting config to:", newConfig);
				setConfig(newConfig);
				setSelectedNodes(existingConfig.source_node_ids || []);
			} else {
				console.log(
					"[END-NODE-DEBUG] No existing config found, using defaults",
				);
			}
		}
		// Only re-run when nodeId changes (switching to different node)
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [nodeId]);

	const handleSave = async () => {
		console.log("[END-NODE-DEBUG] ========================================");
		console.log("[END-NODE-DEBUG] SAVE CLICKED");
		console.log("[END-NODE-DEBUG] Current config state:", config);
		console.log("[END-NODE-DEBUG] Selected nodes state:", selectedNodes);
		console.log("[END-NODE-DEBUG] ========================================");

		setSaving(true);
		try {
			const saveConfig = {
				...config,
				source_node_ids: selectedNodes,
			};

			console.log("[END-NODE-DEBUG] === SAVING END NODE CONFIG ===");
			console.log("[END-NODE-DEBUG] Node ID:", nodeId);
			console.log("[END-NODE-DEBUG] Final config to save:", saveConfig);
			console.log("[END-NODE-DEBUG] Config fields:", {
				input_source: saveConfig.input_source,
				output_structure: saveConfig.output_structure,
				source_node_ids: saveConfig.source_node_ids,
				include_metadata: saveConfig.include_metadata,
				include_node_names: saveConfig.include_node_names,
			});

			const result = await updateNode(nodeId, {
				end_node_config: saveConfig,
			});

			console.log("[END-NODE-DEBUG] Update result:", result);

			setTimeout(() => {
				onClose();
			}, 100);
		} catch (error) {
			console.error("[END-NODE-DEBUG] Failed to save end node config:", error);
		} finally {
			setSaving(false);
		}
	};

	const filterCount =
		(config.include_fields?.length || 0) + (config.exclude_fields?.length || 0);

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center overflow-y-auto bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="mb-8 w-full max-w-4xl sm:mb-16 lg:mb-20"
				onClick={handleModalClick}
			>
				<div className="flex max-h-[calc(100vh-4rem)] flex-col overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)] sm:max-h-[calc(100vh-8rem)] lg:max-h-[calc(100vh-10rem)]">
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex items-center justify-between gap-4 px-6 pb-4 pt-5 sm:px-6">
							<div className="flex min-w-0 items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<Target className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Node configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										Workflow Output
									</h2>
									<p className="text-xs text-gray-600">
										Configure what data this workflow returns.
									</p>
								</div>
							</div>
							<button
								type="button"
								onClick={handleClose}
								className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					<div className="min-h-0 flex-1 overflow-y-auto bg-slate-50 px-5 py-6 sm:px-7">
						<div className="space-y-6">
							{/* Input Source Selection */}
							<section className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
								<div className="mb-5">
									<p className="mb-1 text-xs font-semibold capitalize tracking-wide text-gray-600">
										Source
									</p>
									<h3 className="text-lg font-semibold text-gray-900">
										Select input source
									</h3>
								</div>
								<div className="grid gap-4 md:grid-cols-2">
									{INPUT_SOURCE_OPTIONS.map((option) => {
										const isSelected = option.value === config.input_source;
										return (
											<button
												key={option.value}
												type="button"
												onClick={() => handleInputSourceChange(option.value)}
												aria-pressed={isSelected}
												className={clsx(
													"group relative rounded-[4px] border px-4 py-4 text-left transition-colors duration-200",
													"border-transparent bg-white hover:border-orange-400 hover:bg-slate-50",
													isSelected &&
														"border-orange-500 shadow-sm hover:border-orange-500",
												)}
											>
												<div className="relative flex items-start gap-3">
													<div
														className={clsx(
															"flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border transition-colors",
															isSelected
																? "border-orange-400 bg-white text-orange-700"
																: "border-gray-200 bg-slate-100 text-gray-600 group-hover:border-orange-300 group-hover:text-slate-900",
														)}
													>
														<option.Icon className="h-5 w-5" />
													</div>
													<div className="min-w-0 flex-1 space-y-1">
														<div className="flex items-center gap-2">
															<h4 className="font-semibold text-gray-900 group-hover:text-slate-900">
																{option.title}
															</h4>
															{isSelected && (
																<CheckCircle2 className="h-4 w-4 text-orange-600" />
															)}
														</div>
														<p className="text-xs text-gray-600">
															{option.description}
														</p>
													</div>
												</div>
											</button>
										);
									})}
								</div>
							</section>

							{/* Node Selection for specific/multiple modes */}
							{(config.input_source === "specific" ||
								config.input_source === "multiple") && (
								<section className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
									<div className="mb-5">
										<p className="mb-1 text-xs font-semibold capitalize tracking-wide text-gray-600">
											Node Picker
										</p>
										<h3 className="text-lg font-semibold text-gray-900">
											{config.input_source === "specific"
												? "Select node"
												: "Select nodes"}
										</h3>
									</div>
									<div className="space-y-2 max-h-64 overflow-y-auto">
										{availableNodes.length === 0 ? (
											<div className="rounded-[4px] border border-gray-200 bg-slate-50 px-4 py-8 text-center">
												<p className="text-sm text-gray-600">
													No nodes available
												</p>
											</div>
										) : (
											availableNodes.map((n) => {
												const isSelected = selectedNodes.includes(n.id);
												return (
													<label
														key={n.id}
														className={clsx(
															"flex cursor-pointer items-center gap-3 rounded-[4px] border p-3 transition-colors duration-200",
															isSelected
																? "border-orange-500 bg-white shadow-sm"
																: "border-transparent bg-white hover:border-orange-400 hover:bg-slate-50",
														)}
													>
														<input
															type={
																config.input_source === "specific"
																	? "radio"
																	: "checkbox"
															}
															name={
																config.input_source === "specific"
																	? "nodeSelection"
																	: undefined
															}
															checked={isSelected}
															onChange={createNodeSelectionChangeHandler(n.id)}
															className="h-4 w-4 accent-[color:var(--color-primary)] border-[color:var(--color-border)]"
														/>
														<div className="min-w-0 flex-1">
															<span className="text-sm font-medium text-gray-900">
																{n.data.name}
															</span>
														</div>
														<span className="rounded-[4px] border border-gray-200 bg-slate-100 px-2 py-1 text-xs font-medium capitalize text-gray-700">
															{n.data.type}
														</span>
													</label>
												);
											})
										)}
									</div>
								</section>
							)}

							{/* Output Structure */}
							<section className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
								<div className="mb-5">
									<p className="mb-1 text-xs font-semibold capitalize tracking-wide text-gray-600">
										Format
									</p>
									<h3 className="text-lg font-semibold text-gray-900">
										Output format
									</h3>
								</div>
								<div className="grid gap-4 md:grid-cols-2">
									{OUTPUT_STRUCTURE_OPTIONS.map((option) => {
										const isSelected = option.value === config.output_structure;
										return (
											<button
												key={option.value}
												type="button"
												onClick={() =>
													handleOutputStructureChange(option.value)
												}
												aria-pressed={isSelected}
												className={clsx(
													"group relative rounded-[4px] border px-4 py-4 text-left transition-colors duration-200",
													"border-transparent bg-white hover:border-orange-400 hover:bg-slate-50",
													isSelected &&
														"border-orange-500 shadow-sm hover:border-orange-500",
												)}
											>
												<div className="relative flex items-start gap-3">
													<div
														className={clsx(
															"flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border transition-colors",
															isSelected
																? "border-orange-400 bg-white text-orange-700"
																: "border-gray-200 bg-slate-100 text-gray-600 group-hover:border-orange-300 group-hover:text-slate-900",
														)}
													>
														<option.Icon className="h-5 w-5" />
													</div>
													<div className="min-w-0 flex-1 space-y-1">
														<div className="flex flex-wrap items-center gap-2">
															<h4 className="font-semibold text-gray-900 group-hover:text-slate-900">
																{option.title}
															</h4>
															{option.badge && (
																<span className="rounded-[4px] border border-amber-400 bg-white px-2 py-0.5 text-[10px] font-semibold capitalize tracking-wide text-amber-900">
																	{option.badge}
																</span>
															)}
															{isSelected && (
																<CheckCircle2 className="h-4 w-4 text-orange-600" />
															)}
														</div>
														<p className="text-xs text-gray-600">
															{option.description}
														</p>
													</div>
												</div>
											</button>
										);
									})}
								</div>
							</section>

							{/* Custom Template */}
							{config.output_structure === "custom" && (
								<section className="rounded-[4px] border border-amber-300 bg-white p-6 shadow-sm">
									<div className="mb-4">
										<div className="mb-1 flex items-center gap-2">
											<FileCode className="h-4 w-4 text-amber-800" />
											<p className="text-xs font-semibold capitalize tracking-wide text-amber-900">
												Custom Template
											</p>
										</div>
										<h3 className="text-lg font-semibold text-gray-900">
											JSON template
										</h3>
										<p className="mt-1 text-xs text-gray-600">
											Use{" "}
											<code className="rounded-[4px] border border-gray-200 bg-slate-50 px-1 py-0.5 text-xs text-gray-900">
												{"{{output}}"}
											</code>{" "}
											and{" "}
											<code className="rounded-[4px] border border-gray-200 bg-slate-50 px-1 py-0.5 text-xs text-gray-900">
												{"{{metadata}}"}
											</code>{" "}
											placeholders.
										</p>
									</div>
									<textarea
										value={config.custom_output_template || ""}
										onChange={handleCustomTemplateChange}
										placeholder='{"result": "{{output}}", "metadata": "{{metadata}}"}'
										className="h-32 w-full resize-none rounded-[4px] border border-gray-200 bg-white px-4 py-3 font-mono text-sm text-gray-900 placeholder:text-gray-400 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-400/40"
									/>
								</section>
							)}

							{/* Metadata Options */}
							<section className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
								<div className="mb-5">
									<p className="mb-1 text-xs font-semibold capitalize tracking-wide text-gray-600">
										Options
									</p>
									<h3 className="text-lg font-semibold text-gray-900">
										Include in output
									</h3>
								</div>
								<div className="space-y-3">
									<label className="flex cursor-pointer items-center justify-between rounded-[4px] border border-transparent bg-white p-4 transition-colors hover:border-orange-400 hover:bg-slate-50">
										<div className="flex items-center gap-3">
											<div className="flex h-9 w-9 items-center justify-center rounded-[4px] border border-blue-200 bg-white text-blue-700">
												<Database className="h-4 w-4" />
											</div>
											<div>
												<span className="text-sm font-medium text-gray-900">
													Metadata
												</span>
												<p className="text-xs text-gray-600">
													Timestamps, execution info
												</p>
											</div>
										</div>
										<button
											type="button"
											role="switch"
											aria-checked={config.include_metadata}
											onClick={() => handleToggle("include_metadata")}
											className={clsx(
												"relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
												config.include_metadata
													? "bg-orange-600"
													: "bg-gray-300",
											)}
										>
											<span
												className={clsx(
													"inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
													config.include_metadata
														? "translate-x-6"
														: "translate-x-1",
												)}
											/>
										</button>
									</label>

									<label className="flex cursor-pointer items-center justify-between rounded-[4px] border border-transparent bg-white p-4 transition-colors hover:border-orange-400 hover:bg-slate-50">
										<div className="flex items-center gap-3">
											<div className="flex h-9 w-9 items-center justify-center rounded-[4px] border border-purple-200 bg-white text-purple-800">
												<GitBranch className="h-4 w-4" />
											</div>
											<div>
												<span className="text-sm font-medium text-gray-900">
													Node Names
												</span>
												<p className="text-xs text-gray-600">
													Source node labels
												</p>
											</div>
										</div>
										<button
											type="button"
											role="switch"
											aria-checked={config.include_node_names}
											onClick={() => handleToggle("include_node_names")}
											className={clsx(
												"relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
												config.include_node_names
													? "bg-orange-600"
													: "bg-gray-300",
											)}
										>
											<span
												className={clsx(
													"inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
													config.include_node_names
														? "translate-x-6"
														: "translate-x-1",
												)}
											/>
										</button>
									</label>

									<label className="flex cursor-pointer items-center justify-between rounded-[4px] border border-transparent bg-white p-4 transition-colors hover:border-orange-400 hover:bg-slate-50">
										<div className="flex items-center gap-3">
											<div className="flex h-9 w-9 items-center justify-center rounded-[4px] border border-orange-300 bg-white text-orange-800">
												<FileJson className="h-4 w-4" />
											</div>
											<div>
												<span className="text-sm font-medium text-gray-900">
													API Wrapper
												</span>
												<p className="text-xs text-gray-600">
													Standard API response structure
												</p>
											</div>
										</div>
										<button
											type="button"
											role="switch"
											aria-checked={config.wrap_response}
											onClick={() => handleToggle("wrap_response")}
											className={clsx(
												"relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
												config.wrap_response
													? "bg-orange-600"
													: "bg-gray-300",
											)}
										>
											<span
												className={clsx(
													"inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
													config.wrap_response
														? "translate-x-6"
														: "translate-x-1",
												)}
											/>
										</button>
									</label>
								</div>
							</section>

							{/* Advanced Options */}
							<section className="overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-sm">
								<button
									type="button"
									onClick={handleShowAdvancedToggle}
									className="flex w-full items-center justify-between p-6 text-left transition-colors hover:bg-slate-50"
								>
									<div className="flex items-center gap-3">
										<div className="flex h-9 w-9 items-center justify-center rounded-[4px] border border-amber-400 bg-white text-amber-900">
											<Settings className="h-4 w-4" />
										</div>
										<div>
											<h3 className="text-base font-semibold text-gray-900">
												Advanced Options
											</h3>
											<p className="text-xs text-gray-600">
												{filterCount > 0
													? `${filterCount} filter${filterCount > 1 ? "s" : ""} configured`
													: "Field filtering and custom keys"}
											</p>
										</div>
									</div>
									<div className="flex items-center gap-2">
										{filterCount > 0 && (
											<span className="rounded-[4px] border border-gray-200 bg-slate-100 px-2.5 py-1 text-xs font-medium text-gray-900">
												{filterCount}
											</span>
										)}
										{showAdvanced ? (
											<ChevronDown className="h-5 w-5 text-gray-600" />
										) : (
											<ChevronRight className="h-5 w-5 text-gray-600" />
										)}
									</div>
								</button>

								{showAdvanced && (
									<div className="space-y-5 border-t border-gray-200 px-6 pb-6 pt-0">
										{config.wrap_response && (
											<div className="pt-4">
												<label className="mb-2 block text-sm font-medium text-gray-900">
													Response key
												</label>
												<FormInput
													value={config.response_key || "result"}
													onChange={handleResponseKeyChange}
													placeholder="result"
													className="!rounded-[4px] !border-gray-200 !bg-white !text-gray-900 focus:!ring-orange-400/40"
												/>
											</div>
										)}

										<div className={!config.wrap_response ? "pt-4" : ""}>
											<div className="mb-2 flex items-center gap-2">
												<Filter className="h-4 w-4 text-orange-600" />
												<label className="block text-sm font-medium text-gray-900">
													Include fields
												</label>
											</div>
											<p className="mb-3 text-xs text-gray-600">
												Only include these fields in output
											</p>
											<div className="flex gap-2">
												<FormInput
													value={includeField}
													onChange={handleIncludeFieldChange}
													placeholder="Field name"
													className="flex-1 !rounded-[4px] !border-gray-200 !bg-white !text-gray-900 focus:!ring-orange-400/40"
												/>
												<Button
													onClick={handleAddIncludeField}
													variant="primary"
													size="sm"
													disabled={
														!includeField ||
														config.include_fields?.includes(includeField)
													}
												>
													<Plus className="mr-1 h-4 w-4" />
													Add
												</Button>
											</div>
											{config.include_fields &&
												config.include_fields.length > 0 && (
													<div className="mt-3 flex flex-wrap gap-2">
														{config.include_fields.map((field) => (
															<span
																key={field}
																className="inline-flex items-center gap-1.5 rounded-[4px] border border-orange-400 bg-white px-3 py-1.5 text-sm text-orange-950"
															>
																{field}
																<button
																	type="button"
																	onClick={createRemoveIncludeFieldHandler(
																		field,
																	)}
																	className="text-orange-900 transition-colors hover:text-gray-950"
																>
																	<X className="h-3.5 w-3.5" />
																</button>
															</span>
														))}
													</div>
												)}
										</div>

										<div>
											<div className="mb-2 flex items-center gap-2">
												<Filter className="h-4 w-4 text-red-600" />
												<label className="block text-sm font-medium text-gray-900">
													Exclude fields
												</label>
											</div>
											<p className="mb-3 text-xs text-gray-600">
												Remove these fields from output
											</p>
											<div className="flex gap-2">
												<FormInput
													value={excludeField}
													onChange={handleExcludeFieldChange}
													placeholder="Field name"
													className="flex-1 !rounded-[4px] !border-gray-200 !bg-white !text-gray-900 focus:!ring-orange-400/40"
												/>
												<Button
													onClick={handleAddExcludeField}
													variant="danger"
													size="sm"
													disabled={
														!excludeField ||
														config.exclude_fields?.includes(excludeField)
													}
												>
													<Plus className="mr-1 h-4 w-4" />
													Add
												</Button>
											</div>
											{config.exclude_fields &&
												config.exclude_fields.length > 0 && (
													<div className="mt-3 flex flex-wrap gap-2">
														{config.exclude_fields.map((field) => (
															<span
																key={field}
																className="inline-flex items-center gap-1.5 rounded-[4px] border border-red-300 bg-white px-3 py-1.5 text-sm text-red-900"
															>
																{field}
																<button
																	type="button"
																	onClick={createRemoveExcludeFieldHandler(
																		field,
																	)}
																	className="text-red-800 transition-colors hover:text-gray-950"
																>
																	<X className="h-3.5 w-3.5" />
																</button>
															</span>
														))}
													</div>
												)}
										</div>
									</div>
								)}
							</section>
						</div>
					</div>

					<div className="flex-none border-t border-gray-200 bg-white px-5 py-4 sm:px-6">
						<div className="flex items-center justify-end gap-3">
							<Button
								onClick={handleClose}
								variant="ghost"
								size="md"
								className="border border-gray-200 bg-white !text-gray-700 hover:!border-orange-400 hover:!bg-slate-50 hover:!text-orange-800"
							>
								Cancel
							</Button>
							<Button
								onClick={() => void handleSave()}
								loading={saving}
								variant="primary"
								size="md"
								className="gap-2 shadow-sm"
							>
								<Save className="h-4 w-4" />
								Save
							</Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
