# Execution History API Module

## Overview

The Execution History API module provides endpoints for querying and analysing workflow execution records in AgenticStudio.
It enables users to retrieve detailed information about past workflow executions, individual node executions within
workflows, and aggregated statistics for monitoring workflow performance and debugging execution issues.

**Location:** [backend/api/execution_history/](../../backend/api/execution_history/)

**Base Path:** `/api/execution-history`

**Primary Responsibilities:**

- Query graph execution history with filtering and pagination
- Retrieve detailed information about specific executions
- Access individual node execution records and metadata
- Provide execution summary statistics and performance metrics
- Support user-scoped data access for multi-tenant security
- Enable debugging and troubleshooting of workflow failures

## Architecture

### Module Structure

```
backend/api/execution_history/
├── __init__.py           # Module exports (router)
├── routes.py             # API endpoint definitions (357 lines)
├── models.py             # Pydantic response models (126 lines)
└── dependencies.py       # Authentication dependencies (42 lines)
```

**File Descriptions:**

- **routes.py**: Defines all REST endpoints for execution history queries. Contains route handlers that delegate to the
  ExecutionHistoryService for data retrieval and formatting.

- **models.py**: Pydantic response models including `NodeExecutionResponse`, `GraphExecutionResponse`, and
  `ExecutionSummaryResponse`. These models ensure consistent API response structure and automatic validation.

- **dependencies.py**: Authentication dependency injection functions. Provides `get_user_identifier()` which extracts
  the user identifier from JWT tokens for user-scoped data access.

### Design Pattern

The Execution History API follows a **service-oriented architecture**:

```
HTTP Request
    ↓
Route Handler (routes.py)
    ↓
ExecutionHistoryService (services/execution/history/)
    ↓
┌─────────────────────┬──────────────────┬────────────────┐
│                     │                  │                │
Graph Execution   Node Execution    Queries         Serialization
Module             Module           Module          Module
│                     │                  │                │
└─────────────────────┴──────────────────┴────────────────┘
    ↓
Database (PostgreSQL via SQLAlchemy ORM)
```

**Flow Explanation:**

1. **Route handlers** receive HTTP requests and extract parameters
2. **ExecutionHistoryService** provides a unified facade over execution history operations
3. **Specialized modules** handle specific concerns:
    - `graph_execution.py` - Graph execution CRUD operations
    - `node_execution.py` - Node execution tracking
    - `queries.py` - Complex queries and filtering
    - `serialization.py` - Data formatting for API responses
4. **Database layer** persists execution records using SQLAlchemy ORM models

**Benefits:**

- Route handlers remain thin and focused on HTTP concerns
- Service layer provides reusable business logic
- Modular design enables easy testing and maintenance
- Clear separation between data access and presentation

## Authentication & Authorisation

### Authentication

All endpoints require authentication via **OAuth2-Proxy** with JWT token validation.

**Required Headers:**

- Standard OAuth2-Proxy headers (injected automatically by proxy)
- JWT token in cookies or authorization header

**User Extraction Pattern:**

```python
from .dependencies import get_user_identifier

@router.get("/executions")
async def get_executions(
    user_id: str = Depends(get_user_identifier)
):
    # user_id contains the authenticated user's email or sub claim
    executions = ExecutionHistoryService.get_graph_executions_dict(
        user_id=user_id,
        limit=100
    )
    return executions
```

The `get_user_identifier()` dependency:

1. Extracts JWT claims via `get_current_user()` from the auth module
2. Attempts to extract email claim first (AIPE users)
3. Falls back to 'sub' claim (legacy Azure AD users)
4. Returns HTTP 401 if no valid identifier found

### Authorisation

**User-Scoped Data Access:**

All execution queries are automatically scoped to workflows accessible by the authenticated user. This ensures
multi-tenant data isolation.

**Authorisation Rules:**

- Users can only access executions of workflows they own or have been granted access to
- User ID filtering is enforced at the service layer
- ExecutionHistoryService queries check workflow ownership via user_id field
- Cross-user data access is prevented at the database query level

**Implementation Example:**

```python
# In routes.py - user_id is injected from authentication
@router.get("/executions")
async def get_executions(
    user_id: str = Depends(get_user_identifier)
):
    # Service layer enforces user scoping
    executions = ExecutionHistoryService.get_graph_executions_dict(
        user_id=user_id,  # Only returns user's executions
        limit=100
    )
    return executions

# In ExecutionHistoryService - queries filter by user_id
def get_graph_executions_dict(user_id: str, ...):
    # Queries automatically include WHERE user_id = :user_id
    return queries.get_user_graph_executions(user_id, ...)
```

## API Endpoints

### Execution Queries

#### `GET /api/execution-history/executions`

Retrieve a list of graph executions with optional filtering and pagination.

**Authentication:** Required

**Query Parameters:**

- `graph_id` (optional) - Filter executions by specific graph/workflow ID
- `limit` (optional) - Maximum number of results to return (default: 100, min: 1, max: 1000)
- `offset` (optional) - Number of results to skip for pagination (default: 0, min: 0)

**Request Body:** None

