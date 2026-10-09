"use client";

import { ChevronRight, ShieldAlert, ShieldX } from "lucide-react";
import type React from "react";
import { useState } from "react";

export interface GuardrailViolationActivityProps {
	category: string;
	ruleName: string;
	message: string;
	severity: string;
	agentName?: string;
	toolName?: string;
	details?: Record<string, unknown> | null;
	enforcementMode?: string | null;
}

/** Human-readable labels for violation categories */
const CATEGORY_LABELS: Record<string, string> = {
	input: "Agent Ingress",
	output: "Agent Egress",
	behavioral: "Behavioral Check",
	tool_call: "Tool Selection",
	tool_ingress: "Tool Ingress",
	tool_egress: "Tool Egress",
	tool_result_injection: "Tool Injection Detection",
	workflow_ingress: "Workflow Ingress",
	workflow_egress: "Workflow Egress",
	resume_ingress: "Resume Ingress",
	node_ingress: "Node Ingress",
	node_egress: "Node Egress",
	prompt_injection: "Prompt Injection",
	jailbreak_attempt: "Jailbreak Attempt",
	instruction_override: "Instruction Override",
	content_filter: "Content Filter",
	token_budget: "Token Budget",
	input_length: "Input Length",
	output_length: "Output Length",
	custom_filter: "Custom Filter",
	custom_filter_error: "Filter Error",
};

/** Format a human-readable location string for a violation checkpoint */
export function formatViolationLocation(
	category: string,
	agentName?: string | null,
	toolName?: string | null,
): string {
	const checkpoint = CATEGORY_LABELS[category] || category;
	if (toolName && agentName) {
		return `${agentName} → ${toolName} (${checkpoint})`;
	}
	if (agentName) {
		return `${agentName} → ${checkpoint}`;
	}
	return checkpoint;
}

/** Format scanner metadata into human-readable lines */
function formatScannerMetadata(
	details: Record<string, unknown>,
): string[] {
	const lines: string[] = [];
	const meta =
		(details.scanner_metadata as Record<string, unknown>) ?? null;

	if (meta) {
		if (Array.isArray(meta.entity_types)) {
			const count = (meta.entity_count as number) ?? meta.entity_types.length;
			lines.push(
				`Entity types: ${(meta.entity_types as string[]).join(", ")} (${count} total)`,
			);
		}
		if (Array.isArray(meta.topics_checked)) {
			lines.push(
				`Topics checked: ${(meta.topics_checked as string[]).join(", ")}`,
			);
		}
		if (Array.isArray(meta.valid_languages)) {
			lines.push(
				`Valid languages: ${(meta.valid_languages as string[]).join(", ")}`,
			);
		}
		if (Array.isArray(meta.competitors_checked)) {
			lines.push(
				`Competitors checked: ${(meta.competitors_checked as string[]).join(", ")}`,
			);
		}
		if (Array.isArray(meta.matched_patterns)) {
			const count = (meta.match_count as number) ?? meta.matched_patterns.length;
			lines.push(
				`Matched patterns: ${(meta.matched_patterns as string[]).join(", ")} (${count} matches)`,
			);
		}
		if (meta.threshold != null) {
			lines.push(`Threshold: ${meta.threshold}`);
		}
		if (meta.limit != null) {
			lines.push(`Limit: ${meta.limit}`);
		}
	}

	// LLM judge / pattern rule details live at top level
	if (typeof details.reasoning === "string") {
		lines.push(`Reasoning: ${details.reasoning}`);
	}
	if (typeof details.summary === "string") {
		lines.push(`Summary: ${details.summary}`);
	}

	return lines;
}

export const GuardrailViolationActivity: React.FC<
	GuardrailViolationActivityProps
> = ({
	category,
	ruleName,
	message,
	severity,
	agentName,
	toolName,
	details,
	enforcementMode,
}) => {
	const [expanded, setExpanded] = useState(false);
	// In audit mode, block-severity violations are not enforced — display as amber/audit
	const isAudit = enforcementMode === "audit";
	const isBlock = severity === "block" && !isAudit;
	const locationLabel = formatViolationLocation(category, agentName, toolName);

	const Icon = isBlock ? ShieldX : ShieldAlert;
	const iconColor = isBlock ? "text-red-400" : "text-amber-400";
	const containerStyles = isBlock
		? "border-red-500/30 bg-red-500/5"
		: "border-amber-500/30 bg-amber-500/5";
	const badgeStyles = isBlock
		? "bg-red-500/20 text-red-400"
		: "bg-amber-500/20 text-amber-400";
	const messageColor = isBlock ? "text-red-400/80" : "text-amber-400/80";

	const detailLines = details ? formatScannerMetadata(details) : [];

	return (
		<div
			className={`flex flex-col rounded-lg border transition-colors ${containerStyles}`}
		>
			<button
				type="button"
				onClick={() => setExpanded(!expanded)}
				className="flex items-center gap-3 px-3 py-2 w-full text-left"
			>
				<Icon className={`h-4 w-4 flex-shrink-0 ${iconColor}`} />
				<div className="flex-1 min-w-0">
					<div className="flex items-center gap-2">
						<span className="text-sm font-medium text-[color:var(--color-text-primary)] truncate">
							{locationLabel}
						</span>
						<span
							className={`text-[0.6rem] capitalize tracking-wider px-1.5 py-0.5 rounded font-medium ${badgeStyles}`}
						>
							{isBlock
								? "blocked"
								: isAudit && severity === "block"
									? "audit"
									: "warning"}
						</span>
					</div>
					{!expanded && (
						<p className={`text-xs truncate mt-0.5 ${messageColor}`}>
							{message}
						</p>
					)}
				</div>
				<ChevronRight
					className={`h-3.5 w-3.5 flex-shrink-0 text-[color:var(--color-text-muted)] transition-transform ${expanded ? "rotate-90" : ""}`}
				/>
			</button>
			{expanded && (
				<div
					className={`border-t px-3 py-2 ${isBlock ? "border-red-500/20" : "border-amber-500/20"}`}
				>
					{ruleName && (
						<p className="text-[11px] text-[color:var(--color-text-muted)] font-mono mb-1">
							Rule: {ruleName}
						</p>
					)}
					<p
						className={`text-xs whitespace-pre-wrap break-words ${messageColor}`}
					>
						{message}
					</p>
					{detailLines.length > 0 && (
						<div className="mt-2 space-y-1">
							{detailLines.map((line) => (
								<p
									key={line}
									className="text-[11px] text-[color:var(--color-text-muted)] font-mono"
								>
									{line}
								</p>
							))}
						</div>
					)}
				</div>
			)}
		</div>
	);
};

export default GuardrailViolationActivity;
