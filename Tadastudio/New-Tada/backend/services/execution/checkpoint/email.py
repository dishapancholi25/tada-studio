"""
Email Checkpoint Executor.

This module handles email-based checkpoint nodes that send an email to a recipient
and wait for their response before continuing execution. The email response is
extracted and used as the checkpoint input.

ISG FIX: Email checkpoint feature is temporarily DISABLED pending security review.
Specifically: sender validation and authorization checks for webhook callbacks.
All email checkpoint execution paths will be skipped. Users must use Manual checkpoints.
"""

import asyncio
import os
from typing import TYPE_CHECKING, Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.feature_flags import (
    EMAIL_COMING_SOON_MESSAGE,
    EMAIL_FEATURE_ENABLED,
)
from backend.services.workflow.state import WorkflowState

from .base import CheckpointExecutor

if TYPE_CHECKING:
    from backend.models import GraphData

email_checkpoint_logger = get_logger("execution.checkpoint.email")


class EmailCheckpointExecutor(CheckpointExecutor):
    """
    Executes email-based checkpoint nodes.

    Email checkpoints:
    1. Create an inbox or use workflow-aware email routing
    2. Send an email to the configured recipient
    3. Wait for email response via webhook
    4. Extract content from the email response
    5. Continue execution with the extracted content

    Supports two email service modes:
    - Mailgun: Uses workflow-aware routing (workflow-{execution_id}@domain)
    - MailSlurp: Creates temporary inbox for each checkpoint

    DISABLED: Email checkpoints are currently disabled. See module docstring.
    """

    def __init__(self, active_executions: Dict[str, Any], field_extractor: Any):
        """
        Initialize email checkpoint executor.

        Args:
            active_executions: Reference to engine's active executions dict
            field_extractor: FieldExtractor instance for extracting values
        """
        super().__init__(active_executions)
        self.field_extractor = field_extractor

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
        input_message: str,
    ) -> Dict[str, Any]:
        """
        Execute email checkpoint node.

        Args:
            node: The checkpoint node to execute
            state: Current workflow state
            graph: The graph definition
            input_message: Input message for email body template

        Returns:
            State updates dictionary with email response content
        """
        email_checkpoint_logger.info(f"Starting email checkpoint: {node.name}")

        # Email is a coming-soon feature: degrade to a manual checkpoint so the
        # workflow still pauses for human approval instead of failing outright.
        if not EMAIL_FEATURE_ENABLED:
            email_checkpoint_logger.warning(
                f"Email checkpoint {node.name} falling back to manual: "
                f"{EMAIL_COMING_SOON_MESSAGE}"
            )
            return self._fallback_to_manual_checkpoint(
                node, state, EMAIL_COMING_SOON_MESSAGE
            )

        # Extract email configuration
        email_config = self._get_email_config(node)
        if not email_config:
            email_checkpoint_logger.error(
                f"Email checkpoint {node.name} missing email configuration"
            )
            return self._fallback_to_manual_checkpoint(
                node, state, "Missing email configuration"
            )

        db_execution_id = state.get("db_execution_id")
        ws_execution_id = state.get("execution_id")

        # Get current iteration (for loop support)
        current_iteration = self.get_current_iteration(node, state)

        # Check if resuming from existing paused checkpoint with email response
        existing_response = await self._check_existing_email_response(
            node, state, current_iteration, ws_execution_id, input_message, graph
        )
        if existing_response:
            return existing_response

        try:
            # Initialize email service from user's DB settings
            email_service = await self._get_email_service(email_config, state)

            # Setup inbox/email routing
            inbox, reply_to_address = await self._setup_email_routing(
                email_service, ws_execution_id, email_config
            )

            # Resolve dynamic email fields
            recipient_email, email_subject, email_body = self._resolve_email_fields(
                email_config, state, graph, input_message, node
            )

            # Send email
            await self._send_checkpoint_email(
                email_service,
                inbox,
                recipient_email,
                email_subject,
                email_body,
                graph,
                ws_execution_id,
            )

            # Log webhook endpoint info
            self._log_webhook_info(ws_execution_id, email_service)

            # Create checkpoint node execution in database
            node_exec_id = self._create_email_checkpoint_record(
                db_execution_id,
                node,
                state,
                input_message,
                current_iteration,
                inbox,
                reply_to_address,
                email_config,
                ws_execution_id,
                email_service,
            )

            # Send WebSocket notifications
            if node_exec_id and ws_execution_id:
                await self.send_node_start_notification(node, state, node_exec_id)

            # Use interrupt to pause execution
            answer = await self._pause_for_email_response(node, reply_to_address, inbox)

            # Clean up email resources
            await self._cleanup_email_resources(email_service, inbox)

            # Complete checkpoint node
            if node_exec_id:
                self.complete_checkpoint_node(
                    node_exec_id,
                    {"email_response": answer},
                )

                await self.send_completion_notification(
                    node,
                    state,
                    {"email_response": answer},
                    input_message,
                    node_exec_id,
                )

            # Build and return result
            return self.build_checkpoint_result(
                answer,
                state,
                node,
                current_iteration,
                {
                    "email_checkpoint": True,
                    "inbox_used": reply_to_address,
                },
            )

        except Exception as e:
            # Check if this is an Interrupt (expected for pausing)
            if "Interrupt" in str(type(e).__name__):
                email_checkpoint_logger.info(
                    "Checkpoint paused, waiting for email response"
                )
                raise  # Re-raise the interrupt to pause properly
            else:
                email_checkpoint_logger.error(
                    f"[EMAIL-CHECKPOINT] Email checkpoint failed for '{node.name}': {e}",
                    exc_info=True,
                )
                return self._fallback_to_manual_checkpoint(node, state, str(e))

    async def _check_existing_email_response(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        current_iteration: int,
        ws_execution_id: str,
        input_message: str,
        graph: "GraphData",
    ) -> Optional[Dict[str, Any]]:
        """Check if resuming from paused checkpoint with email response."""
        db_execution_id = state.get("db_execution_id")
        if not db_execution_id:
            return None

        try:
            from backend.services.execution.history import ExecutionHistoryService
            from backend.services.common.utils.websocket_notifier import ws_notifier

            node_execs = ExecutionHistoryService.get_node_executions(db_execution_id)

            for ne in node_execs:
                if (
                    ne.get("node_id") == node.uniq_id
                    and ne.get("node_type") == "CHECKPOINT"
                    and ne.get("status") == "paused"
                    and ne.get("iteration", 0) == current_iteration - 1
                ):
                    # Found paused checkpoint from previous iteration
                    output_data = ne.get("output_data", {})
                    email_response = output_data.get("email_response", {})
                    extracted_content = email_response.get("extracted_content", "")
                    node_exec_id = ne.get("id")

                    # Only return early if we have actual email response
                    if email_response and extracted_content:
                        email_checkpoint_logger.info(
                            "Resuming from paused email checkpoint with response"
                        )

                        # Send completion notification
                        if ws_notifier and ws_execution_id:
                            await self.send_completion_notification(
                                node,
                                state,
                                {"email_response": email_response},
                                input_message,
                                node_exec_id,
                            )

                        # Return result
                        return self.build_checkpoint_result(
                            extracted_content,
                            state,
                            node,
                            current_iteration,
                            {
                                "email_checkpoint": True,
                                "email_response": email_response,
                            },
                        )
                    break

        except Exception as e:
            email_checkpoint_logger.error(f"Error checking for paused checkpoint: {e}")

        return None

    async def _get_email_service(self, email_config, state: WorkflowState):
        """Get email service provider using user's DB-stored settings."""
        from backend.services.email.credential_resolver import (
            resolve_email_provider_config,
        )
        from backend.services.email.providers.factory import EmailServiceFactory

        user_id = state.get("user_id")
        provider_name, provider_kwargs = resolve_email_provider_config(user_id)

        # Allow email_config to override the provider name if explicitly set
        config_provider = getattr(email_config, "email_provider", None)
        if config_provider:
            provider_name = config_provider

        provider = EmailServiceFactory.create_provider(provider_name, **provider_kwargs)
        email_checkpoint_logger.info(
            f"[EMAIL-CHECKPOINT] Email service resolved: {type(provider).__name__}"
        )
        return provider

    async def _setup_email_routing(
        self, email_service, ws_execution_id: str, email_config=None
    ) -> tuple[Optional[Any], str]:
        """
        Set up email inbox or routing for checkpoint.

        Returns:
            Tuple of (inbox object or None, reply-to address)
        """
        use_workflow_mapping = hasattr(email_service, "send_email_with_workflow_id")

        if use_workflow_mapping:
            email_checkpoint_logger.info("Using workflow-aware email sending (Mailgun)")
            inbox = None
            domain = getattr(email_service, "domain", "mailgun")
            reply_to_address = f"workflow-{ws_execution_id}@{domain}"
        else:
            email_checkpoint_logger.info("Creating temporary inbox (MailSlurp)")
            expires_minutes = (
                getattr(email_config, "timeout_minutes", 60) if email_config else 60
            )
            inbox = await email_service.create_inbox(expires_in_minutes=expires_minutes)
            reply_to_address = inbox.email_address
            email_checkpoint_logger.info(f"Created inbox: {reply_to_address}")
            # Small delay to ensure inbox is ready
            await asyncio.sleep(1)

        return inbox, reply_to_address

    def _resolve_email_fields(
        self,
        email_config,
        state: WorkflowState,
        graph: "GraphData",
        input_message: str,
        node: EnhancedNodeData,
    ) -> tuple[str, str, str]:
        """
        Resolve dynamic email fields (recipient, subject, body).

        Returns:
            Tuple of (recipient_email, subject, body)
        """
        recipient_email = self._extract_value(
            email_config.recipient_email,
            getattr(email_config, "recipient_email_source_mode", "static"),
            getattr(email_config, "recipient_email_source_node_id", None),
            getattr(email_config, "recipient_email_field_path", None),
            email_config.recipient_email,
            state,
            graph,
            node,
        )

        email_subject = self._extract_value(
            email_config.email_subject,
            getattr(email_config, "email_subject_source_mode", "static"),
            getattr(email_config, "email_subject_source_node_id", None),
            getattr(email_config, "email_subject_field_path", None),
            email_config.email_subject or f"Action Required: {node.name}",
            state,
            graph,
            node,
        )

        email_body = self._extract_value(
            email_config.email_body_template,
            getattr(email_config, "email_body_source_mode", "static"),
            getattr(email_config, "email_body_source_node_id", None),
            getattr(email_config, "email_body_field_path", None),
            email_config.email_body_template
            or "Please respond to this email to continue the workflow.",
            state,
            graph,
            node,
        )

        # Apply template variables
        if "{{input}}" in email_body:
            email_body = email_body.replace("{{input}}", input_message)
        if "{{workflow_name}}" in email_body:
            email_body = email_body.replace("{{workflow_name}}", graph.name)

        email_checkpoint_logger.info(
            f"[EMAIL-CHECKPOINT] Resolved email fields: "
            f"recipient='{recipient_email}', "
            f"subject='{email_subject}', "
            f"body_length={len(email_body)}"
        )

        return recipient_email, email_subject, email_body

    async def _send_checkpoint_email(
        self,
        email_service,
        inbox: Optional[Any],
        recipient_email: str,
        email_subject: str,
        email_body: str,
        graph: "GraphData",
        ws_execution_id: str,
    ):
        """Send the checkpoint email."""
        use_workflow_mapping = inbox is None

        email_checkpoint_logger.info(
            f"[EMAIL-CHECKPOINT] Sending email: "
            f"routing={'workflow-mapping (Mailgun)' if use_workflow_mapping else 'inbox-based (MailSlurp)'}, "
            f"to='{recipient_email}', subject='{email_subject}'"
        )

        if use_workflow_mapping:
            # Use workflow-aware sending for Mailgun
            await email_service.send_email_with_workflow_id(
                workflow_id=graph.name,
                execution_id=ws_execution_id,
                to_address=recipient_email,
                subject=email_subject,
                body=email_body,
            )
            email_checkpoint_logger.info(
                f"Email sent with workflow tracking to {recipient_email}"
            )
        else:
            # Use regular inbox-based sending
            await email_service.send_email_from_inbox(
                inbox_id=inbox.inbox_id,
                to_address=recipient_email,
                subject=email_subject,
                body=email_body,
            )
            email_checkpoint_logger.info(f"Email sent to {recipient_email}")

    def _log_webhook_info(self, ws_execution_id: str, email_service):
        """Log webhook endpoint information."""
        webhook_base_url = os.getenv("EMAIL_WEBHOOK_BASE_URL", "http://localhost:8000")
        webhook_url = f"{webhook_base_url}/api/email/webhooks/callback"
        domain = getattr(email_service, "domain", "mailgun")

        email_checkpoint_logger.info(f"Ready to receive webhooks at: {webhook_url}")
        email_checkpoint_logger.info(
            f"Email Reply-To: workflow-{ws_execution_id}@{domain}"
        )

    def _create_email_checkpoint_record(
        self,
        db_execution_id: Optional[int],
        node: EnhancedNodeData,
        state: WorkflowState,
        input_message: str,
        current_iteration: int,
        inbox: Optional[Any],
        reply_to_address: str,
        email_config,
        ws_execution_id: str,
        email_service,
    ) -> Optional[int]:
        """Create database record for email checkpoint."""
        if not db_execution_id:
            return None

        try:
            from backend.services.execution.history import ExecutionHistoryService
            from backend.services.execution.state import StateExecutionTracker

            current_order = StateExecutionTracker.get_execution_order(state)

            node_metadata = {
                "await_mode": "email",
                "inbox_id": inbox.inbox_id if inbox else ws_execution_id,
                "reply_to_address": reply_to_address,
                "webhook_id": None,  # No longer creating webhooks
                "email_sent": True,
                "email_config": {
                    "extract_mode": email_config.extract_mode,
                    "extraction_pattern": email_config.extraction_pattern,
                },
                "iteration": current_iteration,
            }

            node_exec = ExecutionHistoryService.create_node_execution(
                graph_execution_id=db_execution_id,
                node_id=node.uniq_id,
                node_name=node.name,
                node_type="CHECKPOINT",
                execution_order=current_order,
                input_data={"message": input_message},
                node_metadata=node_metadata,
            )
            node_exec_id = node_exec["id"]
            ExecutionHistoryService.start_node_execution(node_exec_id)

            # Track for pause handling
            exec_id = state.get("execution_id")
            if exec_id in self.active_executions:
                self.active_executions[exec_id]["node_execution_map"][node.uniq_id] = (
                    node_exec_id
                )

            email_checkpoint_logger.info(
                f"Node execution created, waiting for email at: {reply_to_address}"
            )

            return node_exec_id

        except Exception as e:
            email_checkpoint_logger.error(f"Failed to create node execution: {e}")
            return None

    async def _pause_for_email_response(
        self,
        node: EnhancedNodeData,
        reply_to_address: str,
        inbox: Optional[Any],
    ) -> Any:
        """Pause execution and wait for email response."""
        from langgraph.types import interrupt

        webhook_id = None  # No longer creating webhooks

        answer = interrupt(
            {
                "type": "email_checkpoint",
                "prompt": f"Waiting for email response at: {reply_to_address}",
                "node_id": node.uniq_id,
                "node_name": node.name,
                "inbox_address": reply_to_address,
                "webhook_id": webhook_id,
            }
        )

        email_checkpoint_logger.info(f"Resumed with email content: {answer}")
        return answer

    async def _cleanup_email_resources(self, email_service, inbox: Optional[Any]):
        """Clean up email inbox if needed."""
        if inbox:
            try:
                await email_service.delete_inbox(inbox.inbox_id)
                email_checkpoint_logger.info("Cleaned up inbox")
            except Exception as e:
                email_checkpoint_logger.warning(f"Failed to clean up inbox: {e}")

    def _fallback_to_manual_checkpoint(
        self, node: EnhancedNodeData, state: WorkflowState, error: str
    ) -> Dict[str, Any]:
        """Fallback to manual checkpoint on email error."""
        from langgraph.types import interrupt

        email_checkpoint_logger.warning(
            f"[EMAIL-CHECKPOINT] Falling back to manual checkpoint for '{node.name}': {error}"
        )

        prompt = f"Email checkpoint failed. {node.checkpoint_config.prompt if hasattr(node, 'checkpoint_config') else 'Please provide input.'}"

        answer = interrupt(
            {
                "type": "checkpoint",
                "prompt": prompt,
                "node_id": node.uniq_id,
                "node_name": node.name,
                "error": error,
            }
        )

        # Get current iteration and build result
        current_iteration = self.get_current_iteration(node, state)
        return self.build_checkpoint_result(answer, state, node, current_iteration)

    def _extract_value(
        self,
        value: str,
        source_mode: str,
        source_node_id: Optional[str],
        source_field_path: Optional[str],
        default: str,
        state: WorkflowState,
        graph: "GraphData",
        node: EnhancedNodeData,
    ) -> str:
        """
        Extract value based on source mode.

        Same logic as EMAIL_SEND nodes for consistency.
        """
        if source_mode == "static":
            return value or default

        elif source_mode == "previous":
            prev_output = self._get_previous_node_output(node, state, graph)
            if source_field_path and prev_output:
                return self.field_extractor.extract(
                    prev_output, source_field_path, default
                )
            return prev_output.get("raw", default) if prev_output else default

        elif source_mode == "specific" and source_node_id:
            node_outputs = state.get("node_outputs", {})
            specific_output = node_outputs.get(source_node_id, {})
            if source_field_path and specific_output:
                return self.field_extractor.extract(
                    specific_output, source_field_path, default
                )
            return specific_output.get("raw", default) if specific_output else default

        elif source_mode == "field" and source_field_path:
            return self._extract_field_from_state(state, source_field_path, default)

        return default

    def _get_previous_node_output(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> Optional[Dict[str, Any]]:
        """Get output from previous node."""
        # Find the previous node in the workflow
        for conn in graph.connections:
            if conn.target_id == node.uniq_id:
                return state.get("node_outputs", {}).get(conn.source_id)
        return None

    def _extract_field_from_state(
        self, state: WorkflowState, field_path: str, default: str
    ) -> str:
        """Extract field from workflow state using field path."""
        try:
            current = state
            for part in field_path.split("."):
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return default
                if current is None:
                    return default
            return str(current) if current is not None else default
        except Exception:
            return default

    def _get_email_config(self, node: EnhancedNodeData):
        """Extract email config from checkpoint node."""
        if not hasattr(node, "checkpoint_config") or not node.checkpoint_config:
            email_checkpoint_logger.warning(
                f"[EMAIL-CHECKPOINT] Node '{node.name}' has no checkpoint_config"
            )
            return None

        email_config = getattr(node.checkpoint_config, "email_config", None)
        if email_config is None:
            email_checkpoint_logger.warning(
                f"[EMAIL-CHECKPOINT] Node '{node.name}' checkpoint_config has no email_config"
            )
        else:
            email_checkpoint_logger.info(
                f"[EMAIL-CHECKPOINT] Node '{node.name}' email_config: "
                f"enabled={email_config.enabled}, "
                f"provider={getattr(email_config, 'email_provider', 'not set')}, "
                f"recipient={'set' if getattr(email_config, 'recipient_email', '') else 'empty'}, "
                f"send_email={getattr(email_config, 'send_email', 'not set')}"
            )
        return email_config
