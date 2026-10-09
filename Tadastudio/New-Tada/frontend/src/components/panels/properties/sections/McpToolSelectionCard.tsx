"use client";

import { ChevronDown, ChevronRight, Search } from "lucide-react";
import type React from "react";
import { useCallback, useMemo, useState } from "react";
import Toggle from "@/components/ui/Toggle";
import type { McpToolInfo } from "@/components/dialogs/McpToolsViewerModal";

interface McpToolSelectionCardProps {
	tools: McpToolInfo[];
	toolPermissions: Record<string, boolean>;
	onToolPermissionsChange: (permissions: Record<string, boolean>) => void;
	providerColor: string;
	providerColorRgb: string;
	providerIcon?: React.ComponentType<{ className?: string }>;
	serverName: string;
}

const DESC_TRUNCATE_THRESHOLD = 120;

export default function McpToolSelectionCard({
	tools,
	toolPermissions,
	onToolPermissionsChange,
	providerColor,
	providerColorRgb,
	providerIcon: ProviderIcon,
	serverName,
}: McpToolSelectionCardProps) {
	const [searchQuery, setSearchQuery] = useState("");
	const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
	const [expandedDescriptions, setExpandedDescriptions] = useState<Set<string>>(new Set());

	const enabledCount = useMemo(() => {
		return tools.filter((t) => toolPermissions[t.name] !== false).length;
	}, [tools, toolPermissions]);

	const filteredTools = useMemo(() => {
		if (!searchQuery.trim()) return tools;
		const query = searchQuery.toLowerCase();
		return tools.filter(
			(tool) =>
				tool.name.toLowerCase().includes(query) ||
				tool.description.toLowerCase().includes(query),
		);
	}, [tools, searchQuery]);

	const toggleToolExpanded = useCallback((toolName: string) => {
		setExpandedTools((prev) => {
			const next = new Set(prev);
			if (next.has(toolName)) {
				next.delete(toolName);
			} else {
				next.add(toolName);
			}
			return next;
		});
	}, []);

	const toggleDescriptionExpanded = useCallback((toolName: string) => {
		setExpandedDescriptions((prev) => {
			const next = new Set(prev);
			if (next.has(toolName)) {
				next.delete(toolName);
			} else {
				next.add(toolName);
			}
			return next;
		});
	}, []);

	const handleToolToggle = useCallback(
		(toolName: string, enabled: boolean) => {
			const next = { ...toolPermissions };
			if (enabled) {
				delete next[toolName];
			} else {
				next[toolName] = false;
			}
			onToolPermissionsChange(next);
		},
		[toolPermissions, onToolPermissionsChange],
	);

	const handleEnableAll = useCallback(() => {
		onToolPermissionsChange({});
	}, [onToolPermissionsChange]);

	const handleDisableAll = useCallback(() => {
		const next: Record<string, boolean> = {};
		for (const tool of tools) {
			next[tool.name] = false;
		}
		onToolPermissionsChange(next);
	}, [tools, onToolPermissionsChange]);

	const hasParameters = (tool: McpToolInfo) =>
		tool.input_schema?.properties &&
		Object.keys(tool.input_schema.properties).length > 0;

	return (
		<div className="overflow-hidden rounded-[4px] border border-gray-200 bg-white shadow-sm">
			<div className="flex items-center justify-between px-3 py-2.5">
				<div className="flex items-center gap-2">
					{ProviderIcon && (
						<ProviderIcon className="h-3.5 w-3.5 flex-shrink-0 text-gray-600" />
					)}
					<span className="text-xs font-medium text-gray-900">
						Available Tools ({tools.length})
					</span>
				</div>
				<span className="text-[11px] text-gray-600">
					{enabledCount} of {tools.length} enabled
				</span>
			</div>

			<div className="px-3 pb-2">
				<div className="flex items-center gap-2">
					<div className="relative flex-1">
						<Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-500" />
						<input
							type="text"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							placeholder="Search tools..."
							className="w-full rounded-[4px] border border-gray-200 bg-white py-1.5 pl-8 pr-3 text-[11px] text-gray-900 placeholder:text-gray-400 transition-colors focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
						/>
					</div>
					<div className="flex flex-shrink-0 items-center gap-1.5">
						<button
							type="button"
							onClick={handleEnableAll}
							className="text-[10px] text-gray-600 transition-colors hover:text-slate-900"
						>
							All
						</button>
						<span className="text-[10px] text-gray-300">|</span>
						<button
							type="button"
							onClick={handleDisableAll}
							className="text-[10px] text-gray-600 transition-colors hover:text-slate-900"
						>
							None
						</button>
					</div>
				</div>
				{searchQuery && (
					<p className="mt-1 pl-0.5 text-[10px] text-gray-600">
						{filteredTools.length} of {tools.length} tools
					</p>
				)}
			</div>
			<div className="custom-scrollbar max-h-[320px] space-y-1.5 overflow-y-auto px-3 pb-3">
				{filteredTools.length === 0 ? (
					<div className="flex flex-col items-center justify-center py-6 text-center">
						<Search className="mb-2 h-5 w-5 text-gray-400 opacity-40" />
						<p className="text-[11px] text-gray-600">
							No tools match &ldquo;{searchQuery}&rdquo;
						</p>
					</div>
				) : (
					filteredTools.map((tool) => {
						const isExpanded = expandedTools.has(tool.name);
						const isDescExpanded = expandedDescriptions.has(tool.name);
						const hasParms = hasParameters(tool);
						const paramCount = hasParms
							? Object.keys(tool.input_schema!.properties!).length
							: 0;
						const isLongDesc = tool.description && tool.description.length > DESC_TRUNCATE_THRESHOLD;

						return (
							<div
								key={tool.name}
								className="overflow-hidden rounded-[4px] border border-gray-200 bg-white transition-colors hover:border-orange-300"
								style={{
									borderLeftWidth: "2px",
									borderLeftColor: `rgba(${providerColorRgb}, 0.5)`,
								}}
							>
								{/* Tool Header */}
								<div className="px-3 py-2">
									<div className="flex items-start justify-between gap-2">
										<div className="flex-1 min-w-0">
											<span className="text-[11px] font-mono font-semibold text-gray-900">
												{tool.name}
											</span>
											{hasParms && (
												<span
													className="text-[8px] px-1 py-0.5 rounded-full ml-1.5 inline-block align-middle"
													style={{
														backgroundColor: `rgba(${providerColorRgb}, 0.15)`,
														color: providerColor,
														border: `1px solid rgba(${providerColorRgb}, 0.3)`,
													}}
												>
													{paramCount} param{paramCount !== 1 ? "s" : ""}
												</span>
											)}
										</div>
										<div
											className="flex-shrink-0"
											onClick={(e) => e.stopPropagation()}
											onKeyDown={(e) => e.stopPropagation()}
										>
											<Toggle
												size="sm"
												checked={toolPermissions[tool.name] !== false}
												onChange={(checked) => handleToolToggle(tool.name, checked)}
												activeColor={providerColor}
											/>
										</div>
									</div>

									{/* Description */}
									{tool.description && (
										<div className="mt-1">
											<p
												className={`text-[10px] text-[color:var(--color-text-muted)] leading-relaxed ${
													!isDescExpanded && isLongDesc ? "line-clamp-2" : ""
												}`}
											>
												{tool.description}
											</p>
											{isLongDesc && (
												<button
													type="button"
													onClick={() => toggleDescriptionExpanded(tool.name)}
													className="text-[10px] mt-0.5 transition-colors hover:underline"
													style={{ color: providerColor }}
												>
													{isDescExpanded ? "Show less" : "Show more"}
												</button>
											)}
										</div>
									)}

									{/* View parameters link */}
									{hasParms && (
										<button
											type="button"
											onClick={() => toggleToolExpanded(tool.name)}
											className="flex items-center gap-1 mt-1.5 text-[10px] transition-colors hover:underline"
											style={{ color: providerColor }}
											aria-expanded={isExpanded}
										>
											{isExpanded ? (
												<ChevronDown className="w-3 h-3" />
											) : (
												<ChevronRight className="w-3 h-3" />
											)}
											{isExpanded ? "Hide parameters" : `View parameters (${paramCount})`}
										</button>
									)}
								</div>

								{/* Expandable Parameters */}
								{hasParms && isExpanded && (
									<div className="px-3 pb-2 pt-0 border-t border-[color:var(--color-border)]/30 mx-2 mb-1">
										<div className="pt-2 space-y-1.5">
											<p className="text-[0.55rem] capitalize text-[color:var(--color-text-muted)] font-semibold">
												Parameters
											</p>
											{Object.entries(
												tool.input_schema!.properties!,
											).map(([paramName, paramDef]) => {
												const isRequired =
													tool.input_schema?.required?.includes(paramName);
												return (
													<div
														key={paramName}
														className="rounded-[4px] border border-gray-200 bg-slate-50 px-2.5 py-1.5"
													>
														<div className="flex flex-wrap items-center gap-1.5">
															<span className="text-[10px] font-mono font-medium text-gray-900">
																{paramName}
															</span>
															{paramDef.type && (
																<span className="rounded bg-gray-100 px-1 py-0.5 text-[9px] text-gray-700">
																	{paramDef.type}
																</span>
															)}
															{isRequired && (
																<span className="rounded-full border border-amber-300 bg-amber-50 px-1 py-0.5 text-[8px] text-amber-900">
																	required
																</span>
															)}
														</div>
														{paramDef.description && (
															<p className="text-[9px] text-[color:var(--color-text-muted)] mt-0.5 leading-relaxed">
																{paramDef.description}
															</p>
														)}
														{paramDef.enum && paramDef.enum.length > 0 && (
															<div className="flex items-center gap-1 mt-0.5 flex-wrap">
																<span className="text-[8px] text-[color:var(--color-text-muted)]">
																	Values:
																</span>
																{paramDef.enum.map((v) => (
																	<span
																		key={v}
																		className="text-[8px] px-1 py-0.5 rounded bg-[color:var(--color-border)]/20 text-[color:var(--color-text-secondary)] font-mono"
																	>
																		{v}
																	</span>
																))}
															</div>
														)}
													</div>
												);
											})}
										</div>
									</div>
								)}
							</div>
						);
					})
				)}
			</div>
		</div>
	);
}
