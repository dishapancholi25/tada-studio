Now let me read the key evaluation components to understand the data architecture
and UI structure the tutorial will need to interact with.
Now let me look at the key remaining components — the runs tab, settings,
and the dataset editor modal.
Now let me look at the RunsListView (for the New Run modal) and the
RecommendationsSubTab, and check if there's a tutorial context/store.
Let me also check the backend for workflow template creation and any
tutorial-related APIs.
I now have enough context across the entire evaluations feature, the existing
portal/tooltip patterns, the API surface, and the modal z-index hierarchy
to write the full technical spec.

# Fix Evaluations Tutorial — Technical Architecture Specification

## Architecture Overview

The Evaluations tutorial is a **custom-built interactive guided tour** implemented entirely in the frontend.
No third-party library (react-joyride, shepherd, driver.js) is installed.
The system follows the existing React portal pattern established by `InfoTooltipPortal.tsx` and `EvalHelpButton.tsx`:
all overlay UI is injected into `document.body` via `createPortal` to escape stacking context constraints.

The tutorial consists of four collaborating layers:

```
┌──────────────────────────────────────────────────────┐
│  TutorialContext (React Context + useReducer)        │
│  — owns tutorial state, step index, demo data refs  │
├──────────────────────────────────────────────────────┤
│  TutorialOrchestrator (step-runner hook)             │
│  — drives automation, API calls, waitFor conditions  │
├──────────────────────────────────────────────────────┤
│  TutorialOverlay (portal — z-[9500])                 │
│  — semi-opaque backdrop + spotlight cutout           │
├──────────────────────────────────────────────────────┤
│  TutorialPopover (portal — z-[10000])                │
│  — guidance text, Next/Back, progress indicator      │
└──────────────────────────────────────────────────────┘
```

The evaluations tutorial lives in `frontend/src/app/evaluations/` alongside the feature it guides.
A shared `TutorialContext` in `frontend/src/contexts/TutorialContext.tsx` handles cross-tutorial concerns
(which tutorial is active, completion, "next tutorial" chaining).

---

## Technical Goals

- Render tutorial popovers above every product modal at every step (z-index correctness)
- Drive the evaluation lifecycle end-to-end through real API calls so all demo data is live
- Terminate cleanly: tutorial state is fully reset on completion and the product UI is fully interactive without a page reload
- Produce a prompt-type recommendation on every demo run by using a deliberately weak workflow prompt
- Support polling-based "wait for run completion" so the tutorial never advances on stale state

---

## Success Criteria

| Criterion | Acceptance Definition |
|-----------|----------------------|
| No popover is hidden by a modal | QA walkthrough: at every step where a modal is open, the popover `getBoundingClientRect()` is fully within the viewport and not covered by any element with `z-index < 10000` |
| Tutorial ends correctly | After the final Settings step, `TutorialContext.isRunning` becomes `false`, the overlay unmounts, and a `TutorialCompletionPopover` renders with "Finish" and "Next Tutorial" buttons |
| Demo workflow produces a prompt recommendation | Every demo run returns at least one recommendation where `recommendation_type === "prompt"` with a non-empty proposed system prompt |
| Re-run creates a second result set | `evalApi.createRun()` is called after recommendation apply; the tutorial polls `evalApi.getRun(runId)` until `status === "completed"` before advancing |
| A/B comparison shows deltas | `evalApi.compareRuns(firstRunId, secondRunId)` returns a `RunCompareResponse` with at least one non-null delta value; the Compare sub-tab renders this data |
| "New Dataset" is Step 3 | `EVAL_TUTORIAL_STEPS[2].id === "new-dataset"` and the step opens the create-dataset modal |
| Settings walkthrough covers both sub-tabs | Steps exist targeting the "General Defaults" and "Auto-Evaluation" tab buttons in `SettingsTab.tsx` |

---

## Scope Boundaries

**In scope:**

- `frontend/src/contexts/TutorialContext.tsx` — shared tutorial state
- `frontend/src/components/tutorial/TutorialOverlay.tsx` — spotlight backdrop
- `frontend/src/components/tutorial/TutorialPopover.tsx` — step guidance popover
- `frontend/src/components/tutorial/TutorialCompletionPopover.tsx` — end-state summary
- `frontend/src/app/evaluations/tutorial/evalTutorialSteps.ts` — step definitions
- `frontend/src/app/evaluations/tutorial/evalTutorialDemoData.ts` — demo data factory
- `frontend/src/app/evaluations/tutorial/useEvalTutorial.ts` — orchestration hook
- Modifications to `frontend/src/app/evaluations/page.tsx` to mount tutorial
- Backend: mutation of the hardcoded tutorial workflow definition (weak system prompt)

