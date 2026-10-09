import { runtimeConfig } from "@/lib/runtime-config";
import { getAuthenticatedApiClientForMain } from "@/lib/api";
import type { TutorialState } from "./types";

const DEFAULT_STATE: TutorialState = {
  completedTutorials: {},
  lastStepReached: {},
  version: 1,
};

// ── In-memory cache ─────────────────────────────────────────────────
// Keeps a local copy so synchronous reads (e.g. initial render) work
// immediately. The cache is hydrated from the API on first load and
// kept in sync by every write.
let cachedState: TutorialState = { ...DEFAULT_STATE };
let hydrated = false;

// ── localStorage helpers (legacy / offline fallback) ────────────────
const STORAGE_KEY = "as-tutorial-state";

function readLocalStorage(): TutorialState {
  if (typeof window === "undefined") return { ...DEFAULT_STATE };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_STATE };
    const parsed = JSON.parse(raw);
    return {
      completedTutorials: parsed.completedTutorials ?? {},
      lastStepReached: parsed.lastStepReached ?? {},
      version: parsed.version ?? 1,
    };
  } catch {
    return { ...DEFAULT_STATE };
  }
}

// ── API helpers ─────────────────────────────────────────────────────

async function apiFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const authenticatedClient = getAuthenticatedApiClientForMain();
  if (authenticatedClient) {
    const method = (options.method ?? "GET").toUpperCase();
    const body = options.body ? JSON.parse(options.body as string) : undefined;
    switch (method) {
      case "GET":
        return await authenticatedClient.get(url);
      case "PUT":
        return await authenticatedClient.put(url, body);
      default:
        break;
    }
  }
  // Fallback: direct fetch
  const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
  const response = await fetch(`${apiBaseUrl}${url}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) throw new Error(`Tutorial API error: ${response.status}`);
  return response.json();
}

// ── Public API ──────────────────────────────────────────────────────

/**
 * Hydrate the in-memory cache from the backend.
 * Called once on app startup. Migrates localStorage data if present.
 */
export async function hydrateTutorialState(): Promise<TutorialState> {
  try {
    const res = await apiFetch<{
      completed_tutorials: Record<string, boolean>;
      last_step_reached: Record<string, number>;
    }>("/api/tutorial/progress");

    cachedState = {
      completedTutorials: res.completed_tutorials ?? {},
      lastStepReached: res.last_step_reached ?? {},
      version: 1,
    };

    // Migrate any localStorage data that the server doesn't have yet
    const local = readLocalStorage();
    let needsSync = false;

    for (const [id, completed] of Object.entries(local.completedTutorials)) {
      if (completed && !cachedState.completedTutorials[id]) {
        cachedState.completedTutorials[id] = true;
        needsSync = true;
      }
    }
    for (const [id, step] of Object.entries(local.lastStepReached)) {
      if (
        step > 0 &&
        (cachedState.lastStepReached[id] === undefined ||
          step > cachedState.lastStepReached[id])
      ) {
        cachedState.lastStepReached[id] = step;
        needsSync = true;
      }
    }

    if (needsSync) {
      await apiFetch("/api/tutorial/progress", {
        method: "PUT",
        body: JSON.stringify({
          completed_tutorials: cachedState.completedTutorials,
          last_step_reached: cachedState.lastStepReached,
        }),
      });
      // Clear localStorage after successful migration
      localStorage.removeItem(STORAGE_KEY);
    } else if (localStorage.getItem(STORAGE_KEY)) {
      localStorage.removeItem(STORAGE_KEY);
    }

    hydrated = true;
  } catch {
    // API unreachable — fall back to localStorage
    cachedState = readLocalStorage();
    hydrated = true;
  }
  return cachedState;
}

/** Synchronous read of cached state (returns default if not yet hydrated). */
export function getTutorialState(): TutorialState {
  if (!hydrated) {
    // On first call before hydration, seed from localStorage so we
    // don't flash an empty state.
    cachedState = readLocalStorage();
  }
  return cachedState;
}

export function markCompleted(tutorialId: string): void {
  cachedState.completedTutorials[tutorialId] = true;
  apiFetch("/api/tutorial/progress", {
    method: "PUT",
    body: JSON.stringify({
      completed_tutorials: { [tutorialId]: true },
    }),
  }).catch(() => {});
}

export function saveProgress(tutorialId: string, stepIndex: number): void {
  cachedState.lastStepReached[tutorialId] = stepIndex;
  apiFetch("/api/tutorial/progress", {
    method: "PUT",
    body: JSON.stringify({
      last_step_reached: { [tutorialId]: stepIndex },
    }),
  }).catch(() => {});
}

export function resetTutorial(tutorialId: string): void {
  delete cachedState.completedTutorials[tutorialId];
  delete cachedState.lastStepReached[tutorialId];
  apiFetch("/api/tutorial/progress", {
    method: "PUT",
    body: JSON.stringify({
      completed_tutorials: cachedState.completedTutorials,
      last_step_reached: cachedState.lastStepReached,
      replace: true,
    }),
  }).catch(() => {});
}

export function resetAllTutorials(): void {
  cachedState = { ...DEFAULT_STATE };
  apiFetch("/api/tutorial/progress", {
    method: "PUT",
    body: JSON.stringify({
      completed_tutorials: {},
      last_step_reached: {},
      replace: true,
    }),
  }).catch(() => {});
}

/**
 * Reset the in-memory tutorial cache so the next call to hydrateTutorialState()
 * re-fetches from the API for the new user.
 * Called by clearUserSession() on user switch.
 */
export function resetTutorialCache(): void {
  cachedState = { ...DEFAULT_STATE };
  hydrated = false;
}

// ── Tutorial button visibility ─────────────────────────────────────
// This remains in localStorage since it's a UI preference, not progress.

const BUTTON_VISIBLE_KEY = "as-tutorial-button-visible";

export function isTutorialButtonVisible(): boolean {
  if (typeof window === "undefined") return true;
  const raw = localStorage.getItem(BUTTON_VISIBLE_KEY);
  if (raw === null) return true;
  return raw === "true";
}

export function setTutorialButtonVisible(visible: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(BUTTON_VISIBLE_KEY, String(visible));
}
