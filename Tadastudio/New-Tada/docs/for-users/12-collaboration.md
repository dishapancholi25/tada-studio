# Real-Time Collaboration

TADA Studio supports real-time collaborative editing, allowing multiple users to work on the same workflow simultaneously — similar to Google Docs, but for AI agent graphs.

---

## Overview

When collaboration is active on a workflow, you will see:

- **Live cursors** — coloured cursors showing where other users are working on the canvas
- **Instant sync** — nodes, edges, and configuration changes appear in real time for all connected editors
- **Presence indicators** — see who is currently viewing or editing the workflow in the top bar

Collaboration uses a Conflict-Free Replicated Data Type (CRDT) protocol (Yjs) under the hood, meaning concurrent edits from different users are automatically merged without conflicts or data loss.

---

## Roles and Permissions

Each user's access to a workflow is governed by their **workflow role**:

| Role | Can view | Can edit | Collaboration WebSocket |
|------|----------|----------|------------------------|
| **Owner** | ✅ | ✅ | ✅ Connected |
| **Editor** | ✅ | ✅ | ✅ Connected |
| **Viewer** | ✅ | ❌ | ❌ Not connected |

- **Owners** have full control and can approve/reject access requests.
- **Editors** can modify the workflow graph, node configurations, and connections.
- **Viewers** can see the workflow but cannot make changes. They do not open a collaboration WebSocket and do not appear as live cursors to other users.

---

## Requesting Access

If you open a workflow you don't have edit access to, you can request access:

1. Open the workflow — it loads in read-only mode.
2. Click **Request Edit Access** in the top bar.
3. The workflow owner receives a notification with your request.
4. Once approved, your role changes to Editor and collaboration activates automatically.

### Access Request States

| State | Meaning |
|-------|---------|
| **Pending** | Request submitted, waiting for owner to respond |
| **Approved** | Owner granted access — you now have editor role |
| **Rejected** | Owner declined the request |

---

## How It Works

### Connecting

When you open a workflow as an owner or editor:

1. The frontend establishes a WebSocket connection to `/api/collab/workflow-<workflow_id>`.
2. The connection is authenticated using your existing session credentials.
3. Your cursor and presence are broadcast to all other connected users.
4. Any graph changes (nodes, edges, positions) are synced bidirectionally in real time.

### Editing Simultaneously

- **Node moves** — If you move a node while someone else moves a different node, both changes are applied.
- **Property edits** — If two users edit the same node's properties at the same time, the last write wins for each individual field (field-level conflict resolution).
- **Node creation/deletion** — Adding or removing nodes and edges is synced instantly.
- **Connection changes** — Adding or removing edges between nodes propagates immediately.

### Disconnection Handling

- If your network drops, edits are buffered locally and synced when the connection is re-established.
- If you close the browser tab, your cursor disappears from other users' canvases within a few seconds.
- Pending changes are never lost — the CRDT protocol guarantees eventual consistency.

---

## Notifications

The notification bell in the top-right corner shows collaboration-related events:

- **Access request received** — (for workflow owners) someone wants edit access
- **Access approved** — your request was granted
- **Access rejected** — your request was declined

Notifications update in real time via a separate WebSocket connection to `/api/notifications/ws`.

---

## Best Practices

1. **Communicate with collaborators** — While the system handles merge conflicts, coordinating who works on which part of the graph avoids confusion.
2. **Use meaningful node names** — Helps collaborators understand the workflow structure quickly.
3. **Save frequently** — Although changes sync in real time, explicit saves create versioned checkpoints in the backend.
4. **Check the presence bar** — Before making large structural changes (deleting multiple nodes), check if someone else is actively editing.

---

## Troubleshooting

### I can't see other users' cursors

- Ensure you have **Editor** or **Owner** role (viewers don't connect to collaboration).
- Check your network — the WebSocket may have disconnected temporarily.
- Try refreshing the page.

### My changes aren't appearing for others

- Check the connection indicator — if disconnected, your changes are buffered locally.
- Ensure the other user is on the same workflow (check the workflow ID in the URL).

### Access request not appearing for the owner

- The owner must have the application open in a browser tab for real-time notification delivery.
- Access requests are also stored in the database — they'll appear when the owner next loads the page.

### Enabling debug logs (developers)

Open the browser console and run:

```javascript
localStorage.setItem("tada_debug_websocket", "true")
location.reload()
```

This outputs detailed WebSocket connection and sync events to the console. Disable with:

```javascript
localStorage.removeItem("tada_debug_websocket")
location.reload()
```
