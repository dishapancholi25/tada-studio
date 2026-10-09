"""
Integration test/example for OutlookProvider.

This demonstrates how to use the OutlookProvider with Microsoft Graph API.
Note: Requires proper Azure AD setup and credentials to run successfully.
"""

import asyncio
import logging
import os

from backend.services.email.providers.outlook import OutlookProvider
from backend.services.email.exceptions import EmailSendError, EmailConfigurationError


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_outlook_send_email():
    """Test sending an email via Outlook/Microsoft 365."""

    # Configuration - these should come from environment variables or config
    user_principal_name = os.getenv(
        "OUTLOOK_USER_PRINCIPAL_NAME", "notifications@yourdomain.com"
    )
    sender_email = os.getenv("OUTLOOK_SENDER_EMAIL", user_principal_name)

    try:
        # Initialize the provider
        logger.info("Initializing OutlookProvider...")
        provider = OutlookProvider(
            user_principal_name=user_principal_name, sender_email=sender_email
        )
        logger.info(f"Provider initialized for {user_principal_name}")

        # Send a plain text email
        logger.info("Sending plain text email...")
        result = await provider.send_email(
            from_address=sender_email,
            to_address="test@example.com",
            subject="Test Email from AgenticStudio",
            body="This is a test email sent via Microsoft Graph API using managed identity.",
        )
        logger.info(f"Email sent successfully: {result}")

        # Send an HTML email
        logger.info("Sending HTML email...")
        html_content = """
        <html>
            <body>
                <h1>Hello from AgenticStudio!</h1>
                <p>This is a <strong>test email</strong> with HTML formatting.</p>
                <ul>
                    <li>Sent via Microsoft Graph API</li>
                    <li>Using managed identity authentication</li>
                    <li>From Azure Kubernetes Service</li>
                </ul>
            </body>
        </html>
        """

        result = await provider.send_email(
            from_address=sender_email,
            to_address="test@example.com",
            subject="HTML Test Email from AgenticStudio",
            body="Plain text fallback",
            html_body=html_content,
            reply_to="support@yourdomain.com",
        )
        logger.info(f"HTML email sent successfully: {result}")

        return True

    except EmailConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("Make sure:")
        logger.info("1. OUTLOOK_USER_PRINCIPAL_NAME is set")
        logger.info(
            "2. Azure credentials are available (workload identity, managed identity, or Azure CLI)"
        )
        logger.info("3. The service principal has Mail.Send permissions")
        return False

    except EmailSendError as e:
        logger.error(f"Failed to send email: {e}")
        return False

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return False


async def test_not_implemented_methods():
    """Test that unimplemented methods raise appropriate exceptions."""

    user_principal_name = os.getenv(
        "OUTLOOK_USER_PRINCIPAL_NAME", "notifications@yourdomain.com"
    )

    try:
        provider = OutlookProvider(user_principal_name=user_principal_name)

        # Test create_inbox (not implemented)
        try:
            await provider.create_inbox()
            logger.error("create_inbox should have raised InboxCreationError")
        except Exception as e:
            logger.info(f"✓ create_inbox correctly raises: {type(e).__name__}")

        # Test delete_inbox (not implemented)
        try:
            await provider.delete_inbox("test-inbox")
            logger.error("delete_inbox should have raised InboxDeletionError")
        except Exception as e:
            logger.info(f"✓ delete_inbox correctly raises: {type(e).__name__}")

        # Test get_emails (not implemented)
        try:
            await provider.get_emails("test-inbox")
            logger.error("get_emails should have raised EmailRetrievalError")
        except Exception as e:
            logger.info(f"✓ get_emails correctly raises: {type(e).__name__}")

        # Test validate_webhook_signature (not implemented)
        result = provider.validate_webhook_signature(b"payload", "signature")
        if result is False:
            logger.info("✓ validate_webhook_signature correctly returns False")

        return True

    except Exception as e:
        logger.error(f"Error testing not implemented methods: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("OutlookProvider Integration Test")
    logger.info("=" * 60)

    logger.info("\n--- Testing Not Implemented Methods ---")
    await test_not_implemented_methods()

    logger.info("\n--- Testing Email Sending ---")
    logger.info("Note: This requires valid Azure credentials and permissions")
    logger.info("Set OUTLOOK_USER_PRINCIPAL_NAME environment variable to test")

    if os.getenv("OUTLOOK_USER_PRINCIPAL_NAME"):
        success = await test_outlook_send_email()
        if success:
            logger.info("\n✓ All tests passed!")
        else:
            logger.error("\n✗ Some tests failed")
    else:
        logger.warning(
            "\nSkipping email send test (OUTLOOK_USER_PRINCIPAL_NAME not set)"
        )
        logger.info("To run the full test, set:")
        logger.info(
            "  export OUTLOOK_USER_PRINCIPAL_NAME='notifications@yourdomain.com'"
        )


if __name__ == "__main__":
    asyncio.run(main())
