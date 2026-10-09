# Adding New Tool Nodes

This guide covers adding new tool nodes that AI agents can invoke during workflow execution.

## Overview

Tool nodes are specialized nodes that provide capabilities to AI agents. Unlike action nodes (which execute with static/workflow values), tool nodes allow the AI to dynamically populate parameters based on context.

Examples: `DATABASE_QUERY`, `WEB_SEARCH`, `HTTP_REQUEST`, `EMAIL_SEND_TOOL`, `MCP_SERVER`

---

## Checklist of Files to Modify

### Backend (Python)

| File | What to Add |
|------|-------------|
| `backend/models/workflow/enums.py` | Add `MY_TOOL = "MY_TOOL"` to NodeType enum |
| `backend/models/workflow/configs/my_tool.py` | Create config dataclass |
| `backend/models/workflow/configs/__init__.py` | Export config class from configs package |
| `backend/models/workflow/__init__.py` | Import and export config class from workflow package |
| `backend/models/workflow/node.py` | Add `my_tool_config: Optional[MyToolConfig]` to EnhancedNodeData |
| `backend/tools/my_tool/` | Create module with schemas.py, config.py, handlers.py, factory.py, __init__.py |
| `backend/services/graph/agent_tools/creators/my_tool.py` | Create tool creator function |
| `backend/services/graph/agent_tools/creators/__init__.py` | Export creator |
| `backend/services/graph/agent_tools/factory.py` | Add handler for NodeType.MY_TOOL in `_create_tool_from_node` |
| `backend/services/graph/agent_tools/utils.py` | Add default node name(s) to `DEFAULT_NODE_NAMES` set (e.g., "My Tool", "My Tool Node") |
| `backend/services/delegation/utils/tool_mapping.py` | Add `_map_my_tool_node()` function and condition in `_map_tool_node()` |
| `backend/services/graph/connection_manager.py` | Add `NodeType.MY_TOOL` to `VALID_TOOL_TARGET_TYPES` set (~line 30) |
| `backend/services/graph/node_manager.py` | Add to `_configure_node_by_type()` for default config, and `_update_type_specific_config()` for property updates |
| `backend/services/nodes/executors/agent.py` | Add to `type_to_prefix` in `_get_tool_name_for_node()` and base name mappings in `_build_tool_node_mapping()` |

### Frontend - Node Rendering (CRITICAL!)

These files determine which React component renders the node. __Missing any of these causes the node to appear as an agent node.__

| File | What to Add |
|------|-------------|
| `frontend/src/lib/graphDefinitionToReactFlow.ts` | Add `case "MY_TOOL": reactFlowType = "myToolNode"` in switch (~line 78) |
| `frontend/src/contexts/GraphContext.tsx` | Add `isMyTool = nodeType === "MY_TOOL"` check and if-else clause (~line 517) |
| `frontend/src/lib/executionGraphUtils.ts` | Add `case "MY_TOOL": return "myToolNode"` in switch (~line 49) |
| `frontend/src/components/nodes/tools/MyToolNode.tsx` | Create node component in `tools/` directory (follow DatabaseQueryNode.tsx pattern - top handle only, no plus button) |
| `frontend/src/components/core/shared/nodeRegistry.ts` | Import and register `myToolNode: MyToolNode` in `sharedToolNodeTypes` |

### Frontend - Properties & Execution Panels

| File | What to Add |
|------|-------------|
| `frontend/src/components/panels/properties/MyToolPropertiesPanel.tsx` | Create properties panel |
| `frontend/src/components/core/shared/useSelectionPanels.ts` | Add panel key to `SelectionPanelKey` type and initial state |
| `frontend/src/components/core/shared/usePropertyPanels.tsx` | Add lazy import, selection extraction, and render logic |
| `frontend/src/components/dialogs/CreateToolNodeDialog.tsx` | Add to `availableTools` array with icon and color |

### Frontend - Execution Rendering

| File | What to Add |
|------|-------------|
| `frontend/src/components/panels/execution/unified/types/execution.types.ts` | Add to `ToolType` union, create execution interface, add to `ToolExecution` union |
| `frontend/src/components/panels/execution/unified/hooks/useToolRegistry.ts` | Add to `TOOL_REGISTRY` with icon, title, gradients, toolNames, nodeType |
| `frontend/src/components/panels/execution/unified/hooks/useExecutionData.ts` | Add to `NODE_TYPE_MAP` |
| `frontend/src/components/panels/execution/unified/utils/executionParser.ts` | Add to `nodeTypeMap` (~line 132) and `toolNameMap` (~line 776) |
| `frontend/src/components/panels/execution/unified/renderers/MyToolRenderer.tsx` | Create renderer extending BaseRenderer |
| `frontend/src/components/panels/execution/unified/UnifiedToolExecutionPanel.tsx` | Add to `RENDERER_MAP` |

