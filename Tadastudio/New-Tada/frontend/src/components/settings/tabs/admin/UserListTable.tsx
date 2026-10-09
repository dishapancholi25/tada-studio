"use client";

import { useState } from "react";
import {
	Edit2,
	Shield,
	User as UserIcon,
	Clock,
	Cpu,
	Loader2,
	Trash2,
} from "lucide-react";
import type { UserListItem, UserRole } from "@/types/api";
import UserAvatar from "@/components/ui/UserAvatar";
import { formatRelativeTime, formatDate } from "@/lib/date-utils";
import { adminUsersAPI } from "@/lib/admin-users-api";
import { useToast } from "@/contexts/ToastContext";

interface UserListTableProps {
	users: UserListItem[];
	onEdit: (user: UserListItem) => void;
	onUserUpdate?: () => void;
	onDelete?: (user: UserListItem) => void;
}

export default function UserListTable({
	users,
	onEdit,
	onUserUpdate,
	onDelete,
}: UserListTableProps) {
	const [updatingRole, setUpdatingRole] = useState<string | null>(null);
	const { showSuccess, showError } = useToast();

	// Get next role in cycle: PENDING -> USER -> ADMIN -> PENDING
	// SYSTEM accounts are auto-assigned and excluded from manual cycling
	const getNextRole = (currentRole: UserRole): UserRole => {
		if (currentRole === "PENDING") return "USER";
		if (currentRole === "USER") return "ADMIN";
		return "PENDING";
	};

	const handleRoleClick = async (
		e: React.MouseEvent,
		user: UserListItem,
	) => {
		e.stopPropagation();

		const nextRole = getNextRole(user.role);
		setUpdatingRole(user.id);

		try {
			await adminUsersAPI.updateUserRole(user.id, nextRole);
			showSuccess(`User role updated to ${nextRole}`);
			if (onUserUpdate) {
				onUserUpdate();
			}
		} catch (error) {
			console.error("Failed to update user role:", error);
			showError(
				"Failed to update user role",
				error instanceof Error ? error.message : undefined,
			);
		} finally {
			setUpdatingRole(null);
		}
	};

	const getRoleBadge = (user: UserListItem) => {
		const isUpdating = updatingRole === user.id;

		if (user.role === "SYSTEM") {
			return (
				<span
					className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
					style={{
						background: "rgba(139, 92, 246, 0.1)",
						color: "rgb(167, 139, 250)",
						border: "1px solid rgba(139, 92, 246, 0.25)",
					}}
					title="System account (managed identity / service principal)"
				>
					<Cpu className="w-3 h-3" />
					System
				</span>
			);
		}

		if (user.role === "ADMIN") {
			return (
				<button
					type="button"
					onClick={(e) => handleRoleClick(e, user)}
					disabled={isUpdating}
					className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-opacity cursor-pointer hover:opacity-80 disabled:opacity-50"
					style={{
						background: "rgba(59, 130, 246, 0.1)",
						color: "rgb(96, 165, 250)",
						border: "1px solid rgba(59, 130, 246, 0.25)",
					}}
					title="Click to change role (currently: ADMIN → next: PENDING)"
				>
					{isUpdating ? (
						<Loader2 className="w-3 h-3 animate-spin text-orange-500" />
					) : (
						<Shield className="w-3 h-3" />
					)}
					Admin
				</button>
			);
		}

		if (user.role === "PENDING") {
			return (
				<button
					type="button"
					onClick={(e) => handleRoleClick(e, user)}
					disabled={isUpdating}
					className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-opacity cursor-pointer hover:opacity-80 disabled:opacity-50"
					style={{
						background: "rgba(251, 191, 36, 0.1)",
						color: "rgb(251, 191, 36)",
						border: "1px solid rgba(251, 191, 36, 0.25)",
					}}
					title="Click to change role (currently: PENDING → next: USER)"
				>
					{isUpdating ? (
						<Loader2 className="w-3 h-3 animate-spin text-orange-500" />
					) : (
						<Clock className="w-3 h-3" />
					)}
					Pending
				</button>
			);
		}

		// USER role
		return (
			<button
				type="button"
				onClick={(e) => handleRoleClick(e, user)}
				disabled={isUpdating}
				className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-opacity cursor-pointer hover:opacity-80 disabled:opacity-50"
				style={{
					background: "rgba(156, 163, 175, 0.1)",
					color: "rgb(156, 163, 175)",
					border: "1px solid rgba(156, 163, 175, 0.25)",
				}}
				title="Click to change role (currently: USER → next: ADMIN)"
			>
				{isUpdating ? (
					<Loader2 className="w-3 h-3 animate-spin text-orange-500" />
				) : (
					<UserIcon className="w-3 h-3" />
				)}
				User
			</button>
		);
	};

	if (users.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center py-16">
				<UserIcon className="mb-4 h-12 w-12 text-slate-400" />
				<p className="text-slate-600">No users found</p>
			</div>
		);
	}

	return (
		<div className="overflow-x-auto">
			<table className="w-full">
				<thead>
					<tr className="border-b border-slate-200 bg-slate-50/80">
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Role
						</th>
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Name
						</th>
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Email
						</th>
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Last Active
						</th>
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Created
						</th>
						<th className="px-6 py-3 text-right text-xs font-semibold capitalize tracking-wider text-slate-600">
							Actions
						</th>
					</tr>
				</thead>
				<tbody>
					{users.map((user) => (
						<tr
							key={user.id}
							className="cursor-pointer border-b border-slate-200 transition-colors last:border-b-0 hover:bg-slate-50"
							onClick={() => onEdit(user)}
						>
							<td className="px-6 py-4">{getRoleBadge(user)}</td>
							<td className="px-6 py-4">
								<div className="flex items-center gap-3">
									<UserAvatar name={user.name} size="sm" />
									<span className="font-medium text-slate-900">{user.name || user.id}</span>
								</div>
							</td>
							<td className="px-6 py-4">
								<span className="text-sm text-slate-600">{user.email || "-"}</span>
							</td>
							<td className="px-6 py-4">
								<span className="text-sm text-slate-600">{formatRelativeTime(user.last_login_at)}</span>
							</td>
							<td className="px-6 py-4">
								<span className="text-sm text-slate-600">{formatDate(user.created_at)}</span>
							</td>
							<td className="px-6 py-4">
								<div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
									<button
										type="button"
										className="rounded-[4px] p-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
										title="Edit user"
										onClick={() => onEdit(user)}
									>
										<Edit2 className="h-4 w-4" />
									</button>
									{onDelete && (
										<button
											type="button"
											className="rounded-[4px] p-2 text-red-600 transition-colors hover:bg-red-50 hover:text-red-700"
											title="Delete user"
											onClick={() => onDelete(user)}
										>
											<Trash2 className="h-4 w-4" />
										</button>
									)}
								</div>
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}
