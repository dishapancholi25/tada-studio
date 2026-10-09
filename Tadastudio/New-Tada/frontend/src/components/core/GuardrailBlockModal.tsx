"use client";

import { useRef } from "react";
import { useFocusTrap } from "@/hooks/useAccessibility";
import type { GuardrailViolationEvent } from "@/hooks/useExecutionWebSocket";
import ViolationFeedbackControl from "./ViolationFeedbackControl";

interface GuardrailBlockModalProps {
	violation: GuardrailViolationEvent | null;
	onEndExecution: () => void;
}

export default function GuardrailBlockModal({
	violation,
	onEndExecution,
}: GuardrailBlockModalProps) {
	const focusTrapRef = useFocusTrap<HTMLDivElement>(violation !== null);

	if (!violation) return null;

	return (
		<div className="fixed inset-0 bg-black/50 z-[9999] flex items-center justify-center backdrop-blur-sm">
			<div
				ref={focusTrapRef}
				role="alertdialog"
				aria-modal="true"
				aria-labelledby="guardrail-block-title"
				className="bg-white border border-red-300 rounded-xl p-7 w-[420px] max-w-[90vw] shadow-xl"
			>
				{/* Header */}
				<div className="flex items-center gap-2.5 mb-4">
					<span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold capitalize tracking-wide bg-red-50 border border-red-300 text-red-700">
						Block
					</span>
					<h2
						id="guardrail-block-title"
						className="text-base font-semibold text-slate-900"
					>
						Execution Paused — Policy Violation
					</h2>
				</div>

				{/* Policy name */}
				<p className="text-sm text-slate-600 mb-3">
					Policy: {violation.policy_name ?? "Compulsory Policy"}
				</p>

				{/* Rule box */}
				<div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
					<p className="text-xs text-slate-500 mb-1">
						Rule triggered
					</p>
					<p className="text-sm text-slate-900 font-medium">
						{violation.rule_name}
					</p>
				</div>

				{/* Message */}
				<p className="text-sm text-slate-600 mb-5 leading-relaxed">
					This execution has been stopped because the input contains content
					that violates a mandatory safety policy. You cannot override this
					block.
				</p>

				{/* Feedback row */}
				<div className="flex items-center justify-between mb-5">
					<span className="text-xs text-slate-500">
						Was this a legitimate block?
					</span>
					<ViolationFeedbackControl
						violationId={violation.violation_db_id}
						size="sm"
					/>
				</div>

				{/* Actions */}
				<div className="flex justify-end">
					<button
						onClick={onEndExecution}
						className="bg-red-50 border border-red-300 text-red-700 rounded-lg px-5 py-2 text-sm font-medium hover:bg-red-100 hover:border-red-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400/45"
					>
						End Execution
					</button>
				</div>
			</div>
		</div>
	);
}
