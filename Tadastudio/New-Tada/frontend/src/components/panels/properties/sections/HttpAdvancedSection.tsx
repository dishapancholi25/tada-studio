"use client";

import { Activity, Clock, Key, Settings, Shield } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import FormLabel from "@/components/ui/FormLabel";
import FormTextarea from "@/components/ui/FormTextarea";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";

interface HttpAdvancedSectionProps {
	timeoutSeconds: number;
	onTimeoutSecondsChange: (timeout: number) => void;
	maxRetries: number;
	onMaxRetriesChange: (retries: number) => void;
	retryDelay: number;
	onRetryDelayChange: (delay: number) => void;
	retryOnStatus: number[];
	onRetryOnStatusChange: (codes: number[]) => void;
	proxyConfig: Record<string, string>;
	onProxyConfigChange: (config: Record<string, string>) => void;
	rateLimit: Record<string, number>;
	onRateLimitChange: (limit: Record<string, number>) => void;
	circuitBreakerConfig: Record<string, number>;
	onCircuitBreakerConfigChange: (config: Record<string, number>) => void;
	requestSigning: Record<string, string>;
	onRequestSigningChange: (signing: Record<string, string>) => void;
	preRequestScript: string;
	onPreRequestScriptChange: (script: string) => void;
	webhookUrl: string;
	onWebhookUrlChange: (url: string) => void;
	cacheConfig: Record<string, any>;
	onCacheConfigChange: (config: Record<string, any>) => void;
}

