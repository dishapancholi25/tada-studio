# Outlook Provider Unit Tests

Comprehensive unit tests for the `OutlookProvider` email service with mocked `GraphServiceClient`.

## Test Performance

⚡ **Fast execution**: All 30 tests complete in **~0.23 seconds** (226x faster than without mocking!)

The `fast_retries` fixture patches `asyncio.sleep` to make retry delays instant (0s instead of 2s, 4s, 8s), enabling
thorough retry logic testing without waiting.

## Test Coverage

### 1. Configuration Tests (`TestConfiguration`)

Tests for provider initialization and configuration validation:

- ✅ **test_init_with_valid_config**: Validates successful initialization with all parameters
- ✅ **test_init_without_user_principal_name**: Ensures `EmailConfigurationError` when `user_principal_name` is missing
- ✅ **test_init_with_user_principal_name_only**: Verifies `sender_email` defaults to `user_principal_name`
- ✅ **test_init_graph_client_failure**: Tests graceful failure when Graph client initialization fails

### 2. Input Validation Tests (`TestInputValidation`)

Tests for the `_validate_email_inputs()` method that validates inputs before API calls:

#### Required Field Validation

- ✅ **test_validate_empty_to_address**: Fails when `to_address` is empty
- ✅ **test_validate_whitespace_to_address**: Fails when `to_address` is whitespace only
- ✅ **test_validate_empty_from_address**: Fails when `from_address` is empty
- ✅ **test_validate_empty_subject**: Fails when `subject` is empty
- ✅ **test_validate_no_body**: Fails when both `body` and `html_body` are missing

#### Email Format Validation

- ✅ **test_validate_invalid_to_address_format**: Fails on invalid `to_address` format
- ✅ **test_validate_invalid_from_address_format**: Fails on invalid `from_address` format
- ✅ **test_validate_invalid_reply_to_format**: Fails on invalid `reply_to` format

#### From Address Validation

- ✅ **test_validate_from_address_mismatch**: Fails when `from_address` doesn't match configured sender
- ✅ **test_validate_from_address_case_insensitive**: Verifies case-insensitive matching of `from_address`

### 3. Send Email Tests (`TestSendEmail`)

Tests for the core `send_email()` functionality:

- ✅ **test_send_plain_text_email**: Sends plain text email successfully
- ✅ **test_send_html_email**: Sends HTML email successfully
- ✅ **test_send_email_with_reply_to**: Sends email with reply-to address
- ✅ **test_send_email_graph_api_error**: Handles Graph API errors gracefully

### 4. Retry Logic Tests (`TestRetryLogic`)

Tests for exponential backoff retry logic using `tenacity`:

- ✅ **test_retry_on_transient_error**: Retries up to 3 times on transient errors and succeeds
- ✅ **test_retry_exhausted**: Fails after max attempts (3) with persistent errors
- ✅ **test_no_retry_on_validation_error**: Validation errors don't trigger retries (fail fast)

### 5. Factory Integration Tests (`TestFactoryIntegration`)

Tests for integration with `EmailServiceFactory`:

- ✅ **test_create_outlook_provider_from_factory**: Creates OutlookProvider via factory
- ✅ **test_factory_outlook_without_user_principal_name**: Factory fails without required config
- ✅ **test_factory_outlook_with_config_values**: Factory uses config values when kwargs not provided

### 6. Not Implemented Methods Tests (`TestNotImplementedMethods`)

Tests that unimplemented methods raise appropriate exceptions:

- ✅ **test_create_inbox_not_implemented**: Raises `InboxCreationError`
- ✅ **test_delete_inbox_not_implemented**: Raises `InboxDeletionError`
- ✅ **test_register_webhook_not_implemented**: Raises `WebhookRegistrationError`
- ✅ **test_unregister_webhook_not_implemented**: Raises `WebhookUnregistrationError`
- ✅ **test_get_emails_not_implemented**: Raises `EmailRetrievalError`
- ✅ **test_validate_webhook_signature_not_implemented**: Returns `False`

## Running the Tests

### Run all Outlook provider tests

```bash
pytest backend/tests/email/test_outlook_provider.py -v
```

### Run a specific test class

```bash
pytest backend/tests/email/test_outlook_provider.py::TestInputValidation -v
```

### Run a specific test

```bash
pytest backend/tests/email/test_outlook_provider.py::TestInputValidation::test_validate_from_address_mismatch -v
```

### Run with coverage

```bash
pytest backend/tests/email/test_outlook_provider.py --cov=backend/services/email/providers/outlook --cov-report=html
```

## Test Results

```
✅ 30 passed in 0.23s
```

All tests pass successfully and execute blazingly fast! ⚡

## Mocking Strategy

The tests use `unittest.mock` to mock external dependencies:

1. **`DefaultAzureCredential`**: Mocked to avoid requiring Azure credentials during tests
2. **`GraphServiceClient`**: Mocked to avoid making real API calls to Microsoft Graph
3. **Graph API chain**: The `users.by_user_id().send_mail.post()` call chain is mocked with `AsyncMock`
4. **`asyncio.sleep`**: Patched via `fast_retries` fixture to make retry delays instant (critical for fast tests!)

### Fast Retries Fixture

The `fast_retries` fixture (autouse=True) patches `asyncio.sleep` to return immediately:

```python
@pytest.fixture(autouse=True)
def fast_retries():
    """Make retry logic instant for tests by mocking asyncio.sleep."""

    async def instant_sleep(delay):
        """Mock sleep that returns immediately."""
        pass

    with patch("asyncio.sleep", new=instant_sleep):
        yield
```

This makes tests with retry logic execute in milliseconds instead of waiting for real exponential backoff delays (2s,
4s, 8s).

## Key Features Tested

### ✅ Fail-Fast Validation

- All input validation happens before API calls
- Clear, descriptive error messages for each validation failure
- No retries triggered for validation errors

### ✅ From Address Validation

- Validates `from_address` matches configured sender
- Case-insensitive comparison
- Clear error messages showing expected values

### ✅ Retry Logic

- Exponential backoff: 2s, 4s, 8s (max 10s)
- Maximum 3 attempts
- Logs warnings before each retry
- Reraises final exception after exhaustion

### ✅ Factory Integration

- Works with `EmailServiceFactory.create_provider()`
- Supports both kwargs and config-based initialization
- Validates required configuration

### ✅ Error Handling

- Maps Graph API errors to `EmailSendError`
- Preserves exception chain with `from e`
- Provides clear error messages

## Dependencies

- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **unittest.mock**: Mocking framework (standard library)

No additional dependencies required! Uses standard mocking instead of `pytest-mock`.
