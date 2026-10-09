"use client";

export type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVELS: Record<LogLevel, number> = {
	debug: 0,
	info: 1,
	warn: 2,
	error: 3,
};

// Environment detection
const isDevelopment =
	typeof process !== "undefined"
		? process.env.NODE_ENV !== "production"
		: true;

// Configurable minimum log level
const getMinLogLevel = (): LogLevel => {
	if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_LOG_LEVEL) {
		return process.env.NEXT_PUBLIC_LOG_LEVEL as LogLevel;
	}
	return isDevelopment ? "debug" : "warn";
};

const minLevel = getMinLogLevel();

// Color configuration for namespaces (browser console)
const namespaceColors: Record<string, string> = {
	GraphStore: "#4ade80",
	GraphContext: "#60a5fa",
	WebSocket: "#f472b6",
	AgentBuilder: "#a78bfa",
	Execution: "#fbbf24",
	Sync: "#2dd4bf",
	ExecutionParser: "#fb923c",
	ExecutionData: "#38bdf8",
};

const getColor = (namespace: string): string => {
	return namespaceColors[namespace] || "#94a3b8";
};

export interface Logger {
	debug: (...args: unknown[]) => void;
	info: (...args: unknown[]) => void;
	warn: (...args: unknown[]) => void;
	error: (...args: unknown[]) => void;
	time: (label: string) => void;
	timeEnd: (label: string) => void;
}

/**
 * Creates a namespaced logger with environment-aware log level filtering.
 *
 * @param namespace - The namespace/tag for log messages (e.g., "GraphStore", "WebSocket")
 * @returns Logger instance with debug, info, warn, error, time, and timeEnd methods
 *
 * @example
 * const log = createLogger("GraphStore");
 * log.debug("Loading graph", { id: "123" });  // Suppressed in production
 * log.info("Graph loaded");
 * log.warn("Missing field");
 * log.error("Failed to save", error);
 */
export function createLogger(namespace: string): Logger {
	const shouldLog = (level: LogLevel): boolean => {
		return LOG_LEVELS[level] >= LOG_LEVELS[minLevel];
	};

	const formatPrefix = (): [string, string, string] => {
		const color = getColor(namespace);
		const timestamp = new Date().toISOString();
		return [
			`%c[${namespace}]%c [${timestamp}]`,
			`color: ${color}; font-weight: bold`,
			"color: inherit",
		];
	};

	return {
		debug: (...args: unknown[]) => {
			if (shouldLog("debug")) {
				const [format, ...styles] = formatPrefix();
				console.log(format, ...styles, ...args);
			}
		},
		info: (...args: unknown[]) => {
			if (shouldLog("info")) {
				const [format, ...styles] = formatPrefix();
				console.info(format, ...styles, ...args);
			}
		},
		warn: (...args: unknown[]) => {
			if (shouldLog("warn")) {
				const [format, ...styles] = formatPrefix();
				console.warn(format, ...styles, ...args);
			}
		},
		error: (...args: unknown[]) => {
			if (shouldLog("error")) {
				const [format, ...styles] = formatPrefix();
				console.error(format, ...styles, ...args);
			}
		},
		time: (label: string) => {
			if (shouldLog("debug")) {
				console.time(`[${namespace}] ${label}`);
			}
		},
		timeEnd: (label: string) => {
			if (shouldLog("debug")) {
				console.timeEnd(`[${namespace}] ${label}`);
			}
		},
	};
}

// Pre-configured loggers for common namespaces
export const graphStoreLogger = createLogger("GraphStore");
export const graphContextLogger = createLogger("GraphContext");
export const webSocketLogger = createLogger("WebSocket");
export const executionLogger = createLogger("Execution");
export const syncLogger = createLogger("Sync");

// Default logger for one-off usage
export const logger = createLogger("App");
