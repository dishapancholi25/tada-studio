"use client";

import {
	ChevronDown,
	ChevronRight,
	ClipboardPaste,
	FileJson,
	Globe,
	Hash,
	Link,
	Lock,
	Plus,
	Save,
	Search,
	ShieldCheck,
	Terminal,
	Trash2,
	X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Node } from "reactflow";
import { useGraph } from "@/contexts/GraphContext";
import { useToast } from "@/contexts/ToastContext";
import { api } from "@/lib/api";
import EndpointPicker from "@/components/ui/EndpointPicker";
import HttpParameterMappingRow, {
	type HttpParameterMapping,
} from "./HttpParameterMappingRow";
import ConfigSidebar from "./ConfigSidebar";
import ToolGuardrailsSection from "@/components/core/guardrails/ToolGuardrailsSection";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { parseCurlCommand } from "@/utils/curlParser";

interface EnhancedHttpRequestActionConfig {
	// Saved endpoint reference
	endpoint_id?: string;

	// Basic config
	url_template?: string;
	method?: string;

	// Parameter mappings
	url_param_mappings?: HttpParameterMapping[];
	query_param_mappings?: HttpParameterMapping[];
	header_mappings?: HttpParameterMapping[];
	body_mappings?: HttpParameterMapping[];

	// Body configuration
	body_type?: "json" | "form" | "text" | "raw";
	body_template?: string; // For text/raw bodies

	// Auth
	auth_type?: string;
	auth_config?: Record<string, string>;

	// Advanced
	timeout_seconds?: number;
	max_retries?: number;
	verify_ssl?: boolean;
	response_path?: string;
	success_status_codes?: number[];

	// Legacy support
	headers?: Record<string, string>;
	body?: string;
}

interface HttpRequestActionPropertiesPanelProps {
	nodeId: string;
	onClose: () => void;
	availableNodes?: Node[];
}

type HttpRequestTabId = "request" | "guardrails";

