import type React from "react";
import FormInput from "../../ui/FormInput";
import type { StructuredOutputSchema } from "../StructuredOutputBuilder";

interface SchemaFormSectionProps {
	schema: StructuredOutputSchema;
	onSchemaChange: (schema: StructuredOutputSchema) => void;
}

const SchemaFormSection: React.FC<SchemaFormSectionProps> = ({
	schema,
	onSchemaChange,
}) => {
	const handleNameChange = (name: string) => {
		onSchemaChange({
			...schema,
			model_name: name,
		});
	};

	return (
		<div>
			<label
				htmlFor="schema-name-input"
				className="block text-sm capitalize text-[color:var(--color-text-muted)] mb-3 font-semibold"
			>
				Schema Name *
			</label>
			<FormInput
				id="schema-name-input"
				type="text"
				value={schema.model_name}
				onChange={(e) => handleNameChange(e.target.value)}
				placeholder="e.g., PersonInfo, CompanyData, UserProfile"
				hint="This will be the name of the generated data structure"
			/>
		</div>
	);
};

export default SchemaFormSection;
