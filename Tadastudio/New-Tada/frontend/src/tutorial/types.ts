/**
 * Declares where the pointer + popover appear relative to the highlighted element.
 * The pointer tip is placed at that edge/corner; the popover extends outward.
 *
 *   top-left      top-center      top-right
 *   left-center   [element]       right-center
 *   bottom-left   bottom-center   bottom-right
 */
export type PointerPlacement =
	| "top-left"
	| "top-center"
	| "top-right"
	| "bottom-left"
	| "bottom-center"
	| "bottom-right"
	| "left-center"
	| "right-center";

export interface TutorialStep {
	/** CSS selector for the highlighted element. Omit for a centered popover with no pointer. */
	element?: string;
	popover: {
		title: string;
		description: string;
		side?: "top" | "bottom" | "left" | "right";
		align?: "start" | "center" | "end";
	};
	/** Where to place the pointer and popover. Defaults to "bottom-center". */
	pointerPlacement?: PointerPlacement;
	/** CSS selector for the pointer/popover target when it differs from the cutout element. */
	pointerTarget?: string;
	waitForElement?: boolean;
	/** Auto-advance after a delay (ms) without the user clicking Next. */
	autoAdvanceDelay?: number;
	/** CSS selector that must exist in DOM before advancing past this step */
	completionSelector?: string;
	/**
	 * Custom event dispatched on `window` when "Next" is clicked.
	 * The hosting page (e.g. AgentBuilder) listens for these events
	 * and performs the actual operation (e.g. connecting nodes).
	 */
	nextEvent?: {
		/** Event name dispatched on `window`. */
		event: string;
		/** Arbitrary payload forwarded as `event.detail`. */
		detail?: Record<string, unknown>;
	};
	/** Dispatch a fitView event when this step is highlighted so all nodes are visible. */
	fitView?: boolean;
	/** Prevent the config panel from being closed (X, Cancel, backdrop) while this step is active. */
	preventPanelClose?: boolean;
	/** CSS selector of an element to auto-click when this step is highlighted (e.g. open a dropdown or select a tab). */
	autoClickSelector?: string;
	/** CSS selector of an element to auto-click when "Next" is pressed, before advancing to the next step. */
	nextClickSelector?: string;
	/** Fields to auto-fill when this step is highlighted (e.g. form inputs). */
	autoFill?: Array<{ selector: string; value: string }>;
	/** Scroll the element to the center of the viewport instead of the nearest edge. */
	scrollCenter?: boolean;
	/** CSS selector that must exist in the DOM for this step to be shown. If absent, the step is skipped. */
	skipIfNotFound?: string;
}

export interface TutorialState {
	completedTutorials: Record<string, boolean>;
	lastStepReached: Record<string, number>;
	version: number;
}

export interface TutorialContextValue {
	startTutorial(id: string): void;
	stopTutorial(): void;
	isRunning: boolean;
	activeTutorialId: string | null;
	completedTutorials: Record<string, boolean>;
	refreshCompletionState(): void;
	/** Non-null when a tutorial is preparing async resources before starting */
	setupProgress: string | null;
}

export interface TutorialDefinition {
	id: string;
	label: string;
	icon: string;
	stepCount: number;
	estimatedMinutes: number;
	/** Route to navigate to before starting the tutorial */
	route: string;
	steps: TutorialStep[];
	/** ID of the next tutorial to offer when this one completes */
	nextTutorialId?: string;
}
