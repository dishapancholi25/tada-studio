# Metrics Service Documentation

## Overview

The metrics service provides comprehensive metrics collection, aggregation, and export capabilities for monitoring
application and system performance in AgenticStudio. It enables tracking of agent executions, tool usage, system resources,
cache performance, and other operational metrics.

**Location:** `backend/services/metrics/`

**Primary Responsibilities:**

- Collect and store time-series metric data points
- Track system metrics (CPU, memory, disk, network I/O)
- Monitor application metrics (agent executions, tool usage, cache hits)
- Calculate summary statistics (percentiles, averages, counts)
- Export metrics in multiple formats (JSON, Prometheus, StatsD)
- Provide dashboard-ready metrics aggregation
- Generate alerts based on threshold monitoring

**Key Use Cases:**

- Performance monitoring and profiling
- Resource usage tracking
- Application health monitoring
- Capacity planning and optimisation
- Integration with monitoring systems (Prometheus, Grafana, StatsD)

## Architecture

### Module Structure

```
backend/services/metrics/
├── __init__.py              # Public API exports
├── manager.py               # Main MetricsManager singleton
├── collector.py             # Core MetricCollector
├── models.py                # Data models and exceptions
├── config.py                # Configuration constants
├── utils.py                 # Validation and utility functions
├── collectors/              # Specialised metric collectors
│   ├── __init__.py
│   ├── base.py             # MetricCollectorInterface abstract base
│   ├── system.py           # SystemMetricsCollector (CPU, memory, I/O)
│   └── application.py      # ApplicationMetricsCollector (agents, tools)
└── exporters/               # Metric export formats
    ├── __init__.py
    ├── base.py             # MetricsExporter abstract base
    ├── json.py             # JSONExporter
    ├── prometheus.py       # PrometheusExporter
    └── statsd.py           # StatsDExporter
```

**File Descriptions:**

- `__init__.py` - Exports public API for easy importing
- `manager.py` - Singleton manager coordinating collection and export
- `collector.py` - Thread-safe collector storing metric data points
- `models.py` - Enums, dataclasses, and exceptions
- `config.py` - Environment-based configuration and constants
- `utils.py` - Validation helpers and calculations
- `collectors/` - Pluggable collectors for different metric categories
- `exporters/` - Export adapters for various monitoring formats

### Design Patterns

**Singleton Pattern:**

- `MetricsManager` implements singleton to ensure single global instance
- Thread-safe initialisation using double-checked locking

**Strategy Pattern:**

- Exporters implement `MetricsExporter` interface
- Different export strategies (JSON, Prometheus, StatsD) interchangeable

**Template Method Pattern:**

- `MetricCollectorInterface` defines collection template
- Concrete collectors implement specific collection logic

**Decorator Pattern:**

- Metric labels add dimensional metadata to data points
- Time windows filter metrics during aggregation

**Observer Pattern:**

- Background collection thread observes system metrics periodically
- Event-driven application metrics recorded on execution

### Dependencies

**Internal Dependencies:**

- `backend.services.config` - Logger configuration
- No other internal service dependencies (self-contained)

**External Dependencies:**

- `psutil` - System and process metrics collection
- `threading` - Background collection and thread safety
- `collections.deque` - Bounded metric history storage
- Standard library: `time`, `json`, `re`, `math`, `dataclasses`, `enum`, `typing`

**Database Dependencies:**

- None (metrics stored in-memory with configurable history)

**Environment Variables:**

- `METRICS_MAX_HISTORY` - Maximum data points per metric (default: 10000)
- `METRICS_COLLECTION_INTERVAL` - Collection interval in seconds (default: 30)
- `METRICS_CPU_WARNING` - CPU warning threshold percentage (default: 80.0)
- `METRICS_MEMORY_CRITICAL` - Memory critical threshold percentage (default: 90.0)
- `METRICS_ERROR_WARNING_COUNT` - Error count for warnings (default: 10)

## Public API

### Exported Functions

- `get_metrics_manager()` - Get singleton MetricsManager instance
- `reset_metrics()` - Reset metrics (primarily for testing)

### Exported Classes

- `MetricsManager` - Main metrics management coordinator
- `MetricCollector` - Core metric storage and aggregation
- `MetricCollectorInterface` - Abstract base for collectors
- `SystemMetricsCollector` - System resource metrics collector
- `ApplicationMetricsCollector` - Application event metrics collector
- `MetricsExporter` - Abstract base for exporters
- `PrometheusExporter` - Prometheus format exporter
- `JSONExporter` - JSON format exporter
- `StatsDExporter` - StatsD format exporter

### Exported Models

- `MetricType` - Enum for metric types (COUNTER, GAUGE, HISTOGRAM, SUMMARY)
- `MetricPoint` - Single metric data point with timestamp and labels
- `MetricSummary` - Summary statistics (count, sum, min, max, avg, percentiles)

### Exported Exceptions

```
Exception
└── MetricsError
    ├── InvalidMetricError
    └── ExportError
```

## Core Classes

### `MetricsManager`

Main metrics management class that coordinates metric collection, aggregation, and export.

**Purpose:** Provides unified interface for all metrics operations and manages background collection.

**Responsibilities:**

- Coordinate specialized collectors (system, application)
- Manage background collection thread
- Aggregate metrics for dashboard display
- Export metrics in various formats
- Check alert conditions and generate alerts

**Initialisation:**

```python
# Singleton - use get_metrics_manager() instead
manager = MetricsManager()
```

**Properties:**

- `collector: MetricCollector` - Core metric collector instance
- `system_metrics: SystemMetricsCollector` - System metrics collector
- `app_metrics: ApplicationMetricsCollector` - Application metrics collector
- `prometheus_exporter: PrometheusExporter` - Prometheus exporter
- `json_exporter: JSONExporter` - JSON exporter
- `statsd_exporter: StatsDExporter` - StatsD exporter

**Key Methods:**

#### `start_collection()`

```python
def start_collection(
    self,
    interval: int = DEFAULT_COLLECTION_INTERVAL,
) -> None:
    """Start background system metrics collection."""
```

**Parameters:**

- `interval` (int) - Collection interval in seconds (default: 30)

**Behaviour:**

- Starts daemon thread for background collection
- Collects system metrics at specified interval
- Logs errors but continues collection on failures
- Does nothing if collection already running

**Example:**

```python
from backend.services.metrics import get_metrics_manager

metrics = get_metrics_manager()
metrics.start_collection(interval=60)  # Collect every 60 seconds
```

**Use Cases:**

- Start monitoring when application initializes
- Custom collection intervals for different environments
- Production: longer intervals (60s) to reduce overhead
- Development: shorter intervals (10s) for rapid feedback

