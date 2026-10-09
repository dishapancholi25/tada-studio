# LangSmith-Style Trace Viewer Implementation Plan

## Overview

This document outlines the implementation plan for creating a LangSmith-style trace viewer within the Agentic Studio
application. The goal is to provide a hierarchical, interactive trace visualization that matches or exceeds the UX
quality of LangSmith's trace viewer.

## 1. UI/UX Analysis of LangSmith Trace Viewer

### Key Visual Elements

1. **Dark Theme Design**
    - Background: `#0F0F0F` (near black)
    - Secondary panels: `#1A1A1A`
    - Borders: `#2A2A2A`
    - Text: `#E0E0E0` (light gray)
    - Accent: Blue (`#3B82F6`) for active/selected items

2. **Hierarchical Tree Structure**
    - Collapsible/expandable nodes with chevron icons
    - Indentation levels showing parent-child relationships
    - Color-coded status indicators (green checkmarks for success)
    - Duration badges showing execution time

3. **Three-Panel Layout**
    - **Left Panel**: Tree view of execution trace
    - **Middle Panel**: Selected node details
    - **Right Panel**: Input/Output/Metadata tabs

4. **Node Type Icons**
    - 🤖 Agent nodes (blue agent icon)
    - 🔧 Tool nodes (blue tool icon)
    - 📊 LLM calls (orange icon)
    - ✅ Success indicators
    - Query nodes with specific icons

5. **Interactive Features**
    - Click to select and view details
    - Expand/collapse tree nodes
    - Copy buttons for data
    - Syntax highlighting for code/JSON
    - Tab navigation for different data views

## 2. Data Requirements & Current Availability

### Already Available in Our System ✅

```typescript
interface NodeExecution {
  id: string
  node_id: string
  node_name: string
  node_type: string
  execution_order: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  start_time: string
  end_time: string
  duration_seconds: number
  input_data: any
  output_data: any
  error_message?: string
  is_sub_agent: boolean
  parent_agent_id?: string
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
}
```

### Additional Data Needed

1. **Hierarchical Relationships**
    - Build parent-child tree from `parent_agent_id`
    - Track tool calls per agent
    - Identify LLM calls within agents

2. **Enhanced Metadata**
    - Model information (GPT-4, Claude, etc.)
    - Temperature and other LLM parameters
    - Prompt templates used
    - System/User/Assistant message breakdown

3. **Real-time Updates**
    - WebSocket integration for live updates
    - Streaming token counts
    - Progressive output display

## 3. Technical Architecture

### Frontend Components Structure

```
components/
  trace-viewer/
    TraceViewer.tsx           # Main container
    TraceTree.tsx            # Left panel tree view
    TraceNode.tsx            # Individual tree node
    TraceDetails.tsx         # Middle panel details
    TraceDataViewer.tsx      # Right panel data viewer
    TraceTimeline.tsx        # Timeline visualization
    hooks/
      useTraceData.ts        # Data fetching/WebSocket
      useTraceSelection.ts   # Selection state
      useTraceExpansion.ts   # Tree expansion state
```

### Backend Enhancements

```python
# New API endpoints needed
GET /api/executions/{id}/trace-tree  # Hierarchical trace data
GET /api/executions/{id}/trace-stream  # SSE/WebSocket stream
GET /api/executions/{id}/llm-calls  # Detailed LLM call data
```

## 4. Implementation Phases

### Phase 1: Core Tree Visualization (Week 1)

- [ ] Create TraceViewer component with three-panel layout
- [ ] Implement collapsible tree structure
- [ ] Add node type icons and status indicators
- [ ] Display execution times and durations
- [ ] Style with dark theme matching LangSmith

### Phase 2: Data Integration (Week 2)

- [ ] Transform flat execution data to hierarchical structure
- [ ] Connect to existing ExecutionHistoryService
- [ ] Add parent-child relationship mapping
- [ ] Implement data fetching hooks

### Phase 3: Interactive Features (Week 3)

