import type { TutorialDefinition } from "../types";

export const workflowCanvasTutorial: TutorialDefinition = {
	id: "workflow-canvas",
	label: "Workflow Canvas",
	icon: "\u{1F527}",
	stepCount: 26,
	estimatedMinutes: 5,
	route: "/workflow",
	nextTutorialId: "library",
	steps: [
		{
			element: '[data-tutorial="canvas-area"]',
			popover: {
				title: "Workflow Canvas",
				description:
					"This is the visual canvas where you design your AI workflows. Drag to pan, scroll to zoom, and connect nodes to build your pipeline.",
				side: "bottom",
				align: "center",
			},
			fitView: true,
		},
		{
			element: '[data-tutorial="start-node"]',
			popover: {
				title: "Start Node",
				description:
					"Every workflow begins with a Start node. It receives the initial user input and passes it to the first agent.",
				side: "right",
				align: "center",
			},
		},
		{
			element: '[data-tutorial="add-node-btn"]',
			popover: {
				title: "Add a Node",
				description:
					"This button opens the node palette where you can add agents, tools, conditions, and more to your workflow.",
				side: "right",
				align: "center",
			},
			nextClickSelector: '[data-tutorial="add-node-btn"]',
			completionSelector: '[data-tutorial="node-picker"]',
		},
		{
			element: '[data-tutorial="node-picker"]',
			popover: {
				title: "Node Palette",
				description:
					"The node palette shows all available node types. Select one to add it to the canvas.",
				side: "right",
				align: "center",
			},
			waitForElement: true,
		},
		{
			element: '[data-tutorial="node-picker-agent"]',
			popover: {
				title: "Add an Agent Node",
				description:
					"We\u2019ll add an Agent node to the canvas and then configure it.",
				side: "right",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="node-picker-agent"]',
			completionSelector: '[data-tutorial="agent-node"]',
		},
		{
			element: '[data-tutorial="agent-settings-btn"]',
			popover: {
				title: "Open Node Settings",
				description:
					"Each node has a settings panel. Let\u2019s open it to configure the agent.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="agent-settings-btn"]',
			completionSelector: '[data-tutorial="config-sidebar"]',
		},
		{
			element: '[data-tutorial="config-sidebar"]',
			popover: {
				title: "Node Configuration Panel",
				description:
					"This is the configuration panel. Here you can set the system prompt, model, tools, and more.",
				side: "left",
				align: "start",
			},
			waitForElement: true,
			preventPanelClose: true,
		},
		{
			element: '[data-tutorial="system-prompt-field"]',
			popover: {
				title: "System Prompt",
				description:
					"The system prompt defines the agent\u2019s role, personality, and behavior. We\u2019ll set a helpful default.",
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
		},
		{
			element: '[data-tutorial="model-selector"]',
			popover: {
				title: "Model Selector",
				description:
					"Choose which AI model deployment this agent should use. Different models offer different capabilities and performance trade-offs.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
			scrollCenter: true,
			preventPanelClose: true,
			autoClickSelector:
				'[data-tutorial="model-selector"] button[aria-haspopup="listbox"]',
		},
		{
			element: '[data-tutorial="tools-section"]',
			popover: {
				title: "Tools & Configuration",
				description:
					"Configure tools, model parameters, and other settings for this agent node.",
				side: "left",
				align: "center",
			},
			waitForElement: true,

			preventPanelClose: true,
		},
		{
			element: '[data-tutorial="config-tab-input"]',
			popover: {
				title: "Input Tab",
				description:
					"The Input tab controls how this agent receives data. You can select which nodes provide context, pick specific fields, or write a custom template.",
				side: "right",
				align: "center",
			},
			waitForElement: true,

			preventPanelClose: true,
			autoClickSelector: '[data-tutorial="config-tab-input"]',
		},
		{
			element: '[data-tutorial="config-tab-memory"]',
			popover: {
				title: "Memory Tab",
				description:
					"The Memory tab enables conversation history. When enabled, the agent remembers previous interactions within the same session.",
				side: "right",
				align: "center",
			},
			waitForElement: true,

			preventPanelClose: true,
			autoClickSelector: '[data-tutorial="config-tab-memory"]',
		},
		{
			element: '[data-tutorial="config-tab-output"]',
			popover: {
				title: "Output Tab",
				description:
					"The Output tab lets you define structured output schemas. This ensures the agent returns data in a specific JSON format you define.",
				side: "right",
				align: "center",
			},
			waitForElement: true,

			preventPanelClose: true,
			autoClickSelector: '[data-tutorial="config-tab-output"]',
		},
		{
			element: '[data-tutorial="config-tab-advanced"]',
			popover: {
				title: "Advanced Tab",
				description:
					"The Advanced tab provides options for human review gating, response validation, and other fine-tuning controls.",
				side: "right",
				align: "center",
			},
			waitForElement: true,

			preventPanelClose: true,
			autoClickSelector: '[data-tutorial="config-tab-advanced"]',
		},
		{
			element: '[data-tutorial="config-save-btn"]',
			popover: {
				title: "Save Changes",
				description:
					"We\u2019ll save the agent configuration and close the panel.",
				side: "top",
				align: "end",
			},
			waitForElement: true,

			nextClickSelector: '[data-tutorial="config-save-btn"]',
			completionSelector: '[data-tutorial="connection-handle"]',
		},
		{
			element: '[data-tutorial="connection-handle"]',
			popover: {
				title: "Connect the Nodes",
				description:
					"Nodes need to be connected to form a pipeline. We\u2019ll automatically connect the Start node to the Agent.",
				side: "top",
				align: "center",
			},

			fitView: true,
			nextEvent: {
				event: "tutorialConnectNodes",
				detail: {
					sourceSelector: '[data-tutorial="start-node"]',
					targetSelector: '[data-tutorial="agent-node"]',
				},
			},
		},
		{
			element: '[data-tutorial="canvas-area"]',
			popover: {
				title: "Add Next Node",
				description:
					"Every workflow needs an End node to complete the pipeline. Let\u2019s add one from the Agent\u2019s + button.",
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
				title: "Add an End Node",
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
		{
			element: '[data-tutorial="toolbar"]',
			popover: {
				title: "Floating Toolbar",
				description:
					"The toolbar provides quick actions: run, reset, save, duplicate, export, import, and version history.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			fitView: true,
		},
		{
			element: '[data-tutorial="run-btn"]',
			popover: {
				title: "Run Workflow",
				description:
					"The Run button opens the execution panel where you can enter input and start your workflow.",
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
				title: "Enter a Message",
				description:
					"This is the initial input that gets passed to the Start node. We\u2019ll fill in a sample message.",
				side: "left",
				align: "start",
			},
			waitForElement: true,

			autoFill: [
				{
					selector: '[data-tutorial="execution-input"]',
					value: "Hello! Please introduce yourself and tell me what you can help with.",
				},
			],
		},
		{
			element: '[data-tutorial="execution-start-btn"]',
			popover: {
				title: "Run the Workflow",
				description:
					"Now we\u2019ll start the workflow. You\u2019ll see each node process in real time on the canvas.",
				side: "left",
				align: "center",
			},
			waitForElement: true,

			nextClickSelector: '[data-tutorial="execution-start-btn"]',
		},
		{
			element: '[data-tutorial="execution-timeline"]',
			popover: {
				title: "Execution Timeline",
				description:
					"The timeline shows each node as it executes in real time. You can see streaming output, execution status, and timing for every step of your workflow.",
				side: "left",
				align: "center",
			},
			waitForElement: true,

			autoAdvanceDelay: 4000,
		},
		{
			element: '[data-tutorial="agent-result-card"]',
			popover: {
				title: "View Agent Output",
				description:
					"The agent card shows the response. Let\u2019s expand it to see the full output, token usage, and any tool calls.",
				side: "left",
				align: "center",
			},
			waitForElement: true,

			nextClickSelector: '[data-tutorial="agent-result-card"]',
		},
		{
			element: '[data-tutorial="enhanced-view-btn"]',
			popover: {
				title: "Enhanced Trace View",
				description:
					"The Enhanced View shows a detailed execution trace with the full node-by-node breakdown, inputs, outputs, and timing.",
				side: "bottom",
				align: "end",
			},
			pointerPlacement: "bottom-right",
			waitForElement: true,

			nextClickSelector: '[data-tutorial="enhanced-view-btn"]',
		},
		{
			element: '[data-tutorial="enhanced-view-close-btn"]',
			popover: {
				title: "Close Enhanced View",
				description:
					"Let\u2019s close the enhanced viewer and return to the workflow canvas.",
				side: "left",
				align: "center",
			},
			pointerPlacement: "left-center",
			waitForElement: true,

			nextClickSelector: '[data-tutorial="enhanced-view-close-btn"]',
		},
	],
};