#### `stop_collection()`

```python
def stop_collection(self) -> None:
    """Stop background metrics collection."""
```

**Behaviour:**

- Sets stop event to signal collection thread
- Waits up to 5 seconds for thread to join
- Safe to call even if collection not running

**Example:**

```python
# Clean shutdown
try:
    # Application running
    pass
finally:
    metrics.stop_collection()
```

#### `get_dashboard_data()`

```python
def get_dashboard_data(self) -> Dict[str, Any]:
    """Get metrics formatted for dashboard display."""
```

**Returns:**

- `Dict[str, Any]` - Dashboard data with structure:

  ```python
  {
      "timestamp": "2025-10-27T10:30:00Z",
      "system": {
          "cpu_percent": 45.2,
          "memory_percent": 68.5,
          "process_memory_mb": 512.3
      },
      "application": {
          "agent_executions": MetricSummary(...),
          "tool_executions": MetricSummary(...),
          "avg_execution_time_ms": MetricSummary(...),
          "cache_hit_rate": 0.85
      },
      "alerts": [
          {
              "level": "warning",
              "message": "High CPU usage: 85.2%",
              "timestamp": "2025-10-27T10:30:00Z"
          }
      ]
  }
  ```

**Behaviour:**

- Triggers immediate system metrics collection
- Calculates summaries over 5-minute window
- Computes cache hit rate
- Checks alert conditions
- Returns UTC timestamps

**Example:**

```python
dashboard_data = metrics.get_dashboard_data()

print(f"CPU: {dashboard_data['system']['cpu_percent']:.1f}%")
print(f"Memory: {dashboard_data['system']['memory_percent']:.1f}%")

if dashboard_data['alerts']:
    for alert in dashboard_data['alerts']:
        print(f"[{alert['level']}] {alert['message']}")
```

**Use Cases:**

- Display real-time metrics in admin dashboard
- Health check endpoints
- Monitoring system integration
- Alert notification systems

#### `export()`

```python
def export(
    self,
    export_format: str = "json",
) -> Any:
    """Export metrics in specified format."""
```

**Parameters:**

- `export_format` (str) - Format: "json", "prometheus", or "statsd" (default: "json")

**Returns:**

- `str` - For JSON and Prometheus formats
- `List[str]` - For StatsD format (list of commands)

**Example:**

```python
# Export as JSON
json_metrics = metrics.export("json")
print(json_metrics)

# Export for Prometheus
prom_metrics = metrics.export("prometheus")
# Serve via /metrics endpoint

# Export as StatsD commands
statsd_commands = metrics.export("statsd")
for cmd in statsd_commands:
    send_to_statsd(cmd)
```

**Use Cases:**

- Expose /metrics endpoint for Prometheus scraping
- Send metrics to StatsD server
- Log metrics to JSON files
- Custom monitoring integrations

### `MetricCollector`

Thread-safe collector that stores and aggregates metric data points.

**Purpose:** Core storage and aggregation engine for all metrics.

**Responsibilities:**

- Store metric data points with bounded history
- Validate metric names, values, and labels
- Track metric types (counter, gauge, histogram, summary)
- Calculate summary statistics
- Provide thread-safe access to metrics

**Initialisation:**

```python
def __init__(
    self,
    max_history: int = DEFAULT_MAX_HISTORY,
) -> None:
    """
    Args:
        max_history: Maximum number of data points to keep per metric (default: 10000)
    """
```

**Class Attributes:**

- `metrics: Dict[str, deque]` - Metric name to data point deque mapping
- `metric_types: Dict[str, MetricType]` - Metric name to type mapping
- `lock: threading.Lock` - Thread safety lock
- `max_history: int` - Maximum points per metric

**Key Methods:**

#### `record()`

```python
def record(
    self,
    name: str,
    value: float,
    metric_type: MetricType = MetricType.GAUGE,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Record a metric value."""
```

**Parameters:**

- `name` (str) - Metric name (must match pattern `^[a-zA-Z][a-zA-Z0-9_.]*$`)
- `value` (float) - Metric value (must be finite number)
- `metric_type` (MetricType) - Type of metric (default: GAUGE)
- `labels` (Optional[Dict[str, str]]) - Optional dimension labels

**Raises:**

- `InvalidMetricError` - If name, value, or labels are invalid

**Behaviour:**

- Validates all inputs before recording
- Stores metric with current timestamp
- Maintains bounded deque (oldest dropped when full)
- Thread-safe via locking

**Example:**

```python
from backend.services.metrics import MetricCollector, MetricType

collector = MetricCollector(max_history=1000)

# Record gauge metric
collector.record("temperature.celsius", 22.5, MetricType.GAUGE)

# Record with labels
collector.record(
    "http.request.duration",
    150.0,
    MetricType.HISTOGRAM,
    labels={"method": "GET", "endpoint": "/api/users"}
)

# Counter metric
collector.record("page.views", 1, MetricType.COUNTER)
```

**Use Cases:**

- Recording custom application metrics
- Tracking business metrics
- Monitoring API performance
- Measuring resource utilization

#### `increment()`

```python
def increment(
    self,
    name: str,
    value: float = 1.0,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Increment a counter metric."""
```

**Parameters:**

- `name` (str) - Counter name
- `value` (float) - Increment amount (default: 1.0)
- `labels` (Optional[Dict[str, str]]) - Optional labels

**Example:**

```python
# Increment by 1
collector.increment("requests.total")

# Increment by custom amount
collector.increment("bytes.sent", value=1024.0)

# Increment with labels
collector.increment(
    "errors.total",
    labels={"error_type": "validation", "service": "api"}
)
```

**Use Cases:**

- Count events (requests, errors, completions)
- Track cumulative metrics
- Measure throughput

#### `gauge()`

```python
def gauge(
    self,
    name: str,
    value: float,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Set a gauge metric."""
```

**Parameters:**

- `name` (str) - Gauge name
- `value` (float) - Current value
- `labels` (Optional[Dict[str, str]]) - Optional labels

**Example:**

```python
# System metrics
collector.gauge("cpu.percent", 45.2)
collector.gauge("memory.used.gb", 8.5)

# Application metrics
collector.gauge("queue.size", 42)
collector.gauge("connection.pool.active", 15)
```

**Use Cases:**

- Track current values (not rates or counts)
- System resource levels
- Queue sizes
- Connection counts

#### `histogram()`

```python
def histogram(
    self,
    name: str,
    value: float,
    labels: Optional[Dict[str, str]] = None,
) -> None:
    """Record a histogram value."""
```

