import {
	AlertCircle,
	Check,
	CheckCircle,
	Copy,
	Mail,
	Paperclip,
} from "lucide-react";
import React from "react";
import JsonViewerEnhanced from "../../../../JsonViewerEnhanced";
import type { EmailSendExecution } from "../types/execution.types";
import { BaseRenderer } from "./BaseRenderer";

export class EmailSendRenderer extends BaseRenderer<EmailSendExecution> {
	state = {
		copiedField: null as string | null,
	};

	getViewModes() {
		return [
			{
				key: "email",
				label: "Email",
				icon: <Mail className="w-4 h-4" />,
			},
			{ key: "raw", label: "Raw Data" },
		];
	}

	renderViewMode(mode: string, execution: EmailSendExecution) {
		switch (mode) {
			case "email":
				return this.renderEmailView(execution);
			default:
				return (
					<div className="bg-[color:var(--color-surface)] rounded-lg p-4">
						<JsonViewerEnhanced data={execution} />
					</div>
				);
		}
	}

	handleCopy = async (field: string, value: string) => {
		try {
			await navigator.clipboard.writeText(value);
			this.setState({ copiedField: field });
			setTimeout(() => this.setState({ copiedField: null }), 2000);
		} catch (err) {
			console.error("Failed to copy:", err);
		}
	};

	renderEmailView(execution: EmailSendExecution) {
		const isSuccess = execution.status === "sent";

		return (
			<div className="space-y-4">
				{/* Status banner */}
				<div
					className={`flex items-center gap-2.5 px-4 py-2.5 rounded-lg border ${
						isSuccess
							? "border-emerald-500/30 bg-emerald-500/5"
							: "border-red-500/30 bg-red-500/5"
					}`}
				>
					{isSuccess ? (
						<CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
					) : (
						<AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
					)}
					<span
						className={`text-sm font-medium ${isSuccess ? "text-emerald-400" : "text-red-400"}`}
					>
						{isSuccess ? "Delivered" : "Failed"}
					</span>
					{execution.duration && (
						<span className="text-xs text-[color:var(--color-text-muted)] ml-auto">
							{execution.duration.toFixed(2)}s
						</span>
					)}
					{execution.error && (
						<span className="text-xs text-red-400 ml-auto truncate max-w-[200px]">
							{execution.error}
						</span>
					)}
				</div>

				{/* Email card — styled like an email client */}
				<div className="bg-white border border-slate-200 shadow-sm rounded-xl overflow-hidden border border-[color:var(--color-border)]/20">
					{/* Header fields */}
					<div className="divide-y divide-[color:var(--color-border)]/10">
						{/* To */}
						<div className="flex items-center px-5 py-3 gap-3">
							<span className="text-xs font-medium text-[color:var(--color-text-muted)] w-14 shrink-0 text-right">
								To
							</span>
							<span className="text-sm text-slate-700 flex-1 truncate">
								{execution.to_address}
							</span>
							<button
								onClick={() =>
									this.handleCopy("to", execution.to_address)
								}
								className="p-1 rounded hover:bg-[color:var(--color-surface)] transition-colors shrink-0"
							>
								{this.state.copiedField === "to" ? (
									<Check className="w-3.5 h-3.5 text-emerald-400" />
								) : (
									<Copy className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
								)}
							</button>
						</div>

						{/* Subject */}
						<div className="flex items-center px-5 py-3 gap-3">
							<span className="text-xs font-medium text-[color:var(--color-text-muted)] w-14 shrink-0 text-right">
								Subject
							</span>
							<span className="text-sm text-slate-700 font-medium flex-1">
								{execution.subject}
							</span>
							<button
								onClick={() =>
									this.handleCopy("subject", execution.subject)
								}
								className="p-1 rounded hover:bg-[color:var(--color-surface)] transition-colors shrink-0"
							>
								{this.state.copiedField === "subject" ? (
									<Check className="w-3.5 h-3.5 text-emerald-400" />
								) : (
									<Copy className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
								)}
							</button>
						</div>

						{/* Attachments (if any) */}
						{execution.attachments_sent != null &&
							execution.attachments_sent > 0 && (
								<div className="flex items-center px-5 py-3 gap-3">
									<span className="text-xs font-medium text-[color:var(--color-text-muted)] w-14 shrink-0 text-right">
										Attach
									</span>
									<div className="flex items-center gap-1.5">
										<Paperclip className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
										<span className="text-sm text-[color:var(--color-text-secondary)]">
											{execution.attachments_sent} file
											{execution.attachments_sent > 1 ? "s" : ""} attached
										</span>
									</div>
								</div>
							)}
					</div>

					{/* Body */}
					<div className="border-t border-[color:var(--color-border)]/20">
						<div className="px-5 py-4">
							{execution.body ? (
								<div className="relative group">
									<pre className="text-sm text-[color:var(--color-text-secondary)] whitespace-pre-wrap font-sans leading-relaxed">
										{execution.body}
									</pre>
									<button
										onClick={() =>
											this.handleCopy("body", execution.body || "")
										}
										className="absolute top-0 right-0 p-1.5 rounded-lg bg-[color:var(--color-surface)]/80 opacity-0 group-hover:opacity-100 transition-opacity"
									>
										{this.state.copiedField === "body" ? (
											<Check className="w-3.5 h-3.5 text-emerald-400" />
										) : (
											<Copy className="w-3.5 h-3.5 text-[color:var(--color-text-muted)]" />
										)}
									</button>
								</div>
							) : (
								<p className="text-sm text-[color:var(--color-text-muted)] italic">
									(No body content)
								</p>
							)}
						</div>
					</div>

					{/* Footer — message ID */}
					{execution.message_id && (
						<div className="border-t border-[color:var(--color-border)]/10 px-5 py-2.5 bg-[color:var(--color-surface)]/30">
							<p className="text-[11px] text-[color:var(--color-text-muted)] font-mono truncate">
								ID: {execution.message_id}
							</p>
						</div>
					)}
				</div>
			</div>
		);
	}
}
