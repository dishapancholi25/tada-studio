"use client";

import clsx from "clsx";
import {
	ArrowLeft,
	BadgeCheck,
	BookOpen,
	Bot,
	Brain,
	Check,
	ClipboardList,
	Copy,
	Cpu,
	Database,
	Download,
	Globe,
	Layers,
	LayoutDashboard,
	Loader2,
	Puzzle,
	Share2,
	Sparkles,
	Timer,
	Upload,
	Users,
	X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import type React from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Edge, Node } from "reactflow";
import { Background } from "reactflow";
import "reactflow/dist/style.css";
import { defaultSmoothEdgeOptions } from "@/components/core/shared/defaultEdgeOptions";
import GraphCanvas from "@/components/core/shared/GraphCanvas";
import {
	builderEdgeTypes,
	builderNodeTypes,
} from "@/components/core/shared/nodeRegistry";
import CloneWorkflowDialog from "@/components/library/CloneWorkflowDialog";
import CustomMinimap from "@/components/ui/CustomMinimap";
import CustomZoomControls from "@/components/ui/CustomZoomControls";
import TabBar from "@/components/ui/TabBar";
import SimpleMarkdown from "@/components/utils/SimpleMarkdown";
import StructuredOutputViewer from "@/components/utils/StructuredOutputViewer";
import { useToast } from "@/contexts/ToastContext";
import {
	getAgentTemplateInsertContext,
	setAgentTemplateInsertPayload,
} from "@/lib/agentTemplateInsertion";
import { api } from "@/lib/api";
import { convertGraphDefinitionToReactFlow } from "@/lib/graphDefinitionToReactFlow";
import type {
	AgentTemplateDetail,
	WorkflowTemplateDetail,
	WorkflowTemplateGraphDefinition,
} from "@/types/library";

type OverviewTabId = "overview" | "input_example" | "output_example";
type AgentTabId = "core" | "input" | "memory" | "output" | "orchestration";

interface WorkflowTemplatePreviewProps {
	templateId: string;
	templateKind?: "workflow" | "agent";
	agentInsertMode?: boolean;
}

const emptyGraph: WorkflowTemplateGraphDefinition = {
	nodes: [],
};

const overviewTabs = [
	{
		id: "overview",
		label: "Overview",
		icon: <LayoutDashboard className="w-4 h-4" />,
		accent: "core",
	},
	{
		id: "input_example",
		label: "Input Example",
		icon: <Download className="w-4 h-4" />,
		accent: "input",
	},
	{
		id: "output_example",
		label: "Output Example",
		icon: <Upload className="w-4 h-4" />,
		accent: "output",
	},
] as const satisfies Array<{
	id: OverviewTabId;
	label: string;
	icon: React.ReactElement;
	accent: any;
}>;

const agentTabs = [
	{
		id: "core",
		label: "Core",
		icon: <Bot className="w-4 h-4" />,
		accent: "core",
	},
	{
		id: "input",
		label: "Input",
		icon: <Share2 className="w-4 h-4" />,
		accent: "input",
	},
	{
		id: "memory",
		label: "Memory",
		icon: <Brain className="w-4 h-4" />,
		accent: "memory",
	},
	{
		id: "output",
		label: "Output",
		icon: <Sparkles className="w-4 h-4" />,
		accent: "output",
	},
	{
		id: "orchestration",
		label: "Orchestration",
		icon: <Layers className="w-4 h-4" />,
		accent: "orchestration",
	},
] as const satisfies Array<{
	id: AgentTabId;
	label: string;
	icon: React.ReactElement;
	accent: any;
}>;

const friendlyType = (type?: string) =>
	type
		? type
				.replace(/_/g, " ")
				.toLowerCase()
				.replace(/\b\w/g, (s) => s.toUpperCase())
		: "Unknown";

function KeyValueChip({
	icon,
	label,
	value,
}: {
	icon: React.ReactElement;
	label: string;
	value: string | number | null | undefined;
}) {
	return (
		<div className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-[0_12px_30px_rgba(15,23,42,0.08)]">
			<div className="rounded-xl border border-slate-200 bg-white p-2 text-orange-600">
				{icon}
			</div>
			<div>
				<div className="text-xs capitalize tracking-wide text-[color:var(--color-text-muted)]">
					{label}
				</div>
				<div className="text-sm font-semibold text-[color:var(--color-text-primary)] mt-0.5">
					{value === null || value === undefined || value === "" ? "—" : value}
				</div>
			</div>
		</div>
	);
}

