"use client";

import clsx from "clsx";
import {
	ArrowLeft,
	BookOpen,
	ChevronRight,
	Code,
	Copy,
	Download,
	FileJson,
	Globe,
	History,
	MoreHorizontal,
	Pause,
	Play,
	Plus,
	RotateCcw,
	Save,
	Share2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useGraph } from "@/contexts/GraphContext";
import { useNotification } from "@/contexts/NotificationContext";
import { useGraphStore } from "@/stores/graphStore";
import { useTutorial } from "@/tutorial/TutorialContext";
import { api } from "@/lib/api";
import InlineNameEditor from "../nodes/shared/InlineNameEditor";
import PausedExecutionsIndicator from "../panels/execution/PausedExecutionsIndicator";
import ModeToggle from "../ui/ModeToggle";
import { SyncStatusIndicator } from "../ui/SyncStatusIndicator";
import HttpExecutionModal from "../modals/HttpExecutionModal";
import ShareWorkflowModal from "../modals/ShareWorkflowModal";
import { NotificationBell } from "../notifications/NotificationBell";

interface CanvasTopBarProps {
	mode: "edit" | "evaluate" | "execution";
	onModeChange: (mode: "edit" | "evaluate" | "execution") => void;
	isExecuting: boolean;
	isRunning?: boolean;
	currentGraph: { name: string } | null;
	nodeCount: number;
	// Read-only mode (for viewers)
	isReadOnly?: boolean;
	// Core actions — always visible
	onRun?: () => void;
	onPause?: () => void;
	onSave?: () => Promise<void> | void;
	onAddNode?: () => void;
	// Secondary actions (overflow menu)
	onExportJson?: () => void;
	onExportPython?: () => void;
	onAddToLibrary?: () => void;
	onReset?: () => void;
	onDuplicate?: () => void;
	onVersionHistory?: () => void;
	// Paused executions
	onLoadExecution: (
		executionId: string,
		threadId: string,
		dbExecutionId: string,
	) => void;
	onSetMode: (mode: "edit" | "evaluate" | "execution") => void;
	onSetShowExecutionPanel: (show: boolean) => void;
	// Workflow ID for access request notifications
	workflowId?: string;
}

