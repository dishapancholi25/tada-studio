"use client";

import { Plus, Upload } from "lucide-react";
import React, { useRef } from "react";
import Button from "@/components/ui/Button";

interface CreateWorkflowTabProps {
	graphName: string;
	onGraphNameChange: (name: string) => void;
	graphDescription: string;
	onGraphDescriptionChange: (description: string) => void;
	loading: boolean;
	creatingWorkflow: boolean;
	creationMessage: string;
	onCreateGraph: () => void;
	onImportGraph: (event: React.ChangeEvent<HTMLInputElement>) => void;
	onGoToWorkflows?: () => void;
}

const MAX_DESCRIPTION_LENGTH = 200;

const CreateWorkflowTab = React.memo(function CreateWorkflowTab({
	graphName,
	onGraphNameChange,
	graphDescription,
	onGraphDescriptionChange,
	loading,
	creatingWorkflow,
	creationMessage,
	onCreateGraph,
	onImportGraph,
	onGoToWorkflows,
}: CreateWorkflowTabProps) {
	const fileInputRef = useRef<HTMLInputElement>(null);

	const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
		const value = e.target.value;
		if (value.length <= MAX_DESCRIPTION_LENGTH) {
			onGraphDescriptionChange(value);
		}
	};

	const handleImportClick = () => {
		fileInputRef.current?.click();
	};

	return (
		<div className="space-y-4">
			{/* Go to My Workflows button */}
			{onGoToWorkflows && (
				<div className="flex justify-end">
					<button
						type="button"
						onClick={onGoToWorkflows}
						className="rounded border border-[#FF5E00] bg-white px-4 py-2 text-[14px] font-semibold text-[#FF5E00] transition-colors hover:bg-[#FFF1E8]"
					>
						Go to My Workflows
					</button>
				</div>
			)}

			{/* Workflow Name */}
			<div className="space-y-1.5">
				<label className="text-[16px] font-semibold text-[#333333]">
					Workflow Name<span className="text-[#FF5E00]">*</span>
				</label>
				<p className="text-[14px] text-[#4C4C4C]">
					Enter a clear, descriptive name for your workflow.
				</p>
				<input
					data-tutorial="workflow-name-input"
					type="text"
					value={graphName}
					onChange={(e) => onGraphNameChange(e.target.value)}
					placeholder="e.g., Customer onboarding automation"
					className="w-full rounded border border-[#AAAAB4] bg-[#FAFAF9] px-4 py-3 text-[14px] text-[#333333] placeholder:text-[#7C7C7C] transition-colors focus:border-[#FF5E00] focus:outline-none focus:ring-2 focus:ring-[#FF5E00]/20"
				/>
			</div>

			{/* Description */}
			<div className="space-y-1.5">
				<label className="text-[16px] font-semibold text-[#333333]">
					Description
				</label>
				<p className="text-[14px] text-[#4C4C4C]">
					Add context about what this workflow does and when to use it
				</p>
				<div className="relative">
					<textarea
						data-tutorial="workflow-desc-input"
						value={graphDescription}
						onChange={handleDescriptionChange}
						rows={3}
						placeholder="Type here"
						className="w-full resize-none rounded border border-[#AAAAB4] bg-[#FAFAF9] px-4 py-2.5 text-[14px] text-[#333333] placeholder:text-[#7C7C7C] transition-colors focus:border-[#FF5E00] focus:outline-none focus:ring-2 focus:ring-[#FF5E00]/20"
					/>
					<span className="absolute bottom-2 right-3 text-[12px] text-[#7C7C7C]">
						{graphDescription.length}/{MAX_DESCRIPTION_LENGTH}
					</span>
				</div>
			</div>

			{/* Ready to build */}
			<div className="space-y-2">
				<h3 className="text-[16px] font-semibold text-[#333333]">Ready to build</h3>
				<p className="text-[14px] text-[#4C4C4C]">
					Import a JSON file for a workflow or create a new one.
				</p>
				<div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
					<input
						ref={fileInputRef}
						type="file"
						accept=".json"
						onChange={onImportGraph}
						disabled={creatingWorkflow}
						className="hidden"
					/>
					<button
						type="button"
						onClick={handleImportClick}
						disabled={creatingWorkflow}
						className="flex flex-1 items-center justify-center gap-2 rounded border border-[#FF5E00] bg-white px-4 py-3 text-[14px] font-semibold text-[#FF5E00] transition-colors hover:bg-[#FFF1E8] disabled:cursor-not-allowed disabled:opacity-50"
					>
						<Upload className="h-4 w-4" />
						Import JSON File
					</button>
					<Button
						data-tutorial="create-workflow-btn"
						onClick={onCreateGraph}
						disabled={loading || creatingWorkflow || !graphName.trim()}
						loading={creatingWorkflow}
						icon={<Plus className="h-4 w-4" />}
						className="flex-1 !rounded !border-[#FF5E00] !bg-[#FF5E00] !px-4 !py-3 !text-[14px] !font-semibold !text-white hover:!bg-[#E05500] disabled:!cursor-not-allowed disabled:!opacity-50"
					>
						{creatingWorkflow ? creationMessage : "Create Workflow"}
					</Button>
				</div>
			</div>
		</div>
	);
});

export default CreateWorkflowTab;
