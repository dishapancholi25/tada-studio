import type { TutorialDefinition } from "../types";

export const evaluationsTutorial: TutorialDefinition = {
	id: "evaluations",
	label: "Evaluations",
	icon: "\u{1F9EA}",
	stepCount: 38,
	estimatedMinutes: 12,
	route: "/evaluations",
	nextTutorialId: "executions",
	steps: [
		// ── 0. Intro ────────────────────────────────────────────────────
		{
			element: '[data-tutorial="nav-evaluations"]',
			popover: {
				title: "Evaluations",
				description:
					"Welcome to Evaluations \u2014 the AI testing ground. We\u2019ll use the Tutorial Workflow from the canvas tutorial and a demo dataset so you can explore the full cycle: create \u2192 run \u2192 review \u2192 improve \u2192 compare.",
				side: "right",
				align: "center",
			},
			pointerPlacement: "right-center",
		},

		// ── 1. Datasets tab ─────────────────────────────────────────────
		{
			element: '[data-tutorial="datasets-tab"]',
			popover: {
				title: "Datasets Tab",
				description:
					"Datasets are collections of test cases \u2014 input/expected\u2011output pairs \u2014 that your workflow is evaluated against. Let\u2019s take a look.",
				side: "bottom",
				align: "center",
			},
			nextClickSelector: '[data-tutorial="datasets-tab"]',
		},

		// ── 2. New Dataset button ───────────────────────────────────────
		{
			element: '[data-tutorial="new-dataset-btn"]',
			popover: {
				title: "Create a New Dataset",
				description:
					"Click \u201CNew Dataset\u201D to create a dataset. You\u2019ll choose a name, target type (workflow, agent, model, or tool), and the specific target. For this tutorial, we\u2019ve already created a demo dataset for you \u2014 let\u2019s explore it.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
		},

		// ── 3. Demo dataset ─────────────────────────────────────────────
		{
			element: '[data-tutorial="eval-dataset-first"]',
			popover: {
				title: "Your Demo Dataset",
				description:
					"We created a dataset with three test cases covering geography, summarization, and translation. Let\u2019s open it to explore the dataset editor.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialOpenDataset",
			},
		},


		// ── 4. Test Cases tab ───────────────────────────────────────────
		{
			element: '[data-tutorial="dataset-modal-content"]',
			popover: {
				title: "Test Cases",
				description:
					"The header shows the dataset name, target type, linked workflow, and test case count. Below, each test case has an input, expected output, optional judge criteria, and tags. We\u2019ve expanded the first case so you can see the full detail \u2014 input on the left, expected output on the right, with judge criteria and tags below.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="test-case-first-row"]',
		},


		// ── 5. Add Manual tab ───────────────────────────────────────────
		{
			element: '[data-tutorial="dataset-tab-manual-content"]',
			popover: {
				title: "Add Manual",
				description:
					"Write test cases by hand \u2014 enter the input text your workflow will receive, the expected output for comparison, and judge criteria that define how to score the response. You can also attach files for document-processing workflows.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			autoClickSelector: '[data-tutorial="dataset-tab-manual"]',
			waitForElement: true,
		},

		// ── 6. AI Generate tab ──────────────────────────────────────────
		{
			element: '[data-tutorial="dataset-tab-ai-content"]',
			popover: {
				title: "AI Generate",
				description:
					"Create test cases automatically from a seed prompt. Pick a generator model, set the count (1\u201320), enable edge cases for adversarial inputs, and select example executions as few-shot guidance. The system auto-enriches context from the workflow\u2019s configuration.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			autoClickSelector: '[data-tutorial="dataset-tab-ai"]',
			waitForElement: true,
		},

		// ── 7. Import Executions tab ────────────────────────────────────
		{
			element: '[data-tutorial="dataset-tab-import-executions"]',
			popover: {
				title: "Import Executions",
				description:
					"Pull test cases from positively-rated past workflow runs. Every thumbs-up you give in the execution viewer can become a test case \u2014 a great way to build your dataset from real production data.",
				side: "bottom",
				align: "center",
			},
			autoClickSelector: '[data-tutorial="dataset-tab-import-executions"]',
			waitForElement: true,
		},

		// ── 8. Export/Import tab ────────────────────────────────────────
		{
			element: '[data-tutorial="dataset-tab-export-import"]',
			popover: {
				title: "Export / Import",
				description:
					"Bulk JSON operations \u2014 export your dataset to share with teammates or version-control it, and import JSON files to bulk-load test cases from external sources.",
				side: "bottom",
				align: "center",
			},
			autoClickSelector: '[data-tutorial="dataset-tab-export-import"]',
			waitForElement: true,
			nextEvent: {
				event: "tutorialCloseDatasetModal",
			},
		},

		// ── 9. Runs tab ────────────────────────────────────────────────
		{
			element: '[data-tutorial="runs-tab"]',
			popover: {
				title: "Runs Tab",
				description:
					"The Runs tab shows all evaluation runs. Each run executes every test case in a dataset against a workflow and scores the results across four pillars. Let\u2019s create one.",
				side: "bottom",
				align: "center",
			},
			nextClickSelector: '[data-tutorial="runs-tab"]',
		},

		// ── 10. New Run button → open the modal ─────────────────────────
		{
			element: '[data-tutorial="new-run-btn"]',
			popover: {
				title: "Create a New Run",
				description:
					"Let\u2019s walk through creating an evaluation run. We\u2019ll open the New Run dialog, name it, configure settings, and start the evaluation.",
				side: "bottom",
				align: "end",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialOpenNewRunModal",
			},
		},

		// ── 11. New Run overview (auto-fill fields) ────────────────────
		{
			element: '[data-tutorial="new-run-modal"]',
			popover: {
				title: "New Evaluation Run",
				description:
					"The General tab lets you name the run, select a workflow, and choose a dataset. We\u2019ve filled these in for you \u2014 the run is called \u201CTutorial Baseline Run\u201D targeting the Tutorial Workflow and its demo dataset.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialFillNewRunForm",
				detail: { name: "Tutorial Baseline Run" },
			},
		},

		// ── 12. Scoring configuration ───────────────────────────────────
		{
			element: '[data-tutorial="new-run-tab-scoring-judge"]',
			popover: {
				title: "Scoring Configuration",
				description:
					"The Evaluations tab controls how runs are scored. Configure the four pillar weights (Cost, Quality, Reliability, Latency) \u2014 they must sum to 1.0. Choose a quality judge provider, select the evaluations model, and set the judge output policy.",
				side: "bottom",
				align: "center",
			},
			autoClickSelector: '[data-tutorial="new-run-tab-scoring-judge"]',
			waitForElement: true,
		},


		// ── 13. Start Evaluation button ─────────────────────────────────
		{
			element: '[data-tutorial="new-run-submit-btn"]',
			popover: {
				title: "Start the Evaluation",
				description:
					"Everything\u2019s configured \u2014 let\u2019s start! This will run each test case through the workflow and score the results across all four pillars.",
				side: "top",
				align: "end",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			nextEvent: {
				event: "tutorialSubmitNewRun",
			},
		},

		// ── 14. Run in progress — wait for completion, then open details ─
		{
			element: '[data-tutorial="eval-run-first"]',
			popover: {
				title: "Evaluation Running",
				description:
					"Your run is now live! Each test case is being executed against the workflow and scored across four pillars \u2014 Quality, Reliability, Latency, and Cost. Once complete, click Next to view the results.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
			completionSelector: '[data-tutorial-run-status="completed"], [data-tutorial-run-status="completed_with_failures"]',
			nextEvent: {
				event: "tutorialOpenEvalRun",
			},
		},

		// ── 15. Score cards ─────────────────────────────────────────────
		{
			element: '[data-tutorial="eval-score-cards"]',
			popover: {
				title: "Pillar Scores",
				description:
					"Five score cards summarise performance: Composite (overall), Quality (LLM judge), Reliability (success rate), Latency (speed), and Cost (token usage). Scores above 80 are green, 60\u201379 amber, below 60 red.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
		},

		// ── 16. Details sub-tab ─────────────────────────────────────────
		{
			element: '[data-tutorial="eval-details-section"]',
			popover: {
				title: "Per-Case Results",
				description:
					"The Details tab lists each test case with individual pillar scores. Click any row to see the full execution output, judge reasoning, cost breakdown, latency metrics, and guardrail violations.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
		},

		// ── 17. Test case drill-through ─────────────────────────────────
		{
			element: '[data-tutorial="eval-result-first"]',
			popover: {
				title: "Drill Into a Test Case",
				description:
					"Let\u2019s click the first result row to see the detail panel. This shows the full input/output, the judge\u2019s reasoning for each pillar score, and a cost/latency breakdown.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialClickResultRow",
			},
		},

		// ── 18. Test case input/output ──────────────────────────────────
		{
			element: '[data-tutorial="result-test-case"]',
			popover: {
				title: "Test Case Input & Expected Output",
				description:
					"This panel shows the original test case: the input that was sent to the workflow and the expected output it should produce. The evaluator compares the actual response against these values.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
		},

		// ── 19. Execution output ────────────────────────────────────────
		{
			element: '[data-tutorial="result-execution-output"]',
			popover: {
				title: "Execution Output",
				description:
					"The workflow\u2019s actual response for this test case. You can see the status, execution duration, and a link to the full execution trace viewer for deeper debugging.",
				side: "bottom",
				align: "start",
			},
			scrollCenter: true,
			waitForElement: true,
		},

		// ── 20. Quality / Judge result ──────────────────────────────────
		{
			element: '[data-tutorial="result-quality"]',
			popover: {
				title: "Quality \u2014 Judge Result",
				description:
					"The LLM judge scored this response for quality. You\u2019ll see the overall judge score, the reasoning behind it, and per-criterion breakdowns if judge criteria were defined. This is the heart of the evaluation \u2014 it tells you why the response scored the way it did.",
				side: "top",
				align: "start",
			},
			scrollCenter: true,
			waitForElement: true,
		},

		// ── 21. Cost & Latency metrics ──────────────────────────────────
		{
			element: '[data-tutorial="result-cost"]',
			popover: {
				title: "Cost & Performance Metrics",
				description:
					"Below the quality assessment you\u2019ll find Cost (token usage and dollar cost), Latency (duration, time to first token, tokens/sec), and Reliability (success rate, node counts). These metrics help you balance quality against efficiency.",
				side: "top",
				align: "start",
			},
			pointerPlacement: "top-center",
			scrollCenter: true,
			waitForElement: true,
		},

		// ── 22. Recommendations tab ─────────────────────────────────────
		{
			element: '[data-tutorial="eval-recommendations-tab"]',
			popover: {
				title: "Recommendations",
				description:
					"The Recommendations tab provides AI-generated suggestions for improving your workflow based on the evaluation results. Let\u2019s take a look.",
				side: "bottom",
				align: "center",
			},
			nextClickSelector: '[data-tutorial="eval-recommendations-tab"]',
		},

		// ── 23. Recommendations content (skip if no recommendations) ───
		{
			element: '[data-tutorial="eval-recommendations-section"]',
			skipIfNotFound: '[data-tutorial="prompt-rec-card"]',
			popover: {
				title: "Review & Apply",
				description:
					"Each recommendation shows a title, rationale, risk tier, and a proposed change. For prompt improvements, you\u2019ll see a side-by-side diff editor before applying. You can also dismiss recommendations you don\u2019t want.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
		},

		// ── 24. Highlight the prompt recommendation card ────────────────
		{
			element: '[data-tutorial="prompt-rec-card"]',
			skipIfNotFound: '[data-tutorial="prompt-rec-card"]',
			popover: {
				title: "Prompt Improvement",
				description:
					"This recommendation suggests an improved system prompt for the agent node. It includes the rationale, risk tier, and a Review & Apply button that opens a side-by-side diff editor. Let\u2019s open it.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialApplyRecommendation",
			},
		},

		// ── 25. Diff editor walkthrough ─────────────────────────────────
		{
			element: '[data-tutorial="prompt-diff-editor"]',
			skipIfNotFound: '[data-tutorial="prompt-diff-editor"]',
			popover: {
				title: "Prompt Diff Editor",
				description:
					"The left side shows the current prompt, the right side shows the AI\u2019s proposed improvement. Added lines are highlighted in green, removed lines in red. You can click Edit to modify the proposed prompt before applying.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
		},

		// ── 26. Apply the change ────────────────────────────────────────
		{
			element: '[data-tutorial="prompt-diff-apply-btn"]',
			skipIfNotFound: '[data-tutorial="prompt-diff-apply-btn"]',
			popover: {
				title: "Apply the Change",
				description:
					"Once you\u2019re happy with the proposed prompt, click Apply Change to update the workflow. This saves the new prompt directly to the agent node.",
				side: "top",
				align: "end",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			nextEvent: {
				event: "tutorialApplyDiffChange",
			},
		},

		// ── 27. Rerun button ────────────────────────────────────────────
		{
			element: '[data-tutorial="eval-rerun-btn"]',
			skipIfNotFound: '[data-tutorial="eval-rerun-btn"]',
			popover: {
				title: "Rerun After Improvements",
				description:
					"After applying the recommendation, let\u2019s rerun the evaluation with the improved prompt. This creates a second result set we can compare against the baseline to measure whether the changes helped.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialTriggerRerun",
			},
		},

		// ── 28. Back to runs list — wait for rerun, then open details ───
		{
			element: '[data-tutorial="eval-run-first"]',
			popover: {
				title: "Rerun In Progress",
				description:
					"The rerun has been launched! We\u2019ll wait for it to complete. Once done, click Next to open the results and compare against the baseline.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
			completionSelector: '[data-tutorial-run-status="completed"], [data-tutorial-run-status="completed_with_failures"]',
			nextEvent: {
				event: "tutorialOpenEvalRun",
			},
		},

		// ── 29. Compare tab ─────────────────────────────────────────────
		{
			element: '[data-tutorial="eval-compare-tab"]',
			popover: {
				title: "Compare Runs",
				description:
					"The Compare tab lets you A/B test two runs side by side. Pick a peer run and see per-pillar deltas, a winner badge, and colour-coded improvements or regressions. Let\u2019s compare our two runs.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="eval-compare-tab"]',
		},

		// ── 30. Compare run picker ──────────────────────────────────────
		{
			element: '[data-tutorial="compare-run-picker"]',
			popover: {
				title: "Select a Run to Compare",
				description:
					"Select our baseline run from the list. The comparison will show score deltas for each pillar \u2014 green means improvement, red means regression.",
				side: "bottom",
				align: "start",
			},
			waitForElement: true,
			nextEvent: {
				event: "tutorialSelectComparePeer",
			},
		},

		// ── 31. Compare results ─────────────────────────────────────────
		{
			element: '[data-tutorial="compare-results"]',
			popover: {
				title: "A/B Comparison",
				description:
					"The table shows each pillar\u2019s score for both runs, the delta percentage, and which run won. Green arrows mean improvement, red means regression. Use this to validate that your changes moved scores in the right direction.",
				side: "top",
				align: "center",
			},
			pointerPlacement: "top-center",
			waitForElement: true,
			nextEvent: {
				event: "tutorialBackToRunsList",
			},
		},

		// ── 32. Settings tab ────────────────────────────────────────────
		{
			element: '[data-tutorial="eval-settings-tab"]',
			popover: {
				title: "Evaluation Settings",
				description:
					"The Settings tab lets you configure global defaults and per-workflow auto-evaluation triggers. Let\u2019s take a look at both sub-tabs.",
				side: "bottom",
				align: "center",
			},
			waitForElement: true,
			nextClickSelector: '[data-tutorial="eval-settings-tab"]',
		},

		// ── 33. Settings — General Defaults ─────────────────────────────
		{
			element: '[data-tutorial="settings-general-tab"]',
			popover: {
				title: "General Defaults",
				description:
					"The General Defaults tab controls the baseline configuration for all new evaluation runs: default pillar weights, the judge model, output policy, and concurrency limits. Changes here apply to new runs unless overridden.",
				side: "right",
				align: "start",
			},
			pointerPlacement: "right-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="settings-general-tab"]',
		},

		// ── 34. Settings — Auto-Evaluation ──────────────────────────────
		{
			element: '[data-tutorial="settings-auto-eval-tab"]',
			popover: {
				title: "Auto-Evaluation",
				description:
					"The Auto-Evaluation tab lets you set up automatic evaluation triggers per workflow. When enabled, evaluations run automatically whenever you publish or modify a workflow \u2014 catching regressions before they reach production.",
				side: "right",
				align: "start",
			},
			pointerPlacement: "right-center",
			waitForElement: true,
			autoClickSelector: '[data-tutorial="settings-auto-eval-tab"]',
		},

		// ── 35. Select a workflow for auto-eval ─────────────────────────
		{
			element: '[data-tutorial="auto-eval-workflow-selector"]',
			popover: {
				title: "Select a Workflow",
				description:
					"Choose a workflow to configure automatic evaluations for. Each workflow can have its own triggers, dataset, and scoring settings. Let\u2019s select the Tutorial Workflow.",
				side: "right",
				align: "start",
			},
			pointerPlacement: "right-center",
			waitForElement: true,
			nextEvent: {
				event: "tutorialSelectAutoEvalWorkflow",
			},
		},

		// ── 36. Auto-eval config form ───────────────────────────────────
		{
			element: '[data-tutorial="auto-eval-config"]',
			popover: {
				title: "Workflow Auto-Eval Settings",
				description:
					"Once a workflow is selected, you can enable auto-evaluation, choose triggers (on publish or modify), set a default dataset, configure pillar weights, and pick the judge model. These settings run evaluations automatically so regressions are caught before reaching production.",
				side: "top",
				align: "end",
			},
			pointerPlacement: "top-right",
			waitForElement: true,
		},

		// ── 37. Completion popover ──────────────────────────────────────
		{
			element: '[data-tutorial="datasets-tab"]',
			popover: {
				title: "Tutorial Complete!",
				description:
					"You\u2019ve explored the full evaluation cycle: creating datasets with test cases, configuring and launching runs, reviewing pillar scores and per-case results, applying AI recommendations, rerunning to measure improvements, comparing runs side by side, and configuring auto-evaluation settings.",
				side: "bottom",
				align: "center",
			},
			pointerTarget: ".__no-pointer__",
			autoClickSelector: '[data-tutorial="datasets-tab"]',
		},
	],
};
