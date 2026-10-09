"use client";

import { Search, Trash2, UserPlus, Users, X } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import Button from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import type { Group, GroupMember, UserInfo } from "@/types/api";

interface GroupMembersDialogProps {
	group: Group;
	onClose: () => void;
	onMembersChanged?: () => void;
}

const SEARCH_INPUT =
	"w-full rounded-[4px] border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15";

export default function GroupMembersDialog({
	group,
	onClose,
	onMembersChanged,
}: GroupMembersDialogProps) {
	const [members, setMembers] = useState<GroupMember[]>([]);
	const [allUsers, setAllUsers] = useState<UserInfo[]>([]);
	const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);
	const [memberSearchQuery, setMemberSearchQuery] = useState("");
	const [addSearchQuery, setAddSearchQuery] = useState("");
	const [loading, setLoading] = useState(true);
	const [adding, setAdding] = useState(false);
	const [removingUserId, setRemovingUserId] = useState<string | null>(null);
	const [mounted, setMounted] = useState(false);
	const { showToast } = useToast();
	const dialogRef = useFocusTrap<HTMLDivElement>(true);
	const canManageMembers =
		!group.is_system || group.name === "Administrators";

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
	}, [group.id]);

	const loadData = async () => {
		setLoading(true);
		try {
			const [membersData, usersData] = await Promise.all([
				api.getGroupMembers(group.id),
				api.getAllUsers(),
			]);
			setMembers(membersData);
			setAllUsers(usersData);
		} catch {
			showToast("error", "Failed to load group members");
		} finally {
			setLoading(false);
		}
	};

	const handleRemoveMember = async (userId: string) => {
		setRemovingUserId(userId);
		try {
			await api.removeGroupMember(group.id, userId);
			setMembers((prev) => prev.filter((m) => m.user_id !== userId));
			onMembersChanged?.();
			showToast("success", "Member removed successfully");
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to remove member",
			);
		} finally {
			setRemovingUserId(null);
		}
	};

	const handleAddMembers = async () => {
		if (selectedUserIds.length === 0) return;
		setAdding(true);
		try {
			for (const userId of selectedUserIds) {
				await api.addGroupMember(group.id, userId);
			}
			showToast(
				"success",
				`Added ${selectedUserIds.length} member${selectedUserIds.length > 1 ? "s" : ""}`,
			);
			setSelectedUserIds([]);
			const updated = await api.getGroupMembers(group.id);
			setMembers(updated);
			onMembersChanged?.();
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to add members",
			);
		} finally {
			setAdding(false);
		}
	};

	const toggleUserSelection = (userId: string) => {
		setSelectedUserIds((prev) =>
			prev.includes(userId)
				? prev.filter((id) => id !== userId)
				: [...prev, userId],
		);
	};

	const memberUserIds = new Set(members.map((m) => m.user_id));
	const availableUsers = allUsers.filter((u) => !memberUserIds.has(u.id));
	const filteredAvailableUsers = availableUsers.filter((u) => {
		if (!addSearchQuery) return true;
		const query = addSearchQuery.toLowerCase();
		return (
			(u.email && u.email.toLowerCase().includes(query)) ||
			(u.name && u.name.toLowerCase().includes(query))
		);
	});

	const filteredMembers = members.filter((m) => {
		if (!memberSearchQuery) return true;
		const query = memberSearchQuery.toLowerCase();
		return (
			(m.user_email && m.user_email.toLowerCase().includes(query)) ||
			(m.user_name && m.user_name.toLowerCase().includes(query)) ||
			m.user_id.toLowerCase().includes(query)
		);
	});

	if (!mounted) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
		>
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

			<div
				ref={dialogRef}
				className="relative flex max-h-[85vh] w-full max-w-2xl animate-fadeIn flex-col overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.12)]"
				onClick={(e) => e.stopPropagation()}
			>
				{/* Header — Workflow Management style */}
				<div className="flex shrink-0 items-start justify-between border-b border-slate-200 px-6 pb-4 pt-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Users className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">
								{group.name} — Members
							</h2>
							<p className="mt-0.5 text-sm text-slate-600">
								{members.length} member{members.length !== 1 ? "s" : ""}
								{!canManageMembers && " (read-only)"}
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Body */}
				<div className="flex-1 space-y-6 overflow-y-auto bg-white px-6 py-5">
					{loading ? (
						<div className="flex items-center justify-center py-12">
							<div className="animate-pulse text-slate-600">Loading members...</div>
						</div>
					) : (
						<>
							{/* Current Members */}
							<div>
								<h3 className="mb-3 text-sm font-semibold capitalize tracking-wider text-slate-600">
									Current Members
								</h3>

								{members.length > 5 && (
									<div className="relative mb-3">
										<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
										<input
											type="text"
											value={memberSearchQuery}
											onChange={(e) => setMemberSearchQuery(e.target.value)}
											placeholder="Search members..."
											className={SEARCH_INPUT}
										/>
									</div>
								)}

								{filteredMembers.length === 0 ? (
									<p className="py-4 text-center text-sm text-slate-600">
										{memberSearchQuery
											? "No members match your search"
											: "No members in this group"}
									</p>
								) : (
									<div className="space-y-2">
										{filteredMembers.map((member) => (
											<div
												key={member.user_id}
												className="flex items-center justify-between rounded-[4px] border border-slate-200 bg-white px-3 py-2.5 shadow-[0_8px_24px_rgba(15,23,42,0.04)] transition-colors hover:border-orange-400"
											>
												<div className="min-w-0 flex-1">
													<div className="truncate text-sm font-medium text-slate-900">
														{member.user_name || member.user_id}
													</div>
													{member.user_email && (
														<div className="truncate text-xs text-slate-600">
															{member.user_email}
														</div>
													)}
												</div>
												{canManageMembers && !member.is_protected && (
													<button
														type="button"
														className="ml-2 shrink-0 rounded-[4px] p-1.5 text-slate-600 transition-colors hover:bg-red-50 hover:text-red-700"
														title="Remove member"
														disabled={removingUserId === member.user_id}
														onClick={() => handleRemoveMember(member.user_id)}
													>
														<Trash2 className="h-4 w-4" />
													</button>
												)}
												{canManageMembers && member.is_protected && (
													<span
														className="ml-2 shrink-0 rounded-[4px] border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-700"
														title="This admin is configured via environment variables and cannot be removed"
													>
														env admin
													</span>
												)}
											</div>
										))}
									</div>
								)}
							</div>

							{canManageMembers && (
								<div>
									<h3 className="mb-3 text-sm font-semibold capitalize tracking-wider text-slate-600">
										Add Members
									</h3>

									<div className="relative mb-3">
										<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
										<input
											type="text"
											value={addSearchQuery}
											onChange={(e) => setAddSearchQuery(e.target.value)}
											placeholder="Search users to add..."
											className={SEARCH_INPUT}
										/>
									</div>

									{filteredAvailableUsers.length === 0 ? (
										<p className="py-4 text-center text-sm text-slate-600">
											{addSearchQuery
												? "No users match your search"
												: "All users are already members"}
										</p>
									) : (
										<>
											<div className="max-h-48 space-y-1 overflow-y-auto rounded-[4px] border border-slate-200 bg-white p-1">
												{filteredAvailableUsers.map((user) => {
													const isSelected = selectedUserIds.includes(user.id);
													return (
														<label
															key={user.id}
															className={`flex cursor-pointer items-center gap-3 rounded-[4px] px-3 py-2 transition-colors ${
																isSelected
																	? "border border-orange-400 bg-slate-50"
																	: "border border-transparent hover:bg-slate-50"
															}`}
														>
															<input
																type="checkbox"
																checked={isSelected}
																onChange={() => toggleUserSelection(user.id)}
																className="rounded border-slate-300 text-orange-600 focus:ring-orange-500/25"
															/>
															<div className="min-w-0 flex-1">
																<div className="truncate text-sm font-medium text-slate-900">
																	{user.name || user.id}
																</div>
																<div className="truncate text-xs text-slate-600">
																	{user.email}
																</div>
															</div>
														</label>
													);
												})}
											</div>

											{selectedUserIds.length > 0 && (
												<div className="mt-3">
													<Button
														variant="primary"
														size="sm"
														icon={<UserPlus className="h-4 w-4" />}
														loading={adding}
														disabled={adding}
														onClick={handleAddMembers}
														className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
													>
														Add {selectedUserIds.length} Selected
													</Button>
												</div>
											)}
										</>
									)}
								</div>
							)}
						</>
					)}
				</div>

				{/* Footer */}
				<div className="flex shrink-0 items-center justify-end border-t border-slate-200 bg-white px-6 py-4">
					<Button
						onClick={onClose}
						variant="secondary"
						className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
					>
						Close
					</Button>
				</div>
			</div>
		</div>,
		document.body,
	);
}
