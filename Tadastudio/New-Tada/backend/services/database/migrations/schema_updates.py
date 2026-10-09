"""Schema update migrations.

This module contains individual schema migration functions that are idempotent
and can be safely run multiple times.
"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.services.wiki.seed_data import WIKI_SEED_PAGES

logger = logging.getLogger(__name__)
LOG_PREFIX = "[DATABASE-MIGRATION]"


def add_thread_id_column(conn: Connection) -> None:
    """Add thread_id column to graph_executions table.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='graph_executions' AND column_name='thread_id'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding thread_id column to graph_executions", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE graph_executions
                    ADD COLUMN thread_id VARCHAR
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_graph_executions_thread_id
                    ON graph_executions(thread_id)
                """)
            )
            conn.commit()
            logger.info("%s Added thread_id column successfully", LOG_PREFIX)
        else:
            logger.debug("%s thread_id column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add thread_id column: %s", LOG_PREFIX, e)


def add_is_sub_agent_column(conn: Connection) -> None:
    """Add is_sub_agent column to node_executions table.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='node_executions' AND column_name='is_sub_agent'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding is_sub_agent column to node_executions", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE node_executions
                    ADD COLUMN is_sub_agent BOOLEAN DEFAULT FALSE
                """)
            )
            conn.commit()
            logger.info("%s Added is_sub_agent column successfully", LOG_PREFIX)
        else:
            logger.debug("%s is_sub_agent column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add is_sub_agent column: %s", LOG_PREFIX, e)


def add_token_counting_columns(conn: Connection) -> None:
    """Add token counting columns to node_executions table.

    Adds input_tokens, output_tokens, total_tokens, and token_metadata columns.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='node_executions' AND column_name='input_tokens'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding token counting columns to node_executions", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE node_executions
                    ADD COLUMN input_tokens INTEGER,
                    ADD COLUMN output_tokens INTEGER,
                    ADD COLUMN total_tokens INTEGER,
                    ADD COLUMN token_metadata JSON
                """)
            )
            conn.commit()
            logger.info("%s Added token counting columns successfully", LOG_PREFIX)
        else:
            logger.debug("%s Token counting columns already exist", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add token counting columns: %s", LOG_PREFIX, e)


def add_websocket_execution_id_column(conn: Connection) -> None:
    """Add websocket_execution_id column to graph_executions table.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='graph_executions'
                AND column_name='websocket_execution_id'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding websocket_execution_id column to graph_executions",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE graph_executions
                    ADD COLUMN websocket_execution_id VARCHAR UNIQUE
                """)
            )
            conn.execute(
                text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_graph_executions_websocket_id
                    ON graph_executions(websocket_execution_id)
                    WHERE websocket_execution_id IS NOT NULL
                """)
            )
            conn.commit()
            logger.info(
                "%s Added websocket_execution_id column successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s websocket_execution_id column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not add websocket_execution_id column: %s", LOG_PREFIX, e
        )


def add_trace_viewer_columns(conn: Connection) -> None:
    """Add trace viewer metadata columns to node_executions table.

    Adds columns for LLM metadata, message structure, tool metadata,
    orchestration metadata, memory metadata, environment metadata,
    cost tracking, and performance metrics.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='node_executions' AND column_name='llm_metadata'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding trace viewer metadata columns", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE node_executions
                    ADD COLUMN IF NOT EXISTS llm_metadata JSONB,
                    ADD COLUMN IF NOT EXISTS message_structure JSONB,
                    ADD COLUMN IF NOT EXISTS tool_metadata JSONB,
                    ADD COLUMN IF NOT EXISTS orchestration_metadata JSONB,
                    ADD COLUMN IF NOT EXISTS memory_metadata JSONB,
                    ADD COLUMN IF NOT EXISTS environment_metadata JSONB,
                    ADD COLUMN IF NOT EXISTS prompt_cost FLOAT,
                    ADD COLUMN IF NOT EXISTS completion_cost FLOAT,
                    ADD COLUMN IF NOT EXISTS total_cost FLOAT,
                    ADD COLUMN IF NOT EXISTS time_to_first_token FLOAT,
                    ADD COLUMN IF NOT EXISTS tokens_per_second FLOAT
                """)
            )
            conn.commit()
            logger.info("%s Added trace viewer metadata columns", LOG_PREFIX)

            # Add indexes for better performance
            logger.info("%s Adding trace viewer indexes", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_node_executions_llm_model
                    ON node_executions ((llm_metadata->>'model'))
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_node_executions_total_cost
                    ON node_executions (total_cost)
                    WHERE total_cost IS NOT NULL
                """)
            )
            conn.commit()
            logger.info("%s Added trace viewer indexes successfully", LOG_PREFIX)
        else:
            logger.debug("%s Trace viewer columns already exist", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add trace viewer columns: %s", LOG_PREFIX, e)


def add_workflow_id_column(conn: Connection) -> None:
    """Add workflow_id column to graph_definitions table.

    Adds workflow_id column with index and foreign key constraint.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='graph_definitions' AND column_name='workflow_id'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding workflow_id column to graph_definitions", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE graph_definitions
                    ADD COLUMN workflow_id VARCHAR
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_graph_definitions_workflow_id
                    ON graph_definitions(workflow_id)
                """)
            )
            conn.commit()
            logger.info("%s Added workflow_id column successfully", LOG_PREFIX)
        else:
            # Ensure index exists even if column exists
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_graph_definitions_workflow_id
                    ON graph_definitions(workflow_id)
                """)
            )
            conn.commit()
            logger.debug("%s workflow_id column already exists", LOG_PREFIX)

        # Add foreign key constraint if it doesn't exist
        constraint_exists = conn.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name='graph_definitions'
                  AND constraint_type='FOREIGN KEY'
                  AND constraint_name='fk_graph_definitions_workflow_id'
            """)
        )

        if not constraint_exists.fetchone():
            try:
                logger.info("%s Adding workflow foreign key constraint", LOG_PREFIX)
                conn.execute(
                    text("""
                        ALTER TABLE graph_definitions
                        ADD CONSTRAINT fk_graph_definitions_workflow_id
                        FOREIGN KEY (workflow_id)
                        REFERENCES workflows(id)
                        ON DELETE SET NULL
                    """)
                )
                conn.commit()
                logger.info("%s Added workflow foreign key constraint", LOG_PREFIX)
            except Exception as fk_error:
                logger.warning(
                    "%s Could not add workflow foreign key: %s", LOG_PREFIX, fk_error
                )
        else:
            logger.debug(
                "%s Workflow foreign key constraint already exists", LOG_PREFIX
            )

    except Exception as e:
        logger.warning("%s Could not add workflow_id column: %s", LOG_PREFIX, e)


def enable_pgvector_extension(conn: Connection) -> None:
    """Enable pgvector extension for vector similarity search.

    Args:
        conn: Database connection
    """
    try:
        logger.info("%s Enabling pgvector extension", LOG_PREFIX)
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        logger.info("%s pgvector extension enabled successfully", LOG_PREFIX)
    except Exception as e:
        # This is expected when multiple workers try to create the extension
        if "tuple concurrently updated" in str(e) or "already exists" in str(e):
            logger.debug("%s pgvector extension already enabled", LOG_PREFIX)
        else:
            logger.warning("%s Could not enable pgvector extension: %s", LOG_PREFIX, e)


def create_user_api_tokens_table(conn: Connection) -> None:
    """Create user_api_tokens table for Personal Access Tokens (PATs).

    This table stores user-generated API tokens that inherit user permissions
    and can be used to authenticate HTTP execution requests.

    Args:
        conn: Database connection
    """
    try:
        # Check if table already exists
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='user_api_tokens'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating user_api_tokens table", LOG_PREFIX)

            # Create the table
            conn.execute(
                text("""
                    CREATE TABLE user_api_tokens (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token_hash VARCHAR NOT NULL,
                        token_prefix VARCHAR(12) NOT NULL,
                        token_name VARCHAR NOT NULL,
                        description TEXT,
                        scopes JSON NOT NULL DEFAULT '[]'::json,
                        expires_at TIMESTAMP WITH TIME ZONE,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        last_used_at TIMESTAMP WITH TIME ZONE,
                        last_used_ip VARCHAR,
                        usage_count BIGINT NOT NULL DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        created_by_user_id VARCHAR
                    )
                """)
            )

            # Create indexes for better performance
            logger.info("%s Creating indexes for user_api_tokens", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE INDEX idx_user_api_tokens_user_id
                    ON user_api_tokens(user_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_user_api_tokens_token_hash
                    ON user_api_tokens(token_hash)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_user_api_tokens_token_prefix
                    ON user_api_tokens(token_prefix)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_user_api_tokens_is_active
                    ON user_api_tokens(is_active)
                """)
            )

            # Create partial index for active, non-expired tokens
            conn.execute(
                text("""
                    CREATE INDEX idx_user_api_tokens_active_valid
                    ON user_api_tokens(user_id, token_hash)
                    WHERE is_active = TRUE
                    AND (expires_at IS NULL OR expires_at > NOW())
                """)
            )

            conn.commit()
            logger.info("%s Created user_api_tokens table successfully", LOG_PREFIX)
        else:
            logger.debug("%s user_api_tokens table already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not create user_api_tokens table: %s", LOG_PREFIX, e)


def create_agent_templates_table(conn: Connection) -> None:
    """Create agent_templates table if it does not already exist.

    Stores standalone agent templates that can be published to the library.
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='agent_templates'
            """)
        )

        if result.fetchone():
            logger.debug("%s agent_templates table already exists", LOG_PREFIX)
            return

        logger.info("%s Creating agent_templates table", LOG_PREFIX)
        conn.execute(
            text("""
                CREATE TABLE agent_templates (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    workflow_id VARCHAR REFERENCES workflows(id) ON DELETE SET NULL,
                    graph_definition_id VARCHAR NOT NULL REFERENCES graph_definitions(id) ON DELETE CASCADE,
                    created_by_user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
                    primary_agent_node_id VARCHAR,
                    primary_agent_label VARCHAR(255),
                    name VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    category JSON NOT NULL DEFAULT '[]'::json,
                    tags JSON NOT NULL DEFAULT '[]'::json,
                    complexity VARCHAR(50),
                    icon_color VARCHAR(50),
                    agent_metadata JSON NOT NULL DEFAULT '{}'::json,
                    usage_count INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 1,
                    parent_template_id VARCHAR REFERENCES agent_templates(id) ON DELETE SET NULL,
                    is_latest_version BOOLEAN NOT NULL DEFAULT TRUE,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        )

        logger.info("%s Creating indexes for agent_templates", LOG_PREFIX)
        conn.execute(
            text("""
                CREATE INDEX idx_agent_templates_workflow_id
                ON agent_templates(workflow_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX idx_agent_templates_graph_definition_id
                ON agent_templates(graph_definition_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX idx_agent_templates_primary_agent_node_id
                ON agent_templates(primary_agent_node_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX idx_agent_templates_created_by_user_id
                ON agent_templates(created_by_user_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX idx_agent_templates_is_active_latest
                ON agent_templates(is_active, is_latest_version)
            """)
        )

        conn.commit()
        logger.info("%s Created agent_templates table successfully", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not create agent_templates table: %s", LOG_PREFIX, e)


def add_workflow_template_name_column(conn: Connection) -> None:
    """Add name column to workflow_templates table.

    Adds a required name field for library workflow templates with a default
    placeholder for existing records.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='workflow_templates' AND column_name='name'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding name column to workflow_templates", LOG_PREFIX)

            # First, add the column as nullable with a default
            conn.execute(
                text("""
                    ALTER TABLE workflow_templates
                    ADD COLUMN name VARCHAR(255)
                """)
            )

            # Update existing rows to use workflow name or generate a placeholder
            conn.execute(
                text("""
                    UPDATE workflow_templates wt
                    SET name = COALESCE(
                        (SELECT w.name FROM workflows w WHERE w.id = wt.workflow_id),
                        'Untitled Template'
                    )
                    WHERE name IS NULL
                """)
            )

            # Now make the column non-nullable
            conn.execute(
                text("""
                    ALTER TABLE workflow_templates
                    ALTER COLUMN name SET NOT NULL
                """)
            )

            # Add index for better search performance
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_templates_name
                    ON workflow_templates(name)
                """)
            )

            conn.commit()
            logger.info("%s Added name column successfully", LOG_PREFIX)
        else:
            logger.debug("%s name column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add name column: %s", LOG_PREFIX, e)


def drop_workflow_template_estimated_time_column(conn: Connection) -> None:
    """Drop estimated_time column from workflow_templates table.

    Removes the estimated_time field as it's no longer needed.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='workflow_templates' AND column_name='estimated_time'
            """)
        )

        if result.fetchone():
            logger.info(
                "%s Dropping estimated_time column from workflow_templates", LOG_PREFIX
            )

            conn.execute(
                text("""
                    ALTER TABLE workflow_templates
                    DROP COLUMN estimated_time
                """)
            )

            conn.commit()
            logger.info("%s Dropped estimated_time column successfully", LOG_PREFIX)
        else:
            logger.debug("%s estimated_time column does not exist", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not drop estimated_time column: %s", LOG_PREFIX, e)


def convert_category_to_json_array(conn: Connection) -> None:
    """Convert category column from string to JSON array in workflow_templates.

    Migrates existing category string values to JSON arrays to support
    multiple categories per template.

    Args:
        conn: Database connection
    """
    try:
        # Check the current data type of the category column
        result = conn.execute(
            text("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name='workflow_templates' AND column_name='category'
            """)
        )

        row = result.fetchone()
        if not row:
            logger.debug("%s category column does not exist", LOG_PREFIX)
            return

        current_type = row[0]

        # If it's already JSON/JSONB, skip migration
        if current_type.lower() in ["json", "jsonb"]:
            logger.debug("%s category column is already JSON type", LOG_PREFIX)
            return

        logger.info(
            "%s Converting category column from string to JSON array", LOG_PREFIX
        )

        # Create a temporary column to hold the JSON array
        conn.execute(
            text("""
                ALTER TABLE workflow_templates
                ADD COLUMN category_temp JSON
            """)
        )

        # Convert existing string values to JSON arrays
        # Wrap each string value in a JSON array
        conn.execute(
            text("""
                UPDATE workflow_templates
                SET category_temp = json_build_array(category)
                WHERE category IS NOT NULL
            """)
        )

        # Drop the old column
        conn.execute(
            text("""
                ALTER TABLE workflow_templates
                DROP COLUMN category
            """)
        )

        # Rename the new column to replace the old one
        conn.execute(
            text("""
                ALTER TABLE workflow_templates
                RENAME COLUMN category_temp TO category
            """)
        )

        # Make the column NOT NULL with default empty array
        conn.execute(
            text("""
                ALTER TABLE workflow_templates
                ALTER COLUMN category SET NOT NULL,
                ALTER COLUMN category SET DEFAULT '[]'::json
            """)
        )

        conn.commit()
        logger.info(
            "%s Converted category column to JSON array successfully", LOG_PREFIX
        )

    except Exception as e:
        logger.warning("%s Could not convert category column: %s", LOG_PREFIX, e)


def create_oauth_tables(conn: Connection) -> None:
    """Create OAuth tables for MCP provider authentication.
    Creates oauth_client_registrations and oauth_tokens tables
    for storing per-user OAuth credentials (e.g., for Notion MCP).
    Args:
        conn: Database connection
    """
    try:
        # Check if oauth_client_registrations exists
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='oauth_client_registrations'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating oauth_client_registrations table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE oauth_client_registrations (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        provider VARCHAR NOT NULL DEFAULT 'notion',
                        client_id VARCHAR NOT NULL,
                        client_secret VARCHAR,
                        registration_access_token VARCHAR,
                        metadata JSON,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, provider)
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_oauth_client_reg_user_provider
                    ON oauth_client_registrations(user_id, provider)
                """)
            )
            conn.commit()
            logger.info("%s Created oauth_client_registrations table", LOG_PREFIX)
        else:
            logger.debug(
                "%s oauth_client_registrations table already exists", LOG_PREFIX
            )

        # Check if oauth_tokens exists
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='oauth_tokens'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating oauth_tokens table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE oauth_tokens (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        provider VARCHAR NOT NULL DEFAULT 'notion',
                        client_id VARCHAR NOT NULL,
                        access_token VARCHAR NOT NULL,
                        refresh_token VARCHAR,
                        expires_at TIMESTAMPTZ,
                        scope VARCHAR,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, provider)
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_oauth_tokens_user_provider
                    ON oauth_tokens(user_id, provider)
                """)
            )
            conn.commit()
            logger.info("%s Created oauth_tokens table", LOG_PREFIX)
        else:
            logger.debug("%s oauth_tokens table already exists", LOG_PREFIX)

        # Check if oauth_states exists (for CSRF protection)
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='oauth_states'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating oauth_states table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE oauth_states (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL,
                        provider VARCHAR NOT NULL DEFAULT 'notion',
                        state VARCHAR NOT NULL,
                        expires_at TIMESTAMPTZ NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        UNIQUE(user_id, provider)
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_oauth_states_user_provider
                    ON oauth_states(user_id, provider)
                """)
            )
            conn.commit()
            logger.info("%s Created oauth_states table", LOG_PREFIX)
        else:
            logger.debug("%s oauth_states table already exists", LOG_PREFIX)

        logger.info("%s OAuth tables migration completed", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not create OAuth tables: %s", LOG_PREFIX, e)


def create_agent_review_states_table(conn: Connection) -> None:
    """Create agent_review_states table for persistent review state.

    This table stores agent review state across checkpoint boundaries,
    solving the LangGraph limitation where interrupt() returns stale values
    during resume operations.

    Args:
        conn: Database connection
    """
    try:
        # Check if table already exists
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='agent_review_states'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating agent_review_states table", LOG_PREFIX)

            # Create the table
            conn.execute(
                text("""
                    CREATE TABLE agent_review_states (
                        id VARCHAR PRIMARY KEY,
                        graph_execution_id VARCHAR NOT NULL
                            REFERENCES graph_executions(id) ON DELETE CASCADE,
                        node_execution_id VARCHAR
                            REFERENCES node_executions(id) ON DELETE SET NULL,
                        agent_node_id VARCHAR NOT NULL,
                        checkpoint_id VARCHAR,
                        thread_id VARCHAR NOT NULL,
                        status VARCHAR NOT NULL DEFAULT 'pending_review',
                        current_iteration INTEGER NOT NULL DEFAULT 1,
                        max_iterations INTEGER NOT NULL DEFAULT 3,
                        review_mode VARCHAR NOT NULL DEFAULT 'human',
                        review_prompt TEXT,
                        current_agent_output TEXT,
                        review_history JSON DEFAULT '[]'::json,
                        input_message TEXT,
                        resume_response JSON,
                        review_config JSON,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
            )

            # Create indexes for better query performance
            logger.info("%s Creating indexes for agent_review_states", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE INDEX idx_agent_review_states_graph_execution_id
                    ON agent_review_states(graph_execution_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_agent_review_states_node_execution_id
                    ON agent_review_states(node_execution_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_agent_review_states_agent_node_id
                    ON agent_review_states(agent_node_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_agent_review_states_checkpoint_id
                    ON agent_review_states(checkpoint_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_agent_review_states_thread_id
                    ON agent_review_states(thread_id)
                """)
            )

            # Partial index for pending reviews (most common query)
            conn.execute(
                text("""
                    CREATE INDEX idx_agent_review_states_pending
                    ON agent_review_states(graph_execution_id, agent_node_id)
                    WHERE status = 'pending_review'
                """)
            )

            conn.commit()
            logger.info("%s Created agent_review_states table successfully", LOG_PREFIX)
        else:
            logger.debug("%s agent_review_states table already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning(
            "%s Could not create agent_review_states table: %s", LOG_PREFIX, e
        )


def create_user_external_services_table(conn: Connection) -> None:
    """Create user_external_services table for storing external service credentials.

    This table stores per-user API keys and settings for external services
    like Tavily web search, encrypted for security.

    Args:
        conn: Database connection
    """
    try:
        # Check if table already exists
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='user_external_services'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating user_external_services table", LOG_PREFIX)

            # Create the table
            conn.execute(
                text("""
                    CREATE TABLE user_external_services (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        service_name VARCHAR(50) NOT NULL,
                        encrypted_api_key VARCHAR NOT NULL,
                        settings JSON DEFAULT '{}'::json,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                """)
            )

            # Create indexes
            logger.info("%s Creating indexes for user_external_services", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE INDEX idx_user_external_services_user_id
                    ON user_external_services(user_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE UNIQUE INDEX idx_user_external_services_user_service
                    ON user_external_services(user_id, service_name)
                """)
            )

            conn.commit()
            logger.info(
                "%s Created user_external_services table successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s user_external_services table already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning(
            "%s Could not create user_external_services table: %s", LOG_PREFIX, e
        )


def add_mcp_server_visibility_fields(conn: Connection) -> None:
    """Add visibility and tracking fields to user_external_services table.

    Adds fields to support public/private MCP server visibility:
    - visibility: ENUM('private', 'public') for server visibility
    - is_template: BOOLEAN for tracking cloned servers
    - original_server_id: UUID for tracking clone source
    - clone_count: INTEGER for tracking popularity
    - shared_at: TIMESTAMP for when server was made public

    Args:
        conn: Database connection
    """
    try:
        # Check if visibility column already exists
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='user_external_services' AND column_name='visibility'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding MCP server visibility fields", LOG_PREFIX)

            # Create mcp_visibility enum type
            conn.execute(
                text("""
                    DO $$ BEGIN
                        CREATE TYPE mcp_visibility AS ENUM ('private', 'public');
                    EXCEPTION
                        WHEN duplicate_object THEN null;
                    END $$;
                """)
            )

            # Commit the ENUM type creation before using it
            conn.commit()

            # Add visibility column with default 'PRIVATE'
            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD COLUMN visibility mcp_visibility NOT NULL DEFAULT 'PRIVATE'::mcp_visibility
                """)
            )

            # Add is_template column
            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD COLUMN is_template BOOLEAN NOT NULL DEFAULT FALSE
                """)
            )

            # Add original_server_id column (self-referential foreign key)
            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD COLUMN original_server_id VARCHAR
                """)
            )

            # Add clone_count column
            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD COLUMN clone_count INTEGER NOT NULL DEFAULT 0
                """)
            )

            # Add shared_at column
            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD COLUMN shared_at TIMESTAMPTZ
                """)
            )

            # Create index on (visibility, is_active) for efficient public server queries
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_user_external_services_visibility
                    ON user_external_services(visibility, is_active)
                """)
            )

            # Create index on original_server_id
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_user_external_services_original
                    ON user_external_services(original_server_id)
                    WHERE original_server_id IS NOT NULL
                """)
            )

            # Add foreign key constraint for original_server_id (self-referential)
            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD CONSTRAINT fk_user_external_services_original
                    FOREIGN KEY (original_server_id)
                    REFERENCES user_external_services(id)
                    ON DELETE SET NULL
                """)
            )

            conn.commit()
            logger.info(
                "%s Added MCP server visibility fields successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s MCP server visibility fields already exist", LOG_PREFIX)

    except Exception as e:
        logger.warning(
            "%s Could not add MCP server visibility fields: %s", LOG_PREFIX, e
        )