function DataBlock({
	title,
	children,
}: {
	title: string;
	children: React.ReactNode;
}) {
	return (
		<section className="rounded-3xl border border-slate-200 bg-white shadow-[0_22px_56px_rgba(15,23,42,0.08)] p-6 space-y-4">
			<h3 className="text-sm font-semibold tracking-wide text-[color:var(--color-text-primary)] capitalize">
				{title}
			</h3>
			<div className="text-sm text-[color:var(--color-text-secondary)] space-y-4">
				{children}
			</div>
		</section>
	);
}

function PlaceholderBlock({ message }: { message: string }) {
	return (
		<div className="flex h-full flex-col items-center justify-center rounded-3xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center text-[color:var(--color-text-muted)]">
			<ClipboardList className="mb-4 h-8 w-8 text-orange-600" />
			<p className="text-sm">{message}</p>
		</div>
	);
}

function JsonPreview({ data }: { data: unknown }) {
	if (
		!data ||
		(typeof data === "object" &&
			Object.keys(data as Record<string, unknown>).length === 0)
	) {
		return (
			<p className="text-xs text-[color:var(--color-text-muted)]">
				No configuration provided.
			</p>
		);
	}

	const formatted =
		typeof data === "string" ? data : JSON.stringify(data, null, 2);

	return (
		<pre className="max-h-64 overflow-auto rounded-2xl border border-slate-200 bg-white p-4 text-xs leading-relaxed text-[color:var(--color-text-secondary)] shadow-[0_10px_30px_rgba(15,23,42,0.08)]">
			{formatted}
		</pre>
	);
}

