"""
Configuration constants for email service.

Centralizes configuration values and constants used across the email service.
"""

import os


# Provider defaults
# None means no default - must be configured via user settings UI or environment variable
DEFAULT_EMAIL_PROVIDER = None
SUPPORTED_PROVIDERS = ["mailgun", "mailslurp", "outlook", "remote"]

# Mailgun configuration
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "sandbox.mailgun.org")
MAILGUN_BASE_URL = "https://api.mailgun.net/v3"

# MailSlurp configuration
MAILSLURP_API_KEY = os.getenv("MAILSLURP_API_KEY")
MAILSLURP_BASE_URL = "https://api.mailslurp.com"

# Outlook/Microsoft 365 configuration
# Uses DefaultAzureCredential for authentication (workload identity, managed identity, Azure CLI)
OUTLOOK_USER_PRINCIPAL_NAME = os.getenv("OUTLOOK_USER_PRINCIPAL_NAME")
OUTLOOK_SENDER_EMAIL = os.getenv("OUTLOOK_SENDER_EMAIL")  # Optional, defaults to UPN

# Cross-tenant credentials (optional)
# When all three are set, uses ClientSecretCredential targeting the specified tenant
# instead of DefaultAzureCredential. Required when the mailbox is in a different tenant.
OUTLOOK_TENANT_ID = os.getenv("OUTLOOK_TENANT_ID")
OUTLOOK_CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID")
OUTLOOK_CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET")

# Remote email relay configuration
# Send email via another Agentic Studio deployment's configured provider
REMOTE_EMAIL_URL = os.getenv("REMOTE_EMAIL_URL")
REMOTE_EMAIL_API_KEY = os.getenv("REMOTE_EMAIL_API_KEY")

# Webhook configuration
EMAIL_WEBHOOK_BASE_URL = os.getenv("EMAIL_WEBHOOK_BASE_URL", "http://localhost:8000")
WEBHOOK_TIMEOUT_SECONDS = 30

# Email defaults
DEFAULT_FROM_NAME = "AgenticStudio"
DEFAULT_FROM_DOMAIN = "noreply@nexusagent.ai"
DEFAULT_INBOX_EXPIRY_MINUTES = 60

# Polling configuration
DEFAULT_POLLING_INTERVAL_SECONDS = 30
DEFAULT_POLLING_TIMEOUT_MINUTES = 60
MIN_POLLING_INTERVAL_SECONDS = 10
MAX_POLLING_INTERVAL_SECONDS = 300
MAX_POLLING_TIMEOUT_MINUTES = 1440  # 24 hours

# Email extraction modes
EXTRACT_MODE_FULL_BODY = "full_body"
EXTRACT_MODE_STRIPPED_TEXT = "stripped_text"
EXTRACT_MODE_REGEX = "regex"
EXTRACT_MODE_JSON = "json"

# Logging prefixes
LOG_PREFIX_EMAIL = "[EMAIL-SERVICE]"
LOG_PREFIX_WEBHOOK = "[EMAIL-WEBHOOK]"
LOG_PREFIX_POLLING = "[EMAIL-POLLING]"
LOG_PREFIX_PROVIDER = "[EMAIL-PROVIDER]"