export default function HttpRequestActionPropertiesPanel({
	nodeId,
	onClose,
	availableNodes = [],
}: HttpRequestActionPropertiesPanelProps) {
	const { nodes, updateNode, deleteNode } = useGraph();
	const { showError: showToastError, showSuccess: showToastSuccess } = useToast();
	const node = nodes.find((n) => n.id === nodeId);

	const [nodeName, setNodeName] = useState(
		node?.data?.name || "HTTP Request Action",
	);
	const [config, setConfig] = useState<EnhancedHttpRequestActionConfig>({
		url_template: "",
		method: "GET",
		url_param_mappings: [],
		query_param_mappings: [],
		header_mappings: [],
		body_mappings: [],
		body_type: "json",
		body_template: "",
		auth_type: "none",
		auth_config: {},
		timeout_seconds: 30,
		max_retries: 3,
		verify_ssl: true,
		response_path: "",
		success_status_codes: [200, 201, 202, 204],
	});

	const [expandedSections, setExpandedSections] = useState({
		basic: true,
		urlParams: false,
		queryParams: false,
		headers: false,
		body: false,
		auth: false,
		advanced: false,
	});

	const [saving, setSaving] = useState(false);
	const [activeTab, setActiveTab] = useState<HttpRequestTabId>("request");
	const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
	const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

	// cURL import dialog state
	const [showCurlImport, setShowCurlImport] = useState(false);
	const [curlText, setCurlText] = useState("");
	const [curlError, setCurlError] = useState<string | null>(null);

	const handleCurlImport = useCallback(() => {
		try {
			const parsed = parseCurlCommand(curlText);

			const toStaticMapping = (
				name: string,
				value: unknown,
				parameterType: HttpParameterMapping["parameter_type"],
			): HttpParameterMapping => ({
				parameter_name: name,
				parameter_type: parameterType,
				source_mode: "static",
				static_value:
					typeof value === "object" && value !== null
						? JSON.stringify(value)
						: String(value ?? ""),
				is_required: false,
				data_type:
					typeof value === "number"
						? "number"
						: typeof value === "boolean"
							? "boolean"
							: "string",
			});

			const queryMappings = parsed.queryParams.map((p) =>
				toStaticMapping(p.name, p.value, "query_param"),
			);
			const headerMappings = parsed.headers.map((h) =>
				toStaticMapping(h.name, h.value, "header"),
			);

			// Body: form bodies and flat JSON objects become editable field
			// mappings. JSON containing nested objects/arrays must keep its exact
			// shape — field mappings hold strings only, which would send nested
			// values as JSON-encoded strings — so those go to the body template
			// verbatim.
			let bodyType: EnhancedHttpRequestActionConfig["body_type"] = "json";
			let bodyMappings: HttpParameterMapping[] = [];
			let bodyTemplate = "";
			const jsonBodyIsFlat = parsed.bodyFields.every(
				(f) => f.value === null || typeof f.value !== "object",
			);
			if (parsed.bodyType === "form") {
				bodyType = "form";
				bodyMappings = parsed.bodyFields.map((f) =>
					toStaticMapping(f.name, f.value, "body_field"),
				);
			} else if (
				parsed.bodyType === "json" &&
				parsed.bodyFields.length > 0 &&
				jsonBodyIsFlat
			) {
				bodyType = "json";
				bodyMappings = parsed.bodyFields.map((f) =>
					toStaticMapping(f.name, f.value, "body_field"),
				);
			} else if (parsed.bodyType !== null) {
				// Nested JSON, arrays, or non-JSON payloads: send as-is.
				bodyType = "raw";
				bodyTemplate = parsed.body;
			}

			let authType = "none";
			let authConfig: Record<string, string> = {};
			if (parsed.auth?.type === "bearer") {
				authType = "bearer";
				authConfig = { token: parsed.auth.token };
			} else if (parsed.auth?.type === "basic") {
				authType = "basic";
				authConfig = {
					username: parsed.auth.username,
					password: parsed.auth.password,
				};
			}

			setConfig((prev) => ({
				...prev,
				endpoint_id: undefined,
				url_template: parsed.url,
				method: parsed.method,
				query_param_mappings: queryMappings,
				header_mappings: headerMappings,
				body_type: bodyType,
				body_template: bodyTemplate,
				body_mappings: bodyMappings,
				auth_type: authType,
				auth_config: authConfig,
				verify_ssl: parsed.verifySsl,
				...(parsed.timeoutSeconds !== undefined
					? { timeout_seconds: parsed.timeoutSeconds }
					: {}),
				...(parsed.maxRetries !== undefined
					? { max_retries: parsed.maxRetries }
					: {}),
			}));

			// Reveal every section the import populated
			setExpandedSections((prev) => ({
				...prev,
				basic: true,
				queryParams: prev.queryParams || queryMappings.length > 0,
				headers: prev.headers || headerMappings.length > 0,
				body: prev.body || bodyMappings.length > 0 || bodyTemplate !== "",
				auth: prev.auth || authType !== "none",
			}));

			setShowCurlImport(false);
			setCurlText("");
			setCurlError(null);

			const summary = [
				`${parsed.method} ${parsed.url}`,
				queryMappings.length > 0 ? `${queryMappings.length} query param(s)` : null,
				headerMappings.length > 0 ? `${headerMappings.length} header(s)` : null,
				parsed.bodyType !== null ? `${bodyType} body` : null,
				authType !== "none" ? `${authType} auth` : null,
			]
				.filter(Boolean)
				.join(" · ");
			showToastSuccess("cURL imported", summary);
			if (parsed.warnings.length > 0) {
				showToastError("Some parts were skipped", parsed.warnings.join("; "));
			}
		} catch (error) {
			setCurlError(
				error instanceof Error ? error.message : "Could not parse this command",
			);
		}
	}, [curlText, showToastSuccess, showToastError]);

	// Track initial config for unsaved changes detection
	const initialConfig = useRef(
		JSON.stringify(node?.data?.http_request_action_config || {}),
	);
	const initialName = useRef(node?.data?.name || "HTTP Request Action");

	const hasUnsavedChanges = useMemo(
		() =>
			JSON.stringify(config) !== initialConfig.current ||
			nodeName !== initialName.current,
		[config, nodeName],
	);

	// Saved API endpoint state
	const [availableEndpoints, setAvailableEndpoints] = useState<
		Array<{ id: string; name: string; method: string; url_template: string; description?: string; auth_type?: string }>
	>([]);

	// Load saved API endpoints for the selector
	useEffect(() => {
		api
			.getApiEndpoints(true)
			.then((eps: any[]) => setAvailableEndpoints(eps || []))
			.catch(() => {});
	}, []);

	const handleEndpointSelect = useCallback(
		(selectedId: string) => {
			if (selectedId) {
				const ep = availableEndpoints.find((e) => e.id === selectedId) as any;
				if (ep) {
					setConfig((prev) => ({
						...prev,
						endpoint_id: selectedId,
						url_template: ep.url_template || prev.url_template,
						method: ep.method || prev.method,
						auth_type: ep.auth_type || prev.auth_type,
						timeout_seconds: ep.timeout_seconds ?? prev.timeout_seconds,
						max_retries: ep.max_retries ?? prev.max_retries,
						verify_ssl: ep.verify_ssl ?? prev.verify_ssl,
						response_path: ep.extract_path || prev.response_path,
						success_status_codes: ep.success_status_codes || prev.success_status_codes,
					}));
				}
			} else {
				setConfig((prev) => ({
					...prev,
					endpoint_id: undefined,
				}));
			}
		},
		[availableEndpoints],
	);

	const handleBackdropClick = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleModalClick = useCallback((e: React.MouseEvent) => {
		e.stopPropagation();
	}, []);

	const handleClose = useCallback(() => {
		onClose();
	}, [onClose]);

	const handleNodeNameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setNodeName(e.target.value);
		},
		[],
	);

	const handleUrlTemplateChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, url_template: e.target.value });
		},
		[config],
	);

	const handleMethodChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			setConfig({ ...config, method: e.target.value });
		},
		[config],
	);

	const handleBodyTypeChange = useCallback(
		(type: "json" | "form" | "text" | "raw") => {
			setConfig({ ...config, body_type: type });
		},
		[config],
	);

	const handleBodyTemplateChange = useCallback(
		(e: React.ChangeEvent<HTMLTextAreaElement>) => {
			setConfig({ ...config, body_template: e.target.value });
		},
		[config],
	);

	const handleAuthTypeChange = useCallback(
		(e: React.ChangeEvent<HTMLSelectElement>) => {
			setConfig({ ...config, auth_type: e.target.value });
		},
		[config],
	);

	const handleAuthTokenChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({
				...config,
				auth_config: { ...config.auth_config, token: e.target.value },
			});
		},
		[config],
	);

	const handleAuthUsernameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({
				...config,
				auth_config: { ...config.auth_config, username: e.target.value },
			});
		},
		[config],
	);

	const handleAuthPasswordChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({
				...config,
				auth_config: { ...config.auth_config, password: e.target.value },
			});
		},
		[config],
	);

	const handleAuthHeaderNameChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({
				...config,
				auth_config: { ...config.auth_config, header_name: e.target.value },
			});
		},
		[config],
	);

	const handleAuthApiKeyChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({
				...config,
				auth_config: { ...config.auth_config, api_key: e.target.value },
			});
		},
		[config],
	);

	const handleTimeoutChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, timeout_seconds: parseInt(e.target.value) });
		},
		[config],
	);

	const handleMaxRetriesChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, max_retries: parseInt(e.target.value) });
		},
		[config],
	);

	const handleVerifySslChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, verify_ssl: e.target.checked });
		},
		[config],
	);

	const handleResponsePathChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({ ...config, response_path: e.target.value });
		},
		[config],
	);

	const handleSuccessStatusCodesChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement>) => {
			setConfig({
				...config,
				success_status_codes: e.target.value
					.split(",")
					.map((s) => parseInt(s.trim()))
					.filter((n) => !isNaN(n)),
			});
		},
		[config],
	);


	// Factory functions for parameter mapping handlers
	const createParameterUpdateHandler = useCallback(
		(
			type: "url_param" | "query_param" | "header" | "body_field",
			index: number,
		) =>
			(updated: any) => {
				updateParameterMapping(type, index, updated);
			},
		[],
	);

	const createParameterDeleteHandler = useCallback(
		(
			type: "url_param" | "query_param" | "header" | "body_field",
			index: number,
		) =>
			() => {
				deleteParameterMapping(type, index);
			},
		[],
	);

	const createBodyTypeChangeHandler = useCallback(
		(type: "json" | "form" | "text" | "raw") => () => {
			handleBodyTypeChange(type);
		},
		[handleBodyTypeChange],
	);

	const toggleSection = useCallback((section: keyof typeof expandedSections) => {
		setExpandedSections((prev) => ({
			...prev,
			[section]: !prev[section],
		}));
	}, []);

	const createToggleSectionHandler = useCallback(
		(section: keyof typeof expandedSections) => () => {
			toggleSection(section);
		},
		[toggleSection],
	);

	// Extract URL parameters from template
	const extractedUrlParams = useMemo(() => {
		if (!config.url_template) return [];
		const matches = config.url_template.match(/\{([^}]+)\}/g);
		if (!matches) return [];
		return matches.map((match) => match.slice(1, -1));
	}, [config.url_template]);

	// Initialize component with existing config
	useEffect(() => {
		if (node?.data?.http_request_action_config) {
			const existingConfig = node.data.http_request_action_config;

			// Convert legacy headers to header mappings if needed
			let headerMappings: HttpParameterMapping[] =
				existingConfig.header_mappings || [];
			if (!headerMappings.length && existingConfig.headers) {
				headerMappings = Object.entries(existingConfig.headers).map(
					([key, value]) => ({
						parameter_name: key,
						parameter_type: "header" as const,
						source_mode: "static" as const,
						static_value: value,
					}),
				);
			}

			setConfig({
				...existingConfig,
				header_mappings: headerMappings,
				body_type: existingConfig.body_type || "json",
			});
		}
	}, [node]);

	// Auto-sync URL parameters with extracted params
	useEffect(() => {
		const currentParamNames =
			config.url_param_mappings?.map((m) => m.parameter_name) || [];
		const newParams = extractedUrlParams.filter(
			(p) => !currentParamNames.includes(p),
		);
		const removedParams = currentParamNames.filter(
			(p) => !extractedUrlParams.includes(p),
		);

		if (newParams.length > 0 || removedParams.length > 0) {
			const updatedMappings = [
				...(config.url_param_mappings || []).filter(
					(m) => !removedParams.includes(m.parameter_name),
				),
				...newParams.map((param) => ({
					parameter_name: param,
					parameter_type: "url_param" as const,
					source_mode: "static" as const,
					is_required: true,
				})),
			];

			setConfig((prev) => ({
				...prev,
				url_param_mappings: updatedMappings,
			}));

			// Auto-expand URL params section if we have params
			if (updatedMappings.length > 0 && !expandedSections.urlParams) {
				setExpandedSections((prev) => ({ ...prev, urlParams: true }));
			}
		}
	}, [extractedUrlParams, expandedSections.urlParams]);

	const handleSave = useCallback(async () => {
		setSaving(true);
		try {
			// Convert header mappings back to headers object for backward compatibility
			const headers: Record<string, string> = {};
			config.header_mappings?.forEach((mapping) => {
				if (mapping.source_mode === "static" && mapping.static_value) {
					headers[mapping.parameter_name] = mapping.static_value;
				}
			});

			await updateNode(nodeId, {
				name: nodeName,
				http_request_action_config: {
					...config,
					headers, // Include for backward compatibility
				},
			});
			onClose();
		} catch (error) {
			console.error("Failed to save HTTP request config:", error);
			showToastError("Save Failed", "Failed to save HTTP request configuration");
		} finally {
			setSaving(false);
		}
	}, [config, nodeName, nodeId, updateNode, onClose, showToastError]);

	const addQueryParameter = () => {
		const newMapping: HttpParameterMapping = {
			parameter_name: `param_${(config.query_param_mappings?.length || 0) + 1}`,
			parameter_type: "query_param",
			source_mode: "static",
			static_value: "",
		};

		setConfig((prev) => ({
			...prev,
			query_param_mappings: [...(prev.query_param_mappings || []), newMapping],
		}));
	};

	const addHeader = () => {
		const hasContentType = config.header_mappings?.some(
			(m) => m.parameter_name.toLowerCase() === "content-type",
		);
		const newMapping: HttpParameterMapping = hasContentType
			? {
					parameter_name: `header_${(config.header_mappings?.length || 0) + 1}`,
					parameter_type: "header",
					source_mode: "static",
					static_value: "",
				}
			: {
					parameter_name: "Content-Type",
					parameter_type: "header",
					source_mode: "static",
					static_value: "application/json",
				};

		setConfig((prev) => ({
			...prev,
			header_mappings: [...(prev.header_mappings || []), newMapping],
		}));
	};

	const addBodyField = () => {
		const newMapping: HttpParameterMapping = {
			parameter_name: `field_${(config.body_mappings?.length || 0) + 1}`,
			parameter_type: "body_field",
			source_mode: "static",
			static_value: "",
		};

		setConfig((prev) => ({
			...prev,
			body_mappings: [...(prev.body_mappings || []), newMapping],
		}));
	};

	// body_field mappings live under "body_mappings", not "body_field_mappings"
	const getMappingKey = (
		type: "url_param" | "query_param" | "header" | "body_field",
	): keyof EnhancedHttpRequestActionConfig =>
		type === "body_field"
			? "body_mappings"
			: (`${type}_mappings` as keyof EnhancedHttpRequestActionConfig);

	const updateParameterMapping = (
		type: "url_param" | "query_param" | "header" | "body_field",
		index: number,
		mapping: HttpParameterMapping,
	) => {
		setConfig((prev) => {
			const key = getMappingKey(type);
			const mappings = [...((prev[key] as HttpParameterMapping[]) || [])];
			mappings[index] = mapping;
			return { ...prev, [key]: mappings };
		});
	};

	const deleteParameterMapping = (
		type: "url_param" | "query_param" | "header" | "body_field",
		index: number,
	) => {
		setConfig((prev) => {
			const key = getMappingKey(type);
			const mappings = [...((prev[key] as HttpParameterMapping[]) || [])];
			mappings.splice(index, 1);
			return { ...prev, [key]: mappings };
		});
	};

	// Get upstream nodes that can provide data
	const upstreamNodes = useMemo(() => {
		return availableNodes.filter(
			(n) =>
				n.id !== nodeId &&
				(n.type === "agentNode" ||
					n.data?.type === "AGENT" ||
					n.data?.type === "START"),
		);
	}, [availableNodes, nodeId]);

	const handleDeleteAndClose = useCallback(() => {
		setShowDeleteConfirm(true);
	}, []);

	const handleConfirmDelete = useCallback(() => {
		deleteNode(nodeId);
		onClose();
	}, [nodeId, deleteNode, onClose]);

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

	// Responsive sidebar collapse
	const contentRef = useRef<HTMLDivElement>(null);

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

	const panelTabs = useMemo(
		() => [
			{
				id: "request" as const,
				label: "Request",
				description: "HTTP settings",
				icon: <Globe className="h-4 w-4" />,
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

	if (!node) return null;

	return (
		<div
			className="fixed inset-0 z-[110] flex items-start justify-center bg-black/50 backdrop-blur-sm px-4 pt-[5vh] pb-4 animate-fadeIn"
			onClick={handleBackdropClick}
		>
			<div
				className="w-[85vw] max-w-[1800px]"
				onClick={handleModalClick}
			>
				{/* Glass halo gradient border frame */}
				<div className="rounded-[4px] p-[1px] bg-gradient-to-br from-[#0DA931]/30 via-transparent to-[#0DA931]/12 shadow-xl">
					<div className="flex flex-col overflow-hidden min-h-[320px] max-h-[80vh] rounded-[4px] border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
						{/* Header */}
						<div className="relative flex-none border-b border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)]">
							<div className="flex items-center justify-between px-6 py-3">
								<div className="flex items-center gap-4">
									<div className="h-12 w-12 rounded-2xl border flex items-center justify-center bg-[#0DA931]/12 border-[#0DA931]/35">
										<Globe className="w-6 h-6 text-[#0DA931]" />
									</div>
									<div>
										<h2 className="text-2xl font-semibold text-[color:var(--color-text-primary)]">
											HTTP Request Action
										</h2>
										<p className="text-sm text-[color:var(--color-text-secondary)] mt-0.5">
											Configure HTTP request with dynamic parameter mapping
										</p>
									</div>
								</div>
								<button
									type="button"
									onClick={handleClose}
									className="rounded-[4px] border border-[color:var(--color-border)] bg-[color:var(--color-surface)] p-1.5 text-[color:var(--color-text-muted)] transition-all duration-150 hover:bg-[color:var(--color-surface-hover)] hover:text-[color:var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0DA931]/45"
								>
									<X className="h-5 w-5" />
								</button>
							</div>
						</div>

						{/* Content: Sidebar + Section */}
						<div
							ref={contentRef}
							className="flex-1 flex min-h-0 overflow-hidden"
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

							<div className="flex-1 overflow-y-auto px-6 py-5 bg-[color:var(--color-bg-primary)] custom-scrollbar space-y-6">
								{/* Request Tab */}
								{activeTab === "request" && (
									<div className="space-y-4">
										{/* Import from cURL */}
										<div className="flex justify-end">
											<button
												type="button"
												onClick={() => {
													setCurlError(null);
													setShowCurlImport(true);
												}}
												className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-xs font-medium text-[color:var(--color-text-secondary)] transition-all hover:bg-[color:var(--color-surface-hover)] hover:text-[color:var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0DA931]/45"
											>
												<Terminal className="w-3.5 h-3.5" />
												Import from cURL
											</button>
										</div>

										{/* Basic Configuration */}
										<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]">
											<button
												onClick={createToggleSectionHandler("basic")}
												className="w-full px-4 py-3 flex items-center justify-between hover:bg-[color:var(--color-surface)]/70 transition-colors"
											>
												<span className="font-medium text-slate-900">
													Basic Configuration
												</span>
												{expandedSections.basic ? (
													<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												) : (
													<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												)}
											</button>

											{expandedSections.basic && (
												<div className="px-4 pb-4 space-y-3">
													{/* Saved API Endpoint Selector */}
													<div className="pb-3 border-b border-[color:var(--color-border)]/30">
														<div className="flex items-center gap-2 mb-2">
															<Link className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
															<label className="text-xs capitalize text-[color:var(--color-text-muted)] font-semibold">
																Saved API Endpoint
															</label>
														</div>
														<EndpointPicker
															endpoints={availableEndpoints}
															value={config.endpoint_id || ""}
															onChange={handleEndpointSelect}
															variant="light"
														/>
														{config.endpoint_id && (
															<p className="text-xs text-[color:var(--color-text-muted)] mt-2">
																Fields pre-filled from saved endpoint. Override any field below.
															</p>
														)}
													</div>

													<div>
														<label
															htmlFor="action-name-input"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															Action Name
														</label>
														<input
															id="action-name-input"
															type="text"
															value={nodeName}
															onChange={handleNodeNameChange}
															placeholder="e.g., Get User Data, Update Customer Info"
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
														/>
														<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
															Give this action a descriptive name
														</p>
													</div>

													<div>
														<label
															htmlFor="url-template-input"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															URL Template
														</label>
														<input
															id="url-template-input"
															type="text"
															value={config.url_template}
															onChange={handleUrlTemplateChange}
															placeholder="https://api.example.com/users/{userId}/posts"
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
														/>
														<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
															Use {"{paramName}"} for URL parameters that will be
															replaced dynamically
														</p>
													</div>

													<div>
														<label
															htmlFor="http-method-select"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															HTTP Method
														</label>
														<select
															id="http-method-select"
															value={config.method}
															onChange={handleMethodChange}
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 focus:outline-none focus:border-[#0DA931]"
														>
															<option value="GET">GET</option>
															<option value="POST">POST</option>
															<option value="PUT">PUT</option>
															<option value="DELETE">DELETE</option>
															<option value="PATCH">PATCH</option>
														</select>
													</div>
												</div>
											)}
										</div>

										{/* URL Parameters */}
										{extractedUrlParams.length > 0 && (
											<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]">
												<button
													onClick={createToggleSectionHandler("urlParams")}
													className="w-full px-4 py-3 flex items-center justify-between hover:bg-[color:var(--color-surface)]/70 transition-colors"
												>
													<div className="flex items-center gap-2">
														<Link className="w-4 h-4 text-[#0DA931]" />
														<span className="font-medium text-slate-900">
															URL Parameters
														</span>
														<span className="px-2 py-0.5 bg-[#0DA931]/20 text-[#0DA931] text-xs rounded">
															{extractedUrlParams.length}
														</span>
													</div>
													{expandedSections.urlParams ? (
														<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
													) : (
														<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
													)}
												</button>

												{expandedSections.urlParams && (
													<div className="px-4 pb-4 space-y-3">
														<p className="text-sm text-[color:var(--color-text-muted)]">
															Configure how to populate URL parameters extracted from
															your template
														</p>
														{config.url_param_mappings?.map((mapping, index) => (
															<HttpParameterMappingRow
																key={`url-${index}`}
																mapping={mapping}
																onUpdate={createParameterUpdateHandler(
																	"url_param",
																	index,
																)}
																availableNodes={upstreamNodes}
																expandedByDefault={
																	config.url_param_mappings?.length === 1
																}
															/>
														))}
													</div>
												)}
											</div>
										)}

										{/* Query Parameters */}
										<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]">
											<button
												onClick={createToggleSectionHandler("queryParams")}
												className="w-full px-4 py-3 flex items-center justify-between hover:bg-[color:var(--color-surface)]/70 transition-colors"
											>
												<div className="flex items-center gap-2">
													<Search className="w-4 h-4 text-[color:var(--color-accent)]" />
													<span className="font-medium text-slate-900">
														Query Parameters
													</span>
													{(config.query_param_mappings?.length || 0) > 0 && (
														<span className="px-2 py-0.5 bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] text-xs rounded">
															{config.query_param_mappings?.length}
														</span>
													)}
												</div>
												{expandedSections.queryParams ? (
													<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												) : (
													<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												)}
											</button>

											{expandedSections.queryParams && (
												<div className="px-4 pb-4 space-y-3">
													{config.query_param_mappings?.map((mapping, index) => (
														<HttpParameterMappingRow
															key={`query-${index}`}
															mapping={mapping}
															onUpdate={createParameterUpdateHandler(
																"query_param",
																index,
															)}
															onDelete={createParameterDeleteHandler(
																"query_param",
																index,
															)}
															availableNodes={upstreamNodes}
														/>
													))}

													<button
														onClick={addQueryParameter}
														className="w-full py-2 border border-dashed border-[color:var(--color-surface-hover)] rounded-lg text-[color:var(--color-text-muted)] hover:text-slate-900 hover:border-[color:var(--color-text-muted)] transition-colors flex items-center justify-center gap-2"
													>
														<Plus className="w-4 h-4" />
														Add Query Parameter
													</button>
												</div>
											)}
										</div>

										{/* Headers */}
										<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]">
											<button
												onClick={createToggleSectionHandler("headers")}
												className="w-full px-4 py-3 flex items-center justify-between hover:bg-[color:var(--color-surface)]/70 transition-colors"
											>
												<div className="flex items-center gap-2">
													<Hash className="w-4 h-4 text-purple-400" />
													<span className="font-medium text-slate-900">Headers</span>
													{(config.header_mappings?.length || 0) > 0 && (
														<span className="px-2 py-0.5 bg-purple-400/20 text-purple-400 text-xs rounded">
															{config.header_mappings?.length}
														</span>
													)}
												</div>
												{expandedSections.headers ? (
													<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												) : (
													<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												)}
											</button>

											{expandedSections.headers && (
												<div className="px-4 pb-4 space-y-3">
													{config.header_mappings?.map((mapping, index) => (
														<HttpParameterMappingRow
															key={`header-${index}`}
															mapping={mapping}
															onUpdate={createParameterUpdateHandler("header", index)}
															onDelete={createParameterDeleteHandler("header", index)}
															availableNodes={upstreamNodes}
														/>
													))}

													<button
														onClick={addHeader}
														className="w-full py-2 border border-dashed border-[color:var(--color-surface-hover)] rounded-lg text-[color:var(--color-text-muted)] hover:text-slate-900 hover:border-[color:var(--color-text-muted)] transition-colors flex items-center justify-center gap-2"
													>
														<Plus className="w-4 h-4" />
														Add Header
													</button>
												</div>
											)}
										</div>

										{/* Request Body */}
										{config.method !== "GET" && config.method !== "DELETE" && (
											<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]">
												<button
													onClick={createToggleSectionHandler("body")}
													className="w-full px-4 py-3 flex items-center justify-between hover:bg-[color:var(--color-surface)]/70 transition-colors"
												>
													<div className="flex items-center gap-2">
														<FileJson className="w-4 h-4 text-[color:var(--color-accent)]" />
														<span className="font-medium text-slate-900">Request Body</span>
													</div>
													{expandedSections.body ? (
														<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
													) : (
														<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
													)}
												</button>

												{expandedSections.body && (
													<div className="px-4 pb-4 space-y-3">
														{/* Body Type Selector */}
														<div>
															<label
																id="body-type-label"
																className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
															>
																Body Type
															</label>
															<div
																className="flex gap-2"
																role="radiogroup"
																aria-labelledby="body-type-label"
															>
																{(["json", "form", "text", "raw"] as const).map(
																	(type) => (
																		<button
																			key={type}
																			onClick={createBodyTypeChangeHandler(type)}
																			className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
																				config.body_type === type
																					? "bg-[#0DA931]/20 text-[#0DA931] border border-[#0DA931]/30"
																					: "bg-[color:var(--color-surface)] text-[color:var(--color-text-muted)] border border-[color:var(--color-border)] hover:bg-[color:var(--color-border)]"
																			}`}
																		>
																			{type === "json" ? "JSON" : type.charAt(0).toUpperCase() + type.slice(1)}
																		</button>
																	),
																)}
															</div>
														</div>

														{/* JSON Body Fields */}
														{config.body_type === "json" && (
															<>
																<div className="space-y-3">
																	{config.body_mappings?.map((mapping, index) => (
																		<HttpParameterMappingRow
																			key={`body-${index}`}
																			mapping={mapping}
																			onUpdate={createParameterUpdateHandler(
																				"body_field",
																				index,
																			)}
																			onDelete={createParameterDeleteHandler(
																				"body_field",
																				index,
																			)}
																			availableNodes={upstreamNodes}
																		/>
																	))}

																	<button
																		onClick={addBodyField}
																		className="w-full py-2 border border-dashed border-[color:var(--color-surface-hover)] rounded-lg text-[color:var(--color-text-muted)] hover:text-slate-900 hover:border-[color:var(--color-text-muted)] transition-colors flex items-center justify-center gap-2"
																	>
																		<Plus className="w-4 h-4" />
																		Add Body Field
																	</button>
																</div>

																<div className="mt-3 p-3 bg-[color:var(--color-accent)]/10 border border-[color:var(--color-border)]/30 rounded-lg">
																	<p className="text-sm text-[color:var(--color-accent)]">
																		Fields will be combined into a JSON object. Use
																		nested paths like &quot;user.name&quot; for nested
																		objects.
																	</p>
																</div>
															</>
														)}

														{/* Form Data Fields */}
														{config.body_type === "form" && (
															<>
																<div className="space-y-3">
																	{config.body_mappings?.map((mapping, index) => (
																		<HttpParameterMappingRow
																			key={`form-${index}`}
																			mapping={mapping}
																			onUpdate={createParameterUpdateHandler(
																				"body_field",
																				index,
																			)}
																			onDelete={createParameterDeleteHandler(
																				"body_field",
																				index,
																			)}
																			availableNodes={upstreamNodes}
																		/>
																	))}

																	<button
																		onClick={addBodyField}
																		className="w-full py-2 border border-dashed border-[color:var(--color-surface-hover)] rounded-lg text-[color:var(--color-text-muted)] hover:text-slate-900 hover:border-[color:var(--color-text-muted)] transition-colors flex items-center justify-center gap-2"
																	>
																		<Plus className="w-4 h-4" />
																		Add Form Field
																	</button>
																</div>
															</>
														)}

														{/* Text/Raw Body Template */}
														{(config.body_type === "text" ||
															config.body_type === "raw") && (
															<div>
																<label
																	htmlFor="body-template-textarea"
																	className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-2"
																>
																	Body Template
																</label>
																<textarea
																	id="body-template-textarea"
																	value={config.body_template}
																	onChange={handleBodyTemplateChange}
																	placeholder={
																		config.body_type === "text"
																			? "Enter your text body here...\nYou can use {{variables}} for dynamic values"
																			: '{\n  "data": "{{message}}",\n  "timestamp": "{{timestamp}}"\n}'
																	}
																	rows={8}
																	className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931] font-mono text-sm"
																/>
																<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
																	Use {"{{node_name}}"} or {"{{node_name.field}}"} to
																	reference node outputs
																</p>
															</div>
														)}
													</div>
												)}
											</div>
										)}

										{/* Authentication */}
										<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]">
											<button
												onClick={createToggleSectionHandler("auth")}
												className="w-full px-4 py-3 flex items-center justify-between hover:bg-[color:var(--color-surface)]/70 transition-colors"
											>
												<div className="flex items-center gap-2">
													<Lock className="w-4 h-4 text-[color:var(--color-accent)]" />
													<span className="font-medium text-slate-900">Authentication</span>
												</div>
												{expandedSections.auth ? (
													<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												) : (
													<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												)}
											</button>

											{expandedSections.auth && (
												<div className="px-4 pb-4 space-y-3">
													<div>
														<label
															htmlFor="auth-type-select"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															Auth Type
														</label>
														<select
															id="auth-type-select"
															value={config.auth_type}
															onChange={handleAuthTypeChange}
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 focus:outline-none focus:border-[#0DA931]"
														>
															<option value="none">None</option>
															<option value="bearer">Bearer Token</option>
															<option value="basic">Basic Auth</option>
															<option value="api_key">API Key</option>
														</select>
													</div>

													{config.auth_type === "bearer" && (
														<div>
															<label
																htmlFor="bearer-token-input"
																className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
															>
																Bearer Token
															</label>
															<input
																id="bearer-token-input"
																type="text"
																value={config.auth_config?.token || ""}
																onChange={handleAuthTokenChange}
																placeholder="Enter token or {{variable}}"
																className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
															/>
														</div>
													)}

													{config.auth_type === "basic" && (
														<>
															<div>
																<label
																	htmlFor="username-input"
																	className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
																>
																	Username
																</label>
																<input
																	id="username-input"
																	type="text"
																	value={config.auth_config?.username || ""}
																	onChange={handleAuthUsernameChange}
																	className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
																/>
															</div>
															<div>
																<label
																	htmlFor="password-input"
																	className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
																>
																	Password
																</label>
																<input
																	id="password-input"
																	type="password"
																	value={config.auth_config?.password || ""}
																	onChange={handleAuthPasswordChange}
																	className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
																/>
															</div>
														</>
													)}

													{config.auth_type === "api_key" && (
														<>
															<div>
																<label
																	htmlFor="api-key-header-input"
																	className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
																>
																	API Key Header Name
																</label>
																<input
																	id="api-key-header-input"
																	type="text"
																	value={config.auth_config?.header_name || "X-API-Key"}
																	onChange={handleAuthHeaderNameChange}
																	className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
																/>
															</div>
															<div>
																<label
																	htmlFor="api-key-value-input"
																	className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
																>
																	API Key Value
																</label>
																<input
																	id="api-key-value-input"
																	type="text"
																	value={config.auth_config?.api_key || ""}
																	onChange={handleAuthApiKeyChange}
																	placeholder="Enter key or {{variable}}"
																	className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
																/>
															</div>
														</>
													)}
												</div>
											)}
										</div>

										{/* Advanced Settings */}
										<div className="bg-[color:var(--color-surface)]/50 rounded-lg border border-[color:var(--color-border)]">
											<button
												onClick={createToggleSectionHandler("advanced")}
												className="w-full px-4 py-3 flex items-center justify-between hover:bg-[color:var(--color-surface)]/70 transition-colors"
											>
												<span className="font-medium text-slate-900">
													Advanced Settings
												</span>
												{expandedSections.advanced ? (
													<ChevronDown className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												) : (
													<ChevronRight className="w-4 h-4 text-[color:var(--color-text-muted)]" />
												)}
											</button>

											{expandedSections.advanced && (
												<div className="px-4 pb-4 space-y-3">
													<div>
														<label
															htmlFor="timeout-input"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															Timeout (seconds)
														</label>
														<input
															id="timeout-input"
															type="number"
															value={config.timeout_seconds}
															onChange={handleTimeoutChange}
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 focus:outline-none focus:border-[#0DA931]"
														/>
													</div>

													<div>
														<label
															htmlFor="max-retries-input"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															Max Retries
														</label>
														<input
															id="max-retries-input"
															type="number"
															value={config.max_retries}
															onChange={handleMaxRetriesChange}
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 focus:outline-none focus:border-[#0DA931]"
														/>
													</div>

													<div>
														<label
															htmlFor="verify-ssl-input"
															className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]"
														>
															<input
																id="verify-ssl-input"
																type="checkbox"
																checked={config.verify_ssl ?? true}
																onChange={handleVerifySslChange}
																className="w-4 h-4 accent-[#0DA931]"
															/>
															Verify SSL Certificates
														</label>
														<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
															Disable only for endpoints with self-signed
															certificates
														</p>
													</div>

													<div>
														<label
															htmlFor="response-path-input"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															Response Path
														</label>
														<input
															id="response-path-input"
															type="text"
															value={config.response_path}
															onChange={handleResponsePathChange}
															placeholder="e.g., data.results"
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
														/>
														<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
															JSONPath to extract specific data from response
														</p>
													</div>

													<div>
														<label
															htmlFor="success-codes-input"
															className="block text-sm font-medium text-[color:var(--color-text-secondary)] mb-1"
														>
															Success Status Codes
														</label>
														<input
															id="success-codes-input"
															type="text"
															value={config.success_status_codes?.join(", ")}
															onChange={handleSuccessStatusCodesChange}
															placeholder="200, 201, 202"
															className="w-full px-3 py-2 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:border-[#0DA931]"
														/>
													</div>
												</div>
											)}
										</div>
									</div>
								)}

								{/* Guardrails Tab */}
								{activeTab === "guardrails" && (
									<ToolGuardrailsSection toolNodeId={nodeId} />
								)}
							</div>
						</div>

						{/* Footer */}
						<div className="border-t border-[color:var(--color-border)]/30 bg-[color:var(--color-bg-secondary)]/80 px-6 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.03),0_-12px_35px_rgba(0,0,0,0.4)]">
							<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
								{/* Left: Delete button */}
								<button
									type="button"
									onClick={handleDeleteAndClose}
									className="px-3 py-2 rounded-[4px] transition-all flex items-center gap-1.5 border bg-white hover:bg-red-50/70 text-red-600 hover:text-red-700 text-xs"
									style={{ borderColor: "var(--color-border)" }}
								>
									<Trash2 className="w-3.5 h-3.5" />
									Delete Node
								</button>

								{/* Right: Unsaved + hint + Cancel + Save */}
								<div className="flex items-center gap-3 sm:ml-auto">
									{hasUnsavedChanges && (
										<span className="flex items-center gap-1.5 text-[11px] text-[color:var(--color-text-muted)]">
											<span className="h-1.5 w-1.5 rounded-full bg-[#0DA931] animate-smoothPulse" />
											Unsaved
										</span>
									)}
									<span className="text-[11px] text-[color:var(--color-text-muted)]/50 hidden sm:inline">
										{"\u2318"}S to save
									</span>
									<button
										type="button"
										onClick={handleClose}
										className="px-4 py-2 rounded-[4px] border border-[color:var(--color-border)] bg-white text-xs text-[color:var(--color-text-secondary)] transition-all hover:bg-[color:var(--color-surface-hover)]/40 hover:text-[color:var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0DA931]/45"
									>
										Cancel
									</button>
									<button
										type="button"
										onClick={() => void handleSave()}
										disabled={saving}
										className="px-5 py-2 rounded-lg bg-gradient-to-br from-[#0DA931] to-[#0DA931]/80 text-xs font-medium text-white shadow-[0_15px_40px_rgba(13,169,49,0.35)] transition-all hover:shadow-[0_20px_50px_rgba(13,169,49,0.45)] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0DA931]/45"
									>
										<span className="inline-flex items-center gap-1.5">
											<Save className="w-3.5 h-3.5" />
											{saving ? "Saving..." : "Save Changes"}
										</span>
									</button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			{/* Delete Confirmation Dialog */}
			<ConfirmDialog
				isOpen={showDeleteConfirm}
				onClose={() => setShowDeleteConfirm(false)}
				onConfirm={handleConfirmDelete}
				title="Delete Node?"
				message="Are you sure you want to delete this node? This action cannot be undone."
				confirmText="Delete"
				cancelText="Cancel"
				variant="danger"
				surface="light"
			/>

			{/* cURL Import Dialog — portaled above the panel modal (z-110),
			    with propagation stopped so the panel's backdrop-close never fires */}
			{showCurlImport &&
				createPortal(
				<div
					className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 p-4"
					onClick={(e) => {
						e.stopPropagation();
						if (e.target === e.currentTarget) setShowCurlImport(false);
					}}
				>
					<div
						className="w-full max-w-2xl rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface)] shadow-2xl"
						onClick={(e) => e.stopPropagation()}
					>
						<div className="flex items-center justify-between border-b border-[color:var(--color-border)] px-5 py-3.5">
							<div className="flex items-center gap-2">
								<ClipboardPaste className="h-4 w-4 text-[#0DA931]" />
								<h3 className="text-sm font-semibold text-[color:var(--color-text-primary)]">
									Import from cURL
								</h3>
							</div>
							<button
								type="button"
								onClick={() => setShowCurlImport(false)}
								className="rounded-[4px] p-1 text-[color:var(--color-text-muted)] transition-colors hover:text-[color:var(--color-text-primary)]"
							>
								<X className="h-4 w-4" />
							</button>
						</div>
						<div className="space-y-3 px-5 py-4">
							<p className="text-xs text-[color:var(--color-text-muted)]">
								Paste a curl command (e.g. from Chrome DevTools “Copy as cURL”
								or API docs). Method, URL, query params, headers, body and auth
								will be filled in automatically — like Postman.
							</p>
							<textarea
								value={curlText}
								onChange={(e) => {
									setCurlText(e.target.value);
									if (curlError) setCurlError(null);
								}}
								placeholder={`curl -X POST 'https://api.example.com/v1/users?active=true' \\\n  -H 'Content-Type: application/json' \\\n  -H 'Authorization: Bearer <token>' \\\n  -d '{"name": "Jane", "role": "admin"}'`}
								rows={9}
								spellCheck={false}
								className="w-full resize-y rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-bg-primary)] px-3 py-2 font-mono text-xs text-[color:var(--color-text-primary)] placeholder-slate-400 focus:border-[#0DA931] focus:outline-none"
							/>
							{curlError && (
								<p className="text-xs font-medium text-red-500">{curlError}</p>
							)}
						</div>
						<div className="flex justify-end gap-2 border-t border-[color:var(--color-border)] px-5 py-3.5">
							<button
								type="button"
								onClick={() => setShowCurlImport(false)}
								className="px-4 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-xs font-medium text-[color:var(--color-text-secondary)] transition-colors hover:bg-[color:var(--color-surface-hover)]"
							>
								Cancel
							</button>
							<button
								type="button"
								onClick={handleCurlImport}
								disabled={!curlText.trim()}
								className="px-4 py-2 rounded-lg bg-gradient-to-br from-[#0DA931] to-[#0DA931]/80 text-xs font-medium text-white transition-all hover:shadow-[0_10px_30px_rgba(13,169,49,0.35)] disabled:opacity-50"
							>
								<span className="inline-flex items-center gap-1.5">
									<Terminal className="w-3.5 h-3.5" />
									Import
								</span>
							</button>
						</div>
					</div>
				</div>,
				document.body,
			)}

		</div>
	);
}
