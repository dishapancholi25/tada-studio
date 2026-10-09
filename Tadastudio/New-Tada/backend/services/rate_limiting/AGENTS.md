# Rate Limiting Service

## Overview

The rate limiting service provides comprehensive request throttling for published workflows in AgenticStudio. It implements
flexible rate limiting with support for multiple time windows (per-second, per-minute, per-hour, per-day), pluggable
storage backends, and various client identification strategies. The service uses a sliding window algorithm for accurate
rate limiting and provides standard HTTP headers for client feedback.

**Location:** `backend/services/rate_limiting/`

**Primary Responsibilities:**

- Enforce rate limits on HTTP-triggered workflow executions
- Track request counts using sliding window algorithm
- Generate client identifiers from IP addresses or authentication tokens
- Provide HTTP headers for rate limit status
- Support multiple rate limit configurations per workflow
- Clean up expired rate limit buckets to prevent memory leaks

**Key Use Cases:**

- Protecting published workflows from abuse or excessive usage
- Implementing different rate limits for authenticated vs unauthenticated users
- Providing API consumers with clear rate limit feedback via HTTP headers
- Supporting per-user and per-IP rate limiting strategies

## Architecture

### Module Structure

```
backend/services/rate_limiting/
├── __init__.py              # Public API exports and factory function
├── service.py               # Main RateLimitingService orchestrator
├── config.py                # Configuration classes and type definitions
├── exceptions.py            # Custom exception hierarchy
├── storage.py               # Storage backends (abstract + in-memory)
├── strategies.py            # Rate limiting strategies (sliding window)
├── client_identifier.py     # Client identification strategies
└── headers.py               # HTTP header generation
```

**File Descriptions:**

- **`__init__.py`**: Defines the public API with all exported classes, functions, and exceptions. Provides
  `create_rate_limiting_service()` factory function and `rate_limiting_service` singleton.

- **`service.py`**: Main orchestrator that coordinates storage, strategies, client identification, and header
  generation. Provides the primary API for rate limit checks.

- **`config.py`**: Configuration dataclasses, type definitions (RateLimitConfig, RateLimitSettings), and validation
  logic for rate limit configurations.

- **`exceptions.py`**: Custom exception hierarchy for rate limiting errors including RateLimitExceeded,
  InvalidRateLimitConfig, and RateLimitStorageError.

- **`storage.py`**: Abstract storage interface and concrete implementations. Currently provides in-memory storage with
  support for sliding window buckets.

- **`strategies.py`**: Rate limiting algorithms. Implements SlidingWindowStrategy for accurate time-based rate limiting.

- **`client_identifier.py`**: Strategies for generating unique client identifiers (IP-based, token-based, hybrid).

- **`headers.py`**: Utilities for generating standard rate limit HTTP headers (X-RateLimit-* headers).

### Design Patterns

**Strategy Pattern**: Used extensively for:

- Rate limiting algorithms (RateLimitStrategy → SlidingWindowStrategy)
- Client identification (ClientIdentifierStrategy → HybridIdentifierStrategy, TokenOnlyIdentifierStrategy,
  IPOnlyIdentifierStrategy)
- Storage backends (RateLimitStorage → InMemoryRateLimitStorage)

**Factory Pattern**: `create_rate_limiting_service()` function provides flexible service initialisation with optional
dependencies.

**Singleton Pattern**: Global `rate_limiting_service` instance for convenient access throughout the application.

**Dependency Injection**: Service accepts pluggable components (storage, strategy, client_identifier_strategy) for
extensibility and testing.

**Component Relationships:**

```
┌─────────────────────────────────────────┐
│      RateLimitingService                │
│      (Main Orchestrator)                │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┬──────────────┬─────────────────┐
       │                │              │                 │
       ▼                ▼              ▼                 ▼
┌──────────────┐ ┌──────────┐  ┌─────────────┐  ┌──────────────────┐
│ RateLimit    │ │ RateLimit│  │   Client    │  │ RateLimitHeader  │
│ Storage      │ │ Strategy │  │ Identifier  │  │   Generator      │
│              │ │          │  │  Strategy   │  │                  │
└──────────────┘ └──────────┘  └─────────────┘  └──────────────────┘
       │                │              │                 │
       │                │              │                 │
       ▼                ▼              ▼                 ▼
┌──────────────┐ ┌──────────┐  ┌─────────────┐  (Generates HTTP
│  InMemory    │ │ Sliding  │  │   Hybrid    │   headers)
│  Storage     │ │  Window  │  │    Token    │
│              │ │          │  │      IP     │
└──────────────┘ └──────────┘  └─────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.services.config` - Logging configuration (get_logger)
- `backend.services.auth.user_api_token_service` - Token validation (used by API layer)
- `backend.services.workflow.publishing` - Published workflow configuration (used by API layer)

**External Dependencies:**

- `dataclasses` - Configuration and bucket data structures
- `threading` - Thread-safe storage operations (Lock)
- `time` - Timestamp tracking for rate limit windows
- `abc` - Abstract base classes for strategies and storage

**Database Dependencies:** None (currently uses in-memory storage; Redis support could be added)

**Environment Variables:** None (configured programmatically)

**Configuration Sources:**

- Rate limit configuration comes from published workflow settings
- Service settings configured via RateLimitSettings dataclass

## Public API

### Exported Classes

- `RateLimitingService` - Main service orchestrator for rate limiting
- `RateLimitConfig` - TypedDict for rate limit configuration
- `RateLimitSettings` - Dataclass for service settings and time windows
- `RateLimitStorage` - Abstract base class for storage backends
- `InMemoryRateLimitStorage` - In-memory storage implementation
- `RateLimitStrategy` - Abstract base class for rate limiting algorithms
- `SlidingWindowStrategy` - Sliding window algorithm implementation
- `ClientIdentifierStrategy` - Abstract base class for client identification
- `HybridIdentifierStrategy` - Token-preferred, IP-fallback identification
- `TokenOnlyIdentifierStrategy` - Token-only identification (requires auth)
- `IPOnlyIdentifierStrategy` - IP-only identification (for public APIs)
- `RateLimitHeaderGenerator` - HTTP header generation utility

### Exported Functions

- `create_rate_limiting_service()` - Factory function to create service instances

### Constants and Configuration

- `rate_limiting_service` - Global singleton instance for convenient access
- `DEFAULT_SETTINGS` - Default RateLimitSettings instance

### Exceptions

```
Exception
└── RateLimitError
    ├── RateLimitExceeded
    ├── InvalidRateLimitConfig
    └── RateLimitStorageError
```

## Core Classes

### `RateLimitingService`

Main service orchestrator that coordinates storage, strategy, client identification, and header generation to provide a
complete rate limiting solution for published workflows.

**Purpose:** Provides a unified API for rate limiting by orchestrating multiple components (storage, strategy, client
identification, header generation).

**Responsibilities:**

- Check if requests are within configured rate limits
- Generate client identifiers from IP/token information
- Produce HTTP headers for rate limit status
- Clean up expired rate limit buckets
- Validate rate limit configurations

**Initialisation:**

```python
def __init__(
    self,
    storage: Optional[RateLimitStorage] = None,
    strategy: Optional[RateLimitStrategy] = None,
    client_identifier_strategy: Optional[ClientIdentifierStrategy] = None,
    settings: Optional[RateLimitSettings] = None,
) -> None:
    """
    Initialize rate limiting service.

    Args:
        storage: Storage backend (defaults to in-memory)
        strategy: Rate limiting strategy (defaults to sliding window)
        client_identifier_strategy: Client ID strategy (defaults to hybrid)
        settings: Rate limit settings (uses defaults if not provided)
    """
```

**Key Methods:**

#### `check_rate_limit()`

```python
def check_rate_limit(
    self,
    workflow_name: str,
    client_identifier: str,
    rate_limit_config: Optional[Dict[str, int]],
) -> Tuple[bool, Dict[str, int]]:
    """Check if request is within rate limits."""
```

**Parameters:**

