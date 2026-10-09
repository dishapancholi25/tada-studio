# Enhanced Trace Viewer Implementation Plan

## With Design System Integration & Advanced Data Tracking

## 1. Design System Alignment

### Color Scheme Integration

Based on your existing design system, the trace viewer will use:

```css
/* Dark Mode (Primary Theme) */
.trace-viewer {
  /* Backgrounds aligned with refreshed palette */
  --trace-bg-primary: #050914;
  --trace-bg-secondary: #0D1A29;
  --trace-bg-surface: #233061;
  --trace-bg-surface-hover: #3D4855;
  
  /* Borders */
  --trace-border: #2F3A54;
  --trace-border-hover: #695DA8;
  
  /* Text */
  --trace-text-primary: #FFFFFF;
  --trace-text-secondary: #DBDAD7;
  --trace-text-muted: #82818A;
  
  /* Brand Integration */
  --trace-accent: #3F1350;
  --trace-accent-dark: #233061;
  --trace-accent-light: #695DA8;
  
  /* Node Type Colors */
  --trace-node-agent: #3F1350;
  --trace-node-tool: #1D7A79;
  --trace-node-llm: #F05365;
  --trace-node-condition: #695DA8;
  --trace-node-orchestrator: #81B29A;
  
  /* Status Colors */
  --trace-success: #81B29A;
  --trace-error: #F05365;
  --trace-warning: #F68A40;
  --trace-info: #3D5A81;
  --trace-running: #695DA8;
  
  /* Glass Effects */
  --trace-glass-bg: rgba(13, 26, 41, 0.8);
  --trace-glass-border: rgba(105, 93, 168, 0.36);
  --trace-glass-shadow: 0 8px 32px rgba(3, 6, 14, 0.75);
}

/* Light Mode Support */
@media (prefers-color-scheme: light) {
  .trace-viewer {
    --trace-bg-primary: #F5F6FA;
    --trace-bg-secondary: #E8EBF5;
    --trace-bg-surface: #FFFFFF;
    --trace-bg-surface-hover: #F1F3FA;
    --trace-border: #E0E5F0;
    --trace-border-hover: #695DA8;
    --trace-text-primary: #242424;
    --trace-text-secondary: #4A4A52;
    --trace-text-muted: #74747D;
    --trace-accent: #3F1350;
    --trace-accent-dark: #233061;
    --trace-accent-light: #695DA8;
  }
}
```

### Component Styling Consistency

```tsx
// Use your existing animation durations
const animations = {
  fast: 'var(--animation-fast)',     // 150ms
  base: 'var(--animation-base)',     // 250ms
  slow: 'var(--animation-slow)',     // 350ms
  slower: 'var(--animation-slower)'  // 500ms
};

// Apply your border radius system
const radius = {
  sm: 'var(--radius-sm)',   // 4px
  md: 'var(--radius-md)',   // 8px
  lg: 'var(--radius-lg)',   // 12px
  xl: 'var(--radius-xl)',   // 16px
};

// Use your shadow system
const shadows = {
  sm: 'var(--shadow-sm)',
  md: 'var(--shadow-md)',
  lg: 'var(--shadow-lg)',
  xl: 'var(--shadow-xl)'
};
```

### Glassmorphism Integration

```tsx
// Floating panels with your glass effect
<div className="trace-panel-glass">
  <style jsx>{`
    .trace-panel-glass {
      background: var(--trace-glass-bg);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--trace-glass-border);
      box-shadow: var(--trace-glass-shadow);
      border-radius: var(--radius-lg);
    }
  `}</style>
</div>
```

## 2. Additional Execution Data to Track

### A. LLM-Specific Metadata

```typescript
interface LLMMetadata {
  // Model Information
  model: string;                    // e.g., "gpt-4o", "claude-3"
  provider: 'azure' | 'openai' | 'anthropic';
  deployment_name?: string;          // Azure specific
  
  // Request Configuration
  temperature: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  seed?: number;                    // For reproducibility
  
  // Response Metadata
  finish_reason: string;             // "stop", "length", "tool_calls"
  model_version?: string;            // Actual model version used
  system_fingerprint?: string;       // OpenAI's system fingerprint
  
  // Cost Tracking
  prompt_cost?: number;              // Calculated cost
  completion_cost?: number;
  total_cost?: number;
  
  // Performance
  time_to_first_token?: number;     // TTFT metric
  tokens_per_second?: number;       // Generation speed
  cache_hit?: boolean;               // If response was cached
}
```

### B. Message Structure Tracking

