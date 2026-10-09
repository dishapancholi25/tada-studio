"use client";

import {
	Loader,
	Minus,
	Plus,
	X,
} from "lucide-react";
import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import FormTextarea from "@/components/ui/FormTextarea";

export interface ApiEndpointFormData {
	id?: string;
	name: string;
	description?: string;
	service_type?: string;
	url_template: string;
	method: string;
	headers?: Record<string, string>;
	query_params?: Record<string, string>;
	request_body_template?: string;
	content_type?: string;
	parameter_schema?: Record<string, any>;
	auth_type: string;
	auth_config?: Record<string, string>;
	timeout_seconds: number;
	max_retries: number;
	retry_delay: number;
	retry_on_status?: number[];
	response_format: string;
	extract_path?: string;
	success_status_codes?: number[];
	verify_ssl: boolean;
	follow_redirects: boolean;
	max_redirects: number;
	visible_to_groups?: string[];
}

interface ApiEndpointFormProps {
	isOpen: boolean;
	mode: "create" | "edit";
	initialData?: Partial<ApiEndpointFormData>;
	onClose: () => void;
	onSubmit: (data: ApiEndpointFormData) => Promise<void>;
}

const HTTP_METHODS = [
	{ value: "GET", label: "GET" },
	{ value: "POST", label: "POST" },
	{ value: "PUT", label: "PUT" },
	{ value: "PATCH", label: "PATCH" },
	{ value: "DELETE", label: "DELETE" },
];

const AUTH_TYPES = [
	{ value: "none", label: "None" },
	{ value: "bearer", label: "Bearer Token" },
	{ value: "api_key_header", label: "API Key (Header)" },
	{ value: "api_key_query", label: "API Key (Query)" },
	{ value: "basic", label: "Basic Auth" },
	{ value: "custom_token", label: "Custom Token" },
];

const RESPONSE_FORMATS = [
	{ value: "auto", label: "Auto-detect" },
	{ value: "json", label: "JSON" },
	{ value: "xml", label: "XML" },
	{ value: "binary", label: "Binary" },
];

const SERVICE_TYPES = [
	{ value: "generic", label: "Generic" },
	{ value: "servicenow", label: "ServiceNow" },
	{ value: "salesforce", label: "Salesforce" },
	{ value: "workday", label: "Workday" },
	{ value: "azure", label: "Azure" },
	{ value: "aws", label: "AWS" },
	{ value: "gcp", label: "GCP" },
	{ value: "custom", label: "Custom" },
];

const CONTENT_TYPES = [
	{ value: "", label: "Auto" },
	{ value: "application/json", label: "application/json" },
	{ value: "application/x-www-form-urlencoded", label: "application/x-www-form-urlencoded" },
	{ value: "multipart/form-data", label: "multipart/form-data" },
	{ value: "text/plain", label: "text/plain" },
	{ value: "text/xml", label: "text/xml" },
];

function getAuthConfigFields(authType: string): Array<{ key: string; label: string; placeholder: string; sensitive?: boolean }> {
	switch (authType) {
		case "bearer":
			return [{ key: "token", label: "Token", placeholder: "Enter bearer token", sensitive: true }];
		case "api_key_header":
			return [
				{ key: "header_name", label: "Header Name", placeholder: "X-API-Key" },
				{ key: "api_key", label: "API Key", placeholder: "Enter API key", sensitive: true },
			];
		case "api_key_query":
			return [
				{ key: "param_name", label: "Parameter Name", placeholder: "api_key" },
				{ key: "api_key", label: "API Key", placeholder: "Enter API key", sensitive: true },
			];
		case "basic":
			return [
				{ key: "username", label: "Username", placeholder: "Enter username" },
				{ key: "password", label: "Password", placeholder: "Enter password", sensitive: true },
			];
		case "custom_token":
			return [
				{ key: "scheme", label: "Scheme", placeholder: "Token" },
				{ key: "token", label: "Token", placeholder: "Enter token", sensitive: true },
			];
		default:
			return [];
	}
}

