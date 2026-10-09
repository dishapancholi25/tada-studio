"use client";

const parseBool = (v?: string) => v === "1" || v === "true" || v === "yes";

export const DEBUG_LOADING =
	typeof process !== "undefined"
		? process.env.NEXT_PUBLIC_DEBUG_LOADING
			? parseBool(process.env.NEXT_PUBLIC_DEBUG_LOADING)
			: process.env.NODE_ENV !== "production"
		: true;

const ts = () => new Date().toISOString();

export function logLoading(...args: any[]) {
	if (!DEBUG_LOADING) return;

	console.log(`[loading][${ts()}]`, ...args);
}

export function timeLoading(label: string) {
	if (!DEBUG_LOADING) return;

	console.time(`[loading] ${label}`);
}

export function timeLoadingEnd(label: string) {
	if (!DEBUG_LOADING) return;

	console.timeEnd(`[loading] ${label}`);
}

// Re-export logger utilities for convenience
export { createLogger, logger } from "./logger";
export type { Logger, LogLevel } from "./logger";