```typescript
interface MessageTracking {
  messages: Array<{
    role: 'system' | 'user' | 'assistant' | 'function' | 'tool';
    content: string;
    name?: string;                  // For function/tool messages
    tool_calls?: ToolCall[];
    function_call?: FunctionCall;   // Legacy OpenAI format
    timestamp: string;
    token_count?: number;
  }>;
  
  // Message Statistics
  message_count: number;
  system_prompt_tokens?: number;
  conversation_history_tokens?: number;
  
  // Template Information
  prompt_template_id?: string;      // If using prompt templates
  prompt_template_version?: string;
  prompt_variables?: Record<string, any>;
}
```

### C. Tool/Function Call Details

```typescript
interface ToolCallMetadata {
  tool_name: string;
  tool_version?: string;
  tool_description?: string;
  
  // Invocation Details
  arguments: Record<string, any>;
  argument_schema?: object;         // JSON schema
  
  // Execution Metrics
  execution_time_ms: number;
  memory_usage_mb?: number;
  cpu_usage_percent?: number;
  
  // Results
  return_value: any;
  return_type?: string;
  error_details?: {
    error_type: string;
    error_message: string;
    stack_trace?: string;
    retry_count?: number;
  };
  
  // External Calls
  external_api_calls?: Array<{
    url: string;
    method: string;
    status_code: number;
    latency_ms: number;
  }>;
}
```

### D. Orchestration & Delegation Tracking

```typescript
interface OrchestrationMetadata {
  // Delegation Details
  delegated_to?: string[];          // Agent IDs delegated to
  delegation_reason?: string;       // Why delegation occurred
  delegation_strategy?: string;     // parallel, sequential, conditional
  
  // Subagent Management
  subagents_created: number;
  subagents_completed: number;
  subagents_failed: number;
  
  // Coordination
  coordination_messages?: Array<{
    from_agent: string;
    to_agent: string;
    message_type: string;
    content: any;
    timestamp: string;
  }>;
  
  // Resource Usage
  total_subagent_tokens?: number;
  total_subagent_cost?: number;
  max_parallel_agents?: number;
}
```

### E. Memory & Context Management

```typescript
interface MemoryMetadata {
  // Memory Operations
  memory_retrievals?: Array<{
    memory_type: 'short_term' | 'long_term' | 'episodic';
    query: string;
    results_count: number;
    relevance_scores?: number[];
    latency_ms: number;
  }>;
  
  memory_writes?: Array<{
    memory_type: string;
    content_size_bytes: number;
    success: boolean;
  }>;
  
  // Context Window Management
  context_window_size: number;
  context_used: number;
  context_pruning_applied?: boolean;
  pruned_messages_count?: number;
  
  // Vector Operations
  embeddings_generated?: number;
  vector_search_performed?: boolean;
  vector_db_latency_ms?: number;
}
```

### F. Execution Environment

```typescript
interface EnvironmentMetadata {
  // Runtime Information
  python_version?: string;
  langchain_version?: string;
  langgraph_version?: string;
  
  // Resource Constraints
  memory_limit_mb?: number;
  cpu_cores?: number;
  gpu_available?: boolean;
  
  // Feature Flags
  feature_flags?: Record<string, boolean>;
  
  // Deployment Info
  environment: 'development' | 'staging' | 'production';
  region?: string;
  instance_id?: string;
  deployment_id?: string;
}
```

## 3. Database Schema Updates

```sql
-- Add new columns to node_executions table
ALTER TABLE node_executions ADD COLUMN llm_metadata JSONB;
ALTER TABLE node_executions ADD COLUMN message_structure JSONB;
ALTER TABLE node_executions ADD COLUMN tool_metadata JSONB;
ALTER TABLE node_executions ADD COLUMN orchestration_metadata JSONB;
ALTER TABLE node_executions ADD COLUMN memory_metadata JSONB;
ALTER TABLE node_executions ADD COLUMN environment_metadata JSONB;

-- Add indexes for performance
CREATE INDEX idx_node_executions_llm_model ON node_executions ((llm_metadata->>'model'));
CREATE INDEX idx_node_executions_tool_name ON node_executions ((tool_metadata->>'tool_name'));
CREATE INDEX idx_node_executions_finish_reason ON node_executions ((llm_metadata->>'finish_reason'));

-- Add computed columns for common queries
ALTER TABLE node_executions 
ADD COLUMN total_cost DECIMAL GENERATED ALWAYS AS 
  (COALESCE((llm_metadata->>'total_cost')::DECIMAL, 0)) STORED;
```

## 4. Enhanced UI Components

### A. Trace Tree Node Component

