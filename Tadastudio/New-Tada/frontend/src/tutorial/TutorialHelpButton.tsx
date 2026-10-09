"use client";

import { GripVertical, HelpCircle } from "lucide-react";
import { usePathname } from "next/navigation";
import {
	useCallback,
	useEffect,
	useLayoutEffect,
	useRef,
	useState,
} from "react";
import { createPortal } from "react-dom";
import { useFeatureAccess } from "@/contexts/FeatureAccessContext";
import { getTutorialIdForRoute, useTutorial } from "./TutorialContext";
import { TUTORIAL_DEFINITIONS } from "./steps";
import { isTutorialButtonVisible, setTutorialButtonVisible } from "./persistence";
import "./tutorial.css";

export type TutorialHelpButtonMode = "fab" | "sidebar" | "edge";

const POPOVER_VIEWPORT_GAP = 12;
/** ~22rem — matches `.as-tutorial-popover-list` width for viewport clamping */
const POPOVER_APPROX_WIDTH = 352;

export default function TutorialHelpButton({
	mode = "fab",
	sidebarCollapsed,
}: {
	mode?: TutorialHelpButtonMode;
	/** When `mode="sidebar"`, matches AppSidebar collapsed state for label + layout. */
	sidebarCollapsed?: boolean;
}) {
	const pathname = usePathname();
	const { startTutorial, completedTutorials } = useTutorial();
	const {
		featureAccess,
		loading: featureLoading,
		error: featureError,
		canAccessFeature,
	} = useFeatureAccess();
	const [isOpen, setIsOpen] = useState(false);
	const [buttonVisible, setButtonVisible] = useState(() => isTutorialButtonVisible());
	const [mounted, setMounted] = useState(false);
	const [sidebarPopoverPos, setSidebarPopoverPos] = useState<{
		left: number;
		bottom: number;
	} | null>(null);

	// Edge mode: vertical dragging state (70% to 95% of viewport height)
	const EDGE_MIN_PERCENT = 70;
	const EDGE_MAX_PERCENT = 95;
	const [edgeTopPercent, setEdgeTopPercent] = useState(() => {
		if (typeof window === "undefined") return 70;
		const saved = localStorage.getItem("tutorial_help_edge_position");
		if (saved) {
			const val = parseFloat(saved);
			if (!Number.isNaN(val) && val >= EDGE_MIN_PERCENT && val <= EDGE_MAX_PERCENT) return val;
		}
		return 70;
	});
	const [isDragging, setIsDragging] = useState(false);
	const dragStartY = useRef(0);
	const dragStartPercent = useRef(70);

	const buttonRef = useRef<HTMLButtonElement>(null);
	const popoverRef = useRef<HTMLDivElement>(null);
	const wrapperRef = useRef<HTMLDivElement>(null);

	const currentTutorialId = getTutorialIdForRoute(pathname);

	const tutorialEnabled = (() => {
		if (featureLoading) return true;
		if (featureError) return false;
		if (!featureAccess.has("tutorial.enabled")) return true;
		return canAccessFeature("tutorial.enabled");
	})();

	// Auto-hide once when the last tutorial is completed in this session.
	// Track the previous completed count so we only trigger on a new completion,
	// not when the user manually re-enables the button.
	const prevCompletedCount = useRef(-1);
	useEffect(() => {
		const allIds = Object.keys(TUTORIAL_DEFINITIONS);
		const doneCount = allIds.filter((id) => completedTutorials[id]).length;
		const allDone = allIds.length > 0 && doneCount === allIds.length;

		// Only auto-hide if a new tutorial just completed (count increased) and all are now done
		if (allDone && prevCompletedCount.current >= 0 && doneCount > prevCompletedCount.current) {
			setButtonVisible(false);
			setTutorialButtonVisible(false);
		}
		prevCompletedCount.current = doneCount;
	}, [completedTutorials]);

	// Listen for toggle changes from the user profile menu
	useEffect(() => {
		const handler = (e: Event) => {
			const visible = (e as CustomEvent).detail?.visible ?? true;
			setButtonVisible(visible);
		};
		window.addEventListener("tutorialButtonVisibilityChanged", handler);
		return () => window.removeEventListener("tutorialButtonVisibilityChanged", handler);
	}, []);

	useEffect(() => {
		if (!isOpen) return;

		function handleMouseDown(e: MouseEvent) {
			const target = e.target as Node;
			if (
				buttonRef.current?.contains(target) ||
				popoverRef.current?.contains(target) ||
				wrapperRef.current?.contains(target)
			) {
				return;
			}
			setIsOpen(false);
		}

		// Use capture phase to catch clicks before React Flow or other components stop propagation
		document.addEventListener("mousedown", handleMouseDown, true);
		return () => document.removeEventListener("mousedown", handleMouseDown, true);
	}, [isOpen]);

	const trapFocus = useCallback((e: KeyboardEvent) => {
		if (e.key === "Escape") {
			setIsOpen(false);
			buttonRef.current?.focus();
			return;
		}
		if (e.key !== "Tab" || !popoverRef.current) return;

		const focusable = popoverRef.current.querySelectorAll<HTMLElement>(
			'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
		);
		if (focusable.length === 0) return;

		const first = focusable[0];
		const last = focusable[focusable.length - 1];

		if (e.shiftKey) {
			if (document.activeElement === first) {
				e.preventDefault();
				last.focus();
			}
		} else {
			if (document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}, []);

	useEffect(() => {
		if (!isOpen) return;

		document.addEventListener("keydown", trapFocus);
		return () => document.removeEventListener("keydown", trapFocus);
	}, [isOpen, trapFocus]);

	useEffect(() => {
		if (!isOpen || !popoverRef.current) return;
		const firstItem =
			popoverRef.current.querySelector<HTMLElement>("button");
		firstItem?.focus();
	}, [isOpen]);

	useEffect(() => {
		setMounted(true);
	}, []);

	// Edge mode: drag handlers
	const handleDragStart = useCallback((clientY: number) => {
		if (mode !== "edge") return;
		setIsDragging(true);
		dragStartY.current = clientY;
		dragStartPercent.current = edgeTopPercent;
	}, [mode, edgeTopPercent]);

	const handleDragMove = useCallback((clientY: number) => {
		if (!isDragging || mode !== "edge") return;
		const vh = window.innerHeight;
		const deltaY = clientY - dragStartY.current;
		const deltaPercent = (deltaY / vh) * 100;
		const newPercent = Math.min(EDGE_MAX_PERCENT, Math.max(EDGE_MIN_PERCENT, dragStartPercent.current + deltaPercent));
		setEdgeTopPercent(newPercent);
	}, [isDragging, mode]);

	const handleDragEnd = useCallback(() => {
		if (!isDragging) return;
		setIsDragging(false);
		localStorage.setItem("tutorial_help_edge_position", String(edgeTopPercent));
	}, [isDragging, edgeTopPercent]);

	// Mouse events for edge dragging
	useEffect(() => {
		if (mode !== "edge" || !isDragging) return;
		const onMouseMove = (e: MouseEvent) => handleDragMove(e.clientY);
		const onMouseUp = () => handleDragEnd();
		document.addEventListener("mousemove", onMouseMove);
		document.addEventListener("mouseup", onMouseUp);
		return () => {
			document.removeEventListener("mousemove", onMouseMove);
			document.removeEventListener("mouseup", onMouseUp);
		};
	}, [mode, isDragging, handleDragMove, handleDragEnd]);

	// Touch events for edge dragging
	useEffect(() => {
		if (mode !== "edge" || !isDragging) return;
		const onTouchMove = (e: TouchEvent) => {
			if (e.touches.length === 1) handleDragMove(e.touches[0].clientY);
		};
		const onTouchEnd = () => handleDragEnd();
		document.addEventListener("touchmove", onTouchMove, { passive: true });
		document.addEventListener("touchend", onTouchEnd);
		document.addEventListener("touchcancel", onTouchEnd);
		return () => {
			document.removeEventListener("touchmove", onTouchMove);
			document.removeEventListener("touchend", onTouchEnd);
			document.removeEventListener("touchcancel", onTouchEnd);
		};
	}, [mode, isDragging, handleDragMove, handleDragEnd]);

	const updateSidebarPopoverPosition = useCallback(() => {
		const btn = buttonRef.current;
		if (!btn) return;
		const r = btn.getBoundingClientRect();
		const vw = window.innerWidth;
		const vh = window.innerHeight;
		// Anchor to the right of the control so the menu opens into the main area; clamp so it stays in view.
		const left = Math.min(
			r.right + POPOVER_VIEWPORT_GAP,
			vw - POPOVER_APPROX_WIDTH - POPOVER_VIEWPORT_GAP,
		);
		setSidebarPopoverPos({
			left: Math.max(POPOVER_VIEWPORT_GAP, left),
			bottom: vh - r.top + POPOVER_VIEWPORT_GAP,
		});
	}, []);

	useLayoutEffect(() => {
		if (mode !== "sidebar" || !isOpen) return;
		updateSidebarPopoverPosition();
		window.addEventListener("resize", updateSidebarPopoverPosition);
		return () => window.removeEventListener("resize", updateSidebarPopoverPosition);
	}, [isOpen, mode, sidebarCollapsed, updateSidebarPopoverPosition]);

	const isOnChatPage = pathname.startsWith("/chat");
	if (!tutorialEnabled || !buttonVisible || isOnChatPage) return null;

	const popover = (
		<div
			className="as-tutorial-popover-list"
			role="dialog"
			aria-label="Help"
			ref={popoverRef}
			style={
				mode === "sidebar" && sidebarPopoverPos
					? {
							position: "fixed",
							left: sidebarPopoverPos.left,
							bottom: sidebarPopoverPos.bottom,
							right: "auto",
							zIndex: 9998,
							maxHeight: `min(28rem, ${Math.max(160, window.innerHeight - 24)}px)`,
						}
					: undefined
			}
		>
			<div className="as-tutorial-popover-list__header">Tutorials</div>
			{Object.values(TUTORIAL_DEFINITIONS).map((def) => (
				<button
					key={def.id}
					type="button"
					className="as-tutorial-popover-list__item"
					aria-label={`Start ${def.label} tutorial`}
					onClick={() => {
						startTutorial(def.id);
						setIsOpen(false);
					}}
				>
					<span aria-hidden="true">{def.icon}</span>
					<span>{def.label}</span>
					<span className="as-tutorial-popover-list__meta">
						<span>
							{def.stepCount} steps &middot; {def.estimatedMinutes}m
						</span>
						{completedTutorials[def.id] && (
							<span className="as-tutorial-popover-list__badge">&#10003;</span>
						)}
						{currentTutorialId === def.id && (
							<span className="as-tutorial-popover-list__current">Current</span>
						)}
					</span>
				</button>
			))}
		</div>
	);

	const wrapperStyle =
		mode === "fab"
			? {
					position: "fixed" as const,
					bottom: "1.5rem",
					right: "1.5rem",
					zIndex: 9998,
				}
			: mode === "edge"
				? {
						position: "fixed" as const,
						top: `${edgeTopPercent}%`,
						right: "0",
						transform: "translateY(-50%)",
						zIndex: 9998,
						cursor: isDragging ? "grabbing" : "grab",
						userSelect: "none" as const,
						touchAction: "none" as const,
					}
				: undefined;

	const wrapperClassName =
		mode === "sidebar"
			? "relative flex w-full min-w-0 items-center gap-0"
			: mode === "edge"
				? `as-tutorial-edge-tab${isOpen ? " as-tutorial-edge-tab--open" : ""}${isDragging ? " as-tutorial-edge-tab--dragging" : ""}`
				: undefined;

	return (
		<div
			ref={wrapperRef}
			className={wrapperClassName}
			style={wrapperStyle}
			onMouseDown={mode === "edge" ? (e) => handleDragStart(e.clientY) : undefined}
			onTouchStart={mode === "edge" ? (e) => e.touches.length === 1 && handleDragStart(e.touches[0].clientY) : undefined}
		>
			{isOpen && (mode === "fab" || mode === "edge") && popover}
			{mounted &&
				isOpen &&
				mode === "sidebar" &&
				createPortal(popover, document.body)}
			{/* Drag handle indicator for edge mode */}
			{mode === "edge" && (
				<span className="as-tutorial-edge-drag-handle" aria-hidden="true">
					<GripVertical size={14} />
				</span>
			)}
			<span
				className="relative flex shrink-0 items-center justify-center"
				style={mode === "sidebar" ? { width: 56, height: 44 } : undefined}
			>
				<button
					type="button"
					className={mode === "edge" ? "as-tutorial-edge-btn" : "as-tutorial-help-btn"}
					aria-label="Open Help"
					title={mode === "sidebar" && sidebarCollapsed ? "Help" : (mode === "edge" ? "Drag to move, click to open help" : undefined)}
					aria-expanded={isOpen}
					aria-haspopup="true"
					ref={buttonRef}
					onClick={() => setIsOpen((v) => !v)}
				>
					{mode !== "edge" && <span className="as-tutorial-pulse-ring" aria-hidden="true" />}
					<HelpCircle size={mode === "edge" ? 18 : 20} />
				</button>
			</span>
			{mode === "sidebar" && sidebarCollapsed === false && (
				<span className="min-w-0 flex-1 truncate text-sm text-gray-700">Help</span>
			)}
		</div>
	);
}
