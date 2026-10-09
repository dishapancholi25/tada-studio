# Monitoring API Module

## Overview

The Monitoring API module provides comprehensive system observability and diagnostics capabilities for AgenticStudio. It
enables health monitoring, performance metrics collection, system diagnostics, and operational management without
requiring authentication, making it ideal for load balancers, monitoring systems, and operational dashboards.

**Location:** [backend/api/monitoring/](../../backend/api/monitoring/)

**Base Path:** `/api/monitoring`

**Primary Responsibilities:**

- Health checks (basic and detailed) for system components
- Metrics collection and export in multiple formats (JSON, Prometheus, StatsD)
- System diagnostics and component validation
- Feature flag status reporting
- Cache management and system optimisation
- Dashboard-ready metrics aggregation
- Performance tracking and alerting

## Architecture

### Module Structure

```
backend/api/monitoring/
├── __init__.py              # Module exports (router)
├── routes.py                # All API endpoints (192 lines, 9 endpoints)
├── models.py                # Pydantic response models (252 lines)
├── utils.py                 # Error handling, cache ops, metrics export (194 lines)
└── services/                # Business logic layer
    ├── __init__.py          # Service exports
    ├── health.py            # Health check implementation with caching (226 lines)
    ├── diagnostics.py       # Component diagnostics (157 lines)
    ├── feature_flags.py     # Feature flag retrieval (50 lines)
    └── system_info.py       # System information with caching (141 lines)
```

### Design Pattern

The Monitoring API follows a **service-based architecture** with clean separation of concerns:

```
HTTP Request (No Auth Required)
    ↓
Route Handler (routes.py)
    ↓
Service Layer (services/*.py)
    ├─→ Health Service (health.py)
    ├─→ Diagnostics Service (diagnostics.py)
    ├─→ System Info Service (system_info.py)
    └─→ Feature Flags Service (feature_flags.py)
    ↓
System Dependencies
    ├─→ MetricsManager (services.metrics)
    ├─→ GraphManager (services.dependency_injection)
    ├─→ ExecutionEngine (services.dependency_injection)
    └─→ ExecutionConfig (services.config)
```

**Benefits:**

- Routes focus purely on HTTP handling
- Business logic isolated in services
- Caching layer for performance (5s for health, 10s for system info)
- Error handling via decorator pattern
- Services are independently testable

### Caching Strategy

The module implements intelligent caching to minimize system overhead:

**Health Checks Cache:**

