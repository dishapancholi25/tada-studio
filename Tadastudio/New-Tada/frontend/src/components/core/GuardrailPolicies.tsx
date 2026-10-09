"use client";

import type { GuardrailPolicy } from "@/types/guardrail-policies";
import {
	AlertTriangle,
	ArrowDownCircle,
	ArrowUpCircle,
	BarChart2,
	Clock,
	Copy,
	Edit3,
	Filter,
	Globe,
	History,
	Lock,
	Plus,
	Save,
	Search,
	Share2,
	Shield,
	ShieldCheck,
	Tag,
	Trash2,
	User,
	Users,
	X,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import * as guardrailsApi from "@/lib/guardrails-api";
import type { GuardrailsConfig } from "@/types/guardrails";
import { DEFAULT_GUARDRAILS_CONFIG } from "@/types/guardrails";
import type { AppliesTo, AssignmentTargetType } from "@/types/guardrail-policies";
import TabContainer from "@/components/ui/TabContainer";
import PolicyVersionHistory from "@/components/core/PolicyVersionHistory";
import SandboxPanel from "@/components/core/SandboxPanel";
import PolicyMetrics from "@/components/core/PolicyMetrics";
import GuardrailBuilder, { toPolicyConfig } from "@/components/core/guardrails/GuardrailBuilder";
import PolicyPicker from "@/components/core/guardrails/PolicyPicker";
import GroupSelector from "@/components/settings/groups/GroupSelector";
import ViolationDashboard from "./ViolationDashboard";
import ComplianceView from "./guardrails/ComplianceView";

type TabId = "my" | "shared" | "templates" | "violations" | "compulsory" | "compliance";

export default function GuardrailPolicies() {
	const { user } = useAuth();
	const router = useRouter();
	const searchParams = useSearchParams();
	const isAdmin = user?.is_admin ?? false;

	const [policies, setPolicies] = useState<GuardrailPolicy[]>([]);
	const [loading, setLoading] = useState(true);
	const [activeTab, setActiveTab] = useState<TabId>("my");
	const [search, setSearch] = useState("");
	const [showCreateDialog, setShowCreateDialog] = useState(false);
	const [selectedPolicy, setSelectedPolicy] = useState<GuardrailPolicy | null>(null);

	// URL-based policy assignment (from ComplianceView links)
	const assignTargetType = searchParams.get("assign") as AssignmentTargetType | null;
	const assignTargetId = searchParams.get("id");
	const [showAssignPicker, setShowAssignPicker] = useState(false);

	useEffect(() => {
		if (assignTargetType && assignTargetId) {
			setShowAssignPicker(true);
		}
	}, [assignTargetType, assignTargetId]);

	const fetchPolicies = useCallback(async () => {
		setLoading(true);
		try {
			const params: Record<string, string | boolean> = {};
			if (activeTab === "templates") params.is_template = true;
			if (search) params.search = search;

			const resp = await guardrailsApi.listPolicies(
				params as Parameters<typeof guardrailsApi.listPolicies>[0],
			);
			setPolicies(resp.policies || []);
		} catch (err) {
			console.error("Failed to load policies:", err);
			setPolicies([]);
		} finally {
			setLoading(false);
		}
	}, [activeTab, search]);

	useEffect(() => {
		fetchPolicies();
	}, [fetchPolicies]);

	const filteredPolicies = useMemo(() => {
		const userId = user?.sub || user?.email || "";
		switch (activeTab) {
			case "my":
				return policies.filter((p) => p.created_by === userId);
			case "shared":
				return policies.filter(
					(p) => p.created_by !== userId && !p.is_template && !p.is_compulsory,
				);
			case "templates":
				return policies.filter((p) => p.is_template);
			case "compulsory":
				return policies.filter((p) => p.is_compulsory);
			default:
				return policies;
		}
	}, [policies, activeTab, user]);

	// Compulsory promotion state
	const [promoteTarget, setPromoteTarget] = useState<GuardrailPolicy | null>(null);

	const handleDelete = async (id: string) => {
		try {
			await guardrailsApi.deletePolicy(id);
			fetchPolicies();
		} catch (err) {
			console.error("Failed to delete policy:", err);
		}
	};

	const handleClone = async (id: string) => {
		try {
			await guardrailsApi.clonePolicy(id);
			setActiveTab("my");
			fetchPolicies();
		} catch (err) {
			console.error("Failed to clone policy:", err);
		}
	};

	const handlePromoteCompulsory = async (policyId: string, auditFirst: boolean) => {
		try {
			if (auditFirst) {
				// Switch enforcement mode to audit before promoting
				await guardrailsApi.updatePolicy(policyId, {
					config: { ...(promoteTarget?.config ?? {}), enforcement_mode: "audit" },
					change_summary: "Switched to audit mode for compulsory rollout",
				});
			}
			await guardrailsApi.setCompulsoryPolicy(policyId, true);
			setPromoteTarget(null);
			setSelectedPolicy(null);
			fetchPolicies();
		} catch (err) {
			console.error("Failed to promote policy:", err);
		}
	};

	const handleDemoteCompulsory = async (policyId: string) => {
		try {
			await guardrailsApi.deactivateCompulsoryPolicy(policyId);
			setSelectedPolicy(null);
			fetchPolicies();
		} catch (err) {
			console.error("Failed to demote policy:", err);
		}
	};

	const handleUpdateVisibility = async (policyId: string, visibleToGroups: string[]) => {
		try {
			const resp = await guardrailsApi.updatePolicyVisibility(policyId, visibleToGroups);
			if (resp.policy) {
				setPolicies((prev) =>
					prev.map((p) => (p.id === resp.policy.id ? resp.policy : p)),
				);
				if (selectedPolicy?.id === policyId) {
					setSelectedPolicy(resp.policy);
				}
			}
		} catch (err) {
			console.error("Failed to update policy visibility:", err);
		}
	};

	const handleCreate = async (name: string, description: string, config?: Record<string, unknown>, appliesTo?: AppliesTo[], visibleToGroups?: string[], isTemplate?: boolean) => {
		try {
			await guardrailsApi.createPolicy({
				name,
				description,
				config: config ?? { enabled: true, enforcement_mode: "enforce" },
				scope: "user",
				applies_to: appliesTo && appliesTo.length > 0 ? appliesTo : ["agent"],
				visible_to_groups: visibleToGroups ?? [],
				is_template: isTemplate ?? false,
				tags: [],
			});
			setShowCreateDialog(false);
			fetchPolicies();
		} catch (err) {
			console.error("Failed to create policy:", err);
		}
	};

	const handleToggleTemplate = async (policyId: string, isTemplate: boolean) => {
		try {
			const resp = await guardrailsApi.updatePolicy(policyId, { is_template: isTemplate });
			if (resp.policy) {
				setPolicies((prev) =>
					prev.map((p) => (p.id === resp.policy.id ? resp.policy : p)),
				);
				if (selectedPolicy?.id === policyId) {
					setSelectedPolicy(resp.policy);
				}
			}
			fetchPolicies();
		} catch (err) {
			console.error("Failed to toggle template status:", err);
		}
	};

	const tabs: Array<{ id: TabId; label: string; icon: typeof Shield }> = [
		{ id: "my", label: "My Policies", icon: User },
		{ id: "shared", label: "Shared with Me", icon: Shield },
		{ id: "templates", label: "Templates", icon: Tag },
		{ id: "violations", label: "Violations", icon: Zap },
		{ id: "compliance", label: "Compliance", icon: BarChart2 },
		...(isAdmin
			? [{ id: "compulsory" as TabId, label: "Compulsory", icon: Lock }]
			: []),
	];

	return (
		<div className="h-full flex flex-col bg-white text-slate-900">
			{/* Header */}
			<div className="border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
				<div className="max-w-screen-2xl mx-auto w-full flex items-center justify-between">
					<div className="flex items-center gap-3">
						<div className="flex items-center justify-center w-10 h-10 rounded-xl bg-white border border-slate-200 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
							<ShieldCheck className="w-5 h-5 text-orange-600" />
						</div>
						<div>
							<h1 className="text-3xl font-bold text-slate-900 mb-2">
								Guardrail Policies
							</h1>
							<p className="text-slate-600">
								Create, share, and manage safety policies for your workflows
							</p>
						</div>
					</div>
					<div className="flex items-center gap-3">
						<button
							type="button"
							onClick={() => setShowCreateDialog(true)}
							className="inline-flex items-center gap-2 rounded-lg border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-medium text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-colors hover:bg-orange-600 hover:border-orange-600"
						>
							<Plus className="w-4 h-4" />
							New Policy
						</button>
					</div>
				</div>
			</div>

			{/* Tabs + Search */}
				<div className="border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8 py-3">
					<div className="max-w-screen-2xl mx-auto flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between lg:gap-4">
					<div className="flex flex-wrap items-center gap-1">
						{tabs.map((tab) => {
							const Icon = tab.icon;
							const isActive = activeTab === tab.id;
							return (
								<button
									key={tab.id}
									type="button"
									onClick={() => setActiveTab(tab.id)}
									className={`inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
										isActive
											? "bg-orange-500 border border-orange-500 text-white"
											: "text-slate-600 hover:text-slate-900 hover:bg-white hover:border-orange-400 border border-transparent"
									}`}
								>
									<Icon className="w-3.5 h-3.5" />
									{tab.label}
								</button>
							);
						})}
					</div>
					<div className="relative w-full lg:w-auto lg:shrink-0">
						<Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
						<input
							type="text"
							value={search}
							onChange={(e) => setSearch(e.target.value)}
							placeholder="Search policies..."
							className="w-full lg:w-64 rounded-lg border border-slate-200 bg-white py-1.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-orange-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/20"
						/>
					</div>
				</div>
			</div>

			{/* Content */}
				<div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
					<div className="max-w-screen-2xl mx-auto">
					{activeTab === "compliance" ? (
						<ComplianceView isAdmin={isAdmin} />
					) : activeTab === "violations" ? (
						<ViolationDashboard />
					) : loading ? (
						<div className="flex flex-col items-center justify-center gap-4 py-20">
							<div className="animate-spin rounded-full h-10 w-10 border-2 border-transparent border-t-orange-500" />
							<p className="text-sm text-slate-600">Loading policies...</p>
						</div>
					) : filteredPolicies.length === 0 ? (
						<div className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white py-20 text-slate-500 shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
							<Shield className="w-12 h-12 mb-4 text-orange-600 opacity-80" />
							{activeTab === "compulsory" && isAdmin ? (
								<>
									<p className="text-sm font-medium text-slate-900 mb-1">No compulsory policies yet</p>
									<p className="text-xs text-slate-500 max-w-md text-center">
										Create a policy in My Policies, test it with the sandbox, then promote it to compulsory
										so it applies to all workflows across the organization.
									</p>
									<div className="flex items-center gap-6 mt-5 text-xs text-slate-500">
										<div className="flex items-center gap-2">
											<div className="flex items-center justify-center w-6 h-6 rounded-full bg-white border border-slate-200 text-orange-600 text-[10px] font-bold">1</div>
											Create
										</div>
										<div className="w-6 border-t border-dashed border-slate-200" />
										<div className="flex items-center gap-2">
											<div className="flex items-center justify-center w-6 h-6 rounded-full bg-white border border-slate-200 text-orange-600 text-[10px] font-bold">2</div>
											Test
										</div>
										<div className="w-6 border-t border-dashed border-slate-200" />
										<div className="flex items-center gap-2">
											<div className="flex items-center justify-center w-6 h-6 rounded-full bg-white border border-slate-200 text-orange-600 text-[10px] font-bold">3</div>
											Promote
										</div>
									</div>
									<button
										type="button"
										onClick={() => setActiveTab("my")}
										className="mt-5 text-sm text-orange-700 hover:text-slate-900"
									>
										Go to My Policies
									</button>
								</>
							) : (
								<>
									<p className="text-sm">
										{activeTab === "my"
											? "You haven't created any policies yet."
											: activeTab === "templates"
												? "No policy templates available yet."
												: `No ${activeTab} policies found.`}
									</p>
									{activeTab === "my" && (
										<button
											type="button"
											onClick={() => setShowCreateDialog(true)}
											className="mt-3 text-sm text-orange-700 hover:text-slate-900"
										>
											Create your first policy
										</button>
									)}
									{activeTab === "templates" && (
										<p className="text-xs text-slate-500 max-w-md text-center mt-2">
											Templates are policies published as reusable starting points.
											Create a policy, then use &quot;Publish as Template&quot; to share it here.
										</p>
									)}
								</>
							)}
						</div>
					) : (
						<>
						{activeTab === "compulsory" && filteredPolicies.length > 0 && (
							<div className="mb-4 rounded-2xl border border-red-200 bg-white px-5 py-3 flex items-center justify-between shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
								<div className="flex items-center gap-3">
									<Lock className="w-4 h-4 text-red-400" />
									<span className="text-sm text-slate-600">
										<span className="font-medium text-slate-900">{filteredPolicies.length}</span> compulsory{" "}
										{filteredPolicies.length === 1 ? "policy" : "policies"} enforced across all workflows
									</span>
								</div>
								{isAdmin && (
									<button
										type="button"
										onClick={() => setActiveTab("compliance")}
										className="text-xs text-red-400 hover:text-red-300 transition-colors"
									>
										View compliance details
									</button>
								)}
							</div>
						)}
						<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
							{filteredPolicies.map((policy) => (
								<PolicyCard
									key={policy.id}
									policy={policy}
									isOwner={
										policy.created_by ===
										(user?.sub || user?.email || "")
									}
									isAdmin={isAdmin}
									onDelete={handleDelete}
									onClone={handleClone}
									onSelect={setSelectedPolicy}
									onPromote={isAdmin ? setPromoteTarget : undefined}
									onDemote={isAdmin ? handleDemoteCompulsory : undefined}
									onToggleTemplate={handleToggleTemplate}
								/>
							))}
						</div>
						</>
					)}
				</div>
			</div>

			{/* Create Dialog */}
			{showCreateDialog && (
				<CreatePolicyDialog
					onClose={() => setShowCreateDialog(false)}
					onCreate={handleCreate}
				/>
			)}

			{/* Policy Detail Modal */}
			{selectedPolicy && (
				<PolicyDetailModal
					policy={selectedPolicy}
					isOwner={selectedPolicy.created_by === (user?.sub || user?.email || "")}
					isAdmin={isAdmin}
					onClose={() => setSelectedPolicy(null)}
					onPolicyRestored={(updated) => {
						setSelectedPolicy(updated);
						setPolicies((prev) =>
							prev.map((p) => (p.id === updated.id ? updated : p)),
						);
					}}
					onUpdateVisibility={handleUpdateVisibility}
					onPromote={isAdmin ? setPromoteTarget : undefined}
					onDemote={isAdmin ? handleDemoteCompulsory : undefined}
					onToggleTemplate={handleToggleTemplate}
				/>
			)}

			{/* Promote to Compulsory Dialog */}
			{promoteTarget && (
				<PromoteCompulsoryDialog
					policy={promoteTarget}
					onClose={() => setPromoteTarget(null)}
					onConfirm={handlePromoteCompulsory}
				/>
			)}

			{/* URL-driven PolicyPicker for ComplianceView integration */}
			{showAssignPicker && assignTargetType && assignTargetId && (
				<PolicyPicker
					targetType={assignTargetType}
					targetId={assignTargetId}
					onAssigned={() => {
						setShowAssignPicker(false);
						router.replace("/guardrails");
					}}
					onClose={() => {
						setShowAssignPicker(false);
						router.replace("/guardrails");
					}}
				/>
			)}
		</div>
	);
}

function PolicyCard({
	policy,
	isOwner,
	isAdmin,
	onDelete,
	onClone,
	onSelect,
	onPromote,
	onDemote,
	onToggleTemplate,
}: {
	policy: GuardrailPolicy;
	isOwner: boolean;
	isAdmin: boolean;
	onDelete: (id: string) => void;
	onClone: (id: string) => void;
	onSelect: (policy: GuardrailPolicy) => void;
	onPromote?: (policy: GuardrailPolicy) => void;
	onDemote?: (id: string) => void;
	onToggleTemplate?: (id: string, isTemplate: boolean) => void;
}) {
	const config = policy.config || {};
	const ruleCount =
		(Array.isArray(config.pattern_rules) ? config.pattern_rules.length : 0) +
		(Array.isArray(config.custom_filters) ? config.custom_filters.length : 0);

	const enforcementMode = (config.enforcement_mode as string) || "enforce";
	const enforcementColor =
		enforcementMode === "enforce"
			? "text-red-600"
			: enforcementMode === "audit"
				? "text-amber-600"
				: "text-slate-400";

	const visibleGroups = policy.visible_to_groups ?? [];
	const isGlobal = visibleGroups.includes("__all__");
	const isShared = visibleGroups.length > 0;
	const visibilityLabel = isGlobal
		? "Everyone"
		: isShared
			? `${visibleGroups.length} group${visibleGroups.length !== 1 ? "s" : ""}`
			: "Private";

	return (
		<div
			className="group relative rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_82%,#f59e0b_180%)] p-5 shadow-[0_18px_50px_rgba(15,23,42,0.08)] transition-all hover:border-orange-400 hover:bg-white cursor-pointer"
			onClick={() => onSelect(policy)}
			onKeyDown={(e) => {
				if (e.key === "Enter" || e.key === " ") onSelect(policy);
			}}
			role="button"
			tabIndex={0}
		>
			{/* Header */}
			<div className="flex items-start justify-between gap-3 mb-3">
				<div className="flex items-center gap-2.5 min-w-0">
					<div
						className={`flex items-center justify-center w-8 h-8 rounded-lg border ${
							policy.is_compulsory
								? "border-red-500/30 bg-red-500/10"
								: "border-slate-200 bg-white"
						}`}
					>
						{policy.is_compulsory ? (
							<Lock className="w-4 h-4 text-red-400" />
						) : (
							<Shield className="w-4 h-4 text-orange-600" />
						)}
					</div>
					<div className="min-w-0">
						<h3 className="text-sm font-medium text-slate-900 truncate">
							{policy.name}
						</h3>
						{policy.description && (
							<p className="text-xs text-slate-500 truncate mt-0.5">
								{policy.description}
							</p>
						)}
					</div>
				</div>
				<div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
					{onPromote && !policy.is_compulsory && (
						<button
							type="button"
							onClick={(e) => { e.stopPropagation(); onPromote(policy); }}
							className="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-white border border-transparent hover:border-red-200"
							title="Promote to compulsory"
						>
							<ArrowUpCircle className="w-3.5 h-3.5" />
						</button>
					)}
					{onDemote && policy.is_compulsory && (
						<button
							type="button"
							onClick={(e) => { e.stopPropagation(); onDemote(policy.id); }}
							className="p-1.5 rounded-md text-slate-400 hover:text-amber-600 hover:bg-white border border-transparent hover:border-amber-300"
							title="Remove compulsory status"
						>
							<ArrowDownCircle className="w-3.5 h-3.5" />
						</button>
					)}
					<button
						type="button"
						onClick={(e) => { e.stopPropagation(); onClone(policy.id); }}
						className="p-1.5 rounded-md text-slate-400 hover:text-slate-900 hover:bg-white border border-transparent hover:border-orange-400"
						title="Clone policy"
					>
						<Copy className="w-3.5 h-3.5" />
					</button>
					{onToggleTemplate && (isOwner || isAdmin) && !policy.is_builtin && (
						<button
							type="button"
							onClick={(e) => { e.stopPropagation(); onToggleTemplate(policy.id, !policy.is_template); }}
							className={`p-1.5 rounded-md border border-transparent ${policy.is_template ? "text-purple-600 hover:text-purple-700 hover:bg-white hover:border-purple-300" : "text-slate-400 hover:text-purple-600 hover:bg-white hover:border-purple-300"}`}
							title={policy.is_template ? "Unpublish template" : "Publish as template"}
						>
							<Tag className="w-3.5 h-3.5" />
						</button>
					)}
					{(isOwner || isAdmin) && !policy.is_compulsory && (
						<button
							type="button"
							onClick={(e) => { e.stopPropagation(); onDelete(policy.id); }}
							className="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-white border border-transparent hover:border-red-200"
							title="Delete policy"
						>
							<Trash2 className="w-3.5 h-3.5" />
						</button>
					)}
				</div>
			</div>

			{/* Metadata */}
			<div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
				<span className={`inline-flex items-center gap-1 ${isShared ? "text-blue-400" : ""}`}>
					{isGlobal ? <Globe className="w-3 h-3" /> : isShared ? <Users className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
					{visibilityLabel}
				</span>
				<span className={`inline-flex items-center gap-1 ${enforcementColor}`}>
					<AlertTriangle className="w-3 h-3" />
					{enforcementMode}
				</span>
				{ruleCount > 0 && (
					<span className="inline-flex items-center gap-1">
						<Filter className="w-3 h-3" />
						{ruleCount} rule{ruleCount !== 1 ? "s" : ""}
					</span>
				)}
				{policy.is_template && (
					<span className="inline-flex items-center gap-1 text-purple-400">
						<Tag className="w-3 h-3" />
						Template
					</span>
				)}
				{policy.is_compulsory && (
					<span className="inline-flex items-center gap-1 text-red-400">
						<Lock className="w-3 h-3" />
						Compulsory
					</span>
				)}
			</div>

			{/* Tags */}
			{policy.tags && policy.tags.length > 0 && (
				<div className="flex flex-wrap gap-1.5 mt-3">
					{policy.tags.slice(0, 4).map((tag) => (
						<span
							key={tag}
							className="rounded-full bg-white border border-slate-200 px-2 py-0.5 text-[10px] text-slate-600"
						>
							{tag}
						</span>
					))}
					{policy.tags.length > 4 && (
						<span className="text-[10px] text-slate-400">
							+{policy.tags.length - 4}
						</span>
					)}
				</div>
			)}

			{/* Footer */}
			<div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-200 text-[10px] text-slate-500">
				<span>
					{policy.creator_name || "Unknown"} &middot; v{policy.current_version ?? policy.version}
				</span>
				{policy.created_at && (
					<span className="inline-flex items-center gap-1">
						<Clock className="w-2.5 h-2.5" />
						{new Date(policy.created_at).toLocaleDateString()}
					</span>
				)}
			</div>

			{/* Applies-to badges */}
			{policy.applies_to && policy.applies_to.length > 0 && (
				<div className="flex gap-1 mt-2">
					{policy.applies_to.map((target) => (
						<span
							key={target}
							className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] text-orange-700"
						>
							{target}
						</span>
					))}
				</div>
			)}
		</div>
	);
}

const APPLIES_TO_OPTIONS: { value: AppliesTo; label: string; description: string }[] = [
	{ value: "agent", label: "Agent", description: "Agent nodes that perform LLM reasoning" },
	{ value: "model", label: "Model", description: "LLM model invocations and responses" },
	{ value: "tool", label: "Tool", description: "Tool calls such as HTTP, DB, or search" },
	{ value: "workflow", label: "Workflow", description: "Entire workflow executions" },
];

function CreatePolicyDialog({
	onClose,
	onCreate,
}: {
	onClose: () => void;
	onCreate: (name: string, description: string, config?: Record<string, unknown>, appliesTo?: AppliesTo[], visibleToGroups?: string[], isTemplate?: boolean) => void;
}) {
	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [appliesTo, setAppliesTo] = useState<AppliesTo[]>(["agent"]);
	const [visibleToGroups, setVisibleToGroups] = useState<string[]>([]);
	const [isTemplate, setIsTemplate] = useState(false);
	const [config, setConfig] = useState<GuardrailsConfig>({
		...DEFAULT_GUARDRAILS_CONFIG,
		enabled: true,
	});

	const toggleAppliesTo = (value: AppliesTo) => {
		setAppliesTo((prev) => {
			const next = prev.includes(value)
				? prev.filter((v) => v !== value)
				: [...prev, value];
			// Require at least one selection
			return next.length > 0 ? next : prev;
		});
	};

	return (
		<div
			className="fixed inset-0 z-50 flex items-center justify-center bg-[#213C81]/45 backdrop-blur-sm"
			onClick={(e) => {
				if (e.target === e.currentTarget) onClose();
			}}
		>
			<div className="relative flex h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
				<div className="min-h-0 flex-1 overflow-y-auto bg-white">
					<div className="border-b border-slate-200 bg-white p-6 pb-4">
						<div className="mb-4 flex items-start justify-between gap-4">
							<div>
								<h2 className="text-lg font-semibold text-slate-900">
									Create New Policy
								</h2>
								<p className="mt-1 text-sm text-slate-500">
									Define guardrail scope, sharing, and rules for this policy.
								</p>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-all hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
								aria-label="Close"
							>
								<X className="h-4 w-4" />
							</button>
						</div>
						<div className="space-y-4">
							<div>
								<label className="block text-sm text-slate-700 mb-1">Name</label>
								<input
									type="text"
									value={name}
									onChange={(e) => setName(e.target.value)}
									placeholder="e.g., PII Protection Policy"
									className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-all hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
								/>
							</div>
							<div>
								<label className="block text-sm text-slate-700 mb-1">
									Description{" "}
									<span className="text-slate-400">(optional)</span>
								</label>
								<textarea
									value={description}
									onChange={(e) => setDescription(e.target.value)}
									placeholder="Describe the purpose of this policy..."
									rows={2}
									className="w-full resize-none rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 transition-all hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
								/>
							</div>
							<div>
								<label className="block text-sm text-slate-700 mb-2">Applies to</label>
								<div className="flex flex-wrap gap-2">
									{APPLIES_TO_OPTIONS.map((opt) => {
										const selected = appliesTo.includes(opt.value);
										return (
											<button
												key={opt.value}
												type="button"
												onClick={() => toggleAppliesTo(opt.value)}
												className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors ${
													selected
														? "border-orange-500 bg-orange-500 text-white"
														: "border-slate-200 bg-white text-slate-600 hover:border-orange-400 hover:text-slate-900"
												}`}
												title={opt.description}
											>
												<div
													className={`w-3 h-3 rounded-sm border flex items-center justify-center ${
														selected
															? "border-white bg-white/20"
															: "border-slate-300"
													}`}
												>
													{selected && (
														<svg className="w-2 h-2 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
															<path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
														</svg>
													)}
												</div>
												{opt.label}
											</button>
										);
									})}
								</div>
								<p className="text-[10px] text-slate-500 mt-1.5">Select which entity types this policy applies to</p>
							</div>
							<div>
								<label className="block text-sm text-slate-700 mb-2">
									Visibility
									<span className="text-slate-400 text-xs ml-2">
										{visibleToGroups.length === 0 ? "(Private — only you)" : visibleToGroups.includes("__all__") ? "(Everyone)" : `(${visibleToGroups.length} group${visibleToGroups.length !== 1 ? "s" : ""})`}
									</span>
								</label>
								<GroupSelector
									selectedGroups={visibleToGroups}
									onChange={setVisibleToGroups}
									placeholder="Private — select groups to share..."
								/>
								<p className="text-[10px] text-slate-500 mt-1.5">Leave empty for private, or select groups who can see this policy</p>
							</div>
							<div>
								<label className="flex items-center gap-3 cursor-pointer">
									<button
										type="button"
										role="switch"
										aria-checked={isTemplate}
										onClick={() => setIsTemplate(!isTemplate)}
										className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors ${
											isTemplate ? "bg-orange-500" : "bg-slate-200"
										}`}
									>
										<span
											className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
												isTemplate ? "translate-x-[18px]" : "translate-x-[3px]"
											}`}
										/>
									</button>
									<div>
										<span className="text-sm text-slate-700">Publish as template</span>
										<p className="text-[10px] text-slate-500">Make this policy available as a reusable starting point for other users</p>
									</div>
								</label>
							</div>
						</div>
					</div>

					<div className="bg-white px-6 pb-4 pt-4">
						<GuardrailBuilder
							config={config}
							onChange={setConfig}
						/>
					</div>
				</div>

				<div className="flex shrink-0 justify-end gap-3 border-t border-slate-200 bg-white p-6 pt-4">
					<button
						type="button"
						onClick={onClose}
						className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 transition-all hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={() => {
							if (name.trim()) {
								onCreate(
									name.trim(),
									description.trim(),
									config as unknown as Record<string, unknown>,
									appliesTo,
									visibleToGroups,
									isTemplate,
								);
							}
						}}
						disabled={!name.trim()}
						className="rounded-xl border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-medium text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] transition-all hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25 disabled:cursor-not-allowed disabled:opacity-40"
					>
						Create Policy
					</button>
				</div>
			</div>
		</div>
	);
}

function PolicyDetailModal({
	policy,
	isOwner,
	isAdmin,
	onClose,
	onPolicyRestored,
	onUpdateVisibility,
	onPromote,
	onDemote,
	onToggleTemplate,
}: {
	policy: GuardrailPolicy;
	isOwner: boolean;
	isAdmin?: boolean;
	onClose: () => void;
	onPolicyRestored?: (updatedPolicy: GuardrailPolicy) => void;
	onUpdateVisibility?: (policyId: string, visibleToGroups: string[]) => void;
	onPromote?: (policy: GuardrailPolicy) => void;
	onDemote?: (id: string) => void;
	onToggleTemplate?: (id: string, isTemplate: boolean) => void;
}) {
	const [activeTab, setActiveTab] = useState("config");
	const [sandboxOpen, setSandboxOpen] = useState(false);
	const [isEditing, setIsEditing] = useState(false);
	const [isSaving, setIsSaving] = useState(false);
	const [editConfig, setEditConfig] = useState<GuardrailsConfig>(() =>
		toPolicyConfig(policy.config),
	);
	const [editName, setEditName] = useState(() => policy.name);
	const [editDescription, setEditDescription] = useState(
		() => policy.description ?? "",
	);
	const [editAppliesTo, setEditAppliesTo] = useState<AppliesTo[]>(
		() => policy.applies_to ?? ["agent"],
	);

	const toggleEditAppliesTo = (value: AppliesTo) => {
		setEditAppliesTo((prev) => {
			const next = prev.includes(value)
				? prev.filter((v) => v !== value)
				: [...prev, value];
			return next.length > 0 ? next : prev;
		});
	};

	// Reset edit state when policy changes
	useEffect(() => {
		setEditName(policy.name);
		setEditDescription(policy.description ?? "");
		setEditConfig(toPolicyConfig(policy.config));
		setEditAppliesTo(policy.applies_to ?? ["agent"]);
		setIsEditing(false);
	}, [policy.id, policy.name, policy.description, policy.config]);

	const handleSave = async () => {
		setIsSaving(true);
		try {
			const resp = await guardrailsApi.updatePolicy(policy.id, {
				name: editName.trim() || policy.name,
				description: editDescription.trim() || null,
				config: editConfig as unknown as Record<string, unknown>,
				applies_to: editAppliesTo,
			});
			if (resp.policy && onPolicyRestored) {
				onPolicyRestored(resp.policy);
			}
			setIsEditing(false);
		} catch (err) {
			console.error("Failed to update policy config:", err);
		} finally {
			setIsSaving(false);
		}
	};

	const handleCancelEdit = () => {
		setEditName(policy.name);
		setEditDescription(policy.description ?? "");
		setEditConfig(toPolicyConfig(policy.config));
		setEditAppliesTo(policy.applies_to ?? ["agent"]);
		setIsEditing(false);
	};

	const tabs = [
		{
			id: "config",
			label: "Configuration",
			icon: <Shield className="w-4 h-4" />,
			content: (
				<div className="p-1">
					<GuardrailBuilder
						config={editConfig}
						onChange={setEditConfig}
						readOnly={!isEditing}
					/>
				</div>
			),
		},
		{
			id: "versions",
			label: "Version History",
			icon: <History className="w-4 h-4" />,
			content: <PolicyVersionHistory policyId={policy.id} onPolicyRestored={onPolicyRestored} />,
		},
		{
			id: "metrics",
			label: "Metrics",
			icon: <BarChart2 className="w-4 h-4" />,
			content: <PolicyMetrics policyId={policy.id} />,
		},
	];

	return (
		<div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
			<div className="relative w-full max-w-3xl max-h-[80vh] rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] flex flex-col overflow-hidden">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
				{/* Compulsory banner inside detail modal */}
				{policy.is_compulsory && (
					<div className="flex items-center gap-2 border-b border-[#B00020] bg-[#B00020] px-6 py-2.5 text-xs font-medium text-white">
						<Lock className="h-3.5 w-3.5 shrink-0" aria-hidden />
						This policy is compulsory and enforced across all workflows
					</div>
				)}

				{/* Header — aligned with Workflow Management: icon block + title + subtitle */}
				<div className="flex items-center justify-between px-6 py-5 border-b border-slate-200 bg-white">
					<div className="flex items-center gap-3 min-w-0">
						<div
							className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border ${
								policy.is_compulsory
									? "border-[#B00020] bg-[#B00020] text-white"
									: "border-orange-200 bg-orange-100 text-orange-600"
							}`}
						>
							{policy.is_compulsory ? (
								<Lock className="h-5 w-5 text-white" />
							) : (
								<Shield className="h-5 w-5 text-orange-600" />
							)}
						</div>
						<div className="min-w-0 flex-1">
							{isEditing ? (
								<input
									type="text"
									value={editName}
									onChange={(e) => setEditName(e.target.value)}
									className="w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-base font-semibold text-slate-900 transition-colors hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
									placeholder="Policy name"
								/>
							) : (
								<h2 className="text-lg font-semibold tracking-tight text-slate-900 truncate">
									{policy.name}
								</h2>
							)}
							{isEditing ? (
								<input
									type="text"
									value={editDescription}
									onChange={(e) => setEditDescription(e.target.value)}
									className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 transition-colors hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15"
									placeholder="Policy description (optional)"
								/>
							) : (
								policy.description && (
									<p className="mt-0.5 text-sm text-slate-500 truncate">
										{policy.description}
									</p>
								)
							)}
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900"
					>
						<X className="w-5 h-5" />
					</button>
				</div>

				{/* Applies-to section */}
				<div className="flex items-center gap-2 px-6 py-2.5 border-b border-slate-200 bg-white">
					<span className="text-[11px] text-slate-500 mr-1">Applies to</span>
					{APPLIES_TO_OPTIONS.map((opt) => {
						const selected = (isEditing ? editAppliesTo : (policy.applies_to ?? [])).includes(opt.value);
						return (
							<button
								key={opt.value}
								type="button"
								onClick={() => isEditing && toggleEditAppliesTo(opt.value)}
								disabled={!isEditing}
								className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] transition-colors ${
									selected
										? "border-orange-500 bg-orange-500 text-white"
										: "border-slate-200 bg-white text-slate-500"
								} ${
									isEditing
										? selected
											? "cursor-pointer hover:border-orange-600 hover:bg-orange-600 hover:text-white"
											: "cursor-pointer hover:border-orange-400 hover:text-slate-900"
										: "cursor-default"
								}`}
								title={opt.description}
							>
								<div
									className={`w-2.5 h-2.5 rounded-sm border flex items-center justify-center ${
										selected
											? "border-white bg-white/20"
											: "border-slate-300"
									}`}
								>
									{selected && (
										<svg className="w-1.5 h-1.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
											<path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
										</svg>
									)}
								</div>
								{opt.label}
							</button>
						);
					})}
				</div>

				{/* Visibility section */}
				{(isOwner || isAdmin) && onUpdateVisibility && (
					<div className="px-6 py-2.5 border-b border-slate-200 bg-white">
						<div className="flex items-center gap-2 mb-2">
							<Share2 className="w-3.5 h-3.5 text-slate-500" />
							<span className="text-[11px] text-slate-500">Visibility</span>
							<span className="text-[10px] text-slate-400">
								{(policy.visible_to_groups ?? []).length === 0
									? "Private"
									: (policy.visible_to_groups ?? []).includes("__all__")
										? "Everyone"
										: `${(policy.visible_to_groups ?? []).length} group${(policy.visible_to_groups ?? []).length !== 1 ? "s" : ""}`}
							</span>
						</div>
						<GroupSelector
							selectedGroups={policy.visible_to_groups ?? []}
							onChange={(groups) => onUpdateVisibility(policy.id, groups)}
							placeholder="Private — select groups to share..."
						/>
					</div>
				)}

				{/* Tabs */}
				<div className="flex-1 min-h-0 overflow-hidden flex flex-col">
					<TabContainer
						tabs={tabs}
						activeTab={activeTab}
						onTabChange={setActiveTab}
						isDarkMode={false}
					/>
				</div>

				{/* Footer: action buttons left, Cancel + Edit/Save right */}
				<div className="flex items-center justify-between px-6 py-3 border-t border-slate-200 bg-white">
					{/* Left — action buttons */}
					<div className="flex items-center gap-2">
						<button
							type="button"
							onClick={() => setSandboxOpen(true)}
							className="inline-flex items-center gap-1.5 border border-slate-200 bg-white text-slate-700 text-xs px-3 py-1.5 rounded-lg hover:border-orange-400 hover:text-slate-900 transition-colors"
						>
							<Zap className="w-3.5 h-3.5" />
							Test Policy
						</button>
						{onToggleTemplate && (isOwner || isAdmin) && !policy.is_builtin && (
							<button
								type="button"
								onClick={() => onToggleTemplate(policy.id, !policy.is_template)}
								className={`inline-flex items-center gap-1.5 border text-xs px-3 py-1.5 rounded-lg transition-colors ${
									policy.is_template
										? "border-blue-300 bg-white text-blue-700 hover:border-blue-400 hover:text-blue-800"
										: "border-slate-200 bg-white text-slate-600 hover:bg-white hover:border-orange-400 hover:text-slate-900"
								}`}
							>
								<Tag className="w-3.5 h-3.5" />
								{policy.is_template ? "Unpublish Template" : "Publish as Template"}
							</button>
						)}
						{onPromote && !policy.is_compulsory && (
							<button
								type="button"
								onClick={() => onPromote(policy)}
								className="inline-flex items-center gap-1.5 rounded-lg border border-orange-500 bg-orange-500 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
							>
								<ArrowUpCircle className="w-3.5 h-3.5" />
								Make Compulsory
							</button>
						)}
						{onDemote && policy.is_compulsory && (
							<button
								type="button"
								onClick={() => onDemote(policy.id)}
								className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700 transition-colors hover:border-orange-400 hover:text-slate-900"
							>
								<ArrowDownCircle className="w-3.5 h-3.5" />
								Remove Compulsory
							</button>
						)}
					</div>

					{/* Right — Cancel + Edit/Save */}
					<div className="flex items-center gap-2">
						{isEditing && (
							<button
								type="button"
								onClick={handleCancelEdit}
								className="inline-flex items-center gap-1.5 border border-slate-200 text-slate-600 text-xs px-3 py-1.5 rounded-lg hover:bg-white hover:border-orange-400 hover:text-slate-900 transition-colors"
							>
								Cancel
							</button>
						)}
						{!policy.is_compulsory && (isOwner || isAdmin) && (
							isEditing ? (
								<button
									type="button"
									onClick={handleSave}
									disabled={isSaving || !editName.trim()}
									className="inline-flex items-center gap-1.5 rounded-lg border border-orange-500 bg-orange-500 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:opacity-40"
								>
									<Save className="w-3.5 h-3.5" />
									{isSaving ? "Saving..." : "Save"}
								</button>
							) : (
								<button
									type="button"
									onClick={() => setIsEditing(true)}
									className="inline-flex items-center gap-1.5 border border-slate-200 text-slate-600 text-xs px-3 py-1.5 rounded-lg hover:bg-white hover:border-orange-400 hover:text-slate-900 transition-colors"
								>
									<Edit3 className="w-3.5 h-3.5" />
									Edit
								</button>
							)
						)}
					</div>
				</div>
			</div>

			{/* Sandbox Panel */}
			<SandboxPanel
				policyId={policy.id}
				isOpen={sandboxOpen}
				onClose={() => setSandboxOpen(false)}
			/>
		</div>
	);
}

function PromoteCompulsoryDialog({
	policy,
	onClose,
	onConfirm,
}: {
	policy: GuardrailPolicy;
	onClose: () => void;
	onConfirm: (policyId: string, auditFirst: boolean) => void;
}) {
	const [mode, setMode] = useState<"audit" | "enforce">("audit");
	const [isSubmitting, setIsSubmitting] = useState(false);

	const config = policy.config || {};
	const patternRules = Array.isArray(config.pattern_rules) ? config.pattern_rules.length : 0;
	const customFilters = Array.isArray(config.custom_filters) ? config.custom_filters.length : 0;
	const hasBehavioral = !!(config.detect_prompt_injection && config.detect_prompt_injection !== "off")
		|| !!(config.detect_jailbreak_attempts && config.detect_jailbreak_attempts !== "off");
	const hasTokenBudget = !!(config.token_budget as Record<string, unknown>)?.max_total_tokens;
	const hasToolCall = !!(config.tool_call_policy as Record<string, unknown>);

	const handleConfirm = async () => {
		setIsSubmitting(true);
		try {
			await onConfirm(policy.id, mode === "audit");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
			<div className="relative w-full max-w-lg rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] overflow-hidden">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />
				{/* Header */}
				<div className="border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-start justify-between gap-4">
						<div className="flex items-center gap-3">
							<div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-orange-600 shadow-[0_10px_28px_rgba(15,23,42,0.08)]">
								<ArrowUpCircle className="w-6 h-6" />
							</div>
							<div>
								<h2 className="text-base font-semibold text-slate-900">
									Promote to Compulsory
								</h2>
								<p className="text-xs text-slate-500">
									&ldquo;{policy.name}&rdquo;
								</p>
							</div>
						</div>
						<button
							type="button"
							onClick={onClose}
							className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900"
							aria-label="Close modal"
						>
							<X className="h-5 w-5" />
						</button>
					</div>
					<p className="mt-4 text-sm text-slate-600">
						This policy will apply to <span className="text-slate-900 font-medium">all workflows</span> across the organization. It cannot be overridden or weakened by individual users.
					</p>
				</div>

				{/* Enforcement mode selection */}
				<div className="px-6 pb-4 space-y-2">
					<label className="block text-xs font-medium text-slate-500 mb-2">
						Enforcement mode
					</label>
					<button
						type="button"
						onClick={() => setMode("audit")}
						className={`w-full text-left rounded-lg border p-3 transition-colors ${
							mode === "audit"
								? "border-orange-500 bg-white"
								: "border-slate-200 bg-white hover:border-orange-400"
						}`}
					>
						<div className="flex items-center justify-between">
							<div className="flex items-center gap-2">
								<div className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center ${
									mode === "audit" ? "border-orange-500" : "border-slate-300"
								}`}>
									{mode === "audit" && <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />}
								</div>
								<span className="text-sm font-medium text-slate-900">Audit first</span>
								<span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium text-orange-700">
									Recommended
								</span>
							</div>
						</div>
						<p className="text-xs text-slate-500 mt-1 ml-5.5 pl-0.5">
							Log violations without blocking. Switch to enforce once you&apos;ve reviewed the data.
						</p>
					</button>
					<button
						type="button"
						onClick={() => setMode("enforce")}
						className={`w-full text-left rounded-lg border p-3 transition-colors ${
							mode === "enforce"
								? "border-red-400 bg-white"
								: "border-slate-200 bg-white hover:border-orange-400"
						}`}
					>
						<div className="flex items-center gap-2">
							<div className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center ${
								mode === "enforce" ? "border-red-400" : "border-slate-300"
							}`}>
								{mode === "enforce" && <div className="w-1.5 h-1.5 rounded-full bg-red-400" />}
							</div>
							<span className="text-sm font-medium text-slate-900">Enforce immediately</span>
						</div>
						<p className="text-xs text-slate-500 mt-1 ml-5.5 pl-0.5">
							Block violations on all workflows right away.
						</p>
					</button>
				</div>

				{/* Rule summary */}
				<div className="mx-6 rounded-lg border border-slate-200 bg-white p-3 mb-4">
					<p className="text-[10px] font-medium text-slate-500 capitalize tracking-wider mb-2">Policy includes</p>
					<div className="flex flex-wrap gap-2 text-xs text-slate-500">
						{patternRules > 0 && (
							<span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-0.5 text-orange-700">
								{patternRules} pattern {patternRules === 1 ? "rule" : "rules"}
							</span>
						)}
						{customFilters > 0 && (
							<span className="inline-flex items-center gap-1 rounded bg-white border border-slate-200 px-2 py-0.5 text-orange-700">
								{customFilters} custom {customFilters === 1 ? "filter" : "filters"}
							</span>
						)}
						{hasBehavioral && (
							<span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-2 py-0.5 text-slate-700">
								Behavioral checks
							</span>
						)}
						{hasTokenBudget && (
							<span className="inline-flex items-center gap-1 rounded border border-[#0DA931] bg-white px-2 py-0.5 text-[#0DA931]">
								Token budget
							</span>
						)}
						{hasToolCall && (
							<span className="inline-flex items-center gap-1 rounded border border-blue-300 bg-white px-2 py-0.5 text-blue-700">
								Tool restrictions
							</span>
						)}
						{patternRules === 0 && customFilters === 0 && !hasBehavioral && !hasTokenBudget && !hasToolCall && (
							<span className="text-slate-400">No rules configured</span>
						)}
					</div>
				</div>

				{/* Actions */}
				<div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200">
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 hover:border-orange-400 hover:text-slate-900 transition-colors"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleConfirm}
						disabled={isSubmitting}
						className="rounded-lg border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-40"
					>
						{isSubmitting ? "Promoting..." : "Promote to Compulsory"}
					</button>
				</div>
			</div>
		</div>
	);
}
