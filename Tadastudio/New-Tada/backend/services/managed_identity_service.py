"""Managed Identity Service for AWS and Azure.

This service provides token generation using cloud provider managed identities
for authenticating with MCP servers without storing static credentials.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)
LOG_PREFIX = "[MANAGED-IDENTITY]"


class ManagedIdentityService:
    """Service for generating authentication tokens using cloud managed identities."""

    def __init__(self, cloud_provider: str):
        """Initialize the managed identity service.

        Args:
            cloud_provider: Cloud provider ('aws' or 'azure')
        """
        self.cloud_provider = cloud_provider.lower()
        self.token_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()

        logger.info(
            f"{LOG_PREFIX} Initialized for cloud provider: {self.cloud_provider}"
        )

    def get_token(
        self,
        resource: Optional[str] = None,
        client_id: Optional[str] = None,
        role_arn: Optional[str] = None,
    ) -> Optional[str]:
        """Get an authentication token using managed identity.

        Args:
            resource: Azure resource scope (e.g., 'https://database.windows.net/.default')
            client_id: Azure managed identity client ID (optional)
            role_arn: AWS IAM role ARN to assume (optional)

        Returns:
            Bearer token string, or None if token generation fails
        """
        if self.cloud_provider == "aws":
            return self._get_aws_token(role_arn)
        elif self.cloud_provider == "azure":
            return self._get_azure_token(resource, client_id)
        else:
            logger.error(
                f"{LOG_PREFIX} Unsupported cloud provider: {self.cloud_provider}"
            )
            return None

    def _get_aws_token(self, role_arn: Optional[str] = None) -> Optional[str]:
        """Get AWS credentials using boto3 default credential chain or assume role.

        Args:
            role_arn: Optional IAM role ARN to assume

        Returns:
            JSON string containing AWS credentials, or None on failure
        """
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, ClientError
            import json

            cache_key = role_arn or "default"
            now = datetime.now(timezone.utc)

            # Check cache (thread-safe)
            with self._cache_lock:
                cached = self.token_cache.get(cache_key)
                if cached and cached.get("expiry_time") and cached["expiry_time"] > now:
                    logger.debug(
                        f"{LOG_PREFIX} Returning cached AWS credentials for key={cache_key}"
                    )
                    return json.dumps(cached["credentials"])

            if role_arn and role_arn.startswith("arn:aws:iam::"):
                # Assume role
                logger.debug(f"{LOG_PREFIX} Assuming AWS role: {role_arn}")
                sts = boto3.client("sts")
                resp = sts.assume_role(
                    RoleArn=role_arn, RoleSessionName="AgenticStudioMCPSession"
                )
                creds = resp["Credentials"]
                expiry = creds["Expiration"]

                credentials = {
                    "access_key": creds["AccessKeyId"],
                    "secret_key": creds["SecretAccessKey"],
                    "session_token": creds["SessionToken"],
                }

                with self._cache_lock:
                    self.token_cache[cache_key] = {
                        "credentials": credentials,
                        "expiry_time": expiry if isinstance(expiry, datetime) else None,
                    }

                logger.info(
                    f"{LOG_PREFIX} Retrieved AWS credentials via role assumption"
                )
                return json.dumps(credentials)
            else:
                # Use default credential chain
                logger.debug(f"{LOG_PREFIX} Using AWS default credential chain")
                session = boto3.Session()
                frozen = session.get_credentials().get_frozen_credentials()

                credentials = {
                    "access_key": frozen.access_key,
                    "secret_key": frozen.secret_key,
                    "session_token": frozen.token,
                }

                # Default credentials don't have expiry, cache for 1 hour
                from datetime import timedelta

                expiry = now + timedelta(hours=1)

                with self._cache_lock:
                    self.token_cache[cache_key] = {
                        "credentials": credentials,
                        "expiry_time": expiry,
                    }

                logger.info(
                    f"{LOG_PREFIX} Retrieved AWS credentials from default chain"
                )
                return json.dumps(credentials)

        except (BotoCoreError, ClientError) as e:
            logger.error(f"{LOG_PREFIX} Failed to retrieve AWS credentials: {e}")
            return None
        except ImportError:
            logger.error(
                f"{LOG_PREFIX} boto3 not installed. Install with: pip install boto3"
            )
            return None
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Unexpected error getting AWS token: {e}")
            return None

    def _get_azure_token(
        self, resource: Optional[str] = None, client_id: Optional[str] = None
    ) -> Optional[str]:
        """Get Azure access token using DefaultAzureCredential.

        Args:
            resource: Azure resource scope (defaults to database scope if not provided)
            client_id: Optional managed identity client ID

        Returns:
            Bearer token string, or None on failure
        """
        try:
            from azure.identity import DefaultAzureCredential

            # Default to database resource if not specified
            resource = resource or "https://database.windows.net/.default"
            cache_key = f"{resource}:{client_id or 'default'}"
            now = datetime.now(timezone.utc)

            # Check cache (thread-safe)
            with self._cache_lock:
                cached = self.token_cache.get(cache_key)
                if cached and cached.get("expiry_time"):
                    expiry_timestamp = cached["expiry_time"]
                    expiry_dt = datetime.fromtimestamp(
                        expiry_timestamp, tz=timezone.utc
                    )
                    if expiry_dt > now:
                        logger.debug(
                            f"{LOG_PREFIX} Returning cached Azure token for resource={resource}"
                        )
                        return cached["token"]

            # Get new token
            params = {}
            if client_id:
                params["managed_identity_client_id"] = client_id
                logger.debug(
                    f"{LOG_PREFIX} Getting Azure token for resource={resource} with client_id={client_id}"
                )
            else:
                logger.debug(
                    f"{LOG_PREFIX} Getting Azure token for resource={resource} using default identity"
                )

            credential = DefaultAzureCredential(**params)
            token = credential.get_token(resource)

            if not token:
                logger.error(
                    f"{LOG_PREFIX} Failed to retrieve Azure token for resource: {resource}"
                )
                return None

            # Cache the token (thread-safe)
            with self._cache_lock:
                self.token_cache[cache_key] = {
                    "token": token.token,
                    "expiry_time": token.expires_on,
                }

            expiry_str = datetime.fromtimestamp(token.expires_on).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            logger.info(
                f"{LOG_PREFIX} Retrieved Azure token for resource={resource}, expires: {expiry_str}"
            )

            return token.token

        except ImportError:
            logger.error(
                f"{LOG_PREFIX} azure-identity not installed. Install with: pip install azure-identity"
            )
            return None
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Failed to retrieve Azure token: {e}")
            return None

    def clear_cache(self):
        """Clear the token cache (thread-safe)."""
        with self._cache_lock:
            self.token_cache.clear()
        logger.debug(f"{LOG_PREFIX} Token cache cleared")
