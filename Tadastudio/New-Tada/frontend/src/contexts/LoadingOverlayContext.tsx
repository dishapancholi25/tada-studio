"use client";

import type React from "react";
import {
	createContext,
	useCallback,
	useContext,
	useRef,
	useState,
} from "react";
import { LoadingSpinner } from "@/components/utils/LazyLoad";
import { logLoading } from "@/lib/debug";

type ShowOptions = {
	message?: string;
	minDurationMs?: number;
};

interface LoadingOverlayContextType {
	showOverlay: (opts?: ShowOptions) => void;
	hideOverlay: () => void;
	withOverlay: <T>(fn: () => Promise<T>, opts?: ShowOptions) => Promise<T>;
}

const LoadingOverlayContext = createContext<LoadingOverlayContextType | null>(
	null,
);

export function LoadingOverlayProvider({
	children,
}: {
	children: React.ReactNode;
}) {
	const [visible, setVisible] = useState(false);
	const [message, setMessage] = useState<string>("Loading...");
	const startTimeRef = useRef<number | null>(null);
	const minDurationRef = useRef<number>(0);
	const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	const clearHideTimer = () => {
		if (hideTimerRef.current) {
			clearTimeout(hideTimerRef.current);
			hideTimerRef.current = null;
		}
	};

	const showOverlay = useCallback((opts?: ShowOptions) => {
		clearHideTimer();
		setMessage(opts?.message || "Loading...");
		minDurationRef.current = Math.max(0, opts?.minDurationMs ?? 0);
		startTimeRef.current = Date.now();
		setVisible(true);
		logLoading("Overlay SHOW", {
			message: opts?.message || "Loading...",
			minDurationMs: minDurationRef.current,
		});
	}, []);

	const hideOverlay = useCallback(() => {
		const started = startTimeRef.current ?? 0;
		const elapsed = Date.now() - started;
		const remaining = Math.max(0, (minDurationRef.current ?? 0) - elapsed);

		if (remaining === 0) {
			setVisible(false);
		} else {
			clearHideTimer();
			hideTimerRef.current = setTimeout(() => setVisible(false), remaining);
		}
		logLoading("Overlay HIDE requested", {
			elapsedMs: elapsed,
			minDurationMs: minDurationRef.current,
			remainingMs: remaining,
		});
	}, []);

	const withOverlay = useCallback(
		async <T,>(fn: () => Promise<T>, opts?: ShowOptions) => {
			showOverlay(opts);
			try {
				const result = await fn();
				return result;
			} finally {
				hideOverlay();
			}
		},
		[hideOverlay, showOverlay],
	);

	return (
		<LoadingOverlayContext.Provider
			value={{ showOverlay, hideOverlay, withOverlay }}
		>
			{children}
			{visible && (
				<div className="fixed inset-0 z-[2147483647] bg-gradient-to-br from-orange-50 to-orange-100 flex items-center justify-center">
					<div className="flex flex-col items-center gap-4 animate-fadeIn">
						<div className="w-12 h-12 rounded-full border-[3px] border-orange-200 border-t-orange-500 animate-spin" />
						<p className="text-slate-700 text-lg animate-pulse">
							{message}
						</p>
					</div>
				</div>
			)}
		</LoadingOverlayContext.Provider>
	);
}

export function useLoadingOverlay() {
	const ctx = useContext(LoadingOverlayContext);
	if (!ctx)
		throw new Error(
			"useLoadingOverlay must be used within a LoadingOverlayProvider",
		);
	return ctx;
}