**Out of scope:**

- Tutorial launcher / tutorial list UI
- Other tutorials (Workflow Builder, Data Sources)
- Changes to the evaluation feature's own business logic or APIs
- The tutorial framework's ability to run on non-evaluations pages
- New backend APIs specifically for the tutorial

---

## Tech Stack & Libraries

No new libraries are added. The implementation uses existing stack:

| Concern | Approach |
|---------|----------|
| Overlay rendering | `ReactDOM.createPortal` to `document.body` — matches `EvalHelpButton.tsx` pattern |
| Spotlight geometry | `Element.getBoundingClientRect()` + CSS clip-path or box-shadow on the overlay |
| Step automation | Direct DOM clicks via `HTMLElement.click()` or React state lifting via context |
| Run completion polling | `setInterval` polling `evalApi.getRun()` with exponential backoff cap at 5s |
| Animation | Framer Motion `AnimatePresence` — already in `frontend/package.json` at `^12.23.6` |
| Tutorial step state | `useReducer` inside `TutorialContext` |

---

## Data Architecture

### Tutorial Demo Data

The tutorial creates ephemeral demo data on each run. It is tracked in `TutorialContext` so it can be referenced across steps and cleaned up.

```typescript
// frontend/src/contexts/TutorialContext.tsx

interface TutorialDemoData {
  workflowId: string | null;        // tutorial workflow created at step 1
  manualDatasetId: string | null;   // "Test Cases" dataset (manual tab demo)
  aiDatasetId: string | null;       // dataset used for AI generation demo
  firstRunId: string | null;        // initial evaluation run
  secondRunId: string | null;       // re-run after applying recommendations
  appliedRecommendationId: string | null;
}

interface TutorialState {
  isRunning: boolean;
  tutorialId: string | null;        // "evaluations" | "workflow-builder" | …
  currentStepIndex: number;
  demoData: TutorialDemoData;
  waitingForCompletion: boolean;    // true while polling run status
}
```

Demo data is created via `evalTutorialDemoData.ts`:

```typescript
// frontend/src/app/evaluations/tutorial/evalTutorialDemoData.ts

export async function createTutorialWorkflow(): Promise<string> {
  // POST /api/graph/create with TUTORIAL_WORKFLOW_DEFINITION
  // Returns workflow_id
}

export async function createTutorialDataset(workflowId: string): Promise<string> {
  // POST /api/evaluation/datasets
  // name: "Tutorial Test Cases", target_type: "workflow", target_id: workflowId
  // Returns dataset id
}

export async function addTutorialManualTestCase(datasetId: string): Promise<void> {
  // POST /api/evaluation/datasets/{id}/test-cases
  // { manual: [{ input_data: '{"query": "What is the capital of France?"}', expected_output: "Paris" }] }
}

export async function generateTutorialAiTestCases(datasetId: string): Promise<void> {
  // POST streaming: /api/evaluation/datasets/{id}/test-cases/generate-stream
  // body: { seed_prompt: "…", count: 3, include_edge_cases: true }
}

export async function createTutorialRun(
  datasetId: string,
  workflowId: string,
  name: string,
): Promise<string> {
  // POST /api/evaluation/runs
  // Returns run id
}
```

### Tutorial Workflow Definition

The tutorial creates a workflow with a deliberately weak, ambiguous system prompt to reliably trigger a `prompt` recommendation.

```typescript
// frontend/src/app/evaluations/tutorial/evalTutorialDemoData.ts

const TUTORIAL_WORKFLOW_DEFINITION = {
  name: "Evaluation Tutorial Demo",
  nodes: [
    { id: "start", type: "START", label: "Start", position: { x: 100, y: 200 } },
    {
      id: "agent-1",
      type: "AGENT",
      label: "Agent",
      position: { x: 350, y: 200 },
      data: {
        // Deliberately vague prompt — no domain context, no output format,
        // no constraints — designed to produce uncertain quality scores
        // and trigger a prompt-type recommendation from the evaluator.
        system_prompt: "Answer the question.",
        model_config: { provider: "anthropic", model: "claude-haiku-4-5-20251001" },
      },
    },
    { id: "end", type: "END", label: "End", position: { x: 600, y: 200 } },
  ],
  connections: [
    { source: "start", target: "agent-1" },
    { source: "agent-1", target: "end" },
  ],
};
```

