"use client";

import { formatDistanceToNow } from "date-fns";
import {
	ArrowLeft,
	ArrowRight,
	Braces,
	Check,
	Clock,
	Copy,
	ExternalLink,
	FileText,
	Hash,
	Play,
	X,
	XCircle,
	Zap,
	DollarSign,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { GraphExecution } from "@/types/api";
import SimpleMarkdown from "../../utils/SimpleMarkdown";
import {
	extractResultDrawerData,
	formatCost,
	formatDuration,
	formatTokens,
	type NodeOutput,
	type ResultDrawerData,
} from "./resultDrawerUtils";

interface ResultDrawerProps {
	isOpen: boolean;
	execution: GraphExecution | null;
	graphName: string;
	onClose: () => void;
	onRunAgain: () => void;
	onOpenTrace: () => void;
}

export default function ResultDrawer({
	isOpen,
	execution,
	graphName,
	onClose,
	onRunAgain,
	onOpenTrace,
}: ResultDrawerProps) {
	const [copied, setCopied] = useState(false);
	const [showRaw, setShowRaw] = useState(false);

	useEffect(() => {
		if (!isOpen) return;

		const handleKeyDown = (e: KeyboardEvent) => {
			if (e.key === "Escape") {
				e.stopPropagation();
				onClose();
			}
		};

		window.addEventListener("keydown", handleKeyDown);
		return () => window.removeEventListener("keydown", handleKeyDown);
	}, [isOpen, onClose]);

	const data = useMemo<ResultDrawerData | null>(() => {
		if (!execution) return null;
		return extractResultDrawerData(execution);
	}, [execution]);

	const handleCopyOutput = useCallback(async () => {
		let text: string;
		if (showRaw) {
			if (!data?.rawJson) return;
			text = data.rawJson;
		} else {
			if (!data?.outputs.length) return;
			text = data.outputs
				.map((o) =>
					data.outputs.length > 1
						? `## ${o.nodeName}\n\n${o.response}`
						: o.response,
				)
				.join("\n\n---\n\n");
		}
		try {
			await navigator.clipboard.writeText(text);
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		} catch (err) {
			console.error("Failed to copy output:", err);
		}
	}, [data?.outputs, data?.rawJson, showRaw]);

	if (!isOpen || !execution || !data) return null;

	const isFailed = data.status === "failed";

	return (
		<>
			<div
				className="animate-fadeIn fixed inset-0 z-[55] bg-black/50"
				onClick={onClose}
				aria-hidden="true"
			/>

			<aside className="animate-slideIn fixed inset-y-0 right-0 z-[56] flex min-w-[600px] w-[85vw] max-w-[1400px] flex-col border-l border-gray-200 bg-white shadow-[0_24px_80px_rgba(15,23,42,0.12)]">
				<DrawerHeader data={data} graphName={graphName} onClose={onClose} />

				<div className="custom-scrollbar flex-1 space-y-6 overflow-y-auto bg-slate-50 px-8 py-6">
					<MetricsStrip data={data} onOpenTrace={onOpenTrace} />

					<InputSection input={data.input} />

					{isFailed ? (
						<ErrorSection errorMessage={data.errorMessage} />
					) : (
						<OutputSection
							outputs={data.outputs}
							rawJson={data.rawJson}
							showRaw={showRaw}
							onToggleRaw={() => setShowRaw((v) => !v)}
							copied={copied}
							onCopy={handleCopyOutput}
						/>
					)}
				</div>

				<ActionBar
					onOpenTrace={onOpenTrace}
					onRunAgain={onRunAgain}
					hasTraceId={!!data.dbExecutionId}
				/>
			</aside>
		</>
	);
}

function DrawerHeader({
	data,
	graphName,
	onClose,
}: {
	data: ResultDrawerData;
	graphName: string;
	onClose: () => void;
}) {
	const isSuccess = data.status === "completed";
	const isFailed = data.status === "failed";

	const statusLabel = isSuccess
		? "Completed"
		: isFailed
			? "Failed"
			: "Stopped";
	const statusClasses = isSuccess
		? "border-emerald-300 bg-white text-emerald-800"
		: isFailed
			? "border-red-300 bg-white text-red-800"
			: "border-amber-300 bg-white text-amber-900";

	const timestampLabel = data.timestamp
		? formatDistanceToNow(new Date(data.timestamp), { addSuffix: true })
		: null;

	return (
		<div className="flex-none border-b border-gray-200 bg-white">
			<div className="flex flex-wrap items-start justify-between gap-4 px-8 pb-4 pt-5">
				<div className="flex min-w-0 items-start gap-3">
					<div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-gray-200 bg-white shadow-sm">
						<FileText className="h-5 w-5 text-orange-600" aria-hidden />
					</div>
					<div className="min-w-0">
						<div className="mb-2 flex flex-wrap items-center gap-2">
							<span
								className={`inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-medium ${statusClasses}`}
							>
								{statusLabel}
							</span>
							{timestampLabel && (
								<span className="font-mono text-xs text-gray-500">
									{timestampLabel}
								</span>
							)}
						</div>
						<h2 className="text-lg font-semibold tracking-tight text-gray-900">
							Workflow Result
						</h2>
						<p className="text-sm text-gray-600">{graphName}</p>
					</div>
				</div>
				<button
					type="button"
					onClick={onClose}
					className="shrink-0 rounded-lg border border-gray-200 bg-white p-2 text-gray-600 transition-colors hover:border-orange-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400/40"
					aria-label="Close result drawer"
				>
					<X className="h-5 w-5" />
				</button>
			</div>
		</div>
	);
}

function MetricsStrip({
	data,
	onOpenTrace,
}: {
	data: ResultDrawerData;
	onOpenTrace: () => void;
}) {
	const metrics = [
		{
			icon: Clock,
			label: "Duration",
			value: formatDuration(data.metrics.durationSeconds),
		},
		{
			icon: Zap,
			label: "Tokens",
			value: formatTokens(data.metrics.totalTokens),
		},
		{
			icon: DollarSign,
			label: "Est. Cost",
			value: formatCost(data.metrics.estimatedCost),
		},
		{
			icon: Hash,
			label: "Nodes",
			value: String(data.metrics.nodeCount),
		},
	];

	return (
		<div className="flex flex-wrap items-center gap-0 rounded-2xl border border-gray-200 bg-white p-1 shadow-sm">
			{metrics.map((metric, i) => (
				<div
					key={metric.label}
					className={`flex items-center gap-2.5 px-5 py-3 ${
						i < metrics.length - 1 ? "border-r border-gray-100" : ""
					}`}
				>
					<metric.icon className="h-3.5 w-3.5 text-gray-500" />
					<div className="flex flex-col">
						<span className="text-[0.6rem] capitalize text-gray-500">
							{metric.label}
						</span>
						<span className="font-mono text-sm font-semibold text-gray-900">
							{metric.value}
						</span>
					</div>
				</div>
			))}

			<div className="ml-auto px-4">
				<button
					type="button"
					onClick={onOpenTrace}
					className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2 text-xs font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900"
				>
					<ExternalLink className="h-3.5 w-3.5" />
					Open Trace
				</button>
			</div>
		</div>
	);
}

function InputSection({ input }: { input: string | null }) {
	return (
		<div className="space-y-3">
			<div className="flex items-center gap-2">
				<ArrowRight className="h-4 w-4 text-gray-500" />
				<span className="text-xs font-semibold capitalize text-gray-700">
					Input
				</span>
			</div>
			<div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
				{input ? (
					<p className="whitespace-pre-wrap text-sm text-gray-800">{input}</p>
				) : (
					<p className="text-sm italic text-gray-500">No input captured</p>
				)}
			</div>
		</div>
	);
}

function OutputSection({
	outputs,
	rawJson,
	showRaw,
	onToggleRaw,
	copied,
	onCopy,
}: {
	outputs: NodeOutput[];
	rawJson: string | null;
	showRaw: boolean;
	onToggleRaw: () => void;
	copied: boolean;
	onCopy: () => void;
}) {
	const hasOutput = outputs.length > 0 || !!rawJson;

	return (
		<div className="space-y-3">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="flex items-center gap-2">
					<ArrowLeft className="h-4 w-4 text-gray-500" />
					<span className="text-xs font-semibold capitalize text-gray-700">
						Output
					</span>
				</div>
				<div className="flex flex-wrap items-center gap-2">
					{rawJson && (
						<div className="flex items-center rounded-lg border border-gray-200 bg-slate-100 p-0.5">
							<button
								type="button"
								onClick={showRaw ? onToggleRaw : undefined}
								className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
									!showRaw
										? "border border-orange-500 bg-white text-gray-900 shadow-sm"
										: "text-gray-600 hover:bg-white hover:text-slate-900"
								}`}
							>
								<FileText className="h-3 w-3" />
								Formatted
							</button>
							<button
								type="button"
								onClick={!showRaw ? onToggleRaw : undefined}
								className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
									showRaw
										? "border border-orange-500 bg-white text-gray-900 shadow-sm"
										: "text-gray-600 hover:bg-white hover:text-slate-900"
								}`}
							>
								<Braces className="h-3 w-3" />
								Raw JSON
							</button>
						</div>
					)}
					{hasOutput && (
						<button
							type="button"
							onClick={onCopy}
							className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:bg-white hover:text-slate-900"
						>
							{copied ? (
								<>
									<Check className="h-3.5 w-3.5 text-emerald-600" />
									<span className="text-emerald-700">Copied!</span>
								</>
							) : (
								<>
									<Copy className="h-3.5 w-3.5" />
									Copy
								</>
							)}
						</button>
					)}
				</div>
			</div>

			{showRaw && rawJson ? (
				<div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
					<pre className="custom-scrollbar overflow-x-auto whitespace-pre-wrap font-mono text-xs text-gray-800">
						{rawJson}
					</pre>
				</div>
			) : outputs.length > 0 ? (
				<div className="space-y-4">
					{outputs.map((entry, i) => (
						<div
							key={`${entry.nodeName}-${i}`}
							className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm"
						>
							<div className="mb-3 flex items-center gap-2">
								<span className="rounded-full border border-orange-400 bg-white px-2.5 py-0.5 text-[11px] font-medium text-orange-900">
									{entry.nodeName}
								</span>
							</div>
							<SimpleMarkdown
								content={entry.response}
								className="custom-scrollbar"
								variant="light"
							/>
						</div>
					))}
				</div>
			) : (
				<div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
					<p className="text-sm italic text-gray-500">No output available</p>
				</div>
			)}
		</div>
	);
}

