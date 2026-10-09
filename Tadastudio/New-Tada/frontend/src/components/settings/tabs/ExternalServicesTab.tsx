"use client";

import {
	Activity,
	Eye,
	EyeOff,
	FileText,
	Globe,
	Link2,
	Loader2,
	Mail,
	Save,
	Search,
	Settings,
	Trash2,
	User,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { systemExternalServicesAPI } from "@/lib/admin-api";
import { configAPI, type EnvironmentConfig } from "@/lib/config-api";
import { modelDeploymentAPI, type ModelDeploymentOption } from "@/lib/model-deployment-api";
import { userSettingsAPI } from "@/lib/user-settings-api";

interface ExternalServicesTabProps {
	config: EnvironmentConfig;
	onUpdate: (section: string, key: string, value: any) => void;
	onSaved?: () => void;
	onHasChanges?: (dirty: boolean) => void;
}

const LIGHT_FIELD =
	"!rounded-[4px] !border-slate-200 !bg-white !text-slate-900 placeholder:!text-slate-400 hover:!border-orange-400 focus:!border-orange-500 focus:!ring-orange-500/15";
const SELECT_LIGHT =
	"w-full rounded-[4px] border border-slate-200 bg-white px-4 py-2 text-slate-900 transition-colors hover:border-orange-400 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/15 disabled:opacity-60";
const DROPDOWN_TRIGGER =
	"w-full !rounded-[4px] !border-slate-200 !bg-white !px-4 !py-2 !text-slate-900 hover:!border-orange-400";

export default function ExternalServicesTab({
	config,
	onUpdate,
	onSaved,
	onHasChanges,
}: ExternalServicesTabProps) {
	const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});
	const { showToast } = useToast();
	const { user: authUser } = useAuth();

	const isAdmin = authUser?.role === "ADMIN" || (authUser as any)?.is_admin === true;
	const [scope, setScope] = useState<"personal" | "system">(isAdmin ? "system" : "personal");
	const [loading, setLoading] = useState(true);
	const [isSaving, setIsSaving] = useState(false);
	const [hasChanges, setHasChanges] = useState(false);
	const markDirty = useCallback(() => setHasChanges(true), []);

	useEffect(() => {
		onHasChanges?.(hasChanges);
	}, [hasChanges, onHasChanges]);

	const createToggleVisibilityHandler = useCallback(
		(key: string) => () => setShowApiKeys((prev) => ({ ...prev, [key]: !prev[key] })),
		[],
	);

	// Sentinel used for system-scope secret fields where the API only tells us
	// a credential exists but never returns the value.
	const MASKED_SENTINEL = "••••••••••••••••";

	// ── Service state (scope-agnostic — reloaded when scope changes) ──────────

	// Tavily
	const [tavilyConfigured, setTavilyConfigured] = useState(false);
	const [tavilyMasked, setTavilyMasked] = useState("");
	const [tavilyKeyInput, setTavilyKeyInput] = useState("");

	// Email
	const [emailConfigured, setEmailConfigured] = useState(false);
	const [emailProvider, setEmailProvider] = useState("outlook");
	const [emailMasked, setEmailMasked] = useState("");
	const [emailKeyInput, setEmailKeyInput] = useState("");
	const [emailUPN, setEmailUPN] = useState("");
	const [emailDomain, setEmailDomain] = useState("");

	// Tika
	const [tikaConfigured, setTikaConfigured] = useState(false);
	const [tikaSavedUrl, setTikaSavedUrl] = useState("");
	const [tikaUrlInput, setTikaUrlInput] = useState("");

	// Azure Document Intelligence
	const [azureDiConfigured, setAzureDiConfigured] = useState(false);
	const [azureDiSavedEndpoint, setAzureDiSavedEndpoint] = useState("");
	const [azureDiEndpointInput, setAzureDiEndpointInput] = useState("");
	const [azureDiMasked, setAzureDiMasked] = useState("");
	const [azureDiKeyInput, setAzureDiKeyInput] = useState("");
	const [azureDiManagedIdentity, setAzureDiManagedIdentity] = useState(false);
	const [azureDiModelId, setAzureDiModelId] = useState("prebuilt-read");

	// Tika timeout and Azure DI model_id (system scope)
	const [tikaTimeout, setTikaTimeout] = useState<number>(60);

	// Model OCR detail level
	const [modelOcrDetail, setModelOcrDetail] = useState(
		config.external_services.document_extraction?.model_ocr_detail ?? "high",
	);

	// ── System-default badge state (personal scope only — loaded once) ────────
	const [sysDefaults, setSysDefaults] = useState({
		tavily: false,
		email: false,
		tika: false,
		azureDi: false,
	});

	// ── System-only settings (document extraction provider + LangChain) ─
	const [docExtractionProvider, setDocExtractionProvider] = useState<string>(
		config.external_services.document_extraction?.provider ?? "model_ocr",
	);
	const [modelOcrDeploymentId, setModelOcrDeploymentId] = useState(
		config.external_services.document_extraction?.model_ocr_deployment_id ?? "",
	);
	const [llmDeployments, setLlmDeployments] = useState<ModelDeploymentOption[]>([]);
	const [langchainApiKey, setLangchainApiKey] = useState(
		config.external_services.langchain?.api_key ?? "",
	);
	const [langchainTracingV2, setLangchainTracingV2] = useState(
		config.external_services.langchain?.tracing_v2 ?? false,
	);
	const [langchainProject, setLangchainProject] = useState(
		config.external_services.langchain?.project ?? "default",
	);

	// Phoenix
	const [phoenixEnabled, setPhoenixEnabled] = useState(
		config.external_services.phoenix?.enabled ?? false,
	);
	const [phoenixEndpoint, setPhoenixEndpoint] = useState(
		config.external_services.phoenix?.endpoint ?? "",
	);
	const [phoenixProjectName, setPhoenixProjectName] = useState(
		config.external_services.phoenix?.project_name ?? "agentic-studio",
	);
	const [phoenixApiKey, setPhoenixApiKey] = useState(
		config.external_services.phoenix?.api_key ?? "",
	);
	const [phoenixUiUrl, setPhoenixUiUrl] = useState(
		config.external_services.phoenix?.ui_url ?? "",
	);
	const [phoenixEvalPenaltyEnabled, setPhoenixEvalPenaltyEnabled] = useState(
		config.external_services.phoenix?.eval_penalty_enabled ?? false,
	);
	const [phoenixEvalFaithfulnessEnabled, setPhoenixEvalFaithfulnessEnabled] = useState(
		config.external_services.phoenix?.eval_faithfulness_enabled ?? true,
	);
	const [phoenixEvalToolSelectionEnabled, setPhoenixEvalToolSelectionEnabled] = useState(
		config.external_services.phoenix?.eval_tool_selection_enabled ?? true,
	);
	const [phoenixEvalLlmJudgeEnabled, setPhoenixEvalLlmJudgeEnabled] = useState(
		config.external_services.phoenix?.eval_llm_judge_enabled ?? false,
	);

	useEffect(() => {
		setDocExtractionProvider(config.external_services.document_extraction?.provider ?? "model_ocr");
		setModelOcrDeploymentId(config.external_services.document_extraction?.model_ocr_deployment_id ?? "");
		setModelOcrDetail(config.external_services.document_extraction?.model_ocr_detail ?? "high");
	}, [config.external_services.document_extraction]);

	useEffect(() => {
		setLangchainApiKey(config.external_services.langchain?.api_key ?? "");
		setLangchainTracingV2(config.external_services.langchain?.tracing_v2 ?? false);
		setLangchainProject(config.external_services.langchain?.project ?? "default");
	}, [config.external_services.langchain]);

	useEffect(() => {
		setPhoenixEnabled(config.external_services.phoenix?.enabled ?? false);
		setPhoenixEndpoint(config.external_services.phoenix?.endpoint ?? "");
		setPhoenixProjectName(config.external_services.phoenix?.project_name ?? "agentic-studio");
		setPhoenixApiKey(config.external_services.phoenix?.api_key ?? "");
		setPhoenixUiUrl(config.external_services.phoenix?.ui_url ?? "");
		setPhoenixEvalPenaltyEnabled(config.external_services.phoenix?.eval_penalty_enabled ?? false);
		setPhoenixEvalFaithfulnessEnabled(config.external_services.phoenix?.eval_faithfulness_enabled ?? true);
		setPhoenixEvalToolSelectionEnabled(config.external_services.phoenix?.eval_tool_selection_enabled ?? true);
		setPhoenixEvalLlmJudgeEnabled(config.external_services.phoenix?.eval_llm_judge_enabled ?? false);
	}, [config.external_services.phoenix]);

	useEffect(() => {
		modelDeploymentAPI
			.listSelectOptions()
			.then((d) => setLlmDeployments(d.filter((x) => x.model_type === "llm" && x.is_active)))
			.catch(() => {});
	}, []);

	// ── Data loaders ──────────────────────────────────────────────────────────

	const loadScope = useCallback(async (s: typeof scope) => {
		setLoading(true);
		try {
			if (s === "personal") {
				const [tavily, email] = await Promise.all([
					userSettingsAPI.getExternalService("tavily").catch(() => null),
					userSettingsAPI.getExternalService("email").catch(() => null),
				]);

				setTavilyConfigured(!!tavily?.api_key_configured);
				setTavilyMasked(tavily?.api_key_masked ?? "");
				setTavilyKeyInput(tavily?.api_key_masked ?? "");

				setEmailConfigured(!!email);
				setEmailProvider(email?.settings?.provider ?? "outlook");
				setEmailMasked(email?.api_key_masked ?? "");
				setEmailKeyInput(email?.api_key_masked ?? "");
				setEmailUPN(email?.settings?.user_principal_name ?? "");
				setEmailDomain(email?.settings?.domain ?? "");
			} else {
				const [tavily, email, tika, azureDi] = await Promise.all([
					systemExternalServicesAPI.get("tavily").catch(() => null),
					systemExternalServicesAPI.get("email").catch(() => null),
					systemExternalServicesAPI.get("tika").catch(() => null),
					systemExternalServicesAPI.get("azure_document_intelligence").catch(() => null),
				]);

				const tavilyMaskedVal = tavily?.credentials_masked?.api_key ?? (tavily?.credentials_configured ? MASKED_SENTINEL : "");
				setTavilyConfigured(!!tavily?.credentials_configured);
				setTavilyMasked(tavilyMaskedVal);
				setTavilyKeyInput(tavilyMaskedVal);

				setEmailConfigured(!!email);
				setEmailProvider((email?.settings?.provider as string) ?? "outlook");
				const emailMaskedVal = email?.credentials_masked?.api_key ?? ((email?.credential_fields_configured as string[] | null)?.includes("api_key") ? MASKED_SENTINEL : "");
				setEmailMasked(emailMaskedVal);
				setEmailKeyInput(emailMaskedVal);
				setEmailUPN((email?.settings?.user_principal_name as string) ?? "");
				setEmailDomain((email?.settings?.domain as string) ?? "");

				setTikaConfigured(!!tika?.service_url);
				setTikaSavedUrl(tika?.service_url ?? "");
				setTikaUrlInput(tika?.service_url ?? "");
				setTikaTimeout((tika?.settings?.timeout_seconds as number) ?? 60);

				setAzureDiConfigured(!!azureDi?.service_url);
				setAzureDiSavedEndpoint(azureDi?.service_url ?? "");
				setAzureDiEndpointInput(azureDi?.service_url ?? "");
				const azureDiMaskedVal = azureDi?.credentials_masked?.api_key ?? ((azureDi?.credential_fields_configured as string[] | null)?.includes("api_key") ? MASKED_SENTINEL : "");
				setAzureDiMasked(azureDiMaskedVal);
				setAzureDiKeyInput(azureDiMaskedVal);
				setAzureDiManagedIdentity(!!(azureDi?.settings?.use_managed_identity));
				setAzureDiModelId((azureDi?.settings?.model_id as string) ?? "prebuilt-read");
			}
		} catch (error) {
			console.error("Failed to load services:", error);
		} finally {
			setLoading(false);
			setHasChanges(false);
		}
	}, [isAdmin]);

	// Load system defaults for personal-scope badges (admin only — endpoint is admin-gated)
	useEffect(() => {
		if (!isAdmin) return;
		systemExternalServicesAPI
			.list()
			.then((services) => {
				const active = new Set(services.filter((s) => s.is_active).map((s) => s.service_name));
				setSysDefaults({
					tavily: active.has("tavily"),
					email: active.has("email"),
					tika: active.has("tika"),
					azureDi: active.has("azure_document_intelligence"),
				});
			})
			.catch(() => {});
	}, [isAdmin]);

	// Reload when scope changes
	useEffect(() => {
		loadScope(scope);
	}, [scope, loadScope]);

	// ── Status helpers ────────────────────────────────────────────────────────

	const statusDot = (configured: boolean, sysActive: boolean) =>
		`w-2 h-2 rounded-full ${
			configured
				? "bg-[#0DA931] animate-pulse"
				: sysActive && scope === "personal"
					? "bg-blue-400"
					: "bg-slate-400"
		}`;

	const statusLabel = (configured: boolean, sysActive: boolean) =>
		configured
			? "Connected"
			: sysActive && scope === "personal"
				? "Using system default"
				: "Not Configured";

	const optionalPlaceholder = (sysActive: boolean, fallback: string) =>
		sysActive && scope === "personal" ? "Optional — system default is active" : fallback;

	// ── Remove handler (personal scope) ──────────────────────────────────────

	const handleRemoveService = async (serviceName: string) => {
		try {
			await userSettingsAPI.deleteExternalService(serviceName);
			showToast("success", `Removed personal ${serviceName} configuration`);
			await loadScope(scope);
		} catch {
			showToast("error", `Failed to remove ${serviceName} configuration`);
		}
	};

	// ── Save handler ──────────────────────────────────────────────────────────

	const handleSaveAll = async () => {
		try {
			setIsSaving(true);

			if (scope === "personal") {
				const saves: Promise<any>[] = [];

				// LangChain + Phoenix are always system-level config (admin only)
				if (isAdmin) {
					saves.push(
						configAPI.updateEnvironmentConfig({
							"external_services.langchain.api_key": langchainApiKey,
							"external_services.langchain.tracing_v2": langchainTracingV2,
							"external_services.langchain.project": langchainProject,
							"external_services.phoenix.enabled": phoenixEnabled,
							"external_services.phoenix.endpoint": phoenixEndpoint,
							"external_services.phoenix.project_name": phoenixProjectName,
							"external_services.phoenix.api_key": phoenixApiKey,
							"external_services.phoenix.ui_url": phoenixUiUrl,
							"external_services.phoenix.eval_penalty_enabled": phoenixEvalPenaltyEnabled,
							"external_services.phoenix.eval_faithfulness_enabled": phoenixEvalFaithfulnessEnabled,
							"external_services.phoenix.eval_tool_selection_enabled": phoenixEvalToolSelectionEnabled,
							"external_services.phoenix.eval_llm_judge_enabled": phoenixEvalLlmJudgeEnabled,
						}),
					);
				}

				// Tavily — skip if unchanged, delete if cleared
				const tavilyChanged = tavilyKeyInput !== tavilyMasked;
				if (tavilyChanged && tavilyKeyInput.trim()) {
					saves.push(
						userSettingsAPI.saveTavilyApiKey(tavilyKeyInput.trim()).then(() => loadScope(scope)),
					);
				} else if (tavilyConfigured && tavilyChanged && !tavilyKeyInput.trim()) {
					saves.push(
						userSettingsAPI.deleteExternalService("tavily").then(() => loadScope(scope)),
					);
				}

				// Email
				const emailBody: Record<string, any> = { provider: emailProvider };
				if (emailProvider === "outlook") emailBody.user_principal_name = emailUPN.trim();
				if (emailProvider === "mailgun") emailBody.domain = emailDomain.trim() || "sandbox.mailgun.org";
				saves.push(
					userSettingsAPI
						.saveExternalService("email", {
							api_key:
								emailKeyInput !== emailMasked && emailKeyInput.trim()
									? emailKeyInput.trim()
									: emailMasked
										? undefined
										: "placeholder",
							settings: emailBody,
						})
						.then(() => loadScope(scope)),
				);

				await Promise.all(saves);
			} else {
				// System scope
				const systemSaves: Promise<any>[] = [];

				// Doc extraction + LangChain via config API
				const configUpdates: Record<string, any> = {
					"external_services.document_extraction.provider": docExtractionProvider,
					"external_services.document_extraction.model_ocr_deployment_id": modelOcrDeploymentId,
					"external_services.document_extraction.model_ocr_detail": modelOcrDetail,
					"external_services.langchain.api_key": langchainApiKey,
					"external_services.langchain.tracing_v2": langchainTracingV2,
					"external_services.langchain.project": langchainProject,
					"external_services.phoenix.enabled": phoenixEnabled,
					"external_services.phoenix.endpoint": phoenixEndpoint,
					"external_services.phoenix.project_name": phoenixProjectName,
					"external_services.phoenix.api_key": phoenixApiKey,
					"external_services.phoenix.ui_url": phoenixUiUrl,
						"external_services.phoenix.eval_penalty_enabled": phoenixEvalPenaltyEnabled,
						"external_services.phoenix.eval_faithfulness_enabled": phoenixEvalFaithfulnessEnabled,
						"external_services.phoenix.eval_tool_selection_enabled": phoenixEvalToolSelectionEnabled,
						"external_services.phoenix.eval_llm_judge_enabled": phoenixEvalLlmJudgeEnabled,
				};
				if (docExtractionProvider === "tika") {
					configUpdates["external_services.document_extraction.tika.server_url"] = tikaUrlInput.trim();
				} else if (docExtractionProvider === "azure_document_intelligence") {
					configUpdates["external_services.document_extraction.azure_document_intelligence.endpoint"] = azureDiEndpointInput.trim();
					configUpdates["external_services.document_extraction.azure_document_intelligence.use_managed_identity"] = azureDiManagedIdentity;
				}
				systemSaves.push(configAPI.updateEnvironmentConfig(configUpdates));

				// Tavily — skip if unchanged, delete if cleared
				const tavilyChanged = tavilyKeyInput !== tavilyMasked;
				if (tavilyChanged && tavilyKeyInput.trim()) {
					systemSaves.push(
						systemExternalServicesAPI.upsert("tavily", {
							credentials: { api_key: tavilyKeyInput.trim() },
							is_active: true,
						}),
					);
				} else if (tavilyConfigured && tavilyChanged && !tavilyKeyInput.trim()) {
					systemSaves.push(systemExternalServicesAPI.delete("tavily"));
				}

				// Email
				const emailBody: Record<string, any> = {
					settings: { provider: emailProvider, user_principal_name: emailUPN, domain: emailDomain },
					is_active: true,
				};
				if (emailKeyInput !== emailMasked && emailKeyInput.trim()) {
					emailBody.credentials = { api_key: emailKeyInput.trim() };
				}
				systemSaves.push(systemExternalServicesAPI.upsert("email", emailBody));

				// Tika
				if (tikaUrlInput.trim()) {
					systemSaves.push(
						systemExternalServicesAPI.upsert("tika", {
							service_url: tikaUrlInput.trim(),
							settings: { timeout_seconds: tikaTimeout },
							is_active: true,
						}),
					);
				} else if (tikaConfigured) {
					systemSaves.push(systemExternalServicesAPI.delete("tika"));
				}

				// Azure Document Intelligence
				const azureDiBody: Record<string, any> = {
					service_url: azureDiEndpointInput.trim(),
					settings: { use_managed_identity: azureDiManagedIdentity, model_id: azureDiModelId },
					is_active: !!azureDiEndpointInput.trim(),
				};
				if (azureDiKeyInput !== azureDiMasked && azureDiKeyInput.trim()) {
					azureDiBody.credentials = { api_key: azureDiKeyInput.trim() };
				}
				if (azureDiEndpointInput.trim() || azureDiConfigured) {
					systemSaves.push(systemExternalServicesAPI.upsert("azure_document_intelligence", azureDiBody));
				}

				await Promise.all(systemSaves);
				await loadScope(scope);
			}

			setHasChanges(false);
			showToast("success", `${scope === "personal" ? "Personal" : "System"} settings saved`);
			onSaved?.();
		} catch (error) {
			console.error("Failed to save external services:", error);
			showToast("error", "Failed to save external services");
		} finally {
			setIsSaving(false);
		}
	};

	// ── Render ────────────────────────────────────────────────────────────────

	return (
		<div className="flex flex-col h-full">
			{/* Header */}
			<div className="flex flex-col gap-4 shrink-0 border-b border-slate-200 px-6 pb-4 pt-6 lg:flex-row lg:items-center lg:justify-between">
				<div className="flex items-center gap-3 flex-shrink-0">
					<div className="flex items-center justify-center rounded-[4px] border border-emerald-200 bg-white p-2">
						<Globe className="h-6 w-6 text-emerald-600" />
					</div>
					<div>
						<h2 className="text-xl font-semibold tracking-tight text-slate-900">External Services</h2>
						<p className="mt-1 text-sm text-slate-600">Configure third-party integrations and APIs</p>
					</div>
				</div>
				<div className="flex flex-wrap items-center gap-3 md:gap-2">
					{isAdmin && (["system", "personal"] as const).map((s) => (
						<button
							key={s}
							type="button"
							onClick={() => setScope(s)}
							className={`flex items-center gap-2 whitespace-nowrap rounded-[4px] px-4 py-2.5 text-sm font-medium transition-colors flex-shrink-0 ${
								scope === s
									? "border border-orange-500 bg-white text-orange-900"
									: "border border-transparent text-slate-700 hover:border-slate-200 hover:bg-slate-50"
							}`}
						>
							{s === "personal" ? <User className="h-4 w-4" /> : <Settings className="h-4 w-4" />}
							<span>{s === "personal" ? "Personal" : "System-wide"}</span>
						</button>
					))}
					<button
						type="button"
						onClick={handleSaveAll}
						disabled={isSaving || !hasChanges}
						className={`flex items-center gap-2 rounded-[4px] px-4 py-2.5 text-sm font-medium transition-all disabled:cursor-not-allowed disabled:opacity-50 flex-shrink-0 ${
							hasChanges
								? "border border-orange-500 bg-orange-500 text-white shadow-[0_8px_20px_rgba(15,23,42,0.12)] hover:bg-orange-600"
								: "border border-slate-200 bg-white text-slate-800 hover:border-orange-400 hover:text-slate-900"
						}`}
					>
						{isSaving ? <Loader2 className="h-4 w-4 animate-spin text-orange-500" /> : <Save className="h-4 w-4" />}
						{isSaving ? "Saving…" : "Save Changes"}
					</button>
				</div>
			</div>

			{/* Scrollable panels area */}
			<div className="flex-1 min-h-0 overflow-y-auto px-6 py-6">
				{loading ? (
					<div className="flex justify-center py-20">
						<Loader2 className="w-8 h-8 animate-spin text-orange-600" />
					</div>
				) : (
					<div className="space-y-6 mb-8">

						{/* ── Tavily Web Search ──────────────────────────────────── */}
						<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
							<div className="flex items-center justify-between mb-4">
								<div className="flex items-center gap-3">
									<Search className="w-6 h-6 text-orange-600" />
									<div>
										<h3 className="text-lg font-semibold text-slate-900">Tavily Web Search</h3>
										<p className="text-sm text-slate-600">AI-powered web search API</p>
									</div>
								</div>
								<div className="flex items-center gap-2">
									<div className={statusDot(tavilyConfigured, sysDefaults.tavily)} />
									<span className="text-sm text-slate-600">
										{statusLabel(tavilyConfigured, sysDefaults.tavily)}
									</span>
									{scope === "personal" && tavilyConfigured && (
										<button
											type="button"
											onClick={() => handleRemoveService("tavily")}
											className="ml-2 rounded p-1 text-slate-600 transition-colors hover:bg-red-50 hover:text-red-700"
											title="Remove personal configuration"
										>
											<Trash2 className="w-4 h-4" />
										</button>
									)}
								</div>
							</div>

							<div className="space-y-4">
								<div>
									<label
										htmlFor="tavily-api-key"
										className="mb-2 block text-sm font-medium text-slate-900"
									>
										API Key
									</label>
									<div className="relative">
										<FormInput
											id="tavily-api-key"
											type={showApiKeys["tavily"] ? "text" : "password"}
											value={tavilyKeyInput}
											onChange={(e) => {
												setTavilyKeyInput(e.target.value);
												markDirty();
											}}
											placeholder={optionalPlaceholder(sysDefaults.tavily, "Enter Tavily API key")}
											className={`${LIGHT_FIELD} pr-10`}
											disabled={isSaving}
										/>
										<button
											type="button"
											onClick={createToggleVisibilityHandler("tavily")}
											className="absolute right-2 top-2.5"
											aria-label="Toggle visibility"
										>
											{showApiKeys["tavily"] ? (
												<EyeOff className="w-5 h-5" />
											) : (
												<Eye className="w-5 h-5" />
											)}
										</button>
									</div>
								</div>
							</div>
						</div>

						{/* ── Email Service ──────────────────────────────────────── */}
						<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
							<div className="flex items-center justify-between mb-4">
								<div className="flex items-center gap-3">
									<Mail className="h-6 w-6 text-blue-600" />
									<div>
										<h3 className="text-lg font-semibold text-slate-900">Email Service</h3>
										<p className="text-sm text-slate-600">
											Email provider for workflow notifications
										</p>
									</div>
								</div>
								<div className="flex items-center gap-2">
									<div className={statusDot(emailConfigured, sysDefaults.email)} />
									<span className="text-sm text-slate-600">
										{statusLabel(emailConfigured, sysDefaults.email)}
									</span>
									{scope === "personal" && emailConfigured && (
										<button
											type="button"
											onClick={() => handleRemoveService("email")}
											className="ml-2 rounded p-1 text-slate-600 transition-colors hover:bg-red-50 hover:text-red-700"
											title="Remove personal configuration"
										>
											<Trash2 className="w-4 h-4" />
										</button>
									)}
								</div>
							</div>

							<div className="space-y-4">
								<div>
									<label
										htmlFor="email-provider"
										className="mb-2 block text-sm font-medium text-slate-900"
									>
										Email Provider
									</label>
									<Dropdown
										value={emailProvider}
										onChange={(v) => {
											setEmailProvider(v);
											markDirty();
										}}
										disabled={isSaving}
										menuAppearance="light"
										width="trigger"
										triggerClassName={DROPDOWN_TRIGGER}
										options={[
											{ value: "outlook", label: "Microsoft Outlook" },
											{ value: "mailgun", label: "Mailgun" },
											{ value: "mailslurp", label: "MailSlurp" },
										]}
									/>
								</div>

								{emailProvider === "outlook" && (
									<FormInput
										label="User Principal Name"
										labelClassName="text-slate-900"
										className={LIGHT_FIELD}
										value={emailUPN}
										onChange={(e) => {
											setEmailUPN(e.target.value);
											markDirty();
										}}
										placeholder="notifications@yourdomain.com"
										disabled={isSaving}
									/>
								)}

								{(emailProvider === "mailgun" || emailProvider === "mailslurp") && (
									<div className="relative">
										<label
											htmlFor="email-api-key"
											className="mb-2 block text-sm font-medium text-slate-900"
										>
											API Key
										</label>
										<FormInput
											id="email-api-key"
											type={showApiKeys["email"] ? "text" : "password"}
											value={emailKeyInput}
											onChange={(e) => {
												setEmailKeyInput(e.target.value);
												markDirty();
											}}
											placeholder="Enter API key"
											className={`${LIGHT_FIELD} pr-10`}
											disabled={isSaving}
										/>
										<button
											type="button"
											onClick={createToggleVisibilityHandler("email")}
											className="absolute right-2 top-9"
											aria-label="Toggle visibility"
										>
											{showApiKeys["email"] ? (
												<EyeOff className="w-5 h-5" />
											) : (
												<Eye className="w-5 h-5" />
											)}
										</button>
									</div>
								)}

								{emailProvider === "mailgun" && (
									<FormInput
										label="Domain"
										labelClassName="text-slate-900"
										className={LIGHT_FIELD}
										value={emailDomain}
										onChange={(e) => {
											setEmailDomain(e.target.value);
											markDirty();
										}}
										placeholder="sandbox.mailgun.org"
										disabled={isSaving}
									/>
								)}
							</div>
						</div>

						{/* ── System-only sections (admin only) ──────────────────── */}
						{scope === "system" && (
							<>
								{/* Document Extraction Provider */}
								<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
									<div className="flex items-center justify-between mb-4">
										<div className="flex items-center gap-3">
											<FileText className="w-6 h-6 text-orange-400" />
											<div>
												<h3 className="text-lg font-semibold text-slate-900">
													Document Extraction Provider
												</h3>
												<p className="text-sm text-slate-600">
													Backend used by Document Reader nodes to extract text
												</p>
											</div>
										</div>
										<div className="flex items-center gap-2">
											<div
												className={`w-2 h-2 rounded-full ${docExtractionProvider !== "model_ocr" ? "bg-[#0DA931] animate-pulse" : "bg-blue-400"}`}
											/>
											<span className="text-sm text-slate-600">
												{docExtractionProvider === "tika"
													? "Apache Tika"
													: docExtractionProvider === "azure_document_intelligence"
														? "Azure Document Intelligence"
														: "Model OCR (default)"}
											</span>
										</div>
									</div>

									<div className="space-y-4">
										<div>
											<label
												htmlFor="doc-extraction-provider"
												className="mb-2 block text-sm font-medium text-slate-900"
											>
												Extraction Provider
											</label>
											<Dropdown
												value={docExtractionProvider}
												onChange={(v) => {
													setDocExtractionProvider(v);
													markDirty();
												}}
												disabled={isSaving}
												menuAppearance="light"
												width="trigger"
												menuMinWidthPx={260}
												triggerClassName={DROPDOWN_TRIGGER}
												options={[
													{ value: "model_ocr", label: "Model OCR" },
													{ value: "tika", label: "Apache Tika" },
													{
														value: "azure_document_intelligence",
														label: "Azure Document Intelligence",
													},
												]}
											/>
											<p className="mt-2 text-xs text-slate-600">
												Model OCR uses an LLM vision model — accurate but slower. Tika and
												Azure Document Intelligence are faster for structured documents.
											</p>
										</div>

										{docExtractionProvider === "model_ocr" && (
											<>
												<div>
													<label
														htmlFor="model-ocr-deployment"
														className="mb-2 block text-sm font-medium text-slate-900"
													>
														Default OCR Model
													</label>
													<Dropdown
														value={modelOcrDeploymentId}
														onChange={(v) => {
															setModelOcrDeploymentId(v);
															markDirty();
														}}
														disabled={isSaving}
														menuAppearance="light"
														width="trigger"
														menuMinWidthPx={280}
														triggerClassName={DROPDOWN_TRIGGER}
														options={[
															{ value: "", label: "Use environment default" },
															...llmDeployments.map((d) => ({
																value: d.id,
																label: `${d.display_name || d.name} (${d.model_name})`,
															})),
														]}
													/>
													<p className="mt-2 text-xs text-slate-600">
														Select the model deployment used for OCR extraction. Individual File
														Reader nodes can override this default.
													</p>
												</div>
												<div>
													<label
														htmlFor="model-ocr-detail"
														className="mb-2 block text-sm font-medium text-slate-900"
													>
														Vision Detail Level
													</label>
													<Dropdown
														value={modelOcrDetail}
														onChange={(v) => {
															setModelOcrDetail(v);
															markDirty();
														}}
														disabled={isSaving}
														menuAppearance="light"
														width="trigger"
														menuMinWidthPx={260}
														triggerClassName={DROPDOWN_TRIGGER}
														options={[
															{ value: "high", label: "High (best accuracy, more tokens)" },
															{ value: "auto", label: "Auto (model decides)" },
															{ value: "low", label: "Low (faster, fewer tokens)" },
														]}
													/>
													<p className="mt-2 text-xs text-slate-600">
														Controls the image detail level sent to the vision API. Higher detail
														improves accuracy but uses more tokens.
													</p>
												</div>
											</>
										)}

										{/* Tika settings */}
										{docExtractionProvider === "tika" && (
											<div className="space-y-4">
												<FormInput
													label="Server URL"
													labelClassName="text-slate-900"
													className={LIGHT_FIELD}
													value={tikaUrlInput}
													onChange={(e) => {
														setTikaUrlInput(e.target.value);
														markDirty();
													}}
													placeholder="http://tika:9998"
													disabled={isSaving}
												/>
												<div>
													<label
														htmlFor="tika-timeout"
														className="mb-2 block text-sm font-medium text-slate-900"
													>
														Request Timeout (seconds)
													</label>
													<input
														id="tika-timeout"
														type="number"
														min={5}
														max={600}
														value={tikaTimeout}
														onChange={(e) => {
															setTikaTimeout(Number(e.target.value));
															markDirty();
														}}
														disabled={isSaving}
														className={SELECT_LIGHT}
													/>
													<p className="mt-2 text-xs text-slate-600">
														HTTP timeout for requests to the Tika server (default: 60 s).
													</p>
												</div>
											</div>
										)}

										{/* Azure Document Intelligence settings */}
										{docExtractionProvider === "azure_document_intelligence" && (
											<div className="space-y-4">
												<FormInput
													label="Endpoint URL"
													labelClassName="text-slate-900"
													className={LIGHT_FIELD}
													value={azureDiEndpointInput}
													onChange={(e) => {
														setAzureDiEndpointInput(e.target.value);
														markDirty();
													}}
													placeholder="https://your-resource.cognitiveservices.azure.com"
													disabled={isSaving}
												/>
												<div>
													<label
														htmlFor="azure-di-key"
														className="mb-2 block text-sm font-medium text-slate-900"
													>
														API Key
													</label>
													<div className="relative">
														<FormInput
															id="azure-di-key"
															type={showApiKeys["azure_di"] ? "text" : "password"}
															value={azureDiKeyInput}
															onChange={(e) => {
																setAzureDiKeyInput(e.target.value);
																markDirty();
															}}
															placeholder="Leave blank to use Managed Identity"
															className={`${LIGHT_FIELD} pr-10`}
															disabled={isSaving}
														/>
														<button
															type="button"
															onClick={createToggleVisibilityHandler("azure_di")}
															className="absolute right-2 top-2.5"
															aria-label="Toggle visibility"
														>
															{showApiKeys["azure_di"] ? (
																<EyeOff className="w-5 h-5" />
															) : (
																<Eye className="w-5 h-5" />
															)}
														</button>
													</div>
												</div>
												<div className="flex items-center gap-3">
													<input
														type="checkbox"
														id="azure-di-managed-identity"
														checked={azureDiManagedIdentity}
														onChange={(e) => {
															setAzureDiManagedIdentity(e.target.checked);
															markDirty();
														}}
														disabled={isSaving}
														className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-2 focus:ring-orange-500/35"
													/>
													<label
														htmlFor="azure-di-managed-identity"
														className="text-sm text-slate-700"
													>
														Use Azure Managed Identity (ignores API Key)
													</label>
												</div>
												<div>
													<label
														htmlFor="azure-di-model-id"
														className="mb-2 block text-sm font-medium text-slate-900"
													>
														Document Model
													</label>
													<Dropdown
														value={azureDiModelId}
														onChange={(v) => {
															setAzureDiModelId(v);
															markDirty();
														}}
														disabled={isSaving}
														menuAppearance="light"
														width="trigger"
														menuMinWidthPx={300}
														triggerClassName={DROPDOWN_TRIGGER}
														options={[
															{
																value: "prebuilt-read",
																label: "prebuilt-read (general text extraction)",
															},
															{
																value: "prebuilt-layout",
																label: "prebuilt-layout (tables + structure)",
															},
															{
																value: "prebuilt-document",
																label: "prebuilt-document (key-value pairs)",
															},
															{
																value: "prebuilt-invoice",
																label: "prebuilt-invoice (invoices)",
															},
															{
																value: "prebuilt-receipt",
																label: "prebuilt-receipt (receipts)",
															},
														]}
													/>
													<p className="mt-2 text-xs text-slate-600">
														Azure Document Intelligence prebuilt model. Use a custom model ID for
														domain-specific documents.
													</p>
												</div>
											</div>
										)}
									</div>
								</div>

								{/* LangChain / LangSmith */}
								<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
									<div className="flex items-center justify-between mb-4">
										<div className="flex items-center gap-3">
											<Link2 className="w-6 h-6 text-purple-400" />
											<div>
												<h3 className="text-lg font-semibold text-slate-900">
													LangChain / LangSmith
												</h3>
												<p className="text-sm text-slate-600">
													Observability and tracing for LLM applications
												</p>
											</div>
										</div>
										<div className="flex items-center gap-2">
											<div
												className={`w-2 h-2 rounded-full ${config.external_services.langchain.enabled ? "bg-[#0DA931] animate-pulse" : "bg-slate-400"}`}
											/>
											<span className="text-sm text-slate-600">
												{config.external_services.langchain.enabled
													? "Connected"
													: "Not Configured"}
											</span>
										</div>
									</div>

									<div className="space-y-4">
										<div>
											<label
												htmlFor="langchain-api-key"
												className="mb-2 block text-sm font-medium text-slate-900"
											>
												API Key
											</label>
											<div className="relative">
												<FormInput
													id="langchain-api-key"
													type={showApiKeys["langchain"] ? "text" : "password"}
													value={langchainApiKey}
													onChange={(e) => {
														setLangchainApiKey(e.target.value);
														markDirty();
													}}
													placeholder="Enter LangChain API key"
													className={`${LIGHT_FIELD} pr-10`}
													disabled={isSaving}
												/>
												<button
													type="button"
													onClick={createToggleVisibilityHandler("langchain")}
													className="absolute right-2 top-2.5"
													aria-label="Toggle visibility"
												>
													{showApiKeys["langchain"] ? (
														<EyeOff className="w-5 h-5" />
													) : (
														<Eye className="w-5 h-5" />
													)}
												</button>
											</div>
										</div>

										<div className="flex items-center gap-3">
											<input
												type="checkbox"
												id="tracing"
												checked={langchainTracingV2}
												onChange={(e) => {
													setLangchainTracingV2(e.target.checked);
													markDirty();
												}}
												disabled={isSaving}
												className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-2 focus:ring-orange-500/35"
											/>
											<label
												htmlFor="tracing"
												className="text-sm text-slate-700"
											>
												Enable LangChain Tracing V2
											</label>
										</div>

										<FormInput
											label="Project Name"
											labelClassName="text-slate-900"
											className={LIGHT_FIELD}
											value={langchainProject}
											onChange={(e) => {
												setLangchainProject(e.target.value);
												markDirty();
											}}
											placeholder="Project name"
											disabled={isSaving}
										/>
									</div>
								</div>

								{/* Phoenix Observability */}
								<div className="rounded-[4px] border border-slate-200 bg-white p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors hover:border-orange-400">
									<div className="flex items-center justify-between mb-4">
										<div className="flex items-center gap-3">
											<Activity className="h-6 w-6 text-orange-600" />
											<div>
												<h3 className="text-lg font-semibold text-slate-900">
													Phoenix Observability
												</h3>
												<p className="text-sm text-slate-600">
													LLM trace exploration and evaluation via Arize Phoenix
												</p>
											</div>
										</div>
										<div className="flex items-center gap-2">
											<div
												className={`w-2 h-2 rounded-full ${phoenixEnabled && phoenixEndpoint ? "bg-[#0DA931] animate-pulse" : "bg-slate-400"}`}
											/>
											<span className="text-sm text-slate-600">
												{phoenixEnabled && phoenixEndpoint
													? "Connected"
													: "Not Configured"}
											</span>
										</div>
									</div>

									<div className="space-y-4">
										<div className="flex items-center gap-3">
											<input
												type="checkbox"
												id="phoenix-enabled"
												checked={phoenixEnabled}
												onChange={(e) => {
													setPhoenixEnabled(e.target.checked);
													markDirty();
												}}
												disabled={isSaving}
												className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-2 focus:ring-orange-500/35"
											/>
											<label
												htmlFor="phoenix-enabled"
												className="text-sm text-slate-700"
											>
												Enable Phoenix tracing
											</label>
										</div>

										<FormInput
											label="Collector Endpoint"
											labelClassName="text-slate-900"
											className={LIGHT_FIELD}
											value={phoenixEndpoint}
											onChange={(e) => {
												setPhoenixEndpoint(e.target.value);
												markDirty();
											}}
											placeholder="http://phoenix:6006/v1/traces"
											disabled={isSaving}
										/>

										<FormInput
											label="Project Name"
											labelClassName="text-slate-900"
											className={LIGHT_FIELD}
											value={phoenixProjectName}
											onChange={(e) => {
												setPhoenixProjectName(e.target.value);
												markDirty();
											}}
											placeholder="agentic-studio"
											disabled={isSaving}
										/>

										<div>
											<label
												htmlFor="phoenix-api-key"
												className="mb-2 block text-sm font-medium text-slate-900"
											>
												API Key (optional)
											</label>
											<div className="relative">
												<FormInput
													id="phoenix-api-key"
													type={showApiKeys["phoenix"] ? "text" : "password"}
													value={phoenixApiKey}
													onChange={(e) => {
														setPhoenixApiKey(e.target.value);
														markDirty();
													}}
													placeholder="Required only for Phoenix Cloud"
													className={`${LIGHT_FIELD} pr-10`}
													disabled={isSaving}
												/>
												<button
													type="button"
													onClick={createToggleVisibilityHandler("phoenix")}
													className="absolute right-2 top-2.5"
													aria-label="Toggle visibility"
												>
													{showApiKeys["phoenix"] ? (
														<EyeOff className="w-5 h-5" />
													) : (
														<Eye className="w-5 h-5" />
													)}
												</button>
											</div>
										</div>

										<FormInput
											label="UI URL"
											labelClassName="text-slate-900"
											className={LIGHT_FIELD}
											value={phoenixUiUrl}
											onChange={(e) => {
												setPhoenixUiUrl(e.target.value);
												markDirty();
											}}
											placeholder="http://localhost:6006"
											disabled={isSaving}
										/>

										{/* Default supplementary evaluations */}
										<div className="space-y-2">
											<p
												className="text-sm font-medium"
											>
												Supplementary Evaluations (Defaults)
											</p>
											<p className="text-xs text-slate-600">
												Select which Phoenix evaluations run by default. Per-run settings can override these.
											</p>
											<div className="flex items-center gap-3">
												<input
													type="checkbox"
													id="phoenix-eval-faithfulness"
													checked={phoenixEvalFaithfulnessEnabled}
													onChange={(e) => {
														setPhoenixEvalFaithfulnessEnabled(e.target.checked);
														markDirty();
													}}
													disabled={isSaving}
													className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-2 focus:ring-orange-500/35"
												/>
												<label
													htmlFor="phoenix-eval-faithfulness"
													className="text-sm text-slate-700"
												>
													Faithfulness
												</label>
												<span className="text-xs text-slate-600">
													Checks output against retrieved context for hallucinations
												</span>
											</div>
											<div className="flex items-center gap-3">
												<input
													type="checkbox"
													id="phoenix-eval-tool-selection"
													checked={phoenixEvalToolSelectionEnabled}
													onChange={(e) => {
														setPhoenixEvalToolSelectionEnabled(e.target.checked);
														markDirty();
													}}
													disabled={isSaving}
													className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-2 focus:ring-orange-500/35"
												/>
												<label
													htmlFor="phoenix-eval-tool-selection"
													className="text-sm text-slate-700"
												>
													Tool Selection
												</label>
												<span className="text-xs text-slate-600">
													Evaluates whether the right tools were chosen
												</span>
											</div>
											<div className="flex items-center gap-3">
												<input
													type="checkbox"
													id="phoenix-eval-llm-judge"
													checked={phoenixEvalLlmJudgeEnabled}
													onChange={(e) => {
														setPhoenixEvalLlmJudgeEnabled(e.target.checked);
														markDirty();
													}}
													disabled={isSaving}
													className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-2 focus:ring-orange-500/35"
												/>
												<label
													htmlFor="phoenix-eval-llm-judge"
													className="text-sm text-slate-700"
												>
													LLM Judge
												</label>
												<span className="text-xs text-slate-600">
													Phoenix LLM judge for comparison with built-in judge
												</span>
											</div>
										</div>

										<div className="flex items-center gap-3">
											<input
												type="checkbox"
												id="phoenix-eval-penalty"
												checked={phoenixEvalPenaltyEnabled}
												onChange={(e) => {
													setPhoenixEvalPenaltyEnabled(e.target.checked);
													markDirty();
												}}
												disabled={isSaving}
												className="h-4 w-4 rounded border-slate-300 text-orange-600 focus:ring-2 focus:ring-orange-500/35"
											/>
											<label
												htmlFor="phoenix-eval-penalty"
												className="text-sm text-slate-700"
											>
												Enable eval quality penalty
											</label>
											<span className="text-xs text-slate-600">
												Deduct 10 pts when faithfulness score &lt; 0.3
											</span>
										</div>
									</div>
								</div>
							</>
						)}
					</div>
				)}
			</div>
		</div>
	);
}