**Why this prompt reliably generates a recommendation:** The quality judge evaluates output against judge criteria
(correctness, completeness, coherence, relevance). A prompt of `"Answer the question."` provides no domain framing,
no format specification, and no output constraints. Across a varied test case set this produces quality scores in the
40-65% range, which crosses the threshold the recommendation engine uses to propose prompt improvements.
The `proposed_change.agent_config.system_prompt` field is populated when `recommendation_type === "prompt"`.

---

## Z-Index Layering Fix

### Root Cause

Current modal z-index values in the codebase:

- Delete confirmation / Import preview dialogs in `DatasetsTab.tsx`: `z-[100]`
- New Run modal in `RunsListView.tsx`: `z-[100]` (inferred — same pattern)
- Settings modal/panel: `z-[100]` range
- `EvalHelpButton` panel: `z-[9999]`
- `InfoTooltipPortal`: `z-[9999]`

Tutorial popovers in the existing `feat/tutorial` branch appear to be rendered with insufficient z-index, causing them to be obscured when any modal is open.

### Fix

```typescript
// frontend/src/components/tutorial/TutorialPopover.tsx

// All tutorial UI is injected into document.body via createPortal
// and uses z-[10000] — above every modal (z-[100]) and help panel (z-[9999])

const popoverStyle = {
  position: "fixed" as const,
  zIndex: 10000,          // must exceed all modal z-values in the codebase
  // …positioning logic
};

const backdropStyle = {
  position: "fixed" as const,
  inset: 0,
  zIndex: 9500,           // above modals (100), below popover (10000)
  pointerEvents: "all" as const,
};
```

Both `TutorialOverlay` and `TutorialPopover` are rendered via `createPortal(…, document.body)`. This follows the exact pattern already used in `EvalHelpButton.tsx:166` and `InfoTooltipPortal.tsx:96`.

### Specific Affected Steps

Three steps highlighted in the stories where popovers were hidden:

1. **New Run modal — General settings popover**: The New Run modal is `z-[100]`; the tutorial popover pointing at it must be `z-[10000]`.
2. **New Run modal — Evaluations tab popover**: Same modal, different tab — same fix applies.
3. **Scoring configuration — covers settings**: Same z-index issue.

No product modal z-index values need to be changed. Only the tutorial's own popover z-index is raised.

---

## Tutorial Step Sequence

```typescript
// frontend/src/app/evaluations/tutorial/evalTutorialSteps.ts

export type TutorialStepId =
  | "welcome"
  | "datasets-overview"
  | "new-dataset"          // ← Step 3: restored
  | "dataset-editor-cases"
  | "manual-test-case"
  | "ai-generation"
  | "expand-example-dataset"
  | "import-executions-tab"
  | "export-import-tab"
  | "runs-tab"
  | "new-run-modal-general"
  | "new-run-name"         // ← run naming step
  | "new-run-modal-eval-tab"
  | "run-executing"
  | "run-results-overview"
  | "test-case-drill-through" // ← specific result drill
  | "recommendations"
  | "apply-recommendation"
  | "rerun-after-apply"    // ← actual re-run trigger
  | "rerun-executing"
  | "compare-tab"
  | "compare-select-runs"
  | "compare-results"
  | "settings-tab"
  | "settings-general"
  | "settings-auto-eval"
  | "completion";

export interface TutorialStep {
  id: TutorialStepId;
  title: string;
  content: string;
  targetSelector: string | null;   // null = centred modal, no spotlight
  placement: "top" | "bottom" | "left" | "right" | "center";
  nextLabel?: string;              // default "Next"
  backDisabled?: boolean;
  // Called before the step is shown — used for navigation/automation
  beforeShow?: (ctx: TutorialStepContext) => Promise<void>;
  // Called when "Next" is pressed — used for form fills or API calls
  onNext?: (ctx: TutorialStepContext) => Promise<void>;
  // If present, "Next" is disabled until this resolves
  waitFor?: (ctx: TutorialStepContext) => Promise<void>;
}

interface TutorialStepContext {
  demoData: TutorialDemoData;
  dispatch: Dispatch<TutorialAction>;
  // Imperative handles exposed by Evaluations page via context
  evalPage: EvalPageHandles;
}

interface EvalPageHandles {
  setActiveTab: (tab: TabId) => void;
  openNewRunModal: () => void;
  openNewDatasetModal: () => void;
  setRunId: (id: string) => void;
  setRunSubTab: (tab: RunSubTab) => void;
  setSettingsSubTab: (tab: "general" | "auto-eval") => void;
  openDatasetEditor: (datasetId: string) => void;
  setDatasetEditorTab: (tab: ModalTab) => void;
  expandDatasetRow: (datasetId: string) => void;
}
```

