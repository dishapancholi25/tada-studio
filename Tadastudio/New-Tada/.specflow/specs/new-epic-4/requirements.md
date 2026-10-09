The `feat/tutorial` branch isn't available in this environment, so let me explore the current
codebase for all tutorial and evaluation-related features to build an accurate product picture.
Now I have all the context I need. Let me write the specification.

# Fix Evaluations Tutorial — Initiative Specification

## Problem Space & Opportunity

The Evaluations module is one of the most powerful — and most complex — areas of Agentic Studio.
It gives users a structured, repeatable way to test their workflows, score results across four
quality dimensions, and act on AI-generated improvement recommendations. Despite this depth,
the Evaluations guided tutorial is currently incomplete and in places broken, leaving users without
reliable in-product guidance at the moment they need it most.

Three categories of issues exist today:

1. **Functional bugs** that actively block users: tutorial popovers and tooltips are hidden behind
   open modals, and the tutorial never terminates — its overlay persists after the final Settings
   step, trapping users in a non-interactive state with no way to exit cleanly.
2. **Missing or removed content**: the "New Dataset" creation step was accidentally dropped, and
   there is no demo of filling in a manual test case, no drill-through of individual test case
   results, and no guided walk of the Settings screen.
3. **A shallow demo experience**: the template workflow used during the tutorial does not reliably
   produce prompt recommendations, the A/B comparison step does not actually perform a comparison,
   the re-run after applying recommendations is described but never triggered, and the AI dataset
   generation step lacks enough guidance to be instructive.

Together, these gaps mean users who rely on the tutorial leave it without understanding how to
create datasets, run evaluations, interpret results, apply recommendations, or configure
auto-evaluation — the core loop the product is built around.

---

## Strategic Goals

- Deliver a complete, trustworthy end-to-end guided tour of the Evaluations module that a new
  user can follow without confusion or dead-ends.
- Ensure the tutorial reliably demonstrates every major capability: dataset creation (manual and
  AI-generated), running an evaluation, inspecting per-case results, applying recommendations,
  re-running for comparison, and configuring evaluation settings.
- Fix all blocking bugs so the tutorial finishes cleanly and users return to a fully interactive
  product state.
- Raise user confidence in the Evaluations feature by showing real, live actions in the product
  rather than static descriptions.

---

## Success Criteria

| Criterion | Measure |
|-----------|---------|
| Tutorial completes without errors | Every step progresses in sequence; no step gets stuck, hidden, or unresponsive during QA walkthrough |
| All tutorial popovers are visible | No tooltip or guidance panel is obscured by a modal or settings overlay at any point in the tutorial |
| Tutorial ends correctly | After the final Settings step, a completion summary popover appears with a "Finish" button and an option to proceed to the next tutorial |
| Prompt recommendation is generated | The demo workflow produces at least one prompt-type recommendation visible in the Recommendations tab during the tutorial |
| Re-run creates a second result set | After recommendations are applied, the tutorial triggers a real re-run that produces a completed second set of results |
| A/B comparison shows real data | The Compare step uses the two demo runs and displays scored pillar deltas between them |
| Manual test case demo works | The tutorial walks through filling in a new test case in the manual entry form |
| Individual test case drill-through works | The tutorial navigates to and explains the detail view for a specific test case result |
| AI dataset generation demo works | The tutorial generates 3 datasets with edge cases checked and narrates the process |
| Settings walkthrough is complete | The tutorial opens Settings and steps through both the General Defaults and Auto-Evaluation sub-tabs |
| New Dataset step is present | "New Dataset" creation appears as Step 3 of the tutorial sequence |
| Dataset modal tabs are covered | Import Executions and Export/Import tabs each have explanatory copy in the tutorial |
| Run is named before execution | The tutorial instructs the user to enter a run name in the New Run form before starting |

All criteria must pass a full QA walkthrough before the feature is considered complete.

---

## Scope Boundaries

**In scope:**

- All 12 stories listed in the attached epic: layering/z-index bug fix, tutorial end-state bug
  fix, template workflow update, run naming, manual test case demo, AI dataset generation demo,
  showing an expanded example dataset, dataset modal tab explainers, restoring the "New Dataset"
  step, demo of specific test case results, A/B comparison walkthrough, re-run after
  recommendations, Settings walkthrough
- The Evaluations tutorial only — no changes to other tutorials in the system

**Out of scope:**

- Creating a new tutorial from scratch or changing the tutorial launcher/entry point
- Changes to the Evaluations feature itself (datasets, runs, settings) beyond what is needed
  to support the tutorial demo
- Changes to the tutorial framework's core rendering engine beyond fixing the z-index
  layering issue
- Changes to other tutorials (e.g. Workflow Builder, Data Sources)
- No new tutorial recordings, video walkthroughs, or help documentation — only the interactive
  guided tour

---

## Key User Roles & High-Level Journeys

**Primary user: New or early-stage Agentic Studio user exploring Evaluations**

This user has built or imported a workflow and wants to understand how to test it systematically.
They access the tutorial from the product's tutorial launcher, select the Evaluations tutorial,
and expect to be guided through the full evaluation cycle — creating test data, running an
evaluation, understanding the results, improving the workflow, and setting up automation —
without needing prior knowledge.

**Journey changes with this initiative:**

