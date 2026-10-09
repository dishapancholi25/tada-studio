import {
	AlertCircle,
	Binary,
	Braces,
	CheckCircle,
	Code,
	Edit3,
	Eye,
	Hash,
	Info,
	LayoutTemplate,
	List,
	Plus,
	Save,
	ToggleLeft,
	Trash2,
	Type,
	X,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { api } from "@/lib/api";
import CustomTypeDropdown from "../ui/CustomTypeDropdown";
import FormInput from "../ui/FormInput";
import FormTextarea from "../ui/FormTextarea";
import SchemaEditorModal from "./structured-output/SchemaEditorModal";
import TemplateDropdown from "./structured-output/TemplateDropdown";

// Field types supported by the system
export const FIELD_TYPES = [
	{ value: "str", label: "String", description: "Text value" },
	{ value: "int", label: "Integer", description: "Whole number" },
	{ value: "float", label: "Float", description: "Decimal number" },
	{ value: "bool", label: "Boolean", description: "True/False value" },
	{
		value: "List[str]",
		label: "List of Strings",
		description: "Array of text values",
	},
	{
		value: "List[int]",
		label: "List of Integers",
		description: "Array of numbers",
	},
	{
		value: "List[float]",
		label: "List of Floats",
		description: "Array of decimal numbers",
	},
	{
		value: "Dict[str, Any]",
		label: "Dictionary",
		description: "Key-value pairs",
	},
	{
		value: "List[Dict[str, Any]]",
		label: "List of Dictionaries",
		description: "Array of objects (e.g. tabular rows)",
	},
] as const;

export type FieldType = (typeof FIELD_TYPES)[number]["value"];

// Template definitions
export const OUTPUT_TEMPLATES = [
	{
		id: "email",
		name: "Email Send",
		description: "Template for email sending operations",
		category: "Action",
		schema: {
			model_name: "EmailData",
			description: "Email sending configuration",
			fields: [
				{
					id: "1",
					name: "to_address",
					type: "str" as FieldType,
					description: "Recipient email address",
					required: true,
				},
				{
					id: "2",
					name: "subject",
					type: "str" as FieldType,
					description: "Email subject line",
					required: true,
				},
				{
					id: "3",
					name: "body",
					type: "str" as FieldType,
					description: "Email body content",
					required: true,
				},
				{
					id: "4",
					name: "from_address",
					type: "str" as FieldType,
					description: "Sender email address",
					required: false,
				},
				{
					id: "5",
					name: "reply_to",
					type: "str" as FieldType,
					description: "Reply-to email address",
					required: false,
				},
				{
					id: "6",
					name: "cc_addresses",
					type: "List[str]" as FieldType,
					description: "CC recipients list",
					required: false,
					default: [],
				},
				{
					id: "7",
					name: "bcc_addresses",
					type: "List[str]" as FieldType,
					description: "BCC recipients list",
					required: false,
					default: [],
				},
				{
					id: "8",
					name: "use_html",
					type: "bool" as FieldType,
					description: "Send as HTML email",
					required: false,
					default: false,
				},
				{
					id: "9",
					name: "html_body",
					type: "str" as FieldType,
					description: "HTML version of email body",
					required: false,
				},
			],
		},
	},
	{
		id: "database",
		name: "Database Insert",
		description: "Template for database insert operations",
		category: "Action",
		schema: {
			model_name: "DatabaseRecord",
			description: "Database record insertion",
			fields: [
				{
					id: "1",
					name: "table_name",
					type: "str" as FieldType,
					description: "Target database table name",
					required: true,
				},
				{
					id: "2",
					name: "record_data",
					type: "Dict[str, Any]" as FieldType,
					description: "Record data as key-value pairs",
					required: true,
				},
				{
					id: "3",
					name: "primary_key",
					type: "str" as FieldType,
					description: "Primary key value if not auto-generated",
					required: false,
				},
				{
					id: "4",
					name: "created_at",
					type: "str" as FieldType,
					description: "Creation timestamp",
					required: false,
				},
				{
					id: "5",
					name: "updated_at",
					type: "str" as FieldType,
					description: "Update timestamp",
					required: false,
				},
				{
					id: "6",
					name: "batch_records",
					type: "List[Dict[str, Any]]" as FieldType,
					description: "Multiple records for batch insert",
					required: false,
					default: [],
				},
			],
		},
	},
	{
		id: "file",
		name: "File Operation",
		description: "Template for file reading/writing operations",
		category: "Action",
		schema: {
			model_name: "FileOperation",
			description: "File operation result",
			fields: [
				{
					id: "1",
					name: "file_path",
					type: "str" as FieldType,
					description: "Path to the file",
					required: true,
				},
				{
					id: "2",
					name: "file_content",
					type: "str" as FieldType,
					description: "Extracted or generated file content",
					required: true,
				},
				{
					id: "3",
					name: "file_format",
					type: "str" as FieldType,
					description: "File format (pdf, txt, csv, json, etc.)",
					required: true,
				},
				{
					id: "4",
					name: "metadata",
					type: "Dict[str, Any]" as FieldType,
					description: "File metadata (size, modified date, etc.)",
					required: false,
					default: {},
				},
				{
					id: "5",
					name: "encoding",
					type: "str" as FieldType,
					description: "File encoding (utf-8, ascii, etc.)",
					required: false,
				},
				{
					id: "6",
					name: "extracted_data",
					type: "Dict[str, Any]" as FieldType,
					description: "Structured data extracted from file",
					required: false,
				},
			],
		},
	},
	{
		id: "http",
		name: "HTTP Request",
		description: "Template for API calls and webhooks",
		category: "Action",
		schema: {
			model_name: "HttpRequest",
			description: "HTTP request configuration",
			fields: [
				{
					id: "1",
					name: "url",
					type: "str" as FieldType,
					description: "API endpoint URL",
					required: true,
				},
				{
					id: "2",
					name: "method",
					type: "str" as FieldType,
					description: "HTTP method (GET, POST, PUT, DELETE)",
					required: true,
				},
				{
					id: "3",
					name: "headers",
					type: "Dict[str, Any]" as FieldType,
					description: "Request headers",
					required: false,
					default: {},
				},
				{
					id: "4",
					name: "body",
					type: "Dict[str, Any]" as FieldType,
					description: "Request body payload",
					required: false,
				},
				{
					id: "5",
					name: "query_params",
					type: "Dict[str, Any]" as FieldType,
					description: "URL query parameters",
					required: false,
				},
				{
					id: "6",
					name: "timeout",
					type: "int" as FieldType,
					description: "Request timeout in seconds",
					required: false,
				},
				{
					id: "7",
					name: "auth_token",
					type: "str" as FieldType,
					description: "Authentication token",
					required: false,
				},
			],
		},
	},
	{
		id: "candidate",
		name: "Candidate Assessment",
		description: "Template for recruitment workflow",
		category: "Workflow",
		schema: {
			model_name: "CandidateAssessment",
			description: "Candidate evaluation result",
			fields: [
				{
					id: "1",
					name: "candidate_name",
					type: "str" as FieldType,
					description: "Full name of the candidate",
					required: true,
				},
				{
					id: "2",
					name: "email",
					type: "str" as FieldType,
					description: "Candidate email address",
					required: true,
				},
				{
					id: "3",
					name: "resume_score",
					type: "float" as FieldType,
					description: "Resume match score (0-100)",
					required: true,
				},
				{
					id: "4",
					name: "skills_matched",
					type: "List[str]" as FieldType,
					description: "List of matching skills",
					required: true,
				},
				{
					id: "5",
					name: "experience_years",
					type: "int" as FieldType,
					description: "Years of relevant experience",
					required: true,
				},
				{
					id: "6",
					name: "education_level",
					type: "str" as FieldType,
					description: "Highest education qualification",
					required: true,
				},
				{
					id: "7",
					name: "recommendation",
					type: "str" as FieldType,
					description: "Hiring recommendation (approve/reject/review)",
					required: true,
				},
				{
					id: "8",
					name: "interview_notes",
					type: "str" as FieldType,
					description: "Additional notes for interview",
					required: false,
				},
				{
					id: "9",
					name: "rejection_reason",
					type: "str" as FieldType,
					description: "Reason if rejected",
					required: false,
				},
			],
		},
	},
	{
		id: "transform",
		name: "Data Transformation",
		description: "Template for general data processing",
		category: "Data",
		schema: {
			model_name: "TransformedData",
			description: "Data transformation result",
			fields: [
				{
					id: "1",
					name: "original_format",
					type: "str" as FieldType,
					description: "Source data format",
					required: true,
				},
				{
					id: "2",
					name: "transformed_format",
					type: "str" as FieldType,
					description: "Target data format",
					required: true,
				},
				{
					id: "3",
					name: "data",
					type: "Dict[str, Any]" as FieldType,
					description: "Transformed data object",
					required: true,
				},
				{
					id: "4",
					name: "validation_errors",
					type: "List[str]" as FieldType,
					description: "List of validation errors if any",
					required: false,
					default: [],
				},
				{
					id: "5",
					name: "transformation_timestamp",
					type: "str" as FieldType,
					description: "When transformation occurred",
					required: true,
				},
				{
					id: "6",
					name: "success",
					type: "bool" as FieldType,
					description: "Whether transformation succeeded",
					required: true,
				},
			],
		},
	},
	{
		id: "search",
		name: "Search Results",
		description: "Template for web/document search operations",
		category: "Data",
		schema: {
			model_name: "SearchResults",
			description: "Search operation results",
			fields: [
				{
					id: "1",
					name: "query",
					type: "str" as FieldType,
					description: "Search query used",
					required: true,
				},
				{
					id: "2",
					name: "total_results",
					type: "int" as FieldType,
					description: "Total number of results found",
					required: true,
				},
				{
					id: "3",
					name: "results",
					type: "List[Dict[str, Any]]" as FieldType,
					description: "List of search result objects",
					required: true,
				},
				{
					id: "4",
					name: "relevant_snippets",
					type: "List[str]" as FieldType,
					description: "Key text snippets from results",
					required: false,
					default: [],
				},
				{
					id: "5",
					name: "confidence_scores",
					type: "List[float]" as FieldType,
					description: "Relevance scores for each result",
					required: false,
					default: [],
				},
				{
					id: "6",
					name: "search_timestamp",
					type: "str" as FieldType,
					description: "When search was performed",
					required: true,
				},
			],
		},
	},
	{
		id: "decision",
		name: "Workflow Decision",
		description: "Template for condition nodes and routing",
		category: "Workflow",
		schema: {
			model_name: "WorkflowDecision",
			description: "Workflow routing decision",
			fields: [
				{
					id: "1",
					name: "decision",
					type: "str" as FieldType,
					description: "Decision outcome (approve/reject/escalate)",
					required: true,
				},
				{
					id: "2",
					name: "confidence",
					type: "float" as FieldType,
					description: "Confidence score of decision (0-1)",
					required: true,
				},
				{
					id: "3",
					name: "reasoning",
					type: "str" as FieldType,
					description: "Explanation for the decision",
					required: true,
				},
				{
					id: "4",
					name: "next_step",
					type: "str" as FieldType,
					description: "Recommended next workflow step",
					required: true,
				},
				{
					id: "5",
					name: "conditions_met",
					type: "List[str]" as FieldType,
					description: "List of conditions that were satisfied",
					required: false,
					default: [],
				},
				{
					id: "6",
					name: "additional_data",
					type: "Dict[str, Any]" as FieldType,
					description: "Any additional context data",
					required: false,
				},
			],
		},
	},
];

export interface StructuredOutputField {
	id: string;
	name: string;
	type: FieldType;
	description: string;
	required: boolean;
	default?: unknown;
}

export interface StructuredOutputSchema {
	id: string;
	model_name: string; // Keep for backend compatibility, but hidden from user
	description: string; // Keep for backend compatibility, but hidden from user
	fields: StructuredOutputField[];
}

interface FieldEditorProps {
	field: StructuredOutputField;
	onChange: (field: StructuredOutputField) => void;
	onDelete: () => void;
	isNew?: boolean;
}

const FieldEditor: React.FC<FieldEditorProps> = ({
	field,
	onChange,
	onDelete,
	isNew = false,
}) => {
	const [isEditing, setIsEditing] = useState(isNew);
	const [editField, setEditField] = useState<StructuredOutputField>(field);
	const [errors, setErrors] = useState<string[]>([]);
	const typeFieldId = `field-type-${field.id}`;
	const typeLabelId = `${typeFieldId}-label`;

	const handleStartEditing = useCallback(() => {
		setIsEditing(true);
	}, []);

	const handleBoolDefaultChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			setEditField({
				...editField,
				default: e.target.value ? e.target.value === "true" : undefined,
			});
		},
		[editField],
	);

	const handleIntDefaultChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setEditField({
				...editField,
				default: e.target.value ? parseInt(e.target.value) : undefined,
			});
		},
		[editField],
	);

	const handleFloatDefaultChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setEditField({
				...editField,
				default: e.target.value ? parseFloat(e.target.value) : undefined,
			});
		},
		[editField],
	);

	const handleTextDefaultChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setEditField({
				...editField,
				default: e.target.value || undefined,
			});
		},
		[editField],
	);

	const handleNameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setEditField({ ...editField, name: e.target.value });
		},
		[editField],
	);

	const handleTypeChange = useCallback(
		(value: string) => {
			setEditField({ ...editField, type: value as FieldType });
		},
		[editField],
	);

	const handleDescriptionChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setEditField({ ...editField, description: e.target.value });
		},
		[editField],
	);

	const handleRequiredChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setEditField({
				...editField,
				required: e.target.checked,
				default: e.target.checked ? undefined : editField.default,
			});
		},
		[editField],
	);

	const validateField = (fieldData: StructuredOutputField): string[] => {
		const errors: string[] = [];

		if (!fieldData.name.trim()) {
			errors.push("Field name is required");
		} else if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(fieldData.name)) {
			errors.push("Field name must be a valid Python identifier");
		}

		if (!fieldData.description.trim()) {
			errors.push("Field description is required");
		}

		if (
			!fieldData.required &&
			fieldData.default !== undefined &&
			fieldData.default !== null
		) {
			// Validate default value type
			const defaultValue = fieldData.default;
			switch (fieldData.type) {
				case "int":
					if (
						typeof defaultValue !== "number" ||
						!Number.isInteger(defaultValue)
					) {
						errors.push("Default value must be an integer");
					}
					break;
				case "float":
					if (typeof defaultValue !== "number") {
						errors.push("Default value must be a number");
					}
					break;
				case "bool":
					if (typeof defaultValue !== "boolean") {
						errors.push("Default value must be true or false");
					}
					break;
				case "str":
					if (typeof defaultValue !== "string") {
						errors.push("Default value must be a string");
					}
					break;
			}
		}

		return errors;
	};

	const handleSave = () => {
		const validationErrors = validateField(editField);
		if (validationErrors.length > 0) {
			setErrors(validationErrors);
			return;
		}

		setErrors([]);
		onChange(editField);
		setIsEditing(false);
	};

	const handleCancel = () => {
		setEditField(field);
		setErrors([]);
		if (isNew) {
			onDelete();
		} else {
			setIsEditing(false);
		}
	};

	const getDefaultValueInput = () => {
		if (editField.required) return null;

		const baseProps = {
			className:
				"w-full rounded border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400",
			placeholder: "Default value (optional)",
		};

		switch (editField.type) {
			case "bool":
				return (
					<select
						{...baseProps}
						value={editField.default?.toString() || ""}
						onChange={handleBoolDefaultChange}
					>
						<option value="">No default</option>
						<option value="true">True</option>
						<option value="false">False</option>
					</select>
				);
			case "int":
				return (
					<input
						{...baseProps}
						type="number"
						step="1"
						value={editField.default?.toString() || ""}
						onChange={handleIntDefaultChange}
					/>
				);
			case "float":
				return (
					<input
						{...baseProps}
						type="number"
						step="any"
						value={editField.default?.toString() || ""}
						onChange={handleFloatDefaultChange}
					/>
				);
			default:
				return (
					<input
						{...baseProps}
						type="text"
						value={editField.default?.toString() || ""}
						onChange={handleTextDefaultChange}
					/>
				);
		}
	};

	// Get icon for field type
	const getTypeIcon = () => {
		const type = field.type.toLowerCase();
		const iconClass = "w-3.5 h-3.5";

		if (type.includes("str")) return <Type className={iconClass} />;
		if (type.includes("int")) return <Hash className={iconClass} />;
		if (type.includes("float")) return <Binary className={iconClass} />;
		if (type.includes("bool")) return <ToggleLeft className={iconClass} />;
		if (type.includes("list")) return <List className={iconClass} />;
		if (type.includes("dict")) return <Braces className={iconClass} />;

		return <Type className={iconClass} />; // default icon
	};

	if (!isEditing) {
		return (
			<div className="group relative overflow-hidden rounded-[4px] border border-slate-200 bg-white px-4 py-3 transition-all duration-300 hover:border-orange-400">
				<div className="relative flex items-center gap-3 pr-32">
					{/* Type icon and badge */}
					<div className="flex flex-shrink-0 items-center gap-2">
						<div className="text-orange-600">{getTypeIcon()}</div>
						<span className="rounded border border-orange-200 bg-white px-2 py-0.5 text-[11px] font-medium capitalize tracking-wider text-orange-800">
							{field.type}
						</span>
					</div>

					{/* Field name */}
					<span className="flex-shrink-0 text-base font-semibold tracking-tight text-slate-900">
						{field.name}:
					</span>

					{/* Description - truncated */}
					<p className="flex-1 truncate text-sm text-slate-600">
						{field.description}
					</p>

					{/* Required/Optional badge - absolutely positioned far right */}
					<div className="absolute right-20 top-1/2 -translate-y-1/2">
						{field.required ? (
							<span className="rounded border border-red-200 bg-white px-2 py-0.5 text-[11px] font-medium capitalize tracking-wider text-red-700">
								Required
							</span>
						) : (
							<span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium capitalize tracking-wider text-slate-600">
								Optional
							</span>
						)}
					</div>

					{/* Action buttons - absolute positioned on right */}
					<div className="absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-1 transition-all duration-200">
						<button
							type="button"
							onClick={handleStartEditing}
							className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
							title="Edit field"
						>
							<Edit3 className="h-4 w-4" />
						</button>
						<button
							type="button"
							onClick={onDelete}
							className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-700"
							title="Delete field"
						>
							<Trash2 className="h-4 w-4" />
						</button>
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className="rounded-[4px] border border-slate-200 bg-white p-6 text-slate-900 shadow-sm">
			{errors.length > 0 && (
				<div className="mb-6 rounded-[4px] border border-red-200 bg-red-50 p-4">
					<div className="mb-3 flex items-center gap-3">
						<AlertCircle className="h-5 w-5 text-red-600" />
						<span className="font-semibold text-red-800">
							Validation Errors
						</span>
					</div>
					<ul className="space-y-2 text-sm text-red-800">
						{errors.map((error, index) => (
							<li
								key={`error-${error.substring(0, 50)}-${index}`}
								className="flex items-start gap-2"
							>
								<span className="mt-0.5 text-red-600">•</span>
								{error}
							</li>
						))}
					</ul>
				</div>
			)}

			<div className="space-y-5">
				<div>
					<label
						htmlFor="field-name-input"
						className="mb-3 block text-xs capitalize text-slate-600"
					>
						Field Name *
					</label>
					<FormInput
						id="field-name-input"
						type="text"
						value={editField.name}
						onChange={handleNameChange}
						placeholder="e.g., firstName"
						className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 hover:border-slate-300"
					/>
				</div>

				<div>
					<div
						id={typeLabelId}
						className="mb-3 block text-xs capitalize text-slate-600"
					>
						Type *
					</div>
					<div className="[&_label_.text-sm.font-medium]:!text-slate-900 [&_label_.text-xs]:!text-slate-600 [&_label_span.capitalize]:!text-slate-500">
						<CustomTypeDropdown
							id={typeFieldId}
							labelId={typeLabelId}
							value={editField.type}
							onChange={handleTypeChange}
						/>
					</div>
				</div>

				<div>
					<label
						htmlFor="field-description-textarea"
						className="mb-3 block text-xs capitalize text-slate-600"
					>
						Description *
					</label>
					<FormTextarea
						id="field-description-textarea"
						value={editField.description}
						onChange={handleDescriptionChange}
						placeholder="Describe this field to help the AI understand what to extract"
						rows={3}
						className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 hover:border-slate-300"
					/>
				</div>

				<div className="flex items-center gap-4">
					<label className="flex items-center gap-3 cursor-pointer group">
						<div className="relative">
							<input
								type="checkbox"
								checked={editField.required}
								onChange={handleRequiredChange}
								className="sr-only peer"
							/>
							<div
								className={`flex h-5 w-5 items-center justify-center rounded border-2 transition-all duration-200 ${
									editField.required
										? "border-orange-500 bg-orange-500 shadow-[0_0_0_2px_rgba(234,88,12,0.2)]"
										: "border-slate-300 bg-white hover:border-orange-400"
								}`}
							>
								{editField.required && (
									<svg
										className="h-3 w-3 text-white transition-opacity duration-200"
										fill="currentColor"
										viewBox="0 0 20 20"
									>
										<path
											fillRule="evenodd"
											d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
											clipRule="evenodd"
										/>
									</svg>
								)}
							</div>
						</div>
						<div className="flex flex-col">
							<span
								className={`text-sm font-medium transition-colors ${
									editField.required
										? "text-orange-800"
										: "text-slate-700 group-hover:text-slate-900"
								}`}
							>
								Required
							</span>
							<span className="text-xs text-slate-600">
								{editField.required
									? "This field must be provided"
									: "This field is optional"}
							</span>
						</div>
					</label>
				</div>

				{!editField.required && (
					<div>
						<label
							htmlFor="default-value-input"
							className="mb-3 block text-xs capitalize text-slate-600"
						>
							Default Value
						</label>
						{getDefaultValueInput()}
					</div>
				)}
			</div>

			<div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-200 pt-5">
				<button
					type="button"
					onClick={handleCancel}
					className="rounded-[4px] border border-slate-200 bg-white px-6 py-2.5 font-medium text-slate-700 transition-all hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
				>
					Cancel
				</button>
				<button
					type="button"
					onClick={handleSave}
					className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-6 py-2.5 font-medium text-white transition-all hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
				>
					<Save className="h-4 w-4" />
					Save Field
				</button>
			</div>
		</div>
	);
};

