import type { TutorialDefinition } from "../types";

export const publishTutorial: TutorialDefinition = {
	id: "publish",
	label: "Publish",
	icon: "\u{1F4E1}",
	stepCount: 11,
	estimatedMinutes: 3,
	route: "/publish",
	nextTutorialId: "datasources",
	steps: [
		{
			element: '[data-tutorial="nav-publish"]',
			popover: {
				title: "Workflow Publishing",
				description:
					"Let's publish a workflow as an HTTP endpoint so it can be called from external applications and automations.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="publish-available-heading"]',
			popover: {
				title: "Available Workflows",
				description:
					"Your unpublished workflows appear here. We'll use the Tutorial Workflow for this demo \u2014 you'll publish it in the next step.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
		},
		{
			element: '[data-tutorial="publish-demo-btn"]',
			popover: {
				title: "Publish the Workflow",
				description:
					"Click Publish to make the Tutorial Workflow available as an HTTP API endpoint.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			nextEvent: {
				event: "tutorialPublishWorkflow",
			},
		},
		{
			element: '[data-tutorial="publish-workflows-section"]',
			popover: {
				title: "Workflow Published!",
				description:
					"Your workflow is now live! It appears in the Published section with a green badge. External apps can call it via HTTP.",
				side: "top",
				align: "center",
			},
			waitForElement: true,
		},
		{
			element: '[data-tutorial="publish-expand-btn"]',
			popover: {
				title: "Expand Endpoint Details",
				description:
					"Let\u2019s expand the details to see the endpoint URL, cURL example, authentication, and scheduling options.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialExpandPublished",
			},
		},
		{
			element: '[data-tutorial="publish-detail-endpoint"]',
			popover: {
				title: "API Endpoint URL",
				description:
					"This is your workflow's unique API endpoint URL. Copy it and use it to call the workflow from external applications, scripts, or integrations.",
				side: "left",
				align: "start",
			},
			waitForElement: true,

		},
		{
			element: '[data-tutorial="publish-detail-curl"]',
			popover: {
				title: "cURL Example",
				description:
					"Here's a ready-to-use cURL command with the correct auth header and request body. Copy it to test your endpoint from the terminal.",
				side: "left",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,

		},
		{
			element: '[data-tutorial="publish-detail-token"]',
			popover: {
				title: "Authentication & Tokens",
				description:
					"Three token types are supported: workflow tokens (wf_), Personal Access Tokens (na_), and JWTs. Each provides different scoping and flexibility.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,

		},
		{
			element: '[data-tutorial="publish-detail-schedule"]',
			popover: {
				title: "Scheduling",
				description:
					"Set up cron-based scheduling to run your workflow automatically on a recurring basis \u2014 hourly, daily, weekly, or custom.",
				side: "left",
				align: "start",
			},
			waitForElement: true,

		},
		{
			element: '[data-tutorial="publish-unpublish-btn"]',
			popover: {
				title: "Unpublish the Workflow",
				description:
					"Let\u2019s clean up by unpublishing the tutorial workflow. This removes the HTTP endpoint so it can no longer be called externally.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialUnpublishWorkflow",
			},
		},
		{
			popover: {
				title: "Tutorial Complete!",
				description:
					"You've learned how to publish and unpublish workflows as HTTP endpoints, configure authentication, and set up scheduling.",
			},
		},
	],
};
