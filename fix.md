# Bug 7705 — Issues & Fixes

**Ticket:** [Altair] [Tada] Components remain Queued and outputs are unavailable after workflow completion

**Status:** Issues 1-4 below are grounded in things we actually saw happen — either in our own local test runs, in the original ticket's screenshots, or in Abid's real-environment run. Anything that was only a theory from reading code, never confirmed by an actual execution, has been removed from this file (previously Issues 5 and 6) — those need to be re-investigated with real evidence before being trusted.

---

## ISSUE 1: Nodes that never executed are labeled "Queued" instead of "Not executed"

*(Confirmed by: our own local test runs, and the original ticket's screenshots)*

### Problem
When a node never ran (its branch wasn't taken), the UI shows the word **"Queued"** — implying it's waiting to run, when actually it simply never ran and never will in that execution.

### Root Cause
The status label is decided by a lookup table that has a `default` fallback labeled "Queued". Any node with no execution record falls into that default.

### File & Line
`frontend/src/components/panels/execution/components/ExecutionModalHeader.tsx`

- **Lines 47-52** — the `default` entry in `STATUS_CONFIG`, labeled "Queued"
- **Line 62** — `const statusKey = nodeExecution?.status ?? "default";`

### Fix

**Change A — add a new entry to `STATUS_CONFIG` (insert above the existing `default` entry, around line 47):**

```ts
	not_executed: {
		label: "Not executed",
		Icon: Clock,
		iconClass: "text-slate-400",
		pillClass: "border-gray-200 bg-white text-slate-500",
	},
	default: {
		label: "Queued",
		Icon: Clock,
		iconClass: "text-slate-600",
		pillClass: "border-gray-200 bg-white text-slate-800",
	},
```

**Change B — line 62, replace:**
```ts
	const statusKey = nodeExecution?.status ?? "default";
```
**with:**
```ts
	const statusKey = nodeExecution ? nodeExecution.status : "not_executed";
```

### Why two separate changes
Change A adds the new label. Change B makes sure it's only used when there is truly **no record** (`nodeExecution` missing) — not for other real in-flight statuses like `pending` that come through during a live run and should keep their own label.

---

## ISSUE 2: Clicking a never-executed node shows a scary red error instead of a neutral message

*(Confirmed by: the original ticket's screenshots — this is the exact error text Ghazanfar and Lakshay both quoted)*

### Problem
Clicking a node with no data shows:
```
Unable to load node execution data
Node execution not found
```
styled as a hard error (red box, alert icon).

### Root Cause
The panel always calls the backend API for node execution data (because the caller never passes `nodeExecution` as a prop). The backend correctly returns 404 for a node with no record. The panel treats **every** API failure — including this expected 404 — as a hard error.

### Files & Lines

**`frontend/src/components/core/shared/usePropertyPanels.tsx`**
- **Lines 1016-1023** — `<NodeExecutionPanel ... />` is rendered without a `nodeExecution` prop, only `allNodeExecutions` (which is empty for a node that never ran)

**`frontend/src/components/panels/execution/NodeExecutionPanel.tsx`**
- **Lines 68-91** — the `useEffect` that calls `api.getNodeExecution(...)` whenever `nodeExecution` is falsy, and sets `error` in the `.catch`
- **Lines 129-136** — the red error box rendered whenever `error` is set

**`frontend/src/lib/api.ts`**
- **Line 671-675** — `getNodeExecution()`, the function making the call. Check how `fetchJson` surfaces a 404 (status code vs. message string) before writing the check in Change B below — this wasn't verified in the conversation, look here first.

**Backend reference (do not change, just for confirmation):**
`backend/api/execution_history/routes.py` line 361 — `raise HTTPException(status_code=404, detail="Node execution not found")`

### Fix

**Change A — `NodeExecutionPanel.tsx`, inside the `.catch` block (around line 78-84):**

Currently:
```ts
				.catch((err) => {
					console.error(
						"[NodeExecutionPanel] Failed to fetch node execution data:",
						err,
					);
					setError(err.message || "Failed to load node execution data");
				})
```

Change to distinguish a 404 ("this node never ran") from a real failure:
```ts
				.catch((err) => {
					const status = err?.status ?? err?.response?.status;
					if (status === 404) {
						setNotExecuted(true);
					} else {
						console.error(
							"[NodeExecutionPanel] Failed to fetch node execution data:",
							err,
						);
						setError(err.message || "Failed to load node execution data");
					}
				})
```
(exact property name for the status code — `err.status` vs `err.response.status` vs something else — depends on what `fetchJson` in `api.ts` actually throws; confirm this first)

**Change B — add new state (near line 36, alongside the other `useState` calls):**
```ts
	const [notExecuted, setNotExecuted] = useState(false);
```

**Change C — render branch (around line 129-136), add a new case before the existing `error` case:**
```tsx
							) : notExecuted ? (
								<div className="flex flex-col items-center gap-3 rounded-2xl border border-gray-200 bg-white px-6 py-10 text-center shadow-sm">
									<Clock className="h-10 w-10 text-slate-400" />
									<p className="text-sm font-semibold text-gray-900">
										This node did not run in this execution
									</p>
									<p className="text-xs text-gray-500">
										Its branch was not taken on this path.
									</p>
								</div>
							) : error ? (
```
(keep the existing `error` block unchanged after this, for real failures)

---

## ISSUE 3: "End 1" can never get an execution record, even on paths that reach it (real backend bug)

*(Confirmed by: querying our own local execution database after real local runs — "End 1" had zero rows across every execution, while "End" had several)*

### Problem
This workflow has two END nodes: "End" and "End 1". Only "End" ever gets a database row — "End 1" gets **zero rows**, confirmed by direct query on our local execution history, even on paths structurally meant to route through it.

### Root Cause — deeper than it first looked

There are actually **two layers** to this bug, confirmed by reading the code:

**Layer 1 — the specific End node is erased at graph-build time, before execution even runs.**

`backend/services/graph/edge_builder.py`:
- **Line 141 & 363:** `end_node_ids = {n.uniq_id for n in self.end_nodes}` — collects ALL End-type node IDs (both "End" and "End 1") into one set
- **Lines 153-154** (FOR_EACH exits) and **lines 376-377** (condition routing):
  ```python
  if c.target_id in end_node_ids:
      targets[routing_key] = END   # LangGraph's generic termination signal
  ```
  Whenever any connection points to **either** End node, it gets replaced with LangGraph's single generic `END` sentinel. The distinction between "this was headed to End" vs "this was headed to End 1" is **destroyed here**, before the workflow ever runs.

**Layer 2 — the recording code then blindly picks the first End node, with no way to know better.**

`backend/services/execution/workflow_executor.py`:
- **Line 2258:** `all_end_nodes = [n for n in graph.nodes if n.type == NodeType.END]`
- **Line 2280:** `end_node = end_nodes[0]` ← always takes the first one ("End", since it's stored before "End 1")

`backend/services/execution/resume_handler.py`:
- **Line 1055:** `end_nodes = [n for n in graph.nodes if n.type == NodeType.END]`
- **Line 1059:** `end_node = end_nodes[0]` ← same bug, resume path

### Fix — confirmed working, verified in code

Since Layer 1 erases the info inside LangGraph's own execution, we can't recover it from there. Instead we reconstruct it a different way: find the **last real node that ran** before the workflow finished, then check **that node's own connections** to see which End node it was actually heading toward.

**Proof this works, traced step by step:**

1. `backend/services/nodes/factory.py`, `_initialize_state_updates` (lines 205-216) — this runs for **every node type**, and does:
   ```python
   return {"current_node": node.uniq_id, ...}
   ```
   Every node records its own ID as "I am the one running right now" when it starts.

2. `workflow_executor.py`, lines 1159-1166 — `current_node` gets merged into `final_state` on every node update, always overwritten with the newest value:
   ```python
   for key in ["messages", "current_node", "metadata", "execution_order"]:
       if key in node_updates:
           final_state[key] = node_updates[key]
   ```

3. **Result:** by the time `_process_end_node` runs, `final_state["current_node"]` holds the ID of the last real node that ran (e.g. "Mark-Processed Agent" or "Re-Run") — exactly what we need.

**The actual fix — apply in both files (`workflow_executor.py` line 2280 and `resume_handler.py` line 1059):**

```python
# Instead of: end_node = end_nodes[0]
last_node_id = final_state.get("current_node") if final_state else None
last_node = next((n for n in graph.nodes if n.uniq_id == last_node_id), None)
target_end_id = last_node.nexts[0] if last_node and last_node.nexts else None

end_node = next(
    (n for n in end_nodes if n.uniq_id == target_end_id),
    end_nodes[0],  # fallback only if we genuinely can't determine it
)
```

⚠️ **Still worth double-checking before applying:** whether `last_node.nexts` can ever contain more than one target where the first entry (`nexts[0]`) isn't reliably "the End node." May need to loop through `last_node.nexts` and find the one that's actually in the End node ID set, instead of blindly taking index 0.

---

## ISSUE 4: The "Is Verified" condition can be fooled by a missing field

*(Confirmed by: real data from one of our own local runs — see below)*

**⏸️ PAUSED — not currently being worked on**, not because it's unverified (it is, from a real run), but because it wasn't reported by anyone in the ticket, unlike Issues 1-3.

### Problem
"Customer Data Extraction Agent" sits on the "false" branch of the "Is Verified" condition. If the field it's supposed to check (`customer_is_verified`) is missing from the previous node's output, the condition falls back to reading the **entire raw text response** instead — and any non-empty text counts as `true`, so the "false" branch is effectively unreachable whenever the field is missing.

### What we actually saw happen
In one of our real local runs, the Sentiment Agent's actual reply was a rate-limit error chat message (unrelated text) instead of structured data. The "Is Verified" condition read that entire message as its input and evaluated to `true` — confirmed directly from that execution's stored data, not just predicted from reading code.

### Root Cause
Passthrough condition evaluation has a silent fallback chain: missing field → falls back to raw output → non-empty string → truthy → `true`.

### Files & Lines

**`backend/services/conditions/value_extractor.py`**
- **Lines 219-224** — when `field_path` isn't found, it falls back to the **raw output string**.

**`backend/services/conditions/evaluators/passthrough.py`**
- **Lines 54-60** — any non-empty, non-"true"/"false" string is evaluated via Python truthiness, which makes it `True`.

### Fix (needs design decision)

Change the fallback in `value_extractor.py` so a genuinely **missing** field returns `None` (not the raw text), letting `passthrough.py`'s existing `None → False` check (lines 63-65) actually run.

⚠️ **Not yet verified:** whether any other condition in this workflow (e.g. "DB-Insertion-Success") relies on this same raw-text fallback intentionally — needs checking before changing, since this affects all conditions, not just "Is Verified."

---

# Abid's Findings (Real Environment — Actually Ran the Workflow)

**This section is different from everything above — Abid ran the real workflow in a real environment (real auth, real database) and captured actual error logs. This is stronger evidence than anything we produced ourselves, since it comes from directly running it, not just reading code.**

Source: `ERROR_REPORT_7705.md`, shared by Abid Dasurkar, dated 2026-09-14.

## What actually happened, in plain words

He ran the workflow with a FOR_EACH loop of 37 cases. Here's the chain of failure:

### 1. Database connection couldn't be found inside the loop (57 errors)

Every single one of the 37 loop iterations tried to fetch case data from the database, and **every single one failed** with "Connection not found" — even though the connection genuinely exists.

**Likely reason:** when code running *inside* a loop iteration (a "sub-agent") tries to look up a database connection, the system checks "does this specific user have permission to use this connection?" — but the information about *which user* is running never gets passed down into the loop. No user → permission check fails → "not found," even though the connection is real.

**Files to look at:** `backend/services/datasource/service.py` (around line 110-130), `backend/services/subgraph/executor.py`

### 2. That failure cascaded into a second, different-looking crash

Because the database call failed, no case data came back. The next step (Translation Agent) then tried to process a text field — but got `null` instead of real text, and crashed, because the system requires that field to always be a string, never empty.

**In plain words:** this looks like two separate bugs, but it's really one failure causing a second failure downstream.

### 3. Auth was also misconfigured

Two required settings (`AZURE_TENANT_ID`, `AZURE_JWKS_URL`) were missing, causing several unrelated 403 (permission denied) errors on other parts of the app, and the live-update connection (WebSocket) failing repeatedly — meaning the screen couldn't get real-time progress updates either.

### 4. THE MOST IMPORTANT FINDING — failures were being reported as successes

> "Tool `database_query_573554db` executed successfully: Query failed: Connection not found..."

**In plain words:** when the database lookup failed, the system didn't treat it as a real error. It wrote the failure message as plain text *inside* a "success" result — so anything checking "did this step fail?" would see **"yes, it succeeded"**, even though it clearly didn't. The failure was invisible to the parts of the system meant to catch failures.

**Why this matters a lot:** any future fix that tries to say "don't mark the workflow Completed if a node failed" **would not catch this specific kind of failure**, because this failure never gets marked as `"failed"` in the first place — it's disguised as a success.

### 5. The final result — matches the ticket exactly

In Abid's own words:
> "Parent workflow shows COMPLETED (incorrect)... 33 node executions remain queued... Database Queries: 57 failed attempts... Frontend: Cannot load execution panel"

**This is the exact symptom from the original ticket** — a completed workflow with nodes stuck in Queued — now backed by real logs showing exactly why, in a real environment.

## Abid's own recommendations (from his report)

1. **Fix sub-agent database access** — pass the correct user context down into loop iterations so connection lookups actually work (`backend/services/datasource/service.py`, `backend/services/subgraph/executor.py`)
2. **Fix the Translation Agent crash** — allow that text field to be empty/null instead of requiring it to always have a value
3. **Fix the missing auth environment variables** — `AZURE_TENANT_ID`, `AZURE_JWKS_URL`
4. **Fix the WebSocket connection issue**
5. **Stop disguising failures as successes** — make failed tool calls actually raise a real error instead of hiding the failure inside a "success" message. This is the change most directly relevant to fixing the "Completed while nodes are stuck" symptom.

## How this connects to what we found

- **Confirms the ticket's core symptom is real and reproducible** — independently, by someone else, with real infrastructure.
- **Gives a much more concrete, evidenced root cause** for *why* nodes end up stuck than our own theories (Issues 1-4 above explain *how the UI mislabels missing data*; Abid's report explains *an actual case where real execution genuinely failed and got hidden*).
- **Both can be true at once** — Issues 1-4 are about display bugs for legitimately-skipped nodes; Abid's findings are about genuine failures that get hidden. They're not competing explanations, they're different parts of the same overall problem.

---

## Summary Table

| # | Issue | Source | Confidence | Status |
|---|---|---|---|---|
| 1 | "Queued" label wrong | Our local runs + ticket screenshots | High | ✅ Ready to apply |
| 2 | Scary 404 error | Ticket screenshots (exact quoted text) | High — one check needed first | ✅ Ready, after confirming `fetchJson`'s error shape |
| 3 | "End 1" never recorded | Our local execution database (real runs) | High | ✅ Ready, one edge case to watch |
| 4 | Condition fooled by missing field | Our local execution data (real run) | High, but not ticket-reported | ⏸️ Paused |
| — | Database connection lookup fails in loop sub-agents | **Abid's real-environment run** | Very high — real logs, real environment | Owned by Abid / his team, not yet in our fix list |
| — | Failures disguised as "successful" tool results | **Abid's real-environment run** | Very high — real logs | Same — most directly relevant to the "Completed while stuck" symptom |

**Recommended order:** 1 → 2 → 3 (ours, fully specified, low-risk) alongside coordinating with Abid on his findings — especially the "failures disguised as success" issue, since that's the most likely actual explanation for the ticket's core symptom.
