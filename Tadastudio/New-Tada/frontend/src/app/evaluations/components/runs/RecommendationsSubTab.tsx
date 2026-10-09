"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import * as evalApi from "@/lib/evaluation-api";
import type { EvaluationRecommendation, RecommendationPreview } from "@/lib/evaluation-api";
import PromptDiffReviewModal from "./PromptDiffReviewModal";

export default function RecommendationsSubTab({ runId, workflowId }: { runId: string; workflowId?: string | null }) {
	const [recs, setRecs] = useState<EvaluationRecommendation[]>([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [confirmTarget, setConfirmTarget] = useState<EvaluationRecommendation | null>(null);
	const [applyingId, setApplyingId] = useState<string | null>(null);

	// Prompt diff review state
	const [reviewTarget, setReviewTarget] = useState<EvaluationRecommendation | null>(null);
	const [reviewPreview, setReviewPreview] = useState<RecommendationPreview | null>(null);
	const [loadingPreview, setLoadingPreview] = useState(false);

	const load = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const list = await evalApi.getRunRecommendations(runId);
			setRecs(list);
		} catch (err: any) {
			setError(err.message ?? "Failed to load recommendations");
		} finally {
			setLoading(false);
		}
	}, [runId]);

	useEffect(() => {
		load();
	}, [load]);

	// Tutorial: open the diff review modal for the first prompt recommendation
	useEffect(() => {
		const handler = () => {
			const promptRec = recs.find((r) => r.status === "pending" && isPromptChange(r));
			if (promptRec) handleApply(promptRec);
		};
		window.addEventListener("tutorialApplyRecommendation", handler);
		return () => window.removeEventListener("tutorialApplyRecommendation", handler);
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [recs]);

	// Tutorial: apply the change from the diff review modal
	useEffect(() => {
		const handler = () => {
			if (reviewTarget && reviewPreview) {
				const proposed = String(reviewPreview.proposed_value ?? "");
				handlePromptReviewApply(proposed);
			}
		};
		window.addEventListener("tutorialApplyDiffChange", handler);
		return () => window.removeEventListener("tutorialApplyDiffChange", handler);
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [reviewTarget, reviewPreview]);

	/** Check if a recommendation involves a prompt change that can be previewed. */
	const isPromptChange = (rec: EvaluationRecommendation): boolean => {
		const pc = rec.proposed_change;
		return !!(pc?.agent_config && typeof pc.agent_config.system_prompt === "string");
	};

	/** Open the diff review modal for a prompt-edit recommendation. */
	const openPromptReview = async (rec: EvaluationRecommendation) => {
		setLoadingPreview(true);
		setError(null);
		try {
			const preview = await evalApi.previewRecommendation(rec.run_id, rec.id);
			setReviewPreview(preview);
			setReviewTarget(rec);
		} catch (err: any) {
			setError(err.message ?? "Failed to load preview");
		} finally {
			setLoadingPreview(false);
		}
	};

	const handleApply = async (rec: EvaluationRecommendation) => {
		// For prompt changes, always show the diff review modal first
		if (isPromptChange(rec)) {
			await openPromptReview(rec);
			return;
		}
		if (rec.risk_tier === "medium" || rec.risk_tier === "high" || rec.risk_tier === "critical") {
			setConfirmTarget(rec);
			return;
		}
		await doApply(rec);
	};

	const doApply = async (
		rec: EvaluationRecommendation,
		fromConfirmModal = false,
		proposedChangeOverride?: Record<string, any> | null,
	) => {
		setApplyingId(rec.id);
		try {
			const result = await evalApi.applyRecommendation(rec.run_id, rec.id, {
				confirmed: true,
				impact_acknowledged: fromConfirmModal,
				proposed_change_override: proposedChangeOverride ?? undefined,
			});
			setConfirmTarget(null);
			setReviewTarget(null);
			setReviewPreview(null);
			let applyError: string | null = null;
			if (result.status === "error") {
				applyError = result.detail ?? result.reason ?? "Failed to apply recommendation";
			} else if (result.status === "manual_apply_required") {
				applyError = "This recommendation requires manual application in the workflow editor.";
			} else if (result.status === "blocked") {
				applyError =
					result.reason === "workflow_is_executing"
						? "Cannot apply while the workflow is executing. Please wait for it to finish."
						: `Blocked: ${result.reason ?? "unknown reason"}`;
			} else if (result.status === "confirmation_required" || result.status === "impact_acknowledgement_required") {
				applyError = "Additional confirmation is required to apply this recommendation.";
			}
			await load();
			if (applyError) {
				setError(applyError);
			}
		} catch (err: any) {
			setError(err.message ?? "Failed to apply recommendation");
		} finally {
			setApplyingId(null);
		}
	};

	/** Called from the diff review modal when user confirms. */
	const handlePromptReviewApply = async (editedPrompt: string) => {
		if (!reviewTarget) return;
		const originalProposed = reviewTarget.proposed_change?.agent_config?.system_prompt;
		const wasEdited = editedPrompt !== originalProposed;
		const override = wasEdited
			? { agent_config: { ...reviewTarget.proposed_change?.agent_config, system_prompt: editedPrompt } }
			: undefined;
		const needsImpactAck = reviewTarget.risk_tier === "medium" || reviewTarget.risk_tier === "high" || reviewTarget.risk_tier === "critical";
		await doApply(reviewTarget, needsImpactAck, override);
	};

	const handleDismiss = async (rec: EvaluationRecommendation) => {
		try {
			await evalApi.dismissRecommendation(rec.run_id, rec.id);
			await load();
		} catch (err: any) {
			setError(err.message ?? "Failed to dismiss recommendation");
		}
	};

	const riskColors: Record<string, string> = {
		low: "border-emerald-400/45 bg-emerald-400/12 text-emerald-600",
		medium: "border-amber-400/45 bg-amber-400/12 text-amber-300",
		high: "border-orange-400/45 bg-orange-400/12 text-orange-300",
		critical: "border-red-400/45 bg-red-400/12 text-red-300",
	};

	return (
		<div className="space-y-4">
			{error && <p className="text-sm text-red-400">{error}</p>}

			{loading ? (
				<p className="py-10 text-center text-sm text-slate-500">Loading recommendations…</p>
			) : recs.length === 0 ? (
				<p className="py-10 text-center text-sm text-slate-500">No recommendations for this run.</p>
			) : (
				<div className="space-y-3">
					{recs.map((rec) => {
						const isPrompt = isPromptChange(rec);
						return (
						<div
							key={rec.id}
							data-tutorial={isPrompt && rec.status === "pending" ? "prompt-rec-card" : undefined}
							className="rounded-xl border border-slate-200 bg-slate-50 p-4"
						>
							<div className="mb-2 flex items-center gap-3">
								<h3 className="text-sm font-semibold text-slate-900">{rec.title}</h3>
								<span
									className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${riskColors[rec.risk_tier] ?? "border-[color:var(--color-border)]/45 bg-[color:var(--color-surface)]/40 text-[color:var(--color-text-muted)]"}`}
								>
									{rec.risk_tier}
								</span>
								<span className="text-xs text-slate-500">{rec.recommendation_type}</span>
								<span className="text-xs text-slate-500">Status: {rec.status}</span>
							</div>
							{rec.rationale && (
								<p className="mb-3 text-sm text-slate-600">{rec.rationale}</p>
							)}
							{rec.status === "pending" && (
								<div className="flex gap-2">
									<button
										type="button"
										data-tutorial={isPrompt ? "apply-prompt-rec-btn" : "apply-rec-btn"}
										onClick={() => handleApply(rec)}
										disabled={applyingId === rec.id || loadingPreview}
										className="rounded-xl bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] px-3 py-1.5 text-xs font-semibold text-[color:var(--button-primary-text)] shadow-[0_8px_20px_rgba(var(--color-primary-rgb),0.25)] transition-all hover:from-[rgba(var(--color-primary-rgb),0.9)] hover:to-[rgba(var(--color-primary-rgb),0.7)] hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40 disabled:pointer-events-none"
									>
										{applyingId === rec.id ? "Applying\u2026" : loadingPreview ? "Loading\u2026" : isPrompt ? "Review & Apply" : "Apply"}
									</button>
									<button
										type="button"
										onClick={() => handleDismiss(rec)}
										disabled={applyingId === rec.id}
										className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-3 py-1.5 text-xs font-medium text-slate-700 transition-all hover:border-[rgba(var(--color-primary-rgb),0.50)] hover:bg-[color:var(--color-surface)]/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)] disabled:opacity-40 disabled:pointer-events-none"
									>
										Dismiss
									</button>
								</div>
							)}
							{rec.status === "applied" && rec.applied_version != null && workflowId && (
								<div className="mt-2 flex items-center gap-1.5 text-xs text-emerald-400/80">
									<span>Applied to</span>
									<a
										href={`/workflow/${encodeURIComponent(workflowId)}${rec.applied_graph_definition_id ? `?version=${rec.applied_version}&graph_definition_id=${rec.applied_graph_definition_id}` : ""}`}
										target="_blank"
										rel="noopener noreferrer"
										className="inline-flex items-center gap-1 font-medium underline decoration-emerald-400/30 hover:decoration-emerald-400 transition"
									>
										v{rec.applied_version}
										<ExternalLink size={11} />
									</a>
								</div>
							)}
						</div>
					); })}
				</div>
			)}

			{/* Confirm modal for medium/high/critical risk */}
			{confirmTarget && (
				<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
					<div className="w-full max-w-md rounded-2xl border border-[color:var(--color-border)]/70 bg-gradient-to-br from-[rgba(28,28,28,0.95)] via-[rgba(20,20,20,0.95)] to-[rgba(14,14,14,0.98)] p-6 shadow-2xl">
						<h3 className="mb-2 text-base font-semibold text-slate-900">
							Confirm Apply — {confirmTarget.risk_tier.toUpperCase()} Risk
						</h3>
						<p className="mb-1 text-sm text-slate-700">{confirmTarget.title}</p>
						{confirmTarget.rationale && (
							<p className="mb-4 text-sm text-slate-500">{confirmTarget.rationale}</p>
						)}
						<p className="mb-4 text-xs text-amber-400">
							This recommendation has a <strong>{confirmTarget.risk_tier}</strong> risk tier.
							Applying it may have significant impact on your workflow.
						</p>
						<div className="flex justify-end gap-2">
							<button
								type="button"
								onClick={() => setConfirmTarget(null)}
								className="rounded-xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 px-4 py-2 text-sm text-slate-700 transition-all hover:border-[rgba(var(--color-primary-rgb),0.50)] hover:bg-[color:var(--color-surface)]/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={() => doApply(confirmTarget, true)}
								className="rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-2 text-sm font-semibold text-red-400 transition-all hover:bg-red-500/20 hover:border-red-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/45"
							>
								Confirm &amp; Apply
							</button>
						</div>
					</div>
				</div>
			)}

			{/* Prompt diff review modal */}
			{reviewTarget && reviewPreview && reviewPreview.field === "system_prompt" && (
				<PromptDiffReviewModal
					currentValue={String(reviewPreview.current_value ?? "")}
					proposedValue={String(reviewPreview.proposed_value ?? "")}
					nodeName={reviewPreview.node_name ?? reviewPreview.target_node_id ?? "Node"}
					onApply={handlePromptReviewApply}
					onCancel={() => { setReviewTarget(null); setReviewPreview(null); }}
					applying={applyingId === reviewTarget.id}
				/>
			)}
		</div>
	);
}
