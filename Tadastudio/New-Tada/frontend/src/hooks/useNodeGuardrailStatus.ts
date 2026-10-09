import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import * as guardrailsApi from "@/lib/guardrails-api";

/**
 * Module-level cache so every AgentNode instance shares a single fetch
 * per workflow. Keyed by workflowId.
 */
const cache = new Map<
	string,
	{
		nodeIds: Set<string>;
		workflowLevel: boolean;
		promise: Promise<void> | null;
		ts: number;
	}
>();

const CACHE_TTL_MS = 30_000;

// ── Revision counter: lets all hook instances react to invalidation ──

let revision = 0;
const listeners = new Set<() => void>();

function getRevision() {
	return revision;
}

function subscribe(cb: () => void) {
	listeners.add(cb);
	return () => {
		listeners.delete(cb);
	};
}

function bumpRevision() {
	revision += 1;
	for (const cb of listeners) cb();
}

// ── Fetching ─────────────────────────────────────────────────────────

function fetchForWorkflow(workflowId: string): Promise<void> {
	const existing = cache.get(workflowId);
	if (existing?.promise && Date.now() - existing.ts < CACHE_TTL_MS) {
		return existing.promise;
	}

	const promise = Promise.all([
		guardrailsApi.listAssignments({ workflow_id: workflowId }),
		guardrailsApi.listAssignments({
			target_type: "workflow",
			target_id: workflowId,
		}),
	])
		.then(([byWorkflow, byTarget]) => {
			const ids = new Set<string>();
			let hasWorkflow = false;
			// Merge both result sets, dedup by assignment id
			const seen = new Set<string>();
			for (const a of [...byWorkflow.assignments, ...byTarget.assignments]) {
				if (seen.has(a.id)) continue;
				seen.add(a.id);
				if (
					a.target_type === "agent_node" ||
					a.target_type === "tool" ||
					a.target_type === "model"
				) {
					ids.add(a.target_id);
				} else if (a.target_type === "workflow") {
					hasWorkflow = true;
				}
			}
			cache.set(workflowId, {
				nodeIds: ids,
				workflowLevel: hasWorkflow,
				promise,
				ts: Date.now(),
			});
		})
		.catch(() => {
			cache.set(workflowId, {
				nodeIds: new Set(),
				workflowLevel: false,
				promise: null,
				ts: 0,
			});
		});

	cache.set(workflowId, {
		nodeIds: existing?.nodeIds ?? new Set(),
		workflowLevel: existing?.workflowLevel ?? false,
		promise,
		ts: Date.now(),
	});

	return promise;
}

// ── Hook ─────────────────────────────────────────────────────────────

/**
 * Returns whether a specific node has guardrail policies assigned.
 * All node instances in the same workflow share a single API call.
 * Automatically re-fetches when `invalidateGuardrailStatusCache` is called.
 *
 * @param workflowId - The workflow ID to check assignments for
 * @param nodeId - The node ID to check for direct assignments
 */
export function useNodeGuardrailStatus(
	workflowId: string | undefined,
	nodeId: string,
): { hasGuardrails: boolean; loading: boolean } {
	const [hasGuardrails, setHasGuardrails] = useState(false);
	const [loading, setLoading] = useState(false);

	// Subscribe to the revision counter so a cache bust triggers re-render
	const rev = useSyncExternalStore(subscribe, getRevision, getRevision);

	const refresh = useCallback(() => {
		if (!workflowId) {
			setHasGuardrails(false);
			setLoading(false);
			return;
		}

		setLoading(true);
		fetchForWorkflow(workflowId).then(() => {
			const entry = cache.get(workflowId);
			if (!entry) {
				setHasGuardrails(false);
			} else {
				setHasGuardrails(entry.nodeIds.has(nodeId) || entry.workflowLevel);
			}
			setLoading(false);
		});
	}, [workflowId, nodeId]);

	// Fetch on mount and whenever workflowId, nodeId, or revision changes
	useEffect(() => {
		refresh();
	}, [refresh, rev]);

	return { hasGuardrails, loading };
}

/**
 * Call this after creating or deleting an assignment.
 * Busts the cache and triggers all hook instances to re-fetch.
 */
export function invalidateGuardrailStatusCache(workflowId?: string) {
	if (workflowId) {
		cache.delete(workflowId);
	} else {
		cache.clear();
	}
	bumpRevision();
}
