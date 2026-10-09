"use client";

import {
	Activity,
	Check,
	CheckCircle,
	Copy,
	Eye,
	EyeOff,
	Globe,
	Key,
	Radio,
	Upload,
	X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";

import { useNotification } from "@/contexts/NotificationContext";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import { api } from "@/lib/api";
import { runtimeConfig } from "@/lib/runtime-config";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface HttpExecutionModalProps {
	isOpen: boolean;
	onClose: () => void;
	graphName: string;
	workflowId: string | undefined;
	onPublishedChange?: (published: boolean) => void;
	httpListenerEnabled: boolean;
	httpListenerConnected: boolean;
	onToggleHttpListener: () => void;
}

type ModalView = "loading" | "unpublished" | "ready";
type CopiedField = "curl" | "endpoint" | "token" | null;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HttpExecutionModal({
	isOpen,
	onClose,
	graphName,
	workflowId,
	onPublishedChange,
	httpListenerEnabled,
	httpListenerConnected,
	onToggleHttpListener,
}: HttpExecutionModalProps) {
	const router = useRouter();
	const { showSuccess, showError } = useNotification();
	const dialogRef = useFocusTrap<HTMLDivElement>(isOpen);
	useEscapeKey(onClose, isOpen);

	const [mounted, setMounted] = useState(false);
	const [view, setView] = useState<ModalView>("loading");
	const [baseUrl, setBaseUrl] = useState("");
	const [copiedField, setCopiedField] = useState<CopiedField>(null);

	const [isPublishing, setIsPublishing] = useState(false);

	const [triggerToken, setTriggerToken] = useState<string | null>(null);
	const [tokenError, setTokenError] = useState<string | null>(null);

	useEffect(() => {
		setMounted(true);
		return () => setMounted(false);
	}, []);

	useEffect(() => {
		if (isOpen) {
			document.body.style.overflow = "hidden";
		} else {
			document.body.style.overflow = "";
		}
		return () => {
			document.body.style.overflow = "";
		};
	}, [isOpen]);

	const fetchTriggerToken = useCallback(async () => {
		try {
			setTokenError(null);
			const result = await api.getWorkflowHttpTriggerToken(graphName);
			setTriggerToken(result.token);
		} catch {
			setTokenError("Could not retrieve workflow trigger token");
			setTriggerToken(null);
		}
	}, [graphName]);

	useEffect(() => {
		if (!isOpen || !graphName) return;

		let cancelled = false;
		setView("loading");

		const fetchData = async () => {
			try {
				const [pubResult, apiBaseUrl] = await Promise.all([
					api
						.getWorkflowPublication(graphName)
						.catch(() => ({ success: false })),
					runtimeConfig.getApiBaseUrl(),
				]);

				if (cancelled) return;

				const resolvedBase = apiBaseUrl || window.location.origin;
				setBaseUrl(resolvedBase);

				const isPublished =
					pubResult && pubResult.is_published === true;
				onPublishedChange?.(!!isPublished);

				if (!isPublished) {
					setView("unpublished");
					return;
				}

				await fetchTriggerToken();

				setView("ready");
			} catch {
				if (!cancelled) {
					setView("unpublished");
				}
			}
		};

		fetchData();
		return () => {
			cancelled = true;
		};
	}, [isOpen, graphName, fetchTriggerToken]);

	const identifier = workflowId || encodeURIComponent(graphName);

	const endpointUrl = useMemo(
		() => `${baseUrl}/api/http-execution/trigger/${identifier}`,
		[baseUrl, identifier],
	);

	const curlCommand = useMemo(() => {
		const tokenValue = triggerToken || "YOUR_TOKEN";
		return `curl -X POST "${endpointUrl}" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${tokenValue}" \\
  -d '{"message": "Your input here", "async_mode": false}'`;
	}, [endpointUrl, triggerToken]);

	const copyToClipboard = useCallback(
		(text: string, field: CopiedField) => {
			navigator.clipboard.writeText(text).then(() => {
				setCopiedField(field);
				showSuccess("Copied to clipboard");
				setTimeout(() => setCopiedField(null), 2000);
			});
		},
		[showSuccess],
	);

	const handlePublishWorkflow = useCallback(async () => {
		setIsPublishing(true);
		try {
			await api.publishWorkflow(graphName, {
				description: `Published API endpoint for ${graphName}`,
				require_authentication: true,
				rate_limit: { requests_per_minute: 60 },
			});
			onPublishedChange?.(true);
			showSuccess("Workflow published successfully");

			const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
			const resolvedBase = apiBaseUrl || window.location.origin;
			setBaseUrl(resolvedBase);

			await fetchTriggerToken();
			setView("ready");
		} catch (err) {
			showError(
				err instanceof Error
					? err.message
					: "Failed to publish workflow",
			);
		} finally {
			setIsPublishing(false);
		}
	}, [graphName, onPublishedChange, showSuccess, showError, fetchTriggerToken]);

	const handleGoToPublish = useCallback(() => {
		onClose();
		router.push("/publish");
	}, [onClose, router]);

	if (!mounted || !isOpen) return null;

	return createPortal(
		<div
			className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
			onClick={onClose}
			role="presentation"
		>
			<div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />

			<div
				ref={dialogRef}
				className="relative w-full max-w-2xl animate-fadeIn overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_30px_80px_rgba(4,7,17,0.15)]"
				onClick={(e) => e.stopPropagation()}
				role="dialog"
				aria-modal="true"
				aria-labelledby="http-exec-dialog-title"
			>
				<div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-orange-500/60" />

				{/* Header — Workflow Management style */}
				<div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-5">
					<div className="flex items-center gap-3">
						<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-orange-200 bg-orange-100">
							<Globe className="h-5 w-5 text-orange-600" aria-hidden />
						</div>
						<div>
							<h2
								id="http-exec-dialog-title"
								className="text-lg font-semibold tracking-tight text-slate-900"
							>
								HTTP API
							</h2>
							<p className="text-xs text-slate-500">
								Trigger this workflow via REST API
							</p>
						</div>
					</div>
					<button
						type="button"
						onClick={onClose}
						className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 transition-colors hover:border-orange-400 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
						aria-label="Close"
					>
						<X className="h-4 w-4" />
					</button>
				</div>

				<div className="custom-scrollbar max-h-[70vh] overflow-y-auto px-6 py-5">
					{view === "loading" && <LoadingView />}
					{view === "unpublished" && (
						<UnpublishedView
							onPublish={handlePublishWorkflow}
							onGoToPublish={handleGoToPublish}
							isPublishing={isPublishing}
						/>
					)}
					{view === "ready" && (
						<ReadyView
							endpointUrl={endpointUrl}
							curlCommand={curlCommand}
							triggerToken={triggerToken}
							tokenError={tokenError}
							onRefreshToken={fetchTriggerToken}
							copiedField={copiedField}
							onCopy={copyToClipboard}
							httpListenerEnabled={httpListenerEnabled}
							httpListenerConnected={httpListenerConnected}
							onToggleHttpListener={onToggleHttpListener}
							graphName={graphName}
						/>
					)}
				</div>
			</div>
		</div>,
		document.body,
	);
}

// ---------------------------------------------------------------------------
// Sub-views
// ---------------------------------------------------------------------------

function LoadingView() {
	return (
		<div className="flex flex-col items-center justify-center gap-4 py-16">
			<div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500" />
			<p className="text-sm text-slate-700">Checking workflow status...</p>
		</div>
	);
}

function UnpublishedView({
	onPublish,
	onGoToPublish,
	isPublishing,
}: {
	onPublish: () => void;
	onGoToPublish: () => void;
	isPublishing: boolean;
}) {
	return (
		<div className="flex flex-col items-center gap-6 py-8 text-center">
			<div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm">
				<Upload className="h-8 w-8 text-orange-600" />
			</div>
			<div className="space-y-2">
				<h3 className="text-xl font-semibold text-slate-900">
					Publish Your Workflow
				</h3>
				<p className="max-w-sm text-sm text-slate-600">
					This workflow must be published before it can be accessed via the HTTP
					API. Publishing makes it available as a REST endpoint.
				</p>
			</div>
			<button
				type="button"
				onClick={onPublish}
				disabled={isPublishing}
				className="inline-flex items-center gap-2 rounded-[4px] border border-orange-500 bg-orange-500 px-6 py-3 text-sm font-semibold text-white transition-colors hover:border-orange-600 hover:bg-orange-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/30 disabled:pointer-events-none disabled:opacity-50"
			>
				{isPublishing ? (
					<>
						<div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
						Publishing...
					</>
				) : (
					<>
						<Upload className="h-4 w-4" />
						Publish Now
					</>
				)}
			</button>
			<button
				type="button"
				onClick={onGoToPublish}
				className="rounded text-xs text-slate-600 transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
			>
				Advanced publish settings
			</button>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Ready view
// ---------------------------------------------------------------------------

interface ReadyViewProps {
	endpointUrl: string;
	curlCommand: string;
	triggerToken: string | null;
	tokenError: string | null;
	onRefreshToken: () => void;
	copiedField: CopiedField;
	onCopy: (text: string, field: CopiedField) => void;
	httpListenerEnabled: boolean;
	httpListenerConnected: boolean;
	onToggleHttpListener: () => void;
	graphName: string;
}

function ReadyView({
	endpointUrl,
	curlCommand,
	triggerToken,
	tokenError,
	onRefreshToken,
	copiedField,
	onCopy,
	httpListenerEnabled,
	httpListenerConnected,
	onToggleHttpListener,
	graphName,
}: ReadyViewProps) {
	const [showToken, setShowToken] = useState(false);

	const maskedToken = triggerToken
		? `${triggerToken.slice(0, 12)}${"*".repeat(20)}`
		: "";

	return (
		<div className="space-y-6">
			{/* Endpoint URL */}
			<section className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-slate-600">
					Endpoint
				</h4>
				<div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
					<span className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-mono font-semibold text-blue-800">
						POST
					</span>
					<code className="min-w-0 flex-1 truncate text-xs font-mono text-slate-800">
						{endpointUrl}
					</code>
					<CopyButton
						onClick={() => onCopy(endpointUrl, "endpoint")}
						copied={copiedField === "endpoint"}
						label="Copy endpoint URL"
					/>
				</div>
			</section>

			{/* API Token */}
			<section className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-slate-600">
					API Token
				</h4>

				{tokenError ? (
					<div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3">
						<p className="text-xs text-red-800">{tokenError}</p>
						<button
							type="button"
							onClick={onRefreshToken}
							className="mt-2 text-xs font-medium text-red-900 underline decoration-red-300 underline-offset-2 transition-colors hover:text-red-950"
						>
							Retry
						</button>
					</div>
				) : triggerToken ? (
					<div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
						<div className="flex items-center gap-2">
							<Key className="h-4 w-4 shrink-0 text-slate-500" />
							<code className="min-w-0 flex-1 truncate text-xs font-mono text-slate-800">
								{showToken ? triggerToken : maskedToken}
							</code>
							<button
								type="button"
								onClick={() => setShowToken((prev) => !prev)}
								className="shrink-0 rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 transition-all hover:border-orange-300 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
								aria-label={showToken ? "Hide token" : "Show token"}
							>
								{showToken ? (
									<EyeOff className="h-3.5 w-3.5" />
								) : (
									<Eye className="h-3.5 w-3.5" />
								)}
							</button>
							<CopyButton
								onClick={() => onCopy(triggerToken, "token")}
								copied={copiedField === "token"}
								label="Copy API token"
							/>
						</div>
						<p className="mt-2 text-[0.65rem] text-slate-600">
							This token is unique to this workflow. Pass it in the
							Authorization: Bearer header.
						</p>
					</div>
				) : (
					<div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
						<div className="h-4 w-4 animate-spin rounded-full border-2 border-slate-200 border-t-orange-500" />
						<span className="text-xs text-slate-600">Loading token...</span>
					</div>
				)}
			</section>

			{/* cURL command */}
			<section className="space-y-3">
				<div className="flex items-center justify-between">
					<h4 className="text-xs font-semibold capitalize text-slate-600">
						cURL Command
					</h4>
					<CopyButton
						onClick={() => onCopy(curlCommand, "curl")}
						copied={copiedField === "curl"}
						label="Copy cURL command"
						showLabel
					/>
				</div>
				<pre className="overflow-x-auto rounded-2xl border border-slate-200 bg-slate-50 p-5">
					<code className="whitespace-pre-wrap break-all text-xs font-mono leading-relaxed text-slate-800">
						{curlCommand}
					</code>
				</pre>
			</section>

			{/* HTTP Listener */}
			<section className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-slate-600">
					Live Listener
				</h4>
				<div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-colors hover:border-orange-200">
					<div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
						<div className="flex items-start gap-3">
							<div
								className={cn(
									"flex h-10 w-10 items-center justify-center rounded-xl border",
									httpListenerConnected
										? "border-emerald-200 bg-emerald-50 text-emerald-700"
										: "border-slate-200 bg-slate-50 text-slate-600",
								)}
							>
								<Radio
									className={cn(
										"h-5 w-5",
										httpListenerConnected && "animate-pulse",
									)}
								/>
							</div>
							<div className="space-y-1">
								<p className="text-[0.6rem] capitalize text-slate-500">
									Live Connection
								</p>
								<h5 className="text-sm font-semibold text-slate-900">
									HTTP Execution Listener
								</h5>
								<p className="text-xs text-slate-600">
									{httpListenerEnabled
										? httpListenerConnected
											? "Listening for HTTP-triggered executions in real time."
											: "Connecting to the listener endpoint..."
										: "Enable live updates when executions are triggered via HTTP."}
								</p>
							</div>
						</div>
						<button
							type="button"
							onClick={onToggleHttpListener}
							className={cn(
								"inline-flex h-10 shrink-0 items-center gap-2 rounded-xl border px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25",
								httpListenerEnabled
									? "border-emerald-300 bg-emerald-50 text-emerald-900 hover:border-emerald-400 hover:bg-emerald-100 hover:text-emerald-950"
									: "border-slate-200 bg-white text-slate-800 hover:border-orange-300 hover:text-slate-900",
							)}
						>
							{httpListenerEnabled ? (
								<>
									<div className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
									Listening
								</>
							) : (
								<>
									<Activity className="h-4 w-4" />
									Enable
								</>
							)}
						</button>
					</div>
					{httpListenerEnabled && httpListenerConnected && (
						<div className="mt-4 flex items-center gap-2 text-xs text-emerald-800">
							<CheckCircle className="h-3.5 w-3.5 shrink-0 text-emerald-600" />
							<span>
								Connected and monitoring executions for{" "}
								<span className="font-mono text-slate-700">{graphName}</span>
							</span>
						</div>
					)}
				</div>
			</section>

			{/* Request / Response format */}
			<section className="space-y-3">
				<h4 className="text-xs font-semibold capitalize text-slate-600">
					Request &amp; Response
				</h4>
				<div className="grid gap-4 sm:grid-cols-2">
					<div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
						<p className="mb-2 text-[0.6rem] capitalize text-slate-500">
							Request Body
						</p>
						<pre className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
							<code className="text-xs font-mono text-slate-800">{`{
  "message": "Your input",
  "async_mode": false,
  "timeout": 300
}`}</code>
						</pre>
					</div>
					<div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
						<p className="mb-2 text-[0.6rem] capitalize text-slate-500">
							Response
						</p>
						<pre className="overflow-x-auto rounded-lg border border-slate-200 bg-slate-50 p-3">
							<code className="text-xs font-mono text-slate-800">{`{
  "success": true,
  "execution_id": "...",
  "status": "completed",
  "final_output": "..."
}`}</code>
						</pre>
					</div>
				</div>
			</section>
		</div>
	);
}

// ---------------------------------------------------------------------------
// Copy button helper
// ---------------------------------------------------------------------------

function CopyButton({
	onClick,
	copied,
	label,
	showLabel = false,
}: {
	onClick: () => void;
	copied: boolean;
	label: string;
	showLabel?: boolean;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-600 transition-all hover:border-orange-300 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/25"
			aria-label={label}
		>
			{copied ? (
				<Check className="h-3 w-3 text-emerald-600" />
			) : (
				<Copy className="h-3 w-3" />
			)}
			{showLabel && (
				<span>{copied ? "Copied" : "Copy"}</span>
			)}
		</button>
	);
}
