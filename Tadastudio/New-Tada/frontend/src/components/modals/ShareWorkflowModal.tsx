"use client";

import { Search, Share2, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

import { useNotification } from "@/contexts/NotificationContext";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import { api } from "@/lib/api";
import type { UserInfo } from "@/types/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ShareWorkflowModalProps {
	isOpen: boolean;
	onClose: () => void;
	workflowId: string;
}

interface WorkflowMember {
	user_id: string;
	user_name: string | null;
	user_email: string | null;
	role: string;
	is_owner: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ShareWorkflowModal({
	isOpen,
	onClose,
	workflowId,
}: ShareWorkflowModalProps) {
	const { showSuccess, showError } = useNotification();
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);
	useEscapeKey(onClose, isOpen);

	const [mounted, setMounted] = useState(false);
	const [members, setMembers] = useState<WorkflowMember[]>([]);
	const [allUsers, setAllUsers] = useState<UserInfo[]>([]);
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedRole, setSelectedRole] = useState<"editor" | "viewer">(
		"viewer",
	);
	const [loading, setLoading] = useState(true);
	const [adding, setAdding] = useState(false);
	const [canManage, setCanManage] = useState(false);

	// Mount guard for portal
	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	// Prevent body scroll when open
	useEffect(() => {
		if (isOpen) {
			document.body.style.overflow = "hidden";
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [isOpen]);

	// Fetch members and users when modal opens
	const fetchData = useCallback(async () => {
		if (!workflowId) return;
		setLoading(true);
		try {
			const [membersResult, usersResult] = await Promise.all([
				api.getWorkflowMembers(workflowId),
				api.getAllUsers(),
			]);
			setMembers(membersResult.members);
			setCanManage(membersResult.can_manage ?? false);
			setAllUsers(usersResult);
		} catch (err) {
			const message =
				err instanceof Error ? err.message : "Failed to load sharing data";
			showError("Share Error", message);
		} finally {
			setLoading(false);
		}
	}, [workflowId, showError]);

	useEffect(() => {
		if (isOpen) {
			fetchData();
			setSearchQuery("");
		}
	}, [isOpen, fetchData]);

	// Filter users for the search dropdown
	const memberIds = useMemo(
		() => new Set(members.map((m) => m.user_id)),
		[members],
	);

	const filteredUsers = useMemo(() => {
		if (!searchQuery.trim()) return [];
		const query = searchQuery.toLowerCase();
		return allUsers
			.filter((u) => !memberIds.has(u.id))
			.filter(
				(u) =>
					(u.name && u.name.toLowerCase().includes(query)) ||
					(u.email && u.email.toLowerCase().includes(query)),
			)
			.slice(0, 8);
	}, [allUsers, memberIds, searchQuery]);

	// Add member
	const handleAddMember = useCallback(
		async (userId: string) => {
			setAdding(true);
			try {
				await api.addWorkflowMember(workflowId, userId, selectedRole);
				showSuccess("Member added", `User added as ${selectedRole}`);
				setSearchQuery("");
				await fetchData();
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to add member";
				showError("Share Error", message);
			} finally {
				setAdding(false);
			}
		},
		[workflowId, selectedRole, fetchData, showSuccess, showError],
	);

	// Remove member
	const handleRemoveMember = useCallback(
		async (userId: string) => {
			try {
				await api.removeWorkflowMember(workflowId, userId);
				showSuccess("Member removed");
				await fetchData();
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to remove member";
				showError("Share Error", message);
			}
		},
		[workflowId, fetchData, showSuccess, showError],
	);

	// Update role
	const handleRoleChange = useCallback(
		async (userId: string, newRole: string) => {
			try {
				await api.updateWorkflowMemberRole(workflowId, userId, newRole);
				await fetchData();
			} catch (err) {
				const message =
					err instanceof Error ? err.message : "Failed to update role";
				showError("Share Error", message);
			}
		},
		[workflowId, fetchData, showError],
	);

	if (!mounted || !isOpen) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			{/* Backdrop */}
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

			{/* Modal shell */}
			<div
				ref={dialogRef}
				className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] animate-fadeIn"
				onClick={(e) => e.stopPropagation()}
				role="dialog"
				aria-modal="true"
				aria-label="Share Workflow"
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />

				{/* Header */}
				<div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<Share2 className="h-4.5 w-4.5 text-orange-600" />
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">
								Share Workflow
							</h2>
							<p className="text-xs text-slate-500">
								Manage who can access this workflow
							</p>
						</div>
					</div>
					<button
						onClick={onClose}
						className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Body */}
				<div className="px-6 py-4">
					{/* Add member section (owner only) */}
					{canManage && (
					<>
					<div className="mb-4">
						<div className="flex gap-2">
							<div className="relative flex-1">
								<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
								<input
									type="text"
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									placeholder="Search users by name or email..."
									className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 outline-none transition-colors hover:border-orange-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
								/>
							</div>
							<select
								value={selectedRole}
								onChange={(e) =>
									setSelectedRole(e.target.value as "editor" | "viewer")
								}
								className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none transition-colors hover:border-orange-300 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20"
							>
								<option value="viewer">Viewer</option>
								<option value="editor">Editor</option>
							</select>
						</div>

						{/* Search results dropdown */}
						{filteredUsers.length > 0 && (
							<div className="mt-2 max-h-48 overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-[0_18px_44px_rgba(15,23,42,0.10)]">
								{filteredUsers.map((user) => (
									<button
										key={user.id}
										onClick={() => handleAddMember(user.id)}
										disabled={adding}
										className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-slate-50 disabled:opacity-50"
									>
										<div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-orange-200 bg-orange-100 text-sm font-medium text-orange-700">
											{(user.name?.[0] || user.email?.[0] || "?").toUpperCase()}
										</div>
										<div className="min-w-0 flex-1">
											<div className="truncate text-sm font-medium text-slate-900">
												{user.name || "Unnamed"}
											</div>
											{user.email && (
												<div className="truncate text-xs text-slate-500">
													{user.email}
												</div>
											)}
										</div>
									</button>
								))}
							</div>
						)}

						{searchQuery.trim() &&
							filteredUsers.length === 0 &&
							!loading && (
								<p className="mt-2 text-center text-xs text-slate-500">
									No matching users found
								</p>
							)}
					</div>

					{/* Divider */}
					<div className="mb-4 border-t border-slate-200" />
					</>
					)}

					{/* Current members */}
					<div>
						<h3 className="mb-3 text-xs font-semibold capitalize tracking-wider text-slate-500">
							Members ({members.length})
						</h3>

						{loading ? (
							<div className="flex justify-center py-8">
								<div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500" />
							</div>
						) : (
							<div className="max-h-64 space-y-1 overflow-y-auto">
								{members.map((member) => (
									<div
										key={member.user_id}
										className="flex items-center gap-3 rounded-xl border border-transparent px-3 py-2.5 transition-colors hover:border-orange-300 hover:bg-white"
									>
										{/* Avatar */}
										<div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full border border-orange-200 bg-orange-100 text-sm font-medium text-orange-700">
											{(
												member.user_name?.[0] ||
												member.user_email?.[0] ||
												"?"
											).toUpperCase()}
										</div>

										{/* Info */}
										<div className="min-w-0 flex-1">
											<div className="truncate text-sm font-medium text-slate-900">
												{member.user_name || "Unnamed"}
											</div>
											{member.user_email && (
												<div className="truncate text-xs text-slate-500">
													{member.user_email}
												</div>
											)}
										</div>

										{/* Role */}
										{member.is_owner ? (
											<span className="rounded-full border border-orange-200 bg-white px-2.5 py-1 text-xs font-medium text-orange-700">
												Owner
											</span>
										) : canManage ? (
											<div className="flex items-center gap-1.5">
												<select
													value={member.role}
													onChange={(e) =>
														handleRoleChange(member.user_id, e.target.value)
													}
													className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 outline-none transition-colors hover:border-orange-300 focus:border-orange-500"
												>
													<option value="viewer">Viewer</option>
													<option value="editor">Editor</option>
												</select>
												<button
													onClick={() => handleRemoveMember(member.user_id)}
													className="rounded-lg p-1 text-slate-400 transition-colors hover:bg-red-50 hover:text-red-600"
													aria-label={`Remove ${member.user_name || member.user_email}`}
												>
													<Trash2 className="h-3.5 w-3.5" />
												</button>
											</div>
										) : (
											<span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 capitalize">
												{member.role}
											</span>
										)}
									</div>
								))}
							</div>
						)}
					</div>
				</div>

				{/* Footer */}
				<div className="border-t border-slate-200 bg-white px-6 py-4">
					<button
						onClick={onClose}
						className="w-full rounded-xl border border-orange-500 bg-orange-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
					>
						Done
					</button>
				</div>
			</div>
		</div>,
		document.body,
	);
}
