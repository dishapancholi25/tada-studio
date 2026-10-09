/**
 * Collaborative editing hook using Yjs
 * Enables real-time sync between multiple users on the same workflow
 */

import { useEffect, useCallback, useState, useRef } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";
import type { Node, Edge } from "reactflow";
import { runtimeConfig } from "@/lib/runtime-config";
import type { WorkflowRole } from "@/lib/api";
import { debugWebSocket, warnWebSocket } from "@/lib/websocket-debug";

// Get WebSocket URL dynamically based on runtime configuration
async function getCollabWsUrl(): Promise<string> {
  const config = await runtimeConfig.getConfig();

  if (config.deployment === "separate-domains" && config.apiUrl) {
    // For separate domains deployment, use the backend URL directly
    const backendUrl = new URL(config.apiUrl);
    const protocol = backendUrl.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${backendUrl.host}/api/collab`;
  } else {
    // For reverse proxy deployment, use current host
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${protocol}//${host}/api/collab`;
  }
}

export type { WorkflowRole } from "@/lib/api";

export interface CollabUser {
  id: string;
  name: string;
  color: string;
  role: WorkflowRole;
  cursor?: { x: number; y: number } | null;
}

export interface UseCollaborationOptions {
  roomId: string;
  userName?: string;
  userRole?: WorkflowRole;
  enabled?: boolean;
}

export interface UseCollaborationReturn {
  isConnected: boolean;
  isReadOnly: boolean;
  users: CollabUser[];
  syncNodes: (nodes: Node[]) => void;
  syncEdges: (edges: Edge[]) => void;
  updateCursor: (position: { x: number; y: number }) => void;
}

interface ProviderConnectionEvent {
	code?: number;
	reason?: string;
	type?: string;
	wasClean?: boolean;
}