**Parameters:**

- `name` (str) - Histogram name
- `value` (float) - Observed value
- `labels` (Optional[Dict[str, str]]) - Optional labels

**Example:**

```python
# Response times
collector.histogram("request.duration.ms", 125.5)

# Request sizes
collector.histogram("request.size.bytes", 2048)

# Query durations
collector.histogram(
    "database.query.duration.ms",
    45.2,
    labels={"query_type": "select", "table": "users"}
)
```

**Use Cases:**

- Measure distributions (latencies, sizes)
- Calculate percentiles
- Identify outliers
- Performance profiling

#### `get_summary()`

```python
def get_summary(
    self,
    name: str,
    window_seconds: Optional[int] = None,
) -> Optional[MetricSummary]:
    """Get summary statistics for a metric."""
```

**Parameters:**

- `name` (str) - Metric name
- `window_seconds` (Optional[int]) - Time window in seconds (None = all data)

**Returns:**

- `Optional[MetricSummary]` - Summary statistics or None if metric not found

**Example:**

```python
# Get all-time summary
summary = collector.get_summary("request.duration.ms")
if summary:
    print(f"Count: {summary.count}")
    print(f"Average: {summary.avg:.2f}ms")
    print(f"P95: {summary.p95:.2f}ms")
    print(f"P99: {summary.p99:.2f}ms")

# Get 5-minute summary
recent = collector.get_summary("request.duration.ms", window_seconds=300)
if recent:
    print(f"Recent requests: {recent.count}")
    print(f"Recent average: {recent.avg:.2f}ms")
```

**Use Cases:**

- Performance analysis
- SLA monitoring (P95, P99 latencies)
- Capacity planning
- Alerting based on statistics

#### `get_all_metrics()`

```python
def get_all_metrics(self) -> Dict[str, dict]:
    """Get all metrics and their current values."""
```

**Returns:**

- `Dict[str, dict]` - Dictionary mapping metric names to latest data:

  ```python
  {
      "cpu.percent": {
          "value": 45.2,
          "timestamp": 1698412800.0,
          "type": "gauge",
          "labels": {}
      },
      "request.duration.ms": {
          "value": 125.5,
          "timestamp": 1698412800.0,
          "type": "histogram",
          "labels": {"method": "GET", "endpoint": "/api/users"}
      }
  }
  ```

**Example:**

```python
all_metrics = collector.get_all_metrics()

for name, data in all_metrics.items():
    print(f"{name}: {data['value']} ({data['type']})")
```

**Use Cases:**

- Export all metrics
- Dashboard display
- Debugging
- Monitoring system integration

#### `clear()`

```python
def clear(self) -> None:
    """Clear all metrics (primarily for testing)."""
```

**Behaviour:**

- Removes all stored metrics
- Clears metric type mappings
- Thread-safe operation

**Example:**

```python
# In test teardown
def teardown():
    collector.clear()
```

### `SystemMetricsCollector`

Collects system-level resource metrics.

**Purpose:** Gather CPU, memory, disk, and network I/O metrics.

**Responsibilities:**

- Collect system-wide resource metrics
- Collect process-specific metrics
- Handle collection errors gracefully
- Use psutil for cross-platform compatibility

**Initialisation:**

```python
def __init__(self, collector: MetricCollector) -> None:
    """
    Args:
        collector: Core MetricCollector instance for recording metrics
    """
```

**Key Methods:**

#### `collect()`

```python
def collect(self) -> None:
    """Collect current system metrics."""
```

**Metrics Collected:**

- `system.cpu.percent` - Overall CPU usage percentage
- `process.cpu.percent` - Process CPU usage percentage
- `system.memory.percent` - System memory usage percentage
- `system.memory.used_gb` - Used memory in gigabytes
- `system.memory.available_gb` - Available memory in gigabytes
- `process.memory.rss_mb` - Process resident set size in megabytes
- `process.memory.vms_mb` - Process virtual memory size in megabytes
- `system.disk.read_mb` - Cumulative disk reads in megabytes
- `system.disk.write_mb` - Cumulative disk writes in megabytes
- `system.network.sent_mb` - Cumulative network sent in megabytes
- `system.network.recv_mb` - Cumulative network received in megabytes

**Behaviour:**

- Captures snapshot of current system state
- Logs errors but doesn't raise exceptions
- Safe to call repeatedly

**Example:**

```python
from backend.services.metrics import MetricCollector, SystemMetricsCollector

collector = MetricCollector()
system_collector = SystemMetricsCollector(collector)

# Collect metrics
system_collector.collect()

# View results
cpu = collector.get_all_metrics().get("system.cpu.percent", {}).get("value", 0)
memory = collector.get_all_metrics().get("system.memory.percent", {}).get("value", 0)

print(f"CPU: {cpu:.1f}%")
print(f"Memory: {memory:.1f}%")
```

**Use Cases:**

- Background system monitoring
- Resource usage tracking
- Capacity planning
- Performance bottleneck identification

### `ApplicationMetricsCollector`

Collects application-specific event metrics.

**Purpose:** Track agent executions, tool usage, graph compilation, and cache performance.

**Responsibilities:**

- Record agent execution metrics
- Track tool execution and caching
- Monitor graph compilation performance
- Calculate cache hit rates

**Initialisation:**

```python
def __init__(self, collector: MetricCollector) -> None:
    """
    Args:
        collector: Core MetricCollector instance
    """
```

**Key Methods:**

#### `record_execution()`

```python
def record_execution(
    self,
    graph_name: str,
    agent_name: str,
    duration_ms: float,
    success: bool,
    token_count: Optional[int] = None,
) -> None:
    """Record agent execution metrics."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph
- `agent_name` (str) - Name of the agent
- `duration_ms` (float) - Execution duration in milliseconds
- `success` (bool) - Whether execution succeeded
- `token_count` (Optional[int]) - Optional LLM token usage

**Metrics Recorded:**

- `agent.execution.duration_ms` - Histogram of execution times
- `agent.execution.count` - Counter of total executions
- `agent.execution.errors` - Counter of failed executions
- `agent.tokens.used` - Histogram of token usage (if provided)

**Example:**

```python
from backend.services.metrics import get_metrics_manager

metrics = get_metrics_manager()

# Record successful execution
metrics.app_metrics.record_execution(
    graph_name="customer_support",
    agent_name="query_classifier",
    duration_ms=125.5,
    success=True,
    token_count=450
)

