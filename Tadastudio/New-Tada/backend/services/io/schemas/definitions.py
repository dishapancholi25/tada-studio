"""Output schema definitions for all node types.

Each schema declares the fields available in the `fields` dict of a node's
NodeOutput. These are derived from the actual return values in each executor.
"""

from .registry import FieldType, NodeOutputSchema, OutputField, register_output_schema

# ---------------------------------------------------------------------------
# AGENT node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="AGENT",
        description="LLM agent that processes input and generates a response",
        fields=[
            OutputField(
                name="response",
                type=FieldType.STRING,
                description="The agent's text response",
            ),
        ],
        raw_description="The agent's text response",
        supports_dynamic_schema=True,
        raw_is_redundant=True,
    )
)

# ---------------------------------------------------------------------------
# HTTP_REQUEST_ACTION node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="HTTP_REQUEST_ACTION",
        description="Makes an HTTP request and returns the response",
        fields=[
            OutputField(
                name="success",
                type=FieldType.BOOLEAN,
                description="Whether the request completed successfully",
            ),
            OutputField(
                name="status_code",
                type=FieldType.INTEGER,
                description="HTTP response status code",
            ),
            OutputField(
                name="data",
                type=FieldType.ANY,
                description="Response body (parsed JSON or raw text)",
                nullable=True,
            ),
        ],
        raw_description="JSON string of the response data",
    )
)

# Alias: HTTP_REQUEST uses the same executor
register_output_schema(
    NodeOutputSchema(
        node_type="HTTP_REQUEST",
        description="Makes an HTTP request and returns the response",
        fields=[
            OutputField(
                name="success",
                type=FieldType.BOOLEAN,
                description="Whether the request completed successfully",
            ),
            OutputField(
                name="status_code",
                type=FieldType.INTEGER,
                description="HTTP response status code",
            ),
            OutputField(
                name="data",
                type=FieldType.ANY,
                description="Response body (parsed JSON or raw text)",
                nullable=True,
            ),
        ],
        raw_description="JSON string of the response data",
    )
)

# ---------------------------------------------------------------------------
# EMAIL_SEND node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="EMAIL_SEND",
        description="Sends an email and returns delivery status",
        fields=[
            OutputField(
                name="message_id",
                type=FieldType.STRING,
                description="Unique message identifier from the provider",
            ),
            OutputField(
                name="to",
                type=FieldType.STRING,
                description="Recipient email address",
            ),
            OutputField(
                name="subject",
                type=FieldType.STRING,
                description="Email subject line",
            ),
            OutputField(
                name="status",
                type=FieldType.STRING,
                description="Delivery status (sent, queued, failed)",
            ),
            OutputField(
                name="provider_response",
                type=FieldType.OBJECT,
                description="Raw response from email provider",
                nullable=True,
            ),
        ],
        raw_description="Confirmation message with recipient address",
    )
)

# Alias: EMAIL_SEND_TOOL uses the same executor
register_output_schema(
    NodeOutputSchema(
        node_type="EMAIL_SEND_TOOL",
        description="Sends an email and returns delivery status",
        fields=[
            OutputField(
                name="message_id",
                type=FieldType.STRING,
                description="Unique message identifier from the provider",
            ),
            OutputField(
                name="to",
                type=FieldType.STRING,
                description="Recipient email address",
            ),
            OutputField(
                name="subject",
                type=FieldType.STRING,
                description="Email subject line",
            ),
            OutputField(
                name="status",
                type=FieldType.STRING,
                description="Delivery status (sent, queued, failed)",
            ),
            OutputField(
                name="provider_response",
                type=FieldType.OBJECT,
                description="Raw response from email provider",
                nullable=True,
            ),
        ],
        raw_description="Confirmation message with recipient address",
    )
)

