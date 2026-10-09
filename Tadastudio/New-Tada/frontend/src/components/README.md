# Component Library Documentation

## Overview

This directory contains all React components for the Agentic Studio frontend application. Components are organized by
function and responsibility.

## Directory Structure

```text
components/
├── core/                 # Main application components
├── nodes/               # Workflow node components
│   └── tools/          # Tool-specific nodes
├── panels/              # Configuration and execution panels
│   ├── properties/     # Node property editors
│   └── execution/      # Execution status panels
├── dialogs/             # Modal dialogs
├── ui/                  # Reusable UI components
├── database/            # Database-related components
├── json-viewer/         # JSON visualization components
├── utils/               # Utility components
└── deprecated/          # Legacy components (to be removed)
```

## Core Components

### AgentBuilder

**Location**: `core/AgentBuilder.tsx`  
**Purpose**: Main workflow builder interface with React Flow canvas  
**Props**:

- None (uses GraphContext)

**Features**:

- Drag-and-drop node creation
- Visual workflow editing
- Real-time execution monitoring
- Mode switching (build/execution)

**Usage**:

```jsx
import AgentBuilder from '@/components/core/AgentBuilder';

<AgentBuilder/>
```

### ExecutionHistory

**Location**: `core/ExecutionHistory.tsx`  
**Purpose**: Display and manage workflow execution history  
**Props**:

- None (fetches data internally)

**Features**:

- Execution timeline
- Status filtering
- Detailed execution logs
- Graph visualization

### DataSources

**Location**: `core/DataSources.tsx`  
**Purpose**: Manage data connections and sources  
**Props**:

- None

**Features**:

- Database connections
- Document uploads
- API configurations

## Node Components

### AgentNode

**Location**: `nodes/AgentNode.tsx`  
**Purpose**: AI agent node with LLM configuration  
**Props**:

```typescript
interface Props extends NodeProps {
    data: ExtendedAgentNodeData;
}
```

**Features**:

- Model selection
- Tool integration
- Sub-agent creation
- Execution status display

### FlowNode

**Location**: `nodes/FlowNode.tsx`  
**Purpose**: Flow control nodes (START, END, etc.)  
**Props**:

```typescript
interface Props extends NodeProps {
    data: {
        label: string;
        type: 'START' | 'END' | 'CONDITION';
    }
}
```

### Tool Nodes

**Location**: `nodes/tools/`

- **DocumentSearchNode**: Search through documents
- **DatabaseQueryNode**: Execute SQL queries
- **HttpRequestNode**: Make HTTP API calls
- **WebSearchNode**: Search the web

## UI Components

### HiddenNodePalette

**Location**: `ui/HiddenNodePalette.tsx`  
**Purpose**: Sliding panel for node selection  
**Props**:

```typescript
interface Props {
    isOpen: boolean;
    onClose: () => void;
    onAddNode: (type: string, sourceId?: string) => void;
    sourceNodeId?: string;
}
```

### Notification

**Location**: `ui/Notification.tsx`  
**Purpose**: Toast notifications  
**Props**:

```typescript
interface Props {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message?: string;
    duration?: number;
    onClose: (id: string) => void;
}
```

### ResultCard

**Location**: `ui/ResultCard.tsx`  
**Purpose**: Display execution results  
**Props**:

```typescript
interface Props {
    title?: string;
    snippet: string;
    url?: string;
    metadata?: MetaData[];
    onExpand?: () => void;
    onOpen?: () => void;
    onCopy?: (text: string) => void;
}
```

### Skeleton

**Location**: `ui/Skeleton.tsx`  
**Purpose**: Loading placeholders  
**Props**:

```typescript
interface Props {
    className?: string;
    variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
    width?: string | number;
    height?: string | number;
    animation?: 'pulse' | 'wave' | 'none';
}
```

## Panel Components

### NodePropertiesPanelV2

**Location**: `panels/properties/NodePropertiesPanelV2.tsx`  
**Purpose**: Configure node properties  
**Props**:

```typescript
interface Props {
    node: Node | null;
    onClose: () => void;
}
```

### ExecutionPanelFinal

**Location**: `panels/execution/ExecutionPanelFinal.tsx`  
**Purpose**: Main execution control panel  
**Props**:

```typescript
interface Props {
    graphName: string;
    onExecutionComplete?: (execution: GraphExecution) => void;
    className?: string;
}
```

