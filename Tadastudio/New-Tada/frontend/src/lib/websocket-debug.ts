const DEBUG_STORAGE_KEY = "tada_debug_websocket";

export function isWebSocketDebugEnabled(): boolean {
	if (process.env.NEXT_PUBLIC_DEBUG_WEBSOCKET === "true") {
		return true;
	}

	if (typeof window === "undefined") {
		return false;
	}

	return window.localStorage.getItem(DEBUG_STORAGE_KEY) === "true";
}

export function debugWebSocket(scope: string, message: string, details?: unknown) {
	if (!isWebSocketDebugEnabled()) {
		return;
	}

	if (details === undefined) {
		console.debug(`[${scope}] ${message}`);
		return;
	}

	console.debug(`[${scope}] ${message}`, details);
}

export function warnWebSocket(scope: string, message: string, details?: unknown) {
	if (!isWebSocketDebugEnabled()) {
		return;
	}

	if (details === undefined) {
		console.warn(`[${scope}] ${message}`);
		return;
	}

	console.warn(`[${scope}] ${message}`, details);
}