export default function HttpAdvancedSection({
	timeoutSeconds,
	onTimeoutSecondsChange,
	maxRetries,
	onMaxRetriesChange,
	retryDelay,
	onRetryDelayChange,
	retryOnStatus,
	onRetryOnStatusChange,
	proxyConfig,
	onProxyConfigChange,
	rateLimit,
	onRateLimitChange,
	circuitBreakerConfig,
	onCircuitBreakerConfigChange,
	requestSigning,
	onRequestSigningChange,
	preRequestScript,
	onPreRequestScriptChange,
	webhookUrl,
	onWebhookUrlChange,
	cacheConfig,
	onCacheConfigChange,
}: HttpAdvancedSectionProps) {
	const handleRetryOnStatusChange = (
		event: React.ChangeEvent<HTMLInputElement>,
	) => {
		onRetryOnStatusChange(
			event.target.value
				.split(",")
				.map((value) => Number(value.trim()))
				.filter((num) => !Number.isNaN(num)),
		);
	};

	const updateProxyConfig = (key: string, value: string) => {
		const next = { ...proxyConfig };
		if (value.trim()) {
			next[key] = value.trim();
		} else {
			delete next[key];
		}
		onProxyConfigChange(next);
	};

	const updateRateLimit = (key: string, value: number | string) => {
		const next = { ...rateLimit };
		const numValue = typeof value === "string" ? Number(value) : value;
		if (Number.isFinite(numValue) && numValue > 0) {
			next[key] = numValue;
		} else {
			delete next[key];
		}
		onRateLimitChange(next);
	};

	const updateCircuitBreakerConfig = (key: string, value: number | string) => {
		const next = { ...circuitBreakerConfig };
		const numValue = typeof value === "string" ? Number(value) : value;
		if (Number.isFinite(numValue) && numValue > 0) {
			next[key] = numValue;
		} else {
			delete next[key];
		}
		onCircuitBreakerConfigChange(next);
	};

	const updateRequestSigning = (key: string, value: string) => {
		const next = { ...requestSigning };
		if (value) {
			next[key] = value;
		} else {
			delete next[key];
		}
		onRequestSigningChange(next);
	};

	const updateCacheConfig = (value: number | string) => {
		const next = { ...cacheConfig };
		const numValue = typeof value === "string" ? Number(value) : value;
		if (Number.isFinite(numValue) && numValue > 0) {
			next.ttl = numValue;
		} else {
			delete next.ttl;
		}
		onCacheConfigChange(next);
	};

	return (
		<div className="space-y-6">
			{/* Timeout & Retry Section */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
							<Clock className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-gray-900">
								Timeout & Retry Strategy
							</h3>
							<p className="text-sm text-gray-600">
								Configure timeout and automatic retry behavior
							</p>
						</div>
					</div>
					<div className="rounded-[4px] border border-orange-400 bg-white px-3 py-1">
						<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
							{timeoutSeconds}s timeout
						</span>
					</div>
				</div>

				<div className="mt-6 space-y-4">
					<div className="grid gap-4 md:grid-cols-3">
						<FormInput
							label="Timeout (seconds)"
							type="number"
							value={timeoutSeconds}
							onChange={(e) =>
								onTimeoutSecondsChange(Number(e.target.value) || 30)
							}
							hint="Maximum time to wait for response"
						/>
						<FormInput
							label="Max retries"
							type="number"
							value={maxRetries}
							onChange={(e) => onMaxRetriesChange(Number(e.target.value) || 0)}
							hint="Number of retry attempts"
						/>
						<FormInput
							label="Retry delay (seconds)"
							type="number"
							value={retryDelay}
							onChange={(e) => onRetryDelayChange(Number(e.target.value) || 1)}
							hint="Delay between retries"
						/>
					</div>
					<FormInput
						label="Retry on status codes"
						value={retryOnStatus.join(", ")}
						onChange={handleRetryOnStatusChange}
						placeholder="429, 500, 502, 503, 504"
						hint="Comma-separated list of HTTP status codes that should trigger a retry"
					/>
				</div>
			</div>

			{/* Network Controls Section */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
							<Activity className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-gray-900">
								Network Controls
							</h3>
							<p className="text-sm text-gray-600">
								Proxy, rate limiting, and circuit breaker settings
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					{/* Proxy Configuration */}
					<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
						<div className="flex items-start gap-3 mb-4">
							<div className="p-2 rounded-[4px] border border-gray-200 bg-white">
								<Activity className="h-4 w-4 text-orange-600" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-gray-900">
										Proxy Configuration
									</h5>
									<InfoTooltip text="Route requests through a proxy server" />
								</div>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Configure HTTP and HTTPS proxies
								</p>
							</div>
						</div>
						<div className="space-y-4">
							<div className="grid gap-4 md:grid-cols-2">
								<FormInput
									label="HTTP proxy"
									value={proxyConfig.http_proxy || ""}
									onChange={(e) =>
										updateProxyConfig("http_proxy", e.target.value)
									}
									placeholder="http://proxy.internal:8080"
								/>
								<FormInput
									label="HTTPS proxy"
									value={proxyConfig.https_proxy || ""}
									onChange={(e) =>
										updateProxyConfig("https_proxy", e.target.value)
									}
									placeholder="https://proxy.internal:8443"
								/>
							</div>
							<div className="grid gap-4 md:grid-cols-2">
								<FormInput
									label="No proxy (comma-separated)"
									value={proxyConfig.no_proxy || ""}
									onChange={(e) =>
										updateProxyConfig("no_proxy", e.target.value)
									}
									placeholder="localhost,127.0.0.1"
								/>
								<FormInput
									label="Proxy username (optional)"
									value={proxyConfig.proxy_username || ""}
									onChange={(e) =>
										updateProxyConfig("proxy_username", e.target.value)
									}
									placeholder="Username"
								/>
							</div>
							{proxyConfig.proxy_username && (
								<FormInput
									label="Proxy password"
									type="password"
									value={proxyConfig.proxy_password || ""}
									onChange={(e) =>
										updateProxyConfig("proxy_password", e.target.value)
									}
									placeholder="Password"
								/>
							)}
						</div>
					</div>

					{/* Rate Limiting */}
					<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
						<div className="flex items-start gap-3 mb-4">
							<div className="p-2 rounded-[4px] bg-[color:var(--color-primary)]/15 border border-[color:var(--color-primary)]/30">
								<Clock className="w-4 h-4 text-[color:var(--color-primary)]" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-gray-900">
										Rate Limiting
									</h5>
									<InfoTooltip text="Limit the number of requests per time period" />
								</div>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Throttle request frequency
								</p>
							</div>
						</div>
						<div className="grid gap-4 md:grid-cols-2">
							<FormInput
								label="Requests / second"
								type="number"
								value={rateLimit.requests_per_second ?? ""}
								onChange={(e) =>
									updateRateLimit("requests_per_second", e.target.value)
								}
								placeholder="10"
							/>
							<FormInput
								label="Requests / minute"
								type="number"
								value={rateLimit.requests_per_minute ?? ""}
								onChange={(e) =>
									updateRateLimit("requests_per_minute", e.target.value)
								}
								placeholder="100"
							/>
						</div>
					</div>

					{/* Circuit Breaker */}
					<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
						<div className="flex items-start gap-3 mb-4">
							<div className="p-2 rounded-[4px] bg-[color:var(--color-primary)]/15 border border-[color:var(--color-primary)]/30">
								<Shield className="w-4 h-4 text-[color:var(--color-primary)]" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-gray-900">
										Circuit Breaker
									</h5>
									<InfoTooltip text="Automatically disable requests after repeated failures to prevent cascading failures" />
								</div>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Prevent cascading failures
								</p>
							</div>
						</div>
						<div className="grid gap-4 md:grid-cols-3">
							<FormInput
								label="Failure threshold"
								type="number"
								value={circuitBreakerConfig.failure_threshold ?? ""}
								onChange={(e) =>
									updateCircuitBreakerConfig(
										"failure_threshold",
										e.target.value,
									)
								}
								placeholder="5"
								hint="Max failures before opening"
							/>
							<FormInput
								label="Timeout (ms)"
								type="number"
								value={circuitBreakerConfig.timeout ?? ""}
								onChange={(e) =>
									updateCircuitBreakerConfig("timeout", e.target.value)
								}
								placeholder="3000"
								hint="Request timeout"
							/>
							<FormInput
								label="Reset timeout (ms)"
								type="number"
								value={circuitBreakerConfig.reset_timeout ?? ""}
								onChange={(e) =>
									updateCircuitBreakerConfig("reset_timeout", e.target.value)
								}
								placeholder="10000"
								hint="Time before retry"
							/>
						</div>
					</div>
				</div>
			</div>

			{/* Signing & Automation Section */}
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
							<Key className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-gray-900">
								Signing & Automation
							</h3>
							<p className="text-sm text-gray-600">
								Request signing, pre-request scripts, and webhooks
							</p>
						</div>
					</div>
				</div>

				<div className="mt-6 space-y-6">
					{/* Request Signing */}
					<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
						<div className="flex items-start gap-3 mb-4">
							<div className="p-2 rounded-[4px] bg-orange-500/15 border border-orange-500/30">
								<Key className="w-4 h-4 text-orange-400" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-gray-900">
										Request Signing
									</h5>
									<InfoTooltip text="Sign requests with HMAC or AWS Signature V4" />
								</div>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Cryptographic request signatures
								</p>
							</div>
						</div>
						<div className="space-y-4">
							<div>
								<FormLabel htmlFor="signing-algorithm-select">
									Signing Algorithm
								</FormLabel>
								<Dropdown
									value={requestSigning.algorithm || ""}
									onChange={(value) => updateRequestSigning("algorithm", value)}
									options={[
										{
											value: "",
											label: "None",
											description: "Do not sign outbound requests",
										},
										{
											value: "hmac-sha256",
											label: "HMAC-SHA256",
											description: "Attach an HMAC signature header",
										},
										{
											value: "aws-v4",
											label: "AWS Signature V4",
											description: "Use AWS request signing",
										},
										{
											value: "custom",
											label: "Custom",
											description: "Provide your own signing scheme",
										},
									]}
									placeholder="Select algorithm"
								/>
							</div>
							{requestSigning.algorithm && (
								<FormInput
									label="Signing Secret"
									type="password"
									value={requestSigning.secret || ""}
									onChange={(e) =>
										updateRequestSigning("secret", e.target.value)
									}
									placeholder="Secret or API key"
								/>
							)}
						</div>
					</div>

					{/* Pre-request Script */}
					<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
						<div className="flex items-start gap-3 mb-4">
							<div className="p-2 rounded-[4px] bg-purple-500/15 border border-purple-500/30">
								<Settings className="w-4 h-4 text-purple-400" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-gray-900">
										Pre-request Script
									</h5>
									<InfoTooltip text="JavaScript code to run before each request to modify headers, body, or parameters" />
								</div>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Modify request before sending
								</p>
							</div>
						</div>
						<FormTextarea
							label=""
							value={preRequestScript}
							onChange={(e) => onPreRequestScriptChange(e.target.value)}
							rows={6}
							placeholder={`// You can mutate the request config here\nrequest.headers['X-Correlation-Id'] = crypto.randomUUID();`}
							resizable
						/>
					</div>

					{/* Webhook URL */}
					<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
						<div className="flex items-start gap-3 mb-4">
							<div className="p-2 rounded-[4px] bg-blue-500/15 border border-blue-500/30">
								<Activity className="w-4 h-4 text-blue-400" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-gray-900">
										Webhook URL
									</h5>
									<InfoTooltip text="Send response data to a webhook endpoint after request completes" />
								</div>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Callback endpoint for async notifications
								</p>
							</div>
						</div>
						<FormInput
							label=""
							value={webhookUrl}
							onChange={(e) => onWebhookUrlChange(e.target.value)}
							placeholder="https://webhook.example.com/callback"
						/>
					</div>

					{/* Cache Configuration */}
					<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
						<div className="flex items-start gap-3 mb-4">
							<div className="p-2 rounded-[4px] bg-[#0DA931]/15 border border-[#0DA931]/30">
								<Clock className="w-4 h-4 text-[#0DA931]" />
							</div>
							<div className="flex-1">
								<div className="flex items-center gap-2">
									<h5 className="text-sm font-semibold text-gray-900">
										Response Caching
									</h5>
									<InfoTooltip text="Cache GET responses to reduce redundant API calls" />
								</div>
								<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
									Only applies to GET requests
								</p>
							</div>
						</div>
						<FormInput
							label="Cache TTL (seconds)"
							type="number"
							value={cacheConfig.ttl ?? ""}
							onChange={(e) => updateCacheConfig(e.target.value)}
							placeholder="300"
							hint="Leave blank to disable caching"
						/>
					</div>
				</div>
			</div>

			{/* Summary Badge */}
			<div className="p-4 bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/30 rounded-[4px]">
				<div className="flex items-center gap-2 mb-2">
					<Settings className="w-4 h-4 text-[color:var(--color-primary)]" />
					<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
						Advanced Configuration Summary
					</span>
				</div>
				<div className="flex flex-wrap gap-2">
					<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
						Timeout: {timeoutSeconds}s
					</span>
					<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
						Max Retries: {maxRetries}
					</span>
					{Object.keys(proxyConfig).length > 0 && (
						<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
							Proxy: Configured
						</span>
					)}
					{Object.keys(rateLimit).length > 0 && (
						<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
							Rate Limit: Active
						</span>
					)}
					{requestSigning.algorithm && (
						<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
							Signing: {requestSigning.algorithm.replace(/\b\w/g, c => c.toUpperCase())}
						</span>
					)}
				</div>
			</div>
		</div>
	);
}
