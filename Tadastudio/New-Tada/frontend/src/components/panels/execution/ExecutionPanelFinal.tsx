"use client";

import {
	Activity,
	AlertCircle,
	CheckCircle,
	ChevronDown,
	ChevronRight,
	Clock,
	Code,
	Copy,
	Database,
	ExternalLink,
	FileText,
	GitBranch,
	Globe,
	Info,
	Key,
	Loader2,
	Maximize2,
	MessageCircle,
	MessageSquare,
	Minimize2,
	Network,
	PauseCircle,
	Play,
	Radio,
	RefreshCw,
	Save,
	Send,
	Square,
	StopCircle,
	Upload,
	Wrench,
	X,
	XCircle,
	Zap,
} from "lucide-react";
import type React from "react";
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNotification } from "@/contexts/NotificationContext";
import { useExecutionWebSocket } from "@/hooks/useExecutionWebSocket";
import { api, ExecutionStatus } from "@/lib/api";
import { processContentForRendering } from "@/lib/markdown-utils";
import { useGraphStore } from "@/stores/graphStore";
import { isToolNode } from "@/lib/utils/toolTypes";
import {
	getNodePlaceholder,
	shouldShowPlaceholder,
} from "@/lib/utils/nodePlaceholders";
import {
	ExecutionStatusResponse,
	type GraphExecution,
	type NodeExecution,
} from "@/types/api";
import type {
	ReviewInterruptPayload,
	ReviewResumeResponse,
} from "@/types/review";
import SimpleMarkdown from "../../utils/SimpleMarkdown";
import AgentReviewSection from "./AgentReviewSection";
import CanvasChatPanel from "./CanvasChatPanel";
import ExecutionInputSection from "./ExecutionInputSection";
import ExecutionPanelHeader from "./ExecutionPanelHeader";
import ExecutionPauseStatus from "./ExecutionPauseStatus";

import ReviewResumeDialog from "./ReviewResumeDialog";
import GuardrailBlockModal from "@/components/core/GuardrailBlockModal";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import type { GuardrailViolationEvent } from "@/hooks/useExecutionWebSocket";
import {
	ActivityFeed,
	useExecutionStreaming,
	type ActivityItem,
	type SubAgentActivityItem,
} from "./streaming";

/** Loop membership recorded by the backend on For Each body nodes. */
interface LoopIterationInfo {
	node_id?: string | null;
	iteration?: number | null;
	total?: number | null;
}

interface ExecutionPanelFinalProps {
	isOpen: boolean;
	onClose: () => void;
	graphName: string;
	initialInput?: Record<string, any>;
	onNodeChange?: (nodeId: string | null) => void;
	onExecutionChange?: (executionData: GraphExecution | null) => void;
	onExecutionStateChange?: (isExecuting: boolean) => void;
	onOpenEnhancedViewer?: (executionId: string) => void;
	// Props for loading existing execution
	loadExecutionId?: string; // WebSocket execution ID to load
	loadThreadId?: string; // Thread ID for reconnection
	loadDbExecutionId?: string; // Database execution ID
	onExecutionLoaded?: (execution: GraphExecution) => void;
	// View result
	onViewResult?: () => void;
	executionStatus?: string;
	hasFileReadNodeProp?: boolean;
	// When true, the panel content is blurred to indicate a modal is on top
	isToolModalOpen?: boolean;
	workflowId?: string;
}