def adjust_embedding_vector_dimension(conn: Connection) -> None:
    """Adjust document_chunks embedding column to match configured dimensions.

    Checks if the embedding column dimension matches EMBEDDING_DIMENSIONS.
    If not, drops and recreates the column with the correct dimension.
    Note: This will clear existing embeddings - documents will need re-embedding.

    Args:
        conn: Database connection
    """
    from ...document_storage.config import EMBEDDING_DIMENSIONS

    try:
        # Check if table and column exist
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='document_chunks' AND column_name='embedding'
            """)
        )

        if not result.fetchone():
            logger.debug(
                "%s embedding column does not exist yet, skipping adjustment",
                LOG_PREFIX,
            )
            return

        # Get current vector dimension using pg_attribute
        # For pgvector, atttypmod stores the dimension
        result = conn.execute(
            text("""
                SELECT atttypmod
                FROM pg_attribute
                WHERE attrelid = 'document_chunks'::regclass
                AND attname = 'embedding'
            """)
        )
        row = result.fetchone()

        if row:
            current_dim = row[0]
            if current_dim == EMBEDDING_DIMENSIONS:
                logger.debug(
                    "%s embedding column already has correct dimension (%d)",
                    LOG_PREFIX,
                    EMBEDDING_DIMENSIONS,
                )
                return

            logger.info(
                "%s Adjusting embedding column from %d to %d dimensions",
                LOG_PREFIX,
                current_dim,
                EMBEDDING_DIMENSIONS,
            )
        else:
            logger.info(
                "%s Adjusting embedding column to %d dimensions",
                LOG_PREFIX,
                EMBEDDING_DIMENSIONS,
            )

        # Drop existing column (clears data)
        conn.execute(
            text("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
        )

        # Add column with correct dimension using parameterized query
        # Note: Vector dimension must be a literal in DDL, but we validate it's an integer
        if not isinstance(EMBEDDING_DIMENSIONS, int) or EMBEDDING_DIMENSIONS <= 0:
            raise ValueError(f"Invalid EMBEDDING_DIMENSIONS: {EMBEDDING_DIMENSIONS}")

        conn.execute(
            text(f"""
                ALTER TABLE document_chunks
                ADD COLUMN embedding vector({EMBEDDING_DIMENSIONS})
            """)
        )

        conn.commit()
        logger.info(
            "%s Embedding column adjusted to %d dimensions successfully",
            LOG_PREFIX,
            EMBEDDING_DIMENSIONS,
        )

    except Exception as e:
        # Table might not exist yet, which is fine
        if "does not exist" in str(e):
            logger.debug("%s document_chunks table does not exist yet", LOG_PREFIX)
        else:
            logger.warning("%s Could not adjust embedding dimension: %s", LOG_PREFIX, e)


def add_groups_column_to_users(conn: Connection) -> None:
    """Add groups column to users table for RBAC.

    Stores OAuth group claims as JSONB array for role-based access control.
    Handles migration from JSON to JSONB if column exists with wrong type.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name='users' AND column_name='groups'
            """)
        )

        row = result.fetchone()

        if not row:
            # Column doesn't exist, create it as JSONB
            logger.info("%s Adding groups column to users table as JSONB", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE users
                    ADD COLUMN groups JSONB
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_users_groups
                    ON users USING GIN (groups)
                """)
            )
            conn.commit()
            logger.info("%s Added groups column successfully", LOG_PREFIX)
        else:
            # Column exists, check if it's the wrong type
            current_type = row[1]
            if current_type.lower() == "json":
                logger.info("%s Migrating groups column from JSON to JSONB", LOG_PREFIX)

                # Drop existing index if it exists
                conn.execute(
                    text("""
                        DROP INDEX IF EXISTS idx_users_groups
                    """)
                )

                # Alter column type from JSON to JSONB
                conn.execute(
                    text("""
                        ALTER TABLE users
                        ALTER COLUMN groups TYPE JSONB USING groups::text::jsonb
                    """)
                )

                # Recreate GIN index on JSONB column
                conn.execute(
                    text("""
                        CREATE INDEX IF NOT EXISTS idx_users_groups
                        ON users USING GIN (groups)
                    """)
                )
                conn.commit()
                logger.info(
                    "%s Migrated groups column to JSONB successfully", LOG_PREFIX
                )
            elif current_type.lower() == "jsonb":
                # Already JSONB, ensure index exists
                logger.debug("%s groups column already exists as JSONB", LOG_PREFIX)
                conn.execute(
                    text("""
                        CREATE INDEX IF NOT EXISTS idx_users_groups
                        ON users USING GIN (groups)
                    """)
                )
                conn.commit()
            else:
                logger.warning(
                    "%s groups column has unexpected type: %s", LOG_PREFIX, current_type
                )
    except Exception as e:
        logger.warning("%s Could not add/migrate groups column: %s", LOG_PREFIX, e)


def add_feature_access_table(conn: Connection) -> None:
    """Create feature_access table for admin settings control.

    Stores per-feature access control flags to determine which settings
    tabs require admin privileges.

    Note on rollbacks: This migration does not provide a rollback function because:
    1. Migrations run automatically on application startup before the app is fully initialized
    2. Rolling back would require manual database intervention (DROP TABLE, etc.)
    3. The table uses idempotent checks - re-running the migration is safe
    4. For production rollbacks, use database backups and manual SQL scripts

    If you need to remove this feature:
    - Manual approach: DROP TABLE feature_access CASCADE;
    - Then remove the migration from the registry to prevent re-creation

    Args:
        conn: Database connection
    """
    try:
        # Check if table already exists
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='feature_access'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating feature_access table", LOG_PREFIX)

            # Create the table
            conn.execute(
                text("""
                    CREATE TABLE feature_access (
                        id VARCHAR PRIMARY KEY,
                        feature_name VARCHAR UNIQUE NOT NULL,
                        display_name VARCHAR NOT NULL,
                        admin_only BOOLEAN NOT NULL DEFAULT TRUE,
                        description VARCHAR,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    )
                """)
            )

            # Create index on feature_name for fast lookups
            conn.execute(
                text("""
                    CREATE INDEX idx_feature_access_feature_name
                    ON feature_access(feature_name)
                """)
            )

            # Insert default feature access records for settings tabs
            logger.info("%s Inserting default feature access records", LOG_PREFIX)
            conn.execute(
                text("""
                    INSERT INTO feature_access (id, feature_name, display_name, admin_only, description)
                    VALUES
                        (gen_random_uuid()::varchar, 'settings.database', 'Database Settings', TRUE, 'Configure database connections and data sources'),
                        (gen_random_uuid()::varchar, 'settings.llm_providers', 'LLM Providers', TRUE, 'Manage LLM deployment configurations'),
                        (gen_random_uuid()::varchar, 'settings.external_services', 'External Services', TRUE, 'Configure external service API keys'),
                        (gen_random_uuid()::varchar, 'settings.external_tools', 'External Tools', FALSE, 'Configure external tools and MCP servers'),
                        (gen_random_uuid()::varchar, 'settings.appearance', 'Appearance', FALSE, 'Customize UI theme and appearance'),
                        (gen_random_uuid()::varchar, 'settings.api_tokens', 'API Tokens', FALSE, 'Manage personal access tokens')
                """)
            )

            conn.commit()
            logger.info("%s Created feature_access table successfully", LOG_PREFIX)
        else:
            logger.debug("%s feature_access table already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not create feature_access table: %s", LOG_PREFIX, e)


def seed_feature_access(conn: Connection) -> None:
    """Seed feature_access table with default feature access settings.

    Args:
        conn: Database connection
    """
    try:
        # Check if table already has data
        result = conn.execute(text("SELECT COUNT(*) FROM feature_access"))
        count = result.scalar()

        if count == 0:
            logger.info("%s Seeding feature_access table with defaults", LOG_PREFIX)

            # Default feature access settings
            features = [
                {
                    "feature_name": "settings.database",
                    "display_name": "Database Settings",
                    "admin_only": True,
                    "description": "Configure database connections and data sources",
                },
                {
                    "feature_name": "settings.llm_providers",
                    "display_name": "LLM Providers",
                    "admin_only": True,
                    "description": "Configure AI language model providers and settings",
                },
                {
                    "feature_name": "settings.external_services",
                    "display_name": "External Services",
                    "admin_only": True,
                    "description": "Configure external integrations and APIs",
                },
                {
                    "feature_name": "settings.external_tools",
                    "display_name": "External Tools",
                    "admin_only": False,
                    "description": "Configure custom MCP servers and external tool integrations",
                },
                {
                    "feature_name": "settings.appearance",
                    "display_name": "Appearance",
                    "admin_only": False,
                    "description": "Choose your preferred theme and branding",
                },
                {
                    "feature_name": "settings.api_tokens",
                    "display_name": "API Tokens",
                    "admin_only": False,
                    "description": "Manage your Personal Access Tokens for HTTP execution API",
                },
            ]

            for feature in features:
                conn.execute(
                    text("""
                        INSERT INTO feature_access (id, feature_name, display_name, admin_only, description)
                        VALUES (gen_random_uuid()::text, :feature_name, :display_name, :admin_only, :description)
                    """),
                    feature,
                )

            conn.commit()
            logger.info(
                "%s Seeded feature_access table successfully with %d features",
                LOG_PREFIX,
                len(features),
            )
        else:
            logger.debug(
                "%s feature_access table already has data (%d rows)", LOG_PREFIX, count
            )

    except Exception as e:
        logger.warning("%s Could not seed feature_access table: %s", LOG_PREFIX, e)
        conn.rollback()


def add_navigation_feature_access(conn: Connection) -> None:
    """Add navigation menu items to feature_access table.

    Adds feature access controls for top-level navigation items so admins
    can control which menu items are visible to non-admin users.

    Args:
        conn: Database connection
    """
    try:
        # Navigation features to add
        nav_features = [
            {
                "feature_name": "nav.workflow",
                "display_name": "Workflow Editor",
                "admin_only": False,
                "description": "Access to the workflow editor and canvas",
            },
            {
                "feature_name": "nav.library",
                "display_name": "Library",
                "admin_only": False,
                "description": "Access to workflow and agent template library",
            },
            {
                "feature_name": "nav.publish",
                "display_name": "Publish",
                "admin_only": False,
                "description": "Publish workflows and agents to the library",
            },
            {
                "feature_name": "nav.datasources",
                "display_name": "Data Sources",
                "admin_only": False,
                "description": "Manage document uploads and data sources",
            },
            {
                "feature_name": "nav.executions",
                "display_name": "Executions",
                "admin_only": False,
                "description": "View workflow execution history and logs",
            },
            {
                "feature_name": "nav.manage",
                "display_name": "Manage Workflows",
                "admin_only": False,
                "description": "Manage saved workflows",
            },
        ]

        # Check and insert each feature if it doesn't exist
        for feature in nav_features:
            result = conn.execute(
                text("""
                    SELECT COUNT(*) FROM feature_access
                    WHERE feature_name = :feature_name
                """),
                {"feature_name": feature["feature_name"]},
            )

            if result.scalar() == 0:
                logger.info(
                    "%s Adding navigation feature: %s",
                    LOG_PREFIX,
                    feature["feature_name"],
                )
                conn.execute(
                    text("""
                        INSERT INTO feature_access (id, feature_name, display_name, admin_only, description)
                        VALUES (gen_random_uuid()::text, :feature_name, :display_name, :admin_only, :description)
                    """),
                    feature,
                )
            else:
                logger.debug(
                    "%s Navigation feature already exists: %s",
                    LOG_PREFIX,
                    feature["feature_name"],
                )

        conn.commit()
        logger.info("%s Navigation feature access migration completed", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not add navigation feature access: %s", LOG_PREFIX, e)
        conn.rollback()


def migrate_template_categories(conn: Connection) -> None:
    """Migrate template categories to new naming convention.

    Performs the following category migrations:
    - Legal & Compliance -> Risk & Compliance
    - Horizon Scanning -> Risk & Compliance
    - Dispute Management -> Customer Service
    - Account Unlock -> Cybersecurity

    Updates both workflow_templates and agent_templates tables.
    Handles deduplication when multiple old categories map to the same new category.

    Args:
        conn: Database connection
    """
    tables = ["workflow_templates", "agent_templates"]

    for table in tables:
        try:
            # Check if table exists
            result = conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = :table_name
                    )
                """),
                {"table_name": table},
            )

            if not result.scalar():
                logger.debug("%s Table %s does not exist, skipping", LOG_PREFIX, table)
                continue

            # Check if any rows need migration
            result = conn.execute(
                text(f"""
                    SELECT COUNT(*) FROM {table}
                    WHERE category IS NOT NULL
                    AND category::text != '[]'
                    AND (
                        category::text LIKE '%Legal & Compliance%'
                        OR category::text LIKE '%Horizon Scanning%'
                        OR category::text LIKE '%Dispute Management%'
                        OR category::text LIKE '%Account Unlock%'
                    )
                """)
            )

            count = result.scalar()
            if count == 0:
                logger.debug("%s No %s rows need category migration", LOG_PREFIX, table)
                continue

            logger.info(
                "%s Migrating %d %s rows with old categories", LOG_PREFIX, count, table
            )

            # Update categories using JSON array transformation with deduplication
            # This query:
            # 1. Expands the JSON array into rows
            # 2. Maps old category names to new ones
            # 3. Aggregates back into a JSON array with DISTINCT to remove duplicates
            conn.execute(
                text(f"""
                    UPDATE {table}
                    SET category = (
                        SELECT COALESCE(
                            json_agg(DISTINCT
                                CASE elem
                                    WHEN 'Legal & Compliance' THEN 'Risk & Compliance'
                                    WHEN 'Horizon Scanning' THEN 'Risk & Compliance'
                                    WHEN 'Dispute Management' THEN 'Customer Service'
                                    WHEN 'Account Unlock' THEN 'Cybersecurity'
                                    ELSE elem
                                END
                            ),
                            '[]'::json
                        )
                        FROM json_array_elements_text(category::json) AS elem
                    )
                    WHERE category IS NOT NULL
                    AND category::text != '[]'
                    AND (
                        category::text LIKE '%Legal & Compliance%'
                        OR category::text LIKE '%Horizon Scanning%'
                        OR category::text LIKE '%Dispute Management%'
                        OR category::text LIKE '%Account Unlock%'
                    )
                """)
            )

            conn.commit()
            logger.info("%s Successfully migrated categories in %s", LOG_PREFIX, table)

        except Exception as e:
            logger.warning(
                "%s Could not migrate categories in %s: %s", LOG_PREFIX, table, e
            )
            conn.rollback()


def add_review_iteration_column(conn: Connection) -> None:
    """Add review_iteration column to node_executions table.

    Adds review_iteration column to track which review iteration a tool
    execution belongs to, enabling tool-to-iteration association in the UI.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='node_executions' AND column_name='review_iteration'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding review_iteration column to node_executions", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE node_executions
                    ADD COLUMN review_iteration INTEGER
                """)
            )
            conn.commit()
            logger.info("%s Added review_iteration column successfully", LOG_PREFIX)
        else:
            logger.debug("%s review_iteration column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add review_iteration column: %s", LOG_PREFIX, e)


def add_node_executions_graph_status_index(conn: Connection) -> None:
    """Add compound index on node_executions for faster count queries.

    Creates index on (graph_execution_id, status) to optimize batched
    node count queries in the execution history list view.

    Args:
        conn: Database connection
    """
    try:
        # Check if index already exists
        result = conn.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'node_executions'
                AND indexname = 'idx_node_executions_graph_status'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Creating compound index on node_executions(graph_execution_id, status)",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_node_executions_graph_status
                    ON node_executions(graph_execution_id, status)
                """)
            )
            conn.commit()
            logger.info(
                "%s Created idx_node_executions_graph_status successfully", LOG_PREFIX
            )
        else:
            logger.debug(
                "%s idx_node_executions_graph_status index already exists", LOG_PREFIX
            )

    except Exception as e:
        logger.warning(
            "%s Could not create node_executions graph_status index: %s",
            LOG_PREFIX,
            e,
        )


