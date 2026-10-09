/**
 * Figma-style remote cursor component
 * Shows cursor with role-based icon (pencil for editors, eye for viewers)
 */

import { getInitials, type WorkflowRole } from "@/hooks/useCollaboration";

interface RemoteCursorProps {
  name: string;
  color: string;
  role: WorkflowRole;
  position: { x: number; y: number };
  avatar?: string;
}

export function RemoteCursor({ name, color, role, position, avatar }: RemoteCursorProps) {
  const initials = getInitials(name);
  const isViewer = role === "viewer";
  const roleLabel = isViewer ? "Viewing" : "Editing";

  return (
    <div
      className="pointer-events-none fixed z-[9999] transition-transform duration-75"
      style={{
        transform: `translate(${position.x}px, ${position.y}px)`,
      }}
    >
      {/* Cursor icon - Pencil for editors, Eye for viewers */}
      {isViewer ? (
        // Eye icon for viewers
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.3))" }}
        >
          <path
            d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5z"
            fill={color}
            stroke="white"
            strokeWidth="1.5"
          />
          <circle cx="12" cy="12" r="3" fill="white" />
        </svg>
      ) : (
        // Pencil icon for editors/owners
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.3))" }}
        >
          <path
            d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a.996.996 0 000-1.41l-2.34-2.34a.996.996 0 00-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
            fill={color}
            stroke="white"
            strokeWidth="1"
            strokeLinejoin="round"
          />
        </svg>
      )}

      {/* Avatar circle with initials and role indicator */}
      <div
        className="absolute left-5 top-4 flex items-center gap-1"
        style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.2))" }}
      >
        {/* Circle with initials or avatar */}
        <div
          className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-white text-xs font-semibold text-white"
          style={{ backgroundColor: color }}
        >
          {avatar ? (
            <img
              src={avatar}
              alt={name}
              className="h-full w-full rounded-full object-cover"
            />
          ) : (
            initials
          )}
        </div>

        {/* Name and role label */}
        <div
          className="flex items-center gap-1 whitespace-nowrap rounded px-2 py-0.5 text-xs font-medium text-white"
          style={{ backgroundColor: color }}
        >
          <span>{name}</span>
          <span className="opacity-75">• {roleLabel}</span>
        </div>
      </div>

      {/* Tooltip on hover (using title for simplicity) */}
      <div className="sr-only">{name} ({roleLabel})</div>
    </div>
  );
}

interface RemoteCursorsProps {
  users: Array<{
    id: string;
    name: string;
    color: string;
    role: WorkflowRole;
    cursor?: { x: number; y: number } | null;
    avatar?: string;
  }>;
}

export function RemoteCursors({ users }: RemoteCursorsProps) {
  return (
    <>
      {users.map((user) =>
        user.cursor ? (
          <RemoteCursor
            key={user.id}
            name={user.name}
            color={user.color}
            role={user.role}
            position={user.cursor}
            avatar={user.avatar}
          />
        ) : null
      )}
    </>
  );
}