```tsx
interface TraceNodeProps {
  node: EnhancedNodeExecution;
  depth: number;
  isExpanded: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onSelect: () => void;
}

const TraceNode: React.FC<TraceNodeProps> = ({ node, depth, ...props }) => {
  const getNodeIcon = () => {
    switch (node.node_type) {
      case 'AGENT': return <Bot className="w-4 h-4 text-[var(--trace-node-agent)]" />;
      case 'TOOL': return <Wrench className="w-4 h-4 text-[var(--trace-node-tool)]" />;
      case 'LLM': return <Brain className="w-4 h-4 text-[var(--trace-node-llm)]" />;
      default: return <Circle className="w-4 h-4" />;
    }
  };
  
  const getStatusColor = () => {
    switch (node.status) {
      case 'completed': return 'var(--trace-success)';
      case 'failed': return 'var(--trace-error)';
      case 'running': return 'var(--trace-running)';
      default: return 'var(--trace-text-muted)';
    }
  };
  
  return (
    <div 
      className="trace-node group"
      style={{ paddingLeft: `${depth * 24}px` }}
    >
      <div className="flex items-center gap-2 px-3 py-2 
                      hover:bg-[var(--trace-bg-surface-hover)] 
                      cursor-pointer rounded-md
                      transition-all duration-[var(--animation-fast)]">
        
        {/* Expand/Collapse Chevron */}
        {node.children?.length > 0 && (
          <ChevronRight 
            className={`w-4 h-4 transition-transform duration-[var(--animation-fast)]
                       ${props.isExpanded ? 'rotate-90' : ''}`}
          />
        )}
        
        {/* Node Icon */}
        {getNodeIcon()}
        
        {/* Node Name */}
        <span className="flex-1 text-[var(--trace-text-primary)]">
          {node.node_name}
        </span>
        
        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          {node.status === 'running' && (
            <div className="w-2 h-2 rounded-full animate-pulse"
                 style={{ backgroundColor: getStatusColor() }} />
          )}
          
          {/* Duration Badge */}
          {node.duration_seconds && (
            <span className="text-xs text-[var(--trace-text-muted)] 
                           bg-[var(--trace-bg-secondary)] 
                           px-2 py-0.5 rounded-full">
              {formatDuration(node.duration_seconds)}
            </span>
          )}
          
          {/* Token Count Badge */}
          {node.total_tokens && (
            <span className="text-xs text-[var(--trace-text-muted)]
                           bg-[var(--trace-bg-secondary)]
                           px-2 py-0.5 rounded-full">
              {node.total_tokens} tokens
            </span>
          )}
          
          {/* Cost Badge (if available) */}
          {node.llm_metadata?.total_cost && (
            <span className="text-xs text-[var(--trace-accent)]
                           bg-[var(--trace-bg-secondary)]
                           px-2 py-0.5 rounded-full">
              ${node.llm_metadata.total_cost.toFixed(4)}
            </span>
          )}
        </div>
      </div>
      
      {/* Children */}
      {props.isExpanded && node.children && (
        <div className="trace-node-children">
          {node.children.map(child => (
            <TraceNode key={child.id} node={child} depth={depth + 1} {...props} />
          ))}
        </div>
      )}
    </div>
  );
};
```

### B. Message Viewer Component

```tsx
const MessageViewer: React.FC<{messages: Message[]}> = ({ messages }) => {
  return (
    <div className="space-y-3">
      {messages.map((msg, idx) => (
        <div key={idx} className="message-block rounded-lg p-3
                                  bg-[var(--trace-bg-surface)]
                                  border border-[var(--trace-border)]">
          <div className="flex items-center justify-between mb-2">
            <span className={`text-xs font-medium px-2 py-0.5 rounded
              ${msg.role === 'system' ? 'bg-purple-500/20 text-purple-400' :
                msg.role === 'user' ? 'bg-blue-500/20 text-blue-400' :
                msg.role === 'assistant' ? 'bg-green-500/20 text-green-400' :
                'bg-gray-500/20 text-gray-400'}`}>
              {msg.role.toUpperCase()}
            </span>
            {msg.token_count && (
              <span className="text-xs text-[var(--trace-text-muted)]">
                {msg.token_count} tokens
              </span>
            )}
          </div>
          <pre className="text-sm text-[var(--trace-text-primary)] 
                         whitespace-pre-wrap font-mono">
            {msg.content}
          </pre>
        </div>
      ))}
    </div>
  );
};
```

### C. Metadata Panel Component

```tsx
const MetadataPanel: React.FC<{node: EnhancedNodeExecution}> = ({ node }) => {
  const tabs = [
    { id: 'input', label: 'Input', icon: ArrowRight },
    { id: 'output', label: 'Output', icon: ArrowLeft },
    { id: 'messages', label: 'Messages', icon: MessageSquare },
    { id: 'metadata', label: 'Metadata', icon: Info },
    { id: 'metrics', label: 'Metrics', icon: BarChart }
  ];
  
  return (
    <div className="trace-metadata-panel h-full flex flex-col
                    bg-[var(--trace-bg-secondary)]
                    border-l border-[var(--trace-border)]">
      {/* Tab Navigation */}
      <div className="flex border-b border-[var(--trace-border)]">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className="flex items-center gap-2 px-4 py-3
                      text-sm text-[var(--trace-text-secondary)]
                      hover:text-[var(--trace-text-primary)]
                      hover:bg-[var(--trace-bg-surface-hover)]
                      transition-all duration-[var(--animation-fast)]">
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Tab Content */}
      <div className="flex-1 overflow-auto p-4">
        {/* Content based on selected tab */}
      </div>
    </div>
  );
};
```

