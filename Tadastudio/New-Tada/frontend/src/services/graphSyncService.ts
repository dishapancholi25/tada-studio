/**
 * Graph Sync Service - Handles background synchronization with debouncing
 * This is the core of the local-first architecture
 */

import { api } from "@/lib/api";
import { setSyncScheduler, useGraphStore } from "@/stores/graphStore";
import type { TypedGraphChange } from "@/types/graphChanges";

class GraphSyncService {
	private syncTimeout: NodeJS.Timeout | null = null;
	private isSyncing = false;
	private syncInterval = 2000; // 2 seconds debounce
	private maxRetries = 3;
	private retryCount = 0;
	private retryDelay = 5000; // 5 seconds between retries

	/**
	 * Schedule a debounced sync
	 * If called multiple times, resets the timer
	 */
	scheduleSync() {
		// Clear existing timeout
		if (this.syncTimeout) {
			clearTimeout(this.syncTimeout);
		}

		// Schedule new sync
		this.syncTimeout = setTimeout(() => {
			this.performSync();
		}, this.syncInterval);
	}

	/**
	 * Force immediate sync (used before execution, publish, etc.)
	 */
	async forceSync(): Promise<boolean> {
		// Clear any pending debounced sync
		if (this.syncTimeout) {
			clearTimeout(this.syncTimeout);
			this.syncTimeout = null;
		}

		return await this.performSync();
	}

	/**
	 * Cancel any pending sync
	 */
	cancelSync() {
		if (this.syncTimeout) {
			clearTimeout(this.syncTimeout);
			this.syncTimeout = null;
		}
	}

	/**
	 * Perform the actual sync operation
	 */
	private async performSync(): Promise<boolean> {
		// Already syncing, reschedule
		if (this.isSyncing) {
			console.log("[Sync] Already syncing, rescheduling...");
			this.scheduleSync();
			return false;
		}

		const store = useGraphStore.getState();

		// Skip sync for historical versions
		if (store.isHistoricalVersion) {
			console.log("[Sync] Viewing historical version, skipping sync");
			return false;
		}

		// Nothing to sync
		if (!store.isDirty || store.localChanges.length === 0) {
			console.log("[Sync] No changes to sync");
			return true;
		}

		// No graph loaded
		if (!store.currentGraph) {
			console.log("[Sync] No graph loaded, skipping sync");
			return false;
		}

		// Offline
		if (!navigator.onLine) {
			console.log("[Sync] Offline, marking as offline");
			store.markAsOffline();
			return false;
		}

		this.isSyncing = true;
		store.markAsSyncing();

		const startTime = Date.now();
		const changes = store.getChangesSinceLastSync();

		// Filter out changes that reference temp IDs (node not yet confirmed by backend).
		// These are kept in localChanges and will be retried on the next sync cycle
		// after replaceNodeId resolves the temp IDs.
		const hasTempId = (id: string | undefined) => id?.startsWith("temp-") || id?.startsWith("paste-");
		const validChanges = changes.filter((change) => {
			if (change.type === "ADD_CONNECTION" || change.type === "DELETE_CONNECTION") {
				if (hasTempId(change.data.sourceId) || hasTempId(change.data.targetId)) {
					console.log(`[Sync] Deferring ${change.type} with temp ID (source=${change.data.sourceId}, target=${change.data.targetId})`);
					return false;
				}
			}
			if ((change.type === "UPDATE_NODE" || change.type === "UPDATE_NODE_POSITION") && hasTempId(change.data.nodeId)) {
				console.log(`[Sync] Deferring ${change.type} with temp ID (nodeId=${change.data.nodeId})`);
				return false;
			}
			return true;
		});

		const deferredCount = changes.length - validChanges.length;
		if (deferredCount > 0) {
			console.log(`[Sync] Deferred ${deferredCount} change(s) with temp IDs`);
		}

		if (validChanges.length === 0) {
			console.log("[Sync] No valid changes to sync (all deferred)");
			this.isSyncing = false;
			store.markAsSynced();
			if (deferredCount > 0) {
				// Reschedule to retry deferred changes after temp IDs resolve
				this.scheduleSync();
			}
			return true;
		}

		console.log(`[Sync] Starting sync of ${validChanges.length} changes...`);

		try {
			// Send changes to backend
			const response = await this.sendChangesToBackend(
				store.currentGraph.name,
				validChanges,
			);

			if (response.success) {
				const duration = Date.now() - startTime;
				console.log(
					`[Sync] ✅ Synced ${validChanges.length} changes in ${duration}ms`,
				);

				// PHASE 1 FIX: Check if new changes arrived while syncing
				// If so, keep them for next sync instead of clearing everything
				const currentChanges = store.getChangesSinceLastSync();
				const newChangesWhileSyncing = currentChanges.filter(
					(change) =>
						!validChanges.some(
							(syncedChange) =>
								syncedChange.type === change.type &&
								syncedChange.timestamp === change.timestamp,
						),
				);

				if (newChangesWhileSyncing.length > 0 || deferredCount > 0) {
					console.log(
						`[Sync] ⚠️ ${newChangesWhileSyncing.length} new + ${deferredCount} deferred changes, preserving for next sync`,
					);
					// Mark as synced but preserve new/deferred changes
					store.markAsSynced();
					// Immediately schedule next sync for the remaining changes
					this.scheduleSync();
				} else {
					store.markAsSynced();
				}

				this.retryCount = 0; // Reset retry counter on success

				return true;
			} else {
				throw new Error(response.error || "Sync failed");
			}
		} catch (error: any) {
			const duration = Date.now() - startTime;
			console.error(`[Sync] ❌ Failed after ${duration}ms:`, error.message);

			store.markAsSyncError(error.message);

			// Retry logic
			if (this.retryCount < this.maxRetries) {
				this.retryCount++;
				console.log(
					`[Sync] Scheduling retry ${this.retryCount}/${this.maxRetries} in ${this.retryDelay}ms...`,
				);

				setTimeout(() => {
					this.performSync();
				}, this.retryDelay);
			} else {
				console.error("[Sync] Max retries reached, giving up");
				this.retryCount = 0;
			}

			return false;
		} finally {
			this.isSyncing = false;
		}
	}

