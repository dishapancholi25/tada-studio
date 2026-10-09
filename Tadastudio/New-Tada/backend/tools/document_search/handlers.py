"""Business logic handlers for document search operations."""

import logging
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from ...services.document_storage import document_search_service
from ...services.document_storage.search_service import get_last_query_embedding_cost
from ...services.streaming import streaming_emitter
from .execution import get_execution_storage
from .formatters import FullDocumentFormatter, get_formatter
from .schemas import DocumentSearchConfig, DocumentSearchExecutionMetadata


logger = logging.getLogger(__name__)

# Tool name constant for streaming events
DOCUMENT_SEARCH_TOOL_NAME = "document_search"


def _increment_search_counts(
    collection_ids: Optional[List[str]] = None, document_ids: Optional[List[str]] = None
) -> None:
    """Increment search_count for collections, resolved from collection IDs or document IDs."""
    try:
        from ...services.database import get_db
        from ...models.documents.collection import DocumentCollection
        from ...models.documents.document import Document as DocumentModel

        ids_to_increment: List[str] = []

        with get_db() as db:
            if collection_ids:
                ids_to_increment = list(collection_ids)
            elif document_ids:
                # Resolve collection IDs from document IDs
                rows = (
                    db.query(DocumentModel.collection_id)
                    .filter(DocumentModel.id.in_(document_ids))
                    .distinct()
                    .all()
                )
                ids_to_increment = [str(r[0]) for r in rows if r[0]]

            if ids_to_increment:
                db.query(DocumentCollection).filter(
                    DocumentCollection.id.in_(ids_to_increment)
                ).update(
                    {
                        DocumentCollection.search_count: DocumentCollection.search_count
                        + 1
                    },
                    synchronize_session=False,
                )
                db.commit()
    except Exception as e:
        logger.warning(f"Failed to increment search counts: {e}")


def execute_full_document_retrieval(
    document_id: str,
    include_metadata: bool = True,
    citation_format: str = "structured",
) -> str:
    """Retrieve and format full document content.

    Args:
        document_id: Document ID to retrieve
        include_metadata: Whether to include metadata
        citation_format: How to format the output

    Returns:
        Formatted full document string
    """
    logger.info(f"Returning full document for document ID: {document_id}")

    # Get all chunks for the single document
    chunks = document_search_service.get_all_chunks_for_document(
        document_id=document_id, include_metadata=include_metadata
    )

    if not chunks:
        return "No content found for the specified document."

    # Format the full document
    return FullDocumentFormatter.format(
        chunks=chunks,
        document_id=document_id,
        citation_format=citation_format,
    )


