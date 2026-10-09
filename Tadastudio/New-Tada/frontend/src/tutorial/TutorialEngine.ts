import { driver as createDriver } from "driver.js";
import type { Config, DriveStep, Driver } from "driver.js";
import "driver.js/dist/driver.css";
import { markCompleted } from "./persistence";
import type { PointerPlacement, TutorialStep } from "./types";

const POINTER_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.904 17.563a1.2 1.2 0 0 0 2.228.308l2.09-3.093 4.907 4.907a1.067 1.067 0 0 0 1.509 0l1.047-1.047a1.067 1.067 0 0 0 0-1.509l-4.907-4.907 3.113-2.09a1.2 1.2 0 0 0-.309-2.228L4.16 4.16z"/></svg>`;

/** Tip offset from element edge (px). */
const TIP_GAP = 6;
/** Space between pointer body and popover (px). */
const POPOVER_GAP = 36;

interface PlacementConfig {
	/** Position of the pointer tip relative to the element rect. */
	getTip(r: DOMRect): { x: number; y: number };
	/** CSS rotation (deg) so the cursor tip points toward the element. */
	rotation: number;
	/** Which side of the element the popover extends toward. */
	popoverSide: "top" | "bottom" | "left" | "right";
}

/*
 * Rotation reference (transform-origin at cursor tip ≈ 4px 4px):
 *   0° = tip points NW   (natural SVG orientation)
 *  45° = tip points N     90° = tip points NE
 * 135° = tip points E    180° = tip points SE
 * -45° = tip points W    -90° = tip points SW
 * -135° = tip points S
 */
const PLACEMENTS: Record<PointerPlacement, PlacementConfig> = {
	"bottom-left": {
		getTip: (r) => ({ x: r.left + 8, y: r.bottom + TIP_GAP }),
		rotation: 90,
		popoverSide: "bottom",
	},
	"bottom-center": {
		getTip: (r) => ({ x: r.left + r.width / 2, y: r.bottom + TIP_GAP }),
		rotation: 45,
		popoverSide: "bottom",
	},
	"bottom-right": {
		getTip: (r) => ({ x: r.right - 8, y: r.bottom + TIP_GAP }),
		rotation: 0,
		popoverSide: "bottom",
	},
	"top-left": {
		getTip: (r) => ({ x: r.left + 8, y: r.top - TIP_GAP }),
		rotation: 180,
		popoverSide: "top",
	},
	"top-center": {
		getTip: (r) => ({ x: r.left + r.width / 2, y: r.top - TIP_GAP }),
		rotation: -135,
		popoverSide: "top",
	},
	"top-right": {
		getTip: (r) => ({ x: r.right - 8, y: r.top - TIP_GAP }),
		rotation: -90,
		popoverSide: "top",
	},
	"left-center": {
		getTip: (r) => ({ x: r.left - TIP_GAP, y: r.top + r.height / 2 }),
		rotation: 135,
		popoverSide: "left",
	},
	"right-center": {
		getTip: (r) => ({ x: r.right + TIP_GAP, y: r.top + r.height / 2 }),
		rotation: -45,
		popoverSide: "right",
	},
};

export type DestroyReason = "completed" | "dismissed" | "stopped";

export class TutorialEngine {
	private driverInstance: Driver | null = null;
	private activeTutorialId: string | null = null;
	private activeSteps: TutorialStep[] = [];
	private cleanupFns: Array<() => void> = [];
	private onCompleteCallback: ((id: string) => void) | null = null;
	private onDestroyCallback:
		| ((id: string, reason: DestroyReason) => void)
		| null = null;
	private pendingWaitAbort: AbortController | null = null;
	private pointerEl: HTMLElement | null = null;
	private activePointerSelector: string | null = null;
	private pointerTrackingCleanup: (() => void) | null = null;
	private activeStepIndex = 0;
	private earlyAutoClicked = -1;
	private nextTutorialId: string | null = null;
	private nextTutorialLabel: string | null = null;
	private activePlacement: PointerPlacement = "bottom-center";
	private escHandler: ((e: KeyboardEvent) => void) | null = null;
	private dragCleanup: (() => void) | null = null;

