"use client";

import { AlertCircle, CheckCircle2, Plus, Tag, Upload, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import Button from "@/components/ui/Button";
import Checkbox from "@/components/ui/Checkbox";
import Dropdown from "@/components/ui/Dropdown";
import { TEMPLATE_CATEGORIES } from "@/types/library";

interface ImportAgentDialogProps {
	isOpen: boolean;
	isSubmitting?: boolean;
	onConfirm: (data: {
		agent_json: Record<string, any>;
		metadata_override?: {
			category?: string[];
			tags?: string[];
			complexity?: string;
			icon_color?: string;
		};
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

const COMPLEXITY_LEVELS = [
	{ value: "beginner", label: "Beginner" },
	{ value: "intermediate", label: "Intermediate" },
	{ value: "advanced", label: "Advanced" },
];

const ImportAgentDialog = ({
	isOpen,
	isSubmitting = false,
	onConfirm,
	onCancel,
}: ImportAgentDialogProps) => {
	const [jsonInput, setJsonInput] = useState("");
	const [parsedJson, setParsedJson] = useState<Record<string, any> | null>(
		null,
	);
	const [jsonError, setJsonError] = useState<string | null>(null);
	const [categories, setCategories] = useState<string[]>([]);
	const [tags, setTags] = useState<string[]>([]);
	const [tagInput, setTagInput] = useState("");
	const [complexity, setComplexity] = useState("");
	const [iconColor, setIconColor] = useState("");
	const [overrideMetadata, setOverrideMetadata] = useState(false);

	const resetForm = useCallback(() => {
		setJsonInput("");
		setParsedJson(null);
		setJsonError(null);
		setCategories([]);
		setTags([]);
		setTagInput("");
		setComplexity("");
		setIconColor("");
		setOverrideMetadata(false);
	}, []);

	useEffect(() => {
		if (!isOpen) {
			resetForm();
		}
	}, [isOpen, resetForm]);

	// Validate and parse JSON on input change
	useEffect(() => {
		if (!jsonInput.trim()) {
			setParsedJson(null);
			setJsonError(null);
			return;
		}

		try {
			const parsed = JSON.parse(jsonInput);
			setParsedJson(parsed);
			setJsonError(null);

			// Auto-populate metadata from JSON if not overriding
			if (!overrideMetadata && parsed.metadata) {
				if (parsed.metadata.category) {
					setCategories(parsed.metadata.category);
				}
				if (parsed.metadata.tags) {
					setTags(parsed.metadata.tags);
				}
				if (parsed.metadata.complexity) {
					setComplexity(parsed.metadata.complexity);
				}
				if (parsed.metadata.icon_color) {
					setIconColor(parsed.metadata.icon_color);
				}
			}
		} catch (error) {
			setParsedJson(null);
			setJsonError(
				error instanceof Error ? error.message : "Invalid JSON format",
			);
		}
	}, [jsonInput, overrideMetadata]);

	const handleToggleCategory = useCallback((category: string) => {
		setCategories((prev) =>
			prev.includes(category)
				? prev.filter((c) => c !== category)
				: [...prev, category],
		);
		setOverrideMetadata(true);
	}, []);

	const handleAddTag = useCallback(() => {
		const trimmed = tagInput.trim();
		if (trimmed && !tags.includes(trimmed)) {
			setTags((prev) => [...prev, trimmed]);
			setTagInput("");
			setOverrideMetadata(true);
		}
	}, [tagInput, tags]);

	const handleRemoveTag = useCallback((tagToRemove: string) => {
		setTags((prev) => prev.filter((tag) => tag !== tagToRemove));
		setOverrideMetadata(true);
	}, []);

	const handleKeyPress = useCallback(
		(event: React.KeyboardEvent) => {
			if (event.key === "Enter") {
				event.preventDefault();
				handleAddTag();
			}
		},
		[handleAddTag],
	);

	const handleSubmit = useCallback(() => {
		if (!parsedJson || jsonError || isSubmitting) {
			return;
		}

		// Build metadata override if user has changed anything
		let metadata_override;
		if (
			overrideMetadata ||
			categories.length > 0 ||
			tags.length > 0 ||
			complexity ||
			iconColor
		) {
			metadata_override = {
				...(categories.length > 0 && { category: categories }),
				...(tags.length > 0 && { tags }),
				...(complexity && { complexity }),
				...(iconColor && { icon_color: iconColor }),
			};
		}

		onConfirm({
			agent_json: parsedJson,
			metadata_override,
		});
	}, [
		parsedJson,
		jsonError,
		categories,
		tags,
		complexity,
		iconColor,
		overrideMetadata,
		onConfirm,
		isSubmitting,
	]);

	const categoryOptions = useMemo(
		() =>
			TEMPLATE_CATEGORIES.map((category) => ({
				value: category,
				label: category,
			})),
		[],
	);

	const complexityOptions = useMemo(() => COMPLEXITY_LEVELS, []);

	const iconColorOptions = useMemo(
		() =>
			ICON_COLORS.map((color) => ({
				value: color.value,
				label: color.label,
				icon: <div className={`w-4 h-4 rounded-full ${color.color}`} />,
			})),
		[],
	);

	const isValid = parsedJson && !jsonError;
	const hasRequiredFields =
		parsedJson?.name && parsedJson?.description && parsedJson?.system_prompt;

	if (!isOpen) {
		return null;
	}

	return (
		<div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-xl p-4 animate-fadeIn">
			<div className="relative w-full max-w-4xl rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] overflow-hidden animate-scaleIn max-h-[90vh] overflow-y-auto">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				<div className="relative p-6 space-y-6">
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_58%,#f59e0b_170%)]">
							<Upload className="h-6 w-6 text-orange-600" />
						</div>
						<div className="flex-1">
							<h2 className="text-2xl font-bold text-[color:var(--color-text-primary)]">
								Import Agent from JSON
							</h2>
							<p className="text-sm text-[color:var(--color-text-muted)] mt-1">
								Paste your agent configuration in JSON format. Supports A2A
								Agent Card format.
							</p>
						</div>
						<button
							type="button"
							onClick={onCancel}
							className="text-[color:var(--color-text-muted)] hover:text-slate-900 transition-colors"
						>
							<X className="w-5 h-5" />
						</button>
					</div>

					{/* JSON Input */}
					<div className="space-y-2">
						<label className="block text-sm font-medium text-[color:var(--color-text-primary)]">
							Agent JSON Configuration *
						</label>
						<textarea
							value={jsonInput}
							onChange={(e) => setJsonInput(e.target.value)}
							placeholder={`{\n  "name": "My Agent",\n  "description": "Agent description",\n  "system_prompt": "Your instructions here",\n  ...\n}`}
							rows={12}
							className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] hover:border-orange-300 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition-all font-mono text-sm resize-y"
							disabled={isSubmitting}
						/>

						{/* JSON Validation Status */}
						{jsonInput && (
							<div className="flex items-start gap-2 text-sm">
								{jsonError ? (
									<>
										<AlertCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
										<div className="text-red-400">
											<span className="font-medium">JSON Error:</span>{" "}
											{jsonError}
										</div>
									</>
								) : parsedJson && !hasRequiredFields ? (
									<>
										<AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
										<div className="text-yellow-400">
											<span className="font-medium">
												Missing required fields:
											</span>{" "}
											name, description, and system_prompt are required
										</div>
									</>
								) : parsedJson ? (
									<>
										<CheckCircle2 className="w-4 h-4 text-[#0DA931] mt-0.5 shrink-0" />
										<div className="text-[#0DA931]">
											<span className="font-medium">Valid JSON detected</span>
											{parsedJson.name && (
												<span className="text-[color:var(--color-text-muted)] ml-2">
													- Agent: {parsedJson.name}
												</span>
											)}
										</div>
									</>
								) : null}
							</div>
						)}
					</div>

					{/* Metadata Override Section */}
					{parsedJson && isValid && (
						<div className="space-y-4 pt-4 border-t border-slate-200">
							<div className="flex items-center gap-2">
								<h3 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
									Metadata & Categorization
								</h3>
								<span className="text-xs text-[color:var(--color-text-muted)]">
									(Optional - customize how this agent appears in the library)
								</span>
							</div>

							{/* Categories */}
							<div className="space-y-2">
								<label className="block text-sm font-medium text-[color:var(--color-text-primary)]">
									Categories
								</label>
								<div className="grid grid-cols-2 md:grid-cols-3 gap-2">
									{categoryOptions.map((category) => (
										<Checkbox
											key={category.value}
											label={category.label}
											checked={categories.includes(category.value)}
											onChange={() => handleToggleCategory(category.value)}
											disabled={isSubmitting}
										/>
									))}
								</div>
							</div>

							{/* Tags */}
							<div className="space-y-2">
								<label className="block text-sm font-medium text-[color:var(--color-text-primary)]">
									Tags
								</label>
								<div className="flex gap-2">
									<input
										type="text"
										value={tagInput}
										onChange={(e) => setTagInput(e.target.value)}
										onKeyPress={handleKeyPress}
										placeholder="Add a tag..."
										className="flex-1 px-4 py-2 bg-white border border-slate-200 rounded-xl text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] hover:border-orange-300 focus:outline-none focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 transition-all"
										disabled={isSubmitting}
									/>
									<Button
										variant="secondary"
										onClick={handleAddTag}
										disabled={!tagInput.trim() || isSubmitting}
									>
										<Plus className="w-4 h-4" />
									</Button>
								</div>
								{tags.length > 0 && (
									<div className="flex flex-wrap gap-2 mt-2">
										{tags.map((tag) => (
											<div
												key={tag}
												className="flex items-center gap-1 px-3 py-1 bg-white border border-slate-200 rounded-lg text-sm text-orange-700"
											>
												<Tag className="w-3 h-3" />
												<span>{tag}</span>
												<button
													type="button"
													onClick={() => handleRemoveTag(tag)}
													className="ml-1 hover:text-red-400 transition-colors"
													disabled={isSubmitting}
												>
													<X className="w-3 h-3" />
												</button>
											</div>
										))}
									</div>
								)}
							</div>

							{/* Complexity */}
							<div className="space-y-2">
								<label className="block text-sm font-medium text-[color:var(--color-text-primary)]">
									Complexity Level
								</label>
								<Dropdown
									options={complexityOptions}
									value={complexity}
									onChange={setComplexity}
									placeholder="Select complexity..."
									disabled={isSubmitting}
								/>
							</div>

							{/* Icon Color */}
							<div className="space-y-2">
								<label className="block text-sm font-medium text-[color:var(--color-text-primary)]">
									Icon Color
								</label>
								<Dropdown
									options={iconColorOptions}
									value={iconColor}
									onChange={setIconColor}
									placeholder="Select icon color..."
									disabled={isSubmitting}
								/>
							</div>
						</div>
					)}

					{/* Actions */}
					<div className="flex gap-3 pt-4">
						<Button
							variant="secondary"
							onClick={onCancel}
							disabled={isSubmitting}
							className="flex-1"
						>
							Cancel
						</Button>
						<Button
							variant="primary"
							onClick={handleSubmit}
							disabled={!isValid || !hasRequiredFields || isSubmitting}
							className="flex-1"
						>
							{isSubmitting ? (
								<>
									<div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
									Importing...
								</>
							) : (
								<>
									<Upload className="w-4 h-4 mr-2" />
									Import Agent
								</>
							)}
						</Button>
					</div>

					{/* Help Text */}
					<div className="text-xs text-[color:var(--color-text-muted)] pt-2 border-t border-slate-200">
						<p>
							<strong>Tip:</strong> Paste your agent JSON configuration above.
							The format supports the A2A Agent Card specification. Required
							fields: name, description, and system_prompt.{" "}
							<a
								href="https://github.com/synechron/agentic-studio/blob/main/AGENT_IMPORT.md"
								target="_blank"
								rel="noopener noreferrer"
								className="text-orange-600 hover:text-slate-900 hover:underline"
							>
								View documentation
							</a>
						</p>
					</div>
				</div>
			</div>
		</div>
	);
};

export default ImportAgentDialog;