### Frontend - API Types

| File | What to Add |
|------|-------------|
| `frontend/src/types/api.ts` | Add `"MY_TOOL"` to `NodeType` union |
| `frontend/src/lib/api.ts` | Add `"MY_TOOL"` to `CreateNodeRequest` node_type union, add `my_tool_config?: Record<string, any>` |
| `frontend/src/lib/utils/toolTypes.ts` | Add `"MY_TOOL"` to `TOOL_NODE_TYPES` array |

### Frontend - AgentBuilder Integration

| File | What to Add |
|------|-------------|
| `frontend/src/components/core/AgentBuilder.tsx` | 1) Node click handler to open panel, 2) Tool type recognition in node type checks, 3) Config in cloning/creation arrays, 4) Node creation logic from tool dialog |

---

## Common Mistakes

1. __Missing from graphDefinitionToReactFlow.ts__ - Node loads from saved graph as agent node
2. __Missing from GraphContext.tsx__ - Newly created nodes appear as agent nodes
3. __Missing from executionGraphUtils.ts__ - Execution view shows agent node instead of tool node
4. __Forgetting nodeRegistry.ts__ - React "component not found" error
5. __Missing from NODE_TYPE_MAP in useExecutionData.ts__ - TypeScript error on build
6. __Missing from executionParser.ts nodeTypeMap/toolNameMap__ - TypeScript error on build
7. __Missing from VALID_TOOL_TARGET_TYPES in connection_manager.py__ - Backend rejects connections from agents to the tool (ConnectionValidationError)
8. __Using wrong node component pattern__ - Tool nodes must use top-handle-only pattern (like DatabaseQueryNode), not left/right handles like action nodes
9. __Missing from DEFAULT_NODE_NAMES in utils.py__ - Tool names become inconsistent (e.g., `my_tool_my_tool` instead of `my_tool_a23f1d69`)
10. __Missing from tool_mapping.py__ - Tool executions fall back to agent node tracking, logs show "Built tool mapping with 0 entries" and "FALLBACK RESOLUTION"
11. __Missing from node_manager.py `_configure_node_by_type()`__ - Nodes created without default config, agent logs show "Node X missing my_tool_config" and "Total tools created: 0"
12. __Missing from node_manager.py `_update_type_specific_config()`__ - Property panel updates are not saved to the node
13. __Config not exported from workflow/__init__.py__ - ImportError when node_manager tries to import the config class
14. __Missing from agent.py `_get_tool_name_for_node()`__ - Tool mapping returns 0 entries despite tool being created, logs show "Built tool mapping with 0 entries"

---

## Testing Checklist

After implementing all files:

- [ ] Create new tool node from dialog - appears with correct icon/color
- [ ] Reload page - node still renders correctly (not as agent)
- [ ] Click node - properties panel opens with correct fields
- [ ] Connect tool to agent via "tools" handle - connection works
- [ ] Run workflow with agent using the tool - tool executes
- [ ] Click tool node during/after execution - execution panel shows tool data
- [ ] Build passes with no TypeScript errors (`npm run build`)

---

## Example: Adding a Tool Node

Here's the pattern for adding EMAIL_SEND_TOOL as a reference:

### 1. Backend enum (enums.py)

```python
class NodeType(str, Enum):
    EMAIL_SEND_TOOL = "EMAIL_SEND_TOOL"
```

### 2. Backend connection validation (connection_manager.py)

```python
VALID_TOOL_TARGET_TYPES = {
    NodeType.TOOL,
    NodeType.DATABASE_QUERY,
    NodeType.EMAIL_SEND_TOOL,  # Add your tool here
    # ...
}
```

### 3. Node type mapping (graphDefinitionToReactFlow.ts)

```typescript
case "EMAIL_SEND_TOOL":
    reactFlowType = "emailSendToolNode";  // Use dedicated tool node component
    break;
```

### 4. Node creation (GraphContext.tsx)

```typescript
const isEmailSendTool = nodeType === "EMAIL_SEND_TOOL";
// ...
else if (isEmailSendTool) reactFlowType = "emailSendToolNode";
```

### 5. Execution view (executionGraphUtils.ts)

```typescript
case "EMAIL_SEND_TOOL":
    return "emailSendToolNode";
```

### 5. Tool registry (useToolRegistry.ts)

