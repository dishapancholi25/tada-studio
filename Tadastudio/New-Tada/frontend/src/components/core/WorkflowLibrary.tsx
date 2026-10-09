"use client";

import { motion } from "framer-motion";
import {
	Bot,
	ChevronLeft,
	FileSpreadsheet,
	Filter,
	LayoutDashboard,
	LayoutGrid,
	Search,
	SortAsc,
	SortDesc,
	Upload,
	X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ConfirmDialog from "@/components/dialogs/ConfirmDialog";
import { AreaSelectionGrid } from "@/components/library/AreaSelectionGrid";
import CloneWorkflowDialog from "@/components/library/CloneWorkflowDialog";
import ImportAgentDialog from "@/components/library/ImportAgentDialog";
import ImportTemplatesCSVDialog from "@/components/library/ImportTemplatesCSVDialog";
import WorkflowCard from "@/components/library/WorkflowCard";
import Dropdown from "@/components/ui/Dropdown";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import {
	type AgentTemplate,
	COMPLEXITY_LEVELS,
	TEMPLATE_CATEGORIES,
	type TemplateCategory,
	type WorkflowTemplate,
} from "@/types/library";

type SortOption = "name" | "category" | "complexity" | "created_at";

interface WorkflowLibraryProps {
	agentInsertMode?: boolean;
}

export default function WorkflowLibrary({
	agentInsertMode = false,
}: WorkflowLibraryProps) {
	const router = useRouter();
	const { user } = useAuth();
	const { showSuccess, showInfo, showError } = useToast();
	const [searchQuery, setSearchQuery] = useState("");
	const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
	const [showFilters, setShowFilters] = useState(false);
	const [sortBy, setSortBy] = useState<SortOption>("created_at");
	const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
	const [cloningWorkflow, setCloningWorkflow] = useState<string | null>(null);
	const [showCloneDialog, setShowCloneDialog] = useState(false);
	const [selectedTemplate, setSelectedTemplate] =
		useState<WorkflowTemplate | null>(null);
	const [workflows, setWorkflows] = useState<WorkflowTemplate[]>([]);
	const [agents, setAgents] = useState<AgentTemplate[]>([]);
	const [counts, setCounts] = useState({ workflows: 0, agents: 0 });
	const [loading, setLoading] = useState(true);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
	const [templateToDelete, setTemplateToDelete] =
		useState<WorkflowTemplate | null>(null);
	const [showAgentDeleteConfirm, setShowAgentDeleteConfirm] = useState(false);
	const [agentToDelete, setAgentToDelete] = useState<AgentTemplate | null>(
		null,
	);
	const [selectedArea, setSelectedArea] = useState<
		TemplateCategory | null | undefined
	>(undefined);
	const [showImportDialog, setShowImportDialog] = useState(false);
	const [isImporting, setIsImporting] = useState(false);
	const [showCSVImportDialog, setShowCSVImportDialog] = useState(false);
	const [isCSVImporting, setIsCSVImporting] = useState(false);

	const [filters, setFilters] = useState({
		categories: new Set<string>(),
		complexities: new Set<string>(),
	});


	const searchInputRef = useRef<HTMLInputElement>(null);

	// Fetch templates + agents from API
	useEffect(() => {
		if (selectedArea === undefined) return;

		const fetchTemplates = async () => {
			try {
				setLoading(true);
				if (agentInsertMode) {
					const response = await api.listAgentTemplates({
						search: debouncedSearchQuery || undefined,
						category:
							selectedArea ||
							(filters.categories.size > 0
								? Array.from(filters.categories)[0]
								: undefined),
						complexity:
							filters.complexities.size > 0
								? Array.from(filters.complexities)[0]
								: undefined,
						sort_by: sortBy,
						sort_order: sortOrder,
					});

					if (response.success) {
						setAgents(response.agents || []);
						setWorkflows([]);
						setCounts({
							workflows: 0,
							agents: response.count ?? response.agents?.length ?? 0,
						});
					}
				} else {
					const response = await api.listLibraryItems({
						search: debouncedSearchQuery || undefined,
						category:
							selectedArea ||
							(filters.categories.size > 0
								? Array.from(filters.categories)[0]
								: undefined),
						complexity:
							filters.complexities.size > 0
								? Array.from(filters.complexities)[0]
								: undefined,
						sort_by: sortBy,
						sort_order: sortOrder,
					});

					if (response.success) {
						setWorkflows(response.workflows || []);
						setAgents(response.agents || []);
						setCounts(
							response.counts || {
								workflows: response.workflows?.length || 0,
								agents: response.agents?.length || 0,
							},
						);
					}
				}
			} catch (error) {
				console.error("Failed to fetch templates:", error);
				showError("Failed to load library items");
			} finally {
				setLoading(false);
			}
		};

		fetchTemplates();
	}, [
		selectedArea,
		debouncedSearchQuery,
		filters,
		sortBy,
		sortOrder,
		showError,
		agentInsertMode,
	]);

	// Debounce search query
	useEffect(() => {
		const timer = setTimeout(() => {
			setDebouncedSearchQuery(searchQuery);
		}, 300);

		return () => clearTimeout(timer);
	}, [searchQuery]);

	// Keyboard shortcut: Cmd/Ctrl+K to focus search
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "k") {
				e.preventDefault();
				searchInputRef.current?.focus();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	// Templates are already filtered and sorted by the API
	const displayedWorkflows = agentInsertMode ? [] : workflows;
	const displayedAgents = agents;
	const totalResults =
		(agentInsertMode ? 0 : displayedWorkflows.length) + displayedAgents.length;
	const pairedRows = useMemo(() => {
		if (agentInsertMode) return [];
		const rowCount = Math.max(
			displayedAgents.length,
			displayedWorkflows.length,
			1,
		);
		return Array.from({ length: rowCount }, (_, index) => ({
			agent: displayedAgents[index] || null,
			workflow: displayedWorkflows[index] || null,
			key: `row-${index}-${displayedAgents[index]?.id || "na"}-${displayedWorkflows[index]?.id || "nw"}`,
		}));
	}, [displayedAgents, displayedWorkflows, agentInsertMode]);
	const hasAgents = displayedAgents.length > 0;
	const hasWorkflows = displayedWorkflows.length > 0;

	const handleClearSearch = useCallback(() => {
		setSearchQuery("");
	}, []);

	const handleToggleFilters = useCallback(() => {
		setShowFilters(!showFilters);
	}, [showFilters]);

	const handleToggleSortOrder = useCallback(() => {
		setSortOrder(sortOrder === "asc" ? "desc" : "asc");
	}, [sortOrder]);

	const handleSortByChange = useCallback((value: string) => {
		setSortBy(value as SortOption);
	}, []);

	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setSearchQuery(e.target.value);
		},
		[],
	);

	const handleCategoryToggle = useCallback((category: string) => {
		setFilters((prev) => {
			const newCategories = new Set(prev.categories);
			if (newCategories.has(category)) {
				newCategories.delete(category);
			} else {
				newCategories.add(category);
			}
			return { ...prev, categories: newCategories };
		});
	}, []);

	const handleComplexityToggle = useCallback((complexity: string) => {
		setFilters((prev) => {
			const newComplexities = new Set(prev.complexities);
			if (newComplexities.has(complexity)) {
				newComplexities.delete(complexity);
			} else {
				newComplexities.add(complexity);
			}
			return { ...prev, complexities: newComplexities };
		});
	}, []);

	const handleClearFilters = useCallback(() => {
		setFilters({
			categories: new Set(),
			complexities: new Set(),
		});
	}, []);

	const handleCloneWorkflow = useCallback(
		(templateId: string) => {
			const template = workflows.find((t) => t.id === templateId);
			if (template) {
				setSelectedTemplate(template);
				setShowCloneDialog(true);
			}
		},
		[workflows],
	);

	const handleDeleteAgentTemplate = useCallback(
		(agentId: string) => {
			const agent = agents.find((a) => a.id === agentId);
			if (agent) {
				setAgentToDelete(agent);
				setShowAgentDeleteConfirm(true);
			}
		},
		[agents],
	);

	const handleConfirmClone = useCallback(
		async (targetName: string) => {
			if (!selectedTemplate) return;

			setCloningWorkflow(selectedTemplate.id);
			setShowCloneDialog(false);

			try {
				const response = await api.cloneTemplate(selectedTemplate.id, {
					target_name: targetName,
				});

				if (response.success) {
					showSuccess(
						`Successfully cloned "${selectedTemplate.name}" as "${targetName}"!`,
					);
					showInfo("The workflow has been added to your workspace.");

					// Navigate to the cloned workflow
					if (response.workflow_id) {
						setTimeout(() => {
							router.push(`/workflow/${response.workflow_id}`);
						}, 1000);
					}
				} else {
					showError("Failed to clone workflow");
				}
			} catch (error) {
				console.error("Failed to clone workflow:", error);
				showError("Failed to clone workflow");
			} finally {
				setCloningWorkflow(null);
				setSelectedTemplate(null);
			}
		},
		[selectedTemplate, router, showSuccess, showInfo, showError],
	);

	const handleDeleteTemplate = useCallback(
		(templateId: string) => {
			const template = workflows.find((t) => t.id === templateId);
			if (template) {
				setTemplateToDelete(template);
				setShowDeleteConfirm(true);
			}
		},
		[workflows],
	);

	const handleOpenTemplate = useCallback(
		(templateId: string) => {
			router.push(`/library/${templateId}`);
		},
		[router],
	);

	const handleOpenAgent = useCallback(
		(agentId: string) => {
			const path = agentInsertMode
				? `/library/agents/${agentId}?mode=agent-template`
				: `/library/agents/${agentId}`;
			router.push(path);
		},
		[router, agentInsertMode],
	);

	const handleConfirmDelete = useCallback(async () => {
		if (!templateToDelete) return;

		try {
			// Optimistically remove from UI
			const previousTemplates = workflows;
			setWorkflows(workflows.filter((t) => t.id !== templateToDelete.id));

			const response = await api.deactivateTemplate(templateToDelete.id);

			if (response.success) {
				showSuccess(
					`Template "${templateToDelete.name}" has been removed from the library`,
				);
			} else {
				// Rollback on failure
				setWorkflows(previousTemplates);
				showError("Failed to delete template");
			}
		} catch (error) {
			console.error("Failed to delete template:", error);
			// Rollback on error
			setWorkflows(workflows);
			showError("Failed to delete template");
		} finally {
			setTemplateToDelete(null);
			setShowDeleteConfirm(false);
		}
	}, [templateToDelete, workflows, showSuccess, showError]);

	const handleConfirmDeleteAgent = useCallback(async () => {
		if (!agentToDelete) return;

		const previousAgents = agents;
		try {
			setAgents((prev) =>
				prev.filter((agent) => agent.id !== agentToDelete.id),
			);

			const response = await api.deleteAgentTemplate(agentToDelete.id);

			if (response.success) {
				showSuccess(
					`Agent "${agentToDelete.name}" has been removed from the library`,
				);
			} else {
				setAgents(previousAgents);
				showError("Failed to delete agent template");
			}
		} catch (error) {
			console.error("Failed to delete agent template:", error);
			setAgents(previousAgents);
			showError("Failed to delete agent template");
		} finally {
			setAgentToDelete(null);
			setShowAgentDeleteConfirm(false);
		}
	}, [agentToDelete, agents, showSuccess, showError]);

	const handleImportAgent = useCallback(
		async (data: {
			agent_json: Record<string, any>;
			metadata_override?: {
				category?: string[];
				tags?: string[];
				complexity?: string;
				icon_color?: string;
			};
		}) => {
			try {
				setIsImporting(true);
				const response = await api.importAgentFromJSON(data);

				if (response.success) {
					showSuccess(`Agent "${data.agent_json.name}" imported successfully`);
					setShowImportDialog(false);

					// Refresh the agent list
					const refreshResponse = await api.listAgentTemplates({
						search: debouncedSearchQuery || undefined,
						category:
							selectedArea ||
							(filters.categories.size > 0
								? Array.from(filters.categories)[0]
								: undefined),
						complexity:
							filters.complexities.size > 0
								? Array.from(filters.complexities)[0]
								: undefined,
						sort_by: sortBy,
						sort_order: sortOrder,
					});

					if (refreshResponse.success) {
						setAgents(refreshResponse.agents || []);
					}
				} else {
					showError("Failed to import agent");
				}
			} catch (error: any) {
				console.error("Failed to import agent:", error);
				const errorMessage = error?.message || "Failed to import agent";
				showError(errorMessage);
			} finally {
				setIsImporting(false);
			}
		},
		[
			showSuccess,
			showError,
			debouncedSearchQuery,
			selectedArea,
			filters,
			sortBy,
			sortOrder,
		],
	);

	const handleImportCSV = useCallback(
		async (files: {
			workflows_csv: File;
			graph_definitions_csv: File;
			workflow_templates_csv: File;
		}) => {
			try {
				setIsCSVImporting(true);
				const response = await api.importTemplatesFromCSV(files);

				if (response.success) {
					showSuccess(
						`Import complete: ${response.inserted} template(s) imported, ${response.skipped_duplicates} skipped`,
					);
					setShowCSVImportDialog(false);

					// Refresh the template list
					const refreshResponse = await api.listLibraryItems({
						search: debouncedSearchQuery || undefined,
						category:
							selectedArea ||
							(filters.categories.size > 0
								? Array.from(filters.categories)[0]
								: undefined),
						complexity:
							filters.complexities.size > 0
								? Array.from(filters.complexities)[0]
								: undefined,
						sort_by: sortBy,
						sort_order: sortOrder,
					});

					if (refreshResponse.success) {
						setWorkflows(refreshResponse.workflows || []);
						setAgents(refreshResponse.agents || []);
						setCounts({
							workflows: refreshResponse.counts?.workflows ?? 0,
							agents: refreshResponse.counts?.agents ?? 0,
						});
					}
				} else {
					showError("Failed to import templates");
				}
			} catch (error: any) {
				console.error("Failed to import templates from CSV:", error);
				const errorMessage =
					error?.message || "Failed to import templates from CSV";
				showError(errorMessage);
			} finally {
				setIsCSVImporting(false);
			}
		},
		[
			showSuccess,
			showError,
			debouncedSearchQuery,
			selectedArea,
			filters,
			sortBy,
			sortOrder,
		],
	);

	const handleSelectArea = useCallback((area: TemplateCategory | null) => {
		setSelectedArea(area);
	}, []);

	const handleBackToAreas = useCallback(() => {
		setSelectedArea(undefined);
		setSearchQuery("");
		setFilters({
			categories: new Set(),
			complexities: new Set(),
		});
	}, []);

	const activeFilterCount = filters.categories.size + filters.complexities.size;

	const pageTitle =
		selectedArea !== undefined
			? selectedArea || "All Templates"
			: agentInsertMode
				? "Agent Template Library"
				: "Workflow Library";

	const subtitle =
		selectedArea !== undefined
			? agentInsertMode
				? "Choose an agent template to add to your workflow"
				: "Browse and clone workflow templates"
			: agentInsertMode
				? "Select a sector to browse agent templates you can insert directly into your workflow"
				: "Browse and clone pre-built workflow templates to accelerate your AI automation journey";

	const searchPlaceholder = agentInsertMode
		? "Search agent templates by name, description, or tags... (⌘K)"
		: "Search workflows by name, description, or tags... (⌘K)";

	return (
		<div className="h-full overflow-auto bg-white px-4 sm:px-6 lg:px-8 py-4 sm:py-6 pb-16 text-[color:var(--color-text-primary)]">
			<div className="max-w-screen-2xl mx-auto">
				{/* Header */}
				<motion.div
					initial={{ opacity: 0, y: -20 }}
					animate={{ opacity: 1, y: 0 }}
					className="mb-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_22px_56px_rgba(15,23,42,0.08)]"
				>
					<div className="flex items-start justify-between gap-4 mb-4">
						<div>
							{/* Back button when inside a category */}
							{selectedArea !== undefined && (
								<button
									onClick={handleBackToAreas}
									className="mb-2 flex items-center gap-1 rounded-lg text-[color:var(--color-text-muted)] transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
								>
									<ChevronLeft className="w-4 h-4" />
									<span className="text-sm">Back to Categories</span>
								</button>
							)}

							{/* Title row */}
							<div className="flex items-center gap-2">
								<div className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-orange-600">
									<LayoutDashboard className="w-5 h-5" />
								</div>
								<h1 className="text-lg font-bold text-[color:var(--color-text-primary)]">{pageTitle}</h1>
							</div>

							{/* Description */}
							<p className="mt-1 text-sm text-[color:var(--color-text-muted)]">{subtitle}</p>
							{selectedArea === undefined && !agentInsertMode && (
								<p className="text-sm text-[color:var(--color-text-muted)]">
									Select a category to explore relevant workflow templates.
								</p>
							)}
						</div>

						{/* Count pill when inside a category */}
						{selectedArea !== undefined &&
							!loading &&
							(counts.agents > 0 || counts.workflows > 0) && (
								<div className="flex items-center gap-3 rounded-full border border-slate-200 bg-white px-4 py-2 shadow-sm">
									{counts.agents > 0 && (
										<div className="flex items-center gap-1.5">
											<Bot className="h-4 w-4 text-orange-600" />
											<span className="text-sm font-semibold text-[color:var(--color-text-primary)]">{counts.agents}</span>
										</div>
									)}
									{counts.workflows > 0 && (
										<div className="flex items-center gap-1.5">
											<LayoutGrid className="h-4 w-4 text-orange-600" />
											<span className="text-sm font-semibold text-[color:var(--color-text-primary)]">{counts.workflows}</span>
										</div>
									)}
								</div>
							)}
					</div>
				</motion.div>

				{/* Agent insert helper */}
				{agentInsertMode && selectedArea === undefined && (
					<motion.div
						initial={{ opacity: 0, y: 10 }}
						animate={{ opacity: 1, y: 0 }}
						className="mb-6 rounded-2xl border border-slate-200 bg-white px-5 py-4 text-sm text-[color:var(--color-text-secondary)] shadow-[0_20px_55px_rgba(15,23,42,0.08)]"
					>
						Select a sector to filter agent templates. When you click "Add to
						Workflow" the agent will be inserted into your active builder
						session.
					</motion.div>
				)}

				{/* Show Area Selection or Template List */}
				{selectedArea === undefined ? (
					/* Area Selection Grid */
					<motion.div
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
					>
						<AreaSelectionGrid onSelectArea={handleSelectArea} />
					</motion.div>
				) : (
					<>
						{/* Search and Filter Controls */}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							className="mb-6"
						>
							<div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-[0_20px_55px_rgba(15,23,42,0.08)]">
								{/* Search Bar */}
								<div className="flex flex-col sm:flex-row sm:flex-wrap gap-3 mb-4">
									<div className="flex-1 relative min-w-full sm:min-w-[220px]">
										<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
										<input
											data-tutorial="library-search"
											ref={searchInputRef}
											type="text"
											placeholder={searchPlaceholder}
											aria-label="Search workflows"
											value={searchQuery}
											onChange={handleSearchChange}
											className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] hover:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-500/20 focus:border-orange-500 transition-all"
										/>
										{searchQuery && (
											<button
												onClick={handleClearSearch}
												className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-900 transition-colors"
												aria-label="Clear search"
											>
												<X className="w-4 h-4" />
											</button>
										)}
									</div>

									{/* Import Agent Button */}
									<button
										data-tutorial="import-agent-btn"
										onClick={() => setShowImportDialog(true)}
										className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-[color:var(--color-text-secondary)] hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
										aria-label="Import agent from JSON"
										title="Import an agent from JSON configuration"
									>
										<Upload className="w-4 h-4" />
										<span className="hidden sm:inline">Import Agent</span>
									</button>

									{/* Import Templates CSV Button */}
									<button
										onClick={() => setShowCSVImportDialog(true)}
										className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-[color:var(--color-text-secondary)] hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
										aria-label="Import templates from CSV"
										title="Import workflow templates from CSV exports"
									>
										<FileSpreadsheet className="w-4 h-4" />
										<span className="hidden sm:inline">Import Templates</span>
									</button>

									{/* Filter Toggle */}
									<button
										data-tutorial="library-filters"
										onClick={handleToggleFilters}
										className={`shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all relative focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] ${
											showFilters
												? "bg-orange-500 border border-orange-500 text-white hover:bg-orange-600"
												: "border border-slate-200 bg-white text-[color:var(--color-text-secondary)] hover:border-orange-400 hover:bg-white hover:text-slate-900"
										}`}
										aria-label="Toggle filters"
										aria-expanded={showFilters}
									>
										<Filter className="w-4 h-4" />
										<span>Filters</span>
										{activeFilterCount > 0 && (
											<span className="absolute -top-2 -right-2 w-5 h-5 bg-[color:var(--color-accent)] text-white text-xs font-bold rounded-full flex items-center justify-center">
												{activeFilterCount}
											</span>
										)}
									</button>

									{/* Sort Controls */}
									<div className="flex items-center gap-2 shrink-0">
										<div className="flex-1 sm:flex-none">
											<Dropdown
												value={sortBy}
												onChange={handleSortByChange}
												options={[
													{ value: "created_at", label: "Sort by Date Added" },
													{ value: "name", label: "Sort by Name" },
													{ value: "category", label: "Sort by Category" },
													{ value: "complexity", label: "Sort by Complexity" },
												]}
												menuAppearance="light"
												width="trigger"
												className="w-full sm:w-[190px]"
												triggerClassName="!rounded-xl !py-2.5"
											/>
										</div>
										<button
											onClick={handleToggleSortOrder}
											className="shrink-0 p-2.5 rounded-xl border border-slate-200 bg-white text-[color:var(--color-text-secondary)] hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
											title={
												sortOrder === "asc"
													? "Sort ascending"
													: "Sort descending"
											}
											aria-label={
												sortOrder === "asc"
													? "Sort ascending"
													: "Sort descending"
											}
										>
											{sortOrder === "asc" ? (
												<SortAsc className="w-4 h-4" />
											) : (
												<SortDesc className="w-4 h-4" />
											)}
										</button>
									</div>
								</div>

								{/* Filter Options */}
								{showFilters && (
									<motion.div
										initial={{ opacity: 0, height: 0 }}
										animate={{ opacity: 1, height: "auto" }}
										exit={{ opacity: 0, height: 0 }}
										className="border-t border-slate-200 pt-4 mt-4"
									>
										<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
											{/* Category Filter */}
											<div>
												<label className="block text-xs capitalize text-[color:var(--color-text-secondary)] font-semibold mb-3">
													Categories
												</label>
												<div className="space-y-2">
													{TEMPLATE_CATEGORIES.map((category) => (
														<label
															key={category}
															className="flex items-center cursor-pointer group"
														>
															<input
																type="checkbox"
																checked={filters.categories.has(category)}
																onChange={() => handleCategoryToggle(category)}
																className="mr-2 w-4 h-4 text-orange-600 bg-white border-slate-200 rounded focus:ring-2 focus:ring-orange-500/25 cursor-pointer"
															/>
															<span className="text-sm text-[color:var(--color-text-secondary)] group-hover:text-slate-900 transition-colors">
																{category}
															</span>
														</label>
													))}
												</div>
											</div>

											{/* Complexity Filter */}
											<div>
												<label className="block text-xs capitalize text-[color:var(--color-text-secondary)] font-semibold mb-3">
													Complexity
												</label>
												<div className="space-y-2">
													{COMPLEXITY_LEVELS.map((complexity) => (
														<label
															key={complexity}
															className="flex items-center cursor-pointer group"
														>
															<input
																type="checkbox"
																checked={filters.complexities.has(complexity)}
																onChange={() =>
																	handleComplexityToggle(complexity)
																}
																className="mr-2 w-4 h-4 text-orange-600 bg-white border-slate-200 rounded focus:ring-2 focus:ring-orange-500/25 cursor-pointer"
															/>
															<span className="text-sm text-[color:var(--color-text-secondary)] group-hover:text-slate-900 transition-colors">
																{complexity.charAt(0).toUpperCase() +
																	complexity.slice(1)}
															</span>
														</label>
													))}
												</div>
											</div>

											{/* Results Count & Clear */}
											<div className="flex flex-col justify-between">
												<div>
													<label className="block text-xs capitalize text-[color:var(--color-text-secondary)] font-semibold mb-3">
														Results
													</label>
													<div className="text-2xl font-semibold text-[color:var(--color-text-primary)]">
														{totalResults}
													</div>
													<div className="text-xs text-[color:var(--color-text-muted)] mt-1">
														{loading ? "Loading..." : "library items found"}
													</div>
												</div>
												{activeFilterCount > 0 && (
													<button
														onClick={handleClearFilters}
														className="mt-4 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm text-[color:var(--color-text-secondary)] hover:border-orange-400 hover:bg-white hover:text-slate-900 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
													>
														Clear Filters
													</button>
												)}
											</div>
										</div>
									</motion.div>
								)}
							</div>
						</motion.div>

						{/* Workflow & Agent Grid */}
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ delay: 0.1 }}
						>
							{loading ? (
								<div className="col-span-full text-center py-16 rounded-2xl bg-white">
									<div className="w-10 h-10 mx-auto mb-4 border-2 border-transparent border-t-orange-500 rounded-full animate-spin" />
									<p className="text-sm text-slate-600">
										Loading library items...
									</p>
								</div>
							) : totalResults === 0 ? (
								<div className="col-span-full py-10 rounded-2xl border border-slate-200 bg-white shadow-[0_20px_55px_rgba(15,23,42,0.08)]">
									{agentInsertMode ? (
										<EmptyColumnState kind="agent" />
									) : (
										<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
											<EmptyColumnState kind="agent" />
											<EmptyColumnState kind="workflow" />
										</div>
									)}
								</div>
							) : agentInsertMode ? (
								<div className="space-y-6">
									<ColumnHeader
										title="Agent Templates"
										description="Select an agent to insert directly into your open workflow."
									/>
									<div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
										{displayedAgents.map((agent) => (
											<WorkflowCard
												key={agent.id}
												workflow={agent}
												onDelete={handleDeleteAgentTemplate}
												onSelect={() => handleOpenAgent(agent.id)}
												currentUserEmail={user?.email}
												hideCloneAction
											/>
										))}
									</div>
								</div>
							) : (
								<div className="space-y-6">
									<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
										<ColumnHeader
											title="Agents"
											description="Standalone agents with reusable prompts, tools, and subagents."
										/>
										<ColumnHeader
											title="Workflows"
											description="Complete workflow templates ready to clone into your workspace."
										/>
									</div>

									<div className="space-y-6">
										{pairedRows.map(({ agent, workflow, key }, index) => (
											<div
												key={key}
												className="grid grid-cols-1 gap-6 lg:grid-cols-2"
											>
												<div className="h-full">
													{agent ? (
														<WorkflowCard
															workflow={agent}
															onDelete={handleDeleteAgentTemplate}
															onSelect={() => handleOpenAgent(agent.id)}
															currentUserEmail={user?.email}
															hideCloneAction
														/>
													) : hasAgents || index > 0 ? (
														<GhostPanel />
													) : (
														<EmptyColumnState kind="agent" compact />
													)}
												</div>
												<div className="h-full">
													{workflow ? (
														<WorkflowCard
															workflow={workflow}
															onClone={handleCloneWorkflow}
															onDelete={handleDeleteTemplate}
															onSelect={handleOpenTemplate}
															currentUserEmail={user?.email}
															isCloning={cloningWorkflow === workflow.id}
															dataTutorial={index === 0 ? "library-card" : undefined}
															dataTutorialClone={index === 0 ? "library-clone-btn" : undefined}
														/>
													) : hasWorkflows || index > 0 ? (
														<GhostPanel />
													) : (
														<EmptyColumnState kind="workflow" compact />
													)}
												</div>
											</div>
										))}
									</div>
								</div>
							)}
						</motion.div>
					</>
				)}
			</div>

			{/* Clone Workflow Dialog */}
			<CloneWorkflowDialog
				isOpen={showCloneDialog}
				templateName={selectedTemplate?.name || null}
				templateId={selectedTemplate?.id || null}
				onConfirm={handleConfirmClone}
				onCancel={() => {
					setShowCloneDialog(false);
					setSelectedTemplate(null);
				}}
			/>

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				title="Delete Template"
				message={`Are you sure you want to delete "${templateToDelete?.name}"? This will remove it from the library and cannot be undone.`}
				confirmText="Delete"
				cancelText="Cancel"
				type="danger"
				onConfirm={handleConfirmDelete}
				onCancel={() => {
					setShowDeleteConfirm(false);
					setTemplateToDelete(null);
				}}
			/>

			<ConfirmDialog
				isOpen={showAgentDeleteConfirm}
				title="Delete Agent Template"
				message={`Are you sure you want to delete "${agentToDelete?.name}"? This will remove the agent from the library and cannot be undone.`}
				confirmText="Delete"
				cancelText="Cancel"
				type="danger"
				onConfirm={handleConfirmDeleteAgent}
				onCancel={() => {
					setShowAgentDeleteConfirm(false);
					setAgentToDelete(null);
				}}
			/>

			{/* Import Agent Dialog */}
			<ImportAgentDialog
				isOpen={showImportDialog}
				isSubmitting={isImporting}
				onConfirm={handleImportAgent}
				onCancel={() => setShowImportDialog(false)}
			/>

			{/* Import Templates CSV Dialog */}
			<ImportTemplatesCSVDialog
				isOpen={showCSVImportDialog}
				isSubmitting={isCSVImporting}
				onConfirm={handleImportCSV}
				onCancel={() => setShowCSVImportDialog(false)}
			/>
		</div>
	);
}

