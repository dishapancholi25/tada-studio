# Phoenix Trace Analysis

## What Is Phoenix?

Phoenix is an open-source observability tool integrated into Agentic Studio for deep LLM trace exploration. It runs alongside the built-in trace viewer and provides additional capabilities for inspecting what your AI agents are doing under the hood.

## Where You Will See Phoenix Links

Phoenix links appear in three places when Phoenix is enabled for your deployment:

- **Execution trace panel** (workflow runs) — a "View in Phoenix" button appears, linking to the full span timeline for that execution
- **Evaluation result detail panels** — each evaluation result includes a Phoenix trace link for the specific test case execution
- **Evaluation run summary** — a link to the Phoenix project view showing all traces for that evaluation run

## Built-in Trace Viewer vs Phoenix

| Feature | Built-in Trace Viewer | Phoenix |
|---------|----------------------|---------|
| Node-by-node execution view | Yes | — |
| LLM prompt/response inspection | — | Yes |
| Span timeline | — | Yes |
| Evaluation score annotations | — | Yes |
| Execution summary annotations | — | Yes |
| Dataset / experiment comparison | — | Yes (when synced) |
| Per-workflow project grouping | — | Yes |

Both views are complementary. The built-in trace viewer shows how your workflow executed node by node, while Phoenix shows the detailed LLM interactions within each node.

## Per-Workflow Projects

Each workflow's traces are automatically routed to a dedicated Phoenix project named after the workflow.
This means you can browse traces grouped by workflow in the Phoenix UI,
making it easy to focus on a specific workflow's behavior without filtering through all traces.

## How to Use Phoenix

### Trace Exploration

Click "View in Phoenix" from any execution or evaluation result. This opens the Phoenix span tree, where you can see the full call hierarchy — from the top-level workflow execution down to individual LLM calls.

### LLM Input/Output Inspection

Select any LLM span in the Phoenix trace to see the exact prompt sent to the model and the full response received. This is invaluable for debugging unexpected agent behavior.

### Evaluation Annotations

When an evaluation run completes, pillar scores (quality, cost, reliability, latency, composite) are attached as annotations to the corresponding spans in Phoenix. This lets you see exactly which LLM calls contributed to each score.

### Execution Summary Annotations

After each workflow execution completes, an "Execution Summary" annotation is added to the root span with the execution status, duration, node count, and trigger type. This makes it easy to filter and correlate runs in the Phoenix UI.

### Phoenix Supplementary Evaluators

When Phoenix evaluators are enabled, evaluation runs automatically include additional scoring beyond the built-in 4-pillar system:

| Evaluator | What it measures | Default |
|-----------|-----------------|---------|
| **Faithfulness** | Whether the output is grounded in the provided context (detects hallucinations) | Enabled |
| **Tool Selection** | Whether the correct tools were selected and called appropriately | Enabled |
| **LLM Judge** | Supplementary quality scoring from Phoenix's LLM judge | Disabled |

These supplementary scores appear in the evaluation result detail panel alongside the standard pillar scores. If **quality penalty** is enabled, low faithfulness scores will reduce the quality pillar score.

### Judge Provider Selection

When starting an evaluation run, you can choose between two judge providers:

- **Built-in** — the default judge that scores against your custom criteria and expected outputs
- **Phoenix** — uses Phoenix's LLM judge for quality scoring, which provides an independent second opinion

The default judge provider can be configured in **Evaluations → Settings**.

### Experiments and Dataset Comparison

When dataset sync is enabled, evaluation runs appear as Phoenix experiments under the linked dataset. This allows you to compare results across multiple evaluation runs side by side.

## Configuring Phoenix

Phoenix settings are managed in **Settings → External Services → Phoenix**. You can enable or disable Phoenix and configure the endpoint, project name, and API key. Changes take effect immediately — no restart required.

## Why a Phoenix Link Might Not Appear

- **Phoenix is not enabled** for this deployment (`PHOENIX_ENABLED=false`) — contact your administrator
- **Trace could not be correlated** — the span was not emitted or metadata was missing during execution
- **Phoenix was temporarily unavailable** during the evaluation run — the evaluation result itself is still valid; only the Phoenix link is missing