| Stage | Current state | Target state |
|-------|---------------|--------------|
| Entering the tutorial | Tutorial launches and begins stepping through Evaluations | No change — entry point is already working |
| Dataset creation | "New Dataset" step is missing from the sequence | Step 3 explicitly creates a new dataset |
| Manual test case | Not demonstrated | Tutorial fills in the manual test case form live |
| AI dataset generation | Briefly mentioned, no guidance | Tutorial generates 3 datasets with edge cases, narrates the options |
| Viewing datasets | No dataset is expanded to show contents | Tutorial expands one example dataset after the "Test Cases" dataset |
| Dataset modal tabs | Import Executions and Export/Import tabs not explained | Tutorial includes explanatory steps for each tab |
| Starting a run | Run name field is skipped | Tutorial prompts user to name the run before proceeding |
| Viewing results | Overall scores shown, no drill-through | Tutorial navigates into a specific test case and walks through the results detail screen |
| Applying recommendations | Recommendations tab exists but may not have content | Tutorial produces at least one prompt-edit recommendation and walks through it |
| Re-running after changes | Re-run described but not triggered | Tutorial triggers the actual re-run and waits for it to complete |
| A/B comparison | Compare tab is opened but not configured | Tutorial selects both demo runs and walks through comparison with scored deltas |
| Settings | Settings tab is opened but not navigated | Tutorial opens Settings, steps through General Defaults tab, then Auto-Evaluation tab |
| Tutorial end | Overlay persists, UI is blocked | Completion popover appears with "Finish" and "Next Tutorial" options; overlay clears |
| Tooltip visibility | Popovers hidden behind open modals | All tutorial tooltips appear above every modal in every step |

---

## Phasing & Milestones

Given the interdependence of several stories (the re-run story depends on the re-run having
recommendation content to apply; the A/B comparison story depends on the re-run completing),
the following delivery order is recommended:

**Phase 1 — Fix blocking bugs (deliver first for unblocked QA)**

- Fix tooltip/popover layering so guidance panels always appear above modals
- Fix tutorial end state so the completion summary popover fires and the overlay clears

**Phase 2 — Fix and restore core demo content**

- Update the demo template workflow to produce a prompt recommendation
- Restore the "New Dataset" step as Step 3
- Add run naming to the New Run step

**Phase 3 — Expand the guided demo experience**

- Demo the manual test case form
- Demo AI dataset generation (3 datasets, edge cases checked)
- Show an expanded example dataset in the dataset modal
- Add Import Executions and Export/Import tab explainers to the dataset modal
- Demo specific test case results drill-through

**Phase 4 — Complete the evaluation lifecycle demo**

- Demo re-run after applying recommendations (actual trigger, waits for completion)
- Configure and walk through A/B comparison between the two demo runs
- Walk through Settings (General Defaults and Auto-Evaluation tabs)

All four phases should be delivered and QA-verified before release.

---

## Dependencies & Risks

| Item | Type | Notes |
|------|------|-------|
| Demo template workflow must produce a prompt recommendation | Internal dependency | Phase 3-4 depends on this. If not done in Phase 2, downstream steps fail during QA. |
| Two demo runs must be created before A/B comparison step | Sequencing dependency | Comparison depends on re-run completing first. These stories must be tested together. |
| Tutorial framework must render tooltips above all modal layers | Technical prerequisite | Must be resolved in Phase 1 before modal-related steps can be QA'd. |
| Tutorial end-state fix must not regress other tutorials | Risk: medium | Completion state changes could affect other tutorials. Smoke-test all after this fix. |

---

## Assumptions

| Assumption | Validated? |
|-----------|-----------|
| The tutorial framework supports a completion summary popover with "Finish" and "Next Tutorial" actions | Validated — confirmed by user |
| The tutorial creates all demo datasets and demo runs from scratch at runtime | Validated — confirmed by user |
| The tutorial is triggered from an existing tutorial launcher accessible to all users | Validated — confirmed by user |
| Internal QA review is the acceptance gate — no external beta or feature-flag rollout is planned | Validated — confirmed by user |
| All changes are isolated to the `feat/tutorial` branch and do not affect production behaviour | Unvalidated — confirm before merge |

---

## Non-Functional Requirements

**Overlay and layering:** Tutorial tooltips and guidance popovers must render above all modals,
dialogs, and settings panels at every step of the tutorial. There must be no step where a
guidance element is partially or fully hidden behind product UI.

**Tutorial state:** When the user reaches the final step and the completion popover is dismissed,
the tutorial overlay must be fully removed. The user must be able to interact with all Evaluations
UI normally without a page reload.

**Demo reliability:** The template workflow used in the tutorial must generate a prompt-type
recommendation on every run, not occasionally. If the recommendation is not generated, the
tutorial cannot proceed to the apply-and-rerun steps. The template should be designed with a
weak or unclear prompt that reliably produces uncertain results so the recommendation engine
flags it.

---

## Migration & Rollout

This initiative changes the behaviour and content of an existing tutorial. Users who have
previously completed the Evaluations tutorial will not be re-prompted automatically — the
tutorial is user-initiated. No migration is required. Users who have the tutorial in progress
(mid-session) will experience a reset if the tutorial step sequence changes, which is an
acceptable trade-off given the bug severity.

---

## Open Questions

| Question | Owner | Impact if unresolved |
|----------|-------|----------------------|
| Should the "New Dataset" step (Step 3) create the dataset automatically, or prompt the user to fill in the form? | PO | Affects step scope and whether it is active or observational |
| After the re-run is triggered, should the tutorial wait with a loading indicator, or advance immediately and return once complete? | PO | Affects tutorial flow design; long evaluations could make the tutorial appear stalled |
| Is the Settings walkthrough observational (explaining settings) or interactive (asking the user to configure values)? | PO | Determines the depth of the Settings walkthrough steps |