export default function ExecutionPanelFinal({
	isOpen,
	onClose,
	graphName,
	initialInput,
	onNodeChange,
	onExecutionChange,
	onExecutionStateChange,
	onOpenEnhancedViewer,
	loadExecutionId,
	loadThreadId,
	loadDbExecutionId,
	onExecutionLoaded,
	onViewResult,
	executionStatus,
	hasFileReadNodeProp,
	isToolModalOpen,
	workflowId,
}: ExecutionPanelFinalProps) {
	const [executionId, setExecutionId] = useState<string | null>(null);
	const [threadId, setThreadId] = useState<string | null>(null); // Store thread ID for resume
	const [dbExecutionId, setDbExecutionId] = useState<string | null>(null);
	const dbExecutionIdRef = useRef<string | null>(null); // Ref to store DB ID immediately
	// REMOVED: status state - WebSocket provides all status updates
	// wsNodeExecutions is the single source of truth for node states
	const [isExecuting, setIsExecuting] = useState(false);
	const [inputMessage, setInputMessage] = useState(initialInput?.message || "");
	const [inputFile, setInputFile] = useState<File | null>(null);
	// TEMPORARILY DISABLED: FILE_READ feature due to ISG security audit
	// Will be re-enabled after fixes are implemented
	const [hasFileReadNode, setHasFileReadNode] = useState(false); // Always false
	// const [hasFileReadNode, setHasFileReadNode] = useState(hasFileReadNodeProp ?? false);
	const [hasRawFileReadNode, setHasRawFileReadNode] = useState(false); // FILE_READ with extraction disabled
	const [hasMCPServerNode, setHasMCPServerNode] = useState(false);
	const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
	const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

	const [isInputExpanded, setIsInputExpanded] = useState(false);
	const [textareaRows, setTextareaRows] = useState(3);
	// Collapsible sections state
	const [isExecutionFlowExpanded, setIsExecutionFlowExpanded] = useState(true);
	const [isInputSectionExpanded, setIsInputSectionExpanded] = useState(true);
	// WebSocket-only state - no polling
	const [wsConnected, setWsConnected] = useState(false);
	// REMOVED: useWebSocket toggle (always true now), pollingIntervalRef (no polling)
	const [isPaused, setIsPaused] = useState(false);
	const [showStartNewConfirm, setShowStartNewConfirm] = useState(false);
	const [pauseInfo, setPauseInfo] = useState<{
		checkpoint_id?: string;
		prompt?: any;
	} | null>(null);
	// pauseInfoRef mirrors pauseInfo state to provide current value in callbacks
	// that may have stale closure over pauseInfo state (e.g., handleResume)
	const pauseInfoRef = useRef<{ checkpoint_id?: string; prompt?: any } | null>(
		null,
	);
	// Removed separate resume input - reuse main inputMessage
	const [isLoadingExecution, setIsLoadingExecution] = useState(false);
	const [isLoadingNodeStatuses, setIsLoadingNodeStatuses] = useState(false);
	const [totalGraphNodes, setTotalGraphNodes] = useState<number | null>(null);
	const loadExecutionRef = useRef<{
		id?: string;
		thread?: string;
		db?: string;
	} | null>(null);
	const [isProcessingResume, setIsProcessingResume] = useState(false); // Track if we're processing a resume
	const [executionRequested, setExecutionRequested] = useState(false);
	const [isManualPause, setIsManualPause] = useState(false);
	const [manualPauseInfo, setManualPauseInfo] = useState<{
		prompt?: string;
	} | null>(null);
	const [isManualResumePending, setIsManualResumePending] = useState(false);
	const [isPausePending, setIsPausePending] = useState(false);
	const [isStopping, setIsStopping] = useState(false);
	const [hasStopped, setHasStopped] = useState(false);
	const [stoppedAt, setStoppedAt] = useState<string | null>(null);
	const [isResumingCheckpoint, setIsResumingCheckpoint] = useState(false);

	// Panel tab state
	const [activeTab, setActiveTab] = useState<"execution" | "chat">("execution");

	// Panel resize state
	const [panelWidth, setPanelWidth] = useState(480);
	const [isResizing, setIsResizing] = useState(false);

	// Agent review state
	const [showReviewDialog, setShowReviewDialog] = useState(false);
	const [isApprovingReview, setIsApprovingReview] = useState(false);
	// Track last acted review iteration to filter stale WebSocket pause events
	const [lastActedReviewIteration, setLastActedReviewIteration] = useState<{
		nodeId: string;
		iteration: number;
	} | null>(null);
	// Ref to access current value in callbacks without stale closure
	const lastActedReviewIterationRef = useRef<{
		nodeId: string;
		iteration: number;
	} | null>(null);

	// Guardrail block modal state
	const [guardrailBlockViolation, setGuardrailBlockViolation] =
		useState<GuardrailViolationEvent | null>(null);

	// Notification hook for error messages
	const { showError, showWarning } = useNotification();

	// Store callbacks in refs to avoid dependency issues
	const onNodeChangeRef = useRef(onNodeChange);
	const onExecutionChangeRef = useRef(onExecutionChange);

	// Unified streaming state management - coordinates timeline and activity feed
	const streaming = useExecutionStreaming({
		executionId,
		dbExecutionId: dbExecutionIdRef.current || dbExecutionId,
		isExecuting,
		onExecutionChange: (data) => {
			onExecutionChangeRef.current?.(data as any);
		},
		onNodeRunning: (nodeId) => {
			onNodeChangeRef.current?.(nodeId);
			setExecutionRequested(false);
		},
		onNodeStopped: () => {
			onNodeChangeRef.current?.(null);
		},
		maxActivities: 50,
		onGuardrailBlock: (event) => setGuardrailBlockViolation(event),
		onGuardrailWarn: (event) => showWarning(event.rule_name, event.message),
	});

	// Destructure for easier access
	const {
		wsNodeExecutions,
		wsNodeExecutionsRef,
		runningNodes,
		activities,
		handlers,
	} = streaming;

	// Update refs when props change
	useEffect(() => {
		onNodeChangeRef.current = onNodeChange;
		onExecutionChangeRef.current = onExecutionChange;
	}, [onNodeChange, onExecutionChange]);

	// Remove automatic sync between isExecuting and runningNodes to prevent flickering
	// isExecuting should only be set false when execution completes, fails, or is paused
	// Not when individual nodes update

	// Update parent with execution state
	useEffect(() => {
		onExecutionStateChange?.(isExecuting);
	}, [isExecuting, onExecutionStateChange]);

	// Sync hasFileReadNode from prop whenever the parent reports a live change
	useEffect(() => {
		if (hasFileReadNodeProp !== undefined) {
			setHasFileReadNode(hasFileReadNodeProp);
		}
	}, [hasFileReadNodeProp]);

	// Subscribe to React Flow nodes to detect file nodes dynamically
	const storeNodes = useGraphStore((state) => state.nodes);

	// Detect FILE_READ nodes from React Flow nodes or backend data
	// FILE_READ can be either in workflow path OR connected as a tool to an Agent
	useEffect(() => {
		if (hasFileReadNodeProp !== undefined) return; // parent is driving this

		// Only FILE_READ needs file upload dropzone (FILE_WRITE generates files, doesn't read them)
		const fileNodeTypes = ["FILE_READ"];

		// Helper: check both React Flow format (node.data.type) and backend format (node.type)
		// This handles multi-user scenarios where updates may come in different formats
		const isFileNode = (node: any) => {
			const nodeType = node.data?.type || node.type;
			return fileNodeTypes.includes(nodeType);
		};

		// Always disable file read for security updates
		setHasFileReadNode(false);
	}, [storeNodes, graphName, hasFileReadNodeProp]);

	// Detect MCP_SERVER nodes from React Flow nodes or backend data
	// When MCP server is present, allow both file upload AND message input together
	useEffect(() => {
		const isMCPNode = (node: any) => {
			const nodeType = node.data?.type || node.type;
			return nodeType === "MCP_SERVER";
		};

		// Check React Flow nodes (includes dynamically added nodes)
		if (storeNodes && storeNodes.length > 0) {
			const hasMCP = storeNodes.some(isMCPNode);
			setHasMCPServerNode(hasMCP);
			return;
		}

		// Fallback: Check backend graph data
		const storeGraph = useGraphStore.getState().currentGraph;
		if (storeGraph && storeGraph.name === graphName && storeGraph.nodes) {
			const hasMCP = storeGraph.nodes.some(isMCPNode);
			setHasMCPServerNode(hasMCP);
			return;
		}

		// Last resort: API call
		const checkForMCPNodes = async () => {
			try {
				const response = await api.getGraph(graphName);
				if (response.success && response.graph && response.graph.nodes) {
					const hasMCP = Object.values(response.graph.nodes).some(isMCPNode);
					setHasMCPServerNode(hasMCP);
				}
			} catch (error) {
				console.error("Failed to check for MCP nodes:", error);
			}
		};

		if (graphName) {
			checkForMCPNodes().catch((error) => {
				console.error("Failed to check for MCP nodes:", error);
			});
		}
	}, [storeNodes, graphName]);

	// Detect FILE_READ nodes with raw/disabled extraction mode
	// These use persistent file storage for MCP/RAG queries
	useEffect(() => {
		const isRawFileReadNode = (node: any) => {
			const nodeType = node.data?.type || node.type;
			if (nodeType !== "FILE_READ") return false;
			// Check config for extraction_mode = "raw" or "disabled"
			const config = node.data?.config || node.config || {};
			const extractionMode = config.extraction_mode || config.extractionMode;
			return extractionMode === "raw" || extractionMode === "disabled";
		};

		// Check React Flow nodes
		if (storeNodes && storeNodes.length > 0) {
			const hasRaw = storeNodes.some(isRawFileReadNode);
			setHasRawFileReadNode(hasRaw);
			return;
		}

		// Fallback: Check backend graph data
		const storeGraph = useGraphStore.getState().currentGraph;
		if (storeGraph && storeGraph.name === graphName && storeGraph.nodes) {
			const hasRaw = storeGraph.nodes.some(isRawFileReadNode);
			setHasRawFileReadNode(hasRaw);
			return;
		}

		// Last resort: API call
		const checkForRawFileReadNodes = async () => {
			try {
				const response = await api.getGraph(graphName);
				if (response.success && response.graph && response.graph.nodes) {
					const hasRaw = Object.values(response.graph.nodes).some(isRawFileReadNode);
					setHasRawFileReadNode(hasRaw);
				}
			} catch (error) {
				console.error("Failed to check for raw FILE_READ nodes:", error);
			}
		};

		if (graphName) {
			checkForRawFileReadNodes().catch((error) => {
				console.error("Failed to check for raw FILE_READ nodes:", error);
			});
		}
	}, [storeNodes, graphName]);

	// Load existing execution when props change
	useEffect(() => {
		if (loadExecutionId && loadThreadId && loadDbExecutionId) {
			// Check if we're already tracking this execution
			if (loadExecutionId === executionId) {
				return;
			}

			// Store the load request
			loadExecutionRef.current = {
				id: loadExecutionId,
				thread: loadThreadId,
				db: loadDbExecutionId,
			};

			// Load the execution state
			loadExistingExecution();
		} else if (loadExecutionId && loadThreadId && !loadDbExecutionId) {
			// Watch a live HTTP-triggered execution (dbExecutionId not yet available)
			if (loadExecutionId === executionId) return;
			watchLiveExecution(loadExecutionId);
		}
	}, [loadExecutionId, loadThreadId, loadDbExecutionId]);

	const loadExistingExecution = useCallback(async () => {
		if (!loadExecutionRef.current) return;

		const { id, thread, db } = loadExecutionRef.current;
		if (!db) {
			console.warn("[LOAD] No database execution ID provided");
			return;
		}
		setIsLoadingExecution(true);

		try {
			// Get the full execution state from the API
			const executionState = await api.getExecutionState(db);

			// Set execution IDs
			setExecutionId(id || null);
			setThreadId(executionState.execution.thread_id || thread || null); // Use thread_id from API or fallback
			setDbExecutionId(db);
			dbExecutionIdRef.current = db;

			// Start loading node statuses
			setIsLoadingNodeStatuses(true);

			// Load node executions using the timeline hook
			if (executionState.nodes && Array.isArray(executionState.nodes)) {
				streaming.loadInitialData(executionState.nodes);
			}

			// Finish loading node statuses
			setIsLoadingNodeStatuses(false);

			// Set total graph nodes count from graph definition (excluding tool nodes)
			if (
				executionState.graph_definition &&
				executionState.graph_definition.nodes
			) {
				const nodes = Array.isArray(executionState.graph_definition.nodes)
					? executionState.graph_definition.nodes
					: Object.values(executionState.graph_definition.nodes);

				const workflowNodeCount = nodes.filter((node: any) => {
					// Exclude tool-type nodes from the graph definition count
					const toolTypes = [
						"TOOL",
						"HTTP_REQUEST",
						"WEB_SEARCH",
						"DOCUMENT_SEARCH",
						"DATABASE_QUERY",
						"MCP_SERVER",
						"DATABASE_INSERT",
						"DATABASE_QUERY_ACTION",
						"HTTP_REQUEST_ACTION",
					];
					// Check both node.type and node.node_type for compatibility
					const nodeType = node.type || node.node_type;
					return !toolTypes.includes(nodeType);
				}).length;

				setTotalGraphNodes(workflowNodeCount);
			}

			// Set execution status
			const status = executionState.execution.status;

			if (status === "paused") {
				const checkpointState = executionState.checkpoint_state;
				const isManual = checkpointState?.manual === true;

				setIsPaused(true);
				setIsExecuting(false);
				setIsPausePending(false);
				setIsStopping(false);
				setHasStopped(false);
				setStoppedAt(null);
				setIsManualPause(isManual);
				setIsManualResumePending(false);

				if (isManual) {
					setManualPauseInfo({ prompt: checkpointState?.prompt });
					setPauseInfo(null);
					pauseInfoRef.current = null;
				} else if (checkpointState) {
					// Check if this is an agent review pause (new system)
					const isAgentReviewFromAPI =
						checkpointState.review_checkpoint === true &&
						checkpointState.interrupt_payload?.type === "agent_review";

					const newPauseInfo = {
						checkpoint_id: checkpointState.checkpoint_id,
						// For agent reviews, use interrupt_payload as the prompt
						// Otherwise fall back to legacy prompt field
						prompt: isAgentReviewFromAPI
							? checkpointState.interrupt_payload
							: checkpointState.prompt,
					};

					setPauseInfo(newPauseInfo);
					pauseInfoRef.current = newPauseInfo;
					setManualPauseInfo(null);
				} else {
					setPauseInfo(null);
					pauseInfoRef.current = null;
					setManualPauseInfo(null);
				}
			} else if (status === "pause_pending") {
				setIsPausePending(true);
				setIsPaused(false);
				setIsStopping(false);
				setHasStopped(false);
				setStoppedAt(null);
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
			} else if (status === "stop_requested" || status === "stopping") {
				setIsStopping(true);
				setIsExecuting(false);
				setIsPaused(false);
				setPauseInfo(null);
				pauseInfoRef.current = null;
				setIsPausePending(false);
				setHasStopped(false);
				setStoppedAt(null);
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
			} else if (status === "stopped") {
				setHasStopped(true);
				setIsStopping(false);
				setIsPausePending(false);
				setIsPaused(false);
				setPauseInfo(null);
				pauseInfoRef.current = null;
				setIsExecuting(false);
				setStoppedAt(
					executionState.execution.end_time || new Date().toISOString(),
				);
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
			} else if (status === "running") {
				setIsExecuting(true);
				setIsPaused(false);
				setIsPausePending(false);
				setIsStopping(false);
				setHasStopped(false);
				setStoppedAt(null);
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
			} else {
				// Completed, failed, or other terminal states
				setIsExecuting(false);
				setIsPaused(false);
				setPauseInfo(null);
				pauseInfoRef.current = null;
				setIsPausePending(false);
				setIsStopping(false);
				setHasStopped(false);
				setStoppedAt(null);
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
			}

			// Now attempt to reconnect WebSocket
			// The WebSocket hook will handle this when executionId changes

			// Notify parent that execution was loaded
			if (onExecutionLoaded && executionState.execution) {
				onExecutionLoaded(executionState.execution);
			}
		} catch (error) {
			console.error("[LOAD] Failed to load execution:", error);
		} finally {
			setIsLoadingExecution(false);
			loadExecutionRef.current = null;
		}
	}, [onExecutionLoaded]);

	// Watch a live HTTP-triggered execution (no DB history to load)
	const watchLiveExecution = useCallback(
		(liveExecutionId: string) => {
			// Reset execution state (mirrors startExecution lines 1081-1098)
			setIsExecuting(true);
			setExecutionRequested(true);
			setIsPaused(false);
			setIsManualPause(false);
			setManualPauseInfo(null);
			setIsManualResumePending(false);
			setIsPausePending(false);
			setIsStopping(false);
			setHasStopped(false);
			setStoppedAt(null);
			setPauseInfo(null);
			pauseInfoRef.current = null;
			setDbExecutionId(null);
			dbExecutionIdRef.current = null;
			streaming.clearState();
			setTotalGraphNodes(null);
			setLastActedReviewIteration(null);
			lastActedReviewIterationRef.current = null;

			// Collapse input, expand execution flow
			setIsInputSectionExpanded(false);
			setIsExecutionFlowExpanded(true);

			// Clear parent callbacks
			onNodeChangeRef.current?.(null);
			onExecutionChangeRef.current?.(null);

			// Notify parent execution is active
			onExecutionStateChange?.(true);

			// Set execution ID — triggers useExecutionWebSocket to connect
			setExecutionId(liveExecutionId);

			// Async: fetch graph definition for total node count (non-blocking)
			api.getGraph(graphName)
				.then((graphResponse) => {
					if (graphResponse.success && graphResponse.graph?.nodes) {
						const nodes = Array.isArray(graphResponse.graph.nodes)
							? graphResponse.graph.nodes
							: Object.values(graphResponse.graph.nodes);
						const toolTypes = [
							"TOOL",
							"HTTP_REQUEST",
							"WEB_SEARCH",
							"DOCUMENT_SEARCH",
							"DATABASE_QUERY",
							"MCP_SERVER",
							"DATABASE_INSERT",
							"DATABASE_QUERY_ACTION",
							"HTTP_REQUEST_ACTION",
						];
						const workflowNodeCount = nodes.filter((node: any) => {
							const nodeType = node.type || node.node_type;
							return !toolTypes.includes(nodeType);
						}).length;
						setTotalGraphNodes(workflowNodeCount);
					}
				})
				.catch((err) => {
					console.warn("[WATCH] Could not fetch graph definition for node count:", err);
				});
		},
		[graphName, streaming, onExecutionStateChange],
	);

	const startNewWorkflow = useCallback(async () => {
		// Show confirmation dialog (handled by state)
		setShowStartNewConfirm(true);
	}, []);

	const handleResume = useCallback(async () => {
		try {
			const resumeThreadId = threadId || executionId;
			if (!resumeThreadId) {
				console.error("Missing thread ID for resume");
				alert(
					"Cannot resume: Missing thread ID. Please refresh and try again.",
				);
				return;
			}

			// Use ref as fallback if state is stale in this callback closure
			const effectivePauseInfo = pauseInfo || pauseInfoRef.current;

			if (!effectivePauseInfo?.checkpoint_id) {
				console.error("Missing checkpoint_id for resume");
				alert(
					"Cannot resume: Missing checkpoint ID. Please refresh and try again.",
				);
				return;
			}

			// Capture the checkpoint ID we're resuming for comparison later
			const resumingCheckpointId = effectivePauseInfo.checkpoint_id;
			const value = inputMessage || "";

			// Update UI state immediately to show resuming
			setExecutionRequested(true);
			setIsPausePending(false);
			setIsStopping(false);
			setHasStopped(false);
			setStoppedAt(null);
			setIsManualPause(false);
			setManualPauseInfo(null);
			setIsManualResumePending(false);
			setIsPaused(false);
			setIsExecuting(true);
			setIsProcessingResume(true);
			setIsResumingCheckpoint(true);

			await api.resumeFromCheckpoint({
				graph_name: graphName,
				thread_id: resumeThreadId,
				checkpoint_id: resumingCheckpointId,
				new_input: typeof value === "string" ? { value } : value,
			});

			// Only clear pauseInfo if it still has the same checkpoint ID we just resumed
			// This prevents race conditions where a new pause arrives while processing the resume
			const currentPauseInfo = pauseInfoRef.current || pauseInfo;
			if (currentPauseInfo?.checkpoint_id === resumingCheckpointId) {
				setPauseInfo(null);
				pauseInfoRef.current = null;
			}
		} catch (e) {
			console.error("Failed to resume from checkpoint:", e);
			// Reset state on error
			setIsPaused(true);
			setIsExecuting(false);
			setIsProcessingResume(false);
			setExecutionRequested(false);
			setIsResumingCheckpoint(false);
		}
	}, [
		executionId,
		threadId,
		pauseInfo,
		inputMessage,
		graphName,
		isExecuting,
		isPaused,
		wsConnected,
	]);

	const handlePause = useCallback(async () => {
		if (!dbExecutionIdRef.current) {
			showError("Unable to pause execution: missing execution identifier.");
			return;
		}
		if (isPaused || isPausePending || hasStopped) {
			return;
		}

		try {
			setIsPausePending(true);
			setIsStopping(false);
			setHasStopped(false);
			setStoppedAt(null);
			setIsManualPause(false);
			setManualPauseInfo(null);
			setIsManualResumePending(false);
			setExecutionRequested(false);

			await api.pauseExecution(dbExecutionIdRef.current);
		} catch (error) {
			console.error("Failed to request pause:", error);
			setIsPausePending(false);
			showError("Failed to request pause.");
		}
	}, [isPaused, isPausePending, hasStopped, showError]);

	const handleManualResume = useCallback(async () => {
		if (!dbExecutionIdRef.current) {
			showError("Unable to resume execution: missing execution identifier.");
			return;
		}
		if (!isManualPause || isManualResumePending) {
			return;
		}

		try {
			setIsManualResumePending(true);
			setExecutionRequested(true);

			await api.resumeManualExecution(dbExecutionIdRef.current);

			setIsManualPause(false);
			setManualPauseInfo(null);
			setIsPaused(false);
			setPauseInfo(null);
			pauseInfoRef.current = null;
			setIsExecuting(true);
			setIsManualResumePending(false);
			setIsPausePending(false);
		} catch (error) {
			console.error("Failed to resume manual pause:", error);
			setIsManualResumePending(false);
			setIsManualPause(true);
			setIsPausePending(false);
			setExecutionRequested(false);
			showError("Failed to resume workflow.");
		}
	}, [isManualPause, isManualResumePending, showError]);

	const handleStop = useCallback(async () => {
		if (!dbExecutionIdRef.current) {
			showError("Unable to stop execution: missing execution identifier.");
			return;
		}
		if (hasStopped || isStopping) {
			return;
		}

		try {
			setIsStopping(true);
			// Clear all execution state immediately for responsive UI
			setIsPausePending(false);
			setIsPaused(false);
			setPauseInfo(null);
			pauseInfoRef.current = null;
			setIsManualPause(false);
			setManualPauseInfo(null);
			setIsManualResumePending(false);
			setIsExecuting(false);
			setExecutionRequested(false);

			// Mark all running nodes as stopped in the timeline immediately
			streaming.markAllNodesAsStopped();

			// Request hard stop from backend
			await api.stopExecution(dbExecutionIdRef.current);

			// Mark as stopped immediately after successful API call
			setHasStopped(true);
			setStoppedAt(new Date().toISOString());
		} catch (error) {
			console.error("Failed to request hard stop:", error);
			setIsStopping(false);
			showError("Failed to stop execution.");
		}
	}, [hasStopped, isStopping, showError, streaming]);

	// Agent review detection with comprehensive logging
	const isAgentReview = pauseInfo?.prompt?.type === "agent_review";
	const reviewPayload = isAgentReview
		? (pauseInfo?.prompt as ReviewInterruptPayload)
		: null;


	// Handle quick approve for agent review
	const handleQuickApprove = useCallback(async () => {
		if (!threadId && !executionId) {
			showError("Cannot approve: Missing thread ID.");
			return;
		}

		const effectivePauseInfo = pauseInfo || pauseInfoRef.current;
		if (!effectivePauseInfo?.checkpoint_id) {
			showError("Cannot approve: Missing checkpoint ID.");
			return;
		}

		const resumeThreadId = threadId || executionId;
		const resumingCheckpointId = effectivePauseInfo.checkpoint_id;

		try {
			setIsApprovingReview(true);
			setExecutionRequested(true);
			setIsPaused(false);
			setIsExecuting(true);

			// Record this iteration to filter stale pause events from WebSocket
			if (reviewPayload) {
				const actedIteration = {
					nodeId: reviewPayload.node_id,
					iteration: reviewPayload.current_iteration,
				};
				setLastActedReviewIteration(actedIteration);
				lastActedReviewIterationRef.current = actedIteration;
			}

			// Clear pauseInfo BEFORE the API call to avoid race condition where
			// a new pause arrives during await and gets wiped out after
			setPauseInfo(null);
			pauseInfoRef.current = null;

			const response: ReviewResumeResponse = { approved: true };
			await api.resumeFromCheckpoint({
				graph_name: graphName,
				thread_id: resumeThreadId!,
				checkpoint_id: resumingCheckpointId,
				new_input: { value: JSON.stringify(response) },
			});
		} catch (error) {
			console.error("handleQuickApprove failed:", error);
			setIsPaused(true);
			setIsExecuting(false);
			setExecutionRequested(false);
			showError("Failed to approve review.");
		} finally {
			setIsApprovingReview(false);
		}
	}, [threadId, executionId, pauseInfo, graphName, showError, reviewPayload]);

	// Open full review dialog
	const handleOpenReviewDialog = useCallback(() => {
		setShowReviewDialog(true);
	}, []);

	// Handle resume from review dialog (approve or reject with feedback)
	const handleReviewResume = useCallback(
		async (_executionId: string, response: ReviewResumeResponse) => {
			if (!threadId && !executionId) {
				showError("Cannot resume: Missing thread ID.");
				return;
			}

			const effectivePauseInfo = pauseInfo || pauseInfoRef.current;
			if (!effectivePauseInfo?.checkpoint_id) {
				showError("Cannot resume: Missing checkpoint ID.");
				return;
			}

			const resumeThreadId = threadId || executionId;
			const resumingCheckpointId = effectivePauseInfo.checkpoint_id;

			try {
				setShowReviewDialog(false);
				setExecutionRequested(true);
				setIsPaused(false);
				setIsExecuting(true);

				// Record this iteration to filter stale pause events from WebSocket
				if (reviewPayload) {
					const actedIteration = {
						nodeId: reviewPayload.node_id,
						iteration: reviewPayload.current_iteration,
					};
					setLastActedReviewIteration(actedIteration);
					lastActedReviewIterationRef.current = actedIteration;
				}

				// Clear pauseInfo BEFORE the API call to avoid race condition where
				// a new pause arrives during await and gets wiped out after
				setPauseInfo(null);
				pauseInfoRef.current = null;

				await api.resumeFromCheckpoint({
					graph_name: graphName,
					thread_id: resumeThreadId!,
					checkpoint_id: resumingCheckpointId,
					new_input: { value: JSON.stringify(response) },
				});
			} catch (error) {
				console.error("handleReviewResume failed:", error);
				setIsPaused(true);
				setIsExecuting(false);
				setExecutionRequested(false);
				showError("Failed to submit review.");
			}
		},
		[threadId, executionId, pauseInfo, graphName, showError, reviewPayload],
	);

	// Auto-resize textarea based on content
	useEffect(() => {
		if (!isInputExpanded) {
			const lines = inputMessage.split("\n");
			const lineCount = lines.length;

			// Also consider long lines that would wrap
			const charPerLine = 80; // approximate characters per line
			let totalLines = lineCount;

			lines.forEach((line: string) => {
				if (line.length > charPerLine) {
					totalLines += Math.floor(line.length / charPerLine);
				}
			});

			// Set rows between 3 and 10 when not expanded
			const rows = Math.max(3, Math.min(10, totalLines));
			setTextareaRows(rows);
		}
	}, [inputMessage, isInputExpanded]);

	// WebSocket handlers - now using timeline hook for state management

	const handleExecutionComplete = useCallback(
		(result: any) => {
			// Clear all pause/stop states when execution completes
			setIsPaused(false);
			setPauseInfo(null);
			pauseInfoRef.current = null;
			setIsStopping(false);
			setIsPausePending(false);
			setHasStopped(false);
			setStoppedAt(null);
			setIsProcessingResume(false);
			setIsManualPause(false);
			setManualPauseInfo(null);
			setIsManualResumePending(false);
			setIsExecuting(false);
			setExecutionRequested(false);
			// Clear stale pause filter
			setLastActedReviewIteration(null);
			lastActedReviewIterationRef.current = null;
			onNodeChangeRef.current?.(null);

			// Update final execution data with complete node executions from ref
			const finalExecutionData = {
				id: executionId || dbExecutionId,
				status: "completed" as const,
				node_executions: Array.from(wsNodeExecutionsRef.current.values()),
				output_data: result,
			};
			onExecutionChangeRef.current?.(finalExecutionData as any);
		},
		[executionId, dbExecutionId, isProcessingResume, runningNodes],
	);

	const handleExecutionError = useCallback((error: string) => {
		console.error("Execution error:", error);
		// Clear all pause/stop states when execution fails
		setIsPaused(false);
		setPauseInfo(null);
		pauseInfoRef.current = null;
		setIsExecuting(false);
		setIsStopping(false);
		setIsPausePending(false);
		setHasStopped(false);
		setStoppedAt(null);
		setIsManualPause(false);
		setManualPauseInfo(null);
		setIsManualResumePending(false);
		setExecutionRequested(false);
		// Clear stale pause filter
		setLastActedReviewIteration(null);
		lastActedReviewIterationRef.current = null;
		onNodeChangeRef.current?.(null);
		// Mark all running nodes as stopped so the trace view transitions out of "running"
		streaming.markAllNodesAsStopped();
	}, [streaming]);

	useEffect(() => {
		// Don't override paused state - when paused, isExecuting should remain false
		// even if there are "running" nodes (they're actually paused for review)
		const shouldExecute =
			!isPaused &&
			(runningNodes.size > 0 ||
				executionRequested ||
				isManualResumePending ||
				isProcessingResume);

		if (shouldExecute !== isExecuting) {
			setIsExecuting(shouldExecute);
		}
	}, [
		runningNodes,
		executionRequested,
		isManualResumePending,
		isProcessingResume,
		isExecuting,
		isPaused,
	]);

	const handleConnectionChange = useCallback((connected: boolean) => {
		setWsConnected(connected);
	}, []);

	const fallbackToPolling = useCallback(() => {
		// No polling fallback - WebSocket will reconnect automatically
	}, []);

	// Use WebSocket hook
	// Keep WebSocket connection alive even after execution completes to preserve node data
	const {
		isConnected: wsConnected2,
		connectionError,
		disconnect: wsDisconnect,
	} = useExecutionWebSocket(
		executionId, // Always use WebSocket - no toggle needed
		{
			enabled: true, // Always enabled - WebSocket is our only real-time source
			onNodeUpdate: handlers.onNodeUpdate,
			onExecutionComplete: handleExecutionComplete,
			onExecutionError: handleExecutionError,
			onConnectionChange: handleConnectionChange,
			onTokenStream: handlers.onTokenStream,
			// Streaming activity handlers for tool calls and sub-agent delegations
			onToolCallStart: handlers.onToolCallStart,
			onToolCallProgress: handlers.onToolCallProgress,
			onToolCallComplete: handlers.onToolCallComplete,
			onToolCallError: handlers.onToolCallError,
			onSubAgentStart: handlers.onSubAgentStart,
			onSubAgentComplete: handlers.onSubAgentComplete,
			onContentChunk: handlers.onContentChunk,
			onGuardrailViolation: handlers.onGuardrailViolation,
			onInitialStatus: (dbId) => {
				if (dbId) {
					dbExecutionIdRef.current = dbId; // Update ref immediately
					setDbExecutionId(dbId); // Also update state for other uses
				}
			},
			// Pass reconnection data if loading an existing execution
			reconnectData: loadExecutionRef.current
				? {
						threadId: loadThreadId || "",
						dbExecutionId: loadDbExecutionId || "",
					}
				: undefined,
			onPaused: (info) => {
				if (info?.manual) {
					// Manual pause (user-initiated)
					setIsManualPause(true);
					setManualPauseInfo({
						prompt:
							typeof info.prompt === "string"
								? info.prompt
								: info.prompt?.prompt,
					});
					setIsManualResumePending(false);
					setPauseInfo(null);
					pauseInfoRef.current = null;
				} else {
					// Checkpoint or agent review pause
					const newPauseInfo = {
						checkpoint_id: info?.checkpoint_id,
						prompt: info?.prompt,
					};

					const isAgentReviewWS = info?.prompt?.type === "agent_review";

					// Filter stale agent_review pause events
					// After user takes action on iteration N, ignore any pause events for iteration <= N
					if (isAgentReviewWS && lastActedReviewIterationRef.current) {
						const incomingNodeId = info.prompt.node_id;
						const incomingIteration = info.prompt.current_iteration;
						const lastActed = lastActedReviewIterationRef.current;

						if (
							incomingNodeId === lastActed.nodeId &&
							incomingIteration <= lastActed.iteration
						) {
							return; // Don't update state with stale data
						}

						// New iteration arrived, clear the filter
						setLastActedReviewIteration(null);
						lastActedReviewIterationRef.current = null;
					}

					setPauseInfo(newPauseInfo);
					pauseInfoRef.current = newPauseInfo;
					setIsManualPause(false);
					setManualPauseInfo(null);
					setIsManualResumePending(false);
				}

				setIsPaused(true);
				setIsExecuting(false);
				setIsPausePending(false);
				setIsStopping(false);
				setHasStopped(false);
				setStoppedAt(null);
				setExecutionRequested(false);
				setIsResumingCheckpoint(false);
			},
			onResumed: () => {
				setIsPaused(false);
				setPauseInfo(null);
				pauseInfoRef.current = null;
				setIsExecuting(true);
				setExecutionRequested(true);
				setIsProcessingResume(false);
				setIsPausePending(false);
				setIsStopping(false);
				setHasStopped(false);
				setStoppedAt(null);
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
				setIsResumingCheckpoint(false);
			},
			onPausePending: (_info) => {
				setIsPausePending(true);
			},
			onStopRequested: (_info) => {
				setIsStopping(true);
				setIsPausePending(false);
				setHasStopped(false);
				setStoppedAt(null);
				setIsPaused(false);
				setPauseInfo(null);
				pauseInfoRef.current = null;
				setIsExecuting(false);
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
				setExecutionRequested(false);
			},
			onStopped: (info) => {
				setIsStopping(false);
				setIsPausePending(false);
				setIsPaused(false);
				setPauseInfo(null);
				pauseInfoRef.current = null;
				setIsExecuting(false);
				setHasStopped(true);
				setStoppedAt(info?.timestamp || new Date().toISOString());
				setIsManualPause(false);
				setManualPauseInfo(null);
				setIsManualResumePending(false);
				setExecutionRequested(false);
				// Mark all running nodes as stopped in the timeline
				streaming.markAllNodesAsStopped();

				// CRITICAL: Also notify onExecutionChange so AgentBuilder's currentExecution is updated
				// This ensures canvas nodes get the "stopped" status and stop showing the spinner
				const stoppedExecutionData = {
					db_execution_id: dbExecutionIdRef.current,
					status: "stopped" as const,
					graph_name: info?.graph_name,
					node_executions: Array.from(streaming.wsNodeExecutionsRef.current.values()),
				};
				onExecutionChangeRef.current?.(stoppedExecutionData as any);

				// Clear stale pause filter
				setLastActedReviewIteration(null);
				lastActedReviewIterationRef.current = null;
			},
			fallbackToPolling: fallbackToPolling,
		},
	);

	// Update wsConnected state
	useEffect(() => {
		setWsConnected(wsConnected2);
	}, [wsConnected2]);

	// Clean up WebSocket only when panel closes
	useEffect(() => {
		return () => {
			if (!isOpen) {
				wsDisconnect?.();
			}
		};
	}, [isOpen, wsDisconnect]);

	// Monitor wsNodeExecutions changes - keep ref in sync with state
	useEffect(() => {
		wsNodeExecutionsRef.current = wsNodeExecutions;
	}, [wsNodeExecutions]);

	// Start execution
	const startExecution = async () => {
		try {
			// Clear previous state
			setIsExecuting(true);
			setExecutionRequested(true);
			setIsPaused(false);
			setIsManualPause(false);
			setManualPauseInfo(null);
			setIsManualResumePending(false);
			setIsPausePending(false);
			setIsStopping(false);
			setHasStopped(false);
			setStoppedAt(null);
			setPauseInfo(null);
			pauseInfoRef.current = null;
			// Status tracking removed - WebSocket handles all updates
			setExecutionId(null);
			setDbExecutionId(null);
			dbExecutionIdRef.current = null; // Clear ref too
			streaming.clearState(); // Clear previous execution data and activity feed
			setTotalGraphNodes(null); // Reset total nodes count

			// Auto-collapse sections when starting execution
			setIsInputSectionExpanded(false);
			setIsExecutionFlowExpanded(true); // Keep results expanded

			onNodeChangeRef.current?.(null);
			onExecutionChangeRef.current?.(null);

			// console.log('[ExecutionPanelFinal] Starting execution for graph:', graphName);

			// Try to get graph definition to know total nodes (excluding tool nodes)
			try {
				const graphResponse = await api.getGraph(graphName);
				if (
					graphResponse.success &&
					graphResponse.graph &&
					graphResponse.graph.nodes
				) {
					// Filter out tool nodes from the count - only count workflow nodes
					const nodes = Array.isArray(graphResponse.graph.nodes)
						? graphResponse.graph.nodes
						: Object.values(graphResponse.graph.nodes);

					const workflowNodeCount = nodes.filter((node: any) => {
						// Exclude tool-type nodes from the graph definition count
						const toolTypes = [
							"TOOL",
							"HTTP_REQUEST",
							"WEB_SEARCH",
							"DOCUMENT_SEARCH",
							"DATABASE_QUERY",
							"MCP_SERVER",
							"DATABASE_INSERT",
							"DATABASE_QUERY_ACTION",
							"HTTP_REQUEST_ACTION",
						];
						// Check both node.type and node.node_type for compatibility
						const nodeType = node.type || node.node_type;
						return !toolTypes.includes(nodeType);
					}).length;

					setTotalGraphNodes(workflowNodeCount);
				}
			} catch (err) {
				console.warn(
					"[ExecutionPanelFinal] Could not fetch graph definition for node count:",
					err,
				);
			}

			let response;

			// Use execute-with-file endpoint when:
			// 1. A file is selected, OR
			// 2. There's a FILE_READ node (backend will check for persistent file)
			// 3. Persistent storage is enabled (MCP server or raw FILE_READ)
			const usePersistentStorage = hasRawFileReadNode || hasMCPServerNode;
			if (hasFileReadNode || usePersistentStorage) {
				const formData = new FormData();
				formData.append("graph_name", graphName);
				formData.append("async_execution", "true");
				formData.append("message", inputMessage);
				if (inputFile) {
					formData.append("file", inputFile);
				}

				const uploadResponse = await fetch(`/api/graph/execute-with-file`, {
					method: "POST",
					body: formData,
				});

				if (!uploadResponse.ok) {
					throw new Error("Failed to execute with file");
				}

				response = await uploadResponse.json();
			} else {
				// Standard execution without file
				response = await api.executeGraph({
					graph_name: graphName,
					initial_input: { message: inputMessage },
					async_execution: true,
				});
			}

			if (response.success && response.execution_id) {
				// console.log('[ExecutionPanelFinal] Execution started:', response.execution_id);
				setExecutionId(response.execution_id);

				// Get initial status to find DB ID - retry a few times if needed
				let dbIdFound = false;
				for (let i = 0; i < 5 && !dbIdFound; i++) {
					if (i > 0) {
						// Wait a bit before retrying
						await new Promise((resolve) => setTimeout(resolve, 200));
					}

					try {
						const statusResponse = await api.getExecutionStatus(
							response.execution_id,
						);

						if (statusResponse.success && statusResponse.execution_status) {
							// Check for db_execution_id in the response
							const dbId = statusResponse.execution_status.db_execution_id;
							if (dbId) {
								dbExecutionIdRef.current = dbId; // Update ref immediately
								setDbExecutionId(dbId);
								dbIdFound = true;
							}
						}
					} catch (statusError) {
						console.error(
							`[ExecutionPanelFinal] Error getting status on attempt ${i + 1}:`,
							statusError,
						);
					}
				}

				if (!dbIdFound) {
					console.warn(
						"[ExecutionPanelFinal] Could not get db_execution_id after 5 attempts",
					);
				}
			}
		} catch (error) {
			console.error("Failed to start execution:", error);
			setIsExecuting(false);
			setExecutionRequested(false);

			// Parse and display error message to user
			let errorMessage =
				"An unexpected error occurred while starting the workflow.";
			let errorTitle = "Execution Failed";

			if (error && typeof error === "object") {
				// Check for validation errors (400 status)
				if ("detail" in error && typeof error.detail === "string") {
					// Backend validation error format: "Graph 'Name' validation failed: [errors]"
					const detail = error.detail;

					// Extract specific error message if it's a validation error
					if (detail.includes("validation failed:")) {
						errorTitle = "Workflow Validation Failed";
						const parts = detail.split("validation failed:");
						errorMessage = parts[1]?.trim() || detail;

						// Add helpful hint if it's an LLM configuration error
						if (errorMessage.includes("LLM configuration is required")) {
							errorMessage +=
								"\n\nPlease configure an LLM model for agent nodes. Visit Settings → LLM Providers to add model deployments.";
						}
					} else {
						errorMessage = detail;
					}
				} else if ("message" in error && typeof error.message === "string") {
					errorMessage = error.message;
				}
			} else if (typeof error === "string") {
				errorMessage = error;
			}

			// Show error notification
			showError(errorTitle, errorMessage);
		}
	};

	// Handler for confirm start new workflow - must be after startExecution
	const handleConfirmStartNew = useCallback(async () => {
		// Clear pause state
		setIsPaused(false);
		setPauseInfo(null);
		pauseInfoRef.current = null;
		setIsManualPause(false);
		setManualPauseInfo(null);
		setIsManualResumePending(false);
		setIsPausePending(false);
		setIsStopping(false);
		setHasStopped(false);
		setStoppedAt(null);

		// Clear execution state
		setExecutionId(null);
		setDbExecutionId(null);
		dbExecutionIdRef.current = null;
		streaming.clearState();
		setExecutionRequested(false);

		// Start fresh execution
		await startExecution();
	}, [streaming]);

	const handleClose = () => {
		setIsExecuting(false);
		onNodeChangeRef.current?.(null);
		onClose();
	};

	const openEnhancedViewer = () => {
		if (dbExecutionId) {
			if (onOpenEnhancedViewer) {
				// Use the callback to open the viewer as a modal
				onOpenEnhancedViewer(dbExecutionId);
			} else {
				// Fallback to the old navigation behavior if no callback provided
				const executionData = {
					graphName,
					executionId,
					dbExecutionId,
					status: "completed", // Status from WebSocket
					results: Array.from(wsNodeExecutions.values()), // Results from WebSocket
				};
				localStorage.setItem(
					"execution-viewer-data",
					JSON.stringify(executionData),
				);

				const viewerUrl = `/execution-viewer/${dbExecutionId}`;
				window.location.href = viewerUrl;
			}
		}
	};

	// Handle HTTP-triggered execution
	const handleHttpExecution = (httpExecutionId: string) => {
		// console.log('[ExecutionPanelFinal] HTTP execution detected:', httpExecutionId);

		// Set the execution ID and start monitoring
		setExecutionId(httpExecutionId);
		setIsExecuting(true);
		// Status tracking removed - WebSocket handles all updates
		streaming.clearState();

		// Clear any db execution ID so polling can find it
		setDbExecutionId(null);
		dbExecutionIdRef.current = null; // Clear ref too

		// The polling effect will automatically start due to the executionId change
	};

	const toggleNodeExpansion = (nodeId: string) => {
		const newExpanded = new Set(expandedNodes);
		if (newExpanded.has(nodeId)) {
			newExpanded.delete(nodeId);
		} else {
			newExpanded.add(nodeId);
		}
		setExpandedNodes(newExpanded);
	};

	const toggleToolExpansion = (nodeId: string) => {
		const newExpanded = new Set(expandedTools);
		if (newExpanded.has(nodeId)) {
			newExpanded.delete(nodeId);
		} else {
			newExpanded.add(nodeId);
		}
		setExpandedTools(newExpanded);
	};

	const formatOutput = (output: unknown): string => {
		// Use our utility function to process content
		const processed = processContentForRendering(output);

		if (processed) {
			return processed;
		}

		// Fallback to original string processing if utility didn't work
		if (typeof output === "string") {
			return output;
		}
		if (output && typeof output === "object") {
			const obj = output as Record<string, any>;

			// Special handling for CONDITION node output
			if ("branch_taken" in obj && "source_handle" in obj) {
				return `Branch taken: **${obj.branch_label || obj.source_handle || "Unknown"}**${
					obj.condition_result ? ` (Result: ${obj.condition_result})` : ""
				}`;
			}

			// Special handling for FILE_READ output
			if (
				"content" in obj &&
				"metadata" in obj &&
				obj.metadata?.extraction_method
			) {
				const metadata = obj.metadata;
				let formattedOutput = "### 📄 File Processed Successfully\n\n";

				// Add metadata section
				formattedOutput += "**File Information:**\n";
				formattedOutput += `- **Filename**: ${metadata.filename || "Unknown"}\n`;
				formattedOutput += `- **Type**: ${metadata.file_type || metadata.extension || "Unknown"}\n`;
				if (metadata.file_size_mb) {
					formattedOutput += `- **Size**: ${metadata.file_size_mb.toFixed(2)} MB\n`;
				}
				if (metadata.page_count) {
					formattedOutput += `- **Pages**: ${metadata.page_count}\n`;
				}
				formattedOutput += `- **Extraction Method**: ${metadata.extraction_method}\n`;
				if (metadata.ocr_confidence) {
					formattedOutput += `- **OCR Confidence**: ${(metadata.ocr_confidence * 100).toFixed(1)}%\n`;
				}
				if (metadata.processing_time) {
					formattedOutput += `- **Processing Time**: ${metadata.processing_time.toFixed(2)}s\n`;
				}

				formattedOutput += "\n---\n\n";

				// Add content section
				if (obj.content) {
					formattedOutput += "**Extracted Content:**\n\n";
					// Truncate very long content for display
					const content =
						typeof obj.content === "string"
							? obj.content
							: JSON.stringify(obj.content, null, 2);
					if (content.length > 5000) {
						formattedOutput +=
							content.substring(0, 5000) +
							"\n\n... (content truncated for display)";
					} else {
						formattedOutput += content;
					}
				}

				// Add structured data if present
				if (obj.structured_data) {
					formattedOutput += "\n\n**Structured Data:**\n```json\n";
					formattedOutput += JSON.stringify(obj.structured_data, null, 2);
					formattedOutput += "\n```";
				}

				return formattedOutput;
			}

			// Special handling for document search results
			if (obj.total_queries !== undefined && obj.results !== undefined) {
				// Format as code block to avoid markdown interpretation
				return `\`\`\`json\n${JSON.stringify(output, null, 2)}\n\`\`\``;
			}

			// Special handling for EMAIL_SEND node output
			if (
				"message_id" in obj &&
				"to" in obj &&
				"subject" in obj &&
				"status" in obj
			) {
				return (
					`**Email Sent Successfully** ✉️\n\n` +
					`**To:** ${obj.to}\n` +
					`**Subject:** ${obj.subject}\n` +
					`**Status:** ${obj.status}\n` +
					`**Message ID:** ${obj.message_id}`
				);
			}

			// For END node results array
			if (Array.isArray(output)) {
				return output
					.map((item: Record<string, any>) =>
						item.response
							? `**${item.agent}**: ${item.response}`
							: JSON.stringify(item),
					)
					.join("\n\n---\n\n");
			}

			if (obj.messages && Array.isArray(obj.messages)) {
				const lastMessage = obj.messages[obj.messages.length - 1];
				if (lastMessage?.content) return lastMessage.content;
			}

			// Default: format as code block to avoid markdown interpretation
			return `\`\`\`json\n${JSON.stringify(output, null, 2)}\n\`\`\``;
		}
		if (output === undefined || output === null) return "";
		return String(output);
	};

	const getNodeStatusIcon = (result: any) => {
		// Type to be fixed when ExecutionResult is imported
		switch (result.status) {
			case "completed":
				return <CheckCircle className="w-4 h-4 text-[#0DA931]" />;
			case "failed":
				return <XCircle className="w-4 h-4 text-red-500" />;
			case "stopped":
				return <StopCircle className="w-4 h-4 text-orange-400" />;
			default:
				return (
					<Loader2 className="w-4 h-4 text-[color:var(--color-accent)] animate-spin" />
				);
		}
	};

	const getToolIcon = (toolType: string) => {
		switch (toolType) {
			case "DATABASE_QUERY":
				return <Database className="w-3 h-3 text-emerald-400" />;
			case "DOCUMENT_SEARCH":
				return (
					<FileText className="w-3 h-3 text-[color:var(--color-text-muted)]" />
				);
			case "HTTP_REQUEST":
				return <Globe className="w-3 h-3 text-purple-400" />;
			case "WEB_SEARCH":
				return <Globe className="w-3 h-3 text-orange-400" />;
			default:
				return (
					<Wrench className="w-3 h-3 text-[color:var(--color-text-muted)]" />
				);
		}
	};

	const getStatusBadgeInfo = (status?: string) => {
		switch (status) {
			case "completed":
				return {
					label: "Completed",
					className:
						"border border-[#0DA931] bg-[#F1F8E9] text-[#0DA931]",
				};
			case "failed":
				return {
					label: "Failed",
					className: "border border-red-400 bg-red-50 text-red-600",
				};
			case "stopped":
				return {
					label: "Stopped",
					className:
						"border border-orange-400 bg-orange-50 text-orange-600",
				};
			case "running":
				return {
					label: "In Progress",
					className:
						"border border-[color:var(--color-accent)]/35 bg-[color:var(--color-accent)]/12 text-[color:var(--color-accent)]",
				};
			case "queued":
				return {
					label: "Queued",
					className:
						"border border-[color:var(--color-border)]/50 bg-[color:var(--color-border)]/20 text-[color:var(--color-text-muted)]",
				};
			default:
				return {
					label: status
						? status.charAt(0).toUpperCase() + status.slice(1)
						: "Pending",
					className:
						"border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-muted)]",
				};
		}
	};

	const getNodeTypeStyle = (nodeType?: string) => {
		const base = {
			cardBorder: "border-[color:var(--color-border)]/50",
			iconContainer:
				"border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/50 text-[color:var(--color-text-muted)]",
			dot: "border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)] ring-2 ring-[color:var(--color-border)]/15",
			dotActive:
				"border border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/80 ring-2 ring-[color:var(--color-accent)]/30",
		};

		switch (nodeType) {
			case "START":
				return {
					...base,
					cardBorder: "border-[#0DA931]/35",
					iconContainer: "border-[#0DA931]/30 bg-[#0DA931]/12 text-[#0DA931]",
					dot: "border border-[#0DA931]/60 bg-[#0DA931]/30 ring-2 ring-[#0DA931]/15",
					dotActive:
						"border border-[#0DA931] bg-[#0DA931]/80 ring-2 ring-[#0DA931]/30 shadow-[0_0_8px_rgba(74,222,128,0.4)]",
				};
			case "END":
				return {
					...base,
					cardBorder: "border-red-500/35",
					iconContainer: "border-red-500/30 bg-red-500/12 text-red-300",
					dot: "border border-red-400/60 bg-red-500/30 ring-2 ring-red-400/15",
					dotActive:
						"border border-red-300 bg-red-500/80 ring-2 ring-red-400/30 shadow-[0_0_8px_rgba(248,113,113,0.4)]",
				};
			case "AGENT":
				return {
					...base,
					cardBorder: "border-[color:var(--color-accent)]/35",
					iconContainer:
						"border-[color:var(--color-accent)]/35 bg-[color:var(--color-accent)]/12 text-[color:var(--color-accent)]",
					dot: "border border-[color:var(--color-accent)]/50 bg-[color:var(--color-accent)]/25 ring-2 ring-[color:var(--color-accent)]/15",
					dotActive:
						"border border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/80 ring-2 ring-[color:var(--color-accent)]/30",
				};
			case "CHECKPOINT":
				return {
					...base,
					cardBorder: "border-purple-500/35",
					iconContainer:
						"border-purple-500/30 bg-purple-500/12 text-purple-600",
					dot: "border border-purple-400/60 bg-purple-500/30 ring-2 ring-purple-400/15",
					dotActive:
						"border border-purple-300 bg-purple-500/80 ring-2 ring-purple-400/30 shadow-[0_0_8px_rgba(168,85,247,0.4)]",
				};
			case "REVIEW":
				return {
					...base,
					cardBorder: "border-cyan-500/35",
					iconContainer: "border-cyan-500/30 bg-cyan-500/12 text-cyan-600",
					dot: "border border-cyan-400/60 bg-cyan-500/30 ring-2 ring-cyan-400/15",
					dotActive:
						"border border-cyan-300 bg-cyan-500/80 ring-2 ring-cyan-400/30 shadow-[0_0_8px_rgba(34,211,238,0.4)]",
				};
			case "CONDITION":
				return {
					...base,
					cardBorder: "border-orange-500/35",
					iconContainer:
						"border-orange-500/30 bg-orange-500/12 text-orange-300",
					dot: "border border-orange-400/60 bg-orange-500/30 ring-2 ring-orange-400/15",
					dotActive:
						"border border-orange-300 bg-orange-500/80 ring-2 ring-orange-400/30 shadow-[0_0_8px_rgba(251,146,60,0.4)]",
				};
			case "DATABASE_QUERY":
			case "DATABASE_INSERT":
			case "DATABASE_QUERY_ACTION":
				return {
					...base,
					cardBorder: "border-emerald-500/35",
					iconContainer:
						"border-emerald-500/30 bg-emerald-500/12 text-emerald-600",
					dot: "border border-emerald-400/60 bg-emerald-500/30 ring-2 ring-emerald-400/15",
					dotActive:
						"border border-emerald-300 bg-emerald-500/80 ring-2 ring-emerald-400/30 shadow-[0_0_8px_rgba(52,211,153,0.4)]",
				};
			case "HTTP_REQUEST":
			case "HTTP_REQUEST_ACTION":
				return {
					...base,
					cardBorder: "border-violet-500/35",
					iconContainer:
						"border-violet-500/30 bg-violet-500/12 text-violet-600",
					dot: "border border-violet-400/60 bg-violet-500/30 ring-2 ring-violet-400/15",
					dotActive:
						"border border-violet-300 bg-violet-500/80 ring-2 ring-violet-400/30 shadow-[0_0_8px_rgba(167,139,250,0.4)]",
				};
			case "WEB_SEARCH":
				return {
					...base,
					cardBorder: "border-orange-500/35",
					iconContainer:
						"border-orange-500/30 bg-orange-500/12 text-orange-300",
					dot: "border border-orange-400/60 bg-orange-500/30 ring-2 ring-orange-400/15",
					dotActive:
						"border border-orange-300 bg-orange-500/80 ring-2 ring-orange-400/30 shadow-[0_0_8px_rgba(251,146,60,0.4)]",
				};
			case "DOCUMENT_SEARCH":
				return {
					...base,
					cardBorder: "border-[color:var(--color-border)]/50",
					iconContainer:
						"border-[color:var(--color-border)]/50 bg-[color:var(--color-border)]/20 text-[color:var(--color-text-muted)]",
					dot: "border border-[color:var(--color-border)]/60 bg-[color:var(--color-border)]/40 ring-2 ring-[color:var(--color-border)]/15",
					dotActive:
						"border border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/80 ring-2 ring-[color:var(--color-accent)]/30",
				};
			case "EMAIL_SEND":
				return {
					...base,
					cardBorder: "border-[#0DA931]/35",
					iconContainer: "border-[#0DA931]/30 bg-[#0DA931]/12 text-[#0DA931]",
					dot: "border border-[#0DA931]/60 bg-[#0DA931]/30 ring-2 ring-[#0DA931]/15",
					dotActive:
						"border border-[#0DA931] bg-[#0DA931]/80 ring-2 ring-[#0DA931]/30 shadow-[0_0_8px_rgba(74,222,128,0.4)]",
				};
			case "FILE_READ":
				return {
					...base,
					cardBorder: "border-emerald-500/35",
					iconContainer:
						"border-emerald-500/30 bg-emerald-500/12 text-emerald-600",
					dot: "border border-emerald-400/60 bg-emerald-500/30 ring-2 ring-emerald-400/15",
					dotActive:
						"border border-emerald-300 bg-emerald-500/80 ring-2 ring-emerald-400/30 shadow-[0_0_8px_rgba(52,211,153,0.4)]",
				};
			default:
				return base;
		}
	};

	// Event handlers to replace arrow functions in JSX
	const handleToggleInputSection = useCallback(() => {
		setIsInputSectionExpanded(!isInputSectionExpanded);
	}, [isInputSectionExpanded]);

	const handleToggleInputExpanded = useCallback(() => {
		setIsInputExpanded(!isInputExpanded);
	}, [isInputExpanded]);

	const handleStartExecution = useCallback(() => {
		startExecution().catch((error) => {
			console.error("Failed to start execution:", error);
		});
	}, [startExecution]);

	const handleToggleExecutionFlowExpanded = useCallback(() => {
		setIsExecutionFlowExpanded(!isExecutionFlowExpanded);
	}, [isExecutionFlowExpanded]);

	// Panel resize handlers
	const handleResizeStart = useCallback(
		(event: React.MouseEvent | React.TouchEvent) => {
			event.preventDefault();
			setIsResizing(true);
		},
		[],
	);

	useEffect(() => {
		if (!isResizing) {
			return;
		}

		const handlePointerMove = (event: MouseEvent | TouchEvent) => {
			const clientX =
				event instanceof TouchEvent
					? (event.touches[0]?.clientX ?? event.changedTouches[0]?.clientX)
					: event.clientX;

			if (clientX == null) {
				return;
			}

			// Calculate width from right edge of viewport to mouse position
			const newWidth = window.innerWidth - clientX;
			// Enforce minimum width of 380px
			setPanelWidth(Math.max(380, newWidth));
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

	// Factory functions for dynamic handlers with parameters
	const createNodeExpansionHandler = useCallback(
		(expansionKey: string) => () => {
			toggleNodeExpansion(expansionKey);
		},
		[toggleNodeExpansion],
	);

	const createToolExpansionHandler = useCallback(
		(expansionKey: string) => () => {
			toggleToolExpansion(expansionKey);
		},
		[toggleToolExpansion],
	);

	const nonToolNodes = useMemo(() => {
		return Array.from(wsNodeExecutions.values()).filter(
			(node) => !isToolNode(node.node_type),
		);
	}, [wsNodeExecutions]);

	const executionTimeline = useMemo(() => {
		const allNodes = Array.from(wsNodeExecutions.values());

		// Group tools by parent_agent_id + step (invocation_index)
		// This ensures each subagent invocation gets only its own tools
		const toolsByParentAndStep = new Map<string, typeof allNodes>();

		allNodes.forEach((node) => {
			if (isToolNode(node.node_type as string) && node.parent_agent_id) {
				// Use step (invocation_index) to distinguish tools from different invocations
				const stepKey = node.step ?? 1;
				const compositeKey = `${node.parent_agent_id}_${stepKey}`;
				const tools = toolsByParentAndStep.get(compositeKey) || [];
				tools.push(node);
				toolsByParentAndStep.set(compositeKey, tools);
			}
		});

		const filtered = allNodes
			.filter(
				(node) =>
					!isToolNode(node.node_type) &&
					(node.status === "completed" ||
						node.status === "failed" ||
						node.status === "running" ||
						node.status === "stopped" ||
						node.output_data),
			)
			.sort((a, b) => {
				if (a.timestamp && b.timestamp) {
					return (
						new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
					);
				}
				return 0;
			});

		const totals = new Map<string, number>();
		filtered.forEach((node) => {
			const current = totals.get(node.node_id) || 0;
			totals.set(node.node_id, current + 1);
		});

		const counts = new Map<string, number>();

		return filtered.map((node, index) => {
			const count = (counts.get(node.node_id) || 0) + 1;
			counts.set(node.node_id, count);

			const key = node.id || `${node.node_id}-${index}`;

			// Match tools by node_id + step (invocation_index from backend)
			// Use node.step from backend, fallback to count for backwards compatibility
			const stepKey = node.step ?? count;
			const toolKey = `${node.node_id}_${stepKey}`;

			const matchedTools = toolsByParentAndStep.get(toolKey) || [];

			// Loop membership, set by the backend for For Each body nodes. Used
			// to group a loop's runs instead of listing look-alike rows.
			const loopInfo = (
				node as { node_metadata?: { for_each?: LoopIterationInfo } }
			).node_metadata?.for_each;

			return {
				key,
				node: {
					...node,
					tool_executions: matchedTools,
				},
				iteration: count,
				totalExecutions: totals.get(node.node_id) || count,
				loop:
					loopInfo && typeof loopInfo.iteration === "number"
						? loopInfo
						: null,
			};
		});
	}, [wsNodeExecutions]);

	const executionStats = useMemo(() => {
		// Count unique nodes by node_id to handle re-executions correctly
		const uniqueNodeIds = new Set(nonToolNodes.map((node) => node.node_id));
		const total = uniqueNodeIds.size;
		const completed = new Set(
			nonToolNodes
				.filter((node) => node.status === "completed")
				.map((node) => node.node_id),
		).size;
		const failed = new Set(
			nonToolNodes
				.filter((node) => node.status === "failed")
				.map((node) => node.node_id),
		).size;
		const running = new Set(
			nonToolNodes
				.filter((node) => node.status === "running")
				.map((node) => node.node_id),
		).size;
		const lastUpdatedDate = nonToolNodes.reduce<Date | null>((latest, node) => {
			if (!node.timestamp) return latest;
			const nodeTime = new Date(node.timestamp);
			if (!latest || nodeTime.getTime() > latest.getTime()) {
				return nodeTime;
			}
			return latest;
		}, null);

		return {
			total,
			completed,
			failed,
			running,
			lastUpdated: lastUpdatedDate ? lastUpdatedDate.toISOString() : null,
		};
	}, [nonToolNodes]);

	const lastUpdatedLabel = executionStats.lastUpdated
		? new Date(executionStats.lastUpdated).toLocaleTimeString()
		: null;

	const hasTimelineData = executionTimeline.length > 0;

	const statusVariant = hasStopped
		? "stopped"
		: isStopping
			? "stopping"
			: isPausePending && !isPaused
				? "pause_pending"
				: isPaused
					? "paused"
					: isExecuting
						? "running"
						: "ready";

	const statusBadgeClassMap: Record<string, string> = {
		stopped: "border border-red-400 bg-red-50 text-red-600",
		stopping: "border border-red-400 bg-red-50 text-red-600",
		pause_pending:
			"border border-orange-400 bg-orange-50 text-orange-600",
		paused:
			"border border-orange-400 bg-orange-50 text-orange-600",
		running:
			"border border-orange-400 bg-orange-50 text-orange-600",
		ready:
			"border border-slate-300 bg-slate-50 text-slate-600",
	};

	if (!isOpen) return null;

	return (
		<aside
			data-tutorial="execution-panel"
			className="fixed inset-y-0 right-0 z-50 flex"
			style={{ width: `${panelWidth}px` }}
		>
			{/* Resize handle */}
			<div
				className={`absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize z-10 transition-colors ${
					isResizing
						? "bg-[color:var(--color-primary)]"
						: "hover:bg-[color:var(--color-primary)]/50"
				}`}
				onMouseDown={handleResizeStart}
				onTouchStart={handleResizeStart}
			/>
			<div
				className={`relative flex h-full w-full flex-col border-l-2 border-orange-400/60 bg-gradient-to-br from-white via-orange-50 to-orange-100 text-gray-800 shadow-[0_35px_120px_rgba(0,0,0,0.35)] animate-slideIn${isToolModalOpen ? " pointer-events-none" : ""}`}
				style={{
					filter: isToolModalOpen ? "blur(3px) brightness(0.7)" : "none",
					transition: "filter 0.2s ease-out",
				}}
			>
				{isLoadingNodeStatuses && (
					<div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-4 bg-gradient-to-br from-white via-orange-50 to-orange-100 backdrop-blur-sm">
						<div className="h-12 w-12 animate-spin rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.35)] border-t-[color:var(--color-accent)]" />
						<p className="text-sm text-[color:var(--color-text-muted)]">
							Loading execution state...
						</p>
					</div>
				)}

				<ExecutionPanelHeader
					graphName={graphName}
					dbExecutionId={dbExecutionId}
					onClose={handleClose}
					onOpenEnhancedViewer={openEnhancedViewer}
				/>

				{workflowId && (
					<div className="flex shrink-0 border-b border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/35">
						<button
							type="button"
							onClick={() => setActiveTab("execution")}
							className={`flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-semibold transition-colors focus-visible:outline-none ${activeTab === "execution" ? "border-b-2 border-[color:var(--color-accent)] text-[color:var(--color-text-primary)]" : "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)]"}`}
						>
							<Zap className="h-3.5 w-3.5" />
							Execution
						</button>
						<button
							type="button"
							onClick={() => setActiveTab("chat")}
							className={`flex flex-1 items-center justify-center gap-1.5 py-2.5 text-xs font-semibold transition-colors focus-visible:outline-none ${activeTab === "chat" ? "border-b-2 border-[color:var(--color-accent)] text-[color:var(--color-text-primary)]" : "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-primary)]"}`}
						>
							<MessageCircle className="h-3.5 w-3.5" />
							Chat
						</button>
					</div>
				)}

				{/* Chat panel — always mounted when workflowId is present so React state
				    (messages, sessionId) survives tab switches. Hidden via CSS only. */}
				{workflowId && (
					<div className={`flex-1 overflow-hidden ${activeTab !== "chat" ? "hidden" : ""}`}>
						<CanvasChatPanel workflowId={workflowId} graphName={graphName} />
					</div>
				)}

				{(activeTab !== "chat" || !workflowId) && (<>

				<ExecutionPauseStatus
					isPaused={isPaused}
					isPausePending={isPausePending}
					isStopping={isStopping}
					hasStopped={hasStopped}
					stoppedAt={stoppedAt}
					pauseInfo={pauseInfo}
					isManualPause={isManualPause}
					manualPauseInfo={manualPauseInfo}
				/>

				<ExecutionInputSection
					isPaused={isPaused}
					isManualPause={isManualPause}
					isInputSectionExpanded={isInputSectionExpanded}
					isInputExpanded={isInputExpanded}
					isExecuting={isExecuting}
					isResumingCheckpoint={isResumingCheckpoint}
					hasFileReadNode={hasFileReadNode}
					hasRawFileReadNode={hasRawFileReadNode}
					hasMCPServerNode={hasMCPServerNode}
					inputMessage={inputMessage}
					inputFile={inputFile}
					textareaRows={textareaRows}
					pauseInfo={pauseInfo}
					graphName={graphName}
					onToggleInputSection={handleToggleInputSection}
					onToggleInputExpanded={handleToggleInputExpanded}
					onMessageChange={setInputMessage}
					onFileSelect={setInputFile}
					onStartExecution={handleStartExecution}
					onResume={handleResume}
					onStartNewWorkflow={startNewWorkflow}
				/>

				{/* Agent Review Section - shown when paused for agent review */}
				{isPaused && isAgentReview && reviewPayload && (
					<AgentReviewSection
						reviewPayload={reviewPayload}
						executionId={executionId || ""}
						threadId={threadId || ""}
						graphName={graphName}
						onApprove={handleQuickApprove}
						onOpenReviewDialog={handleOpenReviewDialog}
						isLoading={isApprovingReview}
					/>
				)}

				<div className="flex-1 overflow-hidden">
						<section data-tutorial="execution-timeline" className="flex h-full flex-col">
							<div className="flex items-center justify-between border-b border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/35 px-6 py-4">
								<button
									onClick={handleToggleExecutionFlowExpanded}
									className="flex flex-1 items-center justify-between text-left transition-colors hover:text-[color:var(--color-text-primary)] focus-visible:outline-none"
									type="button"
								>
									<div className="flex items-center gap-3">
										<div className="flex h-9 w-9 items-center justify-center rounded-xl border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-accent)]">
											<Zap className="h-4 w-4" />
										</div>
										<div className="space-y-0.5">
											<p className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
												Timeline
											</p>
											<p className="text-sm font-semibold text-[color:var(--color-text-primary)]">
												Execution Flow
											</p>
										</div>
									</div>
									<div className="flex items-center gap-3">
										{isExecuting && (
											<span className="inline-flex items-center gap-1.5 rounded-full border border-[rgba(var(--color-primary-rgb),0.50)] bg-[rgba(var(--color-primary-rgb),0.12)] px-2.5 py-1 text-[11px] font-medium text-orange-600">
												<Loader2 className="h-3 w-3 animate-spin text-orange-500" />
												Streaming
											</span>
										)}
										{isExecutionFlowExpanded ? (
											<ChevronDown className="h-4 w-4 text-[color:var(--color-text-muted)]" />
										) : (
											<ChevronRight className="h-4 w-4 text-[color:var(--color-text-muted)]" />
										)}
									</div>
								</button>
								<div className="ml-4 flex shrink-0 items-center gap-2">
									{isManualPause ? (
										<button
											onClick={handleManualResume}
											disabled={isManualResumePending}
											className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.50)] ${
												isManualResumePending
													? "cursor-not-allowed border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 text-[color:var(--color-text-muted)]"
													: "border-[rgba(var(--color-primary-rgb),0.50)] bg-[rgba(var(--color-primary-rgb),0.15)] text-orange-600 hover:bg-[rgba(var(--color-primary-rgb),0.25)]"
											}`}
											type="button"
										>
											{isManualResumePending ? (
												<>
													<Loader2 className="h-3 w-3 animate-spin text-orange-500" />
													Resuming…
												</>
											) : (
												<>
													<Play className="h-3 w-3" />
													Resume
												</>
											)}
										</button>
									) : (
										<button
											onClick={handlePause}
											disabled={
												isPausePending ||
												isStopping ||
												hasStopped ||
												isPaused ||
												!isExecuting
											}
											className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-warning)]/50 ${
												isPausePending ||
												isStopping ||
												hasStopped ||
												isPaused ||
												!isExecuting
													? "cursor-not-allowed border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 text-[color:var(--color-text-muted)]"
													: "border-[color:var(--color-warning)]/50 bg-[color:var(--color-warning)]/15 text-[color:var(--color-warning-light)] hover:bg-[color:var(--color-warning)]/25"
											}`}
											type="button"
										>
											<PauseCircle className="h-3 w-3" />
											Pause
										</button>
									)}
									<button
										onClick={handleStop}
										disabled={
											isStopping ||
											hasStopped ||
											(!isExecuting && !isPausePending && !isManualPause)
										}
										className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/50 ${
											isStopping ||
											hasStopped ||
											(!isExecuting && !isPausePending && !isManualPause)
												? "cursor-not-allowed border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 text-[color:var(--color-text-muted)]"
												: "border-red-500/50 bg-red-500/15 text-red-600 hover:bg-red-500/25"
										}`}
										type="button"
									>
										{isStopping ? (
											<Loader2 className="h-3 w-3 animate-spin text-orange-500" />
										) : (
											<Square className="h-3 w-3 fill-current" />
										)}
										Stop Now
									</button>
								</div>
							</div>

							{!isExecuting &&
								onViewResult &&
								(executionStatus === "completed" ||
									executionStatus === "failed" ||
									executionStatus === "stopped") && (
									<button
										type="button"
										onClick={onViewResult}
										className="mx-4 mt-3 mb-2 flex items-center justify-center gap-2 rounded-lg border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.10)] px-3 py-2.5 text-sm font-medium text-[color:var(--color-text-primary)] transition-all hover:bg-[rgba(var(--color-primary-rgb),0.20)] hover:border-[rgba(var(--color-primary-rgb),0.50)] cursor-pointer"
									>
										{executionStatus === "failed" ? (
											<XCircle className="h-4 w-4 text-red-400" />
										) : executionStatus === "stopped" ? (
											<StopCircle className="h-4 w-4 text-amber-400" />
										) : (
											<CheckCircle className="h-4 w-4 text-[#0DA931]" />
										)}
										{executionStatus === "failed"
											? "View Error"
											: executionStatus === "stopped"
												? "Execution Stopped"
												: "View Result"}
										<ChevronRight className="h-4 w-4 text-[color:var(--color-text-muted)]" />
									</button>
								)}

							{isExecutionFlowExpanded && (
								<div className="flex-1 overflow-y-auto px-6 pb-8 pt-6 custom-scrollbar">
									{!hasTimelineData ? (
										<div className="flex h-full flex-col items-center justify-center gap-4 text-center">
											<div className="h-10 w-10 animate-spin rounded-full border-2 border-[rgba(var(--color-primary-rgb),0.35)] border-t-[color:var(--color-accent)]" />
											<p className="text-sm text-[color:var(--color-text-muted)]">
												Waiting for execution results...
											</p>
										</div>
									) : (
										<div className="relative">
											<div className="absolute left-4 top-0 h-full w-px bg-[color:var(--color-border)]/30" />
											<div className="space-y-3 pl-10">
												{(() => { let _firstAgentTagged = false; let _prevLoopKey: string | null = null; return executionTimeline.map(
													({ key, node, iteration, totalExecutions, loop }) => {
														const expansionKey = key;
														const _isFirstAgent = !_firstAgentTagged && node.node_type === "AGENT";
														if (_isFirstAgent) _firstAgentTagged = true;

														// Start a new group whenever the loop iteration changes, so a
														// loop's runs read as blocks instead of repeated rows.
														const loopKey = loop
															? `${loop.node_id ?? ""}#${loop.iteration}`
															: null;
														const startsLoopGroup = loopKey !== null && loopKey !== _prevLoopKey;
														_prevLoopKey = loopKey;
														const statusInfo = getStatusBadgeInfo(node.status);
														const timestampLabel = node.timestamp
															? new Date(node.timestamp).toLocaleTimeString()
															: null;
														const durationLabel =
															typeof node.duration_seconds === "number"
																? `${node.duration_seconds.toFixed(2)}s`
																: null;
														const isReExecution = totalExecutions > 1;
														const isCurrent = node.status === "running";
														const nodeStyle = getNodeTypeStyle(node.node_type);

														const loopHeader = startsLoopGroup && loop ? (
															<div
																key={`${expansionKey}-loop-header`}
																className="relative flex items-center gap-2 pt-2"
															>
																<span className="absolute -left-[26px] top-1/2 h-3 w-3 -translate-y-1/2 transform rounded-full border-2 border-[color:var(--color-border)] bg-[color:var(--color-surface)]" />
																<span className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]/60 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)]">
																	Iteration {(loop.iteration ?? 0) + 1}
																	{loop.total ? ` of ${loop.total}` : ""}
																</span>
																<span className="h-px flex-1 bg-[color:var(--color-border)]/40" />
															</div>
														) : null;

														return (
															<Fragment key={expansionKey}>
															{loopHeader}
															<div className="relative">
																<span
																	className={`absolute -left-6 top-1/2 h-2.5 w-2.5 -translate-y-1/2 transform rounded-full ${
																		isCurrent
																			? nodeStyle.dotActive
																			: nodeStyle.dot
																	}`}
																/>
																<div
																	className={`overflow-hidden rounded-xl border ${nodeStyle.cardBorder} bg-[color:var(--color-surface)]/35 shadow-[0_8px_24px_rgba(0,0,0,0.35)] transition-all hover:border-[rgba(var(--color-primary-rgb),0.35)] ${
																		isCurrent
																			? "ring-1 ring-[rgba(var(--color-primary-rgb),0.35)]"
																			: ""
																	}`}
																>
																	<button
																		data-tutorial={_isFirstAgent ? "agent-result-card" : undefined}
																		onClick={createNodeExpansionHandler(
																			expansionKey,
																		)}
																		className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition-colors hover:bg-[color:var(--color-surface)]/40"
																	>
																		<div className="flex items-start gap-3">
																			<div
																				className={`flex h-7 w-7 items-center justify-center rounded-lg border ${nodeStyle.iconContainer}`}
																			>
																				{getNodeStatusIcon(node)}
																			</div>
																			<div className="space-y-1">
																				<div className="flex flex-wrap items-center gap-2">
																					<span className="text-sm font-semibold text-[color:var(--color-text-primary)]">
																						{node.node_name || "Unknown Node"}
																					</span>
																					<span className="rounded-full border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-2 py-0.5 text-[11px] capitalize text-[color:var(--color-text-muted)]">
																						{node.node_type || "Unknown"}
																					</span>
																					{node.is_sub_agent &&
																						node.node_type === "AGENT" && (
																							<span className="rounded-full border border-[rgba(var(--color-primary-rgb),0.50)] bg-[rgba(var(--color-primary-rgb),0.12)] px-2 py-0.5 text-[11px] capitalize text-orange-600">
																								Sub-Agent
																							</span>
																						)}
																					{node.node_type === "REVIEW" &&
																						(node.status === "running" ? (
																							<span className="rounded-full border border-cyan-500/50 bg-cyan-500/12 px-2 py-0.5 text-[11px] capitalize text-cyan-600">
																								Reviewing...
																							</span>
																						) : node.output_data &&
																							typeof node.output_data
																								.approved === "boolean" ? (
																							<span
																								className={`rounded-full border px-2 py-0.5 text-[11px] capitalize ${
																									node.output_data.approved
																										? "border-[#0DA931]/50 bg-[#0DA931]/12 text-[#0DA931]"
																										: "border-red-500/50 bg-red-500/12 text-red-300"
																								}`}
																							>
																								{node.output_data.approved
																									? "Approved"
																									: "Rejected"}
																							</span>
																						) : null)}
																					{isReExecution && (
																						<span className="rounded-full border border-blue-500/50 bg-blue-500/12 px-2 py-0.5 text-[11px] capitalize text-blue-600">
																							Run {iteration} of{" "}
																							{totalExecutions}
																						</span>
																					)}
																				</div>
																				<div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[color:var(--color-text-muted)]">
																					{timestampLabel && (
																						<span className="flex items-center gap-1 font-mono">
																							<Clock className="h-3 w-3" />
																							{timestampLabel}
																						</span>
																					)}
																					{durationLabel && (
																						<span className="flex items-center gap-1 font-mono">
																							<Activity className="h-3 w-3" />
																							{durationLabel}
																						</span>
																					)}
																					{node.tool_executions &&
																						node.tool_executions.length > 0 && (
																							<span className="flex items-center gap-1 text-purple-600">
																								<Wrench className="h-3 w-3" />
																								{node.tool_executions.length}{" "}
																								tool
																								{node.tool_executions.length > 1
																									? "s"
																									: ""}
																							</span>
																						)}
																					{node.input_tokens &&
																						node.output_tokens && (
																							<span className="flex items-center gap-1 font-mono">
																								<MessageSquare className="h-3 w-3" />
																								{node.input_tokens} in /{" "}
																								{node.output_tokens} out
																							</span>
																						)}
																				</div>
																			</div>
																		</div>
																		<div className="flex items-center gap-3">
																			<span
																				className={`inline-flex items-center whitespace-nowrap flex-shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${statusInfo.className}`}
																			>
																				{statusInfo.label}
																			</span>
																			{expandedNodes.has(expansionKey) ? (
																				<ChevronDown className="h-4 w-4 text-[color:var(--color-text-muted)]" />
																			) : (
																				<ChevronRight className="h-4 w-4 text-[color:var(--color-text-muted)]" />
																			)}
																		</div>
																	</button>

																	{expandedNodes.has(expansionKey) && (
																		<div className="space-y-5 border-t border-[color:var(--color-border)]/50 bg-[color:var(--color-surface)]/25 px-5 py-5">
																			{/* Live Activity Feed for AGENT nodes */}
																			{node.node_type === "AGENT" &&
																				(() => {
																					const nodeActivities =
																						activities.filter((a) => {
																							// Top-level tool calls for this agent
																							if (
																								a.type === "tool_call" &&
																								a.agentId === node.node_id
																							) {
																								return true;
																							}
																							// Subagent activities where this node is the parent (orchestrator)
																							if (
																								a.type === "subagent" &&
																								a.parentAgentId === node.node_id
																							) {
																								return true;
																							}
																							// For subagent nodes: find the subagent activity that matches
																							// this node's ID and current iteration, so we can show its nested tools
																							if (
																								node.is_sub_agent &&
																								a.type === "subagent" &&
																								a.subagentId === node.node_id &&
																								a.iteration === iteration
																							) {
																								return true;
																							}
																							// Guardrail violations for this agent
																							if (
																								a.type === "guardrail_violation" &&
																								a.agentId === node.node_id
																							) {
																								return true;
																							}
																							return false;
																						});

																					// For subagent nodes, extract nested tools from the matching subagent activity
																					// This shows tools directly without the subagent wrapper
																					let displayActivities: ActivityItem[] =
																						nodeActivities;
																					if (
																						node.is_sub_agent &&
																						nodeActivities.length > 0
																					) {
																						const matchingSubagent =
																							nodeActivities.find(
																								(a) =>
																									a.type === "subagent" &&
																									a.subagentId === node.node_id &&
																									a.iteration === iteration,
																							) as SubAgentActivityItem | undefined;
																						if (
																							matchingSubagent?.nestedActivities &&
																							matchingSubagent.nestedActivities
																								.length > 0
																						) {
																							displayActivities =
																								matchingSubagent.nestedActivities;
																						}
																					}

																					return displayActivities.length > 0 ? (
																						<div className="border-b border-[color:var(--color-border)]/50 pb-4 mb-1">
																							<h4 className="text-xs capitalize text-[color:var(--color-text-secondary)] font-semibold mb-3">
																								Live Activity
																							</h4>
																							<ActivityFeed
																								activities={displayActivities}
																								maxHeight="200px"
																								showHeader={false}
																								currentIteration={iteration}
																							/>
																						</div>
																					) : null;
																				})()}
																			<div className="flex items-center justify-between">
																				<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
																					Node Output
																				</span>
																				{timestampLabel && (
																					<span className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)] font-mono">
																						{timestampLabel}
																					</span>
																				)}
																			</div>
																			<div className="max-h-[420px] overflow-y-auto rounded-xl border border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/70 p-4 custom-scrollbar">
																				{shouldShowPlaceholder(
																					node.status,
																					node.output_data,
																				) ||
																				(node.output_data?.isThinking &&
																					!node.output_data?.raw) ? (
																					<div className="flex items-center gap-2 text-[color:var(--color-text-muted)]">
																						<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
																						<span>
																							{getNodePlaceholder(node.node_type)}
																						</span>
																					</div>
																				) : node.node_type === "REVIEW" &&
																					node.output_data &&
																					"approved" in node.output_data ? (
																					/* Custom rendering for REVIEW nodes */
																					<div className="space-y-3">
																						{/* Verdict with icon */}
																						<div className="flex items-center gap-3">
																							{node.output_data.approved ? (
																								<CheckCircle className="h-5 w-5 text-[#0DA931]" />
																							) : (
																								<XCircle className="h-5 w-5 text-red-400" />
																							)}
																							<span
																								className={`text-base font-medium ${node.output_data.approved ? "text-[#0DA931]" : "text-red-300"}`}
																							>
																								{node.output_data.approved
																									? "Output Approved"
																									: "Output Rejected"}
																							</span>
																							{node.output_data.iteration && (
																								<span className="text-sm text-[color:var(--color-text-muted)]">
																									(Iteration{" "}
																									{node.output_data.iteration}/
																									{node.output_data
																										.max_iterations || "?"}
																									)
																								</span>
																							)}
																						</div>

																						{/* Feedback */}
																						{node.output_data.feedback && (
																							<div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-tertiary)] p-3">
																								<div className="mb-1 text-xs font-medium capitalize tracking-wider text-[color:var(--color-text-muted)]">
																									Feedback
																								</div>
																								<div className="text-sm text-[color:var(--color-text-primary)] whitespace-pre-wrap">
																									{node.output_data.feedback}
																								</div>
																							</div>
																						)}

																						{/* Agent output preview */}
																						{node.output_data
																							.agent_output_reviewed && (
																							<details className="group">
																								<summary className="flex cursor-pointer items-center gap-2 text-xs text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]">
																									<ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
																									Reviewed Output Preview
																								</summary>
																								<div className="mt-2 rounded-lg border border-slate-200 bg-slate-100 p-2 text-xs text-slate-600 font-mono">
																									{
																										node.output_data
																											.agent_output_reviewed
																									}
																								</div>
																							</details>
																						)}

																						{/* LLM Review raw output (collapsible) */}
																						{node.output_data.raw && (
																							<details className="group">
																								<summary className="flex cursor-pointer items-center gap-2 text-xs text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text-secondary)]">
																									<ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
																									Raw LLM Response
																								</summary>
																								<div className="mt-2">
																									<SimpleMarkdown
																										content={formatOutput(
																											node.output_data.raw,
																										)}
																										variant="light"
																									/>
																								</div>
																							</details>
																						)}
																					</div>
																				) : node.status === "failed" &&
																					!node.output_data?.raw &&
																					!node.output_data?.response ? (
																					<div className="flex items-center gap-2 text-red-400/90">
																						<XCircle className="h-4 w-4 shrink-0" />
																						<span className="text-sm">
																							{node.error_message || "Execution failed"}
																						</span>
																					</div>
																				) : (
																					<SimpleMarkdown
																						content={formatOutput(
																							// Extract raw/response content for streaming, fall back to full object
																							node.output_data?.raw ||
																								node.output_data?.response ||
																								node.output_data,
																						)}
																						variant="light"
																					/>
																				)}
																			</div>
																			{node.tool_executions &&
																				node.tool_executions.length > 0 && (
																					<div className="border-t border-[color:var(--color-border)]/50 pt-4">
																						<button
																							onClick={createToolExpansionHandler(
																								expansionKey,
																							)}
																							className="flex items-center gap-2 text-xs font-medium text-orange-600 transition-colors hover:text-[color:var(--color-accent)] focus-visible:outline-none"
																						>
																							{expandedTools.has(
																								expansionKey,
																							) ? (
																								<ChevronDown className="h-3 w-3" />
																							) : (
																								<ChevronRight className="h-3 w-3" />
																							)}
																							<Wrench className="h-3 w-3" />
																							Tool Executions (
																							{node.tool_executions.length})
																						</button>
																						{expandedTools.has(
																							expansionKey,
																						) && (
																							<div className="mt-3 space-y-2">
																								{node.tool_executions.map(
																									(tool, toolIndex) => {
																										const isToolRunning =
																											tool.status === "running";
																										const isToolCompleted =
																											tool.status ===
																											"completed";
																										const isToolError =
																											tool.status === "failed";
																										return (
																											<div
																												key={`${tool.node_id}-${toolIndex}`}
																												className={`flex items-start gap-3 rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-4 py-3 shadow-[0_15px_40px_rgba(0,0,0,0.35)] transition-all ${
																													isToolRunning
																														? "ring-1 ring-[rgba(var(--color-primary-rgb),0.35)] animate-pulse"
																														: isToolCompleted
																															? "ring-1 ring-[#0DA931]/30"
																															: isToolError
																																? "ring-1 ring-red-500/30"
																																: ""
																												}`}
																											>
																												<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[color:var(--color-border)]/70 bg-[color:var(--color-bg-secondary)]/70">
																													{getToolIcon(
																														tool.node_type,
																													)}
																												</div>
																												<div className="min-w-0 flex-1 space-y-1">
																													<div className="flex flex-wrap items-center gap-2 text-xs">
																														<span className="font-semibold text-[color:var(--color-text-primary)]">
																															{tool.node_name}
																														</span>
																														<span className="rounded-full border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-2 py-0.5 text-[10px] capitalize text-[color:var(--color-text-muted)]">
																															{tool.node_type.replace(
																																"_",
																																" ",
																															)}
																														</span>
																														{tool.duration_seconds && (
																															<span className="flex items-center gap-1 text-[color:var(--color-text-muted)] font-mono">
																																<Clock className="h-3 w-3" />
																																{tool.duration_seconds.toFixed(
																																	2,
																																)}
																																s
																															</span>
																														)}
																													</div>
																													{tool.input_data && (
																														<div className="text-[11px] text-[color:var(--color-text-muted)]">
																															<span className="font-medium text-[color:var(--color-text-primary)]/80">
																																Input:
																															</span>{" "}
																															<span className="font-mono">
																																{typeof tool.input_data ===
																																	"object" &&
																																"query" in
																																	tool.input_data
																																	? String(
																																			tool
																																				.input_data
																																				.query,
																																		).substring(
																																			0,
																																			120,
																																		) +
																																		(String(
																																			tool
																																				.input_data
																																				.query,
																																		).length >
																																		120
																																			? "…"
																																			: "")
																																	: JSON.stringify(
																																			tool.input_data,
																																		).substring(
																																			0,
																																			120,
																																		)}
																															</span>
																														</div>
																													)}
																												</div>
																											</div>
																										);
																									},
																								)}
																							</div>
																						)}
																					</div>
																				)}
																		</div>
																	)}
																</div>
															</div>
															</Fragment>
														);
													},
												); })()}
											</div>
										</div>
									)}
								</div>
							)}
						</section>
				</div>

				</>)}

			</div>

			{/* Review Resume Dialog - shown when user clicks "Review & Revise" */}
			{/* Guardrail Block Modal - non-dismissable modal for block-severity violations */}
			<GuardrailBlockModal
				violation={guardrailBlockViolation}
				onEndExecution={() => {
					// The backend already marked this execution as "failed" when the
					// guardrail block interrupt was handled, so we only need to clean
					// up frontend state — calling the stop API would fail with a
					// "already finished" error.
					setIsExecuting(false);
					setExecutionRequested(false);
					setIsPausePending(false);
					setIsPaused(false);
					setPauseInfo(null);
					pauseInfoRef.current = null;
					setIsManualPause(false);
					setManualPauseInfo(null);
					setIsManualResumePending(false);
					setHasStopped(true);
					setStoppedAt(new Date().toISOString());
					streaming.markAllNodesAsStopped();
					setGuardrailBlockViolation(null);
				}}
			/>

			{/* Start New Workflow Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showStartNewConfirm}
				onClose={() => setShowStartNewConfirm(false)}
				onConfirm={handleConfirmStartNew}
				title="Start New Workflow?"
				message="This will abandon the current paused execution. You can still resume it later from the Paused Executions list."
				confirmText="Start New"
				cancelText="Cancel"
				variant="warning"
				surface="light"
			/>

			{showReviewDialog && reviewPayload && (
				<ReviewResumeDialog
					execution={{
						execution_id: executionId || "",
						thread_id: threadId || "",
						graph_name: graphName,
					}}
					reviewPayload={reviewPayload}
					onClose={() => setShowReviewDialog(false)}
					onResume={handleReviewResume}
				/>
			)}
		</aside>
	);
}
