# Email Provider Fix - Testing Guide

## What Was Fixed

The email system was ignoring user-configured providers from the Settings UI and always trying to use the hardcoded
`DEFAULT_EMAIL_PROVIDER = "mailgun"`. This has been fixed so that:

1. **User settings take priority** - Email provider configured in Settings > External Services is used first
2. **Environment variables as fallback** - `EMAIL_PROVIDER` env var is used if no user setting exists
3. **Helpful error messages** - Clear guidance when no provider is configured

## How to Test

### 1. Configure Email Provider in UI

1. Start the application
2. Navigate to **Settings > External Services**
3. Scroll to **Email Service** section
4. Select **Microsoft Outlook** from dropdown
5. Enter your User Principal Name (e.g., `notifications@yourdomain.com`)
6. Click **Save Configuration**

### 2. Test Email Sending

Create a workflow with an EMAIL_SEND node and execute it. The system should now:

- ✅ Use Outlook provider (from your settings)
- ✅ Not try to use Mailgun
- ✅ Not throw "Mailgun API key is required" error

### 3. Verify Logs

When an email is sent, you should see in the logs:

```
Using email provider 'outlook' from user settings
```

Instead of the previous error:

```
Failed to create provider 'mailgun': Mailgun API key is required
```

## Expected Behavior Before vs After

### BEFORE (Broken)

```
❌ User configures Outlook in Settings UI
❌ System ignores this configuration
❌ System tries to use hardcoded Mailgun default
❌ Error: "Mailgun API key is required"
```

### AFTER (Fixed)

```
✅ User configures Outlook in Settings UI
✅ Configuration saved to database
✅ Email executor retrieves Outlook settings
✅ Email sent successfully via Outlook
```

## Configuration Priority Order

1. **User Settings** (highest priority)
    - Stored in `user_external_services` table
    - Configured via Settings > External Services UI

2. **Environment Variable**
    - `EMAIL_PROVIDER` env var
    - Provider-specific env vars (e.g., `OUTLOOK_USER_PRINCIPAL_NAME`)

3. **No Default**
    - If nothing configured, helpful error message guides user to Settings UI

## Provider-Specific Configuration

### Outlook

- **Required**: User Principal Name
- **Optional**: Sender Email (defaults to UPN)
- **Authentication**: Uses Azure Managed Identity

### Mailgun

- **Required**: API Key, Domain
- **Authentication**: API key-based

### MailSlurp

- **Required**: API Key
- **Authentication**: API key-based

## Troubleshooting

### Error: "No email provider configured"

**Solution**: Configure a provider in Settings > External Services

### Error: "User Principal Name is required for Outlook"

**Solution**: Enter your UPN in the Outlook configuration in Settings

### Email still tries to use Mailgun

**Possible causes**:

1. Email configuration not saved in Settings
2. User not authenticated (user_id is None)
3. Check database: `SELECT * FROM user_external_services WHERE service_name = 'email'`

## Database Verification

Check if email configuration is saved:

```sql
SELECT user_id,
       service_name,
       settings,
       is_active,
       updated_at
FROM user_external_services
WHERE service_name = 'email';
```

Expected result for Outlook:

```json
{
  "provider": "outlook",
  "user_principal_name": "notifications@yourdomain.com",
  "sender_email": "notifications@yourdomain.com"
}
```

## Files Changed

1. `backend/services/nodes/executors/email.py`
    - Added user_id parameter to `_send_email()`
    - Retrieves email config from UserExternalServiceService
    - Passes provider settings to factory

2. `backend/services/email/config.py`
    - Changed `DEFAULT_EMAIL_PROVIDER` from `"mailgun"` to `None`

3. `backend/services/email/providers/factory.py`
    - Added validation for None provider
    - Improved error messages to guide users

## Related Documentation

- [Email Provider User Settings Implementation](./EMAIL_PROVIDER_USER_SETTINGS.md)
- [Email Configuration UI](./EMAIL_CONFIGURATION_UI.md)
- [Outlook Provider Implementation](./OUTLOOK.md)
