import type { TutorialDefinition } from "../types";

export const datasourcesTutorial: TutorialDefinition = {
	id: "datasources",
	label: "Data Sources",
	icon: "\u{1F4C2}",
	stepCount: 27,
	estimatedMinutes: 5,
	route: "/datasources",
	nextTutorialId: "evaluations",
	steps: [
		{
			element: '[data-tutorial="nav-datasources"]',
			popover: {
				title: "Data Sources",
				description:
					"Manage the data your AI agents can access: document collections for RAG, database connections, and API endpoints.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},
		{
			element: '[data-tutorial="collections-tab"]',
			popover: {
				title: "Document Collections",
				description:
					"The Documents tab lets you manage document collections for Retrieval-Augmented Generation (RAG).",
				side: "bottom",
				align: "center",
			},
			nextClickSelector: '[data-tutorial="collections-tab"]',
		},
		{
			element: '[data-tutorial="new-collection-btn"]',
			popover: {
				title: "Add a Collection",
				description:
					"This button opens the create collection form. Let\u2019s create one.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="new-collection-btn"]',
			completionSelector: '[data-tutorial="create-collection-modal"]',
		},
		{
			element: '[data-tutorial="create-collection-modal"]',
			popover: {
				title: "Create Collection Form",
				description:
					"This is the collection creation form. Give your collection a name and optional description, then choose visibility settings.",
				side: "left",
				align: "start",
			},
			waitForElement: true,

		},
		{
			element: '[data-tutorial="collection-name-input"]',
			popover: {
				title: "Collection Name",
				description:
					"The collection name identifies it when you attach it to a Document Search node in your workflow. We\u2019ll fill one in.",
				side: "left",
				align: "center",
			},
			waitForElement: true,

			autoFill: [
				{
					selector: '[data-tutorial="collection-name-input"]',
					value: "Tutorial Collection",
				},
			],
		},
		{
			element: '[data-tutorial="collection-description-input"]',
			popover: {
				title: "Collection Description",
				description:
					"Add a description so collaborators know what this collection is for. We\u2019ll fill one in.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
			autoFill: [
				{
					selector: '[data-tutorial="collection-description-input"]',
					value: "A sample document collection created by the tutorial.",
				},
			],
		},
		{
			element: '[data-tutorial="create-collection-submit"]',
			popover: {
				title: "Create the Collection",
				description:
					"We\u2019ll save the collection so you can then upload documents to it.",
				side: "top",
				align: "end",
			},
			pointerPlacement: "top-center",
			waitForElement: true,

			nextClickSelector: '[data-tutorial="create-collection-submit"]',
		},
		{
			element: '[data-tutorial="collection-card-first"]',
			popover: {
				title: "Open Your Collection",
				description:
					"Your newly created collection appears here. Let\u2019s open it to view its documents.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="collection-card-first"]',
			completionSelector: '[data-tutorial="collection-edit-upload-btn"]',
		},
		{
			element: '[data-tutorial="collection-edit-upload-btn"]',
			popover: {
				title: "Edit & Upload",
				description:
					"The Edit & Upload button opens the collection editor where you can manage settings and upload documents.",
				side: "bottom",
				align: "end",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="collection-edit-upload-btn"]',
			completionSelector: '[data-tutorial="collection-upload-zone"]',
		},
		{
			element: '[data-tutorial="collection-upload-zone"]',
			popover: {
				title: "Upload Documents",
				description:
					"Drag and drop files here or click to browse. Upload PDFs, text files, and other documents \u2014 they'll be chunked and indexed for vector search.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,

		},
		{
			element: '[data-tutorial="collection-edit-close-btn"]',
			popover: {
				title: "Back to Collections",
				description:
					"Let's close the editor and explore the other data source types.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialCloseCollectionEditor",
			},
		},
		// ── Database connections ────────────────────────────────────────
		{
			element: '[data-tutorial="db-connections-tab"]',
			popover: {
				title: "Database Connections",
				description:
					"The Databases tab lets you connect your agents to external databases for querying structured data.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="db-connections-tab"]',
		},
		{
			element: '[data-tutorial="db-add-connection-btn"]',
			popover: {
				title: "Add a Database Connection",
				description:
					"Let\u2019s open the connection form to see the available options.",
				side: "bottom",
				align: "end",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="db-add-connection-btn"]',
			completionSelector: '[data-tutorial="db-connection-modal"]',
		},
		{
			element: '[data-tutorial="db-type-selector"]',
			popover: {
				title: "Choose a Database Type",
				description:
					"Select your database engine \u2014 PostgreSQL, MySQL, MongoDB, SQLite, MS SQL, or Oracle. The form adapts its fields to each type.",
				side: "left",
				align: "start",
			},
			waitForElement: true,
		},
		{
			element: '[data-tutorial="db-connection-method"]',
			popover: {
				title: "Connection Method",
				description:
					"Connect using individual fields (host, port, credentials) or paste a full connection string. Both produce the same result.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
		},
		{
			element: '[data-tutorial="db-connection-modal"]',
			popover: {
				title: "Close the Form",
				description:
					"We won\u2019t save a connection now \u2014 let\u2019s close the form and move on to API endpoints.",
				side: "bottom",
				align: "center",
			},
			pointerPlacement: "bottom-center",
			pointerTarget: '[data-tutorial="db-cancel-btn"]',
			waitForElement: true,
			nextClickSelector: '[data-tutorial="db-cancel-btn"]',
		},
		// ── API endpoints ──────────────────────────────────────────────
		{
			element: '[data-tutorial="endpoints-tab"]',
			popover: {
				title: "API Endpoints",
				description:
					"The Endpoints tab lets you define reusable HTTP endpoint configurations for your workflow\u2019s HTTP request nodes.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="endpoints-tab"]',
		},
		{
			element: '[data-tutorial="endpoint-add-btn"]',
			popover: {
				title: "Add an Endpoint",
				description:
					"Let\u2019s open the endpoint form to explore its configuration tabs.",
				side: "bottom",
				align: "end",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="endpoint-add-btn"]',
			completionSelector: '[data-tutorial="endpoint-modal"]',
		},
		{
			element: '[data-tutorial="endpoint-tab-basic"]',
			popover: {
				title: "Basic Information",
				description:
					"Name your endpoint, add a description, and choose the service type (generic, ServiceNow, Salesforce, Azure, AWS, etc.).",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
		},
		{
			element: '[data-tutorial="endpoint-tab-request"]',
			popover: {
				title: "Request Configuration",
				description:
					"Set the HTTP method, URL template, content type, custom headers, and an optional request body template.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="endpoint-tab-request"]',
		},
		{
			element: '[data-tutorial="endpoint-tab-auth"]',
			popover: {
				title: "Authentication",
				description:
					"Configure how the endpoint authenticates \u2014 Bearer token, API key (header or query), Basic auth, or a custom token scheme.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="endpoint-tab-auth"]',
		},
		{
			element: '[data-tutorial="endpoint-tab-response"]',
			popover: {
				title: "Response Handling",
				description:
					"Choose the expected response format (JSON, XML, binary) and optionally specify a JSONPath to extract a specific field.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="endpoint-tab-response"]',
		},
		{
			element: '[data-tutorial="endpoint-tab-advanced"]',
			popover: {
				title: "Advanced Options",
				description:
					"Fine-tune timeouts, retries, retry delay, redirect behaviour, and SSL verification.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="endpoint-tab-advanced"]',
		},
		{
			element: '[data-tutorial="endpoint-close-btn"]',
			popover: {
				title: "Close the Form",
				description:
					"We\u2019ve toured all the configuration tabs. Let\u2019s close the form.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="endpoint-close-btn"]',
		},
		// ── Cleanup ────────────────────────────────────────────────────
		{
			element: '[data-tutorial="collections-tab"]',
			popover: {
				title: "Clean Up",
				description:
					"Let\u2019s switch back to collections and remove the demo collection we created earlier.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="collections-tab"]',
		},
		{
			element: '[data-tutorial="collection-delete-btn"]',
			popover: {
				title: "Delete Demo Collection",
				description:
					"We\u2019ll delete the Tutorial Collection to keep your workspace tidy.",
				side: "left",
				align: "center",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialDeleteCollection",
			},
		},
		{
			popover: {
				title: "Tutorial Complete!",
				description:
					"You've explored the Data Sources page \u2014 document collections with RAG, database connections, and API endpoints. Data sources can be shared across workflows using visibility controls.",
			},
		},
	],
};