# Record failed execution
metrics.app_metrics.record_execution(
    graph_name="customer_support",
    agent_name="response_generator",
    duration_ms=89.2,
    success=False
)
```

**Use Cases:**

- Track agent performance
- Monitor execution success rates
- Measure token usage costs
- Identify slow agents

#### `record_tool_execution()`

```python
def record_tool_execution(
    self,
    tool_name: str,
    duration_ms: float,
    success: bool,
    cached: bool = False,
) -> None:
    """Record tool execution metrics."""
```

**Parameters:**

- `tool_name` (str) - Name of the tool
- `duration_ms` (float) - Execution duration in milliseconds
- `success` (bool) - Whether execution succeeded
- `cached` (bool) - Whether result was from cache (default: False)

**Metrics Recorded:**

- `tool.execution.duration_ms` - Histogram of execution times
- `tool.execution.count` - Counter of executions
- `tool.cache.hits` - Counter of cache hits
- `tool.cache.misses` - Counter of cache misses

**Example:**

```python
# Record cached tool execution
metrics.app_metrics.record_tool_execution(
    tool_name="database_query",
    duration_ms=5.2,
    success=True,
    cached=True
)

# Record uncached execution
metrics.app_metrics.record_tool_execution(
    tool_name="api_call",
    duration_ms=250.8,
    success=True,
    cached=False
)
```

**Use Cases:**

- Monitor tool performance
- Track cache effectiveness
- Identify slow tools
- Optimize caching strategies

#### `record_compilation()`

```python
def record_compilation(
    self,
    graph_name: str,
    agent_count: int,
    duration_ms: float,
    success: bool,
) -> None:
    """Record graph compilation metrics."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph
- `agent_count` (int) - Number of agents in graph
- `duration_ms` (float) - Compilation duration in milliseconds
- `success` (bool) - Whether compilation succeeded

**Metrics Recorded:**

- `graph.compilation.duration_ms` - Histogram of compilation times
- `graph.compilation.agent_count` - Gauge of agents in graph
- `graph.compilation.count` - Counter of compilations

**Example:**

```python
metrics.app_metrics.record_compilation(
    graph_name="customer_support",
    agent_count=5,
    duration_ms=450.3,
    success=True
)
```

**Use Cases:**

- Track compilation performance
- Monitor graph complexity
- Identify compilation bottlenecks

#### `record_cache_stats()`

```python
def record_cache_stats(
    self,
    cache_name: str,
    hits: int,
    misses: int,
    size: int,
    evictions: int,
) -> None:
    """Record cache statistics."""
```

**Parameters:**

- `cache_name` (str) - Name of the cache
- `hits` (int) - Number of cache hits
- `misses` (int) - Number of cache misses
- `size` (int) - Current cache size
- `evictions` (int) - Number of evictions

**Metrics Recorded:**

- `cache.hits` - Gauge of total hits
- `cache.misses` - Gauge of total misses
- `cache.size` - Gauge of current size
- `cache.evictions` - Gauge of evictions
- `cache.hit_rate` - Calculated hit rate (hits / total)

**Example:**

```python
metrics.app_metrics.record_cache_stats(
    cache_name="llm_responses",
    hits=850,
    misses=150,
    size=500,
    evictions=20
)
```

**Use Cases:**

- Monitor cache performance
- Optimize cache sizes
- Tune eviction policies

### Exporters

#### `JSONExporter`

Export metrics in JSON format.

**Signature:**

```python
def export(self) -> str:
    """Export metrics as JSON string."""
```

**Returns:**

- `str` - JSON-formatted metrics with indentation

**Raises:**

- `ExportError` - If export fails

**Example:**

```python
from backend.services.metrics import get_metrics_manager

metrics = get_metrics_manager()
json_output = metrics.export("json")

# Parse JSON
import json
data = json.loads(json_output)

for metric_name, metric_data in data.items():
    print(f"{metric_name}: {metric_data['value']}")
```

#### `PrometheusExporter`

Export metrics in Prometheus text exposition format.

**Signature:**

```python
def export(self) -> str:
    """Export metrics in Prometheus text format."""
```

**Returns:**

- `str` - Prometheus-formatted metrics

**Raises:**

- `ExportError` - If export fails

**Behaviour:**

- Converts dots to underscores in metric names
- Adds TYPE annotations
- Includes labels in Prometheus syntax
- Adds millisecond timestamps

**Example:**

```python
prom_output = metrics.export("prometheus")

# Output format:
# # TYPE system_cpu_percent gauge
# system_cpu_percent 45.2 1698412800000
# # TYPE agent_execution_duration_ms histogram
# agent_execution_duration_ms{graph="support",agent="classifier"} 125.5 1698412800000
```

**Use Cases:**

- Prometheus scraping endpoint
- Integration with Grafana
- Standard monitoring infrastructure

#### `StatsDExporter`

Export metrics in StatsD wire protocol format.

**Signature:**

```python
def export(self) -> List[str]:
    """Export metrics as StatsD commands."""
```

**Returns:**

- `List[str]` - List of StatsD command strings

**Raises:**

- `ExportError` - If export fails

**Behaviour:**

- Maps COUNTER to `|c`
- Maps GAUGE to `|g`
- Maps HISTOGRAM/SUMMARY to `|ms`

**Example:**

```python
statsd_commands = metrics.export("statsd")

# Output format:
# ["system.cpu.percent:45.2|g", "agent.execution.count:1|c", ...]

# Send to StatsD server
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for cmd in statsd_commands:
    sock.sendto(cmd.encode(), ("localhost", 8125))
```

**Use Cases:**

- StatsD integration
- DataDog metrics
- Telegraf collection

## Models

### `MetricType`

Enumeration of supported metric types.

**Values:**

- `MetricType.COUNTER` - Monotonically increasing counter
- `MetricType.GAUGE` - Point-in-time value that can go up or down
- `MetricType.HISTOGRAM` - Distribution of values (for percentiles)
- `MetricType.SUMMARY` - Pre-aggregated statistics

**Example:**

```python
from backend.services.metrics import MetricType, MetricCollector

collector = MetricCollector()

# Counter for events
collector.record("requests.total", 1, MetricType.COUNTER)

# Gauge for current value
collector.record("queue.size", 42, MetricType.GAUGE)

# Histogram for distribution
collector.record("response.time.ms", 125.5, MetricType.HISTOGRAM)
```

### `MetricPoint`

Single metric data point.

**Attributes:**

- `timestamp: float` - Unix timestamp when metric was recorded
- `value: float` - Numeric value of the metric
- `labels: Dict[str, str]` - Optional key-value labels for dimensions

**Example:**

```python
from backend.services.metrics import MetricPoint

point = MetricPoint(
    timestamp=1698412800.0,
    value=125.5,
    labels={"method": "GET", "status": "200"}
)
```

### `MetricSummary`

Summary statistics for a metric.

**Attributes:**

- `count: int` - Number of data points
- `sum: float` - Sum of all values
- `min: float` - Minimum value
- `max: float` - Maximum value
- `avg: float` - Average value
- `p50: float` - 50th percentile (median)
- `p95: float` - 95th percentile
- `p99: float` - 99th percentile

**Example:**

```python
summary = collector.get_summary("response.time.ms", window_seconds=300)

print(f"Last 5 minutes:")
print(f"  Count: {summary.count}")
print(f"  Average: {summary.avg:.2f}ms")
print(f"  Median (P50): {summary.p50:.2f}ms")
print(f"  P95: {summary.p95:.2f}ms")
print(f"  P99: {summary.p99:.2f}ms")
print(f"  Max: {summary.max:.2f}ms")
```

## Configuration

### Environment Variables

| Variable                      | Description                    | Default | Required |
|-------------------------------|--------------------------------|---------|----------|
| `METRICS_MAX_HISTORY`         | Maximum data points per metric | 10000   | No       |
| `METRICS_COLLECTION_INTERVAL` | Collection interval (seconds)  | 30      | No       |
| `METRICS_CPU_WARNING`         | CPU warning threshold (%)      | 80.0    | No       |
| `METRICS_MEMORY_CRITICAL`     | Memory critical threshold (%)  | 90.0    | No       |
| `METRICS_ERROR_WARNING_COUNT` | Error count for warnings       | 10      | No       |

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.metrics import get_metrics_manager

# Get singleton instance (auto-starts collection)
metrics = get_metrics_manager()

# Use via specialized collectors
metrics.app_metrics.record_execution(
    graph_name="my_graph",
    agent_name="my_agent",
    duration_ms=150.0,
    success=True
)
```

**Advanced Initialisation:**

```python
from backend.services.metrics import MetricCollector, SystemMetricsCollector

# Custom collector with limited history
collector = MetricCollector(max_history=1000)

# Manual system metrics collection
system_collector = SystemMetricsCollector(collector)
system_collector.collect()

# Custom collection interval
metrics = get_metrics_manager()
metrics.stop_collection()
metrics.start_collection(interval=60)  # Collect every 60 seconds
```

**Testing Initialisation:**

```python
from backend.services.metrics import reset_metrics, get_metrics_manager

# In test setup
def setup():
    reset_metrics()  # Clear previous test state
    metrics = get_metrics_manager()
    return metrics

# In test teardown
def teardown():
    reset_metrics()
```

## Error Handling

### Exception Hierarchy

```
Exception
└── MetricsError
    ├── InvalidMetricError
    └── ExportError
```

### Exception Details

#### `MetricsError`

Base exception for all metrics-related errors.

**Inherits from:** `Exception`

**When raised:**

- Base class for specific metric errors
- Generally not raised directly

#### `InvalidMetricError`

Raised when metric name, value, or labels are invalid.

**Inherits from:** `MetricsError`

**When raised:**

- Empty metric name
- Metric name too long (>200 chars)
- Invalid metric name pattern (must start with letter, contain only alphanumerics, dots, underscores)
- Non-numeric metric value
- NaN or infinite metric value
- Invalid labels (non-dict, too many, keys/values too long)

**Example:**

```python
from backend.services.metrics import MetricCollector, InvalidMetricError

collector = MetricCollector()

try:
    # Invalid name (starts with number)
    collector.record("123invalid", 10.0)
except InvalidMetricError as e:
    print(f"Invalid metric: {e}")

try:
    # Invalid value (NaN)
    import math
    collector.record("my.metric", math.nan)
except InvalidMetricError as e:
    print(f"Invalid value: {e}")
```

#### `ExportError`

Raised when metric export fails.

**Inherits from:** `MetricsError`

**When raised:**

- JSON serialization failure
- Prometheus formatting error
- StatsD export error

**Example:**

```python
from backend.services.metrics import get_metrics_manager, ExportError

metrics = get_metrics_manager()

try:
    output = metrics.export("prometheus")
except ExportError as e:
    logger.error(f"Failed to export metrics: {e}")
    # Fallback to JSON
    output = metrics.export("json")
```

### Error Handling Patterns

```python
from backend.services.metrics import (
    get_metrics_manager,
    InvalidMetricError,
    ExportError,
    MetricsError
)

def record_with_validation(name: str, value: float) -> bool:
    """Safely record a metric with error handling."""
    try:
        metrics = get_metrics_manager()
        metrics.collector.record(name, value)
        return True
    except InvalidMetricError as e:
        logger.warning(f"Invalid metric {name}={value}: {e}")
        return False
    except MetricsError as e:
        logger.error(f"Metrics error: {e}")
        return False

def export_with_fallback(preferred_format: str = "prometheus") -> str:
    """Export metrics with fallback to JSON."""
    metrics = get_metrics_manager()

    try:
        return metrics.export(preferred_format)
    except ExportError as e:
        logger.warning(f"Export failed for {preferred_format}: {e}, falling back to JSON")
        return metrics.export("json")
```

## Integration Patterns

### Integration with API Layer

The metrics service integrates with the monitoring API to expose metrics via HTTP endpoints.

```python
# From backend/api/monitoring/routes.py
from fastapi import APIRouter
from backend.services.metrics import get_metrics_manager

router = APIRouter(prefix="/api/monitoring")

@router.get("/metrics/dashboard")
async def metrics_dashboard():
    """Get dashboard metrics."""
    metrics = get_metrics_manager()
    return metrics.get_dashboard_data()

@router.get("/metrics")
async def get_metrics(export_format: str = "json"):
    """Export metrics in specified format."""
    metrics = get_metrics_manager()
    return metrics.export(export_format)
```

### Integration with Execution Service

The execution service uses metrics to track agent performance.

```python
from backend.services.metrics import get_metrics_manager
import time

async def execute_agent(graph_name: str, agent_name: str, input_data: dict):
    """Execute agent with metrics tracking."""
    metrics = get_metrics_manager()

    start_time = time.time()
    success = False
    token_count = None

    try:
        # Execute agent
        result = await agent.execute(input_data)
        success = True
        token_count = result.get("token_usage")
        return result

    finally:
        # Always record metrics
        duration_ms = (time.time() - start_time) * 1000
        metrics.app_metrics.record_execution(
            graph_name=graph_name,
            agent_name=agent_name,
            duration_ms=duration_ms,
            success=success,
            token_count=token_count
        )
```

### Integration with Tool Execution

Tools track execution time and caching.

```python
from backend.services.metrics import get_metrics_manager
from functools import wraps
import time

def track_tool_execution(tool_name: str):
    """Decorator to track tool execution metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            metrics = get_metrics_manager()
            start_time = time.time()
            success = False
            cached = False

            try:
                result = await func(*args, **kwargs)
                success = True
                cached = getattr(result, "from_cache", False)
                return result

            finally:
                duration_ms = (time.time() - start_time) * 1000
                metrics.app_metrics.record_tool_execution(
                    tool_name=tool_name,
                    duration_ms=duration_ms,
                    success=success,
                    cached=cached
                )

        return wrapper
    return decorator