## Dialog Components

### CreateToolNodeDialog

**Location**: `dialogs/CreateToolNodeDialog.tsx`  
**Purpose**: Dialog for adding tool nodes  
**Props**:

```typescript
interface Props {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (toolType: string, toolName: string) => void;
    parentAgentName: string;
}
```

### ConfirmDialog

**Location**: `dialogs/ConfirmDialog.tsx`  
**Purpose**: Confirmation prompts  
**Props**:

```typescript
interface Props {
    isOpen: boolean;
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    onConfirm: () => void;
    onCancel: () => void;
    variant?: 'danger' | 'warning' | 'info';
}
```

## JSON Viewer Components

### JsonViewerEnhanced

**Location**: `JsonViewerEnhanced.tsx`  
**Purpose**: Enhanced JSON visualization  
**Props**:

```typescript
interface Props {
    data: unknown;
    className?: string;
    maxHeight?: string;
}
```

**Features**:

- Tree view
- Table view for arrays
- Raw JSON view
- Automatic JSON parsing
- Copy functionality

## Utility Components

### AccessibleLayout

**Location**: `utils/AccessibleLayout.tsx`  
**Purpose**: Accessibility wrapper  
**Props**:

```typescript
interface Props {
    children: React.ReactNode;
    skipLinks?: Array<{ href: string; label: string }>;
}
```

### LazyLoad

**Location**: `utils/LazyLoad.tsx`  
**Purpose**: Lazy loading wrapper  
**Props**:

```typescript
interface Props {
    children: React.ReactNode;
    fallback?: React.ReactNode;
    variant?: 'skeleton' | 'card' | 'text' | 'custom';
}
```

## Best Practices

### Component Creation

1. Use TypeScript for all components
2. Export interfaces for props
3. Add JSDoc comments for complex logic
4. Include default props where appropriate
5. Implement error boundaries for critical components

### Styling

1. Use Tailwind CSS classes
2. Leverage CSS variables for theming
3. Add focus visible states
4. Ensure responsive design
5. Follow the design system guidelines

### Performance

1. Use React.memo for expensive components
2. Implement lazy loading for heavy components
3. Use useMemo and useCallback appropriately
4. Avoid inline function definitions
5. Optimize re-renders

### Accessibility

1. Add ARIA labels to interactive elements
2. Ensure keyboard navigation
3. Include focus management
4. Provide screen reader support
5. Meet WCAG 2.1 AA standards

### Testing

1. Write unit tests for utility functions
2. Add integration tests for complex flows
3. Include accessibility tests
4. Test error states
5. Verify loading states

## Component Patterns

### Container/Presentational Pattern

```jsx
// Container Component
function AgentNodeContainer({nodeId}) {
    const data = useNodeData(nodeId);
    const handlers = useNodeHandlers(nodeId);

    return <AgentNodeView {...data} {...handlers} />;
}

// Presentational Component
function AgentNodeView({name, status, onEdit, onDelete}) {
    return (
        <div>
            {/* Pure presentation */}
        </div>
    );
}
```

### Compound Components

```jsx
// Parent Component
<ExecutionPanel>
    <ExecutionPanel.Header/>
    <ExecutionPanel.Body/>
    <ExecutionPanel.Footer/>
</ExecutionPanel>
```

### Render Props

```jsx
<DataProvider
    render={(data) => (
        <DataDisplay data={data}/>
    )}
/>
```

## Migration Guide

### Deprecated Components

The following components are deprecated and should not be used:

- `Sidebar.tsx` → Use `HiddenNodePalette.tsx`
- `NodePropertiesPanel.tsx` → Use `NodePropertiesPanelV2.tsx`
- `JsonViewer.tsx` → Use `JsonViewerEnhanced.tsx`

### Breaking Changes

- Component reorganization in v2.0
- Import paths have changed
- Some prop interfaces updated

## Contributing

### Adding New Components

1. Choose appropriate directory
2. Follow naming conventions
3. Add TypeScript types
4. Include documentation
5. Write tests
6. Update this README

### Component Checklist

- [ ] TypeScript interfaces defined
- [ ] Props documented
- [ ] Default props set
- [ ] Error handling implemented
- [ ] Loading states handled
- [ ] Accessibility features added
- [ ] Tests written
- [ ] Documentation updated