export default function WorkflowTemplatePreview({
	templateId,
	templateKind = "workflow",
	agentInsertMode = false,
}: WorkflowTemplatePreviewProps) {
	const router = useRouter();
	const { showSuccess, showError, showInfo } = useToast();
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [template, setTemplate] = useState<
		WorkflowTemplateDetail | AgentTemplateDetail | null
	>(null);
	const [flowNodes, setFlowNodes] = useState<Node[]>([]);
	const [flowEdges, setFlowEdges] = useState<Edge[]>([]);
	const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
	const [activeOverviewTab, setActiveOverviewTab] =
		useState<OverviewTabId>("overview");
	const [activeAgentTab, setActiveAgentTab] = useState<AgentTabId>("core");
	const [isResizing, setIsResizing] = useState(false);
	const [panelRatio, setPanelRatio] = useState(0.6);
	const [showCloneDialog, setShowCloneDialog] = useState(false);
	const [isCloning, setIsCloning] = useState(false);
	const [justCloned, setJustCloned] = useState(false);
	const [cloneMode, setCloneMode] = useState<"workflow" | "agent">("workflow");
	const rootRef = useRef<HTMLDivElement | null>(null);
	const layoutRef = useRef<HTMLDivElement | null>(null);
	const detailsPaneRef = useRef<HTMLDivElement | null>(null);
	const isAgentMode = templateKind === "agent";
	const isAgentInsertMode = isAgentMode && agentInsertMode;

	useEffect(() => {
		let isMounted = true;
		const fetchTemplate = async () => {
			try {
				setLoading(true);
				setError(null);
				const response =
					templateKind === "agent"
						? await api.getAgentTemplate(templateId)
						: await api.getTemplate(templateId);
				if (!isMounted) return;

				const payload =
					templateKind === "agent" ? response?.agent : response?.template;

				if (response?.success && payload) {
					const detail = payload as
						| WorkflowTemplateDetail
						| AgentTemplateDetail;
					if (templateKind === "agent") {
						// eslint-disable-next-line no-console
						console.debug("[AgentPreview] Loaded agent template", {
							nodeCount: detail.node_count,
							connectionCount:
								detail.graph_definition?.definition?.connections?.length ?? 0,
						});
					}
					setTemplate(detail);

					const definition = detail.graph_definition?.definition ?? emptyGraph;
					if (templateKind === "agent") {
						const definitionConnections =
							definition.connections ?? definition.edges ?? [];
						// eslint-disable-next-line no-console
						console.debug("[AgentPreview] Definition nodes/connections", {
							nodes: (definition.nodes ?? []).length,
							connections: definitionConnections.length,
						});
					}
					const { nodes, edges } = convertGraphDefinitionToReactFlow({
						nodes: definition.nodes ?? [],
						connections: definition.connections ?? definition.edges ?? [],
						edges: definition.edges ?? [],
					});

					const defaultAgentNodeId =
						templateKind === "agent"
							? (detail as AgentTemplateDetail).primary_agent_node_id ||
								nodes.find((node) => {
									const typeValue = node.data?.type || node.type;
									return (
										typeof typeValue === "string" &&
										typeValue.toUpperCase() === "AGENT"
									);
								})?.id ||
								null
							: null;

					const previewNodes = nodes.map((node) => ({
						...node,
						selected: defaultAgentNodeId
							? node.id === defaultAgentNodeId
							: false,
						deletable: false,
						draggable: false,
						data: {
							...(node.data ?? {}),
							isReadOnlyPreview: true,
							isAgentTemplatePreview: isAgentMode,
						},
					}));

					if (isAgentMode) {
						const delegationEdgeCount = edges.filter((edge) => {
							const originalConn = (
								definition.connections ??
								definition.edges ??
								[]
							).find(
								(conn: any) =>
									(conn.source || conn.source_id) === edge.source &&
									(conn.target || conn.target_id) === edge.target &&
									(conn.connection_type || "workflow") === "delegation",
							);
							return Boolean(originalConn);
						}).length;
						// eslint-disable-next-line no-console
						console.debug("[AgentPreview] Edge debug", {
							totalEdges: edges.length,
							delegationEdgeCount,
						});
					}

					const previewEdges = edges.map((edge) => ({
						...edge,
						deletable: false,
					}));

					setFlowNodes(previewNodes);
					setFlowEdges(previewEdges);
					setSelectedNodeId(defaultAgentNodeId);
					setActiveAgentTab("core");
					setActiveOverviewTab("overview");
				} else {
					setTemplate(null);
					setFlowNodes([]);
					setFlowEdges([]);
					setSelectedNodeId(null);
					setError(
						templateKind === "agent"
							? "Agent template not found."
							: "Template not found.",
					);
				}
			} catch (err) {
				console.error("Failed to load template preview", err);
				setError(
					templateKind === "agent"
						? "Unable to load this agent template."
						: "Unable to load this workflow template.",
				);
			} finally {
				if (isMounted) {
					setLoading(false);
				}
			}
		};

		fetchTemplate();
		return () => {
			isMounted = false;
		};
	}, [templateId, templateKind]);

	const graphDefinition = useMemo<WorkflowTemplateGraphDefinition>(() => {
		return template?.graph_definition?.definition ?? emptyGraph;
	}, [template]);

	const rawGraphNodes = useMemo(() => {
		return Array.isArray(graphDefinition.nodes) ? graphDefinition.nodes : [];
	}, [graphDefinition]);

	const selectedFlowNode = useMemo(
		() => flowNodes.find((node) => node.id === selectedNodeId),
		[flowNodes, selectedNodeId],
	);

	const selectedNodeType = useMemo(() => {
		const typeValue = selectedFlowNode?.data?.type || selectedFlowNode?.type;
		return typeof typeValue === "string" ? typeValue.toUpperCase() : "";
	}, [selectedFlowNode]);

	const isAgentInspector = selectedNodeType === "AGENT";
	const showAgentInspector = Boolean(
		selectedFlowNode && (isAgentMode || isAgentInspector),
	);
	const inspectorNode = showAgentInspector ? selectedFlowNode : null;

	const handleBack = useCallback(() => {
		router.push("/library");
	}, [router]);

	const clearSelection = useCallback(() => {
		if (isAgentMode) return;
		setSelectedNodeId(null);
		setActiveOverviewTab("overview");
		setFlowNodes((prev) =>
			prev.map((node) => (node.selected ? { ...node, selected: false } : node)),
		);
	}, [isAgentMode]);

	const handleNodeClick = useCallback(
		(_event: React.MouseEvent, node: Node) => {
			const typeValue = node.data?.type || node.type;
			const upperType =
				typeof typeValue === "string" ? typeValue.toUpperCase() : "";

			if (upperType === "AGENT" || upperType === "START") {
				setSelectedNodeId(node.id);
				setActiveAgentTab("core");
				setFlowNodes((prev) =>
					prev.map((existing) => ({
						...existing,
						selected: existing.id === node.id,
					})),
				);
			} else {
				clearSelection();
			}
		},
		[clearSelection],
	);

	const handlePaneClick = useCallback(() => {
		if (isAgentMode) return;
		clearSelection();
	}, [clearSelection, isAgentMode]);

	const handleClone = useCallback(() => {
		if (!template) return;
		setCloneMode(isAgentMode ? "agent" : "workflow");
		setShowCloneDialog(true);
	}, [template, isAgentMode]);

	const handleConfirmClone = useCallback(
		async (targetName: string) => {
			if (!template) return;

			setIsCloning(true);
			setShowCloneDialog(false);

			try {
				const response =
					cloneMode === "agent"
						? await api.cloneAgentTemplate(template.id, {
								target_name: targetName,
							})
						: await api.cloneTemplate(template.id, { target_name: targetName });

				if (response.success) {
					const entityLabel =
						cloneMode === "agent" ? "agent template" : "workflow template";
					showSuccess(
						`Successfully cloned ${entityLabel} "${template.name}" as "${targetName}"!`,
					);
					showInfo("The workflow has been added to your workspace.");

					setJustCloned(true);
					setTimeout(() => setJustCloned(false), 2000);

					// Navigate to the cloned workflow
					if (response.workflow_id) {
						setTimeout(() => {
							router.push(`/workflow/${response.workflow_id}`);
						}, 1000);
					}
				} else {
					showError(
						cloneMode === "agent"
							? "Failed to clone agent template"
							: "Failed to clone workflow",
					);
				}
			} catch (error) {
				console.error("Failed to clone template:", error);
				showError(
					cloneMode === "agent"
						? "Failed to clone agent template"
						: "Failed to clone workflow",
				);
			} finally {
				setIsCloning(false);
			}
		},
		[template, cloneMode, router, showSuccess, showInfo, showError],
	);

	const handleAddAgentToWorkflow = useCallback(async () => {
		if (!template || !isAgentInsertMode || !isAgentMode) return;

		const context = getAgentTemplateInsertContext();
		if (!context?.workflowId) {
			showError(
				"No active workflow",
				"Open the workflow builder and relaunch the Agent Templates palette to add agents.",
			);
			return;
		}

		const definition = template.graph_definition?.definition;
		if (!definition) {
			showError(
				"Missing agent definition",
				"Unable to add this agent to your workflow.",
			);
			return;
		}

		try {
			setIsCloning(true);
			setShowCloneDialog(false);

			setAgentTemplateInsertPayload({
				templateId: template.id,
				templateName: template.name,
				graphDefinition: definition,
				primaryAgentNodeId: (template as AgentTemplateDetail)
					.primary_agent_node_id,
				storedAt: Date.now(),
			});

			showSuccess(
				`"${template.name}" is ready to insert`,
				"Returning to your workflow...",
			);
			router.push(context.returnPath || `/workflow/${context.workflowId}`);
		} catch (error) {
			console.error("Failed to queue agent insertion:", error);
			showError("Failed to prepare agent for insertion");
		} finally {
			setIsCloning(false);
		}
	}, [
		template,
		isAgentInsertMode,
		isAgentMode,
		showError,
		showSuccess,
		router,
	]);

	useEffect(() => {
		if (!isResizing) {
			return;
		}

		const handlePointerMove = (event: MouseEvent | TouchEvent) => {
			const container = layoutRef.current;
			if (!container) return;

			const clientX =
				event instanceof TouchEvent
					? (event.touches[0]?.clientX ?? event.changedTouches[0]?.clientX)
					: event.clientX;

			if (clientX == null) {
				return;
			}

			const { left, width } = container.getBoundingClientRect();
			const offset = clientX - left;
			const ratio = Math.min(Math.max(offset / width, 0.35), 0.75);
			setPanelRatio(ratio);
		};

		const stopResizing = () => setIsResizing(false);

		window.addEventListener("mousemove", handlePointerMove);
		window.addEventListener("touchmove", handlePointerMove);
		window.addEventListener("mouseup", stopResizing);
		window.addEventListener("touchend", stopResizing);
		window.addEventListener("touchcancel", stopResizing);

		return () => {
			window.removeEventListener("mousemove", handlePointerMove);
			window.removeEventListener("touchmove", handlePointerMove);
			window.removeEventListener("mouseup", stopResizing);
			window.removeEventListener("touchend", stopResizing);
			window.removeEventListener("touchcancel", stopResizing);
		};
	}, [isResizing]);

	const handleResizeStart = useCallback(
		(event: React.MouseEvent | React.TouchEvent) => {
			event.preventDefault();
			setIsResizing(true);
		},
		[],
	);

	useEffect(() => {
		if (typeof window === "undefined") {
			return;
		}

		const measureHeights = () => {
			window.requestAnimationFrame(() => {
				const rootEl = rootRef.current;
				const layoutEl = layoutRef.current;
				const detailsEl = detailsPaneRef.current;

				if (!rootEl || !layoutEl || !detailsEl) {
					return;
				}

				const viewportHeight = window.innerHeight;
				const rootRect = rootEl.getBoundingClientRect();
				const layoutRect = layoutEl.getBoundingClientRect();
				const detailsRect = detailsEl.getBoundingClientRect();
			});
		};

		measureHeights();

		const resizeHandler = () => measureHeights();
		window.addEventListener("resize", resizeHandler);

		const observer = new MutationObserver(measureHeights);
		if (layoutRef.current) {
			observer.observe(layoutRef.current, {
				childList: true,
				subtree: true,
				attributes: true,
			});
		}

		const intervalId = window.setInterval(measureHeights, 2000);

		return () => {
			window.removeEventListener("resize", resizeHandler);
			observer.disconnect();
			window.clearInterval(intervalId);
		};
	}, []);

	const metadataChips = useMemo(() => {
		if (!template) return [];

		// For agent templates, only show Tools and Creator
		if (isAgentMode) {
			return [
				{
					icon: <Puzzle className="w-4 h-4" />,
					label: "Tools",
					value: template.tool_count,
				},
				{
					icon: <Users className="w-4 h-4" />,
					label: "Creator",
					value: template.creator_name,
				},
			];
		}

		// For workflow templates, show all metadata
		const chips = [
			{
				icon: <BookOpen className="w-4 h-4" />,
				label: "Category",
				value: template.category,
			},
			{
				icon: <BadgeCheck className="w-4 h-4" />,
				label: "Complexity",
				value: template.complexity
					? template.complexity.charAt(0).toUpperCase() +
						template.complexity.slice(1)
					: "Unspecified",
			},
			{
				icon: <Layers className="w-4 h-4" />,
				label: "Nodes",
				value: template.node_count,
			},
			{
				icon: <Bot className="w-4 h-4" />,
				label: "Agents",
				value: template.agent_count,
			},
			{
				icon: <Puzzle className="w-4 h-4" />,
				label: "Tools",
				value: template.tool_count,
			},
			{
				icon: <Users className="w-4 h-4" />,
				label: "Creator",
				value: template.creator_name,
			},
		];
		if ("primary_agent_label" in template && template.primary_agent_label) {
			chips.unshift({
				icon: <Bot className="w-4 h-4" />,
				label: "Primary Agent",
				value: template.primary_agent_label,
			});
		}
		return chips;
	}, [template, isAgentMode]);

	if (loading) {
		return (
			<div className="flex flex-1 items-center justify-center bg-white">
				<div className="flex flex-col items-center gap-4 text-[color:var(--color-text-muted)]">
					<Loader2 className="w-8 h-8 animate-spin text-orange-600" />
					<span className="text-sm tracking-wide capitalize">
						{isAgentMode
							? "Loading agent template..."
							: "Loading workflow template..."}
					</span>
				</div>
			</div>
		);
	}

	if (error || !template) {
		return (
			<div className="flex flex-1 flex-col items-center justify-center space-y-3 bg-white text-center">
				<div className="rounded-full border border-red-300 bg-white p-4 text-red-600">
					<Cpu className="w-6 h-6" />
				</div>
				<h2 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
					Preview unavailable
				</h2>
				<p className="text-sm text-[color:var(--color-text-muted)]">
					{error || "This template could not be loaded."}
				</p>
				<button
					onClick={handleBack}
					className="mt-4 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-[color:var(--color-text-secondary)] transition-colors hover:border-orange-400 hover:text-slate-900"
				>
					<ArrowLeft className="w-4 h-4" />
					Back to Library
				</button>
			</div>
		);
	}

	const overviewTabConfig = overviewTabs.map((tab) => ({
		id: tab.id,
		label: tab.label,
		icon: tab.icon,
		accent: tab.accent,
	}));

	const agentTabConfig = agentTabs.map((tab) => ({
		id: tab.id,
		label: tab.label,
		icon: tab.icon,
		accent: tab.accent,
	}));

	const agentData = inspectorNode?.data ?? {};
	const agentConfig = agentData.agent_config ?? {};
	const llmConfig = agentConfig.llm_config ?? {};
	const memoryConfig = agentConfig;
	const structuredOutputs = agentConfig.structured_outputs ?? [];
	const orchestratorMode = agentConfig.orchestrator_mode ?? "supervisor";
	const delegatedAgents = agentConfig.delegated_agents ?? [];

	const descriptionMarkdown =
		template.description || "*No description provided.*";
	const shouldShowDescription = !isAgentMode && !selectedNodeId;
	const previewTitle = isAgentMode ? "Agent Preview" : "Workflow Preview";
	const badgeText = isAgentMode ? "Agent Template" : "Workflow Template";
	const cloneButtonLabel = isAgentMode ? "Clone as Workflow" : "Clone Workflow";
	const primaryButtonLabel = isAgentInsertMode
		? "Add to Workflow"
		: cloneButtonLabel;
	const primaryButtonWorkingLabel = isAgentInsertMode
		? "Adding..."
		: "Cloning...";
	const primaryButtonCompleteLabel = isAgentInsertMode ? "Added!" : "Cloned!";
	const PrimaryActionIcon = isAgentInsertMode ? Bot : Copy;
	const shouldShowInspector = isAgentMode || Boolean(selectedNodeId);

	return (
		<div
			ref={rootRef}
			className="flex flex-1 flex-col overflow-hidden bg-white"
		>
			<div className="border-b border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_70%,#f59e0b_185%)] px-6 py-4">
				<div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
					<div className="flex items-center gap-3">
						<button
							onClick={handleBack}
							className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-[color:var(--color-text-secondary)] transition-colors hover:border-orange-400 hover:text-slate-900"
						>
							<ArrowLeft className="w-4 h-4" />
							Back to Library
						</button>
						<div>
							<div className="flex items-center gap-2">
								<h1 className="text-xl font-semibold text-[color:var(--color-text-primary)]">
									{template.name}
								</h1>
								<span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[12px] font-semibold capitalize tracking-wide text-orange-700">
									{badgeText}
								</span>
							</div>
							<p className="text-sm text-[color:var(--color-text-muted)]">
								Version {template.version} • Used {template.usage_count} times
							</p>
						</div>
					</div>

					<div className="flex flex-wrap items-center gap-3">
						{metadataChips.map((chip) => (
							<div
								key={chip.label}
								className="flex items-center gap-2.5 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm text-[color:var(--color-text-secondary)] shadow-[0_4px_12px_rgba(15,23,42,0.08)] transition-colors hover:border-orange-400"
							>
								<span className="text-orange-600">
									{chip.icon}
								</span>
								<span className="capitalize tracking-wide text-xs text-[color:var(--color-text-muted)]">
									{chip.label}
								</span>
								<span className="font-semibold text-[color:var(--color-text-primary)]">{chip.value}</span>
							</div>
						))}

						<button
							onClick={
								isAgentInsertMode ? handleAddAgentToWorkflow : handleClone
							}
							disabled={isCloning || justCloned}
							className={`flex items-center justify-center gap-2 rounded-full px-5 py-2.5 font-semibold text-sm transition-all shadow-[0_12px_30px_rgba(15,23,42,0.12)] disabled:cursor-not-allowed ${
								justCloned
									? "bg-[#0DA931] text-white border-2 border-[#0DA931]"
									: "bg-orange-500 border-2 border-orange-500 hover:bg-orange-600 hover:border-orange-600 disabled:opacity-40"
							}`}
							style={{
								color: justCloned ? undefined : "var(--button-primary-text)",
							}}
							aria-label={`${primaryButtonLabel} ${template.name}`}
						>
							{isCloning ? (
								<>
									<div
										className="w-4 h-4 border-2 border-slate-200 border-t-orange-500 rounded-full animate-spin"
										style={{
											borderColor: "var(--button-primary-text)",
											borderTopColor: "transparent",
										}}
									></div>
									<span>{primaryButtonWorkingLabel}</span>
								</>
							) : justCloned ? (
								<>
									<Check className="w-4 h-4" />
									<span>{primaryButtonCompleteLabel}</span>
								</>
							) : (
								<>
									<PrimaryActionIcon className="w-4 h-4" />
									<span>{primaryButtonLabel}</span>
								</>
							)}
						</button>
					</div>
				</div>
			</div>

			{/* Workflow Description Section */}
			{shouldShowDescription && (
				<div className="border-b border-slate-200 bg-white px-8 py-6">
					<div className="max-w-screen-2xl mx-auto">
						<div className="rounded-2xl border border-slate-200 bg-white shadow-[0_20px_55px_rgba(15,23,42,0.08)] p-6">
							<h3 className="text-sm font-semibold tracking-wide text-[color:var(--color-text-primary)] capitalize mb-4">
								About This Workflow
							</h3>
							<div className="text-sm text-[color:var(--color-text-secondary)] prose max-w-none">
								<SimpleMarkdown content={descriptionMarkdown} />
							</div>
						</div>
					</div>
				</div>
			)}

			<div
				ref={layoutRef}
				className="flex flex-1 min-h-0 flex-col overflow-hidden xl:flex-row"
			>
				<div
					className="relative flex h-[420px] flex-auto overflow-hidden bg-white xl:h-auto xl:flex-none"
					style={{
						flexBasis: shouldShowInspector ? `${panelRatio * 100}%` : "100%",
						minWidth: 0,
					}}
				>
					<div className="relative flex-1 p-6 flex flex-col">
						<div className="flex items-center justify-center py-3 mb-2">
							<h2 className="text-xl font-bold tracking-wider capitalize text-orange-600 text-center">
								{previewTitle}
							</h2>
						</div>
						<div className="flex-1 overflow-hidden rounded-[32px] border border-slate-200 bg-white shadow-[0_24px_65px_rgba(15,23,42,0.11)]">
							<GraphCanvas
								nodes={flowNodes}
								edges={flowEdges}
								nodeTypes={builderNodeTypes}
								edgeTypes={builderEdgeTypes}
								defaultEdgeOptions={defaultSmoothEdgeOptions}
								isReadOnly
								fitView
								fitViewOptions={{ padding: 0.18 }}
								minZoom={0.2}
								maxZoom={1.75}
								nodesDraggable={false}
								nodesConnectable={false}
								elementsSelectable
								selectionOnDrag={false}
								deleteKeyCode={null}
								onNodeClick={handleNodeClick}
								onPaneClick={isAgentMode ? undefined : handlePaneClick}
								flowExtras={
									<>
										<Background gap={12} size={1} color="#4B5563" />
										<CustomMinimap
											className="!bg-white/90 !border !border-slate-200 !rounded-xl !shadow-2xl"
											maskColor="rgba(10,12,22,0.75)"
											maskStrokeColor="rgba(var(--color-primary-rgb), 0.5)"
											maskStrokeWidth={2}
											nodeBorderRadius={4}
											width={200}
											height={150}
										/>
										<CustomZoomControls position="panel" />
									</>
								}
							/>
						</div>
					</div>
				</div>

				{shouldShowInspector && (
					<>
						<div
							className="hidden select-none xl:block"
							onMouseDown={handleResizeStart}
							onTouchStart={handleResizeStart}
						>
							<div
								className={clsx(
									"relative h-full w-[3px] rounded-full border-l-2 border-slate-200 bg-slate-200 transition-colors hover:border-orange-400 hover:bg-orange-500",
									isResizing && "bg-orange-500",
								)}
							>
								<div className="absolute inset-y-0 -left-3 w-8 cursor-col-resize" />
							</div>
						</div>

						<aside
							ref={detailsPaneRef}
							className="relative flex min-h-0 w-full flex-auto flex-col border-t border-slate-200 bg-white xl:flex-none xl:border-t-0 xl:border-l"
							style={{ flexBasis: `${(1 - panelRatio) * 100}%`, minWidth: 0 }}
						>
							<div className="flex h-full min-h-0 flex-col">
								<div className="border-b border-slate-200 px-6 py-5">
									<div className="flex items-start justify-between gap-4">
										<div className="flex-1">
											{showAgentInspector && inspectorNode ? (
												<div className="space-y-1.5">
													<div className="flex items-center gap-2">
														<span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold capitalize tracking-wide text-orange-700">
															Agent Node
														</span>
														<span className="text-xs text-[color:var(--color-text-muted)]">
															#{inspectorNode.id}
														</span>
													</div>
													<h2 className="text-xl font-semibold text-[color:var(--color-text-primary)]">
														{inspectorNode.data?.name || "Unnamed Agent"}
													</h2>
													<p className="text-xs capitalize tracking-wide text-[color:var(--color-text-muted)]">
														{llmConfig.provider
															? `${llmConfig.provider} • ${llmConfig.model_name || llmConfig.model}`
															: "Model configuration pending"}
													</p>
												</div>
											) : !isAgentMode ? (
												<div className="space-y-1.5">
													<div className="flex items-center gap-2">
														<span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold capitalize tracking-wide text-[color:var(--color-text-muted)]">
															Workflow Overview
														</span>
														<span className="text-xs text-[color:var(--color-text-muted)]">
															Tap any agent node to inspect configuration
														</span>
													</div>
													<h2 className="text-xl font-semibold text-[color:var(--color-text-primary)]">
														{template.name}
													</h2>
													<p className="text-xs capitalize tracking-wide text-[color:var(--color-text-muted)]">
														Created by {template.creator_name}
													</p>
												</div>
											) : (
												<div className="space-y-1.5">
													<div className="flex items-center gap-2">
														<span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold capitalize tracking-wide text-orange-700">
															Agent Preview
														</span>
													</div>
													<h2 className="text-xl font-semibold text-[color:var(--color-text-primary)]">
														Agent Details
													</h2>
													<p className="text-xs capitalize tracking-wide text-[color:var(--color-text-muted)]">
														Select an agent node in the canvas to inspect its
														configuration.
													</p>
												</div>
											)}
										</div>
										{!isAgentMode && (
											<button
												onClick={clearSelection}
												className="flex-shrink-0 p-2 rounded-lg hover:bg-white transition-colors text-[color:var(--color-text-muted)] hover:text-slate-900"
												aria-label="Close details panel"
											>
												<X className="w-5 h-5" />
											</button>
										)}
									</div>
								</div>

								<div className="border-b border-slate-200 px-4 py-4">
									{showAgentInspector ? (
										<TabBar
											tabs={agentTabConfig}
											activeTab={activeAgentTab}
											onChange={(tabId) =>
												setActiveAgentTab(tabId as AgentTabId)
											}
											size="sm"
											equalWidth={false}
											variant="subtle"
											className="overflow-x-auto"
										/>
									) : (
										!isAgentMode && (
											<TabBar
												tabs={overviewTabConfig}
												activeTab={activeOverviewTab}
												onChange={(tabId) =>
													setActiveOverviewTab(tabId as OverviewTabId)
												}
												size="sm"
												equalWidth={false}
												variant="subtle"
												className="overflow-x-auto"
											/>
										)
									)}
								</div>

								<div className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
									{showAgentInspector && inspectorNode ? (
										<>
											{activeAgentTab === "core" && (
												<DataBlock title="System Prompt">
													<SimpleMarkdown
														content={
															agentConfig.system_prompt ||
															agentData.prompt ||
															"*No system prompt configured.*"
														}
													/>
												</DataBlock>
											)}

											{activeAgentTab === "input" && (
												<>
													<DataBlock title="Input Source Configuration">
														<JsonPreview data={agentData.input_source_config} />
													</DataBlock>
													<DataBlock title="Input Schema">
														<JsonPreview data={agentConfig.input_schema} />
													</DataBlock>
													<DataBlock title="Context Variables">
														<JsonPreview data={agentConfig.context_vars} />
													</DataBlock>
												</>
											)}

											{activeAgentTab === "memory" && (
												<>
													<DataBlock title="Memory Settings">
														<div className="grid grid-cols-1 gap-3">
															<KeyValueChip
																icon={<Brain className="w-3.5 h-3.5" />}
																label="Memory Enabled"
																value={
																	memoryConfig.memory_enabled
																		? "Enabled"
																		: "Disabled"
																}
															/>
															<KeyValueChip
																icon={<Timer className="w-3.5 h-3.5" />}
																label="Window Size"
																value={memoryConfig.memory_window_size ?? "N/A"}
															/>
															<KeyValueChip
																icon={<Layers className="w-3.5 h-3.5" />}
																label="Strategy"
																value={
																	memoryConfig.memory_strategy ||
																	"Thread scoped"
																}
															/>
														</div>
														<JsonPreview data={memoryConfig.memory_settings} />
													</DataBlock>
												</>
											)}

											{activeAgentTab === "output" && (
												<>
													<DataBlock title="Structured Outputs">
														{Array.isArray(structuredOutputs) &&
														structuredOutputs.length > 0 ? (
															<StructuredOutputViewer
																schemas={structuredOutputs}
															/>
														) : (
															<p className="text-xs text-[color:var(--color-text-muted)]">
																No structured output schema defined for this
																agent.
															</p>
														)}
													</DataBlock>
													<DataBlock title="Post Processing">
														<JsonPreview
															data={agentConfig.post_processing_rules}
														/>
													</DataBlock>
												</>
											)}

											{activeAgentTab === "orchestration" && (
												<>
													<DataBlock title="Delegation & Orchestration">
														<div className="grid grid-cols-1 gap-3">
															<KeyValueChip
																icon={<Share2 className="w-3.5 h-3.5" />}
																label="Orchestrator Mode"
																value={
																	agentConfig.is_orchestrator
																		? orchestratorMode
																		: "Not an orchestrator"
																}
															/>
															<KeyValueChip
																icon={<Users className="w-3.5 h-3.5" />}
																label="Delegated Agents"
																value={
																	delegatedAgents.length > 0
																		? delegatedAgents.length
																		: "None"
																}
															/>
														</div>
														{delegatedAgents.length > 0 && (
															<div className="space-y-3">
																<div className="text-xs capitalize tracking-wide text-[color:var(--color-text-muted)]">
																	Delegated Agents
																</div>
																<div className="space-y-2">
																	{delegatedAgents.map((agentId: string) => (
																		<div
																			key={agentId}
																			className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs text-[color:var(--color-text-secondary)]"
																		>
																			{agentId}
																		</div>
																	))}
																</div>
															</div>
														)}
														<JsonPreview data={agentConfig.routing_rules} />
													</DataBlock>
												</>
											)}
										</>
									) : !isAgentMode ? (
										<>
											{activeOverviewTab === "overview" && (
												<>
													<DataBlock title="Workflow Description">
														<SimpleMarkdown content={descriptionMarkdown} />
													</DataBlock>
												</>
											)}

											{activeOverviewTab === "input_example" && (
												<PlaceholderBlock message="Input samples are coming soon for this template." />
											)}

											{activeOverviewTab === "output_example" && (
												<PlaceholderBlock message="Output exemplars will be available shortly." />
											)}
										</>
									) : (
										<div className="flex h-full items-center justify-center text-sm text-[color:var(--color-text-muted)]">
											Select an agent node in the preview to inspect its
											configuration.
										</div>
									)}
								</div>
							</div>
						</aside>
					</>
				)}
			</div>

			<CloneWorkflowDialog
				isOpen={showCloneDialog}
				templateName={template?.name ?? null}
				templateId={template?.id ?? null}
				onConfirm={handleConfirmClone}
				onCancel={() => setShowCloneDialog(false)}
			/>
		</div>
	);
}