# Usage
@track_tool_execution("database_query")
async def query_database(query: str):
    return await db.execute(query)
```

### Dependency Flow

**Metrics Service Dependencies:**

```
metrics (no internal dependencies)
  ↓ uses
config (for logging only)
```

**Services Using Metrics:**

```
monitoring API → metrics
execution → metrics
tools → metrics
graph compilation → metrics
```

### Common Integration Patterns

#### Pattern 1: Execution Tracking

```python
from backend.services.metrics import get_metrics_manager
import time

class ExecutionTracker:
    """Context manager for tracking execution metrics."""

    def __init__(self, graph_name: str, agent_name: str):
        self.graph_name = graph_name
        self.agent_name = agent_name
        self.metrics = get_metrics_manager()
        self.start_time = None
        self.success = False
        self.token_count = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.success = exc_type is None

        self.metrics.app_metrics.record_execution(
            graph_name=self.graph_name,
            agent_name=self.agent_name,
            duration_ms=duration_ms,
            success=self.success,
            token_count=self.token_count
        )

# Usage
with ExecutionTracker("support_graph", "classifier") as tracker:
    result = agent.execute(input_data)
    tracker.token_count = result.token_usage
```

#### Pattern 2: Periodic System Monitoring

```python
from backend.services.metrics import get_metrics_manager

