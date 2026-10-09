"use client";

import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
} from "react";

export type ColorTheme = "mashreq" | "expose";

interface ColorThemeContextValue {
  theme: ColorTheme;
  setTheme: (theme: ColorTheme) => void;
  toggleTheme: () => void;
  getLogo: () => string;
}

const ColorThemeContext = createContext<ColorThemeContextValue | undefined>(
  undefined,
);

const STORAGE_KEY = "agenticstudio-color-theme";
const THEME_COOKIE = "agenticstudio-color-theme";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year

// Theme is locked to "mashreq" — any stored / legacy value resolves to it.
const normaliseTheme = (_raw: string | null | undefined): ColorTheme => {
  return "mashreq";
};

// Build the cookie string with industry-standard attributes.
// SameSite=Lax: safe for top-level navigations, blocks CSRF.
// Secure flag is appended automatically on HTTPS.
const buildCookieString = (theme: ColorTheme): string => {
  const secure =
    typeof location !== "undefined" && location.protocol === "https:"
      ? "; Secure"
      : "";
  return `${THEME_COOKIE}=${theme}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax${secure}`;
};

// Read theme from localStorage (client-side persistence).
const getStoredTheme = (fallback: ColorTheme): ColorTheme => {
  if (typeof window === "undefined") return fallback;
  try {
    return normaliseTheme(window.localStorage.getItem(STORAGE_KEY)) ?? fallback;
  } catch {
    return fallback;
  }
};

interface ColorThemeProviderProps {
  children: React.ReactNode;
  // Passed from the server via cookie so the first paint matches.
  initialTheme?: ColorTheme;
}

export function ColorThemeProvider({
  children,
  initialTheme = "mashreq",
}: ColorThemeProviderProps) {
  const [theme, setThemeState] = useState<ColorTheme>(initialTheme);

  const applyTheme = useCallback((_nextTheme: ColorTheme) => {
    // Theme is locked to "mashreq" — ignore any other requested value.
    const nextTheme: ColorTheme = "mashreq";
    setThemeState((prev) => (prev === nextTheme ? prev : nextTheme));

    if (typeof document !== "undefined") {
      // data-color-theme drives all CSS variable blocks in globals.css.
      document.documentElement.dataset.colorTheme = nextTheme;
      // Cookie keeps the server in sync so SSR can read it for first paint.
      document.cookie = buildCookieString(nextTheme);
    }

    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(STORAGE_KEY, nextTheme);
      } catch {
        // Ignore — storage may be blocked (private mode, quota, etc.).
      }
    }
  }, []);

  // useLayoutEffect avoids a visible flash: runs synchronously after DOM paint
  // but before the browser has a chance to display the wrong theme.
  useLayoutEffect(() => {
    // Client localStorage wins over the SSR cookie so users who explicitly
    // changed their theme don't get reset on every hard reload.
    const clientTheme = getStoredTheme(initialTheme);
    applyTheme(clientTheme);
  }, [applyTheme, initialTheme]);

  // Allow the auth logout flow to reset theme to the default.
  useEffect(() => {
    const reset = () => applyTheme("mashreq");
    window.addEventListener("agentic-studio:user-clear", reset);
    return () => window.removeEventListener("agentic-studio:user-clear", reset);
  }, [applyTheme]);

  const value = useMemo<ColorThemeContextValue>(
    () => ({
      theme,
      setTheme: applyTheme,
      // Toggle is a no-op — only the "mashreq" theme is supported.
      toggleTheme: () => applyTheme("mashreq"),
      getLogo: () => "/logos/AgenticStudioSynechron.svg",
    }),
    [applyTheme, theme],
  );

  return (
    <ColorThemeContext.Provider value={value}>
      {children}
    </ColorThemeContext.Provider>
  );
}

export function useColorTheme(): ColorThemeContextValue {
  const context = useContext(ColorThemeContext);
  if (!context) {
    throw new Error("useColorTheme must be used within a ColorThemeProvider");
  }
  return context;
}
