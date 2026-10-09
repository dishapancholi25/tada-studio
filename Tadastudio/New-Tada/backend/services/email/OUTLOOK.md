# Outlook Email Provider Usage

## Overview

The `OutlookProvider` enables sending emails through Microsoft 365/Outlook using the Microsoft Graph API. It uses Azure
managed identity authentication via `DefaultAzureCredential`, making it ideal for deployment in Azure Kubernetes
Service (AKS) with workload identity.

## Features

- ✅ **Send Email** - Fully implemented with HTML and plain text support
- ⏳ **Create Inbox** - Not yet implemented
- ⏳ **Delete Inbox** - Not yet implemented
- ⏳ **Register Webhook** - Not yet implemented
- ⏳ **Unregister Webhook** - Not yet implemented
- ⏳ **Get Emails** - Not yet implemented

## Prerequisites

### 1. Azure AD Setup

Your application needs the following:

- A managed identity (system-assigned or user-assigned) in Azure
- Microsoft Graph API permissions:
  - `Mail.Send` (Application permission)
  - OR `Mail.Send` (Delegated permission) if using user delegation

### 2. Azure Kubernetes Service Configuration

For AKS with workload identity:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentic-studio-sa
  annotations:
    azure.workload.identity/client-id: <YOUR_MANAGED_IDENTITY_CLIENT_ID>
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-studio
spec:
  template:
    metadata:
      labels:
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: agentic-studio-sa
      containers:
        - name: backend
          # ... other config
```

### 3. Required Permissions

Grant the managed identity `Mail.Send` permissions in Azure AD:

```bash
# Using Azure CLI
az ad app permission add \
  --id <APP_ID> \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Role

# Grant admin consent
az ad app permission admin-consent --id <APP_ID>
```

## Usage

### Basic Email Sending

```python
from backend.services.email.providers.outlook import OutlookProvider

# Initialize the provider
provider = OutlookProvider(
    user_principal_name="notifications@yourdomain.com"
)

# Send a plain text email
result = await provider.send_email(
    from_address="notifications@yourdomain.com",
    to_address="user@example.com",
    subject="Hello from Agentic Studio",
    body="This is a plain text email."
)

print(result)
# {
#     'status': 'sent',
#     'provider': 'outlook',
#     'to': 'user@example.com',
#     'from': 'notifications@yourdomain.com',
#     'subject': 'Hello from Agentic Studio'
# }
```

### Sending HTML Email

```python
# Send HTML email with plain text fallback
result = await provider.send_email(
    from_address="notifications@yourdomain.com",
    to_address="user@example.com",
    subject="HTML Email Example",
    body="Plain text fallback",
    html_body="""
    <html>
        <body>
            <h1>Hello!</h1>
            <p>This is an <strong>HTML</strong> email.</p>
        </body>
    </html>
    """
)
```

### Email with Reply-To

```python
result = await provider.send_email(
    from_address="noreply@yourdomain.com",
    to_address="user@example.com",
    subject="Support Ticket Created",
    body="Your support ticket has been created.",
    reply_to="support@yourdomain.com"
)
```

## Configuration

### Environment Variables (for DefaultAzureCredential)

The provider automatically uses `DefaultAzureCredential`, which checks for credentials in this order:

1. **Workload Identity** (recommended for AKS)
2. **Managed Identity**
3. **Azure CLI** (for local development)
4. **Environment Variables**:
    - `AZURE_CLIENT_ID`
    - `AZURE_TENANT_ID`
    - `AZURE_CLIENT_SECRET` or `AZURE_CLIENT_CERTIFICATE_PATH`

### Provider Initialization Options

```python
# Minimal configuration (recommended)
provider = OutlookProvider(
    user_principal_name="notifications@yourdomain.com"
)