	/**
	 * querySelector that prefers the first *visible* match when multiple
	 * elements share the same selector (e.g. desktop vs compact nav bars).
	 */
	private queryVisible<T extends Element = Element>(selector: string): T | null {
		const all = document.querySelectorAll<T>(selector);
		if (all.length <= 1) return (all[0] as T) ?? null;
		for (const el of all) {
			const htmlEl = el as unknown as HTMLElement;
			if (htmlEl.offsetWidth > 0 || htmlEl.offsetHeight > 0) return el;
		}
		return (all[0] as T) ?? null;
	}

	start(
		tutorialId: string,
		steps: TutorialStep[],
		startStep?: number,
		onComplete?: (id: string) => void,
		onDestroy?: (id: string, reason: DestroyReason) => void,
		nextTutorialId?: string,
		nextTutorialLabel?: string,
	): void {
		this.stop();

		this.activeTutorialId = tutorialId;
		this.activeSteps = steps;
		this.onCompleteCallback = onComplete ?? null;
		this.onDestroyCallback = onDestroy ?? null;
		this.nextTutorialId = nextTutorialId ?? null;
		this.nextTutorialLabel = nextTutorialLabel ?? null;

		const driverSteps = this.buildDriverSteps(steps);
		const lastStepIndex = steps.length - 1;

		const config: Config = {
			animate: true,
			overlayColor: "#000",
			overlayOpacity: 0.15,
			stagePadding: 12,
			stageRadius: 8,
			allowClose: false,
			showProgress: true,
			popoverClass: "as-tutorial-popover",
			showButtons: ["next", "previous", "close"],
			nextBtnText: "Next \u2192",
			prevBtnText: "\u2190 Back",
			doneBtnText: "Finish \u2713",
			steps: driverSteps,
			onNextClick: () => {
				const idx = this.driverInstance?.getActiveIndex() ?? 0;
				const step = this.activeSteps[idx];
				if (!step) {
					this.advanceToNext();
					return;
				}
				this.executeNextAction(step);
			},
			onPrevClick: () => {
				const idx = this.driverInstance?.getActiveIndex() ?? 0;
				if (idx > 0) {
					this.goToStep(idx - 1);
				}
			},
			onDeselected: () => {
				this.cleanupListeners();
			},
			onHighlighted: (_el, _step) => {
				const idx = this.driverInstance?.getActiveIndex() ?? 0;
				this.activeStepIndex = idx;
				if (idx < this.activeSteps.length) {
					const tutorialStep = this.activeSteps[idx];
					const prevStep = idx > 0 ? this.activeSteps[idx - 1] : null;
					// Close anything the previous step auto-opened (dropdowns, popovers)
					if (prevStep?.autoClickSelector) {
						this.closeAutoOpened(prevStep.autoClickSelector);
					}

					// Scroll the element into view within its scroll
					// container (driver.js only handles page-level scroll).
					// Skip when fitView is set — fitView handles canvas
					// viewport positioning and scrollIntoView fights it.
					// Skip when no element is defined (centered popover).
					if (!tutorialStep.fitView && tutorialStep.element) {
						const targetEl = this.queryVisible<HTMLElement>(tutorialStep.element);
						if (targetEl) {
							targetEl.scrollIntoView({
								behavior: "smooth",
								block: tutorialStep.scrollCenter ? "center" : "nearest",
							});
						}
					}

					if (tutorialStep.fitView) {
						window.dispatchEvent(new CustomEvent("tutorialFitView"));
						// Reposition the pointer after the fitView animation
						// moves canvas elements to new positions.
						setTimeout(() => {
							if (this.driverInstance?.getActiveIndex() === idx) {
								const pSelector = tutorialStep.pointerTarget ?? tutorialStep.element;
								if (pSelector) {
									this.positionPointer(pSelector);
									const wrapper = document.querySelector<HTMLElement>(
										".driver-popover.as-tutorial-popover",
									);
									if (wrapper) {
										const pl = tutorialStep.pointerPlacement ?? "bottom-center";
										this.anchorPopoverOnPointer(wrapper, pSelector, pl);
										this.resolvePointerPopoverOverlap(wrapper, pSelector, pl);
									}
								}
							}
						}, 500);
					}
					if (
						tutorialStep.waitForElement &&
						tutorialStep.element &&
						!this.queryVisible(tutorialStep.element)
					) {
						this.waitForElement(tutorialStep.element).then(
							(found) => {
								if (
									found &&
									this.driverInstance?.isActive() &&
									this.driverInstance.getActiveIndex() === idx
								) {
									this.goToStep(idx);
								}
							},
						);
					}

					// Auto-advance after delay (no user interaction needed)
					if (tutorialStep.autoAdvanceDelay) {
						const timer = setTimeout(() => {
							this.advanceToNext();
						}, tutorialStep.autoAdvanceDelay);
						this.cleanupFns.push(() => clearTimeout(timer));
					}

					// Auto-fill form fields on highlight
					if (tutorialStep.autoFill) {
						setTimeout(() => {
							if (this.driverInstance?.getActiveIndex() === idx) {
								this.executeAutoFill(tutorialStep.autoFill!);
							}
						}, 300);
					}

					// Auto-click element on highlight (e.g. open a dropdown or select a tab).
					// Skip if goToStepSkipping already fired the click for this step.
					if (tutorialStep.autoClickSelector && this.earlyAutoClicked !== idx) {
						const selector = tutorialStep.autoClickSelector;
						setTimeout(() => {
							if (this.driverInstance?.getActiveIndex() === idx) {
								const clickEl = this.queryVisible<HTMLElement>(selector);
								if (clickEl) clickEl.click();
								// Re-scroll after auto-click may have expanded/changed content
								if (tutorialStep.element) {
									setTimeout(() => {
										if (this.driverInstance?.getActiveIndex() === idx) {
											const el = this.queryVisible<HTMLElement>(tutorialStep.element!);
											if (el) {
												el.scrollIntoView({
													behavior: "smooth",
													block: "center",
												});
											}
										}
									}, 300);
								}
							}
						}, 250);
					}
				}
			},
			onDestroyed: () => {
				const idx = this.activeStepIndex;
				const tutorialId = this.activeTutorialId;
				const isComplete =
					idx >= lastStepIndex && tutorialId != null;

				if (isComplete && tutorialId) {
					markCompleted(tutorialId);
					this.onCompleteCallback?.(tutorialId);
				}

				this.cleanupListeners();
				this.removeEscHandler();
				this.cancelPendingWait();
				const destroyCb = this.onDestroyCallback;
				const destroyId = this.activeTutorialId;
				this.driverInstance = null;
				this.activeTutorialId = null;
				this.activeSteps = [];
				this.onCompleteCallback = null;
				this.onDestroyCallback = null;
				this.nextTutorialId = null;
				this.nextTutorialLabel = null;

				if (destroyId && destroyCb) {
					destroyCb(
						destroyId,
						isComplete ? "completed" : "dismissed",
					);
				}
			},
		};

		this.driverInstance = createDriver(config);

		this.escHandler = (e: KeyboardEvent) => {
			if (e.key === "Escape") {
				e.stopImmediatePropagation();
				this.stop();
			}
		};
		document.addEventListener("keydown", this.escHandler);

		const resolvedStart = startStep ?? 0;
		const targetStep = steps[resolvedStart];

		if (targetStep?.waitForElement && targetStep.element) {
			this.waitForElement(targetStep.element).then(() => {
				this.goToStep(resolvedStart);
			});
		} else {
			this.goToStep(resolvedStart);
		}
	}

