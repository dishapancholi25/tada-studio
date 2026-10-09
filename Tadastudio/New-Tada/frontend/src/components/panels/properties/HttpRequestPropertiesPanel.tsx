"use client";

import {
	Activity,
	FileText,
	Globe,
	Key,
	Link,
	Save,
	Settings,
	ShieldCheck,
	Trash2,
	X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import EndpointPicker from "@/components/ui/EndpointPicker";
import { api } from "@/lib/api";
import ConfigSidebar from "./ConfigSidebar";
import HttpAdvancedSection from "./sections/HttpAdvancedSection";
import HttpAuthSection from "./sections/HttpAuthSection";
import HttpRequestSection from "./sections/HttpRequestSection";
import HttpResponseSection from "./sections/HttpResponseSection";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
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

interface HttpRequestConfig {
	endpoint_id?: string;
	url_template?: string;
	method?: string;
	parameter_schema?: Record<string, ParameterDefinition>;
	headers?: Record<string, string>;
	query_params?: Record<string, string>;
	request_body_template?: string;
	content_type?: string;
	user_agent?: string;
	auth_type?: string;
	auth_config?: Record<string, string>;
	oauth2_config?: Record<string, string>;
	certificate_path?: string;
	timeout_seconds?: number;
	max_retries?: number;
	retry_delay?: number;
	retry_on_status?: number[];
	response_format?: string;
	error_handling?: string;
	follow_redirects?: boolean;
	max_redirects?: number;
	verify_ssl?: boolean;
	compression?: boolean;
	cookie_jar?: boolean;
	success_status_codes?: number[];
	accept_headers?: Record<string, string>;
	extract_path?: string;
	response_transform?: string;
	encoding?: string;
	proxy_config?: Record<string, string>;
	rate_limit?: Record<string, number>;
	circuit_breaker_config?: Record<string, number>;
	request_signing?: Record<string, string>;
	pre_request_script?: string;
	webhook_url?: string;
	cache_config?: Record<string, any>;
	parent_agent_id?: string | null;
}

interface HttpRequestNodeData {
	id: string;
	name: string;
	http_request_config?: HttpRequestConfig;
}

interface HttpRequestPropertiesPanelProps {
	node: {
		id: string;
		data: HttpRequestNodeData;
		position?: { x: number; y: number };
	};
	onUpdateNode: (nodeId: string, newData: any) => void;
	onDeleteNode?: (nodeId: string) => void;
	onClose: () => void;
}

type HttpRequestTabId = "request" | "auth" | "response" | "advanced" | "guardrails";

export default function HttpRequestPropertiesPanel({
	node,
	onUpdateNode,
	onDeleteNode,
	onClose,
}: HttpRequestPropertiesPanelProps) {
	const config = node.data.http_request_config || {};

	// Saved API endpoint reference
	const [endpointId, setEndpointId] = useState(config.endpoint_id || "");
	const [availableEndpoints, setAvailableEndpoints] = useState<
		Array<{ id: string; name: string; method: string; url_template: string }>
	>([]);
	const [endpointHeaders, setEndpointHeaders] = useState<Record<string, string>>({});
	const [endpointQueryParams, setEndpointQueryParams] = useState<Record<string, string>>({});

	// Request configuration
	const [urlTemplate, setUrlTemplate] = useState(config.url_template || "");
	const [method, setMethod] = useState(config.method || "GET");
	const [parameterSchema, setParameterSchema] = useState<
		Record<string, ParameterDefinition>
	>(config.parameter_schema || {});
	// Static request headers/query params and the owning agent link.
	// These currently have no dedicated editor UI, but MUST be preserved
	// on save - otherwise opening/saving this panel silently wipes them
	// (see: headers -> {} and parent_agent_id -> null corruption bug).
	const [headers, setHeaders] = useState<Record<string, string>>(
		config.headers || {},
	);
	const [queryParams, setQueryParams] = useState<Record<string, string>>(
		config.query_params || {},
	);
	const [parentAgentId, setParentAgentId] = useState<string | null>(
		config.parent_agent_id ?? null,
	);
	const [requestBodyTemplate, setRequestBodyTemplate] = useState(
		config.request_body_template || "",
	);
	const [contentType, setContentType] = useState(config.content_type || "");
	const [userAgent, setUserAgent] = useState(config.user_agent || "");

	// Authentication configuration
	const [authType, setAuthType] = useState(config.auth_type || "none");
	const [authConfig, setAuthConfig] = useState<Record<string, string>>(
		config.auth_config || {},
	);
	const [oauth2Config, setOauth2Config] = useState<Record<string, string>>(
		config.oauth2_config || {},
	);
	const [certificatePath, setCertificatePath] = useState(
		config.certificate_path || "",
	);

	// Response configuration
	const [responseFormat, setResponseFormat] = useState(
		config.response_format || "auto",
	);
	const [errorHandling, setErrorHandling] = useState(
		config.error_handling || "fail",
	);
	const [successStatusCodes, setSuccessStatusCodes] = useState<number[]>(
		config.success_status_codes || [200, 201, 202, 204],
	);
	const [acceptHeaders, setAcceptHeaders] = useState<Record<string, string>>(
		config.accept_headers || {},
	);
	const [extractPath, setExtractPath] = useState(config.extract_path || "");
	const [responseTransform, setResponseTransform] = useState(
		config.response_transform || "",
	);
	const [encoding, setEncoding] = useState(config.encoding || "utf-8");
	const [followRedirects, setFollowRedirects] = useState(
		config.follow_redirects ?? true,
	);
	const [maxRedirects, setMaxRedirects] = useState(config.max_redirects || 10);
	const [verifySSL, setVerifySSL] = useState(config.verify_ssl ?? true);
	const [compression, setCompression] = useState(config.compression ?? true);
	const [cookieJar, setCookieJar] = useState(config.cookie_jar ?? false);

	// Advanced configuration
	const [timeoutSeconds, setTimeoutSeconds] = useState(
		config.timeout_seconds || 30,
	);
	const [maxRetries, setMaxRetries] = useState(config.max_retries || 3);
	const [retryDelay, setRetryDelay] = useState(config.retry_delay || 1);
	const [retryOnStatus, setRetryOnStatus] = useState<number[]>(
		config.retry_on_status || [429, 500, 502, 503, 504],
	);
	const [proxyConfig, setProxyConfig] = useState<Record<string, string>>(
		config.proxy_config || {},
	);
	const [rateLimit, setRateLimit] = useState<Record<string, number>>(
		config.rate_limit || {},
	);
	const [circuitBreakerConfig, setCircuitBreakerConfig] = useState<
		Record<string, number>
	>(config.circuit_breaker_config || {});
	const [requestSigning, setRequestSigning] = useState<Record<string, string>>(
		config.request_signing || {},
	);
	const [preRequestScript, setPreRequestScript] = useState(
		config.pre_request_script || "",
	);
	const [webhookUrl, setWebhookUrl] = useState(config.webhook_url || "");
	const [cacheConfig, setCacheConfig] = useState<Record<string, any>>(
		config.cache_config || {},
	);

	// Tab navigation
	const [activeTab, setActiveTab] = useState<HttpRequestTabId>("request");

	// Track initial values for unsaved changes detection
	const initialValues = useRef({
		endpointId: config.endpoint_id || "",
		urlTemplate: config.url_template || "",
		method: config.method || "GET",
		parameterSchema: config.parameter_schema || {},
		headers: config.headers || {},
		queryParams: config.query_params || {},
		parentAgentId: config.parent_agent_id ?? null,
		requestBodyTemplate: config.request_body_template || "",
		contentType: config.content_type || "",
		userAgent: config.user_agent || "",
		authType: config.auth_type || "none",
		authConfig: config.auth_config || {},
		oauth2Config: config.oauth2_config || {},
		certificatePath: config.certificate_path || "",
		responseFormat: config.response_format || "auto",
		errorHandling: config.error_handling || "fail",
		successStatusCodes: config.success_status_codes || [200, 201, 202, 204],
		acceptHeaders: config.accept_headers || {},
		extractPath: config.extract_path || "",
		responseTransform: config.response_transform || "",
		encoding: config.encoding || "utf-8",
		followRedirects: config.follow_redirects ?? true,
		maxRedirects: config.max_redirects || 10,
		verifySSL: config.verify_ssl ?? true,
		compression: config.compression ?? true,
		cookieJar: config.cookie_jar ?? false,
		timeoutSeconds: config.timeout_seconds || 30,
		maxRetries: config.max_retries || 3,
		retryDelay: config.retry_delay || 1,
		retryOnStatus: config.retry_on_status || [429, 500, 502, 503, 504],
		proxyConfig: config.proxy_config || {},
		rateLimit: config.rate_limit || {},
		circuitBreakerConfig: config.circuit_breaker_config || {},
		requestSigning: config.request_signing || {},
		preRequestScript: config.pre_request_script || "",
		webhookUrl: config.webhook_url || "",
		cacheConfig: config.cache_config || {},
	});

	// Unsaved changes detection
	const hasUnsavedChanges = useMemo(() => {
		const init = initialValues.current;
		return (
			endpointId !== init.endpointId ||
			urlTemplate !== init.urlTemplate ||
			method !== init.method ||
			JSON.stringify(parameterSchema) !==
				JSON.stringify(init.parameterSchema) ||
			JSON.stringify(headers) !== JSON.stringify(init.headers) ||
			JSON.stringify(queryParams) !== JSON.stringify(init.queryParams) ||
			parentAgentId !== init.parentAgentId ||
			requestBodyTemplate !== init.requestBodyTemplate ||
			contentType !== init.contentType ||
			userAgent !== init.userAgent ||
			authType !== init.authType ||
			JSON.stringify(authConfig) !== JSON.stringify(init.authConfig) ||
			JSON.stringify(oauth2Config) !== JSON.stringify(init.oauth2Config) ||
			certificatePath !== init.certificatePath ||
			responseFormat !== init.responseFormat ||
			errorHandling !== init.errorHandling ||
			JSON.stringify(successStatusCodes) !==
				JSON.stringify(init.successStatusCodes) ||
			JSON.stringify(acceptHeaders) !==
				JSON.stringify(init.acceptHeaders) ||
			extractPath !== init.extractPath ||
			responseTransform !== init.responseTransform ||
			encoding !== init.encoding ||
			followRedirects !== init.followRedirects ||
			maxRedirects !== init.maxRedirects ||
			verifySSL !== init.verifySSL ||
			compression !== init.compression ||
			cookieJar !== init.cookieJar ||
			timeoutSeconds !== init.timeoutSeconds ||
			maxRetries !== init.maxRetries ||
			retryDelay !== init.retryDelay ||
			JSON.stringify(retryOnStatus) !==
				JSON.stringify(init.retryOnStatus) ||
			JSON.stringify(proxyConfig) !== JSON.stringify(init.proxyConfig) ||
			JSON.stringify(rateLimit) !== JSON.stringify(init.rateLimit) ||
			JSON.stringify(circuitBreakerConfig) !==
				JSON.stringify(init.circuitBreakerConfig) ||
			JSON.stringify(requestSigning) !==
				JSON.stringify(init.requestSigning) ||
			preRequestScript !== init.preRequestScript ||
			webhookUrl !== init.webhookUrl ||
			JSON.stringify(cacheConfig) !== JSON.stringify(init.cacheConfig)
		);
	}, [
		endpointId,
		urlTemplate,
		method,
		parameterSchema,
		headers,
		queryParams,
		parentAgentId,
		requestBodyTemplate,
		contentType,
		userAgent,
		authType,
		authConfig,
		oauth2Config,
		certificatePath,
		responseFormat,
		errorHandling,
		successStatusCodes,
		acceptHeaders,
		extractPath,
		responseTransform,
		encoding,
		followRedirects,
		maxRedirects,
		verifySSL,
		compression,
		cookieJar,
		timeoutSeconds,
		maxRetries,
		retryDelay,
		retryOnStatus,
		proxyConfig,
		rateLimit,
		circuitBreakerConfig,
		requestSigning,
		preRequestScript,
		webhookUrl,
		cacheConfig,
	]);

	const handleSave = useCallback(() => {
		const updatedConfig: HttpRequestConfig = {
			endpoint_id: endpointId || undefined,
			url_template: urlTemplate,
			method,
			parameter_schema: parameterSchema,
			headers,
			query_params: queryParams,
			request_body_template: requestBodyTemplate,
			content_type: contentType,
			user_agent: userAgent,
			auth_type: authType,
			auth_config: authConfig,
			oauth2_config: oauth2Config,
			certificate_path: certificatePath,
			timeout_seconds: timeoutSeconds,
			max_retries: maxRetries,
			retry_delay: retryDelay,
			retry_on_status: retryOnStatus,
			response_format: responseFormat,
			error_handling: errorHandling,
			follow_redirects: followRedirects,
			max_redirects: maxRedirects,
			verify_ssl: verifySSL,
			compression,
			cookie_jar: cookieJar,
			success_status_codes: successStatusCodes,
			accept_headers: acceptHeaders,
			extract_path: extractPath,
			response_transform: responseTransform,
			encoding,
			proxy_config: proxyConfig,
			rate_limit: rateLimit,
			circuit_breaker_config: circuitBreakerConfig,
			request_signing: requestSigning,
			pre_request_script: preRequestScript,
			webhook_url: webhookUrl,
			cache_config: cacheConfig,
			parent_agent_id: parentAgentId,
		};

		const updateData: any = {
			http_request_config: updatedConfig,
		};

		if (node.position) {
			updateData.position = node.position;
		}

		onUpdateNode(node.id, updateData);
		onClose();
	}, [
		endpointId,
		urlTemplate,
		method,
		parameterSchema,
		headers,
		queryParams,
		parentAgentId,
		requestBodyTemplate,
		contentType,
		userAgent,
		authType,
		authConfig,
		oauth2Config,
		certificatePath,
		timeoutSeconds,
		maxRetries,
		retryDelay,
		retryOnStatus,
		responseFormat,
		errorHandling,
		followRedirects,
		maxRedirects,
		verifySSL,
		compression,
		cookieJar,
		successStatusCodes,
		acceptHeaders,
		extractPath,
		responseTransform,
		encoding,
		proxyConfig,
		rateLimit,
		circuitBreakerConfig,
		requestSigning,
		preRequestScript,
		webhookUrl,
		cacheConfig,
		node,
		onUpdateNode,
		onClose,
	]);

	// Load saved API endpoints for the selector
	useEffect(() => {
		api
			.getApiEndpoints(true)
			.then((eps: any[]) => setAvailableEndpoints(eps || []))
			.catch(() => {});
	}, []);

	const handleEndpointSelect = useCallback(
		(selectedId: string) => {
			setEndpointId(selectedId);
			if (selectedId) {
				const ep = availableEndpoints.find((e) => e.id === selectedId) as any;
				if (ep) {
					setUrlTemplate(ep.url_template || "");
					setMethod(ep.method || "GET");
					setContentType(ep.content_type || "");
					setAuthType(ep.auth_type || "none");
					setTimeoutSeconds(ep.timeout_seconds ?? 30);
					setMaxRetries(ep.max_retries ?? 3);
					setRetryDelay(ep.retry_delay ?? 1);
					setResponseFormat(ep.response_format || "auto");
					setExtractPath(ep.extract_path || "");
					setVerifySSL(ep.verify_ssl ?? true);
					setFollowRedirects(ep.follow_redirects ?? true);
					setMaxRedirects(ep.max_redirects ?? 10);
					if (ep.request_body_template)
						setRequestBodyTemplate(ep.request_body_template);
					if (ep.success_status_codes)
						setSuccessStatusCodes(ep.success_status_codes);
					if (ep.retry_on_status) setRetryOnStatus(ep.retry_on_status);
					setEndpointHeaders(ep.headers || {});
					setEndpointQueryParams(ep.query_params || {});
				}
			} else {
				setEndpointHeaders({});
				setEndpointQueryParams({});
			}
		},
		[availableEndpoints],
	);

	// Keyboard shortcut: Cmd/Ctrl+S to save
	const handleSaveRef = useRef(handleSave);
	handleSaveRef.current = handleSave;

	useEffect(() => {
		const handleKeyDown = (e: KeyboardEvent) => {
			if ((e.metaKey || e.ctrlKey) && e.key === "s") {
				e.preventDefault();
				handleSaveRef.current();
			}
		};
		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, []);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleStopPropagation = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleDeleteAndClose = useCallback(() => {
		onDeleteNode?.(node.id);
		onClose();
	}, [onDeleteNode, node.id, onClose]);

	// Responsive sidebar collapse
	const contentRef = useRef<HTMLDivElement>(null);
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

	useEffect(() => {
		const el = contentRef.current;
		if (!el || typeof ResizeObserver === "undefined") return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				setSidebarCollapsed(entry.contentRect.width < 400);
			}
		});
		observer.observe(el);
		return () => observer.disconnect();
	}, []);

	// Sidebar tab configuration
	const panelTabs = useMemo(
		() => [
			{
				id: "request" as const,
				label: "Request",
				description: "Method, URL & parameters",
				icon: <Globe className="h-4 w-4" />,
			},
			{
				id: "auth" as const,
				label: "Authentication",
				description: "Credentials & tokens",
				icon: <Key className="h-4 w-4" />,
			},
			{
				id: "response" as const,
				label: "Response",
				description: "Parsing & transformation",
				icon: <Activity className="h-4 w-4" />,
			},
			{
				id: "advanced" as const,
				label: "Advanced",
				description: "Retry, proxy & signing",
				icon: <Settings className="h-4 w-4" />,
			},
			{
				id: "guardrails" as const,
				label: "Guardrails",
				description: "Safety policies",
				icon: <ShieldCheck className="h-4 w-4" />,
			},
		],
		[],
	);

	const isGuardrailsTab = activeTab === "guardrails";

	return (
		<div
			className="fixed inset-0 z-[110] flex animate-fadeIn items-start justify-center bg-black/50 px-4 pb-4 pt-[5vh] backdrop-blur-sm"
			onClick={handleBackdropClick}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleStopPropagation}
			>
				<div
					className={cn(
						"flex min-h-[320px] flex-col rounded-[4px] border border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]",
						isGuardrailsTab
							? "max-h-[90vh] overflow-visible"
							: "max-h-[80vh] overflow-hidden",
					)}
				>
					<div className="flex-none border-b border-gray-200 bg-white">
						<div className="flex flex-wrap items-start justify-between gap-4 px-6 pb-4 pt-5">
							<div className="flex min-w-0 items-start gap-3">
								<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[4px] border border-gray-200 bg-white shadow-sm">
									<FileText className="h-5 w-5 text-orange-600" aria-hidden />
								</div>
								<div className="min-w-0">
									<p className="text-xs font-semibold capitalize tracking-wide text-gray-900">
										Tool configuration
									</p>
									<h2 className="text-lg font-semibold tracking-tight text-gray-900">
										HTTP Request Configuration
									</h2>
								</div>
							</div>
							<button
								type="button"
								onClick={onClose}
								className="shrink-0 rounded-[4px] border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
								aria-label="Close"
							>
								<X className="h-5 w-5" />
							</button>
						</div>
					</div>

					<div
						ref={contentRef}
						className={cn(
							"flex min-h-0 flex-1",
							!isGuardrailsTab && "overflow-hidden",
						)}
					>
						<ConfigSidebar
							items={panelTabs}
							activeItem={activeTab}
							onChange={(id) =>
								setActiveTab(id as HttpRequestTabId)
							}
							collapsed={sidebarCollapsed}
							variant="light"
						/>

						<div
							className={cn(
								"flex-1 min-h-0 bg-slate-50 px-6 py-4",
								isGuardrailsTab ? "overflow-visible" : "overflow-y-auto",
							)}
						>
								{activeTab === "request" && (
									<>
										{/* Saved API Endpoint Selector */}
										<div className="mb-6 border-b border-gray-200 pb-5">
											<div className="mb-2 flex items-center gap-2">
												<Link className="h-3.5 w-3.5 text-gray-700" />
												<label className="text-xs font-semibold capitalize text-gray-900">
													Saved API Endpoint
												</label>
											</div>
											<EndpointPicker
												endpoints={availableEndpoints}
												value={endpointId}
												onChange={handleEndpointSelect}
												variant="light"
											/>
											{endpointId && (
												<div className="mt-2 space-y-1">
													<p className="text-xs text-gray-600">
														Fields pre-filled from saved endpoint. Override any field below.
													</p>
													{(Object.keys(endpointHeaders).length > 0 || Object.keys(endpointQueryParams).length > 0) && (
														<p className="text-xs text-gray-600">
															Endpoint also provides
															{Object.keys(endpointHeaders).length > 0 && (
																<span className="font-medium text-gray-800"> {Object.keys(endpointHeaders).length} header{Object.keys(endpointHeaders).length !== 1 ? "s" : ""}</span>
															)}
															{Object.keys(endpointHeaders).length > 0 && Object.keys(endpointQueryParams).length > 0 && " and"}
															{Object.keys(endpointQueryParams).length > 0 && (
																<span className="font-medium text-gray-800"> {Object.keys(endpointQueryParams).length} query param{Object.keys(endpointQueryParams).length !== 1 ? "s" : ""}</span>
															)}
															{" "}applied at execution time.
														</p>
													)}
												</div>
											)}
										</div>
									<HttpRequestSection
										urlTemplate={urlTemplate}
										onUrlTemplateChange={setUrlTemplate}
										method={method}
										onMethodChange={setMethod}
										parameterSchema={parameterSchema}
										onParameterSchemaChange={setParameterSchema}
										contentType={contentType}
										onContentTypeChange={setContentType}
										userAgent={userAgent}
										onUserAgentChange={setUserAgent}
										requestBodyTemplate={requestBodyTemplate}
										onRequestBodyTemplateChange={setRequestBodyTemplate}
									/>
									</>
								)}

								{activeTab === "auth" && (
									<HttpAuthSection
										authType={authType}
										onAuthTypeChange={setAuthType}
										authConfig={authConfig}
										onAuthConfigChange={setAuthConfig}
										oauth2Config={oauth2Config}
										onOauth2ConfigChange={setOauth2Config}
										certificatePath={certificatePath}
										onCertificatePathChange={setCertificatePath}
									/>
								)}

								{activeTab === "response" && (
									<HttpResponseSection
										responseFormat={responseFormat}
										onResponseFormatChange={setResponseFormat}
										errorHandling={errorHandling}
										onErrorHandlingChange={setErrorHandling}
										successStatusCodes={successStatusCodes}
										onSuccessStatusCodesChange={setSuccessStatusCodes}
										acceptHeaders={acceptHeaders}
										onAcceptHeadersChange={setAcceptHeaders}
										extractPath={extractPath}
										onExtractPathChange={setExtractPath}
										responseTransform={responseTransform}
										onResponseTransformChange={setResponseTransform}
										encoding={encoding}
										onEncodingChange={setEncoding}
										followRedirects={followRedirects}
										onFollowRedirectsChange={setFollowRedirects}
										maxRedirects={maxRedirects}
										onMaxRedirectsChange={setMaxRedirects}
										verifySSL={verifySSL}
										onVerifySSLChange={setVerifySSL}
										compression={compression}
										onCompressionChange={setCompression}
										cookieJar={cookieJar}
										onCookieJarChange={setCookieJar}
									/>
								)}

								{activeTab === "advanced" && (
									<HttpAdvancedSection
										timeoutSeconds={timeoutSeconds}
										onTimeoutSecondsChange={setTimeoutSeconds}
										maxRetries={maxRetries}
										onMaxRetriesChange={setMaxRetries}
										retryDelay={retryDelay}
										onRetryDelayChange={setRetryDelay}
										retryOnStatus={retryOnStatus}
										onRetryOnStatusChange={setRetryOnStatus}
										proxyConfig={proxyConfig}
										onProxyConfigChange={setProxyConfig}
										rateLimit={rateLimit}
										onRateLimitChange={setRateLimit}
										circuitBreakerConfig={circuitBreakerConfig}
										onCircuitBreakerConfigChange={setCircuitBreakerConfig}
										requestSigning={requestSigning}
										onRequestSigningChange={setRequestSigning}
										preRequestScript={preRequestScript}
										onPreRequestScriptChange={setPreRequestScript}
										webhookUrl={webhookUrl}
										onWebhookUrlChange={setWebhookUrl}
										cacheConfig={cacheConfig}
										onCacheConfigChange={setCacheConfig}
									/>
								)}

								{activeTab === "guardrails" && (
									<ToolGuardrailsSection toolNodeId={node.id} />
								)}
							</div>
						</div>

						{/* Footer */}
						<div className="border-t border-gray-200 bg-white px-6 py-3">
							<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
								{/* Left: Delete button */}
								<button
									type="button"
									onClick={handleDeleteAndClose}
									className="flex items-center gap-1.5 rounded-[4px] border border-gray-200 bg-white px-3 py-2 text-xs text-red-700 transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-800"
								>
									<Trash2 className="w-3.5 h-3.5" />
									Delete Node
								</button>

								{/* Right: Unsaved + hint + Cancel + Save */}
								<div className="flex items-center gap-3 sm:ml-auto">
									{hasUnsavedChanges && (
										<span className="flex items-center gap-1.5 text-[11px] text-gray-600">
											<span className="h-1.5 w-1.5 animate-smoothPulse rounded-[4px] bg-orange-500" />
											Unsaved
										</span>
									)}
									<span className="hidden text-[11px] text-gray-400 sm:inline">
										{"\u2318"}S to save
									</span>
									<button
										type="button"
										onClick={onClose}
										className="rounded-[4px] border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
									>
										Cancel
									</button>
									<button
										type="button"
										onClick={handleSave}
										className="rounded-[4px] bg-orange-600 px-5 py-2 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-orange-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
									>
										<span className="inline-flex items-center gap-1.5">
											<Save className="w-3.5 h-3.5" />
											Save Changes
										</span>
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
	);
}
