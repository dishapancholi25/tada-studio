"use client";

import type { GuardrailPolicy, PolicyTestResult } from "@/types/guardrail-policies";
import {
	AlertTriangle,
	CheckCircle,
	FlaskConical,
	Loader,
	XCircle,
	Zap,
} from "lucide-react";
import { useState } from "react";
import * as guardrailsApi from "@/lib/guardrails-api";

interface PolicyTestSandboxProps {
	policy: GuardrailPolicy;
}

export default function PolicyTestSandbox({ policy }: PolicyTestSandboxProps) {
	const [sampleInput, setSampleInput] = useState("");
	const [sampleOutput, setSampleOutput] = useState("");
	const [includeBehavioral, setIncludeBehavioral] = useState(true);
	const [running, setRunning] = useState(false);
	const [result, setResult] = useState<PolicyTestResult | null>(null);
	const [error, setError] = useState<string | null>(null);

	const handleRun = async () => {
		if (!sampleInput && !sampleOutput) {
			setError("Provide at least one of: sample input or sample output.");
			return;
		}
		setRunning(true);
		setResult(null);
		setError(null);
		try {
			const resp = await guardrailsApi.testPolicy(policy.id, {
				sample_input: sampleInput || undefined,
				sample_output: sampleOutput || undefined,
				include_behavioral: includeBehavioral,
			});
			setResult(resp);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Test failed");
		} finally {
			setRunning(false);
		}
	};

	return (
		<div className="flex flex-col gap-5">
			{/* Header */}
			<div className="flex items-center gap-2 text-slate-600">
				<FlaskConical className="w-4 h-4" />
				<span className="text-sm">
					Test policy config against sample content without affecting executions.
				</span>
			</div>

			{/* Inputs */}
			<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
				<div>
					<label className="block text-xs text-slate-500 mb-1.5">
						Sample Input
					</label>
					<textarea
						value={sampleInput}
						onChange={(e) => setSampleInput(e.target.value)}
						placeholder="Paste sample user input to check..."
						rows={6}
						className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder-white/30 resize-none"
					/>
				</div>
				<div>
					<label className="block text-xs text-slate-500 mb-1.5">
						Sample Output
					</label>
					<textarea
						value={sampleOutput}
						onChange={(e) => setSampleOutput(e.target.value)}
						placeholder="Paste sample agent output to check..."
						rows={6}
						className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 placeholder-white/30 resize-none"
					/>
				</div>
			</div>

			{/* Behavioral toggle */}
			<div className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
				<input
					type="checkbox"
					id="behavioral-toggle"
					checked={includeBehavioral}
					onChange={(e) => setIncludeBehavioral(e.target.checked)}
					className="mt-0.5"
				/>
				<div>
					<label
						htmlFor="behavioral-toggle"
						className="text-sm text-slate-700 cursor-pointer"
					>
						Include Behavioral Checks
					</label>
					<p className="text-xs text-blue-400/80 mt-0.5">
						Runs behavioral safety checks (prompt injection, jailbreak detection, etc.).
					</p>
				</div>
			</div>

			{/* Run button */}
			<button
				type="button"
				onClick={handleRun}
				disabled={running}
				className="flex items-center justify-center gap-2 w-full py-2.5 rounded-lg bg-blue-600/20 border border-blue-500/30 text-blue-300 hover:bg-blue-600/30 transition-colors disabled:opacity-50 text-sm font-medium"
			>
				{running ? (
					<Loader className="w-4 h-4 animate-spin text-orange-500" />
				) : (
					<Zap className="w-4 h-4" />
				)}
				{running ? "Running..." : "Run Test"}
			</button>

			{/* Error */}
			{error && (
				<div className="flex items-center gap-2 p-3 rounded-lg bg-red-400/10 border border-red-400/20 text-sm text-red-300">
					<AlertTriangle className="w-4 h-4 shrink-0" />
					{error}
				</div>
			)}

			{/* Results */}
			{result && (
				<div className="flex flex-col gap-3">
					{/* Summary */}
					<div
						className={`flex items-center gap-2 p-3 rounded-lg border text-sm ${
							result.total_violations === 0
								? "bg-[#0DA931]/10 border-[#0DA931]/20 text-[#0DA931]"
								: "bg-red-400/10 border-red-400/20 text-red-300"
						}`}
					>
						{result.total_violations === 0 ? (
							<CheckCircle className="w-4 h-4 shrink-0" />
						) : (
							<XCircle className="w-4 h-4 shrink-0" />
						)}
						{result.total_violations === 0
							? "All checks passed"
							: `${result.total_violations} violation${result.total_violations !== 1 ? "s" : ""} found`}
					</div>

					{/* Cost warning */}
					{result.execution_cost_warning && (
						<p className="text-xs text-yellow-400/80">
							{result.execution_cost_warning}
						</p>
					)}

					{/* Per-check results */}
					{result.results.map((r, i) => (
						<div
							key={`${r.check_type}-${i}`}
							className={`p-3 rounded-lg border ${
								r.passed
									? "border-[#0DA931]/15 bg-[#0DA931]/5"
									: "border-red-400/15 bg-red-400/5"
							}`}
						>
							<div className="flex items-center gap-2 mb-2">
								{r.passed ? (
									<CheckCircle className="w-4 h-4 text-[#0DA931]" />
								) : (
									<XCircle className="w-4 h-4 text-red-400" />
								)}
								<span className="text-sm font-medium text-slate-700 capitalize">
									{r.check_type} check
								</span>
								{r.llm_judge_called && (
									<span className="text-xs text-yellow-400/70 ml-auto">
										LLM judge used
									</span>
								)}
							</div>

							{r.violations.length > 0 && (
								<div className="space-y-1 mt-2">
									{r.violations.map((v, vi) => (
										<div
											key={vi}
											className="text-xs text-slate-600 bg-black/20 rounded p-2"
										>
											<span className="text-slate-700 font-medium">
												{String(v.rule_name ?? v.name ?? "Rule")}
											</span>
											{v.message != null && (
												<span className="text-slate-500 ml-2">
													— {String(v.message)}
												</span>
											)}
										</div>
									))}
								</div>
							)}

							{r.sanitized_content && (
								<div className="mt-2">
									<p className="text-xs text-slate-500 mb-1">
										Transformed content (passed to next step):
									</p>
									<pre className="text-xs text-slate-600 bg-black/20 rounded p-2 overflow-auto max-h-24">
										{r.sanitized_content}
									</pre>
								</div>
							)}

							{r.passed_content && !r.sanitized_content && (
								<div className="mt-2">
									<p className="text-xs text-slate-500 mb-1">
										Content passed to next step (unchanged):
									</p>
									<pre className="text-xs text-slate-600 bg-black/20 rounded p-2 overflow-auto max-h-24">
										{r.passed_content}
									</pre>
								</div>
							)}

							{r.error && (
								<p className="text-xs text-red-400 mt-1">{r.error}</p>
							)}
						</div>
					))}
				</div>
			)}
		</div>
	);
}
