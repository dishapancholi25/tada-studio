"use client";

import { Search, Users } from "lucide-react";
import { useEffect, useState } from "react";
import UserListTable from "./UserListTable";
import UserEditPanel from "./UserEditPanel";
import Pagination from "@/components/ui/Pagination";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { adminUsersAPI } from "@/lib/admin-users-api";
import { useToast } from "@/contexts/ToastContext";
import type { UserListItem } from "@/types/api";
import Dropdown from "@/components/ui/Dropdown";

export default function UsersTabContent() {
	const [users, setUsers] = useState<UserListItem[]>([]);
	const [totalCount, setTotalCount] = useState(0);
	const [searchQuery, setSearchQuery] = useState("");
	const [roleFilter, setRoleFilter] = useState<string>("");
	const [currentPage, setCurrentPage] = useState(1);
	const [pageSize, setPageSize] = useState(20);
	const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
	const [deletingUser, setDeletingUser] = useState<{ id: string; displayName: string } | null>(null);
	const [loading, setLoading] = useState(true);
	const { showToast } = useToast();

	useEffect(() => {
		// Reset to page 1 when search or role filter changes
		setCurrentPage(1);
	}, [searchQuery, roleFilter]);

	useEffect(() => {
		loadUsers();
	}, [searchQuery, roleFilter, currentPage, pageSize]);

	const loadUsers = async () => {
		try {
			setLoading(true);
			const offset = (currentPage - 1) * pageSize;
			const data = await adminUsersAPI.listUsers({
				limit: pageSize,
				offset: offset,
				search: searchQuery || undefined,
				role: roleFilter || undefined,
			});
			setUsers(data.users);
			setTotalCount(data.total_count);
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to load users",
			);
		} finally {
			setLoading(false);
		}
	};

	const handleEditUser = (user: UserListItem) => {
		setSelectedUserId(user.id);
	};

	const handleClosePanel = () => {
		setSelectedUserId(null);
	};

	const handleSaved = () => {
		loadUsers();
	};

	const handlePageChange = (page: number) => {
		setCurrentPage(page);
	};

	const handlePageSizeChange = (size: number) => {
		setPageSize(size);
		setCurrentPage(1); // Reset to first page when changing page size
	};

	const handleDeleteUser = (user: UserListItem) => {
		setDeletingUser({
			id: user.id,
			displayName: user.name || user.email || user.id,
		});
	};

	const handleDeleteFromPanel = (userId: string, displayName: string) => {
		setSelectedUserId(null);
		setDeletingUser({ id: userId, displayName });
	};

	const confirmDeleteUser = async () => {
		if (!deletingUser) return;
		try {
			await adminUsersAPI.deleteUser(deletingUser.id);
			showToast("success", `User "${deletingUser.displayName}" deleted`);
			setDeletingUser(null);
			await loadUsers();
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to delete user",
			);
		}
	};

	return (
		<div className="p-6">
			{/* Header */}
			<div className="mb-6">
				<div className="mb-4 flex items-center justify-between">
					<div className="flex items-start gap-3">
						<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
							<Users className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h3 className="text-xl font-semibold tracking-tight text-slate-900">User Management</h3>
							<p className="mt-1 text-slate-600">
								{totalCount} total user{totalCount !== 1 ? "s" : ""}
							</p>
						</div>
					</div>
				</div>

				{/* Search and Filter */}
				<div className="flex max-w-2xl gap-3">
					<div className="relative flex-1">
						<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
						<input
							type="text"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							placeholder="Search users by name, email, or role..."
							className="w-full rounded-[4px] border border-slate-200 bg-white py-2 pl-10 pr-4 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15"
						/>
					</div>
					<Dropdown
						value={roleFilter}
						onChange={setRoleFilter}
						menuAppearance="light"
						width="trigger"
						options={[
							{ value: "", label: "All Roles" },
							{ value: "ADMIN", label: "Admin" },
							{ value: "USER", label: "User" },
							{ value: "SYSTEM", label: "System" },
							{ value: "PENDING", label: "Pending" },
						]}
					/>
				</div>
			</div>

			{/* Users Table */}
			<div className="overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
				{loading ? (
					<div className="flex items-center justify-center py-16">
						<div className="animate-pulse text-slate-600">Loading users...</div>
					</div>
				) : (
					<>
						<UserListTable
							users={users}
							onEdit={handleEditUser}
							onUserUpdate={loadUsers}
							onDelete={handleDeleteUser}
						/>
						<Pagination
							currentPage={currentPage}
							totalCount={totalCount}
							pageSize={pageSize}
							onPageChange={handlePageChange}
							onPageSizeChange={handlePageSizeChange}
						/>
					</>
				)}
			</div>

			{/* Edit Panel */}
			{selectedUserId && (
				<UserEditPanel
					userId={selectedUserId}
					onClose={handleClosePanel}
					onSaved={handleSaved}
					onDelete={handleDeleteFromPanel}
				/>
			)}

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={!!deletingUser}
				onClose={() => setDeletingUser(null)}
				onConfirm={confirmDeleteUser}
				title="Delete User"
				message={`Are you sure you want to permanently delete "${deletingUser?.displayName}"? This action cannot be undone.`}
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>
		</div>
	);
}