- `workflow_name` (str) - Name of the workflow being accessed
- `client_identifier` (str) - Unique identifier for the client (format: "type:value", e.g., "ip:1.2.3.4" or "token:
  abc123")
- `rate_limit_config` (Optional[Dict[str, int]]) - Rate limit configuration from published workflow, e.g., {"
  requests_per_minute": 60, "requests_per_hour": 1000}

**Returns:**

- `Tuple[bool, Dict[str, int]]` - (is_allowed, rate_limit_info)
  - If allowed: `is_allowed=True`, info contains remaining counts (e.g., `{"per_minute_remaining": 9}`)
  - If denied: `is_allowed=False`, info contains
      `{"limit_type_hit": "per_minute", "remaining": 0, "reset_time": 1234567890, "retry_after": 45}`

**Raises:**

- No exceptions (returns tuple with success/failure information)

**Example:**

```python
from backend.services.rate_limiting import rate_limiting_service

# Check rate limit for a workflow
is_allowed, rate_info = rate_limiting_service.check_rate_limit(
    workflow_name="my_workflow",
    client_identifier="ip:192.168.1.100",
    rate_limit_config={"requests_per_minute": 60, "requests_per_hour": 1000}
)

if is_allowed:
    # Request allowed - proceed with execution
    print(f"Request allowed. Remaining: {rate_info}")
    # Output: Request allowed. Remaining: {'requests_per_minute_remaining': 59, 'requests_per_hour_remaining': 999}
else:
    # Rate limit exceeded
    retry_after = rate_info["retry_after"]
    limit_type = rate_info["limit_type_hit"]
    print(f"Rate limit exceeded for {limit_type}. Retry after {retry_after} seconds")
```

**Behaviour:**

- Checks all configured rate limit types (per_minute, per_hour, etc.)
- Uses sliding window algorithm for accurate counting
- Returns False immediately if any limit is exceeded
- Consumes a request slot if allowed
- Thread-safe for concurrent requests

**Use Cases:**

- Validate rate limits before executing published workflows
- Implement tiered rate limiting (different limits for different time windows)
- Provide detailed feedback on rate limit status

#### `get_rate_limit_headers()`

```python
def get_rate_limit_headers(
    self,
    workflow_name: str,
    client_identifier: str,
    rate_limit_config: Optional[Dict[str, int]],
) -> Dict[str, str]:
    """Get rate limit headers for HTTP responses."""
```

**Parameters:**

- `workflow_name` (str) - Name of the workflow
- `client_identifier` (str) - Unique identifier for the client
- `rate_limit_config` (Optional[Dict[str, int]]) - Rate limit configuration

**Returns:**

- `Dict[str, str]` - Dictionary of HTTP headers in format:

  ```
  {
      "X-RateLimit-Per-Minute-Limit": "60",
      "X-RateLimit-Per-Minute-Remaining": "59",
      "X-RateLimit-Per-Minute-Reset": "1234567890",
      "X-RateLimit-Per-Hour-Limit": "1000",
      "X-RateLimit-Per-Hour-Remaining": "999",
      "X-RateLimit-Per-Hour-Reset": "1234571490"
  }
  ```

**Example:**

```python
from backend.services.rate_limiting import rate_limiting_service

headers = rate_limiting_service.get_rate_limit_headers(
    workflow_name="my_workflow",
    client_identifier="token:na_abc123...",
    rate_limit_config={"requests_per_minute": 60}
)

# Add headers to HTTP response
response.headers.update(headers)
```

**Behaviour:**

- Generates standard X-RateLimit-* headers
- Does not consume request slots (read-only)
- Returns empty dict if no rate limits configured
- Gracefully handles missing buckets

**Use Cases:**

- Provide rate limit feedback in HTTP responses
- Allow API clients to track their usage
- Implement client-side rate limit handling

#### `get_client_identifier()`

```python
def get_client_identifier(
    self,
    client_ip: Optional[str],
    token: Optional[str]
) -> str:
    """Generate a unique identifier for rate limiting."""
```

**Parameters:**

- `client_ip` (Optional[str]) - Client IP address
- `token` (Optional[str]) - Authentication token (if any)

**Returns:**

- `str` - Unique identifier string (e.g., "token:abc123" or "ip:1.2.3.4")

**Example:**

```python
# For authenticated request
identifier = rate_limiting_service.get_client_identifier(
    client_ip="192.168.1.100",
    token="na_abc123..."
)
# Returns: "token:na_abc123..."

# For unauthenticated request
identifier = rate_limiting_service.get_client_identifier(
    client_ip="192.168.1.100",
    token=None
)
# Returns: "ip:192.168.1.100"
```

**Behaviour:**

- Uses configured ClientIdentifierStrategy (default: HybridIdentifierStrategy)
- Hybrid strategy prefers token over IP
- Returns "unknown:client" if neither IP nor token available
- Logs warning for unknown clients

**Use Cases:**

- Generate consistent identifiers for rate limiting
- Support both authenticated and unauthenticated workflows
- Allow different rate limits for users vs IPs

#### `cleanup_expired_buckets()`

```python
def cleanup_expired_buckets(
    self,
    max_age_seconds: Optional[int] = None
) -> None:
    """Clean up expired rate limit buckets to prevent memory leaks."""
```

**Parameters:**

- `max_age_seconds` (Optional[int]) - Maximum age of unused buckets in seconds (uses setting default if not provided)

**Returns:**

- None

**Example:**

```python
from backend.services.rate_limiting import rate_limiting_service
import time

# Schedule periodic cleanup (e.g., in a background task)
def periodic_cleanup():
    while True:
        rate_limiting_service.cleanup_expired_buckets(max_age_seconds=3600)
        time.sleep(600)  # Run every 10 minutes
```

**Behaviour:**

- Removes buckets with no recent requests older than max_age_seconds
- Thread-safe operation
- Logs number of buckets cleaned up
- Should be called periodically via background task

**Use Cases:**

- Prevent memory leaks from accumulating rate limit buckets
- Clean up buckets for inactive workflows/clients
- Maintain service performance over time

#### `get_storage_stats()`

```python
def get_storage_stats(self) -> Dict[str, int]:
    """Get statistics about the rate limiting storage."""
```

**Returns:**

- `Dict[str, int]` - Storage statistics (e.g., `{"workflow_keys": 42, "total_buckets": 156}`)

**Example:**

```python
stats = rate_limiting_service.get_storage_stats()
print(f"Tracking {stats['workflow_keys']} workflow/client combinations")
print(f"Total buckets: {stats['total_buckets']}")
```

**Behaviour:**

- Returns implementation-dependent statistics
- InMemoryRateLimitStorage returns workflow_keys and total_buckets counts
- Returns empty dict if storage doesn't support stats

**Use Cases:**

- Monitor service resource usage
- Debug rate limiting issues
- Track service growth over time

#### `validate_config()`

```python
def validate_config(
    self,
    rate_limit_config: Dict[str, int]
) -> bool:
    """Validate a rate limit configuration."""
```

**Parameters:**

- `rate_limit_config` (Dict[str, int]) - Rate limit configuration to validate

**Returns:**

- `bool` - True if valid

**Raises:**

- `ValueError` - If configuration is invalid (empty, unknown limit type, or non-positive max_requests)

**Example:**

```python
# Valid configuration
valid_config = {"requests_per_minute": 60, "requests_per_hour": 1000}
rate_limiting_service.validate_config(valid_config)  # Returns True

# Invalid configuration
invalid_config = {"requests_per_minute": -10}
try:
    rate_limiting_service.validate_config(invalid_config)
except ValueError as e:
    print(f"Invalid config: {e}")
```

**Behaviour:**

- Validates limit types are recognized (per_second, per_minute, per_hour, per_day, or custom per_N)
- Ensures max_requests values are positive integers
- Raises ValueError with descriptive message if invalid

**Use Cases:**

- Validate workflow rate limit configurations before saving
- Provide early feedback on configuration errors
- Prevent runtime errors from invalid configurations

---

### `RateLimitConfig`

TypedDict for rate limit configuration dictionaries. Provides type hints for rate limit configurations without enforcing
runtime validation.

**Purpose:** Type definition for rate limit configuration passed to the service.

```python
class RateLimitConfig(TypedDict, total=False):
    """Type definition for rate limit configuration dictionary."""

    per_second: int
    per_minute: int
    per_hour: int
    per_day: int
    requests_per_second: int
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
```

**Example:**

```python
from backend.services.rate_limiting import RateLimitConfig

# Type-checked configuration
config: RateLimitConfig = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
}
```

**Use Cases:**

- Type hints for rate limit configurations
- IDE auto-completion support
- Static type checking with mypy

---

### `RateLimitSettings`

Configuration dataclass for rate limiting service settings, time window mappings, and validation.

**Purpose:** Configures service behaviour and defines time windows for rate limit types.

```python
@dataclass
class RateLimitSettings:
    """Configuration settings for rate limiting service."""

    max_bucket_age_seconds: int = 3600
    debug_logging: bool = False
    time_windows: Dict[str, int] = field(default_factory=lambda: {
        "per_second": 1,
        "requests_per_second": 1,
        "per_minute": 60,
        "requests_per_minute": 60,
        "per_hour": 3600,
        "requests_per_hour": 3600,
        "per_day": 86400,
        "requests_per_day": 86400,
    })
```

**Fields:**

- `max_bucket_age_seconds` (int) - Maximum age for unused buckets before cleanup (default: 3600)
- `debug_logging` (bool) - Enable debug logging for rate limit checks (default: False)
- `time_windows` (Dict[str, int]) - Mapping of limit types to window durations in seconds

**Key Methods:**

#### `get_window_seconds()`

```python
def get_window_seconds(self, limit_type: str) -> Optional[int]:
    """Get the time window in seconds for a given limit type."""
```

**Parameters:**

- `limit_type` (str) - Rate limit type (e.g., "per_minute", "requests_per_hour")

**Returns:**

- `Optional[int]` - Window duration in seconds, or None if not recognised

**Example:**

```python
from backend.services.rate_limiting import RateLimitSettings

settings = RateLimitSettings()

# Standard window
window = settings.get_window_seconds("per_minute")
print(window)  # Output: 60

# Custom window (e.g., "per_300" for 300 seconds)
window = settings.get_window_seconds("per_300")
print(window)  # Output: 300
```

**Behaviour:**

- Checks predefined time_windows mapping
- Supports custom windows with format "per_N" where N is seconds
- Returns None for unrecognised formats

#### `validate_rate_limit_config()`

```python
def validate_rate_limit_config(self, config: Dict[str, int]) -> bool:
    """Validate a rate limit configuration dictionary."""
```

**Parameters:**

- `config` (Dict[str, int]) - Rate limit configuration to validate

**Returns:**

- `bool` - True if valid

**Raises:**

- `ValueError` - If configuration is invalid

**Example:**

```python
settings = RateLimitSettings()

try:
    settings.validate_rate_limit_config({"requests_per_minute": 60})
    print("Configuration valid")
except ValueError as e:
    print(f"Invalid: {e}")
```

---

### `RateLimitStorage`

Abstract base class for rate limit storage backends. Defines the interface for storing and retrieving rate limit
buckets.

**Purpose:** Provides pluggable storage backends for rate limiting data.

```python
class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    def get_bucket(
        self,
        workflow_key: str,
        limit_type: str,
        max_requests: int,
        window_seconds: int
    ) -> RateLimitBucket:
        """Get or create a rate limit bucket."""

    @abstractmethod
    def cleanup_expired(
        self,
        current_time: float,
        max_age_seconds: int
    ) -> int:
        """Clean up expired rate limit buckets."""
```

**Use Cases:**

- Implement custom storage backends (Redis, database)
- Support distributed rate limiting
- Test with mock storage backends

---

### `InMemoryRateLimitStorage`

In-memory storage implementation using thread-safe dictionaries for rate limit buckets.

**Purpose:** Provides fast, in-process storage for rate limiting with thread safety.

**Responsibilities:**

- Store rate limit buckets in memory
- Provide thread-safe access to buckets
- Clean up expired buckets
- Track storage statistics

**Initialisation:**

```python
def __init__(self):
    """Initialize in-memory storage."""
```

**Key Methods:**

#### `get_bucket()`

```python
def get_bucket(
    self,
    workflow_key: str,
    limit_type: str,
    max_requests: int,
    window_seconds: int
) -> RateLimitBucket:
    """Get or create a rate limit bucket."""
```

**Parameters:**

- `workflow_key` (str) - Unique key for workflow:client combination (e.g., "my_workflow:ip:1.2.3.4")
- `limit_type` (str) - Type of rate limit (e.g., "per_minute")
- `max_requests` (int) - Maximum requests allowed
- `window_seconds` (int) - Time window in seconds

**Returns:**

- `RateLimitBucket` - Existing or newly created bucket

**Example:**

```python
from backend.services.rate_limiting import InMemoryRateLimitStorage

storage = InMemoryRateLimitStorage()

bucket = storage.get_bucket(
    workflow_key="my_workflow:ip:192.168.1.100",
    limit_type="per_minute",
    max_requests=60,
    window_seconds=60
)

is_allowed, remaining = bucket.is_allowed(time.time())
```

**Behaviour:**

- Thread-safe bucket creation with double-checked locking
- Creates buckets on-demand
- Reuses existing buckets for same workflow_key:limit_type combination

#### `cleanup_expired()`

```python
def cleanup_expired(
    self,
    current_time: float,
    max_age_seconds: int
) -> int:
    """Clean up expired rate limit buckets."""
```

**Parameters:**

- `current_time` (float) - Current timestamp in seconds
- `max_age_seconds` (int) - Maximum age for unused buckets

**Returns:**

- `int` - Number of workflow keys cleaned up

**Behaviour:**

- Removes buckets with no recent requests
- Cleans up empty workflow entries
- Thread-safe operation
- Logs cleanup statistics

#### `get_stats()`

```python
def get_stats(self) -> Dict[str, int]:
    """Get storage statistics."""
```

**Returns:**

- `Dict[str, int]` - Statistics with keys "workflow_keys" and "total_buckets"

**Example:**

```python
stats = storage.get_stats()
print(f"Workflow keys: {stats['workflow_keys']}")
print(f"Total buckets: {stats['total_buckets']}")
```

---

### `RateLimitBucket`

Dataclass representing a single rate limit bucket using sliding window algorithm.

**Purpose:** Tracks request timestamps and enforces limits for a specific workflow:client:limit_type combination.

```python
@dataclass
class RateLimitBucket:
    """Rate limit bucket for tracking requests using sliding window algorithm."""

    max_requests: int
    window_seconds: int
    requests: List[float] = field(default_factory=list)
    lock: Lock = field(default_factory=Lock)
```

**Fields:**

- `max_requests` (int) - Maximum requests allowed in the window
- `window_seconds` (int) - Duration of the time window in seconds
- `requests` (List[float]) - Timestamps of requests within the window
- `lock` (Lock) - Thread lock for concurrent access

**Key Methods:**

#### `is_allowed()`

```python
def is_allowed(self, current_time: float) -> Tuple[bool, int]:
    """Check if request is allowed and return remaining count."""
```

**Parameters:**

- `current_time` (float) - Current timestamp in seconds

**Returns:**

- `Tuple[bool, int]` - (is_allowed, remaining_requests)

**Behaviour:**

- Removes expired requests outside the time window
- Checks if under the limit
- Adds current request to bucket if allowed
- Returns remaining capacity

#### `get_reset_time()`

```python
def get_reset_time(self, current_time: float) -> float:
    """Get the time when the oldest request will expire."""
```

**Returns:**

- `float` - Timestamp when the rate limit will reset

#### `get_remaining_count()`

```python
def get_remaining_count(self, current_time: float) -> int:
    """Get the number of remaining requests without consuming one."""
```

**Returns:**

- `int` - Number of remaining requests

---

### `SlidingWindowStrategy`

Sliding window rate limiting strategy implementation that provides accurate rate limiting across multiple time windows.

**Purpose:** Implements sliding window algorithm for precise rate limiting.

**Responsibilities:**

- Check requests against multiple rate limit types
- Track request timestamps in sliding windows
- Provide rate limit status without consuming requests
- Log rate limit violations

**Initialisation:**

```python
def __init__(
    self,
    storage: RateLimitStorage,
    settings: Optional[RateLimitSettings] = None,
) -> None:
    """
    Initialize sliding window strategy.

    Args:
        storage: Storage backend for rate limit data
        settings: Rate limit settings (uses defaults if not provided)
    """
```

**Key Methods:**

#### `check_limit()`

```python
def check_limit(
    self,
    workflow_name: str,
    client_identifier: str,
    rate_limit_config: Dict[str, int],
) -> Tuple[bool, Dict[str, int]]:
    """Check if request is within rate limits using sliding window algorithm."""
```

**Parameters:**

- `workflow_name` (str) - Name of the workflow
- `client_identifier` (str) - Unique identifier for the client
- `rate_limit_config` (Dict[str, int]) - Rate limit configuration (e.g., {"per_minute": 60})

**Returns:**

- `Tuple[bool, Dict[str, int]]` - (is_allowed, rate_limit_info)

**Example:**

```python
from backend.services.rate_limiting import (
    SlidingWindowStrategy,
    InMemoryRateLimitStorage,
    RateLimitSettings
)

storage = InMemoryRateLimitStorage()
settings = RateLimitSettings(debug_logging=True)
strategy = SlidingWindowStrategy(storage, settings)

is_allowed, info = strategy.check_limit(
    workflow_name="my_workflow",
    client_identifier="ip:192.168.1.100",
    rate_limit_config={"per_minute": 60, "per_hour": 1000}
)

if is_allowed:
    print(f"Request allowed: {info}")
else:
    print(f"Rate limit exceeded: {info['limit_type_hit']}")
```

**Behaviour:**

- Checks all configured rate limit types sequentially
- Returns False immediately if any limit exceeded
- Tracks remaining counts for each limit type
- Logs debug information if enabled

#### `get_rate_limit_status()`

```python
def get_rate_limit_status(
    self,
    workflow_name: str,
    client_identifier: str,
    rate_limit_config: Dict[str, int],
) -> Dict[str, Dict[str, int]]:
    """Get current rate limit status without consuming a request."""
```

**Returns:**

- `Dict[str, Dict[str, int]]` - Mapping of limit_type to status info (remaining, reset_time, limit)

**Example:**

```python
status = strategy.get_rate_limit_status(
    workflow_name="my_workflow",
    client_identifier="ip:192.168.1.100",
    rate_limit_config={"per_minute": 60}
)

print(status)
# Output: {
#     "per_minute": {
#         "limit": 60,
#         "remaining": 45,
#         "reset_time": 1234567890
#     }
# }
```

**Behaviour:**

- Read-only operation (doesn't consume requests)
- Returns current status for all configured limits
- Useful for generating headers or status endpoints

---

### `ClientIdentifierStrategy`

Abstract base class for client identification strategies.

**Purpose:** Defines interface for generating unique client identifiers from request information.

```python
class ClientIdentifierStrategy(ABC):
    """Abstract base class for client identification strategies."""

    @abstractmethod
    def get_identifier(
        self,
        client_ip: Optional[str],
        token: Optional[str]
    ) -> str:
        """Generate a unique identifier for rate limiting."""
```

---

### `HybridIdentifierStrategy`

Hybrid client identification strategy that prefers token-based identification for authenticated requests, falls back to
IP-based for unauthenticated requests.

**Purpose:** Provides flexible identification supporting both authenticated and unauthenticated workflows.

**Responsibilities:**

- Prefer token-based identification when available
- Fall back to IP-based identification for public workflows
- Provide default identifier for unidentifiable clients

**Key Methods:**

#### `get_identifier()`

```python
def get_identifier(
    self,
    client_ip: Optional[str],
    token: Optional[str]
) -> str:
    """Generate a unique identifier preferring token over IP."""
```

**Returns:**

- `str` - Unique identifier in format "type:value" (e.g., "token:abc123", "ip:1.2.3.4", "unknown:client")

**Example:**

```python
from backend.services.rate_limiting import HybridIdentifierStrategy

strategy = HybridIdentifierStrategy()

# Authenticated request
identifier = strategy.get_identifier(
    client_ip="192.168.1.100",
    token="na_abc123..."
)
print(identifier)  # Output: "token:na_abc123..."

# Unauthenticated request
identifier = strategy.get_identifier(
    client_ip="192.168.1.100",
    token=None
)
print(identifier)  # Output: "ip:192.168.1.100"

# No identification
identifier = strategy.get_identifier(
    client_ip=None,
    token=None
)
print(identifier)  # Output: "unknown:client"
```

**Behaviour:**

- Priority: token → IP → default "unknown:client"
- Logs warning for unknown clients
- Allows different rate limits for authenticated vs unauthenticated users

**Use Cases:**

- Workflows that support both authenticated and public access
- Per-user rate limiting for authenticated requests
- Per-IP rate limiting for public requests

---

### `TokenOnlyIdentifierStrategy`

Token-only identification strategy that requires authentication for rate limiting.

**Purpose:** Strict identification for authenticated-only workflows.

**Key Methods:**

#### `get_identifier()`

```python
def get_identifier(
    self,
    client_ip: Optional[str],
    token: Optional[str]
) -> str:
    """Generate identifier based only on token."""
```

**Raises:**

- `ValueError` - If no token provided

**Example:**

```python
from backend.services.rate_limiting import TokenOnlyIdentifierStrategy

strategy = TokenOnlyIdentifierStrategy()

try:
    identifier = strategy.get_identifier(
        client_ip="192.168.1.100",
        token=None
    )
except ValueError as e:
    print(f"Error: {e}")  # Error: Token required for rate limiting
```

**Use Cases:**

- APIs that require authentication
- Per-user rate limiting only
- Preventing unauthenticated access

---

### `IPOnlyIdentifierStrategy`

IP-only identification strategy for public workflows.

**Purpose:** Simple IP-based identification for unauthenticated workflows.

**Key Methods:**

#### `get_identifier()`

```python
def get_identifier(
    self,
    client_ip: Optional[str],
    token: Optional[str]
) -> str:
    """Generate identifier based only on IP."""
```

**Raises:**

- `ValueError` - If no IP provided

**Example:**

```python
from backend.services.rate_limiting import IPOnlyIdentifierStrategy

strategy = IPOnlyIdentifierStrategy()

identifier = strategy.get_identifier(
    client_ip="192.168.1.100",
    token="ignored"
)
print(identifier)  # Output: "ip:192.168.1.100"
```

**Use Cases:**

- Public APIs without authentication
- Per-IP rate limiting
- Simple rate limiting scenarios

---

### `RateLimitHeaderGenerator`

Utility class for generating standard rate limit HTTP headers.

**Purpose:** Generates X-RateLimit-* headers for HTTP responses.

**Initialisation:**

```python
def __init__(
    self,
    storage: RateLimitStorage,
    settings: Optional[RateLimitSettings] = None,
) -> None:
    """
    Initialize header generator.

    Args:
        storage: Storage backend for rate limit data
        settings: Rate limit settings (uses defaults if not provided)
    """
```

**Key Methods:**

#### `generate_headers()`

```python
def generate_headers(
    self,
    workflow_name: str,
    client_identifier: str,
    rate_limit_config: Optional[Dict[str, int]],
) -> Dict[str, str]:
    """Generate rate limit headers for HTTP responses."""
```

**Returns:**

- `Dict[str, str]` - HTTP headers in format:

  ```
  {
      "X-RateLimit-Per-Minute-Limit": "60",
      "X-RateLimit-Per-Minute-Remaining": "59",
      "X-RateLimit-Per-Minute-Reset": "1234567890"
  }
  ```

**Example:**

```python
from backend.services.rate_limiting import (
    RateLimitHeaderGenerator,
    InMemoryRateLimitStorage
)

storage = InMemoryRateLimitStorage()
generator = RateLimitHeaderGenerator(storage)

headers = generator.generate_headers(
    workflow_name="my_workflow",
    client_identifier="ip:192.168.1.100",
    rate_limit_config={"requests_per_minute": 60}
)

# Add to FastAPI response
from fastapi import Response

response = Response()
response.headers.update(headers)
```

**Behaviour:**

- Generates headers for all configured limit types
- Does not consume request slots (read-only)
- Formats limit type names for headers (per_minute → Per-Minute)
- Returns empty dict if no rate limits configured
- Gracefully handles errors

#### `generate_retry_after_headers()`

```python
def generate_retry_after_headers(
    self,
    retry_after: int,
    reset_time: int
) -> Dict[str, str]:
    """Generate headers for rate limit exceeded responses."""
```

**Returns:**

- `Dict[str, str]` - Headers with "Retry-After" and "X-RateLimit-Reset"

**Example:**

```python
headers = generator.generate_retry_after_headers(
    retry_after=45,
    reset_time=1234567890
)

# Output: {
#     "Retry-After": "45",
#     "X-RateLimit-Reset": "1234567890"
# }
```

**Use Cases:**

- Include in 429 Too Many Requests responses
- Inform clients when they can retry
- Provide standard retry information

---

## Functions

### `create_rate_limiting_service()`

Factory function to create a configured RateLimitingService instance with optional custom components.

**Signature:**

```python
def create_rate_limiting_service(
    storage: Optional[RateLimitStorage] = None,
    strategy: Optional[RateLimitStrategy] = None,
    client_identifier_strategy: Optional[ClientIdentifierStrategy] = None,
    debug_logging: bool = False,
    max_bucket_age_seconds: int = 3600,
) -> RateLimitingService:
    """Create a rate limiting service instance."""
```

**Parameters:**

- `storage` (Optional[RateLimitStorage]) - Storage backend (defaults to InMemoryRateLimitStorage)
- `strategy` (Optional[RateLimitStrategy]) - Rate limiting strategy (defaults to SlidingWindowStrategy)
- `client_identifier_strategy` (Optional[ClientIdentifierStrategy]) - Client ID strategy (defaults to
  HybridIdentifierStrategy)
- `debug_logging` (bool) - Enable debug logging for rate limit checks (default: False)
- `max_bucket_age_seconds` (int) - Maximum age for unused buckets before cleanup (default: 3600)

**Returns:**

- `RateLimitingService` - Configured service instance

**Example:**

```python
from backend.services.rate_limiting import (
    create_rate_limiting_service,
    TokenOnlyIdentifierStrategy
)

# Create service with custom configuration
service = create_rate_limiting_service(
    debug_logging=True,
    max_bucket_age_seconds=7200,
    client_identifier_strategy=TokenOnlyIdentifierStrategy()
)

# Use the service
is_allowed, info = service.check_rate_limit(
    workflow_name="my_workflow",
    client_identifier="token:abc123",
    rate_limit_config={"requests_per_minute": 100}
)
```

**Use Cases:**

- Create custom service instances for testing
- Configure service with different strategies
- Enable debug logging for troubleshooting
- Adjust cleanup intervals for specific needs

---

## Configuration

### Configuration Classes

**RateLimitSettings:**

```python
@dataclass
class RateLimitSettings:
    """Configuration settings for rate limiting service."""

    max_bucket_age_seconds: int = 3600
    debug_logging: bool = False
    time_windows: Dict[str, int] = field(default_factory=lambda: {
        "per_second": 1,
        "requests_per_second": 1,
        "per_minute": 60,
        "requests_per_minute": 60,
        "per_hour": 3600,
        "requests_per_hour": 3600,
        "per_day": 86400,
        "requests_per_day": 86400,
    })
```

**Fields:**

- `max_bucket_age_seconds` - Maximum age for unused buckets before cleanup (default: 3600)
- `debug_logging` - Enable debug logging (default: False)
- `time_windows` - Mapping of limit types to window durations in seconds

**RateLimitConfig (TypedDict):**

```python
class RateLimitConfig(TypedDict, total=False):
    """Type definition for rate limit configuration."""

    per_second: int
    per_minute: int
    per_hour: int
    per_day: int
    requests_per_second: int
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
```

### Environment Variables

None. The rate limiting service is configured entirely through code and published workflow settings.

### Initialisation Patterns

**Basic Initialisation (Using Global Singleton):**

```python
from backend.services.rate_limiting import rate_limiting_service

# Use the global singleton instance
is_allowed, info = rate_limiting_service.check_rate_limit(
    workflow_name="my_workflow",
    client_identifier="ip:192.168.1.100",
    rate_limit_config={"requests_per_minute": 60}
)
```

**Advanced Initialisation (Custom Instance):**

```python
from backend.services.rate_limiting import (
    create_rate_limiting_service,
    RateLimitSettings,
    TokenOnlyIdentifierStrategy
)

# Create custom settings
settings = RateLimitSettings(
    debug_logging=True,
    max_bucket_age_seconds=7200
)

# Create service with custom configuration
service = create_rate_limiting_service(
    debug_logging=True,
    max_bucket_age_seconds=7200,
    client_identifier_strategy=TokenOnlyIdentifierStrategy()
)

# Use the custom service
is_allowed, info = service.check_rate_limit(
    workflow_name="my_workflow",
    client_identifier="token:abc123",
    rate_limit_config={"requests_per_minute": 100}
)
```

**Testing Initialisation (Mock Storage):**

```python
from backend.services.rate_limiting import (
    RateLimitingService,
    RateLimitSettings,
    SlidingWindowStrategy
)
from unittest.mock import Mock

# Create mock storage for testing
mock_storage = Mock()
settings = RateLimitSettings(debug_logging=False)
strategy = SlidingWindowStrategy(mock_storage, settings)

# Create service with mock
service = RateLimitingService(
    storage=mock_storage,
    strategy=strategy,
    settings=settings
)
```

---

## Error Handling

### Exception Hierarchy

```
Exception
└── RateLimitError
    ├── RateLimitExceeded
    ├── InvalidRateLimitConfig
    └── RateLimitStorageError
```

### Exception Details

#### `RateLimitError`

Base exception for all rate limiting errors.

**Inherits from:** `Exception`

**When raised:**

- Base class for all rate limiting exceptions
- Not typically raised directly

#### `RateLimitExceeded`

Raised when a client exceeds configured rate limits.

**Inherits from:** `RateLimitError`

**When raised:**

- Client has exceeded rate limit for a specific time window
- Typically raised by API layer, not directly by the service

**Attributes:**

- `limit_type` (str) - Type of limit that was hit (e.g., "per_minute")
- `retry_after` (int) - Seconds until the client can retry
- `reset_time` (int) - Unix timestamp when the limit resets

**Example:**

```python
from backend.services.rate_limiting import RateLimitExceeded

try:
    # This would typically be raised by API layer
    raise RateLimitExceeded(
        limit_type="per_minute",
        retry_after=45,
        reset_time=1234567890,
        message="Too many requests"
    )
except RateLimitExceeded as e:
    print(f"Rate limit hit: {e.limit_type}")
    print(f"Retry after: {e.retry_after} seconds")
    print(f"Resets at: {e.reset_time}")
```

#### `InvalidRateLimitConfig`

Raised when rate limit configuration is invalid.

**Inherits from:** `RateLimitError`

**When raised:**

- Unknown rate limit type in configuration
- Non-positive max_requests value
- Empty rate limit configuration

**Attributes:**

- `config_type` (str) - Type of config that's invalid
- `reason` (str) - Reason why it's invalid

**Example:**

```python
from backend.services.rate_limiting import InvalidRateLimitConfig

try:
    # Invalid configuration
    config = {"unknown_limit_type": 100}
    rate_limiting_service.validate_config(config)
except InvalidRateLimitConfig as e:
    print(f"Invalid config: {e.config_type}")
    print(f"Reason: {e.reason}")
```

#### `RateLimitStorageError`

Raised when there's an error with the rate limit storage backend.

**Inherits from:** `RateLimitError`

**When raised:**

- Storage backend connection failure
- Storage operation timeout
- Unexpected storage errors

**Example:**

```python
from backend.services.rate_limiting import RateLimitStorageError

try:
    # Storage operation
    storage.get_bucket(...)
except RateLimitStorageError as e:
    logger.error(f"Storage error: {e}")
    # Fall back to allowing request
```

### Error Handling Patterns

**Recommended Pattern for API Integration:**

```python
from backend.services.rate_limiting import (
    rate_limiting_service,
    RateLimitExceeded
)
from fastapi import HTTPException, status

async def check_workflow_rate_limit(
    workflow_name: str,
    client_ip: str,
    token: Optional[str],
    rate_limit_config: Dict[str, int]
):
    """Check rate limits and raise HTTP exception if exceeded."""

    try:
        # Get client identifier
        client_identifier = rate_limiting_service.get_client_identifier(
            client_ip, token
        )

        # Check rate limit
        is_allowed, rate_info = rate_limiting_service.check_rate_limit(
            workflow_name=workflow_name,
            client_identifier=client_identifier,
            rate_limit_config=rate_limit_config
        )

        if not is_allowed:
            # Rate limit exceeded
            limit_type = rate_info.get("limit_type_hit", "requests")
            retry_after = rate_info.get("retry_after", 60)
            reset_time = rate_info.get("reset_time")

            # Raise HTTP 429 Too Many Requests
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {limit_type}. "
                       f"Retry after {retry_after} seconds.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Reset": str(reset_time)
                }
            )

        # Request allowed - return rate limit info
        return rate_info

    except Exception as e:
        # Log error but allow request (fail open)
        logger.error(f"Rate limiting error: {e}")
        return {"error": "rate_limiting_check_failed"}
```

**Configuration Validation Pattern:**

```python
from backend.services.rate_limiting import rate_limiting_service

def validate_workflow_rate_limits(config: Dict[str, int]) -> bool:
    """Validate rate limit configuration before saving workflow."""

    try:
        rate_limiting_service.validate_config(config)
        return True
    except ValueError as e:
        logger.error(f"Invalid rate limit config: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid rate limit configuration: {str(e)}"
        )
```

**Graceful Degradation Pattern:**

```python
def check_rate_limit_with_fallback(
    workflow_name: str,
    client_identifier: str,
    rate_limit_config: Dict[str, int]
) -> Tuple[bool, Dict[str, int]]:
    """Check rate limit with graceful fallback on errors."""

    try:
        return rate_limiting_service.check_rate_limit(
            workflow_name, client_identifier, rate_limit_config
        )
    except Exception as e:
        # Log error and fail open (allow request)
        logger.error(f"Rate limiting error: {e}")
        return True, {"error": "rate_limiting_unavailable"}
```

---

## Integration Patterns

### Integration with API Layer

The rate limiting service is primarily used by the HTTP execution API to enforce limits on published workflows.

**Example
from [backend/api/http_execution/services/authentication.py](../../backend/api/http_execution/services/authentication.py):
**

```python
from backend.services.rate_limiting import rate_limiting_service
from backend.api.http_execution.exceptions import RateLimitExceededException

class HttpAuthService:
    """Service for authenticating and authorizing HTTP execution requests."""

    @staticmethod
    def check_rate_limits(
        published_workflow: Any,
        graph_name: str,
        client_ip: Optional[str],
        token: Optional[str],
    ) -> None:
        """Check and enforce rate limits for a workflow execution."""

        if not published_workflow.rate_limit:
            return  # No rate limits configured

        # Get client identifier for rate limiting
        client_identifier = rate_limiting_service.get_client_identifier(
            client_ip, token
        )

        # Check rate limits
        is_allowed, rate_info = rate_limiting_service.check_rate_limit(
            workflow_name=graph_name,
            client_identifier=client_identifier,
            rate_limit_config=published_workflow.rate_limit,
        )

        if not is_allowed:
            limit_type = rate_info.get("limit_type_hit", "requests")
            retry_after = rate_info.get("retry_after", 60)
            reset_time = rate_info.get("reset_time")
            remaining = rate_info.get("remaining", 0)

            raise RateLimitExceededException(
                limit_type=limit_type,
                retry_after=retry_after,
                reset_time=reset_time,
                remaining=remaining,
            )
```

**Complete API Route Example:**

```python
from fastapi import APIRouter, Request, HTTPException, status
from backend.services.rate_limiting import rate_limiting_service
from backend.services.workflow.publishing import WorkflowPublishingService

router = APIRouter()

@router.post("/api/http-execution/trigger/{workflow_name}")
async def trigger_workflow(
    workflow_name: str,
    request: Request,
    authorization: Optional[str] = None
):
    """Trigger a published workflow with rate limiting."""

    # Extract client information
    client_ip = request.client.host
    token = authorization.replace("Bearer ", "") if authorization else None

    # Get published workflow
    published_workflow = WorkflowPublishingService.get_published_workflow_by_identifier(
        workflow_name
    )

    if not published_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check rate limits
    if published_workflow.rate_limit:
        client_identifier = rate_limiting_service.get_client_identifier(
            client_ip, token
        )

        is_allowed, rate_info = rate_limiting_service.check_rate_limit(
            workflow_name=workflow_name,
            client_identifier=client_identifier,
            rate_limit_config=published_workflow.rate_limit
        )

        if not is_allowed:
            retry_after = rate_info.get("retry_after", 60)
            reset_time = rate_info.get("reset_time")

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Reset": str(reset_time)
                }
            )

        # Add rate limit headers to response
        headers = rate_limiting_service.get_rate_limit_headers(
            workflow_name, client_identifier, published_workflow.rate_limit
        )

    # Execute workflow
    # ... execution logic ...

    return {"status": "success"}
```

### Integration with Other Services

**Workflow Publishing Service:**

The rate limiting service integrates with the workflow publishing service to retrieve rate limit configurations.

```python
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.services.rate_limiting import rate_limiting_service

# Get published workflow with rate limit config
published_workflow = WorkflowPublishingService.get_published_workflow_by_identifier(
    "my-workflow"
)

# Use rate limit config from workflow
if published_workflow.rate_limit:
    client_identifier = rate_limiting_service.get_client_identifier(
        client_ip="192.168.1.100",
        token=None
    )

    is_allowed, rate_info = rate_limiting_service.check_rate_limit(
        workflow_name=published_workflow.name,
        client_identifier=client_identifier,
        rate_limit_config=published_workflow.rate_limit
    )
```

**Authentication Service:**

The rate limiting service uses tokens from the authentication service for client identification.

```python
from backend.services.auth.user_api_token_service import UserAPITokenService
from backend.services.rate_limiting import rate_limiting_service

# Validate token
result = UserAPITokenService.validate_token(token, workflow_name)

if result:
    token_obj, user_id = result

    # Use token for rate limiting
    client_identifier = rate_limiting_service.get_client_identifier(
        client_ip=None,
        token=token
    )

    # Token-based rate limiting (per-user)
    is_allowed, rate_info = rate_limiting_service.check_rate_limit(
        workflow_name=workflow_name,
        client_identifier=client_identifier,  # Will be "token:abc123..."
        rate_limit_config={"requests_per_minute": 100}
    )
```

### Dependency Flow

```
Published Workflow Config
         │
         ▼
┌────────────────────────┐
│   API Route Handler    │
│  (HTTP Execution)      │
└───────────┬────────────┘
            │
            ├─────────────────────────────────┐
            │                                 │
            ▼                                 ▼
┌───────────────────────┐         ┌──────────────────────┐
│  Workflow Publishing  │         │  Authentication      │
│  Service              │         │  Service             │
│  (rate limit config)  │         │  (token validation)  │
└───────────────────────┘         └──────────────────────┘
            │                                 │
            │                                 │
            └─────────────┬───────────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │  Rate Limiting       │
                │  Service             │
                └──────────────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │  Storage Backend     │
                │  (In-Memory)         │
                └──────────────────────┘
```

**Data Flow:**

1. API receives HTTP request
2. Extracts client IP and authentication token
3. Retrieves published workflow configuration
4. Validates authentication token (if required)
5. Rate limiting service generates client identifier
6. Checks rate limits using workflow configuration
7. Returns allow/deny decision with rate limit info
8. API adds rate limit headers to response

### Common Integration Patterns

#### Pattern 1: Rate Limit Middleware

```python
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.rate_limiting import rate_limiting_service

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        # Extract workflow name from path
        workflow_name = request.path_params.get("workflow_name")

        if workflow_name:
            # Get client info
            client_ip = request.client.host
            token = request.headers.get("Authorization", "").replace("Bearer ", "")

            # Get workflow config
            published_workflow = get_published_workflow(workflow_name)

            if published_workflow and published_workflow.rate_limit:
                # Check rate limit
                client_identifier = rate_limiting_service.get_client_identifier(
                    client_ip, token
                )

                is_allowed, rate_info = rate_limiting_service.check_rate_limit(
                    workflow_name=workflow_name,
                    client_identifier=client_identifier,
                    rate_limit_config=published_workflow.rate_limit
                )

                if not is_allowed:
                    return HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded"
                    )

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers
        if workflow_name and published_workflow:
            headers = rate_limiting_service.get_rate_limit_headers(
                workflow_name, client_identifier, published_workflow.rate_limit
            )
            for key, value in headers.items():
                response.headers[key] = value

        return response
```

#### Pattern 2: Rate Limit Dependency

```python
from fastapi import Depends, HTTPException, Request, status
from backend.services.rate_limiting import rate_limiting_service

async def check_rate_limit(
    request: Request,
    workflow_name: str,
    rate_limit_config: Dict[str, int]
):
    """FastAPI dependency for rate limiting."""

    client_ip = request.client.host
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    client_identifier = rate_limiting_service.get_client_identifier(
        client_ip, token
    )

    is_allowed, rate_info = rate_limiting_service.check_rate_limit(
        workflow_name=workflow_name,
        client_identifier=client_identifier,
        rate_limit_config=rate_limit_config
    )

    if not is_allowed:
        retry_after = rate_info.get("retry_after", 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

    return rate_info


@router.post("/trigger/{workflow_name}")
async def trigger_workflow(
    workflow_name: str,
    rate_limit_info: Dict = Depends(check_rate_limit)
):
    """Route with rate limit dependency."""
    # Execute workflow
    return {"status": "success", "rate_limit": rate_limit_info}
```

#### Pattern 3: Background Cleanup Task

```python
import asyncio
from backend.services.rate_limiting import rate_limiting_service

async def cleanup_rate_limit_buckets():
    """Background task to clean up expired rate limit buckets."""

    while True:
        try:
            # Run cleanup every 10 minutes
            await asyncio.sleep(600)

            # Clean up buckets older than 1 hour
            rate_limiting_service.cleanup_expired_buckets(
                max_age_seconds=3600
            )

            # Log statistics
            stats = rate_limiting_service.get_storage_stats()
            logger.info(f"Rate limit storage: {stats}")

        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# Start background task on application startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_rate_limit_buckets())
```

---

## Usage Examples

### Example 1: Basic Usage

Complete end-to-end example of basic rate limiting for a published workflow:

```python
from backend.services.rate_limiting import rate_limiting_service

# Step 1: Get client identifier
client_identifier = rate_limiting_service.get_client_identifier(
    client_ip="192.168.1.100",
    token=None  # Unauthenticated request
)
print(f"Client ID: {client_identifier}")
# Output: Client ID: ip:192.168.1.100

# Step 2: Check rate limit
rate_limit_config = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
}

is_allowed, rate_info = rate_limiting_service.check_rate_limit(
    workflow_name="my_workflow",
    client_identifier=client_identifier,
    rate_limit_config=rate_limit_config
)

# Step 3: Process result
if is_allowed:
    print("Request allowed!")
    print(f"Remaining this minute: {rate_info.get('requests_per_minute_remaining')}")
    print(f"Remaining this hour: {rate_info.get('requests_per_hour_remaining')}")
    # Proceed with workflow execution
else:
    print("Rate limit exceeded!")
    print(f"Limit hit: {rate_info['limit_type_hit']}")
    print(f"Retry after: {rate_info['retry_after']} seconds")
    print(f"Resets at: {rate_info['reset_time']}")
```

### Example 2: Advanced Usage with Custom Strategy

Complete example showing advanced features with custom client identification:

```python
from backend.services.rate_limiting import (
    create_rate_limiting_service,
    TokenOnlyIdentifierStrategy,
    InMemoryRateLimitStorage,
    RateLimitSettings
)

# Step 1: Create custom service with token-only identification
service = create_rate_limiting_service(
    client_identifier_strategy=TokenOnlyIdentifierStrategy(),
    debug_logging=True,
    max_bucket_age_seconds=7200
)

# Step 2: Configure rate limits
rate_limit_config = {
    "requests_per_second": 10,
    "requests_per_minute": 100,
    "requests_per_hour": 5000
}

# Step 3: Validate configuration
try:
    service.validate_config(rate_limit_config)
    print("Configuration valid")
except ValueError as e:
    print(f"Invalid configuration: {e}")
    exit(1)

# Step 4: Check rate limit for authenticated user
client_identifier = service.get_client_identifier(
    client_ip="192.168.1.100",
    token="na_abc123..."
)

is_allowed, rate_info = service.check_rate_limit(
    workflow_name="premium_workflow",
    client_identifier=client_identifier,
    rate_limit_config=rate_limit_config
)

# Step 5: Get rate limit headers
headers = service.get_rate_limit_headers(
    workflow_name="premium_workflow",
    client_identifier=client_identifier,
    rate_limit_config=rate_limit_config
)

print(f"Rate limit headers: {headers}")
# Output:
# {
#     "X-RateLimit-Per-Second-Limit": "10",
#     "X-RateLimit-Per-Second-Remaining": "9",
#     "X-RateLimit-Per-Second-Reset": "1234567891",
#     "X-RateLimit-Per-Minute-Limit": "100",
#     "X-RateLimit-Per-Minute-Remaining": "99",
#     ...
# }
```

### Example 3: Complete Workflow with FastAPI

Show a realistic, complete workflow for HTTP-triggered workflow execution:

```python
from fastapi import FastAPI, Request, HTTPException, status, Header
from typing import Optional, Dict, Any
from backend.services.rate_limiting import rate_limiting_service
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.services.execution import execute_workflow

app = FastAPI()

async def execute_published_workflow(
    workflow_name: str,
    input_data: Dict[str, Any],
    client_ip: str,
    token: Optional[str]
) -> Dict[str, Any]:
    """Complete workflow execution with rate limiting."""

    # Step 1: Get published workflow configuration
    published_workflow = WorkflowPublishingService.get_published_workflow_by_identifier(
        workflow_name
    )

    if not published_workflow:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_name}' not found or not published"
        )

    # Step 2: Check rate limits (if configured)
    rate_limit_headers = {}

    if published_workflow.rate_limit:
        # Generate client identifier
        client_identifier = rate_limiting_service.get_client_identifier(
            client_ip, token
        )

        # Check rate limit
        is_allowed, rate_info = rate_limiting_service.check_rate_limit(
            workflow_name=workflow_name,
            client_identifier=client_identifier,
            rate_limit_config=published_workflow.rate_limit
        )

        if not is_allowed:
            # Rate limit exceeded - return 429
            retry_after = rate_info.get("retry_after", 60)
            reset_time = rate_info.get("reset_time")

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit_type": rate_info.get("limit_type_hit"),
                    "retry_after": retry_after,
                    "reset_time": reset_time
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Reset": str(reset_time)
                }
            )

        # Get rate limit headers for response
        rate_limit_headers = rate_limiting_service.get_rate_limit_headers(
            workflow_name, client_identifier, published_workflow.rate_limit
        )

    # Step 3: Execute workflow
    execution_result = await execute_workflow(
        workflow_name=workflow_name,
        input_data=input_data
    )

    # Step 4: Return result with rate limit headers
    return {
        "status": "success",
        "execution_id": execution_result.execution_id,
        "output": execution_result.output,
        "rate_limit_headers": rate_limit_headers
    }


@app.post("/api/http-execution/trigger/{workflow_name}")
async def trigger_workflow_endpoint(
    workflow_name: str,
    request: Request,
    input_data: Dict[str, Any],
    authorization: Optional[str] = Header(None)
):
    """HTTP endpoint for triggering published workflows with rate limiting."""

    # Extract client information
    client_ip = request.client.host
    token = authorization.replace("Bearer ", "") if authorization else None

    try:
        # Execute workflow with rate limiting
        result = await execute_published_workflow(
            workflow_name=workflow_name,
            input_data=input_data,
            client_ip=client_ip,
            token=token
        )

        return result

    except HTTPException:
        # Re-raise HTTP exceptions (including 429)
        raise
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}"
        )
```

### Example 4: Testing Usage

Show how to use this service in tests:

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.rate_limiting import (
    RateLimitingService,
    InMemoryRateLimitStorage,
    SlidingWindowStrategy,
    HybridIdentifierStrategy,
    RateLimitSettings
)

@pytest.fixture
def rate_limiting_service():
    """Create rate limiting service for testing."""
    storage = InMemoryRateLimitStorage()
    settings = RateLimitSettings(debug_logging=False)
    strategy = SlidingWindowStrategy(storage, settings)
    client_strategy = HybridIdentifierStrategy()

    return RateLimitingService(
        storage=storage,
        strategy=strategy,
        client_identifier_strategy=client_strategy,
        settings=settings
    )


def test_rate_limit_basic_usage(rate_limiting_service):
    """Test basic rate limiting functionality."""

    config = {"requests_per_minute": 10}

    # First request should be allowed
    is_allowed, info = rate_limiting_service.check_rate_limit(
        workflow_name="test_workflow",
        client_identifier="ip:192.168.1.100",
        rate_limit_config=config
    )

    assert is_allowed is True
    assert info["requests_per_minute_remaining"] == 9


def test_rate_limit_exceeded(rate_limiting_service):
    """Test rate limit exceeded scenario."""

    config = {"requests_per_minute": 2}

    # Make 2 requests (should succeed)
    for i in range(2):
        is_allowed, _ = rate_limiting_service.check_rate_limit(
            workflow_name="test_workflow",
            client_identifier="ip:192.168.1.100",
            rate_limit_config=config
        )
        assert is_allowed is True

    # Third request should be denied
    is_allowed, info = rate_limiting_service.check_rate_limit(
        workflow_name="test_workflow",
        client_identifier="ip:192.168.1.100",
        rate_limit_config=config
    )

    assert is_allowed is False
    assert info["limit_type_hit"] == "requests_per_minute"
    assert info["remaining"] == 0
    assert "retry_after" in info
    assert "reset_time" in info


def test_client_identifier_strategy(rate_limiting_service):
    """Test client identification strategies."""

    # Token-based identifier
    identifier = rate_limiting_service.get_client_identifier(
        client_ip="192.168.1.100",
        token="na_abc123"
    )
    assert identifier == "token:na_abc123"

    # IP-based identifier
    identifier = rate_limiting_service.get_client_identifier(
        client_ip="192.168.1.100",
        token=None
    )
    assert identifier == "ip:192.168.1.100"

    # Unknown identifier
    identifier = rate_limiting_service.get_client_identifier(
        client_ip=None,
        token=None
    )
    assert identifier == "unknown:client"


def test_rate_limit_headers(rate_limiting_service):
    """Test rate limit header generation."""

    config = {"requests_per_minute": 60}

    # Make a request
    rate_limiting_service.check_rate_limit(
        workflow_name="test_workflow",
        client_identifier="ip:192.168.1.100",
        rate_limit_config=config
    )

    # Get headers
    headers = rate_limiting_service.get_rate_limit_headers(
        workflow_name="test_workflow",
        client_identifier="ip:192.168.1.100",
        rate_limit_config=config
    )

    assert "X-RateLimit-Requests-Per-Minute-Limit" in headers
    assert headers["X-RateLimit-Requests-Per-Minute-Limit"] == "60"
    assert "X-RateLimit-Requests-Per-Minute-Remaining" in headers
    assert "X-RateLimit-Requests-Per-Minute-Reset" in headers


def test_config_validation(rate_limiting_service):
    """Test rate limit configuration validation."""

    # Valid config
    valid_config = {"requests_per_minute": 60}
    assert rate_limiting_service.validate_config(valid_config) is True

    # Invalid: negative limit
    with pytest.raises(ValueError, match="positive integer"):
        rate_limiting_service.validate_config({"requests_per_minute": -10})

    # Invalid: unknown limit type
    with pytest.raises(ValueError, match="Unknown rate limit type"):
        rate_limiting_service.validate_config({"unknown_type": 100})

    # Invalid: empty config
    with pytest.raises(ValueError, match="cannot be empty"):
        rate_limiting_service.validate_config({})


def test_cleanup_expired_buckets(rate_limiting_service):
    """Test bucket cleanup functionality."""

    config = {"requests_per_minute": 10}

    # Create some buckets
    rate_limiting_service.check_rate_limit(
        "workflow1", "ip:192.168.1.100", config
    )
    rate_limiting_service.check_rate_limit(
        "workflow2", "ip:192.168.1.101", config
    )

    # Check stats before cleanup
    stats = rate_limiting_service.get_storage_stats()
    assert stats["workflow_keys"] == 2

    # Cleanup with very short age (should remove nothing)
    rate_limiting_service.cleanup_expired_buckets(max_age_seconds=1)

    # Stats should be unchanged
    stats = rate_limiting_service.get_storage_stats()
    assert stats["workflow_keys"] == 2
```

---

## Performance Considerations

### Performance Characteristics

**Complexity Analysis:**

- `check_rate_limit()`: O(n) where n is the number of requests in the window (typically small, bounded by max_requests)
- `get_bucket()`: O(1) average case with hash table lookup
- `cleanup_expired_buckets()`: O(m * n) where m is number of buckets and n is requests per bucket
- `get_rate_limit_headers()`: O(k) where k is the number of rate limit types configured

**Memory Usage:**

- In-memory storage grows with number of unique workflow:client combinations
- Each bucket stores timestamps for requests within the window
- Memory usage: O(W *C* T * R) where:
  - W = number of workflows
  - C = number of clients
  - T = number of rate limit types per workflow
  - R = average requests in window

**I/O Characteristics:**

- CPU-bound: Rate limit checks are fast in-memory operations
- No I/O for in-memory storage backend
- Redis backend (if implemented) would be network I/O bound
- Thread-safe with fine-grained locking (per-bucket locks)

### Optimisation Tips

#### Tip 1: Periodic Cleanup

**Problem:**

```python
# Without cleanup, memory usage grows indefinitely
for i in range(1000000):
    client_id = f"ip:192.168.1.{i % 255}"
    rate_limiting_service.check_rate_limit(
        f"workflow_{i}", client_id, {"per_minute": 10}
    )
# Memory usage: very high (millions of buckets)
```

**Solution:**

```python
# Schedule periodic cleanup in background task
import asyncio

async def cleanup_task():
    while True:
        await asyncio.sleep(600)  # Every 10 minutes
        rate_limiting_service.cleanup_expired_buckets(
            max_age_seconds=3600  # Remove buckets older than 1 hour
        )

# Start cleanup task
asyncio.create_task(cleanup_task())
```

#### Tip 2: Configure Appropriate Time Windows

**Problem:**

```python
# Too many time windows increases memory and CPU usage
excessive_config = {
    "per_second": 10,
    "per_minute": 100,
    "per_hour": 1000,
    "per_day": 10000,
    "per_300": 500,  # Custom 5-minute window
    "per_900": 1500,  # Custom 15-minute window
}
# Each time window requires a separate bucket
```

**Solution:**

```python
# Use only necessary time windows
efficient_config = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
}
# Fewer buckets = less memory and faster checks
```

#### Tip 3: Use Appropriate Client Identification

**Problem:**

```python
# IP-only identification can be too broad for authenticated APIs
# All requests from same IP share limits (e.g., corporate proxy)
service = create_rate_limiting_service(
    client_identifier_strategy=IPOnlyIdentifierStrategy()
)

# Multiple users behind same IP hit limits quickly
for user in corporate_users:  # All from same IP
    is_allowed, _ = service.check_rate_limit(...)
    # All users share the same limit!
```

**Solution:**

```python
# Use token-based or hybrid identification for per-user limits
service = create_rate_limiting_service(
    client_identifier_strategy=HybridIdentifierStrategy()  # Default
)

# Each authenticated user gets separate limits
for user in users:
    identifier = service.get_client_identifier(
        client_ip=user.ip,
        token=user.token  # Unique per user
    )
    is_allowed, _ = service.check_rate_limit(...)
    # Each user has independent limits
```

### Async/Await Support

The rate limiting service is currently synchronous but can be used in async contexts:

```python
from backend.services.rate_limiting import rate_limiting_service
import asyncio

async def async_check_rate_limit(
    workflow_name: str,
    client_identifier: str,
    rate_limit_config: Dict[str, int]
) -> Tuple[bool, Dict[str, int]]:
    """Async wrapper for rate limit checking."""

    # Run synchronous rate limit check in thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        rate_limiting_service.check_rate_limit,
        workflow_name,
        client_identifier,
        rate_limit_config
    )

# Use in async context
async def handle_request():
    is_allowed, info = await async_check_rate_limit(
        "my_workflow",
        "ip:192.168.1.100",
        {"requests_per_minute": 60}
    )

    if is_allowed:
        # Proceed with async workflow execution
        result = await execute_async_workflow()
        return result
```

**Note:** The synchronous implementation is fast enough for most use cases. Thread-safe locking ensures correct
behaviour in async environments.

### Connection Pooling

Not applicable for in-memory storage. For future Redis implementation:

```python
# Future Redis implementation example
from backend.services.rate_limiting import (
    create_rate_limiting_service,
    RedisRateLimitStorage  # Not yet implemented
)
import redis

# Create Redis connection pool
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
    decode_responses=True
)

