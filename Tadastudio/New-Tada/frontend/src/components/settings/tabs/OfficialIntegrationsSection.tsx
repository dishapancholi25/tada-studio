"use client";

import {
  CheckCircle,
  ChevronRight,
  CircleDot,
  Loader2,
  Settings,
  User,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getProviderVisuals } from "@/components/icons/McpProviderIcons";
import Toggle from "@/components/ui/Toggle";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";
import { systemMcpIntegrationsAPI } from "@/lib/admin-api";
import {
  type McpIntegrationSummary,
  userSettingsAPI,
} from "@/lib/user-settings-api";
import McpIntegrationConfigModal from "../dialogs/McpIntegrationConfigModal";

const OFFICIAL_PROVIDERS = [
  "github",
  "atlassian",
  "databricks",
  "databricks_devops",
  "sharepoint",
  "onedrive",
  "notion",
  "fabric",
] as const;

type OfficialProvider = (typeof OFFICIAL_PROVIDERS)[number];

export default function OfficialIntegrationsSection() {
  const { showToast } = useToast();
  const { user: authUser } = useAuth();
  const isAdmin =
    authUser?.role === "ADMIN" || (authUser as any)?.is_admin === true;

  const [scope, setScope] = useState<"personal" | "system">(
    isAdmin ? "system" : "personal",
  );
  const [integrations, setIntegrations] = useState<McpIntegrationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [togglingProvider, setTogglingProvider] = useState<string | null>(null);
  const [configureProvider, setConfigureProvider] = useState<string | null>(
    null,
  );

  const loadIntegrations = useCallback(async () => {
    try {
      setLoading(true);
      const data =
        scope === "system"
          ? await systemMcpIntegrationsAPI.list()
          : await userSettingsAPI.listMcpIntegrations();
      setIntegrations(data);
    } catch (err) {
      console.error("Failed to load integrations:", err);
      showToast("error", "Failed to load integrations");
    } finally {
      setLoading(false);
    }
  }, [scope, showToast]);

  useEffect(() => {
    loadIntegrations();
  }, [loadIntegrations]);

  const handleToggle = useCallback(
    async (provider: string) => {
      if (scope === "system") return; // System toggle not supported via simple toggle
      setTogglingProvider(provider);
      try {
        await userSettingsAPI.toggleMcpIntegration(provider);
        // Optimistic update
        setIntegrations((prev) =>
          prev.map((i) =>
            i.provider === provider ? { ...i, is_active: !i.is_active } : i,
          ),
        );
      } catch (err) {
        console.error("Failed to toggle integration:", err);
        showToast("error", "Failed to toggle integration");
      } finally {
        setTogglingProvider(null);
      }
    },
    [scope, showToast],
  );

  const handleConfigureDone = useCallback(() => {
    setConfigureProvider(null);
    loadIntegrations();
  }, [loadIntegrations]);

  const getStatusBadge = (integration: McpIntegrationSummary) => {
    if (integration.is_configured && integration.is_active) {
      return {
        label: "Configured",
        dotColor: "rgb(13, 169, 49)",
        bgColor: "rgba(13, 169, 49, 0.1)",
        borderColor: "rgba(13, 169, 49, 0.3)",
      };
    }
    if (integration.is_configured && !integration.is_active) {
      return {
        label: "Disabled",
        dotColor: "rgb(156, 163, 175)",
        bgColor: "rgba(156, 163, 175, 0.1)",
        borderColor: "rgba(156, 163, 175, 0.3)",
      };
    }
    if (integration.has_system_default) {
      return {
        label: "System Default",
        dotColor: "rgb(59, 130, 246)",
        bgColor: "rgba(59, 130, 246, 0.1)",
        borderColor: "rgba(59, 130, 246, 0.3)",
      };
    }
    if (integration.has_group_default) {
      return {
        label: "Via Group",
        dotColor: "rgb(168, 85, 247)",
        bgColor: "rgba(168, 85, 247, 0.1)",
        borderColor: "rgba(168, 85, 247, 0.3)",
      };
    }
    return {
      label: "Not Configured",
      dotColor: "rgb(107, 114, 128)",
      bgColor: "rgba(107, 114, 128, 0.1)",
      borderColor: "rgba(107, 114, 128, 0.3)",
    };
  };

  return (
    <div className="mb-8">
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Official Integrations
          </h3>
          <p className="text-sm text-slate-600 mt-0.5">
            Pre-built integrations with popular services. Configure once, use
            across all workflows.
          </p>
        </div>
        {isAdmin && (
          <div className="flex items-center gap-2">
            {(["personal", "system"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setScope(s)}
                className={`flex items-center gap-1.5 whitespace-nowrap rounded-[4px] px-3 py-1.5 text-sm font-medium transition-colors duration-200 ${
                  scope === s
                    ? "border border-orange-500 bg-white text-orange-900"
                    : "border border-transparent text-slate-700 hover:border-slate-200 hover:bg-slate-50"
                }`}
              >
                {s === "personal" ? (
                  <User className="w-3.5 h-3.5" />
                ) : (
                  <Settings className="w-3.5 h-3.5" />
                )}
                <span>{s === "personal" ? "Personal" : "System-wide"}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Integration cards */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-orange-600" />
          <span className="ml-2 text-sm text-slate-600">
            Loading integrations...
          </span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {OFFICIAL_PROVIDERS.map((provider) => {
            const integration = integrations.find(
              (i) => i.provider === provider,
            );
            const visuals = getProviderVisuals(provider);
            const IconComponent = visuals.icon;
            const status = getStatusBadge(
              integration || {
                provider,
                display_name: visuals.label,
                is_configured: false,
                is_active: false,
                has_system_default: false,
                has_group_default: false,
                group_names: [],
                tool_count: null,
                tool_permissions: {},
              },
            );

            return (
              <div
                key={provider}
                className="group relative cursor-pointer rounded-[4px] border border-slate-200 bg-white shadow-[0_18px_50px_rgba(15,23,42,0.06)] transition-colors duration-200 hover:border-orange-400"
                onClick={() => setConfigureProvider(provider)}
              >
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="p-2 rounded-lg"
                        style={{
                          background: `rgba(${visuals.colorRgb}, 0.15)`,
                        }}
                      >
                        <IconComponent
                          size={20}
                          style={{
                            color: visuals.color,
                          }}
                        />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">
                          {visuals.label}
                        </div>
                        <div className="text-xs text-slate-600 mt-0.5 line-clamp-1">
                          {visuals.description}
                        </div>
                      </div>
                    </div>
                    <ChevronRight className="mt-1 h-4 w-4 text-slate-400 opacity-0 transition-opacity group-hover:opacity-100 group-hover:text-slate-900" />
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
                    {/* Status badge */}
                    <span
                      className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full"
                      style={{
                        color: status.dotColor,
                        background: status.bgColor,
                        border: `1px solid ${status.borderColor}`,
                      }}
                    >
                      <CircleDot className="w-3 h-3" />
                      {status.label}
                    </span>

                    {/* Toggle (only for configured personal integrations) */}
                    {integration?.is_configured && scope === "personal" && (
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                        }}
                      >
                        <Toggle
                          checked={integration.is_active}
                          onChange={() => handleToggle(provider)}
                          size="sm"
                          disabled={togglingProvider === provider}
                          activeColor={visuals.color}
                        />
                      </div>
                    )}

                    {/* Tool count */}
                    {integration?.tool_count ? (
                      <span className="text-xs text-slate-600">
                        {integration.tool_count} tools
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Config modal */}
      {configureProvider && (
        <McpIntegrationConfigModal
          provider={configureProvider}
          scope={scope}
          onClose={() => setConfigureProvider(null)}
          onSaved={handleConfigureDone}
        />
      )}
    </div>
  );
}