## 5. Performance Optimizations

### Virtual Scrolling for Large Traces

```tsx
import { VariableSizeList } from 'react-window';

const VirtualTraceTree = ({ nodes, height }) => {
  const getItemSize = (index) => {
    // Calculate height based on expanded state
    const node = nodes[index];
    return node.isExpanded ? 40 * (1 + node.children.length) : 40;
  };
  
  return (
    <VariableSizeList
      height={height}
      itemCount={nodes.length}
      itemSize={getItemSize}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <TraceNode node={nodes[index]} />
        </div>
      )}
    </VariableSizeList>
  );
};
```

### Lazy Loading of Node Details

```tsx
const useLazyNodeDetails = (nodeId: string) => {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    if (!nodeId) return;
    
    setLoading(true);
    // Only fetch when needed
    api.get(`/api/trace/nodes/${nodeId}/details`)
      .then(setDetails)
      .finally(() => setLoading(false));
  }, [nodeId]);
  
  return { details, loading };
};
```

## 6. Real-time Updates via WebSocket

```tsx
const useTraceWebSocket = (executionId: string) => {
  const [trace, setTrace] = useState<TraceData | null>(null);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/trace/${executionId}`);
    
    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      
      setTrace(prev => {
        // Efficiently update only changed nodes
        return updateTraceNode(prev, update.nodeId, update.changes);
      });
    };
    
    return () => ws.close();
  }, [executionId]);
  
  return trace;
};
```

## 7. Export & Sharing Features

```tsx
const exportTrace = async (format: 'json' | 'yaml' | 'opentelemetry') => {
  const trace = await api.get(`/api/trace/${executionId}/export?format=${format}`);
  
  if (format === 'opentelemetry') {
    // Convert to OpenTelemetry format for compatibility
    return convertToOTLP(trace);
  }
  
  return trace;
};
```

## 8. Integration Points

### A. Replace/Enhance Current Viewer

```tsx
// In EnhancedExecutionViewer.tsx
const ViewerMode = {
  TIMELINE: 'timeline',  // Current view
  TRACE: 'trace',        // New trace view
  HYBRID: 'hybrid'       // Split view
};

// Add mode switcher
<div className="viewer-mode-switcher">
  <button onClick={() => setMode(ViewerMode.TRACE)}>
    Trace View
  </button>
</div>
```

### B. Standalone Route

```tsx
// pages/executions/[id]/trace.tsx
export default function TracePage() {
  const { id } = useParams();
  return <TraceViewer executionId={id} />;
}
```

## 9. Testing Strategy

```typescript
// Unit tests for trace tree transformation
describe('TraceTreeBuilder', () => {
  it('should build hierarchical tree from flat nodes', () => {
    const flat = [
      { id: '1', parent_agent_id: null },
      { id: '2', parent_agent_id: '1' }
    ];
    
    const tree = buildTraceTree(flat);
    expect(tree[0].children).toHaveLength(1);
  });
});

// E2E tests
describe('TraceViewer', () => {
  it('should expand and collapse nodes', async () => {
    // Test interaction
  });
});
```

## 10. Migration Path

### Phase 1: Data Collection (Week 1)

- [ ] Add new metadata columns to database
- [ ] Update execution tracking to capture LLM metadata
- [ ] Implement message structure tracking

### Phase 2: API Development (Week 2)

- [ ] Create trace tree transformation endpoint
- [ ] Add metadata aggregation endpoints
- [ ] Implement WebSocket streaming

### Phase 3: UI Implementation (Week 3-4)

- [ ] Build trace tree component with your design system
- [ ] Implement metadata panels
- [ ] Add virtual scrolling for performance

### Phase 4: Integration (Week 5)

- [ ] Add to existing execution viewer as new mode
- [ ] Implement smooth transition between views
- [ ] Add export/sharing features

### Phase 5: Polish & Optimization (Week 6)

- [ ] Performance testing with large traces
- [ ] Add keyboard navigation
- [ ] Implement search & filter
- [ ] Add trace comparison feature

## Conclusion

This enhanced plan ensures:

1. **Complete design consistency** with your existing system
2. **Comprehensive data tracking** for professional debugging
3. **Performance optimizations** for large-scale traces
4. **Smooth integration** with existing components
5. **Future-proof architecture** for additional features

The trace viewer will feel native to your application while providing LangSmith-level debugging capabilities.