### Step Definitions (Key Steps)

```typescript
// Partial listing of the 27-step sequence

{
  id: "new-dataset",
  title: "Step 3 — Create a Dataset",
  content: "Datasets hold the test cases for your evaluations. Click 'New Dataset' to create one. Give it a name like 'Customer Support Tests' and choose 'Workflow' as the target type.",
  targetSelector: "button[data-tutorial='new-dataset-btn']",
  placement: "bottom",
  beforeShow: async (ctx) => {
    ctx.evalPage.setActiveTab("datasets");
  },
  onNext: async (ctx) => {
    ctx.evalPage.openNewDatasetModal();
    // Dataset is created inside the modal; demo dataset ID is captured
    // via an onDatasetCreated callback injected through EvalPageHandles
  },
},

{
  id: "new-run-name",
  title: "Name Your Run",
  content: "Give this run a descriptive name so you can identify it later when comparing results. We'll call it 'Tutorial Baseline Run'.",
  targetSelector: "input[data-tutorial='run-name-input']",
  placement: "bottom",
  onNext: async (ctx) => {
    const input = document.querySelector<HTMLInputElement>("input[data-tutorial='run-name-input']");
    if (input) {
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype, "value"
      )?.set;
      nativeInputValueSetter?.call(input, "Tutorial Baseline Run");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
  },
},

{
  id: "rerun-after-apply",
  title: "Re-Run the Evaluation",
  content: "Now let's run the evaluation again with the improved prompt to see if scores went up. This creates a second result set we can compare against the baseline.",
  targetSelector: "button[data-tutorial='rerun-btn']",
  placement: "bottom",
  onNext: async (ctx) => {
    const secondRunId = await evalApi.createRun({
      name: "Tutorial Rerun",
      dataset_id: ctx.demoData.manualDatasetId!,
      workflow_id: ctx.demoData.workflowId!,
      trigger: "manual",
    });
    ctx.dispatch({ type: "SET_SECOND_RUN_ID", payload: secondRunId.id });
  },
  waitFor: async (ctx) => {
    // Poll until secondRunId is completed
    await pollRunCompletion(ctx.demoData.secondRunId!);
  },
},

{
  id: "compare-select-runs",
  title: "Compare the Two Runs",
  content: "Select the 'Tutorial Baseline Run' as the comparison target. You'll see score deltas for each pillar — green means improvement, red means regression.",
  targetSelector: "[data-tutorial='compare-run-picker']",
  placement: "right",
  beforeShow: async (ctx) => {
    ctx.evalPage.setRunSubTab("compare");
    // Pre-select the first run as the peer in CompareSubTab
    // via an injected handle
    ctx.evalPage.selectComparePeer(ctx.demoData.firstRunId!);
  },
},

{
  id: "completion",
  title: "🎉 You've completed the Evaluations tutorial",
  content: "You've created datasets, run an evaluation, reviewed results, applied a recommendation, re-run for comparison, and configured auto-evaluation settings.",
  targetSelector: null,
  placement: "center",
  nextLabel: "Finish",
  backDisabled: true,
},
```

---

## Completion State Fix

### Root Cause

The tutorial overlay component does not unmount after the final step. The `isRunning` flag in `TutorialContext` remains `true` because the reducer's `COMPLETE_TUTORIAL` action is either never dispatched or does not clear the overlay component.

### Fix

```typescript
// frontend/src/contexts/TutorialContext.tsx

type TutorialAction =
  | { type: "START_TUTORIAL"; tutorialId: string }
  | { type: "NEXT_STEP" }
  | { type: "BACK_STEP" }
  | { type: "SET_DEMO_DATA"; payload: Partial<TutorialDemoData> }
  | { type: "SET_SECOND_RUN_ID"; payload: string }
  | { type: "COMPLETE_TUTORIAL" }   // ← must fully reset isRunning + currentStepIndex
  | { type: "SET_WAITING"; payload: boolean };

function tutorialReducer(state: TutorialState, action: TutorialAction): TutorialState {
  switch (action.type) {
    case "COMPLETE_TUTORIAL":
      return {
        ...INITIAL_STATE,      // ← reset to initial — isRunning: false
        // showCompletion flag triggers the completion popover independently of the overlay
        showCompletion: true,
        completedTutorialId: state.tutorialId,
      };
    // …
  }
}
```