def create_execution_files_table(conn: Connection) -> None:
    """Create execution_files table for storing workflow-generated files.

    This table stores binary files created by FILE_WRITE tool executions
    in PostgreSQL instead of the filesystem. Files are automatically
    deleted when their parent node_execution is deleted (CASCADE).

    Args:
        conn: Database connection
    """
    try:
        # Check if table already exists
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='execution_files'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating execution_files table", LOG_PREFIX)

            # Create the table
            conn.execute(
                text("""
                    CREATE TABLE execution_files (
                        id VARCHAR PRIMARY KEY,
                        node_execution_id VARCHAR NOT NULL
                            REFERENCES node_executions(id) ON DELETE CASCADE,
                        filename VARCHAR(255) NOT NULL,
                        mime_type VARCHAR(100) NOT NULL,
                        file_size INTEGER NOT NULL,
                        content BYTEA NOT NULL,
                        text_content TEXT,
                        status VARCHAR(50) NOT NULL DEFAULT 'stored',
                        error_message TEXT,
                        subdirectory VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
            )

            # Create indexes
            logger.info("%s Creating indexes for execution_files", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE INDEX idx_execution_files_node_execution_id
                    ON execution_files(node_execution_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_execution_files_filename
                    ON execution_files(filename)
                """)
            )

            conn.commit()
            logger.info("%s Created execution_files table successfully", LOG_PREFIX)
        else:
            logger.debug("%s execution_files table already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not create execution_files table: %s", LOG_PREFIX, e)


def create_subagent_iteration_states_table(conn: Connection) -> None:
    """Create subagent_iteration_states table for tracking subagent iterations.

    This table tracks subagent execution iterations when a parent agent calls
    a subagent multiple times, ensuring proper WebSocket routing and database
    record separation across checkpoint boundaries.

    Args:
        conn: Database connection
    """
    try:
        # Check if table already exists
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='subagent_iteration_states'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating subagent_iteration_states table", LOG_PREFIX)

            # Create the table
            conn.execute(
                text("""
                    CREATE TABLE subagent_iteration_states (
                        id VARCHAR PRIMARY KEY,
                        graph_execution_id VARCHAR NOT NULL
                            REFERENCES graph_executions(id) ON DELETE CASCADE,
                        parent_agent_id VARCHAR NOT NULL,
                        subagent_node_id VARCHAR NOT NULL,
                        thread_id VARCHAR NOT NULL,
                        current_iteration INTEGER NOT NULL DEFAULT 1,
                        status VARCHAR NOT NULL DEFAULT 'active',
                        iteration_history JSON DEFAULT '[]'::json,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
            )

            # Create indexes for better query performance
            logger.info("%s Creating indexes for subagent_iteration_states", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE INDEX idx_subagent_iteration_states_graph_execution_id
                    ON subagent_iteration_states(graph_execution_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_subagent_iteration_states_parent_agent_id
                    ON subagent_iteration_states(parent_agent_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_subagent_iteration_states_subagent_node_id
                    ON subagent_iteration_states(subagent_node_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_subagent_iteration_states_thread_id
                    ON subagent_iteration_states(thread_id)
                """)
            )

            # Composite index for efficient lookup by graph execution + parent + subagent
            conn.execute(
                text("""
                    CREATE INDEX idx_subagent_iteration_states_lookup
                    ON subagent_iteration_states(graph_execution_id, parent_agent_id, subagent_node_id)
                    WHERE status = 'active'
                """)
            )

            conn.commit()
            logger.info(
                "%s Created subagent_iteration_states table successfully", LOG_PREFIX
            )
        else:
            logger.debug(
                "%s subagent_iteration_states table already exists", LOG_PREFIX
            )

    except Exception as e:
        logger.warning(
            "%s Could not create subagent_iteration_states table: %s", LOG_PREFIX, e
        )


def add_invocation_index_column(conn: Connection) -> None:
    """Add invocation_index column to node_executions table.

    Adds invocation_index column to track which invocation of a subagent
    (1st, 2nd, etc.) a node execution belongs to, enabling tool-to-invocation
    association in the UI when a subagent is called multiple times.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='node_executions' AND column_name='invocation_index'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding invocation_index column to node_executions", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE node_executions
                    ADD COLUMN invocation_index INTEGER
                """)
            )
            conn.commit()
            logger.info("%s Added invocation_index column successfully", LOG_PREFIX)
        else:
            logger.debug("%s invocation_index column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add invocation_index column: %s", LOG_PREFIX, e)


def create_groups_table(conn: Connection) -> None:
    """Create groups table if it does not exist.

    Creates the groups table for storing both OAuth groups (system) and
    custom admin-created groups, with indexes on name and is_system.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'groups'
                )
            """)
        )
        exists = result.scalar()
        if exists:
            logger.debug("%s groups table already exists, skipping", LOG_PREFIX)
            return
        conn.execute(
            text("""
                CREATE TABLE groups (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    is_system BOOLEAN NOT NULL DEFAULT false,
                    created_by_user_id VARCHAR(255),
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_groups_is_system ON groups(is_system)")
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_groups_name ON groups(name)"))
        conn.commit()
        logger.info("%s Created groups table and indexes", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Failed to create groups table: %s", LOG_PREFIX, e)


def create_group_memberships_table(conn: Connection) -> None:
    """Create group_memberships table if it does not exist.

    Creates the many-to-many relationship table between users and groups
    with foreign key constraints and a unique constraint on (group_id, user_id).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'group_memberships'
                )
            """)
        )
        exists = result.scalar()
        if exists:
            logger.debug(
                "%s group_memberships table already exists, skipping", LOG_PREFIX
            )
            return
        conn.execute(
            text("""
                CREATE TABLE group_memberships (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    user_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(group_id, user_id)
                )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_group_memberships_group_id "
                "ON group_memberships(group_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_group_memberships_user_id "
                "ON group_memberships(user_id)"
            )
        )
        conn.commit()
        logger.info("%s Created group_memberships table and indexes", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Failed to create group_memberships table: %s", LOG_PREFIX, e)


def add_visible_to_groups_column(conn: Connection) -> None:
    """Add visible_to_groups JSONB column to document_collections table.

    Adds a JSONB column for group-based visibility control on collections.
    Empty array means private, ["__all__"] means global, specific group
    names restrict access to members of those groups.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='document_collections'
                AND column_name='visible_to_groups'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding visible_to_groups column to document_collections",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE document_collections
                    ADD COLUMN visible_to_groups JSONB NOT NULL DEFAULT '[]'::jsonb
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_document_collections_visible_to_groups
                    ON document_collections USING GIN (visible_to_groups)
                """)
            )
            conn.commit()
            logger.info("%s Added visible_to_groups column successfully", LOG_PREFIX)
        else:
            logger.debug("%s visible_to_groups column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add visible_to_groups column: %s", LOG_PREFIX, e)


def seed_administrators_group(conn: Connection) -> None:
    """Seed the Administrators group if it does not exist.

    Creates a well-known system group named "Administrators" that provides
    database-backed admin RBAC permissions alongside the ADMIN_USERS and
    ADMIN_GROUP environment variables.

    Args:
        conn: Database connection
    """
    from backend.services.auth.config import ADMINISTRATORS_GROUP_NAME

    try:
        result = conn.execute(
            text("""
                SELECT id FROM groups WHERE name = :name
            """),
            {"name": ADMINISTRATORS_GROUP_NAME},
        )

        if not result.fetchone():
            logger.info(
                "%s Seeding '%s' system group",
                LOG_PREFIX,
                ADMINISTRATORS_GROUP_NAME,
            )
            conn.execute(
                text("""
                    INSERT INTO groups (id, name, description, is_system, created_by_user_id, created_at)
                    VALUES (
                        gen_random_uuid(),
                        :name,
                        'Built-in administrator group. Members have full admin privileges.',
                        TRUE,
                        NULL,
                        NOW()
                    )
                """),
                {"name": ADMINISTRATORS_GROUP_NAME},
            )
            conn.commit()
            logger.info(
                "%s Seeded '%s' group successfully",
                LOG_PREFIX,
                ADMINISTRATORS_GROUP_NAME,
            )
        else:
            logger.debug(
                "%s '%s' group already exists",
                LOG_PREFIX,
                ADMINISTRATORS_GROUP_NAME,
            )
    except Exception as e:
        logger.warning(
            "%s Could not seed '%s' group: %s",
            LOG_PREFIX,
            ADMINISTRATORS_GROUP_NAME,
            e,
        )


def add_model_deployment_pricing_columns(conn: Connection) -> None:
    """Add token pricing columns to model_deployments table.

    Adds input_cost_per_million and output_cost_per_million columns
    for custom USD pricing per 1M tokens on LLM deployments.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='model_deployments'
                AND column_name='input_cost_per_million'
            """)
        )
        if not result.fetchone():
            logger.info("%s Adding pricing columns to model_deployments", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE model_deployments
                    ADD COLUMN input_cost_per_million FLOAT,
                    ADD COLUMN output_cost_per_million FLOAT
                """)
            )
            conn.commit()
            logger.info(
                "%s Added pricing columns to model_deployments successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s Pricing columns already exist in model_deployments",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Failed to add pricing columns to model_deployments: %s",
            LOG_PREFIX,
            e,
        )


def add_cron_schedule_columns(conn: Connection) -> None:
    """Add cron scheduling columns to published_workflows table.

    Adds columns for cron-based workflow scheduling: expression, timezone,
    active flag, run timestamps, and counters.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='published_workflows' AND column_name='cron_expression'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding cron schedule columns to published_workflows", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE published_workflows
                    ADD COLUMN cron_expression VARCHAR,
                    ADD COLUMN cron_input VARCHAR,
                    ADD COLUMN cron_timezone VARCHAR DEFAULT 'UTC' NOT NULL,
                    ADD COLUMN cron_is_active BOOLEAN DEFAULT FALSE NOT NULL,
                    ADD COLUMN cron_last_run_at TIMESTAMPTZ,
                    ADD COLUMN cron_next_run_at TIMESTAMPTZ,
                    ADD COLUMN cron_run_count BIGINT DEFAULT 0 NOT NULL,
                    ADD COLUMN cron_failure_count BIGINT DEFAULT 0 NOT NULL
                """)
            )

            # Partial index for active schedules
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_published_workflows_cron_active
                    ON published_workflows(cron_is_active)
                    WHERE cron_is_active = TRUE
                """)
            )

            conn.commit()
            logger.info("%s Added cron schedule columns successfully", LOG_PREFIX)
        else:
            logger.debug("%s cron schedule columns already exist", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add cron schedule columns: %s", LOG_PREFIX, e)


def add_cron_input_column(conn: Connection) -> None:
    """Add cron_input column to published_workflows for already-migrated DBs.

    Separate, idempotent migration so databases that already have the
    cron_expression column (added before cron_input existed) still get it.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='published_workflows' AND column_name='cron_input'
            """)
        )
        if not result.fetchone():
            conn.execute(
                text(
                    "ALTER TABLE published_workflows ADD COLUMN IF NOT EXISTS cron_input VARCHAR"
                )
            )
            conn.commit()
            logger.info("%s Added cron_input column successfully", LOG_PREFIX)
        else:
            logger.debug("%s cron_input column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add cron_input column: %s", LOG_PREFIX, e)


def add_system_user_role(conn: Connection) -> None:
    """Expand the users.role CHECK constraint to include the SYSTEM role.

    The SYSTEM role is auto-assigned to service principals and managed
    identities that authenticate via Azure AD app-only tokens.  PostgreSQL
    does not support altering an existing CHECK constraint in-place, so we
    drop the old constraint and add a new one that includes 'SYSTEM'.

    This migration is idempotent: it checks whether 'SYSTEM' is already
    present in the constraint definition before modifying anything.

    Args:
        conn: Database connection
    """
    try:
        # Check whether the constraint already allows SYSTEM
        result = conn.execute(
            text("""
                SELECT pg_get_constraintdef(c.oid) AS def
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'users'
                  AND c.conname = 'ck_users_role'
            """)
        )
        row = result.fetchone()
        if row and "SYSTEM" in row[0]:
            logger.debug(
                "%s ck_users_role already includes SYSTEM, skipping", LOG_PREFIX
            )
            return

        logger.info("%s Expanding ck_users_role to include 'SYSTEM' role", LOG_PREFIX)

        # Drop old constraint
        conn.execute(
            text("""
                ALTER TABLE users
                DROP CONSTRAINT IF EXISTS ck_users_role
            """)
        )

        # Add updated constraint
        conn.execute(
            text("""
                ALTER TABLE users
                ADD CONSTRAINT ck_users_role
                CHECK (role IN ('PENDING', 'USER', 'ADMIN', 'SYSTEM'))
            """)
        )

        conn.commit()
        logger.info("%s Updated ck_users_role constraint successfully", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not update ck_users_role constraint: %s", LOG_PREFIX, e
        )


def add_user_role_column(conn: Connection) -> None:
    """Add role column to users table for role-based authorization.

    Adds a VARCHAR(20) column with CHECK constraint for role validation.
    Backfills existing users with 'ADMIN' role if they are in Administrators group.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='users' AND column_name='role'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding role column to users table", LOG_PREFIX)

            # Add role column with default value 'USER'
            conn.execute(
                text("""
                    ALTER TABLE users
                    ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'USER'
                """)
            )

            # Add CHECK constraint to ensure role is valid
            conn.execute(
                text("""
                    ALTER TABLE users
                    ADD CONSTRAINT ck_users_role
                    CHECK (role IN ('PENDING', 'USER', 'ADMIN'))
                """)
            )

            # Create index on role column for efficient filtering
            conn.execute(
                text("""
                    CREATE INDEX idx_users_role ON users(role)
                """)
            )

            # Backfill existing users: set role to 'ADMIN' if in Administrators group
            conn.execute(
                text("""
                    UPDATE users
                    SET role = 'ADMIN'
                    WHERE id IN (
                        SELECT gm.user_id
                        FROM group_memberships gm
                        JOIN groups g ON gm.group_id = g.id
                        WHERE g.name = 'Administrators'
                    )
                """)
            )

            conn.commit()
            logger.info(
                "%s Added role column successfully and backfilled admin users",
                LOG_PREFIX,
            )
        else:
            logger.debug("%s role column already exists in users table", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not add role column: %s", LOG_PREFIX, e)


def create_system_settings_table(conn: Connection) -> None:
    """Create the system_settings table for cross-pod persistent configuration.

    Stores admin-configurable settings (e.g. document extraction provider, Tika URL)
    in PostgreSQL so they are shared across all pods and survive pod restarts.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='system_settings'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating system_settings table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE system_settings (
                        key VARCHAR PRIMARY KEY,
                        value TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
            )
            conn.commit()
            logger.info("%s Created system_settings table successfully", LOG_PREFIX)
        else:
            logger.debug("%s system_settings table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not create system_settings table: %s", LOG_PREFIX, e)


def create_system_external_services_table(conn: Connection) -> None:
    """Create the system_external_services table for admin-managed external services.

    Stores organisation-level external service configurations (e.g. Azure Document
    Intelligence, Apache Tika) following the schema proposed in issue #217.
    Credentials are encrypted at rest; the table is write-only for admins and
    metadata-read-only for regular authenticated users.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='system_external_services'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating system_external_services table", LOG_PREFIX)

            # Create auth_type enum if it doesn't exist
            conn.execute(
                text("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_type WHERE typname = 'external_service_auth_type'
                        ) THEN
                            CREATE TYPE external_service_auth_type AS ENUM (
                                'api_key_header',
                                'bearer_token',
                                'basic_auth',
                                'query_param',
                                'none'
                            );
                        END IF;
                    END
                    $$;
                """)
            )

            conn.execute(
                text("""
                    CREATE TABLE system_external_services (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        service_name VARCHAR(100) NOT NULL UNIQUE,
                        display_name VARCHAR(255),
                        description TEXT,
                        service_url TEXT,
                        auth_type external_service_auth_type NOT NULL DEFAULT 'api_key_header',
                        encrypted_credentials JSONB,
                        settings JSONB NOT NULL DEFAULT '{}',
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_system_external_services_name
                    ON system_external_services(service_name)
                """)
            )

            conn.commit()
            logger.info(
                "%s Created system_external_services table successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s system_external_services table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not create system_external_services table: %s", LOG_PREFIX, e
        )