	stop(): void {
		delete document.body.dataset.tutorialLockPanel;
		this.hideActionProgress();
		this.cleanupListeners();
		this.removeEscHandler();
		this.cancelPendingWait();
		const destroyCb = this.onDestroyCallback;
		const destroyId = this.activeTutorialId;
		this.onDestroyCallback = null;
		this.onCompleteCallback = null;
		this.driverInstance?.destroy();
		this.removePointer();
		this.driverInstance = null;
		this.activeTutorialId = null;
		this.activeSteps = [];
		this.earlyAutoClicked = -1;
		this.nextTutorialId = null;
		this.nextTutorialLabel = null;

		if (destroyId && destroyCb) {
			destroyCb(destroyId, "stopped");
		}
	}

	isActive(): boolean {
		return this.driverInstance?.isActive() ?? false;
	}

	// ── Single step-transition method ──────────────────────────────

	/**
	 * The single way to navigate to any step. Rebuilds the driver step
	 * list (so element references are fresh) and calls drive() to render
	 * the step. Duplicate overlays / popovers left by drive() are cleaned
	 * up in the onHighlighted callback.
	 */
	private goToStep(idx: number): void {
		if (!this.driverInstance) return;
		this.removePointer();
		this.driverInstance.drive(idx);
	}

	/**
	 * Immediately hide the pointer and driver.js popover/overlay so nothing
	 * lingers on screen while the engine waits for the next step's element.
	 */
	private hideCurrentStepUI(): void {
		this.removePointer();
		const popover = document.querySelector<HTMLElement>(".driver-popover.as-tutorial-popover");
		if (popover) popover.style.display = "none";
		const overlay = document.querySelector<HTMLElement>(".driver-overlay");
		if (overlay) overlay.style.display = "none";
	}

