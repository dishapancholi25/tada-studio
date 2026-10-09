"use client";

import { LayoutTemplate, Save, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Node } from "reactflow";
import { useOutputSchemas } from "@/contexts/OutputSchemaContext";
import {
	useEscapeKey,
	useFocusTrap,
} from "@/hooks/useAccessibility";
import TemplateComposer, {
	type TemplateComposerHandle,
} from "./template-builder/TemplateComposer";
import TemplatePreview from "./template-builder/TemplatePreview";
import VariableSourcePanel from "./template-builder/VariableSourcePanel";
import {
	buildVariableGroups,
	buildVariableList,
} from "./template-builder/templateBuilderTypes";
import type { VariableInfo } from "./template-builder/templateBuilderTypes";
import { useTemplateSegments } from "./template-builder/useTemplateSegments";

interface InputTemplateBuilderModalProps {
	isOpen: boolean;
	onClose: () => void;
	template: string;
	availableNodes: Node[];
	onApply: (template: string) => void;
}

export default function InputTemplateBuilderModal({
	isOpen,
	onClose,
	template,
	availableNodes,
	onApply,
}: InputTemplateBuilderModalProps) {
	const [mounted, setMounted] = useState(false);
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);
	const composerRef = useRef<TemplateComposerHandle>(null);
	const { schemas: schemaRegistry } = useOutputSchemas();

	const variables = useMemo(
		() => buildVariableList(availableNodes, schemaRegistry),
		[availableNodes, schemaRegistry],
	);

	const groups = useMemo(
		() => buildVariableGroups(availableNodes, schemaRegistry),
		[availableNodes, schemaRegistry],
	);

	const {
		segments,
		templateString,
		replaceSegments,
	} = useTemplateSegments(template, variables);

	useEscapeKey(onClose, isOpen);

	// Body scroll prevention
	useEffect(() => {
		if (isOpen) {
			document.body.style.overflow = "hidden";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [isOpen]);

	useEffect(() => {
		setMounted(true);
	}, []);

	const handleInsertVariable = useCallback(
		(variable: VariableInfo) => {
			composerRef.current?.insertAtCursor(variable);
		},
		[],
	);

	const handleApply = useCallback(() => {
		onApply(templateString);
	}, [onApply, templateString]);

	const handleBackdropClick = useCallback(
		(e: React.MouseEvent) => {
			if (e.target === e.currentTarget) {
				onClose();
			}
		},
		[onClose],
	);

	if (!isOpen || !mounted) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex animate-fadeIn items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				ref={dialogRef}
				role="dialog"
				aria-modal="true"
				aria-labelledby="template-builder-title"
				className="relative flex w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] animate-scaleIn"
				style={{ maxHeight: "85vh" }}
				onClick={(e) => e.stopPropagation()}
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />

				{/* Header — aligned with Workflow Management */}
				<div className="flex flex-none items-center justify-between border-b border-slate-200 bg-white px-6 pt-5 pb-4">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<LayoutTemplate className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h2
								id="template-builder-title"
								className="text-lg font-semibold tracking-tight text-slate-900"
							>
								Input Template Builder
							</h2>
							<p className="mt-0.5 text-sm text-slate-600">
								Compose a custom input by combining text and variable references
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						aria-label="Close template builder"
					>
						<X className="h-4 w-4" />
					</button>
				</div>

				{/* Body: two columns */}
				<div className="relative flex min-h-0 flex-1 overflow-hidden bg-white">
					<div className="w-[280px] shrink-0 overflow-hidden border-r border-slate-200 bg-white">
						<VariableSourcePanel
							groups={groups}
							onInsert={handleInsertVariable}
						/>
					</div>

					<div className="flex min-h-0 flex-1 flex-col overflow-hidden">
						<div className="min-h-0 flex-1 overflow-y-auto p-5">
							<TemplateComposer
								ref={composerRef}
								segments={segments}
								onSegmentsChange={replaceSegments}
								variables={variables}
							/>
						</div>

						<div className="shrink-0 border-t border-slate-200 bg-slate-50/80">
							<TemplatePreview
								templateString={templateString}
								variables={variables}
							/>
						</div>
					</div>
				</div>

				<div className="flex flex-none items-center justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
					<button
						type="button"
						onClick={onClose}
						className="rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleApply}
						className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
					>
						<Save className="h-3.5 w-3.5" />
						Apply Template
					</button>
				</div>
			</div>
		</div>,
		document.body,
	);
}