def migrate_user_external_services_schema(conn: Connection) -> None:
    """Add rich credential columns to user_external_services table.

    Adds display_name, service_url, auth_type, and encrypted_credentials columns
    to align the user-tier table with the system-tier schema (issue #217).
    Also migrates existing non-MCP rows to populate encrypted_credentials from
    the legacy encrypted_api_key column.

    This migration requires the external_service_auth_type enum to already exist
    (created by create_system_external_services_table).

    Args:
        conn: Database connection
    """
    try:
        # Check if encrypted_credentials column already exists (idempotency guard)
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='user_external_services'
                AND column_name='encrypted_credentials'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding credential columns to user_external_services", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD COLUMN IF NOT EXISTS display_name VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS service_url TEXT,
                    ADD COLUMN IF NOT EXISTS auth_type external_service_auth_type
                        NOT NULL DEFAULT 'api_key_header',
                    ADD COLUMN IF NOT EXISTS encrypted_credentials JSONB
                """)
            )
            conn.commit()
            logger.info(
                "%s Added credential columns to user_external_services", LOG_PREFIX
            )
        else:
            logger.debug(
                "%s Credential columns already exist in user_external_services",
                LOG_PREFIX,
            )

        # Data migration: wrap existing non-MCP api_key values into the new JSON blob
        conn.execute(
            text("""
                UPDATE user_external_services
                SET encrypted_credentials = jsonb_build_object('api_key', encrypted_api_key)
                WHERE service_name NOT LIKE 'mcp_server_%'
                  AND encrypted_credentials IS NULL
                  AND encrypted_api_key != ''
            """)
        )
        conn.commit()
        logger.info("%s Migrated non-MCP rows to encrypted_credentials", LOG_PREFIX)

    except Exception as e:
        logger.warning(
            "%s Could not migrate user_external_services schema: %s", LOG_PREFIX, e
        )


def add_workflow_http_trigger_token(conn: Connection) -> None:
    """Add http_trigger_token column to workflows table and backfill existing rows.

    Each workflow gets a unique ``wf_`` prefixed token used for HTTP trigger
    authentication via the ``Authorization: Bearer`` header.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='workflows' AND column_name='http_trigger_token'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding http_trigger_token column to workflows", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE workflows
                    ADD COLUMN http_trigger_token VARCHAR
                """)
            )
            conn.commit()
            logger.info("%s Added http_trigger_token column successfully", LOG_PREFIX)
        else:
            logger.debug("%s http_trigger_token column already exists", LOG_PREFIX)

        # Backfill existing workflows that don't have a token yet
        result = conn.execute(
            text("SELECT id FROM workflows WHERE http_trigger_token IS NULL")
        )
        rows = result.fetchall()
        if rows:
            import secrets as _secrets

            logger.info(
                "%s Backfilling http_trigger_token for %d existing workflows",
                LOG_PREFIX,
                len(rows),
            )
            for row in rows:
                token = "wf_" + _secrets.token_urlsafe(32)
                conn.execute(
                    text(
                        "UPDATE workflows SET http_trigger_token = :token WHERE id = :id"
                    ),
                    {"token": token, "id": row[0]},
                )
            conn.commit()
            logger.info("%s Backfilled http_trigger_token successfully", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not add/backfill http_trigger_token: %s", LOG_PREFIX, e
        )


def add_collection_embedding_deployment_id(conn: Connection) -> None:
    """Add embedding_deployment_id column to document_collections table.

    Stores which embedding model deployment was used to vectorise documents
    in this collection. Once set it should not change without re-vectorising
    all documents, so the column is deliberately nullable and left empty until
    the first document upload.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='document_collections'
                AND column_name='embedding_deployment_id'
            """)
        )
        if result.fetchone() is None:
            conn.execute(
                text("""
                    ALTER TABLE document_collections
                    ADD COLUMN embedding_deployment_id VARCHAR(255)
                """)
            )
            conn.commit()
            logger.info(
                "%s Added embedding_deployment_id column to document_collections",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s embedding_deployment_id column already exists on document_collections",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add embedding_deployment_id to document_collections: %s",
            LOG_PREFIX,
            e,
        )


def add_document_embedding_cost_columns(conn: Connection) -> None:
    """Add embedding cost tracking columns to documents table.

    Stores embedding_tokens, embedding_cost, and embedding_model on each
    document so the data is available when listing documents later (not
    only at upload time in the toast notification).

    Args:
        conn: Database connection
    """
    columns = [
        ("embedding_tokens", "INTEGER"),
        ("embedding_cost", "DOUBLE PRECISION"),
        ("embedding_model", "VARCHAR(255)"),
    ]
    try:
        for col_name, col_type in columns:
            result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='documents' AND column_name=:col"
                ),
                {"col": col_name},
            )
            if result.fetchone() is None:
                conn.execute(
                    text(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type}")
                )
                logger.info("%s Added %s column to documents", LOG_PREFIX, col_name)
        conn.commit()
    except Exception as e:
        logger.warning(
            "%s Could not add embedding cost columns to documents: %s",
            LOG_PREFIX,
            e,
        )
    except Exception as e:
        logger.warning(
            "%s Could not add embedding cost columns to documents: %s",
            LOG_PREFIX,
            e,
        )


def add_evaluation_run_id_column(conn: Connection) -> None:
    """Add evaluation_run_id column to graph_executions table.

    Links graph executions to evaluation runs so results can reference
    the execution that produced them.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='graph_executions' AND column_name='evaluation_run_id'"
            )
        )

        if not result.fetchone():
            logger.info(
                "%s Adding evaluation_run_id column to graph_executions", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE graph_executions
                    ADD COLUMN evaluation_run_id VARCHAR
                    REFERENCES evaluation_runs(id) ON DELETE SET NULL
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS ix_graph_executions_evaluation_run_id
                    ON graph_executions (evaluation_run_id)
                """)
            )
            conn.commit()
            logger.info("%s Added evaluation_run_id column successfully", LOG_PREFIX)
        else:
            logger.debug("%s evaluation_run_id column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not add evaluation_run_id column: %s",
            LOG_PREFIX,
            e,
        )


def add_evaluation_regression_ack_column(conn):
    """Add regression_ack_required column to evaluation_runs table.

    Tracks whether user acknowledgement is required before proceeding
    when a regression is detected in production environments.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='evaluation_runs' AND column_name='regression_ack_required'"
            )
        )

        if not result.fetchone():
            logger.info(
                "%s Adding regression_ack_required column to evaluation_runs",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE evaluation_runs
                    ADD COLUMN regression_ack_required BOOLEAN DEFAULT FALSE
                """)
            )
            conn.commit()
            logger.info(
                "%s Added regression_ack_required column successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s regression_ack_required column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not add regression_ack_required column: %s",
            LOG_PREFIX,
            e,
        )


def add_evaluation_dataset_target_and_tags_columns(conn: Connection) -> None:
    """Add target_id and tags columns to evaluation_datasets table.

    These columns allow datasets to reference a specific workflow/node
    target and carry user-defined tags for organisation.

    Args:
        conn: Database connection
    """
    try:
        # target_id
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='evaluation_datasets' AND column_name='target_id'"
            )
        )
        if not result.fetchone():
            logger.info("%s Adding target_id column to evaluation_datasets", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE evaluation_datasets
                    ADD COLUMN target_id VARCHAR
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_target_id
                    ON evaluation_datasets (target_id)
                """)
            )
            conn.commit()
            logger.info("%s Added target_id column successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s target_id column already exists on evaluation_datasets", LOG_PREFIX
            )

        # tags
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='evaluation_datasets' AND column_name='tags'"
            )
        )
        if not result.fetchone():
            logger.info("%s Adding tags column to evaluation_datasets", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE evaluation_datasets
                    ADD COLUMN tags JSON
                """)
            )
            conn.commit()
            logger.info("%s Added tags column successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s tags column already exists on evaluation_datasets", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not add target_id/tags columns to evaluation_datasets: %s",
            LOG_PREFIX,
            e,
        )


def add_workflow_auto_eval_config_column(conn: Connection) -> None:
    """Add auto_eval_config JSON column to workflows table.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='workflows' AND column_name='auto_eval_config'
            """)
        )

        if not result.fetchone():
            logger.info("%s Adding auto_eval_config column to workflows", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE workflows
                    ADD COLUMN auto_eval_config JSON
                """)
            )
            conn.commit()
            logger.info("%s Added auto_eval_config column successfully", LOG_PREFIX)
        else:
            logger.debug("%s auto_eval_config column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not add auto_eval_config column: %s",
            LOG_PREFIX,
            e,
        )


def add_trigger_type_column(conn: Connection) -> None:
    """Add trigger_type column to graph_executions table.

    Tracks how each execution was triggered: editor, api, evaluation, or scheduler.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='graph_executions' AND column_name='trigger_type'"
            )
        )

        if not result.fetchone():
            logger.info("%s Adding trigger_type column to graph_executions", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE graph_executions
                    ADD COLUMN trigger_type VARCHAR
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS ix_graph_executions_trigger_type
                    ON graph_executions (trigger_type)
                """)
            )
            conn.commit()
            logger.info("%s Added trigger_type column successfully", LOG_PREFIX)
        else:
            logger.debug("%s trigger_type column already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not add trigger_type column: %s",
            LOG_PREFIX,
            e,
        )


def create_execution_feedback_table(conn: Connection) -> None:
    """Create execution_feedback table for thumbs up/down ratings on runs.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name='execution_feedback'"
            )
        )

        if not result.fetchone():
            logger.info("%s Creating execution_feedback table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE execution_feedback (
                        id VARCHAR PRIMARY KEY,
                        graph_execution_id VARCHAR NOT NULL
                            REFERENCES graph_executions(id) ON DELETE CASCADE,
                        rating VARCHAR NOT NULL,
                        comment TEXT,
                        user_id VARCHAR NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX ix_execution_feedback_graph_execution_id
                    ON execution_feedback (graph_execution_id)
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX ix_execution_feedback_user_id
                    ON execution_feedback (user_id)
                """)
            )
            conn.execute(
                text("""
                    CREATE UNIQUE INDEX uq_execution_feedback_user_execution
                    ON execution_feedback (graph_execution_id, user_id)
                """)
            )
            conn.commit()
            logger.info("%s Created execution_feedback table successfully", LOG_PREFIX)
        else:
            logger.debug("%s execution_feedback table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not create execution_feedback table: %s",
            LOG_PREFIX,
            e,
        )


def add_node_execution_id_to_feedback(conn: Connection) -> None:
    """Add node_execution_id column to execution_feedback table for node-level ratings.

    Also updates the unique constraint to include node_execution_id so that
    a user can rate both the overall execution and individual nodes.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='execution_feedback' AND column_name='node_execution_id'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding node_execution_id column to execution_feedback", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE execution_feedback
                    ADD COLUMN node_execution_id VARCHAR
                        REFERENCES node_executions(id) ON DELETE CASCADE
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX ix_execution_feedback_node_execution_id
                    ON execution_feedback (node_execution_id)
                """)
            )
            # Drop the old unique constraint and create a new one that includes node_execution_id
            conn.execute(
                text("""
                    DROP INDEX IF EXISTS uq_execution_feedback_user_execution
                """)
            )
            conn.execute(
                text("""
                    CREATE UNIQUE INDEX uq_execution_feedback_user_execution
                    ON execution_feedback (graph_execution_id, COALESCE(node_execution_id, ''), user_id)
                """)
            )
            conn.commit()
            logger.info("%s Added node_execution_id column successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s node_execution_id column already exists in execution_feedback",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add node_execution_id to execution_feedback: %s",
            LOG_PREFIX,
            e,
        )


def create_node_version_index_table(conn: Connection) -> None:
    """Create the node_version_index table for tracking individual node versions.

    Each row maps a node_id within a graph_definition to its config hash and
    auto-incremented node_version, enabling per-node version tracking across
    graph definition versions.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'node_version_index'
                )
            """)
        )
        if result.scalar():
            logger.debug("%s node_version_index table already exists", LOG_PREFIX)
            return

        logger.info("%s Creating node_version_index table", LOG_PREFIX)
        conn.execute(
            text("""
                CREATE TABLE node_version_index (
                    id VARCHAR PRIMARY KEY,
                    graph_definition_id VARCHAR NOT NULL
                        REFERENCES graph_definitions(id) ON DELETE CASCADE,
                    workflow_id VARCHAR
                        REFERENCES workflows(id) ON DELETE CASCADE,
                    node_id VARCHAR NOT NULL,
                    node_type VARCHAR NOT NULL,
                    node_name VARCHAR NOT NULL,
                    config_hash VARCHAR(64) NOT NULL,
                    config_json JSONB NOT NULL,
                    node_version INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX ix_node_version_index_graph_definition_id
                ON node_version_index (graph_definition_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX ix_node_version_index_workflow_id
                ON node_version_index (workflow_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX ix_node_version_index_node_id
                ON node_version_index (node_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX ix_node_version_index_config_hash
                ON node_version_index (config_hash)
            """)
        )
        conn.execute(
            text("""
                CREATE UNIQUE INDEX _node_version_graph_def_uc
                ON node_version_index (graph_definition_id, node_id)
            """)
        )
        conn.commit()
        logger.info("%s Created node_version_index table successfully", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not create node_version_index table: %s", LOG_PREFIX, e
        )


def add_graph_definition_id_to_evaluation_runs(conn: Connection) -> None:
    """Add graph_definition_id FK column to evaluation_runs table.

    Links evaluation runs to the specific graph definition version that was evaluated.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='evaluation_runs' AND column_name='graph_definition_id'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding graph_definition_id column to evaluation_runs", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE evaluation_runs
                    ADD COLUMN graph_definition_id VARCHAR
                        REFERENCES graph_definitions(id) ON DELETE SET NULL
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX ix_evaluation_runs_graph_definition_id
                    ON evaluation_runs (graph_definition_id)
                """)
            )
            conn.commit()
            logger.info(
                "%s Added graph_definition_id to evaluation_runs successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s graph_definition_id already exists in evaluation_runs", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not add graph_definition_id to evaluation_runs: %s",
            LOG_PREFIX,
            e,
        )


def add_graph_definition_id_to_execution_feedback(conn: Connection) -> None:
    """Add graph_definition_id FK column to execution_feedback table.

    Links feedback directly to the graph definition version for easy version-based queries.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='execution_feedback' AND column_name='graph_definition_id'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding graph_definition_id column to execution_feedback", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE execution_feedback
                    ADD COLUMN graph_definition_id VARCHAR
                        REFERENCES graph_definitions(id) ON DELETE SET NULL
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX ix_execution_feedback_graph_definition_id
                    ON execution_feedback (graph_definition_id)
                """)
            )
            conn.commit()
            logger.info(
                "%s Added graph_definition_id to execution_feedback successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s graph_definition_id already exists in execution_feedback",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add graph_definition_id to execution_feedback: %s",
            LOG_PREFIX,
            e,
        )


def add_node_config_hash_to_node_executions(conn: Connection) -> None:
    """Add node_config_hash column to node_executions table.

    Stores the SHA256 hash of the node's configuration at execution time,
    enabling grouping of execution results by node version.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='node_executions' AND column_name='node_config_hash'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding node_config_hash column to node_executions", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE node_executions
                    ADD COLUMN node_config_hash VARCHAR(64)
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX ix_node_executions_node_config_hash
                    ON node_executions (node_config_hash)
                """)
            )
            conn.commit()
            logger.info(
                "%s Added node_config_hash to node_executions successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s node_config_hash already exists in node_executions", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not add node_config_hash to node_executions: %s",
            LOG_PREFIX,
            e,
        )


def add_evaluation_dataset_workflow_id_column(conn: Connection) -> None:
    """Add workflow_id column to evaluation_datasets table.

    Stores the parent workflow for agent/tool target datasets so the
    workflow name can be resolved directly rather than scanning graph definitions.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='evaluation_datasets' AND column_name='workflow_id'"
            )
        )
        if not result.fetchone():
            logger.info(
                "%s Adding workflow_id column to evaluation_datasets", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE evaluation_datasets
                    ADD COLUMN workflow_id VARCHAR
                    REFERENCES workflows(id) ON DELETE SET NULL
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS ix_evaluation_datasets_workflow_id
                    ON evaluation_datasets (workflow_id)
                """)
            )
            conn.commit()
            logger.info(
                "%s Added workflow_id to evaluation_datasets successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s workflow_id already exists in evaluation_datasets", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not add workflow_id to evaluation_datasets: %s",
            LOG_PREFIX,
            e,
        )


def create_test_case_files_table(conn: Connection) -> None:
    """Create test_case_files table for evaluation dataset file attachments.

    Stores binary file content (BYTEA) attached to individual evaluation
    test cases, enabling file-based workflow evaluations. Files are
    cascade-deleted when their parent test case is removed.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='test_case_files'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating test_case_files table", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE TABLE test_case_files (
                        id VARCHAR PRIMARY KEY,
                        test_case_id VARCHAR NOT NULL
                            REFERENCES evaluation_test_cases(id) ON DELETE CASCADE,
                        filename VARCHAR(255) NOT NULL,
                        mime_type VARCHAR(100) NOT NULL,
                        file_size INTEGER NOT NULL,
                        content BYTEA NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_test_case_files_test_case_id
                    ON test_case_files(test_case_id)
                """)
            )

            conn.commit()
            logger.info("%s Created test_case_files table successfully", LOG_PREFIX)
        else:
            logger.debug("%s test_case_files table already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not create test_case_files table: %s", LOG_PREFIX, e)


