# RAG Gap Analysis — As-Is Findings + Proposed Approach

**Purpose:** Stage-by-stage audit of Tada Studio's RAG pipeline. Original columns (Category, Capability, Status, Evidence, Impact, Severity) are the as-is findings. The **Proposed Approach / Owner** column adds where our data-layer redesign already addresses the gap, where it's someone else's area, and where it's genuinely still open.

---

## Pre-Retrieval (Query Processing)

| Capability | Status | Evidence | Impact | Severity | Proposed Approach / Owner |
|---|---|---|---|---|---|
| Query Rewriting / Condensation | Missing | Query string passed to `document_search` tool is generated ad-hoc by the agent LLM; no dedicated rewrite step in `backend/tools/document_search` or `backend/services/nodes`. | Follow-up questions ("what about the second one?") may retrieve irrelevant chunks — pronouns/context never resolved before search. | High | **Outside data-layer scope** — this is agent/prompt-level, not a chunking/storage/embedding concern. Not addressed by our redesign. |
| Query Expansion / Multi-Query | Missing | No code generates multiple query variants for a single search. | Recall capped by a single, possibly poorly-phrased query. | Medium | **Outside data-layer scope.** Not addressed. |
| HyDE (Hypothetical Document Embeddings) | Missing | No hypothetical-answer generation step before embedding the query. | Short/ambiguous queries retrieve weaker matches. | Low | **Outside data-layer scope.** Not addressed. |
| Query Routing / Classification | Partial | Agent LLM implicitly decides whether to call `document_search` via tool-calling; no explicit router/classifier. | Inconsistent behavior across models/prompts; no guaranteed decision logic. | Medium | **Outside data-layer scope.** Not addressed. |
| Query Decomposition (multi-hop) | Missing | No mechanism to split a complex question into sub-questions and retrieve for each. | Multi-hop questions needing 2+ facts from different chunks/documents are answered incompletely. | High | **Outside data-layer scope.** Not addressed. |
| Cross-Language Query Translation | Missing | No translation step before search. | Documents in a different language than the query won't be retrieved via keyword search; vector recall degrades. | Low | **Outside data-layer scope.** Not addressed. |

---

## Indexing / Ingestion

| Capability | Status | Evidence | Impact | Severity | Proposed Approach / Owner |
|---|---|---|---|---|---|
| Basic Chunking Strategies | Have | `backend/services/document_storage/chunking/strategies.py` supports recursive, character, sentence, whole_page. | N/A | Low | **Superseded by our redesign** — content-type routing replaces the single fixed-rule approach (`chunking-strategy.md`, sections 1.1–1.9). |
| Semantic Chunking | Missing | Only fixed-rule strategies exist; no similarity-based boundary detection. | Chunks may split related sentences/ideas apart, hurting retrieval precision. | Medium | **Addressed, scoped narrowly** — evaluated and adopted as a complement to structural chunking for prose only, not a primary method (cost/predictability concerns; see `chunking-strategy.md` section 1.3 and section 2 rejection table). Testing against real documents still pending. |
| Contextual Chunk Enrichment | Missing | Chunks embedded as raw text slices with no contextual prefix. | Chunks lose surrounding context, especially harmful for short/ambiguous chunks. | Medium | **Directly addressed** — contextual prefixing before embedding (`chunking-strategy.md` section 1.8): prepends a short context string (doc type, section, key facts) to each chunk. |
| Document-Level Embedding / Summary Index | Missing | `Document` model (`backend/models/documents/document.py`) has no embedding column; only `DocumentChunk` has embeddings. | Can't identify "which document is relevant" before drilling into chunks; whole-document/summary questions are weak. | High | **Not yet addressed** — new item to scope. Not part of the current chunking/parsing/embedding design. |
| Automated Metadata / Entity Tagging | Partial | Only basic metadata stored (page, source, file_type); no automatic entity/topic extraction. | No structured filters (by entity/topic) possible at query time. | Medium | **Partially addressed** — metadata-enriched chunking (`chunking-strategy.md` section 1.7) tags sensitivity level and extracted entities (account holder, account number, etc.). Still needs a lightweight NER pass to be fully implemented. |
| Multi-Modal Parsing (tables, images) | Partial | OCR processor and Excel loader exist, but PDF tables aren't specially structured during parsing. | Tabular data inside PDFs may be flattened into unstructured text, losing row/column relationships. | Low | **Addressed** — Tier 2 (Azure Document Intelligence) in the 4-tier parsing cascade reconstructs tables as real row/column objects (`parsingstrategy.md`). |