**Response:**

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "graph_id": "customer_support_workflow",
    "graph_name": "Customer Support AI Agent",
    "graph_definition": {
      "nodes": [...],
      "edges": [...]
    },
    "status": "completed",
    "start_time": "2025-10-21T10:30:00Z",
    "end_time": "2025-10-21T10:30:45Z",
    "duration_seconds": 45.2,
    "input_data": {
      "customer_query": "How do I reset my password?",
      "customer_id": "CUST-12345"
    },
    "output_data": {
      "response": "To reset your password, visit...",
      "confidence": 0.95
    },
    "error_message": null,
    "user_id": "user@example.com",
    "created_at": "2025-10-21T10:30:00Z",
    "node_executions": [
      {
        "id": "node_exec_001",
        "node_id": "intent_classifier",
        "node_name": "Intent Classification",
        "node_type": "AGENT",
        "execution_order": 1,
        "status": "completed",
        "start_time": "2025-10-21T10:30:01Z",
        "end_time": "2025-10-21T10:30:05Z",
        "duration_seconds": 4.1,
        "input_data": {
          "query": "How do I reset my password?"
        },
        "output_data": {
          "intent": "password_reset",
          "confidence": 0.95
        },
        "error_message": null,
        "node_metadata": {
          "model": "gpt-4",
          "tokens_used": 150
        },
        "is_sub_agent": false,
        "created_at": "2025-10-21T10:30:01Z"
      }
    ]
  }
]
```

**Use Cases:**

- View recent workflow execution history in a dashboard
- Monitor workflow activity and performance
- Filter executions for a specific workflow to analyse its behaviour
- Implement pagination for large execution histories
- Audit workflow usage and execution patterns

**Behaviour:**

- Returns executions sorted by start time (most recent first)
- Automatically filters to only include workflows accessible by the authenticated user
- Includes full graph definition and nested node executions for each result
- Pagination enables efficient handling of large execution histories
- Empty array returned if no executions match the criteria

**Validation:**

- `limit` must be between 1 and 1000 (FastAPI validates automatically)
- `offset` must be non-negative (0 or greater)
- `graph_id` validated as a string if provided

**Errors:**

- **500 Internal Server Error** - Database query failure or service error

**Example Requests:**

```bash
# Get 10 most recent executions
curl -X GET "https://api.agenticstudio.com/api/execution-history/executions?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get executions for specific workflow
curl -X GET "https://api.agenticstudio.com/api/execution-history/executions?graph_id=customer_support_workflow&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Paginate through results
curl -X GET "https://api.agenticstudio.com/api/execution-history/executions?limit=20&offset=40" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### `GET /api/execution-history/executions/{execution_id}`

Retrieve detailed information about a specific graph execution by its ID.

**Authentication:** Required

**Path Parameters:**

- `execution_id` - Graph execution identifier (database UUID or WebSocket execution ID)

**Query Parameters:** None

**Request Body:** None

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "graph_id": "data_analysis_pipeline",
  "graph_name": "Data Analysis Pipeline",
  "graph_definition": {
    "nodes": [
      {
        "id": "data_loader",
        "type": "AGENT",
        "name": "Load Data"
      },
      {
        "id": "analyzer",
        "type": "AGENT",
        "name": "Analyse Data"
      }
    ],
    "edges": [
      {
        "source": "data_loader",
        "target": "analyzer"
      }
    ]
  },
  "status": "completed",
  "start_time": "2025-10-21T14:20:00Z",
  "end_time": "2025-10-21T14:22:30Z",
  "duration_seconds": 150.3,
  "input_data": {
    "dataset_url": "https://data.example.com/sales_2025.csv",
    "analysis_type": "quarterly_trends"
  },
  "output_data": {
    "summary": "Q1 sales increased by 15%",
    "charts": ["sales_trend.png"],
    "insights": ["Peak sales in March", "New product line growing"]
  },
  "error_message": null,
  "user_id": "analyst@company.com",
  "created_at": "2025-10-21T14:20:00Z",
  "node_executions": [
    {
      "id": "node_exec_100",
      "node_id": "data_loader",
      "node_name": "Load Data",
      "node_type": "AGENT",
      "execution_order": 1,
      "status": "completed",
      "start_time": "2025-10-21T14:20:05Z",
      "end_time": "2025-10-21T14:20:30Z",
      "duration_seconds": 25.1,
      "input_data": {
        "dataset_url": "https://data.example.com/sales_2025.csv"
      },
      "output_data": {
        "rows_loaded": 15000,
        "columns": ["date", "product", "sales", "region"]
      },
      "error_message": null,
      "node_metadata": {
        "file_size_mb": 2.5
      },
      "is_sub_agent": false,
      "created_at": "2025-10-21T14:20:05Z"
    },
    {
      "id": "node_exec_101",
      "node_id": "analyzer",
      "node_name": "Analyse Data",
      "node_type": "AGENT",
      "execution_order": 2,
      "status": "completed",
      "start_time": "2025-10-21T14:20:31Z",
      "end_time": "2025-10-21T14:22:30Z",
      "duration_seconds": 119.2,
      "input_data": {
        "data_summary": {
          "rows": 15000,
          "columns": 4
        }
      },
      "output_data": {
        "trends": ["Q1 growth: 15%"],
        "anomalies": []
      },
      "error_message": null,
      "node_metadata": {
        "model": "gpt-4o",
        "tokens_used": 3500
      },
      "is_sub_agent": false,
      "created_at": "2025-10-21T14:20:31Z"
    }
  ]
}
```

**Use Cases:**

- Debug a specific workflow execution failure
- Inspect detailed node execution data for troubleshooting
- Retrieve execution results after workflow completion
- Analyse execution performance for optimization
- Display execution details in a monitoring dashboard

**Behaviour:**

- Supports lookup by database UUID (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- Also supports lookup by WebSocket execution ID (e.g., `exec_12345`)
- Returns full execution details including all nested node executions
- Node executions are ordered by `execution_order` field
- Includes complete graph definition for context
- Returns `null` values for fields not applicable to the execution

**Validation:**

- `execution_id` must be a valid UUID or WebSocket ID format
- No user-scoping validation (any authenticated user can view any execution - consider adding authorisation)

**Errors:**

- **404 Not Found** - Execution with the specified ID does not exist
- **500 Internal Server Error** - Database query failure

**Special Considerations:**

- MCP_SERVER nodes are logged separately for debugging MCP tool executions
- DATABASE_QUERY nodes receive detailed logging of query operations
- Large output_data fields may be truncated in logs but returned in full via API

**Example Requests:**

```bash
# Get execution by UUID
curl -X GET "https://api.agenticstudio.com/api/execution-history/executions/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get execution by WebSocket ID
curl -X GET "https://api.agenticstudio.com/api/execution-history/executions/exec_12345" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### `GET /api/execution-history/executions/{execution_id}/nodes/{node_id}`

