"use client";

import { Edit2, Folder, Shield, Trash2, Users } from "lucide-react";
import type { Group } from "@/types/api";

interface GroupListTableProps {
	groups: Group[];
	onEdit: (group: Group) => void;
	onDelete: (group: Group) => void;
	onViewMembers: (group: Group) => void;
}

export default function GroupListTable({
	groups,
	onEdit,
	onDelete,
	onViewMembers,
}: GroupListTableProps) {
	if (groups.length === 0) {
		return (
			<div className="flex flex-col items-center justify-center py-16">
				<Users className="mb-4 h-12 w-12 text-slate-400" />
				<p className="text-slate-600">No groups found</p>
			</div>
		);
	}

	return (
		<div className="overflow-x-auto">
			<table className="w-full">
				<thead>
					<tr className="border-b border-slate-200 bg-slate-50">
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Name
						</th>
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Description
						</th>
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Type
						</th>
						<th className="px-6 py-3 text-left text-xs font-semibold capitalize tracking-wider text-slate-600">
							Members
						</th>
						<th className="px-6 py-3 text-right text-xs font-semibold capitalize tracking-wider text-slate-600">
							Actions
						</th>
					</tr>
				</thead>
				<tbody>
					{groups.map((group) => (
						<tr
							key={group.id}
							className="cursor-pointer border-b border-slate-200 transition-colors hover:bg-slate-50"
							onClick={() => onViewMembers(group)}
						>
							<td className="px-6 py-4">
								<span className="font-medium text-slate-900">{group.name}</span>
							</td>
							<td className="px-6 py-4">
								<span className="text-sm text-slate-600">
									{group.description || "-"}
								</span>
							</td>
							<td className="px-6 py-4">
								{group.is_system ? (
									<span
										className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-800"
									>
										<Shield className="h-3 w-3" />
										System
									</span>
								) : (
									<span
										className="inline-flex items-center gap-1.5 rounded-full border border-[#0DA931] bg-[#F1F8E9] px-2.5 py-1 text-xs font-medium text-[#0DA931]"
									>
										<Folder className="h-3 w-3" />
										Custom
									</span>
								)}
							</td>
							<td className="px-6 py-4">
								<span className="text-sm text-slate-700">{group.member_count}</span>
							</td>
							<td className="px-6 py-4">
								<div
									className="flex items-center justify-end gap-1"
									onClick={(e) => e.stopPropagation()}
								>
									{!group.is_system && (
										<>
											<button
												type="button"
												className="rounded-[4px] p-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
												title="Edit group"
												onClick={() => onEdit(group)}
											>
												<Edit2 className="h-4 w-4" />
											</button>
											<button
												type="button"
												className="rounded-[4px] p-2 text-slate-600 transition-colors hover:bg-red-50 hover:text-red-700"
												title="Delete group"
												onClick={() => onDelete(group)}
											>
												<Trash2 className="h-4 w-4" />
											</button>
										</>
									)}
									<button
										type="button"
										className="rounded-[4px] p-2 text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
										title="View members"
										onClick={() => onViewMembers(group)}
									>
										<Users className="h-4 w-4" />
									</button>
								</div>
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}
