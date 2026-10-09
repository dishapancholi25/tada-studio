# BUG-5624: Custom Word Template Upload Fails with JSON Parsing Error

## Summary

Uploading a valid `.docx` custom Word template in the File Write Tool → Templates tab
failed with a 500 Internal Server Error. The browser displayed:

```
Unexpected token 'I', "Internal S"... is not valid JSON
```

because the frontend tried to `response.json()` on an HTML error page returned by
the server.

## Root Cause

`backend/api/graph/handlers/template_upload.py` contained three bugs that caused
the handler to crash before it could return a JSON response:

### Bug 1 — `get_graph()` called with wrong number of arguments

```python
# Before (TypeError — takes 2 positional args but 3 were given)
graph = graph_manager.get_graph(graph_name, user_id)

# After
graph = get_graph_or_404(graph_name, user_id)
```

`GraphManager.get_graph(graph_name)` only accepts the graph name. It also only checks
the in-memory cache and will return `None` if the graph is not yet loaded. The correct
helper is `get_graph_or_404(graph_name, user_id)` which checks the cache first and
falls back to loading from the database — the same pattern used by all other handlers.

### Bug 2 — `get_workflow_id()` does not exist on `GraphManager`

```python
# Before (AttributeError — GraphManager has no method get_workflow_id)
workflow_id = graph_manager.get_workflow_id(graph_name, user_id)

# After
workflow_id = graph.workflow_id
```

`workflow_id` is a field on the `GraphData` object returned by `get_graph_or_404`.

### Bug 3 — `update_node()` called with extra `user_id` keyword argument

```python
# Before (TypeError — unexpected keyword argument 'user_id')
graph_manager.update_node(
    graph_name=graph_name,
    node_id=node_id,
    updates={"file_write_config": existing_config},
    user_id=user_id,
)

# After
graph_manager.update_node(graph_name, node_id, {"file_write_config": updated_config})
```

`GraphManager.update_node(graph_name, node_id, updates)` takes exactly three
positional arguments.

### Bug 4 — Nodes accessed as dicts instead of `EnhancedNodeData` objects

```python
# Before (AttributeError — EnhancedNodeData has no .get() method)
node = next((n for n in graph.nodes if n.get("id") == node_id), None)
node_type = node.get("type", "")
config = node.get("file_write_config") or {}

# After
node = graph.get_node_by_id(node_id)   # uses node.uniq_id internally
if node.type != NodeType.FILE_WRITE: ...
config = node.file_write_config or {}
```

`graph.nodes` is a list of `EnhancedNodeData` dataclass instances, not dicts.
The correct method to look up a node is `GraphData.get_node_by_id(node_id)`.

The same four bugs existed in `handle_delete_node_template` and were fixed at the
same time.

## Fix

**File changed:** `backend/api/graph/handlers/template_upload.py`

Both handler functions (`handle_upload_node_template` and `handle_delete_node_template`)
were rewritten to:

- Use `get_graph_or_404(graph_name, user_id)` to load the graph.
- Read `graph.workflow_id` for the workflow ID.
- Look up nodes via `graph.get_node_by_id(node_id)` and access attributes directly.
- Call `graph_manager.update_node(graph_name, node_id, updates)` without `user_id`.

No other files were changed.

## How to Verify

1. Open a workflow and add a **File Write Tool** node.
2. Open its configuration → **Templates** tab.
3. Click **Upload Template (.docx)** and select a `.docx` file containing Jinja2
   placeholders, e.g.:

   ```
   Customer: {{ customer_name }}
   {% for item in items %}{{ item.name }}{% endfor %}
   ```

4. Expected: upload succeeds, detected variables are displayed as badges.
5. Expected: clicking **Remove** clears the template without error.

## API Reference

```
POST /api/graph/node/{graph_name}/{node_id}/template
DELETE /api/graph/node/{graph_name}/{node_id}/template
```

Handler: `backend/api/graph/handlers/template_upload.py`  
Asset storage: `backend/services/workflow/asset_service.py` (`WorkflowAssetService`)  
Asset model: `backend/models/workflows/workflow_asset.py` (`WorkflowAsset`)
