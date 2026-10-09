"use client";

import { Copy, Globe, Loader2, Users, X } from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import { api } from "@/lib/api";
import type { CollectionDependency } from "@/types/api";

const formatAccessReason = (reason: string): string => {
	if (reason === "owner") return "You own this";
	if (reason === "global") return "Global collection";
	if (reason.startsWith("group:")) {
		const group = reason.substring(6).trim();
		return `Via group: ${group}`;
	}
	return reason;
};

const DependencyItem = ({ dependency }: { dependency: CollectionDependency }) => {
	const isGlobal = dependency.visible_to_groups.includes("__all__");
	const hasGroups = dependency.visible_to_groups.length > 0 && !isGlobal;
	const hasAccess = dependency.has_access;

	return (
		<div
			className={`flex items-start gap-3 p-3 rounded-xl border transition-all ${
				hasAccess
					? "bg-white border-slate-200"
					: "bg-white border-amber-400"
			}`}
		>
			<span className="text-lg flex-shrink-0 mt-0.5">
				{hasAccess ? "\u2705" : "\u26A0\uFE0F"}
			</span>

			<div className="flex-1 min-w-0 space-y-1">
				<div className="flex items-center gap-2 flex-wrap">
					{isGlobal && <Globe className="w-3.5 h-3.5 text-blue-400" />}
					{hasGroups &&
						dependency.visible_to_groups.map((group) => (
							<span
								key={group}
									className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-white text-purple-700 border border-purple-300"
							>
								<Users className="w-3 h-3" />
								{group}
							</span>
						))}
					<span className="text-sm font-medium text-[color:var(--color-text-primary)] truncate">
						{dependency.collection_name}
					</span>
				</div>

				<div className="text-xs text-[color:var(--color-text-muted)]">
					{hasAccess ? (
						<span>{formatAccessReason(dependency.access_reason)}</span>
					) : (
						<span className="text-amber-700">
							Private collection &bull; No access
						</span>
					)}
					{dependency.created_by_name && (
						<span> &bull; Created by {dependency.created_by_name}</span>
					)}
				</div>
			</div>
		</div>
	);
};

const DependenciesSection = ({
	dependencies,
	loading,
}: {
	dependencies: CollectionDependency[];
	loading: boolean;
}) => {
	if (loading) {
		return (
			<div className="flex items-center justify-center py-4">
				<Loader2 className="w-5 h-5 animate-spin text-[color:var(--color-text-muted)]" />
			</div>
		);
	}

	if (dependencies.length === 0) {
		return null;
	}

	return (
		<div className="space-y-2">
			<div className="text-xs capitalize font-semibold text-[color:var(--color-text-muted)]">
				Collection Dependencies
			</div>
			<div className="space-y-2 max-h-48 overflow-y-auto">
				{dependencies.map((dep) => (
					<DependencyItem key={dep.collection_name} dependency={dep} />
				))}
			</div>
		</div>
	);
};

const WarningBanner = () => (
	<div className="flex gap-3 p-3 rounded-xl bg-white border border-amber-400">
		<span className="text-lg flex-shrink-0">{"\u26A0\uFE0F"}</span>
		<div className="flex-1 text-xs text-amber-700 leading-relaxed">
			This workflow requires collections you don&apos;t have access to. The
			workflow may not function correctly until you create or gain access to
			these collections.
		</div>
	</div>
);

interface CloneWorkflowDialogProps {
	isOpen: boolean;
	templateName: string | null;
	templateId: string | null;
	onConfirm: (targetName: string) => void;
	onCancel: () => void;
}

