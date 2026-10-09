"use client";

import type {
	AppliesTo,
	AssignmentTargetType,
	GuardrailAssignment,
	GuardrailPolicy,
} from "@/types/guardrail-policies";
import * as guardrailsApi from "@/lib/guardrails-api";
import { cn } from "@/lib/utils";
import { invalidateGuardrailStatusCache } from "@/hooks/useNodeGuardrailStatus";
import { Check, Loader2, Lock, Plus, Shield, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

interface AssignmentListProps {
	targetType: AssignmentTargetType;
	targetId: string;
	workflowId?: string;
	onOpenPolicyPicker: () => void;
	refreshTrigger?: number;
	/** When true, hides the built-in header (parent provides its own). */
	hideHeader?: boolean;
	appearance?: "default" | "light";
}

const OVERRIDE_LABELS: Record<string, string> = {
	merge: "Merge",
	replace: "Replace",
	append: "Append",
};

export default function AssignmentList({
	targetType,
	targetId,
	workflowId,
	onOpenPolicyPicker,
	refreshTrigger,
	hideHeader = false,
	appearance = "default",
}: AssignmentListProps) {
	const isLight = appearance === "light";
	const [assignments, setAssignments] = useState<GuardrailAssignment[]>([]);
	const [compulsoryPolicies, setCompulsoryPolicies] = useState<GuardrailPolicy[]>([]);
	const [loading, setLoading] = useState(true);
	const [removingId, setRemovingId] = useState<string | null>(null);
	const [editingField, setEditingField] = useState<{
		assignmentId: string;
		field: "priority" | "override_mode";
	} | null>(null);
	const [editingValue, setEditingValue] = useState<string>("");
	const [savingField, setSavingField] = useState<{
		assignmentId: string;
		field: "priority" | "override_mode";
	} | null>(null);
	const editInputRef = useRef<HTMLInputElement>(null);

	const fetchData = useCallback(async () => {
		setLoading(true);
		try {
			const [assignmentResult, compulsoryResult] = await Promise.all([
				guardrailsApi.listAssignments({
					target_type: targetType,
					target_id: targetId,
				}),
				guardrailsApi.listCompulsoryPolicies().catch(() => ({ policies: [] })),
			]);
			setAssignments(assignmentResult.assignments || []);
			setCompulsoryPolicies(compulsoryResult.policies || []);
		} catch {
			// Silently handle - empty list is fine
		} finally {
			setLoading(false);
		}
	}, [targetType, targetId]);

	useEffect(() => {
		fetchData();
	}, [fetchData, refreshTrigger]);

	const handleRemove = useCallback(
		async (assignmentId: string) => {
			setRemovingId(assignmentId);
			try {
				await guardrailsApi.deleteAssignment(assignmentId);
				setAssignments((prev) =>
					prev.filter((a) => a.id !== assignmentId),
				);
				invalidateGuardrailStatusCache(workflowId);
			} catch {
				// Silently handle
			} finally {
				setRemovingId(null);
			}
		},
		[workflowId],
	);

	const startEditing = useCallback(
		(assignmentId: string, field: "priority" | "override_mode", currentValue: string | number) => {
			setEditingField({ assignmentId, field });
			setEditingValue(String(currentValue));
			if (field === "priority") {
				setTimeout(() => editInputRef.current?.select(), 0);
			}
		},
		[],
	);

	const cancelEditing = useCallback(() => {
		setEditingField(null);
		setEditingValue("");
	}, []);

	const saveField = useCallback(
		async (assignmentId: string, field: "priority" | "override_mode") => {
			const current = assignments.find((a) => a.id === assignmentId);
			if (!current) {
				cancelEditing();
				return;
			}

			const payload: { priority?: number; override_mode?: string } = {};
			if (field === "priority") {
				const newPriority = Number.parseInt(editingValue, 10);
				if (Number.isNaN(newPriority) || newPriority < 0 || newPriority > 9999) {
					cancelEditing();
					return;
				}
				if (current.priority === newPriority) {
					cancelEditing();
					return;
				}
				payload.priority = newPriority;
			} else {
				if (current.override_mode === editingValue) {
					cancelEditing();
					return;
				}
				payload.override_mode = editingValue;
			}

			setSavingField({ assignmentId, field });
			try {
				const result = await guardrailsApi.updateAssignment(assignmentId, payload);
				setAssignments((prev) => {
					const updated = prev.map((a) =>
						a.id === assignmentId
							? {
									...a,
									...(field === "priority"
										? { priority: result.assignment.priority }
										: { override_mode: result.assignment.override_mode }),
								}
							: a,
					);
					return [...updated].sort((a, b) => a.priority - b.priority);
				});
				invalidateGuardrailStatusCache(workflowId);
			} catch {
				// Silently handle
			} finally {
				setSavingField(null);
				setEditingField(null);
				setEditingValue("");
			}
		},
		[editingValue, assignments, workflowId, cancelEditing],
	);

	// Map assignment target types to policy applies_to values
	const targetTypeToAppliesTo: Record<string, string> = {
		agent_node: "agent",
		workflow: "workflow",
		tool: "tool",
		model: "model",
	};
	const appliesToValue = targetTypeToAppliesTo[targetType] || targetType;

	// Filter compulsory policies: must match this target type and not already assigned
	const assignedPolicyIds = new Set(assignments.map((a) => a.policy_id));
	const extraCompulsory = compulsoryPolicies.filter(
		(p) =>
			!assignedPolicyIds.has(p.id) &&
			(p.applies_to.length === 0 || p.applies_to.includes(appliesToValue as AppliesTo)),
	);
	const hasAny = assignments.length > 0 || extraCompulsory.length > 0;

	return (
		<div className="space-y-3">
			{!hideHeader && (
				<div className="flex items-center justify-between">
					<h4
							className={`flex items-center gap-2 text-sm font-medium ${isLight ? "text-slate-900" : "text-slate-900"}`}
					>
						<Shield
								className={`h-4 w-4 ${isLight ? "text-orange-600" : "text-orange-600"}`}
						/>
						Guardrail Policies
					</h4>
					<button
						onClick={onOpenPolicyPicker}
							className={`flex items-center gap-1.5 rounded-[4px] px-2.5 py-1.5 text-xs font-medium transition-colors ${isLight ? "text-orange-700 hover:bg-orange-50 hover:text-orange-900" : "text-orange-700 hover:bg-orange-50 hover:text-orange-900"}`}
					>
						<Plus className="h-3.5 w-3.5" />
						Assign
					</button>
				</div>
			)}

			{loading ? (
				<div
						className={`flex items-center justify-center py-4 ${isLight ? "text-slate-600" : "text-slate-600"}`}
				>
					<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
				</div>
			) : !hasAny ? (
				<div
						className={`rounded-[4px] border border-dashed px-4 py-6 text-center ${isLight ? "border-slate-300" : "border-slate-300"}`}
				>
					<Shield
							className={`mx-auto mb-2 h-6 w-6 ${isLight ? "text-slate-400" : "text-slate-400"}`}
					/>
					<p
							className={`text-sm ${isLight ? "text-slate-600" : "text-slate-600"}`}
					>
						No policies assigned
					</p>
					<button
						onClick={onOpenPolicyPicker}
							className={`mt-2 text-xs font-medium ${isLight ? "text-orange-700 hover:text-orange-900" : "text-orange-700 hover:text-orange-900"}`}
					>
						Assign a policy
					</button>
				</div>
			) : (
				<div className="space-y-1.5">
					{/* Compulsory policies (not already in assignments) */}
					{extraCompulsory.map((policy) => (
						<div
							key={`compulsory-${policy.id}`}
							className={
								isLight
									? "flex items-center justify-between rounded-[4px] border border-slate-200 bg-white px-3 py-2.5 shadow-sm"
									: "flex items-center justify-between rounded-lg border border-amber-500/20 bg-amber-500/[0.04] px-3 py-2.5"
							}
						>
							<div className="min-w-0 flex-1">
								<div className="flex items-center gap-2">
									<span
										className={`truncate text-sm font-medium ${isLight ? "text-slate-900" : "text-[color:var(--color-text-primary)]"}`}
									>
										{policy.name}
									</span>
									<span
										className={`inline-flex flex-shrink-0 items-center gap-1 rounded-[4px] border px-1.5 py-0.5 text-[10px] font-medium ${isLight ? "border-amber-500 bg-white text-amber-900" : "border-transparent bg-amber-500/15 text-amber-400"}`}
									>
										<Lock className="h-2.5 w-2.5" />
										Compulsory
									</span>
								</div>
								<div
									className={`mt-0.5 text-xs ${isLight ? "text-slate-600" : "text-[color:var(--color-text-tertiary)]"}`}
								>
									Admin-enforced — applies to all agents
								</div>
							</div>
						</div>
					))}

					{/* Assigned policies (mark compulsory ones as non-removable) */}
					{assignments.map((assignment) => {
						const isCompulsory = compulsoryPolicies.some((p) => p.id === assignment.policy_id);
						return (
							<div
								key={assignment.id}
								className={`flex items-center justify-between rounded-[4px] border px-3 py-2.5 ${
									isCompulsory
										? isLight
											? "border-slate-200 bg-white shadow-sm"
											: "border-amber-500/20 bg-amber-500/[0.04]"
										: isLight
											? "border-slate-200 bg-white"
											: "border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)]"
								}`}
							>
								<div className="min-w-0 flex-1">
									<div className="flex items-center gap-2">
										<span
											className={`truncate text-sm font-medium ${isLight ? "text-slate-900" : "text-[color:var(--color-text-primary)]"}`}
										>
											{assignment.policy_name || "Unknown Policy"}
										</span>
										{isCompulsory && (
											<span
												className={`inline-flex flex-shrink-0 items-center gap-1 rounded-[4px] border px-1.5 py-0.5 text-[10px] font-medium ${isLight ? "border-amber-500 bg-white text-amber-900" : "border-transparent bg-amber-500/15 text-amber-400"}`}
											>
												<Lock className="h-2.5 w-2.5" />
												Compulsory
											</span>
										)}
									</div>
									{isCompulsory ? (
										<div
											className={`mt-0.5 text-xs ${isLight ? "text-slate-600" : "text-[color:var(--color-text-tertiary)]"}`}
										>
											Admin-enforced — cannot be removed
										</div>
									) : (
										<div
											className={`mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs ${isLight ? "text-slate-600" : "text-[color:var(--color-text-tertiary)]"}`}
										>
											{/* Priority field */}
											{editingField?.assignmentId === assignment.id &&
											editingField.field === "priority" ? (
												<span className="inline-flex items-center gap-1">
													Priority:
													<input
														ref={editInputRef}
														type="number"
														min={0}
														max={9999}
														value={editingValue}
														onChange={(e) => setEditingValue(e.target.value)}
														onKeyDown={(e) => {
															if (e.key === "Enter") saveField(assignment.id, "priority");
															if (e.key === "Escape") cancelEditing();
														}}
														disabled={
															savingField?.assignmentId === assignment.id &&
															savingField.field === "priority"
														}
														className={cn(
															"w-16 rounded-[4px] px-1.5 py-0.5 text-xs outline-none",
															isLight
																? "border border-slate-200 bg-white text-slate-900 focus:border-orange-500"
																: "border border-slate-200 bg-white text-slate-900 focus:border-orange-500",
														)}
													/>
													{savingField?.assignmentId === assignment.id &&
													savingField.field === "priority" ? (
														<Loader2
															className={cn(
																"h-3 w-3 animate-spin",
																isLight ? "text-orange-600" : "text-orange-600",
															)}
														/>
													) : (
														<>
															<button
																type="button"
																onClick={() => saveField(assignment.id, "priority")}
																className={cn(
																	"rounded p-0.5",
																	isLight
																		? "text-[#0DA931] hover:bg-[#F1F8E9]"
																		: "text-[#0DA931] hover:bg-[#0DA931]/10",
																)}
															>
																<Check className="h-3 w-3" />
															</button>
															<button
																type="button"
																onClick={cancelEditing}
																className={cn(
																	"rounded p-0.5",
																	isLight
																		? "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
																		: "text-[color:var(--color-text-tertiary)] hover:bg-red-500/10 hover:text-red-400",
																)}
															>
																<X className="h-3 w-3" />
															</button>
														</>
													)}
												</span>
											) : (
												<button
													type="button"
													onClick={() =>
														startEditing(assignment.id, "priority", assignment.priority)
													}
													className={
														isLight
															? "cursor-pointer text-slate-600 transition-colors hover:text-slate-900"
															: "cursor-pointer transition-colors hover:text-blue-400"
													}
													title="Click to edit priority"
												>
													Priority: {assignment.priority}
												</button>
											)}

											<span
												className={
													isLight ? "text-slate-300" : "text-[color:var(--color-border)]"
												}
											>
												|
											</span>

											{/* Override mode field */}
											{editingField?.assignmentId === assignment.id &&
											editingField.field === "override_mode" ? (
												<span className="inline-flex items-center gap-1">
													Mode:
													<select
														value={editingValue}
														onChange={(e) => {
															setEditingValue(e.target.value);
														}}
														onKeyDown={(e) => {
															if (e.key === "Escape") cancelEditing();
														}}
														disabled={
															savingField?.assignmentId === assignment.id &&
															savingField.field === "override_mode"
														}
														className={cn(
															"rounded-[4px] px-1.5 py-0.5 text-xs outline-none",
															isLight
																? "border border-slate-200 bg-white text-slate-900 focus:border-orange-500"
																	: "border border-slate-200 bg-white text-slate-900 focus:border-orange-500",
														)}
													>
														<option value="merge">Merge</option>
														<option value="replace">Replace</option>
														<option value="append">Append</option>
													</select>
													{savingField?.assignmentId === assignment.id &&
													savingField.field === "override_mode" ? (
														<Loader2
															className={cn(
																"h-3 w-3 animate-spin",
																	isLight ? "text-orange-600" : "text-orange-600",
															)}
														/>
													) : (
														<>
															<button
																type="button"
																onClick={() =>
																	saveField(assignment.id, "override_mode")
																}
																className={cn(
																	"rounded p-0.5",
																	isLight
																		? "text-[#0DA931] hover:bg-[#F1F8E9]"
																		: "text-[#0DA931] hover:bg-[#0DA931]/10",
																)}
															>
																<Check className="h-3 w-3" />
															</button>
															<button
																type="button"
																onClick={cancelEditing}
																className={cn(
																	"rounded p-0.5",
																	isLight
																		? "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
																		: "text-[color:var(--color-text-tertiary)] hover:bg-red-500/10 hover:text-red-400",
																)}
															>
																<X className="h-3 w-3" />
															</button>
														</>
													)}
												</span>
											) : (
												<button
													type="button"
													onClick={() =>
														startEditing(
															assignment.id,
															"override_mode",
															assignment.override_mode,
														)
													}
													className={
														isLight
															? "cursor-pointer text-slate-600 transition-colors hover:text-slate-900"
																: "cursor-pointer text-slate-600 transition-colors hover:text-orange-600"
													}
													title="Click to edit override mode"
												>
													Mode:{" "}
													{OVERRIDE_LABELS[assignment.override_mode] ||
														assignment.override_mode}
												</button>
											)}
										</div>
									)}
								</div>
								{!isCompulsory && (
									<button
										onClick={() => handleRemove(assignment.id)}
										disabled={removingId === assignment.id}
										className={
											isLight
												? "ml-2 flex-shrink-0 rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-red-700"
												: "ml-2 flex-shrink-0 rounded-lg p-1.5 text-[color:var(--color-text-tertiary)] transition-colors hover:bg-red-500/10 hover:text-red-400"
										}
									>
										{removingId === assignment.id ? (
											<Loader2 className="h-3.5 w-3.5 animate-spin text-orange-500" />
										) : (
											<Trash2 className="h-3.5 w-3.5" />
										)}
									</button>
								)}
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
}
