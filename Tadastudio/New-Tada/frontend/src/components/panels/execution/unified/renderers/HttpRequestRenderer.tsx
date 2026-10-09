import {
	ArrowRight,
	ChevronRight,
	Clock,
	Code,
	Copy,
	Download,
	Eye,
	EyeOff,
	Key,
	RefreshCw,
	Shield,
	Terminal,
} from "lucide-react";
import React, { useState } from "react";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import type { HttpRequestExecution } from "../types/execution.types";
import {
	copyToClipboard,
	formatDuration,
	getMethodColor,
	getStatusColor,
	maskSensitiveData,
} from "../utils/formatters";
import { BaseRenderer, BaseRendererProps } from "./BaseRenderer";

export class HttpRequestRenderer extends BaseRenderer<HttpRequestExecution> {
	state = {
		showSecrets: false,
		copiedItem: null as string | null,
	};

	getViewModes() {
		return [
			{
				key: "request",
				label: "Request",
				icon: <ArrowRight className="w-4 h-4" />,
			},
			{
				key: "response",
				label: "Response",
				icon: <Code className="w-4 h-4" />,
			},
			{ key: "curl", label: "cURL", icon: <Terminal className="w-4 h-4" /> },
			{ key: "config", label: "Config", icon: <Key className="w-4 h-4" /> },
			{ key: "raw", label: "Raw Data" },
		];
	}

