import { Plus } from "lucide-react";
import type React from "react";
import { useEffect, useRef } from "react";
import type {
	StructuredOutputField,
	StructuredOutputSchema,
} from "../StructuredOutputBuilder";

interface FieldsListSectionProps {
	schema: StructuredOutputSchema;
	onSchemaChange: (schema: StructuredOutputSchema) => void;
	newFieldId: string | null;
	onNewFieldAdded?: (fieldId: string) => void;
	FieldEditor: React.ComponentType<{
		field: StructuredOutputField;
		onChange: (field: StructuredOutputField) => void;
		onDelete: () => void;
		isNew?: boolean;
	}>;
}

const FieldsListSection: React.FC<FieldsListSectionProps> = ({
	schema,
	onSchemaChange,
	newFieldId,
	onNewFieldAdded,
	FieldEditor,
}) => {
	const modalContentRef = useRef<HTMLDivElement>(null);

	const addField = () => {
		const newFieldId = Math.random().toString(36).substr(2, 9);
		const newField: StructuredOutputField = {
			id: newFieldId,
			name: "",
			type: "str",
			description: "",
			required: true,
		};

		onSchemaChange({
			...schema,
			fields: [newField, ...schema.fields],
		});

		onNewFieldAdded?.(newFieldId);
	};

	const updateField = (
		fieldId: string,
		updatedField: StructuredOutputField,
	) => {
		onSchemaChange({
			...schema,
			fields: schema.fields.map((f) => (f.id === fieldId ? updatedField : f)),
		});
	};

	const removeField = (fieldId: string) => {
		onSchemaChange({
			...schema,
			fields: schema.fields.filter((f) => f.id !== fieldId),
		});
	};

	// Auto-scroll to new field when added
	useEffect(() => {
		if (newFieldId && modalContentRef.current) {
			const timer = setTimeout(() => {
				const newFieldElement = modalContentRef.current?.querySelector(
					`[data-field-id="${newFieldId}"]`,
				);
				if (newFieldElement) {
					newFieldElement.scrollIntoView({
						behavior: "smooth",
						block: "center",
						inline: "nearest",
					});
				}
			}, 100);

			return () => clearTimeout(timer);
		}
	}, [newFieldId]);

	return (
		<div ref={modalContentRef}>
			<div className="flex items-center justify-between mb-5">
				<h3 className="text-sm capitalize text-[color:var(--color-text-muted)] font-semibold">
					Fields
				</h3>
				<button
					onClick={addField}
					className="flex items-center gap-2 px-5 py-2 bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.85)] text-[color:var(--button-primary-text)] rounded-lg transition-all shadow-md hover:shadow-lg hover:-translate-y-0.5 font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]"
				>
					<Plus className="w-4 h-4" />
					Add Field
				</button>
			</div>

			<div className="space-y-4">
				{schema.fields.map((field, index) => (
					<div key={field.id} data-field-id={field.id}>
						<FieldEditor
							field={field}
							onChange={(updatedField) => updateField(field.id, updatedField)}
							onDelete={() => removeField(field.id)}
							isNew={!field.name}
						/>
					</div>
				))}

				{schema.fields.length === 0 && (
					<div className="text-center py-12 bg-[color:var(--color-bg-secondary)] border border-[color:var(--color-border)] rounded">
						<div className="mb-3 flex justify-center">
							<div className="p-3 bg-[rgba(var(--color-primary-rgb),0.1)] rounded-xl">
								<Plus className="w-6 h-6 text-[color:var(--color-primary)]/50" />
							</div>
						</div>
						<p className="text-sm text-[color:var(--color-text-secondary)] mb-1 font-medium">
							No fields defined
						</p>
						<p className="text-xs text-[color:var(--color-text-muted)]">
							Click "Add Field" above to create your first field
						</p>
					</div>
				)}
			</div>
		</div>
	);
};

export default FieldsListSection;