- TTL: 5 seconds
- Scope: Component status checks
- Location: [services/health.py:32-66](services/health.py#L32-L66)
- Thread-safe with lock

**System Info Cache:**

- TTL: 10 seconds
- Scope: Platform, resources, process info
- Location: [services/system_info.py:26-49](services/system_info.py#L26-L49)
- Reduces psutil calls

## Authentication & Authorisation

### Authentication

**No Authentication Required**

All monitoring endpoints are **publicly accessible** without authentication. This design decision enables:

1. **Load Balancer Health Checks** - F5, HAProxy, AWS ALB can poll endpoints
2. **External Monitoring Systems** - Prometheus, Datadog, New Relic can scrape metrics
3. **Kubernetes Probes** - Liveness and readiness probes work without auth
4. **Emergency Access** - Diagnostics available even if auth system fails

**Security Considerations:**

- Endpoints return only status information (no sensitive data)
- No user-specific data exposed
- Read-only operations (except cache clearing/optimisation)
- Rate limiting recommended at infrastructure level

### Authorisation

Not applicable - all endpoints are public read-only status endpoints.

**Exception:** POST endpoints (cache clear, optimise) should ideally be restricted to internal networks or protected by
infrastructure-level authentication.

## API Endpoints

### Health Checks (2 endpoints)

#### `GET /api/monitoring/health`

Quick health check returning basic system status. Ideal for load balancer health checks with minimal overhead.

**Authentication:** None

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T08:30:45.123Z",
  "components": {
    "graph_manager": "ready",
    "execution_engine": "ready",
    "database": "connected"
  },
  "warnings": []
}
```

**Status Values:**

- `healthy` - All components operational
- `degraded` - Some components have issues but system functional
- `unhealthy` - Critical components failed

**Component Status Values:**

- `ready` - Component operational
- `degraded` - Component functioning with issues
- `error` - Component failed
- `unknown` - Component status cannot be determined

**Use Cases:**

- Load balancer health checks (F5, HAProxy, AWS ALB)
- Kubernetes liveness probes
- Quick uptime monitoring
- Service discovery health validation

**Behaviour:**

- Checks availability of GraphManager and ExecutionEngine
- Results cached for 5 seconds to reduce overhead
- Returns `200 OK` for healthy/degraded, consider `503` handling for unhealthy
- Extremely fast response (~5-10ms with caching)

**Validation:**

- No input validation required (no parameters)

**Example Usage (Python):**

```python
import requests

# Check if AgenticStudio is healthy
response = requests.get("http://localhost:8000/api/monitoring/health")
if response.json()["status"] == "healthy":
    print("System is operational")
else:
    print(f"System status: {response.json()['status']}")
    print(f"Warnings: {response.json()['warnings']}")
```

**Example Usage (curl):**

```bash
# Basic health check
curl http://localhost:8000/api/monitoring/health

# Use in shell script
if curl -s http://localhost:8000/api/monitoring/health | grep -q "healthy"; then
  echo "System OK"
else
  echo "System degraded or unhealthy"
  exit 1
fi
```

---

#### `GET /api/monitoring/health/detailed`

Comprehensive health check with full system metrics, configuration, alerts, and detailed component status. Use for
dashboards and detailed monitoring.

**Authentication:** None

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T08:30:45.456Z",
  "components": {
    "graph_manager": "ready",
    "execution_engine": "ready",
    "database": "connected"
  },
  "configuration": {
    "engine": "langgraph",
    "checkpointing_enabled": true,
    "memory_enabled": true
  },
  "system_metrics": {
    "cpu_percent": 42.3,
    "memory_percent": 68.7,
    "process_memory_mb": 512.45
  },
  "application_metrics": {
    "agent_executions": {
      "total": 1247,
      "successful": 1189,
      "failed": 58
    },
    "tool_executions": {
      "total": 3891,
      "successful": 3856,
      "failed": 35
    },
    "avg_execution_time_ms": {
      "agents": 1834.2,
      "tools": 287.6
    },
    "cache_hit_rate": 0.73
  },
  "cache_statistics": {},
  "migration_progress": {},
  "warnings": [],
  "errors": [],
  "alerts": [
    {
      "level": "warning",
      "message": "Memory usage above 60%",
      "timestamp": "2025-10-21T08:28:15.000Z"
    },
    {
      "level": "critical",
      "message": "Execution failure rate above 5%",
      "timestamp": "2025-10-21T08:29:32.000Z"
    }
  ]
}
```

**Alert Levels:**

- `info` - Informational message
- `warning` - Attention needed but not critical
- `critical` - Immediate action required

**Use Cases:**

- Operations dashboards
- Detailed system monitoring
- Capacity planning
- Performance troubleshooting
- Pre-deployment validation

**Behaviour:**

- Collects comprehensive metrics from MetricsManager
- Includes system resource usage (CPU, memory)
- Provides application-level statistics (executions, cache hit rate)
- Generates alerts based on thresholds
- Slower than basic health check (~50-100ms) due to metrics aggregation

**Validation:**

- No input validation required (no parameters)

**Performance:**

- Response time: 50-100ms (includes metrics collection)
- Consider caching results for dashboards that refresh frequently

**Example Usage (Python):**

```python
import requests

# Get detailed health for dashboard
response = requests.get("http://localhost:8000/api/monitoring/health/detailed")
data = response.json()

# Check for critical alerts
critical_alerts = [a for a in data["alerts"] if a["level"] == "critical"]
if critical_alerts:
    print(f"⚠️  {len(critical_alerts)} critical alerts!")
    for alert in critical_alerts:
        print(f"  - {alert['message']}")

# Display system metrics
print(f"\n📊 System Metrics:")
print(f"  CPU: {data['system_metrics']['cpu_percent']}%")
print(f"  Memory: {data['system_metrics']['memory_percent']}%")
print(f"  Cache Hit Rate: {data['application_metrics']['cache_hit_rate'] * 100:.1f}%")
```

---

### Metrics (2 endpoints)

#### `GET /api/monitoring/metrics`

Export metrics in various formats for integration with monitoring systems. Supports JSON (default), Prometheus, and
StatsD formats.

**Authentication:** None

**Query Parameters:**

- `export_format` (optional) - Export format: `json`, `prometheus`, or `statsd` (default: `json`)

**Response (format=json):**

```json
{
  "agent_executions_total": {
    "value": 1247,
    "type": "counter"
  },
  "agent_executions_success": {
    "value": 1189,
    "type": "counter"
  },
  "agent_executions_failure": {
    "value": 58,
    "type": "counter"
  },
  "tool_executions_total": {
    "value": 3891,
    "type": "counter"
  },
  "execution_duration_ms": {
    "value": 1834.2,
    "type": "gauge"
  },
  "cache_hits": {
    "value": 2841,
    "type": "counter"
  },
  "cache_misses": {
    "value": 1050,
    "type": "counter"
  },
  "system_cpu_percent": {
    "value": 42.3,
    "type": "gauge"
  },
  "system_memory_percent": {
    "value": 68.7,
    "type": "gauge"
  }
}
```

**Response (format=prometheus):**

```
# HELP agent_executions_total Total number of agent executions
# TYPE agent_executions_total counter
agent_executions_total 1247

# HELP agent_executions_success Successful agent executions
# TYPE agent_executions_success counter
agent_executions_success 1189

# HELP agent_executions_failure Failed agent executions
# TYPE agent_executions_failure counter
agent_executions_failure 58

# HELP execution_duration_ms Average execution duration in milliseconds
# TYPE execution_duration_ms gauge
execution_duration_ms 1834.2

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent 42.3
```

**Response (format=statsd):**

```json
{
  "commands": [
    "agent_executions_total:1247|c",
    "agent_executions_success:1189|c",
    "agent_executions_failure:58|c",
    "tool_executions_total:3891|c",
    "execution_duration_ms:1834.2|g",
    "cache_hits:2841|c",
    "cache_misses:1050|c",
    "system_cpu_percent:42.3|g",
    "system_memory_percent:68.7|g"
  ]
}
```

**Use Cases:**

- Prometheus scraping endpoint (`format=prometheus`)
- StatsD integration (`format=statsd`)
- Custom monitoring dashboards (`format=json`)
- Grafana data source
- DataDog/New Relic integration

**Behaviour:**

- Retrieves all metrics from MetricsManager
- Formats according to requested export format
- No caching (always fresh data)
- Lightweight operation (~10-20ms)

**Validation:**

- `export_format` must be one of: `json`, `prometheus`, `statsd`
- Invalid format returns `400 Bad Request`

**Errors:**

```json
{
  "detail": "Invalid format: xml. Must be json, prometheus, or statsd"
}
```

**Example Usage (Prometheus Scrape Config):**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agenticstudio'
    metrics_path: '/api/monitoring/metrics'
    params:
      export_format: ['prometheus']
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
```

**Example Usage (Python - StatsD):**

```python
import requests

# Get StatsD format metrics
response = requests.get(
    "http://localhost:8000/api/monitoring/metrics",
    params={"export_format": "statsd"}
)

# Send to StatsD server
import socket
statsd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for command in response.json()["commands"]:
    statsd_socket.sendto(
        command.encode(),
        ("localhost", 8125)
    )
```

---

#### `GET /api/monitoring/metrics/dashboard`

Get metrics pre-formatted for dashboard display with categorised system and application metrics plus active alerts.

**Authentication:** None

**Response:**

```json
{
  "timestamp": "2025-10-21T08:30:45.789Z",
  "system": {
    "cpu_percent": 42.3,
    "memory_percent": 68.7,
    "process_memory_mb": 512.45
  },
  "application": {
    "agent_executions": {
      "total": 1247,
      "successful": 1189,
      "failed": 58,
      "success_rate": 0.953
    },
    "tool_executions": {
      "total": 3891,
      "successful": 3856,
      "failed": 35,
      "success_rate": 0.991
    },
    "avg_execution_time_ms": {
      "agents": 1834.2,
      "tools": 287.6
    },
    "cache_hit_rate": 0.73
  },
  "alerts": [
    {
      "level": "warning",
      "message": "Memory usage above 60%",
      "timestamp": "2025-10-21T08:28:15.000Z"
    }
  ]
}
```

**Use Cases:**

- Operations dashboards
- React/Vue dashboard components
- Real-time monitoring displays
- Management consoles
- Status pages

**Behaviour:**

- Aggregates metrics from MetricsManager.get_dashboard_data()
- Separates system vs application metrics
- Includes active alerts
- Optimised for dashboard display (no unnecessary data)
- Response time: ~30-50ms

**Validation:**

- No input parameters

**Example Usage (React Dashboard):**

```javascript
// Dashboard component
import { useEffect, useState } from 'react';

function MonitoringDashboard() {
  const [metrics, setMetrics] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      const response = await fetch('http://localhost:8000/api/monitoring/metrics/dashboard');
      const data = await response.json();
      setMetrics(data);
    };

    // Fetch immediately and then every 10 seconds
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics) return <div>Loading...</div>;

  return (
    <div className="dashboard">
      <h2>System Health</h2>
      <div className="metrics">
        <MetricCard
          title="CPU Usage"
          value={`${metrics.system.cpu_percent}%`}
          warning={metrics.system.cpu_percent > 80}
        />
        <MetricCard
          title="Memory Usage"
          value={`${metrics.system.memory_percent}%`}
          warning={metrics.system.memory_percent > 80}
        />
        <MetricCard
          title="Cache Hit Rate"
          value={`${(metrics.application.cache_hit_rate * 100).toFixed(1)}%`}
          warning={metrics.application.cache_hit_rate < 0.5}
        />
      </div>

      {metrics.alerts.length > 0 && (
        <div className="alerts">
          <h3>Active Alerts</h3>
          {metrics.alerts.map((alert, i) => (
            <Alert key={i} level={alert.level} message={alert.message} />
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### System Information (3 endpoints)

#### `GET /api/monitoring/status`

Get current system configuration and operational status.

**Authentication:** None

**Response:**

```json
{
  "engine": "langgraph",
  "implementation": "standard",
  "checkpointing_enabled": true,
  "memory_enabled": true,
  "cleanup_status": "complete",
  "removed_files": 26,
  "timestamp": "2025-10-21T08:30:46.123Z"
}
```

**Fields:**

- `engine` - Execution engine type (always "langgraph")
- `implementation` - Implementation variant ("standard", "experimental")
- `checkpointing_enabled` - Workflow state persistence enabled
- `memory_enabled` - Conversation memory feature enabled
- `cleanup_status` - Migration cleanup status
- `removed_files` - Number of legacy files removed during migration
- `timestamp` - ISO 8601 timestamp

**Use Cases:**

- Configuration validation
- Pre-deployment checks
- Feature availability verification
- System compatibility checking
- Documentation of production configuration

**Behaviour:**

- Reads configuration from ExecutionConfig
- No heavy computation (very fast, ~2-5ms)
- Static configuration information
- Safe to call frequently

**Validation:**

- No input parameters

**Example Usage (Python - Pre-deployment Check):**

```python
import requests

def verify_deployment_config():
    """Verify system configuration before deploying workflows."""
    response = requests.get("http://localhost:8000/api/monitoring/status")
    config = response.json()

    # Verify required features
    assert config["engine"] == "langgraph", "Wrong execution engine"
    assert config["checkpointing_enabled"], "Checkpointing required"
    assert config["memory_enabled"], "Memory required"

    print("✅ System configuration validated")
    print(f"   Engine: {config['engine']}")
    print(f"   Checkpointing: {config['checkpointing_enabled']}")
    print(f"   Memory: {config['memory_enabled']}")

    return config

# Use in deployment script
config = verify_deployment_config()
```

---

#### `GET /api/monitoring/diagnostics`

Run comprehensive diagnostic checks on all system components. Returns detailed status for graph manager, execution
engine, integration layer, and metrics system.

**Authentication:** None

**Response:**

```json
{
  "timestamp": "2025-10-21T08:30:46.456Z",
  "overall_status": "healthy",
  "checks": {
    "graph_manager": {
      "status": "ok",
      "message": null,
      "error": null,
      "details": null,
      "graphs_loaded": 23,
      "graphs": [
        "customer-support-workflow",
        "data-pipeline-etl",
        "content-moderation",
        "email-classifier",
        "document-processor",
        "lead-scoring",
        "sentiment-analysis",
        "chatbot-agent",
        "research-assistant",
        "code-reviewer"
      ]
    },
    "execution_engine": {
      "status": "ok",
      "message": null,
      "error": null,
      "details": null,
      "type": "LangGraphExecutionEngine"
    },
    "integration": {
      "status": "ok",
      "message": null,
      "error": null,
      "details": null,
      "engine": "langgraph",
      "implementation": "standard",
      "cleanup": "complete"
    },
    "metrics": {
      "status": "ok",
      "message": null,
      "error": null,
      "details": null,
      "metrics_count": 47,
      "collection_active": true
    }
  }
}
```

**Overall Status Values:**

- `healthy` - All checks passed
- `degraded` - Some checks have warnings or non-critical failures
- `unhealthy` - Critical checks failed

**Check Status Values:**

- `ok` - Check passed
- `warning` - Check passed with warnings
- `error` - Check failed

**Use Cases:**

- System troubleshooting
- Pre-deployment validation
- Post-deployment verification
- Incident investigation
- Component health verification
- Integration testing

**Behaviour:**

- Runs 4 diagnostic checks in sequence
- Each check is independent (failure of one doesn't block others)
- Checks actual component availability (not just configuration)
- Response time: ~50-100ms (depends on component response)
- Safe to run frequently (read-only operations)

**Validation:**

- No input parameters

**Example Usage (Python - System Validation):**

```python
import requests
from typing import Dict, Any

def run_system_diagnostics() -> Dict[str, Any]:
    """Run comprehensive system diagnostics."""
    response = requests.get("http://localhost:8000/api/monitoring/diagnostics")
    diagnostics = response.json()

    print(f"🔍 System Diagnostics ({diagnostics['timestamp']})")
    print(f"Overall Status: {diagnostics['overall_status'].upper()}\n")

    # Check each component
    for component, check in diagnostics['checks'].items():
        status_emoji = "✅" if check['status'] == 'ok' else "❌"
        print(f"{status_emoji} {component.replace('_', ' ').title()}: {check['status']}")

        # Display additional info
        if check.get('graphs_loaded'):
            print(f"   Loaded {check['graphs_loaded']} graphs")
        if check.get('type'):
            print(f"   Type: {check['type']}")
        if check.get('metrics_count'):
            print(f"   Tracking {check['metrics_count']} metrics")
            print(f"   Collection active: {check['collection_active']}")
        if check.get('error'):
            print(f"   ⚠️  Error: {check['error']}")

    return diagnostics

# Use in health check script
diagnostics = run_system_diagnostics()
if diagnostics['overall_status'] != 'healthy':
    print("\n⚠️  System is not fully healthy!")
    exit(1)
```

**Example Response (Error State):**

```json
{
  "timestamp": "2025-10-21T08:35:12.789Z",
  "overall_status": "degraded",
  "checks": {
    "graph_manager": {
      "status": "error",
      "message": null,
      "error": "Connection refused",
      "details": null
    },
    "execution_engine": {
      "status": "ok",
      "type": "LangGraphExecutionEngine"
    },
    "integration": {
      "status": "ok",
      "engine": "langgraph",
      "implementation": "standard",
      "cleanup": "complete"
    },
    "metrics": {
      "status": "ok",
      "metrics_count": 47,
      "collection_active": true
    }
  }
}
```

---

#### `GET /api/monitoring/feature-flags`

Get current feature flag configuration showing which experimental and optional features are enabled.

**Authentication:** None

**Response:**

```json
{
  "use_unified_state": true,
  "use_compile_time_tools": true,
  "cache_subgraphs": true,
  "enable_performance_tracking": true,
  "parallel_tool_execution": true,
  "use_memory": true,
  "timestamp": "2025-10-21T08:30:47.123Z"
}
```

**Feature Flags:**

- `use_unified_state` - Unified state management for workflows
- `use_compile_time_tools` - Compile-time tool resolution (better performance)
- `cache_subgraphs` - Cache compiled subgraphs
- `enable_performance_tracking` - Detailed performance metrics collection
- `parallel_tool_execution` - Execute independent tools in parallel
- `use_memory` - Conversation memory across workflow executions

**Use Cases:**

- Feature availability checking
- Client capability detection
- Configuration documentation
- A/B testing support
- Gradual feature rollout monitoring

**Behaviour:**

- Reads feature flags from ExecutionConfig.get_features()
- Fast response (~2-5ms)
- Returns current runtime configuration
- Safe to call frequently

**Validation:**

- No input parameters

**Example Usage (Python - Client Feature Detection):**

```python
import requests

class AgenticStudioClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.features = self._detect_features()

    def _detect_features(self) -> dict:
        """Detect available features from server."""
        response = requests.get(f"{self.base_url}/api/monitoring/feature-flags")
        return response.json()

    def supports_parallel_tools(self) -> bool:
        """Check if server supports parallel tool execution."""
        return self.features.get("parallel_tool_execution", False)

    def supports_memory(self) -> bool:
        """Check if server supports conversation memory."""
        return self.features.get("use_memory", False)

    def execute_workflow(self, workflow_id: str, inputs: dict):
        """Execute workflow with feature-aware configuration."""
        config = {}

        # Use parallel tools if available
        if self.supports_parallel_tools():
            config["parallel_execution"] = True

        # Use memory if available
        if self.supports_memory():
            config["use_memory"] = True

        # Execute workflow with detected capabilities
        # ... execution logic ...

# Client automatically adapts to server capabilities
client = AgenticStudioClient("http://localhost:8000")
if client.supports_memory():
    print("✅ Server supports conversation memory")
```

**Example Usage (JavaScript/TypeScript):**

```typescript
interface FeatureFlags {
  use_unified_state: boolean;
  use_compile_time_tools: boolean;
  cache_subgraphs: boolean;
  enable_performance_tracking: boolean;
  parallel_tool_execution: boolean;
  use_memory: boolean;
  timestamp: string;
}

async function getServerFeatures(): Promise<FeatureFlags> {
  const response = await fetch('http://localhost:8000/api/monitoring/feature-flags');
  return response.json();
}

// Use in application initialization
const features = await getServerFeatures();
console.log('Server features:', features);

// Configure client based on server capabilities
const clientConfig = {
  parallelTools: features.parallel_tool_execution,
  memory: features.use_memory,
  performanceTracking: features.enable_performance_tracking,
};
```

---

### Maintenance Operations (2 endpoints)

#### `POST /api/monitoring/cache/clear`

Clear all system caches including graph manager caches, health check caches, and system info caches. Use when deploying
new graphs or debugging caching issues.

**Authentication:** None (should be restricted at infrastructure level)

**Request:** No body required

**Response:**

```json
{
  "status": "success",
  "message": "Cleared 3 cache(s)",
  "timestamp": "2025-10-21T08:30:47.456Z",
  "caches_cleared": [
    "graph_manager",
    "system_info",
    "health_checks"
  ]
}
```

**Fields:**

- `status` - Operation status ("success" or "error")
- `message` - Human-readable status message
- `timestamp` - ISO 8601 timestamp of operation
- `caches_cleared` - List of cache names that were cleared

**Caches Cleared:**

1. **graph_manager** - Graph compilation and metadata cache
2. **system_info** - System information cache (platform, resources)
3. **health_checks** - Component status cache

**Use Cases:**

- After deploying new workflow versions
- Debugging stale cache issues
- Forcing fresh metrics collection
- Post-configuration changes
- Manual cache management

**Behaviour:**

- Attempts to clear all caches independently
- Partial failures logged but don't stop other cache clearing
- Thread-safe operation
- Returns list of successfully cleared caches
- Response time: ~10-20ms

**Side Effects:**

- Next health check will re-query all components
- Next system info request will call psutil
- Graph manager will recompile workflows on next access

**Validation:**

- No input validation required

**Security:**

- Consider restricting to internal network
- Add infrastructure-level auth for production
- Monitor for abuse (frequent clearing)

**Example Usage (Python):**

```python
import requests

def clear_caches():
    """Clear all system caches."""
    response = requests.post("http://localhost:8000/api/monitoring/cache/clear")
    result = response.json()

    print(f"Cache clear: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Cleared: {', '.join(result['caches_cleared'])}")

    return result

# Use after deploying new workflow
def deploy_workflow(workflow_def: dict):
    # Deploy workflow
    # ...

    # Clear caches to ensure fresh compilation
    clear_caches()
    print("✅ Workflow deployed and caches cleared")

# Use in debugging
def debug_stale_metrics():
    print("Clearing caches to get fresh metrics...")
    clear_caches()

    # Wait a moment for background collection
    import time
    time.sleep(2)

    # Fetch fresh metrics
    response = requests.get("http://localhost:8000/api/monitoring/metrics/dashboard")
    print("Fresh metrics:", response.json())
```

**Example Usage (curl):**

```bash
# Clear all caches
curl -X POST http://localhost:8000/api/monitoring/cache/clear

# Use in deployment script
#!/bin/bash
echo "Deploying new workflow..."
# ... deployment logic ...

echo "Clearing caches..."
curl -X POST http://localhost:8000/api/monitoring/cache/clear

echo "Deployment complete"
```

---

#### `POST /api/monitoring/optimize`

Trigger system performance optimisations. Currently optimises graph manager performance and can be extended for
additional optimisation operations.

**Authentication:** None (should be restricted at infrastructure level)

**Request:** No body required

**Response:**

```json
{
  "status": "success",
  "message": "Applied 1 optimization(s)",
  "timestamp": "2025-10-21T08:30:47.789Z",
  "optimizations_applied": [
    "graph_manager_optimization"
  ]
}
```

**Fields:**

- `status` - Operation status ("success" or "error")
- `message` - Human-readable status message
- `timestamp` - ISO 8601 timestamp of operation
- `optimizations_applied` - List of optimisations that were applied

**Optimisations Applied:**

1. **graph_manager_optimization** - Optimises graph compilation caches and internal structures

**Use Cases:**

- After system has been running for extended periods
- Before high-load events
- During maintenance windows
- Performance tuning
- Proactive optimisation

**Behaviour:**

- Calls optimise_performance() on GraphManager if available
- Gracefully handles components that don't support optimisation
- Logs optimisation operations
- Thread-safe
- Response time: ~50-200ms (depends on optimisation operations)

**Side Effects:**

- May trigger garbage collection
- May reorganise internal data structures
- May clear stale cache entries
- Temporary CPU spike during optimisation

**Validation:**

- No input validation required

**Security:**

- Consider restricting to internal network
- Add infrastructure-level auth for production
- Monitor for abuse (excessive optimisation calls)

**When to Call:**

- During low-traffic periods (maintenance windows)
- After deploying many workflows
- When performance degradation observed
- As part of scheduled maintenance (e.g., weekly)

**When NOT to Call:**

- During peak traffic
- More than once per hour
- During active workflow executions

**Example Usage (Python - Scheduled Maintenance):**

```python
import requests
import schedule
import time

def run_optimization():
    """Run system optimization during maintenance window."""
    print(f"Running optimization at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    response = requests.post("http://localhost:8000/api/monitoring/optimize")
    result = response.json()

    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    print(f"Optimizations: {', '.join(result['optimizations_applied'])}")

    return result

# Schedule optimization weekly on Sundays at 2 AM
schedule.every().sunday.at("02:00").do(run_optimization)

print("Optimization scheduler started")
while True:
    schedule.run_pending()
    time.sleep(60)
```

**Example Usage (Kubernetes CronJob):**

```yaml
# k8s-optimization-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: agenticstudio-optimization
spec:
  # Run every Sunday at 2 AM
  schedule: "0 2 * * 0"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: optimizer
            image: curlimages/curl:latest
            command:
            - /bin/sh
            - -c
            - |
              echo "Running AgenticStudio optimization..."
              curl -X POST http://agenticstudio-service:8000/api/monitoring/optimize
              echo "Optimization complete"
          restartPolicy: OnFailure
```

**Example Usage (bash script):**

```bash
#!/bin/bash
# optimize-system.sh - Run system optimization

echo "🔧 Starting system optimization..."
response=$(curl -s -X POST http://localhost:8000/api/monitoring/optimize)

# Parse response
status=$(echo "$response" | jq -r '.status')
message=$(echo "$response" | jq -r '.message')

if [ "$status" = "success" ]; then
  echo "✅ Optimization successful: $message"
  exit 0
else
  echo "❌ Optimization failed: $message"
  exit 1
fi
```

---

## Error Handling

### Error Response Format

All monitoring endpoints use a consistent error response format:

```json
{
  "error": "validation_error",
  "message": "Invalid export format",
  "detail": "Invalid format: xml. Must be json, prometheus, or statsd",
  "timestamp": "2025-10-21T08:30:48.123Z"
}
```

**Error Response Fields:**

- `error` - Error type/category (snake_case)
- `message` - Brief error description
- `detail` (optional) - Additional error details
- `timestamp` - ISO 8601 timestamp when error occurred

### Common Error Codes

#### 400 Bad Request

**When:** Invalid input parameters

**Example Scenarios:**

- Invalid metrics export format
- Malformed query parameters

**Example Response:**

```json
{
  "detail": "Invalid format: xml. Must be json, prometheus, or statsd"
}
```

**How to Handle:**

```python
try:
    response = requests.get(
        "http://localhost:8000/api/monitoring/metrics",
        params={"export_format": "xml"}
    )
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print(f"Invalid request: {e.response.json()['detail']}")
```

#### 500 Internal Server Error

**When:** Unexpected server errors, component failures

**Example Scenarios:**

- Database connection failure during health check
- Metrics collection failure
- Component initialisation error

**Example Response:**

```json
{
  "detail": "metrics_dashboard failed: Connection to metrics backend lost"
}
```

**How to Handle:**

```python
def get_metrics_with_retry(max_retries=3):
    """Get metrics with automatic retry on server errors."""
    for attempt in range(max_retries):
        try:
            response = requests.get("http://localhost:8000/api/monitoring/metrics/dashboard")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                if attempt < max_retries - 1:
                    print(f"Server error, retrying ({attempt + 1}/{max_retries})...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print("Max retries reached, giving up")
                    raise
            else:
                raise
```

### Error Handling Decorator Pattern

The monitoring module uses a decorator pattern for consistent error handling across all endpoints.

**Implementation:** [utils.py:23-51](utils.py#L23-L51)

```python
@handle_monitoring_errors("endpoint_name")
async def endpoint():
    # Endpoint logic
    pass
```

**Behaviour:**

- Catches all exceptions except HTTPException (which are re-raised)
- Logs errors with consistent formatting
- Returns 500 with detailed error message
- Includes endpoint name in error detail for debugging

**Example from routes.py:**

```python
@router.get("/metrics/dashboard", response_model=DashboardMetricsResponse)
@handle_monitoring_errors("metrics_dashboard")
async def metrics_dashboard() -> DashboardMetricsResponse:
    # If any exception occurs, decorator catches it and returns:
    # HTTPException(status_code=500, detail="metrics_dashboard failed: {error}")
    metrics_manager = get_metrics_manager()
    return metrics_manager.get_dashboard_data()
```

### Error Handling Example

Complete example showing proper error handling for monitoring API calls:

```python
import requests
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MonitoringClient:
    """Client for AgenticStudio monitoring API with proper error handling."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def get_health(self, detailed: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get system health status.

        Args:
            detailed: If True, get detailed health check

        Returns:
            Health status dict or None if request fails
        """
        endpoint = "/api/monitoring/health/detailed" if detailed else "/api/monitoring/health"

        try:
            response = requests.get(
                f"{self.base_url}{endpoint}",
                timeout=10
            )
            response.raise_for_status()
            health = response.json()

            # Log if system is not healthy
            if health.get("status") != "healthy":
                logger.warning(f"System status: {health['status']}")
                if health.get("warnings"):
                    for warning in health["warnings"]:
                        logger.warning(f"  - {warning}")

            return health

        except requests.exceptions.Timeout:
            logger.error("Health check timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to monitoring API")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Health check failed: HTTP {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during health check: {e}")
            return None

    def get_metrics(self, format: str = "json") -> Optional[Dict[str, Any]]:
        """
        Get system metrics in specified format.

        Args:
            format: Export format (json, prometheus, statsd)

        Returns:
            Metrics dict or None if request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/monitoring/metrics",
                params={"export_format": format},
                timeout=10
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                logger.error(f"Invalid metrics format: {format}")
                logger.error(f"Error detail: {e.response.json().get('detail')}")
            else:
                logger.error(f"Metrics request failed: HTTP {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting metrics: {e}")
            return None

# Usage example
client = MonitoringClient("http://localhost:8000")

# Check health
health = client.get_health(detailed=True)
if health and health["status"] == "healthy":
    print("✅ System is healthy")
else:
    print("⚠️ System has issues")

# Get metrics
metrics = client.get_metrics(format="json")
if metrics:
    print(f"📊 Collected {len(metrics)} metrics")
```

---

## Integration with Services Layer

### Dependency Flow

The monitoring module integrates with multiple services across the AgenticStudio backend:

```
Monitoring Routes
    │
    ├─→ Health Service (services/health.py)
    │   ├─→ get_graph_manager() → GraphManager
    │   ├─→ get_execution_engine() → ExecutionEngine
    │   └─→ get_metrics_manager() → MetricsManager
    │
    ├─→ Diagnostics Service (services/diagnostics.py)
    │   ├─→ get_graph_manager() → GraphManager
    │   ├─→ get_execution_engine() → ExecutionEngine
    │   └─→ get_metrics_manager() → MetricsManager
    │
    ├─→ System Info Service (services/system_info.py)
    │   └─→ ExecutionConfig
    │
    ├─→ Feature Flags Service (services/feature_flags.py)
    │   └─→ ExecutionConfig.get_features()
    │
    └─→ Utils (utils.py)
        ├─→ get_graph_manager() → GraphManager
        └─→ get_metrics_manager() → MetricsManager
```

### Example Integration

Complete example showing how monitoring routes integrate with services:

**Route Handler:** [routes.py:48-56](routes.py#L48-L56)

```python
@router.get("/health/detailed", response_model=DetailedHealthCheckResponse)
async def detailed_health_check() -> DetailedHealthCheckResponse:
    """Detailed health check with comprehensive system information."""
    return get_detailed_health()
```

**Service Implementation:** [services/health.py:139-225](services/health.py#L139-L225)

```python
def get_detailed_health() -> DetailedHealthCheckResponse:
    """Perform detailed health check with comprehensive information."""
    try:
        # Get basic health
        basic_health = get_basic_health()

        # Get metrics from MetricsManager
        metrics_manager = get_metrics_manager()
        dashboard_data = metrics_manager.get_dashboard_data()

        # Extract and structure metrics
        system_metrics = SystemMetrics(
            cpu_percent=dashboard_data.get("system", {}).get("cpu_percent", 0.0),
            memory_percent=dashboard_data.get("system", {}).get("memory_percent", 0.0),
            process_memory_mb=dashboard_data.get("system", {}).get("process_memory_mb", 0.0),
        )

        # Get configuration from ExecutionConfig
        config = ConfigurationInfo(
            engine="langgraph",
            checkpointing_enabled=ExecutionConfig.use_checkpointing(),
            memory_enabled=ExecutionConfig.use_memory(),
        )

        # Build comprehensive response
        return DetailedHealthCheckResponse(
            status=basic_health.status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            components=basic_health.components,
            configuration=config,
            system_metrics=system_metrics,
            application_metrics=application_metrics,
            alerts=alerts,
        )
    except Exception as e:
        logger.error(f"[MONITORING-HEALTH] Detailed health check failed: {e}")
        # Return minimal error response
        return DetailedHealthCheckResponse(...)
```

**Component Check:** [services/health.py:69-97](services/health.py#L69-L97)

```python
def get_component_status() -> ComponentInfo:
    """Get status of system components."""
    # Try cache first (5 second TTL)
    cached = _get_cached("component_status")
    if cached:
        return cached

    try:
        # Check if components are available via dependency injection
        get_graph_manager()  # Raises if unavailable
        get_execution_engine()  # Raises if unavailable

        component_info = ComponentInfo(
            graph_manager="ready",
            execution_engine="ready",
            database="connected"
        )

        _set_cached("component_status", component_info)
        return component_info

    except Exception as e:
        logger.error(f"[MONITORING-HEALTH] Error checking components: {e}")
        return ComponentInfo(
            graph_manager="error",
            execution_engine="error",
            database="unknown"
        )
```

### Services Used

#### MetricsManager

**Location:** `backend/services/metrics/`

**Purpose:** Collect, aggregate, and export application and system metrics

**Usage in Monitoring:**

- Dashboard metrics aggregation
- Metrics export (Prometheus, StatsD, JSON)
- Alert generation based on thresholds
- Performance tracking

**Integration Points:**

```python
from ...services.metrics import get_metrics_manager

metrics_manager = get_metrics_manager()

# Get all metrics
all_metrics = metrics_manager.collector.get_all_metrics()

# Get dashboard data
dashboard_data = metrics_manager.get_dashboard_data()

# Export to Prometheus
prometheus_export = metrics_manager.export("prometheus")

# Export to StatsD
statsd_commands = metrics_manager.statsd_exporter.export()
```

#### GraphManager

**Location:** `backend/services/dependency_injection/`

**Purpose:** Manage workflow graphs, compilation, and execution coordination

**Usage in Monitoring:**

- Component health checking
- Graph list retrieval (diagnostics)
- Cache clearing
- Performance optimisation

**Integration Points:**

```python
from ...services.dependency_injection import get_graph_manager

graph_manager = get_graph_manager()

# List all graphs
graphs = graph_manager.list_graphs()

# Clear caches
if hasattr(graph_manager, "clear_caches"):
    graph_manager.clear_caches()

# Optimize performance
if hasattr(graph_manager, "optimize_performance"):
    graph_manager.optimize_performance()
```

#### ExecutionEngine

**Location:** `backend/services/dependency_injection/`

**Purpose:** Execute workflow graphs using LangGraph

**Usage in Monitoring:**

- Component health checking
- Engine type identification (diagnostics)
- Execution status verification

**Integration Points:**

```python
from ...services.dependency_injection import get_execution_engine

execution_engine = get_execution_engine()

# Get engine type
engine_type = type(execution_engine).__name__  # "LangGraphExecutionEngine"

# Health check (just verify it's available)
# If this doesn't raise, engine is healthy
```

#### ExecutionConfig

**Location:** `backend/services/config/`

**Purpose:** Configuration management for execution features and settings

**Usage in Monitoring:**

- Feature flag retrieval
- Configuration status reporting
- Checkpointing/memory status

**Integration Points:**

```python
from ...services.config import ExecutionConfig

# Get feature flags
features = ExecutionConfig.get_features()
# Returns: FeatureConfig with use_unified_state, cache_subgraphs, etc.

# Check specific features
checkpointing_enabled = ExecutionConfig.use_checkpointing()
memory_enabled = ExecutionConfig.use_memory()
```

---

## Usage Examples

### Complete Monitoring Integration Example

This example shows a complete monitoring integration for a production AgenticStudio deployment:

```python
"""
Production monitoring integration for AgenticStudio.

This module provides comprehensive monitoring including:
- Health checks
- Metrics collection
- Alerting
- Dashboard integration
"""

import requests
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """System alert."""
    level: str
    message: str
    timestamp: str


class AgenticStudioMonitor:
    """Comprehensive monitoring client for AgenticStudio."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.alert_threshold = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "cache_hit_rate": 0.5,
            "error_rate": 0.05,
        }

    def check_health(self) -> bool:
        """
        Check if system is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/monitoring/health",
                timeout=5
            )
            response.raise_for_status()

            health = response.json()
            is_healthy = health.get("status") == "healthy"

            if not is_healthy:
                logger.warning(f"System unhealthy: {health.get('status')}")
                for warning in health.get("warnings", []):
                    logger.warning(f"  - {warning}")

            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_detailed_health(self) -> Optional[Dict[str, Any]]:
        """Get detailed health information."""
        try:
            response = requests.get(
                f"{self.base_url}/api/monitoring/health/detailed",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get detailed health: {e}")
            return None

    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """Get dashboard metrics."""
        try:
            response = requests.get(
                f"{self.base_url}/api/monitoring/metrics/dashboard",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return None

    def run_diagnostics(self) -> Optional[Dict[str, Any]]:
        """Run comprehensive diagnostics."""
        try:
            response = requests.get(
                f"{self.base_url}/api/monitoring/diagnostics",
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Diagnostics failed: {e}")
            return None

    def check_alerts(self, metrics: Dict[str, Any]) -> List[Alert]:
        """
        Check metrics for alert conditions.

        Args:
            metrics: Dashboard metrics response

        Returns:
            List of alerts
        """
        alerts = []

        # Check server-side alerts first
        for alert_data in metrics.get("alerts", []):
            alerts.append(Alert(
                level=alert_data["level"],
                message=alert_data["message"],
                timestamp=alert_data["timestamp"]
            ))

        # Check custom thresholds
        system = metrics.get("system", {})
        application = metrics.get("application", {})

        # CPU alert
        cpu_percent = system.get("cpu_percent", 0)
        if cpu_percent > self.alert_threshold["cpu_percent"]:
            alerts.append(Alert(
                level="warning",
                message=f"High CPU usage: {cpu_percent:.1f}%",
                timestamp=datetime.utcnow().isoformat()
            ))

        # Memory alert
        memory_percent = system.get("memory_percent", 0)
        if memory_percent > self.alert_threshold["memory_percent"]:
            alerts.append(Alert(
                level="warning",
                message=f"High memory usage: {memory_percent:.1f}%",
                timestamp=datetime.utcnow().isoformat()
            ))

        # Cache hit rate alert
        cache_hit_rate = application.get("cache_hit_rate", 1.0)
        if cache_hit_rate < self.alert_threshold["cache_hit_rate"]:
            alerts.append(Alert(
                level="warning",
                message=f"Low cache hit rate: {cache_hit_rate * 100:.1f}%",
                timestamp=datetime.utcnow().isoformat()
            ))

        # Error rate alert
        agent_execs = application.get("agent_executions", {})
        if agent_execs:
            total = agent_execs.get("total", 0)
            failed = agent_execs.get("failed", 0)
            if total > 0:
                error_rate = failed / total
                if error_rate > self.alert_threshold["error_rate"]:
                    alerts.append(Alert(
                        level="critical",
                        message=f"High error rate: {error_rate * 100:.1f}% ({failed}/{total} failed)",
                        timestamp=datetime.utcnow().isoformat()
                    ))

        return alerts

    def monitor_loop(self, interval: int = 60):
        """
        Continuous monitoring loop.

        Args:
            interval: Check interval in seconds
        """
        logger.info(f"Starting monitoring loop (interval: {interval}s)")

        while True:
            try:
                # Check basic health
                is_healthy = self.check_health()

                # Get detailed metrics
                metrics = self.get_metrics()

                if metrics:
                    # Check for alerts
                    alerts = self.check_alerts(metrics)

                    # Log critical alerts
                    for alert in alerts:
                        if alert.level == "critical":
                            logger.error(f"🚨 CRITICAL: {alert.message}")
                        elif alert.level == "warning":
                            logger.warning(f"⚠️  WARNING: {alert.message}")

                    # Log metrics summary
                    system = metrics.get("system", {})
                    application = metrics.get("application", {})

                    logger.info(f"📊 Metrics: CPU={system.get('cpu_percent', 0):.1f}% "
                              f"Memory={system.get('memory_percent', 0):.1f}% "
                              f"Cache={application.get('cache_hit_rate', 0) * 100:.1f}%")

                # Every 10 minutes, run full diagnostics
                if int(time.time()) % 600 == 0:
                    logger.info("Running full diagnostics...")
                    diagnostics = self.run_diagnostics()
                    if diagnostics:
                        status = diagnostics.get("overall_status")
                        logger.info(f"Diagnostics: {status}")

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

            time.sleep(interval)

    def export_to_prometheus(self, output_file: str = "/tmp/agenticstudio_metrics.prom"):
        """
        Export metrics to Prometheus format file.

        Args:
            output_file: Path to output file
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/monitoring/metrics",
                params={"export_format": "prometheus"},
                timeout=10
            )
            response.raise_for_status()

            # Write Prometheus format to file
            with open(output_file, 'w') as f:
                f.write(response.text)

            logger.info(f"Exported Prometheus metrics to {output_file}")

        except Exception as e:
            logger.error(f"Failed to export Prometheus metrics: {e}")


# Example 1: Simple health check script
def simple_health_check():
    """Simple health check for cronjobs."""
    monitor = AgenticStudioMonitor("http://localhost:8000")

    if monitor.check_health():
        print("✅ AgenticStudio is healthy")
        exit(0)
    else:
        print("❌ AgenticStudio is unhealthy")
        exit(1)


# Example 2: Pre-deployment validation
def validate_deployment():
    """Validate system before deployment."""
    monitor = AgenticStudioMonitor("http://localhost:8000")

    print("🔍 Running pre-deployment checks...")

    # Check health
    if not monitor.check_health():
        print("❌ Health check failed")
        return False
    print("✅ Health check passed")

    # Run diagnostics
    diagnostics = monitor.run_diagnostics()
    if not diagnostics or diagnostics.get("overall_status") != "healthy":
        print("❌ Diagnostics failed")
        return False
    print("✅ Diagnostics passed")

    # Check metrics
    metrics = monitor.get_metrics()
    if not metrics:
        print("❌ Metrics unavailable")
        return False

    # Check no critical alerts
    alerts = monitor.check_alerts(metrics)
    critical_alerts = [a for a in alerts if a.level == "critical"]
    if critical_alerts:
        print(f"❌ {len(critical_alerts)} critical alerts")
        for alert in critical_alerts:
            print(f"  - {alert.message}")
        return False
    print("✅ No critical alerts")

    print("\n✅ All pre-deployment checks passed!")
    return True


# Example 3: Continuous monitoring daemon
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        # Run pre-deployment validation
        success = validate_deployment()
        sys.exit(0 if success else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "health":
        # Simple health check
        simple_health_check()
    else:
        # Continuous monitoring
        monitor = AgenticStudioMonitor("http://localhost:8000")
        monitor.monitor_loop(interval=30)
```

### Grafana Dashboard Integration

Example Grafana dashboard configuration using Prometheus data source:

```json
{
  "dashboard": {
    "title": "AgenticStudio Monitoring",
    "panels": [
      {
        "title": "System Health",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=\"agenticstudio\"}",
            "legendFormat": "Status"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_cpu_percent",
            "legendFormat": "CPU %"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "system_memory_percent",
            "legendFormat": "Memory %"
          }
        ]
      },
      {
        "title": "Execution Success Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(agent_executions_success[5m]) / rate(agent_executions_total[5m])",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Cache Hit Rate",
        "type": "gauge",
        "targets": [
          {
            "expr": "cache_hits / (cache_hits + cache_misses)",
            "legendFormat": "Hit Rate"
          }
        ]
      }
    ]
  }
}
```

---

## Performance Considerations

### Endpoint Performance

Monitoring endpoints are categorised by typical response time:

#### Fast Endpoints (< 10ms)

**Characteristics:** Cached data, minimal computation, configuration reads

- `GET /api/monitoring/health` - Basic health check with 5s cache
- `GET /api/monitoring/status` - Configuration read from ExecutionConfig
- `GET /api/monitoring/feature-flags` - Static configuration retrieval

**Best Practices:**

- Safe to call frequently (every 1-5 seconds)
- Ideal for load balancer health checks
- Use for high-frequency monitoring

**Example:**

```python
# Fast polling for load balancer
while True:
    health = requests.get("http://localhost:8000/api/monitoring/health").json()
    if health["status"] != "healthy":
        # Remove from load balancer pool
        pass
    time.sleep(2)  # 2 second polling is fine for fast endpoints
```

#### Medium Endpoints (10-100ms)

**Characteristics:** Aggregated metrics, moderate computation, service calls

- `GET /api/monitoring/health/detailed` - Aggregates metrics + health checks
- `GET /api/monitoring/metrics` - Exports metrics (all formats)
- `GET /api/monitoring/metrics/dashboard` - Dashboard metrics aggregation
- `GET /api/monitoring/diagnostics` - Component checks
- `POST /api/monitoring/cache/clear` - Cache clearing operations

**Best Practices:**

- Poll every 10-60 seconds
- Use for dashboards and monitoring displays
- Consider caching results client-side

**Example:**

```python
# Medium-frequency dashboard updates
while True:
    metrics = requests.get("http://localhost:8000/api/monitoring/metrics/dashboard").json()
    update_dashboard(metrics)
    time.sleep(15)  # 15 second updates for dashboards
```

#### Slow Endpoints (100-500ms)

**Characteristics:** Performance optimisations, heavy computations

- `POST /api/monitoring/optimize` - Performance optimisation operations

**Best Practices:**

- Call during maintenance windows only
- Don't call more than once per hour
- Avoid during peak traffic
- Use async/background jobs

**Example:**

```python
# Schedule optimization for low-traffic periods
import schedule

def optimize_system():
    """Run during maintenance window only."""
    print("Running optimization (this may take a moment)...")
    response = requests.post("http://localhost:8000/api/monitoring/optimize")
    print(f"Optimization complete: {response.json()['message']}")

# Run at 2 AM every Sunday
schedule.every().sunday.at("02:00").do(optimize_system)
```

### Optimisation Tips

#### Good: Use caching and batch requests

```python
# GOOD: Cache health checks client-side
class MonitoringClient:
    def __init__(self, base_url: str, cache_ttl: int = 5):
        self.base_url = base_url
        self.cache_ttl = cache_ttl
        self._health_cache = None
        self._health_cache_time = 0

    def get_health(self) -> dict:
        """Get health with client-side caching."""
        now = time.time()
        if self._health_cache and (now - self._health_cache_time) < self.cache_ttl:
            return self._health_cache

        response = requests.get(f"{self.base_url}/api/monitoring/health")
        self._health_cache = response.json()
        self._health_cache_time = now
        return self._health_cache
```

```python
# GOOD: Batch multiple monitoring checks
async def get_system_status():
    """Get complete status in parallel."""
    import asyncio
    import aiohttp

    async with aiohttp.ClientSession() as session:
        # Fetch multiple endpoints in parallel
        health_task = session.get("http://localhost:8000/api/monitoring/health")
        metrics_task = session.get("http://localhost:8000/api/monitoring/metrics/dashboard")
        features_task = session.get("http://localhost:8000/api/monitoring/feature-flags")

        # Wait for all
        health, metrics, features = await asyncio.gather(
            health_task,
            metrics_task,
            features_task
        )

        return {
            "health": await health.json(),
            "metrics": await metrics.json(),
            "features": await features.json(),
        }
```

#### Bad: Excessive polling or synchronous calls

```python
# BAD: Polling too frequently without caching
while True:
    health = requests.get("http://localhost:8000/api/monitoring/health/detailed").json()
    time.sleep(0.5)  # 0.5 second polling is excessive!
```

```python
# BAD: Sequential requests when parallel would work
def get_system_status():
    """Inefficient sequential calls."""
    health = requests.get("http://localhost:8000/api/monitoring/health").json()
    metrics = requests.get("http://localhost:8000/api/monitoring/metrics/dashboard").json()
    features = requests.get("http://localhost:8000/api/monitoring/feature-flags").json()
    return {"health": health, "metrics": metrics, "features": features}
    # This takes 3x longer than parallel requests!
```

### Caching Strategies

#### Server-Side Caching (Built-in)

The monitoring module implements automatic caching:

**Health Checks:** 5 second TTL

```python
# services/health.py
CACHE_TTL = 5.0  # 5 seconds

# Multiple calls within 5 seconds use cache
health1 = get_component_status()  # Queries components
health2 = get_component_status()  # Returns cached (< 5s)
time.sleep(6)
health3 = get_component_status()  # Queries components (> 5s)
```

**System Info:** 10 second TTL

```python
# services/system_info.py
SYSTEM_INFO_CACHE_TTL = 10.0  # 10 seconds

# psutil calls are expensive, cache reduces overhead
info1 = get_system_info()  # Calls psutil
info2 = get_system_info()  # Returns cached (< 10s)
```

#### Client-Side Caching

Implement client-side caching for additional performance:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedMonitoringClient:
    """Monitoring client with TTL-based caching."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self._cache = {}

    def _get_cached(self, key: str, ttl: int):
        """Get cached value if not expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                return value
        return None

    def _set_cached(self, key: str, value: any, ttl: int):
        """Set cached value with expiry."""
        expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)

    def get_health(self, ttl: int = 10) -> dict:
        """Get health with configurable TTL."""
        cached = self._get_cached("health", ttl)
        if cached:
            return cached

        response = requests.get(f"{self.base_url}/api/monitoring/health")
        health = response.json()
        self._set_cached("health", health, ttl)
        return health

    def get_features(self, ttl: int = 300) -> dict:
        """Get features with long TTL (features rarely change)."""
        cached = self._get_cached("features", ttl)
        if cached:
            return cached

        response = requests.get(f"{self.base_url}/api/monitoring/feature-flags")
        features = response.json()
        self._set_cached("features", features, ttl)
        return features
```

### Prometheus Configuration Best Practices

```yaml
# prometheus.yml
global:
  scrape_interval: 15s  # Don't scrape more frequently than cache TTL
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agenticstudio-monitoring'
    metrics_path: '/api/monitoring/metrics'
    params:
      export_format: ['prometheus']
    static_configs:
      - targets: ['agenticstudio-prod:8000']

    # Relabeling for better metric organisation
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: '(agent|tool)_.*'
        target_label: 'category'
        replacement: 'application'

      - source_labels: [__name__]
        regex: 'system_.*'
        target_label: 'category'
        replacement: 'system'

    # Only scrape if service is healthy
    scrape_interval: 15s
    scrape_timeout: 10s
```

---

## Related Documentation

### Architecture Documentation

- **[AgenticStudio Architecture Overview](../architecture/overview.md)** - System architecture and design patterns
- **[Services Layer Design](../architecture/services.md)** - Service layer architecture
- **[Dependency Injection](../architecture/dependency-injection.md)** - DI system used for component access

### API Documentation

- **[Graph API](../../../backend/api/graph/graph.md)** - Workflow management API (uses similar monitoring patterns)
- **[Execution API](../../../backend/api/execution/execution.md)** - Workflow execution endpoints
- **[WebSocket API](../websocket/websocket.md)** - Real-time execution streaming

### Services Documentation

- **[Metrics System](../../services/metrics.md)** - MetricsManager documentation
- **[Execution Config](../../services/config.md)** - ExecutionConfig and feature flags
- **[Graph Manager](../services/graph-manager.md)** - GraphManager service

### Operations Documentation

- **[Deployment Guide](../operations/deployment.md)** - Production deployment procedures
- **[Monitoring Setup](../operations/monitoring-setup.md)** - Complete monitoring stack setup
- **[Prometheus Integration](../operations/prometheus.md)** - Prometheus/Grafana integration guide
- **[Health Check Guide](../operations/health-checks.md)** - Load balancer and K8s health check configuration

### Development Documentation

- **[Contributing Guide](../../CONTRIBUTING.md)** - How to contribute to AgenticStudio
- **[Testing Guide](../development/testing.md)** - Testing monitoring endpoints
- **[Local Development](../development/local-setup.md)** - Running AgenticStudio locally

---

## Summary

The Monitoring API module is a critical observability component of AgenticStudio, providing comprehensive health checks,
metrics collection, diagnostics, and operational management capabilities. Its no-authentication design makes it ideal
for integration with external monitoring systems, load balancers, and Kubernetes probes.

### Key Features

- **Comprehensive Health Checks** - Basic and detailed health endpoints with component status validation
- **Multi-Format Metrics Export** - JSON, Prometheus, and StatsD format support for flexible monitoring integration
- **Intelligent Caching** - Built-in caching (5s for health, 10s for system info) minimises overhead
- **Component Diagnostics** - Detailed checks for GraphManager, ExecutionEngine, metrics system, and integration status
- **Dashboard-Ready Data** - Pre-formatted metrics optimised for dashboard display
- **Feature Flag Reporting** - Runtime feature configuration visibility
- **Operational Tools** - Cache clearing and performance optimisation endpoints
- **Clean Architecture** - Service-based design with clear separation of concerns
- **Error Handling** - Consistent error handling with decorator pattern
- **Performance Optimised** - Response times from 2ms (config reads) to 100ms (detailed metrics)

### Primary Use Cases

1. **Load Balancer Health Checks** - Fast, cached basic health endpoint for F5, HAProxy, AWS ALB
2. **Kubernetes Probes** - Liveness and readiness probes without authentication requirements
3. **Prometheus/Grafana Monitoring** - Native Prometheus format export for metric scraping
4. **Operations Dashboards** - Dashboard-formatted metrics with system and application categorisation
5. **System Diagnostics** - Comprehensive component validation for troubleshooting
6. **Pre-Deployment Validation** - Verify system health and configuration before deployments
7. **Alerting** - Built-in alert generation based on metric thresholds
8. **Performance Management** - Cache clearing and optimisation for operational maintenance
9. **Feature Detection** - Client-side feature capability detection via feature flags
10. **Incident Response** - Detailed diagnostics and component status during incidents

### Quick Start

```python
import requests

# Basic health check (load balancer)
health = requests.get("http://localhost:8000/api/monitoring/health").json()
print(f"Status: {health['status']}")

# Dashboard metrics
metrics = requests.get("http://localhost:8000/api/monitoring/metrics/dashboard").json()
print(f"CPU: {metrics['system']['cpu_percent']}%")
print(f"Cache hit rate: {metrics['application']['cache_hit_rate'] * 100}%")

# Diagnostics
diagnostics = requests.get("http://localhost:8000/api/monitoring/diagnostics").json()
print(f"Overall status: {diagnostics['overall_status']}")

# Feature flags
features = requests.get("http://localhost:8000/api/monitoring/feature-flags").json()
print(f"Memory enabled: {features['use_memory']}")
```

The monitoring module is production-ready, extensively tested, and designed for high-frequency access with minimal
performance impact. Its integration with the services layer provides accurate, real-time visibility into the AgenticStudio
system's health and performance.
