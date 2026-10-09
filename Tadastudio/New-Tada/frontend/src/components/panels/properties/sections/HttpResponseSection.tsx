"use client";

import { Activity, CheckCircle, FileJson, XCircle } from "lucide-react";
import Dropdown from "@/components/ui/Dropdown";
import FormInput from "@/components/ui/FormInput";
import FormLabel from "@/components/ui/FormLabel";
import FormTextarea from "@/components/ui/FormTextarea";
import InfoTooltip from "@/components/ui/InfoTooltipPortal";
import Toggle from "@/components/ui/Toggle";

interface HttpResponseSectionProps {
	responseFormat: string;
	onResponseFormatChange: (format: string) => void;
	errorHandling: string;
	onErrorHandlingChange: (handling: string) => void;
	successStatusCodes: number[];
	onSuccessStatusCodesChange: (codes: number[]) => void;
	acceptHeaders: Record<string, string>;
	onAcceptHeadersChange: (headers: Record<string, string>) => void;
	extractPath: string;
	onExtractPathChange: (path: string) => void;
	responseTransform: string;
	onResponseTransformChange: (transform: string) => void;
	encoding: string;
	onEncodingChange: (encoding: string) => void;
	followRedirects: boolean;
	onFollowRedirectsChange: (follow: boolean) => void;
	maxRedirects: number;
	onMaxRedirectsChange: (max: number) => void;
	verifySSL: boolean;
	onVerifySSLChange: (verify: boolean) => void;
	compression: boolean;
	onCompressionChange: (compression: boolean) => void;
	cookieJar: boolean;
	onCookieJarChange: (cookieJar: boolean) => void;
}

