import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { KEYS, trapFocus } from "@/lib/accessibility";

/**
 * Hook for managing focus trap (useful for modals/dialogs)
 */
export function useFocusTrap<T extends HTMLElement = HTMLDivElement>(
	isActive = true,
) {
	const containerRef = useRef<T>(null);

	useEffect(() => {
		if (!isActive || !containerRef.current) return;

		const cleanup = trapFocus(containerRef.current);
		return cleanup;
	}, [isActive]);

	return containerRef;
}

/**
 * Hook for keyboard navigation in lists/menus
 */
export function useKeyboardNavigation(
	itemCount: number,
	onSelect?: (index: number) => void,
	initialIndex = 0,
) {
	const [selectedIndex, setSelectedIndex] = useState(initialIndex);

	const handleKeyDown = useCallback(
		(event: React.KeyboardEvent) => {
			switch (event.key) {
				case KEYS.ARROW_DOWN:
					event.preventDefault();
					setSelectedIndex((prev) => {
						const next = (prev + 1) % itemCount;
						onSelect?.(next);
						return next;
					});
					break;
				case KEYS.ARROW_UP:
					event.preventDefault();
					setSelectedIndex((prev) => {
						const next = (prev - 1 + itemCount) % itemCount;
						onSelect?.(next);
						return next;
					});
					break;
				case KEYS.HOME:
					event.preventDefault();
					setSelectedIndex(0);
					onSelect?.(0);
					break;
				case KEYS.END:
					event.preventDefault();
					setSelectedIndex(itemCount - 1);
					onSelect?.(itemCount - 1);
					break;
			}
		},
		[itemCount, onSelect],
	);

	return {
		selectedIndex,
		setSelectedIndex,
		handleKeyDown,
	};
}

/**
 * Hook for escape key handling
 */
export function useEscapeKey(onEscape: () => void, isActive = true) {
	useEffect(() => {
		if (!isActive) return;

		const handleEscape = (event: KeyboardEvent) => {
			if (event.key === KEYS.ESCAPE) {
				onEscape();
			}
		};

		document.addEventListener("keydown", handleEscape);
		return () => document.removeEventListener("keydown", handleEscape);
	}, [onEscape, isActive]);
}

/**
 * Hook for managing ARIA live regions
 */
export function useAriaLive() {
	const [message, setMessage] = useState("");
	const [priority, setPriority] = useState<"polite" | "assertive">("polite");

	const announce = useCallback(
		(text: string, level: "polite" | "assertive" = "polite") => {
			setMessage(text);
			setPriority(level);

			// Clear message after announcement
			setTimeout(() => setMessage(""), 100);
		},
		[],
	);

	return {
		message,
		priority,
		announce,
	};
}

/**
 * Hook for managing focus on mount
 */
export function useAutoFocus<T extends HTMLElement = HTMLElement>(
	shouldFocus = true,
	delay = 0,
) {
	const elementRef = useRef<T>(null);

	useEffect(() => {
		if (!shouldFocus || !elementRef.current) return;

		const timeoutId = setTimeout(() => {
			elementRef.current?.focus();
		}, delay);

		return () => clearTimeout(timeoutId);
	}, [shouldFocus, delay]);

	return elementRef;
}

/**
 * Hook for roving tabindex pattern
 */
export function useRovingTabIndex(
	itemCount: number,
	orientation: "horizontal" | "vertical" = "vertical",
) {
	const [focusedIndex, setFocusedIndex] = useState(0);

	const handleKeyDown = useCallback(
		(event: React.KeyboardEvent) => {
			const horizontalKeys = [KEYS.ARROW_LEFT, KEYS.ARROW_RIGHT];
			const verticalKeys = [KEYS.ARROW_UP, KEYS.ARROW_DOWN];
			const navigationKeys =
				orientation === "horizontal" ? horizontalKeys : verticalKeys;

			if (event.key === navigationKeys[0]) {
				// Previous item
				event.preventDefault();
				setFocusedIndex((prev) => (prev - 1 + itemCount) % itemCount);
			} else if (event.key === navigationKeys[1]) {
				// Next item
				event.preventDefault();
				setFocusedIndex((prev) => (prev + 1) % itemCount);
			} else if (event.key === KEYS.HOME) {
				event.preventDefault();
				setFocusedIndex(0);
			} else if (event.key === KEYS.END) {
				event.preventDefault();
				setFocusedIndex(itemCount - 1);
			}
		},
		[itemCount, orientation],
	);

	const getRovingProps = useCallback(
		(index: number) => ({
			tabIndex: index === focusedIndex ? 0 : -1,
			onFocus: () => setFocusedIndex(index),
		}),
		[focusedIndex],
	);

	return {
		focusedIndex,
		handleKeyDown,
		getRovingProps,
	};
}