- [ ] Node selection and detail display
- [ ] Input/Output/Metadata tabs
- [ ] JSON syntax highlighting
- [ ] Copy functionality
- [ ] Search/filter capabilities

### Phase 4: Real-time Updates (Week 4)

- [ ] WebSocket integration for live traces
- [ ] Progressive rendering of running executions
- [ ] Auto-expand for active nodes
- [ ] Status updates and animations

### Phase 5: Advanced Features (Week 5)

- [ ] Timeline view alternative
- [ ] Export trace data
- [ ] Compare multiple traces
- [ ] Performance profiling view
- [ ] Token usage analytics

## 5. UI Component Libraries & Tools

### Recommended Stack

1. **Tree Component**:
    - `react-arborist` or `rc-tree` for advanced tree functionality
    - Custom implementation using React + Tailwind for full control

2. **Icons**:
    - `lucide-react` for consistent icon set
    - Custom SVG icons for node types

3. **Syntax Highlighting**:
    - `react-syntax-highlighter` with tomorrow-night theme
    - `monaco-editor` for advanced editing capabilities

4. **Animations**:
    - `framer-motion` for smooth expand/collapse
    - CSS transitions for hover states

5. **Data Visualization**:
    - `recharts` for token usage charts
    - Custom D3.js for timeline visualization

## 6. Styling Approach

### Tailwind Classes for LangSmith-style Theme

```css
/* Background layers */
.trace-bg-primary: bg-gray-950
.trace-bg-secondary: bg-gray-900
.trace-bg-tertiary: bg-gray-800

/* Borders */
.trace-border: border-gray-700

/* Text */
.trace-text-primary: text-gray-100
.trace-text-secondary: text-gray-400

/* Status colors */
.trace-success: text-green-400
.trace-error: text-red-400
.trace-running: text-blue-400
.trace-pending: text-gray-500

/* Interactive states */
.trace-hover: hover:bg-gray-800
.trace-selected: bg-blue-900/20 border-blue-500
```

## 7. API Design for Trace Data

### Transform existing data to trace format

```typescript
interface TraceNode {
  id: string
  name: string
  type: 'agent' | 'tool' | 'llm' | 'chain'
  status: 'pending' | 'running' | 'completed' | 'failed'
  startTime: number
  endTime?: number
  duration?: number
  children: TraceNode[]
  metadata: {
    model?: string
    temperature?: number
    tokens?: {
      input: number
      output: number
      total: number
    }
  }
  input: any
  output?: any
  error?: string
}
```

### Hierarchical Data Builder

```python
def build_trace_tree(execution_id: str) -> Dict:
    """Transform flat execution data into hierarchical trace tree"""
    nodes = ExecutionHistoryService.get_node_executions(execution_id)
    
    # Build parent-child relationships
    tree = {}
    root_nodes = []
    
    for node in nodes:
        node_data = {
            'id': node['id'],
            'name': node['node_name'],
            'type': map_node_type(node['node_type']),
            'status': node['status'],
            'startTime': node['start_time'],
            'endTime': node['end_time'],
            'duration': node['duration_seconds'],
            'children': [],
            'metadata': extract_metadata(node),
            'input': node['input_data'],
            'output': node['output_data'],
            'error': node.get('error_message')
        }
        
        if node.get('parent_agent_id'):
            parent = tree.get(node['parent_agent_id'], {})
            parent.setdefault('children', []).append(node_data)
        else:
            root_nodes.append(node_data)
        
        tree[node['id']] = node_data
    
    return {'nodes': root_nodes, 'metadata': {...}}
```

## 8. Migration Strategy

### Option 1: Replace EnhancedExecutionViewer

- Pros: Clean replacement, single source of truth
- Cons: Loss of existing functionality during transition

### Option 2: Add as New Route/Tab

- Pros: Gradual migration, A/B testing possible
- Cons: Duplicate code during transition

### Option 3: Progressive Enhancement

- Start with current viewer
- Add tree view as alternative view mode
- Gradually migrate features
- **Recommended approach**

## 9. Performance Considerations

