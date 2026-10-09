"""
File Node Executor.

This module handles execution of FILE_READ nodes, including:
- File validation (size, type, permissions)
- Multiple input formats (path, base64, content)
- OCR processing via AI model for PDFs, images, documents
- Direct text extraction for simple text files
- Database tracking and WebSocket notifications
"""

import asyncio
import base64
import os
import tempfile
import time
from typing import Any, Dict, Optional, Union

from langchain_core.messages import HumanMessage
from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState
from backend.services.model_deployment import ModelDeploymentService

from ..base import BaseNodeExecutor
from ..handlers import NodeDatabaseTracker, NodeNotificationHandler


file_executor_logger = get_logger("nodes.executors.file")


class FileNodeExecutor(BaseNodeExecutor):
    """
    Executor for FILE_READ nodes.

    Handles file reading with comprehensive features including:
    - Multiple input formats (path, base64, content)
    - File validation (size, extension, existence)
    - OCR processing for PDFs, images, documents
    - Direct text extraction for plain text files
    - Chunking support for large documents
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """Initialize file node executor."""
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
        Execute a file read node.

        Args:
            node: The file read node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            State updates with file content or error if disabled
        """
        file_executor_logger.info(f"Executing FILE_READ node: {node.name}")
        execution_start_time = time.time()

        # Create tracking record
        node_exec_id = await self._create_tracking_record(node, state)

        # TEMPORARILY DISABLED: due to ISG security audit
        # Will be re-enabled after fixes are implemented
        try:
            # FILE_READ is temporarily disabled
            error_message = (
                "File Read feature is temporarily unavailable due to security updates "
                "reported by ISG team. This feature will be re-enabled after security fixes are implemented."
            )
            file_executor_logger.warning(f"FILE_READ node execution blocked: {error_message}")

            node_output = {
                "raw": error_message,
                "structured": {
                    "success": False,
                    "error": error_message,
                    "error_type": "feature_disabled",
                },
                "fields": {},
            }

            # Complete tracking
            execution_duration = time.time() - execution_start_time
            await self._complete_tracking(
                node, state, node_exec_id, node_output, execution_duration
            )

            # Return state update with error
            return self._build_state_update(node, node_output, state)

        except Exception as e:
            file_executor_logger.error(
                f"FILE_READ node error for {node.name}: {e}", exc_info=True
            )
            return await self._handle_error(node, state, node_exec_id, str(e))

        finally:
            # Clean up temp file if created
            if temp_file_path:
                try:
                    os.unlink(temp_file_path)
                except (OSError, FileNotFoundError):
                    pass

    def _validate_config(self, node: EnhancedNodeData) -> Union[Dict, Any]:
        """
        Validate file read configuration exists.

        Args:
            node: The file read node

        Returns:
            File read configuration object

        Raises:
            ValueError: If configuration is missing
        """
        config = node.file_read_config
        if not config:
            raise ValueError("File read configuration is missing")
        return config

    def _parse_config(self, config: Union[Dict, Any]) -> "FileReadConfig":
        """
        Parse configuration from dict or dataclass into standard format.

        Args:
            config: Configuration as dict or dataclass

        Returns:
            FileReadConfig with normalized values
        """
        # Create a helper function to get values from either dict or dataclass
        if isinstance(config, dict):

            def get_value(key, default=None):
                return config.get(key, default)
        else:

            def get_value(key, default=None):
                return getattr(config, key, default)

        return FileReadConfig(
            max_file_size_mb=get_value("max_file_size_mb", 10),
            allowed_extensions=get_value(
                "allowed_extensions",
                [
                    ".pdf",
                    ".txt",
                    ".docx",
                    ".xlsx",
                    ".csv",
                    ".tsv",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".html",
                    ".md",
                ],
            ),
            extraction_mode=get_value("extraction_mode", "model_ocr"),
            output_format=get_value("output_format", "markdown"),
            ocr_prompt=get_value("ocr_prompt"),
            doc_type=get_value("doc_type", "auto"),
            max_pages=get_value("max_pages"),
            chunk_by_page=get_value("chunk_by_page", False),
            max_tokens_per_request=get_value("max_tokens_per_request", 4000),
            skip_on_error=get_value("skip_on_error", False),
            model_deployment_id=get_value("model_deployment_id"),
            llm_safe_output=get_value("llm_safe_output", False),
            # CSV-specific configuration
            csv_delimiter=get_value("csv_delimiter", "auto"),
            csv_has_header=get_value("csv_has_header", "auto"),
            csv_output_format=get_value("csv_output_format", "markdown"),
            csv_max_rows=get_value("csv_max_rows"),
            csv_chunk_size=get_value("csv_chunk_size", 50),
            csv_include_schema=get_value("csv_include_schema", True),
            csv_include_stats=get_value("csv_include_stats", True),
            csv_encoding=get_value("csv_encoding", "auto"),
        )

    def _resolve_file_path(self, file_info: Union[str, Dict]) -> tuple:
        """
        Resolve file path from various input formats.

        Args:
            file_info: File information (path string, or dict with path/base64/content)

        Returns:
            Tuple of (file_path, temp_file_path)
            temp_file_path is None if no temp file was created

        Raises:
            ValueError: If file info format is invalid
        """
        if isinstance(file_info, str):
            # Direct file path
            return file_info, None

        elif isinstance(file_info, dict):
            # Check for path with actual value (not None)
            if file_info.get("path"):
                return file_info["path"], None

            elif "base64" in file_info:
                # Create temp file from base64
                file_data = base64.b64decode(file_info["base64"])
                file_ext = file_info.get("extension", ".tmp")
                temp_file = tempfile.NamedTemporaryFile(suffix=file_ext, delete=False)
                temp_file.write(file_data)
                temp_file.close()
                return temp_file.name, temp_file.name

            elif "content" in file_info:
                # Direct content - create temp text file
                file_ext = file_info.get("extension", ".txt")
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=file_ext, delete=False
                )
                temp_file.write(file_info["content"])
                temp_file.close()
                return temp_file.name, temp_file.name

            else:
                raise ValueError(
                    "File info must contain 'path', 'base64', or 'content'"
                )

        else:
            raise ValueError(f"Invalid file info type: {type(file_info)}")

    def _validate_file(self, file_path: str, config: "FileReadConfig") -> None:
        """
        Validate file exists, size, and extension.

        Args:
            file_path: Path to file
            config: File read configuration

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file size or extension is invalid
        """
        # Check file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > config.max_file_size_mb:
            raise ValueError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum ({config.max_file_size_mb} MB)"
            )

        # Check file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in config.allowed_extensions:
            raise ValueError(
                f"File type {file_ext} not allowed. Allowed types: {config.allowed_extensions}"
            )

    async def _extract_file_content(
        self, file_path: str, config: "FileReadConfig"
    ) -> Dict[str, Any]:
        """
        Extract content from file using appropriate method.

        Args:
            file_path: Path to file
            config: File read configuration

        Returns:
            Dictionary with extraction results
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        # Handle raw mode - pass file content as-is without any processing
        # Used for sending files directly to MCP servers or external tools
        if config.extraction_mode == "raw":
            return self._extract_raw_content(file_path, file_ext)

        # Handle CSV files with dedicated processor
        if file_ext in [".csv", ".tsv"]:
            return await self._extract_csv_content(file_path, config)

        # Handle text-only mode for simple text files
        if config.extraction_mode == "text_only" and file_ext in [".txt", ".md"]:
            return self._extract_direct_text(file_path)

        # Use AI model OCR service for other files
        return await self._extract_with_ocr(file_path, file_ext, config)

    def _extract_direct_text(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text directly from text file.

        Args:
            file_path: Path to text file

        Returns:
            Dictionary with text content and metadata
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
            return {
                "success": True,
                "text": text_content,
                "extraction_method": "direct_text",
                "total_tokens": 0,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "extraction_method": "direct_text",
            }

    def _extract_raw_content(self, file_path: str, file_ext: str) -> Dict[str, Any]:
        """
        Extract raw file content without any processing.

        Used for passing files directly to MCP servers or external tools.
        Returns text content for text files, base64 for binary files.

        Args:
            file_path: Path to file
            file_ext: File extension

        Returns:
            Dictionary with raw content and metadata
        """
        text_extensions = [".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".xml", ".html"]

        try:
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)

            if file_ext in text_extensions:
                # Read as text for text files
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return {
                    "success": True,
                    "text": content,
                    "raw_content": content,
                    "content_type": "text",
                    "extraction_method": "raw",
                    "total_tokens": 0,
                    "metadata": {
                        "filename": filename,
                        "file_size": file_size,
                        "file_extension": file_ext,
                    },
                }
            else:
                # Read as binary and encode to base64 for binary files
                with open(file_path, "rb") as f:
                    binary_content = f.read()
                base64_content = base64.b64encode(binary_content).decode("utf-8")
                return {
                    "success": True,
                    "text": f"[Binary file: {filename}, size: {file_size} bytes, base64 encoded]",
                    "raw_content": base64_content,
                    "content_type": "base64",
                    "extraction_method": "raw",
                    "total_tokens": 0,
                    "metadata": {
                        "filename": filename,
                        "file_size": file_size,
                        "file_extension": file_ext,
                    },
                }
        except Exception as e:
            file_executor_logger.error(f"Error reading raw file content: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "extraction_method": "raw",
            }

    async def _extract_csv_content(
        self, file_path: str, config: "FileReadConfig"
    ) -> Dict[str, Any]:
        """
        Extract and format CSV content for LLM consumption.

        Args:
            file_path: Path to CSV file
            config: File read configuration

        Returns:
            Dictionary with formatted CSV content and metadata
        """
        from backend.services.ocr import GPT4oOCRService

        file_executor_logger.info(
            f"Processing CSV file with dedicated processor: {file_path}"
        )

        # Initialize OCR service (CSV processor doesn't need AI, but uses same service)
        ocr_service = GPT4oOCRService()

        # Use csv_output_format if set, otherwise fall back to general output_format
        csv_format = getattr(config, "csv_output_format", None)
        if not csv_format or csv_format == "markdown":
            # Check if a general output_format was specified (e.g., "raw")
            general_format = getattr(config, "output_format", None)
            if general_format in ("raw", "json"):
                csv_format = general_format
            else:
                csv_format = csv_format or "markdown"

        return ocr_service.process_csv(
            csv_path=file_path,
            delimiter=getattr(config, "csv_delimiter", "auto"),
            has_header=getattr(config, "csv_has_header", "auto"),
            output_format=csv_format,
            max_rows=getattr(config, "csv_max_rows", None),
            chunk_size=getattr(config, "csv_chunk_size", 50),
            include_schema=getattr(config, "csv_include_schema", True),
            include_stats=getattr(config, "csv_include_stats", True),
            encoding=getattr(config, "csv_encoding", "auto"),
        )

    async def _extract_with_ocr(
        self, file_path: str, file_ext: str, config: "FileReadConfig"
    ) -> Dict[str, Any]:
        """
        Extract content using the configured document extraction service.

        Routes to Tika, Azure Document Intelligence, or AI model OCR
        depending on the DOCUMENT_EXTRACTION_PROVIDER environment variable.

        Args:
            file_path: Path to file
            file_ext: File extension
            config: File read configuration

        Returns:
            Dictionary with extraction results
        """
        from backend.services.document_extraction import (
            DocumentExtractionFactory,
            get_extraction_provider,
        )
        from backend.services.ocr import GPT4oOCRService

        provider = get_extraction_provider()
        file_executor_logger.info(
            f"Processing file with extraction provider '{provider}': {file_path}"
        )

        # Delegate to Tika or Azure DI via the factory when not using model OCR.
        # Run in a thread pool to avoid blocking the async event loop during
        # the network call to Azure DI / Tika (can take 10–30 s for large docs).
        if provider != "model_ocr":
            factory = DocumentExtractionFactory(provider=provider)
            result = await asyncio.to_thread(factory.extract_file, file_path)
            if result.get("success"):
                return result
            # Fall back to model OCR on failure if fallback is enabled
            file_executor_logger.warning(
                f"[FILE_READ] {provider} extraction failed, falling back to model OCR: "
                f"{result.get('error')}"
            )

        # Build model config from per-node model_deployment_id (no env var fallback)
        model_config = None
        model_deployment_id = getattr(config, "model_deployment_id", None)
        if not model_deployment_id:
            raise ValueError(
                "No model deployment configured for OCR extraction. "
                "Please select a model in the File Read node's OCR settings."
            )
        file_executor_logger.info(
            f"[OCR-DEBUG] model_deployment_id from config: {model_deployment_id}, "
            f"config type: {type(config).__name__}"
        )
        if model_deployment_id:
            try:
                model_service = ModelDeploymentService()
                deployment = model_service.get_deployment(
                    model_deployment_id, include_credentials=True
                )

                if not deployment:
                    file_executor_logger.warning(
                        f"Model deployment {model_deployment_id} not found, "
                        f"falling back to environment config"
                    )
                else:
                    # Build model config from deployment (deployment is a dict)
                    provider = deployment.get("provider", "")
                    settings = deployment.get("settings", {}) or {}
                    credentials = deployment.get("credentials", {}) or {}

                    # Normalize provider for OCR service. Keep
                    # ``azure_openai_ptu`` distinct so the OCR client can pick
                    # the OAuth/gateway auth path; collapse plain
                    # ``azure_openai`` variants to ``azure`` for backward
                    # compatibility with the existing OCR client init.
                    provider_lower = provider.lower()
                    if provider_lower == "azure_openai_ptu":
                        normalized_provider = "azure_openai_ptu"
                    elif "azure" in provider_lower:
                        normalized_provider = "azure"
                    else:
                        normalized_provider = provider

                    model_config = {
                        "provider": normalized_provider,
                        "model_name": settings.get("deployment_name")
                        or deployment.get("model_name"),
                        "api_key": None,  # Will be set below
                    }

                    # Add provider-specific settings
                    if "azure" in provider_lower:
                        model_config["endpoint"] = (
                            settings.get("endpoint")
                            or settings.get("azure_endpoint")
                            or settings.get("base_url")
                        )
                        model_config["api_version"] = settings.get(
                            "api_version", "2024-02-01"
                        )
                        model_config["use_managed_identity"] = settings.get(
                            "use_managed_identity", False
                        )
                        model_config["managed_identity_client_id"] = settings.get(
                            "managed_identity_client_id"
                        )
                    else:
                        model_config["base_url"] = settings.get("base_url")

                    # Get credentials
                    if credentials:
                        model_config["api_key"] = credentials.get("api_key")

                    # Propagate PTU/gateway-specific settings and credentials
                    # so ``GPT4oOCRService`` can build an OAuth-authenticated
                    # client with the required gateway headers.
                    if normalized_provider == "azure_openai_ptu":
                        model_config["token_url"] = (
                            settings.get("token_url")
                            or credentials.get("token_url")
                        )
                        model_config["client_id"] = (
                            settings.get("client_id")
                            or credentials.get("client_id")
                        )
                        model_config["client_secret"] = credentials.get(
                            "client_secret"
                        )
                        model_config["oauth_scope"] = (
                            settings.get("oauth_scope")
                            or settings.get("scope")
                            or "CORP"
                        )
                        model_config["grant_type"] = (
                            settings.get("grant_type") or "client_credentials"
                        )
                        model_config["x_user_id"] = (
                            settings.get("x_user_id") or "TADAUSER"
                        )
                        model_config["verify_ssl"] = bool(
                            settings.get("verify_ssl", False)
                        )

                    file_executor_logger.info(
                        f"Using model deployment: {deployment.get('display_name') or deployment.get('name')} "
                        f"(provider: {provider} -> {normalized_provider}, model: {deployment.get('model_name')}, "
                        f"endpoint: {model_config.get('endpoint') or model_config.get('base_url')})"
                    )
            except Exception as e:
                file_executor_logger.error(
                    f"Failed to load model deployment {model_deployment_id}: {e}. "
                    f"Falling back to environment config"
                )
                model_config = None

        # Initialize AI model OCR service with model config or fallback to env vars
        file_executor_logger.info(f"Processing file with AI model OCR: {file_path}")
        # Read ocr_detail from DB so admin changes apply immediately (no restart needed)
        from backend.services.document_extraction.factory import _read_db_setting

        ocr_detail = _read_db_setting(
            "DOCUMENT_EXTRACTION_MODEL_OCR_DETAIL",
            os.getenv("DOCUMENT_EXTRACTION_MODEL_OCR_DETAIL", "high"),
        )
        ocr_service = GPT4oOCRService(model_config=model_config, detail=ocr_detail)

        # Route to appropriate processing method based on file type
        if file_ext == ".pdf":
            return ocr_service.process_pdf(
                pdf_path=file_path,
                prompt=config.ocr_prompt,
                max_pages=config.max_pages,
                chunk_by_page=config.chunk_by_page,
            )

        elif file_ext in [".docx", ".doc"]:
            return ocr_service.process_docx(
                docx_path=file_path,
                prompt=config.ocr_prompt,
            )

        elif file_ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]:
            return ocr_service.process_image(
                image_path=file_path,
                prompt=config.ocr_prompt,
                max_tokens=config.max_tokens_per_request,
            )

        else:
            # Use general process_file method
            return ocr_service.process_file(
                file_path=file_path,
                prompt=config.ocr_prompt,
                doc_type=config.doc_type,
                max_pages=config.max_pages,
                chunk_by_page=config.chunk_by_page,
            )

    def _process_extraction_result(
        self, result: Dict[str, Any], file_path: str, config: "FileReadConfig"
    ) -> Dict[str, Any]:
        """
        Process extraction result into standardized node output.

        Args:
            result: Result from extraction
            file_path: Path to file
            config: File read configuration

        Returns:
            Standardized node output dictionary

        Raises:
            RuntimeError: If extraction failed and skip_on_error is False
        """
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        file_ext = os.path.splitext(file_path)[1].lower()

        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error processing file")
            if config.skip_on_error:
                # Skip and continue workflow
                file_executor_logger.warning(f"Skipping file due to error: {error_msg}")
                return {
                    "content": "",
                    "metadata": {
                        "filename": os.path.basename(file_path),
                        "file_size_mb": file_size_mb,
                        "file_type": file_ext,
                    },
                    "error": error_msg,
                    "skipped": True,
                }
            else:
                raise RuntimeError(error_msg)

        # Build successful output.
        # For raw binary files, keep legacy behavior unless the node explicitly
        # opts into LLM-safe output.
        content = result.get("text", "")
        is_raw_binary = (
            result.get("extraction_method") == "raw"
            and result.get("content_type") == "base64"
        )
        if is_raw_binary and not getattr(config, "llm_safe_output", False):
            content = result.get("raw_content", content)

        node_output = {
            "content": content,
            "metadata": {
                "filename": os.path.basename(file_path),
                "file_size_mb": file_size_mb,
                "file_type": file_ext,
                "extraction_method": result.get("extraction_method", "unknown"),
                "total_tokens": result.get("total_tokens", 0),
                "content_type": result.get("content_type", "text"),
            },
            "extraction_method": result.get("extraction_method", "unknown"),
        }

        if is_raw_binary and getattr(config, "llm_safe_output", False):
            node_output["llm_safe_output_enabled"] = True

        # Include raw_content separately for downstream nodes that need it
        if "raw_content" in result:
            node_output["raw_content"] = result["raw_content"]

        # Add page count for PDFs
        if "page_count" in result:
            node_output["metadata"]["page_count"] = result["page_count"]

        # Add page results if chunked by page
        if "pages" in result and result["pages"]:
            node_output["pages"] = result["pages"]

        # Add structured CSV data if available (parsed rows, columns, headers)
        if "parsed_rows" in result:
            node_output["parsed_rows"] = result["parsed_rows"]
        if "parsed_columns" in result:
            node_output["parsed_columns"] = result["parsed_columns"]
        if "column_names" in result:
            node_output["column_names"] = result["column_names"]

        file_executor_logger.info(
            f"FILE_READ completed successfully: {node_output.get('metadata', {}).get('filename', 'unknown')}"
        )

        return node_output

    async def _create_tracking_record(
        self, node: EnhancedNodeData, state: WorkflowState
    ) -> Optional[int]:
        """
        Create database tracking record and send start notification.

        Args:
            node: The file read node
            state: Current workflow state

        Returns:
            Node execution ID, or None if tracking disabled
        """
        file_info = state.get("file_info", {})

        # Get review iteration from state (set by upstream agent nodes)
        review_iteration = state.get("current_review_iteration")

        node_exec_id = await self.database_tracker.create_node_execution(
            node,
            state,
            "FILE_READ",
            {"file_info": file_info},
            review_iteration=review_iteration,
        )

        # Send start notification
        if node_exec_id:
            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_start(
                node,
                state,
                "FILE_READ",
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
            node: The file read node
            state: Current workflow state
            node_exec_id: Database node execution ID
            node_output: Output data from file read
            duration_seconds: Execution duration
        """
        # Complete database record
        await self.database_tracker.complete_node_execution(node_exec_id, node_output, None)

        # Get complete node execution data for proper notification
        from backend.services.execution.history import ExecutionHistoryService

        start_time = None
        end_time = None
        node_input_data = None

        if node_exec_id:
            try:
                node_exec_data = ExecutionHistoryService.get_node_execution_by_id(
                    node_exec_id
                )
                if node_exec_data and isinstance(node_exec_data, dict):
                    start_time = (
                        str(node_exec_data.get("start_time"))
                        if node_exec_data.get("start_time")
                        else None
                    )
                    end_time = (
                        str(node_exec_data.get("end_time"))
                        if node_exec_data.get("end_time")
                        else None
                    )
                    node_input_data = node_exec_data.get("input_data")
            except Exception as e:
                file_executor_logger.warning(
                    f"Failed to get complete node data for FILE_READ {node.name}: {e}"
                )

        # Send completion notification with timing data
        current_order = self.database_tracker.get_execution_order(state)

        # Build notification parameters - notify_complete accepts start_time and end_time
        # but our notification_handler.notify_complete signature may not have these yet
        # For now, we include them in the notification for future compatibility
        await self.notification_handler.notify_complete(
            node,
            state,
            node_output,
            "FILE_READ",
            node_exec_id=node_exec_id,
            duration_seconds=duration_seconds,
            input_data=node_input_data,
            execution_order=current_order,
        )

        # Log timing information
        if start_time and end_time:
            file_executor_logger.info(
                f"FILE_READ {node.name} timing: start={start_time}, end={end_time}"
            )

    def _build_state_update(
        self, node: EnhancedNodeData, node_output: Dict[str, Any], state: WorkflowState
    ) -> Dict[str, Any]:
        """
        Build state update dictionary.

        Args:
            node: The file read node
            node_output: Output from file read
            state: Current workflow state

        Returns:
            State update dictionary
        """
        node_output = self._prepare_llm_safe_output(node, node_output, state)
        file_content = node_output.get("content", "")

        # Fallback: If content is empty, log warning
        if not file_content:
            file_executor_logger.warning(
                f"[FILE_READ DEBUG] Node {node.name} has empty content"
            )

        file_executor_logger.info(
            f"[FILE_READ DEBUG] Node {node.name} - Content length: {len(file_content)}"
        )

        order_update = self.database_tracker.increment_execution_order(state)

        # Build fields dict with structured CSV data at top level for easy access
        fields = dict(node_output)
        if node_output.get("parsed_columns"):
            fields["columns"] = node_output["parsed_columns"]
        if node_output.get("parsed_rows"):
            fields["rows"] = node_output["parsed_rows"]
        if node_output.get("column_names"):
            fields["column_names"] = node_output["column_names"]

        # Get file metadata for state
        metadata = node_output.get("metadata", {})
        file_name = metadata.get("filename", "uploaded_file")
        content_type = metadata.get("content_type", "text")

        state_update = {
            "messages": [HumanMessage(content=file_content)],  # For agents
            "file_content": file_content,  # Direct access
            "file_name": file_name,  # Filename for MCP servers
            "file_content_type": content_type,  # text or base64
            "file_metadata": metadata,  # Full metadata
            "node_output": {  # Standard node output format
                "raw": file_content,
                "structured": node_output,
                "fields": fields,
            },
            **order_update,
        }

        if node_output.get("raw_content"):
            state_update["file_raw_content"] = node_output["raw_content"]
        if node_output.get("content_ref"):
            state_update["file_content_ref"] = node_output["content_ref"]
            state_update["file_content_is_llm_safe"] = True

        return state_update

    def _prepare_llm_safe_output(
        self,
        node: EnhancedNodeData,
        node_output: Dict[str, Any],
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Replace raw binary prompt content with a compact runtime reference."""

        if not node_output.get("llm_safe_output_enabled"):
            return node_output
        if node_output.get("content_ref"):
            return node_output

        raw_content = node_output.get("raw_content")
        if not raw_content:
            return node_output

        from backend.services.file_content_references import (
            register_file_content_reference,
        )

        metadata = dict(node_output.get("metadata", {}))
        execution_id = state.get("execution_id") or str(
            state.get("db_execution_id") or ""
        )
        token = register_file_content_reference(
            raw_content,
            execution_id=execution_id,
            node_id=node.uniq_id,
            metadata=metadata,
        )
        safe_content = self._build_llm_safe_content(token, metadata, len(raw_content))

        updated_output = dict(node_output)
        metadata["llm_safe_output"] = True
        metadata["content_ref"] = token
        metadata["raw_content_length"] = len(raw_content)
        updated_output["metadata"] = metadata
        updated_output["content"] = safe_content
        updated_output["llm_safe_content"] = safe_content
        updated_output["content_ref"] = token
        return updated_output

    def _build_llm_safe_content(
        self,
        token: str,
        metadata: Dict[str, Any],
        raw_content_length: int,
    ) -> str:
        """Build the LLM-facing content for a raw binary file reference."""

        filename = metadata.get("filename", "uploaded_file")
        file_type = metadata.get("file_type", "unknown")
        file_size_mb = metadata.get("file_size_mb")
        size_text = (
            f"{file_size_mb:.2f} MB"
            if isinstance(file_size_mb, (int, float))
            else "unknown size"
        )

        return (
            "[File content reference]\n"
            f"Filename: {filename}\n"
            f"Type: {file_type}\n"
            f"Size: {size_text}\n"
            f"Raw base64 length: {raw_content_length} characters\n"
            f"File/base64 payload: {token}\n"
            "Pass the File/base64 payload value unchanged when a delegated agent or "
            "tool needs the file. The runtime expands this compact reference to raw "
            "base64 only when a tool uses it."
        )

    async def _handle_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Handle file read error.

        Args:
            node: The file read node
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
                ExecutionHistoryService.mark_node_failed(
                    node_exec_id, error=error_message, output_data=error_output
                )
            except Exception as db_error:
                file_executor_logger.error(
                    f"Failed to mark FILE_READ node as failed: {db_error}"
                )

        # Send error notification
        await self.notification_handler.notify_error(
            node, state, error_message, "FILE_READ"
        )

        # Build error state update
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": {
                "raw": f"File read failed: {error_message}",
                "structured": error_output,
                "fields": error_output,
            },
            **order_update,
        }


# Helper data class for internal use
class FileReadConfig:
    """Configuration for file reading."""

    def __init__(
        self,
        max_file_size_mb: int,
        allowed_extensions: list,
        extraction_mode: str,
        ocr_prompt: Optional[str],
        doc_type: str,
        max_pages: Optional[int],
        chunk_by_page: bool,
        max_tokens_per_request: int,
        skip_on_error: bool,
        model_deployment_id: Optional[str] = None,
        llm_safe_output: bool = False,
        # General output format
        output_format: str = "markdown",
        # CSV-specific configuration
        csv_delimiter: str = "auto",
        csv_has_header: str = "auto",
        csv_output_format: str = "markdown",
        csv_max_rows: Optional[int] = None,
        csv_chunk_size: int = 50,
        csv_include_schema: bool = True,
        csv_include_stats: bool = True,
        csv_encoding: str = "auto",
    ):
        """Initialize file read configuration."""
        self.max_file_size_mb = max_file_size_mb
        self.allowed_extensions = allowed_extensions
        self.extraction_mode = extraction_mode
        self.output_format = output_format
        self.ocr_prompt = ocr_prompt
        self.doc_type = doc_type
        self.max_pages = max_pages
        self.chunk_by_page = chunk_by_page
        self.max_tokens_per_request = max_tokens_per_request
        self.skip_on_error = skip_on_error
        self.model_deployment_id = model_deployment_id
        self.llm_safe_output = llm_safe_output
        # CSV-specific
        self.csv_delimiter = csv_delimiter
        self.csv_has_header = csv_has_header
        self.csv_output_format = csv_output_format
        self.csv_max_rows = csv_max_rows
        self.csv_chunk_size = csv_chunk_size
        self.csv_include_schema = csv_include_schema
        self.csv_include_stats = csv_include_stats
        self.csv_encoding = csv_encoding
