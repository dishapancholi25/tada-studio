"use client";

import { Coins, Edit2, Folder, Globe, Lock, Plus, Save, Users, X } from "lucide-react";
import { useState } from "react";
import Button from "@/components/ui/Button";
import FormInput from "@/components/ui/FormInput";
import FormTextarea from "@/components/ui/FormTextarea";
import GroupSelector from "@/components/settings/groups/GroupSelector";
import Dropdown from "@/components/ui/Dropdown";

export type CollectionFilterTab = 'all' | 'my' | 'shared';

export interface Collection {
	id: string;
	name: string;
	description?: string;
	visible_to_groups?: string[];
	is_read_only?: boolean;
	created_by_name?: string;
}

export interface CollectionStats {
	processedCount: number;
	failedCount: number;
	totalSize: number;
	totalTokens: number;
	totalCost: number;
}

interface CollectionSidebarProps {
	collections: Collection[];
	selectedCollection: string | null;
	onSelectCollection: (id: string | null) => void;
	onCreateCollection: (name: string, description: string) => Promise<void>;
	onDeleteCollection: (id: string) => void;
	stats: CollectionStats;
	loading?: boolean;
	isCreatingCollection: boolean;
	onStartCreate: () => void;
	onCancelCreate: () => void;
	newCollectionName: string;
	newCollectionDescription: string;
	onNewCollectionNameChange: (name: string) => void;
	onNewCollectionDescriptionChange: (description: string) => void;
	formatFileSize: (bytes: number) => string;
	className?: string;
	activeTab?: CollectionFilterTab;
	onTabChange?: (tab: CollectionFilterTab) => void;
	onUpdateVisibility?: (collectionId: string, visibleToGroups: string[]) => Promise<void>;
}

interface CollectionDropdownProps {
	collections: Collection[];
	selectedCollection: string | null;
	onSelectCollection: (id: string | null) => void;
	onCreateNew: () => void;
}

const NEW_COLLECTION_NAME_ID = "documents-tab-new-collection-name";

function isGlobalCollection(collection: Collection): boolean {
	return collection.visible_to_groups?.includes('__all__') ?? false;
}

function hasGroupRestrictions(collection: Collection): boolean {
	const groups = collection.visible_to_groups ?? [];
	return groups.length > 0 && !groups.includes('__all__');
}

function getCollectionLabel(collection: Collection): string {
	let label = collection.name;
	if (isGlobalCollection(collection)) {
		label = `\u{1F310} ${label}`;
	}
	if (collection.is_read_only) {
		label = `${label} \u{1F512}`;
	}
	return label;
}

function getCollectionDescription(collection: Collection): string | undefined {
	if (collection.is_read_only && collection.created_by_name) {
		const base = collection.description ? `${collection.description} \u00B7 ` : '';
		return `${base}Created by ${collection.created_by_name}`;
	}
	if (hasGroupRestrictions(collection)) {
		const groupNames = (collection.visible_to_groups ?? []).join(', ');
		const base = collection.description ? `${collection.description} \u00B7 ` : '';
		return `${base}Shared with: ${groupNames}`;
	}
	return collection.description;
}

// Compact dropdown for mobile view
export function CollectionDropdown({
	collections,
	selectedCollection,
	onSelectCollection,
	onCreateNew,
}: CollectionDropdownProps) {
	const hasCollections = collections.length > 0;

	return (
		<div className="flex items-center gap-3">
			<div className="flex-1">
				<Dropdown
					value={selectedCollection || ""}
					onChange={onSelectCollection}
					options={collections.map((col) => ({
						value: col.id,
						label: getCollectionLabel(col),
						description: getCollectionDescription(col),
					}))}
					placeholder={hasCollections ? "Select collection" : "No collections"}
				/>
			</div>
			<Button
				onClick={onCreateNew}
				size="sm"
				icon={<Plus className="w-4 h-4" />}
			>
				<span className="hidden sm:inline">New</span>
			</Button>
		</div>
	);
}

const FILTER_TABS: { key: CollectionFilterTab; label: string }[] = [
	{ key: 'all', label: 'All' },
	{ key: 'my', label: 'My Collections' },
	{ key: 'shared', label: 'Shared' },
];

