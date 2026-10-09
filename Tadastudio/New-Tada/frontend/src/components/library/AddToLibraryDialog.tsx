"use client";

import { AlertTriangle, BookOpen, Plus, Tag, X } from "lucide-react";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import Dropdown from "@/components/ui/Dropdown";
import { api } from "@/lib/api";
import { COMPLEXITY_LEVELS, TEMPLATE_CATEGORIES } from "@/types/library";

interface AddToLibraryDialogProps {
	isOpen: boolean;
	workflowId: string | null;
	workflowName: string | null;
	onConfirm: (data: {
		name: string;
		description: string;
		category: string[];
		tags: string[];
		complexity?: string;
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

const AddToLibraryDialog = React.memo(function AddToLibraryDialog({
	isOpen,
	workflowId,
	workflowName,
	onConfirm,
	onCancel,
}: AddToLibraryDialogProps) {
	const [name, setName] = useState(workflowName || "");
	const [description, setDescription] = useState("");
	const [categories, setCategories] = useState<string[]>([]);
	const [tags, setTags] = useState<string[]>([]);
	const [tagInput, setTagInput] = useState("");
	const [complexity, setComplexity] = useState<string>("");
	const [iconColor, setIconColor] = useState("");
	const [showCancelConfirm, setShowCancelConfirm] = useState(false);
	const [initialData, setInitialData] = useState<{
		name: string;
		description: string;
		categories: string[];
		tags: string[];
	} | null>(null);

	// Check if form has unsaved changes
	const hasChanges = useMemo(() => {
		if (!initialData) return false;
		return (
			name !== initialData.name ||
			description !== initialData.description ||
			JSON.stringify(categories) !== JSON.stringify(initialData.categories) ||
			JSON.stringify(tags) !== JSON.stringify(initialData.tags)
		);
	}, [name, description, categories, tags, initialData]);

	// Update name when workflowName changes
	useEffect(() => {
		if (workflowName) {
			setName(workflowName);
		}
	}, [workflowName]);

	// Fetch existing template data when dialog opens
	useEffect(() => {
		const fetchExistingTemplate = async () => {
			if (!isOpen || !workflowName) return;

			try {
				const response = await api.findTemplateByWorkflowName(workflowName);

				if (response.success && response.template) {
					// Prepopulate form with existing template data
					setName(response.template.name);
					setDescription(response.template.description);
					setCategories(response.template.category || []);
					setTags(response.template.tags || []);
					setComplexity(response.template.complexity || "");
					setIconColor(response.template.icon_color || "");
					// Store initial data for change detection
					setInitialData({
						name: response.template.name,
						description: response.template.description,
						categories: response.template.category || [],
						tags: response.template.tags || [],
					});
				} else {
					// No existing template, start with workflow name
					setName(workflowName);
					setDescription("");
					setCategories([]);
					setTags([]);
					setComplexity("");
					setIconColor("");
					setInitialData({
						name: workflowName,
						description: "",
						categories: [],
						tags: [],
					});
				}
			} catch (error) {
				console.error("Error fetching existing template:", error);
				// On error, start fresh with just the workflow name
				setName(workflowName);
				setInitialData({
					name: workflowName,
					description: "",
					categories: [],
					tags: [],
				});
			}
		};

		fetchExistingTemplate();
	}, [isOpen, workflowName]);

	const handleAddTag = useCallback(() => {
		const trimmedTag = tagInput.trim();
		if (trimmedTag && !tags.includes(trimmedTag)) {
			setTags([...tags, trimmedTag]);
			setTagInput("");
		} else if (trimmedTag) {
			// Clear if duplicate
			setTagInput("");
		}
	}, [tagInput, tags]);

	const handleRemoveTag = useCallback(
		(tagToRemove: string) => {
			setTags(tags.filter((tag) => tag !== tagToRemove));
		},
		[tags],
	);

	const handleToggleCategory = useCallback((category: string) => {
		setCategories((prev) => {
			if (prev.includes(category)) {
				return prev.filter((c) => c !== category);
			} else {
				return [...prev, category];
			}
		});
	}, []);

	const handleTagKeyDown = useCallback(
		(e: React.KeyboardEvent) => {
			// Add tag on Enter, Tab, or comma
			if (e.key === "Enter" || e.key === "Tab" || e.key === ",") {
				e.preventDefault();
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
			tags.length === 0
		) {
			return;
		}

		onConfirm({
			name: name.trim(),
			description: description.trim(),
			category: categories,
			tags,
			complexity: complexity || undefined,
			iconColor: iconColor || undefined,
		});

		// Reset form
		setName("");
		setDescription("");
		setCategories([]);
		setTags([]);
		setTagInput("");
		setComplexity("");
		setIconColor("");
	}, [name, description, categories, tags, complexity, iconColor, onConfirm]);

	if (!isOpen || !workflowId) return null;

	const categoryOptions = TEMPLATE_CATEGORIES.map((cat) => ({
		value: cat,
		label: cat,
	}));

	const complexityOptions = COMPLEXITY_LEVELS.map((level) => ({
		value: level,
		label: level.charAt(0).toUpperCase() + level.slice(1),
	}));

	const iconColorOptions = ICON_COLORS.map((color) => ({
		value: color.value,
		label: color.label,
		icon: <div className={`w-4 h-4 rounded-full ${color.color}`} />,
	}));

	const dropdownTriggerClassName =
		"!bg-white !border-slate-200 !text-[color:var(--color-text-primary)] hover:!bg-slate-50 hover:!border-slate-300 focus:!border-orange-400 focus:!ring-orange-500/20";
	const dropdownMenuClassName =
		"!bg-white !border-slate-200 !shadow-[0_20px_55px_rgba(15,23,42,0.12)]";
	const dropdownOptionClassName =
		"!text-[color:var(--color-text-secondary)] hover:!bg-slate-50 hover:!text-[color:var(--color-text-primary)] aria-selected:!bg-orange-50 aria-selected:!text-[color:var(--color-text-primary)]";

	const isValid =
		name.trim() &&
		description.trim() &&
		categories.length > 0 &&
		tags.length > 0;

	return (
		<div className="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-[60] p-4 animate-fadeIn">
			<div className="relative w-full max-w-2xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.18)] animate-scaleIn max-h-[90vh] overflow-y-auto">
				<div className="relative p-6 space-y-6">
					{/* Header */}
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-orange-50 border border-orange-100">
							<BookOpen className="w-6 h-6 text-orange-600" />
						</div>
						<div className="flex-1 min-w-0 space-y-1">
							<h3 className="text-xl font-semibold text-[color:var(--color-text-primary)] tracking-tight">
								Add to Library
							</h3>
							<p className="text-sm text-[color:var(--color-text-secondary)] leading-relaxed">
								Add{" "}
								<span className="font-medium text-[color:var(--color-text-primary)]">
									&quot;{workflowName}&quot;
								</span>{" "}
								to template library
							</p>
						</div>
						<button
							onClick={onCancel}
							className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 text-[color:var(--color-text-muted)] hover:bg-slate-50 hover:text-[color:var(--color-text-primary)] transition-all"
						>
							<X className="w-4 h-4" />
						</button>
					</div>

					{/* Form */}
					<div className="space-y-4">
						{/* Name */}
						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Template Name <span className="text-red-600">*</span>
							</label>
							<input
								type="text"
								value={name}
								onChange={(e) => setName(e.target.value)}
								placeholder="Enter a name for this template"
								className="w-full px-4 py-3 rounded-xl bg-white border border-slate-200 text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-orange-400 focus:ring-4 focus:ring-orange-500/15 transition-all"
							/>
							<p className="text-xs text-[color:var(--color-text-muted)]">
								This name will appear in the library (can be different from your
								workflow name)
							</p>
						</div>

						{/* Description */}
						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Description <span className="text-red-600">*</span>
							</label>
							<textarea
								value={description}
								onChange={(e) => setDescription(e.target.value)}
								placeholder="Describe what this workflow does and how to use it..."
								rows={3}
								className="w-full px-4 py-3 rounded-xl bg-white border border-slate-200 text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-orange-400 focus:ring-4 focus:ring-orange-500/15 transition-all resize-none"
							/>
						</div>

						{/* Categories */}
						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Categories <span className="text-red-600">*</span>
							</label>
							<p className="text-xs text-[color:var(--color-text-muted)] mb-2">
								Select one or more categories that best describe this workflow
							</p>
							<div className="grid grid-cols-2 md:grid-cols-3 gap-2">
								{TEMPLATE_CATEGORIES.map((category) => (
									<label
										key={category}
										className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border-2 cursor-pointer transition-all ${
											categories.includes(category)
												? "bg-orange-50 border-orange-300 text-orange-800"
												: "bg-white border-slate-200 text-[color:var(--color-text-secondary)] hover:bg-slate-50 hover:border-slate-300"
										}`}
									>
										<Checkbox
											checked={categories.includes(category)}
											onChange={(checked) => handleToggleCategory(category)}
											variant="plum"
											size="sm"
										/>
										<span className="text-sm font-medium">{category}</span>
									</label>
								))}
							</div>
							{categories.length > 0 && (
								<p className="text-xs text-orange-700">
									{categories.length}{" "}
									{categories.length === 1 ? "category" : "categories"} selected
								</p>
							)}
						</div>

						{/* Tags */}
						<div className="space-y-2">
							<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
								Tags <span className="text-red-600">*</span>
							</label>
							<div className="space-y-2">
								<div className="flex gap-2">
									<input
										type="text"
										value={tagInput}
										onChange={(e) => setTagInput(e.target.value)}
										onKeyDown={handleTagKeyDown}
										onBlur={handleTagBlur}
										placeholder="Type a tag and press Enter"
										className="flex-1 px-4 py-3 rounded-xl bg-white border border-slate-200 text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:border-orange-400 focus:ring-4 focus:ring-orange-500/15 transition-all"
									/>
									<button
										onClick={handleAddTag}
										disabled={!tagInput.trim()}
										className="px-4 py-3 rounded-xl bg-orange-50 border border-orange-200 text-orange-800 hover:bg-orange-100 hover:border-orange-300 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
									>
										<Plus className="w-5 h-5" />
									</button>
								</div>
								{tags.length > 0 && (
									<div className="flex flex-wrap gap-2">
										{tags.map((tag) => (
											<div
												key={tag}
												className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-orange-50 border border-orange-200 text-sm text-orange-800"
											>
												<Tag className="w-3 h-3" />
												{tag}
												<button
													onClick={() => handleRemoveTag(tag)}
													className="hover:text-slate-900 transition-colors"
												>
													<X className="w-3 h-3" />
												</button>
											</div>
										))}
									</div>
								)}
							</div>
						</div>

						{/* Optional fields in a grid */}
						<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
							{/* Complexity */}
							<div className="space-y-2">
								<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
									Complexity
								</label>
								<Dropdown
									value={complexity}
									onChange={setComplexity}
									options={complexityOptions}
									placeholder="Optional"
									triggerClassName={dropdownTriggerClassName}
									dropdownClassName={dropdownMenuClassName}
									optionClassName={dropdownOptionClassName}
								/>
							</div>

							{/* Icon Color */}
							<div className="space-y-2">
								<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
									Icon Color
								</label>
								<Dropdown
									value={iconColor}
									onChange={setIconColor}
									options={iconColorOptions}
									placeholder="Optional"
									triggerClassName={dropdownTriggerClassName}
									dropdownClassName={dropdownMenuClassName}
									optionClassName={dropdownOptionClassName}
								/>
							</div>
						</div>
					</div>

					{/* Action Buttons */}
					<div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
						<Button
							onClick={handleCancel}
							variant="secondary"
							className="flex-1 !bg-white !border-slate-200 !text-[color:var(--color-text-secondary)] hover:!bg-slate-50 hover:!border-slate-300 hover:!shadow-[0_10px_30px_rgba(15,23,42,0.10)] hover:!-translate-y-0.5 !transition-all !duration-200"
						>
							Cancel
						</Button>
						<Button
							onClick={handleSubmit}
							disabled={!isValid}
							variant="primary"
							className="flex-1 !bg-orange-500 !border-orange-500 !text-white hover:!bg-orange-600 hover:!border-orange-600 hover:!-translate-y-0.5 !transition-all !duration-200 disabled:!opacity-40 disabled:!cursor-not-allowed flex items-center justify-center gap-2"
							icon={<BookOpen className="w-4 h-4" />}
						>
							Add to Library
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
});

export default AddToLibraryDialog;
