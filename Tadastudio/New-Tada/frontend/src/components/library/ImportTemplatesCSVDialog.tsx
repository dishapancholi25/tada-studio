"use client";

import { AlertCircle, CheckCircle2, FileSpreadsheet, Upload, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";

interface ImportTemplatesCSVDialogProps {
	isOpen: boolean;
	isSubmitting?: boolean;
	onConfirm: (files: {
		workflows_csv: File;
		graph_definitions_csv: File;
		workflow_templates_csv: File;
	}) => void;
	onCancel: () => void;
}

interface FileState {
	file: File | null;
	error: string | null;
}

const CSV_FILES = [
	{
		key: "workflows_csv" as const,
		label: "Workflows CSV",
		description: "Export of the workflows table",
	},
	{
		key: "graph_definitions_csv" as const,
		label: "Graph Definitions CSV",
		description: "Export of the graph_definitions table",
	},
	{
		key: "workflow_templates_csv" as const,
		label: "Workflow Templates CSV",
		description: "Export of the workflow_templates table",
	},
];

const ImportTemplatesCSVDialog = ({
	isOpen,
	isSubmitting = false,
	onConfirm,
	onCancel,
}: ImportTemplatesCSVDialogProps) => {
	const [files, setFiles] = useState<Record<string, FileState>>({
		workflows_csv: { file: null, error: null },
		graph_definitions_csv: { file: null, error: null },
		workflow_templates_csv: { file: null, error: null },
	});

	const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

	const resetForm = useCallback(() => {
		setFiles({
			workflows_csv: { file: null, error: null },
			graph_definitions_csv: { file: null, error: null },
			workflow_templates_csv: { file: null, error: null },
		});
	}, []);

	useEffect(() => {
		if (!isOpen) {
			resetForm();
		}
	}, [isOpen, resetForm]);

	const handleFileChange = useCallback(
		(key: string, selectedFile: File | null) => {
			if (!selectedFile) {
				setFiles((prev) => ({
					...prev,
					[key]: { file: null, error: null },
				}));
				return;
			}

			if (!selectedFile.name.endsWith(".csv")) {
				setFiles((prev) => ({
					...prev,
					[key]: { file: null, error: "File must be a .csv file" },
				}));
				return;
			}

			setFiles((prev) => ({
				...prev,
				[key]: { file: selectedFile, error: null },
			}));
		},
		[],
	);

	const allFilesSelected =
		files.workflows_csv.file &&
		files.graph_definitions_csv.file &&
		files.workflow_templates_csv.file;

	const hasErrors =
		files.workflows_csv.error ||
		files.graph_definitions_csv.error ||
		files.workflow_templates_csv.error;

	const handleSubmit = useCallback(() => {
		if (!allFilesSelected || hasErrors || isSubmitting) return;

		onConfirm({
			workflows_csv: files.workflows_csv.file!,
			graph_definitions_csv: files.graph_definitions_csv.file!,
			workflow_templates_csv: files.workflow_templates_csv.file!,
		});
	}, [allFilesSelected, hasErrors, isSubmitting, files, onConfirm]);

	if (!isOpen) return null;

	return (
		<div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 backdrop-blur-xl p-4 animate-fadeIn">
			<div className="relative w-full max-w-2xl rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] overflow-hidden animate-scaleIn max-h-[90vh] overflow-y-auto">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				<div className="relative p-6 space-y-6">
					<div className="flex items-start gap-4">
						<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-[linear-gradient(135deg,#ffffff_0%,#ffffff_58%,#f59e0b_170%)]">
							<FileSpreadsheet className="h-6 w-6 text-orange-600" />
						</div>
						<div className="flex-1">
							<h2 className="text-2xl font-bold text-[color:var(--color-text-primary)]">
								Import Templates from CSV
							</h2>
							<p className="text-sm text-[color:var(--color-text-muted)] mt-1">
								Upload three CSV files exported from another database to import
								workflow templates into the library.
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

					{/* File Upload Inputs */}
					<div className="space-y-4">
						{CSV_FILES.map(({ key, label, description }) => (
							<div key={key} className="space-y-2">
								<label className="block text-sm font-medium text-[color:var(--color-text-primary)]">
									{label} *
								</label>
								<p className="text-xs text-[color:var(--color-text-muted)]">{description}</p>
								<div
									className={`flex items-center gap-3 px-4 py-3 rounded-xl border transition-all cursor-pointer ${
										files[key].file
											? "border-[#0DA931] bg-white"
											: files[key].error
												? "border-red-300 bg-white"
												: "border-slate-200 bg-white hover:border-orange-400"
									}`}
									onClick={() => fileInputRefs.current[key]?.click()}
								>
									<input
										ref={(el) => {
											fileInputRefs.current[key] = el;
										}}
										type="file"
										accept=".csv"
										className="hidden"
										onChange={(e) =>
											handleFileChange(key, e.target.files?.[0] || null)
										}
										disabled={isSubmitting}
									/>
									{files[key].file ? (
										<>
											<CheckCircle2 className="w-5 h-5 text-[#0DA931] shrink-0" />
											<span className="text-sm text-[color:var(--color-text-primary)] truncate flex-1">
												{files[key].file!.name}
											</span>
											<button
												type="button"
												onClick={(e) => {
													e.stopPropagation();
													handleFileChange(key, null);
													if (fileInputRefs.current[key]) {
														fileInputRefs.current[key]!.value = "";
													}
												}}
												className="text-[color:var(--color-text-muted)] hover:text-red-600 transition-colors"
												disabled={isSubmitting}
											>
												<X className="w-4 h-4" />
											</button>
										</>
									) : files[key].error ? (
										<>
											<AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
											<span className="text-sm text-red-400">
												{files[key].error}
											</span>
										</>
									) : (
										<>
											<Upload className="w-5 h-5 text-[color:var(--color-text-muted)] shrink-0" />
											<span className="text-sm text-[color:var(--color-text-muted)]">
												Click to select {label.toLowerCase()}...
											</span>
										</>
									)}
								</div>
							</div>
						))}
					</div>

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
							disabled={!allFilesSelected || !!hasErrors || isSubmitting}
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
									Import Templates
								</>
							)}
						</Button>
					</div>

					{/* Help Text */}
					<div className="text-xs text-[color:var(--color-text-muted)] pt-2 border-t border-slate-200">
						<p>
							<strong>Tip:</strong> Export the three CSV files from your source
							database using PostgreSQL COPY commands. Templates with matching
							name + tags will be skipped as duplicates.
						</p>
					</div>
				</div>
			</div>
		</div>
	);
};

export default ImportTemplatesCSVDialog;
