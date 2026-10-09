import type { TutorialDefinition } from "../types";

export const settingsTutorial: TutorialDefinition = {
	id: "settings",
	label: "Settings",
	icon: "\u2699\uFE0F",
	stepCount: 9,
	estimatedMinutes: 2,
	route: "/settings",
	steps: [
		{
			element: '[data-tutorial="nav-settings"]',
			popover: {
				title: "Settings",
				description:
					"Configure your TADA Studio environment: API tokens, external service connections, and appearance preferences.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="appearance-tab"]',
			popover: {
				title: "Appearance",
				description:
					"Customize the look and feel of TADA Studio by selecting your preferred theme and branding.",
				side: "bottom",
				align: "center",
			},
			skipIfNotFound: '[data-tutorial="appearance-tab"]',
			autoClickSelector: '[data-tutorial="appearance-tab"]',
		},
		{
			element: '[data-tutorial="api-tokens-tab"]',
			popover: {
				title: "API Tokens",
				description:
					"Create and manage Personal Access Tokens (PATs) for authenticating API calls to your published workflows.",
				side: "bottom",
				align: "center",
			},
			skipIfNotFound: '[data-tutorial="api-tokens-tab"]',
			autoClickSelector: '[data-tutorial="api-tokens-tab"]',
		},
		{
			element: '[data-tutorial="llm-tab"]',
			popover: {
				title: "LLM Providers",
				description:
					"Configure AI model providers, manage deployments, and set default models for your agents.",
				side: "bottom",
				align: "center",
			},
			skipIfNotFound: '[data-tutorial="llm-tab"]',
			autoClickSelector: '[data-tutorial="llm-tab"]',
		},
		{
			element: '[data-tutorial="database-tab"]',
			popover: {
				title: "Database",
				description:
					"Manage database connections and settings used by the platform.",
				side: "bottom",
				align: "center",
			},
			skipIfNotFound: '[data-tutorial="database-tab"]',
			autoClickSelector: '[data-tutorial="database-tab"]',
		},
		{
			element: '[data-tutorial="external-tab"]',
			popover: {
				title: "External Services",
				description:
					"Configure connections to external services like LangSmith, Phoenix, and other observability integrations.",
				side: "bottom",
				align: "center",
			},
			skipIfNotFound: '[data-tutorial="external-tab"]',
			autoClickSelector: '[data-tutorial="external-tab"]',
		},
		{
			element: '[data-tutorial="external-tools-tab"]',
			popover: {
				title: "External Tools & MCP",
				description:
					"Configure custom MCP servers and external tool integrations that your workflow agents can use.",
				side: "bottom",
				align: "center",
			},
			skipIfNotFound: '[data-tutorial="external-tools-tab"]',
			autoClickSelector: '[data-tutorial="external-tools-tab"]',
		},
		{
			element: '[data-tutorial="tutorials-tab"]',
			popover: {
				title: "Tutorials",
				description:
					"Reset your tutorial progress to replay any tutorial from the beginning, or check which tutorials you\u2019ve completed.",
				side: "bottom",
				align: "center",
			},
			skipIfNotFound: '[data-tutorial="tutorials-tab"]',
			autoClickSelector: '[data-tutorial="tutorials-tab"]',
		},
		{
			popover: {
				title: "That\u2019s Settings!",
				description:
					"You\u2019ve seen the available settings tabs. Explore each section to configure TADA Studio to your needs.",
			},
		},
	],
};
