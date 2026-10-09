"use client";

import { Key, Lock, Shield } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import FormLabel from "@/components/ui/FormLabel";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

interface HttpAuthSectionProps {
	authType: string;
	onAuthTypeChange: (authType: string) => void;
	authConfig: Record<string, string>;
	onAuthConfigChange: (config: Record<string, string>) => void;
	oauth2Config: Record<string, string>;
	onOauth2ConfigChange: (config: Record<string, string>) => void;
	certificatePath: string;
	onCertificatePathChange: (path: string) => void;
}

export default function HttpAuthSection({
	authType,
	onAuthTypeChange,
	authConfig,
	onAuthConfigChange,
	oauth2Config,
	onOauth2ConfigChange,
	certificatePath,
	onCertificatePathChange,
}: HttpAuthSectionProps) {
	const updateAuthConfig = (key: string, value: string) => {
		onAuthConfigChange({ ...authConfig, [key]: value });
	};

	const updateOauth2Config = (key: string, value: string) => {
		onOauth2ConfigChange({ ...oauth2Config, [key]: value });
	};

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				{/* Section header with icon */}
				<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
							<Key className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-gray-900">
								Authentication
							</h3>
							<p className="text-sm text-gray-600">
								Configure how this request authenticates with the target service
							</p>
						</div>
					</div>
					{authType !== "none" && (
						<div className="rounded-[4px] border border-orange-400 bg-white px-3 py-1">
							<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
								{authType.replace(/_/g, " ")}
							</span>
						</div>
					)}
				</div>

				{/* Section content */}
				<div className="mt-6 space-y-6">
					{/* Auth Type Selector */}
					<div className="space-y-2">
						<div className="flex items-center gap-2">
							<FormLabel htmlFor="auth-type-select">
								Authentication Type
							</FormLabel>
							<InfoTooltip text="Select the authentication method required by your API" />
						</div>
						<Dropdown
							value={authType}
							onChange={onAuthTypeChange}
							options={[
								{
									value: "none",
									label: "None",
									description: "No authentication",
									icon: <Shield className="w-4 h-4 text-gray-400" />,
								},
								{
									value: "bearer",
									label: "Bearer Token",
									description: "Authorization header with Bearer token",
									icon: <Key className="w-4 h-4 text-orange-400" />,
								},
								{
									value: "api_key_header",
									label: "API Key (Header)",
									description: "Custom header with API key",
									icon: <Key className="w-4 h-4 text-blue-400" />,
								},
								{
									value: "api_key_query",
									label: "API Key (Query)",
									description: "Query parameter with API key",
									icon: <Key className="w-4 h-4 text-cyan-400" />,
								},
								{
									value: "basic",
									label: "Basic Auth",
									description: "Username and password",
									icon: <Lock className="w-4 h-4 text-[#0DA931]" />,
								},
								{
									value: "digest",
									label: "Digest Auth",
									description: "Digest authentication",
									icon: <Lock className="w-4 h-4 text-emerald-400" />,
								},
								{
									value: "oauth2",
									label: "OAuth 2.0",
									description: "OAuth2 client credentials",
									icon: <Shield className="w-4 h-4 text-purple-400" />,
								},
								{
									value: "custom_token",
									label: "Custom Token",
									description: "Custom authorization scheme",
									icon: <Key className="w-4 h-4 text-yellow-400" />,
								},
								{
									value: "certificate",
									label: "Client Certificate",
									description: "Mutual TLS authentication",
									icon: <Shield className="w-4 h-4 text-red-400" />,
								},
							]}
							placeholder="Select authentication type"
						/>
					</div>

					{/* Auth Configuration Fields */}
					{authType === "bearer" && (
						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-orange-500/15 border border-orange-500/30">
									<Key className="w-4 h-4 text-orange-400" />
								</div>
								<div className="flex-1">
									<h5 className="text-sm font-semibold text-gray-900">
										Bearer Token Configuration
									</h5>
									<p className="mt-1 text-xs text-gray-600">
										Sent as: Authorization: Bearer YOUR_TOKEN
									</p>
								</div>
							</div>
							<FormInput
								label="Bearer Token"
								type="password"
								value={authConfig.token || ""}
								onChange={(e) => updateAuthConfig("token", e.target.value)}
								placeholder="Enter token"
							/>
						</div>
					)}

					{authType === "custom_token" && (
						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-yellow-500/15 border border-yellow-500/30">
									<Key className="w-4 h-4 text-yellow-400" />
								</div>
								<div className="flex-1">
									<h5 className="text-sm font-semibold text-gray-900">
										Custom Token Configuration
									</h5>
									<p className="mt-1 text-xs text-gray-600">
										Sent as: Authorization: YOUR_SCHEME YOUR_TOKEN
									</p>
								</div>
							</div>
							<div className="grid gap-4 sm:grid-cols-2">
								<FormInput
									label="Authorization Scheme"
									value={authConfig.scheme || ""}
									onChange={(e) => updateAuthConfig("scheme", e.target.value)}
									placeholder="e.g., Token, ApiKey"
								/>
								<FormInput
									label="Token Value"
									type="password"
									value={authConfig.token || ""}
									onChange={(e) => updateAuthConfig("token", e.target.value)}
									placeholder="Enter token value"
								/>
							</div>
						</div>
					)}

					{authType === "api_key_header" && (
						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-blue-500/15 border border-blue-500/30">
									<Key className="w-4 h-4 text-blue-400" />
								</div>
								<div className="flex-1">
									<h5 className="text-sm font-semibold text-gray-900">
										API Key Header Configuration
									</h5>
									<p className="mt-1 text-xs text-gray-600">
										Sent as a custom HTTP header
									</p>
								</div>
							</div>
							<div className="grid gap-4 sm:grid-cols-2">
								<FormInput
									label="Header Name"
									value={authConfig.header_name || ""}
									onChange={(e) =>
										updateAuthConfig("header_name", e.target.value)
									}
									placeholder="e.g., X-API-Key"
								/>
								<FormInput
									label="API Key"
									type="password"
									value={authConfig.key || ""}
									onChange={(e) => updateAuthConfig("key", e.target.value)}
									placeholder="Enter API key"
								/>
							</div>
						</div>
					)}

					{authType === "api_key_query" && (
						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-cyan-500/15 border border-cyan-500/30">
									<Key className="w-4 h-4 text-cyan-400" />
								</div>
								<div className="flex-1">
									<h5 className="text-sm font-semibold text-gray-900">
										API Key Query Parameter Configuration
									</h5>
									<p className="mt-1 text-xs text-gray-600">
										Appended to URL as a query parameter
									</p>
								</div>
							</div>
							<div className="grid gap-4 sm:grid-cols-2">
								<FormInput
									label="Parameter Name"
									value={authConfig.param_name || ""}
									onChange={(e) =>
										updateAuthConfig("param_name", e.target.value)
									}
									placeholder="e.g., api_key"
								/>
								<FormInput
									label="API Key"
									type="password"
									value={authConfig.key || ""}
									onChange={(e) => updateAuthConfig("key", e.target.value)}
									placeholder="Enter API key"
								/>
							</div>
						</div>
					)}

					{(authType === "basic" || authType === "digest") && (
						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-[#0DA931]/15 border border-[#0DA931]/30">
									<Lock className="w-4 h-4 text-[#0DA931]" />
								</div>
								<div className="flex-1">
									<h5 className="text-sm font-semibold text-gray-900">
										{authType === "basic" ? "Basic" : "Digest"} Authentication
										Configuration
									</h5>
									<p className="mt-1 text-xs text-gray-600">
										{authType === "basic"
											? "Credentials sent Base64 encoded"
											: "Challenge-response authentication"}
									</p>
								</div>
							</div>
							<div className="grid gap-4 sm:grid-cols-2">
								<FormInput
									label="Username"
									value={authConfig.username || ""}
									onChange={(e) => updateAuthConfig("username", e.target.value)}
									placeholder="Enter username"
								/>
								<FormInput
									label="Password"
									type="password"
									value={authConfig.password || ""}
									onChange={(e) => updateAuthConfig("password", e.target.value)}
									placeholder="Enter password"
								/>
							</div>
						</div>
					)}

					{authType === "oauth2" && (
						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-purple-500/15 border border-purple-500/30">
									<Shield className="w-4 h-4 text-purple-400" />
								</div>
								<div className="flex-1">
									<h5 className="text-sm font-semibold text-gray-900">
										OAuth 2.0 Configuration
									</h5>
									<p className="mt-1 text-xs text-gray-600">
										Client credentials flow for service-to-service
										authentication
									</p>
								</div>
							</div>
							<div className="space-y-4">
								<div className="grid gap-4 sm:grid-cols-2">
									<FormInput
										label="Client ID"
										value={oauth2Config.client_id || ""}
										onChange={(e) =>
											updateOauth2Config("client_id", e.target.value)
										}
										placeholder="Client ID"
									/>
									<FormInput
										label="Client Secret"
										type="password"
										value={oauth2Config.client_secret || ""}
										onChange={(e) =>
											updateOauth2Config("client_secret", e.target.value)
										}
										placeholder="Client Secret"
									/>
								</div>
								<FormInput
									label="Token URL"
									value={oauth2Config.token_url || ""}
									onChange={(e) =>
										updateOauth2Config("token_url", e.target.value)
									}
									placeholder="https://auth.example.com/oauth/token"
								/>
								<FormInput
									label="Scope (space-separated)"
									value={oauth2Config.scope || ""}
									onChange={(e) => updateOauth2Config("scope", e.target.value)}
									placeholder="read write"
								/>
							</div>
						</div>
					)}

					{authType === "certificate" && (
						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-red-500/15 border border-red-500/30">
									<Shield className="w-4 h-4 text-red-400" />
								</div>
								<div className="flex-1">
									<h5 className="text-sm font-semibold text-gray-900">
										Client Certificate Configuration
									</h5>
									<p className="mt-1 text-xs text-gray-600">
										Mutual TLS (mTLS) authentication with client certificate
									</p>
								</div>
							</div>
							<FormInput
								label="Certificate Path"
								value={certificatePath}
								onChange={(e) => onCertificatePathChange(e.target.value)}
								placeholder="/path/to/client.pem"
								hint="Path to the client certificate file (.pem, .crt, or .p12)"
							/>
						</div>
					)}

					{authType === "none" && (
						<div className="rounded-[4px] border border-dashed border-gray-300 bg-white p-6 text-center">
							<Shield className="mx-auto mb-3 h-12 w-12 text-gray-400" />
							<h5 className="mb-1 text-sm font-semibold text-gray-900">
								No Authentication Selected
							</h5>
							<p className="text-xs text-gray-600">
								The request will be sent without authentication headers. Select
								an authentication type above if your API requires it.
							</p>
						</div>
					)}

					{/* Current Configuration Summary */}
					{authType !== "none" && (
						<div className="rounded-[4px] border border-orange-400 bg-white p-4">
							<div className="mb-2 flex items-center gap-2">
								<Key className="h-4 w-4 text-orange-600" />
								<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
									Authentication Status
								</span>
							</div>
							<div className="flex flex-wrap gap-2">
								<span className="rounded-[4px] border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-900">
									Type: {authType.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
								</span>
								{authType === "oauth2" && oauth2Config.client_id && (
									<span className="rounded-[4px] border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-900">
										Client ID: {oauth2Config.client_id}
									</span>
								)}
								{(authType === "basic" || authType === "digest") &&
									authConfig.username && (
										<span className="rounded-[4px] border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-900">
											Username: {authConfig.username}
										</span>
									)}
								{authType === "api_key_header" && authConfig.header_name && (
									<span className="rounded-[4px] border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-900">
										Header: {authConfig.header_name}
									</span>
								)}
								{authType === "api_key_query" && authConfig.param_name && (
									<span className="rounded-[4px] border border-gray-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-gray-900">
										Parameter: {authConfig.param_name}
									</span>
								)}
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
