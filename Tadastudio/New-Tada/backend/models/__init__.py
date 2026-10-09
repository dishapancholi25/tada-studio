"""SQLAlchemy ORM models for the LangGraph application.

This package contains all database models organized by domain:
- execution: Graph and node execution tracking
- memory: Agent memory and conversation history
- configuration: Model deployments and datasource connections
- documents: Document collections, documents, and chunks
- workflows: Workflows, memberships, and graph definitions
- auth: User authentication and resource memberships
- wiki: Wiki pages and revisions

The models are designed to work with PostgreSQL and use pgvector
for embedding storage.
"""

# Chat models
from .chat import ChatSession

# Auth models
from .auth import (
    DataSourceConnectionMembership,
    DocumentCollectionMembership,
    Group,
    GroupMembership,
    User,
    UserAPIToken,
)

# Base classes and enums
from .base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin, generate_uuid

# Configuration models
from .configuration import (
    ApiEndpoint,
    DataSourceConnection,
    DataSourceQueryHistory,
    ModelDeployment,
)

# Document models
from .documents import Document, DocumentChunk, DocumentCollection

# Email models
from .email import EmailInboxOwnership, EmailWebhookOwnership
from .enums import AccessRequestStatus, DatabaseType, WorkflowRole

# Execution models
from .execution import (
    CheckpointMetadata,
    ExecutionFeedback,
    ExecutionFile,
    ExecutionSummary,
    GraphExecution,
    NodeExecution,
)

# Memory models
from .memory import AgentMemoryProfile, ConversationMemory

# Guardrail policy models
from .guardrails import (
    GuardrailAssignment,
    GuardrailPolicy,
    GuardrailPolicyVersion,
    GuardrailViolation,
    GuardrailViolationEvent,
    GuardrailViolationFeedback,
)

# Evaluation models
from .evaluation import (
    ChatResponseScore,
    EvaluationDataset,
    EvaluationRecommendation,
    EvaluationResult,
    EvaluationRun,
    EvaluationTestCase,
)

# Wiki models
from .wiki import WikiPage, WikiRevision

# Workflow models
from .workflows import (
    AccessRequest,
    AgentTemplate,
    GraphDefinition,
    NodeVersionIndex,
    Workflow,
    WorkflowAsset,
    WorkflowMembership,
    WorkflowTemplate,
)

# Workflow publishing models
from .workflows.publishing import (
    PublishedWorkflow,
    WorkflowAccessLog,
    WorkflowAuthToken,
)


__all__ = [
    # Chat
    "ChatSession",
    # Base classes and utilities
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    "generate_uuid",
    # Enums
    "AccessRequestStatus",
    "DatabaseType",
    "WorkflowRole",
    # Execution
    "ExecutionFeedback",
    "ExecutionFile",
    "GraphExecution",
    "NodeExecution",
    "ExecutionSummary",
    "CheckpointMetadata",
    # Memory
    "ConversationMemory",
    "AgentMemoryProfile",
    # Configuration
    "ModelDeployment",
    "DataSourceConnection",
    "DataSourceQueryHistory",
    "ApiEndpoint",
    # Documents
    "DocumentCollection",
    "Document",
    "DocumentChunk",
    # Email
    "EmailInboxOwnership",
    "EmailWebhookOwnership",
    # Workflows
    "AccessRequest",
    "Workflow",
    "WorkflowAsset",
    "WorkflowMembership",
    "GraphDefinition",
    "WorkflowTemplate",
    "AgentTemplate",
    "NodeVersionIndex",
    # Publishing
    "PublishedWorkflow",
    "WorkflowAuthToken",
    "WorkflowAccessLog",
    # Auth
    "User",
    "UserAPIToken",
    "Group",
    "GroupMembership",
    "DocumentCollectionMembership",
    "DataSourceConnectionMembership",
    # Guardrail policies
    "GuardrailPolicy",
    "GuardrailAssignment",
    "GuardrailPolicyVersion",
    "GuardrailViolation",
    "GuardrailViolationEvent",
    "GuardrailViolationFeedback",
    # Evaluation
    "EvaluationDataset",
    "EvaluationTestCase",
    "EvaluationRun",
    "EvaluationResult",
    "EvaluationRecommendation",
    "ChatResponseScore",
    # Wiki
    "WikiPage",
    "WikiRevision",
]