export default function ApiEndpointForm({
	isOpen,
	mode,
	initialData,
	onClose,
	onSubmit,
}: ApiEndpointFormProps) {
	const [saving, setSaving] = useState(false);
	const [activeSection, setActiveSection] = useState("basic");

	// Basic fields
	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [serviceType, setServiceType] = useState("generic");
	const [urlTemplate, setUrlTemplate] = useState("");
	const [method, setMethod] = useState("GET");
	const [contentType, setContentType] = useState("");
	const [requestBodyTemplate, setRequestBodyTemplate] = useState("");

	// Headers
	const [headers, setHeaders] = useState<Array<{ key: string; value: string }>>([]);

	// Auth
	const [authType, setAuthType] = useState("none");
	const [authConfig, setAuthConfig] = useState<Record<string, string>>({});

	// Response
	const [responseFormat, setResponseFormat] = useState("auto");
	const [extractPath, setExtractPath] = useState("");

	// Advanced
	const [timeoutSeconds, setTimeoutSeconds] = useState(30);
	const [maxRetries, setMaxRetries] = useState(3);
	const [retryDelay, setRetryDelay] = useState(1);
	const [verifySsl, setVerifySsl] = useState(true);
	const [followRedirects, setFollowRedirects] = useState(true);
	const [maxRedirects, setMaxRedirects] = useState(10);

	useEffect(() => {
		if (isOpen && initialData) {
			setName(initialData.name || "");
			setDescription(initialData.description || "");
			setServiceType(initialData.service_type || "generic");
			setUrlTemplate(initialData.url_template || "");
			setMethod(initialData.method || "GET");
			setContentType(initialData.content_type || "");
			setRequestBodyTemplate(initialData.request_body_template || "");
			setAuthType(initialData.auth_type || "none");
			setAuthConfig(initialData.auth_config || {});
			setResponseFormat(initialData.response_format || "auto");
			setExtractPath(initialData.extract_path || "");
			setTimeoutSeconds(initialData.timeout_seconds ?? 30);
			setMaxRetries(initialData.max_retries ?? 3);
			setRetryDelay(initialData.retry_delay ?? 1);
			setVerifySsl(initialData.verify_ssl ?? true);
			setFollowRedirects(initialData.follow_redirects ?? true);
			setMaxRedirects(initialData.max_redirects ?? 10);

			// Convert headers object to array
			const h = initialData.headers || {};
			setHeaders(Object.entries(h).map(([key, value]) => ({ key, value })));
		} else if (isOpen && !initialData) {
			// Reset form for create
			setName("");
			setDescription("");
			setServiceType("generic");
			setUrlTemplate("");
			setMethod("GET");
			setContentType("");
			setRequestBodyTemplate("");
			setAuthType("none");
			setAuthConfig({});
			setResponseFormat("auto");
			setExtractPath("");
			setTimeoutSeconds(30);
			setMaxRetries(3);
			setRetryDelay(1);
			setVerifySsl(true);
			setFollowRedirects(true);
			setMaxRedirects(10);
			setHeaders([]);
		}
		if (isOpen) {
			setActiveSection("basic");
		}
	}, [isOpen, initialData]);

	const handleSubmit = async () => {
		if (!name.trim() || !urlTemplate.trim()) return;

		setSaving(true);
		try {
			const headersObj: Record<string, string> = {};
			for (const h of headers) {
				if (h.key.trim()) {
					headersObj[h.key.trim()] = h.value;
				}
			}

			await onSubmit({
				id: initialData?.id,
				name: name.trim(),
				description: description.trim() || undefined,
				service_type: serviceType,
				url_template: urlTemplate.trim(),
				method,
				headers: Object.keys(headersObj).length > 0 ? headersObj : undefined,
				content_type: contentType || undefined,
				request_body_template: requestBodyTemplate.trim() || undefined,
				auth_type: authType,
				auth_config: authType !== "none" ? authConfig : undefined,
				timeout_seconds: timeoutSeconds,
				max_retries: maxRetries,
				retry_delay: retryDelay,
				response_format: responseFormat,
				extract_path: extractPath.trim() || undefined,
				verify_ssl: verifySsl,
				follow_redirects: followRedirects,
				max_redirects: maxRedirects,
			});
			onClose();
		} catch {
			// Error handled by caller
		} finally {
			setSaving(false);
		}
	};

	if (!isOpen) return null;

	const sections = [
		{ id: "basic", label: "Basic" },
		{ id: "request", label: "Request" },
		{ id: "auth", label: "Authentication" },
		{ id: "response", label: "Response" },
		{ id: "advanced", label: "Advanced" },
	];

	const authFields = getAuthConfigFields(authType);

	return (
		<div className="fixed inset-0 z-50 flex items-start justify-center pt-[7.5vh]">
			{/* Backdrop */}
			<div
				className="absolute inset-0 bg-black/60 backdrop-blur-sm"
				onClick={onClose}
			/>

			{/* Modal */}
			<div
				data-tutorial="endpoint-modal"
				className="relative z-10 w-full max-w-2xl max-h-[85vh] rounded-2xl overflow-hidden flex flex-col"
				style={{
					background: "var(--color-bg-secondary)",
					border: "1px solid var(--color-border)",
				}}
			>
				{/* Header */}
				<div
					className="flex items-center justify-between px-6 py-4 border-b"
					style={{ borderColor: "var(--color-border)" }}
				>
					<h2 className="text-lg font-semibold text-slate-900">
						{mode === "create" ? "Create API Endpoint" : "Edit API Endpoint"}
					</h2>
					<button
						onClick={onClose}
						className="p-1 rounded-lg hover:bg-[color:var(--color-surface)] transition-colors"
						data-tutorial="endpoint-close-btn"
					>
						<X className="w-5 h-5 text-[color:var(--color-text-muted)]" />
					</button>
				</div>

				{/* Section Tabs */}
				<div
					data-tutorial="endpoint-tabs"
					className="flex gap-1 px-6 py-3 border-b overflow-x-auto"
					style={{ borderColor: "var(--color-border)" }}
				>
					{sections.map((section) => (
						<button
							key={section.id}
							data-tutorial={`endpoint-tab-${section.id}`}
							onClick={() => setActiveSection(section.id)}
							className="px-3 py-1.5 rounded-lg text-sm font-medium transition-all whitespace-nowrap"
							style={{
								color: activeSection === section.id ? "var(--nav-link-active)" : "var(--color-text-secondary)",
								background: activeSection === section.id ? "rgba(var(--color-primary-rgb), 0.15)" : "transparent",
								border: activeSection === section.id ? "1px solid rgba(var(--color-primary-rgb), 0.3)" : "1px solid transparent",
							}}
						>
							{section.label}
						</button>
					))}
				</div>

				{/* Content */}
				<div data-tutorial="endpoint-content" className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
					{activeSection === "basic" && (
						<>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Name *
								</label>
								<FormInput
									value={name}
									onChange={(e) => setName(e.target.value)}
									placeholder="e.g. GitHub API, Weather Service"
								/>
							</div>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Description
								</label>
								<FormTextarea
									value={description}
									onChange={(e) => setDescription(e.target.value)}
									placeholder="Brief description of this API endpoint"
									rows={2}
								/>
							</div>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Service Type
								</label>
								<Dropdown
									value={serviceType}
									onChange={(value) => setServiceType(value)}
									options={SERVICE_TYPES}
								/>
							</div>
						</>
					)}

					{activeSection === "request" && (
						<>
							<div className="grid grid-cols-4 gap-3">
								<div>
									<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
										Method
									</label>
									<Dropdown
										value={method}
										onChange={setMethod}
										options={HTTP_METHODS}
									/>
								</div>
								<div className="col-span-3">
									<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
										URL Template *
									</label>
									<FormInput
										value={urlTemplate}
										onChange={(e) => setUrlTemplate(e.target.value)}
										placeholder="https://api.example.com/v1/{resource}"
									/>
								</div>
							</div>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Content Type
								</label>
								<Dropdown
									value={contentType}
									onChange={setContentType}
									options={CONTENT_TYPES}
								/>
							</div>
							{/* Headers */}
							<div>
								<div className="flex items-center justify-between mb-2">
									<label className="text-xs capitalize text-[color:var(--color-text-muted)]">
										Headers
									</label>
									<button
										type="button"
										onClick={() => setHeaders([...headers, { key: "", value: "" }])}
										className="flex items-center gap-1 text-xs text-[color:var(--color-primary-light)] hover:underline"
									>
										<Plus className="w-3 h-3" /> Add Header
									</button>
								</div>
								{headers.map((header, idx) => (
									<div key={idx} className="flex gap-2 mb-2">
										<FormInput
											className="flex-1"
											placeholder="Header name"
											value={header.key}
											onChange={(e) => {
												const updated = [...headers];
												updated[idx] = { ...updated[idx], key: e.target.value };
												setHeaders(updated);
											}}
										/>
										<FormInput
											className="flex-1"
											placeholder="Header value"
											value={header.value}
											onChange={(e) => {
												const updated = [...headers];
												updated[idx] = { ...updated[idx], value: e.target.value };
												setHeaders(updated);
											}}
										/>
										<button
											type="button"
											onClick={() => setHeaders(headers.filter((_, i) => i !== idx))}
											className="p-2 rounded-lg hover:bg-red-500/20 transition-colors"
										>
											<Minus className="w-4 h-4 text-red-400" />
										</button>
									</div>
								))}
							</div>
							{/* Body template */}
							{(method === "POST" || method === "PUT" || method === "PATCH") && (
								<div>
									<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
										Request Body Template
									</label>
									<FormTextarea
										value={requestBodyTemplate}
										onChange={(e) => setRequestBodyTemplate(e.target.value)}
										placeholder='{"key": "value"}'
										rows={4}
										className="font-mono text-sm"
									/>
								</div>
							)}
						</>
					)}

					{activeSection === "auth" && (
						<>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Authentication Type
								</label>
								<Dropdown
									value={authType}
									onChange={(val) => {
										setAuthType(val);
										setAuthConfig({});
									}}
									options={AUTH_TYPES}
								/>
							</div>
							{authFields.map((field) => (
								<div key={field.key}>
									<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
										{field.label}
									</label>
									<FormInput
										type={field.sensitive ? "password" : "text"}
										value={authConfig[field.key] || ""}
										onChange={(e) =>
											setAuthConfig({
												...authConfig,
												[field.key]: e.target.value,
											})
										}
										placeholder={field.placeholder}
									/>
								</div>
							))}
							{authType === "none" && (
								<p className="text-sm text-[color:var(--color-text-muted)]">
									No authentication will be used for this endpoint.
								</p>
							)}
						</>
					)}

					{activeSection === "response" && (
						<>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Response Format
								</label>
								<Dropdown
									value={responseFormat}
									onChange={setResponseFormat}
									options={RESPONSE_FORMATS}
								/>
							</div>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Extract Path (JSONPath)
								</label>
								<FormInput
									value={extractPath}
									onChange={(e) => setExtractPath(e.target.value)}
									placeholder="data.results"
								/>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Extract a specific field from the response using dot notation
								</p>
							</div>
						</>
					)}

					{activeSection === "advanced" && (
						<>
							<div className="grid grid-cols-3 gap-3">
								<div>
									<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
										Timeout (s)
									</label>
									<FormInput
										type="number"
										value={timeoutSeconds}
										onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
										min={1}
										max={300}
									/>
								</div>
								<div>
									<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
										Max Retries
									</label>
									<FormInput
										type="number"
										value={maxRetries}
										onChange={(e) => setMaxRetries(Number(e.target.value))}
										min={0}
										max={10}
									/>
								</div>
								<div>
									<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
										Retry Delay (s)
									</label>
									<FormInput
										type="number"
										value={retryDelay}
										onChange={(e) => setRetryDelay(Number(e.target.value))}
										min={0}
										max={60}
									/>
								</div>
							</div>
							<div>
								<label className="block text-xs capitalize text-[color:var(--color-text-muted)] mb-2">
									Max Redirects
								</label>
								<FormInput
									type="number"
									value={maxRedirects}
									onChange={(e) => setMaxRedirects(Number(e.target.value))}
									min={0}
									max={30}
								/>
							</div>
							<div className="space-y-3">
								<div className="flex items-center justify-between">
									<div>
										<span className="text-sm text-slate-700">Verify SSL</span>
										<p className="text-xs text-[color:var(--color-text-muted)]">
											Verify server SSL certificates
										</p>
									</div>
									<button
										type="button"
										onClick={() => setVerifySsl(!verifySsl)}
										className={`relative w-12 h-6 rounded-full transition-colors ${verifySsl ? "bg-[#0DA931]" : "bg-[color:var(--color-border)]"}`}
									>
										<span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${verifySsl ? "left-7" : "left-1"}`} />
									</button>
								</div>
								<div className="flex items-center justify-between">
									<div>
										<span className="text-sm text-slate-700">Follow Redirects</span>
										<p className="text-xs text-[color:var(--color-text-muted)]">
											Automatically follow HTTP redirects
										</p>
									</div>
									<button
										type="button"
										onClick={() => setFollowRedirects(!followRedirects)}
										className={`relative w-12 h-6 rounded-full transition-colors ${followRedirects ? "bg-[#0DA931]" : "bg-[color:var(--color-border)]"}`}
									>
										<span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${followRedirects ? "left-7" : "left-1"}`} />
									</button>
								</div>
							</div>
						</>
					)}
				</div>

				{/* Footer */}
				<div
					className="flex items-center justify-end gap-3 px-6 py-4 border-t"
					style={{ borderColor: "var(--color-border)" }}
				>
					<Button variant="ghost" onClick={onClose} disabled={saving}>
						Cancel
					</Button>
					<Button
						variant="primary"
						onClick={handleSubmit}
						disabled={saving || !name.trim() || !urlTemplate.trim()}
						icon={saving ? <Loader className="w-4 h-4 animate-spin text-orange-500" /> : undefined}
					>
						{saving ? "Saving..." : mode === "create" ? "Create Endpoint" : "Save Changes"}
					</Button>
				</div>
			</div>
		</div>
	);
}