def add_dataset_visible_to_groups_column(conn: Connection) -> None:
    """Add visible_to_groups JSONB column to evaluation_datasets table.

    Adds a JSONB column for group-based visibility control on datasets.
    Empty array means private, ["__all__"] means global, specific group
    names restrict access to members of those groups.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='evaluation_datasets'
                AND column_name='visible_to_groups'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding visible_to_groups column to evaluation_datasets",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE evaluation_datasets
                    ADD COLUMN visible_to_groups JSONB NOT NULL DEFAULT '[]'::jsonb
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_evaluation_datasets_visible_to_groups
                    ON evaluation_datasets USING GIN (visible_to_groups)
                """)
            )
            conn.commit()
            logger.info(
                "%s Added visible_to_groups column to evaluation_datasets successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s visible_to_groups column already exists in evaluation_datasets",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add visible_to_groups to evaluation_datasets: %s",
            LOG_PREFIX,
            e,
        )


def add_recommendation_applied_version_columns(conn: Connection) -> None:
    """Add applied_version and applied_graph_definition_id columns to evaluation_recommendations.

    Tracks which graph version a recommendation was applied to so the
    UI can link directly to the correct version.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='evaluation_recommendations' "
                "AND column_name='applied_version'"
            )
        )
        if not result.fetchone():
            logger.info(
                "%s Adding applied_version and applied_graph_definition_id "
                "columns to evaluation_recommendations",
                LOG_PREFIX,
            )
            conn.execute(
                text(
                    "ALTER TABLE evaluation_recommendations "
                    "ADD COLUMN applied_version INTEGER, "
                    "ADD COLUMN applied_graph_definition_id VARCHAR"
                )
            )
            conn.commit()
        else:
            logger.debug(
                "%s applied_version column already exists in evaluation_recommendations",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add applied version columns to evaluation_recommendations: %s",
            LOG_PREFIX,
            e,
        )


def add_judge_output_policy_column(conn: Connection) -> None:
    """Add judge_output_policy JSON column to evaluation_runs table.

    Stores the output extraction policy for the LLM judge, controlling
    which part of the workflow output is evaluated (final node, specific
    node, all nodes) and the max character budget.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='evaluation_runs' "
                "AND column_name='judge_output_policy'"
            )
        )
        if not result.fetchone():
            logger.info(
                "%s Adding judge_output_policy column to evaluation_runs",
                LOG_PREFIX,
            )
            conn.execute(
                text("ALTER TABLE evaluation_runs ADD COLUMN judge_output_policy JSONB")
            )
            conn.commit()
            logger.info("%s Added judge_output_policy column successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s judge_output_policy column already exists in evaluation_runs",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add judge_output_policy column: %s",
            LOG_PREFIX,
            e,
        )


def add_visible_to_groups_to_datasource_connections(conn: Connection) -> None:
    """Add visible_to_groups JSONB column to datasource_connections table.

    Adds a JSONB column for group-based visibility control on database connections.
    Empty array means private, ["__all__"] means global, specific group
    names restrict access to members of those groups.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='datasource_connections'
                AND column_name='visible_to_groups'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding visible_to_groups column to datasource_connections",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE datasource_connections
                    ADD COLUMN visible_to_groups JSONB NOT NULL DEFAULT '[]'::jsonb
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_datasource_connections_visible_to_groups
                    ON datasource_connections USING GIN (visible_to_groups)
                """)
            )
            conn.commit()
            logger.info(
                "%s Added visible_to_groups column to datasource_connections successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s visible_to_groups column already exists on datasource_connections",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add visible_to_groups column to datasource_connections: %s",
            LOG_PREFIX,
            e,
        )


def ensure_api_endpoints_jsonb_columns(conn: Connection) -> None:
    """Ensure api_endpoints.visible_to_groups is JSONB with a GIN index.

    The column may have been created as JSON by SQLAlchemy's create_all.
    JSONB is required for the @> and ?| operators used in visibility queries.

    Args:
        conn: Database connection
    """
    try:
        # Check if the table exists
        result = conn.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name='api_endpoints'
                AND column_name='visible_to_groups'
            """)
        )
        row = result.fetchone()

        if not row:
            logger.debug(
                "%s api_endpoints.visible_to_groups column not found, skipping",
                LOG_PREFIX,
            )
            return

        current_type = row[1]
        if current_type.lower() == "json":
            logger.info(
                "%s Converting api_endpoints.visible_to_groups from JSON to JSONB",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE api_endpoints
                    ALTER COLUMN visible_to_groups TYPE JSONB USING visible_to_groups::text::jsonb
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_api_endpoints_visible_to_groups
                    ON api_endpoints USING GIN (visible_to_groups)
                """)
            )
            conn.commit()
            logger.info(
                "%s Converted api_endpoints.visible_to_groups to JSONB successfully",
                LOG_PREFIX,
            )
        else:
            # Already JSONB, just ensure index exists
            logger.debug(
                "%s api_endpoints.visible_to_groups is already %s",
                LOG_PREFIX,
                current_type,
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_api_endpoints_visible_to_groups
                    ON api_endpoints USING GIN (visible_to_groups)
                """)
            )
            conn.commit()
    except Exception as e:
        logger.warning(
            "%s Could not ensure api_endpoints JSONB columns: %s",
            LOG_PREFIX,
            e,
        )


def update_api_endpoint_name_uniqueness(conn: Connection) -> None:
    """Change api_endpoints.name unique constraint from global to per-user.

    Replaces the global unique constraint on name with a composite
    unique constraint on (name, user_id) so different users can have
    endpoints with the same name.

    Args:
        conn: Database connection
    """
    try:
        # Check if the table exists
        result = conn.execute(
            text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name='api_endpoints'
            """)
        )
        if not result.fetchone():
            logger.debug("%s api_endpoints table not found, skipping", LOG_PREFIX)
            return

        # Check if per-user constraint already exists
        result = conn.execute(
            text("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name='api_endpoints'
                AND constraint_name='uq_api_endpoint_name_user'
            """)
        )
        if result.fetchone():
            logger.debug(
                "%s uq_api_endpoint_name_user constraint already exists", LOG_PREFIX
            )
            return

        # Drop the old global unique constraint on name (may have auto-generated name)
        result = conn.execute(
            text("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name='api_endpoints'
                AND constraint_type='UNIQUE'
                AND constraint_name IN (
                    SELECT constraint_name
                    FROM information_schema.constraint_column_usage
                    WHERE table_name='api_endpoints'
                    AND column_name='name'
                    GROUP BY constraint_name
                    HAVING COUNT(*) = 1
                )
            """)
        )
        old_constraints = [row[0] for row in result.fetchall()]
        for old_name in old_constraints:
            logger.info(
                "%s Dropping old unique constraint %s on api_endpoints.name",
                LOG_PREFIX,
                old_name,
            )
            conn.execute(
                text(f'ALTER TABLE api_endpoints DROP CONSTRAINT "{old_name}"')
            )

        # Create the new per-user unique constraint
        logger.info(
            "%s Creating per-user unique constraint uq_api_endpoint_name_user",
            LOG_PREFIX,
        )
        conn.execute(
            text("""
                ALTER TABLE api_endpoints
                ADD CONSTRAINT uq_api_endpoint_name_user UNIQUE (name, user_id)
            """)
        )
        conn.commit()
        logger.info(
            "%s Updated api_endpoints name uniqueness to per-user successfully",
            LOG_PREFIX,
        )

    except Exception as e:
        logger.warning(
            "%s Could not update api_endpoints name uniqueness: %s",
            LOG_PREFIX,
            e,
        )


def add_api_endpoint_service_type_and_health_columns(conn: Connection) -> None:
    """Add service_type, last_connection_test, and last_connection_status columns to api_endpoints.

    Args:
        conn: Database connection
    """
    try:
        # Check if the table exists
        result = conn.execute(
            text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name='api_endpoints'
            """)
        )
        if not result.fetchone():
            logger.debug("%s api_endpoints table not found, skipping", LOG_PREFIX)
            return

        # Add service_type column if missing
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='api_endpoints' AND column_name='service_type'
            """)
        )
        if not result.fetchone():
            logger.info("%s Adding service_type column to api_endpoints", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE api_endpoints
                    ADD COLUMN service_type VARCHAR(50) NOT NULL DEFAULT 'generic'
                """)
            )

        # Add last_connection_test column if missing
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='api_endpoints' AND column_name='last_connection_test'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding last_connection_test column to api_endpoints", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE api_endpoints
                    ADD COLUMN last_connection_test TIMESTAMPTZ
                """)
            )

        # Add last_connection_status column if missing
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='api_endpoints' AND column_name='last_connection_status'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding last_connection_status column to api_endpoints", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE api_endpoints
                    ADD COLUMN last_connection_status VARCHAR(20)
                """)
            )

        conn.commit()
        logger.info(
            "%s Added service_type and health columns to api_endpoints successfully",
            LOG_PREFIX,
        )

    except Exception as e:
        logger.warning(
            "%s Could not add service_type/health columns to api_endpoints: %s",
            LOG_PREFIX,
            e,
        )


def add_search_count_to_collections(conn: Connection) -> None:
    """Add search_count column to document_collections table.

    Tracks how many searches have been performed against each collection.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='document_collections'
                AND column_name='search_count'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding search_count column to document_collections", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE document_collections
                    ADD COLUMN search_count BIGINT NOT NULL DEFAULT 0
                """)
            )
            conn.commit()
            logger.info(
                "%s Added search_count column to document_collections successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s search_count column already exists in document_collections",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add search_count column to document_collections: %s",
            LOG_PREFIX,
            e,
        )


def add_execution_history_performance_indexes(conn: Connection) -> None:
    """Add indexes to speed up execution history list queries.

    Covers:
    - graph_executions.created_at DESC — used by ORDER BY in every list query
    - graph_executions.status — filtered frequently
    - graph_executions.graph_name — filtered with ILIKE for search
    - graph_executions(workflow_id, user_id) — composite for user access control
    - node_executions.graph_execution_id — FK column used in batched count queries

    All CREATE INDEX statements use IF NOT EXISTS for idempotency.

    Args:
        conn: Database connection
    """
    indexes = [
        (
            "idx_graph_executions_created_at_desc",
            "CREATE INDEX IF NOT EXISTS idx_graph_executions_created_at_desc "
            "ON graph_executions(created_at DESC)",
        ),
        (
            "idx_graph_executions_status",
            "CREATE INDEX IF NOT EXISTS idx_graph_executions_status "
            "ON graph_executions(status)",
        ),
        (
            "idx_graph_executions_graph_name",
            "CREATE INDEX IF NOT EXISTS idx_graph_executions_graph_name "
            "ON graph_executions(graph_name)",
        ),
        (
            "idx_graph_executions_workflow_user",
            "CREATE INDEX IF NOT EXISTS idx_graph_executions_workflow_user "
            "ON graph_executions(workflow_id, user_id)",
        ),
        (
            "idx_node_executions_graph_execution_id",
            "CREATE INDEX IF NOT EXISTS idx_node_executions_graph_execution_id "
            "ON node_executions(graph_execution_id)",
        ),
    ]

    for index_name, ddl in indexes:
        try:
            conn.execute(text(ddl))
            conn.commit()
            logger.info("%s Created index %s", LOG_PREFIX, index_name)
        except Exception as e:
            logger.debug("%s Index %s may already exist: %s", LOG_PREFIX, index_name, e)


def ensure_datasource_connections_jsonb_visible_to_groups(conn: Connection) -> None:
    """Convert datasource_connections.visible_to_groups from json to jsonb if needed.

    The model was initially created with JSON instead of JSONB, causing
    @> and ?| operators to fail. This migration fixes existing columns.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'datasource_connections'
                AND column_name = 'visible_to_groups'
            """)
        )
        row = result.fetchone()
        if row and row[0] == "json":
            logger.info(
                "%s Converting datasource_connections.visible_to_groups from json to jsonb",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE datasource_connections
                    ALTER COLUMN visible_to_groups
                    SET DATA TYPE jsonb USING visible_to_groups::jsonb
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_datasource_connections_visible_to_groups
                    ON datasource_connections USING GIN (visible_to_groups)
                """)
            )
            conn.commit()
            logger.info(
                "%s Converted datasource_connections.visible_to_groups to jsonb successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s datasource_connections.visible_to_groups is already jsonb or does not exist",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not convert datasource_connections.visible_to_groups to jsonb: %s",
            LOG_PREFIX,
            e,
        )


def add_evaluations_navigation_feature_access(conn: Connection) -> None:
    """Add nav.evaluations to feature_access table.

    Seeds the evaluations navigation feature so non-admin users can access
    evaluations when the feature is toggled on (admin_only=False by default).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT COUNT(*) FROM feature_access
                WHERE feature_name = :feature_name
            """),
            {"feature_name": "nav.evaluations"},
        )

        if result.scalar() == 0:
            logger.info("%s Adding navigation feature: nav.evaluations", LOG_PREFIX)
            conn.execute(
                text("""
                    INSERT INTO feature_access (id, feature_name, display_name, admin_only, description)
                    VALUES (gen_random_uuid()::text, :feature_name, :display_name, :admin_only, :description)
                """),
                {
                    "feature_name": "nav.evaluations",
                    "display_name": "Evaluations",
                    "admin_only": False,
                    "description": "Access to workflow evaluation and testing tools",
                },
            )
            conn.commit()
            logger.info(
                "%s nav.evaluations feature access added successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s nav.evaluations feature already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning(
            "%s Could not add nav.evaluations feature access: %s", LOG_PREFIX, e
        )
        conn.rollback()


def add_execution_list_performance_indexes(conn: Connection) -> None:
    """Add composite indexes to speed up execution list queries.

    Covers:
    - graph_executions(status, created_at) — common filter+sort pattern
    - execution_feedback(rating) — used in feedback_rating filter subquery
    - execution_feedback(graph_execution_id, node_execution_id) — batch feedback lookup

    Args:
        conn: Database connection
    """
    indexes = [
        (
            "idx_graph_executions_status_created",
            "CREATE INDEX IF NOT EXISTS idx_graph_executions_status_created "
            "ON graph_executions(status, created_at DESC)",
        ),
        (
            "idx_execution_feedback_rating",
            "CREATE INDEX IF NOT EXISTS idx_execution_feedback_rating "
            "ON execution_feedback(rating)",
        ),
        (
            "idx_execution_feedback_exec_node",
            "CREATE INDEX IF NOT EXISTS idx_execution_feedback_exec_node "
            "ON execution_feedback(graph_execution_id, node_execution_id)",
        ),
    ]

    for index_name, ddl in indexes:
        try:
            conn.execute(text(ddl))
            conn.commit()
            logger.info("%s Created index %s", LOG_PREFIX, index_name)
        except Exception as e:
            logger.debug("%s Index %s may already exist: %s", LOG_PREFIX, index_name, e)


def create_tutorial_step_overrides_table(conn: Connection) -> None:
    """Create tutorial_step_overrides table for admin-customizable tutorial positioning."""
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'tutorial_step_overrides'
            """)
        )
        if not result.fetchone():
            logger.info("%s Creating tutorial_step_overrides table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE tutorial_step_overrides (
                        id VARCHAR PRIMARY KEY,
                        tutorial_id VARCHAR NOT NULL,
                        step_index INTEGER NOT NULL,
                        popover_offset_x INTEGER NOT NULL DEFAULT 0,
                        popover_offset_y INTEGER NOT NULL DEFAULT 0,
                        pointer_offset_x INTEGER NOT NULL DEFAULT 0,
                        pointer_offset_y INTEGER NOT NULL DEFAULT 0,
                        title TEXT,
                        description TEXT,
                        interaction_hint TEXT,
                        updated_by VARCHAR,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ,
                        CONSTRAINT uq_tutorial_step_override UNIQUE (tutorial_id, step_index)
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_tutorial_step_overrides_tutorial_id
                    ON tutorial_step_overrides(tutorial_id)
                """)
            )
            conn.commit()
            logger.info(
                "%s Created tutorial_step_overrides table successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s tutorial_step_overrides table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not create tutorial_step_overrides table: %s", LOG_PREFIX, e
        )


def add_breakpoint_to_tutorial_step_overrides(conn: Connection) -> None:
    """Add breakpoint column to tutorial_step_overrides for separate desktop/compact overrides."""
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'tutorial_step_overrides' AND column_name = 'breakpoint'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding breakpoint column to tutorial_step_overrides", LOG_PREFIX
            )
            conn.execute(
                text(
                    "ALTER TABLE tutorial_step_overrides ADD COLUMN breakpoint VARCHAR NOT NULL DEFAULT 'desktop'"
                )
            )
            # Replace old unique constraint with new one that includes breakpoint
            conn.execute(
                text(
                    "ALTER TABLE tutorial_step_overrides DROP CONSTRAINT IF EXISTS uq_tutorial_step_override"
                )
            )
            conn.execute(
                text("""
                    ALTER TABLE tutorial_step_overrides
                    ADD CONSTRAINT uq_tutorial_step_override_bp UNIQUE (tutorial_id, step_index, breakpoint)
                """)
            )
            conn.commit()
            logger.info("%s Added breakpoint column successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s breakpoint column already exists on tutorial_step_overrides",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add breakpoint column to tutorial_step_overrides: %s",
            LOG_PREFIX,
            e,
        )


def create_tutorial_progress_table(conn: Connection) -> None:
    """Create tutorial_progress table for per-user tutorial completion tracking."""
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'tutorial_progress'
            """)
        )
        if not result.fetchone():
            logger.info("%s Creating tutorial_progress table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE tutorial_progress (
                        id VARCHAR PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        completed_tutorials JSONB NOT NULL DEFAULT '{}',
                        last_step_reached JSONB NOT NULL DEFAULT '{}',
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ
                    )
                """)
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX ix_tutorial_progress_user_id ON tutorial_progress (user_id)"
                )
            )
            conn.commit()
            logger.info("%s Created tutorial_progress table successfully", LOG_PREFIX)
        else:
            logger.debug("%s tutorial_progress table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not create tutorial_progress table: %s", LOG_PREFIX, e)




def create_chat_sessions_table(conn: Connection) -> None:
    """Create chat_sessions table for conversational workflow interaction.

    Stores metadata for chat sessions — conversations between users and
    published workflows. Message content is derived from linked GraphExecution
    and ConversationMemory records.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='chat_sessions'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating chat_sessions table", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE TABLE chat_sessions (
                        id VARCHAR PRIMARY KEY,
                        title VARCHAR NOT NULL,
                        workflow_id VARCHAR NOT NULL
                            REFERENCES workflows(id) ON DELETE CASCADE,
                        user_id VARCHAR NOT NULL,
                        workflow_name VARCHAR NOT NULL,
                        last_message_at TIMESTAMP WITH TIME ZONE,
                        message_count INTEGER NOT NULL DEFAULT 0,
                        is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_chat_sessions_user_id
                    ON chat_sessions(user_id)
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_chat_sessions_workflow_id
                    ON chat_sessions(workflow_id)
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_chat_sessions_user_workflow
                    ON chat_sessions(user_id, workflow_id)
                """)
            )

            conn.commit()
            logger.info("%s Created chat_sessions table successfully", LOG_PREFIX)
        else:
            logger.debug("%s chat_sessions table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not create chat_sessions table: %s", LOG_PREFIX, e)

