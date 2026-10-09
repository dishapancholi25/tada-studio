/**
 * Sync Status Indicator - Shows the current sync state to the user
 * Part of local-first architecture UX
 */

"use client";

import clsx from "clsx";
import { AlertCircle, Check, Cloud, CloudOff, Loader2 } from "lucide-react";
import { syncService } from "@/services/graphSyncService";
import { useGraphStore } from "@/stores/graphStore";
import type { SyncStatus } from "@/types/graphChanges";

interface SyncStatusIndicatorProps {
	className?: string;
	variant?: "card" | "inline";
}

export function SyncStatusIndicator({
	className,
	variant = "card",
}: SyncStatusIndicatorProps = {}) {
	const syncStatus = useGraphStore((state) => state.syncStatus);
	const lastSyncedAt = useGraphStore((state) => state.lastSyncedAt);
	const changeCount = useGraphStore((state) => state.localChanges.length);
	const lastSyncError = useGraphStore((state) => state.lastSyncError);

	const status = getStatusDisplay(syncStatus, changeCount);
	const lastSyncText = lastSyncedAt
		? `Last saved ${formatRelativeTime(lastSyncedAt)}`
		: "";

	if (variant === "inline") {
		const inlineStatus = getInlineStatusDisplay(syncStatus);
		return (
			<button
				type="button"
				onClick={syncStatus === "error" ? handleRetrySync : undefined}
				className={clsx(
					"flex items-center gap-1.5 transition-colors duration-200",
					syncStatus === "error" && "cursor-pointer hover:opacity-80",
					className,
				)}
				title={
					syncStatus === "error"
						? lastSyncError || "Click to retry sync"
						: lastSyncText || undefined
				}
				disabled={syncStatus !== "error"}
			>
				{inlineStatus.icon}
				<span
					className={clsx(
						"text-sm font-medium",
						inlineStatus.textColor,
					)}
				>
					{inlineStatus.text}
				</span>
			</button>
		);
	}

	const secondaryText =
		status.subtitle ??
		(syncStatus === "saved" && lastSyncText
			? lastSyncText
			: syncStatus === "unsaved"
				? "Pending sync"
				: "");

	return (
		<div
			className={clsx(
				"flex min-h-[3.5rem] items-center gap-3 rounded-xl border border-[color:var(--color-border)]/60 bg-[color:var(--color-bg-secondary)]/80 px-4 py-3 shadow-[0_12px_24px_rgba(0,0,0,0.35)] backdrop-blur-xl transition-all duration-200",
				className,
			)}
			title={lastSyncError || lastSyncText || undefined}
		>
			<div
				className={clsx(
					"flex h-9 w-9 items-center justify-center rounded-lg border transition-colors duration-200",
					status.iconBg,
				)}
			>
				{status.icon}
			</div>

			<div className="flex flex-1 flex-col">
				<span
					className={clsx(
						"text-sm font-semibold tracking-wide",
						status.textColor,
					)}
				>
					{status.text}
				</span>
				{secondaryText && (
					<span className="text-xs text-[color:var(--color-text-muted)]">
						{secondaryText}
					</span>
				)}
			</div>

			{syncStatus === "error" && (
				<button
					onClick={handleRetrySync}
					className="rounded-md border border-red-400/40 px-2 py-1 text-xs font-medium text-red-600 transition-colors duration-200 hover:border-red-300 hover:text-red-100"
				>
					Retry
				</button>
			)}
		</div>
	);
}

function handleRetrySync() {
	syncService.forceSync();
}

function getInlineStatusDisplay(syncStatus: SyncStatus) {
	switch (syncStatus) {
		case "saved":
			return {
				icon: <Check className="h-4 w-4 text-emerald-400" />,
				text: "Saved",
				textColor: "text-emerald-600",
			};
		case "saving":
			return {
				icon: <Loader2 className="h-4 w-4 text-sky-400 animate-spin" />,
				text: "Syncing...",
				textColor: "text-sky-600",
			};
		case "unsaved":
			return {
				icon: <Cloud className="h-4 w-4 text-amber-400" />,
				text: "Unsaved",
				textColor: "text-amber-300",
			};
		case "offline":
			return {
				icon: <CloudOff className="h-4 w-4 text-slate-400" />,
				text: "Offline",
				textColor: "text-slate-300",
			};
		case "error":
		default:
			return {
				icon: <AlertCircle className="h-4 w-4 text-red-400" />,
				text: "Sync error",
				textColor: "text-red-300",
			};
	}
}

function getStatusDisplay(syncStatus: SyncStatus, changeCount: number) {
	switch (syncStatus) {
		case "saved":
			return {
				icon: <Check className="h-4 w-4 text-emerald-600" />,
				text: "All changes saved",
				textColor: "text-emerald-600",
				iconBg: "border-emerald-400/40 bg-emerald-500/15",
			};
		case "saving":
			return {
				icon: <Loader2 className="h-4 w-4 text-sky-600 animate-spin" />,
				text: "Syncing changes…",
				textColor: "text-sky-600",
				iconBg: "border-sky-400/40 bg-sky-500/15",
				subtitle: "Sync in progress",
			};
		case "unsaved":
			return {
				icon: <Cloud className="h-4 w-4 text-amber-300" />,
				text:
					changeCount > 0
						? `${changeCount} pending change${changeCount > 1 ? "s" : ""}`
						: "Pending changes",
				textColor: "text-amber-700",
				iconBg: "border-amber-400/40 bg-amber-500/15",
			};
		case "offline":
			return {
				icon: <CloudOff className="h-4 w-4 text-slate-300" />,
				text: "Offline mode",
				textColor: "text-slate-200",
				iconBg: "border-slate-400/40 bg-slate-500/15",
				subtitle: "Changes will sync when reconnected",
			};
		case "error":
		default:
			return {
				icon: <AlertCircle className="h-4 w-4 text-red-300" />,
				text: "Sync failed",
				textColor: "text-red-600",
				iconBg: "border-red-400/40 bg-red-500/15",
				subtitle: "Tap retry to attempt again",
			};
	}
}

function formatRelativeTime(timestamp: number): string {
	const seconds = Math.floor((Date.now() - timestamp) / 1000);

	if (seconds < 10) return "just now";
	if (seconds < 60) return `${seconds}s ago`;

	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes}m ago`;

	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;

	const days = Math.floor(hours / 24);
	return `${days}d ago`;
}
