import { type RefObject, useCallback, useEffect, useRef } from "react";
import {
	autoUpdate,
	flip,
	offset as floatingOffset,
	shift,
	size,
	useFloating,
	type Placement,
} from "@floating-ui/react";

export interface DropdownPosition {
	top: number;
	left: number;
	width: number;
	maxHeight: number;
}

export interface UseDropdownOptions {
	isOpen: boolean;
	onClose: () => void;
	triggerRef: RefObject<HTMLElement | null>;
	dropdownRef: RefObject<HTMLElement | null>;
	align?: "start" | "end" | "center";
	side?: "bottom" | "top" | "auto";
	maxHeight?: number;
	width?: number | "trigger" | "auto";
	/** When width is "trigger", menu width is at least this many px (helps long labels stay inside the panel). */
	menuMinWidthPx?: number;
	offset?: number;
}

export interface UseDropdownReturn {
	position: DropdownPosition;
	setTriggerRef: (el: HTMLElement | null) => void;
	setDropdownRef: (el: HTMLDivElement | null) => void;
}

function buildPlacement(
	side: "bottom" | "top" | "auto",
	align: "start" | "end" | "center",
): Placement {
	const baseSide = side === "auto" ? "bottom" : side;
	if (align === "center") return baseSide;
	return `${baseSide}-${align}`;
}

export function useDropdown({
	isOpen,
	onClose,
	triggerRef,
	dropdownRef,
	align = "start",
	side = "auto",
	maxHeight = 400,
	width = "trigger",
	menuMinWidthPx,
	offset = 8,
}: UseDropdownOptions): UseDropdownReturn {
	const sizeDataRef = useRef({ width: 0, maxHeight: 0 });

	const placement = buildPlacement(side, align);

	const flipFallbacks: Placement[] | undefined =
		side === "auto"
			? undefined
			: [buildPlacement(side === "bottom" ? "top" : "bottom", align)];

	const { x, y, refs } = useFloating({
		open: isOpen,
		placement,
		strategy: "fixed",
		middleware: [
			floatingOffset(offset),
			flip({
				fallbackPlacements: flipFallbacks,
				padding: 4,
			}),
			shift({ padding: 4 }),
			size({
				padding: 8,
				apply({ availableHeight, rects, elements }) {
					const finalMaxHeight = Math.max(
						0,
						Math.min(maxHeight, availableHeight - 8),
					);

					let finalWidth: number;
					if (typeof width === "number") {
						finalWidth = width;
					} else if (width === "auto") {
						finalWidth = Math.max(200, rects.reference.width);
					} else {
						const refW = rects.reference.width;
						finalWidth =
							typeof menuMinWidthPx === "number" && menuMinWidthPx > 0
								? Math.max(refW, menuMinWidthPx)
								: refW;
					}

					sizeDataRef.current = {
						width: finalWidth,
						maxHeight: finalMaxHeight,
					};

					// Apply directly to DOM to avoid React state render loops
					Object.assign(elements.floating.style, {
						maxHeight: `${finalMaxHeight}px`,
						width: `${finalWidth}px`,
					});
				},
			}),
		],
		whileElementsMounted: autoUpdate,
	});

	// Merged callback refs — set both the external ref AND floating-ui's ref
	// so floating-ui is notified the instant elements mount (including inside FloatingPortal)
	const setTriggerRef = useCallback(
		(el: HTMLElement | null) => {
			(triggerRef as RefObject<HTMLElement | null>).current = el;
			refs.setReference(el);
		},
		[triggerRef, refs],
	);

	const setDropdownRef = useCallback(
		(el: HTMLDivElement | null) => {
			(dropdownRef as RefObject<HTMLElement | null>).current = el;
			refs.setFloating(el);
		},
		[dropdownRef, refs],
	);

	// Handle click outside
	useEffect(() => {
		if (!isOpen) return;

		const handleClickOutside = (event: MouseEvent) => {
			const target = event.target as Node;

			if (
				triggerRef.current &&
				!triggerRef.current.contains(target) &&
				dropdownRef.current &&
				!dropdownRef.current.contains(target)
			) {
				onClose();
			}
		};

		// Use capture phase to catch events before they bubble
		document.addEventListener("mousedown", handleClickOutside, true);

		return () => {
			document.removeEventListener("mousedown", handleClickOutside, true);
		};
	}, [isOpen, onClose, triggerRef, dropdownRef]);

	// Handle escape key
	useEffect(() => {
		if (!isOpen) return;

		const handleEscape = (event: KeyboardEvent) => {
			if (event.key === "Escape") {
				event.preventDefault();
				event.stopPropagation();
				onClose();
			}
		};

		document.addEventListener("keydown", handleEscape, true);

		return () => {
			document.removeEventListener("keydown", handleEscape, true);
		};
	}, [isOpen, onClose]);

	const position: DropdownPosition = {
		top: y ?? 0,
		left: x ?? 0,
		width: sizeDataRef.current.width,
		maxHeight: sizeDataRef.current.maxHeight,
	};

	return { position, setTriggerRef, setDropdownRef };
}