	/**
	 * Send changes to backend
	 * Uses batch API if available, falls back to individual calls
	 */
	private async sendChangesToBackend(
		graphName: string,
		changes: TypedGraphChange[],
	): Promise<{ success: boolean; error?: string }> {
		try {
			// Try batch API first (will be implemented in Phase 3)
			if (typeof api.batchUpdateGraph === "function") {
				console.log("[Sync] Using batch API");
				const response = await api.batchUpdateGraph({
					graphName,
					changes: changes.map((change) => ({
						type: change.type,
						timestamp: change.timestamp,
						data: change.data,
					})),
				});

				// Update current version from server response
				if (response.success && response.version != null) {
					useGraphStore.getState().setCurrentVersion(response.version);
				}

				return { success: response.success };
			} else {
				// Fallback: Apply changes individually (slower)
				console.log("[Sync] Batch API not available, using fallback");
				await this.sendChangesIndividually(graphName, changes);
				return { success: true };
			}
		} catch (error: any) {
			return { success: false, error: error.message };
		}
	}

	/**
	 * Fallback method: Send changes individually
	 * Used when batch API is not available yet
	 */
	private async sendChangesIndividually(
		graphName: string,
		changes: TypedGraphChange[],
	): Promise<void> {
		// Group changes by type to minimize API calls
		const nodeAdds = changes.filter((c) => c.type === "ADD_NODE");
		const nodeUpdates = changes.filter(
			(c) => c.type === "UPDATE_NODE" || c.type === "UPDATE_NODE_POSITION",
		);
		const nodeDeletes = changes.filter((c) => c.type === "DELETE_NODE");
		const connectionAdds = changes.filter((c) => c.type === "ADD_CONNECTION");
		const connectionDeletes = changes.filter(
			(c) => c.type === "DELETE_CONNECTION",
		);

		// Apply node additions (e.g., pasted nodes)
		for (const change of nodeAdds) {
			if (change.type === "ADD_NODE" && change.data.node) {
				const nodeData = change.data.node;
				await api.createNode({
					graph_name: graphName,
					node_type: nodeData.type?.toUpperCase() || "AGENT",
					name: nodeData.name || "Untitled Node",
					position: nodeData.position,
					description: nodeData.description,
				});
			}
		}

		// Apply node updates (can be batched)
		for (const change of nodeUpdates) {
			if (change.type === "UPDATE_NODE") {
				await api.updateNode(
					graphName,
					change.data.nodeId,
					change.data.updates,
				);
			} else if (change.type === "UPDATE_NODE_POSITION") {
				await api.updateNode(graphName, change.data.nodeId, {
					position: change.data.position,
				});
			}
		}

		// Apply node deletions
		for (const change of nodeDeletes) {
			if (change.type === "DELETE_NODE") {
				await api.deleteNode(graphName, change.data.nodeId);
			}
		}

		// Apply connection additions
		for (const change of connectionAdds) {
			if (change.type === "ADD_CONNECTION") {
				await api.createConnection({
					graph_name: graphName,
					source_id: change.data.sourceId,
					target_id: change.data.targetId,
					source_handle: change.data.sourceHandle,
					target_handle: change.data.targetHandle,
					label: change.data.label,
					connection_type: change.data.connectionType,
				});
			}
		}

		// Apply connection deletions
		for (const change of connectionDeletes) {
			if (change.type === "DELETE_CONNECTION") {
				await api.deleteConnection(
					graphName,
					change.data.sourceId,
					change.data.targetId,
				);
			}
		}

		// Save graph after all changes
		await api.saveGraph(graphName);
	}

	/**
	 * Get sync statistics
	 */
	getStats() {
		const store = useGraphStore.getState();
		return {
			isDirty: store.isDirty,
			changeCount: store.localChanges.length,
			syncStatus: store.syncStatus,
			lastSyncedAt: store.lastSyncedAt,
			isSyncing: this.isSyncing,
			retryCount: this.retryCount,
		};
	}
}

// Export singleton instance
export const syncService = new GraphSyncService();

// Register sync scheduler with store
if (typeof window !== "undefined") {
	setSyncScheduler(() => syncService.scheduleSync());
}

// Auto-sync on window beforeunload
if (typeof window !== "undefined") {
	window.addEventListener("beforeunload", (e) => {
		const store = useGraphStore.getState();
		if (store.isDirty && store.localChanges.length > 0) {
			// Try to force sync
			syncService.forceSync();

			// Show confirmation dialog
			e.preventDefault();
			e.returnValue =
				"You have unsaved changes. Are you sure you want to leave?";
		}
	});

	// Sync on visibility change (tab becomes visible)
	document.addEventListener("visibilitychange", () => {
		if (!document.hidden) {
			const store = useGraphStore.getState();
			if (store.isDirty) {
				console.log("[Sync] Tab became visible, syncing changes...");
				syncService.scheduleSync();
			}
		}
	});

	// Detect online/offline
	window.addEventListener("online", () => {
		console.log("[Sync] Back online, syncing pending changes...");
		const store = useGraphStore.getState();
		if (store.syncStatus === "offline" && store.isDirty) {
			store.setIsDirty(true);
			syncService.scheduleSync();
		}
	});

	window.addEventListener("offline", () => {
		console.log("[Sync] Went offline");
		useGraphStore.getState().markAsOffline();
	});
}
