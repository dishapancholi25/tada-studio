"use client";

import clsx from "clsx";
import { GitBranch, Grid3X3, Keyboard, Map, Maximize2, ZoomIn, ZoomOut } from "lucide-react";
import { useCallback, useState } from "react";
import { useReactFlow } from "reactflow";

interface CustomZoomControlsProps {
	showInteractive?: boolean;
	position?: "fixed" | "panel";
	className?: string;
	onAutoLayout?: () => void;
	// Canvas preference toggles
	snapToGrid?: boolean;
	onToggleSnapToGrid?: () => void;
	showMiniMap?: boolean;
	onToggleMiniMap?: () => void;
	// Help
	onShowShortcuts?: () => void;
	// Layout orientation
	orientation?: "vertical" | "horizontal";
}

export default function CustomZoomControls({
	showInteractive = false,
	position = "fixed",
	className = "",
	onAutoLayout,
	snapToGrid = false,
	onToggleSnapToGrid,
	showMiniMap = true,
	onToggleMiniMap,
	onShowShortcuts,
	orientation = "vertical",
}: CustomZoomControlsProps) {
	const [showTooltip, setShowTooltip] = useState<string | null>(null);
	const { zoomIn, zoomOut, fitView } = useReactFlow();

	const createMouseEnterHandler = useCallback(
		(buttonId: string) => () => setShowTooltip(buttonId),
		[],
	);
	const clearTooltip = useCallback(() => setShowTooltip(null), []);

	const handleZoomIn = useCallback(() => {
		zoomIn();
	}, [zoomIn]);

	const handleZoomOut = useCallback(() => {
		zoomOut();
	}, [zoomOut]);

	const handleFitView = useCallback(() => {
		fitView();
	}, [fitView]);

	const isHorizontal = orientation === "horizontal";

	const buttons = [
		{
			id: "zoom-in",
			icon: ZoomIn,
			label: "Zoom In",
			onClick: handleZoomIn,
			color:
				"text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary)]",
			bgColor: "hover:bg-[color:var(--color-primary)]/15",
			isActive: false,
			tooltipTextColor: "text-[color:var(--color-text-muted)]",
		},
		{
			id: "zoom-out",
			icon: ZoomOut,
			label: "Zoom Out",
			onClick: handleZoomOut,
			color:
				"text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary)]",
			bgColor: "hover:bg-[color:var(--color-primary)]/15",
			isActive: false,
			tooltipTextColor: "text-[color:var(--color-text-muted)]",
		},
		{
			id: "fit-view",
			icon: Maximize2,
			label: "Fit View",
			onClick: handleFitView,
			color:
				"text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary)]",
			bgColor: "hover:bg-[color:var(--color-primary)]/15",
			isActive: false,
			tooltipTextColor: "text-[color:var(--color-text-muted)]",
		},
		...(onAutoLayout
			? [
					{
						id: "auto-layout",
						icon: GitBranch,
						label: "Auto Layout",
						onClick: onAutoLayout,
						color:
							"text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary)]",
						bgColor: "hover:bg-[color:var(--color-primary)]/15",
						isActive: false,
						tooltipTextColor: "text-[color:var(--color-text-muted)]",
					},
				]
			: []),
		// Canvas preference toggles
		...(onToggleSnapToGrid
			? [
					{
						id: "snap-to-grid",
						icon: Grid3X3,
						label: "Snap to Grid",
						onClick: onToggleSnapToGrid,
						color: snapToGrid
							? "text-[color:var(--color-primary)]"
							: "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary)]",
						bgColor: snapToGrid
							? "bg-[color:var(--color-primary)]/20"
							: "hover:bg-[color:var(--color-primary)]/15",
						isActive: snapToGrid,
						tooltipTextColor: snapToGrid
							? "text-[color:var(--color-primary)]"
							: "text-[color:var(--color-text-muted)]",
					},
				]
			: []),
		...(onToggleMiniMap
			? [
					{
						id: "toggle-minimap",
						icon: Map,
						label: "Minimap",
						onClick: onToggleMiniMap,
						color: showMiniMap
							? "text-[color:var(--color-primary)]"
							: "text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary)]",
						bgColor: showMiniMap
							? "bg-[color:var(--color-primary)]/20"
							: "hover:bg-[color:var(--color-primary)]/15",
						isActive: showMiniMap,
						tooltipTextColor: showMiniMap
							? "text-[color:var(--color-primary)]"
							: "text-[color:var(--color-text-muted)]",
					},
				]
			: []),
		// Keyboard shortcuts button
		...(onShowShortcuts
			? [
					{
						id: "shortcuts-help",
						icon: Keyboard,
						label: "Shortcuts",
						onClick: onShowShortcuts,
						color:
							"text-[color:var(--color-text-muted)] hover:text-[color:var(--color-primary)]",
						bgColor: "hover:bg-[color:var(--color-primary)]/15",
						isActive: false,
						tooltipTextColor: "text-[color:var(--color-text-muted)]",
					},
				]
			: []),
	];

	// Positioning classes
	const containerClass = isHorizontal
		? position === "fixed"
			? "fixed bottom-6 left-1/2 -translate-x-1/2 z-40"
			: "absolute bottom-6 left-1/2 -translate-x-1/2 z-20"
		: position === "fixed"
			? "fixed bottom-8 z-40"
			: "absolute bottom-6 left-6 z-20";

	// Container flex direction and styling
	const innerClass = isHorizontal
		? "flex flex-row items-center gap-1.5 rounded-2xl border-2 border-[color:var(--color-primary)]/25 bg-[color:var(--color-bg-secondary)]/90 px-3 py-2.5 shadow-lg backdrop-blur-xl"
		: "flex flex-col gap-2 rounded-2xl border-2 border-[color:var(--color-primary)]/35 bg-[color:var(--color-bg-secondary)]/90 px-3 py-3 shadow-[0_18px_40px_rgba(0,0,0,0.45)] backdrop-blur-xl";

	// Button sizing
	const buttonClass = isHorizontal
		? "rounded-lg p-3 transition-all duration-200 hover:scale-110"
		: "rounded-xl p-3 transition-all duration-300 hover:scale-110 hover:shadow-lg";

	const iconClass = isHorizontal ? "h-[18px] w-[18px]" : "h-5 w-5";

	return (
		<div
			className={clsx(containerClass, className, "transition-all duration-300")}
			style={
				!isHorizontal && position === "fixed"
					? { left: "calc(var(--sidebar-width, 0px) + 2rem)" }
					: undefined
			}
			data-tutorial="canvas-controls"
		>
			<div className={innerClass}>
				{buttons.map((button) => {
					const Icon = button.icon;
					return (
						<div key={button.id} className="relative">
							<button
								onClick={button.onClick}
								onMouseEnter={createMouseEnterHandler(button.id)}
								onMouseLeave={clearTooltip}
								className={clsx(
									buttonClass,
									button.color,
									button.bgColor,
								)}
							>
								<Icon className={iconClass} />
							</button>
							{showTooltip === button.id && (
								isHorizontal ? (
									// Tooltip above for horizontal layout
									<div className={clsx("absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 transform whitespace-nowrap rounded-lg border border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/95 px-2.5 py-1.5 text-xs shadow-xl backdrop-blur-sm", button.tooltipTextColor)}>
										{button.label}
										<div className="absolute top-full left-1/2 -translate-x-1/2 transform">
											<div className="h-0 w-0 border-x-4 border-t-4 border-x-transparent border-t-[color:var(--color-bg-secondary)]/95" />
										</div>
									</div>
								) : (
									// Tooltip to the right for vertical layout
									<div className={clsx("absolute left-full top-1/2 z-50 ml-3 -translate-y-1/2 transform whitespace-nowrap rounded-lg border border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/95 px-3 py-2 text-xs shadow-xl backdrop-blur-sm", button.tooltipTextColor)}>
										{button.label}
										<div className="absolute right-full top-1/2 -translate-y-1/2 transform">
											<div className="h-0 w-0 border-y-4 border-l-4 border-y-transparent border-l-[color:var(--color-bg-secondary)]/95" />
										</div>
									</div>
								)
							)}
						</div>
					);
				})}
			</div>
		</div>
	);
}