# Application startup
def on_startup():
    metrics = get_metrics_manager()
    metrics.start_collection(interval=30)

# Application shutdown
def on_shutdown():
    metrics = get_metrics_manager()
    metrics.stop_collection()
```

## Usage Examples

### Example 1: Basic Usage

```python
from backend.services.metrics import get_metrics_manager

# Step 1: Get metrics manager
metrics = get_metrics_manager()

# Step 2: Record application metrics
metrics.app_metrics.record_execution(
    graph_name="customer_support",
    agent_name="query_classifier",
    duration_ms=125.5,
    success=True,
    token_count=450
)

# Step 3: View dashboard data
dashboard = metrics.get_dashboard_data()
print(f"CPU: {dashboard['system']['cpu_percent']:.1f}%")
print(f"Memory: {dashboard['system']['memory_percent']:.1f}%")
```

### Example 2: Advanced Usage with Custom Metrics

```python
from backend.services.metrics import (
    get_metrics_manager,
    MetricCollector,
    MetricType
)

# Get metrics manager
metrics = get_metrics_manager()

# Record custom business metrics
metrics.collector.record(
    "orders.completed",
    value=1,
    metric_type=MetricType.COUNTER,
    labels={"region": "us-east", "product": "premium"}
)

metrics.collector.histogram(
    "order.value.usd",
    value=299.99,
    labels={"region": "us-east"}
)

# Get summary statistics
summary = metrics.collector.get_summary(
    "order.value.usd",
    window_seconds=3600  # Last hour
)

if summary:
    print(f"Orders (last hour): {summary.count}")
    print(f"Average order value: ${summary.avg:.2f}")
    print(f"P95 order value: ${summary.p95:.2f}")

# Export for monitoring
prometheus_metrics = metrics.export("prometheus")
```

### Example 3: Complete Workflow with Error Handling

```python
from backend.services.metrics import (
    get_metrics_manager,
    InvalidMetricError,
    ExportError,
)
import time
import logging

logger = logging.getLogger(__name__)

async def process_workflow_with_metrics(
    graph_name: str,
    agent_name: str,
    input_data: dict
):
    """Complete workflow example with metrics tracking."""

    metrics = get_metrics_manager()
    start_time = time.time()
    success = False
    token_count = None

    try:
        # Step 1: Execute agent
        result = await execute_agent(graph_name, agent_name, input_data)
        success = True
        token_count = result.get("token_usage")

        # Step 2: Record custom metrics
        try:
            metrics.collector.increment(
                "workflow.completed",
                labels={"graph": graph_name, "agent": agent_name}
            )
        except InvalidMetricError as e:
            logger.warning(f"Failed to record custom metric: {e}")

        # Step 3: Check performance alerts
        dashboard = metrics.get_dashboard_data()
        if dashboard["alerts"]:
            for alert in dashboard["alerts"]:
                logger.warning(f"[{alert['level']}] {alert['message']}")

        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        return {"success": False, "error": str(e)}

    finally:
        # Always record execution metrics
        duration_ms = (time.time() - start_time) * 1000
        try:
            metrics.app_metrics.record_execution(
                graph_name=graph_name,
                agent_name=agent_name,
                duration_ms=duration_ms,
                success=success,
                token_count=token_count
            )
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
```

### Example 4: Testing Usage

```python
import pytest
from backend.services.metrics import (
    get_metrics_manager,
    reset_metrics,
    MetricCollector,
)

@pytest.fixture
def metrics():
    """Metrics fixture with cleanup."""
    reset_metrics()
    manager = get_metrics_manager()
    yield manager
    reset_metrics()

def test_execution_metrics(metrics):
    """Test recording execution metrics."""
    # Record execution
    metrics.app_metrics.record_execution(
        graph_name="test_graph",
        agent_name="test_agent",
        duration_ms=100.0,
        success=True,
        token_count=500
    )

    # Verify metrics
    all_metrics = metrics.collector.get_all_metrics()
    assert "agent.execution.duration_ms" in all_metrics
    assert "agent.execution.count" in all_metrics

    # Check summary
    summary = metrics.collector.get_summary("agent.execution.duration_ms")
    assert summary is not None
    assert summary.count == 1
    assert summary.avg == 100.0

def test_export_formats(metrics):
    """Test metric export formats."""
    # Record some metrics
    metrics.collector.gauge("test.metric", 42.0)

    # Test JSON export
    json_output = metrics.export("json")
    assert isinstance(json_output, str)
    assert "test.metric" in json_output

    # Test Prometheus export
    prom_output = metrics.export("prometheus")
    assert isinstance(prom_output, str)
    assert "test_metric" in prom_output  # Dots converted to underscores

    # Test StatsD export
    statsd_output = metrics.export("statsd")
    assert isinstance(statsd_output, list)
    assert any("test.metric" in cmd for cmd in statsd_output)

