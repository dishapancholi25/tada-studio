import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock dependencies before importing the module under test
vi.mock("@/stores/graphStore", () => ({
  useGraphStore: {
    getState: vi.fn(() => ({
      clearGraph: vi.fn(),
    })),
  },
}));

vi.mock("@/tutorial/persistence", () => ({
  resetTutorialCache: vi.fn(),
}));

import { useGraphStore } from "@/stores/graphStore";
import { resetTutorialCache } from "@/tutorial/persistence";
import {
  broadcastUserSwitch,
  clearUserSession,
  subscribeToUserSwitch,
} from "./user-session";

describe("clearUserSession", () => {
  beforeEach(() => {
    // Populate localStorage with user-specific keys
    localStorage.setItem("eval_default_judge_model", "gpt-4");
    localStorage.setItem("eval_default_weight_cost", "0.25");
    localStorage.setItem("agenticstudio-color-theme", "expose");
    localStorage.setItem("agenticstudio-graph-storage", '{"state":{}}');
    localStorage.setItem("as-welcome-dismissed", "true");
    localStorage.setItem("as-tutorial-button-visible", "true");
    localStorage.setItem("execution-viewer-data", "{}");
    localStorage.setItem("return-from-viewer", "true");
    localStorage.setItem("agent-panel-show-tips", "true");
    localStorage.setItem("recentNodeSelections", "[]");
    localStorage.setItem("patBannerDismissed", "true");
    // Non-user key that should be preserved
    localStorage.setItem("unrelated-key", "keep-me");

    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("removes all eval_ prefixed keys", () => {
    clearUserSession();
    expect(localStorage.getItem("eval_default_judge_model")).toBeNull();
    expect(localStorage.getItem("eval_default_weight_cost")).toBeNull();
  });

  it("removes agenticstudio- prefixed keys", () => {
    clearUserSession();
    expect(localStorage.getItem("agenticstudio-color-theme")).toBeNull();
    expect(localStorage.getItem("agenticstudio-graph-storage")).toBeNull();
  });

  it("removes as- prefixed keys", () => {
    clearUserSession();
    expect(localStorage.getItem("as-welcome-dismissed")).toBeNull();
    expect(localStorage.getItem("as-tutorial-button-visible")).toBeNull();
  });

  it("removes exact-match keys", () => {
    clearUserSession();
    expect(localStorage.getItem("execution-viewer-data")).toBeNull();
    expect(localStorage.getItem("return-from-viewer")).toBeNull();
    expect(localStorage.getItem("agent-panel-show-tips")).toBeNull();
    expect(localStorage.getItem("recentNodeSelections")).toBeNull();
    expect(localStorage.getItem("patBannerDismissed")).toBeNull();
  });

  it("does not remove unrelated keys", () => {
    clearUserSession();
    expect(localStorage.getItem("unrelated-key")).toBe("keep-me");
  });

  it("does not throw when storage is already empty", () => {
    localStorage.clear();
    expect(() => clearUserSession()).not.toThrow();
  });

  it("calls clearGraph on the graph store", () => {
    const mockClearGraph = vi.fn();
    vi.mocked(useGraphStore.getState).mockReturnValue({
      clearGraph: mockClearGraph,
    } as never);
    clearUserSession();
    expect(mockClearGraph).toHaveBeenCalledOnce();
  });

  it("calls resetTutorialCache", () => {
    clearUserSession();
    expect(resetTutorialCache).toHaveBeenCalledOnce();
  });

  it("dispatches the agentic-studio:user-clear custom event", () => {
    const handler = vi.fn();
    window.addEventListener("agentic-studio:user-clear", handler);
    clearUserSession();
    window.removeEventListener("agentic-studio:user-clear", handler);
    expect(handler).toHaveBeenCalledOnce();
  });
});

describe("broadcastUserSwitch", () => {
  afterEach(() => {
    localStorage.clear();
  });

  it("does not throw when called", () => {
    expect(() => broadcastUserSwitch()).not.toThrow();
  });
});

describe("subscribeToUserSwitch", () => {
  it("returns a cleanup function", () => {
    const cleanup = subscribeToUserSwitch(vi.fn());
    expect(typeof cleanup).toBe("function");
    cleanup();
  });

  it("calls onSwitch when storage sentinel key event fires (fallback path)", () => {
    // Temporarily delete BroadcastChannel so the "in" check returns false
    const descriptor = Object.getOwnPropertyDescriptor(
      window,
      "BroadcastChannel",
    );
    // biome-ignore lint/performance/noDelete: required for test isolation
    delete (window as Window & { BroadcastChannel?: unknown }).BroadcastChannel;

    const onSwitch = vi.fn();
    const cleanup = subscribeToUserSwitch(onSwitch);

    // Simulate the storage event from another tab
    window.dispatchEvent(
      new StorageEvent("storage", { key: "agenticstudio-user-switch" }),
    );

    expect(onSwitch).toHaveBeenCalledOnce();
    cleanup();

    // Restore
    if (descriptor) {
      Object.defineProperty(window, "BroadcastChannel", descriptor);
    }
  });
});