# Create service with Redis storage
redis_storage = RedisRateLimitStorage(pool=redis_pool)
service = create_rate_limiting_service(storage=redis_storage)
```

### Batch Operations

Not currently supported. Rate limits are checked per-request. For batch workflows:

```python
# Current approach: check limit for each item
async def process_batch(items: List[Dict], workflow_name: str):
    """Process batch with per-item rate limiting."""

    results = []

    for item in items:
        # Check rate limit for each item
        is_allowed, _ = rate_limiting_service.check_rate_limit(
            workflow_name=workflow_name,
            client_identifier=f"batch:{item['id']}",
            rate_limit_config={"requests_per_minute": 100}
        )

        if is_allowed:
            result = await process_item(item)
            results.append(result)
        else:
            results.append({"error": "rate_limit_exceeded"})

    return results
```

---

## Testing Patterns

### Unit Testing

```python
import pytest
import time
from backend.services.rate_limiting import (
    InMemoryRateLimitStorage,
    SlidingWindowStrategy,
    RateLimitSettings,
    HybridIdentifierStrategy
)

@pytest.fixture
def storage():
    """Storage fixture."""
    return InMemoryRateLimitStorage()


@pytest.fixture
def settings():
    """Settings fixture."""
    return RateLimitSettings(debug_logging=False)