Retrieve detailed information about a specific node execution within a graph execution.

**Authentication:** Required

**Path Parameters:**

- `execution_id` - Graph execution identifier (UUID or WebSocket ID)
- `node_id` - Node identifier from the graph definition

**Query Parameters:** None

**Request Body:** None

**Response:**

```json
{
  "id": "node_exec_250",
  "node_id": "sentiment_analyzer",
  "node_name": "Sentiment Analysis",
  "node_type": "AGENT",
  "execution_order": 3,
  "status": "completed",
  "start_time": "2025-10-21T15:10:20Z",
  "end_time": "2025-10-21T15:10:25Z",
  "duration_seconds": 5.3,
  "input_data": {
    "text": "The customer service was excellent and very helpful!",
    "language": "en"
  },
  "output_data": {
    "sentiment": "positive",
    "confidence": 0.92,
    "emotions": {
      "joy": 0.85,
      "trust": 0.78,
      "satisfaction": 0.88
    }
  },
  "error_message": null,
  "node_metadata": {
    "model": "gpt-4",
    "temperature": 0.3,
    "max_tokens": 500,
    "tokens_used": 87
  },
  "is_sub_agent": false,
  "created_at": "2025-10-21T15:10:20Z"
}
```

**Use Cases:**

- Debug a specific node within a workflow execution
- Retrieve detailed input/output data for a particular step
- Inspect node-specific metadata (model settings, tokens used, etc.)
- Analyse performance of individual workflow steps
- Troubleshoot data transformation issues between nodes

**Behaviour:**

- Returns detailed node execution record including all metadata
- Includes complete input_data and output_data for the node
- Node metadata contains node-specific configuration and runtime info
- `is_sub_agent` flag indicates if this was executed as a delegated sub-agent
- Returns exact data as it was at execution time

**Validation:**

- `execution_id` must reference an existing graph execution
- `node_id` must reference a node within that execution
- Both parameters are validated as non-empty strings

**Errors:**

- **404 Not Found** - Node execution not found (execution_id or node_id invalid)
- **500 Internal Server Error** - Database query failure

**Special Considerations:**

- DATABASE_QUERY nodes receive enhanced logging with query details
- MCP_SERVER nodes include tool execution information in output_data
- Large input/output data is preserved in database and returned in full
- Sub-agent nodes (is_sub_agent=true) may have parent_agent_id in metadata

**Example Requests:**

```bash
# Get specific node execution
curl -X GET "https://api.agenticstudio.com/api/execution-history/executions/exec_12345/nodes/sentiment_analyzer" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get node by UUID execution
curl -X GET "https://api.agenticstudio.com/api/execution-history/executions/550e8400-e29b-41d4-a716-446655440000/nodes/data_loader" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Statistics & Analytics

#### `GET /api/execution-history/graphs/{graph_id}/summary`

Retrieve aggregated execution statistics and performance metrics for a specific graph/workflow.

**Authentication:** Required

**Path Parameters:**

- `graph_id` - Graph/workflow identifier

**Query Parameters:** None

**Request Body:** None

**Response:**

```json
{
  "graph_id": "email_classifier_workflow",
  "total_executions": 1247,
  "successful_executions": 1189,
  "failed_executions": 58,
  "average_duration_seconds": 3.8,
  "min_duration_seconds": 1.2,
  "max_duration_seconds": 45.6,
  "last_execution_time": "2025-10-21T16:45:30Z",
  "last_execution_status": "completed"
}
```

**Empty Summary Response** (when no executions exist):

```json
{
  "graph_id": "new_workflow",
  "total_executions": 0,
  "successful_executions": 0,
  "failed_executions": 0,
  "average_duration_seconds": null,
  "min_duration_seconds": null,
  "max_duration_seconds": null,
  "last_execution_time": null,
  "last_execution_status": null
}
```

**Use Cases:**

- Monitor workflow health and success rates
- Identify performance degradation or anomalies
- Display workflow statistics in monitoring dashboards
- Track workflow reliability over time
- Calculate SLAs and performance metrics
- Identify workflows that need optimization

**Behaviour:**

- Calculates aggregate statistics from all executions of the specified graph
- Returns empty summary (zeros and nulls) if no executions exist
- Success/failure counts based on execution status field
- Duration statistics calculated from completed executions only
- Last execution information provides most recent execution details
- Statistics are computed in real-time from the database

**Validation:**

- `graph_id` must be a valid string identifier
- No user-scoping enforced (returns stats for all users' executions of this graph)

**Errors:**

- **500 Internal Server Error** - Database query failure or calculation error

**Special Considerations:**

- Statistics include all historical executions (no time filtering)
- Failed executions may include error states: "failed", "error", "cancelled"
- Duration statistics exclude executions that haven't completed
- Consider caching summary data for high-traffic workflows

**Example Requests:**

```bash
# Get workflow summary statistics
curl -X GET "https://api.agenticstudio.com/api/execution-history/graphs/email_classifier_workflow/summary" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check if new workflow has executions
curl -X GET "https://api.agenticstudio.com/api/execution-history/graphs/new_experimental_workflow/summary" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Management Operations

