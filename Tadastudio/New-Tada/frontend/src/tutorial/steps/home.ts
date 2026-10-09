import type { TutorialDefinition } from "../types";

export const homeTutorial: TutorialDefinition = {
	id: "home",
	label: "Getting Started",
	icon: "\u{1F3E0}",
	stepCount: 21,
	estimatedMinutes: 4,
	route: "/",
	nextTutorialId: "library",
	steps: [
		// ── Navigation overview (7 steps) ────────────────────────────
		{
			element: '[data-tutorial="nav-workflow"]',
			popover: {
				title: "Workflow Tab",
				description:
					"Switch to the Workflow canvas where you build and edit your AI agent workflows visually.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="nav-library"]',
			popover: {
				title: "Library Tab",
				description:
					"Browse the workflow library to find templates and pre-built agents you can clone into your workspace.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="nav-publish"]',
			popover: {
				title: "Publish Tab",
				description:
					"Publish your workflows as API endpoints or shareable agents that others can use.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="nav-datasources"]',
			popover: {
				title: "Data Sources Tab",
				description:
					"Connect external data sources like databases and document stores for your agents to query.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="nav-evaluations"]',
			popover: {
				title: "Evaluations Tab",
				description:
					"Create and run evaluations to measure your workflow's quality, accuracy, and performance.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="nav-history"]',
			popover: {
				title: "Executions Tab",
				description:
					"View the history of all your workflow executions, inspect results, and debug runs.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="nav-manage"]',
			popover: {
				title: "Manage Workflows",
				description:
					"Use the Manage tab to manage all your workflows and load them for editing.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		// ── Create a workflow (1 step: fill + submit) ────────────────
		{
			element: '[data-tutorial="new-workflow-btn"]',
			popover: {
				title: "Create a New Workflow",
				description:
					"Let\u2019s create a new AI workflow. We\u2019ll open the dialog, fill in the details, and create it.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			nextClickSelector: '[data-tutorial="new-workflow-btn"]',
			completionSelector: '[data-tutorial="create-workflow-btn"]',
			autoFill: [
				{
					selector: '[data-tutorial="workflow-name-input"]',
					value: "Tutorial Workflow",
				},
				{
					selector: '[data-tutorial="workflow-desc-input"]',
					value: "A simple AI workflow that demonstrates how to build and run an agent.",
				},
			],
		},
		{
			element: '[data-tutorial="create-workflow-btn"]',
			popover: {
				title: "Create the Workflow",
				description:
					"The name and description are filled in. A good description helps the Evaluations feature auto-generate relevant test data. Let\u2019s create the workflow.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			autoFill: [
				{
					selector: '[data-tutorial="workflow-name-input"]',
					value: "Tutorial Workflow",
				},
				{
					selector: '[data-tutorial="workflow-desc-input"]',
					value: "A simple AI workflow that demonstrates how to build and run an agent.",
				},
			],
			nextClickSelector: '[data-tutorial="create-workflow-btn"]',
			completionSelector: '[data-tutorial="canvas-area"]',
		},
		// ── Add an agent from Start node (1 step) ────────────────────
		{
			element: '[data-tutorial="canvas-area"]',
			popover: {
				title: "Add an Agent Node",
				description:
					"Welcome to the canvas! The <strong>Start</strong> node receives user input. Click its <strong>+</strong> button to add an Agent node \u2014 it will be connected automatically.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			pointerTarget: '[data-tutorial="start-add-next-btn"]',
			waitForElement: true,
			fitView: true,
			nextClickSelector: '[data-tutorial="start-add-next-btn"]',
			completionSelector: '[data-tutorial="node-picker"]',
		},
		{
			element: '[data-tutorial="node-picker-agent"]',
			popover: {
				title: "Select Agent",
				description:
					"The node palette shows all available types. Select <strong>Agent</strong> to add an LLM-powered node.",
				side: "right",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="node-picker-agent"]',
			completionSelector: '[data-tutorial="agent-node"]',
		},
		// ── Configure the agent (open + fill + save) ─────────────────
		{
			element: '[data-tutorial="agent-node"]',
			popover: {
				title: "Agent Added",
				description:
					"Great \u2014 your Agent node is on the canvas and connected to Start. Let\u2019s open its settings to configure it.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			fitView: true,
			autoAdvanceDelay: 2000,
			autoClickSelector: '[data-tutorial="agent-settings-btn"]',
		},
		{
			element: '[data-tutorial="system-prompt-field"]',
			popover: {
				title: "System Prompt & Save",
				description:
					"The system prompt defines the agent\u2019s behavior. We\u2019ve filled in a default. You can also choose a model and explore the Input, Memory, Output, and Advanced tabs. Click <strong>Next</strong> to save and continue.",
				side: "left",
				align: "start",
			},
			waitForElement: true,
			preventPanelClose: true,
			autoFill: [
				{
					selector: '[data-tutorial="system-prompt-field"]',
					value: "You are a helpful AI assistant. You provide clear, accurate, and concise answers to user questions. When you don't know something, you say so honestly rather than guessing.",
				},
			],
			nextClickSelector: '[data-tutorial="config-save-btn"]',
			completionSelector: '[data-tutorial="agent-add-next-btn"]',
		},
		// ── Add End node (1 step) ────────────────────────────────────
		{
			element: '[data-tutorial="canvas-area"]',
			popover: {
				title: "Add the End Node",
				description:
					"Every workflow needs an End node. Click the Agent\u2019s <strong>+</strong> button to add one and complete the pipeline.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			pointerTarget: '[data-tutorial="agent-add-next-btn"]',
			waitForElement: true,
			fitView: true,
			nextClickSelector: '[data-tutorial="agent-add-next-btn"]',
			completionSelector: '[data-tutorial="node-picker-end"]',
		},
		{
			element: '[data-tutorial="node-picker-end"]',
			popover: {
				title: "Select End",
				description:
					"The End node marks where the workflow finishes and returns results.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
			waitForElement: true,
			nextClickSelector: '[data-tutorial="node-picker-end"]',
			completionSelector: '[data-tutorial="end-node"]',
		},
		// ── Run the workflow (1 step: open + fill + execute) ─────────
		{
			element: '[data-tutorial="run-btn"]',
			popover: {
				title: "Run the Workflow",
				description:
					"Let\u2019s run the workflow! We\u2019ll open the execution panel and fill in a sample message.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			nextClickSelector: '[data-tutorial="run-btn"]',
			completionSelector: '[data-tutorial="execution-panel"]',
		},
		{
			element: '[data-tutorial="execution-input"]',
			popover: {
				title: "Enter Input & Execute",
				description:
					"We\u2019ve filled in a sample message. Click <strong>Next</strong> to start the workflow and watch each node execute in real time.",
				side: "left",
				align: "center",
			},
			pointerPlacement: "left-center",
			waitForElement: true,
			autoFill: [
				{
					selector: '[data-tutorial="execution-textarea"]',
					value: "Hello! Please introduce yourself and tell me what you can help with.",
				},
			],
			nextClickSelector: '[data-tutorial="execution-start-btn"]',
		},
		// ── Execution results + enhanced trace (3 steps) ─────────────
		{
			element: '[data-tutorial="execution-timeline"]',
			popover: {
				title: "Execution Results",
				description:
					"The timeline shows each node as it executes with streaming output, status, and timing.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
			autoAdvanceDelay: 4000,
		},
		{
			element: '[data-tutorial="execution-input"]',
			popover: {
				title: "Agent Output",
				description:
					"Here\u2019s the agent\u2019s response. Click <strong>Next</strong> to open the Enhanced Trace View for a detailed breakdown of inputs, outputs, and timing.",
				side: "left",
				align: "center",
			},
			pointerTarget: '[data-tutorial="agent-result-card"]',
			pointerPlacement: "left-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="agent-result-card"]',
			nextClickSelector: '[data-tutorial="enhanced-view-btn"]',
			completionSelector: '[data-tutorial="trace-tree-panel"]',
		},
		{
			element: '[data-tutorial="trace-details-panel"]',
			popover: {
				title: "Trace Details",
				description:
					"The trace tree on the left shows every node that executed. Select any node to inspect its full output \u2014 messages exchanged with the model, tool calls, token usage, and cost. Use this view to debug and understand agent behavior.",
				side: "left",
				align: "start",
			},
			pointerPlacement: "left-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="trace-agent-node"]',
			nextClickSelector: '[data-tutorial="enhanced-view-close-btn"]',
		},
		{
			element: '[data-tutorial="canvas-area"]',
			popover: {
				title: "Tutorial Complete!",
				description:
					"You\u2019ve learned the basics: creating a workflow, adding and configuring an agent, running it, and exploring execution traces. Next, try the <strong>Library</strong> tutorial to discover pre-built templates you can clone and customize.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			fitView: true,
		},
	],
};