@pytest.fixture
def strategy(storage, settings):
    """Strategy fixture."""
    return SlidingWindowStrategy(storage, settings)


def test_sliding_window_allows_under_limit(strategy):
    """Test that requests under limit are allowed."""

    config = {"requests_per_minute": 5}

    # Make 5 requests (all should be allowed)
    for i in range(5):
        is_allowed, info = strategy.check_limit(
            "test_workflow",
            "ip:192.168.1.100",
            config
        )

        assert is_allowed is True
        assert info["requests_per_minute_remaining"] == 4 - i


def test_sliding_window_denies_over_limit(strategy):
    """Test that requests over limit are denied."""

    config = {"requests_per_minute": 3}

    # Make 3 requests (should all be allowed)
    for _ in range(3):
        is_allowed, _ = strategy.check_limit(
            "test_workflow", "ip:192.168.1.100", config
        )
        assert is_allowed is True

    # 4th request should be denied
    is_allowed, info = strategy.check_limit(
        "test_workflow", "ip:192.168.1.100", config
    )

    assert is_allowed is False
    assert info["limit_type_hit"] == "requests_per_minute"
    assert info["remaining"] == 0
    assert "retry_after" in info


def test_storage_cleanup(storage):
    """Test storage cleanup removes old buckets."""

    # Create some buckets
    bucket1 = storage.get_bucket("workflow1:client1", "per_minute", 10, 60)
    bucket2 = storage.get_bucket("workflow2:client2", "per_minute", 10, 60)

    # Verify buckets exist
    stats = storage.get_stats()
    assert stats["workflow_keys"] == 2

    # Simulate old requests
    old_time = time.time() - 7200  # 2 hours ago
    bucket1.requests = [old_time]
    bucket2.requests = [old_time]

    # Cleanup buckets older than 1 hour
    cleaned = storage.cleanup_expired(time.time(), 3600)

    # Both buckets should be cleaned
    assert cleaned == 2

    stats = storage.get_stats()
    assert stats["workflow_keys"] == 0


