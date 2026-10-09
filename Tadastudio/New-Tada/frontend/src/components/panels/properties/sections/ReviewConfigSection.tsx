"use client";

import { Bot, Clock, Info, RefreshCw, Shield, User } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import type {
	ReviewConfig,
	ReviewerLLMConfig,
	ReviewMode,
} from "@/types/review";
import { DEFAULT_REVIEW_CONFIG } from "@/types/review";
import Dropdown from "../../../ui/Dropdown";

interface ModelOption {
	value: string;
	label: string;
	provider: string;
	providerKey: string;
	description: string;
	model: {
		id: string;
		model_name: string;
		display_name?: string;
		name?: string;
		provider: string;
		settings?: Record<string, unknown>;
	};
}

interface ReviewConfigSectionProps {
	reviewConfig: ReviewConfig;
	onReviewConfigChange: (config: ReviewConfig) => void;
	modelOptions: ModelOption[];
	modelsLoading: boolean;
	dropdownMenuAppearance?: "default" | "light";
}

export default function ReviewConfigSection({
	reviewConfig,
	onReviewConfigChange,
	modelOptions,
	modelsLoading,
	dropdownMenuAppearance = "light",
}: ReviewConfigSectionProps) {
	const [isEditingIterations, setIsEditingIterations] = useState(false);
	const [editIterations, setEditIterations] = useState(
		reviewConfig.max_iterations.toString(),
	);
	const [isEditingTimeout, setIsEditingTimeout] = useState(false);
	const [editTimeout, setEditTimeout] = useState(
		reviewConfig.timeout_seconds?.toString() ?? "",
	);
	const iterationsInputRef = useRef<HTMLInputElement>(null);
	const timeoutInputRef = useRef<HTMLInputElement>(null);

	// Sync local state with prop changes
	useEffect(() => {
		setEditIterations(reviewConfig.max_iterations.toString());
	}, [reviewConfig.max_iterations]);

	useEffect(() => {
		setEditTimeout(reviewConfig.timeout_seconds?.toString() ?? "");
	}, [reviewConfig.timeout_seconds]);

	// Focus inputs when editing
	useEffect(() => {
		if (isEditingIterations && iterationsInputRef.current) {
			iterationsInputRef.current.focus();
			iterationsInputRef.current.select();
		}
	}, [isEditingIterations]);

	useEffect(() => {
		if (isEditingTimeout && timeoutInputRef.current) {
			timeoutInputRef.current.focus();
			timeoutInputRef.current.select();
		}
	}, [isEditingTimeout]);

	const handleEnabledChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onReviewConfigChange({
				...reviewConfig,
				review_enabled: e.target.checked,
			});
		},
		[reviewConfig, onReviewConfigChange],
	);

	const handleModeChange = useCallback(
		(mode: string) => {
			onReviewConfigChange({
				...reviewConfig,
				review_mode: mode as ReviewMode,
			});
		},
		[reviewConfig, onReviewConfigChange],
	);

	const handlePromptChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			onReviewConfigChange({
				...reviewConfig,
				review_prompt: e.target.value,
			});
		},
		[reviewConfig, onReviewConfigChange],
	);

	const handleIterationsClick = useCallback(() => {
		setIsEditingIterations(true);
	}, []);

	const handleIterationsBlur = useCallback(() => {
		const newValue = parseInt(editIterations);
		if (!isNaN(newValue) && newValue >= 1 && newValue <= 10) {
			onReviewConfigChange({
				...reviewConfig,
				max_iterations: newValue,
			});
		} else {
			setEditIterations(reviewConfig.max_iterations.toString());
		}
		setIsEditingIterations(false);
	}, [editIterations, reviewConfig, onReviewConfigChange]);

	const handleIterationsKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLInputElement>) => {
			if (e.key === "Enter") {
				handleIterationsBlur();
			} else if (e.key === "Escape") {
				setEditIterations(reviewConfig.max_iterations.toString());
				setIsEditingIterations(false);
			}
		},
		[handleIterationsBlur, reviewConfig.max_iterations],
	);

	const handleTimeoutClick = useCallback(() => {
		setIsEditingTimeout(true);
	}, []);

	const handleTimeoutBlur = useCallback(() => {
		if (editTimeout === "" || editTimeout === "0") {
			onReviewConfigChange({
				...reviewConfig,
				timeout_seconds: null,
			});
		} else {
			const newValue = parseInt(editTimeout);
			if (!isNaN(newValue) && newValue >= 0) {
				onReviewConfigChange({
					...reviewConfig,
					timeout_seconds: newValue > 0 ? newValue : null,
				});
			} else {
				setEditTimeout(reviewConfig.timeout_seconds?.toString() ?? "");
			}
		}
		setIsEditingTimeout(false);
	}, [editTimeout, reviewConfig, onReviewConfigChange]);

	const handleTimeoutKeyDown = useCallback(
		(e: React.KeyboardEvent<HTMLInputElement>) => {
			if (e.key === "Enter") {
				handleTimeoutBlur();
			} else if (e.key === "Escape") {
				setEditTimeout(reviewConfig.timeout_seconds?.toString() ?? "");
				setIsEditingTimeout(false);
			}
		},
		[handleTimeoutBlur, reviewConfig.timeout_seconds],
	);

	const handleReviewerModelChange = useCallback(
		(modelId: string) => {
			const selectedOption = modelOptions.find(
				(option) => option.value === modelId,
			);
			if (selectedOption) {
				const deployment = selectedOption.model;
				const newConfig: ReviewerLLMConfig = {
					model_deployment_id: deployment.id,
					provider: deployment.provider,
					model_name: deployment.model_name,
					display_name: deployment.display_name || deployment.name,
					temperature: 0.0,
				};
				onReviewConfigChange({
					...reviewConfig,
					reviewer_llm_config: newConfig,
				});
			}
		},
		[modelOptions, reviewConfig, onReviewConfigChange],
	);

	const handleAutoApproveOnMaxChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onReviewConfigChange({
				...reviewConfig,
				auto_approve_on_max_iterations: e.target.checked,
			});
		},
		[reviewConfig, onReviewConfigChange],
	);

	const handleAutoApproveOnTimeoutChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			onReviewConfigChange({
				...reviewConfig,
				auto_approve_on_timeout: e.target.checked,
			});
		},
		[reviewConfig, onReviewConfigChange],
	);

	const iterationsSliderProgress =
		((reviewConfig.max_iterations - 1) / 9) * 100;

	return (
		<div className="space-y-6">
			{/* Main toggle card */}
			<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
				<div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100 text-orange-600">
							<Shield className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-slate-900">
								Output Review
							</h3>
							<p className="text-sm text-slate-600">
								Gate agent output with human or LLM review before proceeding.
							</p>
						</div>
					</div>
					<label className="relative inline-flex items-center cursor-pointer">
						<input
							type="checkbox"
							checked={reviewConfig.review_enabled}
							onChange={handleEnabledChange}
							className="peer sr-only"
						/>
						<div className="h-7 w-12 rounded-full border border-slate-300 bg-slate-200 transition-colors duration-200 peer-checked:bg-orange-500 peer-checked:border-orange-500 peer-focus-visible:ring-2 peer-focus-visible:ring-orange-500/30" />
						<span className="absolute left-1 top-1 h-5 w-5 rounded-full bg-white shadow-sm transition-transform duration-200 peer-checked:translate-x-5" />
					</label>
				</div>
				<p className="mt-4 text-sm text-slate-600">
					When enabled, the agent&apos;s output will be reviewed before
					continuing. If rejected, feedback is sent back to the agent for
					revision.
				</p>
			</div>

			{reviewConfig.review_enabled && (
				<div className="space-y-6 rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
					{/* Review Mode Selection */}
					<div>
						<label className="mb-3 block text-sm font-medium text-slate-800">
							Review Mode
						</label>
						<Dropdown
							value={reviewConfig.review_mode}
							onChange={handleModeChange}
							menuAppearance={dropdownMenuAppearance}
							triggerClassName="!rounded-[4px] !border-slate-200 hover:!border-orange-400 hover:!bg-slate-50"
							dropdownClassName="!border-slate-200 !bg-white"
							optionClassName="!text-slate-900 hover:!bg-slate-100 hover:!text-orange-800"
							options={[
								{
									value: "human",
									label: "Human Review",
									description:
										"Pause execution for manual approval or feedback",
									icon: <User className="h-4 w-4" />,
								},
								{
									value: "llm",
									label: "LLM Review",
									description:
										"Automated review using a separate LLM as reviewer",
									icon: <Bot className="h-4 w-4" />,
								},
							]}
						/>
					</div>

					{/* Review Prompt / Criteria */}
					<div>
						<label
							htmlFor="review-prompt"
							className="mb-3 block text-sm font-medium text-slate-800"
						>
							{reviewConfig.review_mode === "human"
								? "Review Instructions"
								: "Review Criteria"}
						</label>
						<textarea
							id="review-prompt"
							value={reviewConfig.review_prompt}
							onChange={handlePromptChange}
							rows={4}
							placeholder={
								reviewConfig.review_mode === "human"
									? "Instructions for the human reviewer..."
									: "Criteria for the LLM reviewer to evaluate..."
							}
							className="w-full rounded-[4px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder:text-slate-400 transition-colors hover:border-orange-400 focus:border-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/15"
						/>
						<p className="mt-2 text-xs text-slate-600">
							{reviewConfig.review_mode === "human"
								? "Guidance shown to reviewers when approving/rejecting output."
								: "Prompt used by the reviewer LLM to evaluate the agent's output."}
						</p>
					</div>

					{/* LLM Review: Model Selector */}
					{reviewConfig.review_mode === "llm" && (
						<div>
							<label className="mb-3 block text-sm font-medium text-slate-800">
								Reviewer Model
							</label>
							{modelsLoading ? (
								<div className="flex items-center gap-2 text-sm text-slate-600">
									<RefreshCw className="h-4 w-4 animate-spin text-orange-600" />
									Loading models...
								</div>
							) : (
								<Dropdown
									value={
										reviewConfig.reviewer_llm_config?.model_deployment_id ?? ""
									}
									onChange={handleReviewerModelChange}
									menuAppearance={dropdownMenuAppearance}
									triggerClassName="!rounded-[4px] !border-slate-200 hover:!border-orange-400 hover:!bg-slate-50"
									dropdownClassName="!border-slate-200 !bg-white"
									optionClassName="!text-slate-900 hover:!bg-slate-100 hover:!text-orange-800"
									options={modelOptions.map((option) => ({
										value: option.value,
										label: option.label,
										description: option.description,
									}))}
									placeholder="Select a model for review..."
								/>
							)}
							<p className="mt-2 text-xs text-slate-600">
								Choose an LLM to evaluate the agent&apos;s output. Can be
								different from the agent&apos;s model.
							</p>
						</div>
					)}

					{/* Max Iterations */}
					<div className="grid gap-6 md:grid-cols-2">
						<div>
							<label
								htmlFor="max-iterations"
								className="mb-3 block text-sm font-medium text-slate-800"
							>
								Max Iterations
							</label>
							<div className="flex items-center gap-4">
								<input
									id="max-iterations"
									type="range"
									min="1"
									max="10"
									value={reviewConfig.max_iterations}
									onChange={(e) =>
										onReviewConfigChange({
											...reviewConfig,
											max_iterations: parseInt(e.target.value),
										})
									}
									className="flex-1 transition-all duration-200"
									style={{
										background: `linear-gradient(to right, rgb(234 88 12) 0%, rgb(234 88 12) ${iterationsSliderProgress}%, rgb(226 232 240) ${iterationsSliderProgress}%, rgb(226 232 240) 100%)`,
										accentColor: "rgb(234 88 12)",
									}}
								/>
								{isEditingIterations ? (
									<input
										ref={iterationsInputRef}
										type="number"
										min="1"
										max="10"
										value={editIterations}
										onChange={(e) => setEditIterations(e.target.value)}
										onBlur={handleIterationsBlur}
										onKeyDown={handleIterationsKeyDown}
										className="w-16 rounded-[4px] border border-slate-200 bg-white px-2 py-1 text-center text-base font-semibold text-slate-900 focus:border-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/15"
									/>
								) : (
									<button
										type="button"
										onClick={handleIterationsClick}
										className="w-14 rounded-[4px] border border-slate-200 bg-white px-2 py-1 text-center text-base font-semibold text-slate-900 transition-colors hover:border-orange-400"
										title="Click to edit"
									>
										{reviewConfig.max_iterations}
									</button>
								)}
							</div>
							<p className="mt-2 text-xs text-slate-600">
								Maximum feedback cycles before auto-approve/fail.
							</p>
						</div>

						{/* Timeout (Human review only) */}
						{reviewConfig.review_mode === "human" && (
							<div>
								<label
									htmlFor="timeout"
									className="mb-3 block text-sm font-medium text-slate-800"
								>
									Timeout (seconds)
								</label>
								<div className="flex items-center gap-2">
									<Clock className="h-5 w-5 text-slate-500" />
									{isEditingTimeout ? (
										<input
											ref={timeoutInputRef}
											type="number"
											min="0"
											value={editTimeout}
											onChange={(e) => setEditTimeout(e.target.value)}
											onBlur={handleTimeoutBlur}
											onKeyDown={handleTimeoutKeyDown}
											placeholder="No timeout"
											className="w-full rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-orange-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/15"
										/>
									) : (
										<button
											type="button"
											onClick={handleTimeoutClick}
											className="w-full rounded-[4px] border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-800 transition-colors hover:border-orange-400"
										>
											{reviewConfig.timeout_seconds
												? `${reviewConfig.timeout_seconds}s`
												: "No timeout"}
										</button>
									)}
								</div>
								<p className="mt-2 text-xs text-slate-600">
									Optional timeout for human review. Leave empty for no timeout.
								</p>
							</div>
						)}
					</div>

					{/* Auto-approve settings */}
					<div className="rounded-[4px] border border-slate-200 bg-slate-50 p-4">
						<div className="flex items-start gap-3 mb-4">
							<Info className="h-5 w-5 text-orange-600 flex-shrink-0 mt-0.5" />
							<div>
								<h4 className="text-sm font-semibold text-slate-900">
									Fallback Behavior
								</h4>
								<p className="text-xs text-slate-600">
									What happens when review limits are reached.
								</p>
							</div>
						</div>

						<div className="space-y-3">
							<label className="flex items-center gap-3 cursor-pointer">
								<input
									type="checkbox"
									checked={reviewConfig.auto_approve_on_max_iterations}
									onChange={handleAutoApproveOnMaxChange}
									className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-orange-500/25"
								/>
								<span className="text-sm text-slate-800">
									Auto-approve when max iterations reached
								</span>
							</label>

							{reviewConfig.review_mode === "human" &&
								reviewConfig.timeout_seconds && (
									<label className="flex items-center gap-3 cursor-pointer">
										<input
											type="checkbox"
											checked={reviewConfig.auto_approve_on_timeout}
											onChange={handleAutoApproveOnTimeoutChange}
											className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-orange-500/25"
										/>
										<span className="text-sm text-slate-800">
											Auto-approve on timeout
										</span>
									</label>
								)}
						</div>
					</div>
				</div>
			)}
		</div>
	);
}
