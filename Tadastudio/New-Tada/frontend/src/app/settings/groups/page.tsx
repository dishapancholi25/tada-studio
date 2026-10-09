"use client";

import { Plus, Search, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AppShell from "@/components/layout/AppShell";
import GroupListTable from "@/components/settings/groups/GroupListTable";
import GroupFormDialog from "@/components/settings/groups/GroupFormDialog";
import GroupMembersDialog from "@/components/settings/groups/GroupMembersDialog";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import Button from "@/components/ui/Button";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import type { Group } from "@/types/api";

export default function GroupManagementPage() {
	const [groups, setGroups] = useState<Group[]>([]);
	const [searchQuery, setSearchQuery] = useState("");
	const [isFormOpen, setIsFormOpen] = useState(false);
	const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
	const [editingGroup, setEditingGroup] = useState<Group | null>(null);
	const [deletingGroup, setDeletingGroup] = useState<Group | null>(null);
	const [loading, setLoading] = useState(true);

	const router = useRouter();
	const { user } = useAuth();
	const { showToast } = useToast();


	const isAdmin = user?.is_admin ?? false;

	useEffect(() => {
		// Redirect to new location under Admin settings
		if (user) {
			if (!isAdmin) {
				router.push("/");
			} else {
				router.push("/settings?tab=admin&subtab=groups");
			}
		}
	}, [user, isAdmin, router]);

	useEffect(() => {
		if (isAdmin) {
			loadGroups();
		}
	}, [isAdmin]);

	const loadGroups = async () => {
		try {
			setLoading(true);
			const data = await api.getGroups();
			setGroups(data.groups);
		} catch (error) {
			showToast(
				"error",
				error instanceof Error ? error.message : "Failed to load groups",
			);
		} finally {
			setLoading(false);
		}
	};

	const filteredGroups = groups
		.filter((g) => {
			if (!searchQuery) return true;
			return g.name.toLowerCase().includes(searchQuery.trim().toLowerCase());
		})
		.sort((a, b) => {
			// System groups first
			if (a.is_system && !b.is_system) return -1;
			if (!a.is_system && b.is_system) return 1;
			return a.name.localeCompare(b.name);
		});

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

	if (!isAdmin) {
		return null;
	}

	return (
		<AppShell>
		<div className="min-h-screen bg-gradient-to-br from-[color:var(--color-bg-secondary)] via-[color:var(--color-surface)] to-[color:var(--color-bg-secondary)]">

			<div className="container mx-auto px-6 py-8">
				{/* Page Header */}
				<div className="mb-8">
					<div className="flex items-center gap-3 mb-4">
						<div className="p-3 bg-gradient-to-br from-[color:var(--color-primary)]/20 to-[color:var(--color-accent)]/15 rounded-xl">
							<Users className="w-8 h-8 text-[color:var(--color-accent)]" />
						</div>
						<div>
							<h1 className="text-3xl font-bold text-slate-900">Groups</h1>
							<p className="text-[color:var(--color-text-muted)] mt-1">
								Manage user groups and memberships
							</p>
						</div>
					</div>
				</div>

				{/* Toolbar */}
				<div
					className="rounded-xl p-4 mb-6 flex items-center gap-4"
					style={{
						background: "var(--color-bg-secondary)",
						border: "1px solid var(--color-border)",
					}}
				>
					{/* Search */}
					<div className="relative flex-1 max-w-md">
						<Search
							className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4"
							style={{ color: "var(--color-text-muted)" }}
						/>
						<input
							type="text"
							value={searchQuery}
							onChange={(e) => setSearchQuery(e.target.value)}
							placeholder="Search groups..."
							className="w-full pl-10 pr-4 py-2 rounded-lg text-sm outline-none transition-colors"
							style={{
								background: "var(--color-surface)",
								border: "1px solid var(--color-border)",
								color: "var(--color-text-primary)",
							}}
							onFocus={(e) => {
								e.currentTarget.style.borderColor = "var(--color-primary)";
							}}
							onBlur={(e) => {
								e.currentTarget.style.borderColor = "var(--color-border)";
							}}
						/>
					</div>

					{/* Create Button */}
					<Button
						variant="primary"
						icon={<Plus className="w-4 h-4" />}
						onClick={handleCreateGroup}
					>
						Create Group
					</Button>
				</div>

				{/* Groups Table */}
				<div
					className="rounded-xl overflow-hidden"
					style={{
						background: "var(--color-surface)",
						border: "1px solid var(--color-border)",
					}}
				>
					{loading ? (
						<div className="flex items-center justify-center py-16">
							<div
								className="animate-pulse"
								style={{ color: "var(--color-text-muted)" }}
							>
								Loading groups...
							</div>
						</div>
					) : (
						<GroupListTable
							groups={filteredGroups}
							onEdit={handleEditGroup}
							onDelete={handleDeleteGroup}
							onViewMembers={handleViewMembers}
						/>
					)}
				</div>
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
			/>
		</div>
		</AppShell>
	);
}