def test_client_identifier_hybrid_strategy():
    """Test hybrid identification strategy."""

    strategy = HybridIdentifierStrategy()

    # Prefer token
    identifier = strategy.get_identifier("192.168.1.100", "token123")
    assert identifier == "token:token123"

    # Fall back to IP
    identifier = strategy.get_identifier("192.168.1.100", None)
    assert identifier == "ip:192.168.1.100"

    # Default for unknown
    identifier = strategy.get_identifier(None, None)
    assert identifier == "unknown:client"
```

### Mocking Dependencies

```python
from unittest.mock import Mock, patch, MagicMock
import pytest
from backend.services.rate_limiting import RateLimitingService

@pytest.fixture
def mock_storage():
    """Mock storage for testing."""
    storage = Mock()
    storage.get_bucket = MagicMock()
    storage.cleanup_expired = MagicMock(return_value=0)
    storage.get_stats = MagicMock(return_value={"workflow_keys": 0})
    return storage


@pytest.fixture
def mock_strategy():
    """Mock strategy for testing."""
    strategy = Mock()
    strategy.check_limit = MagicMock(return_value=(True, {"remaining": 10}))
    strategy.get_rate_limit_status = MagicMock(return_value={})
    return strategy


def test_service_with_mocks(mock_storage, mock_strategy):
    """Test service with mocked dependencies."""

    service = RateLimitingService(
        storage=mock_storage,
        strategy=mock_strategy
    )

    # Test check_rate_limit delegates to strategy
    is_allowed, info = service.check_rate_limit(
        "workflow", "client", {"per_minute": 10}
    )

    assert is_allowed is True
    mock_strategy.check_limit.assert_called_once_with(
        "workflow", "client", {"per_minute": 10}
    )


