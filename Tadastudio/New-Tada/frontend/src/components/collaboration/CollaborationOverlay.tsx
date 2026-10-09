/**
 * Collaboration Overlay - Shows connected users, their cursors, and role indicators
 */

import React, { useState } from "react";
import type { CollabUser } from "@/hooks/useCollaboration";
import { getInitials } from "@/hooks/useCollaboration";
import { RemoteCursors } from "./RemoteCursor";
import { useToast } from "@/contexts/ToastContext";

interface CollaborationOverlayProps {
  users: CollabUser[];
  isConnected: boolean;
  isReadOnly?: boolean;
  workflowId?: string;
  onRequestAccess?: (workflowId: string) => Promise<void>;
}

export function CollaborationOverlay({
  users,
  isConnected,
  isReadOnly = false,
  workflowId,
  onRequestAccess,
}: CollaborationOverlayProps) {
  const [requestStatus, setRequestStatus] = useState<"idle" | "loading" | "sent" | "error" | "pending">("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const { showSuccess, showWarning, showError } = useToast();

  const handleRequestAccess = async () => {
    if (!workflowId || !onRequestAccess) return;

    setRequestStatus("loading");
    setErrorMessage("");
    try {
      await onRequestAccess(workflowId);
      setRequestStatus("sent");
      showSuccess(
        "Request Sent",
        "Your edit access request has been sent to the workflow owner"
      );
    } catch (error: any) {
      console.error("Failed to request access:", error);
      const message = error?.message || "Failed to request access";

      // Check for specific error cases
      if (message.includes("already have edit access")) {
        setRequestStatus("idle");
        showWarning("Already Have Access", "You already have edit access to this workflow");
      } else if (message.includes("already have a pending")) {
        setRequestStatus("pending");
        showWarning("Request Pending", "You already have a pending access request for this workflow");
      } else {
        setRequestStatus("error");
        setErrorMessage(message);
        showError("Request Failed", message);
        // Reset after 3 seconds
        setTimeout(() => setRequestStatus("idle"), 3000);
      }
    }
  };

  return (
    <>
      {/* Read Mode Banner for viewers */}
      {isReadOnly && (
        <div className="absolute left-1/2 top-4 z-50 -translate-x-1/2 transform">
          <div
            className="flex items-center gap-3 rounded-lg px-4 py-2 shadow-md border"
            style={{
              backgroundColor: "var(--color-bg-secondary)",
              borderColor: "var(--color-border)",
            }}
          >
            <svg
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{ color: "var(--color-warning)" }}
            >
              <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            <span
              className="text-sm font-medium"
              style={{ color: "var(--color-text-primary)" }}
            >
              View Only Mode
            </span>
            <span
              className="hidden sm:inline text-xs"
              style={{ color: "var(--color-text-muted)" }}
            >
              You can view but not edit this workflow
            </span>

            {/* Request Access Button */}
            {workflowId && onRequestAccess && (
              <button
                onClick={handleRequestAccess}
                disabled={requestStatus === "loading" || requestStatus === "sent" || requestStatus === "pending"}
                className="ml-2 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-70"
                style={{
                  backgroundColor:
                    requestStatus === "sent"
                      ? "#22c55e"
                      : requestStatus === "pending"
                      ? "var(--color-warning)"
                      : requestStatus === "error"
                      ? "#ef4444"
                      : "var(--color-accent)",
                  color: "white",
                }}
                title={requestStatus === "pending" ? "Your request is pending approval" : undefined}
              >
                {requestStatus === "loading" ? (
                  <>
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Requesting...
                  </>
                ) : requestStatus === "sent" ? (
                  <>
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Request Sent
                  </>
                ) : requestStatus === "pending" ? (
                  <>
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Request Pending
                  </>
                ) : requestStatus === "error" ? (
                  <>
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    Failed
                  </>
                ) : (
                  <>
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                    </svg>
                    Request Edit Access
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Connection status indicator - positioned in bottom left to avoid panel overlaps */}
      <div className="absolute left-4 bottom-4 z-40 flex items-center gap-2 bg-white/90 backdrop-blur-sm px-3 py-1.5 rounded-lg shadow-sm border border-gray-200">
        <div
          className={`h-2 w-2 rounded-full ${
            isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"
          }`}
        />
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {isConnected ? "Live" : "Offline"}
        </span>

        {/* Connected users avatars with role indicators */}
        {users.length > 0 && (
          <div className="ml-3 flex -space-x-2">
            {users.slice(0, 5).map((user) => (
              <div
                key={user.id}
                className="relative flex h-7 w-7 items-center justify-center rounded-full border-2 border-white text-xs font-semibold text-white shadow-sm transition-transform hover:z-10 hover:scale-110 dark:border-gray-800"
                style={{ backgroundColor: user.color }}
                title={`${user.name} (${user.role === "viewer" ? "Viewing" : "Editing"})`}
              >
                {getInitials(user.name)}
                {/* Role indicator badge */}
                <span
                  className="absolute -bottom-1 -right-1 flex h-3.5 w-3.5 items-center justify-center rounded-full border border-white bg-white dark:border-gray-800 dark:bg-gray-800"
                  title={user.role === "viewer" ? "Viewing" : "Editing"}
                >
                  {user.role === "viewer" ? (
                    <svg className="h-2.5 w-2.5 text-gray-500" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" />
                    </svg>
                  ) : (
                    <svg className="h-2.5 w-2.5 text-blue-500" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a.996.996 0 000-1.41l-2.34-2.34a.996.996 0 00-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z" />
                    </svg>
                  )}
                </span>
              </div>
            ))}
            {users.length > 5 && (
              <div
                className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-gray-500 text-xs font-semibold text-white dark:border-gray-800"
                title={`${users.length - 5} more users`}
              >
                +{users.length - 5}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Remote cursors with Figma-style design */}
      <RemoteCursors users={users} />
    </>
  );
}

export default CollaborationOverlay;