const CanvasTopBar = React.memo(function CanvasTopBar({
	mode,
	onModeChange,
	isExecuting,
	isRunning = false,
	currentGraph,
	nodeCount,
	isReadOnly = false,
	onRun,
	onPause,
	onSave,
	onAddNode,
	onExportJson,
	onExportPython,
	onAddToLibrary,
	onReset,
	onDuplicate,
	onVersionHistory,
	onLoadExecution,
	onSetMode,
	onSetShowExecutionPanel,
	workflowId,
}: CanvasTopBarProps) {
	const router = useRouter();
	const { updateWorkflowName } = useGraph();
	const { showWarning, showError } = useNotification();
	const storeWorkflowId = useGraphStore(
		(state) => state.currentGraph?.workflow_id,
	);
	const currentVersion = useGraphStore((state) => state.currentVersion);
	const setCurrentVersion = useGraphStore(
		(state) => state.setCurrentVersion,
	);

	useEffect(() => {
		if (currentVersion != null || !storeWorkflowId) return;
		let cancelled = false;
		api
			.getWorkflowVersions(storeWorkflowId)
			.then((result) => {
				if (cancelled) return;
				const latest = result.versions?.find((v: { is_latest: boolean }) => v.is_latest);
				if (latest) setCurrentVersion((latest as { version: number }).version);
			})
			.catch(() => {});
		return () => { cancelled = true; };
	}, [currentVersion, storeWorkflowId, setCurrentVersion]);

	const [showHttpModal, setShowHttpModal] = useState(false);
	const [showShareModal, setShowShareModal] = useState(false);
	const [isPublished, setIsPublished] = useState<boolean | null>(null);
	const [isSaving, setIsSaving] = useState(false);
	const [showOverflowMenu, setShowOverflowMenu] = useState(false);
	const overflowMenuRef = useRef<HTMLDivElement>(null);

	const [httpListenerEnabled, setHttpListenerEnabled] = useState(false);
	const [httpListenerConnected, setHttpListenerConnected] = useState(false);
	const httpListenerWsRef = useRef<WebSocket | null>(null);

	const handleToggleHttpListener = useCallback(() => {
		setHttpListenerEnabled((prev) => !prev);
	}, []);

	const graphName = currentGraph?.name;

	useEffect(() => {
		if (!graphName) return;
		let cancelled = false;
		api
			.getWorkflowPublicationStatus(graphName)
			.then((result) => {
				if (!cancelled) setIsPublished(result?.is_published === true);
			})
			.catch(() => {
				if (!cancelled) setIsPublished(false);
			});
		return () => { cancelled = true; };
	}, [graphName]);

	useEffect(() => {
		if (!httpListenerEnabled || !graphName) return;
		const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
		const ws = new WebSocket(
			`${protocol}//${window.location.host}/api/ws/http-listener/${encodeURIComponent(graphName)}`,
		);
		httpListenerWsRef.current = ws;
		ws.onopen = () => setHttpListenerConnected(true);
		ws.onclose = () => setHttpListenerConnected(false);
		ws.onerror = () => setHttpListenerConnected(false);
		ws.onmessage = (event) => {
			try {
				const msg = JSON.parse(event.data);
				if (msg.type === "http_execution_started" && msg.execution_id) {
					onLoadExecution(msg.execution_id, msg.execution_id, "");
					onSetShowExecutionPanel(true);
					onSetMode("execution");
				}
			} catch {}
		};
		const ping = setInterval(() => {
			if (ws.readyState === WebSocket.OPEN) ws.send("ping");
		}, 30000);
		return () => {
			clearInterval(ping);
			if (ws.readyState === WebSocket.OPEN) ws.close();
			httpListenerWsRef.current = null;
			setHttpListenerConnected(false);
		};
	}, [httpListenerEnabled, graphName, onLoadExecution, onSetShowExecutionPanel, onSetMode]);

	useEffect(() => {
		if (!showOverflowMenu) return;
		const handler = (e: MouseEvent) => {
			if (overflowMenuRef.current && !overflowMenuRef.current.contains(e.target as Node)) {
				setShowOverflowMenu(false);
			}
		};
		// Use capture phase to catch clicks before they're stopped by other handlers
		document.addEventListener("mousedown", handler, true);
		return () => document.removeEventListener("mousedown", handler, true);
	}, [showOverflowMenu]);

	const handleWorkflowNameSave = useCallback(
		async (_nodeId: string, newName: string) => { await updateWorkflowName(newName); },
		[updateWorkflowName],
	);

	const handleSaveClick = useCallback(async () => {
		if (!onSave) return;
		setIsSaving(true);
		try { await onSave(); } finally { setIsSaving(false); }
	}, [onSave]);

	const { isRunning: isTutorialRunning } = useTutorial();
	const isFresh = nodeCount <= 1;
	const showSecondaryActions = !isFresh || isTutorialRunning;

	// ── shared style tokens ────────────────────────────────────────────────
	const ghostBtn =
		"flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-sm font-medium text-gray-600 transition-all duration-150 hover:border-gray-300 hover:text-gray-800 hover:bg-gray-50 focus-visible:outline-none";

	const dropdownItem =
		"flex items-center gap-2.5 w-full px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors";

	return (
		<>
			{/* ── Top bar ──────────────────────────────────────────────────── */}
			<div className="flex min-h-14 shrink-0 flex-wrap items-center gap-x-1 gap-y-2 sm:gap-x-2 border-b border-gray-200 bg-white px-2 py-2 sm:px-4">

				{/* ← Back */}
				<button
					type="button"
					onClick={() => router.back()}
					className="flex items-center gap-1 sm:gap-1.5 rounded-lg px-2 sm:px-2.5 py-1.5 text-sm font-medium transition-colors hover:bg-orange-50 focus-visible:outline-none shrink-0"
					style={{ color: "#ff6b00" }}
					title="Go back"
				>
					<ArrowLeft className="h-4 w-4" />
					<span className="hidden sm:inline">Back</span>
				</button>

				<div className="h-5 w-px bg-gray-200 shrink-0" />

				{/* + Add Node - disabled for viewers */}
				{mode === "edit" && (
					<button
						data-tutorial="add-node-btn"
						type="button"
						onClick={isReadOnly ? undefined : onAddNode}
						disabled={isReadOnly}
						className={clsx(ghostBtn, "shrink-0", isReadOnly && "opacity-50 cursor-not-allowed")}
						title={isReadOnly ? "View only - cannot add nodes" : "Add a node (press / to search)"}
					>
						<Plus className="h-4 w-4" />
						<span className="hidden sm:inline">Add Node</span>
					</button>
				)}

				{/* Mode toggle */}
				<ModeToggle
					mode={mode}
					onModeChange={onModeChange}
					isExecuting={isExecuting}
					compact
				/>

				{mode === "evaluate" && (
					<span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-semibold capitalize tracking-wider text-amber-700 shrink-0">
						Read-only
					</span>
				)}

				{/* Workflow name — center */}
				{currentGraph && (
					<div className="flex min-w-0 items-center gap-2 pl-1">
						<InlineNameEditor
							nodeId="workflow"
							initialName={currentGraph.name}
							placeholder="Workflow Name"
							className="truncate text-sm font-semibold text-gray-800"
							editClassName="text-gray-800"
							onSave={handleWorkflowNameSave}
							showEditIcon
						/>
						{currentVersion != null && (
							<span className="rounded-full border border-gray-200 bg-gray-100 px-2 py-0.5 text-xs font-medium tabular-nums text-gray-500 shrink-0">
								v{currentVersion}
							</span>
						)}
						<SyncStatusIndicator variant="inline" />
					</div>
				)}

				<div className="flex-1 min-w-2" />

				{/* ── Right side actions ──────────────────────────────────── */}
				{currentGraph && showSecondaryActions && (
					<>
						{/* Publish / HTTP listener - disabled for viewers */}
						<button
							data-tutorial="publish-api-btn"
							type="button"
							onClick={isReadOnly ? undefined : () => setShowHttpModal(true)}
							disabled={isReadOnly}
							className={clsx(ghostBtn, "shrink-0 hidden md:flex", isReadOnly && "opacity-50 cursor-not-allowed")}
							title={isReadOnly ? "View only - cannot publish" : "Publish & HTTP API"}
						>
							<Globe className="h-4 w-4" />
							<span className="hidden lg:inline">Publish</span>
							{isPublished !== null && (
								<span
									className={clsx(
										"h-2 w-2 rounded-full",
										isPublished ? "bg-[#0DA931]" : "bg-amber-400",
									)}
								/>
							)}
						</button>

						<div className="h-5 w-px bg-gray-200 hidden md:block shrink-0" />

						<PausedExecutionsIndicator
							graphName={currentGraph.name}
							onSelectExecution={(eid, tid, dbid) => {
								onLoadExecution(eid, tid, dbid);
								onSetShowExecutionPanel(true);
								onSetMode("execution");
							}}
						/>
					</>
				)}

				{/* Save - green background with white text */}
				{currentGraph && onSave && (
					<button
						type="button"
						onClick={isReadOnly ? undefined : handleSaveClick}
						disabled={isSaving || isReadOnly}
						className={clsx(
							"flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold text-white bg-[#0DA931] hover:bg-[#0B8A29] shadow-sm transition-all duration-150 focus-visible:outline-none shrink-0",
							(isSaving || isReadOnly) && "opacity-50 cursor-not-allowed"
						)}
						title={isReadOnly ? "View only - cannot save" : "Save workflow"}
					>
						<Save className="h-4 w-4" />
						<span className="hidden sm:inline">{isSaving ? "Saving…" : "Save"}</span>
					</button>
				)}

				{/* Run Workflow — primary color */}
				{currentGraph && (
					<button
						data-tutorial="run-btn"
						type="button"
						onClick={isRunning ? onPause : onRun}
						className={clsx(
							"flex items-center gap-1 sm:gap-1.5 rounded-lg px-2 sm:px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 focus-visible:outline-none shrink-0",
							isRunning
								? "bg-amber-500 hover:bg-amber-600"
								: "bg-[color:var(--color-primary)] hover:bg-[color:var(--color-secondary)]",
						)}
						title={isRunning ? "Pause execution" : "Run workflow"}
					>
						{isRunning ? (
							<Pause className="h-4 w-4" />
						) : (
							<Play className="h-4 w-4 fill-white stroke-none" />
						)}
						<span className="hidden sm:inline">{isRunning ? "Pause" : "Run Workflow"}</span>
						<span className="sm:hidden">{isRunning ? "Pause" : "Run"}</span>
					</button>
				)}

				{/* Overflow "…" — secondary actions */}
				{currentGraph && showSecondaryActions && (
					<div className="relative shrink-0" ref={overflowMenuRef}>
						<button
							type="button"
							onClick={() => setShowOverflowMenu((v) => !v)}
							className={clsx(ghostBtn, "px-2")}
							title="More actions"
						>
							<MoreHorizontal className="h-5 w-5" />
						</button>
						{showOverflowMenu && (
							<div className="absolute right-0 top-full z-50 mt-1 min-w-[180px] animate-scaleIn rounded-xl border border-gray-200 bg-white py-1.5 shadow-xl">
								{/* Show Publish in overflow menu on small screens */}
								<button
									type="button"
									onClick={isReadOnly ? undefined : () => { setShowOverflowMenu(false); setShowHttpModal(true); }}
									disabled={isReadOnly}
									className={clsx(dropdownItem, "md:hidden", isReadOnly && "opacity-50 cursor-not-allowed")}
									title={isReadOnly ? "View only" : undefined}
								>
									<Globe className="h-4 w-4" /> Publish
									{isPublished !== null && (
										<span
											className={clsx(
												"ml-auto h-2 w-2 rounded-full",
												isPublished ? "bg-[#0DA931]" : "bg-amber-400",
											)}
										/>
									)}
								</button>
								{onAddToLibrary && (
									<button
										type="button"
										onClick={isReadOnly ? undefined : () => { setShowOverflowMenu(false); onAddToLibrary(); }}
										disabled={isReadOnly}
										className={clsx(dropdownItem, isReadOnly && "opacity-50 cursor-not-allowed")}
										title={isReadOnly ? "View only" : undefined}
									>
										<BookOpen className="h-4 w-4" /> Add to Library
									</button>
								)}
								<button
									type="button"
									onClick={isReadOnly ? undefined : () => { setShowOverflowMenu(false); onReset?.(); }}
									disabled={isReadOnly}
									className={clsx(dropdownItem, isReadOnly && "opacity-50 cursor-not-allowed")}
									title={isReadOnly ? "View only" : undefined}
								>
									<RotateCcw className="h-4 w-4" /> Reset
								</button>
								<button type="button" onClick={() => { setShowOverflowMenu(false); onDuplicate?.(); }} className={dropdownItem}>
									<Copy className="h-4 w-4" /> Duplicate
								</button>
								<button type="button" onClick={() => { setShowOverflowMenu(false); onVersionHistory?.(); }} className={dropdownItem}>
									<History className="h-4 w-4" /> Version History
								</button>
								{storeWorkflowId && (
									<button
										data-tutorial="share-btn"
										type="button"
										onClick={isReadOnly ? undefined : () => { setShowOverflowMenu(false); setShowShareModal(true); }}
										disabled={isReadOnly}
										className={clsx(dropdownItem, isReadOnly && "opacity-50 cursor-not-allowed")}
										title={isReadOnly ? "View only" : undefined}
									>
										<Share2 className="h-4 w-4" /> Share
									</button>
								)}
								<div className="my-1 border-t border-gray-100" />
								<div className="group">
									<div className={`${dropdownItem} justify-between cursor-pointer`}>
										<span className="flex items-center gap-2">
											<Download className="h-4 w-4" /> Export
										</span>
										<ChevronRight className="h-3 w-3 text-gray-400 transition-transform group-hover:rotate-90" />
									</div>
									<div className="hidden group-hover:block overflow-hidden">
										<button type="button" onClick={() => { setShowOverflowMenu(false); onExportJson?.(); }} className={`${dropdownItem} pl-10`}>
											<FileJson className="h-4 w-4 text-purple-500" /> JSON
										</button>
										<button type="button" onClick={() => { setShowOverflowMenu(false); onExportPython?.(); }} className={`${dropdownItem} pl-10`}>
											<Code className="h-4 w-4 text-purple-500" /> Python
										</button>
									</div>
								</div>
							</div>
						)}
					</div>
				)}

					{/* Notification Bell - at the far right */}
					{currentGraph && (
						<>
							<div className="h-5 w-px bg-gray-200 mx-1 shrink-0" />
							<NotificationBell workflowId={workflowId} />
						</>
					)}
			</div>

			{/* Modals */}
			{currentGraph && (
				<HttpExecutionModal
					isOpen={showHttpModal}
					onClose={() => setShowHttpModal(false)}
					graphName={currentGraph.name}
					workflowId={storeWorkflowId}
					onPublishedChange={setIsPublished}
					httpListenerEnabled={httpListenerEnabled}
					httpListenerConnected={httpListenerConnected}
					onToggleHttpListener={handleToggleHttpListener}
				/>
			)}
			{currentGraph && storeWorkflowId && (
				<ShareWorkflowModal
					isOpen={showShareModal}
					onClose={() => setShowShareModal(false)}
					workflowId={storeWorkflowId}
				/>
			)}
		</>
	);
});

export default CanvasTopBar;
