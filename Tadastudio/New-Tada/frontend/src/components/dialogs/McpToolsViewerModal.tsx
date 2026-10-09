"use client";

import { ChevronDown, ChevronRight, Search, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import Toggle from "@/components/ui/Toggle";

export interface McpToolInfo {
	name: string;
	description: string;
	input_schema?: {
		type?: string;
		properties?: Record<
			string,
			{
				type?: string;
				description?: string;
				enum?: string[];
				default?: unknown;
			}
		>;
		required?: string[];
	};
}

interface McpToolsViewerModalProps {
	isOpen: boolean;
	onClose: () => void;
	tools: McpToolInfo[];
	serverName: string;
	providerColor: string;
	providerColorRgb: string;
	providerIcon?: React.ComponentType<{ className?: string }>;
	toolPermissions?: Record<string, boolean>;
	onToolPermissionsChange?: (permissions: Record<string, boolean>) => void;
}

export default function McpToolsViewerModal({
	isOpen,
	onClose,
	tools,
	serverName,
	providerColor,
	providerColorRgb,
	providerIcon: ProviderIcon,
	toolPermissions,
	onToolPermissionsChange,
}: McpToolsViewerModalProps) {
	const isInteractive = Boolean(onToolPermissionsChange);
	const [mounted, setMounted] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");
	const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
	const [expandedDescriptions, setExpandedDescriptions] = useState<Set<string>>(new Set());
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, isOpen);

	// Reset state when modal opens
	useEffect(() => {
		if (isOpen) {
			setSearchQuery("");
			setExpandedTools(new Set());
			setExpandedDescriptions(new Set());
		}
	}, [isOpen]);

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

	const enabledCount = useMemo(() => {
		if (!toolPermissions) return tools.length;
		return tools.filter((t) => toolPermissions[t.name] !== false).length;
	}, [tools, toolPermissions]);

	const handleToolToggle = useCallback(
		(toolName: string, enabled: boolean) => {
			if (!onToolPermissionsChange) return;
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
		if (!onToolPermissionsChange) return;
		onToolPermissionsChange({});
	}, [onToolPermissionsChange]);

	const handleDisableAll = useCallback(() => {
		if (!onToolPermissionsChange) return;
		const next: Record<string, boolean> = {};
		for (const tool of tools) {
			next[tool.name] = false;
		}
		onToolPermissionsChange(next);
	}, [tools, onToolPermissionsChange]);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleDialogClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	if (!isOpen || !mounted) {
		return null;
	}

	const hasParameters = (tool: McpToolInfo) =>
		tool.input_schema?.properties &&
		Object.keys(tool.input_schema.properties).length > 0;

	const DESC_TRUNCATE_THRESHOLD = 120;

	return createPortal(
		<div
			className="fixed inset-0 bg-black/70 backdrop-blur-xl flex items-center justify-center z-[140] animate-fadeIn"
			onClick={handleBackdropClick}
			role="presentation"
		>
			{/* Modal Shell with Gradient Border */}
			<div
				className="rounded-[32px] p-[1px] shadow-[0_35px_120px_rgba(0,0,0,0.65)]"
				style={{
					background: `linear-gradient(to bottom right, rgba(${providerColorRgb}, 0.5), transparent, rgba(${providerColorRgb}, 0.18))`,
				}}
				onClick={handleDialogClick}
			>
				<div
					ref={dialogRef}
					className="rounded-[30px] border border-slate-200 bg-white overflow-hidden max-w-4xl w-[90vw] max-h-[85vh] flex flex-col shadow-[0_25px_60px_rgba(0,0,0,0.15)]"
					role="dialog"
					aria-modal="true"
					aria-labelledby="tools-viewer-title"
				>
					{/* Header */}
					<div className="flex-shrink-0 flex items-center justify-between px-6 py-5 border-b border-slate-200">
						<div className="flex items-center gap-3">
							{ProviderIcon && (
								<div
									className="h-10 w-10 rounded-xl flex items-center justify-center"
									style={{
										backgroundColor: `rgba(${providerColorRgb}, 0.12)`,
										border: `1px solid rgba(${providerColorRgb}, 0.35)`,
										boxShadow: `0 0 30px rgba(${providerColorRgb}, 0.25)`,
									}}
								>
									<ProviderIcon
										className="w-5 h-5"
									/>
								</div>
							)}
							<div>
								<h2
									id="tools-viewer-title"
									className="text-lg font-semibold text-slate-900"
								>
									{serverName}
								</h2>
								<p className="text-xs text-[color:var(--color-text-muted)]">
									{isInteractive
										? `${enabledCount} of ${tools.length} tool${tools.length !== 1 ? "s" : ""} enabled`
										: `${tools.length} tool${tools.length !== 1 ? "s" : ""} available`}
								</p>
							</div>
						</div>
						<button
							type="button"
							onClick={onClose}
							className="p-2 rounded-xl hover:bg-[color:var(--color-surface)] text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
							aria-label="Close"
						>
							<X className="w-5 h-5" />
						</button>
					</div>

					{/* Search Bar */}
					<div className="flex-shrink-0 px-6 py-3 border-b border-[color:var(--color-border)]/40">
						<div className="flex items-center gap-3">
							<div className="relative flex-1">
								<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
								<input
									type="text"
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									placeholder="Search tools..."
									className="w-full pl-9 pr-4 py-2 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)]/60 rounded-xl text-slate-900 text-sm placeholder-[color:var(--color-text-muted)] focus:outline-none focus:border-[rgba(var(--color-primary-rgb),0.5)] transition-colors"
								/>
							</div>
							{isInteractive && (
								<div className="flex items-center gap-2 flex-shrink-0">
									<button
										type="button"
										onClick={handleEnableAll}
										className="text-[11px] text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
									>
										Enable all
									</button>
									<span className="text-[color:var(--color-border)]">|</span>
									<button
										type="button"
										onClick={handleDisableAll}
										className="text-[11px] text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
									>
										Disable all
									</button>
								</div>
							)}
						</div>
						{searchQuery && (
							<p className="text-[10px] text-[color:var(--color-text-muted)] mt-1.5 pl-1">
								Showing {filteredTools.length} of {tools.length}{" "}
								tools
							</p>
						)}
					</div>

					{/* Tool Grid */}
					<div className="flex-1 overflow-y-auto custom-scrollbar px-6 py-4">
						{filteredTools.length === 0 ? (
							<div className="flex flex-col items-center justify-center py-12 text-center">
								<Search className="w-8 h-8 text-[color:var(--color-text-muted)] mb-3 opacity-40" />
								<p className="text-sm text-[color:var(--color-text-muted)]">
									No tools match &ldquo;{searchQuery}&rdquo;
								</p>
							</div>
						) : (
							<div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
								{filteredTools.map((tool) => {
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
											className="rounded-xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/30 overflow-hidden transition-colors hover:border-[color:var(--color-border)]"
											style={{
												borderLeftWidth: "2px",
												borderLeftColor: `rgba(${providerColorRgb}, 0.5)`,
											}}
										>
											{/* Tool Header */}
											<div className="px-4 py-3">
												<div className="flex items-start justify-between gap-3">
													<div className="flex-1 min-w-0">
														<span className="text-[13px] font-mono font-semibold text-slate-900">
															{tool.name}
														</span>
														{hasParms && (
															<span
																className="text-[9px] px-1.5 py-0.5 rounded-full ml-2 inline-block align-middle"
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

													{isInteractive && (
														<div
															className="flex-shrink-0"
															onClick={(e) => e.stopPropagation()}
															onKeyDown={(e) => e.stopPropagation()}
														>
															<Toggle
																size="sm"
																checked={toolPermissions?.[tool.name] !== false}
																onChange={(checked) => handleToolToggle(tool.name, checked)}
																activeColor={providerColor}
															/>
														</div>
													)}
												</div>

												{/* Description with truncation */}
												{tool.description && (
													<div className="mt-1.5">
														<p
															className={`text-xs text-[color:var(--color-text-muted)] leading-relaxed ${
																!isDescExpanded && isLongDesc ? "line-clamp-2" : ""
															}`}
														>
															{tool.description}
														</p>
														{isLongDesc && (
															<button
																type="button"
																onClick={() => toggleDescriptionExpanded(tool.name)}
																className="text-[11px] mt-0.5 transition-colors hover:underline"
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
														className="flex items-center gap-1 mt-2 text-[11px] transition-colors hover:underline"
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
												<div className="px-4 pb-3 pt-0 border-t border-[color:var(--color-border)]/30 mx-3 mb-2">
													<div className="pt-2.5 space-y-2">
														<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-semibold">
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
																	className="rounded-lg bg-[color:var(--color-bg-secondary)]/60 px-3 py-2"
																>
																	<div className="flex items-center gap-2 flex-wrap">
																		<span className="text-[11px] font-mono font-medium text-slate-900">
																			{paramName}
																		</span>
																		{paramDef.type && (
																			<span className="text-[10px] px-1.5 py-0.5 rounded bg-[color:var(--color-border)]/20 text-[color:var(--color-text-muted)]">
																				{paramDef.type}
																			</span>
																		)}
																		{isRequired && (
																			<span className="text-[9px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
																				required
																			</span>
																		)}
																	</div>
																	{paramDef.description && (
																		<p className="text-[10px] text-[color:var(--color-text-muted)] mt-1 leading-relaxed">
																			{paramDef.description}
																		</p>
																	)}
																	{paramDef.enum && paramDef.enum.length > 0 && (
																		<div className="flex items-center gap-1 mt-1 flex-wrap">
																			<span className="text-[9px] text-[color:var(--color-text-muted)]">
																				Values:
																			</span>
																			{paramDef.enum.map((v) => (
																				<span
																					key={v}
																					className="text-[9px] px-1.5 py-0.5 rounded bg-[color:var(--color-border)]/20 text-[color:var(--color-text-secondary)] font-mono"
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
								})}
							</div>
						)}
					</div>

					{/* Footer */}
					<div className="flex-shrink-0 flex items-center justify-between px-6 py-3 border-t border-[color:var(--color-border)]/70">
						<p className="text-[10px] text-[color:var(--color-text-muted)]">
							{isInteractive
								? `${enabledCount} of ${tools.length} tool${tools.length !== 1 ? "s" : ""} enabled`
								: `${tools.length} tool${tools.length !== 1 ? "s" : ""} discovered from ${serverName}`}
						</p>
						<button
							type="button"
							onClick={onClose}
							className="px-4 py-1.5 text-xs rounded-xl bg-[color:var(--color-surface)] hover:bg-[color:var(--color-surface-hover)] text-[color:var(--color-text-secondary)] hover:text-slate-900 border border-[color:var(--color-border)]/50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
						>
							Close
						</button>
					</div>
				</div>
			</div>
		</div>,
		document.body,
	);
}
