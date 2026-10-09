import type { TutorialDefinition } from "../types";

export const libraryTutorial: TutorialDefinition = {
	id: "library",
	label: "Library",
	icon: "\u{1F4DA}",
	stepCount: 7,
	estimatedMinutes: 2,
	route: "/library",
	nextTutorialId: "publish",
	steps: [
		{
			element: '[data-tutorial="nav-library"]',
			popover: {
				title: "Workflow Library",
				description:
					"Welcome to the Library. Here you can browse, search, and clone pre-built workflow templates and agents.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="library-category"]',
			popover: {
				title: "Select a Category",
				description:
					"The library is organised into categories. Let\u2019s open one to see the available templates.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="library-category"]',
			completionSelector: '[data-tutorial="library-search"]',
		},
		{
			element: '[data-tutorial="library-search"]',
			popover: {
				title: "Search Workflows",
				description:
					"Type here to search for workflows by name, description, or category. Results update as you type.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
		},
		{
			element: '[data-tutorial="library-filters"]',
			popover: {
				title: "Filter Options",
				description:
					"Toggle filters to narrow results by category, complexity, or other criteria.",
				side: "bottom",
				align: "center",
			},
		},
		{
			element: '[data-tutorial="library-card"]',
			popover: {
				title: "Workflow Card",
				description:
					"Each card shows a workflow template with its name, description, and metadata. You can preview or clone it.",
				side: "bottom",
				align: "center",
			},
		},
		{
			element: '[data-tutorial="library-clone-btn"]',
			popover: {
				title: "Clone a Template",
				description:
					"Use the Clone button on any template to copy it into your workspace. You can then customize it freely.",
				side: "top",
				align: "center",
			},
		},
		{
			element: '[data-tutorial="import-agent-btn"]',
			popover: {
				title: "Import Agent",
				description:
					"Import an agent from a JSON configuration file. Useful for sharing agents between teams or environments.",
				side: "bottom",
				align: "center",
			},
		},
	],
};
