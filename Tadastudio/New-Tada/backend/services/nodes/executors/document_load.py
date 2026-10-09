"""
Document Load Node Executor.

This module handles execution of DOCUMENT_LOAD nodes, which deterministically
load full document content from collections into the workflow state.
Supports single and batch modes for downstream consumption by FOR_EACH nodes.
"""

import time
from typing import Any, Dict, List, Optional

from backend.models.workflow import EnhancedNodeData
from backend.models.workflow.configs.document_load import DocumentLoadConfig
from backend.services.config import get_logger
from backend.services.document_storage.search_service import get_document_search_service
from backend.services.document_storage.storage.repository import DocumentRepository
from backend.services.workflow.state import WorkflowState

from ..base import BaseNodeExecutor
from ..handlers import NodeDatabaseTracker, NodeNotificationHandler


document_load_logger = get_logger("nodes.executors.document_load")


class DocumentLoadNodeExecutor(BaseNodeExecutor):
    """
    Executor for DOCUMENT_LOAD nodes.

    Loads full document content from collections into node_outputs,
    supporting both single document and batch (array) output modes.
    Batch output is designed for consumption by FOR_EACH nodes.
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """Initialize document load node executor."""
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
        """Execute a document load node."""
        document_load_logger.info(f"Executing DOCUMENT_LOAD node: {node.name}")
        start_time = time.time()

        # Create tracking record
        node_exec_id = await self._create_tracking_record(node, state, graph)

        try:
            config = node.document_load_config or DocumentLoadConfig()

            # Load documents
            documents = self._load_documents(config)

            if not documents:
                return await self._handle_empty_result(node, state, node_exec_id, config)

            # Build output based on mode
            if config.output_mode == "single" and len(documents) == 1:
                node_output = self._build_single_output(documents[0], config)
            else:
                node_output = self._build_batch_output(documents, config)

            # Track in database
            duration = time.time() - start_time
            if node_exec_id:
                from backend.services.execution.history import ExecutionHistoryService

                ExecutionHistoryService.complete_node_execution(
                    node_exec_id,
                    status="completed",
                    output_data={"document_count": len(documents), "duration": duration},
                )

            # Notify completion
            await self.notification_handler.notify_complete(
                node, state, duration, "DOCUMENT_LOAD"
            )

            order_update = self.database_tracker.increment_execution_order(state)

            return {
                "node_outputs": {node.uniq_id: node_output},
                **order_update,
            }

        except Exception as e:
            document_load_logger.error(f"Error in DOCUMENT_LOAD node: {e}")
            return await self._handle_error(node, state, node_exec_id, str(e))

    def _load_documents(self, config: DocumentLoadConfig) -> List[Dict[str, Any]]:
        """Load documents from collection based on config."""
        documents = []

        if config.document_ids:
            # Load specific documents
            for doc_id in config.document_ids:
                doc = self._load_single_document(doc_id, config)
                if doc:
                    documents.append(doc)
        elif config.collection_id:
            # Load all documents from collection
            doc_infos = DocumentRepository.get_documents(
                collection_id=config.collection_id,
                status="processed",
            )
            for doc_info in doc_infos:
                doc = self._load_single_document(doc_info.id, config)
                if doc:
                    documents.append(doc)
        else:
            document_load_logger.warning("No collection_id or document_ids configured")

        return documents

    def _load_single_document(
        self, document_id: str, config: DocumentLoadConfig
    ) -> Optional[Dict[str, Any]]:
        """Load a single document's full content."""
        doc_info = DocumentRepository.get_document(document_id)
        if not doc_info:
            document_load_logger.warning(f"Document {document_id} not found")
            return None

        # Get content from chunks (ordered)
        search_service = get_document_search_service()
        chunks = search_service.get_all_chunks_for_document(
            document_id, include_metadata=True
        )

        if not chunks:
            document_load_logger.warning(f"No chunks found for document {document_id}")
            return None

        # Handle chunk output modes
        if config.chunk_output_mode == "by_page":
            return self._build_page_chunked_document(doc_info, chunks, config)
        elif config.chunk_output_mode == "by_token_limit":
            return self._build_token_chunked_document(doc_info, chunks, config)

        # Full mode - reassemble all chunks
        content = "\n\n".join(c["content"] for c in chunks if c.get("content"))
        content = self._truncate_content(content, config)

        doc_data = {
            "id": doc_info.id,
            "name": doc_info.name,
            "content": content,
            "file_type": doc_info.file_type,
            "file_size": doc_info.file_size,
            "chunk_count": doc_info.chunk_count,
            "token_count": len(content) // 4,  # Rough estimate
        }

        if config.include_metadata:
            doc_data["collection_id"] = doc_info.collection_id
            doc_data["uploaded_at"] = (
                doc_info.uploaded_at.isoformat() if doc_info.uploaded_at else None
            )

        return doc_data

    def _build_page_chunked_document(
        self, doc_info, chunks: list, config: DocumentLoadConfig
    ) -> Dict[str, Any]:
        """Build a document split into pages for FOR_EACH processing."""
        pages: Dict[int, List[str]] = {}
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            page = metadata.get("page", 0)
            if page not in pages:
                pages[page] = []
            pages[page].append(chunk.get("content", ""))

        page_items = []
        for page_num in sorted(pages.keys()):
            content = "\n\n".join(pages[page_num])
            content = self._truncate_content(content, config)
            page_items.append({
                "id": doc_info.id,
                "name": doc_info.name,
                "content": content,
                "page": page_num,
                "file_type": doc_info.file_type,
                "token_count": len(content) // 4,
            })

        return {
            "id": doc_info.id,
            "name": doc_info.name,
            "pages": page_items,
            "file_type": doc_info.file_type,
            "total_pages": len(page_items),
        }

    def _build_token_chunked_document(
        self, doc_info, chunks: list, config: DocumentLoadConfig
    ) -> Dict[str, Any]:
        """Build a document split into token-limited segments."""
        segments = []
        current_segment = []
        current_tokens = 0

        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_tokens = len(content) // 4

            if current_tokens + chunk_tokens > config.chunk_token_limit and current_segment:
                segments.append("\n\n".join(current_segment))
                current_segment = []
                current_tokens = 0

            current_segment.append(content)
            current_tokens += chunk_tokens

        if current_segment:
            segments.append("\n\n".join(current_segment))

        segment_items = []
        for i, segment in enumerate(segments):
            segment_items.append({
                "id": doc_info.id,
                "name": doc_info.name,
                "content": segment,
                "segment_index": i,
                "file_type": doc_info.file_type,
                "token_count": len(segment) // 4,
            })

        return {
            "id": doc_info.id,
            "name": doc_info.name,
            "segments": segment_items,
            "file_type": doc_info.file_type,
            "total_segments": len(segment_items),
        }

    def _build_single_output(
        self, document: Dict[str, Any], config: DocumentLoadConfig
    ) -> Dict[str, Any]:
        """Build node_output for single document mode."""
        return {
            "raw": document.get("content", ""),
            "structured": document,
            "fields": document,
        }

    def _build_batch_output(
        self, documents: List[Dict[str, Any]], config: DocumentLoadConfig
    ) -> Dict[str, Any]:
        """Build node_output for batch mode (FOR_EACH consumable)."""
        # For chunked documents, flatten pages/segments into the documents array
        flat_documents = []
        for doc in documents:
            if "pages" in doc:
                flat_documents.extend(doc["pages"])
            elif "segments" in doc:
                flat_documents.extend(doc["segments"])
            else:
                flat_documents.append(doc)

        total_tokens = sum(d.get("token_count", 0) for d in flat_documents)

        return {
            "raw": f"Loaded {len(flat_documents)} items from {len(documents)} document(s)",
            "structured": {"documents": flat_documents},
            "fields": {
                "documents": flat_documents,
                "summary": {
                    "total_documents": len(documents),
                    "total_items": len(flat_documents),
                    "total_tokens": total_tokens,
                },
            },
        }

    def _truncate_content(self, content: str, config: DocumentLoadConfig) -> str:
        """Truncate content if it exceeds token limit."""
        estimated_tokens = len(content) // 4

        if estimated_tokens <= config.max_document_size_tokens:
            return content

        max_chars = config.max_document_size_tokens * 4

        if config.truncation_strategy == "start":
            return f"[... truncated ...]\n\n{content[-max_chars:]}"
        else:
            return f"{content[:max_chars]}\n\n[... truncated ({estimated_tokens} est. tokens) ...]"

    async def _create_tracking_record(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
    ) -> Optional[int]:
        """Create database tracking record."""
        try:
            return await self.database_tracker.create_node_execution(
                node, state, "DOCUMENT_LOAD"
            )
        except Exception as e:
            document_load_logger.warning(f"Failed to create tracking record: {e}")
            return None

    async def _handle_empty_result(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        config: DocumentLoadConfig,
    ) -> Dict[str, Any]:
        """Handle case when no documents were found."""
        message = "No documents found"
        if config.collection_id:
            message += f" in collection {config.collection_id}"
        if config.document_ids:
            message += f" for IDs: {config.document_ids}"

        document_load_logger.warning(message)

        if node_exec_id:
            from backend.services.execution.history import ExecutionHistoryService

            ExecutionHistoryService.complete_node_execution(
                node_exec_id,
                status="completed",
                output_data={"message": message, "document_count": 0},
            )

        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_outputs": {
                node.uniq_id: {
                    "raw": message,
                    "structured": {"documents": []},
                    "fields": {
                        "documents": [],
                        "summary": {"total_documents": 0, "total_items": 0, "total_tokens": 0},
                    },
                }
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
        """Handle execution error."""
        from backend.services.execution.history import ExecutionHistoryService

        if node_exec_id:
            try:
                ExecutionHistoryService.complete_node_execution(
                    node_exec_id,
                    status="failed",
                    error_message=error_message,
                )
            except Exception as db_error:
                document_load_logger.error(f"Failed to mark node as failed: {db_error}")

        await self.notification_handler.notify_error(
            node, state, error_message, "DOCUMENT_LOAD"
        )

        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_outputs": {
                node.uniq_id: {
                    "raw": f"Error: {error_message}",
                    "structured": {"error": error_message},
                    "fields": {"error": error_message},
                }
            },
            **order_update,
        }
