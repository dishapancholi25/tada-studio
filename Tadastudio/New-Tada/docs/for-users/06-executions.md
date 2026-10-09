# Execution History

Navigate to **Executions** in the left menu to see a log of all past runs across your workflows.

<img width="1511" height="670" alt="image" src="https://github.com/user-attachments/assets/ba330e43-0595-4c85-b66e-e8bc962d16ed" />

The list shows:

| Column | Description |
|--------|-------------|
| **Workflow** | Name of the workflow that was run |
| **Status** | `completed`, `failed`, `running`, or `stopped` |
| **Started** | When the execution began |
| **Duration** | How long it took |

Use the search and filter controls to narrow by workflow name or status.

---

## Node Trace View

Click any execution in the list to open its trace. The trace shows each node as a step in the execution, in the order they ran.

<img width="1509" height="782" alt="image" src="https://github.com/user-attachments/assets/104ebd39-a16a-4871-9731-98102c4a4fe3" />

Click a node step to expand its detail:

- **Input** — what data the node received
- **Output** — what it produced
- **LLM metadata** — model used, token counts (input/output/total), duration
- **Tool calls** — for agent nodes with tools, each tool call and its result
- **Messages** — the full message history passed to the LLM

<img width="1381" height="811" alt="image" src="https://github.com/user-attachments/assets/94aaa0e0-f4a4-431f-b52a-9751f83005ad" />

---

## LangSmith Trace

If LangSmith tracing is enabled for your instance, each execution is also sent to LangSmith for deeper inspection. Click the **LangSmith** link on an execution to open the run in LangSmith.

<img width="1475" height="775" alt="image" src="https://github.com/user-attachments/assets/d02cd1a6-695e-475b-81bc-f0257c90077a" />

LangSmith provides a full chain-level trace including all LLM calls, tool invocations, latency breakdown,
and the ability to replay or annotate individual runs. This is most useful for debugging complex multi-agent
workflows or investigating performance issues.

> LangSmith tracing is configured by an administrator via the `LANGSMITH_API_KEY` and `LANGSMITH_TRACING` environment variables. If the link does not appear, tracing is not enabled on your instance.

---

## Feedback

You can rate executions and individual node results using the thumbs-up / thumbs-down buttons. Feedback serves two purposes:

1. **Quick quality signal** — Track which runs produced good or bad results as you iterate on a workflow.
2. **Evaluation datasets** — Positively-rated executions can be imported directly into the [Evaluations](./05-evaluations.md) feature as test cases, giving you a fast way to build a regression suite from known-good outputs.

### Rating an Execution

On any completed execution card in the history list, click the **thumbs-up** (good result) or **thumbs-down** (bad result) button. The button fills in to confirm your rating. Click the same button again to remove the rating.

<!-- SCREENSHOT: Execution card with thumbs-up/thumbs-down buttons -->

### Rating Individual Nodes

Inside the trace view, each node step also has its own thumbs-up / thumbs-down buttons. Use these when the overall execution was acceptable but a specific node underperformed (or vice versa).

<!-- SCREENSHOT: Node execution row with feedback buttons -->

### Filtering by Feedback

Use the **Feedback** filter dropdown in the execution history header to show only positively-rated or negatively-rated executions. This is useful for quickly finding your best runs when building evaluation datasets.

<!-- SCREENSHOT: Feedback filter dropdown showing All Feedback / Positive / Negative options -->

### How Feedback Feeds into Evaluations

When you create an evaluation dataset, the **Import Executions** tab shows only executions you have given a thumbs-up.
Select the runs you want, and they are converted into test cases with the original input and output pre-filled.
The **AI Generate** tab also lets you select positively-rated runs as few-shot examples
to guide the style and format of generated test cases.

> **Tip:** Get into the habit of rating executions as you work. A library of positively-rated runs makes it much faster to build high-quality evaluation datasets later.

---

## Exporting a Trace

From an execution's trace view, use the **Export** option to download the trace in JSON, YAML, or OpenTelemetry format for use in external tools.

<img width="148" height="77" alt="image" src="https://github.com/user-attachments/assets/2c9d0582-72c1-4fa8-bbc3-9e1e60c545e3" />
