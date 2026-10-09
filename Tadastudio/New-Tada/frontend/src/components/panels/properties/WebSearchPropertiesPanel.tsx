"use client";

import { Filter, Save, Search, Settings, ShieldCheck, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ConfigSidebar from "./ConfigSidebar";
import WebSearchAdvancedSection from "./sections/WebSearchAdvancedSection";
import WebSearchFiltersSection from "./sections/WebSearchFiltersSection";
import WebSearchSearchSection from "./sections/WebSearchSearchSection";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
import { cn } from "@/lib/utils";

interface WebSearchConfig {
	search_provider?: string;
	api_key?: string;
	max_results?: number;
	search_depth?: string;
	include_answer?: boolean;
	include_raw_content?: boolean;
	include_images?: boolean;
	timeout_seconds?: number;
	region?: string;
	safe_search?: string;
	time_range?: string;
	parent_agent_id?: string;
}

interface WebSearchNodeData {
	id: string;
	name: string;
	web_search_config?: WebSearchConfig;
}

interface WebSearchPropertiesPanelProps {
	node: {
		id: string;
		data: WebSearchNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode: (nodeId: string) => void;
	onClose: () => void;
}

type WebSearchTabId = "search" | "filters" | "advanced" | "guardrails";

export default function WebSearchPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: WebSearchPropertiesPanelProps) {
	const config = node.data.web_search_config || {};

	// Web search configuration
	const [searchProvider, setSearchProvider] = useState(
		config.search_provider || "duckduckgo",
	);
	const [apiKey, setApiKey] = useState(config.api_key || "");
	const [maxResults, setMaxResults] = useState(config.max_results || 5);
	const [searchDepth, setSearchDepth] = useState(
		config.search_depth || "basic",
	);
	const [includeAnswer, setIncludeAnswer] = useState(
		config.include_answer || false,
	);
	const [includeRawContent, setIncludeRawContent] = useState(
		config.include_raw_content || false,
	);
	const [includeImages, setIncludeImages] = useState(
		config.include_images || false,
	);
	const [timeoutSeconds, setTimeoutSeconds] = useState(
		config.timeout_seconds || 10,
	);
	const [region, setRegion] = useState(config.region || "wt-wt");
	const [safeSearch, setSafeSearch] = useState(
		config.safe_search || "moderate",
	);
	const [timeRange, setTimeRange] = useState(config.time_range || "");

	// Tab navigation
	const [activeTab, setActiveTab] = useState<WebSearchTabId>("search");

	// Track initial values for unsaved changes detection
	const initialValues = useRef({
		searchProvider: config.search_provider || "duckduckgo",
		apiKey: config.api_key || "",
		maxResults: config.max_results || 5,
		searchDepth: config.search_depth || "basic",
		includeAnswer: config.include_answer || false,
		includeRawContent: config.include_raw_content || false,
		includeImages: config.include_images || false,
		timeoutSeconds: config.timeout_seconds || 10,
		region: config.region || "wt-wt",
		safeSearch: config.safe_search || "moderate",
		timeRange: config.time_range || "",
	});

	// Unsaved changes detection
	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return (
			searchProvider !== init.searchProvider ||
			apiKey !== init.apiKey ||
			maxResults !== init.maxResults ||
			searchDepth !== init.searchDepth ||
			includeAnswer !== init.includeAnswer ||
			includeRawContent !== init.includeRawContent ||
			includeImages !== init.includeImages ||
			timeoutSeconds !== init.timeoutSeconds ||
			region !== init.region ||
			safeSearch !== init.safeSearch ||
			timeRange !== init.timeRange
		);
	}, [
		searchProvider,
		apiKey,
		maxResults,
		searchDepth,
		includeAnswer,
		includeRawContent,
		includeImages,
		timeoutSeconds,
		region,
		safeSearch,
		timeRange,
	]);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleSearchProviderChange = useCallback((value: string) => {
		setSearchProvider(value);
	}, []);

	const handleApiKeyChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setApiKey(e.target.value);
		},
		[],
	);

	const handleMaxResultsChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setMaxResults(parseInt(e.target.value));
		},
		[],
	);

	const handleIncludeImagesToggle = useCallback(() => {
		setIncludeImages(!includeImages);
	}, [includeImages]);

	const handleIncludeAnswerToggle = useCallback(() => {
		setIncludeAnswer(!includeAnswer);
	}, [includeAnswer]);

	const handleSearchDepthChange = useCallback((value: string) => {
		setSearchDepth(value);
	}, []);

	const handleRegionChange = useCallback((value: string) => {
		setRegion(value);
	}, []);

	const handleTimeRangeChange = useCallback((value: string) => {
		setTimeRange(value);
	}, []);

	const handleSafeSearchChange = useCallback((value: string) => {
		setSafeSearch(value);
	}, []);

	const handleTimeoutSecondsChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setTimeoutSeconds(parseInt(e.target.value) || 10);
		},
		[],
	);

	const handleIncludeRawContentToggle = useCallback(() => {
		setIncludeRawContent(!includeRawContent);
	}, [includeRawContent]);

	const handleSave = useCallback(() => {
		const updatedConfig: WebSearchConfig = {
			search_provider: searchProvider,
			api_key: apiKey,
			max_results: maxResults,
			search_depth: searchDepth,
			include_answer: includeAnswer,
			include_raw_content: includeRawContent,
			include_images: includeImages,
			timeout_seconds: timeoutSeconds,
			region: region,
			safe_search: safeSearch,
			time_range: timeRange,
			parent_agent_id: config.parent_agent_id,
		};

		const updateData: any = {
			web_search_config: updatedConfig,
		};

		if (node.position) {
			updateData.position = node.position;
		}

		onUpdateNode(node.id, updateData);
		onClose();
	}, [
		searchProvider,
		apiKey,
		maxResults,
		searchDepth,
		includeAnswer,
		includeRawContent,
		includeImages,
		timeoutSeconds,
		region,
		safeSearch,
		timeRange,
		config.parent_agent_id,
		node,
		onUpdateNode,
		onClose,
	]);

	// Keyboard shortcut: Cmd/Ctrl+S to save
	const handleSaveRef = useRef(handleSave);
	handleSaveRef.current = handleSave;

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSaveRef.current();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	const handleDeleteAndClose = useCallback(() => {
		onDeleteNode(node.id);
		onClose();
	}, [onDeleteNode, node.id, onClose]);

	// Responsive sidebar collapse
	const contentRef = useRef<HTMLDivElement>(null);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

	useEffect(() => {
		const el = contentRef.current;
		if (!el || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				setSidebarCollapsed(entry.contentRect.width < 400);
			}
		});
		observer.observe(el);
		return () => observer.disconnect();
	}, []);

	// Sidebar tab configuration
	const panelTabs = useMemo(
		() => [
			{
				id: "search" as const,
				label: "Search",
				description: "Provider & results",
				icon: <Search className="h-4 w-4" />,
			},
			{
				id: "filters" as const,
				label: "Filters",
				description: "Region & time",
				icon: <Filter className="h-4 w-4" />,
			},
			{
				id: "advanced" as const,
				label: "Advanced",
				description: "Timeout & content",
				icon: <Settings className="h-4 w-4" />,
			},
			{
				id: "guardrails" as const,
				label: "Guardrails",
				description: "Safety policies",
				icon: <ShieldCheck className="h-4 w-4" />,
			},
		],
		[],
	);

	const isGuardrailsTab = activeTab === "guardrails";

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleStopPropagation}
			>
				<div
					className={cn(
						"flex min-h-[320px] flex-col rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]",
						isGuardrailsTab
							? "max-h-[90vh] overflow-visible"
							: "max-h-[80vh] overflow-hidden",
					)}
				>
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex flex-wrap items-start justify-between gap-4 px-6 pb-4 pt-5">
							<div className="flex min-w-0 items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<Search className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										Web Search Configuration
									</h2>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					<div
						ref={contentRef}
						className={cn(
							"flex min-h-0 flex-1",
							!isGuardrailsTab && "overflow-hidden",
						)}
					>
						<ConfigSidebar
							items={panelTabs}
							activeItem={activeTab}
							onChange={(id) =>
								setActiveTab(id as WebSearchTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"flex-1 min-h-0 bg-slate-50 px-6 py-4",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
								{activeTab === "search" && (
									<WebSearchSearchSection
										searchProvider={searchProvider}
										onSearchProviderChange={
											handleSearchProviderChange
										}
										apiKey={apiKey}
										onApiKeyChange={handleApiKeyChange}
										maxResults={maxResults}
										onMaxResultsChange={
											handleMaxResultsChange
										}
										searchDepth={searchDepth}
										onSearchDepthChange={
											handleSearchDepthChange
										}
										includeImages={includeImages}
										onIncludeImagesToggle={
											handleIncludeImagesToggle
										}
										includeAnswer={includeAnswer}
										onIncludeAnswerToggle={
											handleIncludeAnswerToggle
										}
									/>
								)}

								{activeTab === "filters" && (
									<WebSearchFiltersSection
										searchProvider={searchProvider}
										region={region}
										onRegionChange={handleRegionChange}
										timeRange={timeRange}
										onTimeRangeChange={
											handleTimeRangeChange
										}
										safeSearch={safeSearch}
										onSafeSearchChange={
											handleSafeSearchChange
										}
									/>
								)}

								{activeTab === "advanced" && (
									<WebSearchAdvancedSection
										searchProvider={searchProvider}
										timeoutSeconds={timeoutSeconds}
										onTimeoutSecondsChange={
											handleTimeoutSecondsChange
										}
										includeRawContent={includeRawContent}
										onIncludeRawContentToggle={
											handleIncludeRawContentToggle
										}
									/>
								)}

							{activeTab === "guardrails" && (
								<ToolGuardrailsSection toolNodeId={node.id} />
							)}
						</div>
					</div>

					<div className="border-t border-gray-200 bg-white px-6 py-3">
						<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
							<button
								type="button"
								onClick={handleDeleteAndClose}
								className="flex items-center gap-1.5 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-xs text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
							>
								<Trash2 className="w-3.5 h-3.5" />
								Delete Node
							</button>

							<div className="flex items-center gap-3 sm:ml-auto">
								{hasUnsavedChanges && (
									<span className="flex items-center gap-1.5 text-[11px] text-gray-600">
										<span className="h-1.5 w-1.5 animate-smoothPulse rounded-[4px] bg-orange-500" />
										Unsaved
									</span>
								)}
								<span className="hidden text-[11px] text-gray-400 sm:inline">
									{"\u2318"}S to save
								</span>
								<button
									type="button"
									onClick={onClose}
									className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleSave}
									className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								>
									<span className="inline-flex items-center gap-1.5">
										<Save className="w-3.5 h-3.5" />
										Save Changes
									</span>
								</button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
