"use client";

import type React from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { setAuthenticatedApiClientForMain } from "@/lib/api";
import { setAuthenticatedApiClient } from "@/lib/config-api";
import { runtimeConfig } from "@/lib/runtime-config";
import {
  broadcastUserSwitch,
  clearUserSession,
  subscribeToUserSwitch,
} from "@/lib/user-session";
import type { AuthContextType, AuthUser } from "@/types/auth";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const SKIP_AUTH = process.env.NEXT_PUBLIC_SKIP_AUTH === "true";
const SKIP_AUTH_SESSION_KEY = "tada_skip_auth_session";

interface AuthProviderProps {
  children: React.ReactNode;
}

const buildDisplayName = (
  firstName?: string,
  lastName?: string,
  fallback?: string,
) => {
  const computed = `${firstName || ""} ${lastName || ""}`.trim();
  return computed || fallback || undefined;
};

const getUserKey = (u: AuthUser | null): string | null =>
  u?.sub ?? u?.email ?? null;

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [apiReady, setApiReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const prevUserKeyRef = useRef<string | null>(null);

  const syncUserWithBackend = useCallback(async (): Promise<boolean> => {
    // ── Skip-auth mode: read session from localStorage, no API call ──
    if (SKIP_AUTH) {
      try {
        const raw = localStorage.getItem(SKIP_AUTH_SESSION_KEY);
        if (!raw) return false;
        const session = JSON.parse(raw) as AuthUser;
        setUser(session);
        setIsAuthenticated(true);
        return true;
      } catch {
        return false;
      }
    }

    try {
      const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/auth/me`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });

      if (!response.ok) {
        setIsAuthenticated(false);
        setUser(null);
        return false;
      }

      const data = await response.json();
      const backendUser = data?.user;
      const claims = data?.claims ?? {};

      const firstName =
        backendUser?.first_name ?? claims.first_name ?? claims.given_name;
      const lastName =
        backendUser?.last_name ?? claims.last_name ?? claims.family_name;
      const email = backendUser?.email ?? claims.email;
      const displayName =
        backendUser?.name ??
        claims.name ??
        buildDisplayName(firstName, lastName, email ?? claims.sub);

      const resolvedUser: AuthUser | null =
        backendUser || claims.sub || email
          ? {
              email,
              first_name: firstName,
              last_name: lastName,
              name: displayName,
              sub: claims.sub,
              preferred_username: claims.preferred_username,
              given_name: claims.given_name ?? claims.first_name ?? firstName,
              family_name: claims.family_name ?? claims.last_name ?? lastName,
              tid: claims.tid,
              oid: claims.oid,
              auth_source: claims.auth_source,
              is_admin: backendUser?.is_admin ?? claims.is_admin ?? false,
              groups: backendUser?.groups ?? claims.groups ?? [],
              role: backendUser?.role,
              is_pending: backendUser?.is_pending ?? false,
            }
          : null;

      if (resolvedUser) {
        setUser(resolvedUser);
      }

      setIsAuthenticated(true);
      return true;
    } catch (error) {
      console.error("Error while syncing user with backend:", error);
      return false;
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    const initialise = async () => {
      try {
        if (!isMounted) {
          return;
        }

				// On the login page there is no valid session yet — skip the
				// /api/auth/me call to avoid a wasted request / potential
				// redirect loop through nginx's auth_request.
				if (
					typeof window !== "undefined" &&
					window.location.pathname === "/login"
				) {
					if (isMounted) setLoading(false);
					return;
				}

				await syncUserWithBackend();
			} catch (error) {
				console.error("Failed to initialise authentication:", error);
			} finally {
				if (isMounted) setLoading(false);
			}
		};

    initialise();

    return () => {
      isMounted = false;
    };
  }, [syncUserWithBackend]);

  // Detect when the authenticated identity changes (user switch)
  useEffect(() => {
    const currentKey = getUserKey(user);

    if (
      prevUserKeyRef.current !== null &&
      currentKey !== null &&
      prevUserKeyRef.current !== currentKey
    ) {
      console.info(
        "[AuthContext] User identity changed — triggering session clear",
        {
          previous: prevUserKeyRef.current,
          next: currentKey,
        },
      );
      clearUserSession();
      broadcastUserSwitch();
    }

    if (currentKey !== null) {
      prevUserKeyRef.current = currentKey;
    }
  }, [user]);

  // Listen for user-switch signals broadcast from other tabs
  useEffect(() => {
    return subscribeToUserSwitch(() => {
      clearUserSession();
    });
  }, []);

  useEffect(() => {
    const createApiClient = () => {
      const apiCall = async (endpoint: string, options: RequestInit = {}) => {
        const headers = new Headers({
          "Content-Type": "application/json",
          ...(options.headers as Record<string, string>),
        });

        const apiBaseUrl = await runtimeConfig.getApiBaseUrl();
        const url = endpoint.startsWith("http")
          ? endpoint
          : `${apiBaseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

        const response = await fetch(url, {
          ...options,
          headers,
          credentials: options.credentials ?? "include",
        });

        if (!response.ok) {
          if (response.status === 401) {
            setIsAuthenticated(false);
            throw new Error("Unauthorised - authentication failed");
          }

          // Try to parse error response body for detailed error message
          let errorDetail = `API call failed: ${response.statusText}`;
          try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorData.message || errorDetail;
          } catch (parseError) {
            // If JSON parsing fails, use the default error message
          }
          throw new Error(errorDetail);
        }

        // Handle 204 No Content responses (e.g., DELETE operations)
        if (response.status === 204) {
          return {};
        }

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const text = await response.text();
          // Handle empty JSON responses
          if (!text) return {};
          return JSON.parse(text);
        }

        return await response.text();
      };

      return {
        get: (endpoint: string, options?: Omit<RequestInit, "method">) =>
          apiCall(endpoint, { ...options, method: "GET" }),

        post: (
          endpoint: string,
          data?: unknown,
          options?: Omit<RequestInit, "method" | "body">,
        ) =>
          apiCall(endpoint, {
            ...options,
            method: "POST",
            body: data ? JSON.stringify(data) : undefined,
          }),

        put: (
          endpoint: string,
          data?: unknown,
          options?: Omit<RequestInit, "method" | "body">,
        ) =>
          apiCall(endpoint, {
            ...options,
            method: "PUT",
            body: data ? JSON.stringify(data) : undefined,
          }),

        patch: (
          endpoint: string,
          data?: unknown,
          options?: Omit<RequestInit, "method" | "body">,
        ) =>
          apiCall(endpoint, {
            ...options,
            method: "PATCH",
            body: data ? JSON.stringify(data) : undefined,
          }),

        delete: (endpoint: string, options?: Omit<RequestInit, "method">) =>
          apiCall(endpoint, { ...options, method: "DELETE" }),
      };
    };

    const apiClient = createApiClient();
    setAuthenticatedApiClient(apiClient);
    setAuthenticatedApiClientForMain(apiClient);
    setApiReady(true);
  }, [isAuthenticated]);

  const logout = async (): Promise<void> => {
    if (SKIP_AUTH) {
      localStorage.removeItem(SKIP_AUTH_SESSION_KEY);
      setIsAuthenticated(false);
      setUser(null);
      setApiReady(false);
      prevUserKeyRef.current = null;
      window.location.href = "/login";
      return;
    }

    const authSource = user?.auth_source;
    clearUserSession();
    broadcastUserSwitch();
    setIsAuthenticated(false);
    setUser(null);
    setApiReady(false);
    prevUserKeyRef.current = null;

    if (authSource === "oauth_proxy") {
      window.location.href = "/oauth2/sign_out?rd=/";
    } else if (authSource === "basic_auth") {
      // Clear the browser's cached basic auth credentials by sending a
      // request with invalid credentials, then redirect to re-prompt login.
      const xhr = new XMLHttpRequest();
      xhr.open("GET", "/", true, "logout", "logout");
      xhr.onloadend = () => {
        window.location.href = "/";
      };
      xhr.send();
    } else {
      window.location.href = "/";
    }
  };

  const value: AuthContextType = {
    isAuthenticated,
    user,
    apiReady,
    loading,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
