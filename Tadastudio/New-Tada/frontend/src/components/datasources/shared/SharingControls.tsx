"use client";

import { Globe, Loader, Lock, Save, Users } from "lucide-react";
import Button from "@/components/ui/Button";
import Toggle from "@/components/ui/Toggle";
import GroupSelector from "@/components/settings/groups/GroupSelector";

interface SharingControlsProps {
	isShared: boolean;
	onSharedChange: (shared: boolean) => void;
	groups: string[];
	onGroupsChange: (groups: string[]) => void;
	onSave: () => void;
	saving?: boolean;
	readOnly?: boolean;
	compact?: boolean;
	className?: string;
}

export default function SharingControls({
	isShared,
	onSharedChange,
	groups,
	onGroupsChange,
	onSave,
	saving = false,
	readOnly = false,
	compact = false,
	className = "",
}: SharingControlsProps) {
	if (readOnly) {
		return (
			<div className={`flex items-center gap-2 text-sm text-[color:var(--color-text-muted)] ${className}`}>
				<Lock className="w-4 h-4 text-amber-400" />
				<span>Read-only (shared by another user)</span>
			</div>
		);
	}

	if (compact) {
		return (
			<div className={`rounded-lg border border-[color:var(--color-border)]/50 bg-[color:var(--color-bg-secondary)]/30 p-3 space-y-3 ${className}`}>
				<div className="flex items-center justify-between">
					<div className="flex items-center gap-2">
						{isShared ? (
							<Globe className="w-4 h-4 text-blue-400" />
						) : (
							<Lock className="w-4 h-4 text-[color:var(--color-text-muted)]" />
						)}
						<div>
							<p className="text-sm font-medium text-slate-900">
								{isShared ? "Shared" : "Private"}
							</p>
							<p className="text-xs text-[color:var(--color-text-muted)]">
								{isShared
									? groups.length === 0
										? "Visible to everyone"
										: "Visible to selected groups"
									: "Only visible to you"}
							</p>
						</div>
					</div>
					<Toggle
						checked={isShared}
						onChange={(checked) => {
							onSharedChange(checked);
							if (!checked) onGroupsChange([]);
						}}
						activeColor="#3b82f6"
					/>
				</div>

				{isShared && (
					<div className="pt-3 border-t border-[color:var(--color-border)]/30">
						<GroupSelector
							selectedGroups={groups}
							onChange={onGroupsChange}
							placeholder="Select groups (optional, defaults to everyone)"
						/>
					</div>
				)}

				<div className="flex justify-end">
					<Button
						onClick={onSave}
						disabled={saving}
						variant="secondary"
						size="sm"
						icon={
							saving ? (
								<Loader className="w-4 h-4 animate-spin text-orange-500" />
							) : (
								<Save className="w-4 h-4" />
							)
						}
					>
						Save
					</Button>
				</div>
			</div>
		);
	}

	return (
		<div
			className={`rounded-xl p-6 ${className}`}
			style={{
				background: "var(--color-bg-secondary)",
				border: "1px solid var(--color-border)",
			}}
		>
			<h3 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
				{isShared ? (
					<Globe className="w-4 h-4 text-blue-400" />
				) : (
					<Users className="w-4 h-4" style={{ color: "var(--color-text-muted)" }} />
				)}
				Sharing: {isShared ? "Shared" : "Private"}
			</h3>

			<div className="flex items-start gap-4 flex-wrap">
				<div className="flex items-center gap-3">
					<span className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
						{isShared
							? groups.length === 0
								? "Visible to everyone"
								: "Visible to selected groups"
							: "Only visible to you"}
					</span>
					<Toggle
						checked={isShared}
						onChange={(checked) => {
							onSharedChange(checked);
							if (!checked) onGroupsChange([]);
						}}
						activeColor="#3b82f6"
					/>
				</div>

				{isShared && (
					<div className="flex-1 min-w-[260px]">
						<GroupSelector
							selectedGroups={groups}
							onChange={onGroupsChange}
							placeholder="Select groups (leave empty for everyone)..."
						/>
					</div>
				)}

				<Button
					onClick={onSave}
					disabled={saving}
					variant="secondary"
					size="sm"
					icon={
						saving ? (
							<Loader className="w-4 h-4 animate-spin text-orange-500" />
						) : (
							<Save className="w-4 h-4" />
						)
					}
				>
					Save
				</Button>
			</div>
		</div>
	);
}
