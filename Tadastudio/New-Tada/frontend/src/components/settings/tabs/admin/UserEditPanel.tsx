"use client";

import { X, Shield, User as UserIcon, Users, Save, Clock, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import Button from "@/components/ui/Button";
import UserAvatar from "@/components/ui/UserAvatar";
import { adminUsersAPI } from "@/lib/admin-users-api";
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import type { UserDetail, Group } from "@/types/api";
import { formatRelativeTime, formatDateTime } from "@/lib/date-utils";

interface UserEditPanelProps {
	userId: string;
	onClose: () => void;
	onSaved?: () => void;
	onDelete?: (userId: string, displayName: string) => void;
}

export default function UserEditPanel({
	userId,
	onClose,
	onSaved,
	onDelete,
}: UserEditPanelProps) {
	const [user, setUser] = useState<UserDetail | null>(null);
	const [allGroups, setAllGroups] = useState<Group[]>([]);
	const [selectedGroupIds, setSelectedGroupIds] = useState<string[]>([]);
	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [mounted, setMounted] = useState(false);
	const { showToast } = useToast();
	const dialogRef = useFocusTrap<HTMLDivElement>(true);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEscapeKey(onClose, true);

	useEffect(() => {
		document.body.style.overflow = "hidden";
		return () => {
			document.body.style.overflow = "";
		};
	}, []);

	useEffect(() => {
		loadData();
	}, [userId]);

	const loadData = async () => {
		setLoading(true);
		try {
			const [userData, groupsData] = await Promise.all([
				adminUsersAPI.getUserDetail(userId),
				api.getGroups(),
			]);
			setUser(userData);
			setAllGroups(groupsData.groups);
			setSelectedGroupIds(userData.groups.map((g) => g.id));
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to load user data",
			);
		} finally {
			setLoading(false);
		}
	};

	const handleSave = async () => {
		if (!user) return;
		setSaving(true);
		try {
			await adminUsersAPI.updateUserGroups(user.id, selectedGroupIds);
			showToast("success", "User groups updated successfully");
			onSaved?.();
			onClose();
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to update user groups",
			);
		} finally {
			setSaving(false);
		}
	};

	const toggleGroup = (groupId: string) => {
		setSelectedGroupIds((prev) =>
			prev.includes(groupId)
				? prev.filter((id) => id !== groupId)
				: [...prev, groupId],
		);
	};

	const hasChanges =
		user &&
		JSON.stringify([...selectedGroupIds].sort()) !==
			JSON.stringify(user.groups.map((g) => g.id).sort());

	if (!mounted) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			{/* Backdrop */}
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

			{/* Panel */}
		<div
			ref={dialogRef}
			className="relative flex max-h-[85vh] w-full max-w-2xl flex-col rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)] animate-fadeIn"
			onClick={(e) => e.stopPropagation()}
		>
				{/* Header — Workflow Management style */}
				<div className="flex shrink-0 items-start justify-between border-b border-slate-200 px-6 pb-4 pt-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<UserIcon className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">Edit User</h2>
							<p className="mt-0.5 text-sm text-slate-600">Manage group memberships</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Body */}
				<div className="flex-1 space-y-6 overflow-y-auto px-6 pb-6">
					{loading ? (
						<div className="flex items-center justify-center py-12">
							<div className="animate-pulse text-slate-600">Loading user data...</div>
						</div>
					) : user ? (
						<>
							{/* User Information */}
							<div>
								<h3 className="mb-3 text-sm font-semibold capitalize tracking-wider text-slate-600">
									User Information
								</h3>
								<div className="rounded-[4px] border border-slate-200 bg-white p-4 shadow-sm">
									<div className="flex items-start gap-4">
										<UserAvatar name={user.name} size="lg" />
										<div className="flex-1 min-w-0">
											<div className="flex items-center gap-2 mb-2">
												<h4 className="text-lg font-semibold text-slate-900">
													{user.name || user.id}
												</h4>
												{user.role === "ADMIN" ? (
													<span
														className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
														style={{
															background: "rgba(59, 130, 246, 0.1)",
															color: "rgb(96, 165, 250)",
															border: "1px solid rgba(59, 130, 246, 0.25)",
														}}
													>
														<Shield className="w-3 h-3" />
														Admin
													</span>
												) : user.role === "PENDING" ? (
													<span
														className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
														style={{
															background: "rgba(251, 191, 36, 0.1)",
															color: "rgb(251, 191, 36)",
															border: "1px solid rgba(251, 191, 36, 0.25)",
														}}
													>
														<Clock className="w-3 h-3" />
														Pending
													</span>
												) : (
													<span
														className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
														style={{
															background: "rgba(156, 163, 175, 0.1)",
															color: "rgb(156, 163, 175)",
															border: "1px solid rgba(156, 163, 175, 0.25)",
														}}
													>
														<UserIcon className="w-3 h-3" />
														User
													</span>
												)}
											</div>
											<div className="mb-1 text-sm text-slate-600">
												{user.email || "No email"}
											</div>
											<div className="space-y-1 text-xs text-slate-500">
												<div>
													Last active: {formatRelativeTime(user.last_login_at)}
												</div>
												<div>Created: {formatDateTime(user.created_at)}</div>
											</div>
										</div>
									</div>
								</div>
							</div>

							{/* Group Memberships */}
							<div>
								<h3 className="mb-3 text-sm font-semibold capitalize tracking-wider text-slate-600">
									Group Memberships
								</h3>

								{allGroups.length === 0 ? (
									<p className="py-4 text-center text-sm text-slate-600">No groups available</p>
								) : (
									<div className="max-h-64 space-y-1 overflow-y-auto rounded-[4px] border border-slate-200 bg-white p-1">
										{allGroups.map((group) => {
											const isSelected = selectedGroupIds.includes(group.id);
											return (
												<label
													key={group.id}
													className={`flex cursor-pointer items-center gap-3 rounded-[4px] px-3 py-2.5 transition-colors hover:bg-slate-50 ${
														isSelected ? "bg-slate-100" : ""
													}`}
												>
													<input
														type="checkbox"
														checked={isSelected}
														onChange={() => toggleGroup(group.id)}
														className="accent-orange-500 rounded"
													/>
													<div className="min-w-0 flex-1">
														<div className="flex items-center gap-2">
															<div className="truncate text-sm font-medium text-slate-900">
																{group.name}
															</div>
															{group.is_system && (
																<span
																	className="text-xs px-2 py-0.5 rounded"
																	style={{
																		background: "rgba(59, 130, 246, 0.1)",
																		color: "rgb(96, 165, 250)",
																	}}
																>
																	System
																</span>
															)}
														</div>
														{group.description && (
															<div className="truncate text-xs text-slate-500">{group.description}</div>
														)}
													</div>
													<div className="shrink-0 text-xs text-slate-500">
														<Users className="h-4 w-4" />
													</div>
												</label>
											);
										})}
									</div>
								)}
							</div>
						</>
					) : (
						<div className="flex items-center justify-center py-12">
							<p className="text-slate-600">User not found</p>
						</div>
					)}
				</div>

				{/* Footer */}
				<div className="flex shrink-0 items-center justify-between gap-3 border-t border-slate-200 p-6 pt-4">
					<div>
						{onDelete && user && (
							<button
								type="button"
								className="inline-flex items-center gap-2 rounded-[4px] border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-700 transition-all hover:border-red-300 hover:bg-red-50"
								onClick={() =>
									onDelete(user.id, user.name || user.email || user.id)
								}
							>
								<Trash2 className="h-4 w-4" />
								Delete User
							</button>
						)}
					</div>
					<div className="flex items-center gap-3">
						<Button
							onClick={onClose}
							variant="secondary"
							className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
						>
							Cancel
						</Button>
						<Button
							onClick={handleSave}
							variant="primary"
							icon={<Save className="w-4 h-4" />}
							loading={saving}
							disabled={saving || !hasChanges}
							className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
						>
							Save Changes
						</Button>
					</div>
				</div>
			</div>
		</div>,
		document.body,
	);
}