#### `DELETE /api/execution-history/executions/{execution_id}`

Delete an execution and all its associated data.

**Authentication:** Required

**Path Parameters:**

- `execution_id` - Execution ID to delete

**Query Parameters:** None

**Request Body:** None

**Response:**

```json
{
  "detail": "Delete functionality not implemented yet"
}
```

**Use Cases:**

- Remove sensitive or obsolete execution records
- Comply with data retention policies
- Clean up test executions

**Behaviour:**

- **Currently not implemented** - Returns 501 Not Implemented
- Planned to include cascade deletion of associated data
- Will require authorisation checks (user must own the workflow)
- Future implementation will include audit logging

**Errors:**

- **501 Not Implemented** - This endpoint is not yet functional

**Future Implementation Plans:**

- Cascade deletion of node executions
- Deletion of associated metadata and logs
- Audit logging for compliance
- Consideration of soft delete vs hard delete strategy
- User authorisation checks

**Example Requests:**

```bash
# Attempt to delete execution (currently returns 501)
curl -X DELETE "https://api.agenticstudio.com/api/execution-history/executions/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Error Handling

### Error Response Format

All errors follow FastAPI's standard error response format:

```json
{
  "detail": "Execution not found"
}
```

For validation errors (e.g., invalid query parameters):

```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is less than or equal to 1000",
      "type": "value_error.number.not_le"
    }
  ]
}
```

### Common Error Codes

#### 401 Unauthorized

**When it occurs:**

- JWT token is missing or invalid
- User identifier cannot be extracted from token
- Authentication headers are missing

**Example:**

```json
{
  "detail": "Token missing user identifier"
}
```

**Resolution:**

- Ensure valid JWT token is included in request
- Verify token contains 'email' or 'sub' claim
- Check OAuth2-Proxy configuration

---

#### 404 Not Found

**When it occurs:**

- Execution ID does not exist in database
- Node execution not found for given execution_id/node_id pair
- Invalid UUID or WebSocket execution ID format

**Examples:**

```json
{
  "detail": "Execution not found"
}
```

```json
{
  "detail": "Node execution not found"
}
```

**Resolution:**

- Verify execution ID is correct
- Check if execution was created successfully
- Ensure node_id matches graph definition

---

#### 422 Unprocessable Entity

**When it occurs:**

- Query parameter validation failure
- Invalid data types for parameters
- Constraint violations (e.g., limit > 1000)

**Example:**

```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is less than or equal to 1000",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**Resolution:**

- Ensure limit is between 1 and 1000
- Ensure offset is non-negative
- Verify all parameters have correct types

---

#### 500 Internal Server Error

**When it occurs:**

- Database connection failures
- Service layer exceptions
- Unexpected runtime errors

**Example:**

```json
{
  "detail": "Database connection failed"
}
```

**Resolution:**

- Check database connectivity
- Review server logs for stack traces
- Verify database schema is up-to-date
- Check for data serialization issues

---

#### 501 Not Implemented

**When it occurs:**

- DELETE endpoint called (not yet implemented)

**Example:**

```json
{
  "detail": "Delete functionality not implemented yet"
}
```

**Resolution:**

- Use alternative cleanup methods
- Wait for future implementation
- Contact development team for timeline

### Error Handling Example

**Python Example with Error Handling:**

```python
import requests
from typing import Optional, Dict, Any, List

class ExecutionHistoryClient:
    """Client for interacting with Execution History API."""

    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {auth_token}"}

    def get_executions(
        self,
        graph_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get execution history with error handling.

        Args:
            graph_id: Optional filter by graph ID
            limit: Maximum results (1-1000)
            offset: Pagination offset

        Returns:
            List of execution dictionaries

        Raises:
            ValueError: For invalid parameters
            requests.HTTPError: For API errors
        """
        # Validate parameters
        if not (1 <= limit <= 1000):
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        # Build request
        url = f"{self.base_url}/api/execution-history/executions"
        params = {"limit": limit, "offset": offset}
        if graph_id:
            params["graph_id"] = graph_id

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise Exception("Authentication failed - check your token")
            elif e.response.status_code == 500:
                error_detail = e.response.json().get("detail", "Unknown error")
                raise Exception(f"Server error: {error_detail}")
            else:
                raise

        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get specific execution with error handling.

        Args:
            execution_id: Execution UUID or WebSocket ID

        Returns:
            Execution dictionary or None if not found
        """
        url = f"{self.base_url}/api/execution-history/executions/{execution_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_graph_summary(self, graph_id: str) -> Dict[str, Any]:
        """Get execution summary for a graph.

        Args:
            graph_id: Graph identifier

        Returns:
            Summary statistics dictionary
        """
        url = f"{self.base_url}/api/execution-history/graphs/{graph_id}/summary"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                # Return empty summary on server error
                return {
                    "graph_id": graph_id,
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "average_duration_seconds": None,
                    "min_duration_seconds": None,
                    "max_duration_seconds": None,
                    "last_execution_time": None,
                    "last_execution_status": None,
                }
            raise


# Usage example
if __name__ == "__main__":
    client = ExecutionHistoryClient(
        base_url="https://api.agenticstudio.com",
        auth_token="your_jwt_token_here"
    )

    try:
        # Get recent executions
        executions = client.get_executions(limit=10)
        print(f"Found {len(executions)} executions")

        # Get specific execution
        if executions:
            exec_id = executions[0]["id"]
            details = client.get_execution(exec_id)
            if details:
                print(f"Execution status: {details['status']}")

        # Get workflow summary
        summary = client.get_graph_summary("customer_support_workflow")
        print(f"Total executions: {summary['total_executions']}")
        print(f"Success rate: {summary['successful_executions'] / summary['total_executions'] * 100:.1f}%")

    except Exception as e:
        print(f"Error: {str(e)}")
```