	renderViewMode(mode: string, execution: HttpRequestExecution) {
		switch (mode) {
			case "request":
				return this.renderRequest(execution);
			case "response":
				return this.renderResponse(execution);
			case "curl":
				return this.renderCurl(execution);
			case "config":
				return this.renderConfig(execution);
			default:
				// Return raw JSON view
				return (
					<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	handleCopy = async (text: string, itemName: string) => {
		const success = await copyToClipboard(text);
		if (success) {
			this.setState({ copiedItem: itemName });
			setTimeout(() => this.setState({ copiedItem: null }), 2000);
		}
	};

	renderRequest(execution: HttpRequestExecution) {
		const { showSecrets, copiedItem } = this.state;

		return (
			<div className="space-y-4">
				{/* URL and Method */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
					<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-2">
						Endpoint
					</h4>
					<div className="flex items-start gap-3">
						<span
							className={`font-bold mt-1 ${getMethodColor(execution.request.method)}`}
						>
							{execution.request.method}
						</span>
						<code className="flex-1 text-sm bg-[color:var(--color-surface)] px-3 py-2 rounded break-all">
							{execution.request.url}
						</code>
						<button
							onClick={() => this.handleCopy(execution.request.url, "url")}
							className="p-2 hover:bg-[color:var(--color-border)] rounded transition-colors"
							title="Copy URL"
						>
							<Copy
								className={`w-4 h-4 ${copiedItem === "url" ? "text-[#0DA931]" : "text-[color:var(--color-text-muted)]"}`}
							/>
						</button>
					</div>
				</div>

				{/* Headers */}
				{execution.request.headers &&
					Object.keys(execution.request.headers).length > 0 && (
						<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
							<div className="flex items-center justify-between mb-3">
								<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)]">
									Request Headers
								</h4>
								<button
									onClick={() => this.setState({ showSecrets: !showSecrets })}
									className="p-1 hover:bg-[color:var(--color-border)] rounded transition-colors"
									title={
										showSecrets ? "Hide sensitive data" : "Show sensitive data"
									}
								>
									{showSecrets ? (
										<EyeOff className="w-4 h-4 text-[color:var(--color-text-muted)]" />
									) : (
										<Eye className="w-4 h-4 text-[color:var(--color-text-muted)]" />
									)}
								</button>
							</div>
							<div className="space-y-2">
								{Object.entries(execution.request.headers).map(
									([key, value]) => (
										<div key={key} className="flex items-center gap-2 text-sm">
											<span className="text-[color:var(--color-text-muted)] font-mono">
												{key}:
											</span>
											<span className="text-slate-900 font-mono">
												{maskSensitiveData(value, showSecrets)}
											</span>
										</div>
									),
								)}
							</div>
						</div>
					)}

				{/* Request Body */}
				{execution.request.body && (
					<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
						<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-3">
							Request Body
						</h4>
						<div className="bg-[color:var(--color-surface)] rounded-lg p-3 max-h-[300px] overflow-auto">
							<JsonViewerEnhanced data={execution.request.body} />
						</div>
					</div>
				)}
			</div>
		);
	}

	renderResponse(execution: HttpRequestExecution) {
		return (
			<div className="space-y-4">
				{/* Status */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
					<div className="flex items-center justify-between">
						<span
							className={`text-lg font-medium ${getStatusColor(execution.response.status_code)}`}
						>
							Status: {execution.response.status_code || "Error"}
						</span>
						{execution.response.elapsed !== undefined && (
							<div className="flex items-center gap-2 text-sm text-[color:var(--color-text-muted)]">
								<Clock className="w-4 h-4" />
								{formatDuration(execution.response.elapsed)}
							</div>
						)}
					</div>

					{execution.response.error && (
						<div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
							<p className="text-red-400 text-sm">{execution.response.error}</p>
						</div>
					)}
				</div>

				{/* Response Headers */}
				{execution.response.headers &&
					Object.keys(execution.response.headers).length > 0 && (
						<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
							<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-3">
								Response Headers
							</h4>
							<div className="space-y-2">
								{Object.entries(execution.response.headers).map(
									([key, value]) => (
										<div key={key} className="flex items-center gap-2 text-sm">
											<span className="text-[color:var(--color-text-muted)] font-mono">
												{key}:
											</span>
											<span className="text-slate-900 font-mono break-all">
												{value}
											</span>
										</div>
									),
								)}
							</div>
						</div>
					)}

				{/* Response Body */}
				{execution.response.data && (
					<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
						<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-3">
							Response Body
						</h4>
						<div className="bg-[color:var(--color-surface)] rounded-lg p-3 max-h-[400px] overflow-auto">
							<JsonViewerEnhanced data={execution.response.data} />
						</div>
					</div>
				)}
			</div>
		);
	}

	generateCurlCommand(execution: HttpRequestExecution) {
		const request = execution.request || {};
		const config = execution.config || {};
		const { showSecrets } = this.state;
		const method = request.method || "GET";
		const url = request.url || "URL_NOT_AVAILABLE";
		const headers = request.headers || {};
		const body = request.body;

		let curl = `curl -X ${method}`;

		curl += ` '${url}'`;

		if (headers && Object.keys(headers).length > 0) {
			Object.entries(headers).forEach(([key, value]) => {
				const maskedValue = maskSensitiveData(String(value), showSecrets);
				curl += ` \\\n  -H '${key}: ${maskedValue}'`;
			});
		}

		if (body && ["POST", "PUT", "PATCH"].includes(method)) {
			const bodyStr =
				typeof body === "string" ? body : JSON.stringify(body, null, 2);
			curl += ` \\\n  -d '${bodyStr}'`;
		}

		if (config) {
			if (config.follow_redirects === false) curl += " \\\n  -L";
			if (config.verify_ssl === false) curl += " \\\n  -k";
			if (config.timeout_seconds)
				curl += ` \\\n  --max-time ${config.timeout_seconds}`;
		}

		return curl;
	}

	renderCurl(execution: HttpRequestExecution) {
		const curlCommand = this.generateCurlCommand(execution);
		const { copiedItem } = this.state;

		return (
			<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
				<div className="flex items-center justify-between mb-3">
					<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)]">
						cURL Command
					</h4>
					<button
						onClick={() => this.handleCopy(curlCommand, "curl")}
						className="flex items-center gap-2 px-3 py-1 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 rounded-lg transition-colors"
					>
						<Copy
							className={`w-3 h-3 ${copiedItem === "curl" ? "text-[#0DA931]" : ""}`}
						/>
						{copiedItem === "curl" ? "Copied!" : "Copy"}
					</button>
				</div>
				<pre className="bg-[color:var(--color-bg-secondary)] rounded-lg p-4 overflow-x-auto">
					<code className="text-sm text-[color:var(--color-text-secondary)] font-mono">
						{curlCommand}
					</code>
				</pre>
			</div>
		);
	}

	renderConfig(execution: HttpRequestExecution) {
		const config = execution.config || {};

		return (
			<div className="space-y-4">
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl p-4">
					<h4 className="text-sm font-medium text-[color:var(--color-text-secondary)] mb-3">
						Request Configuration
					</h4>
					<div className="space-y-3">
						{config.auth_type && config.auth_type !== "none" && (
							<div className="flex items-center gap-2">
								<Key className="w-4 h-4 text-purple-400" />
								<span className="text-sm text-[color:var(--color-text-muted)]">
									Authentication:
								</span>
								<span className="text-sm text-slate-700">{config.auth_type}</span>
							</div>
						)}
						{config.timeout_seconds && (
							<div className="flex items-center gap-2">
								<Clock className="w-4 h-4 text-purple-400" />
								<span className="text-sm text-[color:var(--color-text-muted)]">
									Timeout:
								</span>
								<span className="text-sm text-slate-700">
									{config.timeout_seconds}s
								</span>
							</div>
						)}
						{config.max_retries !== undefined && (
							<div className="flex items-center gap-2">
								<RefreshCw className="w-4 h-4 text-purple-400" />
								<span className="text-sm text-[color:var(--color-text-muted)]">
									Max Retries:
								</span>
								<span className="text-sm text-slate-700">{config.max_retries}</span>
							</div>
						)}
						<div className="flex items-center gap-2">
							<ChevronRight className="w-4 h-4 text-purple-400" />
							<span className="text-sm text-[color:var(--color-text-muted)]">
								Follow Redirects:
							</span>
							<span className="text-sm text-slate-700">
								{config.follow_redirects !== false ? "Yes" : "No"}
							</span>
						</div>
						<div className="flex items-center gap-2">
							<Shield className="w-4 h-4 text-purple-400" />
							<span className="text-sm text-[color:var(--color-text-muted)]">
								Verify SSL:
							</span>
							<span className="text-sm text-slate-700">
								{config.verify_ssl !== false ? "Yes" : "No"}
							</span>
						</div>
					</div>
				</div>
			</div>
		);
	}
}
