"use client";

import { Bot, Settings, Sparkles, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import Button from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import SubAgentAdvancedSection from "./sections/SubAgentAdvancedSection";
import SubAgentCoreSection from "./sections/SubAgentCoreSection";

interface CreateSubAgentDialogProps {
	isOpen: boolean;
	onClose: () => void;
	onConfirm: (
		name: string,
		delegationDescription: string,
		agentTemplate?: string,
	) => void;
	parentAgentName: string;
}

type SubAgentTabId = "core" | "advanced";

export default function CreateSubAgentDialog({
	isOpen,
	onClose,
	onConfirm,
	parentAgentName,
}: CreateSubAgentDialogProps) {
	const [name, setName] = useState("");
	const [delegationDescription, setDelegationDescription] = useState("");
	const [mounted, setMounted] = useState(false);
	const [activeTab, setActiveTab] = useState<SubAgentTabId>("core");

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	const handleSubmit = useCallback(
		(e: React.FormEvent) => {
			e.preventDefault();
			if (name.trim() && delegationDescription.trim()) {
				onConfirm(
					name.trim(),
					delegationDescription.trim(),
					"general_assistant",
				);
				setName("");
				setDelegationDescription("");
				setActiveTab("core");
			}
		},
		[name, delegationDescription, onConfirm],
	);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const subAgentTabs = useMemo(() => {
		return [
			{
				id: "core" as SubAgentTabId,
				label: "Core",
				description: "Identity & purpose",
				icon: <Bot className="h-4 w-4" />,
			},
			{
				id: "advanced" as SubAgentTabId,
				label: "Advanced",
				description: "LLM & memory config",
				icon: <Settings className="h-4 w-4" />,
			},
		];
	}, []);

	const isFormValid = name.trim() && delegationDescription.trim();

	if (!isOpen || !mounted) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[120] flex animate-fadeIn items-center justify-center bg-black/60 backdrop-blur-sm"
			onClick={handleBackdropClick}
			role="presentation"
		>
			<div
				className="relative mx-4 flex max-h-[90vh] w-full max-w-3xl animate-scaleIn flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]"
				onClick={handleStopPropagation}
				role="dialog"
				aria-modal="true"
				aria-labelledby="sub-agent-dialog-title"
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />

				{/* Header — Workflow Management style */}
				<div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<Bot className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div>
							<h2
								id="sub-agent-dialog-title"
								className="text-lg font-semibold tracking-tight text-slate-900"
							>
								Create Sub-Agent
							</h2>
							<p className="mt-0.5 text-sm text-slate-500">
								Add a specialized agent to{" "}
								<span className="font-medium text-orange-800">
									{parentAgentName}
								</span>
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<form id="create-sub-agent-form" onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
					<div className="custom-scrollbar min-h-0 max-h-[calc(90vh-200px)] space-y-6 overflow-y-auto px-6 py-5">
						{/* Light tabs (avoid TabBar dark/orange-glow theme) */}
						<div
							className="flex flex-col gap-1 rounded-2xl border border-slate-200 bg-slate-50/80 p-1.5 sm:flex-row"
							role="tablist"
							aria-label="Sub-agent configuration"
						>
							{subAgentTabs.map((tab) => {
								const isActive = activeTab === tab.id;
								return (
									<button
										key={tab.id}
										type="button"
										role="tab"
										aria-selected={isActive}
										onClick={() => setActiveTab(tab.id)}
										className={cn(
											"group flex min-h-[3.25rem] flex-1 flex-col items-center justify-center gap-0.5 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors",
											isActive
												? "border border-orange-200 bg-white text-slate-900 shadow-sm"
												: "border border-transparent text-slate-600 hover:border-orange-200 hover:bg-white hover:text-slate-900",
										)}
									>
										<span className="inline-flex items-center gap-2 text-inherit">
											<span
												className={cn(
													"shrink-0",
													isActive
														? "text-orange-600"
														: "text-slate-500 group-hover:text-slate-900",
												)}
											>
												{tab.icon}
											</span>
											{tab.label}
										</span>
										<span className="text-center text-[11px] font-normal text-slate-500 group-hover:text-slate-700">
											{tab.description}
										</span>
									</button>
								);
							})}
						</div>

						{activeTab === "core" && (
							<SubAgentCoreSection
								name={name}
								onNameChange={setName}
								delegationDescription={delegationDescription}
								onDelegationDescriptionChange={setDelegationDescription}
								parentAgentName={parentAgentName}
							/>
						)}

						{activeTab === "advanced" && <SubAgentAdvancedSection />}
					</div>

					<div className="flex shrink-0 gap-3 border-t border-slate-200 bg-white px-6 py-4">
						<Button
							type="button"
							onClick={onClose}
							variant="ghost"
							className="flex-1 !rounded-xl !border !border-slate-200 !bg-white !text-slate-700 hover:!border-orange-400 hover:!text-orange-800"
						>
							Cancel
						</Button>
						<Button
							type="submit"
							variant="primary"
							className="flex-1 !rounded-[4px] !border !border-orange-500 !bg-orange-500 !text-white !shadow-md hover:!border-orange-600 hover:!bg-orange-600"
							icon={<Sparkles className="h-4 w-4" />}
							disabled={!isFormValid}
						>
							Create Sub-Agent
						</Button>
					</div>
				</form>
			</div>
		</div>,
		document.body,
	);
}