	// ── Action progress ─────────────────────────────────────────────

	private showActionProgress(_message: string): void {
		// No-op: progress indicator removed — transitions are fast enough
	}

	private hideActionProgress(): void {
		// No-op: progress indicator removed
	}

	// ── Next-click action handling ──────────────────────────────────

	/**
	 * Execute any action associated with the current step when "Next" is clicked,
	 * then advance to the next step.
	 */
	private executeNextAction(step: TutorialStep): void {
		// Immediately clear the current pointer and popover so nothing
		// lingers on screen while the action runs.
		this.hideCurrentStepUI();

		// Ensure any autoFill fields are applied before performing actions
		if (step.autoFill) {
			this.executeAutoFill(step.autoFill);
		}

		// Custom event (e.g. tutorialConnectNodes)
		if (step.nextEvent) {
			this.showActionProgress("Performing action…");
			window.dispatchEvent(
				new CustomEvent(step.nextEvent.event, {
					detail: step.nextEvent.detail ?? {},
				}),
			);
			setTimeout(() => {
				this.hideActionProgress();
				if (this.driverInstance?.isActive()) {
					this.advanceToNext();
				}
			}, 600);
			return;
		}

		// Click a button/element (e.g. "New Workflow", "Run", "Save").
		// Perform the click first, then wait for completionSelector if present.
		if (step.nextClickSelector) {
			this.showActionProgress("Waiting for action to complete…");
			const el = this.queryVisible<HTMLElement>(step.nextClickSelector);
			if (el) {
				el.click();
			}
			if (step.completionSelector) {
				// Wait for the completion element to appear before advancing
				this.waitForElement(step.completionSelector, 10000).then((found) => {
					this.hideActionProgress();
					if (found && this.driverInstance?.isActive()) {
						this.advanceToNext();
					}
				});
			} else {
				setTimeout(() => {
					this.hideActionProgress();
					if (this.driverInstance?.isActive()) {
						this.advanceToNext();
					}
				}, 400);
			}
			return;
		}

		// Block advancement if completionSelector is not yet satisfied
		// (steps without nextClickSelector that need to wait for a condition).
		if (step.completionSelector && !this.queryVisible(step.completionSelector)) {
			return;
		}

		// Default: just advance
		this.advanceToNext();
	}

	// ── Auto-fill ───────────────────────────────────────────────────

	private executeAutoFill(fields: Array<{ selector: string; value: string }>): void {
		for (const field of fields) {
			const el = this.queryVisible<HTMLElement>(field.selector);
			if (!el) continue;
			if (
				el instanceof HTMLInputElement ||
				el instanceof HTMLTextAreaElement
			) {
				this.setNativeInputValue(el, field.value);
			}
		}
	}