The `TutorialCompletionPopover` is rendered independently of `TutorialOverlay` — it checks `state.showCompletion` rather than `state.isRunning`, so the backdrop and spotlight are gone but the completion summary remains visible:

```typescript
// frontend/src/components/tutorial/TutorialCompletionPopover.tsx

export function TutorialCompletionPopover({ onFinish, onNextTutorial, nextTutorialLabel }: Props) {
  return createPortal(
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="w-full max-w-md rounded-2xl border border-[rgba(var(--color-primary-rgb),0.3)] bg-gradient-to-br from-[rgba(30,30,30,0.98)] via-[rgba(22,22,22,0.97)] to-[rgba(16,16,16,0.98)] p-8 shadow-2xl"
      >
        <h2 className="text-xl font-semibold text-white mb-3">
          Tutorial Complete
        </h2>
        <p className="text-sm text-white/70 mb-6">
          You've finished the Evaluations tutorial. …
        </p>
        <div className="flex gap-3 justify-end">
          <button onClick={onFinish} type="button" className="…">
            Finish
          </button>
          {onNextTutorial && (
            <button onClick={onNextTutorial} type="button" className="…">
              {nextTutorialLabel ?? "Next Tutorial"} →
            </button>
          )}
        </div>
      </motion.div>
    </div>,
    document.body,
  );
}
```

When "Finish" is pressed, `dispatch({ type: "DISMISS_COMPLETION" })` resets `showCompletion` to `false` and the component unmounts. The user can interact with all Evaluations UI without a reload.

---

## API Integration

### Run Completion Polling

```typescript
// frontend/src/app/evaluations/tutorial/evalTutorialDemoData.ts

export async function pollRunCompletion(
  runId: string,
  timeoutMs = 300_000,  // 5-minute timeout
): Promise<void> {
  const start = Date.now();
  let interval = 2000;

  return new Promise((resolve, reject) => {
    const tick = async () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error("Evaluation run timed out"));
        return;
      }
      try {
        const run = await evalApi.getRun(runId);
        if (run.status === "completed" || run.status === "failed") {
          run.status === "completed" ? resolve() : reject(new Error("Run failed"));
          return;
        }
      } catch {
        // network hiccup — continue polling
      }
      interval = Math.min(interval * 1.5, 5000);
      setTimeout(tick, interval);
    };
    setTimeout(tick, interval);
  });
}
```

The `waitFor` handler on `rerun-executing` calls `pollRunCompletion`. While polling, the tutorial shows a loading
indicator in the popover ("Running evaluation...") via the `waitingForCompletion` state flag. The "Next" button is
replaced with a spinner. The popover itself remains visible and above all modals throughout.

### Recommendation Pre-condition

Before advancing to the `recommendations` step, the tutorial verifies that at least one `prompt`-type recommendation exists:

```typescript
// In the waitFor for step "recommendations":
waitFor: async (ctx) => {
  const recs = await evalApi.getRunRecommendations(ctx.demoData.firstRunId!);
  const promptRec = recs.find(
    (r) => r.recommendation_type === "prompt" && r.proposed_change?.agent_config?.system_prompt,
  );
  if (!promptRec) {
    throw new Error("No prompt recommendation generated — check demo workflow prompt");
  }
  ctx.dispatch({ type: "SET_DEMO_DATA", payload: { appliedRecommendationId: promptRec.id } });
},
```

If no prompt recommendation is found, the tutorial surfaces an error state rather than silently advancing to a broken step.

---

## EvalPageHandles — Imperative Page Interface

To allow the tutorial orchestrator to drive UI state (open modals, switch tabs, select items) without coupling
to component internals, the `EvaluationsPage` exposes an imperative handle via `useImperativeHandle` through a
ref registered in `TutorialContext`:

```typescript
// frontend/src/app/evaluations/page.tsx additions

const evalHandlesRef = useRef<EvalPageHandles>(null);

useImperativeHandle(evalHandlesRef, () => ({
  setActiveTab,
  openNewRunModal: () => setShowNewRunModal(true),
  openNewDatasetModal: () => setShowCreateModal(true),
  setRunId: (id) => setSelectedRunId(id),
  setRunSubTab: (tab) => setActiveRunSubTab(tab),
  setSettingsSubTab: (tab) => setSettingsSubTab(tab),
  openDatasetEditor: (id) => setEditingDatasetId(id),
  setDatasetEditorTab: (tab) => setDatasetModalTab(tab),
  selectComparePeer: (id) => setComparePeerId(id),
}), [/* deps */]);

// Register the handle with TutorialContext on mount
const { registerPageHandles } = useTutorial();
useEffect(() => {
  registerPageHandles("evaluations", evalHandlesRef);
}, [registerPageHandles]);
```

