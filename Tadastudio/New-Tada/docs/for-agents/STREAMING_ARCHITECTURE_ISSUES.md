# Streaming Architecture Issues & Improvements

This document tracks technical debt and improvement opportunities identified during the architecture review of the tool streaming and timeline status system.

## Overview

The core architecture is sound - streaming events + database persistence with tool-node mapping is the right approach. The main technical debt is in **state management fragmentation** and **heuristic-based duplicate detection**.

---

## Issues

### Issue 1: Frontend Timeline State Management Fragmentation

**Status**: Open
**Priority**: Medium
**Location**: `frontend/src/components/panels/execution/ExecutionPanelFinal.tsx`

**Problem**:
The `wsNodeExecutions` Map is updated in multiple places:

1. `onNodeUpdate` callback (lines ~1127-1266) - handles `node_update` WebSocket messages
2. `handleToolCallStartWrapper` (lines 1609-1655) - handles streaming events
3. `handleToolCallCompleteWrapper` (lines 1657-1693) - handles streaming events
4. `handleToolCallErrorWrapper` (lines 1695-1731) - handles streaming events
5. Initial load from execution history

**Why It's A Problem**:

- Duplicates state management logic across multiple callbacks
- Hard to reason about state transitions
- Risk of inconsistent updates
- Each handler has slightly different update logic

**Current Bandaid**:
Created wrapper handlers that call both the streaming activity hook AND manually update `wsNodeExecutions`.

**Suggested Fix**:
Create a unified `useTimelineState` hook or reducer pattern:

```typescript
// Option A: Reducer pattern
type TimelineAction =
  | { type: 'TOOL_START'; payload: ToolCallStartEvent }
  | { type: 'TOOL_COMPLETE'; payload: ToolCallCompleteEvent }
  | { type: 'TOOL_ERROR'; payload: ToolCallErrorEvent }
  | { type: 'NODE_UPDATE'; payload: NodeUpdatePayload }
  | { type: 'INITIAL_LOAD'; payload: NodeExecution[] };

function timelineReducer(state: Map<string, NodeExecution>, action: TimelineAction): Map<string, NodeExecution> {
  // Single place for all timeline state transitions
}

// Option B: Custom hook
function useTimelineState() {
  // Encapsulates all timeline state management
  // Exposes handlers for different event types
  // Single source of truth for update logic
}
```

**Testing Required**:

- [ ] Unit tests for reducer/hook with all action types
- [ ] Integration test: streaming event updates timeline correctly
- [ ] Integration test: node_update message updates timeline correctly
- [ ] Integration test: no duplicate entries created
- [ ] E2E test: tool shows running -> completed transition

---

### Issue 2: Heuristic-Based Duplicate Notification Detection

**Status**: Open
**Priority**: Medium
**Location**: `backend/services/subgraph/agent/tool_tracker.py` (lines 527-536)

**Problem**:
The `_send_tool_notification` function checks for `"id"`, `"call_id"`, or `"tool_id"` to detect if streaming events were already sent:

```python
tool_call_id = tool_exec.get("id") or tool_exec.get("call_id") or tool_exec.get("tool_id")
if tool_call_id:
    # Skip duplicate notification
    return
```

**Why It's A Problem**:

- Field name inconsistency: `ToolExecutionRecord.to_dict()` uses `"id"`/`"call_id"`, but original check looked for `"tool_id"`
- Heuristic-based detection - fragile if field names change
- No explicit flag indicating whether streaming was used
- Relies on implementation detail of how tool_id is stored

**Current Bandaid**:
Check multiple possible field names with fallback chain.

**Suggested Fix**:
Add explicit `was_streamed` flag to `ToolExecutionRecord`:

```python
# In backend/services/execution/async_agent/models.py
class ToolExecutionRecord(BaseModel):
    tool_name: str
    tool_id: Optional[str] = None
    was_streamed: bool = Field(
        default=False,
        description="True if streaming events were emitted for this tool call"
    )
    # ... other fields ...

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "tool": self.tool_name,
            "was_streamed": self.was_streamed,
            # ...
        }
```

Then in tool_tracker.py:

```python
if tool_exec.get("was_streamed", False):
    tool_tracker_logger.debug("Skipping duplicate notification - already streamed")
    return
```

**Testing Required**:

- [ ] Unit test: `was_streamed=True` skips notification
- [ ] Unit test: `was_streamed=False` sends notification
- [ ] Unit test: Missing field defaults to False (backward compat)
- [ ] Integration test: LLM tool calls set `was_streamed=True`
- [ ] Integration test: Non-LLM tool calls have `was_streamed=False`

---

### Issue 3: Over-Engineered Tool-to-Node Resolution

**Status**: Completed
**Priority**: Low
**Location**: `backend/services/subgraph/agent/tool_tracker.py`

**Problem** (was):
Four different resolution strategies with complex fallback logic including `ToolResolver.find_tool_node()` graph search.

**Solution Implemented**:

- Simplified to 3 strategies: direct mapping, delegation parsing, explicit fallback
- Removed `ToolResolver.find_tool_node()` strategy
- Added `ToolNodeInfo` dataclass with `is_fallback` flag
- Added `ResolutionStrategy` enum for tracking resolution method
- Added `_record_fallback_metric()` for production monitoring
- Added detailed warning logging when fallback is used

**Testing Completed**:

- [x] Unit test: Direct mapping lookup works (new format and legacy)
- [x] Unit test: Delegation tool parsing works
- [x] Unit test: Missing mapping logs warning and uses fallback
- [x] Unit test: `is_fallback` flag set correctly
- [x] Unit test: Fallback records metrics
- [x] 27 tests passing in `backend/tests/subgraph/agent/test_tool_tracker.py`

---

### Issue 4: Streaming Activity Hook Separation

**Status**: Open
**Priority**: Low
**Location**:

- `frontend/src/components/panels/execution/streaming/useStreamingActivity.tsx`
- `frontend/src/components/panels/execution/ExecutionPanelFinal.tsx`

**Problem**:
The `useStreamingActivity` hook manages the activity feed, but timeline updates require separate handling. The wrapper handlers in ExecutionPanelFinal.tsx call both:

```typescript
const handleToolCallStartWrapper = useCallback((event) => {
  // 1. Forward to activity feed
  streamingActivity.handleToolCallStart(event);

  // 2. Also update timeline (duplicate logic)
  if (event.tool_node_id) {
    setWsNodeExecutions((prev) => { /* ... */ });
  }
}, [streamingActivity]);
```

**Why It's A Problem**:

- Two separate state updates for the same event
- Activity feed and timeline can get out of sync
- Wrapper pattern is a workaround, not a solution

**Suggested Fix**:
Extend `useStreamingActivity` to optionally update timeline state, or create a parent hook that coordinates both:

```typescript
// Option A: Extend useStreamingActivity
interface UseStreamingActivityOptions {
  maxActivities?: number;
  onTimelineUpdate?: (nodeId: string, status: string, metadata: any) => void;
}

// Option B: Parent coordinator hook
function useExecutionStreaming(options: Options) {
  const timeline = useTimelineState();
  const activity = useStreamingActivity();

  const handleToolCallStart = useCallback((event) => {
    activity.handleToolCallStart(event);
    if (event.tool_node_id) {
      timeline.setToolRunning(event.tool_node_id, event);
    }
  }, [activity, timeline]);

  return { timeline, activity, handleToolCallStart, /* ... */ };
}
```

**Testing Required**:

- [ ] Unit test: Both activity and timeline updated on single event
- [ ] Unit test: Activity and timeline stay in sync
- [ ] Integration test: Tool execution shows in both activity feed and timeline

---

## Implementation Order

Recommended order based on impact and dependencies:

1. ~~**Issue 2** (Explicit `was_streamed` flag) - Simple, low risk, improves reliability~~ **DONE**
2. **Issue 1** (Timeline state reducer) - Higher impact, enables cleaner code
3. **Issue 4** (Streaming hook coordination) - Depends on Issue 1
4. ~~**Issue 3** (Tool resolution simplification) - Lower priority, mostly cleanup~~ **DONE**

---

## Completed Items

### Fixed: Issue 3 - Tool-to-Node Resolution Simplification

**Date**: 2024-12-22
**Location**: `backend/services/subgraph/agent/tool_tracker.py`

**What Was Fixed**:

- Simplified `_resolve_tool_node_info()` from 4 strategies to 3
- Removed `ToolResolver.find_tool_node()` complex graph search strategy
- Added `ToolNodeInfo` dataclass with `is_fallback` flag for debugging
- Added `ResolutionStrategy` enum for tracking resolution method
- Added `_record_fallback_metric()` for production monitoring
- Added detailed warning logging when fallback is used

**Files Changed**:

- `backend/services/subgraph/agent/tool_tracker.py` - Added dataclass, enum, metrics, refactored function
- `backend/tests/subgraph/agent/test_tool_tracker.py` - Updated tests for new return type, added 5 new test classes

---

### Fixed: Bridging Code Duplication

**Date**: 2024-12-22
**Location**: `backend/services/execution/workflow_executor.py`

**What Was Fixed**:

- Removed bridging code that was calling `on_node_start`/`on_node_complete` for streaming events
- This was creating duplicate timeline entries (3 entries instead of 1)
- Frontend now handles streaming events directly via wrapper handlers

**Files Changed**:

- `backend/services/execution/workflow_executor.py` - Removed bridging (lines 697-771)
- `frontend/src/hooks/useExecutionWebSocket.ts` - Added tool_node_id fields
- `frontend/src/components/panels/execution/ExecutionPanelFinal.tsx` - Added wrapper handlers
- `backend/services/subgraph/agent/tool_tracker.py` - Fixed duplicate skip logic
- `backend/tests/execution/test_workflow_executor_streaming.py` - Updated tests