@patch('backend.services.rate_limiting.service.logger')
def test_service_logging(mock_logger, mock_storage, mock_strategy):
    """Test service logging with mocked logger."""

    service = RateLimitingService(
        storage=mock_storage,
        strategy=mock_strategy
    )

    # Trigger cleanup
    service.cleanup_expired_buckets()

    # Verify logger was not called (0 buckets cleaned)
    # (logger.info only called if cleaned > 0)
    mock_logger.info.assert_not_called()
```

### Integration Testing

```python
import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.services.rate_limiting import rate_limiting_service

@pytest.mark.integration
def test_rate_limiting_integration():
    """Integration test with real service."""

    # Reset service state
    rate_limiting_service.storage._buckets.clear()

    config = {"requests_per_minute": 5}
    workflow = "integration_test_workflow"
    client = "ip:192.168.1.100"

    # Make 5 requests (should all succeed)
    for i in range(5):
        is_allowed, info = rate_limiting_service.check_rate_limit(
            workflow, client, config
        )

        assert is_allowed is True

    # 6th request should fail
    is_allowed, info = rate_limiting_service.check_rate_limit(
        workflow, client, config
    )

    assert is_allowed is False
    assert "retry_after" in info

    # Get headers
    headers = rate_limiting_service.get_rate_limit_headers(
        workflow, client, config
    )

    assert "X-RateLimit-Requests-Per-Minute-Limit" in headers
    assert headers["X-RateLimit-Requests-Per-Minute-Remaining"] == "0"


