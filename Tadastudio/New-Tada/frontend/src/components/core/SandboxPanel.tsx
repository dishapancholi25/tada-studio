"use client";

import type {
	SandboxCheckResult,
	SandboxPreviewResponse,
	SandboxTestResponse,
} from "@/types/guardrail-policies";
import * as guardrailsApi from "@/lib/guardrails-api";
import { AlertTriangle, X, Zap } from "lucide-react";
import { useEffect, useState } from "react";

/** Normalize legacy { results: [...] } format to { input_result, output_result } */
function normalizeTestResponse(
	raw: Record<string, unknown>,
	fallbackMs: number,
): SandboxTestResponse {
	// New sandbox handler format — already has input_result
	if (raw.input_result) {
		return {
			success: Boolean(raw.success),
			input_result: raw.input_result as SandboxCheckResult,
			output_result: (raw.output_result as SandboxCheckResult | null) ?? null,
			static_only: Boolean(raw.static_only),
			llm_call_made: Boolean(raw.llm_call_made),
			evaluation_ms: (raw.evaluation_ms as number) ?? fallbackMs,
		};
	}

	// Legacy handler format — { results: [...], total_violations }
	const results = (raw.results ?? []) as Array<Record<string, unknown>>;
	const inputChecks = results.filter((r) => r.check_type === "input" || r.check_type === "behavioral");
	const outputChecks = results.filter((r) => r.check_type === "output");

	const mergeChecks = (checks: Array<Record<string, unknown>>): SandboxCheckResult => {
		const violations = checks.flatMap(
			(c) => (c.violations as Array<Record<string, unknown>>) ?? [],
		);
		const passed = checks.every((c) => c.passed !== false);
		const actions = checks.map((c) => (c.action_taken as string) ?? "none");
		const actionPriority: Record<string, number> = { none: 0, warned: 1, transformed: 2, redacted: 3, blocked: 4 };
		const topAction = actions.reduce((a, b) =>
			(actionPriority[b] ?? 0) > (actionPriority[a] ?? 0) ? b : a, "none");
		const sanitized = checks.find((c) => c.sanitized_content)?.sanitized_content as string | null ?? null;
		return {
			passed,
			violations: violations as unknown as SandboxCheckResult["violations"],
			action_taken: topAction,
			sanitized_content: sanitized,
		};
	};

	const llmCalled = results.some((r) => r.llm_judge_called === true);

	return {
		success: Boolean(raw.success),
		input_result: inputChecks.length > 0 ? mergeChecks(inputChecks) : { passed: true, violations: [], action_taken: "none", sanitized_content: null },
		output_result: outputChecks.length > 0 ? mergeChecks(outputChecks) : null,
		static_only: !llmCalled,
		llm_call_made: llmCalled,
		evaluation_ms: (raw.evaluation_ms as number) ?? fallbackMs,
	};
}

interface SandboxPanelProps {
	policyId: string;
	isOpen: boolean;
	onClose: () => void;
}

