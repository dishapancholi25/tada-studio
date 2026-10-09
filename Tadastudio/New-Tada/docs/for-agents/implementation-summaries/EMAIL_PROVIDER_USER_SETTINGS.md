# Email Provider Configuration from User Settings

## Summary

Fixed email provider configuration to use user-configured settings from the UI instead of hardcoded defaults.

## Problem

The email service was hardcoded to use `DEFAULT_EMAIL_PROVIDER = "mailgun"`, which meant:

- Even when users configured Outlook in Settings > External Services, the system still tried to use Mailgun
- This caused errors like: `Failed to create provider 'mailgun': Mailgun API key is required`
- User settings from the UI were being ignored

## Solution

Modified the email provider resolution to prioritize user settings:

### 1. Email Executor Changes (`backend/services/nodes/executors/email.py`)

- Updated `_send_email()` to accept `user_id` parameter
- Added logic to retrieve email configuration from `UserExternalServiceService`
- Extracts provider name and settings from user's configured external service
- Passes provider-specific settings to the factory (e.g., `user_principal_name` for Outlook)
- Falls back to environment variables/defaults only if user hasn't configured anything

```python
# Get provider configuration from user settings
if user_id:
    email_service = UserExternalServiceService.get_service(user_id, "email")
    if email_service and email_service.is_active:
        provider_name = email_service.settings.get("provider")
        # Extract provider-specific settings...
```

### 2. Config Changes (`backend/services/email/config.py`)

- Set `DEFAULT_EMAIL_PROVIDER = None` to make it clear no default exists
- Updated comments to emphasize user settings UI configuration

### 3. Factory Changes (`backend/services/email/providers/factory.py`)

- Added validation for `None` provider with helpful error message
- Error now guides users to configure email in Settings UI
- Improved error message: "No email provider configured. Please configure an email provider in Settings > External
  Services..."

## Configuration Priority (Highest to Lowest)

1. **User Settings (from UI)** - Stored in `user_external_services` table
2. **Environment Variable** - `EMAIL_PROVIDER` env var
3. **None** - No default fallback (raises helpful error)

## Provider-Specific Settings Handled

- **Outlook**: `user_principal_name`, `sender_email`
- **Mailgun**: `domain` (API key is encrypted in database)
- **MailSlurp**: (API key is encrypted in database)

## Database Schema

User settings are stored in the `user_external_services` table:

- `service_name`: "email"
- `encrypted_api_key`: Encrypted API key (for Mailgun/MailSlurp)
- `settings`: JSONB field containing:
  - `provider`: "outlook" | "mailgun" | "mailslurp"
  - `user_principal_name`: (Outlook only)
  - `sender_email`: (Outlook only)
  - `domain`: (Mailgun only)

## User Flow

1. User navigates to Settings > External Services
2. Selects email provider from dropdown
3. Enters provider-specific configuration
4. Saves configuration (stored encrypted in database)
5. Email nodes now automatically use this configuration

## Testing

Existing tests continue to work because they mock `EmailServiceFactory.create_provider()`.

## Related Files

- `backend/services/nodes/executors/email.py` - Email executor
- `backend/services/email/providers/factory.py` - Provider factory
- `backend/services/email/config.py` - Configuration constants
- `backend/services/auth/user_external_service.py` - User settings service
- `backend/api/user_settings/routes.py` - API endpoints
- `frontend/src/components/settings/tabs/ExternalServicesTab.tsx` - Settings UI
