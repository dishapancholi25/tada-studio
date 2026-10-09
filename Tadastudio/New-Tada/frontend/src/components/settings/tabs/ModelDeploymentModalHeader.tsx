"use client";

import { Brain, X } from "lucide-react";
import React from "react";

interface ModelDeploymentModalHeaderProps {
	isEditing: boolean;
	onClose: () => void;
}

const ModelDeploymentModalHeader = React.memo(
	function ModelDeploymentModalHeader({
		isEditing,
		onClose,
	}: ModelDeploymentModalHeaderProps) {
		return (
			<div className="flex shrink-0 items-start justify-between border-b border-slate-200 px-6 pb-4 pt-5">
				<div className="flex items-center gap-3">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-orange-200 bg-orange-100">
						<Brain className="h-5 w-5 text-orange-600" />
					</div>
					<div>
						<h3 className="text-lg font-semibold tracking-tight text-slate-900">
							{isEditing ? "Edit Model Deployment" : "Add Model Deployment"}
						</h3>
						<p className="mt-0.5 text-sm text-slate-600">
							Provide provider credentials and deployment details. Credentials are encrypted at rest.
						</p>
					</div>
				</div>
				<button
					type="button"
					onClick={onClose}
					className="rounded-[4px] p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
					aria-label="Close form dialog"
				>
					<X className="h-5 w-5" />
				</button>
			</div>
		);
	},
);

export default ModelDeploymentModalHeader;
