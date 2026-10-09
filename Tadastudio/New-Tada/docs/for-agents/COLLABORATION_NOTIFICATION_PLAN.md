# Collaboration Notification Enhancements Plan

## Context

The collaboration notification system is functional (WebSocket-driven, real-time toasts, bell icon on canvas).
However, there are gaps that limit the user experience for multi-user workflows.

This plan covers enhancements to the **Global Bell Icon** and **Notification UI** as part of the
real-time collaboration feature set.

## Current State

| Feature | Status | Location |
|---------|--------|----------|
| Toast popup (access request received) | ✅ Live | `AccessRequestContext.tsx` |
| Bell icon on canvas page | ✅ Live | `NotificationBell.tsx` in `CanvasTopBar.tsx` |
| Approve/Reject in dropdown | ✅ Working | `NotificationBell.tsx` |
| Persists until actioned | ✅ Server-side | Backend `/api/ws/notifications/access-requests` |
| Global bell component | ✅ Built, **NOT mounted** | `GlobalNotificationBell.tsx` (exists but unused in AppHeader) |

## Enhancements

### 1. Mount GlobalNotificationBell in AppHeader

**Priority:** HIGH  
**Effort:** Small (30 min)  
**Why:** Users on non-canvas pages (home, manage, settings, library) cannot see incoming access requests.

**Implementation:**

- File: `frontend/src/components/layout/AppHeader.tsx`
- Replace the static bell placeholder (line ~142) with `<GlobalNotificationBell />`
- Import from `@/components/notifications/GlobalNotificationBell`
- The component already matches the Mashreq design system (orange avatar, rounded-xl, shadow-lg)

**Acceptance criteria:**
- Bell icon with red badge count visible on ALL pages
- Dropdown shows pending requests with Approve/Reject buttons
- Clicking a request navigates to that workflow
- Badge disappears when no pending requests

---

### 2. Increase Toast Duration for Access Requests

**Priority:** MEDIUM  
**Effort:** Tiny (5 min)  
**Why:** Default 5-second auto-dismiss means owners can miss requests if they look away.

**Implementation:**

- File: `frontend/src/contexts/AccessRequestContext.tsx`
- Change `showInfo(...)` calls to use `showToast("info", title, message, 10000)` for 10-second duration
- Alternatively, add `duration` param to the convenience methods in `ToastContext.tsx`

**Acceptance criteria:**
- Access request toasts stay visible for 10 seconds (vs 5s default)
- Other toasts remain at default 5s duration

---

### 3. Notification History Popup Panel

**Priority:** LOW  
**Effort:** Medium (2-3 hours)  
**Why:** Once a toast dismisses, users have no way to see past notifications. The bell only shows pending requests.

**Design (Popup from bell icon):**

```
┌─────────────────────────────────────────┐
│ 🔔 Notifications              ✕ Close  │
├─────────────────────────────────────────┤
│ ● Pending                               │
│ ┌─────────────────────────────────────┐ │
│ │ 👤 bob@test.com                     │ │
│ │ Wants editor access to "GCEO V2.0"  │ │
│ │ 2 min ago    [Approve] [Reject]     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ○ Recent                                │
│ ┌─────────────────────────────────────┐ │
│ │ ✅ alice@corp.com — Approved        │ │
│ │ "Sales Workflow" · 1 hour ago       │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ ❌ charlie@corp.com — Rejected      │ │
│ │ "HR Workflow" · Yesterday           │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Implementation:**

- Extend `GlobalNotificationBell.tsx` dropdown with a "Recent" section below pending
- Add backend query: `GET /api/ws/notifications/access-requests?status=all&limit=20`
- Show resolved requests (approved/rejected) from last 7 days below the pending section
- Use existing Mashreq design patterns from `GlobalNotificationBell.tsx` (same card style)
- Use popup/dropdown approach (NOT a separate page) — stays in context, no navigation away
- Reference for slide-over pattern if needed: `ResultDrawer.tsx`
- Scrollable with `max-h-96 overflow-y-auto`

**Backend data already available:**
- `GET /api/ws/notifications/access-requests?status=pending` — existing
- `GET /api/ws/notifications/access-requests?status=approved` — likely supported
- `GET /api/ws/notifications/access-requests?status=rejected` — likely supported

**Acceptance criteria:**
- Dropdown shows both pending AND recent resolved requests
- Pending requests on top with action buttons
- Recent section shows last 7 days of resolved requests
- Scrollable if many items
- No separate route/page needed — all inline in the bell popup

---

## Implementation Order

```
Step 1 → Mount GlobalNotificationBell in AppHeader (immediate value)
Step 2 → Longer toast duration for access requests (quick win)
Step 3 → Notification history popup panel (can defer to next sprint)
```

## Related Files

| File | Purpose |
|------|---------|
| `frontend/src/components/notifications/GlobalNotificationBell.tsx` | Global bell (ready to mount) |
| `frontend/src/components/notifications/NotificationBell.tsx` | Canvas-scoped bell |
| `frontend/src/components/layout/AppHeader.tsx` | App header (mount point for global bell) |
| `frontend/src/contexts/AccessRequestContext.tsx` | WebSocket + state management |
| `frontend/src/contexts/ToastContext.tsx` | Toast display logic |
| `frontend/src/components/panels/result/ResultDrawer.tsx` | Slide-over design reference |
| `backend/api/notifications/routes.py` | Backend access request API |
| `backend/api/notifications/manager.py` | Notification broadcast logic |
| `backend/api/collaboration/README.md` | Collaboration architecture overview |
