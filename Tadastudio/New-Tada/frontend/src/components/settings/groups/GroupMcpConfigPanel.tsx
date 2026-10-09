"use client";

import {
  Edit,
  Loader2,
  Plus,
  Shield,
  Trash2,
  Users,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import { useToast } from "@/contexts/ToastContext";
import { type GroupMcpConfig, groupMcpConfigsAPI } from "@/lib/admin-api";
import { api } from "@/lib/api";
import type { Group } from "@/types/api";
import GroupMcpConfigDialog from "./GroupMcpConfigDialog";

export default function GroupMcpConfigPanel() {
  const { showToast } = useToast();
  const [configs, setConfigs] = useState<GroupMcpConfig[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<GroupMcpConfig | null>(
    null,
  );
  const [deletingConfigId, setDeletingConfigId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // biome-ignore lint/correctness/useExhaustiveDependencies: load on mount only
  useEffect(() => {
    void loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [cfgs, grpData] = await Promise.all([
        groupMcpConfigsAPI.list(),
        api.getGroups({ limit: 200 }),
      ]);
      setConfigs(cfgs);
      setGroups(grpData.groups);
    } catch (err) {
      showToast(
        "error",
        err instanceof Error ? err.message : "Failed to load group MCP configs",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingConfig(null);
    setDialogOpen(true);
  };

  const handleEdit = (config: GroupMcpConfig) => {
    setEditingConfig(config);
    setDialogOpen(true);
  };

  const handleDeleteClick = (configId: string) => {
    setDeletingConfigId(configId);
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = async () => {
    if (!deletingConfigId) return;
    try {
      await groupMcpConfigsAPI.delete(deletingConfigId);
      showToast("success", "Group MCP configuration deleted");
      await loadData();
    } catch (err) {
      showToast("error", "Failed to delete group MCP configuration");
    } finally {
      setDeletingConfigId(null);
    }
  };

  const handleSaveComplete = async () => {
    setDialogOpen(false);
    await loadData();
  };

  const groupNamesForConfig = (cfg: GroupMcpConfig): string => {
    if (cfg.group_names.length === 0) return "No groups assigned";
    return cfg.group_names.join(", ");
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-purple-500/20 to-blue-500/20 rounded-lg">
            <Shield className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text-primary)]">
              Group MCP Tool Configurations
            </h3>
            <p className="text-sm text-[color:var(--color-text-muted)] mt-0.5">
              Provision MCP tool access for specific groups. Members
              automatically get access — no individual setup required.
            </p>
          </div>
        </div>
        {!loading && (
          <Button onClick={handleAdd} icon={<Plus className="w-4 h-4" />}>
            Add Config
          </Button>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-[color:var(--color-accent)]" />
        </div>
      )}

      {/* Empty */}
      {!loading && configs.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
          <div className="p-3 bg-[color:var(--color-bg-secondary)] rounded-full mb-3">
            <Wrench className="w-8 h-8 text-[color:var(--color-text-muted)]" />
          </div>
          <p className="text-[color:var(--color-text-muted)] mb-4">
            No group MCP configurations yet. Create one to provision a tool for
            a group of users.
          </p>
          <Button onClick={handleAdd} icon={<Plus className="w-4 h-4" />}>
            Add Group MCP Config
          </Button>
        </div>
      )}

      {/* Config list */}
      {!loading && configs.length > 0 && (
        <div className="space-y-3">
          {configs.map((cfg) => (
            <div
              key={cfg.id}
              className="flex items-start justify-between gap-4 p-4 rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-bg-secondary)]/60"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-[color:var(--color-text-primary)]">
                    {cfg.display_name || cfg.service_name}
                  </span>
                  <span
                    className="px-2 py-0.5 text-xs rounded-full font-mono"
                    style={{
                      background: "rgba(99,102,241,0.12)",
                      color: "rgb(129,140,248)",
                      border: "1px solid rgba(99,102,241,0.3)",
                    }}
                  >
                    {cfg.service_name}
                  </span>
                  {cfg.is_active ? (
                    <span
                      className="px-2 py-0.5 text-xs rounded-full"
                      style={{
                        background: "rgba(16,185,129,0.1)",
                        color: "rgb(16,185,129)",
                        border: "1px solid rgba(16,185,129,0.3)",
                      }}
                    >
                      Active
                    </span>
                  ) : (
                    <span
                      className="px-2 py-0.5 text-xs rounded-full"
                      style={{
                        background: "rgba(107,114,128,0.1)",
                        color: "rgb(156,163,175)",
                        border: "1px solid rgba(107,114,128,0.3)",
                      }}
                    >
                      Inactive
                    </span>
                  )}
                </div>
                {cfg.description && (
                  <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
                    {cfg.description}
                  </p>
                )}
                <div className="flex items-center gap-1 mt-2 text-sm text-[color:var(--color-text-muted)]">
                  <Users className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="truncate">{groupNamesForConfig(cfg)}</span>
                </div>
                {cfg.credentials_configured && (
                  <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                    Credentials configured
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => handleEdit(cfg)}
                  className="p-2 rounded-lg transition-all hover:bg-[color:var(--color-surface)]"
                  style={{
                    color: "var(--color-text-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                  title="Edit configuration"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={() => handleDeleteClick(cfg.id)}
                  className="p-2 rounded-lg transition-all hover:bg-red-500/10"
                  style={{
                    color: "rgb(239,68,68)",
                    border: "1px solid rgba(239,68,68,0.3)",
                  }}
                  title="Delete configuration"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      {dialogOpen && (
        <GroupMcpConfigDialog
          isOpen={dialogOpen}
          config={editingConfig}
          groups={groups}
          onClose={() => {
            setDialogOpen(false);
            setEditingConfig(null);
          }}
          onSave={handleSaveComplete}
        />
      )}

      {/* Delete Confirm */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => {
          setShowDeleteConfirm(false);
          setDeletingConfigId(null);
        }}
        onConfirm={handleConfirmDelete}
        title="Delete Group MCP Configuration"
        message="Are you sure you want to delete this configuration? All group members will immediately lose access to this tool on their next workflow run."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
    </div>
  );
}