/**
 * Hook for WAI-ARIA tree keyboard navigation.
 * Handles ArrowUp/Down (visible items), ArrowLeft/Right (collapse/expand),
 * Home/End (first/last), and Enter/Space (activate).
 */
export function useTreeNavigation<T extends { id: string; children: T[] }>(
	nodes: T[],
	expandedIds: Set<string>,
	callbacks: {
		onToggle: (id: string) => void;
		onActivate: (id: string) => void;
		getParentId: (id: string) => string | null;
	},
) {
	const [focusedId, setFocusedId] = useState<string | null>(null);

	const visibleIds = useMemo(() => {
		const result: string[] = [];
		const walk = (items: T[]) => {
			for (const item of items) {
				result.push(item.id);
				if (item.children.length > 0 && expandedIds.has(item.id)) {
					walk(item.children);
				}
			}
		};
		walk(nodes);
		return result;
	}, [nodes, expandedIds]);

	const hasChildrenMap = useMemo(() => {
		const map = new Map<string, boolean>();
		const walk = (items: T[]) => {
			for (const item of items) {
				map.set(item.id, item.children.length > 0);
				walk(item.children);
			}
		};
		walk(nodes);
		return map;
	}, [nodes]);

	const handleTreeKeyDown = useCallback(
		(event: React.KeyboardEvent) => {
			const currentIndex = focusedId
				? visibleIds.indexOf(focusedId)
				: -1;

			switch (event.key) {
				case KEYS.ARROW_DOWN: {
					event.preventDefault();
					const next = currentIndex + 1;
					if (next < visibleIds.length)
						setFocusedId(visibleIds[next]);
					break;
				}
				case KEYS.ARROW_UP: {
					event.preventDefault();
					const prev = currentIndex - 1;
					if (prev >= 0) setFocusedId(visibleIds[prev]);
					break;
				}
				case KEYS.ARROW_RIGHT: {
					event.preventDefault();
					if (!focusedId) break;
					const hasKids = hasChildrenMap.get(focusedId);
					if (hasKids && !expandedIds.has(focusedId)) {
						callbacks.onToggle(focusedId);
					} else if (hasKids && expandedIds.has(focusedId)) {
						const nextIdx = currentIndex + 1;
						if (nextIdx < visibleIds.length)
							setFocusedId(visibleIds[nextIdx]);
					}
					break;
				}
				case KEYS.ARROW_LEFT: {
					event.preventDefault();
					if (!focusedId) break;
					const hasKids = hasChildrenMap.get(focusedId);
					if (hasKids && expandedIds.has(focusedId)) {
						callbacks.onToggle(focusedId);
					} else {
						const parentId = callbacks.getParentId(focusedId);
						if (parentId) setFocusedId(parentId);
					}
					break;
				}
				case KEYS.HOME: {
					event.preventDefault();
					if (visibleIds.length > 0) setFocusedId(visibleIds[0]);
					break;
				}
				case KEYS.END: {
					event.preventDefault();
					if (visibleIds.length > 0)
						setFocusedId(visibleIds[visibleIds.length - 1]);
					break;
				}
				case KEYS.ENTER:
				case KEYS.SPACE: {
					event.preventDefault();
					if (focusedId) callbacks.onActivate(focusedId);
					break;
				}
			}
		},
		[focusedId, visibleIds, expandedIds, hasChildrenMap, callbacks],
	);

	const getTreeItemProps = useCallback(
		(id: string) => ({
			tabIndex: focusedId === id ? 0 : -1,
			onFocus: () => setFocusedId(id),
		}),
		[focusedId],
	);

	return { focusedId, setFocusedId, handleTreeKeyDown, getTreeItemProps };
}

/**
 * Hook for managing keyboard shortcuts
 */
export function useKeyboardShortcut(
	key: string,
	callback: () => void,
	options: {
		ctrl?: boolean;
		alt?: boolean;
		shift?: boolean;
		preventDefault?: boolean;
	} = {},
) {
	useEffect(() => {
		const handleKeyDown = (event: KeyboardEvent) => {
			const {
				ctrl = false,
				alt = false,
				shift = false,
				preventDefault = true,
			} = options;

			if (
				event.key.toLowerCase() === key.toLowerCase() &&
				event.ctrlKey === ctrl &&
				event.altKey === alt &&
				event.shiftKey === shift
			) {
				if (preventDefault) {
					event.preventDefault();
				}
				callback();
			}
		};

		document.addEventListener("keydown", handleKeyDown);
		return () => document.removeEventListener("keydown", handleKeyDown);
	}, [key, callback, options]);
}