export default function HttpResponseSection({
	responseFormat,
	onResponseFormatChange,
	errorHandling,
	onErrorHandlingChange,
	successStatusCodes,
	onSuccessStatusCodesChange,
	acceptHeaders,
	onAcceptHeadersChange,
	extractPath,
	onExtractPathChange,
	responseTransform,
	onResponseTransformChange,
	encoding,
	onEncodingChange,
	followRedirects,
	onFollowRedirectsChange,
	maxRedirects,
	onMaxRedirectsChange,
	verifySSL,
	onVerifySSLChange,
	compression,
	onCompressionChange,
	cookieJar,
	onCookieJarChange,
}: HttpResponseSectionProps) {
	const handleSuccessStatusCodesChange = (
		event: React.ChangeEvent<HTMLInputElement>,
	) => {
		onSuccessStatusCodesChange(
			event.target.value
				.split(",")
				.map((value) => Number(value.trim()))
				.filter((num) => !Number.isNaN(num)),
		);
	};

	const handleAcceptHeaderChange = (
		event: React.ChangeEvent<HTMLInputElement>,
	) => {
		const value = event.target.value.trim();
		const next = { ...acceptHeaders };
		if (value) {
			next.accept = value;
		} else {
			delete next.accept;
		}
		onAcceptHeadersChange(next);
	};

	return (
		<div className="space-y-6">
			<div className="rounded-[4px] border border-gray-200 bg-white p-6 shadow-sm">
				{/* Section header with icon */}
				<div className="flex items-start justify-between gap-4 border-b border-gray-200 pb-5">
					<div className="flex items-center gap-3">
						<div className="flex h-12 w-12 items-center justify-center rounded-[4px] border border-gray-200 bg-white text-orange-600 shadow-sm">
							<Activity className="h-6 w-6" />
						</div>
						<div>
							<h3 className="text-xl font-semibold text-gray-900">
								Response Behavior
							</h3>
							<p className="text-sm text-gray-600">
								Control response handling, parsing, and transformation
							</p>
						</div>
					</div>
				</div>

				{/* Section content */}
				<div className="mt-6 space-y-6">
					{/* Response Format & Error Handling */}
					<div className="space-y-5">
						<div className="flex items-center gap-2 mb-1">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-gray-900">
								Response Processing
							</h4>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-[color:var(--color-primary)]/15 border border-[color:var(--color-primary)]/30">
									<FileJson className="w-4 h-4 text-[color:var(--color-primary)]" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Response Format
										</h5>
										<InfoTooltip text="Choose how the response payload should be parsed" />
									</div>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
										How to interpret the response body
									</p>
								</div>
							</div>
							<Dropdown
								value={responseFormat}
								onChange={onResponseFormatChange}
								options={[
									{
										value: "auto",
										label: "Auto-detect",
										description:
											"Attempt to infer JSON, text, or binary automatically",
									},
									{
										value: "json",
										label: "JSON",
										description: "Force JSON parsing for structured payloads",
									},
									{
										value: "text",
										label: "Text",
										description: "Return the raw response as text",
									},
									{
										value: "xml",
										label: "XML",
										description: "Parse XML into an object",
									},
									{
										value: "binary",
										label: "Binary",
										description: "Treat the payload as binary (Base64 encoded)",
									},
								]}
								placeholder="Select response format"
							/>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-[color:var(--color-primary)]/15 border border-[color:var(--color-primary)]/30">
									<XCircle className="w-4 h-4 text-[color:var(--color-primary)]" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Error Handling
										</h5>
										<InfoTooltip text="Decide what happens when the server responds with an error" />
									</div>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
										How to handle failed requests
									</p>
								</div>
							</div>
							<Dropdown
								value={errorHandling}
								onChange={onErrorHandlingChange}
								options={[
									{
										value: "fail",
										label: "Fail",
										description: "Stop the workflow if this request fails",
									},
									{
										value: "continue",
										label: "Continue",
										description: "Capture the error but continue the workflow",
									},
									{
										value: "retry",
										label: "Retry",
										description:
											"Retry using the configured retry policy when errors occur",
									},
								]}
								placeholder="Select behavior"
							/>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-[color:var(--color-primary)]/15 border border-[color:var(--color-primary)]/30">
									<CheckCircle className="w-4 h-4 text-[color:var(--color-primary)]" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Success Status Codes
										</h5>
										<InfoTooltip text="HTTP status codes that should be treated as successful responses" />
									</div>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
										Comma-separated list
									</p>
								</div>
							</div>
							<FormInput
								label=""
								value={successStatusCodes.join(", ")}
								onChange={handleSuccessStatusCodesChange}
								placeholder="200, 201, 202, 204"
							/>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<FormInput
								label="Accept Header (optional)"
								value={acceptHeaders.accept || ""}
								onChange={handleAcceptHeaderChange}
								placeholder="application/json"
								hint="Specify the content type(s) you want to accept from the server"
							/>
						</div>
					</div>

					{/* Response Shaping */}
					<div className="space-y-5">
						<div className="flex items-center gap-2 mb-1">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-gray-900">
								Response Shaping
							</h4>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-purple-500/15 border border-purple-500/30">
									<FileJson className="w-4 h-4 text-purple-400" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Extract Path
										</h5>
										<InfoTooltip text="Use dot notation to extract a specific value from the JSON payload" />
									</div>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
										JSONPath or dot notation
									</p>
								</div>
							</div>
							<FormInput
								label=""
								value={extractPath}
								onChange={(e) => onExtractPathChange(e.target.value)}
								placeholder="data.results[0].value"
								hint="Example: data.users[0].name extracts the first user's name"
							/>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-purple-500/15 border border-purple-500/30">
									<FileJson className="w-4 h-4 text-purple-400" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Response Transform
										</h5>
										<InfoTooltip text="JavaScript function to transform the response data before returning it" />
									</div>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
										JavaScript expression or template
									</p>
								</div>
							</div>
							<FormTextarea
								label=""
								value={responseTransform}
								onChange={(e) => onResponseTransformChange(e.target.value)}
								rows={6}
								placeholder={`// Return a JavaScript expression or JSON template\nreturn { id: response.data.id, status: response.status };`}
								resizable
							/>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="flex items-start gap-3 mb-4">
								<div className="p-2 rounded-[4px] bg-[color:var(--color-primary)]/15 border border-[color:var(--color-primary)]/30">
									<FileJson className="w-4 h-4 text-[color:var(--color-primary)]" />
								</div>
								<div className="flex-1">
									<div className="flex items-center gap-2">
										<h5 className="text-sm font-semibold text-gray-900">
											Encoding
										</h5>
										<InfoTooltip text="Select the character encoding for the request body" />
									</div>
									<p className="text-xs text-[color:var(--color-text-muted)] mt-1">
										Character encoding
									</p>
								</div>
							</div>
							<Dropdown
								value={encoding}
								onChange={onEncodingChange}
								options={[
									{
										value: "utf-8",
										label: "UTF-8",
										description: "Standard Unicode encoding",
									},
									{
										value: "latin1",
										label: "Latin-1",
										description: "ISO-8859-1 encoding",
									},
									{
										value: "utf-16",
										label: "UTF-16",
										description: "UTF-16 encoding",
									},
									{
										value: "ascii",
										label: "ASCII",
										description: "ASCII encoding",
									},
								]}
								placeholder="Select encoding"
							/>
						</div>
					</div>

					{/* Connection Options */}
					<div className="space-y-5">
						<div className="flex items-center gap-2 mb-1">
							<h4 className="text-sm font-semibold capitalize tracking-wide text-gray-900">
								Connection Options
							</h4>
						</div>

						<div className="p-5 rounded-[4px] border border-gray-200 bg-slate-50">
							<div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
								<div className="flex items-center justify-between gap-4 p-3 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/30">
									<div className="flex-1">
										<h5 className="text-sm font-semibold text-gray-900">
											Follow Redirects
										</h5>
										<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
											Automatically follow 3xx redirects
										</p>
									</div>
									<Toggle
										checked={followRedirects}
										onChange={onFollowRedirectsChange}
										size="sm"
									/>
								</div>

								<div className="flex items-center justify-between gap-4 p-3 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/30">
									<div className="flex-1">
										<h5 className="text-sm font-semibold text-gray-900">
											Verify SSL
										</h5>
										<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
											Validate SSL certificates
										</p>
									</div>
									<Toggle
										checked={verifySSL}
										onChange={onVerifySSLChange}
										size="sm"
									/>
								</div>

								<div className="flex items-center justify-between gap-4 p-3 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/30">
									<div className="flex-1">
										<h5 className="text-sm font-semibold text-gray-900">
											Compression
										</h5>
										<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
											Enable gzip/deflate compression
										</p>
									</div>
									<Toggle
										checked={compression}
										onChange={onCompressionChange}
										size="sm"
									/>
								</div>

								<div className="flex items-center justify-between gap-4 p-3 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/30">
									<div className="flex-1">
										<h5 className="text-sm font-semibold text-gray-900">
											Cookie Jar
										</h5>
										<p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">
											Persist cookies across requests
										</p>
									</div>
									<Toggle
										checked={cookieJar}
										onChange={onCookieJarChange}
										size="sm"
									/>
								</div>
							</div>

							{followRedirects && (
								<div className="mt-4 pt-4 border-t border-[color:var(--color-border)]/30">
									<FormInput
										label="Max Redirects"
										type="number"
										value={maxRedirects}
										onChange={(e) =>
											onMaxRedirectsChange(Number(e.target.value) || 1)
										}
										hint="Maximum number of redirects to follow (default: 10)"
									/>
								</div>
							)}
						</div>
					</div>

					{/* Summary Badge */}
					<div className="p-4 bg-[color:var(--color-primary)]/10 border border-[color:var(--color-primary)]/30 rounded-[4px]">
						<div className="flex items-center gap-2 mb-2">
							<Activity className="w-4 h-4 text-[color:var(--color-primary)]" />
							<span className="text-xs font-semibold capitalize tracking-wide text-gray-900">
								Current Response Settings
							</span>
						</div>
						<div className="flex flex-wrap gap-2">
							<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
								Format: {responseFormat.charAt(0).toUpperCase() + responseFormat.slice(1)}
							</span>
							<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
								Error: {errorHandling.charAt(0).toUpperCase() + errorHandling.slice(1)}
							</span>
							<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
								Redirects: {followRedirects ? "Yes" : "No"}
							</span>
							<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
								SSL: {verifySSL ? "Verify" : "Skip"}
							</span>
							<span className="px-3 py-1 rounded-[4px] bg-[color:var(--color-surface)]/60 border border-[color:var(--color-border)]/40 text-xs font-semibold text-gray-900">
								Compression: {compression ? "Enabled" : "Disabled"}
							</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}
