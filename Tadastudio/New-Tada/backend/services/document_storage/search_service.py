"""Document search service using custom document_chunks table."""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from backend.services.database import get_db
from .embeddings.cost_tracker import calculate_embedding_cost, count_tokens
from .service import DocumentStorageService


logger = logging.getLogger(__name__)

# Module-level storage for last query embedding cost
_last_query_embedding_cost: Optional[Dict[str, Any]] = None


def get_last_query_embedding_cost() -> Optional[Dict[str, Any]]:
    """Get the cost data from the most recent query embedding."""
    global _last_query_embedding_cost
    return _last_query_embedding_cost


class DocumentSearchService:
    """Service for searching documents using our custom tables."""

    def __init__(self, storage_service: Optional[DocumentStorageService] = None):
        """Initialize document search service.

        Args:
            storage_service: Optional DocumentStorageService instance
        """
        self.storage_service = storage_service or DocumentStorageService()

        # Get embeddings from storage service
        embeddings = self.storage_service.get_embeddings()

        # Log which embeddings are being used
        if embeddings:
            embedding_type = type(embeddings).__name__
            deployment = getattr(
                embeddings,
                "deployment_name",
                getattr(embeddings, "azure_deployment", "unknown"),
            )
            logger.info(
                f"[DOC-SEARCH] DocumentSearchService initialized with embeddings: "
                f"{embedding_type}, deployment: {deployment}"
            )
        else:
            logger.warning(
                "[DOC-SEARCH] DocumentSearchService initialized without embeddings!"
            )

    def vector_search(
        self,
        collection_id: str,
        query: str,
        k: int = 5,
        include_metadata: bool = True,
        document_ids: Optional[List[str]] = None,
        embedding_deployment_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search."""
        try:
            embeddings = self.storage_service.get_embeddings(embedding_deployment_id)
            if not embeddings:
                logger.warning(
                    "[DOC-SEARCH] No embeddings service available for vector search"
                )
                return []

            # Generate query embedding
            try:
                query_embedding = embeddings.embed_query(query)
                query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

                # Track query embedding cost
                model_name = getattr(embeddings, "model", None) or getattr(
                    embeddings, "azure_deployment", "text-embedding-3-small"
                )
                query_tokens = count_tokens([query], model_name)
                query_cost = calculate_embedding_cost(query_tokens, model_name)
                logger.debug(
                    f"[DOC-SEARCH] Query embedding: {query_tokens} tokens, "
                    f"cost=${query_cost['cost']:.6f} ({query_cost['pricing_source']})"
                )
                global _last_query_embedding_cost
                _last_query_embedding_cost = {
                    "tokens": query_tokens,
                    "cost": query_cost.get("cost", 0),
                    "model": model_name,
                }
            except Exception as embed_error:
                # Log detailed error about which deployment failed
                embedding_type = type(embeddings).__name__
                deployment = getattr(
                    embeddings,
                    "deployment_name",
                    getattr(embeddings, "azure_deployment", "unknown"),
                )
                logger.error(
                    f"[DOC-SEARCH] Failed to generate embedding using {embedding_type} "
                    f"with deployment '{deployment}': {str(embed_error)}"
                )
                raise

            with get_db() as db:
                # Build query with optional document ID filter
                sql_query = """
                    SELECT
                        dc.id,
                        dc.chunk_index,
                        dc.content,
                        dc.chunk_metadata,
                        dc.embedding <=> CAST(:query_embedding AS vector) as distance,
                        d.id as document_id,
                        d.name as document_name,
                        d.file_type,
                        d.storage_path
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE d.collection_id = :collection_id
                    AND dc.embedding IS NOT NULL
                """

                params = {
                    "collection_id": collection_id,
                    "query_embedding": query_embedding_str,
                    "k": k,
                }

                # Add document filter if specified
                if document_ids:
                    sql_query += " AND d.id = ANY(:document_ids)"
                    params["document_ids"] = document_ids

                sql_query += """
                    ORDER BY dc.embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :k
                """

                results = db.execute(text(sql_query), params).fetchall()

                search_results = []
                for row in results:
                    document_id_str = str(row.document_id)
                    file_url = self.storage_service.build_file_url(
                        document_id=document_id_str,
                        storage_path=row.storage_path,
                        file_name=row.document_name,
                    )
                    result = {
                        "content": row.content,
                        "score": 1.0
                        - row.distance,  # Convert distance to similarity score
                        "metadata": {
                            **(row.chunk_metadata or {}),
                            "chunk_id": str(row.id),
                            "chunk_index": row.chunk_index,
                            "document_id": document_id_str,
                            "document_name": row.document_name,
                            "file_type": row.file_type,
                            "file_url": file_url,
                            "source_location": row.storage_path,
                        }
                        if include_metadata
                        else {},
                    }
                    search_results.append(result)

                return search_results

        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            raise

    def text_search(
        self,
        collection_id: str,
        query: str,
        k: int = 5,
        include_metadata: bool = True,
        document_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform full-text search."""
        try:
            with get_db() as db:
                # Search in chunks for more accurate results and to get chunk metadata
                sql_query = """
                    SELECT
                        dc.id as chunk_id,
                        dc.document_id,
                        dc.chunk_index,
                        dc.content,
                        dc.chunk_metadata,
                        d.name as document_name,
                        d.storage_path,
                        d.file_type,
                        ts_rank(to_tsvector('english', dc.content), websearch_to_tsquery(:lang, :query)) as rank,
                        ts_headline(
                            :lang,
                            dc.content,
                            websearch_to_tsquery(:lang, :query),
                            'MaxWords=150, MinWords=50, StartSel=<mark>, StopSel=</mark>'
                        ) as snippet
                    FROM document_chunks dc
                    INNER JOIN documents d ON d.id = dc.document_id
                    WHERE d.collection_id = :collection_id
                    AND to_tsvector('english', dc.content) @@ websearch_to_tsquery(:lang, :query)
                """

                params = {
                    "collection_id": collection_id,
                    "query": query,
                    "lang": "english",
                    "k": k,
                }

                # Add document filter if specified
                if document_ids:
                    sql_query += " AND d.id = ANY(:document_ids)"
                    params["document_ids"] = document_ids

                sql_query += """
                    ORDER BY rank DESC
                    LIMIT :k
                """

                results = db.execute(text(sql_query), params).fetchall()

                search_results = []
                for row in results:
                    document_id_str = str(row.document_id)
                    file_url = self.storage_service.build_file_url(
                        document_id=document_id_str,
                        storage_path=row.storage_path,
                        file_name=row.document_name,
                    )
                    result = {
                        "content": row.snippet if row.snippet else row.content,
                        "score": float(row.rank),
                        "metadata": {
                            **(
                                row.chunk_metadata or {}
                            ),  # Include chunk metadata (page numbers, etc.)
                            "document_id": document_id_str,
                            "chunk_id": str(row.chunk_id),
                            "chunk_index": row.chunk_index,
                            "document_name": row.document_name,
                            "file_type": row.file_type,
                            "file_url": file_url,
                            "source_location": row.storage_path,
                            "search_type": "text",
                        }
                        if include_metadata
                        else {},
                    }
                    search_results.append(result)

                return search_results

        except Exception as e:
            logger.error(f"Error in text search: {str(e)}")
            raise

    def hybrid_search(
        self,
        collection_id: str,
        query: str,
        k: int = 5,
        alpha: float = 0.5,  # Weight for vector search (0-1)
        include_metadata: bool = True,
        document_ids: Optional[List[str]] = None,
        embedding_deployment_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining vector and text search with improved RRF."""
        try:
            logger.info(
                f"[HYBRID-SEARCH] Starting hybrid search for query: '{query}', requested k={k}"
            )

            # Get both search results - fetch more for better fusion
            vector_results = self.vector_search(
                collection_id,
                query,
                k=k * 3,
                include_metadata=True,
                document_ids=document_ids,
                embedding_deployment_id=embedding_deployment_id,
            )
            logger.info(
                f"[HYBRID-SEARCH] Vector search returned {len(vector_results)} results (fetched k*3={k * 3})"
            )

            text_results = self.text_search(
                collection_id,
                query,
                k=k * 3,
                include_metadata=True,
                document_ids=document_ids,
            )
            logger.info(
                f"[HYBRID-SEARCH] Text search returned {len(text_results)} results (fetched k*3={k * 3})"
            )

            # Reciprocal Rank Fusion (RRF) with proper scoring
            rrf_k = 60  # Standard RRF parameter

            # Calculate RRF scores
            doc_scores = {}
            logger.debug(
                f"[HYBRID-SEARCH] Starting RRF fusion with rrf_k={rrf_k}, alpha={alpha}"
            )

            # Process vector results with rank-based RRF
            for rank, result in enumerate(vector_results):
                # Use chunk_id for unique identification
                chunk_id = result["metadata"].get("chunk_id")
                if not chunk_id:
                    # Fallback: create unique key from document_id and chunk_index
                    doc_id = result["metadata"].get("document_id", "")
                    chunk_index = result["metadata"].get("chunk_index", rank)
                    chunk_id = f"{doc_id}_chunk_{chunk_index}"

                # Calculate RRF score for this rank
                rrf_score = alpha / (rrf_k + rank + 1)

                if chunk_id in doc_scores:
                    # Combine scores if already exists
                    doc_scores[chunk_id]["rrf_score"] += rrf_score
                    doc_scores[chunk_id]["vector_rank"] = rank + 1
                    doc_scores[chunk_id]["vector_score"] = result.get("score", 0)
                else:
                    doc_scores[chunk_id] = {
                        "rrf_score": rrf_score,
                        "content": result["content"],
                        "metadata": result["metadata"],
                        "vector_score": result.get("score", 0),
                        "vector_rank": rank + 1,
                        "text_score": 0,
                        "text_rank": None,
                        "source": "vector",
                    }

            # Process text results with rank-based RRF
            for rank, result in enumerate(text_results):
                # Use chunk_id for unique identification (same as vector search)
                chunk_id = result["metadata"].get("chunk_id")
                if not chunk_id:
                    # Fallback: create unique key from document_id and chunk_index
                    doc_id = result["metadata"].get("document_id", "")
                    chunk_index = result["metadata"].get("chunk_index", rank)
                    chunk_id = f"{doc_id}_chunk_{chunk_index}"

                # Calculate RRF score for this rank
                rrf_score = (1 - alpha) / (rrf_k + rank + 1)

                if chunk_id in doc_scores:
                    # Update existing entry - this chunk was also found in vector search
                    doc_scores[chunk_id]["rrf_score"] += rrf_score
                    doc_scores[chunk_id]["text_rank"] = rank + 1
                    doc_scores[chunk_id]["text_score"] = result.get("score", 0)
                    # Prefer highlighted text content from text search
                    if "<mark>" in result["content"]:
                        doc_scores[chunk_id]["content"] = result["content"]
                    doc_scores[chunk_id]["source"] = "hybrid"
                else:
                    # New chunk from text search only
                    doc_scores[chunk_id] = {
                        "rrf_score": rrf_score,
                        "content": result["content"],
                        "metadata": result["metadata"],
                        "vector_score": 0,
                        "vector_rank": None,
                        "text_score": result.get("score", 0),
                        "text_rank": rank + 1,
                        "source": "text",
                    }

            # Calculate final scores and prepare results
            final_results = []

            # Calculate max possible RRF score for normalization
            # Max RRF = alpha/(rrf_k+1) + (1-alpha)/(rrf_k+1) = 1/(rrf_k+1) when found at rank 0 in both
            max_rrf_score = 1.0 / (rrf_k + 1)

            for chunk_id, info in doc_scores.items():
                # Calculate confidence score using normalized RRF score
                # This provides a consistent, rank-based confidence measure
                rrf_score = info["rrf_score"]
                confidence = min(1.0, rrf_score / max_rrf_score)

                # Boost confidence slightly if found in both searches (true hybrid result)
                if info["source"] == "hybrid":
                    confidence = min(1.0, confidence * 1.15)

                # Prepare metadata with search quality indicators
                metadata = info["metadata"].copy() if include_metadata else {}
                if include_metadata:
                    metadata["search_quality"] = {
                        "confidence": round(confidence, 3),
                        "source": info["source"],
                        "vector_rank": info["vector_rank"],
                        "text_rank": info["text_rank"],
                        "rrf_score": round(info["rrf_score"], 4),
                    }

                final_results.append(
                    {
                        "content": info["content"],
                        "score": confidence,  # Use confidence as the main score
                        "metadata": metadata,
                    }
                )

            # Sort by RRF score and return top k
            logger.info(
                f"[HYBRID-SEARCH] Generated {len(final_results)} fusion results before limiting to k={k}"
            )

            final_results.sort(
                key=lambda x: x["metadata"]
                .get("search_quality", {})
                .get("rrf_score", 0),
                reverse=True,
            )

            top_k_results = final_results[:k]
            logger.info(
                f"[HYBRID-SEARCH] Returning top {len(top_k_results)} results after RRF fusion"
            )

            # Log details of top results for debugging
            for idx, result in enumerate(top_k_results[:5]):  # Log first 5
                quality = result["metadata"].get("search_quality", {})
                logger.debug(
                    f"[HYBRID-SEARCH] Result {idx + 1}: rrf_score={quality.get('rrf_score', 0):.4f}, "
                    f"confidence={quality.get('confidence', 0):.3f}, source={quality.get('source', 'unknown')}, "
                    f"v_rank={quality.get('vector_rank')}, t_rank={quality.get('text_rank')}"
                )

            return top_k_results

        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            raise

    def search_multiple_collections(
        self,
        collection_ids: List[str],
        query: str,
        k: int = 5,
        search_type: str = "similarity",
        document_ids: Optional[List[str]] = None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Search across multiple collections.

        Args:
            collection_ids: List of collection IDs to search
            query: Search query
            k: Number of results per collection
            search_type: 'similarity', 'text', or 'hybrid'
            document_ids: Optional document ID filter
        """
        logger.info(
            f"[MULTI-COLLECTION] Searching {len(collection_ids)} collections with type={search_type}, k={k}"
        )
        all_results = []
        embedding_costs: list[Dict[str, Any]] = []

        global _last_query_embedding_cost

        for idx, collection_id in enumerate(collection_ids):
            logger.debug(
                f"[MULTI-COLLECTION] Searching collection {idx + 1}/{len(collection_ids)}: {collection_id}"
            )

            col = self.storage_service.get_collection(collection_id)
            embedding_deployment_id = col.embedding_deployment_id if col else None

            if search_type == "similarity":
                results = self.vector_search(
                    collection_id,
                    query,
                    k=k,
                    document_ids=document_ids,
                    embedding_deployment_id=embedding_deployment_id,
                    **kwargs,
                )
            elif search_type == "text":
                results = self.text_search(
                    collection_ids[idx], query, k=k, document_ids=document_ids, **kwargs
                )
            elif search_type == "hybrid":
                results = self.hybrid_search(
                    collection_id,
                    query,
                    k=k,
                    document_ids=document_ids,
                    embedding_deployment_id=embedding_deployment_id,
                    **kwargs,
                )
            else:
                logger.warning(
                    f"Unknown search type: {search_type}, defaulting to similarity"
                )
                results = self.vector_search(
                    collection_id,
                    query,
                    k=k,
                    document_ids=document_ids,
                    embedding_deployment_id=embedding_deployment_id,
                    **kwargs,
                )

            # Capture per-collection embedding cost before next iteration overwrites it
            if _last_query_embedding_cost is not None:
                embedding_costs.append(_last_query_embedding_cost)

            logger.debug(
                f"[MULTI-COLLECTION] Collection {collection_id} returned {len(results)} results"
            )
            all_results.extend(results)

        # Aggregate embedding costs across all collections
        if embedding_costs:
            total_tokens = sum(c.get("tokens", 0) for c in embedding_costs)
            total_cost = sum(c.get("cost", 0) for c in embedding_costs)
            models = list(dict.fromkeys(c.get("model", "") for c in embedding_costs))
            _last_query_embedding_cost = {
                "tokens": total_tokens,
                "cost": total_cost,
                "model": ", ".join(models) if len(models) > 1 else models[0],
            }

        logger.info(
            f"[MULTI-COLLECTION] Combined results from all collections: {len(all_results)} total results"
        )

        # Sort by score and return top k
        all_results.sort(key=lambda x: x["score"], reverse=True)
        final_results = all_results[:k]

        logger.info(
            f"[MULTI-COLLECTION] Returning top {len(final_results)} results after cross-collection sorting (k={k})"
        )

        return final_results

    def get_all_chunks_for_document(
        self,
        document_id: str,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document, ordered by chunk index."""
        try:
            with get_db() as db:
                sql_query = """
                    SELECT
                        dc.id,
                        dc.chunk_index,
                        dc.content,
                        dc.chunk_metadata,
                        d.id as document_id,
                        d.name as document_name,
                        d.storage_path,
                        d.file_type,
                        d.collection_id
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE d.id = :document_id
                    ORDER BY dc.chunk_index
                """

                params = {"document_id": document_id}
                results = db.execute(text(sql_query), params).fetchall()

                chunks = []
                for row in results:
                    document_id_str = str(row.document_id)
                    file_url = self.storage_service.build_file_url(
                        document_id=document_id_str,
                        storage_path=row.storage_path,
                        file_name=row.document_name,
                    )
                    chunk = {
                        "content": row.content,
                        "chunk_index": row.chunk_index,
                        "metadata": {
                            **(row.chunk_metadata or {}),
                            "chunk_id": str(row.id),
                            "chunk_index": row.chunk_index,
                            "document_id": document_id_str,
                            "document_name": row.document_name,
                            "file_type": row.file_type,
                            "collection_id": str(row.collection_id),
                            "file_url": file_url,
                            "source_location": row.storage_path,
                        }
                        if include_metadata
                        else {},
                    }
                    chunks.append(chunk)

                logger.info(
                    f"Retrieved {len(chunks)} chunks for document {document_id}"
                )
                return chunks

        except Exception as e:
            logger.error(f"Error getting all chunks for document: {str(e)}")
            return []


# Global instance (will be created in __init__ with proper storage service)
_document_search_service = None


def get_document_search_service() -> DocumentSearchService:
    """Get or create global document search service instance.

    Returns:
        DocumentSearchService instance
    """
    global _document_search_service
    if _document_search_service is None:
        _document_search_service = DocumentSearchService()
    return _document_search_service


# For backward compatibility
document_search_service = get_document_search_service()