## Integration with Services Layer

### Dependency Flow

```
Route Handler (routes.py)
    ↓
ExecutionHistoryService (facade)
    ↓
┌───────────────────┬─────────────────┬──────────────┬─────────────────┐
│                   │                 │              │                 │
graph_execution.py  node_execution.py queries.py   serialization.py
│                   │                 │              │                 │
└───────────────────┴─────────────────┴──────────────┴─────────────────┘
    ↓
SQLAlchemy ORM Models
    ↓
PostgreSQL Database
```

### Example Integration

**Route Handler → Service:**

```python
# In routes.py
from ...services.execution.history import ExecutionHistoryService

@router.get("/executions")
async def get_executions(
    graph_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_user_identifier),
):
    """Get execution history."""
    try:
        # Delegate to service layer
        executions = ExecutionHistoryService.get_graph_executions_dict(
            graph_id=graph_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return executions

    except Exception as e:
        logger.error(f"Failed to get executions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Service Layer → Database:**

```python
# In services/execution/history/service.py
class ExecutionHistoryService:
    """Facade for execution history operations."""

    @staticmethod
    def get_graph_executions_dict(
        graph_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ):
        """Get graph executions as dictionaries."""
        # Delegate to queries module
        return queries.get_user_graph_executions_dict(
            graph_id=graph_id,
            user_id=user_id,
            limit=limit,
            offset=offset
        )
```

**Queries Module → ORM:**

```python
# In services/execution/history/queries.py
from ....models.graph_execution import GraphExecution
from sqlalchemy import select

