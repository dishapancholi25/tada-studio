"use client";

import { Loader2, TestTube2 } from "lucide-react";
import React from "react";
import Button from "@/components/ui/Button";

interface ModelDeploymentModalFooterProps {
	isEditing: boolean;
	isSaving: boolean;
	isTesting?: boolean;
	onClose: () => void;
	onSubmit: () => void;
	onTest?: () => void;
}

const ModelDeploymentModalFooter = React.memo(
	function ModelDeploymentModalFooter({
		isEditing,
		isSaving,
		isTesting,
		onClose,
		onSubmit,
		onTest,
	}: ModelDeploymentModalFooterProps) {
		return (
			<div className="flex items-center justify-between border-t border-slate-200 bg-white px-6 py-4">
				<div>
					{isEditing && onTest && (
						<Button
							variant="ghost"
							size="sm"
							onClick={onTest}
							disabled={isSaving || isTesting}
							className="!text-slate-700 hover:!bg-slate-100 hover:!text-orange-700"
							icon={
								isTesting ? (
									<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
								) : (
									<TestTube2 className="h-4 w-4" />
								)
							}
						>
							Test Connection
						</Button>
					)}
				</div>
				<div className="flex items-center gap-3">
					<Button
						variant="secondary"
						onClick={onClose}
						disabled={isSaving}
						className="!border-slate-200 !bg-white !text-slate-800 hover:!border-orange-500 hover:!text-orange-700"
					>
						Cancel
					</Button>
					<Button
						onClick={onSubmit}
						disabled={isSaving}
						icon={
							isSaving ? (
								<Loader2 className="h-4 w-4 animate-spin text-orange-500" />
							) : undefined
						}
						className="shadow-[0_8px_20px_rgba(15,23,42,0.12)]"
					>
						{isEditing ? "Save Changes" : "Create Deployment"}
					</Button>
				</div>
			</div>
		);
	},
);

export default ModelDeploymentModalFooter;