@pytest.mark.integration
async def test_rate_limiting_with_api(async_client):
    """Integration test with API endpoint."""

    # Make requests to published workflow
    responses = []

    for i in range(10):
        response = await async_client.post(
            "/api/http-execution/trigger/test_workflow",
            json={"input": "test"}
        )
        responses.append(response)

    # Check that some requests succeeded
    success_count = sum(1 for r in responses if r.status_code == 200)

    # Check that some requests were rate limited
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)

    assert success_count > 0
    assert rate_limited_count > 0

    # Check rate limit headers
    for response in responses:
        if response.status_code == 200:
            assert "X-RateLimit-Requests-Per-Minute-Limit" in response.headers
```

---

## Best Practices

### Do's

✅ **Use the global singleton for convenience**

```python
from backend.services.rate_limiting import rate_limiting_service

# Simple and convenient
is_allowed, info = rate_limiting_service.check_rate_limit(
    workflow_name="my_workflow",
    client_identifier="ip:192.168.1.100",
    rate_limit_config={"requests_per_minute": 60}
)
```

✅ **Always add rate limit headers to responses**

```python
from fastapi import Response
from backend.services.rate_limiting import rate_limiting_service

@app.post("/trigger/{workflow_name}")
async def trigger_workflow(workflow_name: str, response: Response):
    # Check rate limit
    is_allowed, info = rate_limiting_service.check_rate_limit(...)

    # Add headers even if allowed
    headers = rate_limiting_service.get_rate_limit_headers(
        workflow_name, client_identifier, rate_limit_config
    )

    response.headers.update(headers)

    return {"status": "success"}
