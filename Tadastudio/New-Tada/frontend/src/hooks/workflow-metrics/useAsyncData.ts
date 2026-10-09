"use client";

import { useCallback, useEffect, useState } from "react";

export interface AsyncState<T> {
	data: T | null;
	loading: boolean;
	error: string | null;
	/** Re-run the fetcher (e.g. from an error-state "Retry" button). */
	refetch: () => void;
}

/**
 * Small helper that mirrors the repo's useState/useEffect data-fetching
 * convention. It runs `fetcher` on mount and whenever the dependency list
 * changes, exposing `{ data, loading, error, refetch }`.
 *
 * `fetcher` is intentionally passed inline by callers; the dependency array is
 * provided explicitly so the hook doesn't depend on the identity of `fetcher`.
 */
export function useAsyncData<T>(
	fetcher: () => Promise<T>,
	deps: unknown[],
): AsyncState<T> {
	const [data, setData] = useState<T | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [reloadToken, setReloadToken] = useState(0);

	const refetch = useCallback(() => setReloadToken((t) => t + 1), []);

	useEffect(() => {
		let cancelled = false;
		setLoading(true);
		setError(null);

		fetcher()
			.then((result) => {
				if (!cancelled) setData(result);
			})
			.catch((err: unknown) => {
				if (!cancelled) {
					setError(err instanceof Error ? err.message : "Failed to load data");
				}
			})
			.finally(() => {
				if (!cancelled) setLoading(false);
			});

		return () => {
			cancelled = true;
		};
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [...deps, reloadToken]);

	return { data, loading, error, refetch };
}
