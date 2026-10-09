# Real-Time Collaboration

Real-time collaborative editing for workflows using Yjs CRDT protocol.

## Overview

This feature enables multiple users to edit the same workflow simultaneously with:
- Real-time cursor positions (Google Docs style - 1 cursor per user)
- Live node/edge synchronization
- Conflict-free concurrent edits using CRDT

## Architecture

```
Frontend (React)                    Backend (FastAPI)
┌─────────────────┐                ┌─────────────────┐
│ useCollaboration│◄──WebSocket──►│ pycrdt-websocket│
│ (Yjs + y-ws)    │                │ server          │
└─────────────────┘                └─────────────────┘
```

**Components:**
- `frontend/src/hooks/useCollaboration.ts` - React hook for collaboration (Yjs + y-websocket)
- `frontend/src/components/core/AgentBuilder.tsx` - Integrates collaboration with graph store
- `backend/api/collaboration/routes.py` - WebSocket endpoint and connection management

**Key Implementation Details:**

1. **Dynamic WebSocket URL:** The frontend determines the WebSocket URL from `runtimeConfig`:
   - Separate-domains deployment: Uses `apiUrl` from runtime config
   - Reverse-proxy deployment: Uses current window location
   The y-websocket provider receives the base URL (`/api/collab`) and appends
   the room name, so workflow collaboration connects as
   `wss://<host>/api/collab/workflow-<workflow_id>`.

2. **Graph Store Sync:** When receiving remote changes, both the Zustand graph store AND
   ReactFlow visual state are updated. A `applyingRemoteChangesRef` flag prevents sync loops.

3. **Editor-only live collaboration:** The frontend only opens the collaboration
   WebSocket for users whose `workflow_role` is explicitly `owner` or `editor`.
   Viewers and users with an unknown/pending role can still view workflows and
   request edit access, but they do not continuously retry the collaboration
   WebSocket while access is pending.

## Local Development

### 1. Start Backend
```bash
cd backend
uvicorn app:app --reload --port 8000
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Test Collaboration
Open the same workflow in multiple browser tabs. Changes sync automatically.

### 4. Check Connection Stats
```bash
curl http://localhost:8000/api/collab/stats | jq
```

## Production Deployment

### Environment Variables

**Backend (.env):**
```env
SKIP_AUTH=false
```

**Frontend:**
No environment variable needed - WebSocket URL is determined dynamically from `runtimeConfig`
based on deployment mode (see Key Implementation Details above).

Optional browser diagnostics can be enabled for a single browser session:

```javascript
localStorage.setItem("tada_debug_websocket", "true")
location.reload()
```

Disable diagnostics:

```javascript
localStorage.removeItem("tada_debug_websocket")
location.reload()
```

### Nginx Configuration

WebSocket connections require special nginx configuration:

```nginx
# WebSocket upgrade for collaboration
location /api/collab {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Auth headers (from oauth2-proxy)
    proxy_set_header X-Auth-Request-User $upstream_http_x_auth_request_user;
    proxy_set_header X-Auth-Request-Email $upstream_http_x_auth_request_email;
    
    # WebSocket timeouts
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
    proxy_connect_timeout 60s;
}
```

### Authentication

#### SKIP_AUTH Configuration

The `SKIP_AUTH` environment variable controls how user identity is determined:

| SKIP_AUTH | oauth2-proxy | Result |
|-----------|--------------|--------|
| `true` | Not needed | All users identified as `DEV_USER_EMAIL` from .env |
| `false` | Running | Real user identity from oauth2-proxy headers |
| `false` | NOT running | **App broken - all requests return 401** |

**Important:** With `SKIP_AUTH=true`, all users appear as the same person (the `DEV_USER_EMAIL`). 
This breaks multi-user collaboration features like seeing other users' cursors with their real identity.

#### Authentication Flow (SKIP_AUTH=false)

```
User Request → Nginx → /api/auth/nginx-check → oauth2-proxy:4180
                                                      │
                                              Validates session
                                                      │
                                                      ▼
                                        X-Auth-Request-Email header
                                                      │
                                                      ▼
                                              Backend receives
                                              real user email