def test_system_metrics_collection(metrics):
    """Test system metrics collection."""
    # Collect system metrics
    metrics.system_metrics.collect()

    # Verify metrics exist
    all_metrics = metrics.collector.get_all_metrics()
    assert "system.cpu.percent" in all_metrics
    assert "system.memory.percent" in all_metrics
    assert "process.memory.rss_mb" in all_metrics

def test_dashboard_data(metrics):
    """Test dashboard data generation."""
    # Record some metrics
    metrics.app_metrics.record_execution(
        graph_name="test",
        agent_name="test",
        duration_ms=150.0,
        success=True
    )

    # Get dashboard data
    dashboard = metrics.get_dashboard_data()

    assert "timestamp" in dashboard
    assert "system" in dashboard
    assert "application" in dashboard
    assert "alerts" in dashboard

    # Check structure
    assert "cpu_percent" in dashboard["system"]
    assert "memory_percent" in dashboard["system"]
```

## Performance Considerations

### Performance Characteristics

**Time Complexity:**

- `record()`: O(1) - Append to deque with automatic eviction
- `get_summary()`: O(n log n) - Sorts values for percentile calculation where n ≤ max_history
- `get_all_metrics()`: O(m) - Iterates over m metrics to get latest values
- `increment()/gauge()/histogram()`: O(1) - Delegate to record()

**Space Complexity:**

- Memory per metric: O(max_history) - Bounded deque
- Total memory: O(m × max_history) where m = number of unique metrics
- Default: 10,000 points × 8 bytes × m metrics

**I/O Characteristics:**

- CPU-bound: Percentile calculations, sorting
- I/O-bound: System metrics collection (psutil system calls)
- Network-bound: Export to remote systems (StatsD)

**Concurrency:**

- Thread-safe using locks
- Background collection in daemon thread
- Lock contention minimal due to fast operations

### Optimisation Tips

#### Tip 1: Reduce History for High-Frequency Metrics

**Problem:**

```python
# High memory usage with default history
collector = MetricCollector()  # 10,000 points per metric

for i in range(1000000):
    collector.record("high.frequency", i)  # Stores 10,000 recent
```

**Solution:**

```python
# Limit history for high-frequency metrics
collector = MetricCollector(max_history=1000)  # Only 1,000 points

# Or use time-windowed summaries instead of full history
summary = collector.get_summary("high.frequency", window_seconds=300)
```

#### Tip 2: Use Labels Wisely

**Problem:**

```python
# Creates separate metric for each user ID
for user_id in range(10000):
    collector.record(f"user.{user_id}.requests", 1)  # 10,000 metrics!
```

**Solution:**

```python
# Use labels for dimensions
collector.increment(
    "user.requests",
    labels={"user_id": str(user_id)}  # Single metric with labels
)
```

#### Tip 3: Batch Exports

**Problem:**

```python
# Export on every request
@router.get("/metrics")
def metrics_endpoint():
    return get_metrics_manager().export("prometheus")  # Expensive
```

**Solution:**

```python
# Cache exports with TTL
from functools import lru_cache
import time

@lru_cache(maxsize=1)
def get_cached_export(timestamp: int):
    return get_metrics_manager().export("prometheus")

@router.get("/metrics")
def metrics_endpoint():
    # Cache for 30 seconds
    cache_key = int(time.time() / 30)
    return get_cached_export(cache_key)
```

#### Tip 4: Adjust Collection Interval

**Problem:**

```python
# Default 30s collection may be too frequent
metrics = get_metrics_manager()
# Collecting system metrics every 30s
```

**Solution:**

```python
# Adjust based on needs
metrics.stop_collection()

# Production: less frequent to reduce overhead
metrics.start_collection(interval=60)

# Development: more frequent for testing
metrics.start_collection(interval=10)
```

### Async/Await Support

The metrics service does not natively support async/await. However, all operations are thread-safe and non-blocking for
typical usage.

```python
# Safe to use in async contexts
async def async_handler():
    metrics = get_metrics_manager()

    # Non-blocking - safe in async
    metrics.app_metrics.record_execution(
        graph_name="async_graph",
        agent_name="async_agent",
        duration_ms=100.0,
        success=True
    )

    # Get dashboard data - fast operation
    dashboard = metrics.get_dashboard_data()
    return dashboard
```

### Batch Operations

For recording multiple metrics, use individual calls (no batch API):

```python
# Record multiple metrics
metrics = get_metrics_manager()

# Each operation is O(1)
for i in range(100):
    metrics.collector.increment("events.processed")
    metrics.collector.histogram("processing.time.ms", i * 10)

# Efficiently use labels instead of separate metrics
for region in ["us-east", "us-west", "eu-central"]:
    metrics.collector.gauge(
        "active.connections",
        get_connections(region),
        labels={"region": region}
    )
```

## Testing Patterns

### Unit Testing

```python
import pytest
from backend.services.metrics import (
    MetricCollector,
    MetricType,
    InvalidMetricError,
)

@pytest.fixture
def collector():
    """Collector fixture."""
    return MetricCollector(max_history=100)

def test_record_metric(collector):
    """Test basic metric recording."""
    collector.record("test.metric", 42.0, MetricType.GAUGE)

    metrics = collector.get_all_metrics()
    assert "test.metric" in metrics
    assert metrics["test.metric"]["value"] == 42.0
    assert metrics["test.metric"]["type"] == "gauge"

def test_increment_counter(collector):
    """Test counter increment."""
    collector.increment("test.counter")
    collector.increment("test.counter", value=5)

    summary = collector.get_summary("test.counter")
    assert summary.count == 2
    assert summary.sum == 6.0

def test_invalid_metric_name(collector):
    """Test metric name validation."""
    with pytest.raises(InvalidMetricError):
        collector.record("123invalid", 10.0)

    with pytest.raises(InvalidMetricError):
        collector.record("", 10.0)

def test_percentile_calculation(collector):
    """Test percentile calculations."""
    # Record 100 values
    for i in range(100):
        collector.histogram("test.histogram", float(i))

    summary = collector.get_summary("test.histogram")
    assert summary.count == 100
    assert 48 <= summary.p50 <= 52  # Median around 50
    assert 93 <= summary.p95 <= 97  # P95 around 95
    assert 98 <= summary.p99 <= 100  # P99 around 99
```

### Mocking Dependencies

```python
from unittest.mock import Mock, patch
import pytest