interface SchemaPreviewProps {
	schema: StructuredOutputSchema;
	onClose: () => void;
}

const SchemaPreview: React.FC<SchemaPreviewProps> = ({ schema, onClose }) => {
	const [previewData, setPreviewData] = useState<{
		model_code?: string;
		tool_code?: string;
		error?: string;
	} | null>(null);
	const [loading, setLoading] = useState(false);

	useEffect(() => {
		const fetchPreview = async () => {
			setLoading(true);
			try {
				const response = await api.previewStructuredOutputCode(
					schema as unknown as Record<string, unknown>,
				);
				if (response.success) {
					setPreviewData({
						model_code: response.model_code,
						tool_code: response.tool_code,
					});
				} else {
					setPreviewData({
						error: response.error || "Failed to generate preview",
					});
				}
			} catch (error) {
				setPreviewData({ error: "Failed to fetch preview" });
			} finally {
				setLoading(false);
			}
		};

		fetchPreview().catch((error) => {
			console.error("Failed to fetch preview:", error);
		});
	}, [schema]);

	return (
		<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
			<div className="relative max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]">
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400/50 to-transparent" />
				<div className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-4">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<Code className="h-5 w-5 text-orange-600" />
						</div>
						<h2 className="text-lg font-semibold text-slate-900">
							Generated Code Preview
						</h2>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="rounded-lg p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800"
					>
						<X className="h-5 w-5" />
					</button>
				</div>

				<div className="max-h-[calc(90vh-80px)] overflow-y-auto bg-white p-6">
					{loading ? (
						<div className="py-8 text-center">
							<div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500"></div>
							<p className="text-slate-600">Generating preview...</p>
						</div>
					) : previewData?.error ? (
						<div className="py-8 text-center">
							<AlertCircle className="mx-auto mb-2 h-8 w-8 text-red-500" />
							<p className="text-red-700">{previewData.error}</p>
						</div>
					) : (
						<div className="space-y-6">
							<div>
								<h3 className="mb-3 text-lg font-medium text-slate-900">
									Generated Pydantic Model
								</h3>
								<div className="overflow-x-auto rounded-[4px] border border-slate-200 bg-slate-800">
									<SyntaxHighlighter
										language="python"
										style={vscDarkPlus}
										customStyle={{
											margin: 0,
											padding: "1rem",
											background: "transparent",
											fontSize: "0.875rem",
										}}
									>
										{previewData?.model_code || ""}
									</SyntaxHighlighter>
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
};

interface SchemaCardProps {
	schema: StructuredOutputSchema;
	onEdit: () => void;
	onDelete: () => void;
	onPreview: () => void;
}

const SchemaCard: React.FC<SchemaCardProps> = ({
	schema,
	onEdit,
	onDelete,
	onPreview,
}) => {
	const [showJsonPreview, setShowJsonPreview] = useState(false);

	const handleToggleJsonPreview = useCallback(() => {
		setShowJsonPreview(!showJsonPreview);
	}, [showJsonPreview]);

	const handleCopyJsonPreview = useCallback(() => {
		navigator.clipboard
			.writeText(generateJsonPreview(schema))
			.catch((error) => {
				console.error("Failed to copy JSON preview:", error);
			});
	}, [schema]);

	const getTypeStyle = (type: string) => {
		if (type.includes("str")) {
			return {
				bg: "border border-orange-200 bg-white",
				text: "text-orange-800",
				short: "str",
			};
		} else if (type.includes("int")) {
			return {
				bg: "border border-cyan-200 bg-white",
				text: "text-cyan-800",
				short: "int",
			};
		} else if (type.includes("float")) {
			return {
				bg: "border border-teal-200 bg-white",
				text: "text-teal-800",
				short: "float",
			};
		} else if (type.includes("bool")) {
			return {
				bg: "border border-indigo-200 bg-white",
				text: "text-indigo-800",
				short: "bool",
			};
		} else if (type.includes("List")) {
			return {
				bg: "border border-[#0DA931] bg-white",
				text: "text-[#0DA931]",
				short: "list",
			};
		} else if (type.includes("Dict")) {
			return {
				bg: "border border-slate-200 bg-white",
				text: "text-slate-800",
				short: "dict",
			};
		}
		return {
			bg: "border border-slate-200 bg-white",
			text: "text-slate-800",
			short: "any",
		};
	};

	const generateJsonPreview = (schema: StructuredOutputSchema) => {
		const exampleData: Record<string, any> = {};

		schema.fields.forEach((field) => {
			let exampleValue;

			switch (field.type) {
				case "str":
					exampleValue =
						field.default !== undefined
							? field.default
							: `"example_${field.name}"`;
					break;
				case "int":
					exampleValue = field.default !== undefined ? field.default : 42;
					break;
				case "float":
					exampleValue = field.default !== undefined ? field.default : 3.14;
					break;
				case "bool":
					exampleValue = field.default !== undefined ? field.default : true;
					break;
				case "List[str]":
					exampleValue =
						field.default !== undefined
							? field.default
							: [`"item1"`, `"item2"`];
					break;
				case "List[int]":
					exampleValue =
						field.default !== undefined ? field.default : [1, 2, 3];
					break;
				case "List[float]":
					exampleValue =
						field.default !== undefined ? field.default : [1.1, 2.2, 3.3];
					break;
				case "Dict[str, Any]":
					exampleValue =
						field.default !== undefined ? field.default : { key: "value" };
					break;
				case "List[Dict[str, Any]]":
					exampleValue =
						field.default !== undefined
							? field.default
							: [{ key: "value" }];
					break;
				default:
					exampleValue =
						field.default !== undefined
							? field.default
							: `"${field.name}_value"`;
			}

			if (field.required || field.default !== undefined) {
				exampleData[field.name] = exampleValue;
			}
		});

		return JSON.stringify(exampleData, null, 2);
	};

	return (
		<div className="relative overflow-hidden rounded-[4px] border border-slate-200 bg-white p-8 shadow-sm">
			<div className="pointer-events-none absolute right-0 top-0 p-6 opacity-5">
				<Code className="h-32 w-32 text-orange-500" />
			</div>

			{/* Header */}
			<div className="relative mb-8 flex items-start justify-between">
				<div className="flex-1">
					<div className="mb-2 flex flex-wrap items-center gap-4">
						<h4 className="text-xl font-semibold tracking-tight text-slate-900">
							{schema.model_name || "Unnamed Schema"}
						</h4>
						<span className="rounded-md border border-[#0DA931] bg-white px-2.5 py-0.5 text-[10px] font-bold capitalize tracking-wider text-[#0DA931]">
							Active
						</span>
					</div>
					<p className="mb-4 max-w-2xl text-sm font-light text-slate-600">
						The agent will strictly adhere to this schema when generating its
						response.
					</p>

					{/* Stats badges */}
					<div className="flex flex-wrap items-center gap-3">
						<span className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700">
							<span className="h-1.5 w-1.5 rounded-full bg-orange-500"></span>
							{schema.fields.length} Fields
						</span>
						{schema.fields.length > 0 && (
							<span className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700">
								<span className="h-1.5 w-1.5 rounded-full bg-blue-500"></span>
								{schema.fields.filter((f) => f.required).length} Required
							</span>
						)}
					</div>
				</div>

				<div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-1.5 shadow-sm">
					<button
						type="button"
						onClick={handleToggleJsonPreview}
						className={`rounded-lg p-2 transition-all ${
							showJsonPreview
								? "bg-orange-50 text-orange-800"
								: "text-slate-500 hover:bg-slate-50 hover:text-slate-900"
						}`}
						title="Toggle JSON preview"
					>
						<Code className="h-4 w-4" />
					</button>
					<div className="mx-1 h-4 w-px bg-slate-200"></div>
					<button
						type="button"
						onClick={onPreview}
						className="rounded-lg p-2 text-slate-500 transition-all hover:bg-slate-50 hover:text-slate-900"
						title="Preview generated code"
					>
						<Eye className="h-4 w-4" />
					</button>
					<button
						type="button"
						onClick={onEdit}
						className="rounded-lg p-2 text-slate-500 transition-all hover:bg-slate-50 hover:text-slate-900"
						title="Edit schema"
					>
						<Edit3 className="h-4 w-4" />
					</button>
					<button
						type="button"
						onClick={onDelete}
						className="rounded-lg p-2 text-slate-500 transition-all hover:bg-red-50 hover:text-red-700"
						title="Delete schema"
					>
						<Trash2 className="h-4 w-4" />
					</button>
				</div>
			</div>

			{/* JSON Preview */}
			{showJsonPreview && (
				<div className="mb-8 animate-fadeIn rounded-[4px] border border-slate-200 bg-slate-50 p-5 shadow-inner">
					<div className="mb-3 flex items-center justify-between">
						<h5 className="flex items-center gap-2 text-xs font-bold capitalize tracking-wider text-slate-600">
							<Code className="h-3 w-3" />
							JSON Preview
						</h5>
						<button
							type="button"
							onClick={handleCopyJsonPreview}
							className="rounded border border-slate-200 bg-white px-2 py-1 text-[10px] font-medium text-slate-700 transition-colors hover:border-orange-400 hover:text-slate-900"
						>
							COPY JSON
						</button>
					</div>
					<pre className="custom-scrollbar overflow-x-auto font-mono text-sm text-slate-800">
						<code>{generateJsonPreview(schema)}</code>
					</pre>
				</div>
			)}

			{/* Field details */}
			{schema.fields.length > 0 && (
				<div className="relative mt-6">
					<div className="mb-4 flex flex-wrap items-center justify-between gap-3">
						<h5 className="text-[0.7rem] font-bold capitalize text-slate-600">
							Fields Overview
						</h5>
						<div className="flex flex-wrap items-center gap-2">
							<span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-700">
								{schema.fields.length} Fields
							</span>
							<span className="rounded-full border border-orange-400 bg-white px-3 py-1 text-[11px] font-medium text-orange-900">
								{schema.fields.filter((f) => f.required).length} Required
							</span>
						</div>
					</div>

					<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
						{schema.fields.map((field) => {
							const typeStyle = getTypeStyle(field.type);
							const hasDefault =
								field.default !== undefined && field.default !== null;

							const getTypeIcon = () => {
								const iconClass = "w-3.5 h-3.5";
								if (field.type.includes("str"))
									return <Type className={iconClass} />;
								if (field.type.includes("int"))
									return <Hash className={iconClass} />;
								if (field.type.includes("float"))
									return <Binary className={iconClass} />;
								if (field.type.includes("bool"))
									return <ToggleLeft className={iconClass} />;
								if (field.type.includes("List"))
									return <List className={iconClass} />;
								if (field.type.includes("Dict"))
									return <Braces className={iconClass} />;
								return <Type className={iconClass} />;
							};

							return (
								<div
									key={field.id}
									className="group relative overflow-hidden rounded-[4px] border border-slate-200 bg-white p-4 transition-all duration-300 hover:border-orange-400"
								>
									<div className="relative space-y-3">
										<div className="flex items-start justify-between gap-3">
											<div className="flex min-w-0 items-center gap-2">
												<span
													className={`h-2 w-2 rounded-full ${field.required ? "bg-red-500" : "bg-slate-400"}`}
												/>
												<span className="truncate text-sm font-semibold text-slate-900">
													{field.name}
												</span>
											</div>
											<span
												className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ${typeStyle.bg} ${typeStyle.text}`}
											>
												{getTypeIcon()}
												{field.type}
											</span>
										</div>

										<p className="line-clamp-2 text-xs leading-relaxed text-slate-600">
											{field.description || "No description provided."}
										</p>

										<div className="flex items-center gap-2 text-[10px] capitalize text-slate-500">
											<span
												className={`rounded-md border px-2 py-1 font-semibold ${
													field.required
														? "border-red-200 bg-white text-red-800"
														: "border-slate-200 bg-slate-50 text-slate-700"
												}`}
											>
												{field.required ? "Required" : "Optional"}
											</span>
											{hasDefault && (
												<span className="rounded-md border border-slate-200 bg-white px-2 py-1 text-slate-700">
													Default set
												</span>
											)}
										</div>
									</div>
								</div>
							);
						})}
					</div>
				</div>
			)}
		</div>
	);
};

interface StructuredOutputBuilderProps {
	schemas: StructuredOutputSchema[];
	onChange: (schemas: StructuredOutputSchema[]) => void;
	className?: string;
}

const StructuredOutputBuilder: React.FC<StructuredOutputBuilderProps> = ({
	schemas,
	onChange,
	className = "",
}) => {
	const [editingSchema, setEditingSchema] =
		useState<StructuredOutputSchema | null>(null);
	const [showPreview, setShowPreview] = useState<StructuredOutputSchema | null>(
		null,
	);
	const [validationErrors, setValidationErrors] = useState<
		Record<string, string[]>
	>({});
	const [showTemplates, setShowTemplates] = useState(false);
	const [newFieldId, setNewFieldId] = useState<string | null>(null);
	const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
		null,
	);

	const generateId = () => Math.random().toString(36).substr(2, 9);

	const handleToggleTemplates = useCallback(() => {
		setShowTemplates((prev) => !prev);
	}, []);

	const handleEditFirstSchema = useCallback(() => {
		setEditingSchema(schemas[0]);
	}, [schemas]);

	const handleEditSchema = useCallback(() => {
		setEditingSchema(schemas[0]);
	}, [schemas]);

	const handleDeleteFirstSchema = useCallback(() => {
		removeSchema(schemas[0].id);
	}, [schemas]);

	const handlePreviewFirstSchema = useCallback(() => {
		setShowPreview(schemas[0]);
	}, [schemas]);

	const validateSchema = async (
		schema: StructuredOutputSchema,
	): Promise<string[]> => {
		try {
			const response = await api.validateStructuredOutputSchema(
				schema as unknown as Record<string, unknown>,
			);
			if (response.success && response.validation_result) {
				return response.validation_result.errors || [];
			}
			// If the API returned a response but validation failed, extract error info
			if (response.validation_result?.errors?.length > 0) {
				return response.validation_result.errors;
			}
			if (response.error) {
				return [response.error];
			}
			// Generic fallback if we got an unsuccessful response with no details
			if (!response.success) {
				return [
					"Schema validation failed. Please check your schema configuration.",
				];
			}
			return [];
		} catch (error) {
			// Network or parsing errors - show a meaningful message
			const errorMessage =
				error instanceof Error ? error.message : "Unknown error";
			console.error("Structured output validation failed:", error);
			return [`Validation request failed: ${errorMessage}`];
		}
	};

	const createNewSchema = () => {
		const newSchema: StructuredOutputSchema = {
			id: generateId(),
			model_name: "", // User must provide this
			description: "Agent output schema", // Fixed default description
			fields: [],
		};
		setEditingSchema(newSchema);
	};

	const applyTemplate = (templateId: string) => {
		const template = OUTPUT_TEMPLATES.find((t) => t.id === templateId);
		if (!template) return;

		const newSchema: StructuredOutputSchema = {
			id: generateId(),
			model_name: template.schema.model_name,
			description: template.schema.description,
			fields: template.schema.fields.map((field) => ({
				...field,
				id: generateId(), // Generate new IDs for fields
			})),
		};

		setEditingSchema(newSchema);
		setShowTemplates(false);
		setSelectedTemplateId(templateId);
	};

	const addField = (schema: StructuredOutputSchema) => {
		const newFieldId = generateId();
		const newField: StructuredOutputField = {
			id: newFieldId,
			name: "",
			type: "str",
			description: "",
			required: true,
		};

		setEditingSchema({
			...schema,
			fields: [newField, ...schema.fields],
		});

		// Set the new field ID to trigger scroll effect
		setNewFieldId(newFieldId);
	};

	const updateField = (
		schemaId: string,
		fieldId: string,
		updatedField: StructuredOutputField,
	) => {
		if (editingSchema?.id === schemaId) {
			setEditingSchema({
				...editingSchema,
				fields: editingSchema.fields.map((f) =>
					f.id === fieldId ? updatedField : f,
				),
			});
		}
	};

	const removeField = (schemaId: string, fieldId: string) => {
		if (editingSchema?.id === schemaId) {
			setEditingSchema({
				...editingSchema,
				fields: editingSchema.fields.filter((f) => f.id !== fieldId),
			});
		}
	};

	const saveSchema = useCallback(async () => {
		if (!editingSchema) return;

		// Validate schema
		const errors = await validateSchema(editingSchema);
		if (errors.length > 0) {
			setValidationErrors({ [editingSchema.id]: errors });
			return;
		}

		// Clear errors
		setValidationErrors({});

		// Update or add schema
		const isNew = !schemas.find((s) => s.id === editingSchema.id);
		if (isNew) {
			onChange([...schemas, editingSchema]);
		} else {
			onChange(
				schemas.map((s) => (s.id === editingSchema.id ? editingSchema : s)),
			);
		}

		setEditingSchema(null);
	}, [editingSchema, schemas, onChange]);

	const cancelEdit = useCallback(() => {
		setEditingSchema(null);
		setValidationErrors({});
	}, []);

	const closePreview = useCallback(() => setShowPreview(null), []);

	const createUpdateFieldHandler = useCallback(
		(schemaId: string, fieldId: string) =>
			(updatedField: StructuredOutputField) =>
				updateField(schemaId, fieldId, updatedField),
		[],
	);

	const createRemoveFieldHandler = useCallback(
		(schemaId: string, fieldId: string) => () => removeField(schemaId, fieldId),
		[],
	);

	const removeSchema = (schemaId: string) => {
		onChange(schemas.filter((s) => s.id !== schemaId));
		setValidationErrors({});
	};

	const handleApplySelectedTemplate = useCallback(() => {
		if (selectedTemplateId) {
			applyTemplate(selectedTemplateId);
		}
	}, [selectedTemplateId]);

	const templatesByCategory = useMemo(() => {
		const categories = ["Action", "Data", "Workflow"] as const;
		const grouped: Record<string, (typeof OUTPUT_TEMPLATES)[number][]> = {};
		categories.forEach((cat) => (grouped[cat] = []));

		OUTPUT_TEMPLATES.forEach((template) => {
			const category = categories.find((c) => c === template.category);
			if (category) {
				grouped[category].push(template);
			} else {
				grouped["Action"].push(template);
			}
		});

		return grouped;
	}, []);

	useEffect(() => {
		if (showTemplates && !selectedTemplateId && OUTPUT_TEMPLATES.length > 0) {
			setSelectedTemplateId(OUTPUT_TEMPLATES[0].id);
		}
	}, [showTemplates, selectedTemplateId]);

	return (
		<div className={`space-y-4 ${className}`}>
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div>
					<h3 className="text-lg font-semibold tracking-tight text-slate-900">
						Schema Configuration
					</h3>
					<p className="mt-1 text-sm text-slate-600">
						Configure the data structure for the agent&apos;s output
					</p>
				</div>
				<div className="flex flex-wrap items-center gap-3">
					<TemplateDropdown
						showTemplates={showTemplates}
						onToggle={handleToggleTemplates}
					/>

					{schemas.length === 0 ? (
						<button
							type="button"
							onClick={createNewSchema}
							className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-5 py-2 font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600"
						>
							<Plus className="h-4 w-4" />
							Add Schema
						</button>
					) : (
						<button
							type="button"
							onClick={handleEditFirstSchema}
							className="group flex items-center gap-2 rounded-[4px] border border-slate-200 bg-white px-5 py-2 font-medium text-slate-800 transition-colors hover:border-orange-400 hover:bg-slate-50"
						>
							<Edit3 className="h-4 w-4 text-slate-500 transition-colors group-hover:text-slate-900" />
							Edit Schema
						</button>
					)}
				</div>
			</div>

			{showTemplates ? (
				<div className="relative space-y-6 overflow-hidden rounded-[4px] border border-slate-200 bg-white p-6 shadow-sm">
					<div className="relative flex flex-wrap items-center justify-between gap-3">
						<div className="flex items-center gap-3">
							<div className="rounded-lg border border-orange-200 bg-orange-100 p-3">
								<LayoutTemplate className="h-5 w-5 text-orange-600" />
							</div>
							<div>
								<h4 className="text-lg font-semibold text-slate-900">
									Choose a template
								</h4>
								<p className="text-sm text-slate-600">
									Start from a prebuilt schema to speed things up.
								</p>
							</div>
						</div>
						<span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-medium text-slate-700">
							{OUTPUT_TEMPLATES.length} templates
						</span>
					</div>

					<div className="relative space-y-4">
						{(
							Object.keys(templatesByCategory) as Array<
								keyof typeof templatesByCategory
							>
						).map((category) => {
							const templates = templatesByCategory[category];
							if (!templates || templates.length === 0) return null;
							return (
								<div key={category} className="space-y-3">
									<div className="flex items-center gap-2 text-[10px] font-semibold capitalize text-slate-600">
										<span className="h-1.5 w-1.5 rounded-full bg-orange-500"></span>
										{category} Templates
									</div>
									<div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
										{templates.map((template) => {
											const isSelected = selectedTemplateId === template.id;
											return (
												<label
													key={template.id}
													className={`group relative block cursor-pointer overflow-hidden rounded-[4px] border p-4 transition-all ${
														isSelected
															? "border-orange-500 bg-white shadow-sm"
															: "border-slate-200 bg-white hover:border-orange-400 hover:bg-slate-50"
													}`}
												>
													<input
														type="radio"
														value={template.id}
														checked={isSelected}
														onChange={() => setSelectedTemplateId(template.id)}
														className="sr-only"
													/>
													<div className="relative flex items-start gap-3">
														<div
															className={`mt-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 transition-all ${
																isSelected
																	? "border-orange-500 bg-white"
																	: "border-slate-300 bg-white"
															}`}
														>
															{isSelected && (
																<div className="h-2 w-2 rounded-full bg-orange-500"></div>
															)}
														</div>
														<div className="min-w-0 flex-1 space-y-2">
															<div className="flex items-center justify-between gap-2">
																<h5 className="truncate text-base font-semibold text-slate-900">
																	{template.name}
																</h5>
																<span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
																	{template.schema.fields.length} fields
																</span>
															</div>
															<p className="line-clamp-2 text-sm text-slate-600">
																{template.description}
															</p>
															<div className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-[11px] text-slate-600">
																<LayoutTemplate className="h-3.5 w-3.5 text-orange-600" />
																{template.schema.model_name}
															</div>
														</div>
													</div>
												</label>
											);
										})}
									</div>
								</div>
							);
						})}
					</div>

					<div className="flex items-center justify-end gap-3">
						<button
							type="button"
							onClick={() => {
								setShowTemplates(false);
								setSelectedTemplateId(null);
							}}
							className="rounded-[4px] border border-slate-200 bg-white px-6 py-2.5 font-medium text-slate-700 transition-all hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleApplySelectedTemplate}
							disabled={!selectedTemplateId}
							className="flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-6 py-2.5 font-medium text-white transition-colors hover:border-orange-600 hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30"
						>
							<LayoutTemplate className="h-4 w-4" />
							Apply Template
						</button>
					</div>
				</div>
			) : (
				<>
					{/* Schema display - Only show if there's one schema */}
					{schemas.length > 0 && (
						<SchemaCard
							schema={schemas[0]}
							onEdit={handleEditSchema}
							onDelete={handleDeleteFirstSchema}
							onPreview={handlePreviewFirstSchema}
						/>
					)}

					{schemas.length === 0 && (
						<div className="group flex flex-col items-center justify-center rounded-[4px] border-2 border-dashed border-slate-300 bg-white py-16 transition-colors hover:border-orange-400">
							<div className="mb-4 rounded-full border border-slate-200 bg-slate-50 p-4 transition-transform duration-300 group-hover:scale-105">
								<Info className="h-8 w-8 text-orange-600" />
							</div>
							<h4 className="mb-2 text-lg font-medium text-slate-900">
								No structured output defined
							</h4>
							<p className="max-w-md text-center text-sm leading-relaxed text-slate-600">
								Create a schema to define exactly how the agent should format
								its response. You can start from scratch or use a template.
							</p>
							<div className="mt-6 flex items-center gap-3">
								<button
									type="button"
									onClick={createNewSchema}
									className="text-sm font-medium text-orange-700 underline-offset-2 transition-colors hover:text-slate-900 hover:underline"
								>
									Create from scratch
								</button>
								<span className="text-slate-400">•</span>
								<button
									type="button"
									onClick={handleToggleTemplates}
									className="text-sm font-medium text-orange-700 underline-offset-2 transition-colors hover:text-slate-900 hover:underline"
								>
									Browse templates
								</button>
							</div>
						</div>
					)}
				</>
			)}

			{/* Schema Editor Modal */}
			{editingSchema && (
				<SchemaEditorModal
					editingSchema={editingSchema}
					validationErrors={validationErrors[editingSchema.id] || []}
					onSave={saveSchema}
					onCancel={cancelEdit}
					onSchemaChange={setEditingSchema}
					newFieldId={newFieldId}
					onNewFieldAdded={setNewFieldId}
					FieldEditor={FieldEditor}
					isNewSchema={!schemas.find((s) => s.id === editingSchema.id)}
				/>
			)}

			{/* Code Preview Modal */}
			{showPreview && (
				<SchemaPreview schema={showPreview} onClose={closePreview} />
			)}
		</div>
	);
};

export default StructuredOutputBuilder;
