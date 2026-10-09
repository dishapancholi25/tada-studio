"use client";

import { Loader2, Save, X } from "lucide-react";
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import Button from "@/components/ui/Button";
import { useToast } from "@/contexts/ToastContext";
import { useEscapeKey, useFocusTrap } from "@/hooks/useAccessibility";
import {
  type CreateGroupMcpConfigRequest,
  type GroupMcpConfig,
  groupMcpConfigsAPI,
} from "@/lib/admin-api";
import type { Group } from "@/types/api";

const OFFICIAL_PROVIDERS = [
  { value: "mcp_preset_github", label: "GitHub" },
  { value: "mcp_preset_atlassian", label: "Atlassian" },
  { value: "mcp_preset_databricks", label: "Databricks" },
  { value: "mcp_preset_databricks_devops", label: "Databricks DevOps" },
  { value: "mcp_preset_sharepoint", label: "SharePoint" },
  { value: "mcp_preset_onedrive", label: "OneDrive" },
  { value: "mcp_preset_notion", label: "Notion" },
];

interface Props {
  isOpen: boolean;
  config: GroupMcpConfig | null;
  groups: Group[];
  onClose: () => void;
  onSave: () => void;
}

export default function GroupMcpConfigDialog({
  isOpen,
  config,
  groups,
  onClose,
  onSave,
}: Props) {
  const { showToast } = useToast();
  const modalRef = useFocusTrap<HTMLDivElement>(isOpen);
  useEscapeKey(onClose);

  const isEditing = config !== null;

  // Form state
  const [serviceName, setServiceName] = useState(
    config?.service_name ?? OFFICIAL_PROVIDERS[0].value,
  );
  const [customServiceName, setCustomServiceName] = useState("");
  const [useCustom, setUseCustom] = useState(false);
  const [displayName, setDisplayName] = useState(config?.display_name ?? "");
  const [description, setDescription] = useState(config?.description ?? "");
  const [apiKey, setApiKey] = useState("");
  const [selectedGroupIds, setSelectedGroupIds] = useState<string[]>(
    config?.group_ids ?? [],
  );
  const [isActive, setIsActive] = useState(config?.is_active ?? true);
  const [saving, setSaving] = useState(false);

  // When editing, detect if service_name is custom
  useEffect(() => {
    if (config) {
      const isPreset = OFFICIAL_PROVIDERS.some(
        (p) => p.value === config.service_name,
      );
      if (!isPreset) {
        setUseCustom(true);
        setCustomServiceName(config.service_name);
      } else {
        setUseCustom(false);
        setServiceName(config.service_name);
      }
    }
  }, [config]);

  const effectiveServiceName = useCustom ? customServiceName : serviceName;

  const toggleGroup = (groupId: string) => {
    setSelectedGroupIds((prev) =>
      prev.includes(groupId)
        ? prev.filter((id) => id !== groupId)
        : [...prev, groupId],
    );
  };

  const handleSave = async () => {
    if (!effectiveServiceName) {
      showToast("error", "Service name is required");
      return;
    }
    if (selectedGroupIds.length === 0) {
      showToast("error", "At least one group must be assigned");
      return;
    }

    setSaving(true);
    try {
      const body: CreateGroupMcpConfigRequest = {
        service_name: effectiveServiceName,
        display_name: displayName || undefined,
        description: description || undefined,
        group_ids: selectedGroupIds,
        is_active: isActive,
      };

      // Only send api_key if user entered one
      if (apiKey.trim()) {
        body.api_key = apiKey.trim();
      }

      if (isEditing && config) {
        await groupMcpConfigsAPI.update(config.id, body);
        showToast("success", "Group MCP configuration updated");
      } else {
        await groupMcpConfigsAPI.create(body);
        showToast("success", "Group MCP configuration created");
      }
      onSave();
    } catch (err) {
      showToast(
        "error",
        err instanceof Error ? err.message : "Failed to save configuration",
      );
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const content = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.6)" }}
    >
      <div
        ref={modalRef}
        className="relative w-full max-w-lg mx-4 rounded-2xl shadow-2xl flex flex-col max-h-[90vh]"
        style={{
          background: "var(--color-bg-primary)",
          border: "1px solid var(--color-border)",
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4 border-b"
          style={{ borderColor: "var(--color-border)" }}
        >
          <h2 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
            {isEditing
              ? "Edit Group MCP Configuration"
              : "Add Group MCP Configuration"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[color:var(--color-surface)] transition-colors"
          >
            <X className="w-5 h-5 text-[color:var(--color-text-muted)]" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
          {/* Service selection */}
          <div>
            <p className="block text-sm font-medium text-[color:var(--color-text-primary)] mb-2">
              MCP Tool / Integration
            </p>
            <div className="flex items-center gap-3 mb-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  checked={!useCustom}
                  onChange={() => setUseCustom(false)}
                  className="accent-[color:var(--color-accent)]"
                />
                <span className="text-[color:var(--color-text-primary)]">
                  Official preset
                </span>
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="radio"
                  checked={useCustom}
                  onChange={() => setUseCustom(true)}
                  className="accent-[color:var(--color-accent)]"
                />
                <span className="text-[color:var(--color-text-primary)]">
                  Custom MCP server
                </span>
              </label>
            </div>
            {!useCustom ? (
              <select
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--color-bg-secondary)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-primary)",
                }}
              >
                {OFFICIAL_PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={customServiceName}
                onChange={(e) => setCustomServiceName(e.target.value)}
                placeholder="e.g. mcp_server_my_tool"
                className="w-full px-3 py-2 rounded-lg text-sm"
                style={{
                  background: "var(--color-bg-secondary)",
                  border: "1px solid var(--color-border)",
                  color: "var(--color-text-primary)",
                }}
              />
            )}
          </div>

          {/* Display name */}
          <div>
            <label
              htmlFor="mcp-display-name"
              className="block text-sm font-medium text-[color:var(--color-text-primary)] mb-2"
            >
              Display Name
              <span className="text-[color:var(--color-text-muted)] font-normal ml-1">
                (optional)
              </span>
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              id="mcp-display-name"
              placeholder="e.g. GitHub (Engineering Team)"
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-primary)",
              }}
            />
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="mcp-description"
              className="block text-sm font-medium text-[color:var(--color-text-primary)] mb-2"
            >
              Description
              <span className="text-[color:var(--color-text-muted)] font-normal ml-1">
                (optional)
              </span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              id="mcp-description"
              placeholder="Brief description visible to group members"
              rows={2}
              className="w-full px-3 py-2 rounded-lg text-sm resize-none"
              style={{
                background: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-primary)",
              }}
            />
          </div>

          {/* Credentials */}
          <div>
            <label
              htmlFor="mcp-credentials"
              className="block text-sm font-medium text-[color:var(--color-text-primary)] mb-2"
            >
              Credentials
              {isEditing && config?.credentials_configured && (
                <span className="text-[color:var(--color-text-muted)] font-normal ml-1">
                  (leave blank to keep existing)
                </span>
              )}
            </label>
            <input
              id="mcp-credentials"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                isEditing && config?.credentials_configured
                  ? "••••••••••••"
                  : "API key or token"
              }
              className="w-full px-3 py-2 rounded-lg text-sm"
              style={{
                background: "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)",
                color: "var(--color-text-primary)",
              }}
            />
            <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
              Credentials are encrypted and never exposed to group members.
            </p>
          </div>

          {/* Group assignment */}
          <div>
            <p className="block text-sm font-medium text-[color:var(--color-text-primary)] mb-2">
              Assign to Groups
            </p>
            {groups.length === 0 ? (
              <p className="text-sm text-[color:var(--color-text-muted)]">
                No groups available. Create groups first.
              </p>
            ) : (
              <div
                className="rounded-lg overflow-y-auto max-h-40"
                style={{
                  background: "var(--color-bg-secondary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                {groups.map((group) => (
                  <label
                    key={group.id}
                    className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-[color:var(--color-surface)] transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedGroupIds.includes(group.id)}
                      onChange={() => toggleGroup(group.id)}
                      className="accent-[color:var(--color-accent)]"
                    />
                    <span className="text-sm text-[color:var(--color-text-primary)]">
                      {group.name}
                    </span>
                    {group.description && (
                      <span className="text-xs text-[color:var(--color-text-muted)] truncate flex-1">
                        {group.description}
                      </span>
                    )}
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Active toggle */}
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="accent-[color:var(--color-accent)]"
            />
            <span className="text-sm text-[color:var(--color-text-primary)]">
              Active (group members can use this tool immediately)
            </span>
          </label>
        </div>

        {/* Footer */}
        <div
          className="flex items-center justify-end gap-3 px-6 py-4 border-t"
          style={{ borderColor: "var(--color-border)" }}
        >
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving}
            icon={
              saving ? (
                <Loader2 className="w-4 h-4 animate-spin text-orange-500" />
              ) : (
                <Save className="w-4 h-4" />
              )
            }
          >
            {saving ? "Saving…" : isEditing ? "Update" : "Create"}
          </Button>
        </div>
      </div>
    </div>
  );

  return createPortal(content, document.body);
}