def get_user_graph_executions_dict(
    user_id: str,
    graph_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Query database for user's graph executions."""
    query = (
        select(GraphExecution)
        .filter(GraphExecution.user_id == user_id)
        .order_by(GraphExecution.start_time.desc())
        .limit(limit)
        .offset(offset)
    )

    if graph_id:
        query = query.filter(GraphExecution.graph_id == graph_id)

    results = session.execute(query).scalars().all()

    # Convert ORM objects to dictionaries
    return [serialize_graph_execution(exec) for exec in results]
```

### Services Used

The Execution History API depends on the following services:

#### ExecutionHistoryService

**Location:** [backend/services/execution/history/](../../backend/services/execution/history/)

**Purpose:** Primary service facade for all execution history operations. Provides a unified interface for creating,
updating, and querying execution records.

**Key Methods:**

- `create_graph_execution()` - Create new graph execution record
- `update_graph_execution()` - Update execution status and results
- `get_graph_execution()` - Retrieve single execution with node executions
- `get_graph_executions_dict()` - Query multiple executions as dictionaries
- `get_node_execution()` - Retrieve specific node execution
- `get_execution_summary()` - Calculate aggregate statistics

**Modules:**

- `graph_execution.py` - Graph execution CRUD operations
- `node_execution.py` - Node execution tracking
- `queries.py` - Complex database queries and filtering
- `serialization.py` - ORM to dictionary conversion

#### DatabaseService

**Location:** [backend/services/database/](../../backend/services/database/)

**Purpose:** Provides database session management and SQLAlchemy ORM models.

**Key Responsibilities:**

- Database connection pooling
- Session lifecycle management
- ORM model definitions (GraphExecution, NodeExecution)
- Migration management

#### ConfigService

**Location:** [backend/services/config.py](../../backend/services/config.py)

**Purpose:** Provides logging configuration and application settings.

**Key Methods:**

- `get_logger()` - Create configured logger instances with consistent formatting

## Usage Examples

### Complete Execution History Workflow Example

**Scenario:** Build a workflow monitoring dashboard that displays execution history, detailed execution information, and
performance statistics.

**Python Example:**

```python
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime

class WorkflowMonitor:
    """Client for monitoring workflow executions via Execution History API."""

    def __init__(self, base_url: str, auth_token: str):
        """Initialize monitor client.

        Args:
            base_url: Base URL of AgenticStudio API
            auth_token: JWT authentication token
        """
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {auth_token}"}

    def get_recent_executions(
        self,
        graph_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Fetch recent workflow executions.

        Args:
            graph_id: Optional filter for specific workflow
            limit: Number of executions to retrieve

        Returns:
            List of execution records
        """
        url = f"{self.base_url}/api/execution-history/executions"
        params = {"limit": limit}

        if graph_id:
            params["graph_id"] = graph_id

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def analyse_execution_details(self, execution_id: str) -> Dict[str, Any]:
        """Analyse detailed execution information.

        Args:
            execution_id: Execution to analyse

        Returns:
            Analysis results with execution details
        """
        # Get full execution details
        url = f"{self.base_url}/api/execution-history/executions/{execution_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        execution = response.json()

        # Analyse node executions
        node_stats = {
            "total_nodes": len(execution["node_executions"]),
            "completed": 0,
            "failed": 0,
            "slowest_node": None,
            "max_duration": 0
        }

        for node in execution["node_executions"]:
            if node["status"] == "completed":
                node_stats["completed"] += 1
            elif node["status"] == "failed":
                node_stats["failed"] += 1

            duration = node.get("duration_seconds", 0)
            if duration and duration > node_stats["max_duration"]:
                node_stats["max_duration"] = duration
                node_stats["slowest_node"] = node["node_name"]

        return {
            "execution_id": execution_id,
            "status": execution["status"],
            "total_duration": execution.get("duration_seconds"),
            "node_statistics": node_stats,
            "input_summary": list(execution.get("input_data", {}).keys()),
            "output_summary": list(execution.get("output_data", {}).keys())
        }

    def get_workflow_health(self, graph_id: str) -> Dict[str, Any]:
        """Get health metrics for a workflow.

        Args:
            graph_id: Workflow to analyse

        Returns:
            Health metrics and recommendations
        """
        # Get summary statistics
        url = f"{self.base_url}/api/execution-history/graphs/{graph_id}/summary"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        summary = response.json()

        # Calculate health score
        if summary["total_executions"] == 0:
            return {
                "graph_id": graph_id,
                "health_score": "unknown",
                "message": "No execution history available"
            }

        success_rate = (
            summary["successful_executions"] / summary["total_executions"] * 100
        )

        # Determine health status
        if success_rate >= 95:
            health = "healthy"
        elif success_rate >= 80:
            health = "warning"
        else:
            health = "critical"

        return {
            "graph_id": graph_id,
            "health_score": health,
            "success_rate": round(success_rate, 2),
            "total_executions": summary["total_executions"],
            "failed_executions": summary["failed_executions"],
            "avg_duration": summary["average_duration_seconds"],
            "last_execution": {
                "time": summary["last_execution_time"],
                "status": summary["last_execution_status"]
            },
            "recommendations": self._generate_recommendations(summary, success_rate)
        }

    def _generate_recommendations(
        self,
        summary: Dict[str, Any],
        success_rate: float
    ) -> List[str]:
        """Generate recommendations based on workflow statistics."""
        recommendations = []

        if success_rate < 95:
            recommendations.append(
                f"Success rate is {success_rate:.1f}%. "
                "Investigate recent failures to improve reliability."
            )

        if summary["average_duration_seconds"] and summary["average_duration_seconds"] > 30:
            recommendations.append(
                f"Average duration is {summary['average_duration_seconds']:.1f}s. "
                "Consider optimizing workflow performance."
            )

        if summary["max_duration_seconds"] and summary["min_duration_seconds"]:
            variance = summary["max_duration_seconds"] - summary["min_duration_seconds"]
            if variance > 60:
                recommendations.append(
                    "High duration variance detected. "
                    "Check for inconsistent data sizes or external API delays."
                )

        return recommendations

    def investigate_failed_execution(self, execution_id: str) -> Dict[str, Any]:
        """Deep dive into a failed execution.

        Args:
            execution_id: Failed execution to investigate

        Returns:
            Failure analysis with root cause
        """
        url = f"{self.base_url}/api/execution-history/executions/{execution_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        execution = response.json()

        if execution["status"] != "failed":
            return {"message": "Execution did not fail"}

        # Find failed nodes
        failed_nodes = [
            node for node in execution["node_executions"]
            if node["status"] == "failed"
        ]

        # Analyse failure
        failure_info = {
            "execution_id": execution_id,
            "execution_error": execution.get("error_message"),
            "failed_nodes": [],
            "failure_point": None
        }

        for node in failed_nodes:
            node_info = {
                "node_id": node["node_id"],
                "node_name": node["node_name"],
                "node_type": node["node_type"],
                "error": node.get("error_message"),
                "execution_order": node["execution_order"]
            }
            failure_info["failed_nodes"].append(node_info)

            # Identify first failure point
            if (failure_info["failure_point"] is None or
                node["execution_order"] < failure_info["failure_point"]["execution_order"]):
                failure_info["failure_point"] = node_info

        return failure_info

    def compare_executions(
        self,
        execution_id_1: str,
        execution_id_2: str
    ) -> Dict[str, Any]:
        """Compare two executions of the same workflow.

        Args:
            execution_id_1: First execution
            execution_id_2: Second execution

        Returns:
            Comparison analysis
        """
        # Fetch both executions
        exec1 = requests.get(
            f"{self.base_url}/api/execution-history/executions/{execution_id_1}",
            headers=self.headers
        ).json()

        exec2 = requests.get(
            f"{self.base_url}/api/execution-history/executions/{execution_id_2}",
            headers=self.headers
        ).json()

        comparison = {
            "graph_id": exec1["graph_id"],
            "executions": {
                "execution_1": {
                    "id": execution_id_1,
                    "status": exec1["status"],
                    "duration": exec1.get("duration_seconds"),
                    "node_count": len(exec1["node_executions"])
                },
                "execution_2": {
                    "id": execution_id_2,
                    "status": exec2["status"],
                    "duration": exec2.get("duration_seconds"),
                    "node_count": len(exec2["node_executions"])
                }
            },
            "differences": []
        }

        # Compare durations
        if exec1.get("duration_seconds") and exec2.get("duration_seconds"):
            duration_diff = abs(
                exec1["duration_seconds"] - exec2["duration_seconds"]
            )
            if duration_diff > 5:
                comparison["differences"].append(
                    f"Duration difference: {duration_diff:.1f}s"
                )

        # Compare statuses
        if exec1["status"] != exec2["status"]:
            comparison["differences"].append(
                f"Different statuses: {exec1['status']} vs {exec2['status']}"
            )

        return comparison


# Example usage
if __name__ == "__main__":
    monitor = WorkflowMonitor(
        base_url="https://api.agenticstudio.com",
        auth_token="your_jwt_token_here"
    )

    # Monitor recent workflow activity
    print("=== Recent Executions ===")
    recent = monitor.get_recent_executions(limit=5)
    for exec in recent:
        print(f"{exec['graph_name']}: {exec['status']} "
              f"({exec.get('duration_seconds', 0):.1f}s)")

    # Check workflow health
    print("\n=== Workflow Health ===")
    health = monitor.get_workflow_health("customer_support_workflow")
    print(f"Status: {health['health_score']}")
    print(f"Success Rate: {health['success_rate']}%")
    for rec in health.get("recommendations", []):
        print(f"  - {rec}")

    # Analyse specific execution
    if recent:
        exec_id = recent[0]["id"]
        print(f"\n=== Analysing Execution {exec_id} ===")
        analysis = monitor.analyse_execution_details(exec_id)
        print(f"Total Duration: {analysis['total_duration']:.1f}s")
        print(f"Nodes: {analysis['node_statistics']['total_nodes']}")
        print(f"Slowest: {analysis['node_statistics']['slowest_node']} "
              f"({analysis['node_statistics']['max_duration']:.1f}s)")

    # Investigate failures
    failed_execs = [e for e in recent if e["status"] == "failed"]
    if failed_execs:
        print(f"\n=== Investigating Failure ===")
        failure = monitor.investigate_failed_execution(failed_execs[0]["id"])
        print(f"Failed at: {failure['failure_point']['node_name']}")
        print(f"Error: {failure['failure_point']['error']}")
```

**JavaScript/TypeScript Example:**

```typescript
import axios, { AxiosInstance } from 'axios';

interface ExecutionSummary {
  graph_id: string;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  average_duration_seconds: number | null;
  last_execution_time: string | null;
  last_execution_status: string | null;
}

interface NodeExecution {
  id: string;
  node_id: string;
  node_name: string;
  node_type: string;
  status: string;
  duration_seconds: number | null;
  error_message: string | null;
}

interface GraphExecution {
  id: string;
  graph_id: string;
  graph_name: string;
  status: string;
  duration_seconds: number | null;
  node_executions: NodeExecution[];
}

class ExecutionHistoryAPI {
  private client: AxiosInstance;

  constructor(baseURL: string, authToken: string) {
    this.client = axios.create({
      baseURL,
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
  }

  async getRecentExecutions(
    graphId?: string,
    limit: number = 20
  ): Promise<GraphExecution[]> {
    const response = await this.client.get('/api/execution-history/executions', {
      params: { graph_id: graphId, limit }
    });
    return response.data;
  }

  async getExecutionDetails(executionId: string): Promise<GraphExecution> {
    const response = await this.client.get(
      `/api/execution-history/executions/${executionId}`
    );
    return response.data;
  }

  async getGraphSummary(graphId: string): Promise<ExecutionSummary> {
    const response = await this.client.get(
      `/api/execution-history/graphs/${graphId}/summary`
    );
    return response.data;
  }

  async getNodeExecution(
    executionId: string,
    nodeId: string
  ): Promise<NodeExecution> {
    const response = await this.client.get(
      `/api/execution-history/executions/${executionId}/nodes/${nodeId}`
    );
    return response.data;
  }

  // Calculate workflow health score
  async calculateHealth(graphId: string): Promise<{
    score: number;
    status: 'healthy' | 'warning' | 'critical';
    metrics: ExecutionSummary;
  }> {
    const summary = await this.getGraphSummary(graphId);

    if (summary.total_executions === 0) {
      return { score: 0, status: 'warning', metrics: summary };
    }

    const successRate =
      (summary.successful_executions / summary.total_executions) * 100;

    let status: 'healthy' | 'warning' | 'critical';
    if (successRate >= 95) {
      status = 'healthy';
    } else if (successRate >= 80) {
      status = 'warning';
    } else {
      status = 'critical';
    }

    return { score: successRate, status, metrics: summary };
  }
}

// Usage example
async function monitorWorkflows() {
  const api = new ExecutionHistoryAPI(
    'https://api.agenticstudio.com',
    'your_jwt_token_here'
  );

  try {
    // Get recent executions
    const executions = await api.getRecentExecutions(undefined, 10);
    console.log(`Found ${executions.length} recent executions`);

    // Check health for each workflow
    const workflows = new Set(executions.map(e => e.graph_id));
    for (const graphId of workflows) {
      const health = await api.calculateHealth(graphId);
      console.log(`${graphId}: ${health.status} (${health.score.toFixed(1)}%)`);
    }

    // Analyse failed executions
    const failed = executions.filter(e => e.status === 'failed');
    for (const exec of failed) {
      const details = await api.getExecutionDetails(exec.id);
      const failedNodes = details.node_executions.filter(
        n => n.status === 'failed'
      );
      console.log(`Failed execution ${exec.id}:`);
      failedNodes.forEach(node => {
        console.log(`  - ${node.node_name}: ${node.error_message}`);
      });
    }

  } catch (error) {
    console.error('Monitoring error:', error);
  }
}

monitorWorkflows();
```

## Performance Considerations

### Endpoint Performance

Endpoints are categorised by typical response time:

#### Fast Endpoints (< 100ms)

- `GET /api/execution-history/executions/{execution_id}/nodes/{node_id}`
  - Single database query with indexed lookup
  - Returns single node execution record
  - Minimal data serialization

- `GET /api/execution-history/graphs/{graph_id}/summary`
  - Aggregation query with database-level calculation
  - Returns pre-computed summary statistics
  - Consider caching for high-traffic workflows

#### Medium Endpoints (100ms - 1s)

- `GET /api/execution-history/executions/{execution_id}`
  - Single execution query with joined node executions
  - Data volume depends on number of nodes
  - Eager loading of relationships reduces query count

#### Potentially Slow Endpoints (> 1s)

- `GET /api/execution-history/executions` (with large result sets)
  - Multiple execution records with nested node executions
  - Performance depends on limit parameter
  - Large offsets can slow down queries
  - User-scoped filtering reduces result set

### Optimisation Tips

#### Use Pagination Effectively

**Good Pattern** - Small, manageable page sizes:

```python
# Fetch executions in small chunks
page_size = 20
executions = []

for page in range(5):
    chunk = client.get_executions(limit=page_size, offset=page * page_size)
    executions.extend(chunk)
    if len(chunk) < page_size:
        break  # No more results
```

**Bad Pattern** - Large result sets without pagination:

```python
# This can be very slow and memory-intensive
all_executions = client.get_executions(limit=1000)  # Avoid large limits
```

#### Filter by Graph ID

**Good Pattern** - Narrow queries with graph_id filter:

```python
# Fast - filtered query
support_execs = client.get_executions(
    graph_id="customer_support_workflow",
    limit=50
)
```

**Bad Pattern** - Retrieve all executions then filter in application:

```python
# Slow - transfers unnecessary data
all_execs = client.get_executions(limit=500)
support_execs = [e for e in all_execs if e["graph_id"] == "customer_support_workflow"]
```

#### Cache Summary Statistics

**Good Pattern** - Cache workflow summaries:

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedMonitor:
    def __init__(self, client):
        self.client = client
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)

    def get_graph_summary(self, graph_id: str):
        """Get summary with 5-minute cache."""
        now = datetime.now()

        if graph_id in self.cache:
            cached_time, data = self.cache[graph_id]
            if now - cached_time < self.cache_ttl:
                return data

        # Fetch fresh data
        summary = self.client.get_graph_summary(graph_id)
        self.cache[graph_id] = (now, summary)
        return summary
```

**Bad Pattern** - Repeated summary queries:

```python
# Inefficient - queries database every time
for i in range(10):
    summary = client.get_graph_summary("my_workflow")
    print(summary["total_executions"])
```

#### Avoid Deep Pagination

**Good Pattern** - Use time-based filtering instead of deep offsets:

```python
# Efficient - time-based filtering (if supported in future)
recent_execs = client.get_executions(
    since="2025-10-20T00:00:00Z",
    limit=100
)
```

**Bad Pattern** - Deep offset pagination:

```python
# Slow - database must scan and skip many rows
page_50 = client.get_executions(limit=20, offset=1000)
```

#### Batch Node Execution Queries

**Good Pattern** - Get full execution with all nodes in one call:

```python
# Efficient - single request with all node data
execution = client.get_execution(exec_id)
for node in execution["node_executions"]:
    process_node(node)
```

**Bad Pattern** - Individual node queries:

```python
# Inefficient - N+1 queries
execution = client.get_execution(exec_id)
for node_id in get_node_ids(execution):
    node = client.get_node_execution(exec_id, node_id)  # Separate query each time
    process_node(node)
```

## Related Documentation

### Architecture Documentation

- [Backend Architecture Overview](../architecture/backend.md) - Overall backend structure and design patterns
- [Service Layer Documentation](../architecture/services.md) - Service architecture and module organisation
- [Database Schema](../architecture/database_schema.md) - Execution history table structure and relationships

### Related API Modules

- [Graph API](../graph/graph.md) - Workflow creation and management (creates executions)
- [Execution API](../../../backend/api/execution/execution.md) - Workflow execution endpoints (populates history)
- [HTTP Execution API](../http_execution/http_execution.md) - Streaming execution with SSE
- [WebSocket API](../websocket/websocket.md) - Real-time execution monitoring

### Service Documentation

- [Execution History Service](../services/execution_history.md) - Detailed service layer documentation
- [Workflow Executor Service](../services/workflow_executor.md) - How executions are created and tracked
- [Database Service](../../services/database.md) - ORM models and database access patterns

### Development Guides

- [API Development Guide](../development/api_development.md) - Guidelines for extending the API
- [Testing Guide](../development/testing.md) - How to test execution history endpoints
- [Database Migrations](../development/migrations.md) - Managing schema changes

## Summary

The Execution History API module is a critical component of AgenticStudio's observability and debugging infrastructure. It
provides comprehensive access to historical workflow execution data, enabling users to monitor workflow health, debug
failures, and analyse performance trends.

The module follows a clean service-oriented architecture where thin route handlers delegate to a modular
ExecutionHistoryService, which in turn coordinates specialised modules for graph executions, node executions, queries,
and serialization. This design promotes code reuse, testability, and maintainability while keeping the API layer focused
on HTTP concerns.

All endpoints enforce user-scoped data access through JWT authentication and user ID filtering, ensuring multi-tenant
security. The API supports flexible querying with pagination, filtering by workflow, and detailed drill-down into
individual executions and node executions.

**Key Features:**

- User-scoped execution history queries with pagination
- Detailed graph and node execution retrieval
- Aggregated summary statistics for workflow monitoring
- Support for both UUID and WebSocket execution ID lookups
- Comprehensive error handling with meaningful error messages
- Integration with ExecutionHistoryService for consistent data access
- Real-time execution tracking and status monitoring

**Primary Use Cases:**

- Monitoring workflow execution health and success rates
- Debugging failed workflow executions and identifying root causes
- Analysing workflow performance and identifying bottlenecks
- Auditing workflow usage and execution patterns
- Building execution dashboards and monitoring tools
- Investigating execution history for compliance and troubleshooting
