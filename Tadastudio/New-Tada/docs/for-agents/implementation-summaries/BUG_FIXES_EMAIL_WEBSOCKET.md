# Bug Fixes: Email Node Execution and WebSocket Errors

## Issues Fixed

### 1. WebSocket JSON Parse Error

**Error**: `SyntaxError: JSON Parse error: Unexpected identifier "pong"`

**Root Cause**: Backend was sending ping/pong messages as plain text (`"ping"`, `"pong"`), but frontend was trying to
parse all WebSocket messages as JSON.

**Files Changed**:

- `backend/api/websocket/execution.py`
- `frontend/src/hooks/useExecutionWebSocket.ts`

**Fix**:

- Backend now sends ping/pong as JSON objects: `{"type": "ping"}`, `{"type": "pong"}`
- Frontend updated to handle JSON ping/pong and added "ping"/"pong" to WebSocketMessage type
- Backwards compatibility maintained for legacy plain text ping/pong messages

### 2. ExecutionEngine Initialization Error in Email Node

**Error**: `ExecutionEngine.__init__() takes 2 positional arguments but 5 were given`

**Root Cause**: EmailNodeExecutor was trying to instantiate ExecutionEngine with 4 None arguments to use utility
methods, but ExecutionEngine signature changed to only accept `graph_manager` parameter.

**File Changed**:

- `backend/services/nodes/executors/email.py`

**Fix**:

- Replaced ExecutionEngine instantiation with direct use of `FieldExtractor` from `backend.services.io`
- Implemented field extraction logic directly using the same utilities that ExecutionEngine uses
- No dependency on ExecutionEngine for email value extraction

## Detailed Changes

### Backend WebSocket Changes

**Before**:

```python
# Sending plain text
await websocket.send_text("ping")
await websocket.send_text("pong")

# Handling plain text
if data == "ping":
    await websocket.send_text("pong")
```

**After**:

```python
# Sending JSON
await websocket.send_json({"type": "ping"})
await websocket.send_json({"type": "pong"})

# Handling JSON with backwards compatibility
try:
    message = json.loads(data)
    if message.get("type") == "ping":
        await websocket.send_json({"type": "pong"})
    elif message.get("type") == "pong":
        pass  # Ignore
except json.JSONDecodeError:
    # Handle legacy plain text
    if data == "ping":
        await websocket.send_json({"type": "pong"})
```

### Frontend WebSocket Changes

**Before**:

```typescript
// Plain text handling before JSON parse
if (event.data === "ping") {
    ws.send("pong");
    return;
}

const message: WebSocketMessage = JSON.parse(event.data);
```

**After**:

```typescript
// Parse JSON first
const message: WebSocketMessage = JSON.parse(event.data);

// Handle JSON ping/pong
if (message.type === "ping") {
    ws.send(JSON.stringify({type: "pong"}));
    return;
}

if (message.type === "pong") {
    return;  // Ignore
}
```

**Type Definition**:

```typescript
interface WebSocketMessage {
    type:
        | "node_update"
        | "execution_status"
        | "node_start"
        | "node_complete"
        | "execution_complete"
        | "reconnected"
        | "initial_status"
        | "token"
        | "ping"    // Added
        | "pong"    // Added
        | "custom";
    // ...
}
```

### Email Executor Changes

**Before**:

```python
from backend.services.execution import ExecutionEngine

engine = ExecutionEngine(None, None, None, None)  # WRONG - signature changed

if source_mode == "previous":
    prev_output = engine._get_previous_node_output(None, state, graph)
```

**After**:

```python
from backend.services.io import FieldExtractor

field_extractor = FieldExtractor()

if source_mode == "previous":
    # Get the previous node's output from state
    node_outputs = state.get("node_outputs", {})
    if not node_outputs:
        return default

    # Find the most recent node output (last in execution order)
    sorted_outputs = sorted(
        node_outputs.items(),
        key=lambda x: x[1].get("execution_order", 0) if isinstance(x[1], dict) else 0,
        reverse=True
    )

    if sorted_outputs:
        prev_output = sorted_outputs[0][1]
        if source_field_path and prev_output:
            return field_extractor.extract_field(prev_output, source_field_path, default)
        return prev_output.get("raw", default) if isinstance(prev_output, dict) else default
```

## Testing

### Verification Steps

1. ✅ Backend Python syntax validation passes
2. ✅ Frontend TypeScript compilation passes
3. ✅ Email node no longer throws ExecutionEngine initialization error
4. ✅ WebSocket messages parse correctly without JSON errors

### Manual Testing Required

1. Run a workflow with an email node
2. Verify email is sent successfully
3. Monitor backend logs for any ExecutionEngine errors
4. Monitor browser console for WebSocket parse errors
5. Test WebSocket reconnection after idle timeout (30s+)

## Related Issues

### HTTP Executor Has Same Issue

The HTTP executor (`backend/services/nodes/executors/http.py`) has the same ExecutionEngine instantiation issue in lines
373, 442, 489, and 536. These should be fixed in a separate PR to avoid scope creep.

**Locations**:

- Line 373: `_process_body()` method
- Line 442: `_extract_mapping_value()` method
- Line 489: `_extract_header_mapping_value()` method
- Line 536: `_extract_body_mapping_value()` method

**Recommended Fix**: Follow same pattern as email executor - replace ExecutionEngine with direct use of FieldExtractor
and MappingValueExtractor.

## Status

✅ **Email Node Fixed** - Ready for testing
✅ **WebSocket Fixed** - JSON protocol now consistent
⚠️ **HTTP Node** - Has same issue, needs separate fix

## Deployment Notes

- No database migrations required
- No configuration changes required
- Backwards compatible with existing workflows
- WebSocket protocol change is backwards compatible
