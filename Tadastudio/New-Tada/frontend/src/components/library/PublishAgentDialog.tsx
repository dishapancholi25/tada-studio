"use client";

import { AlertTriangle, Bot, Tag, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import Dropdown from "@/components/ui/Dropdown";
import { TEMPLATE_CATEGORIES } from "@/types/library";

interface PublishAgentDialogProps {
	isOpen: boolean;
	agentName: string | null;
	agentDescription?: string | null;
	isSubmitting?: boolean;
	onConfirm: (data: {
		name: string;
		description: string;
		category: string[];
		tags: string[];
		iconColor?: string;
	}) => void;
	onCancel: () => void;
}

const ICON_COLORS = [
	{ value: "cyan", label: "Cyan", color: "bg-cyan-500" },
	{ value: "purple", label: "Purple", color: "bg-purple-500" },
	{ value: "orange", label: "Orange", color: "bg-orange-500" },
	{ value: "green", label: "Green", color: "bg-[#0DA931]" },
	{ value: "pink", label: "Pink", color: "bg-pink-500" },
	{ value: "blue", label: "Blue", color: "bg-blue-500" },
];

const PublishAgentDialog = ({
	isOpen,
	agentName,
	agentDescription,
	isSubmitting = false,
	onConfirm,
	onCancel,
}: PublishAgentDialogProps) => {
	const [name, setName] = useState(agentName || "");
	const [description, setDescription] = useState(agentDescription || "");
	const [categories, setCategories] = useState<string[]>([]);
	const [tags, setTags] = useState<string[]>([]);
	const [tagInput, setTagInput] = useState("");
	const [iconColor, setIconColor] = useState("");
	const [showCancelConfirm, setShowCancelConfirm] = useState(false);
	const [initialData, setInitialData] = useState<{
		name: string;
		description: string;
	} | null>(null);

	// Track if user has made changes
	const hasChanges = useMemo(() => {
		if (!initialData) return false;
		return (
			name !== initialData.name ||
			description !== initialData.description ||
			categories.length > 0 ||
			tags.length > 0
		);
	}, [name, description, categories, tags, initialData]);

	const resetForm = useCallback(() => {
		setName(agentName || "");
		setDescription(agentDescription || "");
		setCategories([]);
		setTags([]);
		setTagInput("");
		setIconColor("");
	}, [agentName, agentDescription]);

	useEffect(() => {
		if (isOpen) {
			setName(agentName || "");
			setDescription(agentDescription || "");
			setInitialData({
				name: agentName || "",
				description: agentDescription || "",
			});
			setShowCancelConfirm(false);
		} else {
			resetForm();
		}
	}, [isOpen, agentName, agentDescription, resetForm]);

	const handleToggleCategory = useCallback((category: string) => {
		setCategories((prev) =>
			prev.includes(category)
				? prev.filter((c) => c !== category)
				: [...prev, category],
		);
	}, []);

	const handleAddTag = useCallback(() => {
		const trimmed = tagInput.trim();
		if (trimmed && !tags.includes(trimmed)) {
			setTags((prev) => [...prev, trimmed]);
			setTagInput("");
		} else if (trimmed) {
			// Clear if duplicate
			setTagInput("");
		}
	}, [tagInput, tags]);

	const handleRemoveTag = useCallback((tagToRemove: string) => {
		setTags((prev) => prev.filter((tag) => tag !== tagToRemove));
	}, []);

	// Auto-add tag on Enter, Tab, or comma
	const handleTagKeyDown = useCallback(
		(event: React.KeyboardEvent) => {
			if (event.key === "Enter" || event.key === "Tab" || event.key === ",") {
				event.preventDefault();
				handleAddTag();
			}
		},
		[handleAddTag],
	);

	// Auto-add tag when input loses focus
	const handleTagBlur = useCallback(() => {
		handleAddTag();
	}, [handleAddTag]);

	// Handle cancel with confirmation if changes exist
	const handleCancel = useCallback(() => {
		if (hasChanges || tagInput.trim()) {
			setShowCancelConfirm(true);
		} else {
			onCancel();
		}
	}, [hasChanges, tagInput, onCancel]);

	const confirmCancel = useCallback(() => {
		setShowCancelConfirm(false);
		onCancel();
	}, [onCancel]);

	const handleSubmit = useCallback(() => {
		if (
			!name.trim() ||
			!description.trim() ||
			categories.length === 0 ||
			tags.length === 0 ||
			isSubmitting
		) {
			return;
		}

		onConfirm({
			name: name.trim(),
			description: description.trim(),
			category: categories,
			tags,
			iconColor: iconColor || undefined,
		});
	}, [name, description, categories, tags, iconColor, onConfirm, isSubmitting]);

	const categoryOptions = useMemo(
		() =>
			TEMPLATE_CATEGORIES.map((category) => ({
				value: category,
				label: category,
			})),
		[],
	);

	const iconColorOptions = useMemo(
		() =>
			ICON_COLORS.map((color) => ({
				value: color.value,
				label: color.label,
				icon: <div className={`w-4 h-4 rounded-full ${color.color}`} />,
			})),
		[],
	);

	const isValid =
		name.trim() &&
		description.trim() &&
		categories.length > 0 &&
		tags.length > 0;

	if (!isOpen) {
		return null;
	}

	return (
		<div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-xl p-4 animate-fadeIn">
			<div className="relative w-full max-w-2xl rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] overflow-hidden animate-scaleIn max-h-[90vh] overflow-y-auto">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				<div className="relative p-6 space-y-6">
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_58%,#f59e0b_170%)]">
							<Bot className="w-6 h-6 text-orange-600" />
						</div>
						<div className="flex-1 min-w-0 space-y-1">
							<h3 className="text-xl font-semibold text-[color:var(--color-text-primary)] tracking-tight">
								Publish Agent Template
							</h3>
							<p className="text-sm text-[color:var(--color-text-muted)] leading-relaxed">
								Add{" "}
								<span className="font-medium text-[color:var(--color-text-primary)]">
									&quot;{agentName || "Unnamed Agent"}&quot;
								</span>{" "}
								to the agent library.
							</p>
						</div>
						<button
							onClick={onCancel}
							className="flex h-8 w-8 items-center justify-center rounded-xl bg-white border border-slate-200 text-[color:var(--color-text-muted)] hover:border-orange-400 hover:text-slate-900 transition-all"
							aria-label="Close publish agent dialog"
						>
							<X className="w-4 h-4" />
						</button>
					</div>

					<div className="space-y-4">
						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Agent Template Name <span className="text-red-400">*</span>
							</label>
							<input
								type="text"
								value={name}
								onChange={(event) => setName(event.target.value)}
								placeholder="Give this agent a descriptive name"
								className="w-full px-4 py-3 rounded-xl bg-white border-2 border-slate-200 text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] hover:border-orange-300 focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/15 transition-all"
							/>
						</div>

						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Description <span className="text-red-400">*</span>
							</label>
							<textarea
								value={description}
								onChange={(event) => setDescription(event.target.value)}
								placeholder="Describe what this agent does, inputs it expects, and how it should be used..."
								rows={3}
								className="w-full px-4 py-3 rounded-xl bg-white border-2 border-slate-200 text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] hover:border-orange-300 focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/15 transition-all resize-none"
							/>
						</div>

						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Categories <span className="text-red-400">*</span>
							</label>
							<p className="text-xs text-[color:var(--color-text-muted)] mb-2">
								Select one or more sectors where this agent is most applicable.
							</p>
							<div className="grid grid-cols-2 md:grid-cols-3 gap-2">
								{categoryOptions.map((option) => (
									<label
										key={option.value}
										className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border-2 cursor-pointer transition-all ${
											categories.includes(option.value)
												? "bg-white border-orange-500 text-orange-700"
												: "bg-white border-slate-200 text-[color:var(--color-text-secondary)] hover:bg-white hover:border-orange-400 hover:text-slate-900"
										}`}
									>
										<Checkbox
											checked={categories.includes(option.value)}
											onChange={() => handleToggleCategory(option.value)}
											variant="plum"
											size="sm"
										/>
										<span className="text-sm font-medium">{option.label}</span>
									</label>
								))}
							</div>
						</div>

						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Tags <span className="text-red-400">*</span>
							</label>
							<div className="space-y-2">
								<div className="flex gap-2">
									<input
										type="text"
										value={tagInput}
										onChange={(event) => setTagInput(event.target.value)}
										onKeyDown={handleTagKeyDown}
										onBlur={handleTagBlur}
										placeholder="Type a tag and press Enter"
										className="flex-1 px-4 py-3 rounded-xl bg-white border-2 border-slate-200 text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] hover:border-orange-300 focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/15 transition-all"
									/>
								</div>
								{tags.length > 0 && (
									<div className="flex flex-wrap gap-2">
										{tags.map((tag) => (
											<div
												key={tag}
												className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-sm text-orange-700"
											>
												<Tag className="w-3 h-3" />
												{tag}
												<button
													onClick={() => handleRemoveTag(tag)}
													className="hover:text-red-600 transition-colors"
												>
													<X className="w-3 h-3" />
												</button>
											</div>
										))}
									</div>
								)}
							</div>
						</div>

						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Icon Color
							</label>
							<Dropdown
								value={iconColor}
								onChange={setIconColor}
								options={iconColorOptions}
								placeholder="Optional"
							/>
							<p className="text-xs text-[color:var(--color-text-muted)]">
								Customize how this agent appears in the library grid.
							</p>
						</div>
					</div>

					<div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
						<Button
							onClick={handleCancel}
							variant="secondary"
							className="flex-1 !bg-white !border-slate-200 !text-[color:var(--color-text-secondary)] hover:!bg-white hover:!border-orange-400 hover:!text-orange-700 !transition-all"
						>
							Cancel
						</Button>
						<Button
							onClick={handleSubmit}
							disabled={!isValid || isSubmitting}
							variant="primary"
							className="flex-1 flex items-center justify-center gap-2 !bg-orange-500 !border-orange-500 !text-white hover:!bg-orange-600 hover:!border-orange-600 !shadow-[0_15px_40px_rgba(15,23,42,0.12)] !transition-all disabled:!opacity-40 disabled:!cursor-not-allowed"
						>
							{isSubmitting ? (
								<>
									<span>Publishing...</span>
								</>
							) : (
								<>
									<Bot className="w-4 h-4" />
									<span>Publish Agent</span>
								</>
							)}
						</Button>
					</div>
				</div>
			</div>

			{/* Cancel Confirmation Dialog */}
			{showCancelConfirm && (
				<div className="fixed inset-0 flex items-center justify-center z-[60]">
					<div
						className="absolute inset-0 bg-black/50"
						onClick={() => setShowCancelConfirm(false)}
					/>
					<div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full mx-4 animate-in fade-in zoom-in-95 duration-200">
						<div className="flex items-start gap-4">
							<div className="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
								<AlertTriangle className="w-5 h-5 text-amber-600" />
							</div>
							<div className="flex-1">
								<h3 className="text-lg font-semibold text-slate-900">
									Discard Changes?
								</h3>
								<p className="mt-1 text-sm text-slate-600">
									You have unsaved changes. Are you sure you want to cancel? All
									entered data will be lost.
								</p>
							</div>
						</div>
						<div className="flex gap-3 mt-6">
							<Button
								onClick={() => setShowCancelConfirm(false)}
								variant="secondary"
								className="flex-1 !bg-white !border-slate-200 !text-slate-700 hover:!bg-slate-50"
							>
								Keep Editing
							</Button>
							<Button
								onClick={confirmCancel}
								variant="primary"
								className="flex-1 !bg-red-500 !border-red-500 !text-white hover:!bg-red-600"
							>
								Discard
							</Button>
						</div>
					</div>
				</div>
			)}
		</div>
	);
};

export default PublishAgentDialog;