This requires promoting a small amount of state from child components (`RunsListView`, `RunDetailView`, `SettingsTab`)
up to `EvaluationsPage` — specifically: `showNewRunModal`, `selectedRunId`, `activeRunSubTab`, `settingsSubTab`,
`editingDatasetId`, `datasetModalTab`, and `comparePeerId`. These are already present as local state in the child
components; they need to become props or be hoisted.

---

## `data-tutorial` Attribute Convention

All tutorial target elements are identified by `data-tutorial` attributes (not CSS class names or test IDs, which may change). Add these attributes to the relevant elements in the evaluations components:

| Attribute | Element | Component |
|-----------|---------|-----------|
| `data-tutorial="new-dataset-btn"` | "New Dataset" button | `DatasetsTab.tsx:388` |
| `data-tutorial="datasets-tab"` | Datasets tab button | `evaluations/page.tsx` |
| `data-tutorial="runs-tab"` | Runs tab button | `evaluations/page.tsx` |
| `data-tutorial="settings-tab"` | Settings tab button | `evaluations/page.tsx` |
| `data-tutorial="new-run-btn"` | "+ New Run" button | `RunsListView.tsx` |
| `data-tutorial="run-name-input"` | Run name input field | `RunsListView.tsx` |
| `data-tutorial="new-run-general-tab"` | "General" tab in New Run modal | `RunsListView.tsx` |
| `data-tutorial="new-run-eval-tab"` | "Evaluations" tab in New Run modal | `RunsListView.tsx` |
| `data-tutorial="run-results-row"` | First result row in RunDetailsSubTab | `RunDetailsSubTab.tsx` |
| `data-tutorial="recommendations-tab"` | Recommendations sub-tab button | `RunDetailView.tsx` |
| `data-tutorial="compare-tab"` | Compare sub-tab button | `RunDetailView.tsx` |
| `data-tutorial="compare-run-picker"` | CompareRunPicker component | `CompareSubTab.tsx` |
| `data-tutorial="rerun-btn"` | Re-run button in RunDetailView | `RunDetailView.tsx` |
| `data-tutorial="settings-general-tab"` | "General Defaults" sub-tab button | `SettingsTab.tsx:46` |
| `data-tutorial="settings-auto-eval-tab"` | "Auto-Evaluation" sub-tab button | `SettingsTab.tsx:46` |
| `data-tutorial="dataset-modal-cases-tab"` | Cases tab in DatasetEditorModal | `DatasetEditorModal.tsx` |
| `data-tutorial="dataset-modal-manual-tab"` | Manual tab in DatasetEditorModal | `DatasetEditorModal.tsx` |
| `data-tutorial="dataset-modal-ai-tab"` | AI tab in DatasetEditorModal | `DatasetEditorModal.tsx` |
| `data-tutorial="dataset-modal-import-exec-tab"` | Import Executions tab | `DatasetEditorModal.tsx` |
| `data-tutorial="dataset-modal-export-import-tab"` | Export/Import tab | `DatasetEditorModal.tsx` |
| `data-tutorial="manual-input-field"` | Input field in Manual tab | `DatasetEditorModal.tsx` |
| `data-tutorial="ai-count-input"` | Count field in AI tab | `DatasetEditorModal.tsx` |
| `data-tutorial="ai-edge-cases-checkbox"` | Edge cases checkbox in AI tab | `DatasetEditorModal.tsx` |
| `data-tutorial="ai-generate-btn"` | Generate button in AI tab | `DatasetEditorModal.tsx` |
| `data-tutorial="apply-rec-btn"` | Apply button on prompt recommendation | `RecommendationsSubTab.tsx` |

---

## Phasing & Implementation Milestones

### Phase 1 — Bug Fixes (unblock QA, ~2 days)

1. **Z-index fix** (`TutorialPopover.tsx`, `TutorialOverlay.tsx`): Change popover z-index to `10000`,
   ensure both components use `createPortal(_, document.body)`. Verify against New Run modal (z-[100])
   and Settings panel.

2. **Tutorial end-state fix** (`TutorialContext.tsx`, `TutorialCompletionPopover.tsx`): Add
   `COMPLETE_TUTORIAL` reducer action that resets `isRunning` to `false`. Add `showCompletion` state flag.
   Render `TutorialCompletionPopover` independently of the overlay. Wire "Finish" to `DISMISS_COMPLETION`.