# ---------------------------------------------------------------------------
# FILE_READ node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="FILE_READ",
        description="Reads content from a file",
        fields=[
            OutputField(
                name="content",
                type=FieldType.STRING,
                description="The extracted text content of the file",
            ),
            OutputField(
                name="metadata",
                type=FieldType.OBJECT,
                description="File metadata",
                children=[
                    OutputField(
                        name="filename",
                        type=FieldType.STRING,
                        description="Original filename",
                    ),
                    OutputField(
                        name="file_size_mb",
                        type=FieldType.FLOAT,
                        description="File size in megabytes",
                    ),
                    OutputField(
                        name="file_type",
                        type=FieldType.STRING,
                        description="File extension",
                    ),
                    OutputField(
                        name="extraction_method",
                        type=FieldType.STRING,
                        description="Method used to extract content",
                    ),
                    OutputField(
                        name="total_tokens",
                        type=FieldType.INTEGER,
                        description="Estimated token count",
                    ),
                ],
            ),
            OutputField(
                name="extraction_method",
                type=FieldType.STRING,
                description="Method used to extract content (direct, ocr, pdf_parse)",
            ),
            OutputField(
                name="columns",
                type=FieldType.OBJECT,
                description="CSV only. Each key is a column header, value is a list of all values in that column. e.g. columns.status returns ['active', 'inactive', ...]",
            ),
            OutputField(
                name="rows",
                type=FieldType.ARRAY,
                description="CSV only. List of row dicts. Use rows.0.column_name for a single value. e.g. rows.0.status returns 'active'",
                items_type=FieldType.OBJECT,
            ),
            OutputField(
                name="column_names",
                type=FieldType.ARRAY,
                description="CSV only. List of column header strings. e.g. ['name', 'status', 'email']",
                items_type=FieldType.STRING,
            ),
        ],
        raw_description="The extracted text content of the file",
    )
)

# ---------------------------------------------------------------------------
# DATABASE_QUERY node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="DATABASE_QUERY",
        description="Executes a database query and returns results",
        fields=[
            OutputField(
                name="success",
                type=FieldType.BOOLEAN,
                description="Whether the query executed successfully",
            ),
            OutputField(
                name="data",
                type=FieldType.ARRAY,
                description="Query result rows",
                items_type=FieldType.OBJECT,
            ),
        ],
        raw_description="JSON string of query results",
    )
)

# ---------------------------------------------------------------------------
# DATABASE_INSERT node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="DATABASE_INSERT",
        description="Inserts data into a database table",
        fields=[
            OutputField(
                name="success",
                type=FieldType.BOOLEAN,
                description="Whether the insert succeeded",
            ),
            OutputField(
                name="rows_inserted",
                type=FieldType.INTEGER,
                description="Number of rows inserted",
            ),
            OutputField(
                name="data",
                type=FieldType.ARRAY,
                description="Inserted row data (if return_inserted_rows enabled)",
                items_type=FieldType.OBJECT,
                nullable=True,
            ),
        ],
        raw_description="JSON string of insert result",
    )
)

# ---------------------------------------------------------------------------
# DOCUMENT_SEARCH node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="DOCUMENT_SEARCH",
        description="Performs vector similarity search over documents",
        fields=[
            OutputField(
                name="results",
                type=FieldType.ARRAY,
                description="Matching document chunks with scores",
                items_type=FieldType.OBJECT,
            ),
            OutputField(
                name="query",
                type=FieldType.STRING,
                description="The search query used",
            ),
        ],
        raw_description="Formatted search results as text",
    )
)

# ---------------------------------------------------------------------------
# WEB_SEARCH node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="WEB_SEARCH",
        description="Searches the web and returns results",
        fields=[
            OutputField(
                name="results",
                type=FieldType.ARRAY,
                description="Search result entries",
                items_type=FieldType.OBJECT,
            ),
            OutputField(
                name="query",
                type=FieldType.STRING,
                description="The search query used",
            ),
        ],
        raw_description="Formatted search results as text",
    )
)

# ---------------------------------------------------------------------------
# FILE_WRITE node
# ---------------------------------------------------------------------------
register_output_schema(
    NodeOutputSchema(
        node_type="FILE_WRITE",
        description="Writes content to a file",
        fields=[
            OutputField(
                name="success",
                type=FieldType.BOOLEAN,
                description="Whether the write succeeded",
            ),
            OutputField(
                name="file_path",
                type=FieldType.STRING,
                description="Path of the written file",
            ),
        ],
        raw_description="Confirmation message with file path",
    )
)
