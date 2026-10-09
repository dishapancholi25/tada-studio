"""
Quick test script to verify Outlook email sending via ClientSecretCredential.

Usage:
    python test_outlook_send.py \
        --tenant-id <TENANT_ID> \
        --client-id <CLIENT_ID> \
        --client-secret <CLIENT_SECRET> \
        --upn <USER_PRINCIPAL_NAME> \
        --to <RECIPIENT_EMAIL>
"""

import argparse
import asyncio

from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.message import Message
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody


async def send_test_email(tenant_id, client_id, client_secret, upn, to_address):
    print(f"Authenticating with tenant {tenant_id}...")
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    client = GraphServiceClient(
        credentials=credential,
        scopes=["https://graph.microsoft.com/.default"],
    )

    message = Message()
    message.subject = "Test Email from Agentic Studio"
    message.body = ItemBody()
    message.body.content_type = BodyType.Text
    message.body.content = "This is a test email sent via Microsoft Graph API using ClientSecretCredential."

    to_recipient = Recipient()
    to_recipient.email_address = EmailAddress()
    to_recipient.email_address.address = to_address
    message.to_recipients = [to_recipient]

    request_body = SendMailPostRequestBody()
    request_body.message = message
    request_body.save_to_sent_items = True

    print(f"Sending email from {upn} to {to_address}...")
    await client.users.by_user_id(upn).send_mail.post(request_body)
    print("Email sent successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Outlook email sending")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--client-secret", required=True)
    parser.add_argument("--upn", required=True, help="User Principal Name (sender mailbox)")
    parser.add_argument("--to", required=True, help="Recipient email address")
    args = parser.parse_args()

    try:
        asyncio.run(send_test_email(args.tenant_id, args.client_id, args.client_secret, args.upn, args.to))
    except Exception as e:
        print(f"Error: {e}")
        raise