def execute_collection_search(
    collection_ids: List[str],
    query: str,
    config: DocumentSearchConfig,
    document_ids: Optional[List[str]] = None,
) -> List[Tuple[Document, float]]:
    """Execute search across collections.

    Args:
        collection_ids: List of collection IDs to search
        query: Search query
        config: Search configuration
        document_ids: Optional list of document IDs to filter by

    Returns:
        List of (Document, score) tuples
    """
    logger.info(f"Searching in collections: {collection_ids}")
    logger.info(
        f"Search parameters - k: {config.search_k}, type: {config.search_type}, "
        f"threshold: {config.similarity_threshold}"
    )

    all_results = []

    # Determine search type based on configuration
    if config.hybrid_search_enabled and config.search_mode in ["hybrid", "keyword"]:
        # Determine search type parameter
        if config.search_mode == "keyword":
            search_type_param = "text"
        else:
            search_type_param = "hybrid"

        logger.info(
            f"Using {search_type_param} search "
            f"(hybrid_enabled={config.hybrid_search_enabled}, mode={config.search_mode})"
        )

        # Use hybrid or text search
        results = document_search_service.search_multiple_collections(
            collection_ids=collection_ids,
            query=query,
            k=config.search_k,
            search_type=search_type_param,
            document_ids=document_ids,
            alpha=1 - config.keyword_weight if search_type_param == "hybrid" else None,
            include_metadata=config.include_metadata,
        )

        logger.info(
            f"[SEARCH-RESULTS] Raw results from search service: {len(results)} results"
        )

        # Convert to (Document, score) format
        # NOTE: For hybrid/text search, DO NOT apply similarity threshold filtering
        # Hybrid search uses its own RRF-based confidence scoring
        for idx, result in enumerate(results):
            doc = Document(
                page_content=result["content"],
                metadata=result.get("metadata", {}),
            )
            all_results.append((doc, result["score"]))
            logger.debug(
                f"[SEARCH-RESULTS] Hybrid result {idx + 1}: score={result['score']:.3f}, "
                f"content_len={len(result['content'])}"
            )

        logger.info(
            f"[SEARCH-RESULTS] Converted {len(all_results)} hybrid search results"
        )

    elif config.search_type == "similarity":
        logger.info("Using similarity search")

        results = document_search_service.search_multiple_collections(
            collection_ids=collection_ids,
            query=query,
            k=config.search_k,
            search_type="similarity",
            document_ids=document_ids,
            include_metadata=config.include_metadata,
        )

        logger.info(
            f"[SEARCH-RESULTS] Raw results from search service: {len(results)} results"
        )

        # Convert and filter by threshold (ONLY for similarity search)
        filtered_count = 0
        filtered_out_count = 0
        for idx, result in enumerate(results):
            score = result["score"]
            if score >= config.similarity_threshold:
                doc = Document(
                    page_content=result["content"],
                    metadata=result.get("metadata", {}),
                )
                all_results.append((doc, score))
                filtered_count += 1
                logger.debug(
                    f"[SEARCH-RESULTS] Similarity result {idx + 1}: KEPT (score={score:.3f} >= threshold={config.similarity_threshold})"
                )
            else:
                filtered_out_count += 1
                logger.debug(
                    f"[SEARCH-RESULTS] Similarity result {idx + 1}: FILTERED OUT (score={score:.3f} < threshold={config.similarity_threshold})"
                )

        logger.info(
            f"[SEARCH-RESULTS] Similarity search: kept {filtered_count} results, "
            f"filtered out {filtered_out_count} results (threshold={config.similarity_threshold})"
        )

    elif config.search_type == "mmr":
        # MMR not implemented in custom service, use similarity search
        logger.warning(
            "MMR search not implemented in custom service, using similarity search"
        )
        results = document_search_service.search_multiple_collections(
            collection_ids=collection_ids,
            query=query,
            k=config.search_k,
            search_type="similarity",
            document_ids=document_ids,
            include_metadata=config.include_metadata,
        )

        # Convert results
        for result in results:
            doc = Document(
                page_content=result["content"],
                metadata=result.get("metadata", {}),
            )
            all_results.append((doc, result["score"]))

    else:
        # Default to similarity search
        results = document_search_service.search_multiple_collections(
            collection_ids=collection_ids,
            query=query,
            k=config.search_k,
            search_type="similarity",
            document_ids=document_ids,
            include_metadata=config.include_metadata,
        )

        # Convert results
        for result in results:
            doc = Document(
                page_content=result["content"],
                metadata=result.get("metadata", {}),
            )
            all_results.append((doc, result["score"]))

    return all_results


def execute_document_search(
    document_ids: List[str],
    query: str,
    config: DocumentSearchConfig,
    user_id: Optional[str] = None,
) -> List[Tuple[Document, float]]:
    """Execute search across specific documents.

    Args:
        document_ids: List of document IDs to search
        query: Search query
        config: Search configuration

    Returns:
        List of (Document, score) tuples
    """
    logger.info(f"Searching in specific documents: {document_ids}")
    logger.info(
        f"Search parameters - k: {config.search_k}, type: {config.search_type}, "
        f"threshold: {config.similarity_threshold}"
    )

    # Get all available collections from the document storage service
    from ...services.document_storage import DocumentStorageService

    doc_service = DocumentStorageService()
    all_collections = doc_service.get_collections(user_id=user_id, filter_type="all")
    collection_ids = [str(col.id) for col in all_collections]

    if not collection_ids:
        logger.warning("No collections found in document service")
        return []

    # Use collection search with document ID filter
    if config.hybrid_search_enabled and config.search_mode in ["hybrid", "keyword"]:
        search_type_param = "keyword" if config.search_mode == "keyword" else "hybrid"
        results = document_search_service.search_multiple_collections(
            collection_ids=collection_ids,
            query=query,
            k=config.search_k,
            search_type=search_type_param,
            document_ids=document_ids,
            alpha=1 - config.keyword_weight if search_type_param == "hybrid" else None,
            include_metadata=config.include_metadata,
        )
    else:
        results = document_search_service.search_multiple_collections(
            collection_ids=collection_ids,
            query=query,
            k=config.search_k,
            search_type="similarity",
            document_ids=document_ids,
            include_metadata=config.include_metadata,
        )

    # Convert results to Document format
    all_results = []
    for result in results:
        doc = Document(
            page_content=result["content"],
            metadata=result.get("metadata", {}),
        )
        all_results.append((doc, result["score"]))

    return all_results