	private setNativeInputValue(
		el: HTMLInputElement | HTMLTextAreaElement,
		value: string,
	): void {
		const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
			Object.getPrototypeOf(el),
			"value",
		)?.set;
		if (nativeInputValueSetter) {
			nativeInputValueSetter.call(el, value);
			el.dispatchEvent(new Event("input", { bubbles: true }));
		} else {
			el.value = value;
			el.dispatchEvent(new Event("input", { bubbles: true }));
		}
	}

	/**
	 * Close something that was auto-opened by `autoClickSelector`.
	 * Re-clicks the trigger to toggle it closed (works for dropdowns,
	 * accordions, tabs that open panels, etc.).
	 */
	private closeAutoOpened(selector: string): void {
		const el = this.queryVisible<HTMLElement>(selector);
		if (!el) return;
		// For dropdown triggers, check aria-expanded to avoid toggling
		// something that is already closed (e.g. a tab button).
		if (el.getAttribute("aria-expanded") === "true") {
			el.click();
		}
	}

	// ── Step advancement ────────────────────────────────────────────

	private advanceToNext(): void {
		const idx = this.driverInstance?.getActiveIndex() ?? 0;
		const nextIdx = idx + 1;

		// Past the last step — explicitly destroy so the overlay is removed.
		if (nextIdx >= this.activeSteps.length) {
			this.driverInstance?.destroy();
			return;
		}

		const step = this.activeSteps[idx];

		// Block advancement if completionSelector is not yet satisfied.
		// The onPopoverRender wait handles re-showing the Next button.
		// Skip this check when the step also has a nextEvent — by the time
		// advanceToNext runs (after the event fires), a view transition may
		// have removed the completion element from the DOM.
		if (step?.completionSelector && !step.nextEvent && !this.queryVisible(step.completionSelector)) {
			return;
		}

		this.goToNextStep();
	}

	private goToNextStep(): void {
		const idx = this.driverInstance?.getActiveIndex() ?? 0;
		this.goToStepSkipping(idx + 1);
	}

	/**
	 * Navigate to the given step index, skipping any steps whose
	 * `skipIfNotFound` selector is not present in the DOM.
	 */
	private goToStepSkipping(targetIdx: number): void {
		if (targetIdx >= this.activeSteps.length) {
			this.driverInstance?.destroy();
			return;
		}

		const step = this.activeSteps[targetIdx];

		// Skip this step if its required element is absent.
		// Wait briefly (up to 5s) before deciding — the element may be
		// loading asynchronously (e.g. recommendations fetched via API).
		if (step?.skipIfNotFound && !this.queryVisible(step.skipIfNotFound)) {
			this.hideCurrentStepUI();
			this.waitForElement(step.skipIfNotFound, 5000).then((found) => {
				if (found) {
					// Element appeared — proceed with this step
					this.goToStep(targetIdx);
				} else {
					// Truly absent — skip
					this.goToStepSkipping(targetIdx + 1);
				}
			});
			return;
		}

		// If the next step's element isn't in the DOM yet, wait for it.
		if (step?.waitForElement && step.element && !this.queryVisible(step.element)) {
			// Hide the previous step's popover/pointer while we wait.
			this.hideCurrentStepUI();

			// When the step has an autoClickSelector, the auto-click is what
			// creates the target element (e.g. opening a settings panel).
			// Fire the click eagerly here so the element exists by the time
			// the step renders — avoids a jarring blank-then-repaint.
			if (step.autoClickSelector) {
				const clickEl = this.queryVisible<HTMLElement>(step.autoClickSelector);
				if (clickEl) {
					clickEl.click();
					this.earlyAutoClicked = targetIdx;
				}
			}
			// Use a generous timeout (15s) since view transitions (e.g. opening
			// run details) can take longer than the default 5s to render.
			this.waitForElement(step.element, 15000).then((found) => {
				if (found && this.driverInstance?.isActive()) {
					this.goToStep(targetIdx);
				}
			});
			return;
		}

		this.goToStep(targetIdx);
	}

	// ── Driver.js step building ─────────────────────────────────────

	private buildDriverSteps(steps: TutorialStep[]): DriveStep[] {
		return steps.map((step, index) => {
			return {
				// Pass the selector string so driver.js resolves it fresh
				// on each drive() call — no stale DOM references.
				element: step.element,
				popover: {
					title: step.popover.title,
					description: step.popover.description,
					side: step.popover.side,
					align: step.popover.align,
					onPopoverRender: (popover: {
						wrapper: HTMLElement;
						title: HTMLElement;
						description: HTMLElement;
					}) => {
						// Lock / unlock the config panel based on the step flag
						if (step.preventPanelClose) {
							document.body.dataset.tutorialLockPanel = "true";
						} else {
							delete document.body.dataset.tutorialLockPanel;
						}

						const placement = step.pointerPlacement ?? "bottom-center";
						const pointerSelector = step.pointerTarget ?? step.element;
						const isLastStep = index === this.activeSteps.length - 1;
						if (pointerSelector) {
							this.injectPointer(popover.wrapper, pointerSelector, index, placement);
						}
						this.injectCloseButton(popover.wrapper);
						this.makeDraggable(popover.wrapper);
						// Anchor the popover near the pointer, then fix overlap.
						// Fall back to the main element if the pointer target is not in the DOM.
						const anchorSelector = pointerSelector && this.queryVisible(pointerSelector)
							? pointerSelector
							: step.element;
						requestAnimationFrame(() => {
							if (anchorSelector) {
								this.anchorPopoverOnPointer(
									popover.wrapper,
									anchorSelector,
									placement,
								);
								this.resolvePointerPopoverOverlap(
									popover.wrapper,
									anchorSelector,
									placement,
								);
							}
						});
						// Hide the Next button until completionSelector is satisfied.
						// Skip hiding when the step has a nextClickSelector — the Next
						// button itself triggers the action that will satisfy the selector.
						if (step.completionSelector && !step.nextClickSelector) {
							const nextBtn = popover.wrapper.querySelector<HTMLButtonElement>(
								".driver-popover-next-btn",
							);
							if (nextBtn && !this.queryVisible(step.completionSelector)) {
								nextBtn.style.display = "none";
								this.waitForElement(step.completionSelector, 300000).then(() => {
									if (
										this.driverInstance?.isActive() &&
										this.driverInstance.getActiveIndex() === index
									) {
										nextBtn.style.display = "";
									}
								});
							}
						}

						// On the last step, inject a "Next Tutorial" button if configured
						if (isLastStep && this.nextTutorialId) {
							this.injectNextTutorialButton(
								popover.wrapper,
								this.nextTutorialId,
								this.nextTutorialLabel,
							);
						}
					},
				},
			};
		});
	}

	// ── UI injection helpers ────────────────────────────────────────

	private injectCloseButton(wrapper: HTMLElement): void {
		wrapper.querySelector(".as-tutorial-close-btn")?.remove();
		const btn = document.createElement("button");
		btn.type = "button";
		btn.className = "as-tutorial-close-btn";
		btn.setAttribute("aria-label", "Close tutorial");
		btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
		btn.addEventListener("click", (e) => {
			e.stopPropagation();
			this.driverInstance?.destroy();
		});
		wrapper.appendChild(btn);
	}

	private injectNextTutorialButton(
		wrapper: HTMLElement,
		nextId: string,
		nextLabel?: string | null,
	): void {
		const footer = wrapper.querySelector<HTMLElement>(".driver-popover-footer");
		if (!footer) return;

		// Change the existing done/next button to "Finish"
		const doneBtn = footer.querySelector<HTMLButtonElement>(
			".driver-popover-next-btn",
		);
		if (doneBtn) {
			doneBtn.textContent = "Finish";
		}

		// Create button with the next tutorial's title
		const nextBtn = document.createElement("button");
		nextBtn.type = "button";
		nextBtn.className = "as-tutorial-next-tutorial-btn";
		nextBtn.textContent = nextLabel ? `${nextLabel} \u2192` : "Next Tutorial \u2192";
		nextBtn.addEventListener("click", (e) => {
			e.stopPropagation();
			// Destroy first, then dispatch event to start the next tutorial
			this.driverInstance?.destroy();
			window.dispatchEvent(
				new CustomEvent("tutorialStartNext", { detail: { id: nextId } }),
			);
		});
		footer.appendChild(nextBtn);
	}

	// ── Drag support ────────────────────────────────────────────────

	/**
	 * Make the popover draggable by its title bar so the user can
	 * reposition it when it obscures content they want to see.
	 */
	private makeDraggable(wrapper: HTMLElement): void {
		this.cleanupDrag();

		const titleEl = wrapper.querySelector<HTMLElement>(".driver-popover-title");
		const handle = titleEl ?? wrapper;
		handle.classList.add("as-tutorial-drag-handle");

		let isDragging = false;
		let startX = 0;
		let startY = 0;
		let origLeft = 0;
		let origTop = 0;

		const onMouseDown = (e: MouseEvent) => {
			// Only left button, and ignore clicks on interactive children
			if (e.button !== 0) return;
			const tag = (e.target as HTMLElement).tagName;
			if (tag === "BUTTON" || tag === "A" || tag === "INPUT") return;

			isDragging = true;
			startX = e.clientX;
			startY = e.clientY;
			origLeft = wrapper.getBoundingClientRect().left;
			origTop = wrapper.getBoundingClientRect().top;
			wrapper.classList.add("as-tutorial-dragging");
			e.preventDefault();
		};

		const onMouseMove = (e: MouseEvent) => {
			if (!isDragging) return;
			const dx = e.clientX - startX;
			const dy = e.clientY - startY;
			const newLeft = Math.max(0, Math.min(origLeft + dx, window.innerWidth - wrapper.offsetWidth));
			const newTop = Math.max(0, Math.min(origTop + dy, window.innerHeight - wrapper.offsetHeight));
			wrapper.style.left = `${newLeft}px`;
			wrapper.style.top = `${newTop}px`;
		};

		const onMouseUp = () => {
			if (!isDragging) return;
			isDragging = false;
			wrapper.classList.remove("as-tutorial-dragging");
		};

		handle.addEventListener("mousedown", onMouseDown);
		document.addEventListener("mousemove", onMouseMove);
		document.addEventListener("mouseup", onMouseUp);

		this.dragCleanup = () => {
			handle.removeEventListener("mousedown", onMouseDown);
			document.removeEventListener("mousemove", onMouseMove);
			document.removeEventListener("mouseup", onMouseUp);
			handle.classList.remove("as-tutorial-drag-handle");
		};
	}

	private cleanupDrag(): void {
		if (this.dragCleanup) {
			this.dragCleanup();
			this.dragCleanup = null;
		}
	}

	// ── Pointer management ──────────────────────────────────────────

	private injectPointer(
		_popoverEl: HTMLElement,
		selector: string,
		stepIndex: number,
		placement: PointerPlacement,
	): void {
		this.removePointer();
		const pointer = document.createElement("div");
		pointer.className = "as-tutorial-pointer";
		pointer.style.position = "fixed";
		pointer.style.zIndex = "1000000001";
		pointer.style.pointerEvents = "none";
		pointer.innerHTML = POINTER_SVG;
		document.body.appendChild(pointer);
		this.pointerEl = pointer;
		this.activePointerSelector = selector;
		this.activeStepIndex = stepIndex;
		this.activePlacement = placement;
		this.positionPointer(selector);

		const onReposition = () => this.positionPointer(this.activePointerSelector!);
		window.addEventListener("scroll", onReposition, true);
		window.addEventListener("resize", onReposition);
		this.pointerTrackingCleanup = () => {
			window.removeEventListener("scroll", onReposition, true);
			window.removeEventListener("resize", onReposition);
		};
	}

	private positionPointer(selector: string): void {
		if (!this.pointerEl) return;
		const el = this.queryVisible(selector);
		if (!el) {
			this.pointerEl.style.display = "none";
			return;
		}
		const rect = el.getBoundingClientRect();
		const config = PLACEMENTS[this.activePlacement];
		const tip = config.getTip(rect);
		this.pointerEl.style.display = "";
		// Offset by 4px so the SVG tip (at ~4,4 in the viewBox) lands on the target point
		this.pointerEl.style.top = `${tip.y - 4}px`;
		this.pointerEl.style.left = `${tip.x - 4}px`;
		// Set rotation via custom property so the CSS bob animation includes it
		this.pointerEl.style.setProperty("--pointer-rotation", `${config.rotation}deg`);
	}

	/**
	 * Position the popover anchored to the pointer tip.
	 * The popover extends outward from the pointer on the side
	 * determined by the placement config.
	 */
	private anchorPopoverOnPointer(
		wrapper: HTMLElement,
		selector: string,
		placement: PointerPlacement,
	): void {
		const el = this.queryVisible(selector);
		if (!el) return;
		const rect = el.getBoundingClientRect();
		const config = PLACEMENTS[placement];
		const tip = config.getTip(rect);
		const popoverRect = wrapper.getBoundingClientRect();
		let top: number;
		let left: number;

		switch (config.popoverSide) {
			case "bottom":
				top = tip.y + POPOVER_GAP;
				left = tip.x - popoverRect.width / 2;
				break;
			case "top":
				top = tip.y - POPOVER_GAP - popoverRect.height;
				left = tip.x - popoverRect.width / 2;
				break;
			case "left":
				top = tip.y - popoverRect.height / 2;
				left = tip.x - POPOVER_GAP - popoverRect.width;
				break;
			case "right":
				top = tip.y - popoverRect.height / 2;
				left = tip.x + POPOVER_GAP;
				break;
		}

		// Clamp to viewport
		top = Math.max(8, Math.min(top, window.innerHeight - popoverRect.height - 8));
		left = Math.max(8, Math.min(left, window.innerWidth - popoverRect.width - 8));

		wrapper.style.top = `${top}px`;
		wrapper.style.left = `${left}px`;
		// Clear driver.js inline right/bottom/transform that can constrain the box
		wrapper.style.right = "unset";
		wrapper.style.bottom = "unset";
		wrapper.style.transform = "none";
	}

	/**
	 * If the pointer overlaps the popover after viewport-clamping,
	 * flip the pointer to the opposite side of the element.
	 */
	private resolvePointerPopoverOverlap(
		wrapper: HTMLElement,
		selector: string,
		placement: PointerPlacement,
	): void {
		if (!this.pointerEl) return;
		const popoverRect = wrapper.getBoundingClientRect();
		const pointerRect = this.pointerEl.getBoundingClientRect();

		const overlaps = !(
			pointerRect.right < popoverRect.left ||
			pointerRect.left > popoverRect.right ||
			pointerRect.bottom < popoverRect.top ||
			pointerRect.top > popoverRect.bottom
		);
		if (!overlaps) return;

		const flipped = this.flipPlacement(placement);
		this.activePlacement = flipped;
		this.positionPointer(selector);
	}

	private flipPlacement(p: PointerPlacement): PointerPlacement {
		const map: Record<PointerPlacement, PointerPlacement> = {
			"top-left": "bottom-left",
			"top-center": "bottom-center",
			"top-right": "bottom-right",
			"bottom-left": "top-left",
			"bottom-center": "top-center",
			"bottom-right": "top-right",
			"left-center": "right-center",
			"right-center": "left-center",
		};
		return map[p];
	}

	private removePointer(): void {
		if (this.pointerTrackingCleanup) {
			this.pointerTrackingCleanup();
			this.pointerTrackingCleanup = null;
		}
		if (this.pointerEl) {
			this.pointerEl.remove();
			this.pointerEl = null;
		}
		this.activePointerSelector = null;
	}

	// ── Cleanup & lifecycle ─────────────────────────────────────────

	private cleanupListeners(): void {
		for (const fn of this.cleanupFns) {
			fn();
		}
		this.cleanupFns = [];
		this.cleanupDrag();
		this.removePointer();
	}

	private removeEscHandler(): void {
		if (this.escHandler) {
			document.removeEventListener("keydown", this.escHandler);
			this.escHandler = null;
		}
	}

	private cancelPendingWait(): void {
		if (this.pendingWaitAbort) {
			this.pendingWaitAbort.abort();
			this.pendingWaitAbort = null;
		}
	}

	private waitForElement(
		selector: string,
		timeout = 5000,
	): Promise<Element | null> {
		this.cancelPendingWait();
		const abortController = new AbortController();
		this.pendingWaitAbort = abortController;

		return new Promise((resolve) => {
			const existing = this.queryVisible(selector);
			if (existing) {
				this.pendingWaitAbort = null;
				resolve(existing);
				return;
			}

			let resolved = false;

			const cleanup = () => {
				if (!resolved) {
					resolved = true;
					observer.disconnect();
					clearTimeout(timer);
					if (this.pendingWaitAbort === abortController) {
						this.pendingWaitAbort = null;
					}
				}
			};

			const observer = new MutationObserver(() => {
				const el = this.queryVisible(selector);
				if (el && !resolved) {
					cleanup();
					resolve(el);
				}
			});

			observer.observe(document.body, {
				childList: true,
				subtree: true,
				attributes: true,
				attributeFilter: ["data-tutorial", "data-tutorial-run-status", "style", "class"],
			});

			const timer = setTimeout(() => {
				if (!resolved) {
					cleanup();
					resolve(null);
				}
			}, timeout);

			abortController.signal.addEventListener(
				"abort",
				() => {
					if (!resolved) {
						cleanup();
						resolve(null);
					}
				},
				{ once: true },
			);
		});
	}
}