3. **Smoke-test all other tutorials**: Run through Workflow Builder and Data Sources tutorials to verify no regression from context changes.

### Phase 2 — Core Content (Step sequence, ~3 days)

4. **Restore "New Dataset" as Step 3**: Add `new-dataset` step to `EVAL_TUTORIAL_STEPS` at index 2.
   Add `data-tutorial="new-dataset-btn"` to `DatasetsTab.tsx`.
   Wire `beforeShow` to call `evalPage.setActiveTab("datasets")`.

5. **Run naming step**: Add `new-run-name` step. Add `data-tutorial="run-name-input"` to the run name
   input in `RunsListView.tsx`. Implement `onNext` automation to pre-fill "Tutorial Baseline Run"
   using the native input setter pattern.

6. **Template workflow weak prompt**: Update `TUTORIAL_WORKFLOW_DEFINITION` in `evalTutorialDemoData.ts`.
   Change `system_prompt` from the current value to `"Answer the question."` or equivalent.
   Verify by running `evalApi.getRunRecommendations` on a test run and confirming
   `recommendation_type === "prompt"` is returned.

### Phase 3 — Expanded Demo (~3 days)

7. **Manual test case demo**: Add `manual-test-case` step targeting `data-tutorial="manual-input-field"`.
   `onNext` handler fills the input with a sample JSON payload using the native input setter,
   then calls `evalApi.addTestCases`.

8. **AI dataset generation demo (3 datasets, edge cases)**: Add `ai-generation` step targeting the AI tab.
   `onNext` sets count to 3, checks the edge-cases checkbox, and calls `evalApi.generateTestCasesStream`.
   A loading message in the popover narrates the streaming progress via the `onProgress` callback.
   On `done` event, dispatch `SET_DEMO_DATA` with the generated dataset ID.

9. **Expand example dataset**: Add `expand-example-dataset` step. After the AI generation step, `beforeShow` calls `evalPage.expandDatasetRow(demoData.aiDatasetId)`. The spotlight targets the expanded row.

10. **Import Executions tab explainer**: Add step targeting `data-tutorial="dataset-modal-import-exec-tab"`. `beforeShow` switches to the Import Executions tab.

11. **Export/Import tab explainer**: Add step targeting `data-tutorial="dataset-modal-export-import-tab"`. `beforeShow` switches to the Export/Import tab.

12. **Test case drill-through**: Add `test-case-drill-through` step. `beforeShow` calls
    `evalPage.setActiveTab("runs")` + `evalPage.setRunId(demoData.firstRunId)`.
    Then programmatically clicks the first result row (`data-tutorial="run-results-row"`).
    Subsequent steps walk through `ResultDetailPanel` sections.

### Phase 4 — Lifecycle Completion (~2 days)

13. **Re-run trigger**: Add `rerun-after-apply` step. `onNext` calls `evalApi.createRun` with the same
    dataset/workflow, dispatches `SET_SECOND_RUN_ID`. `waitFor` calls `pollRunCompletion`.
    Popover shows a spinner while polling.

14. **A/B comparison walkthrough**: Add `compare-select-runs`, `compare-results` steps. `beforeShow` on
    `compare-select-runs` calls `evalPage.selectComparePeer(demoData.firstRunId)` and
    `evalPage.setRunSubTab("compare")`. `onNext` calls `evalApi.compareRuns(secondRunId, firstRunId)`
    and dispatches comparison result for use in popover copy.

15. **Settings walkthrough**: Add `settings-general`, `settings-auto-eval` steps. `beforeShow` on
    `settings-general` calls `evalPage.setActiveTab("settings")` + `evalPage.setSettingsSubTab("general")`.
    `beforeShow` on `settings-auto-eval` calls `evalPage.setSettingsSubTab("auto-eval")`.

16. **Completion popover**: Add `completion` step with `targetSelector: null` and `placement: "center"`.
    `onNext` dispatches `COMPLETE_TUTORIAL`. Renders `TutorialCompletionPopover` with "Finish" and
    "Next Tutorial" buttons.

---

## Observability & Monitoring

No server-side observability changes are required. Frontend-side:

- Tutorial errors (run polling timeout, missing recommendation, API failure) are caught in `useEvalTutorial.ts`
  and dispatched as `{ type: "TUTORIAL_ERROR", message }`, which renders an error state in the popover with
  a "Restart" option and logs to `console.error`.
- Tutorial completion is logged via a browser `CustomEvent` (`tutorial:complete`) for any future analytics instrumentation.

---

## Testing Strategy

### Unit Tests

