"use client";

import { type ReactNode, useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface TooltipProps {
	children: ReactNode;
	content: string;
	/** Position of tooltip relative to trigger */
	position?: "top" | "right" | "bottom" | "left";
	/** Whether tooltip is disabled */
	disabled?: boolean;
	/** Additional class for the wrapper */
	className?: string;
	/** Display mode: "inline-flex" (default) or "block" for truncated content */
	display?: "inline-flex" | "block";
}

/**
 * Reusable Tooltip component matching Ant Design style
 * - Background: rgb(64,64,64)
 * - Text: rgb(214,214,214)
 * - Border radius: 6px
 * - Padding: 4px 6px
 * Uses portal to escape overflow:hidden containers
 */
export default function Tooltip({
	children,
	content,
	position = "right",
	disabled = false,
	className = "",
	display = "inline-flex",
}: TooltipProps) {
	const [isVisible, setIsVisible] = useState(false);
	const [coords, setCoords] = useState({ top: 0, left: 0 });
	const [mounted, setMounted] = useState(false);
	const triggerRef = useRef<HTMLDivElement>(null);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	const updatePosition = useCallback(() => {
		if (!triggerRef.current) return;
		const rect = triggerRef.current.getBoundingClientRect();
		
		let top = 0;
		let left = 0;

		switch (position) {
			case "right":
				top = rect.top + rect.height / 2;
				left = rect.right + 8;
				break;
			case "left":
				top = rect.top + rect.height / 2;
				left = rect.left - 8;
				break;
			case "top":
				top = rect.top - 8;
				left = rect.left + rect.width / 2;
				break;
			case "bottom":
				top = rect.bottom + 8;
				left = rect.left + rect.width / 2;
				break;
		}

		setCoords({ top, left });
	}, [position]);

	const handleMouseEnter = useCallback(() => {
		updatePosition();
		setIsVisible(true);
	}, [updatePosition]);

	const handleMouseLeave = useCallback(() => {
		setIsVisible(false);
	}, []);

	if (disabled) {
		return <>{children}</>;
	}

	const transformClasses = {
		top: "-translate-x-1/2 -translate-y-full",
		right: "-translate-y-1/2",
		bottom: "-translate-x-1/2",
		left: "-translate-x-full -translate-y-1/2",
	};

	const arrowPositions = {
		top: "top-full left-1/2 -translate-x-1/2 -mt-1",
		right: "right-full top-1/2 -translate-y-1/2 -mr-1",
		bottom: "bottom-full left-1/2 -translate-x-1/2 -mb-1",
		left: "left-full top-1/2 -translate-y-1/2 -ml-1",
	};

	const tooltipContent = isVisible && mounted && (
		<div
			role="tooltip"
			className={`fixed z-[9999] pointer-events-none transition-opacity duration-150 ${transformClasses[position]} ${isVisible ? "opacity-100" : "opacity-0"}`}
			style={{ top: coords.top, left: coords.left }}
		>
			<div className="relative">
				{/* Tooltip box */}
				<span className="block whitespace-nowrap rounded-md bg-[rgb(64,64,64)] px-1.5 py-1 text-xs text-[rgb(214,214,214)]">
					{content}
				</span>
				{/* Arrow */}
				<span className={`absolute h-2 w-2 rotate-45 bg-[rgb(64,64,64)] ${arrowPositions[position]}`} />
			</div>
		</div>
	);

	return (
		<div
			ref={triggerRef}
			className={`relative ${display === "block" ? "block overflow-hidden" : "inline-flex"} ${className}`}
			onMouseEnter={handleMouseEnter}
			onMouseLeave={handleMouseLeave}
		>
			{children}
			{mounted && createPortal(tooltipContent, document.body)}
		</div>
	);
}
