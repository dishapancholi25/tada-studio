"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
	Background,
	type Connection,
	type Edge,
	type Node,
	type NodeChange,
	type ReactFlowInstance,
	useEdgesState,
	useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import KeyboardShortcutsDialog from "@/components/dialogs/KeyboardShortcutsDialog";
import PublishAgentDialog from "@/components/library/PublishAgentDialog";
import { ConflictResolutionDialog } from "@/components/ui/ConflictResolutionDialog";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { useGraph } from "@/contexts/GraphContext";
import { useLoadingOverlay } from "@/contexts/LoadingOverlayContext";
import { useNotification } from "@/contexts/NotificationContext";
import type {
	AgentTemplateInsertContext,
	AgentTemplateInsertPayload,
} from "@/lib/agentTemplateInsertion";
import {
	clearAgentTemplateInsertContext,
	clearAgentTemplateInsertPayload,
	getAgentTemplateInsertContext,
	getAgentTemplateInsertPayload,
	setAgentTemplateInsertContext,
} from "@/lib/agentTemplateInsertion";
import { api, type CreateNodeRequest } from "@/lib/api";
import { getLayoutedElements } from "@/lib/autoLayout";
import { isEndNode, isStartNode } from "@/lib/nodeTypeUtils";
import {
	type ExternalServiceForNode,
	type McpServerInfo,
	userSettingsAPI,
} from "@/lib/user-settings-api";
import { syncService } from "@/services/graphSyncService";
import { useGraphStore } from "@/stores/graphStore";
import { type GraphExecution, NodeExecution } from "@/types/api";
import CustomConnectionLine from "../edges/CustomConnectionLine";
import ExecutionPanelFinal from "../panels/execution/ExecutionPanelFinal";
import ResultDrawer from "../panels/result/ResultDrawer";
import CustomMinimap from "../ui/CustomMinimap";
import CustomZoomControls from "../ui/CustomZoomControls";
import DuplicateWorkflowModal from "../ui/DuplicateWorkflowModal";
import AgentBuilderModals from "./AgentBuilderModals";
import AgentBuilderStatusOverlays from "./AgentBuilderStatusOverlays";
import CanvasTopBar from "./CanvasTopBar";
import EvaluateModePanel from "./EvaluateModePanel";
import GraphCanvasOverlays from "./GraphCanvasOverlays";
import type { WorkflowTemplate } from "./shared/TemplateSuggestionsPanel";
import { defaultSmoothEdgeOptions } from "./shared/defaultEdgeOptions";
import {
	createOnEdgesChangeHandler,
	createOnNodesChangeHandler,
} from "./shared/editModeHandlers";
import GraphCanvas from "./shared/GraphCanvas";
import { createGraphContextAdapter } from "./shared/graphContextAdapter";
import { builderEdgeTypes, builderNodeTypes } from "./shared/nodeRegistry";
import { useGraphHistory } from "./shared/useGraphHistory";
import { usePropertyPanels } from "./shared/usePropertyPanels";
import { useSelectionPanels } from "./shared/useSelectionPanels";
import { useTutorial } from "@/tutorial/TutorialContext";
import { useCollaboration } from "@/hooks/useCollaboration";
import { CollaborationOverlay } from "@/components/collaboration/CollaborationOverlay";
import { useAuth } from "@/contexts/AuthContext";
import { useAccessRequests } from "@/contexts/AccessRequestContext";

const initialNodes: Node[] = [];
const initialEdges: Edge[] = [];

// Helper function to get provider-specific defaults for MCP servers
function getProviderDefaults(provider: string): Record<string, any> {
	switch (provider) {
		case "github":
			return {
				connection_type: "http",
				server_url: "https://api.githubcopilot.com/mcp",
				auth_type: "bearer",
				timeout_seconds: 30,
				max_retries: 3,
				retry_delay: 1.0,
				description: "GitHub Copilot MCP Server for repository access",
			};
		case "notion":
			return {
				connection_type: "http",
				server_url: "https://mcp.notion.com/mcp",
				auth_type: "oauth",
				auth_config: { provider: "notion" },
				timeout_seconds: 60,
				max_retries: 3,
				retry_delay: 2.0,
				description: "Notion MCP Server for workspace access",
			};
		case "atlassian":
			return {
				connection_type: "http",
				server_url: "https://mcp.atlassian.com/v1/mcp",
				auth_type: "mcp_oauth",
				timeout_seconds: 60,
				max_retries: 3,
				retry_delay: 2.0,
				description: "Atlassian MCP Server for Jira, Confluence, and Bitbucket",
			};
		case "databricks":
			return {
				connection_type: "http",
				server_url: "",
				auth_type: "bearer",
				timeout_seconds: 60,
				max_retries: 3,
				retry_delay: 2.0,
				description: "Databricks Catalog MCP Server for Unity Catalog functions",
			};
		case "databricks_devops":
			return {
				connection_type: "stdio",
				command: "python",
				args: ["-m", "backend.tools.databricks_devops_mcp"],
				auth_type: "custom",
				timeout_seconds: 60,
				max_retries: 3,
				retry_delay: 2.0,
				description:
					"Databricks workspace & Azure DevOps notebook management",
			};
		case "sharepoint":
			return {
				connection_type: "stdio",
				command: "python",
				args: ["-m", "backend.tools.sharepoint_mcp"],
				auth_type: "none",
				timeout_seconds: 60,
				max_retries: 3,
				retry_delay: 2.0,
				description:
					"SharePoint MCP Server for document library and site access",
			};
		case "fabric":
			return {
				connection_type: "stdio",
				command: "python",
				args: ["-m", "backend.tools.fabric_mcp"],
				auth_type: "oauth",
				auth_config: { provider: "fabric" },
				timeout_seconds: 60,
				max_retries: 3,
				retry_delay: 2.0,
				description:
					"Microsoft Fabric MCP Server for workspaces, lakehouses, notebooks, and pipelines",
			};
		default:
			return {
				connection_type: "stdio",
				auth_type: "none",
				timeout_seconds: 30,
				max_retries: 3,
				retry_delay: 1.0,
				description: "",
			};
	}
}

interface AgentBuilderProps {
	onAddToLibrary?: () => void;
	onVersionHistory?: () => void;
}