@patch('backend.services.metrics.collectors.system.psutil')
def test_system_collector_with_mock(mock_psutil):
    """Test system metrics collection with mocked psutil."""
    # Mock psutil responses
    mock_psutil.cpu_percent.return_value = 45.0
    mock_psutil.virtual_memory.return_value = Mock(
        percent=60.0,
        used=8 * 1024**3,
        available=4 * 1024**3
    )

    from backend.services.metrics import MetricCollector, SystemMetricsCollector

    collector = MetricCollector()
    system_collector = SystemMetricsCollector(collector)

    # Collect metrics
    system_collector.collect()

    # Verify
    metrics = collector.get_all_metrics()
    assert metrics["system.cpu.percent"]["value"] == 45.0
    assert metrics["system.memory.percent"]["value"] == 60.0
```

### Integration Testing

```python
@pytest.mark.integration
async def test_metrics_integration():
    """Integration test with real metrics collection."""
    from backend.services.metrics import get_metrics_manager, reset_metrics

    # Reset state
    reset_metrics()

    # Get fresh manager
    metrics = get_metrics_manager()

    # Record real metrics
    metrics.app_metrics.record_execution(
        graph_name="integration_test",
        agent_name="test_agent",
        duration_ms=150.0,
        success=True,
        token_count=500
    )

    # Collect system metrics
    metrics.system_metrics.collect()

    # Get dashboard data
    dashboard = metrics.get_dashboard_data()

    # Verify structure
    assert dashboard["timestamp"]
    assert dashboard["system"]["cpu_percent"] >= 0
    assert dashboard["application"]["agent_executions"] is not None

    # Test export
    json_output = metrics.export("json")
    assert "agent.execution.duration_ms" in json_output

    # Cleanup
    reset_metrics()
```

## Best Practices

### Do's

✅ **Use the singleton pattern via `get_metrics_manager()`**

```python
# Good: Use singleton
from backend.services.metrics import get_metrics_manager

metrics = get_metrics_manager()
metrics.app_metrics.record_execution(...)
```

✅ **Use labels for dimensions instead of metric names**

```python
# Good: Single metric with labels
metrics.collector.increment(
    "http.requests",
    labels={"method": "GET", "status": "200", "endpoint": "/api/users"}
)

# Bad: Separate metric for each combination
metrics.collector.increment("http.requests.GET.200.api_users")
```

✅ **Handle metric errors gracefully**

```python
# Good: Metrics should never break application
try:
    metrics.app_metrics.record_execution(...)
except Exception as e:
    logger.warning(f"Failed to record metrics: {e}")
    # Continue execution
```

✅ **Use appropriate metric types**

```python
# Good: Choose correct type
metrics.collector.increment("requests.count")  # Counter for events
metrics.collector.gauge("queue.size", 42)  # Gauge for current value
metrics.collector.histogram("response.time", 125.5)  # Histogram for distribution
```

✅ **Use time windows for summaries**

```python
# Good: Window for recent data
recent = metrics.collector.get_summary("requests.duration", window_seconds=300)

# Okay: All-time summary
all_time = metrics.collector.get_summary("requests.duration")
```

### Don'ts

❌ **Don't create new MetricsManager instances**

```python
# Bad: Bypasses singleton
from backend.services.metrics import MetricsManager
metrics = MetricsManager()  # Creates separate instance

# Good: Use singleton
from backend.services.metrics import get_metrics_manager
metrics = get_metrics_manager()
```

❌ **Don't use unbounded labels**

```python
# Bad: Unlimited unique labels
for user_id in all_users:  # Could be millions
    metrics.collector.increment("logins", labels={"user_id": str(user_id)})

# Good: Use bounded labels
metrics.collector.increment("logins", labels={"region": "us-east"})
```

❌ **Don't record metrics in tight loops without consideration**

```python
# Bad: High-frequency recording may impact performance
for i in range(1000000):
    metrics.collector.record("tight.loop", i)

# Good: Sample or aggregate
if i % 1000 == 0:
    metrics.collector.record("tight.loop.sample", i)
```

❌ **Don't ignore metric validation errors in critical paths**

```python
# Bad: Silent failure
try:
    metrics.collector.record(invalid_name, value)
except InvalidMetricError:
    pass  # Silently ignore

# Good: Log validation errors
try:
    metrics.collector.record(name, value)
except InvalidMetricError as e:
    logger.error(f"Invalid metric {name}: {e}")
```

❌ **Don't call `reset_metrics()` in production**

```python
# Bad: Only for testing
reset_metrics()  # Loses all metrics!

# Good: Only in tests
@pytest.fixture
def metrics():
    reset_metrics()
    yield get_metrics_manager()
    reset_metrics()
```

## Related Documentation

### Related Services

- None (metrics service is self-contained)

### Related API Modules

- [Monitoring API](../agents-guide/api/monitoring.md) - HTTP endpoints for metrics and health checks

### Architecture Documentation

- Service architecture patterns
- Singleton pattern implementation
- Thread safety in services

### External Documentation

- [Prometheus Documentation](https://prometheus.io/docs/) - Prometheus metrics format
- [StatsD Protocol](https://github.com/statsd/statsd/blob/master/docs/metric_types.md) - StatsD wire protocol
- [psutil Documentation](https://psutil.readthedocs.io/) - System metrics collection

## Summary

The metrics service provides a comprehensive, thread-safe solution for collecting, aggregating, and exporting
application and system metrics in AgenticStudio. It implements a singleton pattern for global access, supports multiple
export formats (JSON, Prometheus, StatsD), and offers specialised collectors for system resources and application
events.

The service is designed for production use with configurable history limits, background collection, automatic alerting,
and graceful error handling. It integrates seamlessly with the monitoring API and can be easily incorporated into any
part of the application using the simple `get_metrics_manager()` interface.

**Key Features:**

- Thread-safe singleton metrics manager
- System metrics collection (CPU, memory, disk, network)
- Application metrics tracking (agents, tools, caching, compilation)
- Multiple export formats (JSON, Prometheus, StatsD)
- Summary statistics with percentiles (P50, P95, P99)
- Automatic alerting based on thresholds
- Bounded memory usage with configurable history
- Background collection with adjustable intervals

**Primary Use Cases:**

- Production monitoring and alerting
- Performance profiling and optimisation
- Resource usage tracking and capacity planning
- Integration with monitoring systems (Prometheus, Grafana, DataDog)
- Dashboard metrics display
- SLA monitoring (P95/P99 latencies)

**When to Use This Service:**

- Track agent and tool performance metrics
- Monitor system resource usage
- Export metrics to external monitoring systems
- Generate operational dashboards
- Set up alerts for system health issues
- Profile application performance
- Measure cache effectiveness
