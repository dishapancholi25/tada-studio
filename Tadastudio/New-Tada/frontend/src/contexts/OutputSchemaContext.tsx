"use client";

import type React from "react";
import { createContext, useContext, useEffect, useState } from "react";
import type { OutputSchemaRegistry } from "@/types/io";
import { runtimeConfig } from "@/lib/runtime-config";

interface OutputSchemaContextValue {
	schemas: OutputSchemaRegistry | null;
	loading: boolean;
	error: string | null;
}

const OutputSchemaContext = createContext<OutputSchemaContextValue>({
	schemas: null,
	loading: true,
	error: null,
});

export function OutputSchemaProvider({
	children,
}: { children: React.ReactNode }) {
	const [schemas, setSchemas] = useState<OutputSchemaRegistry | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		let cancelled = false;

		async function fetchSchemas() {
			try {
				const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
				const response = await fetch(`${apiBaseUrl}/api/schemas/outputs`, {
					headers: { "Content-Type": "application/json" },
				});

				if (!response.ok) {
					throw new Error(`HTTP ${response.status}`);
				}

				const data: OutputSchemaRegistry = await response.json();
				if (!cancelled) {
					setSchemas(data);
					setLoading(false);
				}
			} catch (err) {
				if (!cancelled) {
					console.error("Failed to fetch output schemas:", err);
					setError(
						err instanceof Error ? err.message : "Failed to fetch schemas",
					);
					setLoading(false);
				}
			}
		}

		fetchSchemas();
		return () => {
			cancelled = true;
		};
	}, []);

	return (
		<OutputSchemaContext.Provider value={{ schemas, loading, error }}>
			{children}
		</OutputSchemaContext.Provider>
	);
}

/**
 * Hook to access the output schema registry.
 * Returns schemas for all node types, or null if still loading.
 */
export function useOutputSchemas(): OutputSchemaContextValue {
	return useContext(OutputSchemaContext);
}

/**
 * Hook to get the output schema for a specific node type.
 */
export function useNodeOutputSchema(nodeType: string | undefined) {
	const { schemas } = useOutputSchemas();
	if (!nodeType || !schemas) return null;
	return schemas[nodeType] ?? null;
}
