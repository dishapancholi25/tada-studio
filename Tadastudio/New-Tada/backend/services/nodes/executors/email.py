"""
Email Node Executor.

This module handles execution of EMAIL_SEND nodes, including:
- Dynamic field extraction (to, from, subject, body) from state/previous nodes
- Template variable substitution
- HTML email support
- Email provider integration (Mailgun)
- Database tracking and WebSocket notifications
"""

import re
import time
from typing import Any, Dict, Optional, Union

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.feature_flags import (
    EMAIL_COMING_SOON_MESSAGE,
    EMAIL_FEATURE_ENABLED,
)
from backend.services.workflow.state import WorkflowState

from ..base import BaseNodeExecutor
from ..handlers import NodeDatabaseTracker, NodeNotificationHandler


email_executor_logger = get_logger("nodes.executors.email")


class EmailNodeExecutor(BaseNodeExecutor):
    """
    Executor for EMAIL_SEND nodes.

    Handles email sending with comprehensive features including:
    - Dynamic field extraction from workflow state
    - Template variable substitution
    - HTML email support
    - Provider integration (Mailgun)
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """Initialize email node executor."""
        super().__init__(
            execution_history_service, ws_notifier, subgraph_executor, graph_manager
        )
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an email send node.

        Args:
            node: The email send node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            State updates with email send results
        """
        email_executor_logger.info(f"Executing EMAIL_SEND node: {node.name}")
        execution_start_time = time.time()

        # Create tracking record
        node_exec_id = await self._create_tracking_record(node, state, graph)

        try:
            if not EMAIL_FEATURE_ENABLED:
                raise ValueError(EMAIL_COMING_SOON_MESSAGE)

            # Validate and parse configuration
            config = self._validate_config(node)
            email_config = self._parse_config(config)

            # Extract email fields from state
            email_fields = self._extract_email_fields(email_config, state, graph)

            # Apply template substitution if enabled
            if email_config.use_template and email_config.template_variables:
                email_fields = self._apply_template_variables(
                    email_fields, email_config.template_variables, state, graph
                )

            # Send email via provider
            result = await self._send_email(email_fields, user_id)

            # Build output
            node_output = self._build_email_output(result, email_fields)

            # Complete tracking
            execution_duration = time.time() - execution_start_time
            await self._complete_tracking(
                node, state, node_exec_id, node_output, execution_duration
            )

            # Return state update
            return self._build_state_update(node_output, state, email_fields)

        except Exception as e:
            email_executor_logger.error(
                f"EMAIL_SEND error for {node.name}: {e}", exc_info=True
            )
            return await self._handle_error(node, state, node_exec_id, str(e))

    def _validate_config(self, node: EnhancedNodeData) -> Union[Dict, Any]:
        """
        Validate email configuration exists.

        Args:
            node: The email send node

        Returns:
            Email configuration object

        Raises:
            ValueError: If configuration is missing
        """
        config = node.email_send_config
        if not config:
            raise ValueError("Email send configuration is missing")
        return config

    def _parse_config(self, config: Union[Dict, Any]) -> "EmailConfig":
        """
        Parse configuration from dict or dataclass into standard format.

        Args:
            config: Configuration as dict or dataclass

        Returns:
            EmailConfig with normalized values
        """
        # Create helper to get values from dict or dataclass
        if isinstance(config, dict):

            def get_value(key, default=None):
                return config.get(key, default)
        else:

            def get_value(key, default=None):
                return getattr(config, key, default)

        return EmailConfig(
            to_address=get_value("to_address", ""),
            to_source_mode=get_value("to_source_mode", "static"),
            to_source_node_id=get_value("to_source_node_id"),
            to_source_field_path=get_value("to_source_field_path"),
            subject=get_value("subject", ""),
            subject_source_mode=get_value("subject_source_mode", "static"),
            subject_source_node_id=get_value("subject_source_node_id"),
            subject_source_field_path=get_value("subject_source_field_path"),
            body=get_value("body", ""),
            body_source_mode=get_value("body_source_mode", "static"),
            body_source_node_id=get_value("body_source_node_id"),
            body_source_field_path=get_value("body_source_field_path"),
            from_address=get_value("from_address", ""),
            from_source_mode=get_value("from_source_mode", "static"),
            from_source_node_id=get_value("from_source_node_id"),
            from_source_field_path=get_value("from_source_field_path"),
            reply_to=get_value("reply_to", ""),
            reply_to_source_mode=get_value("reply_to_source_mode", "static"),
            reply_to_source_node_id=get_value("reply_to_source_node_id"),
            reply_to_source_field_path=get_value("reply_to_source_field_path"),
            use_html=get_value("use_html", False),
            html_body=get_value("html_body", ""),
            html_body_source_mode=get_value("html_body_source_mode", "static"),
            html_body_source_node_id=get_value("html_body_source_node_id"),
            html_body_source_field_path=get_value("html_body_source_field_path"),
            use_template=get_value("use_template", False),
            template_variables=get_value("template_variables", {}),
        )

    def _extract_email_fields(
        self, config: "EmailConfig", state: WorkflowState, graph: Any
    ) -> "EmailFields":
        """
        Extract email fields from workflow state based on configuration.

        Args:
            config: Email configuration
            state: Current workflow state
            graph: The graph definition

        Returns:
            EmailFields with extracted values
        """
        to_address = self._extract_value(
            config.to_address,
            config.to_source_mode,
            config.to_source_node_id,
            config.to_source_field_path,
            state,
            graph,
            default="",
        )

        subject = self._extract_value(
            config.subject,
            config.subject_source_mode,
            config.subject_source_node_id,
            config.subject_source_field_path,
            state,
            graph,
            default="Email notification",
        )

        body = self._extract_value(
            config.body,
            config.body_source_mode,
            config.body_source_node_id,
            config.body_source_field_path,
            state,
            graph,
            default="No body content",
        )

        from_address = self._extract_value(
            config.from_address,
            config.from_source_mode,
            config.from_source_node_id,
            config.from_source_field_path,
            state,
            graph,
            default="",
        )

        reply_to = self._extract_value(
            config.reply_to,
            config.reply_to_source_mode,
            config.reply_to_source_node_id,
            config.reply_to_source_field_path,
            state,
            graph,
            default="",
        )

        html_body = None
        if config.use_html:
            html_body = self._extract_value(
                config.html_body,
                config.html_body_source_mode,
                config.html_body_source_node_id,
                config.html_body_source_field_path,
                state,
                graph,
                default="",
            )

        return EmailFields(
            to=to_address,
            subject=subject,
            body=body,
            from_address=from_address,
            reply_to=reply_to,
            html_body=html_body,
        )

    def _extract_value(
        self,
        value: str,
        source_mode: str,
        source_node_id: Optional[str],
        source_field_path: Optional[str],
        state: WorkflowState,
        graph: Any,
        default: str = "",
    ) -> str:
        """
        Extract a value based on source mode.

        Args:
            value: Static value (if source_mode is static)
            source_mode: How to extract value (static/previous/specific/field)
            source_node_id: Source node ID (for specific mode)
            source_field_path: Field path to extract
            state: Current workflow state
            graph: The graph definition
            default: Default value if extraction fails

        Returns:
            Extracted value
        """
        # Use field extractor for extraction logic
        from backend.services.io import FieldExtractor

        field_extractor = FieldExtractor()

        if source_mode == "static":
            return value or default

        elif source_mode == "previous":
            # Get the previous node's output from state
            node_outputs = state.get("node_outputs", {})
            if not node_outputs:
                return default

            # Find the most recent node output (last in execution order)
            sorted_outputs = sorted(
                node_outputs.items(),
                key=lambda x: x[1].get("execution_order", 0)
                if isinstance(x[1], dict)
                else 0,
                reverse=True,
            )

            if sorted_outputs:
                prev_output = sorted_outputs[0][1]
                if source_field_path and prev_output:
                    return field_extractor.extract(
                        prev_output, source_field_path, default
                    )
                return (
                    prev_output.get("raw", default)
                    if isinstance(prev_output, dict)
                    else default
                )
            return default

        elif source_mode == "specific" and source_node_id:
            node_outputs = state.get("node_outputs", {})
            specific_output = node_outputs.get(source_node_id, {})
            if source_field_path and specific_output:
                return field_extractor.extract(
                    specific_output, source_field_path, default
                )
            return (
                specific_output.get("raw", default)
                if isinstance(specific_output, dict)
                else default
            )

        elif source_mode == "field" and source_field_path:
            # Extract field from state using dot notation
            return field_extractor.extract(state, source_field_path, default)

        return default

    def _apply_template_variables(
        self,
        email_fields: "EmailFields",
        template_variables: Dict,
        state: WorkflowState,
        graph: Any,
    ) -> "EmailFields":
        """
        Apply template variable substitution to email fields.

        Args:
            email_fields: Email fields to process
            template_variables: Template variable definitions
            state: Current workflow state
            graph: The graph definition

        Returns:
            EmailFields with substituted values
        """
        # Process each template variable
        substitutions = {}
        for var_name, var_value in template_variables.items():
            # Extract variable value if it's a reference
            if isinstance(var_value, dict) and "source_mode" in var_value:
                var_value = self._extract_value(
                    var_value.get("value", ""),
                    var_value.get("source_mode", "static"),
                    var_value.get("source_node_id"),
                    var_value.get("source_field_path"),
                    state,
                    graph,
                    default="",
                )
            substitutions[var_name] = str(var_value)

        # Apply substitutions to body and html_body
        body = email_fields.body
        html_body = email_fields.html_body

        for var_name, var_value in substitutions.items():
            pattern = r"\{\{" + re.escape(var_name) + r"\}\}"
            body = re.sub(pattern, var_value, body)
            if html_body:
                html_body = re.sub(pattern, var_value, html_body)

        return EmailFields(
            to=email_fields.to,
            subject=email_fields.subject,
            body=body,
            from_address=email_fields.from_address,
            reply_to=email_fields.reply_to,
            html_body=html_body,
        )

    async def _send_email(
        self, email_fields: "EmailFields", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email via provider.

        Args:
            email_fields: Email fields to send
            user_id: User identifier for retrieving email configuration

        Returns:
            Provider response dictionary
        """
        from backend.services.email.credential_resolver import (
            resolve_email_provider_config,
        )
        from backend.services.email.providers.factory import EmailServiceFactory

        # Resolve provider config from user-tier, then system-tier, then env vars
        provider_name, provider_kwargs = resolve_email_provider_config(user_id)

        # Create provider
        email_provider = EmailServiceFactory.create_provider(
            provider_name, **provider_kwargs
        )

        # Set from address with domain/default if not specified
        from_address = email_fields.from_address
        if not from_address:
            # Use provider's default sender if available
            if hasattr(email_provider, "sender_email") and email_provider.sender_email:
                from_address = email_provider.sender_email
            elif hasattr(
                email_provider, "domain"
            ):  # provided for Mailgun and computed for Outlook
                from_address = f"AgenticStudio <noreply@{email_provider.domain}>"
            elif provider_name == "mailslurp":
                # MailSlurp uses domain pool — from_address is optional
                from_address = from_address or ""
            else:
                raise ValueError("Email send configuration is missing")

        email_executor_logger.info(
            f"Sending email to {email_fields.to} with subject: {email_fields.subject}"
        )

        result = await email_provider.send_email(
            from_address=from_address,
            to_address=email_fields.to,
            subject=email_fields.subject,
            body=email_fields.body,
            html_body=email_fields.html_body,
            reply_to=email_fields.reply_to if email_fields.reply_to else None,
        )

        return result

    def _build_email_output(
        self, result: Dict[str, Any], email_fields: "EmailFields"
    ) -> Dict[str, Any]:
        """
        Build email output dictionary.

        Args:
            result: Provider response
            email_fields: Email fields that were sent

        Returns:
            Node output dictionary
        """
        node_output = {
            "message_id": result.get("id", ""),
            "to": email_fields.to,
            "subject": email_fields.subject,
            "status": "sent",
            "provider_response": result,
        }

        email_executor_logger.info(f"EMAIL_SEND completed successfully: {node_output}")
        return node_output

    async def _create_tracking_record(
        self, node: EnhancedNodeData, state: WorkflowState, graph: Any
    ) -> Optional[int]:
        """
        Create database tracking record and send start notification.

        Args:
            node: The email send node
            state: Current workflow state
            graph: The graph definition

        Returns:
            Node execution ID, or None if tracking disabled
        """
        # Build input for tracking using InputBuilder
        from backend.services.io import InputBuilder

        input_builder = InputBuilder()
        input_message = input_builder.build(node, state, graph)

        # Get review iteration from state (set by upstream agent nodes)
        review_iteration = state.get("current_review_iteration")

        node_exec_id = await self.database_tracker.create_node_execution(
            node,
            state,
            "EMAIL_SEND",
            {"message": input_message},
            review_iteration=review_iteration,
        )

        # Send start notification
        if node_exec_id:
            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_start(
                node,
                state,
                "EMAIL_SEND",
                node_exec_id=node_exec_id,
                execution_order=current_order,
            )

        return node_exec_id

    async def _complete_tracking(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        node_output: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """
        Complete database tracking and send completion notification.

        Args:
            node: The email send node
            state: Current workflow state
            node_exec_id: Database node execution ID
            node_output: Output data from email send
            duration_seconds: Execution duration
        """
        # Complete database record
        await self.database_tracker.complete_node_execution(
            node_exec_id, node_output, None
        )

        # Send completion notification
        if node_exec_id:
            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_complete(
                node,
                state,
                node_output,
                "EMAIL_SEND",
                node_exec_id=node_exec_id,
                duration_seconds=duration_seconds,
                execution_order=current_order,
            )

    def _build_state_update(
        self,
        node_output: Dict[str, Any],
        state: WorkflowState,
        email_fields: "EmailFields",
    ) -> Dict[str, Any]:
        """
        Build state update dictionary.

        Args:
            node_output: Output from email send
            state: Current workflow state
            email_fields: Email fields that were sent

        Returns:
            State update dictionary
        """
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": f"Email sent to {email_fields.to}",
                "structured": node_output,
                "fields": node_output,
            },
            **order_update,
        }

    async def _handle_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Handle email send error.

        Args:
            node: The email send node
            state: Current workflow state
            node_exec_id: Database node execution ID
            error_message: Error message

        Returns:
            Error state update
        """
        from backend.services.execution.history import ExecutionHistoryService

        error_output = {"error": error_message, "status": "failed", "node": node.name}

        # Mark as failed in database
        if node_exec_id:
            try:
                ExecutionHistoryService.complete_node_execution(
                    node_exec_id,
                    status="failed",
                    error_message=error_message,
                    output_data=error_output,
                )
            except Exception as db_error:
                email_executor_logger.error(
                    f"Failed to mark EMAIL_SEND node as failed: {db_error}"
                )

        # Send error notification
        await self.notification_handler.notify_error(
            node, state, error_message, "EMAIL_SEND"
        )

        # Build error state update
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": f"Email send failed: {error_message}",
                "structured": error_output,
                "fields": error_output,
            },
            **order_update,
        }