```

✅ **Validate rate limit configurations early**

```python
from backend.services.rate_limiting import rate_limiting_service

@app.post("/workflows/{id}/publish")
async def publish_workflow(id: str, config: Dict):
    # Validate rate limit config before saving
    if "rate_limit" in config:
        try:
            rate_limiting_service.validate_config(config["rate_limit"])
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid rate limit configuration: {e}"
            )

    # Save workflow...
```

✅ **Schedule periodic cleanup**

```python
import asyncio
from backend.services.rate_limiting import rate_limiting_service

async def cleanup_task():
    """Background task to clean up expired buckets."""
    while True:
        await asyncio.sleep(600)  # Every 10 minutes
        rate_limiting_service.cleanup_expired_buckets()

# Start on application startup
@app.on_event("startup")
async def startup():
    asyncio.create_task(cleanup_task())
```

✅ **Use appropriate client identification strategy**

```python
from backend.services.rate_limiting import (
    create_rate_limiting_service,
    HybridIdentifierStrategy,  # For mixed authenticated/public
    TokenOnlyIdentifierStrategy,  # For authenticated-only
    IPOnlyIdentifierStrategy  # For public-only
)

# Choose strategy based on your use case
service = create_rate_limiting_service(
    client_identifier_strategy=HybridIdentifierStrategy()  # Most flexible
)
```

✅ **Implement graceful degradation**

```python
def check_rate_limit_safe(workflow, client, config):
    """Check rate limit with error handling."""
    try:
        return rate_limiting_service.check_rate_limit(
            workflow, client, config
        )
    except Exception as e:
        logger.error(f"Rate limiting error: {e}")
        # Fail open - allow request if rate limiting fails
        return True, {"error": "rate_limiting_unavailable"}
```

### Don'ts

❌ **Don't skip rate limit headers in responses**

```python
# BAD: No feedback to clients
@app.post("/trigger/{workflow}")
async def trigger(workflow: str):
    is_allowed, _ = rate_limiting_service.check_rate_limit(...)

    if not is_allowed:
        raise HTTPException(status_code=429)

    return {"status": "success"}
    # Missing: Rate limit headers!
```

```python
# GOOD: Always include headers
@app.post("/trigger/{workflow}")
async def trigger(workflow: str, response: Response):
    is_allowed, info = rate_limiting_service.check_rate_limit(...)

    # Add headers
    headers = rate_limiting_service.get_rate_limit_headers(...)
    response.headers.update(headers)

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            headers={"Retry-After": str(info["retry_after"])}
        )

    return {"status": "success"}
```

❌ **Don't use IP-only identification for authenticated workflows**

```python
# BAD: All users from same IP share limits
service = create_rate_limiting_service(
    client_identifier_strategy=IPOnlyIdentifierStrategy()
)

# Users behind corporate proxy hit limits together
for user in corporate_users:  # All from same IP
    identifier = service.get_client_identifier(user.ip, user.token)
    # identifier is "ip:10.0.0.1" for all users!
```

```python
# GOOD: Use token-based or hybrid identification
service = create_rate_limiting_service(
    client_identifier_strategy=HybridIdentifierStrategy()
)

# Each user gets independent limits
for user in users:
    identifier = service.get_client_identifier(user.ip, user.token)
    # identifier is "token:unique_token" for each user
```

❌ **Don't configure excessive time windows**

```python
# BAD: Too many time windows waste memory
excessive_config = {
    "per_second": 10,
    "per_minute": 100,
    "per_5_minutes": 400,
    "per_15_minutes": 1000,
    "per_hour": 3000,
    "per_day": 50000,
    "per_week": 300000
}
# Each window requires separate bucket storage!
```

```python
# GOOD: Use only necessary windows
reasonable_config = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
}
# Fewer buckets = better performance
```

❌ **Don't ignore rate limit configuration validation**

```python
# BAD: Save invalid configuration
@app.post("/workflows/publish")
async def publish(workflow: Dict):
    # No validation!
    save_workflow(workflow)
    # Runtime errors when checking limits
```

```python
# GOOD: Validate before saving
@app.post("/workflows/publish")
async def publish(workflow: Dict):
    if "rate_limit" in workflow:
        try:
            rate_limiting_service.validate_config(workflow["rate_limit"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    save_workflow(workflow)
```

❌ **Don't forget periodic cleanup**

```python
# BAD: No cleanup = memory leak
# Buckets accumulate forever
# Memory usage grows unbounded
```

```python
# GOOD: Schedule cleanup
async def cleanup_task():
    while True:
        await asyncio.sleep(600)
        rate_limiting_service.cleanup_expired_buckets()

asyncio.create_task(cleanup_task())
```

---

## Related Documentation

### Related Services

- [Workflow Publishing Service](./workflow.md) - Provides rate limit configurations for published workflows
- [Authentication Service](./auth.md) - Provides tokens for client identification
- [HTTP Execution Service](../agents-guide/api/http_execution.md) - Primary consumer of rate limiting

### Related API Modules

- [HTTP Execution API](../agents-guide/api/http_execution.md) - Endpoints that enforce rate limits

### Architecture Documentation

- [Service Architecture](../architecture/services.md) - Overview of service layer patterns

### External Documentation

- [Sliding Window Algorithm](https://en.wikipedia.org/wiki/Sliding_window_protocol) - Background on sliding window
  technique
- [HTTP 429 Too Many Requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429) - Standard HTTP rate
  limiting response
- [RateLimit HTTP Headers](https://datatracker.ietf.org/doc/html/draft-ietf-httpapi-ratelimit-headers) - IETF draft for
  standard rate limit headers

---

## Summary

The rate limiting service provides comprehensive request throttling for AgenticStudio's published workflows. It implements a
sliding window algorithm for accurate rate limiting across multiple time windows, supports flexible client
identification strategies (IP-based, token-based, or hybrid), and integrates seamlessly with the HTTP execution API. The
service is designed for extensibility with pluggable storage backends and rate limiting strategies, currently providing
an efficient in-memory implementation with thread-safe operations.

The service uses the Strategy pattern extensively, allowing different implementations for rate limiting algorithms,
client identification, and storage backends. The global singleton `rate_limiting_service` provides convenient access
throughout the application, while the factory function `create_rate_limiting_service()` enables custom configurations
for testing and specialised use cases.

**Key Features:**

- Sliding window algorithm for precise rate limiting
- Multiple time window support (per-second, per-minute, per-hour, per-day, custom)
- Flexible client identification (IP, token, or hybrid)
- Standard HTTP headers for client feedback (X-RateLimit-*)
- Thread-safe in-memory storage with periodic cleanup
- Extensible architecture with strategy and storage interfaces
- Configuration validation and error handling
- Debug logging support for troubleshooting

**Primary Use Cases:**

- Protecting published workflows from abuse or excessive usage
- Implementing tiered rate limits (different limits for different time windows)
- Supporting per-user rate limiting for authenticated workflows
- Providing per-IP rate limiting for public workflows
- Enforcing API quotas and usage limits

**When to Use This Service:**

- When publishing workflows for HTTP trigger access
- When implementing API usage quotas or fair use policies
- When protecting backend resources from overload
- When providing feedback to API consumers about their usage
- When enforcing different rate limits for authenticated vs unauthenticated access
