/**
 * Accessibility utilities and helpers
 */

/**
 * Generate a unique ID for accessibility purposes
 */
export function generateId(prefix = "id"): string {
	return `${prefix}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Keyboard navigation keys
 */
export const KEYS = {
	ENTER: "Enter",
	SPACE: " ",
	ESCAPE: "Escape",
	TAB: "Tab",
	ARROW_UP: "ArrowUp",
	ARROW_DOWN: "ArrowDown",
	ARROW_LEFT: "ArrowLeft",
	ARROW_RIGHT: "ArrowRight",
	HOME: "Home",
	END: "End",
	PAGE_UP: "PageUp",
	PAGE_DOWN: "PageDown",
} as const;

/**
 * Check if a keyboard event matches a specific key
 */
export function isKey(
	event: React.KeyboardEvent,
	key: keyof typeof KEYS,
): boolean {
	return event.key === KEYS[key];
}

/**
 * Handle keyboard navigation for menu/list items
 */
export function handleListKeyNavigation(
	event: React.KeyboardEvent,
	currentIndex: number,
	itemCount: number,
	onSelect: (index: number) => void,
	onActivate?: (index: number) => void,
): void {
	switch (event.key) {
		case KEYS.ARROW_DOWN:
			event.preventDefault();
			onSelect((currentIndex + 1) % itemCount);
			break;
		case KEYS.ARROW_UP:
			event.preventDefault();
			onSelect((currentIndex - 1 + itemCount) % itemCount);
			break;
		case KEYS.HOME:
			event.preventDefault();
			onSelect(0);
			break;
		case KEYS.END:
			event.preventDefault();
			onSelect(itemCount - 1);
			break;
		case KEYS.ENTER:
		case KEYS.SPACE:
			event.preventDefault();
			onActivate?.(currentIndex);
			break;
	}
}

/**
 * Trap focus within a container (useful for modals)
 */
export function trapFocus(container: HTMLElement): () => void {
	const focusableElements = container.querySelectorAll<HTMLElement>(
		'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select, [tabindex]:not([tabindex="-1"])',
	);

	const firstFocusable = focusableElements[0];
	const lastFocusable = focusableElements[focusableElements.length - 1];

	const handleKeyDown = (e: KeyboardEvent) => {
		if (e.key !== "Tab") return;

		if (e.shiftKey) {
			if (document.activeElement === firstFocusable) {
				e.preventDefault();
				lastFocusable?.focus();
			}
		} else {
			if (document.activeElement === lastFocusable) {
				e.preventDefault();
				firstFocusable?.focus();
			}
		}
	};

	container.addEventListener("keydown", handleKeyDown);
	firstFocusable?.focus();

	return () => {
		container.removeEventListener("keydown", handleKeyDown);
	};
}

/**
 * Announce message to screen readers
 */
export function announce(
	message: string,
	priority: "polite" | "assertive" = "polite",
): void {
	const announcement = document.createElement("div");
	announcement.setAttribute("aria-live", priority);
	announcement.setAttribute("aria-atomic", "true");
	announcement.setAttribute("class", "sr-only");
	announcement.textContent = message;

	document.body.appendChild(announcement);

	setTimeout(() => {
		document.body.removeChild(announcement);
	}, 1000);
}

/**
 * Get contrast ratio between two colors
 */
export function getContrastRatio(color1: string, color2: string): number {
	const getLuminance = (color: string): number => {
		const rgb = color.match(/\d+/g);
		if (!rgb) return 0;

		const [r, g, b] = rgb.map((val) => {
			const sRGB = parseInt(val) / 255;
			return sRGB <= 0.03928 ? sRGB / 12.92 : ((sRGB + 0.055) / 1.055) ** 2.4;
		});

		return 0.2126 * r + 0.7152 * g + 0.0722 * b;
	};

	const l1 = getLuminance(color1);
	const l2 = getLuminance(color2);
	const lighter = Math.max(l1, l2);
	const darker = Math.min(l1, l2);

	return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if contrast meets WCAG standards
 */
export function meetsContrastGuidelines(
	ratio: number,
	fontSize = 16,
	isBold = false,
): { AA: boolean; AAA: boolean } {
	const isLargeText = fontSize >= 18 || (fontSize >= 14 && isBold);

	return {
		AA: ratio >= (isLargeText ? 3 : 4.5),
		AAA: ratio >= (isLargeText ? 4.5 : 7),
	};
}

/**
 * Skip to main content link helper
 */
export function skipToMain(): void {
	const main =
		document.querySelector("main") || document.querySelector('[role="main"]');
	if (main instanceof HTMLElement) {
		main.tabIndex = -1;
		main.focus();
		main.removeAttribute("tabindex");
	}
}

/**
 * Screen reader only class
 */
export const srOnly =
	"absolute w-px h-px p-0 -m-px overflow-hidden whitespace-nowrap border-0";

/**
 * Focus visible class for keyboard navigation
 */
export const focusVisible =
	"focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)] focus:ring-offset-2 focus:ring-offset-gray-900";

/**
 * Common ARIA labels
 */
export const ARIA_LABELS = {
	CLOSE: "Close",
	OPEN_MENU: "Open menu",
	CLOSE_MENU: "Close menu",
	LOADING: "Loading",
	ERROR: "Error",
	SUCCESS: "Success",
	WARNING: "Warning",
	INFO: "Information",
	SEARCH: "Search",
	FILTER: "Filter",
	SORT: "Sort",
	PREVIOUS: "Previous",
	NEXT: "Next",
	EXPAND: "Expand",
	COLLAPSE: "Collapse",
	DELETE: "Delete",
	EDIT: "Edit",
	SAVE: "Save",
	CANCEL: "Cancel",
	SUBMIT: "Submit",
} as const;