`frontend/src/app/evaluations/tutorial/evalTutorialDemoData.test.ts`:

- Mock `evalApi` and verify `createTutorialWorkflow` posts the correct graph definition
- Verify `pollRunCompletion` resolves on `status === "completed"` and rejects on timeout

`frontend/src/contexts/TutorialContext.test.ts`:

- `COMPLETE_TUTORIAL` action sets `isRunning: false`, `showCompletion: true`
- `DISMISS_COMPLETION` sets `showCompletion: false`
- Step index increments/decrements correctly; does not go below 0 or above steps length

### Integration Tests

`frontend/src/app/evaluations/tutorial/evalTutorialSteps.test.ts`:

- `EVAL_TUTORIAL_STEPS[2].id === "new-dataset"` — verifies step 3 is present and in position
- `EVAL_TUTORIAL_STEPS` contains a step with `id === "rerun-after-apply"` and a non-null `waitFor`
- `EVAL_TUTORIAL_STEPS` contains a step with `id === "completion"` and `targetSelector === null`

### QA Walkthrough Checklist

All of the following must pass in a full end-to-end walkthrough before the feature is merged:

1. Start the Evaluations tutorial from the launcher. Confirm Step 1 popover is visible.
2. Progress to Step 3. Confirm "New Dataset" step appears and opens the modal.
3. Open the New Run modal. Confirm the tutorial popover is fully visible above the modal.
4. Enter a run name. Confirm the run name field accepts input.
5. Execute the run. Confirm the tutorial shows a loading state while polling.
6. After run completes, navigate to Recommendations. Confirm at least one prompt recommendation is visible.
7. Apply the recommendation. Confirm the diff review modal opens with a proposed prompt change.
8. Confirm re-run is triggered and a second run appears in the Runs list.
9. Navigate to Compare. Confirm both runs are selectable and delta scores are shown.
10. Navigate to Settings → General Defaults tab. Confirm tutorial popover is visible.
11. Switch to Auto-Evaluation tab. Confirm tutorial popover is visible.
12. Press "Next" on final step. Confirm completion popover appears with "Finish" and "Next Tutorial" buttons.
13. Press "Finish". Confirm overlay and completion popover unmount. Confirm Evaluations UI is fully interactive.
14. Run the Workflow Builder tutorial. Confirm it completes normally (regression test).

---

## Deployment & Rollout

All changes are isolated to the `feat/tutorial` branch and limited to the frontend. No database migrations, no new API routes, no environment variable changes are required.

The tutorial creates demo data (a workflow, datasets, runs) in the user's account during the walkthrough.
This data persists after tutorial completion. A future "clean up demo data" option can be added to the
completion popover but is not in scope for this initiative.

The tutorial is user-initiated via the existing tutorial launcher. No feature flag or phased rollout is needed — the launcher already gates access and no production behaviour of the Evaluations feature changes.

---

## Dependencies & Risks

| Item | Risk | Likelihood | Mitigation |
|------|------|-----------|-----------|
| Demo workflow must produce a `prompt` recommendation on every run | High — if not, Steps 16-18 are broken | Medium — depends on evaluator model scoring | Use a weak prompt with a varied 3-test-case dataset; validate in dev before merge |
| State hoisting in `EvaluationsPage` may surface hidden bugs | Medium — lifting state from children | Low — state is already well-isolated | Keep a single EvalPageHandles ref; minimise surface area |
| `pollRunCompletion` may appear stalled on slow evaluation runs | Low UX risk — tutorial looks frozen | Medium | Show a live elapsed-time counter; add 5-minute hard timeout with error state |
| Changes to `TutorialContext` may regress other working tutorials | Medium | Low | All `TutorialAction` types are discriminated. Smoke-test other tutorials before merge. |
| `EvalPageHandles.selectComparePeer` needs state in `RunDetailView` or higher | Low — small refactor | Low | Add optional `initialPeerRunId` prop and a `ref`-forwarded `setPeerRunId` method |

---

## Open Questions

| Question | Impact if Unresolved | Owner |
|----------|---------------------|-------|
| Should Step 3 create the dataset automatically via API, or spotlight the modal and wait for user submission? | Affects whether step is observational or interactive; affects `onNext` handler implementation | PO |
| Should the tutorial advance to `rerun-executing` and block on `waitFor`, or show inline loading in the popover? | Determines whether a dedicated `rerun-executing` step exists or the existing step handles both | PO |
| Is the Settings walkthrough observational or interactive (user configures values before advancing)? | If interactive, `onNext` handlers must validate form state; if observational, no validation needed | PO |