function ColumnHeader({
	title,
	description,
}: {
	title: string;
	description: string;
}) {
	return (
		<div className="rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_76%,#f59e0b_190%)] px-5 py-4 shadow-[0_20px_55px_rgba(15,23,42,0.08)]">
			<h3 className="text-base font-semibold text-[color:var(--color-text-primary)]">{title}</h3>
			<p className="mt-1 text-xs text-[color:var(--color-text-muted)]">
				{description}
			</p>
		</div>
	);
}

function EmptyColumnState({
	kind,
	compact = false,
}: {
	kind: "agent" | "workflow";
	compact?: boolean;
}) {
	const Icon = kind === "agent" ? Bot : LayoutDashboard;
	const title =
		kind === "agent"
			? "No agents match your filters yet."
			: "No workflows match your filters yet.";
	const subtext =
		kind === "agent"
			? "Adjust your search to explore other agent presets."
			: "Try a different search or remove filters to view workflows.";

	return (
		<div
			className={`flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white px-6 text-center transition-colors hover:border-orange-400 ${
				compact ? "py-8 min-h-[260px]" : "py-12 min-h-[320px]"
			}`}
		>
			<div className="p-3 rounded-xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_58%,#f59e0b_170%)] mb-3">
				<Icon className="w-6 h-6 text-orange-600" />
			</div>
			<h3 className="text-base font-semibold text-[color:var(--color-text-primary)] mb-1">
				{kind === "agent" ? "Agents" : "Workflows"}
			</h3>
			<p className="text-sm text-[color:var(--color-text-secondary)] mb-1">
				{title}
			</p>
			{!compact && (
				<p className="text-xs text-[color:var(--color-text-muted)]">
					{subtext}
				</p>
			)}
		</div>
	);
}

function GhostPanel() {
	return (
		<div className="min-h-[40px] rounded-2xl border border-dashed border-slate-200 bg-white transition-colors hover:border-orange-400" />
	);
}