def add_chat_session_id_to_graph_executions(conn: Connection) -> None:
    """Add chat_session_id column to graph_executions table.

    Links executions to chat sessions for chat-triggered workflows.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='graph_executions' AND column_name='chat_session_id'"
            )
        )

        if not result.fetchone():
            logger.info("%s Adding chat_session_id column to graph_executions", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE graph_executions
                    ADD COLUMN chat_session_id VARCHAR
                        REFERENCES chat_sessions(id) ON DELETE SET NULL
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_graph_executions_chat_session
                    ON graph_executions (chat_session_id, created_at DESC)
                """)
            )
            conn.commit()
            logger.info("%s Added chat_session_id column successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s chat_session_id column already exists on graph_executions", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not add chat_session_id to graph_executions: %s", LOG_PREFIX, e
        )

def add_chat_session_id_to_conversation_memories(conn: Connection) -> None:
    """Add chat_session_id column to conversation_memories table.

    Enables chat-scoped memory filtering for robust memory isolation
    between chat sessions.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='conversation_memories' AND column_name='chat_session_id'"
            )
        )

        if not result.fetchone():
            logger.info(
                "%s Adding chat_session_id column to conversation_memories", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE conversation_memories
                    ADD COLUMN chat_session_id VARCHAR
                        REFERENCES chat_sessions(id) ON DELETE SET NULL
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS idx_conversation_memories_chat_session
                    ON conversation_memories (chat_session_id)
                """)
            )
            conn.commit()
            logger.info("%s Added chat_session_id column successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s chat_session_id column already exists on conversation_memories",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add chat_session_id to conversation_memories: %s",
            LOG_PREFIX,
            e,
        )

def add_chat_navigation_feature_access(conn: Connection) -> None:
    """Add nav.chat to feature_access table.

    Seeds the chat navigation feature so users can access the chat UI
    when the feature is toggled on (admin_only=False by default).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT COUNT(*) FROM feature_access
                WHERE feature_name = :feature_name
            """),
            {"feature_name": "nav.chat"},
        )

        if result.scalar() == 0:
            logger.info("%s Adding navigation feature: nav.chat", LOG_PREFIX)
            conn.execute(
                text("""
                    INSERT INTO feature_access (id, feature_name, display_name, admin_only, description)
                    VALUES (gen_random_uuid()::text, :feature_name, :display_name, :admin_only, :description)
                """),
                {
                    "feature_name": "nav.chat",
                    "display_name": "Chat",
                    "admin_only": False,
                    "description": "Chat with published workflows",
                },
            )
            conn.commit()
            logger.info("%s Added nav.chat feature access", LOG_PREFIX)
        else:
            logger.debug("%s nav.chat feature access already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not add chat feature access: %s", LOG_PREFIX, e
        )

def seed_wiki_pages(conn: Connection) -> None:
    """Seed wiki_pages and wiki_revisions with built-in documentation.

    Idempotent: skips pages whose slugs already exist. Runs after create_all()
    has created the wiki_pages and wiki_revisions tables.

    Args:
        conn: Database connection
    """
    try:
        for page in WIKI_SEED_PAGES:
            slug = page["slug"]

            existing = conn.execute(
                text("SELECT id FROM wiki_pages WHERE slug = :slug"),
                {"slug": slug},
            ).fetchone()

            if existing:
                logger.debug("%s Wiki page already exists, skipping: %s", LOG_PREFIX, slug)
                continue

            page_id = conn.execute(
                text(
                    """
                    INSERT INTO wiki_pages
                        (id, slug, title, content, order_index, is_published,
                         created_by, updated_by, created_at, updated_at)
                    VALUES
                        (gen_random_uuid()::text, :slug, :title, :content, :order_index,
                         TRUE, 'system', 'system', NOW(), NOW())
                    RETURNING id
                    """
                ),
                {
                    "slug": slug,
                    "title": page["title"],
                    "content": page["content"],
                    "order_index": page["order_index"],
                },
            ).scalar()

            conn.execute(
                text(
                    """
                    INSERT INTO wiki_revisions
                        (id, page_id, title, content, version, created_by,
                         change_summary, created_at)
                    VALUES
                        (gen_random_uuid()::text, :page_id, :title, :content,
                         1, 'system', 'Initial import from built-in documentation', NOW())
                    """
                ),
                {"page_id": page_id, "title": page["title"], "content": page["content"]},
            )

            conn.execute(
                text(
                    """
                    UPDATE wiki_pages
                    SET search_vector = to_tsvector('english', :combined)
                    WHERE id = :page_id
                    """
                ),
                {"combined": f"{page['title']} {page['content']}", "page_id": page_id},
            )

            logger.info("%s Seeded wiki page: %s", LOG_PREFIX, slug)

        conn.commit()
        logger.info("%s Wiki seed migration complete", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not seed wiki pages: %s", LOG_PREFIX, e)
        conn.rollback()

def create_wiki_images_table(conn: Connection) -> None:
    """Create wiki_images table for storing uploaded wiki images in PostgreSQL."""
    try:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS wiki_images (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    filename VARCHAR(255) NOT NULL,
                    mime_type VARCHAR(100) NOT NULL,
                    file_size INTEGER NOT NULL,
                    content BYTEA NOT NULL,
                    created_by VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_wiki_images_created_at
                ON wiki_images (created_at DESC)
            """)
        )
        conn.commit()
        logger.info("%s wiki_images table created successfully", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not create wiki_images table: %s", LOG_PREFIX, e)
        conn.rollback()

def add_wiki_search_vector_index(conn: Connection) -> None:
    """Add GIN index on wiki_pages search_vector for full-text search performance."""
    try:
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_wiki_pages_search_vector
                ON wiki_pages USING GIN (search_vector)
            """)
        )
        conn.commit()
        logger.info("%s Created GIN index on wiki_pages.search_vector", LOG_PREFIX)
    except Exception as e:
        logger.warning("%s Could not create wiki search_vector index: %s", LOG_PREFIX, e)
        conn.rollback()


def create_guardrail_violations_table(conn: Connection) -> None:
    """Create guardrail_violations table and indexes (Phase 3).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='guardrail_violations'
            """)
        )
        if not result.fetchone():
            logger.info("%s Creating guardrail_violations table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE guardrail_violations (
                        id VARCHAR PRIMARY KEY,
                        policy_id VARCHAR REFERENCES guardrail_policies(id) ON DELETE SET NULL,
                        policy_name VARCHAR(255),
                        rule_name VARCHAR(255) NOT NULL,
                        category VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) NOT NULL,
                        action_taken VARCHAR(20) NOT NULL,
                        message TEXT,
                        execution_id VARCHAR NOT NULL,
                        node_execution_id VARCHAR,
                        workflow_id VARCHAR,
                        agent_node_id VARCHAR,
                        agent_node_name VARCHAR(255),
                        tool_name VARCHAR(255),
                        user_id VARCHAR,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
            )
            conn.execute(
                text("CREATE INDEX idx_gv_policy_id ON guardrail_violations(policy_id)")
            )
            conn.execute(
                text("CREATE INDEX idx_gv_severity ON guardrail_violations(severity)")
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_execution_id ON guardrail_violations(execution_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_node_execution_id ON guardrail_violations(node_execution_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_workflow_id ON guardrail_violations(workflow_id)"
                )
            )
            conn.execute(
                text("CREATE INDEX idx_gv_user_id ON guardrail_violations(user_id)")
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_created_at ON guardrail_violations(created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_policy_severity_created ON guardrail_violations(policy_id, severity, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_workflow_created ON guardrail_violations(workflow_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_execution_created ON guardrail_violations(execution_id, created_at)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gv_user_created ON guardrail_violations(user_id, created_at)"
                )
            )
            conn.commit()
            logger.info("%s Created guardrail_violations table", LOG_PREFIX)
        else:
            logger.debug("%s guardrail_violations table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not create guardrail_violations table: %s", LOG_PREFIX, e
        )


def create_guardrail_policy_versions_table(conn: Connection) -> None:
    """Create guardrail_policy_versions table (Phase 4).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='guardrail_policy_versions'
            """)
        )
        if not result.fetchone():
            logger.info("%s Creating guardrail_policy_versions table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE guardrail_policy_versions (
                        id VARCHAR PRIMARY KEY,
                        policy_id VARCHAR NOT NULL REFERENCES guardrail_policies(id) ON DELETE CASCADE,
                        version INTEGER NOT NULL,
                        config_snapshot JSONB NOT NULL,
                        name_snapshot VARCHAR(255) NOT NULL,
                        description_snapshot TEXT,
                        changed_by VARCHAR NOT NULL,
                        change_summary TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        CONSTRAINT uq_guardrail_policy_version UNIQUE (policy_id, version)
                    )
                """)
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gpv_policy_id ON guardrail_policy_versions(policy_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gpv_policy_version ON guardrail_policy_versions(policy_id, version)"
                )
            )
            conn.commit()
            logger.info("%s Created guardrail_policy_versions table", LOG_PREFIX)
        else:
            logger.debug(
                "%s guardrail_policy_versions table already exists", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not create guardrail_policy_versions table: %s", LOG_PREFIX, e
        )


def create_guardrail_violation_feedback_table(conn: Connection) -> None:
    """Create guardrail_violation_feedback table (Phase 4).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='guardrail_violation_feedback'
            """)
        )
        if not result.fetchone():
            logger.info("%s Creating guardrail_violation_feedback table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE guardrail_violation_feedback (
                        id VARCHAR PRIMARY KEY,
                        violation_id VARCHAR NOT NULL REFERENCES guardrail_violations(id) ON DELETE CASCADE,
                        user_id VARCHAR NOT NULL,
                        rating VARCHAR(20) NOT NULL,
                        comment TEXT,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ,
                        CONSTRAINT uq_violation_user_feedback UNIQUE (violation_id, user_id)
                    )
                """)
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gvf_violation_id ON guardrail_violation_feedback(violation_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_gvf_user_id ON guardrail_violation_feedback(user_id)"
                )
            )
            conn.commit()
            logger.info("%s Created guardrail_violation_feedback table", LOG_PREFIX)
        else:
            logger.debug(
                "%s guardrail_violation_feedback table already exists", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not create guardrail_violation_feedback table: %s", LOG_PREFIX, e
        )


def add_is_builtin_column_to_guardrail_policies(conn: Connection) -> None:
    """Add is_builtin BOOLEAN column to guardrail_policies (Phase 4).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='guardrail_policies' AND column_name='is_builtin'
            """)
        )
        if not result.fetchone():
            logger.info("%s Adding is_builtin column to guardrail_policies", LOG_PREFIX)
            conn.execute(
                text("""
                    ALTER TABLE guardrail_policies
                    ADD COLUMN is_builtin BOOLEAN NOT NULL DEFAULT FALSE
                """)
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_guardrail_policies_is_builtin ON guardrail_policies(is_builtin)"
                )
            )
            conn.commit()
            logger.info("%s Added is_builtin column to guardrail_policies", LOG_PREFIX)
        else:
            logger.debug(
                "%s is_builtin column already exists on guardrail_policies", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not add is_builtin column to guardrail_policies: %s",
            LOG_PREFIX,
            e,
        )


def add_guardrail_policy_versioning_columns(conn: Connection) -> None:
    """Add current_version and version_count columns to guardrail_policies (Phase 4).

    Args:
        conn: Database connection
    """
    try:
        # Check if current_version column exists
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='guardrail_policies' AND column_name='current_version'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding current_version column to guardrail_policies", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE guardrail_policies
                    ADD COLUMN current_version INTEGER NOT NULL DEFAULT 1
                """)
            )
        else:
            logger.debug(
                "%s current_version column already exists on guardrail_policies",
                LOG_PREFIX,
            )

        # Check if version_count column exists
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='guardrail_policies' AND column_name='version_count'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding version_count column to guardrail_policies", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE guardrail_policies
                    ADD COLUMN version_count INTEGER NOT NULL DEFAULT 1
                """)
            )
        else:
            logger.debug(
                "%s version_count column already exists on guardrail_policies",
                LOG_PREFIX,
            )

        # Commit the changes
        conn.commit()
    except Exception as e:
        logger.warning(
            "%s Could not add versioning columns to guardrail_policies: %s",
            LOG_PREFIX,
            e,
        )


def fix_guardrail_policy_versions_schema(conn: Connection) -> None:
    """Fix guardrail_policy_versions table schema.

    The table may have been created with 'version_number' instead of 'version',
    and may be missing 'name_snapshot' and 'description_snapshot' columns.

    Args:
        conn: Database connection
    """
    try:
        # Check if 'version_number' exists and 'version' does not
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='guardrail_policy_versions' AND column_name='version_number'
            """)
        )
        if result.fetchone():
            logger.info(
                "%s Renaming version_number -> version on guardrail_policy_versions",
                LOG_PREFIX,
            )
            # Drop old constraints/indexes that reference version_number
            conn.execute(
                text("""
                ALTER TABLE guardrail_policy_versions
                RENAME COLUMN version_number TO version
            """)
            )
            conn.commit()
            logger.info("%s Renamed version_number to version", LOG_PREFIX)

        # Add name_snapshot if missing
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='guardrail_policy_versions' AND column_name='name_snapshot'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding name_snapshot column to guardrail_policy_versions",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                ALTER TABLE guardrail_policy_versions
                ADD COLUMN name_snapshot VARCHAR(255)
            """)
            )
            conn.commit()

        # Add description_snapshot if missing
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='guardrail_policy_versions' AND column_name='description_snapshot'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding description_snapshot column to guardrail_policy_versions",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                ALTER TABLE guardrail_policy_versions
                ADD COLUMN description_snapshot TEXT
            """)
            )
            conn.commit()

        # Ensure unique constraint exists with correct column name
        result = conn.execute(
            text("""
                SELECT constraint_name FROM information_schema.table_constraints
                WHERE table_name='guardrail_policy_versions'
                AND constraint_name='uq_guardrail_policy_version'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding unique constraint uq_guardrail_policy_version", LOG_PREFIX
            )
            conn.execute(
                text("""
                ALTER TABLE guardrail_policy_versions
                ADD CONSTRAINT uq_guardrail_policy_version UNIQUE (policy_id, version)
            """)
            )
            conn.commit()

        # Ensure index exists
        result = conn.execute(
            text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename='guardrail_policy_versions' AND indexname='idx_gpv_policy_version'
            """)
        )
        if not result.fetchone():
            conn.execute(
                text(
                    "CREATE INDEX idx_gpv_policy_version ON guardrail_policy_versions(policy_id, version)"
                )
            )
            conn.commit()

    except Exception as e:
        logger.warning(
            "%s Could not fix guardrail_policy_versions schema: %s", LOG_PREFIX, e
        )


def migrate_inline_guardrails_to_policies(conn: Connection) -> None:
    """One-time migration: extract inline guardrails_config from agent nodes
    into guardrail_policies + guardrail_policy_versions + guardrail_assignments,
    then null out the inline config.

    Idempotent: find-or-create semantics at every step.
    Scope: is_latest=True graph definitions only.
    """
    import json
    import uuid

    try:
        # Ensure guardrail_policies table exists (may have been created by ORM)
        result = conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name='guardrail_policies'
            )
        """)
        )
        if not result.scalar():
            logger.info(
                "%s guardrail_policies table does not exist — skipping inline migration",
                LOG_PREFIX,
            )
            return

        # Fetch latest graph definitions
        rows = conn.execute(
            text("""
            SELECT gd.id, gd.definition_json, gd.created_by, gd.name AS graph_name,
                   gd.workflow_id
            FROM graph_definitions gd
            WHERE gd.is_latest = TRUE
        """)
        ).fetchall()

        total_policies = 0
        total_assignments = 0

        for row in rows:
            gd_id = row[0]
            definition_json = row[1]
            created_by = row[2]
            graph_name = row[3] or "Unnamed Workflow"
            workflow_id = row[4]

            if not definition_json:
                continue

            if isinstance(definition_json, str):
                try:
                    definition = json.loads(definition_json)
                except (json.JSONDecodeError, TypeError):
                    continue
            else:
                definition = definition_json

            nodes = definition.get("nodes", [])
            if not nodes:
                continue

            seen_names = set()
            modified = False

            for node in nodes:
                node_type = node.get("type", "")
                if node_type != "AGENT":
                    continue

                agent_config = node.get("agent_config")
                if not agent_config:
                    continue

                gc = agent_config.get("guardrails_config")
                if not gc:
                    continue

                if not gc.get("enabled", False):
                    continue

                # Check that at least one rule or meaningful config exists
                has_rules = bool(
                    gc.get("pattern_rules")
                    or gc.get("custom_filters")
                    or gc.get("tool_call_policy")
                    or gc.get("token_budget")
                    or gc.get("behavioral")
                )
                if not has_rules:
                    continue

                node_name = node.get("name", node.get("label", "Agent"))
                node_uniq_id = node.get("uniq_id") or node.get("id", "")

                # Build candidate name
                candidate_name = f"{graph_name} - {node_name}"[:250]
                if candidate_name in seen_names:
                    suffix = node_uniq_id[:6] if node_uniq_id else uuid.uuid4().hex[:6]
                    candidate_name = f"{candidate_name[:244]} ({suffix})"
                seen_names.add(candidate_name)

                # Translate filter scopes (ingress/egress -> inlet/outlet)
                custom_filters = gc.get("custom_filters", [])
                if custom_filters:
                    scope_map = {"ingress": "inlet", "egress": "outlet"}
                    for f in custom_filters:
                        if (
                            isinstance(f, dict)
                            and f.get("filter_type") == "python_code"
                        ):
                            old_scope = f.get("scope", "both")
                            f["scope"] = scope_map.get(old_scope, old_scope)

                # Find-or-create policy
                existing_policy = conn.execute(
                    text("""
                    SELECT id FROM guardrail_policies
                    WHERE name = :name AND created_by = :created_by
                """),
                    {"name": candidate_name, "created_by": created_by or "__system__"},
                ).fetchone()

                if existing_policy:
                    policy_id = existing_policy[0]
                else:
                    policy_id = str(uuid.uuid4())
                    conn.execute(
                        text("""
                        INSERT INTO guardrail_policies (id, name, description, config, scope, is_compulsory,
                            applies_to, created_by, shared_with, is_template, tags, version,
                            current_version, version_count, created_at)
                        VALUES (:id, :name, :description, :config::jsonb, 'user', FALSE,
                            '[]'::jsonb, :created_by, '[]'::jsonb, FALSE, '[]'::jsonb, 1, 1, 1, NOW())
                    """),
                        {
                            "id": policy_id,
                            "name": candidate_name,
                            "description": f"Migrated from {graph_name} - {node_name}",
                            "config": json.dumps(gc),
                            "created_by": created_by or "__system__",
                        },
                    )
                    total_policies += 1

                # Find-or-create version
                existing_version = conn.execute(
                    text("""
                    SELECT id FROM guardrail_policy_versions
                    WHERE policy_id = :policy_id AND version = 1
                """),
                    {"policy_id": policy_id},
                ).fetchone()

                if not existing_version:
                    conn.execute(
                        text("""
                        INSERT INTO guardrail_policy_versions (id, policy_id, version, config_snapshot,
                            name_snapshot, description_snapshot, changed_by, change_summary, created_at)
                        VALUES (:id, :policy_id, 1, :config::jsonb, :name, :description,
                            :changed_by, 'Initial migration from inline config', NOW())
                    """),
                        {
                            "id": str(uuid.uuid4()),
                            "policy_id": policy_id,
                            "config": json.dumps(gc),
                            "name": candidate_name,
                            "description": f"Migrated from {graph_name} - {node_name}",
                            "changed_by": created_by or "__system__",
                        },
                    )

                # Find-or-create assignment
                existing_assignment = conn.execute(
                    text("""
                    SELECT id FROM guardrail_assignments
                    WHERE policy_id = :policy_id AND target_type = 'agent_node'
                        AND target_id = :target_id
                """),
                    {"policy_id": policy_id, "target_id": node_uniq_id},
                ).fetchone()

                if not existing_assignment:
                    conn.execute(
                        text("""
                        INSERT INTO guardrail_assignments (id, policy_id, target_type, target_id,
                            workflow_id, priority, override_mode, assigned_by, created_at)
                        VALUES (:id, :policy_id, 'agent_node', :target_id, :workflow_id,
                            500, 'merge', :assigned_by, NOW())
                    """),
                        {
                            "id": str(uuid.uuid4()),
                            "policy_id": policy_id,
                            "target_id": node_uniq_id,
                            "workflow_id": workflow_id,
                            "assigned_by": created_by or "__system__",
                        },
                    )
                    total_assignments += 1

                # Null out inline config
                agent_config["guardrails_config"] = None
                modified = True

            if modified:
                conn.execute(
                    text("""
                    UPDATE graph_definitions SET definition_json = :definition_json::jsonb
                    WHERE id = :id
                """),
                    {"definition_json": json.dumps(definition), "id": gd_id},
                )
                conn.commit()

        logger.info(
            "%s Inline guardrails migration complete: %d policies, %d assignments created",
            LOG_PREFIX,
            total_policies,
            total_assignments,
        )

    except Exception as e:
        logger.warning(
            "%s Could not migrate inline guardrails to policies: %s", LOG_PREFIX, e
        )