# With explicit sender email (if different from UPN)
provider = OutlookProvider(
    user_principal_name="service-account@yourdomain.onmicrosoft.com",
    sender_email="notifications@yourdomain.com"
)
```

## Cross-Tenant Setup

If the Microsoft 365 mailbox is in a different Azure AD tenant than where your app runs:

### 1. Register an App in the Mailbox Tenant

Create an app registration in the tenant that owns the mailbox. Grant it `Mail.Send` application permission and admin consent (same steps as the standard setup above).

### 2. Set Environment Variables

```bash
OUTLOOK_TENANT_ID=<mailbox-tenant-id>
OUTLOOK_CLIENT_ID=<app-registration-client-id>
OUTLOOK_CLIENT_SECRET=<app-registration-client-secret>
OUTLOOK_USER_PRINCIPAL_NAME=notifications@mailbox-tenant-domain.com
```

When all three cross-tenant variables are set, the provider uses `ClientSecretCredential` targeting that tenant instead of `DefaultAzureCredential`. If any are missing, it falls back to `DefaultAzureCredential`.

## Local Development

For local testing, authenticate using Azure CLI:

```bash
az login
az account set --subscription <SUBSCRIPTION_ID>
```

The `DefaultAzureCredential` will automatically use your Azure CLI credentials.

## Error Handling

```python
from backend.services.email.exceptions import EmailSendError, EmailConfigurationError

try:
    provider = OutlookProvider(user_principal_name="notifications@yourdomain.com")
    result = await provider.send_email(
        from_address="notifications@yourdomain.com",
        to_address="user@example.com",
        subject="Test",
        body="Test message"
    )
except EmailConfigurationError as e:
    print(f"Configuration error: {e}")
except EmailSendError as e:
    print(f"Failed to send email: {e}")
```

## Integration with Email Service Manager

```python
from backend.services.email.manager import EmailServiceManager
from backend.services.email.providers.outlook import OutlookProvider

# Register Outlook provider
manager = EmailServiceManager()
outlook = OutlookProvider(user_principal_name="notifications@yourdomain.com")
manager.register_provider("outlook", outlook)

# Use through manager
result = await manager.send_email(
    provider="outlook",
    from_address="notifications@yourdomain.com",
    to_address="user@example.com",
    subject="Via Manager",
    body="Sent through email service manager"
)
```

## Limitations

### Not Yet Implemented

The following methods will raise `NotImplementedError`:

- `create_inbox()` - Creating temporary inboxes
- `delete_inbox()` - Deleting inboxes
- `register_webhook()` - Webhook registration for inbox events
- `unregister_webhook()` - Webhook unregistration
- `get_emails()` - Retrieving emails from inbox
- `validate_webhook_signature()` - Returns `False` (not implemented)

### Send Limitations

- The `from_address` should match the `user_principal_name` or be an address the service account has "Send As" or "Send
  on Behalf" permissions for
- Rate limits apply based on your Microsoft 365 plan
- Maximum message size is typically 150 MB (including attachments)

## Troubleshooting

### Authentication Errors

**Error**: "Failed to initialize Microsoft Graph client"

**Solutions**:

- Verify managed identity is properly configured
- Check that workload identity federation is set up in AKS
- Ensure the service account has the correct annotations
- For local development, run `az login`

### Permission Errors

**Error**: "Insufficient privileges to complete the operation"

**Solutions**:

- Verify `Mail.Send` permission is granted to the managed identity
- Ensure admin consent has been granted for application permissions
- Check that the managed identity has access to the mailbox

### Send Failures

**Error**: "Failed to send email via Microsoft Graph"

**Solutions**:

- Verify the `from_address` matches the service account or has delegation
- Check recipient email address is valid
- Ensure the mailbox is not disabled or full
- Review Microsoft 365 message trace logs

## References

- [Microsoft Graph Mail API](https://learn.microsoft.com/en-us/graph/api/resources/mail-api-overview)
- [DefaultAzureCredential](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)
- [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview)
- [Graph API Permissions](https://learn.microsoft.com/en-us/graph/permissions-reference)