export default function AgentBuilder({ onAddToLibrary, onVersionHistory }: AgentBuilderProps) {
	// PHASE 4B: Use store directly instead of going through Context
	// This eliminates the final layer of state duplication
	const storeNodes = useGraphStore((state) => state.nodes);
	const storeEdges = useGraphStore((state) => state.edges);
	const storeSetNodes = useGraphStore((state) => state.setNodes);
	const storeSetEdges = useGraphStore((state) => state.setEdges);
	const router = useRouter();
	const { user } = useAuth();
	const { requestAccess } = useAccessRequests();

	// Still use Context for API operations (these don't cause re-renders)
	const {
		currentGraph,
		graphs,
		createNode,
		updateNode,
		deleteNode: deleteNodeApi,
		createConnection,
		deleteConnection,
		createGraph,
		deleteGraph,
		exportGraph,
		exportGraphPython,
		loadGraph,
		loadGraphByWorkflowId,
		reloadGraph,
		saveGraph,
		clearGraph,
		createSubAgent,
		loading,
		error,
	} = useGraph();

	const { showSuccess, showError, showInfo } = useNotification();
	const { withOverlay } = useLoadingOverlay();

	// React 19: Use transition for expensive operations like auto-layout
	const [isLayoutPending, startLayoutTransition] = useTransition();

	const [reactFlowNodes, setReactFlowNodes, onNodesChange] =
		useNodesState(initialNodes);
	const [reactFlowEdges, setReactFlowEdges, onEdgesChange] =
		useEdgesState(initialEdges);
	const selectionPanels = useSelectionPanels();
	const { selectionMap, openPanel, closePanel, resetPanels, isAnyPanelOpen } =
		selectionPanels;

	useEffect(() => {
		window.dispatchEvent(
			new CustomEvent("workflowCanvasPropertyPanelOpen", {
				detail: { open: isAnyPanelOpen },
			}),
		);
	}, [isAnyPanelOpen]);

	useEffect(() => {
		return () => {
			window.dispatchEvent(
				new CustomEvent("workflowCanvasPropertyPanelOpen", {
					detail: { open: false },
				}),
			);
		};
	}, []);

	const { isRunning: isTutorialRunning } = useTutorial();

	// Real-time collaboration
	const {
		isConnected: isCollabConnected,
		isReadOnly: isCollabReadOnly,
		users: collabUsers,
		syncNodes,
		syncEdges,
		updateCursor,
	} = useCollaboration({
		roomId: currentGraph?.workflow_id || "",
		userName: user?.email || user?.name || "Anonymous",
		userRole: currentGraph?.workflow_role || "viewer",
		enabled:
			!!currentGraph?.workflow_id &&
			(currentGraph.workflow_role === "owner" ||
				currentGraph.workflow_role === "editor"),
	});

	const [publishAgentDialog, setPublishAgentDialog] = useState<{
		isOpen: boolean;
		agentNodeId: string | null;
		agentName: string | null;
		agentDescription: string | null;
	}>({ isOpen: false, agentNodeId: null, agentName: null, agentDescription: null });
	const [isPublishingAgent, setIsPublishingAgent] = useState(false);
	const [showDuplicateModal, setShowDuplicateModal] = useState(false);
	const [isDuplicating, setIsDuplicating] = useState(false);

	// Create graph operations adapter
	// Uses store nodes/edges directly, semantic operations from context
	const graphOperations = useMemo(
		() =>
			createGraphContextAdapter({
				currentGraph,
				graphs,
				nodes: storeNodes,
				edges: storeEdges,
				createNode,
				updateNode,
				deleteNode: deleteNodeApi,
				createConnection,
				deleteConnection,
				createGraph,
				deleteGraph,
				exportGraph,
				loadGraph,
				reloadGraph,
				saveGraph,
				clearGraph,
				createSubAgent,
				loading,
				error,
			}),
		[
			currentGraph,
			graphs,
			storeNodes,
			storeEdges,
			createNode,
			updateNode,
			deleteNodeApi,
			createConnection,
			deleteConnection,
			createGraph,
			deleteGraph,
			exportGraph,
			loadGraph,
			reloadGraph,
			saveGraph,
			clearGraph,
			createSubAgent,
			loading,
			error,
		],
	);

	// All selected nodes are now handled by the shared usePropertyPanels hook
	const [nodeCounter, setNodeCounter] = useState(1);
	const [showExecutionPanel, setShowExecutionPanel] = useState(false);

	// Tavily config for auto-populating web search nodes
	const [tavilyConfig, setTavilyConfig] =
		useState<ExternalServiceForNode | null>(null);

	// Fetch Tavily config on mount
	useEffect(() => {
		const fetchTavilyConfig = async () => {
			try {
				const config = await userSettingsAPI.getTavilyConfigForNode();
				setTavilyConfig(config);
			} catch (error) {
				console.error("Failed to fetch Tavily config:", error);
			}
		};
		fetchTavilyConfig();
	}, []);
	const [executingNodeId, setExecutingNodeId] = useState<string | null>(null);
	const [mode, setMode] = useState<"edit" | "evaluate" | "execution">("edit");
	const [nodeEvalScores, setNodeEvalScores] = useState<Record<string, number>>({});
	const [isExecuting, setIsExecuting] = useState(false);
	const [executionValidationHint, setExecutionValidationHint] = useState<
		string | null
	>(null);
	const [createSubAgentDialog, setCreateSubAgentDialog] = useState<{
		isOpen: boolean;
		parentAgentId: string;
		parentAgentName: string;
	}>({ isOpen: false, parentAgentId: "", parentAgentName: "" });

	const [createSubWorkflowDialog, setCreateSubWorkflowDialog] = useState<{
		isOpen: boolean;
		parentAgentId: string;
		parentAgentName: string;
	}>({ isOpen: false, parentAgentId: "", parentAgentName: "" });
	const [createToolNodeDialog, setCreateToolNodeDialog] = useState<{
		isOpen: boolean;
		parentAgentId: string;
		parentAgentName: string;
	}>({ isOpen: false, parentAgentId: "", parentAgentName: "" });
	const [currentExecution, setCurrentExecution] =
		useState<GraphExecution | null>(null);
	const currentExecutionRef = useRef<GraphExecution | null>(null);
	const [showResultDrawer, setShowResultDrawer] = useState(false);
	// selectedExecutionNode is now handled by the shared useSelectionPanels hook

	// Use shared property panels hook
	const { renderPropertyPanels, renderExecutionPanels, isExecutionDetailOpen } = usePropertyPanels({
		graphOperations,
		selectionPanels,
		nodes: reactFlowNodes,
		edges: reactFlowEdges,
		mode,
		currentExecution,
	});
	const [showNodePalette, setShowNodePalette] = useState(false);
	const [paletteSourceNodeId, setPaletteSourceNodeId] = useState<string | null>(
		null,
	);
	const [paletteSourceBranchIndex, setPaletteSourceBranchIndex] = useState<
		number | null
	>(null);
	const [showEnhancedExecutionViewer, setShowEnhancedExecutionViewer] =
		useState(false);
	const [enhancedExecutionViewerId, setEnhancedExecutionViewerId] = useState<
		string | null
	>(null);

	// Canvas preferences (persisted to localStorage)
	const [snapToGrid, setSnapToGrid] = useState(() => {
		if (typeof window !== "undefined") {
			return localStorage.getItem("agenticstudio-snap-to-grid") === "true";
		}
		return false;
	});
	const [showMiniMap, setShowMiniMap] = useState(() => {
		if (typeof window !== "undefined") {
			const stored = localStorage.getItem("agenticstudio-show-minimap");
			return stored === null ? true : stored === "true"; // Default to true
		}
		return true;
	});

	// Persist canvas preferences
	useEffect(() => {
		localStorage.setItem("agenticstudio-snap-to-grid", String(snapToGrid));
	}, [snapToGrid]);
	useEffect(() => {
		localStorage.setItem("agenticstudio-show-minimap", String(showMiniMap));
	}, [showMiniMap]);

	// Listen for access role changes (when viewer gets promoted to editor)
	useEffect(() => {
		const handleRoleChange = async (event: CustomEvent<{ workflowId: string; newRole: string }>) => {
			const { workflowId, newRole } = event.detail;
			console.log("[AgentBuilder] Access role changed:", { workflowId, newRole, currentWorkflowId: currentGraph?.workflow_id });
			// Reload graph if this is the current workflow
			if (currentGraph?.workflow_id === workflowId) {
				console.log("[AgentBuilder] Reloading graph by workflow ID to apply new role...");
				try {
					await loadGraphByWorkflowId(workflowId);
					console.log("[AgentBuilder] Graph reloaded successfully with new role");
				} catch (err) {
					console.error("[AgentBuilder] Failed to reload graph:", err);
				}
			}
		};

		window.addEventListener("accessRoleChanged", handleRoleChange as unknown as EventListener);
		return () => {
			window.removeEventListener("accessRoleChanged", handleRoleChange as unknown as EventListener);
		};
	}, [currentGraph?.workflow_id, loadGraphByWorkflowId]);

	// Keyboard shortcuts help dialog
	const [showShortcutsHelp, setShowShortcutsHelp] = useState(false);

	// Reset graph confirmation dialog
	const [showResetConfirm, setShowResetConfirm] = useState(false);

	// Listen for '?' key to show shortcuts help
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			// Only trigger on '?' without modifier keys
			if (e.key === "?" && !e.ctrlKey && !e.altKey && !e.metaKey) {
				// Don't trigger when typing in input fields
				const activeElement = document.activeElement;
				const isInputField =
					activeElement?.tagName === "INPUT" ||
					activeElement?.tagName === "TEXTAREA" ||
					(activeElement as HTMLElement)?.isContentEditable;
				if (!isInputField) {
					e.preventDefault();
					setShowShortcutsHelp(true);
				}
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	// State for loading paused executions
	const [loadExecutionData, setLoadExecutionData] = useState<{
		executionId: string;
		threadId: string;
		dbExecutionId: string;
	} | null>(null);

	const positionUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);
	const reactFlowWrapper = useRef<HTMLDivElement>(null);
	const reactFlowInstance = useRef<ReactFlowInstance | null>(null);
	const insertingAgentTemplateRef = useRef(false);
	// Track when applying remote collaboration changes to avoid sync loops
	const applyingRemoteChangesRef = useRef(false);

	const restoreGraphFromStore = useCallback(() => {
		const { nodes: storeNodesSnapshot, edges: storeEdgesSnapshot } =
			useGraphStore.getState();

		setReactFlowNodes((prevNodes) => {
			const existingIds = new Set(prevNodes.map((node) => node.id));
			let changed = false;
			const nextNodes = [...prevNodes];

			storeNodesSnapshot.forEach((node) => {
				if (!existingIds.has(node.id)) {
					nextNodes.push({
						...node,
						data: node.data ? { ...node.data } : node.data,
					});
					changed = true;
				}
			});

			return changed ? nextNodes : prevNodes;
		});

		setReactFlowEdges((prevEdges) => {
			const existingIds = new Set(prevEdges.map((edge) => edge.id));
			let changed = false;
			const nextEdges = [...prevEdges];

			storeEdgesSnapshot.forEach((edge) => {
				if (!existingIds.has(edge.id)) {
					nextEdges.push({
						...edge,
						data: edge.data ? { ...edge.data } : edge.data,
					});
					changed = true;
				}
			});

			return changed ? nextEdges : prevEdges;
		});
	}, [setReactFlowNodes, setReactFlowEdges]);

	const hasEndNode = useMemo(
		() => storeNodes.some((node) => isEndNode(node)),
		[storeNodes],
	);

	const ensureEndNodeBeforeExecution = useCallback(() => {
		if (!hasEndNode) {
			const message =
				"Add an End node to mark where your workflow should finish before running it.";
			setExecutionValidationHint(message);
			showError("Add an End node", message);
			return false;
		}
		return true;
	}, [hasEndNode, showError]);

	const validateNodeConfigurations = useCallback(() => {
		const unconfiguredNodes: string[] = [];

		storeNodes.forEach((node) => {
			const nodeType = node.data?.type?.toUpperCase();
			const nodeName = node.data?.name || "Unnamed";

			// Check Agent nodes
			if (nodeType === "AGENT") {
				if (!node.data?.agent_config?.llm_config) {
					unconfiguredNodes.push(
						`• Agent "${nodeName}" - missing LLM configuration`,
					);
				}
			}

			// Check HTTP Request nodes
			if (nodeType === "HTTP_REQUEST") {
				if (!node.data?.http_request_config?.url_template) {
					unconfiguredNodes.push(`• HTTP Request "${nodeName}" - missing URL`);
				}
			}

			// Check Document Search nodes
			if (nodeType === "DOCUMENT_SEARCH") {
				const hasCollections =
					(node.data?.document_search_config?.document_collections?.length ||
						0) > 0;
				const hasDocuments =
					(node.data?.document_search_config?.document_ids?.length || 0) > 0;
				if (!hasCollections && !hasDocuments) {
					unconfiguredNodes.push(
						`• Document Search "${nodeName}" - no documents selected`,
					);
				}
			}

			// Check Database Query nodes
			if (nodeType === "DATABASE_QUERY") {
				if (!node.data?.database_query_config?.connection_id) {
					unconfiguredNodes.push(
						`• Database Query "${nodeName}" - missing connection`,
					);
				}
			}
		});

		if (unconfiguredNodes.length > 0) {
			const message = `Please configure the following nodes before running:\n\n${unconfiguredNodes.join("\n")}`;
			showError("Unconfigured Nodes", message);
			return false;
		}

		return true;
	}, [storeNodes, showError]);

	const handleDismissValidationHint = useCallback(() => {
		setExecutionValidationHint(null);
	}, []);

	useEffect(() => {
		if (hasEndNode && executionValidationHint) {
			setExecutionValidationHint(null);
		}
	}, [hasEndNode, executionValidationHint]);

	const { saveToHistory, handleUndo, handleRedo } = useGraphHistory({
		reactFlowNodes,
		reactFlowEdges,
		setReactFlowNodes,
		setReactFlowEdges,
		// PHASE 4B: Apply undo/redo directly to store
		applyGraphNodes: useGraphStore.getState().setNodes,
		applyGraphEdges: useGraphStore.getState().setEdges,
		showInfo,
		resetKey: currentGraph?.name,
	});

	const rawNodesChangeHandler = useMemo(
		() =>
			createOnNodesChangeHandler({
				mode,
				onNodesChange,
				saveToHistory,
				updateNodePosition: (nodeId, position) =>
					updateNode(nodeId, { position }),
				positionUpdateTimeoutRef,
			}),
		[mode, onNodesChange, saveToHistory, updateNode, positionUpdateTimeoutRef],
	);

	const handleNodesChange = useCallback(
		(changes: NodeChange[]) => {
			const storeState = useGraphStore.getState();
			let blockedStartRemoval = false;

			const filteredChanges = changes.filter((change) => {
				// Intercept position changes during Ctrl+drag to prevent React Flow's automatic update
				if (
					change.type === "position" &&
					dragStateRef.current.ctrlPressed &&
					dragStateRef.current.isDragging &&
					change.id === dragStateRef.current.draggedNodeId &&
					change.position
				) {
					// Store the position but don't apply it yet
					// We'll apply it together with children in handleNodeDrag
					dragStateRef.current.pendingPosition = change.position;
					return false; // Filter out this change
				}

				if (change.type !== "remove") {
					return true;
				}

				const node = storeState.nodes.find((n) => n.id === change.id);
				if (isStartNode(node)) {
					blockedStartRemoval = true;
					return false;
				}

				return true;
			});

			if (filteredChanges.length > 0) {
				rawNodesChangeHandler(filteredChanges);
			}

			if (blockedStartRemoval) {
				// Restore the authoritative graph with the start node intact
				restoreGraphFromStore();
			}
		},
		[rawNodesChangeHandler, restoreGraphFromStore],
	);

	const handleEdgesChange = useMemo(
		() =>
			createOnEdgesChangeHandler({
				mode,
				onEdgesChange,
				saveToHistory,
			}),
		[mode, onEdgesChange, saveToHistory],
	);

	useEffect(() => {
		if (mode !== "edit") {
			resetPanels();
		}
	}, [mode, resetPanels]);

	useEffect(() => {
		resetPanels();
	}, [currentGraph?.name, resetPanels]);

	// Track nodes that should display as running with minimum duration
	const [runningNodesCache, setRunningNodesCache] = useState<
		Record<string, number>
	>({});
	const runningNodeTimeouts = useRef<Record<string, NodeJS.Timeout>>({});

	// Cleanup timeout on unmount
	useEffect(() => {
		return () => {
			if (positionUpdateTimeoutRef.current) {
				clearTimeout(positionUpdateTimeoutRef.current);
			}
			// Clean up running node timeouts
			Object.values(runningNodeTimeouts.current).forEach((timeout) =>
				clearTimeout(timeout),
			);
		};
	}, []);

	// Clear running node state when switching graphs (memory cleanup)
	useEffect(() => {
		// Clear any lingering timeouts from previous graph
		Object.values(runningNodeTimeouts.current).forEach(clearTimeout);
		runningNodeTimeouts.current = {};
		setRunningNodesCache({});
	}, [currentGraph?.name]);

	// Keyboard shortcuts for undo/redo and copy/paste
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			// Only handle shortcuts in edit mode
			if (mode !== "edit") return;

			// Don't handle if user is typing in an input field
			const target = e.target as HTMLElement;
			if (
				target.tagName === "INPUT" ||
				target.tagName === "TEXTAREA" ||
				target.isContentEditable
			)
				return;

			// Check for Ctrl (Windows/Linux) or Cmd (Mac)
			const isModifierKey = e.ctrlKey || e.metaKey;

			// Ctrl/Cmd+Z for undo
			if (isModifierKey && e.key === "z" && !e.shiftKey) {
				e.preventDefault();
				handleUndo();
			}
			// Ctrl+Y or Ctrl/Cmd+Shift+Z for redo
			else if (
				(e.ctrlKey && e.key === "y") ||
				(isModifierKey && e.shiftKey && e.key === "z")
			) {
				e.preventDefault();
				handleRedo();
			}
			// Ctrl/Cmd+C for copy
			else if (isModifierKey && e.key === "c" && !e.shiftKey) {
				// Use reactFlowNodes (React Flow state) instead of storeNodes
				// because selection state is managed by React Flow, not the store
				const selectedNodeIds = reactFlowNodes
					.filter((n) => n.selected)
					.map((n) => n.id);

				if (selectedNodeIds.length > 0) {
					e.preventDefault();
					useGraphStore.getState().copySelectedNodes(selectedNodeIds);
					showInfo(
						"Copied",
						`${selectedNodeIds.length} node${selectedNodeIds.length > 1 ? "s" : ""} copied`,
					);
				}
			}
			// Ctrl/Cmd+V for paste
			else if (isModifierKey && e.key === "v" && !e.shiftKey) {
				const clipboard = useGraphStore.getState().clipboard;
				if (clipboard && clipboard.nodes.length > 0) {
					e.preventDefault();

					// Calculate paste position - offset from viewport center or use default
					let pasteOffset = { x: 100, y: 100 };
					if (reactFlowInstance.current) {
						const viewport = reactFlowInstance.current.getViewport();
						const bounds =
							reactFlowInstance.current.getNodes().length > 0
								? reactFlowInstance.current.getNodes()[0].position
								: { x: 0, y: 0 };
						// Place at rough center of visible area
						pasteOffset = {
							x: (-viewport.x + 400) / viewport.zoom,
							y: (-viewport.y + 300) / viewport.zoom,
						};
					}

					const { newNodes } = useGraphStore.getState().pasteNodes(pasteOffset);

					if (newNodes.length > 0) {
						showSuccess(
							"Pasted",
							`${newNodes.length} node${newNodes.length > 1 ? "s" : ""} pasted`,
						);
						saveToHistory(); // Save to undo/redo history
					}
				}
			}
			// Ctrl/Cmd+0 for fit view
			else if (isModifierKey && e.key === "0") {
				e.preventDefault();
				if (reactFlowInstance.current) {
					reactFlowInstance.current.fitView({ padding: 0.2 });
				}
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [mode, handleUndo, handleRedo, reactFlowNodes, showInfo, showSuccess, saveToHistory]);

	// Check if returning from enhanced viewer
	useEffect(() => {
		const returnData = localStorage.getItem("return-from-viewer");
		if (returnData) {
			try {
				const { graphName, showExecutionPanel: shouldShow } =
					JSON.parse(returnData);

				// Load the graph if it matches
				if (graphName && currentGraph?.name === graphName && shouldShow) {
					if (ensureEndNodeBeforeExecution()) {
						setShowExecutionPanel(true);
						setMode("execution");
					}
				}

				// Clear the flag
				localStorage.removeItem("return-from-viewer");
			} catch (error) {
				console.error("Error restoring from viewer:", error);
				localStorage.removeItem("return-from-viewer");
			}
		}
	}, [currentGraph, ensureEndNodeBeforeExecution]);

	// Keyboard shortcut for chat overlay (Cmd/Ctrl + K)

	// Add logging for mode changes
	useEffect(() => {
		// console.log('[AgentBuilder] *** MODE CHANGED ***:', mode);
	}, [mode, openPanel]);

	// Update nodes with execution state, completion status, and connection info
	useEffect(() => {
		// console.log('[AgentBuilder] === NODE UPDATE EFFECT ===');
		// console.log('[AgentBuilder] Current mode:', mode);
		// console.log('[AgentBuilder] currentExecution (state):', currentExecution);
		// console.log('[AgentBuilder] currentExecutionRef.current:', currentExecutionRef.current);
		// console.log('[AgentBuilder] executingNodeId:', executingNodeId);

		// Use ref if state is null (due to React batching)
		const executionData = currentExecution || currentExecutionRef.current;

		if (executionData) {
			// console.log('[AgentBuilder] *** HAS EXECUTION DATA *** - Updating nodes with execution data:', executionData.status, 'nodes:', executionData.node_executions?.length || 0);
			// if (executionData.node_executions) {
			//   console.log('[AgentBuilder] Node executions with FULL details:', executionData.node_executions.map(ne => ({
			//     node_id: ne.node_id,
			//     node_name: ne.node_name,
			//     status: ne.status,
			//     node_type: ne.node_type,
			//     execution_order: ne.execution_order
			//   })));
			// }
		} else {
			// console.log('[AgentBuilder] *** NO EXECUTION DATA *** - both state and ref are null/undefined');
		}

		// Build execution index once (O(m)) instead of filtering per node (O(n*m))
		const executionsByNodeId = new Map<string, NodeExecution[]>();
		if (executionData?.node_executions) {
			for (const ne of executionData.node_executions) {
				const existing = executionsByNodeId.get(ne.node_id) || [];
				existing.push(ne);
				executionsByNodeId.set(ne.node_id, existing);
			}
		}

		setReactFlowNodes((nds) => {
			// console.log('[AgentBuilder] Current React Flow nodes:', nds.map(n => ({ id: n.id, name: n.data?.name })));

			return nds.map((node) => {
				// Log detailed matching info - commented out to reduce verbosity
				// console.log(`[AgentBuilder] 🔍 Matching node:`, {
				//   nodeId: node.id,
				//   nodeName: node.data?.name,
				//   nodeType: node.type
				// });

				// Look up executions from pre-built index (O(1) instead of O(m))
				const allNodeExecutions = executionsByNodeId.get(node.id) || [];

				// DEBUG: Log multiple executions for checkpoint tracking
				if (allNodeExecutions.length > 1) {
					console.log(
						`[CHECKPOINT-RESUME-DEBUG] Node ${node.id} (${node.data?.name}) has ${allNodeExecutions.length} executions:`,
						allNodeExecutions.map((ne) => ({
							execution_order: ne.execution_order,
							status: ne.status,
							database_node_id: ne.id || (ne as any).database_node_id,
						})),
					);
				}

				// Get the latest execution (highest execution_order or last in array)
				// For checkpoint nodes with multiple executions, we need the most recent one
				const nodeExecution =
					allNodeExecutions.length > 0
						? allNodeExecutions.reduce((latest, current) => {
								// For checkpoint nodes, prefer the one with the highest database ID (most recent)
								if (node.data?.type === "CHECKPOINT") {
									// If both have database IDs, compare them
									const latestDbId =
										latest.id || (latest as any).database_node_id || "";
									const currentDbId =
										current.id || (current as any).database_node_id || "";
									if (latestDbId && currentDbId) {
										// Database IDs are UUIDs, compare them lexicographically (later = higher)
										// But actually, we should use execution_order if available
										if (
											latest.execution_order !== undefined &&
											current.execution_order !== undefined
										) {
											return current.execution_order > latest.execution_order
												? current
												: latest;
										}
										// Fall back to array position (last is most recent)
										return current;
									}
								}
								// Use execution_order if both have it (normal node executions)
								const latestOrder = latest.execution_order;
								const currentOrder = current.execution_order;
								if (
									latestOrder !== undefined &&
									currentOrder !== undefined
								) {
									return currentOrder > latestOrder
										? current
										: latest;
								}
								if (latestOrder !== undefined) return latest;
								if (currentOrder !== undefined) return current;

								// Tool call entries lack execution_order; use step (invocation_index)
								const latestStep = (latest as any).step;
								const currentStep = (current as any).step;
								if (
									latestStep !== undefined &&
									currentStep !== undefined
								) {
									return currentStep > latestStep
										? current
										: latest;
								}

								// Fallback: prefer current (later in array = more recent)
								return current;
							})
						: undefined;

				if (nodeExecution) {
					const durationDisplay =
						nodeExecution.duration_seconds !== undefined &&
						nodeExecution.duration_seconds !== null
							? `${nodeExecution.duration_seconds}s`
							: "undefined";
					// Commented out to reduce verbosity
					// console.log(`[AgentBuilder] Node ${node.id} matched with execution! Status: ${nodeExecution.status}, Duration: ${durationDisplay}`);

					// DEBUG: Special logging for checkpoint nodes
					if (node.type === "flowNode" && node.data?.type === "CHECKPOINT") {
						console.log(
							`[CHECKPOINT-STATUS-DEBUG] Checkpoint node ${node.data.name}:`,
							{
								node_id: node.id,
								node_type: node.data?.type,
								executions_count: allNodeExecutions.length,
								latest_status: nodeExecution.status,
								all_statuses: allNodeExecutions.map((ne) => ne.status),
								execution_order: nodeExecution.execution_order,
								database_node_id:
									nodeExecution.id || (nodeExecution as any).database_node_id,
								is_paused: nodeExecution.status === "paused",
								is_running: nodeExecution.status === "running",
								is_completed: nodeExecution.status === "completed",
							},
						);
					}

					// DEBUG: Log re-execution detection for Agent and Condition nodes
					if (
						(node.type === "agentNode" || node.type === "conditionNode") &&
						allNodeExecutions.length > 1
					) {
						// Sort executions by execution_order to find the correct index
						const sortedExecutions = [...allNodeExecutions].sort(
							(a, b) => (a.execution_order ?? 0) - (b.execution_order ?? 0),
						);
						const executionIndex = sortedExecutions.findIndex(
							(e) => e.id === nodeExecution.id,
						);
						console.log(
							`[RE-EXECUTION-DEBUG] ${node.data?.name} is on execution #${executionIndex + 1}/${allNodeExecutions.length}, status: ${nodeExecution.status}`,
						);
					}
				} else if (
					executionData?.node_executions?.length &&
					executionData.node_executions.length > 0
				) {
					// console.log(`[AgentBuilder] Node ${node.id} (${node.data?.name}) - no matching execution found in ${executionData.node_executions.length} available executions`);
				}

				// Determine if this node is currently executing
				const isCurrentlyExecuting = node.id === executingNodeId;

				// Determine execution status - prioritize node execution status over current executing
				let executionStatus = nodeExecution?.status;

				// Check if ANY execution for this node is currently running (handles
				// rapid successive tool calls where the reduce may pick a completed entry)
				const hasAnyRunningExecution = allNodeExecutions.some(
					(ne) => ne.status === "running",
				);

				// Count completed tool calls for badge display on tool nodes
				const completedToolCallCount = allNodeExecutions.filter(
					(ne) => ne.status === "completed",
				).length;

				// Override executionStatus if any execution is still running but
				// the reduce picked a completed/failed one
				if (hasAnyRunningExecution && executionStatus !== "running") {
					executionStatus = "running";
				}

				// DEBUG: Track visual state transitions for re-executing nodes
				if (
					(node.type === "agentNode" || node.type === "conditionNode") &&
					allNodeExecutions.length > 1
				) {
					const previousExecution =
						allNodeExecutions[allNodeExecutions.length - 2];
					if (
						previousExecution &&
						previousExecution.status === "completed" &&
						nodeExecution?.status === "running"
					) {
						console.log(
							`[VISUAL-STATE-TRANSITION] ${node.data?.name} transitioning from completed → running (re-execution after checkpoint)`,
							{
								node_id: node.id,
								previous_status: previousExecution.status,
								current_status: nodeExecution.status,
								previous_db_id: previousExecution.id,
								current_db_id: nodeExecution.id,
							},
						);
					}
				}

				// Debug sub-agent status
				if (nodeExecution?.is_sub_agent) {
					console.log(
						`[AgentBuilder] Sub-agent ${node.id} (${node.data?.name}) status from execution data:`,
						{
							status: nodeExecution.status,
							duration: nodeExecution.duration_seconds,
							is_sub_agent: nodeExecution.is_sub_agent,
							parent_agent_id: nodeExecution.parent_agent_id,
						},
					);
				}

				// If node is currently executing but has no status yet, mark as 'running'
				if (isCurrentlyExecuting && !executionStatus) {
					executionStatus = "running";
				}

				// Check if this is a sub-agent from node execution data
				const isSubAgent =
					node.data?.isSubAgent || nodeExecution?.is_sub_agent || false;

				// For sub-agents, they should show as executing if their status is 'running'
				// regardless of whether they are the current node
				// Paused nodes should not show as executing (they're waiting)
				const isExecuting =
					executionStatus === "running" ||
					hasAnyRunningExecution ||
					(isCurrentlyExecuting &&
						executionStatus !== "completed" &&
						executionStatus !== "failed" &&
						executionStatus !== "paused") ||
					node.id in runningNodesCache; // Check cache for minimum display duration

				// Verbose logging for debugging
				if (nodeExecution || isCurrentlyExecuting) {
					const visualState = {
						isSubAgent,
						executionStatus,
						isCurrentlyExecuting,
						isInCache: node.id in runningNodesCache,
						isExecuting,
						dbStatus: nodeExecution?.status,
						timestamp: new Date().toISOString(),
					};

					// Commented out general visual state log to reduce verbosity
					// console.log(`[AgentBuilder] Node ${node.id} (${node.data?.name}) visual state:`, visualState);

					// DEBUG: Special tracking for re-executing nodes
					if (
						(node.type === "agentNode" || node.type === "conditionNode") &&
						allNodeExecutions.length > 1
					) {
						const willPulse = isExecuting;
						const willShowGreen =
							executionStatus === "completed" && !isExecuting;
						const willShowYellow = isExecuting || node.id in runningNodesCache;

						console.log(
							`[VISUAL-STATE-DEBUG] ${node.data?.name} visual indicators:`,
							{
								node_id: node.id,
								execution_count: allNodeExecutions.length,
								current_status: executionStatus,
								will_pulse: willPulse,
								will_show_green: willShowGreen,
								will_show_yellow: willShowYellow,
								is_latest_execution:
									nodeExecution ===
									allNodeExecutions[allNodeExecutions.length - 1],
								database_node_id: nodeExecution?.id,
							},
						);
					}
				}

				// When a node starts running, add it to the cache
				if (executionStatus === "running" && !(node.id in runningNodesCache)) {
					// console.log(`[AgentBuilder] Adding node ${node.id} (${node.data?.name}) to running cache - will show plum accent for min 2s`);
					setRunningNodesCache((prev) => ({ ...prev, [node.id]: Date.now() }));

					// Set a timeout to remove it after minimum duration (2 seconds)
					if (runningNodeTimeouts.current[node.id]) {
						clearTimeout(runningNodeTimeouts.current[node.id]);
					}
					runningNodeTimeouts.current[node.id] = setTimeout(() => {
						setRunningNodesCache((prev) => {
							const newCache = { ...prev };
							delete newCache[node.id];
							return newCache;
						});
						delete runningNodeTimeouts.current[node.id];
						// console.log(`[AgentBuilder] Removed ${node.id} (${node.data?.name}) from running cache after minimum duration`);
					}, 2000); // 2 second minimum display time
				}

				const finalData = {
					...node.data,
					isExecuting: isExecuting,
					executionStatus: executionStatus,
					executionDuration: nodeExecution?.duration_seconds,
					// Ensure sub-agent flag is preserved
					isSubAgent: isSubAgent,
					// Tool call count for badge display on tool nodes
					toolCallCount: completedToolCallCount,
				};

				if (
					isCurrentlyExecuting ||
					nodeExecution ||
					finalData.executionStatus
				) {
					// console.log(`[AgentBuilder] *** Node ${node.id} final data ***:`, {
					//   isExecuting: finalData.isExecuting,
					//   executionStatus: finalData.executionStatus,
					//   executionDuration: finalData.executionDuration,
					//   isCurrentlyExecuting,
					//   hasNodeExecution: !!nodeExecution,
					//   isSubAgent: finalData.isSubAgent
					// });
				}

				return {
					...node,
					data: finalData,
				};
			});
		});
	}, [executingNodeId, currentExecution, setReactFlowNodes, runningNodesCache]);

	// PHASE 4B: Sync React Flow state directly from store
	// This is now the only sync point (Store → ReactFlow), eliminating Context middleman
	useEffect(() => {
		if (storeNodes) {
			// Ensure each node has a unique key
			const uniqueNodes = storeNodes.map((node, index) => ({
				...node,
				id: node.id || `node-${index}`,
			}));
			setReactFlowNodes(uniqueNodes);
		}
	}, [storeNodes, setReactFlowNodes]);

	useEffect(() => {
		if (storeEdges) {
			// Ensure each edge has a unique key
			const uniqueEdges = storeEdges.map((edge, index) => ({
				...edge,
				id: edge.id || `edge-${index}`,
			}));
			setReactFlowEdges(uniqueEdges);
		}
	}, [storeEdges, setReactFlowEdges]);

	// Collaboration: Sync local changes to other users
	useEffect(() => {
		// Skip sync when applying remote changes to avoid loops
		if (applyingRemoteChangesRef.current) return;

		if (isCollabConnected && storeNodes.length > 0) {
			syncNodes(storeNodes);
		}
	}, [isCollabConnected, storeNodes, syncNodes]);

	useEffect(() => {
		// Skip sync when applying remote changes to avoid loops
		if (applyingRemoteChangesRef.current) return;

		if (isCollabConnected && storeEdges.length > 0) {
			syncEdges(storeEdges);
		}
	}, [isCollabConnected, storeEdges, syncEdges]);

	// Collaboration: Listen for remote changes from other users
	useEffect(() => {
		const handleRemoteNodes = (e: Event) => {
			const customEvent = e as CustomEvent;
			const remoteNodes = customEvent.detail.nodes;

			// Set flag to avoid sync loop, then update the graph store
			applyingRemoteChangesRef.current = true;
			storeSetNodes(remoteNodes || []);
			setReactFlowNodes(remoteNodes || []);
			setTimeout(() => {
				applyingRemoteChangesRef.current = false;
			}, 0);
		};
		const handleRemoteEdges = (e: Event) => {
			const customEvent = e as CustomEvent;
			const remoteEdges = customEvent.detail.edges;

			// Set flag to avoid sync loop, then update the graph store
			applyingRemoteChangesRef.current = true;
			storeSetEdges(remoteEdges || []);
			setReactFlowEdges(remoteEdges || []);
			setTimeout(() => {
				applyingRemoteChangesRef.current = false;
			}, 0);
		};

		window.addEventListener("collab:nodes-changed", handleRemoteNodes);
		window.addEventListener("collab:edges-changed", handleRemoteEdges);

		return () => {
			window.removeEventListener("collab:nodes-changed", handleRemoteNodes);
			window.removeEventListener("collab:edges-changed", handleRemoteEdges);
		};
	}, [setReactFlowNodes, setReactFlowEdges, storeSetNodes, storeSetEdges]);

	// Listen for create sub-agent dialog events
	useEffect(() => {
		const handleOpenCreateSubAgentDialog = (event: CustomEvent) => {
			const { parentAgentId, parentAgentName } = event.detail;
			setCreateSubAgentDialog({
				isOpen: true,
				parentAgentId,
				parentAgentName,
			});
		};

		window.addEventListener(
			"openCreateSubAgentDialog",
			handleOpenCreateSubAgentDialog as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openCreateSubAgentDialog",
				handleOpenCreateSubAgentDialog as EventListener,
			);
		};
	}, []);

	// Listen for tool selection dialog events
	useEffect(() => {
		const handleOpenToolSelectionDialog = (event: CustomEvent) => {
			const { parentAgentId, parentAgentName } = event.detail;
			setCreateToolNodeDialog({
				isOpen: true,
				parentAgentId,
				parentAgentName,
			});
		};

		window.addEventListener(
			"openToolSelectionDialog",
			handleOpenToolSelectionDialog as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openToolSelectionDialog",
				handleOpenToolSelectionDialog as EventListener,
			);
		};
	}, []);

	// Listen for create sub-workflow dialog events
	useEffect(() => {
		const handleOpenCreateSubWorkflowDialog = (event: CustomEvent) => {
			const { parentAgentId, parentAgentName } = event.detail;
			setCreateSubWorkflowDialog({
				isOpen: true,
				parentAgentId,
				parentAgentName,
			});
		};

		window.addEventListener(
			"openCreateSubWorkflowDialog",
			handleOpenCreateSubWorkflowDialog as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openCreateSubWorkflowDialog",
				handleOpenCreateSubWorkflowDialog as EventListener,
			);
		};
	}, []);

	// Listen for publish agent dialog events
	useEffect(() => {
		const handleOpenPublishAgentDialog = (event: CustomEvent) => {
			const { agentNodeId, agentName, agentDescription } = event.detail;
			setPublishAgentDialog({
				isOpen: true,
				agentNodeId,
				agentName,
				agentDescription: agentDescription || null,
			});
		};

		window.addEventListener(
			"openPublishAgentDialog",
			handleOpenPublishAgentDialog as EventListener,
		);
		return () => {
			window.removeEventListener(
				"openPublishAgentDialog",
				handleOpenPublishAgentDialog as EventListener,
			);
		};
	}, [currentGraph]);

	// Listen for node palette events - open left palette
	useEffect(() => {
		const handleOpenNodePalette = (event: CustomEvent) => {
			const { sourceNodeId, sourceBranchIndex } = event.detail;
			setPaletteSourceNodeId(sourceNodeId || null);
			setPaletteSourceBranchIndex(sourceBranchIndex ?? null);
			setShowNodePalette(true);
		};

		window.addEventListener(
			"openNodePalette",
			handleOpenNodePalette as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openNodePalette",
				handleOpenNodePalette as EventListener,
			);
		};
	}, []);

	// Listen for tutorial "connect nodes" events
	useEffect(() => {
		const handleTutorialConnect = (event: CustomEvent) => {
			const { sourceSelector, targetSelector } = event.detail ?? {};
			if (!sourceSelector || !targetSelector) return;
			const sourceEl = document.querySelector(sourceSelector);
			const targetEl = document.querySelector(targetSelector);
			if (!sourceEl || !targetEl) return;
			// Walk up to the React Flow node wrapper to read its data-id
			const sourceNode = sourceEl.closest(".react-flow__node");
			const targetNode = targetEl.closest(".react-flow__node");
			const sourceId = sourceNode?.getAttribute("data-id");
			const targetId = targetNode?.getAttribute("data-id");
			if (sourceId && targetId) {
				createConnection(sourceId, targetId).catch((err) => {
					console.warn("[Tutorial] connection failed:", err);
				});
			}
		};
		window.addEventListener(
			"tutorialConnectNodes",
			handleTutorialConnect as EventListener,
		);
		return () => {
			window.removeEventListener(
				"tutorialConnectNodes",
				handleTutorialConnect as EventListener,
			);
		};
	}, [createConnection]);

	// Listen for tutorial "fit view" events
	useEffect(() => {
		const handleTutorialFitView = () => {
			reactFlowInstance.current?.fitView({ padding: 0.3, maxZoom: 0.85, duration: 400 });
		};
		window.addEventListener("tutorialFitView", handleTutorialFitView);
		return () => {
			window.removeEventListener("tutorialFitView", handleTutorialFitView);
		};
	}, []);

	// Listen for tutorial "close execution panel" events
	useEffect(() => {
		const handleClosePanel = () => {
			setShowExecutionPanel(false);
		};
		window.addEventListener("tutorialCloseExecutionPanel", handleClosePanel);
		return () => {
			window.removeEventListener("tutorialCloseExecutionPanel", handleClosePanel);
		};
	}, []);

	// Keyboard shortcuts for node picker
	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			const target = e.target as HTMLElement;
			const isInputFocused =
				target.tagName === "INPUT" ||
				target.tagName === "TEXTAREA" ||
				target.isContentEditable;
			if (isInputFocused) return;

			// / key: Open full palette with search
			if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
				e.preventDefault();
				setPaletteSourceNodeId(null);
				setPaletteSourceBranchIndex(null);
				setShowNodePalette(true);
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	// Listen for node properties events
	useEffect(() => {
		const handleOpenNodeProperties = (event: CustomEvent) => {
			const { nodeId } = event.detail;
			// Prefer live Zustand store data so optimistic updates (e.g. is_sub_agent)
			// are reflected immediately; fall back to reactFlowNodes if not found.
			const node =
				useGraphStore.getState().nodes.find((n) => n.id === nodeId) ??
				reactFlowNodes.find((n) => n.id === nodeId);
			if (node && mode === "edit") {
				openPanel("node", node);
			}
		};

		window.addEventListener(
			"openNodeProperties",
			handleOpenNodeProperties as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openNodeProperties",
				handleOpenNodeProperties as EventListener,
			);
		};
	}, [reactFlowNodes, mode, openPanel]);

	// Listen for node settings events (from settings cog button)
	useEffect(() => {
		const handleOpenNodeSettings = (event: CustomEvent) => {
			const { nodeId } = event.detail;
			// Prefer live Zustand store data so optimistic updates (e.g. is_sub_agent)
			// are reflected immediately; fall back to reactFlowNodes if not found.
			const node =
				useGraphStore.getState().nodes.find((n) => n.id === nodeId) ??
				reactFlowNodes.find((n) => n.id === nodeId);
			if (node && mode === "edit") {
				// Route to correct panel based on node type
				const nodeTypeOriginal = node.data?.type || node.data?.node_type;
				const nodeType = nodeTypeOriginal?.toLowerCase();

				if (nodeType === "document_search") {
					openPanel("documentSearch", node);
				} else if (nodeType === "document_retrieve") {
					openPanel("documentRetrieve", node);
				} else if (nodeType === "document_load") {
					openPanel("documentLoad", node);
				} else if (nodeType === "condition") {
					openPanel("condition", node);
				} else if (nodeType === "subworkflow" || node.type === "subWorkflowNode") {
					openPanel("subWorkflow", node);
				} else if (nodeType === "database_query") {
					openPanel("databaseQuery", node);
				} else if (nodeType === "database_insert") {
					openPanel("databaseInsert", node);
				} else if (nodeType === "database_query_action") {
					openPanel("databaseQueryAction", node);
				} else if (nodeType === "http_request_action") {
					openPanel("httpRequestAction", node);
				} else if (nodeType === "email_send") {
					openPanel("emailSend", node);
				} else if (nodeType === "file_read") {
					openPanel("fileRead", node);
				} else if (nodeType === "file_write") {
					openPanel("fileWrite", node);
				} else if (nodeType === "http_request") {
					openPanel("httpRequest", node);
				} else if (nodeType === "web_search") {
					openPanel("webSearch", node);
				} else if (nodeType === "mcp_server") {
					openPanel("mcpServer", node);
				} else if (nodeType === "email_send_tool") {
					openPanel("emailSendTool", node);
				} else if (nodeType === "end") {
					openPanel("end", node);
				} else if (nodeType === "checkpoint") {
					openPanel("checkpoint", node);
				} else if (nodeType === "for_each" || node.type === "forEachNode") {
					openPanel("forEach", node);
				} else if (nodeType === "code_executor" || node.type === "codeExecutorNode") {
					openPanel("codeExecutor", node);
				} else {
					openPanel("node", node);
				}
			}
		};

		window.addEventListener(
			"openNodeSettings",
			handleOpenNodeSettings as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openNodeSettings",
				handleOpenNodeSettings as EventListener,
			);
		};
	}, [reactFlowNodes, mode, openPanel]);

	// Listen for document search properties panel events
	useEffect(() => {
		const handleOpenDocumentSearchProperties = (event: CustomEvent) => {
			const { nodeId } = event.detail;
			const node = reactFlowNodes.find((n) => n.id === nodeId);
			if (node && mode === "edit" && node.data?.type === "document_search") {
				openPanel("documentSearch", node);
			}
		};

		window.addEventListener(
			"openDocumentSearchProperties",
			handleOpenDocumentSearchProperties as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openDocumentSearchProperties",
				handleOpenDocumentSearchProperties as EventListener,
			);
		};
	}, [reactFlowNodes, mode, openPanel]);

	// Listen for file read properties panel events
	useEffect(() => {
		const handleOpenFileReadProperties = (event: CustomEvent) => {
			const { nodeId } = event.detail;
			const node = reactFlowNodes.find((n) => n.id === nodeId);
			if (node && mode === "edit") {
				openPanel("fileRead", node);
			}
		};

		window.addEventListener(
			"openFileReadProperties",
			handleOpenFileReadProperties as EventListener,
		);

		return () => {
			window.removeEventListener(
				"openFileReadProperties",
				handleOpenFileReadProperties as EventListener,
			);
		};
	}, [reactFlowNodes, mode]);

	const handlePublishAgentConfirm = useCallback(
		async (formData: {
			name: string;
			description: string;
			category: string[];
			tags: string[];
			iconColor?: string;
		}) => {
			if (!currentGraph?.workflow_id) {
				showError(
					"Unable to publish",
					"Please save or load the workflow before publishing an agent.",
				);
				return;
			}
			if (!publishAgentDialog.agentNodeId) {
				showError("Unable to publish", "Select a valid agent node to publish.");
				return;
			}

			setIsPublishingAgent(true);
			try {
				const response = await api.addAgentToLibrary({
					workflow_id: currentGraph.workflow_id,
					agent_node_id: publishAgentDialog.agentNodeId,
					name: formData.name,
					description: formData.description,
					category: formData.category,
					tags: formData.tags,
					icon_color: formData.iconColor,
				});

				if (response?.success) {
					showSuccess(
						"Agent published",
						`"${formData.name}" is now available in the library.`,
					);
					showInfo(
						"You can find this agent under the selected categories on the Library page.",
					);
					setPublishAgentDialog({
						isOpen: false,
						agentNodeId: null,
						agentName: null,
						agentDescription: null,
					});
				} else {
					showError(
						"Failed to publish agent",
						response?.message || "Unknown error",
					);
				}
			} catch (error) {
				console.error("[AgentBuilder] Failed to publish agent", error);
				showError(
					"Failed to publish agent",
					"An unexpected error occurred while publishing this agent.",
				);
			} finally {
				setIsPublishingAgent(false);
			}
		},
		[
			currentGraph?.workflow_id,
			publishAgentDialog.agentNodeId,
			showError,
			showInfo,
			showSuccess,
		],
	);

	const handlePublishAgentCancel = useCallback(() => {
		if (isPublishingAgent) {
			return;
		}
		setPublishAgentDialog({
			isOpen: false,
			agentNodeId: null,
			agentName: null,
			agentDescription: null,
		});
	}, [isPublishingAgent]);

	const onConnect = useCallback(
		async (params: Connection) => {
			if (!currentGraph) {
				showError("No graph", "Please create a graph first");
				return;
			}

			if (params.source && params.target) {
				// Infer connection type from handle IDs
				let connectionType: string;
				if (
					params.sourceHandle === "delegation" &&
					params.targetHandle === "top"
				) {
					connectionType = "delegation";
				} else if (params.sourceHandle === "tools") {
					connectionType = "tool";
				} else {
					connectionType = "workflow";
				}

				// Pre-flight validation for delegation connections
				if (connectionType === "delegation") {
					const targetNode = storeNodes.find(
						(n) => n.id === params.target,
					);
					if (targetNode) {
						// Reject if target is already a sub-agent of a different orchestrator
						if (
							(targetNode.data?.is_sub_agent ||
								targetNode.data?.isSubAgent) &&
							targetNode.data?.parent_agent_id &&
							targetNode.data.parent_agent_id !== params.source
						) {
							showError(
								"Connection failed",
								"This agent is already a sub-agent of another orchestrator",
							);
							return;
						}
						// Reject circular delegation (target already delegates back to source)
						const hasCycle = storeEdges.some(
							(edge) =>
								edge.source === params.target &&
								edge.target === params.source &&
								edge.data?.connection_type === "delegation",
						);
						if (hasCycle) {
							showError(
								"Connection failed",
								"Circular delegation is not allowed",
							);
							return;
						}
					}
				}

				try {
					await createConnection(
						params.source,
						params.target,
						params.sourceHandle || undefined,
						params.targetHandle || undefined,
						undefined,
						connectionType,
					);
				} catch (err) {
					showError("Connection failed", (err as Error).message);
				}
			}
		},
		[currentGraph, createConnection, storeNodes, storeEdges, showError],
	);

	const onNodeDoubleClick = useCallback(
		(event: React.MouseEvent, node: Node) => {
			// Prevent event bubbling to avoid triggering ExecutionPanelFinal
			event.stopPropagation();
			event.preventDefault();
			if (event.nativeEvent.stopImmediatePropagation) {
				event.nativeEvent.stopImmediatePropagation();
			}

			// Get the original node type (may be capitalize from palette)
			const nodeTypeOriginal = node.data?.type || node.data?.node_type;
			const nodeType = nodeTypeOriginal?.toLowerCase();

			if (mode === "edit") {
				// Check if it's a document search node (handle both capitalize and lowercase)
				if (nodeType === "document_search") {
					openPanel("documentSearch", node);
				} else if (nodeType === "document_retrieve") {
					openPanel("documentRetrieve", node);
				} else if (nodeType === "document_load") {
					openPanel("documentLoad", node);
				} else if (nodeType === "condition") {
					openPanel("condition", node);
				} else if (
					nodeType === "subworkflow" ||
					node.type === "subWorkflowNode"
				) {
					openPanel("subWorkflow", node);
				} else if (nodeType === "database_query") {
					openPanel("databaseQuery", node);
				} else if (nodeType === "database_insert") {
					openPanel("databaseInsert", node);
				} else if (nodeType === "database_query_action") {
					openPanel("databaseQueryAction", node);
				} else if (nodeType === "http_request_action") {
					openPanel("httpRequestAction", node);
				} else if (nodeType === "email_send") {
					openPanel("emailSend", node);
				} else if (nodeType === "file_read") {
					openPanel("fileRead", node);
				} else if (nodeType === "file_write") {
					openPanel("fileWrite", node);
				} else if (nodeType === "http_request") {
					openPanel("httpRequest", node);
				} else if (nodeType === "web_search") {
					openPanel("webSearch", node);
				} else if (nodeType === "mcp_server") {
					openPanel("mcpServer", node);
				} else if (nodeType === "email_send_tool") {
					openPanel("emailSendTool", node);
				} else if (nodeType === "end") {
					openPanel("end", node);
				} else if (nodeType === "checkpoint") {
					openPanel("checkpoint", node);
				} else if (
					nodeType === "for_each" ||
					node.type === "forEachNode"
				) {
					openPanel("forEach", node);
				} else if (
					nodeType === "code_executor" ||
					node.type === "codeExecutorNode"
				) {
					console.log("[AgentBuilder] Opening Code Executor properties panel");
					openPanel("codeExecutor", node);
				} else {
					openPanel("node", node);
				}
			} else if (mode === "execution") {
				// In execution mode, open execution panel via shared selection system
				openPanel("execution", {
					id: node.id,
					nodeName: node.data?.name || node.data?.label || "Node",
					nodeType: nodeType,
				});
			}
		},
		[mode],
	);

	// Removed addAgentNode - all node creation now handled through HiddenNodePalette

	// DEPRECATED: Legacy debounced save - now using syncService
	// Keeping this for backward compatibility but it now delegates to syncService
	const debouncedSave = useCallback(() => {
		// Use sync service for consistent behavior
		syncService.scheduleSync();
	}, []);

	const getCanvasCenterPosition = useCallback(() => {
		const instance = reactFlowInstance.current;
		const wrapper = reactFlowWrapper.current;
		if (!instance || !wrapper) {
			return null;
		}

		const { width, height } = wrapper.getBoundingClientRect();
		return instance.project({
			x: width / 2,
			y: height / 2,
		});
	}, []);

	const getSourceHandleForConnection = useCallback(
		(sourceNodeId?: string) => {
			if (!sourceNodeId) return undefined;
			if (paletteSourceBranchIndex === null || paletteSourceBranchIndex < 0)
				return undefined;
			const sourceNode = reactFlowNodes.find((n) => n.id === sourceNodeId);
			const typeValue = sourceNode?.data?.type || sourceNode?.type;
			if (
				typeof typeValue === "string" &&
				typeValue.toUpperCase() === "CONDITION"
			) {
				return `branch-${paletteSourceBranchIndex}`;
			}
			return undefined;
		},
		[paletteSourceBranchIndex, reactFlowNodes],
	);

	// Handle adding nodes from the palette
	const handleAddNodeFromPalette = useCallback(
		async (nodeType: string, sourceNodeId?: string) => {
			if (!currentGraph) {
				showError("No graph loaded", "Please create or load a graph first");
				return;
			}

			if (nodeType === "AGENT_TEMPLATE_LIBRARY") {
				if (!currentGraph.workflow_id) {
					showError(
						"No workflow ID",
						"Please save or reload the workflow before inserting agents.",
					);
					return;
				}

				const dropPosition = getCanvasCenterPosition() || { x: 0, y: 0 };
				const sourceHandle = getSourceHandleForConnection(sourceNodeId);

				const contextPayload: AgentTemplateInsertContext = {
					workflowId: currentGraph.workflow_id,
					graphName: currentGraph.name,
					returnPath:
						typeof window !== "undefined"
							? window.location.pathname + window.location.search
							: `/workflow/${currentGraph.workflow_id}`,
					sourceNodeId: sourceNodeId || null,
					sourceHandle: sourceHandle || null,
					insertionPosition: dropPosition,
					createdAt: Date.now(),
				};
				setAgentTemplateInsertContext(contextPayload);
				clearAgentTemplateInsertPayload();
				setPaletteSourceBranchIndex(null);
				router.push("/library?mode=agent-template");
				return;
			}

			try {
				// Calculate position to the right of the source node
				let position = { x: 400, y: 300 }; // Default fallback

				if (sourceNodeId) {
					const sourceNode = reactFlowNodes.find(
						(node) => node.id === sourceNodeId,
					);
					if (sourceNode) {
						// Position the new node to the right of the source node
						position = {
							x: sourceNode.position.x + 500, // 500px to the right for better spacing
							y: sourceNode.position.y, // Same vertical position
						};

						// Adjust vertical position based on branch index for condition nodes
						if (paletteSourceBranchIndex !== null) {
							const branchCount = 2; // Default to 2 branches for now
							const verticalOffset =
								branchCount === 2
									? paletteSourceBranchIndex === 0
										? -25
										: 25 // True up, False down
									: (paletteSourceBranchIndex - (branchCount - 1) / 2) * 30;

							position.y += (position.y * verticalOffset) / 50; // Convert percentage to pixels
						}
					}
				}

				// Generate temporary ID for optimistic UI update
				const tempNodeId = `temp-node-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
				const tempEdgeId = sourceNodeId
					? `temp-edge-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
					: null;

				// Prepare node configuration based on type
				const nodeConfig: any = {
					node_type: nodeType as
						| "START"
						| "END"
						| "AGENT"
						| "TOOL"
						| "STEP"
						| "CONDITION"
						| "INFO"
						| "SUBGRAPH"
						| "DATABASE_INSERT"
						| "DATABASE_QUERY_ACTION"
						| "HTTP_REQUEST_ACTION"
						| "CHECKPOINT",
					name: `${nodeType.charAt(0).toUpperCase() + nodeType.slice(1).toLowerCase().replace("_", " ")} ${nodeCounter}`,
					position,
					description:
						nodeType === "AGENT"
							? "You are a helpful AI assistant. Please respond to the user's message thoughtfully and accurately."
							: `${nodeType} node`,
				};

				// Add specific configurations for action nodes
				if (nodeType === "DATABASE_INSERT") {
					nodeConfig.database_insert_config = {
						connection_id: "",
						table_name: "",
						column_mappings: [],
						return_inserted_rows: true,
						on_conflict_strategy: "fail",
						conflict_columns: [],
						timeout_seconds: 30,
						batch_size: 1,
						transaction_mode: "auto",
					};
				} else if (nodeType === "DATABASE_QUERY_ACTION") {
					nodeConfig.database_query_action_config = {
						connection_id: "",
						table_name: "",
						table_names: [],
						allowed_operations: ["SELECT"],
						max_rows: 100,
						timeout_seconds: 30,
						enable_read_only: true,
						return_format: "json",
						include_schema: true,
					};
				} else if (nodeType === "HTTP_REQUEST_ACTION") {
					nodeConfig.http_request_action_config = {
						url_template: "",
						method: "GET",
						headers: {},
						auth_type: "none",
						auth_config: {},
						request_body_template: "",
						timeout_seconds: 30,
						max_retries: 3,
						retry_delay: 1.0,
						response_format: "auto",
						error_handling: "fail",
						follow_redirects: true,
						verify_ssl: true,
						extract_path: "",
						success_status_codes: [200, 201, 202, 204],
					};
				} else if (nodeType === "CHECKPOINT") {
					nodeConfig.checkpoint_config = {
						prompt: `Checkpoint: ${nodeConfig.name}`,
						require_input: true,
						timeout_seconds: null,
						default_value: "",
					};
				} else if (nodeType === "FOR_EACH") {
					nodeConfig.for_each_config = {
						source_mode: "previous",
						source_node_id: "",
						field_path: "fields.rows",
						concurrency_limit: 5,
						rate_limit_per_second: null,
						max_iterations: 1000,
						error_strategy: "continue_on_error",
						max_retries_per_item: 0,
					};
				} else if (nodeType === "CODE_EXECUTOR") {
					nodeConfig.code_executor_config = {
						language: "python",
						code: "# Your Python code here\n# Input variables are available directly by name\n# Set the output variable (default: result) with your return value\n\nresult = \"Hello, World!\"\n",
						timeout_seconds: 30,
						memory_limit_mb: 256,
						allow_network: true,
						allow_filesystem: true,
						allow_subprocess: false,
						allowed_packages: [],
						input_variables: [],
						output_variable: "result",
						working_directory: "",
						environment_variables: {},
						capture_stdout: true,
						capture_stderr: true,
					};
				} else if (nodeType === "DOCUMENT_LOAD") {
					nodeConfig.document_load_config = {
						collection_id: null,
						document_ids: [],
						max_document_size_tokens: 100000,
						truncation_strategy: "end",
						output_mode: "batch",
						chunk_output_mode: "full",
						chunk_token_limit: 50000,
						output_format: "markdown",
						include_metadata: true,
					};
				} else if (nodeType === "FILE_READ") {
					nodeConfig.file_read_config = {
						extraction_mode: "model_ocr",
						output_format: "markdown",
						doc_type: "auto",
						ocr_prompt: `Extract all text from this document image. Preserve the original formatting including:
- Headers and sections
- Lists and bullet points  
- Tables (use markdown table format)
- Bold and italic text
- Page numbers if visible

Output as clean, well-structured markdown.`,
						max_tokens_per_request: 4000,
						include_metadata: true,
						preserve_formatting: true,
						extract_tables: true,
						extract_images: true,
						max_file_size_mb: 1024,
						allowed_extensions: [
							".pdf",
							".png",
							".jpg",
							".jpeg",
							".docx",
							".txt",
							".xlsx",
							".csv",
						],
						fallback_on_error: true,
						llm_safe_output: false,
						use_cache: true,
					};
				}

				// Create node — instant optimistic UI, backend sync in background
				const { tempId, promise: nodeCreationPromise } =
					createNode(nodeConfig);

				setNodeCounter((count) => count + 1);

				// Create connection immediately using temp ID for instant UI.
				// replaceNodeId (inside the promise) will update the connection's
				// target to the real backend ID before the sync service fires.
				if (sourceNodeId) {
					const sourceHandle = getSourceHandleForConnection(sourceNodeId);
					createConnection(sourceNodeId, tempId, sourceHandle, undefined).catch(
						(connectionErr) => {
							console.error("Failed to create connection:", connectionErr);
							showError("Connection failed", (connectionErr as Error).message);
						},
					);
				}

				// Handle backend errors in background
				nodeCreationPromise.catch((err) => {
					showError("Node creation failed", (err as Error).message);
				});

				debouncedSave();

				// Fit view after adding a node so it's visible on canvas
				setTimeout(() => {
					reactFlowInstance.current?.fitView({ padding: 0.2, duration: 300 });
				}, 100);

				// Reset the branch index after use
				setPaletteSourceBranchIndex(null);
			} catch (err) {
				showError("Node creation failed", (err as Error).message);
			}
		},
		[
			currentGraph,
			createNode,
			createConnection,
			debouncedSave,
			nodeCounter,
			getCanvasCenterPosition,
			getSourceHandleForConnection,
			router,
			setPaletteSourceBranchIndex,
			showError,
		],
	);

	const insertAgentTemplateSubgraph = useCallback(
		async (
			payload: AgentTemplateInsertPayload,
			context: AgentTemplateInsertContext,
		) => {
			const definition = payload.graphDefinition ?? {};
			const allNodes: any[] = Array.isArray(definition.nodes)
				? definition.nodes
				: [];
			const filteredNodes = allNodes.filter((node) => {
				const typeValue = (
					node?.type?.value ||
					node?.type ||
					node?.data?.type ||
					""
				)
					.toString()
					.toUpperCase();
				return typeValue !== "START" && typeValue !== "END";
			});

			if (!filteredNodes.length) {
				throw new Error(
					"Agent template does not contain any insertable nodes.",
				);
			}

			const bounds = filteredNodes.reduce(
				(acc, node) => {
					const pos = node.position || { x: 0, y: 0 };
					return {
						minX: Math.min(acc.minX, pos.x ?? 0),
						maxX: Math.max(acc.maxX, pos.x ?? 0),
						minY: Math.min(acc.minY, pos.y ?? 0),
						maxY: Math.max(acc.maxY, pos.y ?? 0),
					};
				},
				{ minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity },
			);

			const templateCenter = {
				x: bounds.minX === Infinity ? 0 : (bounds.minX + bounds.maxX) / 2,
				y: bounds.minY === Infinity ? 0 : (bounds.minY + bounds.maxY) / 2,
			};

			const insertionOffset = context.insertionPosition
				? {
						x: context.insertionPosition.x - templateCenter.x,
						y: context.insertionPosition.y - templateCenter.y,
					}
				: { x: 0, y: 0 };

			const normalizeNodeType = (node: any): string => {
				const typeValue = node?.type?.value || node?.type || node?.data?.type;
				return typeof typeValue === "string" ? typeValue.toUpperCase() : "";
			};

			const extractParentAgentId = (node: any): string | null => {
				if (node.parent_agent_id) return node.parent_agent_id;
				const configAttrs = [
					"agent_config",
					"tool_config",
					"web_search_config",
					"document_search_config",
					"document_retrieve_config",
					"database_query_config",
					"database_insert_config",
					"http_request_config",
					"http_request_action_config",
					"mcp_server_config",
					"email_send_config",
					"email_send_tool_config",
					"file_read_config",
					"subworkflow_config",
					"input_source_config",
					"code_executor_config",
				];
				for (const attr of configAttrs) {
					const config = node[attr];
					if (config?.parent_agent_id) {
						return config.parent_agent_id;
					}
				}
				return null;
			};

			const agentNodes = filteredNodes.filter(
				(node) => normalizeNodeType(node) === "AGENT",
			);
			const agentMap = new Map<string, any>();
			agentNodes.forEach((node) => {
				const id = node.uniq_id || node.id;
				if (id) {
					agentMap.set(id, node);
				}
			});

			const visitedAgents = new Set<string>();
			const sortedAgents: any[] = [];
			const visitAgent = (node: any) => {
				const id = node.uniq_id || node.id;
				if (!id || visitedAgents.has(id)) {
					return;
				}
				const parentId = extractParentAgentId(node);
				if (parentId && agentMap.has(parentId)) {
					visitAgent(agentMap.get(parentId));
				}
				visitedAgents.add(id);
				sortedAgents.push(node);
			};
			agentNodes.forEach(visitAgent);

			const nonAgentNodes = filteredNodes.filter(
				(node) => normalizeNodeType(node) !== "AGENT",
			);
			const sortedNodes = [...sortedAgents, ...nonAgentNodes];

			const idMap = new Map<string, string>();

			const cloneConfig = (value: any) => JSON.parse(JSON.stringify(value));

			const remapParentAgentIds = (value: any): any => {
				if (value === null || value === undefined) {
					return value;
				}

				if (Array.isArray(value)) {
					return value.map((entry) => {
						if (typeof entry === "string" && idMap.has(entry)) {
							return idMap.get(entry);
						}
						return remapParentAgentIds(entry);
					});
				}

				if (typeof value !== "object") {
					return value;
				}

				const result: Record<string, any> = {};
				Object.keys(value).forEach((key) => {
					const entry = (value as Record<string, any>)[key];
					if (
						key === "parent_agent_id" &&
						typeof entry === "string" &&
						idMap.has(entry)
					) {
						result[key] = idMap.get(entry);
					} else if (key === "delegated_agents" && Array.isArray(entry)) {
						result[key] = entry
							.map((agentId: string) =>
								idMap.has(agentId) ? idMap.get(agentId) : agentId,
							)
							.filter(Boolean);
					} else if (Array.isArray(entry) || typeof entry === "object") {
						result[key] = remapParentAgentIds(entry);
					} else {
						result[key] = entry;
					}
				});
				return result;
			};

			const buildCreateRequest = (node: any) => {
				const type = normalizeNodeType(node);
				const basePosition = node.position || { x: 0, y: 0 };
				const position = {
					x: (basePosition.x ?? 0) + insertionOffset.x,
					y: (basePosition.y ?? 0) + insertionOffset.y,
				};

				const payload: Omit<CreateNodeRequest, "graph_name"> = {
					node_type: type as CreateNodeRequest["node_type"],
					name: node.name || type,
					description: node.description || "",
					position,
				};

				const configFields: Array<keyof CreateNodeRequest> = [
					"agent_config",
					"document_search_config",
					"document_retrieve_config",
					"document_load_config",
					"database_query_config",
					"http_request_config",
					"web_search_config",
					"mcp_server_config",
					"subworkflow_config",
					"condition_config",
					"input_source_config",
					"email_send_config",
					"email_send_tool_config",
					"file_read_config",
					"checkpoint_config",
					"database_insert_config",
					"http_request_action_config",
					"end_node_config",
					"code_executor_config",
					"for_each_config",
				];

				configFields.forEach((field) => {
					if (node[field]) {
						const cloned = remapParentAgentIds(cloneConfig(node[field]));
						if (field === "agent_config" && cloned?.delegated_agents) {
							cloned.delegated_agents = [];
						}
						(payload as any)[field] = cloned;
					}
				});

				if (node.prompt_template) {
					payload.prompt_template = node.prompt_template;
				}

				return payload;
			};

			for (const node of sortedNodes) {
				const originalId = node.uniq_id || node.id;
				const createPayload = buildCreateRequest(node);
				const { promise } = createNode(createPayload);
				const newNodeId = await promise;
				if (!newNodeId) {
					throw new Error(`Failed to create node "${node.name}"`);
				}
				if (originalId) {
					idMap.set(originalId, newNodeId);
				}
			}

			const definitionConnections: any[] =
				Array.isArray(definition.connections) && definition.connections.length
					? definition.connections
					: Array.isArray(definition.edges)
						? definition.edges
						: [];

			for (const connection of definitionConnections) {
				const sourceOriginal = connection.source_id || connection.source;
				const targetOriginal = connection.target_id || connection.target;
				if (!sourceOriginal || !targetOriginal) {
					continue;
				}
				const mappedSource = idMap.get(sourceOriginal);
				const mappedTarget = idMap.get(targetOriginal);
				if (!mappedSource || !mappedTarget) {
					continue;
				}

				await createConnection(
					mappedSource,
					mappedTarget,
					connection.source_handle || undefined,
					connection.target_handle || undefined,
					connection.label,
					connection.connection_type || connection.connectionType || undefined,
				);
			}

			if (context.sourceNodeId && payload.primaryAgentNodeId) {
				const mappedPrimary = idMap.get(payload.primaryAgentNodeId);
				if (mappedPrimary) {
					await createConnection(
						context.sourceNodeId,
						mappedPrimary,
						context.sourceHandle || undefined,
						undefined,
					);
				}
			}

			if (context.insertionPosition && reactFlowInstance.current) {
				reactFlowInstance.current.setCenter(
					context.insertionPosition.x,
					context.insertionPosition.y,
					{ duration: 800, zoom: 0.9 },
				);
			}
		},
		[createConnection, createNode],
	);

	// updateNodeData and deleteNode are now handled by the shared usePropertyPanels hook

	const handleCreateSubAgent = useCallback(
		async (
			name: string,
			delegationDescription: string,
			agentTemplate?: string,
		) => {
			try {
				await createSubAgent(createSubAgentDialog.parentAgentId, {
					name,
					delegation_description: delegationDescription,
					agent_template: agentTemplate,
				});
				setCreateSubAgentDialog({
					isOpen: false,
					parentAgentId: "",
					parentAgentName: "",
				});
				showSuccess(
					"Sub-agent created",
					`Successfully created sub-agent "${name}"`,
				);
			} catch (error) {
				// console.error('Error creating sub-agent:', error);
				showError("Failed to create sub-agent", (error as Error).message);
			}
		},
		[
			createSubAgent,
			createSubAgentDialog.parentAgentId,
			showSuccess,
			showError,
		],
	);

	const handleCreateSubWorkflow = useCallback(
		async (
			name: string,
			delegationDescription: string,
			targetWorkflowId?: string,
		) => {
			if (!currentGraph) {
				await createGraph(
					`New Graph ${graphs.length + 1}`,
					"A new AI workflow",
				);
			}

			try {
				// Get parent agent position to place workflow node below it
				const parentNode = reactFlowNodes.find(
					(n) => n.id === createSubWorkflowDialog.parentAgentId,
				);

				// Calculate position for new workflow node
				let position;
				if (parentNode) {
					// Place workflow node below and to the right of the agent
					position = {
						x: parentNode.position.x + 150,
						y: parentNode.position.y + 200,
					};
				} else {
					// Default position if parent not found
					position = { x: 400, y: 300 };
				}

				// Create the sub-workflow node — instant UI with temp ID
				const { tempId, promise: nodePromise } = createNode({
					name: name || "Sub-Workflow",
					node_type: "SUBWORKFLOW",
					description: delegationDescription || "Execute a sub-workflow",
					position,
					subworkflow_config: {
						workflow_name: name,
						target_workflow_id: targetWorkflowId,
						delegation_description: delegationDescription,
						share_context: true,
						parent_agent_id: createSubWorkflowDialog.parentAgentId,
					},
				});

				// Create connection immediately using temp ID for instant UI
				createConnection(
					createSubWorkflowDialog.parentAgentId,
					tempId,
					"workflow",
					"input",
					undefined,
					"TOOL",
				).catch((err) => {
					console.error("Failed to create connection:", err);
				});

				// Handle backend errors in background
				nodePromise.catch((err) => {
					showError("Sub-workflow creation failed", (err as Error).message);
				});

				setCreateSubWorkflowDialog({
					isOpen: false,
					parentAgentId: "",
					parentAgentName: "",
				});
				showSuccess(
					"Sub-workflow created",
					`Successfully created sub-workflow "${name}"`,
				);
			} catch (error) {
				// console.error('Error creating sub-workflow:', error);
				showError("Failed to create sub-workflow", (error as Error).message);
			}
		},
		[
			currentGraph,
			createGraph,
			createNode,
			createConnection,
			createSubWorkflowDialog.parentAgentId,
			graphs.length,
			reactFlowNodes,
			showSuccess,
			showError,
		],
	);

	const handleCreateToolNode = useCallback(
		async (
			toolType: string,
			toolName: string,
			metadata?: {
				provider?: string;
				customConfig?: McpServerInfo;
				shouldClone?: boolean;
			},
		) => {
			if (!currentGraph) {
				await createGraph(
					`New Graph ${graphs.length + 1}`,
					"A new AI workflow",
				);
			}

			try {
				// Clone the MCP server if requested
				let customConfig = metadata?.customConfig;
				if (
					metadata?.shouldClone &&
					customConfig &&
					customConfig.id &&
					!customConfig.is_owned_by_current_user
				) {
					try {
						const clonedServer = await userSettingsAPI.cloneMcpServer(
							customConfig.id,
							customConfig.server_name,
						);
						customConfig = clonedServer;
						showSuccess(
							"Server cloned",
							`Successfully cloned ${customConfig.server_name} to your servers`,
						);
					} catch (error) {
						showError("Failed to clone server", (error as Error).message);
						// Continue with original config if cloning fails
					}
				}
				// Get parent agent position to place tool node below it
				const parentNode = reactFlowNodes.find(
					(n) => n.id === createToolNodeDialog.parentAgentId,
				);

				// Find existing tool nodes connected to this agent
				const existingToolNodes = reactFlowNodes.filter((node) => {
					// Check if this node is connected to the parent agent
					const hasConnection = reactFlowEdges.some(
						(edge) =>
							edge.source === createToolNodeDialog.parentAgentId &&
							edge.target === node.id &&
							(node.type === "toolNode" ||
								node.data?.node_type === "DOCUMENT_SEARCH" ||
								node.data?.node_type === "DATABASE_QUERY" ||
								node.data?.node_type === "HTTP_REQUEST" ||
								node.data?.node_type === "WEB_SEARCH" ||
								node.data?.node_type === "MCP_SERVER" ||
								node.data?.node_type === "EMAIL_SEND_TOOL" ||
								node.data?.node_type === "FILE_WRITE" ||
								node.data?.node_type === "FILE_READ" ||
								node.data?.node_type === "CODE_EXECUTOR" ||
								node.data?.node_type === "TOOL"),
					);
					return hasConnection;
				});

				// Calculate position for new tool node
				let position;
				if (parentNode) {
					const baseY = parentNode.position.y + 200; // Base distance below agent
					const horizontalSpacing = 250; // Horizontal spacing between tools

					if (existingToolNodes.length === 0) {
						// First tool: center it below the agent
						position = {
							x: parentNode.position.x,
							y: baseY,
						};
					} else {
						// Multiple tools: arrange them horizontally
						const toolCount = existingToolNodes.length;

						// Calculate the x position for the new tool
						// Distribute tools evenly, centered around the agent
						const totalWidth = toolCount * horizontalSpacing;
						const startX = parentNode.position.x - totalWidth / 2;

						position = {
							x: startX + toolCount * horizontalSpacing,
							y: baseY,
						};

						// Reposition existing tools to maintain centered layout
						const newTotalWidth = (toolCount + 1) * horizontalSpacing;
						const newStartX =
							parentNode.position.x - newTotalWidth / 2 + horizontalSpacing / 2;

						existingToolNodes.forEach((tool, index) => {
							const newX = newStartX + index * horizontalSpacing;
							// Update the position through the React Flow API
							const updates = [
								{
									id: tool.id,
									type: "position" as const,
									position: { x: newX, y: baseY },
								},
							];
							onNodesChange(updates);
						});
					}
				} else {
					position = { x: 100, y: 100 };
				}

				// Create the appropriate tool node based on toolType
				const nodeConfig: any = {
					name: toolName,
					position,
				};

				if (toolType === "document_search") {
					nodeConfig.node_type = "DOCUMENT_SEARCH";
					nodeConfig.document_search_config = {
						document_collections: [],
						document_ids: [],
						search_k: 3,
						search_type: "similarity",
						similarity_threshold: 0.7,
						citation_format: "inline",
						parent_agent_id: createToolNodeDialog.parentAgentId,
					};
				} else if (toolType === "document_retrieve") {
					nodeConfig.node_type = "DOCUMENT_RETRIEVE";
					nodeConfig.document_retrieve_config = {
						collection_ids: [],
						parent_agent_id: createToolNodeDialog.parentAgentId,
					};
				} else if (toolType === "database_query") {
					nodeConfig.node_type = "DATABASE_QUERY";
					nodeConfig.database_query_config = {
						connection_id: "", // Will need to be configured later
						table_name: "",
						allowed_operations: ["SELECT"],
						max_rows: 100,
						timeout_seconds: 30,
						enable_read_only: true,
						return_format: "json",
						include_schema: true,
						parent_agent_id: createToolNodeDialog.parentAgentId,
					};
				} else if (toolType === "database_insert") {
					nodeConfig.node_type = "DATABASE_INSERT";
					nodeConfig.database_insert_config = {
						connection_id: "", // Will need to be configured later
						table_name: "",
						column_mappings: [],
						return_inserted_rows: true,
						on_conflict_strategy: "fail",
						conflict_columns: [],
						timeout_seconds: 30,
						batch_size: 1,
						transaction_mode: "auto",
					};
				} else if (toolType === "http_request") {
					nodeConfig.node_type = "HTTP_REQUEST";
					nodeConfig.http_request_config = {
						url_template: "",
						method: "GET",
						headers: {},
						auth_type: "none",
						auth_config: {},
						request_body_template: "",
						timeout_seconds: 30,
						max_retries: 3,
						retry_delay: 1.0,
						response_format: "auto",
						error_handling: "fail",
						follow_redirects: true,
						verify_ssl: true,
						extract_path: "",
						success_status_codes: [200, 201, 202, 204],
						parent_agent_id: createToolNodeDialog.parentAgentId,
					};
				} else if (toolType === "web_search") {
					nodeConfig.node_type = "WEB_SEARCH";
					// Use Tavily if user has it configured, otherwise default to DuckDuckGo
					const useTavily = tavilyConfig?.configured && tavilyConfig.api_key;
					nodeConfig.web_search_config = {
						search_provider: useTavily ? "tavily" : "duckduckgo",
						api_key: useTavily ? tavilyConfig.api_key : "",
						max_results: 5,
						search_depth: "basic",
						include_answer: false,
						include_raw_content: false,
						include_images: false,
						timeout_seconds: 10,
						region: "wt-wt",
						safe_search: "moderate",
						time_range: "",
						parent_agent_id: createToolNodeDialog.parentAgentId,
					};
				} else if (toolType === "mcp_server") {
					const provider = metadata?.provider || "";
					// Use the potentially-cloned customConfig from above
					nodeConfig.node_type = "MCP_SERVER";

					// Use custom config if available, otherwise use provider defaults
					if (customConfig) {
						// Map custom server config to mcp_server_config
						nodeConfig.mcp_server_config = {
							provider: "",
							server_name: customConfig.server_name,
							connection_type: customConfig.connection_type,
							server_url: customConfig.server_url || "",
							command: customConfig.command || "",
							args: customConfig.config_summary?.args || [],
							working_directory:
								customConfig.config_summary?.working_directory || "",
							environment_variables:
								customConfig.config_summary?.environment_variables || {},
							auth_type: customConfig.auth_type,
							auth_config: customConfig.config_summary?.auth_credentials || {},
							timeout_seconds:
								customConfig.config_summary?.timeout_seconds || 30,
							max_retries: customConfig.config_summary?.max_retries || 3,
							retry_delay: customConfig.config_summary?.retry_delay || 1.0,
							keep_alive: true,
							capabilities_filter: [],
							resource_access: {},
							tool_permissions: {},
							logging_level: "info",
							description: customConfig.description || "",
							parent_agent_id: createToolNodeDialog.parentAgentId,
						};
					} else {
						// Try to load saved integration config from settings
						let savedConfig: Record<string, any> | null = null;
						try {
							const integrationResult =
								await userSettingsAPI.getMcpIntegrationForWorkflow(provider);
							if (integrationResult.configured && integrationResult.mcp_server_config) {
								savedConfig = integrationResult.mcp_server_config;
							}
						} catch {
							// Silently fall back to provider defaults
						}

						if (savedConfig) {
							// Use saved integration config from settings
							nodeConfig.mcp_server_config = {
								...savedConfig,
								server_name: toolName,
								parent_agent_id: createToolNodeDialog.parentAgentId,
								keep_alive: true,
								capabilities_filter: [],
								resource_access: {},
								logging_level: "info",
							};
						} else {
							// Provider-specific defaults for built-in providers
							const providerDefaults = getProviderDefaults(provider);

							nodeConfig.mcp_server_config = {
								provider,
								server_name: toolName,
								connection_type: providerDefaults.connection_type || "stdio",
								server_url: providerDefaults.server_url || "",
								command: "",
								args: [],
								working_directory: "",
								auth_type: providerDefaults.auth_type || "none",
								auth_config: providerDefaults.auth_config || {},
								timeout_seconds: providerDefaults.timeout_seconds || 30,
								max_retries: providerDefaults.max_retries || 3,
								retry_delay: providerDefaults.retry_delay || 1.0,
								keep_alive: true,
								capabilities_filter: [],
								resource_access: {},
								tool_permissions: {},
								logging_level: "info",
								description: providerDefaults.description || "",
								parent_agent_id: createToolNodeDialog.parentAgentId,
							};
						}
					}
				} else if (toolType === "email_send") {
					nodeConfig.node_type = "EMAIL_SEND_TOOL";
					nodeConfig.email_send_tool_config = {
						to_address: {
							mode: "ai",
							static_value: "",
							ai_description: "",
						},
						subject: {
							mode: "ai",
							static_value: "",
							ai_description: "",
						},
						body: {
							mode: "ai",
							static_value: "",
							ai_description: "",
						},
					};
				} else if (toolType === "file_write") {
					nodeConfig.node_type = "FILE_WRITE";
					nodeConfig.file_write_config = {
						output_directory: "outputs",
						allowed_extensions: [
							".txt",
							".md",
							".json",
							".csv",
							".yaml",
							".yml",
						],
						max_file_size_mb: 1024,
						create_directories: true,
					};
				} else if (toolType === "file_read") {
					nodeConfig.node_type = "FILE_READ";
					nodeConfig.file_read_config = {
						extraction_mode: "model_ocr",
						output_format: "markdown",
						doc_type: "auto",
						max_tokens_per_request: 4000,
						include_metadata: true,
						preserve_formatting: true,
						extract_tables: true,
						extract_images: true,
						max_file_size_mb: 10,
						allowed_extensions: [
							".pdf",
							".txt",
							".docx",
							".xlsx",
							".csv",
							".png",
							".jpg",
							".jpeg",
							".html",
							".md",
						],
						fallback_on_error: true,
						skip_on_error: false,
						llm_safe_output: false,
						use_cache: true,
					};
				} else if (toolType === "code_executor") {
					nodeConfig.node_type = "CODE_EXECUTOR";
					nodeConfig.code_executor_config = {
						language: "python",
						code: "# Agent provides code at runtime\nresult = None",
						timeout_seconds: 30,
						memory_limit_mb: 256,
						allow_network: true,
						allow_filesystem: true,
						allow_subprocess: false,
						input_variables: [],
						output_variable: "result",
						capture_stdout: true,
						capture_stderr: true,
					};
				}

				// Create node — instant UI with temp ID
				const { tempId, promise: nodePromise } = createNode(nodeConfig);

				// Create connection immediately using temp ID for instant UI
				if (createToolNodeDialog.parentAgentId) {
					createConnection(
						createToolNodeDialog.parentAgentId,
						tempId,
						"tools", // From tools handle of agent (left bottom handle)
						"top", // To top of tool
						undefined, // No label
						"tool", // Connection type for tool nodes
					).catch((err) => {
						console.error("Failed to create connection:", err);
					});
				}

				// Handle backend errors in background
				nodePromise.catch((err) => {
					showError("Tool creation failed", (err as Error).message);
				});

				setCreateToolNodeDialog({
					isOpen: false,
					parentAgentId: "",
					parentAgentName: "",
				});
				showSuccess("Tool created", `Successfully created ${toolName}`);
			} catch (error) {
				showError("Failed to create tool", (error as Error).message);
			}
		},
		[
			currentGraph,
			createGraph,
			createNode,
			createConnection,
			createToolNodeDialog.parentAgentId,
			graphs.length,
			reactFlowNodes,
			reactFlowEdges,
			onNodesChange,
			showSuccess,
			showError,
			tavilyConfig,
		],
	);

	// Inject eval scores and read-only flag into node data for evaluate mode or collab read-only (viewer)
	const nodesWithScores = useMemo(() => {
		if (mode !== "evaluate" && !isCollabReadOnly) {
			return reactFlowNodes;
		}
		return reactFlowNodes.map((n) => ({
			...n,
			data: {
				...n.data,
				isReadOnlyPreview: mode === "evaluate" || isCollabReadOnly,
				evalScore: mode === "evaluate" ? (nodeEvalScores[n.id] ?? null) : n.data.evalScore,
			},
		}));
	}, [reactFlowNodes, nodeEvalScores, mode, isCollabReadOnly]);

	// Event handlers to replace arrow functions in JSX
	const handleReactFlowInit = useCallback((instance: ReactFlowInstance) => {
		reactFlowInstance.current = instance;
	}, []);

	const handleNodesDelete = useCallback(
		(nodesToDelete: Node[]) => {
			if (nodesToDelete.length === 0 || mode === "evaluate") {
				return;
			}

			const protectedNodes = nodesToDelete.filter((node) => isStartNode(node));
			const deletableNodes = nodesToDelete.filter((node) => !isStartNode(node));

			if (protectedNodes.length > 0) {
				showError(
					"Start node required",
					"Every workflow begins with a Start node, so it cannot be deleted.",
				);
			}

			const deletionPromises = deletableNodes.map((node) =>
				graphOperations.deleteNode(node.id).catch((err) => {
					showError("Delete failed", (err as Error).message);
				}),
			);

			if (deletionPromises.length > 0) {
				Promise.allSettled(deletionPromises).then(() => {
					if (protectedNodes.length > 0) {
						restoreGraphFromStore();
					}
				});
			} else if (protectedNodes.length > 0) {
				restoreGraphFromStore();
			}
		},
		[graphOperations, restoreGraphFromStore, showError, mode],
	);

	const handleEdgesDelete = useCallback(
		(edgesToDelete: Edge[]) => {
			if (mode === "evaluate") return;
			edgesToDelete.forEach((edge) => {
				graphOperations
					.deleteConnection(edge.source, edge.target)
					.catch((err) => {
						showError("Delete failed", (err as Error).message);
					});
			});
		},
		[graphOperations, showError, mode],
	);

	// Track drag state for Ctrl+drag tree movement
	const dragStateRef = useRef<{
		isDragging: boolean;
		draggedNodeId: string | null;
		ctrlPressed: boolean;
		initialPositions: Map<string, { x: number; y: number }>;
		pendingPosition: { x: number; y: number } | null;
	}>({
		isDragging: false,
		draggedNodeId: null,
		ctrlPressed: false,
		initialPositions: new Map(),
		pendingPosition: null,
	});

	// rAF handle for throttling drag updates to 60fps
	const dragRafRef = useRef<number | null>(null);

	/**
	 * Recursively find all descendants of a node (children, grandchildren, etc.)
	 * through delegation and tool edges
	 */
	const getAllDescendants = useCallback(
		(nodeId: string, edges: Edge[]): string[] => {
			const descendants: string[] = [];
			const visited = new Set<string>();

			const traverse = (currentId: string) => {
				if (visited.has(currentId)) return;
				visited.add(currentId);

				// Find all edges where this node is the source and connection type is delegation or tool
				edges.forEach((edge) => {
					if (
						edge.source === currentId &&
						(edge.data?.connection_type === "delegation" ||
							edge.data?.connection_type === "tool")
					) {
						descendants.push(edge.target);
						traverse(edge.target); // Recursively find children of children
					}
				});
			};

			traverse(nodeId);
			return descendants;
		},
		[],
	);

	const handleNodeDragStart = useCallback(
		(event: React.MouseEvent, node: Node) => {
			dragStateRef.current.isDragging = true;
			dragStateRef.current.draggedNodeId = node.id;
			dragStateRef.current.ctrlPressed = event.ctrlKey || event.metaKey;

			// Store initial positions of dragged node and all its descendants
			if (dragStateRef.current.ctrlPressed) {
				const descendants = getAllDescendants(node.id, reactFlowEdges);
				const allNodes = [node.id, ...descendants];

				dragStateRef.current.initialPositions.clear();
				allNodes.forEach((nodeId) => {
					const n = reactFlowNodes.find((n) => n.id === nodeId);
					if (n) {
						dragStateRef.current.initialPositions.set(nodeId, {
							x: n.position.x,
							y: n.position.y,
						});
					}
				});
			}
		},
		[getAllDescendants, reactFlowEdges, reactFlowNodes],
	);

	const handleNodeDrag = useCallback(
		(event: React.MouseEvent, node: Node) => {
			if (
				!dragStateRef.current.isDragging ||
				!dragStateRef.current.ctrlPressed ||
				dragStateRef.current.draggedNodeId !== node.id
			) {
				return;
			}

			// Cancel any pending rAF to coalesce rapid updates
			if (dragRafRef.current !== null) {
				cancelAnimationFrame(dragRafRef.current);
			}

			// Throttle updates to 60fps using requestAnimationFrame
			dragRafRef.current = requestAnimationFrame(() => {
				// Use the pending position captured from handleNodesChange
				const newParentPosition = dragStateRef.current.pendingPosition;
				if (!newParentPosition) return;

				// Calculate delta from initial position
				const initialPos = dragStateRef.current.initialPositions.get(node.id);
				if (!initialPos) return;

				const deltaX = newParentPosition.x - initialPos.x;
				const deltaY = newParentPosition.y - initialPos.y;

				// Get all descendants that need to move
				const descendants = getAllDescendants(node.id, reactFlowEdges);

				// Collect all position updates for batch store update
				const positionUpdates: Array<{
					nodeId: string;
					position: { x: number; y: number };
				}> = [];

				// Batch update all nodes (parent + descendants) in a single state update
				setReactFlowNodes((nodes) =>
					nodes.map((n) => {
						// Update parent node
						if (n.id === node.id) {
							positionUpdates.push({
								nodeId: n.id,
								position: newParentPosition,
							});
							return { ...n, position: newParentPosition };
						}

						// Update descendants
						if (descendants.includes(n.id)) {
							const initialDescendantPos =
								dragStateRef.current.initialPositions.get(n.id);
							if (!initialDescendantPos) return n;

							const newPosition = {
								x: initialDescendantPos.x + deltaX,
								y: initialDescendantPos.y + deltaY,
							};

							positionUpdates.push({ nodeId: n.id, position: newPosition });
							return { ...n, position: newPosition };
						}

						return n;
					}),
				);

				// Single store update for all positions (instead of N individual updates)
				if (positionUpdates.length > 0) {
					useGraphStore.getState().batchUpdateNodePositions(positionUpdates);
				}
			});
		},
		[getAllDescendants, reactFlowEdges, setReactFlowNodes],
	);

	const handleNodeDragStop = useCallback(() => {
		// Clean up any pending rAF
		if (dragRafRef.current !== null) {
			cancelAnimationFrame(dragRafRef.current);
			dragRafRef.current = null;
		}
		dragStateRef.current.isDragging = false;
		dragStateRef.current.draggedNodeId = null;
		dragStateRef.current.ctrlPressed = false;
		dragStateRef.current.initialPositions.clear();
		dragStateRef.current.pendingPosition = null;
	}, []);

	const handleLoadExecution = useCallback(
		(executionId: string, threadId: string, dbExecutionId: string) => {
			setLoadExecutionData({ executionId, threadId, dbExecutionId });
		},
		[],
	);

	const handleShowNodePalette = useCallback(() => {
		setShowNodePalette(true);
	}, []);

	const handleSetMode = useCallback(
		(mode: "edit" | "evaluate" | "execution") => {
			if (mode === "execution") {
				if (!ensureEndNodeBeforeExecution()) {
					return;
				}
			}
			setMode(mode);
		},
		[ensureEndNodeBeforeExecution],
	);

	const handleRun = useCallback(async () => {
		if (!currentGraph) {
			showError("No graph", "Please create or load a graph first");
			return;
		}

		// Validate node configurations first
		if (!validateNodeConfigurations()) {
			return;
		}

		if (!ensureEndNodeBeforeExecution()) {
			return;
		}

		// CRITICAL: Force sync before execution to ensure all changes are saved
		try {
			await syncService.forceSync();
			console.log("[AgentBuilder] ✅ All changes synced before execution");
		} catch (err) {
			console.error("[AgentBuilder] ❌ Failed to sync before execution:", err);
			showError(
				"Sync failed",
				"Please ensure all changes are saved before executing",
			);
			return;
		}

		setShowExecutionPanel(true);
		handleSetMode("execution");
	}, [
		currentGraph,
		validateNodeConfigurations,
		ensureEndNodeBeforeExecution,
		showError,
		handleSetMode,
	]);

	const handleSave = useCallback(async () => {
		if (!currentGraph) {
			showError("No graph loaded", "Please create or load a graph first");
			return;
		}
		try {
			// Force immediate sync instead of waiting for debounce
			await syncService.forceSync();
			showSuccess("Graph saved", `Successfully saved "${currentGraph.name}"`);
		} catch (err) {
			showError("Save failed", (err as Error).message);
		}
	}, [currentGraph, showSuccess, showError]);

	const handleExport = useCallback(async () => {
		try {
			const data = await exportGraph("full");
			const blob = new Blob([JSON.stringify(data, null, 2)], {
				type: "application/json",
			});
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			const timestamp = new Date()
				.toISOString()
				.replace(/[:.]/g, "-")
				.slice(0, -5);
			a.download = `${currentGraph?.name || "workflow"}_${timestamp}.json`;
			a.click();
			URL.revokeObjectURL(url);
			showSuccess(
				"Graph exported",
				`Exported "${currentGraph?.name}" successfully`,
			);
		} catch (err) {
			showError("Export failed", (err as Error).message);
		}
	}, [exportGraph, currentGraph?.name, showSuccess, showError]);

	const handleExportPython = useCallback(async () => {
		try {
			const code = await exportGraphPython();
			const blob = new Blob([code], { type: "text/x-python" });
			const url = URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			const timestamp = new Date()
				.toISOString()
				.replace(/[:.]/g, "-")
				.slice(0, -5);
			a.download = `${currentGraph?.name || "workflow"}_${timestamp}.py`;
			a.click();
			URL.revokeObjectURL(url);
			showSuccess(
				"Python exported",
				`Exported "${currentGraph?.name}" as Python`,
			);
		} catch (err) {
			showError("Export failed", (err as Error).message);
		}
	}, [exportGraphPython, currentGraph?.name, showSuccess, showError]);

	const handleDuplicate = useCallback(() => {
		if (!currentGraph) {
			showError("No graph loaded", "Please create or load a graph first");
			return;
		}
		setShowDuplicateModal(true);
	}, [currentGraph, showError]);

	const handleDuplicateConfirm = useCallback(
		async (newName: string) => {
			if (!currentGraph) return;
			setIsDuplicating(true);
			try {
				const result = await api.duplicateWorkflow(currentGraph.name, newName);
				setShowDuplicateModal(false);
				showSuccess(
					"Workflow duplicated",
					`Created "${newName}" from "${currentGraph.name}"`,
				);
				sessionStorage.setItem("newWorkflowCreation", "true");
				router.push(`/workflow/${result.workflow_id}`);
			} catch (err) {
				showError("Duplication failed", (err as Error).message);
			} finally {
				setIsDuplicating(false);
			}
		},
		[currentGraph, showSuccess, showError, router],
	);

	const handleReset = useCallback(async () => {
		setShowResetConfirm(true);
	}, []);

	const handleConfirmReset = useCallback(async () => {
		try {
			// Use tracked clearGraph operation (persists to backend)
			await clearGraph();
			resetPanels();
			showInfo("Graph reset", "All nodes and connections have been cleared");
		} catch (err) {
			// User may have cancelled or error occurred
			if (err instanceof Error) {
				showError("Reset failed", err.message);
			}
		}
	}, [clearGraph, resetPanels, showInfo, showError]);

	const handleRefresh = useCallback(async () => {
		console.log(
			"[handleRefresh] Starting refresh, currentGraph:",
			currentGraph,
		);
		if (currentGraph) {
			try {
				await withOverlay(
					async () => {
						await loadGraph(currentGraph.name);
					},
					{ message: "Refreshing workflow...", minDurationMs: 500 },
				);
				console.log(
					"[handleRefresh] Refresh complete, currentGraph after:",
					currentGraph,
				);
				showInfo("Graph refreshed", "Successfully refreshed from backend");
			} catch (err) {
				showError("Refresh failed", (err as Error).message);
			}
		}
	}, [currentGraph, withOverlay, loadGraph, showInfo, showError]);

	const handleReload = useCallback(async () => {
		if (currentGraph) {
			try {
				await withOverlay(
					async () => {
						await reloadGraph();
					},
					{ message: "Reloading workflow...", minDurationMs: 500 },
				);
			} catch (err) {
				showError("Reload failed", (err as Error).message);
			}
		}
	}, [currentGraph, withOverlay, reloadGraph, showError]);

	const handleAutoLayout = useCallback(() => {
		if (!reactFlowInstance.current) {
			showError("Auto Layout Error", "Canvas not ready");
			return;
		}

		// Get current nodes and edges
		const currentNodes = reactFlowInstance.current.getNodes();
		const currentEdges = reactFlowInstance.current.getEdges();

		if (currentNodes.length === 0) {
			showInfo("No nodes", "Add some nodes to the canvas first");
			return;
		}

		// Use React 19 transition to keep UI responsive during layout calculation
		startLayoutTransition(() => {
			try {
				// Apply dagre layout (expensive operation)
				const { nodes: layoutedNodes, edges: layoutedEdges } =
					getLayoutedElements(currentNodes, currentEdges, {
						direction: "LR",
						nodeWidth: 250,
						nodeHeight: 150,
						nodeSeparation: 100,
						rankSeparation: 150,
					});

				// Save current state to history before making changes
				saveToHistory();

				// Update nodes with new positions
				setReactFlowNodes(layoutedNodes);
				setReactFlowEdges(layoutedEdges);

				// Update positions in the store
				const storeState = useGraphStore.getState();
				layoutedNodes.forEach((node) => {
					storeState.updateNodePosition(node.id, node.position);
				});

				// Fit view to show the layouted graph
				setTimeout(() => {
					reactFlowInstance.current?.fitView({ padding: 0.2, duration: 300 });
				}, 50);

				showSuccess(
					"Auto Layout Applied",
					"Graph has been automatically arranged",
				);
			} catch (err) {
				console.error("Auto layout error:", err);
				showError("Auto Layout Failed", (err as Error).message);
			}
		});
	}, [
		saveToHistory,
		setReactFlowNodes,
		setReactFlowEdges,
		showSuccess,
		showError,
		showInfo,
		startLayoutTransition,
	]);

	const handleCloseExecutionPanel = useCallback(() => {
		setShowExecutionPanel(false);
		setExecutingNodeId(null);
		setIsExecuting(false);
		setLoadExecutionData(null); // Clear load data on close
		// Don't clear currentExecution so users can still view results by double-clicking nodes
		// Stay in execution mode after completion to allow viewing results
	}, []);

	const handleOpenEnhancedViewer = useCallback((executionId: string) => {
		setEnhancedExecutionViewerId(executionId);
		setShowEnhancedExecutionViewer(true);
	}, []);

	// Result Drawer
	const handleOpenResultDrawer = useCallback(
		() => setShowResultDrawer(true),
		[],
	);
	const handleCloseResultDrawer = useCallback(
		() => setShowResultDrawer(false),
		[],
	);
	const handleRunAgainFromDrawer = useCallback(() => {
		setShowResultDrawer(false);
		handleRun();
	}, [handleRun]);
	const handleOpenTraceFromDrawer = useCallback(() => {
		const dbId =
			(currentExecution as unknown as Record<string, unknown>)?.db_execution_id ??
			currentExecution?.id;
		if (dbId) {
			handleOpenEnhancedViewer(dbId as string);
			setShowResultDrawer(false);
		}
	}, [currentExecution, handleOpenEnhancedViewer]);

	const handleExecutionChange = useCallback(
		(execData: any) => {
			console.log(
				"[AgentBuilder] === EXECUTION DATA RECEIVED FROM ExecutionPanel ===",
			);
			console.log("[AgentBuilder] execData:", execData);
			console.log("[AgentBuilder] execData.id (WebSocket):", execData?.id);
			console.log(
				"[AgentBuilder] execData.db_execution_id (Database):",
				(execData as any)?.db_execution_id,
			);

			// Close result drawer when starting new execution or clearing
			if (execData === null || execData?.status === "running") {
				setShowResultDrawer(false);
			}

			// Clear running nodes cache only when starting a brand-new execution
			// (not on every tool call notification during an active execution)
			if (
				execData === null ||
				(execData &&
					execData.status === "running" &&
					Object.keys(runningNodesCache).length > 0 &&
					(!execData.node_executions || execData.node_executions.length <= 1))
			) {
				setRunningNodesCache({});
				Object.values(runningNodeTimeouts.current).forEach((timeout) =>
					clearTimeout(timeout),
				);
				runningNodeTimeouts.current = {};
				// console.log('[AgentBuilder] Cleared running nodes cache');
			}

			if (execData && execData.node_executions) {
				console.log(
					"[AgentBuilder] Execution data contains",
					execData.node_executions.length,
					"node executions",
				);
				// console.log('[AgentBuilder] Node execution details received:', execData.node_executions.map((ne: NodeExecution) => ({
				//   node_id: ne.node_id,
				//   node_name: ne.node_name,
				//   status: ne.status,
				//   execution_order: ne.execution_order
				// })));
			} else if (execData === null) {
				// console.log('[AgentBuilder] Execution data cleared (null)');
			} else {
				console.log(
					"[AgentBuilder] Execution data received but no node_executions:",
					execData,
				);
			}

			setCurrentExecution(execData);
			currentExecutionRef.current = execData;
			// console.log('[AgentBuilder] *** CURRENT EXECUTION SET COMPLETE ***');
			// console.log('[AgentBuilder] *** VERIFYING STATE UPDATE - currentExecutionRef.current:', currentExecutionRef.current);
		},
		[runningNodesCache],
	);

	useEffect(() => {
		if (!currentGraph || insertingAgentTemplateRef.current) {
			return;
		}

		const context = getAgentTemplateInsertContext();
		const payload = getAgentTemplateInsertPayload();

		if (!context || !payload) {
			return;
		}

		if (context.workflowId !== currentGraph.workflow_id) {
			return;
		}

		insertingAgentTemplateRef.current = true;
		insertAgentTemplateSubgraph(payload, context)
			.then(() => {
				showSuccess(
					"Agent inserted",
					`"${payload.templateName}" has been added to "${currentGraph.name}".`,
				);
			})
			.catch((error) => {
				console.error("[AgentBuilder] Failed to insert agent template", error);
				showError(
					"Failed to insert agent template",
					(error as Error)?.message || "Unknown error",
				);
			})
			.finally(() => {
				clearAgentTemplateInsertPayload();
				clearAgentTemplateInsertContext();
				insertingAgentTemplateRef.current = false;
			});
	}, [currentGraph, insertAgentTemplateSubgraph, showError, showSuccess]);

	const handleExecutionLoaded = useCallback((execution: any) => {
		console.log("[AgentBuilder] Execution loaded:", execution);
		setCurrentExecution(execution as any);
		currentExecutionRef.current = execution as any;
		setLoadExecutionData(null); // Clear after loading
	}, []);

	const handleCloseSubAgentDialog = useCallback(() => {
		setCreateSubAgentDialog({
			isOpen: false,
			parentAgentId: "",
			parentAgentName: "",
		});
	}, []);

	const handleCloseSubWorkflowDialog = useCallback(() => {
		setCreateSubWorkflowDialog({
			isOpen: false,
			parentAgentId: "",
			parentAgentName: "",
		});
	}, []);

	const handleCloseToolNodeDialog = useCallback(() => {
		setCreateToolNodeDialog({
			isOpen: false,
			parentAgentId: "",
			parentAgentName: "",
		});
	}, []);

	const handleCloseNodePalette = useCallback(() => {
		setShowNodePalette(false);
		setPaletteSourceNodeId(null);
	}, []);

	// Handle template selection from empty state
	const handleApplyTemplate = useCallback(
		async (template: WorkflowTemplate) => {
			if (!currentGraph) return;

			// Skip the START node in template (already exists), create others
			for (let i = 1; i < template.nodes.length; i++) {
				const templateNode = template.nodes[i];
				await handleAddNodeFromPalette(templateNode.type);
			}
		},
		[currentGraph, handleAddNodeFromPalette],
	);

	const handleCloseEnhancedViewer = useCallback(() => {
		setShowEnhancedExecutionViewer(false);
		setEnhancedExecutionViewerId(null);
	}, []);

	return (
		<div
			className="flex h-full w-full flex-col"
			style={{
				background: "var(--color-bg-primary)",
				color: "var(--color-text-primary)",
			}}
		>
			{/* Canvas Top Bar */}
			<CanvasTopBar
				mode={mode}
				onModeChange={handleSetMode}
				isExecuting={isExecuting}
				isRunning={isExecuting}
				currentGraph={currentGraph}
				nodeCount={storeNodes.length}
				isReadOnly={isCollabReadOnly}
				onRun={handleRun}
				onSave={handleSave}
				onAddNode={handleShowNodePalette}
				onExportJson={handleExport}
				onExportPython={handleExportPython}
				onAddToLibrary={onAddToLibrary}
				onReset={handleReset}
				onDuplicate={handleDuplicate}
				onVersionHistory={onVersionHistory}
				onLoadExecution={handleLoadExecution}
				onSetMode={handleSetMode}
				onSetShowExecutionPanel={setShowExecutionPanel}
				workflowId={currentGraph?.workflow_id}
			/>

			{/* Canvas area */}
			<div
				className="flex flex-1 min-h-0 relative"
				onMouseMove={(e) => {
					if (isCollabConnected) {
						updateCursor({ x: e.clientX, y: e.clientY });
					}
				}}
			>

			{/* Collaboration Overlay */}
			<CollaborationOverlay
				users={collabUsers}
				isConnected={isCollabConnected}
				isReadOnly={isCollabReadOnly}
				workflowId={currentGraph?.workflow_id}
				onRequestAccess={requestAccess}
			/>

			{/* Main Canvas */}
			<GraphCanvas
				nodes={nodesWithScores}
				edges={reactFlowEdges}
				isReadOnly={mode === "evaluate" || isCollabReadOnly}
				nodeTypes={builderNodeTypes}
				edgeTypes={builderEdgeTypes}
				defaultEdgeOptions={defaultSmoothEdgeOptions}
				connectionLineComponent={CustomConnectionLine}
				connectionLineStyle={{
					stroke: "#4a4a4a",
					strokeWidth: 3,
				}}
				onInit={handleReactFlowInit}
				onNodesChange={isCollabReadOnly ? undefined : handleNodesChange}
				onEdgesChange={isCollabReadOnly ? undefined : handleEdgesChange}
				onConnect={isCollabReadOnly ? undefined : onConnect}
				onNodeDoubleClick={onNodeDoubleClick}
				onNodesDelete={isCollabReadOnly ? undefined : handleNodesDelete}
				onEdgesDelete={isCollabReadOnly ? undefined : handleEdgesDelete}
				deleteKeyCode={mode === "evaluate" || isCollabReadOnly ? null : "Backspace"}
				onNodeDragStart={isCollabReadOnly ? undefined : handleNodeDragStart}
				onNodeDrag={isCollabReadOnly ? undefined : handleNodeDrag}
				onNodeDragStop={isCollabReadOnly ? undefined : handleNodeDragStop}
				nodesDraggable={!isCollabReadOnly}
				nodesConnectable={!isCollabReadOnly}
				elementsSelectable={!isCollabReadOnly}
				fitView
				fitViewOptions={{ padding: 0.3, maxZoom: 0.85 }}
				snapToGrid={snapToGrid}
				snapGrid={[15, 15]}
				className="bg-[color:var(--color-surface)]"
				wrapperClassName="flex-1 relative"
				wrapperRef={reactFlowWrapper}
				flowExtras={
					<>
						<CustomZoomControls
							orientation="horizontal"
							onAutoLayout={handleAutoLayout}
							snapToGrid={snapToGrid}
							onToggleSnapToGrid={() => setSnapToGrid((prev) => !prev)}
							showMiniMap={showMiniMap}
							onToggleMiniMap={() => setShowMiniMap((prev) => !prev)}
							onShowShortcuts={() => setShowShortcutsHelp(true)}
						/>
						{showMiniMap && storeNodes.length > 3 && (
							<CustomMinimap
								className="!bg-gradient-to-br !from-[color:var(--color-bg-secondary)]/95 !to-[color:var(--color-surface)]/95 !backdrop-blur-xl !border-2 !border-[color:var(--color-primary)]/30 !shadow-2xl !rounded-2xl !overflow-hidden"
								maskColor="rgba(30, 30, 30, 0.4)"
								maskStrokeColor="rgba(var(--color-primary-rgb), 0.5)"
								maskStrokeWidth={2}
								nodeBorderRadius={4}
								width={200}
								height={150}
							/>
						)}
						<Background gap={snapToGrid ? 15 : 12} size={1} color="#4B5563" />
					</>
				}
				overlays={
					<GraphCanvasOverlays
						showNodePalette={showNodePalette}
						onShowNodePalette={handleShowNodePalette}
						onSetPaletteSourceNodeId={setPaletteSourceNodeId}
						onSetPaletteSourceBranchIndex={setPaletteSourceBranchIndex}
						validationMessage={executionValidationHint}
						onDismissValidationMessage={handleDismissValidationHint}
					/>
				}
			/>

			{/* Evaluate Mode Panel */}
			{mode === "evaluate" && currentGraph?.workflow_id && (
				<EvaluateModePanel
					workflowId={currentGraph.workflow_id}
					nodes={reactFlowNodes}
					onClose={() => handleSetMode("edit")}
					onNodeScoresLoaded={setNodeEvalScores}
				/>
			)}

			{/* Duplicate Workflow Modal */}
			<DuplicateWorkflowModal
				isOpen={showDuplicateModal}
				currentName={currentGraph?.name || ""}
				onConfirm={handleDuplicateConfirm}
				onCancel={() => setShowDuplicateModal(false)}
				isSubmitting={isDuplicating}
			/>

			{/* Status Overlays */}
			<AgentBuilderStatusOverlays error={error} loading={loading} />

			{/* Property Panels - Rendered via shared hook */}
			{renderPropertyPanels()}

			{/* Execution Panels - Rendered via shared hook */}
			{renderExecutionPanels()}

			{/* Execution Panel - Using Fixed Version */}
			{currentGraph && (
				<ExecutionPanelFinal
					isOpen={showExecutionPanel}
					onClose={handleCloseExecutionPanel}
					graphName={currentGraph.name}
					onNodeChange={setExecutingNodeId}
					onOpenEnhancedViewer={handleOpenEnhancedViewer}
					onExecutionChange={handleExecutionChange}
					onExecutionStateChange={setIsExecuting}
					// Pass loading data if available
					loadExecutionId={loadExecutionData?.executionId}
					loadThreadId={loadExecutionData?.threadId}
					loadDbExecutionId={loadExecutionData?.dbExecutionId}
					onExecutionLoaded={handleExecutionLoaded}
					onViewResult={handleOpenResultDrawer}
					executionStatus={currentExecution?.status}
					isToolModalOpen={isExecutionDetailOpen}
					workflowId={currentGraph.workflow_id}
				/>
			)}

			</div>{/* end canvas area */}

			{/* Result Drawer - full-page slide-over */}
			<ResultDrawer
				isOpen={showResultDrawer}
				execution={currentExecution}
				graphName={currentGraph?.name ?? ""}
				onClose={handleCloseResultDrawer}
				onRunAgain={handleRunAgainFromDrawer}
				onOpenTrace={handleOpenTraceFromDrawer}
			/>

			{/* Modals and Dialogs */}
			<AgentBuilderModals
				createSubAgentDialog={createSubAgentDialog}
				createSubWorkflowDialog={createSubWorkflowDialog}
				createToolNodeDialog={createToolNodeDialog}
				onCloseSubAgentDialog={handleCloseSubAgentDialog}
				onCloseSubWorkflowDialog={handleCloseSubWorkflowDialog}
				onCloseToolNodeDialog={handleCloseToolNodeDialog}
				onCreateSubAgent={handleCreateSubAgent}
				onCreateSubWorkflow={handleCreateSubWorkflow}
				onCreateToolNode={handleCreateToolNode}
				showNodePalette={showNodePalette}
				paletteSourceNodeId={paletteSourceNodeId}
				onCloseNodePalette={handleCloseNodePalette}
				onAddNodeFromPalette={handleAddNodeFromPalette}
				showEnhancedExecutionViewer={showEnhancedExecutionViewer}
				enhancedExecutionViewerId={enhancedExecutionViewerId}
				onCloseEnhancedViewer={handleCloseEnhancedViewer}
			/>

			<PublishAgentDialog
				isOpen={publishAgentDialog.isOpen}
				agentName={publishAgentDialog.agentName}
				agentDescription={publishAgentDialog.agentDescription}
				isSubmitting={isPublishingAgent}
				onConfirm={handlePublishAgentConfirm}
				onCancel={handlePublishAgentCancel}
			/>

			{/* PHASE 5: Conflict Resolution Dialog */}
			<ConflictResolutionDialog />

			{/* Keyboard Shortcuts Help Dialog */}
			<KeyboardShortcutsDialog
				isOpen={showShortcutsHelp}
				onClose={() => setShowShortcutsHelp(false)}
			/>

			{/* Reset Graph Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showResetConfirm}
				onClose={() => setShowResetConfirm(false)}
				onConfirm={handleConfirmReset}
				title="Reset Graph?"
				message="This will clear all nodes and connections. This action cannot be undone."
				confirmText="Reset"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
