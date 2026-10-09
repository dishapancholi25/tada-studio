# Streaming Activity Components

Real-time streaming components for displaying tool calls and sub-agent activity during workflow execution.

## Components

### ActivityFeed

Container component that displays a scrollable list of streaming activities.

```tsx
import { ActivityFeed, useStreamingActivity } from './streaming';

function ExecutionView({ executionId }) {
  const {
    activities,
    handleToolCallStart,
    handleToolCallProgress,
    handleToolCallComplete,
    handleToolCallError,
    handleSubAgentStart,
    handleSubAgentComplete,
    clearActivities,
  } = useStreamingActivity({ maxActivities: 50 });

  // Connect to WebSocket
  useExecutionWebSocket(executionId, {
    onToolCallStart: handleToolCallStart,
    onToolCallProgress: handleToolCallProgress,
    onToolCallComplete: handleToolCallComplete,
    onToolCallError: handleToolCallError,
    onSubAgentStart: handleSubAgentStart,
    onSubAgentComplete: handleSubAgentComplete,
  });

  return (
    <ActivityFeed
      activities={activities}
      maxHeight="300px"
      showHeader={true}
    />
  );
}
```

### ToolCallActivity

Displays a single tool call with status, progress, and duration.

```tsx
<ToolCallActivity
  callId="call_123"
  toolName="document_search"
  status="running"
  progressMessage="Searching 3 collections..."
  progressPercent={45}
  agentName="Research Agent"
/>
```

### SubAgentActivity

Displays a sub-agent delegation with optional nested tool calls.

```tsx
<SubAgentActivity
  subagentId="agent_456"
  subagentName="Research Agent"
  status="running"
  taskDescription="Find relevant documents about pricing"
  parentAgentName="Orchestrator"
>
  {/* Nested tool calls appear here */}
  <ToolCallActivity ... />
</SubAgentActivity>
```

## Integration with ExecutionPanelFinal

To add the activity feed to the execution panel, add this section where you want it displayed (typically near the streaming token output):

```tsx
import {
  ActivityFeed,
  useStreamingActivity,
} from './streaming';

// In your component:
const streamingActivity = useStreamingActivity();

// In your useExecutionWebSocket call, add the handlers:
useExecutionWebSocket(executionId, {
  // ... existing handlers ...
  onToolCallStart: streamingActivity.handleToolCallStart,
  onToolCallProgress: streamingActivity.handleToolCallProgress,
  onToolCallComplete: streamingActivity.handleToolCallComplete,
  onToolCallError: streamingActivity.handleToolCallError,
  onSubAgentStart: streamingActivity.handleSubAgentStart,
  onSubAgentComplete: streamingActivity.handleSubAgentComplete,
});

// In the render, add:
{streamingActivity.activities.length > 0 && (
  <div className="mt-4">
    <ActivityFeed
      activities={streamingActivity.activities}
      maxHeight="250px"
    />
  </div>
)}
```

## Event Types

The following WebSocket events are handled:

| Event Type | Description |
|------------|-------------|
| `tool_call_start` | Tool execution begins |
| `tool_call_progress` | Progress update (message, percentage) |
| `tool_call_complete` | Tool finished successfully |
| `tool_call_error` | Tool execution failed |
| `subagent_start` | Sub-agent delegation begins |
| `subagent_complete` | Sub-agent finished |

## Styling

Components use Tailwind CSS with the project's color variables:

- Running states: Blue accents (`blue-500`)
- Complete states: Emerald accents (`emerald-500`)
- Error states: Red accents (`red-500`)
- Sub-agent states: Purple accents (`purple-500`)
