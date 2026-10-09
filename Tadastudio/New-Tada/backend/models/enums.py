"""Enumeration types used across models.

This module contains all enum definitions used by the application models.
"""

import enum


class DatabaseType(enum.Enum):
    """Supported database types for datasource connections.

    Attributes:
        POSTGRES: PostgreSQL database.
        MYSQL: MySQL database.
        MONGODB: MongoDB database.
        SQLITE: SQLite database.
        MSSQL: Microsoft SQL Server database.
        ORACLE: Oracle database.
    """

    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"
    MSSQL = "mssql"
    ORACLE = "oracle"


class WorkflowRole(enum.Enum):
    """Roles for workflow access control.

    Attributes:
        OWNER: Full control over the workflow.
        EDITOR: Can edit workflow but not manage permissions.
        VIEWER: Read-only access to workflow.
    """

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class AccessRequestStatus(enum.Enum):
    """Status of an access request.

    Attributes:
        PENDING: Request is awaiting owner decision.
        APPROVED: Request was approved by owner.
        REJECTED: Request was rejected by owner.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