---

## Retrieval

| Capability | Status | Evidence | Impact | Severity | Proposed Approach / Owner |
|---|---|---|---|---|---|
| Vector Similarity Search | Have | `backend/services/document_storage/search_service.py` `vector_search()` using pgvector cosine distance. | N/A | Low | **Kept as-is, built upon** — not replaced by our redesign (`chunking-strategy.md` section 5). |
| Keyword / Full-Text Search | Have (chunk-level only) | `text_search()` uses `to_tsvector('english', dc.content)` on `DocumentChunk.content`. | N/A | Low | **Kept as-is.** |
| Hybrid Search with RRF Fusion | Have | `hybrid_search()` combines vector + keyword results via Reciprocal Rank Fusion. | N/A | Low | **Kept as-is.** |
| MMR (result diversity) | Broken (configured but not implemented) | `backend/tools/document_search/handlers.py` explicitly logs "MMR not implemented in custom service, using similarity search" and silently falls back. | Users who select MMR in the UI get plain similarity search without warning — misleading configuration surface. | High (fix or remove) | **Not addressed by data-layer redesign** — this is a retrieval-layer bug. Recommend flagging to whoever owns `document_search` (retrieval is Dipankar's area per the Sept work split) to fix or remove the option. |
| Structured Metadata Filtering | Missing | Search only accepts `document_ids`/`collection_ids`; no arbitrary field filters. | Can't narrow retrieval by business-relevant fields (e.g. "only 2026 contracts"). | Medium | **Partially unlocked, not fully designed** — our metadata tags (section 1.7) provide the underlying data this needs, but the actual filter-query logic at retrieval time isn't designed yet. New item to scope. |
| Document-Level Retrieval / Ranking | Missing | `return_full_document` mode requires the caller to already know a single `document_id`; it's a bypass, not a search. | Can't answer "which document is most relevant, give me the whole thing" — a common enterprise RAG need. | High | **Not yet addressed** — new item to scope. |
| Knowledge Graph Retrieval | Missing | No entity/relationship graph is built or queried anywhere in the codebase. | Complex questions requiring reasoning across multiple documents/entities are answered poorly or not at all. | High | **Owned by Dipankar** — ontology + knowledge graph is his assigned piece of the split (Sept 3/4 work division), currently in progress. Not mine to claim or solve. |

---

## Post-Retrieval

| Capability | Status | Evidence | Impact | Severity | Proposed Approach / Owner |
|---|---|---|---|---|---|
| Re-Ranking (cross-encoder / LLM reranker) | Missing | No rerank step exists anywhere in `backend/tools/document_search` or `backend/services/document_storage`. | Top-k results ranked purely by raw similarity/RRF score, often less accurate than a dedicated reranker. | High | **Directly addressed** — reranker added as a required new component (`chunking-strategy.md` section 1.8), confirming the same gap `existing-dataarchitecture.md` already flagged. Needs a cross-encoder model at query time — new infra, not yet built. |
| Contextual Compression | Missing | `max_context_tokens` config field exists but its own docstring says "not currently enforced." | Long/noisy retrieved chunks can crowd out the context window, diluting the LLM's attention. | Medium | **Not addressed — and worth flagging as a new risk**, not just a gap: our parent-child retrieval (section 1.6) pulls in *more* surrounding context per match, which could make this problem worse unless paired with compression. New item to scope. |
| De-duplication of Near-Identical Chunks | Missing | No de-duplication logic found before chunks are handed to the LLM. | Top-k can be dominated by near-duplicate chunks, wasting context budget. | Low | **Not yet addressed** — new item to scope. |

---

## Generation

| Capability | Status | Evidence | Impact | Severity | Proposed Approach / Owner |
|---|---|---|---|---|---|
| Citation / Source Attribution | Have | `DocumentSearchConfig.citation_format` supports structured/inline/footnote/none. | N/A | Low | **Kept as-is** — outside data-layer scope. |
| Grounding Enforcement | Partial | Not enforced by the system; depends entirely on each agent's own `system_prompt`. | Agents without an explicit grounding instruction can hallucinate beyond retrieved context. | Medium | **Outside data-layer scope** — prompt/agent-level concern. Not addressed. |
| Post-Hoc Faithfulness / Relevance Scoring | Partial (built but disabled) | `backend/services/evaluation/chat_scoring.py` implements LLM-judge scoring, gated by `ANALYTICS_CHAT_JUDGE_ENABLED=false`. | No ongoing visibility into answer accuracy unless a user manually reports an issue. | High (flip the flag) | **Outside data-layer scope, but a quick win** — this is a config flag someone already built and disabled. Recommend flagging to Vishal/Sachin as a low-effort fix, not a data-layer design task. |

---

## Post-Generation / Feedback Loop

| Capability | Status | Evidence | Impact | Severity | Proposed Approach / Owner |
|---|---|---|---|---|---|
| Retrieval Observability | Have | Custom Trace API/Viewer (`backend/api/trace`) plus optional Phoenix OTel tracing. | N/A | Low | **Kept as-is** — outside data-layer scope. |
| Self-Correction / Iterative Re-Retrieval (CRAG-style) | Missing | No logic re-triggers retrieval or rewrites the query when the first retrieval pass is judged insufficient. | A single bad retrieval pass with no recovery path directly produces an inaccurate answer. | High | **Outside data-layer scope** — agent/orchestration-level. Not addressed. |
| Semantic Caching of Frequent Queries | Missing | No caching layer for search results found in `document_storage`. | Repeated/common questions re-run the full embedding + search pipeline every time — extra cost/latency. | Low | **Not addressed** — possible future storage-layer optimization, but not part of the current design. |
| Continuous Automated Quality Monitoring | Partial (disabled) | Same `chat_scoring.py` mechanism as above; feeds the "Accuracy" dashboard metric only when enabled. | Quality regressions are invisible until users complain. | High (flip the flag) | **Outside data-layer scope, quick win** — same flag as Faithfulness Scoring above. Recommend to Vishal/Sachin. |

---

## Summary for Vishal

- **Directly addressed by the data-layer redesign:** Contextual Chunk Enrichment, Semantic Chunking (scoped), Re-Ranking, Multi-Modal Parsing (tables), Automated Metadata Tagging (partial).
- **Partially unlocked, needs further scoping:** Structured Metadata Filtering, Contextual Compression (new risk introduced by parent-child retrieval).
- **New gaps not previously covered, need scoping:** Document-Level Embedding/Summary Index, Document-Level Retrieval, De-duplication.
- **Owned by Dipankar, in progress:** Knowledge Graph Retrieval (ontology).
- **Outside data-layer scope entirely (agent/prompt/orchestration-level):** all Pre-Retrieval query-processing items, Grounding Enforcement, Self-Correction/Re-Retrieval, Semantic Caching.
- **Quick wins, not a design task:** Faithfulness Scoring and Continuous Quality Monitoring are both already built — just disabled by a config flag.
- **Needs a fix/decision, not new design:** MMR is broken (silently falls back), owned by retrieval, not the data layer.