def add_visible_to_groups_to_guardrail_policies(conn: Connection) -> None:
    """Add visible_to_groups JSONB column to guardrail_policies table.

    Mirrors the collection/datasource sharing pattern:
      []            → private (owner only)
      ["__all__"]   → visible to everyone
      ["grp1", …]  → visible to listed groups

    Migrates existing scope/shared_with data:
      scope='global'  →  ["__all__"]
      shared_with containing 'all'  →  ["__all__"]
      otherwise  →  []

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='guardrail_policies'
                AND column_name='visible_to_groups'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding visible_to_groups column to guardrail_policies",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE guardrail_policies
                    ADD COLUMN visible_to_groups JSONB NOT NULL DEFAULT '[]'::jsonb
                """)
            )

            # Migrate existing data: global scope or shared_with containing "all" → ["__all__"]
            conn.execute(
                text("""
                    UPDATE guardrail_policies
                    SET visible_to_groups = '["__all__"]'::jsonb
                    WHERE scope = 'global'
                       OR (shared_with IS NOT NULL AND shared_with @> '"all"'::jsonb)
                """)
            )

            # Add GIN index for efficient group overlap queries
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS ix_guardrail_policies_visible_to_groups
                    ON guardrail_policies USING GIN (visible_to_groups)
                """)
            )

            logger.info(
                "%s visible_to_groups column added to guardrail_policies with data migrated",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s visible_to_groups column already exists on guardrail_policies",
                LOG_PREFIX,
            )

    except Exception as e:
        logger.warning(
            "%s Could not add visible_to_groups to guardrail_policies: %s",
            LOG_PREFIX,
            e,
        )


def create_group_external_service_configs_table(conn: Connection) -> None:
    """Create group_external_service_configs table for group-tier MCP tool sharing.

    This table stores admin-managed MCP tool configurations scoped to groups,
    enabling the personal → group → system credential resolution order.
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'group_external_service_configs'
            """)
        )
        if not result.fetchone():
            logger.info("%s Creating group_external_service_configs table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE group_external_service_configs (
                        id VARCHAR PRIMARY KEY,
                        service_name VARCHAR(100) NOT NULL,
                        display_name VARCHAR(255),
                        description TEXT,
                        service_url TEXT,
                        auth_type VARCHAR(50) NOT NULL DEFAULT 'api_key_header',
                        encrypted_api_key VARCHAR NOT NULL DEFAULT '',
                        encrypted_credentials JSONB,
                        settings JSONB NOT NULL DEFAULT '{}',
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_group_external_service_configs_service_name
                    ON group_external_service_configs (service_name)
                """)
            )
            conn.commit()
            logger.info(
                "%s Created group_external_service_configs table successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s group_external_service_configs table already exists", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not create group_external_service_configs table: %s",
            LOG_PREFIX,
            e,
        )


def create_group_external_service_assignments_table(conn: Connection) -> None:
    """Create group_external_service_assignments table.

    Maps group_external_service_configs records to one or more groups,
    supporting the admin use-case of assigning a single MCP config to
    multiple groups.
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name = 'group_external_service_assignments'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Creating group_external_service_assignments table", LOG_PREFIX
            )
            conn.execute(
                text("""
                    CREATE TABLE group_external_service_assignments (
                        id VARCHAR PRIMARY KEY,
                        config_id VARCHAR(36) NOT NULL REFERENCES group_external_service_configs(id) ON DELETE CASCADE,
                        group_id VARCHAR(36) NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_group_ext_svc_assignments_config
                    ON group_external_service_assignments (config_id)
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_group_ext_svc_assignments_group
                    ON group_external_service_assignments (group_id)
                """)
            )
            conn.execute(
                text("""
                    CREATE UNIQUE INDEX idx_group_ext_svc_assignments_unique
                    ON group_external_service_assignments (config_id, group_id)
                """)
            )
            conn.commit()
            logger.info(
                "%s Created group_external_service_assignments table successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s group_external_service_assignments table already exists", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not create group_external_service_assignments table: %s",
            LOG_PREFIX,
            e,
        )


def add_mcp_shared_with_groups_column(conn: Connection) -> None:
    """Add shared_with_group_ids JSONB column to user_external_services.

    This column stores which groups an MCP server is shared with:
    - [] = private (only owner)
    - ["__all__"] = shared with everyone
    - ["group-id-1", "group-id-2"] = shared with specific groups

    Existing PUBLIC servers are migrated to shared_with_group_ids = '["__all__"]'.
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='user_external_services'
                AND column_name='shared_with_group_ids'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Adding shared_with_group_ids column to user_external_services",
                LOG_PREFIX,
            )

            conn.execute(
                text("""
                    ALTER TABLE user_external_services
                    ADD COLUMN shared_with_group_ids JSONB NOT NULL DEFAULT '[]'
                """)
            )

            # Migrate existing PUBLIC servers to shared with everyone
            conn.execute(
                text("""
                    UPDATE user_external_services
                    SET shared_with_group_ids = '["__all__"]'
                    WHERE visibility = 'PUBLIC'
                """)
            )

            conn.commit()
            logger.info(
                "%s Added shared_with_group_ids column and migrated existing public servers",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s shared_with_group_ids column already exists on user_external_services",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add shared_with_group_ids column: %s", LOG_PREFIX, e
        )


def add_guardrails_navigation_feature_access(conn: Connection) -> None:
    """Add nav.guardrails to feature_access table.

    Seeds the guardrails navigation feature so non-admin users can access
    guardrails when the feature is toggled on (admin_only=False by default).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT COUNT(*) FROM feature_access
                WHERE feature_name = :feature_name
            """),
            {"feature_name": "nav.guardrails"},
        )

        if result.scalar() == 0:
            logger.info("%s Adding navigation feature: nav.guardrails", LOG_PREFIX)
            conn.execute(
                text("""
                    INSERT INTO feature_access (id, feature_name, display_name, admin_only, description)
                    VALUES (gen_random_uuid()::text, :feature_name, :display_name, :admin_only, :description)
                """),
                {
                    "feature_name": "nav.guardrails",
                    "display_name": "Guardrails",
                    "admin_only": False,
                    "description": "Access to guardrail policies and violation monitoring",
                },
            )
            conn.commit()
            logger.info(
                "%s nav.guardrails feature access added successfully", LOG_PREFIX
            )
        else:
            logger.debug("%s nav.guardrails feature already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning(
            "%s Could not add nav.guardrails feature access: %s", LOG_PREFIX, e
        )
        conn.rollback()


def create_scope_rejection_log_table(conn: Connection) -> None:
    """Create scope_rejection_log table for PAT scope enforcement audit trail.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='scope_rejection_log'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating scope_rejection_log table", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE TABLE scope_rejection_log (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        token_id VARCHAR REFERENCES user_api_tokens(id) ON DELETE SET NULL,
                        token_prefix VARCHAR(12),
                        user_id VARCHAR,
                        resource VARCHAR NOT NULL,
                        scope_required VARCHAR NOT NULL,
                        scopes_held VARCHAR,
                        client_ip VARCHAR,
                        timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    )
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_scope_rejection_log_token_id
                    ON scope_rejection_log(token_id, timestamp DESC)
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_scope_rejection_log_timestamp
                    ON scope_rejection_log(timestamp DESC)
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX idx_scope_rejection_log_user_id
                    ON scope_rejection_log(user_id)
                """)
            )

            conn.commit()
            logger.info("%s Created scope_rejection_log table successfully", LOG_PREFIX)
        else:
            logger.debug("%s scope_rejection_log table already exists", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not create scope_rejection_log table: %s", LOG_PREFIX, e)


def seed_api_tokens_restrict_feature_access(conn: Connection) -> None:
    """Seed api_tokens.restrict_to_workflow feature access row.

    When admin_only=True (the default), non-admin users can only create tokens
    with workflow-scoped permissions. Admins can toggle this via the admin UI.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT id FROM feature_access
                WHERE feature_name = 'api_tokens.restrict_to_workflow'
            """)
        )

        if not result.fetchone():
            logger.info(
                "%s Seeding api_tokens.restrict_to_workflow feature access row", LOG_PREFIX
            )
            conn.execute(
                text("""
                    INSERT INTO feature_access (id, feature_name, display_name, admin_only, description)
                    VALUES (
                        gen_random_uuid()::text,
                        'api_tokens.restrict_to_workflow',
                        'Restrict token scopes to workflow only (non-admins)',
                        TRUE,
                        'When enabled, non-admin users can only create tokens with workflow:* scopes.'
                    )
                """)
            )
            conn.commit()
            logger.info(
                "%s Seeded api_tokens.restrict_to_workflow feature access row", LOG_PREFIX
            )
        else:
            logger.debug(
                "%s api_tokens.restrict_to_workflow feature access row already exists",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not seed api_tokens.restrict_to_workflow: %s", LOG_PREFIX, e
        )


def migrate_pat_scopes_to_v2(conn: Connection) -> None:
    """Migrate existing PAT scopes from legacy two-part format to v2 three-part taxonomy.

    Rules:
      - ``workflow:*``        → ``workflow:*:execute``
      - ``workflow:<name>``   → ``workflow:<name>:execute``
      - Three-part scopes that are already valid are left unchanged (idempotent).

    Args:
        conn: Database connection
    """
    try:
        logger.info("%s Migrating PAT scopes to v2 taxonomy", LOG_PREFIX)

        # Fetch all tokens that have scopes in JSON format
        result = conn.execute(
            text("SELECT id, scopes FROM user_api_tokens WHERE scopes IS NOT NULL")
        )
        rows = result.fetchall()

        import json
        import re

        named_resource_pattern = re.compile(
            r"^(workflow|document|datasource|execution|memory):[^:*]+:(read|write|execute)$"
        )
        valid_three_part = {
            "workflow:*:read", "workflow:*:execute", "workflow:*:write",
            "document:*:read", "document:*:write",
            "datasource:*:read", "datasource:*:write",
            "execution:*:read",
            "memory:*:read", "memory:*:write",
            "api:*",
        }

        updated = 0
        for row in rows:
            token_id, scopes_raw = row[0], row[1]
            try:
                scopes = json.loads(scopes_raw) if isinstance(scopes_raw, str) else scopes_raw
            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "%s Could not parse scopes for token %s: %s", LOG_PREFIX, token_id, scopes_raw
                )
                continue

            if not isinstance(scopes, list):
                continue

            new_scopes = []
            changed = False
            for scope in scopes:
                if not isinstance(scope, str):
                    new_scopes.append(scope)
                    continue

                # Already a valid three-part scope → keep as-is
                if scope in valid_three_part or named_resource_pattern.match(scope):
                    new_scopes.append(scope)
                    continue

                # Legacy "workflow:*" → "workflow:*:execute"
                if scope == "workflow:*":
                    new_scopes.append("workflow:*:execute")
                    changed = True
                    continue

                # Legacy "workflow:<name>" → "workflow:<name>:execute"
                if scope.startswith("workflow:") and scope.count(":") == 1:
                    name = scope[len("workflow:"):]
                    if name and name != "*":
                        new_scopes.append(f"workflow:{name}:execute")
                        changed = True
                        continue

                # Unknown scope → leave untouched (flagged for manual review)
                logger.warning(
                    "%s Unrecognised scope '%s' on token %s — leaving unchanged",
                    LOG_PREFIX, scope, token_id
                )
                new_scopes.append(scope)

            if changed:
                conn.execute(
                    text("UPDATE user_api_tokens SET scopes = :scopes WHERE id = :id"),
                    {"scopes": json.dumps(new_scopes), "id": token_id},
                )
                updated += 1

        conn.commit()
        logger.info(
            "%s PAT scope migration complete — updated %d token(s)", LOG_PREFIX, updated
        )

    except Exception as e:
        logger.warning("%s Could not migrate PAT scopes: %s", LOG_PREFIX, e)


def flatten_behavioral_guardrails_config(conn: Connection) -> None:
    """Flatten nested 'behavioral' dicts in guardrail policy configs.

    Moves keys from config->'behavioral' to top-level config keys and
    removes the nested 'behavioral' object.  Idempotent: only touches
    rows where the 'behavioral' key still exists.

    Applies to both guardrail_policies.config and
    guardrail_policy_versions.config_snapshot.
    """
    import json as _json

    def _flatten_rows(table: str, config_col: str, id_col: str) -> int:
        """Flatten behavioral in a single table.  Returns rows updated."""
        try:
            result = conn.execute(
                text(f"SELECT {id_col}, {config_col} FROM {table} WHERE {config_col} ? 'behavioral'")
            )
            rows = result.fetchall()
        except Exception:
            # Table may not exist yet
            return 0

        count = 0
        for row in rows:
            row_id = row[0]
            config = row[1]
            if not isinstance(config, dict):
                try:
                    config = _json.loads(config) if isinstance(config, str) else config
                except (TypeError, _json.JSONDecodeError):
                    continue

            behavioral = config.pop("behavioral", None)
            if not isinstance(behavioral, dict):
                continue

            # Remove deprecated keys
            for dep_key in ("detect_instruction_override", "use_local_models",
                            "local_model_threshold", "fallback_to_llm"):
                behavioral.pop(dep_key, None)

            # Merge behavioral keys to top level (existing top-level keys win)
            for k, v in behavioral.items():
                config.setdefault(k, v)

            conn.execute(
                text(f"UPDATE {table} SET {config_col} = :config WHERE {id_col} = :id"),
                {"config": _json.dumps(config), "id": row_id},
            )
            count += 1
        return count

    try:
        updated_policies = _flatten_rows("guardrail_policies", "config", "id")
        updated_versions = _flatten_rows("guardrail_policy_versions", "config_snapshot", "id")

        if updated_policies or updated_versions:
            conn.commit()
            logger.info(
                "%s Flattened behavioral config in %d policy row(s) and %d version row(s)",
                LOG_PREFIX, updated_policies, updated_versions,
            )
        else:
            logger.debug("%s No behavioral configs to flatten", LOG_PREFIX)

    except Exception as e:
        logger.warning("%s Could not flatten behavioral guardrails config: %s", LOG_PREFIX, e)


def create_workflow_assets_table(conn: Connection) -> None:
    """Create workflow_assets table for storing design-time assets.

    This table stores binary assets (e.g., custom Word templates) attached
    to workflow nodes. Assets persist across executions and graph definition
    versions, and are deleted when the parent workflow is deleted (CASCADE).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name='workflow_assets'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating workflow_assets table", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE TABLE workflow_assets (
                        id VARCHAR PRIMARY KEY,
                        workflow_id VARCHAR NOT NULL
                            REFERENCES workflows(id) ON DELETE CASCADE,
                        node_id VARCHAR(255) NOT NULL,
                        asset_type VARCHAR(50) NOT NULL,
                        filename VARCHAR(255) NOT NULL,
                        mime_type VARCHAR(100) NOT NULL,
                        file_size INTEGER NOT NULL,
                        content BYTEA NOT NULL,
                        metadata_json JSONB,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """)
            )

            logger.info("%s Creating indexes for workflow_assets", LOG_PREFIX)

            conn.execute(
                text("""
                    CREATE INDEX idx_workflow_assets_workflow_id
                    ON workflow_assets(workflow_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_workflow_assets_node_id
                    ON workflow_assets(node_id)
                """)
            )

            conn.execute(
                text("""
                    CREATE INDEX idx_workflow_assets_workflow_node
                    ON workflow_assets(workflow_id, node_id, asset_type)
                """)
            )

            conn.commit()
            logger.info("%s Created workflow_assets table successfully", LOG_PREFIX)
        else:
            logger.debug("%s workflow_assets table already exists", LOG_PREFIX)
    except Exception as e:
        logger.warning(
            "%s Could not create workflow_assets table: %s", LOG_PREFIX, e
        )


