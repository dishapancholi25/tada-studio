"""File write configuration for AI agent tools.

This module defines the configuration for file write tools that AI agents
can invoke to create files in a sandboxed workspace directory.
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
from typing import List, Optional


@dataclass
class FileWriteConfig:
    """Configuration for file write tool nodes.

    Allows AI agents to write files to a sandboxed output directory
    with configurable constraints on file types and sizes.

    Attributes:
        output_directory: Sandboxed directory path for file outputs
            (relative to workspace, e.g., "outputs/")
        allowed_extensions: List of permitted file extensions
            Note: .pdf/.docx/.xlsx/.pptx are generated from markdown/structured content
        max_file_size_mb: Maximum file size in megabytes
        create_directories: Whether to create subdirectories within output_directory
        parent_agent_id: ID of the parent agent (set by connection manager)
        default_template: Default template for styled document generation
            ('modern', 'executive', 'report', 'invoice', 'minimal')
    """

    output_directory: str = "outputs"
    allowed_extensions: List[str] = field(
        default_factory=lambda: [
            ".txt",
            ".md",
            ".json",
            ".csv",
            ".yaml",
            ".yml",
            ".pdf",
            ".docx",
            ".xlsx",
            ".pptx",
        ]
    )
    max_file_size_mb: int = 1024
    create_directories: bool = True
    parent_agent_id: Optional[str] = None
    default_template: Optional[str] = None
    custom_template_asset_id: Optional[str] = None
    custom_template_variables: Optional[List[str]] = None
    custom_template_filename: Optional[str] = None
    guardrails_config: Optional["GuardrailsConfig"] = None