const CloneWorkflowDialog = React.memo(function CloneWorkflowDialog({
	isOpen,
	templateName,
	templateId,
	onConfirm,
	onCancel,
}: CloneWorkflowDialogProps) {
	const [targetName, setTargetName] = useState(templateName || "");
	const [dependencies, setDependencies] = useState<CollectionDependency[]>([]);
	const [loadingDependencies, setLoadingDependencies] = useState(false);

	// Update targetName when templateName changes
	useEffect(() => {
		if (templateName) {
			setTargetName(templateName);
		}
	}, [templateName]);

	useEffect(() => {
		if (isOpen && templateId) {
			loadDependencies();
		} else {
			setDependencies([]);
		}
	}, [isOpen, templateId]);

	const loadDependencies = async () => {
		if (!templateId) return;

		setLoadingDependencies(true);
		try {
			const deps = await api.getTemplateDependencies(templateId);
			setDependencies(deps);
		} catch (error) {
			console.error("Failed to load dependencies:", error);
			// Continue anyway - dependencies are informational
		} finally {
			setLoadingDependencies(false);
		}
	};

	const handleSubmit = useCallback(() => {
		if (!targetName.trim()) {
			return;
		}

		onConfirm(targetName.trim());

		// Reset form
		setTargetName("");
	}, [targetName, onConfirm]);

	const handleKeyPress = useCallback(
		(e: React.KeyboardEvent) => {
			if (e.key === "Enter") {
				e.preventDefault();
				handleSubmit();
			} else if (e.key === "Escape") {
				onCancel();
			}
		},
		[handleSubmit, onCancel],
	);

	if (!isOpen) return null;

	const isValid = targetName.trim();

	return (
		<div className="fixed inset-0 bg-black/50 backdrop-blur-xl flex items-center justify-center z-[60] p-4 animate-fadeIn">
			<div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] animate-scaleIn">
				{/* Top glow line */}
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />

				<div className="relative p-6 space-y-6">
					{/* Header */}
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_58%,#f59e0b_170%)]">
							<Copy className="w-6 h-6 text-orange-600" />
						</div>
						<div className="flex-1 min-w-0 space-y-1">
							<h3 className="text-xl font-semibold text-[color:var(--color-text-primary)] tracking-tight">
								Clone Template
							</h3>
							<p className="text-sm text-[color:var(--color-text-muted)] leading-relaxed">
								Choose a name for your new workflow
							</p>
						</div>
						<button
							onClick={onCancel}
							className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-white border border-slate-200 text-[color:var(--color-text-muted)] hover:border-orange-400 hover:text-slate-900 transition-all"
						>
							<X className="w-4 h-4" />
						</button>
					</div>

					{/* Form */}
					<div className="space-y-2">
						<label className="text-sm font-medium text-[color:var(--color-text-primary)]">
							Workflow Name <span className="text-red-400">*</span>
						</label>
						<input
							type="text"
							value={targetName}
							onChange={(e) => setTargetName(e.target.value)}
							onKeyDown={handleKeyPress}
							placeholder="Enter workflow name"
							autoFocus
							className="w-full px-4 py-3 rounded-xl bg-white border-2 border-slate-200 text-[color:var(--color-text-primary)] placeholder:text-[color:var(--color-text-muted)] hover:border-orange-300 focus:outline-none focus:border-orange-500 focus:ring-4 focus:ring-orange-500/15 transition-all"
						/>
						<p className="text-xs text-[color:var(--color-text-muted)]">
							This will be the name of your workflow in your workspace
						</p>
					</div>

					{/* Dependencies Section */}
					{(loadingDependencies || dependencies.length > 0) && (
						<DependenciesSection
							dependencies={dependencies}
							loading={loadingDependencies}
						/>
					)}

					{/* Warning Banner */}
					{dependencies.some((d) => !d.has_access) && <WarningBanner />}

					{/* Action Buttons */}
					<div className="flex flex-col-reverse sm:flex-row gap-3 pt-2">
						<Button
							onClick={onCancel}
							variant="secondary"
							className="flex-1 !bg-white !border-slate-200 !text-[color:var(--color-text-secondary)] hover:!bg-white hover:!border-orange-400 hover:!text-orange-700 !transition-all !duration-200"
						>
							Cancel
						</Button>
						<Button
							onClick={handleSubmit}
							disabled={!isValid}
							variant="primary"
							className="flex-1 !bg-orange-500 !border-orange-500 !text-white hover:!bg-orange-600 hover:!border-orange-600 !shadow-[0_15px_40px_rgba(15,23,42,0.12)] !transition-all !duration-200 disabled:!opacity-40 disabled:!cursor-not-allowed flex items-center justify-center gap-2"
							icon={<Copy className="w-4 h-4" />}
						>
							Clone Workflow
						</Button>
					</div>
				</div>
			</div>
		</div>
	);
});

export default CloneWorkflowDialog;