# Helper data classes for internal use
class EmailConfig:
    """Configuration for email sending."""

    def __init__(
        self,
        to_address: str,
        to_source_mode: str,
        to_source_node_id: Optional[str],
        to_source_field_path: Optional[str],
        subject: str,
        subject_source_mode: str,
        subject_source_node_id: Optional[str],
        subject_source_field_path: Optional[str],
        body: str,
        body_source_mode: str,
        body_source_node_id: Optional[str],
        body_source_field_path: Optional[str],
        from_address: str,
        from_source_mode: str,
        from_source_node_id: Optional[str],
        from_source_field_path: Optional[str],
        reply_to: str,
        reply_to_source_mode: str,
        reply_to_source_node_id: Optional[str],
        reply_to_source_field_path: Optional[str],
        use_html: bool,
        html_body: str,
        html_body_source_mode: str,
        html_body_source_node_id: Optional[str],
        html_body_source_field_path: Optional[str],
        use_template: bool,
        template_variables: Dict,
    ):
        """Initialize email configuration."""
        self.to_address = to_address
        self.to_source_mode = to_source_mode
        self.to_source_node_id = to_source_node_id
        self.to_source_field_path = to_source_field_path
        self.subject = subject
        self.subject_source_mode = subject_source_mode
        self.subject_source_node_id = subject_source_node_id
        self.subject_source_field_path = subject_source_field_path
        self.body = body
        self.body_source_mode = body_source_mode
        self.body_source_node_id = body_source_node_id
        self.body_source_field_path = body_source_field_path
        self.from_address = from_address
        self.from_source_mode = from_source_mode
        self.from_source_node_id = from_source_node_id
        self.from_source_field_path = from_source_field_path
        self.reply_to = reply_to
        self.reply_to_source_mode = reply_to_source_mode
        self.reply_to_source_node_id = reply_to_source_node_id
        self.reply_to_source_field_path = reply_to_source_field_path
        self.use_html = use_html
        self.html_body = html_body
        self.html_body_source_mode = html_body_source_mode
        self.html_body_source_node_id = html_body_source_node_id
        self.html_body_source_field_path = html_body_source_field_path
        self.use_template = use_template
        self.template_variables = template_variables


class EmailFields:
    """Extracted email fields ready for sending."""

    def __init__(
        self,
        to: str,
        subject: str,
        body: str,
        from_address: str,
        reply_to: str,
        html_body: Optional[str],
    ):
        """Initialize email fields."""
        self.to = to
        self.subject = subject
        self.body = body
        self.from_address = from_address
        self.reply_to = reply_to
        self.html_body = html_body
