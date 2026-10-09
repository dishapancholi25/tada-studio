import { Layers, Save, X } from "lucide-react";
import type React from "react";
import { createPortal } from "react-dom";
import type { StructuredOutputSchema } from "../StructuredOutputBuilder";
import FieldsListSection from "./FieldsListSection";
import SchemaFormSection from "./SchemaFormSection";
import SchemaValidationErrors from "./SchemaValidationErrors";

interface SchemaEditorModalProps {
	editingSchema: StructuredOutputSchema;
	validationErrors: string[];
	onSave: () => void;
	onCancel: () => void;
	onSchemaChange: (schema: StructuredOutputSchema) => void;
	newFieldId: string | null;
	onNewFieldAdded?: (fieldId: string) => void;
	FieldEditor: React.ComponentType<{
		field: any;
		onChange: (field: any) => void;
		onDelete: () => void;
		isNew?: boolean;
	}>;
	isNewSchema: boolean;
}

const SchemaEditorModal: React.FC<SchemaEditorModalProps> = ({
	editingSchema,
	validationErrors,
	onSave,
	onCancel,
	onSchemaChange,
	newFieldId,
	onNewFieldAdded,
	FieldEditor,
	isNewSchema,
}) => {
	return createPortal(
		<div className="fixed inset-0 z-[120] flex animate-fadeIn items-center justify-center bg-black/40 p-6 backdrop-blur-sm">
			<div className="relative flex max-h-[90vh] w-[90vw] max-w-7xl flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)] animate-scaleIn">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				{/* Header */}
				<div className="flex flex-shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<Layers className="h-5 w-5 text-orange-600" />
						</div>
						<div>
							<h2 className="text-lg font-semibold tracking-tight text-slate-900">
								{isNewSchema ? "Create Schema" : "Edit Schema"}
							</h2>
							<p className="mt-0.5 text-sm text-slate-600">
								Define the structure and fields for this output schema
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onCancel}
						className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						aria-label="Close"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				{/* Content */}
				<div className="relative p-6 flex flex-col flex-1 min-h-0 gap-5 bg-white overflow-hidden">
					<SchemaValidationErrors errors={validationErrors} />

					{/* Schema Name - Top Row */}
					<div className="flex-shrink-0">
						<SchemaFormSection
							schema={editingSchema}
							onSchemaChange={onSchemaChange}
						/>
					</div>

					{/* Fields - Takes remaining space */}
					<div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
						<FieldsListSection
							schema={editingSchema}
							onSchemaChange={onSchemaChange}
							newFieldId={newFieldId}
							onNewFieldAdded={onNewFieldAdded}
							FieldEditor={FieldEditor}
						/>
					</div>
				</div>

				{/* Footer */}
				<div className="flex flex-shrink-0 items-center justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
					<button
						type="button"
						onClick={onCancel}
						className="rounded-[4px] border border-slate-200 bg-white px-5 py-2 font-medium text-slate-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={onSave}
						disabled={
							!editingSchema.model_name || editingSchema.fields.length === 0
						}
						className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-5 py-2 font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
					>
						<Save className="w-4 h-4" />
						Save Schema
					</button>
				</div>
			</div>
		</div>,
		document.body,
	);
};

export default SchemaEditorModal;
