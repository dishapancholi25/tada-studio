"use client";

import {
	AlertCircle,
	CalendarClock,
	Check,
	ChevronDown,
	ChevronRight,
	Clock,
	Code,
	Copy,
	Eye,
	EyeOff,
	Filter,
	Globe,
	Key,
	Lock,
	Pause,
	Play,
	Search,
	Settings,
	SortAsc,
	SortDesc,
	Trash2,
	TrendingUp,
	Users,
	X,
	AlertTriangle,
	CheckCircle,
	Rocket,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { WorkflowSchedule } from "@/types/api";
import { runtimeConfig } from "@/lib/runtime-config";
import { getLatestRun } from "@/lib/evaluation-api";
import type { EvaluationRun } from "@/lib/evaluation-api";
import ConfirmDialog from "@/components/dialogs/ConfirmDialog";
import Dropdown from "@/components/ui/Dropdown";

const getWindowOrigin = () =>
	typeof window !== "undefined" ? window.location.origin : "";

interface PublishedWorkflow {
	workflow_id: string;
	graph_name: string;
	is_published: boolean;
	endpoint_url: string;
	custom_slug?: string;
	description: string;
	require_authentication: boolean;
	published_at?: string;
	last_accessed?: string;
	access_count: number;
	workflow_updated_at?: string;
	rate_limit?: { [key: string]: number };
	allowed_origins: string[];
	webhook_url?: string;
}

interface WorkflowInfo {
	name: string;
	description: string;
	workflow_id: string;
}

export default function WorkflowPublisher() {
	const [publishedWorkflows, setPublishedWorkflows] = useState<
		PublishedWorkflow[]
	>([]);
	const [availableWorkflows, setAvailableWorkflows] = useState<WorkflowInfo[]>(
		[],
	);
	const [loading, setLoading] = useState(true);
	const [publishingWorkflow, setPublishingWorkflow] = useState<string | null>(
		null,
	);
	const [unpublishingWorkflow, setUnpublishingWorkflow] = useState<
		string | null
	>(null);
	const [error, setError] = useState<string | null>(null);
	const [copiedItem, setCopiedItem] = useState<string | null>(null);
	const [expandedWorkflows, setExpandedWorkflows] = useState<{
		[key: string]: boolean;
	}>({});
	const [showPatBanner, setShowPatBanner] = useState(true);
	const [unpublishConfirm, setUnpublishConfirm] = useState<{
		isOpen: boolean;
		workflowName: string | null;
	}>({ isOpen: false, workflowName: null });

	// Schedule state
	const [schedules, setSchedules] = useState<{ [workflowId: string]: WorkflowSchedule }>({});
	const [editingSchedule, setEditingSchedule] = useState<string | null>(null);
	const [scheduleForm, setScheduleForm] = useState<{
		cronExpression: string;
		timezone: string;
		input: string;
		isCustom: boolean;
	}>({
		cronExpression: "0 9 * * *",
		timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
		input: "",
		isCustom: false,
	});
	const [scheduleLoading, setScheduleLoading] = useState<string | null>(null);

	// Workflow trigger token state (lazy-loaded per expanded workflow)
	const [workflowTokens, setWorkflowTokens] = useState<Record<string, string>>({});
	const [visibleTokens, setVisibleTokens] = useState<Record<string, boolean>>({});

	// Evaluation regression state (per workflow)
	const [latestEvalRuns, setLatestEvalRuns] = useState<Record<string, EvaluationRun | null>>({});
	const [regressionAcknowledged, setRegressionAcknowledged] = useState<Record<string, boolean>>({});

	// Tutorial integration: track the demo workflow name so we can tag its elements
	const [tutorialWorkflowName, setTutorialWorkflowName] = useState<string | null>(null);

	const [endpointBaseUrl, setEndpointBaseUrl] = useState<string>(() => {
		const origin = getWindowOrigin();
		return origin ? origin.replace(/\/+$/, "") : "";
	});

	useEffect(() => {
		let cancelled = false;

		const resolveBaseUrl = async () => {
			try {
				const config = await runtimeConfig.getConfig();
				const baseCandidate =
					config.deployment === "separate-domains" && config.apiUrl
						? config.apiUrl
						: getWindowOrigin();

				if (!baseCandidate) {
					return;
				}

				if (!cancelled) {
					setEndpointBaseUrl(baseCandidate.replace(/\/+$/, ""));
				}
			} catch (error) {
				console.warn(
					"Failed to load runtime config for workflow publisher:",
					error,
				);
				const originFallback = getWindowOrigin();
				if (!cancelled && originFallback) {
					setEndpointBaseUrl(originFallback.replace(/\/+$/, ""));
				}
			}
		};

		resolveBaseUrl();
		return () => {
			cancelled = true;
		};
	}, []);

	// Search and filtering state
	const [searchQuery, setSearchQuery] = useState("");
	const [showFilters, setShowFilters] = useState(false);
	const [filters, setFilters] = useState({
		showPublished: true,
		showUnpublished: true,
		requiresAuth: "all", // 'all', 'required', 'not-required'
	});
	const [sortBy, setSortBy] = useState<
		"name" | "accessCount" | "lastAccessed" | "publishedAt"
	>("publishedAt");
	const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
	const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");

	// Refs for navigation, search, and stable access to schedules
	const schedulesRef = useRef(schedules);
	schedulesRef.current = schedules;
	const publishedSectionRef = useRef<HTMLDivElement>(null);
	const searchInputRef = useRef<HTMLInputElement>(null);

	// Check localStorage for PAT banner dismissal on mount
	useEffect(() => {
		const dismissed = localStorage.getItem("patBannerDismissed");
		if (dismissed === "true") {
			setShowPatBanner(false);
		}
	}, []);

	// Load data on component mount
	useEffect(() => {
		loadData().catch((error) => {
			console.error("Failed to load workflow publisher data:", error);
		});
	}, []);

	// Refresh when a workflow is created/deleted elsewhere
	useEffect(() => {
		const refresh = () => loadData().catch(() => {});
		window.addEventListener("workflowListChanged", refresh);
		return () => window.removeEventListener("workflowListChanged", refresh);
	}, []);

	// Debounce search query for better performance
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

	// Tutorial: listen for the demo workflow name dispatched by TutorialContext.
	// Also check the stashed value on window in case the event fired before mount.
	useEffect(() => {
		const stashed = (window as any).__tutorialPublishWorkflowName as string | undefined;
		if (stashed) {
			setTutorialWorkflowName(stashed);
			loadData().catch(() => {});
		}

		const handleName = (e: Event) => {
			const detail = (e as CustomEvent).detail;
			if (detail?.name) {
				setTutorialWorkflowName(detail.name);
				// Reload data so the new workflow appears in the list
				loadData().catch(() => {});
			}
		};
		window.addEventListener("tutorialPublishWorkflowName", handleName);
		return () => {
			window.removeEventListener("tutorialPublishWorkflowName", handleName);
			delete (window as any).__tutorialPublishWorkflowName;
		};
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const loadData = async () => {
		try {
			setLoading(true);

			// Load published workflows
			const publishedResponse = await api.getPublishedWorkflows();
			setPublishedWorkflows(publishedResponse.published_workflows || []);

			// Load all available workflows
			const workflowsResponse = await api.listGraphs();
			setAvailableWorkflows(workflowsResponse.graphs || []);
		} catch (error) {
			console.error("Error loading workflow data:", error);
		} finally {
			setLoading(false);
		}
	};

	const appendBaseToPath = useCallback(
		(path: string) => {
			if (!path) {
				return endpointBaseUrl;
			}

			// Preserve fully qualified URLs when no override is needed
			if (path.startsWith("http://") || path.startsWith("https://")) {
				return path;
			}

			const normalizedPath = path.startsWith("/") ? path : `/${path}`;
			if (!endpointBaseUrl) {
				return normalizedPath;
			}

			return `${endpointBaseUrl}${normalizedPath}`;
		},
		[endpointBaseUrl],
	);

	const resolveEndpointUrl = useCallback(
		(workflow: PublishedWorkflow) => {
			const rawUrl = workflow.endpoint_url;
			const defaultPath = `/api/http-execution/trigger/${workflow.graph_name}`;

			if (!rawUrl) {
				return appendBaseToPath(defaultPath);
			}

			if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) {
				try {
					const parsed = new URL(rawUrl);
					const pathWithQueryAndHash = `${parsed.pathname}${parsed.search}${parsed.hash || ""}`;
					return appendBaseToPath(pathWithQueryAndHash || defaultPath);
				} catch {
					return rawUrl;
				}
			}

			return appendBaseToPath(rawUrl || defaultPath);
		},
		[appendBaseToPath],
	);

	const publishWorkflow = async (workflowName: string) => {
		try {
			setPublishingWorkflow(workflowName);
			setError(null);

			// Optimistic update: immediately move workflow from available to published
			const workflowToPublish = availableWorkflows.find(
				(w) => w.name === workflowName,
			);
			if (workflowToPublish) {
				const triggerPath = `/api/http-execution/trigger/${workflowName}`;
				const optimisticEndpointUrl = appendBaseToPath(triggerPath);

				const optimisticPublishedWorkflow: PublishedWorkflow = {
					workflow_id: workflowToPublish.workflow_id,
					graph_name: workflowName,
					is_published: true,
					endpoint_url: optimisticEndpointUrl,
					custom_slug: undefined,
					description: `Published API endpoint for ${workflowName}`,
					require_authentication: true,
					published_at: new Date().toISOString(),
					last_accessed: undefined,
					access_count: 0,
					workflow_updated_at: undefined,
					rate_limit: { requests_per_minute: 60 },
					allowed_origins: [],
					webhook_url: undefined,
				};

				// Update state optimistically
				setPublishedWorkflows((prev) => [...prev, optimisticPublishedWorkflow]);
				setAvailableWorkflows((prev) =>
					prev.filter((w) => w.name !== workflowName),
				);

				// Auto-scroll to published section immediately
				setTimeout(() => {
					publishedSectionRef.current?.scrollIntoView({
						behavior: "smooth",
						block: "start",
					});
				}, 100);
			}

			// Make the API call
			const response = await api.publishWorkflow(workflowName, {
				description: `Published API endpoint for ${workflowName}`,
				require_authentication: true,
				rate_limit: { requests_per_minute: 60 },
			});

			if (response.success) {
				// Load fresh data to get accurate info (but UI is already updated)
				const publishedResponse = await api.getPublishedWorkflows();

				// Update with accurate server data
				setPublishedWorkflows(publishedResponse.published_workflows || []);
			} else {
				// Revert optimistic update on failure
				const workflowToRevert = publishedWorkflows.find(
					(w) => w.graph_name === workflowName,
				);
				if (workflowToRevert && workflowToPublish) {
					setPublishedWorkflows((prev) =>
						prev.filter((w) => w.graph_name !== workflowName),
					);
					setAvailableWorkflows((prev) => [...prev, workflowToPublish]);
				}
				setError(
					`Failed to publish ${workflowName}: ${response.message || "Unknown error"}`,
				);
			}
		} catch (error: any) {
			console.error("Error publishing workflow:", error);

			// Revert optimistic update on error
			const workflowToRevert = availableWorkflows.find(
				(w) => w.name === workflowName,
			);
			if (!workflowToRevert) {
				// Workflow was moved optimistically, need to move it back
				const publishedWorkflow = publishedWorkflows.find(
					(w) => w.graph_name === workflowName,
				);
				if (publishedWorkflow) {
					setPublishedWorkflows((prev) =>
						prev.filter((w) => w.graph_name !== workflowName),
					);
					setAvailableWorkflows((prev) => [
						...prev,
						{
							name: workflowName,
							description: publishedWorkflow.description,
							workflow_id: publishedWorkflow.workflow_id,
						},
					]);
				}
			}

			setError(
				`Failed to publish ${workflowName}: ${error.message || "Network error"}`,
			);
		} finally {
			setPublishingWorkflow(null);
		}
	};

	const unpublishWorkflow = async (workflowName: string) => {
		setUnpublishConfirm({ isOpen: true, workflowName });
	};

	const executeUnpublish = async (workflowName: string) => {
		// Store the workflow we're about to unpublish for potential rollback
		const workflowToUnpublish = publishedWorkflows.find(
			(w) => w.graph_name === workflowName,
		);

		try {
			setUnpublishingWorkflow(workflowName);
			setError(null);

			// Optimistic update: immediately move workflow from published to available
			if (workflowToUnpublish) {
				const availableWorkflow: WorkflowInfo = {
					name: workflowName,
					description:
						workflowToUnpublish.description || `Workflow ${workflowName}`,
					workflow_id: workflowToUnpublish.workflow_id,
				};

				// Update state optimistically
				setPublishedWorkflows((prev) =>
					prev.filter((w) => w.graph_name !== workflowName),
				);
				setAvailableWorkflows((prev) => [...prev, availableWorkflow]);

				// Close expanded state if it was open
				setExpandedWorkflows((prev) => {
					const newExpanded = { ...prev };
					delete newExpanded[workflowName];
					return newExpanded;
				});
			}

			// Make the API call
			await api.unpublishWorkflow(workflowName);

			// Success - the optimistic update was correct, no need to reload everything
			// Just refresh the available workflows to get the correct list
			const workflowsResponse = await api.listGraphs();
			setAvailableWorkflows(workflowsResponse.graphs || []);
		} catch (error: any) {
			console.error("Error unpublishing workflow:", error);

			// Revert optimistic update on error
			const workflowToRevert = availableWorkflows.find(
				(w) => w.name === workflowName,
			);
			if (workflowToRevert && workflowToUnpublish) {
				setAvailableWorkflows((prev) =>
					prev.filter((w) => w.name !== workflowName),
				);
				setPublishedWorkflows((prev) => [...prev, workflowToUnpublish]);
			}

			setError(
				`Failed to unpublish ${workflowName}: ${error.message || "Network error"}`,
			);
		} finally {
			setUnpublishingWorkflow(null);
		}
	};

	const copyToClipboard = async (text: string, type: string) => {
		try {
			await navigator.clipboard.writeText(text);
			setCopiedItem(type);
			setTimeout(() => setCopiedItem(null), 2000);
		} catch (error) {
			console.error("Failed to copy to clipboard:", error);
		}
	};

	const formatDate = (dateString?: string) => {
		if (!dateString) return "Never";
		return (
			new Date(dateString).toLocaleDateString() +
			" " +
			new Date(dateString).toLocaleTimeString()
		);
	};

	// Cron presets
	const CRON_PRESETS = [
		{ label: "Every 30 minutes", value: "*/30 * * * *" },
		{ label: "Every hour", value: "0 * * * *" },
		{ label: "Every 6 hours", value: "0 */6 * * *" },
	];

	const getCronLabel = (expression: string | null): string => {
		if (!expression) return "No schedule";
		const preset = CRON_PRESETS.find((p) => p.value === expression);
		return preset ? preset.label : expression;
	};

	const loadSchedule = async (workflowId: string) => {
		try {
			const schedule = await api.getWorkflowSchedule(workflowId);
			setSchedules((prev) => ({ ...prev, [workflowId]: schedule }));
		} catch {
			// No schedule set yet — that's fine
		}
	};

	const handleSaveSchedule = async (workflowId: string) => {
		const inputValue = String(scheduleForm.input ?? "").trim();
		if (!inputValue) {
			setError("Input is required");
			return;
		}
		setScheduleLoading(workflowId);
		try {
			const schedule = await api.updateWorkflowSchedule(workflowId, {
				cron_expression: scheduleForm.cronExpression,
				timezone: scheduleForm.timezone,
				is_active: true,
				input: inputValue,
			});
			setSchedules((prev) => ({ ...prev, [workflowId]: schedule }));
			setEditingSchedule(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to save schedule");
		} finally {
			setScheduleLoading(null);
		}
	};

	const handleDeleteSchedule = async (workflowId: string) => {
		setScheduleLoading(workflowId);
		try {
			await api.deleteWorkflowSchedule(workflowId);
			setSchedules((prev) => {
				const next = { ...prev };
				delete next[workflowId];
				return next;
			});
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to delete schedule");
		} finally {
			setScheduleLoading(null);
		}
	};

	const handleToggleSchedule = async (workflowId: string, isActive: boolean) => {
		setScheduleLoading(workflowId);
		try {
			const schedule = isActive
				? await api.resumeWorkflowSchedule(workflowId)
				: await api.pauseWorkflowSchedule(workflowId);
			setSchedules((prev) => ({ ...prev, [workflowId]: schedule }));
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to update schedule");
		} finally {
			setScheduleLoading(null);
		}
	};

	const handleTriggerSchedule = async (workflowId: string) => {
		setScheduleLoading(workflowId);
		try {
			await api.triggerWorkflowSchedule(workflowId);
			// Reload schedule to get updated counters
			await loadSchedule(workflowId);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Failed to trigger execution");
		} finally {
			setScheduleLoading(null);
		}
	};

	const getUnpublishedWorkflows = () => {
		const publishedNames = publishedWorkflows.map((pw) => pw.graph_name);
		return availableWorkflows.filter((wf) => !publishedNames.includes(wf.name));
	};

	// Filtering and sorting functions
	const getFilteredWorkflows = (
		workflows: PublishedWorkflow[] | WorkflowInfo[],
		isPublished: boolean,
	) => {
		return workflows.filter((workflow) => {
			const name =
				"graph_name" in workflow ? workflow.graph_name : workflow.name;
			const description = workflow.description || "";

			// Search filter (using debounced query for performance)
			const matchesSearch =
				debouncedSearchQuery === "" ||
				name.toLowerCase().includes(debouncedSearchQuery.trim().toLowerCase()) ||
				description.toLowerCase().includes(debouncedSearchQuery.trim().toLowerCase());

			if (!matchesSearch) return false;

			// Published/Unpublished filter
			if (isPublished) {
				if (!filters.showPublished) return false;

				// Authentication filter for published workflows
				const pubWorkflow = workflow as PublishedWorkflow;
				if (
					filters.requiresAuth === "required" &&
					!pubWorkflow.require_authentication
				)
					return false;
				if (
					filters.requiresAuth === "not-required" &&
					pubWorkflow.require_authentication
				)
					return false;
			} else {
				if (!filters.showUnpublished) return false;
			}

			return true;
		});
	};

	const getSortedWorkflows = <T extends PublishedWorkflow | WorkflowInfo>(
		workflows: T[],
	): T[] => {
		return [...workflows].sort((a, b) => {
			let aValue: any, bValue: any;

			switch (sortBy) {
				case "name":
					aValue = ("graph_name" in a ? a.graph_name : a.name).toLowerCase();
					bValue = ("graph_name" in b ? b.graph_name : b.name).toLowerCase();
					break;
				case "accessCount":
					aValue = "access_count" in a ? a.access_count : 0;
					bValue = "access_count" in b ? b.access_count : 0;
					break;
				case "lastAccessed":
					aValue =
						"last_accessed" in a ? new Date(a.last_accessed || 0).getTime() : 0;
					bValue =
						"last_accessed" in b ? new Date(b.last_accessed || 0).getTime() : 0;
					break;
				case "publishedAt":
					aValue =
						"published_at" in a ? new Date(a.published_at || 0).getTime() : 0;
					bValue =
						"published_at" in b ? new Date(b.published_at || 0).getTime() : 0;
					break;
				default:
					return 0;
			}

			if (sortOrder === "asc") {
				return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
			} else {
				return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
			}
		});
	};

	const filteredPublishedWorkflows = getSortedWorkflows(
		getFilteredWorkflows(publishedWorkflows, true) as PublishedWorkflow[],
	);
	const filteredUnpublishedWorkflows = getSortedWorkflows(
		getFilteredWorkflows(getUnpublishedWorkflows(), false) as WorkflowInfo[],
	);

	// Fetch latest eval runs for unpublished workflows
	useEffect(() => {
		let cancelled = false;
		const fetchEvalRuns = async () => {
			const results: Record<string, EvaluationRun | null> = {};
			for (const wf of filteredUnpublishedWorkflows) {
				if (wf.workflow_id in latestEvalRuns) continue;
				try {
					const run = await getLatestRun(wf.workflow_id);
					if (!cancelled) results[wf.workflow_id] = run;
				} catch {
					if (!cancelled) results[wf.workflow_id] = null;
				}
			}
			if (!cancelled && Object.keys(results).length > 0) {
				setLatestEvalRuns((prev) => ({ ...prev, ...results }));
				setRegressionAcknowledged((prev) => {
					const next = { ...prev };
					for (const id of Object.keys(results)) {
						if (!(id in next)) next[id] = false;
					}
					return next;
				});
			}
		};
		fetchEvalRuns();
		return () => { cancelled = true; };
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [availableWorkflows]);

	const fetchWorkflowToken = useCallback(async (graphName: string) => {
		try {
			const result = await api.getWorkflowHttpTriggerToken(graphName);
			setWorkflowTokens((prev) => ({ ...prev, [graphName]: result.token }));
		} catch {
			// Token fetch failed — leave empty, cURL will use placeholder
		}
	}, []);

	const toggleWorkflowExpansion = useCallback(
		(workflowName: string, workflowId?: string) => {
			setExpandedWorkflows((prev) => {
				const wasExpanded = prev[workflowName];
				if (!wasExpanded) {
					// Load schedule when expanding if we haven't loaded it yet.
					if (workflowId && !schedulesRef.current[workflowId]) {
						loadSchedule(workflowId);
					}
					// Fetch workflow token when expanding (if not already fetched)
					if (!workflowTokens[workflowName]) {
						fetchWorkflowToken(workflowName);
					}
				}
				return { ...prev, [workflowName]: !wasExpanded };
			});
		},
		[workflowTokens, fetchWorkflowToken],
	);

	// Tutorial: "Show Me" action handlers
	useEffect(() => {
		const handlePublish = () => {
			const target = tutorialWorkflowName
				? availableWorkflows.find((w) => w.name === tutorialWorkflowName)
				: availableWorkflows[0];
			if (target) {
				publishWorkflow(target.name);
			}
		};

		const handleExpand = () => {
			const target = tutorialWorkflowName
				? publishedWorkflows.find((w) => w.graph_name === tutorialWorkflowName)
				: publishedWorkflows[0];
			if (target) {
				toggleWorkflowExpansion(target.graph_name, target.workflow_id);
			}
		};

		const handleUnpublish = () => {
			const target = tutorialWorkflowName
				? publishedWorkflows.find((w) => w.graph_name === tutorialWorkflowName)
				: publishedWorkflows[0];
			if (target) {
				// Skip confirmation dialog during tutorial
				executeUnpublishRef.current(target.graph_name);
			}
		};

		window.addEventListener("tutorialPublishWorkflow", handlePublish);
		window.addEventListener("tutorialExpandPublished", handleExpand);
		window.addEventListener("tutorialUnpublishWorkflow", handleUnpublish);
		return () => {
			window.removeEventListener("tutorialPublishWorkflow", handlePublish);
			window.removeEventListener("tutorialExpandPublished", handleExpand);
			window.removeEventListener("tutorialUnpublishWorkflow", handleUnpublish);
		};
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [tutorialWorkflowName, availableWorkflows, publishedWorkflows, toggleWorkflowExpansion]);

	const getExampleRequestBody = (workflowName: string) => {
		return {
			message: `Process this data for ${workflowName}`,
			async_mode: false,
			timeout: 300,
		};
	};

	const getCurlExample = (workflow: PublishedWorkflow) => {
		const exampleBody = getExampleRequestBody(workflow.graph_name);
		const resolvedEndpoint = resolveEndpointUrl(workflow);

		const tokenValue = workflowTokens[workflow.graph_name] || "YOUR_TOKEN";
		const authHeader = workflow.require_authentication
			? ` \\\n  -H "Authorization: Bearer ${tokenValue}"`
			: "";

		return `curl -X POST "${resolvedEndpoint}"${authHeader} \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify(exampleBody, null, 2)}'`;
	};

	// useCallback handlers for event handling optimization
	const handleClearError = useCallback(() => {
		setError(null);
	}, []);

	const handleClearSearch = useCallback(() => {
		setSearchQuery("");
	}, []);

	const handleToggleFilters = useCallback(() => {
		setShowFilters(!showFilters);
	}, [showFilters]);

	const handleToggleSortOrder = useCallback(() => {
		setSortOrder(sortOrder === "asc" ? "desc" : "asc");
	}, [sortOrder]);

	const handleDismissPatBanner = useCallback(() => {
		setShowPatBanner(false);
		localStorage.setItem("patBannerDismissed", "true");
	}, []);

	const handleSearchChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setSearchQuery(e.target.value);
		},
		[],
	);

	const handleSortByChange = useCallback(
  		(value: string) => {
    		setSortBy( value as "name" | "accessCount" | "lastAccessed" | "publishedAt");
  		},
 		[],
	);

	const handleShowPublishedChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setFilters((prev) => ({ ...prev, showPublished: e.target.checked }));
		},
		[],
	);

	const handleShowUnpublishedChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setFilters((prev) => ({ ...prev, showUnpublished: e.target.checked }));
		},
		[],
	);

	const handleRequiresAuthChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			setFilters((prev) => ({ ...prev, requiresAuth: e.target.value }));
		},
		[],
	);

	const handleExpandAll = useCallback(() => {
		const allExpanded: { [key: string]: boolean } = {};
		filteredPublishedWorkflows.forEach((workflow) => {
			allExpanded[workflow.graph_name] = true;
		});
		setExpandedWorkflows(allExpanded);
	}, [filteredPublishedWorkflows]);

	const handleCollapseAll = useCallback(() => {
		setExpandedWorkflows({});
	}, []);

	// Factory functions for dynamic handlers
	const createToggleWorkflowHandler = useCallback(
		(workflowName: string, workflowId?: string) => () => {
			toggleWorkflowExpansion(workflowName, workflowId);
		},
		[toggleWorkflowExpansion],
	);

	const unpublishWorkflowRef = useRef(unpublishWorkflow);
	unpublishWorkflowRef.current = unpublishWorkflow;

	const executeUnpublishRef = useRef(executeUnpublish);
	executeUnpublishRef.current = executeUnpublish;

	const createUnpublishHandler = useCallback(
		(workflowName: string) => () => {
			unpublishWorkflowRef.current(workflowName);
		},
		[],
	);

	const createCopyHandler = useCallback(
		(text: string, type: string) => () => {
			copyToClipboard(text, type);
		},
		[],
	);

	const createPublishHandler = useCallback(
		(workflowName: string) => () => {
			publishWorkflow(workflowName);
		},
		[],
	);

	const areAllPublishedWorkflowsExpanded =
		filteredPublishedWorkflows.length > 0 &&
		filteredPublishedWorkflows.every(
			(workflow) => expandedWorkflows[workflow.graph_name],
		);

	if (loading) {
		return (
			<div className="h-full bg-white flex items-center justify-center p-6">
				<div className="flex flex-col items-center justify-center gap-4 rounded-2xl bg-white px-8 py-16 w-full max-w-md">
					<div className="h-10 w-10 rounded-full border-2 border-transparent border-t-orange-500 animate-spin" />
					<p className="text-sm text-slate-600">
						Loading workflow publishing data...
					</p>
				</div>
			</div>
		);
	}


	return (
		<div className="h-full overflow-auto bg-white">
			<div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">

				{/* ── Header ── */}
				<div className="mb-5" data-tutorial="publish-header">
					<h1 className="text-2xl font-bold text-gray-900">Workflow Publishing</h1>
					<p className="text-sm text-gray-500 mt-1">
						Publish your workflows as HTTP endpoints for external integration and automation.
					</p>
					{error && (
						<div className="mt-3 flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded">
							<p className="text-red-600 text-sm flex-1">{error}</p>
							<button onClick={handleClearError} className="text-red-400 hover:text-red-600">
								<X className="w-4 h-4" />
							</button>
						</div>
					)}
				</div>

				{/* ── PAT Banner ── */}
				{showPatBanner && (
					<div className="mb-5 border border-gray-200 rounded bg-white p-4 flex items-start gap-3">
						<Rocket className="w-5 h-5 text-[#ff6b00] shrink-0 mt-0.5" />
						<div className="flex-1 min-w-0">
							<p className="text-sm font-semibold text-gray-900 mb-1">
								New Themed Access Tokens Available!
							</p>
							<p className="text-xs text-gray-500 mb-3">
								You can now create user-specific API tokens that inherit your workflow permission.
								These tokens are more flexible and can be scoped to multiple workflows.
							</p>
							<div className="flex flex-wrap items-center gap-2">
								<a
									href="/settings?tab=api-tokens"
									className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#ff6b00] text-white text-xs font-semibold rounded hover:bg-[#e55f00] transition-colors"
								>
									<Key className="w-3 h-3" />
									Manage API Tokens
								</a>
								<span className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#ff6b00] text-white text-xs font-medium rounded">
									<Check className="w-3 h-3" />
									User-Scoped
								</span>
								<span className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#ff6b00] text-white text-xs font-medium rounded">
									<Key className="w-3 h-3" />
									Revocable
								</span>
								<span className="inline-flex items-center gap-1 px-2.5 py-1 bg-[#ff6b00] text-white text-xs font-medium rounded">
									<Globe className="w-3 h-3" />
									Multi-workflow
								</span>
							</div>
						</div>
						<button
							onClick={handleDismissPatBanner}
							className="text-gray-400 hover:text-gray-600 shrink-0 mt-0.5"
							title="Dismiss banner"
						>
							<X className="w-4 h-4" />
						</button>
					</div>
				)}

				{/* ── Search & Filter Controls ── */}
				<div className="mb-5">
					<div className="flex flex-wrap items-center gap-2">
						<div className="flex-1 relative min-w-48">
							<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
							<input
								ref={searchInputRef}
								data-tutorial="publish-search"
								type="text"
								placeholder="Search workflows by name or description..."
								aria-label="Search workflows"
								value={searchQuery}
								onChange={handleSearchChange}
								className="w-full pl-9 pr-8 py-2 text-sm border border-gray-200 rounded bg-white placeholder-gray-400 text-gray-800 focus:outline-none focus:ring-2 focus:ring-orange-400/30 focus:border-orange-400"
							/>
							{searchQuery && (
								<button onClick={handleClearSearch} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
									<X className="w-4 h-4" />
								</button>
							)}
						</div>
						<button
							data-tutorial="publish-filters"
							onClick={handleToggleFilters}
							className={`flex items-center gap-1.5 px-3 py-2 text-sm border rounded transition-colors ${
								showFilters
									? "bg-[#ff6b00] border-[#ff6b00] text-white"
									: "bg-white border-gray-200 text-[#ff6b00] hover:border-orange-300 hover:bg-[#FFF1E8]"
							}`}
						>
							<Filter className="w-4 h-4" />
							Filters
						</button>
						<div className="w-full sm:w-[180px]">
							<Dropdown
								value={sortBy}
								onChange={handleSortByChange}
								menuAppearance="light"
								width="trigger"
								triggerClassName="border border-gray-200 rounded bg-white text-gray-600 hover:border-orange-300 focus:border-orange-400"
								options={[
									{ value: "name", label: "Sort by Name" },
									{ value: "accessCount", label: "Sort by Access Count" },
									{ value: "lastAccessed", label: "Sort by Last Accessed" },
									{ value: "publishedAt", label: "Sort by Published Date" },
								]}
							/>
						</div>
						<button
							onClick={handleToggleSortOrder}
							className="p-2 border border-gray-200 rounded bg-white text-gray-500 hover:bg-gray-50 transition-colors"
							title={sortOrder === "asc" ? "Sort ascending" : "Sort descending"}
						>
							{sortOrder === "asc" ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
						</button>
					</div>

					{showFilters && (
						<div className="mt-3 p-4 border border-gray-200 rounded bg-gray-50">
							<div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
								<div>
									<label id="workflow-status-label" className="block text-xs font-semibold text-gray-600 mb-2 capitalize tracking-wide">Workflow Status</label>
									<div className="space-y-1.5" role="group" aria-labelledby="workflow-status-label">
										<label htmlFor="show-published-checkbox" className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
											<input id="show-published-checkbox" type="checkbox" checked={filters.showPublished} onChange={handleShowPublishedChange} className="accent-orange-500" />
											Published
										</label>
										<label htmlFor="show-unpublished-checkbox" className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
											<input id="show-unpublished-checkbox" type="checkbox" checked={filters.showUnpublished} onChange={handleShowUnpublishedChange} className="accent-orange-500" />
											Unpublished
										</label>
									</div>
								</div>
								<div>
									<label htmlFor="auth-filter-select" className="block text-xs font-semibold text-gray-600 mb-2 capitalize tracking-wide">Authentication</label>
									<select id="auth-filter-select" value={filters.requiresAuth} onChange={handleRequiresAuthChange} className="w-full pl-3 pr-8 py-2 text-sm border border-gray-200 rounded bg-white text-gray-600 focus:outline-none focus:border-orange-400 cursor-pointer appearance-none">
										<option value="all">All Workflows</option>
										<option value="required">Requires Authentication</option>
										<option value="not-required">No Authentication</option>
									</select>
								</div>
								<div className="flex items-end">
									<div className="text-xs text-gray-500 space-y-0.5">
										<div>Published: {filteredPublishedWorkflows.length}</div>
										<div>Unpublished: {filteredUnpublishedWorkflows.length}</div>
									</div>
								</div>
							</div>
						</div>
					)}
				</div>

				{/* ── Published Workflows ── */}
				<div data-tutorial="publish-workflows-section" ref={publishedSectionRef} className="mb-6">
					<div className="flex items-center justify-between mb-3">
						<h2 className="text-base font-semibold text-gray-900">
							Published Workflows ({filteredPublishedWorkflows.length})
							{filteredPublishedWorkflows.length !== publishedWorkflows.length && (
								<span className="ml-2 text-sm text-gray-400 font-normal">of {publishedWorkflows.length} total</span>
							)}
						</h2>
						{filteredPublishedWorkflows.length > 0 && (
							<div className="flex gap-2">
								<button onClick={handleExpandAll} data-tutorial="publish-btn" className={`text-xs px-3 py-1.5 rounded transition-colors font-medium ${
									areAllPublishedWorkflowsExpanded
										? "bg-[#ff6b00] text-white hover:bg-[#e55f00]"
										: "border border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
								}`}>
									Expand All
								</button>
								<button onClick={handleCollapseAll} className={`text-xs px-3 py-1.5 rounded transition-colors font-medium ${
									areAllPublishedWorkflowsExpanded
										? "border border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
										: "bg-[#ff6b00] text-white hover:bg-[#e55f00]"
								}`}>
									Collapse All
								</button>
							</div>
						)}
					</div>

					{filteredPublishedWorkflows.length === 0 ? (
						<div className="py-12 border border-dashed border-gray-200 rounded text-center">
							<Globe className="w-8 h-8 text-gray-300 mx-auto mb-2" />
							{publishedWorkflows.length === 0 ? (
								<>
									<p className="text-sm font-medium text-gray-600">No workflows published yet</p>
									<p className="text-xs text-gray-400 mt-1">Publish a workflow below to make it available via HTTP API</p>
								</>
							) : (
								<p className="text-sm text-gray-500">No workflows match your filters</p>
							)}
						</div>
					) : (
						<div className="space-y-2">
							{filteredPublishedWorkflows.map((workflow, pubIndex) => {
								const isExpanded = expandedWorkflows[workflow.graph_name];
								const isTutorialTarget = tutorialWorkflowName ? workflow.graph_name === tutorialWorkflowName : pubIndex === 0;
								const isBeingUnpublished = unpublishingWorkflow === workflow.graph_name;
								const resolvedEndpointUrl = resolveEndpointUrl(workflow);
								const endpointDisplay = resolvedEndpointUrl.replace(/^https?:\/\//, "");
								const slugBadge = workflow.custom_slug || workflow.graph_name.slice(0, 6).replace(/-/g, "");

								return (
									<div key={workflow.graph_name} className={`border border-gray-200 rounded bg-white transition-opacity ${isBeingUnpublished ? "opacity-50 pointer-events-none" : ""}`}>
										{/* Card header row */}
										<div className="px-4 py-3">
											<div className="flex items-start gap-3">
												<button
													onClick={createToggleWorkflowHandler(workflow.graph_name, workflow.workflow_id)}
													className="mt-1 text-gray-400 hover:text-gray-600 shrink-0"
													{...(isTutorialTarget ? { "data-tutorial": "publish-expand-btn" } : {})}
												>
													{isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
												</button>
												<div className="flex-1 min-w-0">
													<h3 className="text-sm font-semibold text-gray-900">{workflow.graph_name}</h3>
													<p className="text-xs text-gray-500 mt-0.5">{workflow.description || "No description provided"}</p>
													<div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-gray-500">
														<span className="flex items-center gap-1.5">
															<Globe className="w-3 h-3 text-orange-500" />
															<button
																onClick={createCopyHandler(resolvedEndpointUrl, `quick-url-${workflow.graph_name}`)}
																className="font-mono truncate max-w-xs hover:text-slate-800 transition-colors text-left"
																title="Copy endpoint URL"
															>
																{endpointDisplay}
															</button>
															{copiedItem === `quick-url-${workflow.graph_name}` && <Check className="w-3 h-3 text-[#0DA931]" />}
														</span>
														{slugBadge && (
															<span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs font-mono">{slugBadge}</span>
														)}
														<span className="flex items-center gap-1">
															<Clock className="w-3 h-3" />
															Last used: {workflow.last_accessed ? formatDate(workflow.last_accessed) : "Never"}
														</span>
														{workflow.require_authentication && (
															<span className="flex items-center gap-1 text-gray-600">
																<Lock className="w-3 h-3" />
																Secured
															</span>
														)}
													</div>
												</div>
												<div className="flex items-center gap-2 shrink-0">
													<span className="px-3 py-1 text-white text-xs font-semibold rounded" style={{ backgroundColor: "#00A63E" }}>
														Published
													</span>
													<button
														onClick={createUnpublishHandler(workflow.graph_name)}
														disabled={isBeingUnpublished}
														className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
														title="Unpublish workflow"
														{...(isTutorialTarget ? { "data-tutorial": "publish-unpublish-btn" } : {})}
													>
														{isBeingUnpublished ? (
															<div className="w-4 h-4 border-2 border-red-300 border-t-transparent rounded-full animate-spin" />
														) : (
															<Trash2 className="w-4 h-4" />
														)}
													</button>
												</div>
											</div>
										</div>

										{/* Expanded content */}
										{isExpanded && (
											<div className="border-t border-gray-100">
												<div className="p-5 space-y-5">
													{/* API Details */}
													<div {...(isTutorialTarget ? { "data-tutorial": "publish-detail-endpoint" } : {})}>
														<h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
															<Globe className="w-4 h-4 text-orange-500" />
															API Integration
														</h4>
														<label className="block text-xs font-medium text-gray-500 mb-1.5">API Endpoint</label>
														<div className="flex items-center gap-2">
															<div className="flex-1 bg-gray-50 border border-gray-200 rounded px-3 py-2 text-xs font-mono text-gray-700">{resolvedEndpointUrl}</div>
															<button onClick={createCopyHandler(resolvedEndpointUrl, `url-${workflow.graph_name}`)} className="p-2 border border-gray-200 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-50 transition-colors" title="Copy endpoint URL">
																{copiedItem === `url-${workflow.graph_name}` ? <Check className="w-4 h-4 text-[#0DA931]" /> : <Copy className="w-4 h-4" />}
															</button>
														</div>
													</div>

													{/* Example Request */}
													<div>
														<h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
															<Code className="w-4 h-4 text-orange-500" />
															Example Request
														</h4>
														<div className="mb-3">
															<label className="block text-xs font-medium text-gray-500 mb-1.5">Request Body (JSON)</label>
															<div className="bg-gray-50 border border-gray-200 rounded p-3">
																<pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap">{JSON.stringify(getExampleRequestBody(workflow.graph_name), null, 2)}</pre>
															</div>
														</div>
														<div className="mb-3" {...(isTutorialTarget ? { "data-tutorial": "publish-detail-curl" } : {})}>
															<div className="flex items-center justify-between mb-1.5">
																<label className="text-xs font-medium text-gray-500">cURL Example</label>
																<button onClick={createCopyHandler(getCurlExample(workflow), `curl-${workflow.graph_name}`)} className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-800 px-2 py-1 rounded hover:bg-gray-100 transition-colors">
																	{copiedItem === `curl-${workflow.graph_name}` ? <><Check className="w-3 h-3 text-[#0DA931]" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
																</button>
															</div>
															<div className="bg-gray-50 border border-gray-200 rounded p-3">
																<pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap">{getCurlExample(workflow)}</pre>
															</div>
														</div>

														{/* API Token */}
														{workflow.require_authentication && (
															<div {...(isTutorialTarget ? { "data-tutorial": "publish-detail-token" } : {})}>
																<h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
																	<Key className="w-4 h-4 text-orange-500" />
																	API Token
																</h4>
																<div className="bg-gray-50 border border-gray-200 rounded p-3">
																	{workflowTokens[workflow.graph_name] ? (
																		<div>
																			<div className="flex items-center gap-2">
																				<code className="flex-1 text-xs font-mono text-gray-700 truncate">
																					{visibleTokens[workflow.graph_name] ? workflowTokens[workflow.graph_name] : `${workflowTokens[workflow.graph_name].slice(0, 12)}${"*".repeat(20)}`}
																				</code>
																				<button onClick={() => setVisibleTokens((prev) => ({ ...prev, [workflow.graph_name]: !prev[workflow.graph_name] }))} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors" title={visibleTokens[workflow.graph_name] ? "Hide token" : "Show token"}>
																					{visibleTokens[workflow.graph_name] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
																				</button>
																				<button onClick={createCopyHandler(workflowTokens[workflow.graph_name], `token-${workflow.graph_name}`)} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors" title="Copy token">
																					{copiedItem === `token-${workflow.graph_name}` ? <Check className="w-4 h-4 text-[#0DA931]" /> : <Copy className="w-4 h-4" />}
																				</button>
																			</div>
																			<p className="mt-2 text-xs text-gray-500">Pass in the <code className="bg-gray-200 px-1 rounded">Authorization: Bearer</code> header.</p>
																		</div>
																	) : (
																		<p className="text-xs text-gray-500">Loading token...</p>
																	)}
																</div>
															</div>
														)}

														{/* Auth info */}
														{workflow.require_authentication && (
															<div className="mt-3 p-3 bg-orange-50 border border-orange-100 rounded" {...(isTutorialTarget ? { "data-tutorial": "publish-detail-auth" } : {})}>
																<p className="text-xs font-semibold text-[#ff6b00] mb-1 flex items-center gap-1">
																	<Lock className="w-3.5 h-3.5" /> Authentication Required
																</p>
																<p className="text-xs text-gray-900 mb-1.5">Pass a token in the <code className="bg-orange-100 px-1 rounded">Authorization: Bearer</code> header. Supported types:</p>
																<ul className="text-xs text-gray-900 space-y-0.5 list-disc list-inside">
																	<li><strong>Workflow token</strong> (<code className="bg-orange-100 px-0.5 rounded">wf_</code>) — unique to this workflow</li>
																	<li><strong>Personal Access Token</strong> (<code className="bg-orange-100 px-0.5 rounded">na_</code>) — create in <a href="/settings?tab=api-tokens" className="underline">Settings</a></li>
																	<li><strong>JWT</strong> — session-based</li>
																</ul>
															</div>
														)}
													</div>

													{/* Schedule */}
													<div {...(isTutorialTarget ? { "data-tutorial": "publish-detail-schedule" } : {})}>
														<h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
															<CalendarClock className="w-4 h-4 text-orange-500" />
															Schedule
														</h4>
														{(() => {
																const schedule = schedules[workflow.workflow_id];
																const isLoadingSchedule = scheduleLoading === workflow.workflow_id;
																const isEditing = editingSchedule === workflow.workflow_id;

																if (isEditing) {
																	return (
																		<div className="space-y-3 bg-gray-50 border border-gray-200 rounded p-4">
																			<div>
																				<label className="block text-xs font-medium text-gray-600 mb-1.5">Frequency</label>
																				<select value={scheduleForm.cronExpression} onChange={(e) => setScheduleForm((prev) => ({ ...prev, cronExpression: e.target.value, isCustom: false }))} className="w-full bg-white border border-gray-200 rounded px-3 py-2 text-sm text-gray-800 focus:outline-none focus:border-orange-400">
																					{CRON_PRESETS.map((preset) => <option key={preset.value} value={preset.value}>{preset.label}</option>)}
																				</select>
																			</div>
																			<div>
																				<label className="block text-xs font-medium text-gray-600 mb-1.5">Timezone</label>
																				<select value={scheduleForm.timezone} onChange={(e) => setScheduleForm((prev) => ({ ...prev, timezone: e.target.value }))} className="w-full bg-white border border-gray-200 rounded px-3 py-2 text-sm text-gray-800 focus:outline-none focus:border-orange-400">
																					{(() => { try { return Intl.supportedValuesOf("timeZone").map((tz) => <option key={tz} value={tz}>{tz}</option>); } catch { return <option value="UTC">UTC</option>; } })()}
																				</select>
																			</div>
																			<div>
																				<label className="block text-xs font-medium text-gray-600 mb-1.5">Input <span className="text-red-500">*</span></label>
																				<input
																					type="text"
																					value={scheduleForm.input}
																					onChange={(e) => setScheduleForm((prev) => ({ ...prev, input: e.target.value }))}
																					placeholder="Input to pass on each scheduled run"
																					required
																					className={`w-full bg-white border rounded px-3 py-2 text-sm text-gray-800 focus:outline-none focus:border-orange-400 ${scheduleForm.input.trim() ? "border-gray-200" : "border-red-400"}`}
																				/>
																				{!scheduleForm.input.trim() && (
																					<p className="text-xs mt-1 text-red-500">Input is required.</p>
																				)}
																			</div>
																			<div className="flex gap-2 pt-1">
																				<button onClick={() => handleSaveSchedule(workflow.workflow_id)} disabled={isLoadingSchedule || !scheduleForm.cronExpression || !scheduleForm.input.trim()} className="flex items-center gap-1.5 px-3 py-1.5 bg-[#ff6b00] text-white text-sm font-medium rounded hover:bg-[#e55f00] disabled:opacity-50 transition-colors">
																					{isLoadingSchedule ? <div className="w-3.5 h-3.5 border-2 border-t-transparent rounded-full animate-spin border-white" /> : <Check className="w-3.5 h-3.5" />}
																					Save
																				</button>
																				<button onClick={() => setEditingSchedule(null)} className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded transition-colors">Cancel</button>
																			</div>
																		</div>
																	);
																}

																if (schedule?.cron_expression) {
																	return (
																		<div className="bg-gray-50 border border-gray-200 rounded p-4 space-y-3">
																			<div className="flex items-center justify-between">
																				<div className="flex items-center gap-2">
																					<span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${schedule.is_active ? "bg-[#F1F8E9] text-[#0DA931]" : "bg-yellow-100 text-yellow-700"}`}>
																						<div className={`w-1.5 h-1.5 rounded-full ${schedule.is_active ? "bg-[#0DA931]" : "bg-yellow-500"}`} />
																						{schedule.is_active ? "Active" : "Paused"}
																					</span>
																					<span className="text-sm text-gray-800 font-medium">{getCronLabel(schedule.cron_expression)}</span>
																				</div>
																				<div className="flex items-center gap-1">
																					<button onClick={() => handleToggleSchedule(workflow.workflow_id, !schedule.is_active)} disabled={isLoadingSchedule} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors" title={schedule.is_active ? "Pause" : "Resume"}>
																						{schedule.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
																					</button>
																					<button onClick={() => { setScheduleForm({ cronExpression: schedule.cron_expression || "0 * * * *", timezone: schedule.timezone || "UTC", input: typeof schedule.input === "string" ? schedule.input : String(schedule.input ?? ""), isCustom: !CRON_PRESETS.find((p) => p.value === schedule.cron_expression) }); setEditingSchedule(workflow.workflow_id); }} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors" title="Edit schedule">
																						<Settings className="w-4 h-4" />
																					</button>
																					<button onClick={() => handleTriggerSchedule(workflow.workflow_id)} disabled={isLoadingSchedule} className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded transition-colors" title="Run now">
																						<Play className="w-4 h-4" />
																					</button>
																					<button onClick={() => handleDeleteSchedule(workflow.workflow_id)} disabled={isLoadingSchedule} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors" title="Delete schedule">
																						<Trash2 className="w-4 h-4" />
																					</button>
																				</div>
																			</div>
																			<div className="grid grid-cols-3 gap-3 text-xs">
																				<div><div className="text-gray-400 mb-0.5">Next run</div><div className="text-gray-700">{schedule.next_run_at ? formatDistanceToNow(new Date(schedule.next_run_at), { addSuffix: true }) : "—"}</div></div>
																				<div><div className="text-gray-400 mb-0.5">Runs</div><div className="text-gray-700">{schedule.run_count}</div></div>
																				<div><div className="text-gray-400 mb-0.5">Failures</div><div className={schedule.failure_count > 0 ? "text-red-500" : "text-gray-700"}>{schedule.failure_count}</div></div>
																			</div>
																			{schedule.last_run_at && <div className="text-xs text-gray-400">Last run: {formatDistanceToNow(new Date(schedule.last_run_at), { addSuffix: true })}</div>}
																			<div className="text-xs text-gray-400">Timezone: {schedule.timezone}</div>
																			{schedule.input && <div className="text-xs text-gray-400">Input: {schedule.input}</div>}
																		</div>
																	);
																}

																return (
																	<button onClick={() => { setScheduleForm({ cronExpression: "0 * * * *", timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, input: "", isCustom: false }); setEditingSchedule(workflow.workflow_id); }} className="w-full flex items-center justify-center gap-2 px-4 py-3 border border-dashed border-gray-200 hover:border-orange-300 rounded text-sm text-gray-400 hover:text-slate-700 transition-colors">
																		<CalendarClock className="w-4 h-4" />
																		Set up a schedule
																	</button>
																);
															})()
														}
													</div>

													{/* Analytics */}
													<div>
														<h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
															<TrendingUp className="w-4 h-4 text-orange-500" />
															Analytics & Usage
														</h4>
														<div className="grid sm:grid-cols-4 gap-3">
															<div className="bg-gray-50 border border-gray-200 rounded p-3">
																<div className="flex items-center gap-1.5 text-orange-500 mb-1.5 text-xs font-medium"><Clock className="w-3 h-3" />Last Modified</div>
																<div className="text-sm font-semibold text-gray-900">{workflow.workflow_updated_at ? formatDate(workflow.workflow_updated_at) : "Unknown"}</div>
																{workflow.workflow_updated_at && <div className="text-xs text-gray-400 mt-0.5">{Math.floor((Date.now() - new Date(workflow.workflow_updated_at).getTime()) / 86400000)} days ago</div>}
															</div>
															<div className="bg-gray-50 border border-gray-200 rounded p-3">
																<div className="flex items-center gap-1.5 text-orange-500 mb-1.5 text-xs font-medium"><Users className="w-3 h-3" />Last Access</div>
																<div className="text-sm font-semibold text-gray-900">{formatDate(workflow.last_accessed)}</div>
																{!workflow.last_accessed && <div className="text-xs text-orange-400 mt-0.5">Never used</div>}
															</div>
															<div className="bg-gray-50 border border-gray-200 rounded p-3">
																<div className="flex items-center gap-1.5 text-orange-500 mb-1.5 text-xs font-medium"><TrendingUp className="w-3 h-3" />Total Calls</div>
																<div className="text-xl font-bold text-gray-900">{workflow.access_count.toLocaleString()}</div>
																{workflow.access_count > 0 && <div className="text-xs text-gray-400 mt-0.5">{workflow.access_count > 100 ? "High" : workflow.access_count > 10 ? "Active" : "Low"}</div>}
															</div>
															<div className="bg-gray-50 border border-gray-200 rounded p-3">
																<div className="flex items-center gap-1.5 text-orange-500 mb-1.5 text-xs font-medium">{workflow.require_authentication ? <Lock className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}Security</div>
																<div className="text-sm font-semibold text-gray-900">{workflow.require_authentication ? "Protected" : "Public"}</div>
																{workflow.rate_limit && <div className="text-xs text-gray-400 mt-0.5">Rate limited</div>}
															</div>
														</div>
													</div>
												</div>
											</div>
										)}
									</div>
								);
							})}
						</div>
					)}
				</div>

				{/* ── Need help section ── */}
				<div className="mb-6 border border-orange-100 rounded p-4 bg-[#FFF1E8]">
					<h3 className="text-sm font-semibold text-gray-900 mb-1">Need help getting started?</h3>
					<p className="text-xs text-gray-500 mb-2">
						Check out our documentation to learn how to publish workflows, manage API tokens, and integrate with external systems.
					</p>
					<Link href="/wiki" className="text-xs text-orange-600 hover:text-slate-900 hover:underline font-medium">
						View Documentation →
					</Link>
				</div>

				{/* ── Available Workflows ── */}
				<div data-tutorial="publish-available-section">
					<h2 data-tutorial="publish-available-heading" className="text-base font-semibold text-gray-900 mb-3">
						Available Workflows ({filteredUnpublishedWorkflows.length})
						{filteredUnpublishedWorkflows.length !== getUnpublishedWorkflows().length && (
							<span className="ml-2 text-sm text-gray-400 font-normal">of {getUnpublishedWorkflows().length} total</span>
						)}
					</h2>

					{filteredUnpublishedWorkflows.length === 0 ? (
						<div className="py-12 border border-dashed border-gray-200 rounded text-center">
							<Settings className="w-8 h-8 text-gray-300 mx-auto mb-2" />
							{getUnpublishedWorkflows().length === 0 ? (
								<>
									<p className="text-sm font-medium text-gray-600">All workflows are published</p>
									<p className="text-xs text-gray-400 mt-1">Create new workflows to publish more API endpoints</p>
								</>
							) : (
								<p className="text-sm text-gray-500">No unpublished workflows match your filters</p>
							)}
						</div>
					) : (
						<div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 pb-6">
							{filteredUnpublishedWorkflows.map((workflow, unpubIndex) => {
								const isBeingPublished = publishingWorkflow === workflow.name;
								const isTutorialPublishTarget = tutorialWorkflowName ? workflow.name === tutorialWorkflowName : unpubIndex === 0;
								const run = latestEvalRuns[workflow.workflow_id];
								const acked = regressionAcknowledged[workflow.workflow_id] ?? false;
								return (
									<div key={workflow.name} className={`bg-white border border-gray-200 rounded p-4 flex flex-col transition-opacity ${isBeingPublished ? "opacity-60" : ""}`}>
										<div className="flex items-start gap-3 mb-3">
											<div className="p-2 bg-gray-100 rounded shrink-0">
												<Settings className="w-4 h-4 text-gray-500" />
											</div>
											<div className="flex-1 min-w-0">
												<h3 className="text-sm font-semibold text-gray-900 truncate">{workflow.name}</h3>
												<p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{workflow.description || "No description provided"}</p>
											</div>
										</div>

										{run?.regression_flag === true && !acked && (
											<div className="bg-red-50 border border-red-200 rounded p-3 mb-3">
												<p className="text-red-700 text-xs font-semibold flex items-center gap-1.5 mb-1"><AlertTriangle className="w-3.5 h-3.5" /> Severe Regression Detected</p>
												<p className="text-xs text-red-600 mb-1">Score: {run.composite_score ?? "—"}/100, severity: {run.regression_severity ?? "unknown"}</p>
												<div className="flex gap-3 mt-2">
													<a href="/evaluations" className="text-xs text-red-500 underline">View Results</a>
													<button type="button" onClick={() => setRegressionAcknowledged((prev) => ({ ...prev, [workflow.workflow_id]: true }))} className="text-xs text-red-600 underline">Acknowledge</button>
												</div>
											</div>
										)}
										{run?.regression_ack_required === true && run?.regression_flag !== true && !acked && (
											<div className="bg-orange-50 border border-orange-200 rounded p-3 mb-3">
												<p className="text-orange-700 text-xs font-semibold flex items-center gap-1.5 mb-1"><AlertTriangle className="w-3.5 h-3.5" /> Moderate Regression Noted</p>
												<div className="flex gap-3 mt-2">
													<a href="/evaluations" className="text-xs text-orange-500 underline">View Results</a>
													<button type="button" onClick={() => setRegressionAcknowledged((prev) => ({ ...prev, [workflow.workflow_id]: true }))} className="text-xs text-orange-600 underline">Acknowledge</button>
												</div>
											</div>
										)}
										{run != null && !run.regression_flag && !run.regression_ack_required && (
											<p className="text-xs text-[#0DA931] flex items-center gap-1 mb-2">
												<CheckCircle className="w-3.5 h-3.5" />
												Latest evaluation: {run.composite_score ?? "—"}/100 — passed
											</p>
										)}

										<div className="mt-auto pt-2">
											<button
												onClick={createPublishHandler(workflow.name)}
												disabled={isBeingPublished}
												className="w-full flex items-center justify-center gap-2 py-2 bg-[#ff6b00] text-white text-sm font-semibold rounded hover:bg-[#e55f00] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
												{...(isTutorialPublishTarget ? { "data-tutorial": "publish-demo-btn" } : {})}
											>
												{isBeingPublished ? (
													<><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Publishing...</>
												) : (
													<><Globe className="w-4 h-4" />Publish Workflow</>
												)}
											</button>
										</div>
									</div>
								);
							})}
						</div>
					)}
				</div>
			</div>

			<ConfirmDialog
				isOpen={unpublishConfirm.isOpen}
				title="Unpublish Workflow"
				message={`Are you sure you want to unpublish "${unpublishConfirm.workflowName}"? This will disable HTTP access to this workflow.`}
				confirmText="Unpublish"
				cancelText="Cancel"
				type="danger"
				onConfirm={() => {
					if (unpublishConfirm.workflowName) {
						executeUnpublish(unpublishConfirm.workflowName);
					}
				}}
				onCancel={() => setUnpublishConfirm({ isOpen: false, workflowName: null })}
			/>
		</div>
	);
}