// Generate user initials from name (e.g., "Abid.dasurkar" -> "AD")
export function getInitials(name: string): string {
  return name
    .split(/[.\s_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

// User colors for visual distinction
const USER_COLORS = [
  "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
  "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
  "#6C5CE7", "#FF7675", "#74B9FF", "#A29BFE",
];

const getRandomColor = () => USER_COLORS[Math.floor(Math.random() * USER_COLORS.length)];

export function useCollaboration({
  roomId,
  userName = "Anonymous",
  userRole = "viewer",
  enabled = true,
}: UseCollaborationOptions): UseCollaborationReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [users, setUsers] = useState<CollabUser[]>([]);
  const isReadOnly = userRole === "viewer";

  const ydocRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<WebsocketProvider | null>(null);
  const yNodesRef = useRef<Y.Map<Node> | null>(null);
  const yEdgesRef = useRef<Y.Map<Edge> | null>(null);

  useEffect(() => {
    // console.log(`[Collab] Hook initialized - enabled: ${enabled}, roomId: ${roomId}`);

    if (!enabled || !roomId) {
      // console.log(`[Collab] Skipping - enabled: ${enabled}, roomId: ${roomId}`);
      return;
    }

    let ydoc: Y.Doc | null = null;
    let provider: WebsocketProvider | null = null;
    let cancelled = false;

    // Initialize connection asynchronously
    const initConnection = async () => {
      const wsUrl = await getCollabWsUrl();
      if (cancelled) return;

      debugWebSocket("CollabWS", "Connecting", {
        wsUrl,
        room: `workflow-${roomId}`,
        userRole,
        userName,
      });

      ydoc = new Y.Doc();
      provider = new WebsocketProvider(wsUrl, `workflow-${roomId}`, ydoc);

      const yNodes = ydoc.getMap<Node>("nodes");
      const yEdges = ydoc.getMap<Edge>("edges");

      ydocRef.current = ydoc;
      providerRef.current = provider;
      yNodesRef.current = yNodes;
      yEdgesRef.current = yEdges;

      const userColor = getRandomColor();
      provider.awareness.setLocalStateField("user", {
        name: userName,
        color: userColor,
        role: userRole,
      });
      // console.log(`[Collab] User awareness set - name: ${userName}, color: ${userColor}, role: ${userRole}`);

      provider.on("status", (event: { status: string }) => {
        setIsConnected(event.status === "connected");
        debugWebSocket("CollabWS", "Status changed", {
          status: event.status,
          room: `workflow-${roomId}`,
        });
      });

      // Log sync state changes
      provider.on("sync", (isSynced: boolean) => {
        debugWebSocket("CollabWS", "Sync state changed", {
          isSynced,
          room: `workflow-${roomId}`,
        });
      });

      const debugProvider = provider as WebsocketProvider & {
        on(
          eventName: "connection-error" | "connection-close",
          handler: (event: ProviderConnectionEvent) => void,
        ): void;
      };

      debugProvider.on("connection-error", (event) => {
        warnWebSocket("CollabWS", "Connection error", {
          room: `workflow-${roomId}`,
          wsUrl,
          eventType: event?.type,
        });
      });

      debugProvider.on("connection-close", (event) => {
        warnWebSocket("CollabWS", "Connection closed", {
          room: `workflow-${roomId}`,
          wsUrl,
          code: event?.code,
          reason: event?.reason,
          wasClean: event?.wasClean,
        });
      });

      const updateUsers = () => {
        const states = provider!.awareness.getStates();
        // Use Map to deduplicate by user name (Google Docs style - 1 cursor per user)
        const userMap = new Map<string, CollabUser>();
        const localUser = provider!.awareness.getLocalState()?.user;

        states.forEach((state, clientId) => {
          if (clientId !== provider!.awareness.clientID && state.user) {
            const userName = state.user.name;
            // Skip if this is the same user as local (different tab, same user)
            if (localUser && userName === localUser.name) {
              return;
            }
            // Keep the most recent cursor position for each unique user
            const existing = userMap.get(userName);
            if (!existing || (state.cursor && (!existing.cursor || state.cursor))) {
              userMap.set(userName, {
                id: userName, // Use name as ID for deduplication
                name: userName,
                color: state.user.color,
                role: state.user.role || "viewer",
                cursor: state.cursor,
              });
            }
          }
        });

        setUsers(Array.from(userMap.values()));
      };

      provider.awareness.on("change", updateUsers);

      yNodes.observe((event) => {
        if (event.transaction.local) return;

        const nodes = Array.from(yNodes.values());
        window.dispatchEvent(
          new CustomEvent("collab:nodes-changed", { detail: { nodes } })
        );
      });

      yEdges.observe((event) => {
        if (event.transaction.local) return;

        const edges = Array.from(yEdges.values());
        window.dispatchEvent(
          new CustomEvent("collab:edges-changed", { detail: { edges } })
        );
      });

      // console.log(`[Collab] Initialized for room: workflow-${roomId}`);
    };

    // Start the async connection
    initConnection();

    // Cleanup function
    return () => {
      cancelled = true;
      debugWebSocket("CollabWS", "Cleaning up connection", {
        room: `workflow-${roomId}`,
      });
      if (provider) {
        provider.disconnect();
      }
      if (ydoc) {
        ydoc.destroy();
      }
      ydocRef.current = null;
      providerRef.current = null;
      yNodesRef.current = null;
      yEdgesRef.current = null;
    };
  }, [roomId, userName, userRole, enabled]);

  const syncNodes = useCallback((nodes: Node[]) => {
    if (isReadOnly) return; // Viewers cannot sync changes
    const yNodes = yNodesRef.current;
    if (!yNodes) return;

    ydocRef.current?.transact(() => {
      yNodes.clear();
      nodes.forEach((node) => yNodes.set(node.id, node));
    });
  }, [isReadOnly]);

  const syncEdges = useCallback((edges: Edge[]) => {
    if (isReadOnly) return; // Viewers cannot sync changes
    const yEdges = yEdgesRef.current;
    if (!yEdges) return;

    ydocRef.current?.transact(() => {
      yEdges.clear();
      edges.forEach((edge) => yEdges.set(edge.id, edge));
    });
  }, [isReadOnly]);

  const updateCursor = useCallback((position: { x: number; y: number }) => {
    providerRef.current?.awareness.setLocalStateField("cursor", position);
  }, []);

  return {
    isConnected,
    isReadOnly,
    users,
    syncNodes,
    syncEdges,
    updateCursor,
  };
}