def execute_search(
    query: str,
    config: DocumentSearchConfig,
    call_id: str = "",
    user_id: Optional[str] = None,
) -> str:
    """Execute document search with given query and configuration.

    Args:
        query: Search query
        config: Search configuration
        call_id: Optional call ID for streaming progress events

    Returns:
        Formatted search results string

    Raises:
        Exception: If search fails
    """
    try:
        # Check if we should return full document(s)
        if (
            config.return_full_document
            and config.document_ids
            and not config.collection_names
        ):
            # Emit progress for full document retrieval
            doc_count = len(config.document_ids)
            streaming_emitter.emit_tool_progress(
                call_id=call_id,
                tool_name=DOCUMENT_SEARCH_TOOL_NAME,
                message=f"Retrieving {doc_count} full document(s)...",
                progress=50,
            )

            if doc_count == 1:
                return execute_full_document_retrieval(
                    document_id=config.document_ids[0],
                    include_metadata=config.include_metadata,
                    citation_format=config.citation_format,
                )

            # Multiple documents - retrieve and concatenate
            parts = []
            for i, doc_id in enumerate(config.document_ids):
                doc_content = execute_full_document_retrieval(
                    document_id=doc_id,
                    include_metadata=config.include_metadata,
                    citation_format=config.citation_format,
                )
                parts.append(f"--- Document {i + 1} ---\n\n{doc_content}")

                streaming_emitter.emit_tool_progress(
                    call_id=call_id,
                    tool_name=DOCUMENT_SEARCH_TOOL_NAME,
                    message=f"Retrieved document {i + 1}/{doc_count}",
                    progress=50 + int(40 * (i + 1) / doc_count),
                )

            return "\n\n".join(parts)

        all_results = []

        # Emit progress: starting search
        search_targets = []
        if config.collection_names:
            search_targets.append(f"{len(config.collection_names)} collection(s)")
        if config.document_ids:
            search_targets.append(f"{len(config.document_ids)} document(s)")
        target_desc = " and ".join(search_targets) if search_targets else "documents"

        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=DOCUMENT_SEARCH_TOOL_NAME,
            message=f"Searching {target_desc}...",
            progress=20,
        )

        # Search in collections
        if config.collection_names:
            collection_results = execute_collection_search(
                collection_ids=config.collection_names,
                query=query,
                config=config,
                document_ids=config.document_ids if config.document_ids else None,
            )
            all_results.extend(collection_results)

            # Increment search counts for searched collections
            _increment_search_counts(collection_ids=config.collection_names)

        # Search in specific documents (if no collections specified)
        elif config.document_ids:
            document_results = execute_document_search(
                document_ids=config.document_ids,
                query=query,
                config=config,
                user_id=user_id,
            )
            all_results.extend(document_results)

            # Increment search counts for collections containing these documents
            _increment_search_counts(document_ids=config.document_ids)

        # Emit progress: processing results
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=DOCUMENT_SEARCH_TOOL_NAME,
            message=f"Found {len(all_results)} results, ranking...",
            progress=70,
        )

        # Sort by score and take top k
        all_results.sort(key=lambda x: x[1], reverse=True)
        all_results = all_results[: config.search_k]

        logger.info(
            f"[SEARCH-RESULTS] Final results: {len(all_results)} results for query '{query}' "
            f"(search_k={config.search_k})"
        )

        # Return empty result message if no results
        if not all_results:
            return "No relevant documents found for the query."

        # Emit progress: formatting results
        streaming_emitter.emit_tool_progress(
            call_id=call_id,
            tool_name=DOCUMENT_SEARCH_TOOL_NAME,
            message=f"Formatting {len(all_results)} results...",
            progress=90,
        )

        # Format results using appropriate formatter
        formatter = get_formatter(
            citation_format=config.citation_format,
            prompt_template=config.prompt_template,
        )

        formatted_result = formatter.format(
            results=all_results,
            query=query,
            include_confidence=config.include_confidence_scores,
        )

        # Store execution metadata with embedding cost
        embedding_cost_data = get_last_query_embedding_cost()
        metadata = DocumentSearchExecutionMetadata(
            query=query,
            config=config,
            result_count=len(all_results),
            collections_searched=config.collection_names,
            documents_searched=config.document_ids,
            search_mode_used=config.search_mode
            if config.hybrid_search_enabled
            else config.search_type,
            embedding_tokens=embedding_cost_data.get("tokens", 0)
            if embedding_cost_data
            else 0,
            embedding_cost=embedding_cost_data.get("cost", 0.0)
            if embedding_cost_data
            else 0.0,
            embedding_model=embedding_cost_data.get("model", "")
            if embedding_cost_data
            else "",
        )
        get_execution_storage().store(None, metadata)

        return formatted_result

    except Exception as e:
        logger.error(f"Error in document search: {str(e)}")
        return f"Error searching documents: {str(e)}"
