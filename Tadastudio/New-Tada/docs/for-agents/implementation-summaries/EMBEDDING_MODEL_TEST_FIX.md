# Fix for Test Connection Button - Embedding Models Support

## Problem

The "Test Connection" button in the LLM Providers settings screen failed for embedding models (like
`text-embedding-3-small`) because it was calling the chat completion API (`llm.invoke()`) for all model types. Embedding
models require a different API endpoint (`embed_query()` or `embed_documents()`).

## Solution Overview

The fix adds proper model type detection and routing to test the appropriate API endpoint based on whether the model is
a chat/completion model (`llm`) or an embedding model (`embedding`).

## Changes Made

### 1. Backend - LLMConfig Model (`backend/models/workflow/configs/llm.py`)

**Added `model_type` field:**

- New field: `model_type: str = "llm"` (accepts "llm" or "embedding")
- Defaults to "llm" for backward compatibility
- Updated docstring to document the new field

**Why:** This allows the system to distinguish between chat models and embedding models throughout the application.

### 2. Backend - Config Enrichment (`backend/services/model_deployment/enrichment.py`)

**Updated enrichment process:**

```python
enriched.model_type = deployment.model_type or "llm"
```

**Why:** When a deployment is referenced by ID, the model_type needs to be copied from the deployment record to the
runtime config.

### 3. Backend - LLM Factory (`backend/services/llm_models/factory.py`)

**Enhanced `test_llm_connection` method:**

- Detects `model_type` from the config
- Routes to `_test_embedding_connection()` for embedding models
- Continues to use `llm.invoke()` for chat/completion models

**Added `_test_embedding_connection` method:**

```python
def _test_embedding_connection(self, llm_config: LLMConfig) -> Dict[str, Any]:
    """Test embedding model connection."""
    # Creates embedding instance using EmbeddingFactory
    # Tests with embed_query() instead of chat completion
    # Returns embedding dimension in response
```

**Key features:**

- Uses `EmbeddingFactory` to create the appropriate embedding instance
- Calls `embed_query()` with test text
- Validates the response is a valid embedding vector
- Returns dimension information in success response

### 4. Frontend - LLM Providers Tab (`frontend/src/components/settings/tabs/LLMProvidersTab.tsx`)

**Added visual indicator for embedding models:**

- Blue "EMBEDDING" badge displayed next to embedding model names
- Helps users quickly identify model types in the UI

## Provider Support

### ✅ Fully Supported

- **OpenAI**: Chat models (GPT-4, GPT-3.5) and embedding models (text-embedding-3-small, text-embedding-3-large)
- **Azure OpenAI**: Chat models and embedding models (with managed identity support)

### ✅ Chat Only

- **Anthropic (Claude)**: Only chat/completion models (Anthropic doesn't provide embedding models)

## Testing Strategy

### For Chat/Completion Models (LLM)

- Sends: `"Hello! Please respond with 'Connection successful'."`
- Uses: `llm.invoke()` method
- Validates: Response content is returned

### For Embedding Models

- Sends: `"This is a test query for embedding model connection."`
- Uses: `embed_query()` method
- Validates:
  - Response is a list
  - Vector has non-zero length
  - Returns dimension in success message

## Error Handling

Both test methods return consistent response format:

```python
{
    "success": bool,
    "response": str,  # Success message or embedding info
    "provider": str,
    "model": str,
    "error": str,  # Only present on failure
    "embedding_dimension": int  # Only for embedding models on success
}
```

## Backward Compatibility

- Default `model_type` is "llm" - existing deployments without model_type continue to work
- Existing chat model tests work exactly as before
- No breaking changes to API contracts

## Usage Example

### Creating an Embedding Model Deployment

1. Go to Settings → LLM Providers
2. Click "Add Model"
3. Select model type: "embedding"
4. Provider: "OpenAI" or "Azure OpenAI"
5. Model: "text-embedding-3-small"
6. Configure credentials/endpoint
7. Click "Test Connection" - now works correctly! ✅

### Visual Feedback

- Embedding models show a blue "EMBEDDING" badge
- Test button shows spinner while testing
- Success toast shows: "Successfully generated embedding vector of dimension 1536"
- Error toast shows specific error message if test fails

## Files Modified

1. `backend/models/workflow/configs/llm.py` - Added model_type field
2. `backend/services/model_deployment/enrichment.py` - Copy model_type during enrichment
3. `backend/services/llm_models/factory.py` - Smart test routing for LLM vs embedding
4. `frontend/src/components/settings/tabs/LLMProvidersTab.tsx` - Visual badge for embedding models

## Test Suite

**Pytest Test Suite**: `backend/tests/test_embedding_model_fix.py`

- `TestLLMConfigModelType` - Tests for model_type field functionality
- `TestLLMFactoryEmbeddingSupport` - Tests for embedding test routing
- `TestBackwardCompatibility` - Ensures backward compatibility

**Demo Script**: `scripts/dev/demo_embedding_model_fix.py`

- Interactive demonstration of all scenarios
- Shows routing logic for different model types

## Running Tests

Run the pytest test suite:

```bash
pytest backend/tests/test_embedding_model_fix.py -v
```

Expected output:

```
test_default_model_type PASSED
test_explicit_llm_type PASSED
test_embedding_model_type PASSED
test_azure_embedding_model_type PASSED
test_factory_has_embedding_test_method PASSED
test_llm_model_test_returns_dict PASSED
test_embedding_model_test_returns_dict PASSED
test_model_type_routing PASSED
test_legacy_config_without_model_type PASSED
test_anthropic_models_are_llm_type PASSED

10 passed
```

Run the demonstration script:

```bash
python scripts/dev/demo_embedding_model_fix.py
```

## Future Enhancements

Potential improvements for future consideration:

1. Add support for batch embedding tests
2. Show embedding dimensions in model card details
3. Add model type filter in LLM Providers list
4. Validate model_type matches model_name pattern (e.g., "text-embedding-*" → embedding)
