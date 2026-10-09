"use client";

import {
	AlertCircle,
	BookOpen,
	CheckCircle2,
	ChevronDown,
	Code,
	Database,
	Eye,
	FileJson,
	FileText,
	Globe,
	Hash,
	Link2,
	Plus,
	RefreshCw,
	Search,
	Trash2,
	Wand2,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import Card from "@/components/ui/Card";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import FormLabel from "@/components/ui/FormLabel";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import Toggle from "@/components/ui/Toggle";
import { cn } from "@/lib/utils";

interface ParameterDefinition {
	name: string;
	param_type: string;
	description: string;
	required: boolean;
	default_value?: any;
	location: string;
	format?: string;
	example?: string;
	enum_values?: string[];
	min_value?: number;
	max_value?: number;
	pattern?: string;
}

interface ApiTemplateParameter {
	name: string;
	location: string;
	param_type: string;
	description: string;
	required?: boolean;
	example?: string;
}

interface ApiTemplate {
	name: string;
	url: string;
	method: string;
	contentType?: string;
	parameters: ApiTemplateParameter[];
}

interface HttpRequestSectionProps {
	urlTemplate: string;
	onUrlTemplateChange: (url: string) => void;
	method: string;
	onMethodChange: (method: string) => void;
	parameterSchema: Record<string, ParameterDefinition>;
	onParameterSchemaChange: (
		schema: Record<string, ParameterDefinition>,
	) => void;
	contentType: string;
	onContentTypeChange: (contentType: string) => void;
	userAgent: string;
	onUserAgentChange: (userAgent: string) => void;
	requestBodyTemplate: string;
	onRequestBodyTemplateChange: (template: string) => void;
}

const getMethodBorderColor = (method: string) => {
	switch (method) {
		case "GET":
			return "border-[#0DA931]/60";
		case "POST":
			return "border-blue-500/60";
		case "PUT":
			return "border-orange-500/60";
		case "DELETE":
			return "border-red-500/60";
		case "PATCH":
			return "border-yellow-500/60";
		case "HEAD":
			return "border-purple-500/60";
		case "OPTIONS":
			return "border-gray-500/60";
		default:
			return "border-gray-300";
	}
};

const getMethodBackgroundColor = (method: string) => {
	switch (method) {
		case "GET":
			return "bg-[#0DA931]/10";
		case "POST":
			return "bg-blue-500/10";
		case "PUT":
			return "bg-orange-500/10";
		case "DELETE":
			return "bg-red-500/10";
		case "PATCH":
			return "bg-yellow-500/10";
		case "HEAD":
			return "bg-purple-500/10";
		case "OPTIONS":
			return "bg-gray-500/10";
		default:
			return "bg-gray-100";
	}
};

const PARAMETER_GROUP_ORDER: Array<
	"path" | "query" | "header" | "body" | "template"
> = ["path", "query", "header", "body", "template"];

const PARAMETER_GROUP_COPY: Record<
	"path" | "query" | "header" | "body" | "template",
	{ title: string; description: string; accent: string }
> = {
	path: {
		title: "Path Parameters",
		description: "Required URL segments such as /users/{userId}.",
		accent: "text-gray-900",
	},
	query: {
		title: "Query Parameters",
		description:
			"Optional filters appended after ? like ?status=active&limit=10.",
		accent: "text-gray-900",
	},
	header: {
		title: "Header Parameters",
		description: "HTTP headers such as Authorization: Bearer token.",
		accent: "text-gray-900",
	},
	body: {
		title: "Body Parameters",
		description:
			"Values included in the JSON payload for POST/PUT/PATCH requests.",
		accent: "text-gray-900",
	},
	template: {
		title: "Template Parameters",
		description:
			"Fill {placeholder} tokens inside the raw JSON body template only — not added to the URL, headers, or as a standalone body field.",
		accent: "text-gray-900",
	},
};

const apiTemplates: Record<"quickchart" | "weather" | "stripe", ApiTemplate> = {
	quickchart: {
		name: "QuickChart API",
		url: "https://quickchart.io/chart",
		method: "POST",
		contentType: "application/json",
		parameters: [
			{
				name: "chart",
				location: "body",
				param_type: "object",
				description: "Root chart configuration object",
				required: true,
			},
			{
				name: "type",
				location: "body.chart",
				param_type: "string",
				description: "Chart type (pie, bar, line, etc.)",
				required: true,
				example: "pie",
			},
			{
				name: "data",
				location: "body.chart",
				param_type: "object",
				description: "Chart data configuration",
				required: true,
			},
			{
				name: "labels",
				location: "body.chart.data",
				param_type: "array",
				description: "Array of labels for chart segments",
				required: true,
				example: '["Chrome", "Safari", "Firefox"]',
			},
			{
				name: "datasets",
				location: "body.chart.data",
				param_type: "array",
				description: "Array of dataset objects",
				required: true,
			},
		],
	},
	weather: {
		name: "OpenWeather API",
		url: "https://api.openweathermap.org/data/2.5/weather",
		method: "GET",
		parameters: [
			{
				name: "q",
				location: "query",
				param_type: "string",
				description: "City name, state code and country code",
				required: true,
				example: "London,uk",
			},
			{
				name: "appid",
				location: "query",
				param_type: "string",
				description: "Your unique API key",
				required: true,
			},
			{
				name: "units",
				location: "query",
				param_type: "string",
				description: "Units of measurement",
				example: "metric",
			},
		],
	},
	stripe: {
		name: "Stripe Payment Intent",
		url: "https://api.stripe.com/v1/payment_intents",
		method: "POST",
		contentType: "application/x-www-form-urlencoded",
		parameters: [
			{
				name: "amount",
				location: "body",
				param_type: "number",
				description: "Amount in cents to charge",
				required: true,
				example: "2000",
			},
			{
				name: "currency",
				location: "body",
				param_type: "string",
				description: "Three-letter ISO currency code",
				required: true,
				example: "usd",
			},
			{
				name: "payment_method_types[]",
				location: "body",
				param_type: "array",
				description: "Payment method types to accept",
				example: '["card"]',
			},
		],
	},
};

export default function HttpRequestSection({
	urlTemplate,
	onUrlTemplateChange,
	method,
	onMethodChange,
	parameterSchema,
	onParameterSchemaChange,
	contentType,
	onContentTypeChange,
	userAgent,
	onUserAgentChange,
	requestBodyTemplate,
	onRequestBodyTemplateChange,
}: HttpRequestSectionProps) {
	const [showStructureBuilder, setShowStructureBuilder] = useState(false);
	const [selectedTemplate, setSelectedTemplate] = useState("");
	const [editingParam, setEditingParam] = useState<string | null>(null);
	const [newParam, setNewParam] = useState<Partial<ParameterDefinition>>({
		name: "",
		param_type: "string",
		description: "",
		required: false,
		location: "query",
		default_value: "",
		example: "",
	});
	const [showBodyPreview, setShowBodyPreview] = useState(true);
	const [bodyMode, setBodyMode] = useState<"structured" | "raw">(
		requestBodyTemplate ? "raw" : "structured",
	);

	const urlParams = useMemo(
		() => (urlTemplate.match(/\{(\w+)\}/g) || []).map((p) => p.slice(1, -1)),
		[urlTemplate],
	);

	const parameterCount = useMemo(
		() => Object.keys(parameterSchema).length,
		[parameterSchema],
	);

	const groupedParameters = useMemo(
		() =>
			Object.entries(parameterSchema).reduce(
				(acc, [paramName, param]) => {
					const baseLocation = param.location.startsWith("body")
						? "body"
						: param.location;
					if (!acc[baseLocation]) acc[baseLocation] = [];
					acc[baseLocation].push({ ...param, name: paramName });
					return acc;
				},
				{} as Record<string, Array<ParameterDefinition & { name: string }>>,
			),
		[parameterSchema],
	);

	const getLocationStyle = (location: string) => {
		if (location === "path") {
			return {
				icon: Link2,
				color: "text-orange-700",
				bgColor: "bg-gray-50",
				borderColor: "border-gray-200",
			};
		}
		if (location === "query") {
			return {
				icon: Search,
				color: "text-emerald-700",
				bgColor: "bg-gray-50",
				borderColor: "border-emerald-200",
			};
		}
		if (location === "header") {
			return {
				icon: Hash,
				color: "text-orange-700",
				bgColor: "bg-gray-50",
				borderColor: "border-gray-200",
			};
		}
		if (location.startsWith("body")) {
			return {
				icon: FileText,
				color: "text-purple-700",
				bgColor: "bg-gray-50",
				borderColor: "border-purple-200",
			};
		}
		return {
			icon: Code,
			color: "text-gray-600",
			bgColor: "bg-gray-50",
			borderColor: "border-gray-200",
		};
	};

	const generateUrlPreview = useCallback(() => {
		let preview = urlTemplate;

		Object.entries(parameterSchema).forEach(([paramName, param]) => {
			if (param.location === "path") {
				const placeholder = `{${paramName}}`;
				const exampleValue = param.example || `example_${paramName}`;
				preview = preview.replace(placeholder, exampleValue);
			}
		});

		const query: string[] = [];
		Object.entries(parameterSchema).forEach(([paramName, param]) => {
			if (param.location === "query") {
				const exampleValue =
					param.example || param.default_value || `example_${paramName}`;
				query.push(`${paramName}=${encodeURIComponent(String(exampleValue))}`);
			}
		});

		if (query.length > 0) preview = `${preview}?${query.join("&")}`;
		return preview;
	}, [urlTemplate, parameterSchema]);

	const parsePathSegment = (segment: string) => {
		const match = segment.match(/^([^[]+)(?:\[(\d+)\])?$/);
		return {
			key: match?.[1] ?? segment,
			index: match?.[2] ? Number(match[2]) : undefined,
		};
	};

	const generateBodyPreview = useCallback(() => {
		const preview: any = {};

		Object.entries(parameterSchema).forEach(([paramName, param]) => {
			if (!param.location.startsWith("body")) return;

			const generateExample = () => {
				if (param.example) {
					if (["array", "object"].includes(param.param_type)) {
						try {
							return JSON.parse(param.example);
						} catch {
							return param.example;
						}
					}
					if (param.param_type === "number")
						return Number(param.example) || param.example;
					if (param.param_type === "boolean") return param.example === "true";
					return param.example;
				}

				const lower = paramName.toLowerCase();
				if (param.param_type === "number") return 123;
				if (lower.includes("email")) return "user@example.com";
				if (lower.includes("url")) return "https://example.com";
				if (lower.includes("id")) return "12345";
				return "example_value";
			};

			const exampleValue = generateExample();

			if (param.location === "body") {
				preview[paramName] = exampleValue;
				return;
			}

			const path = param.location
				.replace(/^body\.?/, "")
				.split(".")
				.filter(Boolean);
			let current = preview;

			for (let i = 0; i < path.length; i++) {
				const { key, index } = parsePathSegment(path[i]);

				if (index !== undefined) {
					if (!current[key]) current[key] = [];
					while (current[key].length <= index) current[key].push({});
					current = current[key][index] = current[key][index] || {};
				} else {
					current[key] = current[key] || {};
					current = current[key];
				}
			}

			current[paramName] = exampleValue;
		});

		return preview;
	}, [parameterSchema]);

	const rawTemplatePlaceholders = useMemo(
		() =>
			Array.from(
				new Set(
					(requestBodyTemplate.match(/\{(\w+)\}/g) || []).map((p) =>
						p.slice(1, -1),
					),
				),
			),
		[requestBodyTemplate],
	);

	const missingRawTemplateParams = useMemo(
		() => rawTemplatePlaceholders.filter((name) => !parameterSchema[name]),
		[rawTemplatePlaceholders, parameterSchema],
	);

	const addMissingRawTemplateParams = useCallback(() => {
		if (missingRawTemplateParams.length === 0) return;
		const next = { ...parameterSchema };
		missingRawTemplateParams.forEach((name) => {
			next[name] = {
				name,
				param_type: "string",
				description: `Value for ${name}`,
				required: true,
				location: "template",
				example: "",
			};
		});
		onParameterSchemaChange(next);
	}, [missingRawTemplateParams, parameterSchema, onParameterSchemaChange]);

	const rawTemplatePreview = useMemo(() => {
		let preview = requestBodyTemplate;
		rawTemplatePlaceholders.forEach((name) => {
			const param = parameterSchema[name];
			const exampleValue =
				param?.example || param?.default_value || `example_${name}`;
			preview = preview.split(`{${name}}`).join(String(exampleValue));
		});
		return preview;
	}, [requestBodyTemplate, rawTemplatePlaceholders, parameterSchema]);

	const rawTemplateValidation = useMemo(() => {
		if (!requestBodyTemplate.trim()) {
			return { valid: true, error: null as string | null };
		}
		try {
			JSON.parse(rawTemplatePreview);
			return { valid: true, error: null as string | null };
		} catch (error) {
			return {
				valid: false,
				error: error instanceof Error ? error.message : "Invalid JSON",
			};
		}
	}, [rawTemplatePreview, requestBodyTemplate]);

	const applyTemplate = useCallback(
		(templateKey: keyof typeof apiTemplates) => {
			const template = apiTemplates[templateKey];
			if (!template) return;

			setSelectedTemplate(templateKey);
			onUrlTemplateChange(template.url);
			onMethodChange(template.method);
			if (template.contentType) onContentTypeChange(template.contentType);

			const next: Record<string, ParameterDefinition> = {};
			template.parameters.forEach((param) => {
				next[param.name] = {
					name: param.name,
					param_type: param.param_type,
					description: param.description,
					required: param.required ?? false,
					location: param.location,
					example: param.example,
				} as ParameterDefinition;
			});

			onParameterSchemaChange(next);
		},
		[
			onUrlTemplateChange,
			onMethodChange,
			onContentTypeChange,
			onParameterSchemaChange,
		],
	);

	const addParameter = useCallback(() => {
		if (!newParam.name || !newParam.description) return;

		const param: ParameterDefinition = {
			name: newParam.name,
			param_type: newParam.param_type || "string",
			description: newParam.description,
			required: newParam.required || false,
			location: newParam.location || "query",
			default_value: newParam.default_value,
			example: newParam.example,
			enum_values: newParam.enum_values,
			min_value: newParam.min_value,
			max_value: newParam.max_value,
			pattern: newParam.pattern,
		};

		onParameterSchemaChange({ ...parameterSchema, [param.name]: param });
		setNewParam({
			name: "",
			param_type: "string",
			description: "",
			required: false,
			location: "query",
			default_value: "",
			example: "",
		});
		setEditingParam(null);
	}, [newParam, parameterSchema, onParameterSchemaChange]);

	const editParameter = useCallback(
		(paramName: string) => {
			const param = parameterSchema[paramName];
			setNewParam(param);
			setEditingParam(paramName);
		},
		[parameterSchema],
	);

	const removeParameter = useCallback(
		(paramName: string) => {
			const next = { ...parameterSchema };
			delete next[paramName];
			onParameterSchemaChange(next);
		},
		[parameterSchema, onParameterSchemaChange],
	);

	const renderParameterCard = (
		param: ParameterDefinition & { name: string },
		groupKey: "path" | "query" | "header" | "body" | "template",
	) => {
		const style = getLocationStyle(groupKey);
		const badges: Array<{ label: string; className: string }> = [];

		badges.push({
			label: groupKey,
			className: `${style.bgColor} ${style.color}`,
		});
		badges.push({
			label: param.param_type,
			className: "bg-gray-100 text-gray-700",
		});

		if (param.required) {
			badges.push({
				label: "required",
				className: "bg-red-50 text-red-800",
			});
		}

		if (param.format) {
			badges.push({
				label: param.format,
				className: "bg-blue-50 text-blue-800",
			});
		}

		return (
			<div
				key={`${groupKey}-${param.name}`}
				className={cn(
					"rounded-[4px] border px-4 py-3 bg-white shadow-sm",
					style.borderColor,
				)}
			>
				<div className="flex items-start justify-between gap-3">
					<div className="space-y-2">
						<div className="flex flex-wrap items-center gap-2">
							<style.icon className={cn("w-3.5 h-3.5", style.color)} />
							<span
								className={cn(
									"font-mono text-sm font-semibold tracking-wide",
									style.color,
								)}
							>
								{param.name}
							</span>
							{badges.map((badge) => (
								<span
									key={`${param.name}-${badge.label}`}
									className={cn(
										"text-[10px] capitalize px-2 py-0.5 rounded-[4px] font-semibold tracking-wide",
										badge.className,
									)}
								>
									{badge.label}
								</span>
							))}
						</div>
						<p className="text-xs text-gray-600 leading-relaxed">
							{param.description}
						</p>
						<div className="flex flex-wrap items-center gap-3 text-[11px] text-gray-600">
							{param.default_value && (
								<span>
									<span className="text-gray-700">
										Default:
									</span>{" "}
									<code className="text-orange-800">
										{String(param.default_value)}
									</code>
								</span>
							)}
							{param.example && (
								<span>
									<span className="text-gray-700">
										Example:
									</span>{" "}
									<code className="text-purple-800">{param.example}</code>
								</span>
							)}
						</div>
					</div>
					<div className="flex items-center gap-1 ml-2">
						<button
							onClick={() => editParameter(param.name)}
							className="rounded-[4px] p-1 text-orange-700 transition-colors hover:bg-gray-100 hover:text-slate-900"
							title="Edit parameter"
						>
							<Code className="w-3.5 h-3.5" />
						</button>
						<button
							onClick={() => removeParameter(param.name)}
							className="rounded-[4px] p-1 text-red-600 transition-colors hover:bg-red-50 hover:text-red-800"
							title="Remove parameter"
						>
							<Trash2 className="w-3.5 h-3.5" />
						</button>
					</div>
				</div>
			</div>
		);
	};

	return (
		<div className="space-y-6">
			{/* Request Setup Section */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
							<Globe className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-gray-900">
								Request Setup
							</h3>
							<p className="text-sm text-gray-600">
								Configure the HTTP method, target URL, and headers
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					{/* Method & URL */}
					<div className="space-y-4">
						<FormLabel
							htmlFor="request-url"
							className="!text-xs !font-semibold !capitalize tracking-wider text-gray-900"
							tooltip="Use {param_name} to mark dynamic path segments. Complex routes like /users/{id}/posts/{postId} are supported."
						>
							Method & Request URL
						</FormLabel>

						<div
							className={cn(
								"flex flex-col overflow-hidden rounded-[4px] border-2 bg-white shadow-sm",
								getMethodBorderColor(method),
							)}
						>
							<div
								className={cn(
									"sm:w-40 border-b border-gray-200 sm:border-b-0 sm:border-r",
									getMethodBackgroundColor(method),
								)}
							>
								<style jsx>{`
                  .method-select-container .method-select button {
                    font-weight: 700 !important;
                    font-size: 12px !important;
                    height: 48px !important;
                    padding: 0 8px 0 12px !important;
                    justify-content: space-between !important;
                  }
                  .method-select-container .method-select button > div:first-child {
                    flex: 0 1 auto !important;
                    min-width: 0 !important;
                  }
                  .method-select-container .method-select button > svg {
                    flex-shrink: 0 !important;
                    margin-left: 4px !important;
                  }
                `}</style>
								<div className="method-select-container">
									<Dropdown
										menuAppearance="light"
										value={method}
										onChange={onMethodChange}
										options={[
											{
												value: "GET",
												label: "GET",
												icon: <Database className="w-3 h-3 text-[#0DA931]" />,
											},
											{
												value: "POST",
												label: "POST",
												icon: <Plus className="w-3 h-3 text-blue-400" />,
											},
											{
												value: "PUT",
												label: "PUT",
												icon: <RefreshCw className="w-3 h-3 text-orange-400" />,
											},
											{
												value: "DELETE",
												label: "DELETE",
												icon: <Trash2 className="w-3 h-3 text-red-400" />,
											},
											{
												value: "PATCH",
												label: "PATCH",
												icon: <Eye className="w-3 h-3 text-yellow-400" />,
											},
											{
												value: "HEAD",
												label: "HEAD",
												icon: <Eye className="w-3 h-3 text-purple-400" />,
											},
											{
												value: "OPTIONS",
												label: "OPTIONS",
												icon: <FileJson className="w-3 h-3 text-gray-400" />,
											},
										]}
										placeholder="GET"
										className="method-select"
									/>
								</div>
							</div>

							<input
								id="request-url"
								value={urlTemplate}
								onChange={(e) => onUrlTemplateChange(e.target.value)}
								className="flex-1 border-0 bg-transparent px-4 py-3 font-mono text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none"
								placeholder="https://api.example.com/users/{id}/posts/{postId}"
							/>
						</div>

						{urlParams.length > 0 && (
							<div className="rounded-[4px] border border-orange-500 bg-white px-4 py-3">
								<p className="text-xs font-medium text-orange-900">
									Path parameters detected:{" "}
									{urlParams.map((p) => `{${p}}`).join(", ")}
								</p>
								<p className="mt-1 text-xs text-gray-600">
									These have been added as required path parameters below.
								</p>
							</div>
						)}
					</div>

					{/* URL Preview */}
					{urlTemplate && (
						<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-5">
							<div className="mb-4 flex items-start gap-3">
								<div className="rounded-[4px] border border-gray-200 bg-white p-2">
									<Eye className="h-4 w-4 text-orange-600" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											URL Preview
										</h5>
										<InfoTooltip text="Shows how the request URL resolves once dynamic parameters are filled" />
									</div>
									<p className="mt-1 text-xs text-gray-600">
										Visual confirmation of the resolved endpoint
									</p>
								</div>
							</div>
							<div className="rounded-[4px] border border-gray-200 bg-white px-4 py-3">
								<code className="break-all font-mono text-sm text-orange-800">
									{generateUrlPreview()}
								</code>
							</div>
						</div>
					)}

					{/* Content Type & User Agent */}
					<div className="grid gap-4 md:grid-cols-2">
						<FormInput
							label="Content Type (optional)"
							value={contentType}
							onChange={(e) => onContentTypeChange(e.target.value)}
							placeholder="application/json"
						/>
						<FormInput
							label="User-Agent (optional)"
							value={userAgent}
							onChange={(e) => onUserAgentChange(e.target.value)}
							placeholder="Custom User-Agent string"
						/>
					</div>
				</div>
			</div>

			{/* Parameter Definitions Section */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
							<FileJson className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-gray-900">
								AI Parameter Definitions
							</h3>
							<p className="text-sm text-gray-600">
								Teach the automation which inputs to supply
							</p>
						</div>
					</div>
					{urlTemplate && (
						<button
							type="button"
							onClick={() => setShowStructureBuilder(!showStructureBuilder)}
							className="flex items-center gap-2 rounded-[4px] border border-purple-300 bg-white px-3 py-1.5 text-xs font-semibold text-purple-900 transition-colors hover:border-purple-400 hover:bg-gray-50 hover:text-purple-950"
						>
							<BookOpen className="w-4 h-4" />
							{showStructureBuilder ? "Hide templates" : "API templates"}
						</button>
					)}
				</div>

				<div className="mt-6 space-y-6">
					{urlTemplate ? (
						<>
							<div className="flex flex-wrap gap-3 text-[10px] capitalize tracking-wider text-gray-600">
								<span className="flex items-center gap-1">
									<Link2 className="h-3 w-3 text-orange-600" /> Path = URL segments
								</span>
								<span className="flex items-center gap-1">
									<Search className="h-3 w-3 text-emerald-600" /> Query = URL
									filters
								</span>
								<span className="flex items-center gap-1">
									<Hash className="h-3 w-3 text-orange-600" /> Header = Metadata
								</span>
								<span className="flex items-center gap-1">
									<FileText className="h-3 w-3 text-purple-600" /> Body = JSON
									payload
								</span>
							</div>

							{showStructureBuilder && (
								<Card className="border border-gray-200 bg-white shadow-sm">
									<div className="mb-3 flex items-center gap-2 text-purple-900">
										<BookOpen className="h-4 w-4 text-purple-700" />
										<h4 className="text-sm font-semibold text-gray-900">
											Quick templates
										</h4>
										<InfoTooltip text="Load pre-configured API examples to jump-start your schema" />
									</div>
									<div className="grid gap-2 sm:grid-cols-2 md:grid-cols-3">
										{Object.entries(apiTemplates).map(([key, template]) => (
											<button
												key={key}
												type="button"
												onClick={() =>
													applyTemplate(key as keyof typeof apiTemplates)
												}
												className={cn(
													"flex items-center justify-between gap-2 rounded-[4px] border px-3 py-2 text-xs transition-colors",
													selectedTemplate === key
														? "border-purple-600 bg-white text-purple-950 shadow-sm ring-1 ring-purple-200"
														: "border-gray-200 bg-white text-gray-700 hover:border-purple-400 hover:bg-gray-50 hover:text-purple-900",
												)}
											>
												<div className="flex items-center gap-2">
													<Wand2 className="h-3 w-3 text-purple-600" />
													<span className="font-medium">{template.name}</span>
												</div>
												<ChevronDown className="h-3 w-3 rotate-[-90deg] text-purple-600" />
											</button>
										))}
									</div>
									{selectedTemplate && (
										<p className="mt-2 text-xs text-gray-600">
											Parameters loaded for{" "}
											{
												apiTemplates[
													selectedTemplate as keyof typeof apiTemplates
												].name
											}
											.
										</p>
									)}
								</Card>
							)}

							{parameterCount > 0 ? (
								<div className="space-y-4">
									{PARAMETER_GROUP_ORDER.map((groupKey) => {
										const params = groupedParameters[groupKey];
										if (!params || params.length === 0) return null;
										const meta = PARAMETER_GROUP_COPY[groupKey];
										return (
											<div key={groupKey} className="space-y-3">
												<div className="flex items-center justify-between">
													<div>
														<h4
															className={cn(
																"text-sm font-semibold",
																meta.accent,
															)}
														>
															{meta.title}
														</h4>
														<p className="mt-1 text-xs text-gray-600">
															{meta.description}
														</p>
													</div>
													<span className="text-[10px] capitalize tracking-wider text-gray-800">
														{params.length} defined
													</span>
												</div>
												<div className="space-y-2">
													{params.map((param) =>
														renderParameterCard(param, groupKey),
													)}
												</div>
											</div>
										);
									})}
								</div>
							) : (
								<div className="rounded-[4px] border border-dashed border-gray-300 bg-slate-50 px-6 py-10 text-center text-sm text-gray-600">
									No parameters yet. Start by adding one below.
								</div>
							)}

							{/* Add/Edit Parameter Form */}
							<Card className="border-2 border-dashed border-gray-300 bg-white shadow-sm">
								<div className="space-y-5">
									<div className="flex items-center justify-between">
										<h4 className="text-sm font-semibold text-gray-900">
											{editingParam
												? `Editing: ${editingParam}`
												: "Define New Parameter"}
										</h4>
										<Toggle
											checked={newParam.required || false}
											onChange={(checked) =>
												setNewParam((prev) => ({ ...prev, required: checked }))
											}
											label="Required"
											size="sm"
										/>
									</div>

									<div className="space-y-4 divide-y divide-gray-200">
										<div className="space-y-3">
											<p className="text-xs font-semibold capitalize tracking-wider text-gray-900">
												Step 1: Basic Info
											</p>
											<div className="grid gap-3 lg:grid-cols-2">
												<FormInput
													label="Parameter name"
													value={newParam.name || ""}
													onChange={(e) =>
														setNewParam((prev) => ({
															...prev,
															name: e.target.value,
														}))
													}
													placeholder="e.g., user_id"
													hint={
														urlParams.includes(newParam.name || "")
															? "Auto-detected from URL"
															: undefined
													}
												/>
												<div>
													<FormLabel htmlFor="new-param-location">
														Location
													</FormLabel>
													<Dropdown
														menuAppearance="light"
														value={newParam.location || "query"}
														onChange={(value) =>
															setNewParam((prev) => ({
																...prev,
																location: value,
															}))
														}
														options={[
															{
																value: "path",
																label: "Path",
																icon: <Link2 className="w-3 h-3" />,
															},
															{
																value: "query",
																label: "Query",
																icon: <Search className="w-3 h-3" />,
															},
															{
																value: "header",
																label: "Header",
																icon: <Hash className="w-3 h-3" />,
															},
															{
																value: "body",
																label: "Body",
																icon: <FileText className="w-3 h-3" />,
															},
															{
																value: "template",
																label: "Template (raw body only)",
																icon: <Code className="w-3 h-3" />,
															},
														]}
														placeholder="Select location"
													/>
												</div>
											</div>
										</div>

										<div className="space-y-3 pt-4">
											<p className="text-xs font-semibold capitalize tracking-wider text-gray-900">
												Step 2: Description
											</p>
											<FormInput
												label=""
												value={newParam.description || ""}
												onChange={(e) =>
													setNewParam((prev) => ({
														...prev,
														description: e.target.value,
													}))
												}
												placeholder="Explain what this parameter does and any constraints..."
											/>
										</div>

										<div className="space-y-3 pt-4">
											<p className="text-xs font-semibold capitalize tracking-wider text-gray-900">
												Step 3: Type & Format
											</p>
											<div className="grid gap-3 lg:grid-cols-2">
												<Dropdown
													menuAppearance="light"
													value={newParam.param_type || "string"}
													onChange={(value) =>
														setNewParam((prev) => ({
															...prev,
															param_type: value,
														}))
													}
													options={[
														{ value: "string", label: "String" },
														{ value: "number", label: "Number" },
														{ value: "boolean", label: "Boolean" },
														{ value: "object", label: "Object" },
														{ value: "array", label: "Array" },
													]}
													placeholder="Data type"
												/>
												<FormInput
													label=""
													value={newParam.example || ""}
													onChange={(e) =>
														setNewParam((prev) => ({
															...prev,
															example: e.target.value,
														}))
													}
													placeholder={
														newParam.param_type === "array"
															? '["example"]'
															: newParam.param_type === "object"
																? '{"key": "value"}'
																: "Example value"
													}
												/>
											</div>
										</div>
									</div>
								</div>

								<div className="mt-6 flex flex-wrap items-center justify-end gap-3">
									{editingParam && (
										<button
											type="button"
											onClick={() => {
												setEditingParam(null);
												setNewParam({
													name: "",
													param_type: "string",
													description: "",
													required: false,
													location: "query",
													default_value: "",
													example: "",
												});
											}}
											className="text-xs text-gray-600 transition-colors hover:text-slate-900"
										>
											Cancel edit
										</button>
									)}
									<button
										type="button"
										onClick={addParameter}
										disabled={!newParam.name || !newParam.description}
										className="flex items-center gap-2 rounded-[4px] bg-orange-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-40"
									>
										<Plus className="w-4 h-4" />
										{editingParam ? "Update parameter" : "Add parameter"}
									</button>
								</div>
							</Card>
						</>
					) : (
						<div className="flex flex-col items-center justify-center gap-3 py-10 text-center text-sm text-gray-600">
							<FileJson className="h-10 w-10 text-gray-400" />
							<p>
								Enter a request URL to start defining parameters. Use{" "}
								<code className="text-purple-800">{"{paramName}"}</code> for
								dynamic path segments.
							</p>
						</div>
					)}
				</div>
			</div>

			{/* Request Body Section */}
			{["POST", "PUT", "PATCH"].includes(method) && (
				<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
					<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
						<div className="flex items-center gap-3">
							<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
								<Code className="h-6 w-6" />
							</div>
							<div>
								<h3 className="text-xl font-semibold text-gray-900">
									Request Body
								</h3>
								<p className="text-sm text-gray-600">
									Compose the payload from parameters, or paste a raw JSON
									template
								</p>
							</div>
						</div>
						<div className="flex items-center gap-1 rounded-[4px] border border-gray-200 bg-slate-50 p-1">
							<button
								type="button"
								onClick={() => setBodyMode("structured")}
								className={cn(
									"rounded-[4px] px-3 py-1.5 text-xs font-semibold transition-colors",
									bodyMode === "structured"
										? "bg-white text-slate-900 shadow-sm"
										: "text-gray-600 hover:text-slate-900",
								)}
							>
								Structured params
							</button>
							<button
								type="button"
								onClick={() => setBodyMode("raw")}
								className={cn(
									"rounded-[4px] px-3 py-1.5 text-xs font-semibold transition-colors",
									bodyMode === "raw"
										? "bg-white text-slate-900 shadow-sm"
										: "text-gray-600 hover:text-slate-900",
								)}
							>
								Raw JSON template
							</button>
						</div>
					</div>

					{bodyMode === "raw" ? (
						<div className="mt-6 space-y-4">
							<div>
								<FormLabel
									htmlFor="request-body-template"
									tooltip="Paste a full JSON body. Use {param_name} placeholders anywhere in the payload — including nested inside fixed structure — to inject values from your parameter definitions at runtime."
								>
									Body template
								</FormLabel>
								<textarea
									id="request-body-template"
									value={requestBodyTemplate}
									onChange={(e) =>
										onRequestBodyTemplateChange(e.target.value)
									}
									rows={14}
									spellCheck={false}
									placeholder={
										'{\n  "field_name": "{param_name}",\n  "nested": {\n    "value": "{another_param}"\n  }\n}'
									}
									className="w-full rounded-[4px] border border-gray-300 bg-slate-50 px-4 py-3 font-mono text-xs text-gray-900 shadow-inner focus:border-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-400"
								/>
							</div>

							{missingRawTemplateParams.length > 0 && (
								<div className="flex flex-wrap items-center justify-between gap-3 rounded-[4px] border border-orange-300 bg-orange-50 px-4 py-3">
									<p className="text-xs text-orange-900">
										Detected placeholder
										{missingRawTemplateParams.length > 1 ? "s" : ""}{" "}
										{missingRawTemplateParams
											.map((p) => `{${p}}`)
											.join(", ")}{" "}
										with no matching parameter definition.
									</p>
									<button
										type="button"
										onClick={addMissingRawTemplateParams}
										className="flex items-center gap-1 rounded-[4px] border border-orange-400 bg-white px-3 py-1.5 text-xs font-semibold text-orange-800 transition-colors hover:bg-orange-100"
									>
										<Plus className="h-3 w-3" />
										Create parameter
										{missingRawTemplateParams.length > 1 ? "s" : ""}
									</button>
								</div>
							)}

							{requestBodyTemplate.trim() && (
								<div className="space-y-2">
									<div className="flex items-center gap-2">
										{rawTemplateValidation.valid ? (
											<CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
										) : (
											<AlertCircle className="h-3.5 w-3.5 text-red-600" />
										)}
										<span
											className={cn(
												"text-xs font-medium",
												rawTemplateValidation.valid
													? "text-emerald-700"
													: "text-red-700",
											)}
										>
											{rawTemplateValidation.valid
												? "Valid JSON once placeholders resolve"
												: `Invalid JSON: ${rawTemplateValidation.error}`}
										</span>
									</div>
									<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-4 shadow-inner">
										<div className="mb-2 flex items-center justify-between">
											<span className="text-xs text-gray-600">
												Live preview (placeholders replaced with example
												values)
											</span>
											<button
												type="button"
												onClick={() => {
													navigator.clipboard
														.writeText(rawTemplatePreview)
														.catch((error) => {
															console.error(
																"Failed to copy body preview:",
																error,
															);
														});
												}}
												className="rounded-[4px] border border-gray-200 px-2 py-1 text-[10px] capitalize tracking-wide text-gray-700 transition-colors hover:border-orange-300 hover:bg-white hover:text-slate-900"
											>
												Copy
											</button>
										</div>
										<pre className="max-h-72 overflow-auto rounded-[4px] border border-gray-200 bg-white p-3 text-xs text-gray-800 shadow-inner">
											{rawTemplatePreview}
										</pre>
									</div>
								</div>
							)}
						</div>
					) : (
						Object.keys(parameterSchema).some((key) =>
							parameterSchema[key].location.startsWith("body"),
						) && (
							<div className="mt-6">
								<div className="flex items-center justify-between">
									<span className="text-xs text-gray-600">
										Example JSON body (using sample values)
									</span>
									<button
										type="button"
										onClick={() => setShowBodyPreview(!showBodyPreview)}
										className="text-xs text-gray-600 transition-colors hover:text-slate-900"
									>
										{showBodyPreview ? "Hide preview" : "Show preview"}
									</button>
								</div>

								{showBodyPreview && (
									<div className="mt-3 space-y-3">
										<div className="rounded-[4px] border border-gray-200 bg-slate-50 p-4 shadow-inner">
											<div className="mb-2 flex items-center justify-between">
												<span className="text-xs text-gray-600" />
												<button
													type="button"
													onClick={() => {
														navigator.clipboard
															.writeText(
																JSON.stringify(
																	generateBodyPreview(),
																	null,
																	2,
																),
															)
															.catch((error) => {
																console.error(
																	"Failed to copy JSON preview:",
																	error,
																);
															});
													}}
													className="rounded-[4px] border border-gray-200 px-2 py-1 text-[10px] capitalize tracking-wide text-gray-700 transition-colors hover:border-orange-300 hover:bg-white hover:text-slate-900"
												>
													Copy
												</button>
											</div>
											<pre className="max-h-72 overflow-auto rounded-[4px] border border-gray-200 bg-white p-3 text-xs text-gray-800 shadow-inner">
												{JSON.stringify(generateBodyPreview(), null, 2)}
											</pre>
										</div>
										<p className="text-xs text-gray-600">
											Adjust parameter definitions above to modify this
											structure. The automation replaces the example values
											with live data at runtime.
										</p>
									</div>
								)}
							</div>
						)
					)}
				</div>
			)}
		</div>
	);
}