export default function SandboxPanel({
	policyId,
	isOpen,
	onClose,
}: SandboxPanelProps) {
	const [preview, setPreview] = useState<SandboxPreviewResponse | null>(null);
	const [inputText, setInputText] = useState("");
	const [outputText, setOutputText] = useState("");
	const [result, setResult] = useState<SandboxTestResponse | null>(null);
	const [loading, setLoading] = useState(false);
	const [previewLoading, setPreviewLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [view, setView] = useState<"input" | "result">("input");

	useEffect(() => {
		if (!isOpen) return;
		setPreviewLoading(true);
		setError(null);
		guardrailsApi
			.getSandboxPreview(policyId)
			.then(setPreview)
			.catch((err) => {
				console.error("Failed to load sandbox preview:", err);
				setError("Failed to load preview");
			})
			.finally(() => setPreviewLoading(false));
	}, [isOpen, policyId]);

	const handleRunTest = async () => {
		setLoading(true);
		setError(null);
		const startMs = performance.now();
		try {
			const resp = await guardrailsApi.runSandboxTest(policyId, {
				input_text: inputText,
				output_text: outputText || undefined,
			});
			// Normalize: the legacy backend handler returns { results: [...] }
			// while the sandbox handler returns { input_result, output_result, ... }.
			const normalized = normalizeTestResponse(
				resp as unknown as Record<string, unknown>,
				performance.now() - startMs,
			);
			setResult(normalized);
			setView("result");
		} catch (err) {
			console.error("Sandbox test failed:", err);
			setError(err instanceof Error ? err.message : "Test failed");
		} finally {
			setLoading(false);
		}
	};

	const handleTestAgain = () => {
		setView("input");
		setResult(null);
		setError(null);
	};

	if (!isOpen) return null;

	return (
		<div className="fixed inset-y-0 right-0 z-[110] flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
			<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
			{/* Header — stays above scroll; must stack above app chrome (parent modal uses z-[100]) */}
			<div className="flex shrink-0 items-start justify-between gap-3 border-b border-slate-200 bg-white px-5 py-4 shadow-[0_6px_16px_rgba(15,23,42,0.06)]">
				<div className="flex min-w-0 items-center gap-3">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100 text-orange-600">
						<Zap className="h-5 w-5" aria-hidden />
					</div>
					<div className="min-w-0">
						<h3 className="text-sm font-semibold text-slate-900">Test Policy</h3>
						<p className="mt-0.5 text-xs text-slate-500">
							Sample input/output against this policy
						</p>
					</div>
				</div>
				<button
					type="button"
					onClick={onClose}
					aria-label="Close sandbox"
					className="shrink-0 rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900"
				>
					<X className="h-5 w-5" />
				</button>
			</div>

			<div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
				{previewLoading ? (
					<div className="flex items-center justify-center py-10">
						<div className="animate-spin rounded-full h-6 w-6 border-2 border-slate-200 border-t-orange-500" />
					</div>
				) : view === "input" ? (
					<>
						{/* LLM warning banner */}
						{preview?.will_use_llm && (
							<div className="border border-amber-300 bg-white rounded-lg px-3 py-2 text-xs text-amber-700 flex items-start gap-2">
								<AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
								<span>
									Some checks (behavioral, custom filters, LLM Guard) may make LLM API calls during this test.
								</span>
							</div>
						)}

						{error && (
							<div className="border border-red-300 bg-white rounded-lg px-3 py-2 text-xs text-red-600">
								{error}
							</div>
						)}

						{/* Sample Input */}
						<div>
							<label className="block text-xs text-slate-600 mb-1.5">
								Sample Input
							</label>
							<textarea
								value={inputText}
								onChange={(e) => setInputText(e.target.value)}
								rows={5}
								placeholder="Enter text to test against this policy..."
								className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15 resize-none"
							/>
						</div>

						{/* Sample Output */}
						<div>
							<label className="block text-xs text-slate-600 mb-1.5">
								Sample Output{" "}
								<span className="text-slate-400">(optional)</span>
							</label>
							<textarea
								value={outputText}
								onChange={(e) => setOutputText(e.target.value)}
								rows={3}
								placeholder="Leave blank to test input only..."
								className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15 resize-none"
							/>
						</div>

						{/* Run Test button */}
						<button
							type="button"
							onClick={handleRunTest}
							disabled={!inputText.trim() || loading}
							className="w-full rounded-lg border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:border-orange-600 hover:bg-orange-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
						>
							{loading ? "Running..." : "Run Test"}
						</button>
					</>
				) : (
					result && (
						<>
							{error && (
								<div className="border border-red-300 bg-white rounded-lg px-3 py-2 text-xs text-red-600">
									{error}
								</div>
							)}

							{/* Input check results */}
							<div className="space-y-3">
								<h4 className="text-xs font-medium text-slate-500 capitalize tracking-wider">
									Input Check
								</h4>
								<CheckResultDisplay result={result.input_result} />
							</div>

							{/* Output check results */}
							{result.output_result && (
								<div className="space-y-3 mt-4">
									<h4 className="text-xs font-medium text-slate-500 capitalize tracking-wider">
										Output Check
									</h4>
									<CheckResultDisplay
										result={result.output_result}
									/>
								</div>
							)}

							{/* Test Again button */}
							<button
								type="button"
								onClick={handleTestAgain}
								className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:border-orange-400 hover:text-slate-900 transition-colors"
							>
								Test Again
							</button>

							{/* Evaluation time */}
							<p className="text-[10px] text-slate-400 text-center">
								Evaluated in {(result.evaluation_ms ?? 0).toFixed(0)}ms
								{result.llm_call_made && " (includes LLM call)"}
							</p>
						</>
					)
				)}
			</div>
		</div>
	);
}

function CheckResultDisplay({ result }: { result: SandboxCheckResult }) {
	const hasViolations = result.violations.length > 0;

	return (
		<div className="space-y-2">
			{/* Pass/Fail badge */}
			{hasViolations ? (
				<div className="inline-flex items-center gap-1.5 rounded-lg bg-white border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600">
					<span>&#10007;</span> {result.violations.length} Violation{result.violations.length !== 1 ? "s" : ""} Detected
				</div>
			) : (
				<div className="inline-flex items-center gap-1.5 rounded-lg bg-white border border-[#0DA931] px-3 py-1.5 text-xs font-medium text-[#0DA931]">
					<span>&#10003;</span> No Violations
				</div>
			)}

			{/* Triggered rules table */}
			{result.violations.length > 0 && (
				<div className="rounded-lg border border-slate-200 overflow-hidden">
					<table className="w-full text-xs">
						<thead>
							<tr className="border-b border-slate-200 text-slate-500">
								<th className="py-2 px-3 text-left font-medium">
									Rule
								</th>
								<th className="py-2 px-3 text-left font-medium">
									Severity
								</th>
								<th className="py-2 px-3 text-left font-medium">
									Action
								</th>
							</tr>
						</thead>
						<tbody>
							{result.violations.map((v, i) => (
								<tr
									key={`${v.rule_name}-${i}`}
									className="border-b border-slate-100"
								>
									<td className="py-2 px-3 text-slate-700">
										{v.rule_name}
									</td>
									<td
										className={`py-2 px-3 ${
											v.severity === "block"
												? "text-red-600"
												: v.severity === "warn"
													? "text-orange-700"
													: "text-slate-500"
										}`}
									>
										{v.severity}
									</td>
									<td className="py-2 px-3 text-slate-500">
										{v.message || "—"}
									</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}

			{/* Redacted content */}
			{result.sanitized_content && (
				<div className="mt-2">
					<p className="text-[10px] text-slate-500 mb-1">
						Redacted content:
					</p>
					<pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono bg-white rounded-lg p-3 border border-slate-200">
						{result.sanitized_content}
					</pre>
				</div>
			)}
		</div>
	);
}