### Optimizations

1. **Virtual Scrolling**: For large trace trees (>1000 nodes)
2. **Lazy Loading**: Load child nodes on expand
3. **Memoization**: React.memo for node components
4. **Debouncing**: Search and filter operations
5. **Data Pagination**: For historical traces

### Benchmarks

- Target: Render 10,000 nodes in <100ms
- Smooth scrolling at 60fps
- <50ms response time for expand/collapse

## 10. Testing Strategy

### Unit Tests

- Tree transformation logic
- Node selection/expansion state
- Data formatting utilities

### Integration Tests

- API endpoint responses
- WebSocket real-time updates
- Parent-child relationship mapping

### E2E Tests

- Full trace viewing workflow
- Interactive features
- Performance under load

## 11. Accessibility

### Requirements

- Keyboard navigation (arrow keys for tree)
- Screen reader support
- Focus management
- ARIA labels for icons
- High contrast mode support

## 12. Example Implementation

### Basic TraceNode Component

```tsx
const TraceNode: React.FC<{node: TraceNode}> = ({ node }) => {
  const [expanded, setExpanded] = useState(false);
  const duration = node.duration ? `${node.duration.toFixed(2)}s` : 'Running...';
  
  return (
    <div className="trace-node">
      <div 
        className="flex items-center gap-2 px-2 py-1 hover:bg-gray-800 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <ChevronIcon className={`transform ${expanded ? 'rotate-90' : ''}`} />
        <NodeIcon type={node.type} />
        <span className="text-gray-100">{node.name}</span>
        <StatusIndicator status={node.status} />
        <span className="text-gray-500 text-sm ml-auto">{duration}</span>
      </div>
      {expanded && node.children && (
        <div className="ml-4">
          {node.children.map(child => (
            <TraceNode key={child.id} node={child} />
          ))}
        </div>
      )}
    </div>
  );
};
```

## 13. Success Metrics

### User Experience

- Time to first meaningful paint: <500ms
- Time to interactive: <1s
- User satisfaction score: >4.5/5

### Technical

- Code coverage: >80%
- Bundle size: <200KB for trace viewer
- Memory usage: <50MB for 10K nodes

## 14. Risks & Mitigations

### Risks

1. **Data volume**: Large traces may overwhelm UI
    - Mitigation: Virtual scrolling, pagination

2. **Real-time complexity**: WebSocket sync issues
    - Mitigation: Optimistic UI updates, retry logic

3. **Browser compatibility**: Modern features required
    - Mitigation: Polyfills, graceful degradation

## 15. Timeline

- **Week 1**: Core tree component and styling
- **Week 2**: Data integration and API
- **Week 3**: Interactive features
- **Week 4**: Real-time updates
- **Week 5**: Polish and advanced features
- **Week 6**: Testing and deployment

## 16. Resources & References

### Open Source Alternatives to Study

1. **Langfuse**: Open-source LLM observability
    - GitHub: <https://github.com/langfuse/langfuse>
    - Trace UI implementation for reference

2. **Phoenix by Arize**: ML observability platform
    - Trace viewer components

3. **OpenTelemetry UI**: Standard trace visualization
    - Tree structure patterns

### Design Inspiration

- LangSmith UI/UX patterns
- Datadog APM trace viewer
- Jaeger distributed tracing UI
- Chrome DevTools Performance panel

## Conclusion

This implementation plan provides a roadmap to create a professional-grade trace viewer that matches the quality and
functionality of LangSmith while leveraging our existing execution tracking infrastructure. The phased approach allows
for incremental delivery of value while maintaining system stability.

The key to success will be:

1. Maintaining visual consistency with the dark theme
2. Ensuring smooth, responsive interactions
3. Properly transforming our flat data into hierarchical structures
4. Implementing real-time updates effectively
5. Focusing on developer experience and debugging capabilities

With our existing PostgreSQL tracking, WebSocket infrastructure, and comprehensive execution data, we have all the
building blocks needed to create an exceptional trace viewing experience.