function ErrorSection({
	errorMessage,
}: {
	errorMessage: string | null;
}) {
	return (
		<div className="space-y-3">
			<div className="flex items-center gap-2">
				<ArrowLeft className="h-4 w-4 text-red-600" />
				<span className="text-xs font-semibold capitalize text-red-700">
					Error
				</span>
			</div>
			<div className="rounded-2xl border border-red-200 bg-white p-5 shadow-sm">
				<div className="flex items-start gap-3">
					<XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
					<div className="space-y-1">
						<p className="text-sm font-medium text-red-800">Execution Error</p>
						<p className="whitespace-pre-wrap text-sm text-red-900/90">
							{errorMessage || "An unknown error occurred"}
						</p>
					</div>
				</div>
			</div>
		</div>
	);
}

function ActionBar({
	onOpenTrace,
	onRunAgain,
	hasTraceId,
}: {
	onOpenTrace: () => void;
	onRunAgain: () => void;
	hasTraceId: boolean;
}) {
	return (
		<div className="flex flex-wrap items-center justify-end gap-3 border-t border-gray-200 bg-white px-8 py-4">
			<button
				type="button"
				onClick={onOpenTrace}
				disabled={!hasTraceId}
				className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:border-orange-400 hover:bg-slate-50 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
			>
				<ExternalLink className="h-4 w-4" />
				View in Trace
			</button>
			<button
				type="button"
				onClick={onRunAgain}
				className="flex items-center gap-2 rounded-xl bg-orange-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-orange-700"
			>
				<Play className="h-4 w-4" />
				Run Again
			</button>
		</div>
	);
}
