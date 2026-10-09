import { useEffect, useState } from "react";
import { configAPI } from "./config-api";
import type { PhoenixServiceConfig } from "./config-api";

/**
 * Sanitize a workflow name into a Phoenix project name.
 * Mirrors backend/services/phoenix/tracing.py:sanitize_project_name.
 */
export function sanitizeProjectName(name: string): string {
	return name
		.toLowerCase()
		.replace(/[^a-z0-9-]/g, "-")
		.replace(/-{2,}/g, "-")
		.replace(/^-|-$/g, "") || "default";
}

/**
 * Returns a Phoenix URL from a trace/run reference.
 *
 * Priority:
 *   1. `path` — relative path stored by backend (e.g. `/projects/<id>/traces/<tid>`)
 *   2. `project_path` — relative project path (run-level summaries)
 *   3. Legacy `url` / `project_url` — old full URLs stored before the path migration
 *   4. Name-based fallback — constructs URL from `project` or `trace_id` fields
 *   5. null
 *
 * For project-level links without a reference, use {@link usePhoenixProjectUrl}.
 */
export function getPhoenixUrl(
	phoenix: PhoenixServiceConfig | undefined | null,
	traceReference?: Record<string, any> | null,
): string | null {
	const baseUrl = phoenix?.enabled && phoenix.ui_url ? phoenix.ui_url.replace(/\/+$/, "") : null;

	// 1. Relative path from backend — construct full URL using current config
	if (traceReference?.path && typeof traceReference.path === "string" && baseUrl)
		return `${baseUrl}${traceReference.path}`;

	// 2. Relative project path (run-level summaries)
	if (traceReference?.project_path && typeof traceReference.project_path === "string" && baseUrl)
		return `${baseUrl}${traceReference.project_path}`;

	// 3. Legacy: full URLs stored before migration (backwards compat)
	if (traceReference?.url && typeof traceReference.url === "string")
		return traceReference.url;
	if (traceReference?.project_url && typeof traceReference.project_url === "string")
		return traceReference.project_url;

	// 4. Fallback: build from project name + trace_id fields (requires config)
	if (!baseUrl) return null;
	const project = (typeof traceReference?.project === "string" && traceReference.project) || null;
	if (project && traceReference?.trace_id && typeof traceReference.trace_id === "string") {
		return `${baseUrl}/projects/${encodeURIComponent(project)}/traces/${encodeURIComponent(traceReference.trace_id)}`;
	}
	if (project) {
		return `${baseUrl}/projects/${encodeURIComponent(project)}`;
	}

	return null;
}

/**
 * Hook that resolves a Phoenix project name to its UI URL via the backend API.
 * Phoenix uses internal project IDs in URLs, so the backend resolves name -> ID.
 *
 * When a ``phoenix`` config is provided, the hook skips the API call if Phoenix
 * is disabled.  When omitted, the backend endpoint checks enablement itself.
 *
 * @param phoenixOrName - Either a PhoenixServiceConfig (for gating) or the project name directly
 * @param projectName - Phoenix project name (e.g. sanitized workflow name)
 * @returns The resolved Phoenix project URL, or null if unavailable
 */
export function usePhoenixProjectUrl(
	phoenix: PhoenixServiceConfig | undefined | null,
	projectName: string | null | undefined,
): string | null {
	const [url, setUrl] = useState<string | null>(null);

	// When phoenix config is provided and explicitly disabled, skip.
	// When phoenix config is null/undefined (not yet loaded), still try
	// the backend endpoint — it checks enablement server-side.
	const skip = phoenix !== undefined && phoenix !== null && !phoenix.enabled;

	useEffect(() => {
		if (skip || !projectName) {
			setUrl(null);
			return;
		}
		let cancelled = false;
		configAPI.getPhoenixProjectUrl(projectName).then((resolved) => {
			if (!cancelled) setUrl(resolved);
		});
		return () => { cancelled = true; };
	}, [skip, projectName]);

	return url;
}

/**
 * Hook that fetches Phoenix config from the environment config API once on mount.
 * Returns the Phoenix service config or null if unavailable.
 */
export function usePhoenixConfig(): PhoenixServiceConfig | null {
	const [config, setConfig] = useState<PhoenixServiceConfig | null>(null);

	useEffect(() => {
		configAPI
			.getEnvironmentConfig()
			.then((env) => setConfig(env.external_services.phoenix ?? null))
			.catch(() => setConfig(null));
	}, []);

	return config;
}
