/**
 * StructuredOutputViewer - Read-only viewer for JSON Schema structured outputs
 *
 * This component displays structured output schemas (in JSON Schema format)
 * in a user-friendly way for the Agent Preview page.
 */

import {
	AlertCircle,
	Binary,
	Braces,
	CheckCircle,
	Hash,
	List,
	ToggleLeft,
	Type,
} from "lucide-react";
import type React from "react";

interface JSONSchemaProperty {
	type: string;
	description?: string;
	items?: JSONSchemaProperty;
	properties?: Record<string, JSONSchemaProperty>;
	required?: string[];
}

interface JSONSchema {
	type: string;
	properties: Record<string, JSONSchemaProperty>;
	required?: string[];
	description?: string;
}

interface StructuredOutputViewerProps {
	schemas: JSONSchema[];
}

const getTypeIcon = (type: string) => {
	switch (type) {
		case "string":
			return <Type className="w-4 h-4" />;
		case "number":
		case "integer":
			return <Hash className="w-4 h-4" />;
		case "boolean":
			return <ToggleLeft className="w-4 h-4" />;
		case "array":
			return <List className="w-4 h-4" />;
		case "object":
			return <Braces className="w-4 h-4" />;
		default:
			return <Binary className="w-4 h-4" />;
	}
};

const getTypeLabel = (type: string, items?: JSONSchemaProperty): string => {
	switch (type) {
		case "string":
			return "String";
		case "number":
			return "Number";
		case "integer":
			return "Integer";
		case "boolean":
			return "Boolean";
		case "array":
			if (items?.type === "string") return "Array of Strings";
			if (items?.type === "number") return "Array of Numbers";
			if (items?.type === "object") return "Array of Objects";
			return "Array";
		case "object":
			return "Object";
		default:
			return type;
	}
};

const getTypeColor = (type: string): string => {
	switch (type) {
		case "string":
			return "var(--color-cyan)";
		case "number":
		case "integer":
			return "var(--color-purple)";
		case "boolean":
			return "var(--color-orange)";
		case "array":
			return "var(--color-green)";
		case "object":
			return "var(--color-pink)";
		default:
			return "var(--color-primary)";
	}
};

const isObjectArray = (property: JSONSchemaProperty): boolean => {
	return (
		property.type === "array" &&
		property.items?.type === "object" &&
		Boolean(property.items.properties)
	);
};

interface PropertyViewProps {
	name: string;
	property: JSONSchemaProperty;
	isRequired: boolean;
	level?: number;
}

const PropertyView: React.FC<PropertyViewProps> = ({
	name,
	property,
	isRequired,
	level = 0,
}) => {
	const typeColor = getTypeColor(property.type);
	const indent = level * 24;

	return (
		<div className="space-y-2" style={{ marginLeft: `${indent}px` }}>
			<div className="rounded-xl border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/40 p-4 transition-all hover:border-[color:var(--color-border)]/60 hover:bg-[color:var(--color-surface)]/60">
				<div className="flex items-start gap-3">
					<div
						className="flex h-9 w-9 items-center justify-center rounded-lg border"
						style={{
							borderColor: `${typeColor}40`,
							backgroundColor: `${typeColor}15`,
							color: typeColor,
						}}
					>
						{getTypeIcon(property.type)}
					</div>
					<div className="flex-1 space-y-1.5">
						<div className="flex items-center gap-2">
							<code className="font-mono text-sm font-semibold text-slate-900">
								{name}
							</code>
							<div
								className="rounded px-2 py-0.5 text-[11px] font-semibold capitalize tracking-wide"
								style={{
									backgroundColor: `${typeColor}20`,
									color: typeColor,
								}}
							>
								{getTypeLabel(property.type, property.items)}
							</div>
							{isRequired && (
								<div className="flex items-center gap-1 rounded-full border border-[#0DA931]/40 bg-[#0DA931]/10 px-2 py-0.5 text-[10px] font-semibold capitalize tracking-wide text-[#0DA931]">
									<CheckCircle className="w-3 h-3" />
									Required
								</div>
							)}
							{!isRequired && (
								<div className="rounded-full border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/40 px-2 py-0.5 text-[10px] font-semibold capitalize tracking-wide text-[color:var(--color-text-muted)]">
									Optional
								</div>
							)}
						</div>
						{property.description && (
							<p className="text-xs text-[color:var(--color-text-muted)] leading-relaxed">
								{property.description}
							</p>
						)}
					</div>
				</div>
			</div>

			{/* Nested object properties */}
			{property.type === "object" && property.properties && (
				<div className="space-y-2 border-l-2 border-[color:var(--color-border)]/30 pl-4">
					{Object.entries(property.properties).map(([propName, propSchema]) => (
						<PropertyView
							key={propName}
							name={propName}
							property={propSchema}
							isRequired={property.required?.includes(propName) ?? false}
							level={level + 1}
						/>
					))}
				</div>
			)}

			{/* Array items (if object) */}
			{isObjectArray(property) && property.items?.properties && (
				<div className="space-y-2 border-l-2 border-[color:var(--color-border)]/30 pl-4">
					<div className="text-xs font-semibold capitalize tracking-wide text-[color:var(--color-text-muted)]">
						Array Item Structure:
					</div>
					{Object.entries(property.items.properties).map(
						([propName, propSchema]) => (
							<PropertyView
								key={propName}
								name={propName}
								property={propSchema}
								isRequired={
									property.items?.required?.includes(propName) ?? false
								}
								level={level + 1}
							/>
						),
					)}
				</div>
			)}
		</div>
	);
};

export default function StructuredOutputViewer({
	schemas,
}: StructuredOutputViewerProps) {
	if (!schemas || schemas.length === 0) {
		return (
			<div className="rounded-xl border border-[color:var(--color-border)]/40 bg-[color:var(--color-surface)]/30 p-6 text-center">
				<AlertCircle className="mx-auto mb-2 h-8 w-8 text-[color:var(--color-text-muted)]" />
				<p className="text-sm text-[color:var(--color-text-muted)]">
					No structured output schema defined for this agent.
				</p>
			</div>
		);
	}

	return (
		<div className="space-y-6">
			{schemas.map((schema, schemaIndex) => (
				<div key={schemaIndex} className="space-y-4">
					{schema.description && (
						<div className="rounded-xl border border-[color:var(--color-primary)]/30 bg-[color:var(--color-primary)]/10 p-4">
							<div className="flex items-start gap-3">
								<div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[color:var(--color-primary)]/40 bg-[color:var(--color-primary)]/20 text-[color:var(--color-primary)]">
									<Braces className="h-4 w-4" />
								</div>
								<div className="flex-1">
									<div className="text-xs font-semibold capitalize tracking-wide text-[color:var(--color-primary)]">
										Schema Description
									</div>
									<p className="mt-1 text-sm text-[color:var(--color-text-secondary)]">
										{schema.description}
									</p>
								</div>
							</div>
						</div>
					)}

					<div className="space-y-3">
						{Object.entries(schema.properties).map(([propName, propSchema]) => (
							<PropertyView
								key={propName}
								name={propName}
								property={propSchema}
								isRequired={schema.required?.includes(propName) ?? false}
							/>
						))}
					</div>

					{schemas.length > 1 && schemaIndex < schemas.length - 1 && (
						<div className="border-t border-[color:var(--color-border)]/30" />
					)}
				</div>
			))}
		</div>
	);
}
