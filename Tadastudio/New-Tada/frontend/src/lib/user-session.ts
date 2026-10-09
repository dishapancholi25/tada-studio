import { useGraphStore } from "@/stores/graphStore";
import { resetTutorialCache } from "@/tutorial/persistence";

/**
 * localStorage key prefixes that are always user-scoped.
 * Any key matching these prefixes is cleared on user switch.
 * Convention: all new user-specific keys MUST use one of these prefixes.
 */
const USER_STORAGE_PREFIXES = ["eval_", "as-", "agenticstudio-"] as const;

/**
 * Individual keys that are user-scoped but do not follow a recognised prefix.
 * Update this list when adding keys outside the prefix convention.
 */
const USER_STORAGE_EXACT_KEYS = [
  "execution-viewer-data",
  "return-from-viewer",
  "agent-panel-show-tips",
  "recentNodeSelections",
  "patBannerDismissed",
] as const;

const BROADCAST_CHANNEL_NAME = "agentic-studio-auth";
const STORAGE_SENTINEL_KEY = "agenticstudio-user-switch";

/**
 * Clear all user-scoped browser storage and reset in-memory stores.
 * Safe to call even if keys are absent — never throws.
 */
export function clearUserSession(): void {
  if (typeof window === "undefined") return;

  console.info(
    "[UserSession] clearUserSession called — all user storage cleared",
  );

  try {
    // 1. Remove localStorage keys by prefix
    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (
        key &&
        USER_STORAGE_PREFIXES.some((prefix) => key.startsWith(prefix))
      ) {
        keysToRemove.push(key);
      }
    }
    // Remove after iteration to avoid index shifting
    keysToRemove.forEach((key) => localStorage.removeItem(key));

    // 2. Remove individual exact-match keys
    USER_STORAGE_EXACT_KEYS.forEach((key) => localStorage.removeItem(key));

    // 3. Expire the theme cookie (prevents stale theme on next SSR paint)
    document.cookie = "agenticstudio-color-theme=; path=/; max-age=0";
  } catch {
    // Storage access errors must not block authentication
  }

  // 4. Reset Zustand graph store (in-memory + triggers persist write)
  try {
    useGraphStore.getState().clearGraph();
  } catch {
    // Must not block
  }

  // 5. Reset tutorial module cache (in-memory)
  try {
    resetTutorialCache();
  } catch {
    // Must not block
  }

  // 6. Signal other contexts to reset (e.g. ColorThemeContext)
  window.dispatchEvent(new CustomEvent("agentic-studio:user-clear"));
}

/**
 * Broadcast a user-switch signal to all other open tabs.
 * Uses BroadcastChannel with a storage-event fallback.
 */
export function broadcastUserSwitch(): void {
  if (typeof window === "undefined") return;

  if ("BroadcastChannel" in window) {
    const channel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
    channel.postMessage({ type: "USER_SWITCH" });
    channel.close();
  } else {
    // Fallback: write then immediately remove a sentinel key.
    // The storage event fires in other tabs (not the originating tab).
    try {
      localStorage.setItem(STORAGE_SENTINEL_KEY, Date.now().toString());
      localStorage.removeItem(STORAGE_SENTINEL_KEY);
    } catch {
      // Ignore
    }
  }
}

/**
 * Subscribe to user-switch signals from other tabs.
 * Returns a cleanup function — call it in useEffect cleanup.
 */
export function subscribeToUserSwitch(onSwitch: () => void): () => void {
  if (typeof window === "undefined") return () => {};

  // Capture window reference with explicit type to prevent TypeScript narrowing
  // it to `never` in the fallback branch after the BroadcastChannel `in` check.
  const win: Window = window;

  if ("BroadcastChannel" in win) {
    const channel = new BroadcastChannel(BROADCAST_CHANNEL_NAME);
    channel.onmessage = (event) => {
      if (event.data?.type === "USER_SWITCH") onSwitch();
    };
    return () => channel.close();
  }

  // Fallback: storage event (fires in other tabs when sentinel is written)
  const handler = (e: StorageEvent) => {
    if (e.key === STORAGE_SENTINEL_KEY) onSwitch();
  };
  win.addEventListener("storage", handler);
  return () => win.removeEventListener("storage", handler);
}