def sanitize_existing_wiki_content(conn: Connection) -> None:
    """Sanitize existing wiki page content to remove XSS vectors.

    This migration is part of the XSS mitigation effort (Observation #5).
    It sanitizes all existing wiki_pages content and wiki_revisions content
    to remove potentially dangerous HTML that was stored before server-side
    sanitization was implemented.

    The migration is idempotent - content that is already safe will not be
    modified. Content that contains XSS vectors will be cleaned.

    Args:
        conn: Database connection
    """
    try:
        # Import here to avoid circular imports
        from backend.services.wiki.sanitizer import sanitize_wiki_content

        # Check if we've already run this migration by looking for a marker
        result = conn.execute(
            text("""
                SELECT value
                FROM system_settings
                WHERE key = 'migration_wiki_xss_sanitized'
            """)
        )
        if result.fetchone():
            logger.debug("%s Wiki XSS sanitization already completed", LOG_PREFIX)
            return

        # Sanitize wiki_pages
        pages_result = conn.execute(
            text("SELECT id, content FROM wiki_pages WHERE content IS NOT NULL")
        )
        pages_updated = 0

        for row in pages_result.fetchall():
            page_id = row[0]
            original_content = row[1]

            if original_content:
                sanitized = sanitize_wiki_content(original_content)
                if sanitized != original_content:
                    conn.execute(
                        text("UPDATE wiki_pages SET content = :content WHERE id = :id"),
                        {"content": sanitized, "id": page_id},
                    )
                    pages_updated += 1

        # Sanitize wiki_revisions
        revisions_result = conn.execute(
            text("SELECT id, content FROM wiki_revisions WHERE content IS NOT NULL")
        )
        revisions_updated = 0

        for row in revisions_result.fetchall():
            revision_id = row[0]
            original_content = row[1]

            if original_content:
                sanitized = sanitize_wiki_content(original_content)
                if sanitized != original_content:
                    conn.execute(
                        text(
                            "UPDATE wiki_revisions SET content = :content WHERE id = :id"
                        ),
                        {"content": sanitized, "id": revision_id},
                    )
                    revisions_updated += 1

        # Mark migration as complete
        conn.execute(
            text("""
                INSERT INTO system_settings (key, value, created_at)
                VALUES ('migration_wiki_xss_sanitized', 'true', NOW())
                ON CONFLICT (key) DO NOTHING
            """)
        )

        conn.commit()

        if pages_updated > 0 or revisions_updated > 0:
            logger.info(
                "%s Sanitized %d wiki page(s) and %d revision(s) for XSS prevention",
                LOG_PREFIX,
                pages_updated,
                revisions_updated,
            )
        else:
            logger.debug("%s No wiki content required sanitization", LOG_PREFIX)

    except Exception as e:
        logger.warning(
            "%s Could not sanitize existing wiki content: %s", LOG_PREFIX, e
        )


def create_tool_security_policies_table(conn: Connection) -> None:
    """Create the tool_security_policies table for admin-configurable SSRF allow-lists.

    Stores admin-managed allow-list entries (exact IP/host, optionally scoped
    to a port and/or path) per tool/service, keyed by ``tool_id`` (e.g.
    ``HTTP_REQUEST``). Once a row exists for a tool, the database is the sole
    source of truth for that tool's allow-list (fail-closed if empty).

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='tool_security_policies'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating tool_security_policies table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE tool_security_policies (
                        id VARCHAR PRIMARY KEY,
                        tool_id VARCHAR NOT NULL UNIQUE,
                        allowed_ip_ranges JSON NOT NULL DEFAULT '[]',
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
            )
            conn.execute(
                text("""
                    CREATE INDEX IF NOT EXISTS ix_tool_security_policies_tool_id
                    ON tool_security_policies (tool_id)
                """)
            )
            conn.commit()
            logger.info(
                "%s Created tool_security_policies table successfully", LOG_PREFIX
            )
        else:
            logger.debug(
                "%s tool_security_policies table already exists", LOG_PREFIX
            )
    except Exception as e:
        logger.warning(
            "%s Could not create tool_security_policies table: %s", LOG_PREFIX, e
        )


def create_email_ownership_tables(conn: Connection) -> None:
    """Create email ownership tables for cross-pod authorization.

    These tables persist provider-side inbox/webhook ownership in PostgreSQL so
    authorization survives pod restarts and multi-worker or multi-pod routing.
    No data backfill is attempted: ownership for legacy in-memory resources is
    intentionally lost on first deploy and those resources remain admin-only.

    Args:
        conn: Database connection
    """
    try:
        logger.info(
            "%s Ensuring email ownership tables exist; legacy in-memory ownership "
            "cannot be backfilled and will remain admin-only",
            LOG_PREFIX,
        )

        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='email_inbox_ownership'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating email_inbox_ownership table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE email_inbox_ownership (
                        inbox_id VARCHAR PRIMARY KEY,
                        owner_id VARCHAR NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    )
                """)
            )
            logger.info("%s Created email_inbox_ownership table", LOG_PREFIX)
        else:
            logger.debug("%s email_inbox_ownership table already exists", LOG_PREFIX)
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_email_inbox_ownership_owner_id
                ON email_inbox_ownership(owner_id)
            """)
        )
        conn.commit()

        result = conn.execute(
            text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_name='email_webhook_ownership'
            """)
        )

        if not result.fetchone():
            logger.info("%s Creating email_webhook_ownership table", LOG_PREFIX)
            conn.execute(
                text("""
                    CREATE TABLE email_webhook_ownership (
                        webhook_id VARCHAR PRIMARY KEY,
                        owner_id VARCHAR NOT NULL,
                        inbox_id VARCHAR,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    )
                """)
            )
            logger.info("%s Created email_webhook_ownership table", LOG_PREFIX)
        else:
            logger.debug("%s email_webhook_ownership table already exists", LOG_PREFIX)
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_email_webhook_ownership_owner_id
                ON email_webhook_ownership(owner_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_email_webhook_ownership_inbox_id
                ON email_webhook_ownership(inbox_id)
            """)
        )
        conn.commit()
    except Exception as e:
        logger.warning("%s Could not create email ownership tables: %s", LOG_PREFIX, e)


def add_fixed_ips_column_to_tool_security_policies(conn: Connection) -> None:
    """Add the informational ``fixed_ips`` column to ``tool_security_policies``.

    ``fixed_ips`` lists the subset of ``blocked_ip_ranges`` that came from the
    ``<TOOL_ID>_ALLOWED_IPS`` env var. It exists purely so the frontend can
    render those entries as non-removable; it is never read by SSRF
    validation and does not change request matching/blocking behavior.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='tool_security_policies' AND column_name='fixed_ips'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding fixed_ips column to tool_security_policies", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE tool_security_policies
                    ADD COLUMN fixed_ips JSON NOT NULL DEFAULT '[]'
                """)
            )
            conn.commit()
            logger.info(
                "%s Added fixed_ips column to tool_security_policies successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s fixed_ips column already exists on tool_security_policies",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add fixed_ips column to tool_security_policies: %s",
            LOG_PREFIX,
            e,
        )


def rename_blocked_ip_ranges_to_allowed_ip_ranges(conn: Connection) -> None:
    """Rename ``tool_security_policies.blocked_ip_ranges`` to ``allowed_ip_ranges``.

    The column already holds allow-list entries (not blocked CIDR ranges)
    since the block-list -> allow-list SSRF policy change; this rename makes
    the column name match its actual meaning. No data is lost - this is a
    plain column rename, values are preserved as-is.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='tool_security_policies' AND column_name='blocked_ip_ranges'
            """)
        )
        if result.fetchone():
            logger.info(
                "%s Renaming tool_security_policies.blocked_ip_ranges -> allowed_ip_ranges",
                LOG_PREFIX,
            )
            conn.execute(
                text("""
                    ALTER TABLE tool_security_policies
                    RENAME COLUMN blocked_ip_ranges TO allowed_ip_ranges
                """)
            )
            conn.commit()
            logger.info(
                "%s Renamed tool_security_policies.blocked_ip_ranges successfully",
                LOG_PREFIX,
            )
        else:
            logger.debug(
                "%s tool_security_policies.blocked_ip_ranges already renamed "
                "(or table not yet created)",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not rename blocked_ip_ranges to allowed_ip_ranges: %s",
            LOG_PREFIX,
            e,
        )


def seed_tool_security_policies_defaults(conn: Connection) -> None:
    """Seed tool_security_policies from each tool's ``<TOOL_ID>_ALLOWED_IPS`` env var.

    Runs once per tool id: if no row exists yet (e.g. for ``HTTP_REQUEST`` or
    ``MCP_SERVER``), inserts one populated from the corresponding
    ``<TOOL_ID>_ALLOWED_IPS`` environment variable (comma-separated allow-list
    entries), or an empty list if that env var is unset/blank - i.e.
    fail-closed, nothing is allowed until an admin adds entries. This makes
    the database the single source of truth going forward; admins can then
    freely add or remove entries via the admin API, independently per tool.

    Note: ``ssrf_policy_service.get_effective_blocked_ranges()`` performs the
    same seed-on-first-access at runtime, so this startup migration is a
    best-effort optimization, not a hard dependency.

    Args:
        conn: Database connection
    """
    import json
    import os
    import uuid

    for tool_id in ("HTTP_REQUEST", "MCP_SERVER"):
        try:
            result = conn.execute(
                text("""
                    SELECT 1 FROM tool_security_policies WHERE tool_id = :tool_id
                """),
                {"tool_id": tool_id},
            )
            if result.fetchone():
                logger.debug(
                    "%s %s tool_security_policies row already exists",
                    LOG_PREFIX,
                    tool_id,
                )
                continue

            raw_env = os.getenv(f"{tool_id}_ALLOWED_IPS", "")
            seed_entries = [entry.strip() for entry in raw_env.split(",") if entry.strip()]

            logger.info(
                "%s Seeding tool_security_policies for %s from %s_ALLOWED_IPS "
                "(%d entries)",
                LOG_PREFIX,
                tool_id,
                tool_id,
                len(seed_entries),
            )
            conn.execute(
                text("""
                    INSERT INTO tool_security_policies
                        (id, tool_id, allowed_ip_ranges, fixed_ips, enabled, created_at, updated_at)
                    VALUES
                        (:id, :tool_id, :ranges, :fixed_ips, TRUE, NOW(), NOW())
                    ON CONFLICT (tool_id) DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tool_id": tool_id,
                    "ranges": json.dumps(seed_entries),
                    "fixed_ips": json.dumps(seed_entries),
                },
            )
            conn.commit()
            logger.info(
                "%s Seeded tool_security_policies %s successfully",
                LOG_PREFIX,
                tool_id,
            )
        except Exception as e:
            logger.warning(
                "%s Could not seed tool_security_policies defaults for %s: %s",
                LOG_PREFIX,
                tool_id,
                e,
            )

# The old hardcoded CIDR blocklist defaults that were seeded into
# tool_security_policies rows before the switch from block-list (CIDR ranges)
# to allow-list (exact host[:port][/path]) semantics. Any row whose contents
# still exactly match this set was never customized by an admin - it's just
# leftover legacy default data - so it's safe to auto-replace on startup.
_LEGACY_DEFAULT_CIDR_BLOCKLIST = frozenset(
    {
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "0.0.0.0/8",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    }
)


def migrate_legacy_cidr_ssrf_policies(conn: Connection) -> None:
    """Auto-replace legacy CIDR blocklist rows with the new allow-list format.

    Prior to the block-list -> allow-list SSRF policy change, every tool row
    was seeded with a fixed set of "blocked" CIDR ranges
    (``_LEGACY_DEFAULT_CIDR_BLOCKLIST``). Those entries are meaningless under
    the new allow-list semantics (CIDR ranges are no longer supported) and,
    left in place, would make ``blocked_ip_ranges`` look "populated" even
    though every request should currently fail closed.

    For each known tool id, if the existing row's entries are exactly the
    legacy default set (i.e. an admin never customized it), this replaces the
    row's contents with a fresh seed from ``<TOOL_ID>_ALLOWED_IPS``. Rows that
    have been customized (any entry outside the legacy default set) are left
    untouched, so this can never silently overwrite deliberate admin
    configuration - only the untouched leftover defaults.

    This runs automatically on app startup; no admin/API action is required.

    Args:
        conn: Database connection
    """
    import json
    import os

    for tool_id in ("HTTP_REQUEST", "MCP_SERVER"):
        try:
            result = conn.execute(
                text("""
                    SELECT allowed_ip_ranges FROM tool_security_policies
                    WHERE tool_id = :tool_id
                """),
                {"tool_id": tool_id},
            )
            row = result.fetchone()
            if row is None:
                continue

            current_entries = row[0] or []
            if not current_entries:
                # Already empty (already migrated, or genuinely never
                # populated) - nothing legacy to replace.
                continue
            if not set(current_entries).issubset(_LEGACY_DEFAULT_CIDR_BLOCKLIST):
                # Contains at least one entry that isn't one of the known
                # legacy CIDR defaults - an admin has added/customized real
                # allow-list entries. Leave it alone.
                continue
            # Every entry present is one of the old hardcoded CIDR defaults
            # (a full or partial subset - some historical rows were seeded
            # without every range, e.g. missing 127.0.0.0/8). None of these
            # were ever a deliberate admin allow-list entry, so it's safe to
            # replace with the env-seeded allow-list.

            raw_env = os.getenv(f"{tool_id}_ALLOWED_IPS", "")
            new_entries = [entry.strip() for entry in raw_env.split(",") if entry.strip()]

            logger.info(
                "%s Migrating legacy CIDR blocklist for %s -> allow-list "
                "(%d entries from %s_ALLOWED_IPS)",
                LOG_PREFIX,
                tool_id,
                len(new_entries),
                tool_id,
            )
            conn.execute(
                text("""
                    UPDATE tool_security_policies
                    SET allowed_ip_ranges = :ranges, fixed_ips = :fixed_ips, updated_at = NOW()
                    WHERE tool_id = :tool_id
                """),
                {
                    "ranges": json.dumps(new_entries),
                    "fixed_ips": json.dumps(new_entries),
                    "tool_id": tool_id,
                },
            )
            conn.commit()
            logger.info(
                "%s Migrated %s to allow-list format successfully",
                LOG_PREFIX,
                tool_id,
            )
        except Exception as e:
            logger.warning(
                "%s Could not migrate legacy CIDR blocklist for %s: %s",
                LOG_PREFIX,
                tool_id,
                e,
            )


def sync_fixed_ips_from_env(conn: Connection) -> None:
    """Re-sync ``fixed_ips`` from ``<TOOL_ID>_ALLOWED_IPS`` on every startup.

    Unlike the seed/legacy migrations above (which only act once, when no
    row exists yet or it's still legacy CIDR data), this runs every time the
    app starts: it removes the previously env-seeded entries (the old
    ``fixed_ips``) from ``allowed_ip_ranges`` and inserts the current env
    entries in their place, then updates ``fixed_ips`` to match. Any entry
    in ``allowed_ip_ranges`` that was never part of ``fixed_ips`` (i.e.
    added manually by an admin) is left untouched.

    Args:
        conn: Database connection
    """
    import json
    import os

    for tool_id in ("HTTP_REQUEST", "MCP_SERVER"):
        try:
            result = conn.execute(
                text("""
                    SELECT allowed_ip_ranges, fixed_ips FROM tool_security_policies
                    WHERE tool_id = :tool_id
                """),
                {"tool_id": tool_id},
            )
            row = result.fetchone()
            if row is None:
                continue

            current_allowed = row[0] or []
            old_fixed = row[1] or []

            raw_env = os.getenv(f"{tool_id}_ALLOWED_IPS", "")
            new_fixed = [entry.strip() for entry in raw_env.split(",") if entry.strip()]

            remaining = [e for e in current_allowed if e not in old_fixed]
            updated_allowed = remaining + [e for e in new_fixed if e not in remaining]

            if set(updated_allowed) == set(current_allowed) and set(new_fixed) == set(old_fixed):
                continue

            logger.info(
                "%s Syncing fixed_ips for %s from %s_ALLOWED_IPS (%d entries)",
                LOG_PREFIX,
                tool_id,
                tool_id,
                len(new_fixed),
            )
            conn.execute(
                text("""
                    UPDATE tool_security_policies
                    SET allowed_ip_ranges = :allowed, fixed_ips = :fixed_ips, updated_at = NOW()
                    WHERE tool_id = :tool_id
                """),
                {
                    "allowed": json.dumps(updated_allowed),
                    "fixed_ips": json.dumps(new_fixed),
                    "tool_id": tool_id,
                },
            )
            conn.commit()
        except Exception as e:
            logger.warning(
                "%s Could not sync fixed_ips from env for %s: %s",
                LOG_PREFIX,
                tool_id,
                e,
            )


def add_groundedness_columns_to_chat_response_scores(conn: Connection) -> None:
    """Add groundedness_score and groundedness_raw columns to chat_response_scores.

    Args:
        conn: Database connection
    """
    try:
        result = conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='chat_response_scores' AND column_name='groundedness_score'
            """)
        )
        if not result.fetchone():
            logger.info(
                "%s Adding groundedness columns to chat_response_scores", LOG_PREFIX
            )
            conn.execute(
                text("""
                    ALTER TABLE chat_response_scores
                    ADD COLUMN groundedness_score FLOAT,
                    ADD COLUMN groundedness_raw JSON
                """)
            )
            conn.commit()
            logger.info("%s Added groundedness columns successfully", LOG_PREFIX)
        else:
            logger.debug(
                "%s groundedness columns already exist on chat_response_scores",
                LOG_PREFIX,
            )
    except Exception as e:
        logger.warning(
            "%s Could not add groundedness columns to chat_response_scores: %s",
            LOG_PREFIX,
            e,
        )