```

#### Headers Used

In production, user identity is determined by HTTP headers set by oauth2-proxy
or the ingress/reverse proxy. The backend accepts the following headers, using
the first available value:

1. `X-User-Email`
2. `X-Auth-Request-Email`
3. `X-Forwarded-Email`
4. `X-Auth-Request-User`
5. `X-Forwarded-User`
6. `X-Forwarded-Preferred-Username`

The backend validates these headers and uses them for:
- Connection tracking
- Room access control
- Cursor identity

#### WebSocket Authentication

WebSocket connections extract user identity from the proxy-forwarded headers
listed above.

If `SKIP_AUTH=true` and no headers present, uses `DEV_USER_EMAIL` or `test_user` query param.

#### Room Access Control

The frontend uses room names in the format `workflow-<workflow_id>`. The backend
normalizes this to the raw workflow ID for access checks, while still supporting
raw workflow IDs, workflow names, and ad-hoc local/dev rooms.

For existing workflows, collaboration access is granted when the authenticated
user is either:

- the workflow creator (`workflows.created_by_user_id`), or
- a member in `workflow_memberships`.

If a user only has viewer/pending/unknown access, the frontend does not open the
collaboration WebSocket. The user must be approved as editor/owner before live
editing starts.

### Connection Limits

| Limit | Value | Purpose |
|-------|-------|---------|
| Max connections per room | 50 | Prevent room overload |
| Max tabs per user per room | 5 | Prevent single user exhausting room |
| Max total connections | 500 | Server protection |
| Stale connection timeout | 30 min | Cleanup inactive connections |

### Monitoring

**Stats Endpoint:** `GET /api/collab/stats`

Response:
```json
{
  "total_connections": 15,
  "total_rooms": 3,
  "server_started": true,
  "rooms": {
    "workflow-abc123": {
      "total_connections": 5,
      "active_connections": 4,
      "stale_connections": 1,
      "unique_users": 3,
      "users": {
        "alice@example.com": 2,
        "bob@example.com": 2,
        "charlie@example.com": 1
      }
    }
  }
}
```

### Health Checks

Add to your monitoring:
```bash
# Check if collaboration server is running
curl -f http://localhost:8000/api/collab/stats || echo "Collaboration server down"
```

## Troubleshooting

### WebSocket Connection Failed

1. Check nginx WebSocket config (Upgrade headers)
2. Verify WebSocket URL in browser console uses `wss://` in production
3. Check browser console for connection errors
4. Verify `/api/config` returns correct `apiUrl` for your deployment
5. Check oauth-proxy logs. If the request returns the oauth-proxy sign-in page
   or `No valid authentication in request`, the browser session is not
   authenticated and the request never reaches FastAPI.
6. Check backend logs for one of:
   - `Unauthorized WebSocket connection attempt` - proxy identity headers are missing
   - `denied collaboration access` - user is authenticated but is not a workflow member/creator
   - `WebSocket error in room` - pycrdt/Yjs runtime error after auth

Example production log filters:

```bash
kubectl logs -n <namespace> -l app=oauth-proxy --since=10m | grep -E "api/collab|No valid authentication"
kubectl logs -n <namespace> -l app=backend-app --since=10m | grep -E "api/collab|collaboration|Unauthorized|denied collaboration|WebSocket error"
```

### Repeated Collaboration Errors for Viewers

If a viewer sees repeated `/api/collab/workflow-...` failures, confirm the
frontend build includes the role gate in `useCollaboration` integration:
collaboration should be enabled only for explicit `owner` or `editor` roles.
The viewer should use the Request Edit Access flow instead.

### Request Edit Access Returns "Already Pending"

`POST /api/ws/notifications/access-requests` returns `400` with
`You already have a pending access request for this workflow` when the requester
already has an open pending request. This is expected. The workflow creator/owner
must approve or reject the pending request.

### Users Not Seeing Each Other

1. Verify both users are in the same room (same workflow ID)
2. Check `/api/collab/stats` to see connected users
3. Ensure authentication headers are being forwarded

### Live Updates Not Syncing (Cursors work but node changes don't)

This is caused by `rooms_ready=False` in the WebsocketServer configuration.

**Fix:** Ensure `rooms_ready=True` in `CollaborationManager._ensure_started()`:
```python
self._websocket_server = WebsocketServer(rooms_ready=True, auto_clean_rooms=True)
```

**Why:** With `rooms_ready=False`, the YRoom's document observer subscription is never created
because it waits for a `ready_event` that is never set. This breaks update broadcasting while
initial sync and cursor awareness still work.

### High Memory Usage

1. Check for stale connections in stats
2. Reduce `MAX_CONNECTIONS_PER_ROOM` if needed
3. Enable `auto_clean_rooms=True` (default)

## API Reference

### WebSocket Endpoint

```
WS /api/collab/{room_name}
```

**Parameters:**
- `room_name` - Workflow room name. Production workflow rooms use
  `workflow-<workflow_id>`; raw workflow IDs and names are also supported
  (alphanumeric, underscore, hyphen only).

**Room Name Format:**
- Max 128 characters
- Pattern: `^[a-zA-Z0-9_\-]+$`

### Protocol

Uses Yjs sync protocol over WebSocket:
1. Client sends sync step 1 (state vector)
2. Server responds with sync step 2 (missing updates)
3. Bidirectional updates flow for real-time sync

### Awareness Protocol

User presence is broadcast via Yjs awareness:
```typescript
{
  user: { name: "alice@example.com", color: "#FF6B6B" },
  cursor: { x: 100, y: 200 }
}
```
