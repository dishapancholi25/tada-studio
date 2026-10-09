import type { TutorialDefinition } from "../types";

export const executionsTutorial: TutorialDefinition = {
	id: "executions",
	label: "Executions",
	icon: "\u{1F4DC}",
	stepCount: 17,
	estimatedMinutes: 4,
	route: "/executions",
	nextTutorialId: "settings",
	steps: [
		// ── Overview ────────────────────────────────────────────────────
		{
			popover: {
				title: "Execution History",
				description:
					"Welcome to the Executions page! We\u2019ve just run the Tutorial Workflow so there\u2019s a completed execution to explore. Let\u2019s walk through all the features.",
				side: "bottom",
				align: "center",
			},
		},
		{
			element: '[data-tutorial="executions-header"]',
			popover: {
				title: "Header & Refresh",
				description:
					"The header shows the total number of executions and a Refresh button to fetch the latest runs from the server.",
				side: "bottom",
				align: "center",
			},
			pointerPlacement: "bottom-center",
		},
		// ── Filters ─────────────────────────────────────────────────────
		{
			element: '[data-tutorial="executions-filters"]',
			popover: {
				title: "Search & Filters",
				description:
					"Filter executions by workflow name, status (completed, failed, running), trigger source (editor, API, evaluation, scheduler), and feedback rating.",
				side: "bottom",
				align: "center",
			},
			pointerPlacement: "bottom-center",
		},
		{
			element: '[data-tutorial="executions-search"]',
			popover: {
				title: "Search Executions",
				description:
					"Type a workflow name or execution ID to quickly find a specific run. Results update as you type.",
				side: "bottom",
				align: "start",
			},
			pointerPlacement: "bottom-left",
		},
		// ── Execution card ──────────────────────────────────────────────
		{
			element: '[data-tutorial="execution-row"]',
			popover: {
				title: "Execution Card",
				description:
					"Each card shows an execution\u2019s status, workflow name, duration, timestamp, trigger source, and node count. Click to expand and see node-level details.",
				side: "bottom",
				align: "center",
			},
			pointerPlacement: "bottom-center",
		},
		{
			element: '[data-tutorial="execution-row"]',
			popover: {
				title: "Expand Execution",
				description:
					"Let\u2019s expand this card to see the node-by-node breakdown of the run.",
				side: "bottom",
				align: "center",
			},
			pointerPlacement: "bottom-center",
			nextClickSelector: '[data-tutorial="execution-row-header"]',
		},
		{
			element: '[data-tutorial="execution-row"]',
			popover: {
				title: "Node Execution Details",
				description:
					"The expanded view shows metadata (start time, end time, user ID, node count) and the result of each node that executed in the workflow.",
				side: "bottom",
				align: "center",
			},
		},
		// ── Action buttons ──────────────────────────────────────────────
		{
			element: '[data-tutorial="execution-actions"]',
			popover: {
				title: "Action Buttons",
				description:
					"Rate results with thumbs up/down for quality tracking. Use the eye icon for the enhanced trace view, the branch icon for the graph view, or the trash icon to delete.",
				side: "bottom",
				align: "end",
			},
			pointerPlacement: "bottom-right",
		},
		// ── Open trace viewer ───────────────────────────────────────────
		{
			element: '[data-tutorial="export-btn"]',
			popover: {
				title: "Open Trace View",
				description:
					"The trace view shows a detailed execution trace with the full node-by-node breakdown, inputs, outputs, and timing. Let\u2019s open it.",
				side: "left",
				align: "center",
			},
			pointerPlacement: "left-center",
			nextEvent: {
				event: "tutorialOpenTraceViewer",
			},
		},
		{
			element: '[data-tutorial="trace-tree-panel"]',
			popover: {
				title: "Trace Tree",
				description:
					"The left panel shows every node that executed as a tree. Expand nodes to see sub-steps like LLM calls and tool invocations.",
				side: "right",
				align: "start",
			},
			pointerPlacement: "right-center",
			waitForElement: true,
		},
		{
			element: '[data-tutorial="trace-agent-node"]',
			popover: {
				title: "Select a Node",
				description:
					"Click a node to see its detailed output \u2014 the full conversation, token usage, cost, and timing.",
				side: "right",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="trace-agent-node"]',
			completionSelector: '[data-tutorial="trace-details-panel"]',
		},
		{
			element: '[data-tutorial="trace-details-panel"]',
			popover: {
				title: "Node Details",
				description:
					"The details panel shows the agent\u2019s full output \u2014 messages exchanged with the model, any tool calls made, and the final response.",
				side: "left",
				align: "start",
			},
			pointerPlacement: "left-center",
			waitForElement: true,
		},
		// ── Switch to graph view ────────────────────────────────────────
		{
			element: '[data-tutorial="view-toggle"]',
			popover: {
				title: "Switch to Graph View",
				description:
					"The view toggle lets you switch between Trace view and Graph view. Let\u2019s switch to the Graph view to see the workflow layout with execution status.",
				side: "bottom",
				align: "center",
			},
			pointerPlacement: "bottom-center",
			waitForElement: true,
			skipIfNotFound: '[data-tutorial="view-toggle"]',
			nextEvent: {
				event: "tutorialSwitchToGraphView",
			},
		},
		{
			element: '[data-tutorial="execution-graph-viewer"]',
			popover: {
				title: "Graph View",
				description:
					"The Graph view shows every node\u2019s execution status, timing, and outputs directly on the visual workflow canvas. Click any node to inspect its details. Great for understanding complex multi-node workflows at a glance.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
		},
		{
			element: '[data-tutorial="graph-view-close-btn"]',
			popover: {
				title: "Close Graph View",
				description:
					"Let\u2019s close the graph viewer and return to the execution list.",
				side: "left",
				align: "center",
			},
			pointerPlacement: "bottom-right",
			waitForElement: true,
			nextEvent: {
				event: "tutorialCloseGraphViewer",
			},
		},
		// ── Wrap-up ─────────────────────────────────────────────────────
		{
			popover: {
				title: "You\u2019re All Set!",
				description:
					"You now know how to browse execution history, filter runs, inspect trace details, and switch between trace and graph views. Every workflow run is recorded here for debugging and quality tracking.",
				side: "bottom",
				align: "center",
			},
		},
	],
};
