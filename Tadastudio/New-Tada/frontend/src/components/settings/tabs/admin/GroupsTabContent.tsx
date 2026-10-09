"use client";

import { Plus, Search, Users } from "lucide-react";
import { useEffect, useState } from "react";
import GroupFormDialog from "@/components/settings/groups/GroupFormDialog";
import GroupListTable from "@/components/settings/groups/GroupListTable";

import GroupMembersDialog from "@/components/settings/groups/GroupMembersDialog";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Pagination from "@/components/ui/Pagination";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import type { Group } from "@/types/api";

export default function GroupsTabContent() {
	const [groups, setGroups] = useState<Group[]>([]);
	const [totalCount, setTotalCount] = useState(0);
	const [searchQuery, setSearchQuery] = useState("");
	const [currentPage, setCurrentPage] = useState(1);
	const [pageSize, setPageSize] = useState(20);
	const [isFormOpen, setIsFormOpen] = useState(false);
	const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
	const [editingGroup, setEditingGroup] = useState<Group | null>(null);
	const [deletingGroup, setDeletingGroup] = useState<Group | null>(null);
	const [loading, setLoading] = useState(true);
	const { showToast } = useToast();

	// biome-ignore lint/correctness/useExhaustiveDependencies: reset page only when search changes
	useEffect(() => {
		// Reset to page 1 when search changes
		setCurrentPage(1);
	}, [searchQuery]);

	// biome-ignore lint/correctness/useExhaustiveDependencies: loadGroups re-declared on each render; deps are the trigger conditions
	useEffect(() => {
		loadGroups();
	}, [searchQuery, currentPage, pageSize]);

	const loadGroups = async () => {
		try {
			setLoading(true);
			const offset = (currentPage - 1) * pageSize;
			const data = await api.getGroups({
				limit: pageSize,
				offset: offset,
				search: searchQuery || undefined,
			});
			setGroups(data.groups);
			setTotalCount(data.total_count);
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to load groups",
			);
		} finally {
			setLoading(false);
		}
	};

	const handlePageChange = (page: number) => {
		setCurrentPage(page);
	};

	const handlePageSizeChange = (size: number) => {
		setPageSize(size);
		setCurrentPage(1); // Reset to first page when changing page size
	};

	const handleCreateGroup = () => {
		setEditingGroup(null);
		setIsFormOpen(true);
	};

	const handleEditGroup = (group: Group) => {
		setEditingGroup(group);
		setIsFormOpen(true);
	};

	const handleDeleteGroup = (group: Group) => {
		setDeletingGroup(group);
	};

	const confirmDeleteGroup = async () => {
		if (!deletingGroup) return;
		try {
			await api.deleteGroup(deletingGroup.id);
			showToast("success", `Group "${deletingGroup.name}" deleted`);
			setDeletingGroup(null);
			await loadGroups();
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to delete group",
			);
		}
	};

	const handleSaveGroup = async (name: string, description?: string) => {
		try {
			if (editingGroup) {
				await api.updateGroup(editingGroup.id, name, description);
				showToast("success", `Group "${name}" updated`);
			} else {
				await api.createGroup(name, description);
				showToast("success", `Group "${name}" created`);
			}
			await loadGroups();
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to save group",
			);
			throw error;
		}
	};

	const handleViewMembers = (group: Group) => {
		setSelectedGroup(group);
	};

	return (
		<div>
			<div className="p-6">
				{/* Header */}
				<div className="mb-6">
					<div className="mb-4 flex items-center justify-between">
						<div className="flex items-center gap-3">
							<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
								<Users className="h-5 w-5 text-orange-600" />
							</div>
							<div>
								<h3 className="text-xl font-semibold tracking-tight text-slate-900">
									Group Management
								</h3>
								<p className="mt-1 text-sm text-slate-600">
									{totalCount} total group{totalCount !== 1 ? "s" : ""}
								</p>
							</div>
						</div>
						<Button
							variant="primary"
							icon={<Plus className="h-4 w-4" />}
							onClick={handleCreateGroup}
							className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
						>
							Create Group
						</Button>
					</div>

					{/* Search */}
					<div className="relative max-w-md">
						<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
						<input
							type="text"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							placeholder="Search groups..."
							className="w-full rounded-[4px] border border-slate-200 bg-white py-2 pl-10 pr-4 text-sm text-slate-900 outline-none transition-colors placeholder:text-slate-400 hover:border-orange-400 focus:border-orange-500 focus:ring-2 focus:ring-orange-500/15"
						/>
					</div>
				</div>

				{/* Groups Table */}
				<div className="overflow-hidden rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
					{loading ? (
						<div className="flex items-center justify-center py-16">
							<div className="animate-pulse text-slate-600">Loading groups...</div>
						</div>
					) : (
						<>
							<GroupListTable
								groups={groups}
								onEdit={handleEditGroup}
								onDelete={handleDeleteGroup}
								onViewMembers={handleViewMembers}
							/>
							<Pagination
								currentPage={currentPage}
								totalCount={totalCount}
								pageSize={pageSize}
								onPageChange={handlePageChange}
								onPageSizeChange={handlePageSizeChange}
								appearance="light"
							/>
						</>
					)}
				</div>

				{/* Dialogs */}
				<GroupFormDialog
					open={isFormOpen}
					group={editingGroup}
					onClose={() => {
						setIsFormOpen(false);
						setEditingGroup(null);
					}}
					onSave={handleSaveGroup}
				/>

				{selectedGroup && (
					<GroupMembersDialog
						group={selectedGroup}
						onClose={() => setSelectedGroup(null)}
						onMembersChanged={loadGroups}
					/>
				)}

				<ConfirmDialog
					isOpen={!!deletingGroup}
					onClose={() => setDeletingGroup(null)}
					onConfirm={confirmDeleteGroup}
					title="Delete Group"
					message={`Are you sure you want to delete the group "${deletingGroup?.name}"? This action cannot be undone.`}
					confirmText="Delete"
					variant="danger"
					surface="light"
				/>
			</div>
		</div>
	);
}
