"use client";

import { FileText, HelpCircle, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export type EvalHelpTopic =
	| "datasets"
	| "dataset-editor"
	| "runs"
	| "run-detail"
	| "run-details-tab"
	| "run-recommendations-tab"
	| "run-compare-tab"
	| "new-run"
	| "general-settings"
	| "auto-eval-settings";

const HELP_CONTENT: Record<EvalHelpTopic, { title: string; items: string[] }> = {
	datasets: {
		title: "Datasets",
		items: [
			"Datasets are collections of test cases used to evaluate your workflows, agents, or models.",
			"Click \"New Dataset\" to create one — choose a name, target type, and optionally select a specific target. The dataset editor opens automatically after creation.",
			"Use the filter dropdowns to narrow by ownership (all, mine, shared), target type, sharing status, specific groups, or date range.",
			"Click any dataset row to open the editor where you can add test cases manually, generate them with AI, or import from past executions.",
			"Use the Export button to download a dataset as JSON, or Import Dataset to upload one from a file — great for sharing across environments.",
			"Clone a dataset with the copy button to create an editable duplicate with all its test cases.",
		],
	},
	"dataset-editor": {
		title: "Dataset Editor",
		items: [
			"Cases tab — view, edit, or delete existing test cases in this dataset.",
			"Manual tab — add test cases one at a time by providing JSON input, expected output, tags, and judge criteria.",
			"AI tab — auto-generate test cases from a seed prompt. You can include edge cases and adversarial inputs for broader coverage.",
			"Import Executions tab — pull positively-rated execution runs as test cases. Only runs you've given a thumbs-up will appear.",
			"Export / Import tab — export this dataset's test cases as JSON, or import test cases from a previously exported file (including file attachments).",
			"Use the visibility toggle to share a dataset with specific groups or keep it private. Shared datasets are read-only for other users.",
			"Judge criteria on each case tell the evaluator what to look for (e.g. accuracy, helpfulness). Use presets for common scenarios.",
		],
	},
	runs: {
		title: "Evaluation Runs",
		items: [
			"A run executes every test case in a dataset against a target and scores the results across four pillars: Quality, Reliability, Latency, and Cost.",
			"Click \"+ New Run\" to start — pick a dataset, a target workflow, and optionally adjust pillar weights and concurrency.",
			"Runs can be triggered manually here, or automatically via Auto-Eval settings when a workflow is published or modified.",
			"Set a completed run as the Baseline for its dataset — future runs will compare against it to detect regressions.",
			"Use the rerun button to re-evaluate with the same configuration to check if issues have been resolved.",
		],
	},
	"run-detail": {
		title: "Run Details",
		items: [
			"The score cards at the top show composite and per-pillar scores. Green (80%+) is good, amber (60-79%) needs attention, red (<60%) is critical.",
			"Details tab — browse per-case results. Click a row to see the full input, output, and assessment for each pillar.",
			"Recommendations tab — AI-generated suggestions for improving your workflow based on the evaluation results.",
			"Compare tab — select another run to see a side-by-side comparison highlighting improvements and regressions.",
			"\"Set as Baseline\" pins this run as the reference point. Future runs on the same dataset will show regression indicators relative to it.",
		],
	},
	"run-details-tab": {
		title: "Per-Case Results",
		items: [
			"Each row shows one test case and its scores across Quality, Reliability, Latency, and Cost pillars.",
			"Click a row to expand a detail panel with the full input, actual output, and the judge's assessment for each pillar.",
			"The trace link opens the execution in the workflow viewer so you can inspect the full node-by-node execution path.",
			"Use the scores to identify which specific test cases are underperforming and need attention.",
		],
	},
	"run-recommendations-tab": {
		title: "Recommendations",
		items: [
			"AI-generated suggestions based on patterns found across all test case results in this run.",
			"Each recommendation includes a risk tier (low, medium, high) indicating the severity of the issue.",
			"Proposed changes describe concrete actions you can take in your workflow to improve scores.",
			"Expected impact estimates how much improvement you can expect from implementing the suggestion.",
			"Re-run the evaluation after making changes to verify the recommendations had the desired effect.",
		],
	},
	"run-compare-tab": {
		title: "Compare Runs",
		items: [
			"Select another run (typically the baseline or a previous version) to compare side-by-side.",
			"The comparison highlights per-pillar score differences, showing improvements in green and regressions in red.",
			"Use this to verify that workflow changes actually improved performance, or to catch unexpected regressions.",
			"For best results, compare runs that use the same dataset so the test cases are identical.",
		],
	},
	"new-run": {
		title: "New Evaluation Run",
		items: [
			"Use the General tab to select a dataset, workflow, environment, and concurrency. A/B comparison and external integrations are also configured here.",
			"The Evaluations tab lets you set pillar weights (must sum to 1.0), choose the evaluations model, and configure judge output policy and max output chars.",
			"Pillar weights control how Quality, Reliability, Latency, and Cost contribute to the composite score.",
			"The Evaluations Model is the LLM used for quality judging and Phoenix supplementary evaluations. Leave empty to use the default from Settings.",
			"Judge Output Policy controls which part of the workflow output is sent to the judge — final node output is recommended for most workflows.",
			"Defaults for scoring and judge settings are inherited from the General Defaults in the Settings tab.",
		],
	},
	"general-settings": {
		title: "General Defaults",
		items: [
			"These defaults pre-fill forms when creating new runs, auto-eval configs, or generating test cases.",
			"General tab — environment, concurrency limit, max dataset size, and generator model for AI test cases.",
			"Evaluations tab — default pillar weights, evaluations model, judge output policy, and max output chars.",
			"Per-run and per-workflow auto-eval settings inherit from these defaults and can override them.",
		],
	},
	"auto-eval-settings": {
		title: "Auto-Evaluation",
		items: [
			"Auto-eval automatically triggers evaluation runs when a workflow is published or modified — no manual action needed.",
			"Select a workflow, then enable auto-eval and choose trigger events (on publish, on modify, or both).",
			"General tab — configure dataset, environment, and debounce window for the automated runs.",
			"Evaluations tab — set pillar weights, evaluations model, output policy, and max output chars. These default from the General Defaults settings.",
			"The debounce window prevents multiple runs from triggering in rapid succession during frequent edits.",
			"Results appear in the Runs tab like any other run, marked with the trigger type that started them.",
		],
	},
};

export default function EvalHelpButton({
	topic,
	appearance = "dark",
}: {
	topic: EvalHelpTopic;
	/** Light: white card, dark text, Workflow Management–style header (use on light surfaces). */
	appearance?: "dark" | "light";
}) {
	const [open, setOpen] = useState(false);
	const panelRef = useRef<HTMLDivElement>(null);
	const buttonRef = useRef<HTMLButtonElement>(null);
	const [mounted, setMounted] = useState(false);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	const handleClickOutside = useCallback(
		(e: MouseEvent) => {
			if (
				panelRef.current &&
				!panelRef.current.contains(e.target as Node) &&
				buttonRef.current &&
				!buttonRef.current.contains(e.target as Node)
			) {
				setOpen(false);
			}
		},
		[],
	);

	const handleEscape = useCallback((e: KeyboardEvent) => {
		if (e.key === "Escape") setOpen(false);
	}, []);

	useEffect(() => {
		if (open) {
			document.addEventListener("mousedown", handleClickOutside);
			document.addEventListener("keydown", handleEscape);
			return () => {
				document.removeEventListener("mousedown", handleClickOutside);
				document.removeEventListener("keydown", handleEscape);
			};
		}
	}, [open, handleClickOutside, handleEscape]);

	const content = HELP_CONTENT[topic];

	const panel = open && mounted && createPortal(
		<div className="fixed inset-0 z-[9998]" aria-hidden="true">
			<div
				ref={panelRef}
				className={
					appearance === "light"
						? "fixed z-[9999] w-[22rem] rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]"
						: "fixed z-[9999] w-80 rounded-xl border border-[rgba(var(--color-primary-rgb),0.2)] bg-gradient-to-br from-[rgba(30,30,30,0.98)] via-[rgba(22,22,22,0.97)] to-[rgba(16,16,16,0.98)] backdrop-blur-xl shadow-[0_20px_50px_rgba(0,0,0,0.5),_0_0_20px_rgba(var(--color-primary-rgb),0.08)]"
				}
				style={{
					top: buttonRef.current
						? buttonRef.current.getBoundingClientRect().bottom + 8
						: 80,
					right: Math.max(
						16,
						buttonRef.current
							? window.innerWidth - buttonRef.current.getBoundingClientRect().right
							: 16,
					),
					animation: "eval-help-enter 0.2s ease-out",
				}}
			>
				{appearance === "dark" && (
					<div className="absolute top-0 left-3 right-3 h-px bg-gradient-to-r from-transparent via-[rgba(var(--color-primary-rgb),0.3)] to-transparent" />
				)}

				<div
					className={
						appearance === "light"
							? "flex items-center justify-between gap-3 border-b border-slate-200 px-4 pt-4 pb-3"
							: "flex items-center justify-between px-4 pt-3 pb-2"
					}
				>
					{appearance === "light" ? (
						<div className="flex min-w-0 items-center gap-3">
							<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
								<FileText className="h-5 w-5 text-orange-600" />
							</div>
							<h4 className="truncate text-sm font-semibold tracking-tight text-slate-900">{content.title}</h4>
						</div>
					) : (
						<h4 className="text-sm font-semibold text-white">{content.title}</h4>
					)}
					<button
						type="button"
						onClick={() => setOpen(false)}
						className={
							appearance === "light"
								? "shrink-0 rounded-[4px] p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
								: "rounded-lg p-1 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
						}
					>
						<X size={14} />
					</button>
				</div>

				<ul className={appearance === "light" ? "space-y-2.5 px-4 py-4" : "space-y-2.5 px-4 pb-4"}>
					{content.items.map((item, i) => (
						<li
							key={i}
							className={
								appearance === "light"
									? "flex gap-2 text-[13px] leading-relaxed text-slate-700"
									: "flex gap-2 text-[13px] leading-relaxed text-white/75"
							}
						>
							<span
								className={
									appearance === "light"
										? "mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500"
										: "mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[rgba(var(--color-primary-rgb),0.5)]"
								}
							/>
							<span>{item}</span>
						</li>
					))}
				</ul>
			</div>
		</div>,
		document.body,
	);

	return (
		<>
			<button
				ref={buttonRef}
				type="button"
				onClick={() => setOpen((v) => !v)}
				className={
					appearance === "light"
						? `inline-flex items-center justify-center rounded-full border p-1.5 transition-all duration-200 ${
							open
								? "border-orange-500 bg-orange-50 text-orange-700"
								: "border-slate-200 bg-white text-slate-600 hover:border-orange-400 hover:bg-white hover:text-slate-900"
						}`
						: `inline-flex items-center justify-center rounded-full border p-1.5 transition-all duration-200 ${
							open
								? "border-[rgba(var(--color-primary-rgb),0.3)] bg-[rgba(var(--color-primary-rgb),0.15)] text-[color:var(--color-primary-light)]"
								: "border-transparent text-slate-400 hover:border-[rgba(var(--color-primary-rgb),0.2)] hover:bg-[rgba(var(--color-primary-rgb),0.1)] hover:text-[color:var(--color-primary-light)]"
						}`
				}
				title="Help"
			>
				<HelpCircle className="w-4 h-4" />
			</button>
			{panel}
			{mounted &&
				createPortal(
					<style>{`
						@keyframes eval-help-enter {
							from {
								opacity: 0;
								transform: translateY(-4px) scale(0.97);
							}
							to {
								opacity: 1;
								transform: translateY(0) scale(1);
							}
						}
					`}</style>,
					document.head,
				)}
		</>
	);
}