```typescript
email_send: {
    icon: Mail,
    title: "Email Send",
    gradientFrom: "from-emerald-600",
    gradientTo: "to-emerald-500/40",
    toolNames: ["email_send", "send_email"],
    nodeType: "EMAIL_SEND",
},
```

### 6. CreateToolNodeDialog.tsx

```typescript
{
    value: "email_send",
    label: "Email Send",
    icon: Mail,
    description: "Send emails with AI-generated content",
    color: "emerald",
},
```

### 7. Tool naming defaults (utils.py)

Add default node names so the tool gets consistent ID-based naming:

```python
# backend/services/graph/agent_tools/utils.py
DEFAULT_NODE_NAMES = {
    "Document Search",
    "Web Search",
    "HTTP Request",
    "Database Query",
    "Email Send Tool",  # Add your tool's default name(s)
    "Email Send",
}
```

### 8. Node config initialization (node_manager.py)

Add default config when nodes are created, and handle property updates:

```python
# backend/services/graph/node_manager.py

# In _configure_node_by_type(), add:
elif node_type == NodeType.EMAIL_SEND_TOOL:
    from backend.models.workflow import EmailSendToolConfig
    node.email_send_tool_config = EmailSendToolConfig()

# In _update_type_specific_config(), add:
if "email_send_tool_config" in updates and node.type == NodeType.EMAIL_SEND_TOOL:
    from backend.models.workflow import EmailSendToolConfig

    if isinstance(updates["email_send_tool_config"], dict):
        node.email_send_tool_config = EmailSendToolConfig(**updates["email_send_tool_config"])
```

__Without this__: Nodes are created with `None` config, and the agent cannot use the tool (logs: "Node X missing email_send_tool_config", "Total tools created: 0").

### 9. Tool node mapping (tool_mapping.py)

Add mapping function and condition so tool executions are properly tracked:

```python
# backend/services/delegation/utils/tool_mapping.py

# In _map_tool_node(), add condition:
elif tool_node.type == NodeType.EMAIL_SEND_TOOL and tool_node.email_send_tool_config:
    _map_email_send_node(tool_node, mapping)

# Add mapping function:
def _map_email_send_node(
    node: EnhancedNodeData,
    mapping: Dict[str, Dict[str, str]],
) -> None:
    """Map an email send tool node."""
    tool_name_key = build_tool_name("email_send", node.name, node.uniq_id)
    node_info = {
        "node_id": node.uniq_id,
        "node_name": node.name,
        "node_type": NodeType.EMAIL_SEND_TOOL,
    }

    mapping[tool_name_key] = node_info
    # Add base names for compatibility (used during tool resolution)
    mapping["email_send"] = node_info
    mapping["send_email"] = node_info

    logger.debug(
        f"Mapped email send: {tool_name_key}, email_send, send_email "
        f"-> {node.uniq_id} ({node.name})"
    )
```

---

## Architecture Notes

### Tool vs Action Nodes

- __Tool Nodes__: Connected to agents via `ConnectionType.TOOL`. AI dynamically populates parameters.
- __Action Nodes__: Part of workflow sequence. Execute with static/workflow values.

### Node Rendering Flow

1. Backend returns `node_type` (e.g., "EMAIL_SEND_TOOL")
2. `graphDefinitionToReactFlow.ts` maps to React Flow type (e.g., "emailSendNode")
3. `nodeRegistry.ts` maps React Flow type to component (e.g., EmailSendNode)
4. React Flow renders the component

### Execution Panel Flow

1. User clicks tool node during execution
2. `usePropertyPanels.tsx` identifies tool type from `node_type`
3. `UnifiedToolExecutionPanel` receives `toolType` prop
4. `useToolRegistry` provides config (icon, colors)
5. `useExecutionData` fetches execution data
6. Appropriate renderer from `RENDERER_MAP` displays results

### Tool Mapping Flow (Backend)

Tool mapping enables the system to track which graph node a tool execution belongs to:

1. Agent runs and calls a tool (e.g., `email_send_a23f1d69`)
2. `build_tool_node_mapping()` creates mapping from tool names → node IDs
3. `_map_tool_node()` dispatches to type-specific mapper (e.g., `_map_email_send_node`)
4. Mapper adds multiple entries: full name, base name, aliases (e.g., `email_send_a23f1d69`, `email_send`, `send_email`)
5. Tool execution tracker uses mapping to resolve tool call → node ID
6. Execution is recorded against the correct node in the database

__Without proper mapping__: Tool executions fall back to agent node, logs show `FALLBACK RESOLUTION`, and tool-level tracking is lost.