export default function CollectionSidebar({
	collections,
	selectedCollection,
	onSelectCollection,
	onCreateCollection,
	onDeleteCollection,
	stats,
	isCreatingCollection,
	onStartCreate,
	onCancelCreate,
	newCollectionName,
	newCollectionDescription,
	onNewCollectionNameChange,
	onNewCollectionDescriptionChange,
	formatFileSize,
	className,
	activeTab = 'all',
	onTabChange,
	onUpdateVisibility,
}: CollectionSidebarProps) {
	const hasSelectedCollection = Boolean(selectedCollection);
	const hasCollections = collections.length > 0;

	const [isEditingVisibility, setIsEditingVisibility] = useState(false);
	const [isEditGlobalVisibility, setIsEditGlobalVisibility] = useState(false);
	const [editVisibilityGroups, setEditVisibilityGroups] = useState<string[]>([]);

	const selectedCol = collections.find((c) => c.id === selectedCollection);

	const handleCreateCollection = async () => {
		if (!newCollectionName.trim()) return;
		await onCreateCollection(newCollectionName, newCollectionDescription);
	};

	const handleStartEditVisibility = () => {
		if (selectedCol) {
			const groups = selectedCol.visible_to_groups ?? [];
			const isShared = groups.length > 0;
			setIsEditGlobalVisibility(isShared);
			setEditVisibilityGroups(isShared ? groups.filter(g => g !== '__all__') : []);
			setIsEditingVisibility(true);
		}
	};

	const handleSaveVisibility = async () => {
		if (selectedCol && onUpdateVisibility) {
			const groups = isEditGlobalVisibility
				? (editVisibilityGroups.length > 0 ? editVisibilityGroups : ['__all__'])
				: [];
			await onUpdateVisibility(selectedCol.id, groups);
			setIsEditingVisibility(false);
			setIsEditGlobalVisibility(false);
		}
	};

	const handleCancelEditVisibility = () => {
		setIsEditingVisibility(false);
		setIsEditGlobalVisibility(false);
		setEditVisibilityGroups([]);
	};

	return (
		<aside className={`flex-shrink-0 space-y-6 ${className || ""}`}>
			<div
				className="rounded-2xl border-2 p-5 space-y-5 transition-all duration-200 bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-bg-secondary)]"
				style={{
					borderColor: hasSelectedCollection
						? "var(--color-border)"
						: "rgba(var(--color-primary-rgb), 0.55)",
					boxShadow: hasSelectedCollection
						? "0 20px 55px rgba(0,0,0,0.55)"
						: "0 0 0 1px rgba(var(--color-primary-rgb), 0.35), 0 20px 55px rgba(0,0,0,0.55)",
				}}
			>
				{/* Header */}
				<div className="flex items-start justify-between gap-3">
					<div className="flex items-center gap-2">
						<Folder className="w-5 h-5 text-[color:var(--color-accent)]" />
						<div>
							<h3 className="text-base font-semibold text-slate-900">
								Collections
							</h3>
							<p className="text-xs text-[color:var(--color-text-muted)]">
								Organize documents into focused groups
							</p>
						</div>
					</div>
					<Button
						onClick={() => {
							if (isCreatingCollection) {
								onCancelCreate();
							} else {
								onStartCreate();
							}
						}}
						variant={isCreatingCollection ? "ghost" : "secondary"}
						size="sm"
						icon={
							isCreatingCollection ? (
								<X className="w-4 h-4" />
							) : (
								<Plus className="w-4 h-4" />
							)
						}
					>
						{isCreatingCollection ? "Cancel" : "New"}
					</Button>
				</div>

				{/* Filter Tabs */}
				{onTabChange && (
					<div className="flex gap-2">
						{FILTER_TABS.map((tab) => (
							<button
								key={tab.key}
								type="button"
								onClick={() => onTabChange(tab.key)}
								className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
								style={{
									color: activeTab === tab.key ? "var(--nav-link-active)" : "var(--color-text-primary)",
									background: activeTab === tab.key ? "rgba(var(--color-primary-rgb), 0.18)" : "transparent",
									border: activeTab === tab.key ? "1px solid var(--nav-link-active)" : "1px solid var(--color-border)",
								}}
							>
								{tab.label}
							</button>
						))}
					</div>
				)}

				{/* Collection Select */}
				<Dropdown
					value={selectedCollection || ""}
					onChange={onSelectCollection}
					options={collections.map((col) => ({
						value: col.id,
						label: getCollectionLabel(col),
						description: getCollectionDescription(col),
					}))}
					placeholder={
						hasCollections
							? "Select a collection"
							: "Create your first collection"
					}
					onAdd={onStartCreate}
					onDelete={selectedCol?.is_read_only ? undefined : onDeleteCollection}
					addLabel="Create collection"
				/>

				{/* Create Collection Form */}
				{isCreatingCollection && (
					<div className="rounded-xl border space-y-3 p-4 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
						<FormInput
							id={NEW_COLLECTION_NAME_ID}
							label="Collection name"
							placeholder="e.g., Technical Documentation"
							value={newCollectionName}
							onChange={(e) => onNewCollectionNameChange(e.target.value)}
						/>
						<FormTextarea
							label="Description"
							rows={2}
							placeholder="Optional description"
							value={newCollectionDescription}
							onChange={(e) =>
								onNewCollectionDescriptionChange(e.target.value)
							}
						/>
						<div className="flex justify-end gap-2">
							<Button onClick={onCancelCreate} variant="ghost" size="sm">
								Cancel
							</Button>
							<Button
								onClick={handleCreateCollection}
								size="sm"
								disabled={!newCollectionName.trim()}
							>
								Create
							</Button>
						</div>
					</div>
				)}

				{/* Collection Stats */}
				{selectedCollection && (
					<div className="space-y-3">
						{/* Visibility Section */}
						{selectedCol && (
							<div className="space-y-2">
								<div className="text-xs capitalize font-semibold text-[color:var(--color-text-muted)]">
									Visibility
								</div>
								{selectedCol.is_read_only ? (
									/* Read-only collection visibility display */
									<div className="rounded-xl border p-3 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
										<div className="flex items-center gap-2 mb-1">
											<Lock className="w-3.5 h-3.5 text-amber-400" />
											<span className="text-xs font-medium text-amber-400">Read-only</span>
										</div>
										{selectedCol.created_by_name && (
											<p className="text-xs text-[color:var(--color-text-muted)] mb-2">
												Created by {selectedCol.created_by_name}
											</p>
										)}
										<div className="flex flex-wrap gap-1.5">
											{isGlobalCollection(selectedCol) ? (
												<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">
													<Globe className="w-3 h-3" />
													Everyone
												</span>
											) : hasGroupRestrictions(selectedCol) ? (
												(selectedCol.visible_to_groups ?? []).map((group) => (
													<span
														key={group}
														className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-500/15 text-purple-400 border border-purple-500/30"
													>
														<Users className="w-3 h-3" />
														{group}
													</span>
												))
											) : (
												<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-[color:var(--color-surface)] text-[color:var(--color-text-muted)] border border-[color:var(--color-border)]">
													Private
												</span>
											)}
										</div>
									</div>
								) : (
									/* Owned collection visibility controls */
									<div className="rounded-xl border p-3 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
										{!isEditingVisibility ? (
											<div className="flex items-center justify-between">
												<div className="flex flex-wrap gap-1.5">
													{isGlobalCollection(selectedCol) ? (
														<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">
															<Globe className="w-3 h-3" />
															Everyone
														</span>
													) : hasGroupRestrictions(selectedCol) ? (
														(selectedCol.visible_to_groups ?? []).map((group) => (
															<span
																key={group}
																className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-purple-500/15 text-purple-400 border border-purple-500/30"
															>
																<Users className="w-3 h-3" />
																{group}
															</span>
														))
													) : (
														<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-[color:var(--color-surface)] text-[color:var(--color-text-muted)] border border-[color:var(--color-border)]">
															Private
														</span>
													)}
												</div>
												{onUpdateVisibility && (
													<button
														type="button"
														onClick={handleStartEditVisibility}
														className="p-1 rounded transition-colors text-[color:var(--color-text-muted)] hover:text-slate-900"
														title="Edit visibility"
													>
														<Edit2 className="w-3.5 h-3.5" />
													</button>
												)}
											</div>
										) : (
											<div className="space-y-3">
												<div className="flex items-center justify-between">
													<div className="flex items-center gap-2">
														{isEditGlobalVisibility ? (
															<Globe className="w-4 h-4 text-blue-400" />
														) : (
															<Users className="w-4 h-4 text-[color:var(--color-text-muted)]" />
														)}
														<div>
															<p className="text-sm font-medium text-slate-900">
																{isEditGlobalVisibility ? "Shared" : "Private"}
															</p>
															<p className="text-xs text-[color:var(--color-text-muted)]">
																{isEditGlobalVisibility
																	? "Visible to selected groups or everyone"
																	: "Only visible to you"}
															</p>
														</div>
													</div>
													<button
														type="button"
														onClick={() => {
															setIsEditGlobalVisibility(!isEditGlobalVisibility);
															if (isEditGlobalVisibility) {
																setEditVisibilityGroups([]);
															}
														}}
														className={`relative w-12 h-6 rounded-full transition-colors ${
															isEditGlobalVisibility
																? "bg-blue-500"
																: "bg-[color:var(--color-border)]"
														}`}
													>
														<span
															className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
																isEditGlobalVisibility ? "left-7" : "left-1"
															}`}
														/>
													</button>
												</div>

												{isEditGlobalVisibility && (
													<div className="pt-3 border-t border-[color:var(--color-border)]/30">
														<GroupSelector
															selectedGroups={editVisibilityGroups}
															onChange={setEditVisibilityGroups}
															placeholder="Select groups (optional, defaults to everyone)"
														/>
													</div>
												)}

												<div className="flex justify-end gap-2">
													<Button onClick={handleCancelEditVisibility} variant="ghost" size="sm">
														Cancel
													</Button>
													<Button
														onClick={handleSaveVisibility}
														size="sm"
														icon={<Save className="w-3.5 h-3.5" />}
													>
														Save
													</Button>
												</div>
											</div>
										)}
									</div>
								)}
							</div>
						)}

						<div className="text-xs capitalize font-semibold text-[color:var(--color-text-muted)]">
							Collection overview
						</div>
						<div className="grid grid-cols-2 gap-3">
							<div className="rounded-xl border p-3 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
								<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Available
								</div>
								<div className="text-lg font-semibold text-slate-900">
									{stats.processedCount}
								</div>
							</div>
							<div className="rounded-xl border p-3 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
								<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Unprocessed
								</div>
								<div className="text-lg font-semibold text-red-400">
									{stats.failedCount}
								</div>
							</div>
							<div className="col-span-2 rounded-xl border p-3 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
								<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
									Total size
								</div>
								<div className="text-lg font-semibold text-slate-900">
									{formatFileSize(stats.totalSize)}
								</div>
							</div>
						</div>

						{/* Embedding cost summary */}
						{(stats.totalTokens > 0 || stats.totalCost > 0) && (
							<>
								<div className="text-xs capitalize font-semibold text-[color:var(--color-text-muted)]">
									Embedding usage
								</div>
								<div className="grid grid-cols-2 gap-3">
									<div className="rounded-xl border p-3 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
										<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
											Tokens
										</div>
										<div className="text-lg font-semibold text-slate-900 font-mono">
											{stats.totalTokens.toLocaleString()}
										</div>
									</div>
									<div className="rounded-xl border p-3 bg-[color:var(--color-surface)] border-[color:var(--color-border)]">
										<div className="text-[0.6rem] capitalize text-[color:var(--color-text-muted)]">
											Cost
										</div>
										<div className="text-lg font-semibold text-slate-900 font-mono flex items-center gap-1.5">
											<Coins className="w-4 h-4 text-amber-400" />
											${stats.totalCost.toFixed(4)}
										</div>
									</div>
								</div>
							</>
						)}
					</div>
				)}
			</div>
		</aside>
	);
}

// Export the ID constants for use in parent component
export { NEW_COLLECTION_NAME_ID };
