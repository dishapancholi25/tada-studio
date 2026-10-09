# Data/Context Layer — Strategy Comparison: Our Plan vs. Azure AI Search (Native)

**Purpose:** Compare our planned parsing/chunking/embedding/storage strategy (locked decisions from the Sept 8 sync with Dipankar) against what Azure AI Search provides natively out of the box.

---

| Strategy | Our Planned Strategy | Azure AI Search (Native) |
|---|---|---|
| **Parsing** | - 4-tier escalation cascade: fast text extraction → Docling (layout-aware, open-source/MIT) → Azure Document Intelligence (forms/tables/OCR) → Vision-LLM (last resort)<br>- Runs in our own K8s, self-hosted<br>- Cost/accuracy tradeoff controlled per document via tier escalation<br><br>**Links:**<br>https://docling.org/<br>https://github.com/docling-project/docling<br>https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/overview?view=doc-intel-4.0.0 | - Document Extraction skill (built-in, free) + OCR skill<br>- Optional Azure Content Understanding skill for advanced layout/tables (separate paid resource)<br>- Single fixed path, no escalation logic<br>- Document cracking runs on Azure's managed infrastructure<br><br>**Links:**<br>https://learn.microsoft.com/en-us/azure/search/cognitive-search-predefined-skills<br>https://learn.microsoft.com/en-us/azure/search/search-indexer-overview |
| **Chunking** | - Content-type routing: row-based for tables, field-based for forms, heading-based for sections, sentence/semantic for prose (our own logic — no external tool)<br>- Preserves structure/meaning per content type<br><br>**Links:** none (internal logic) | - Text Split skill: fixed-size splitting (~5,000 char "pages") or sentence splitting<br>- Azure Content Understanding skill offers "semantic chunking" (separate paid resource)<br>- No content-type-aware routing out of the box<br><br>**Links:**<br>https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-textsplit<br>https://learn.microsoft.com/en-us/azure/search/cognitive-search-working-with-skillsets<br>https://learn.microsoft.com/en-us/azure/search/cognitive-search-predefined-skills |
| **Embedding** | - Azure OpenAI large text embedding model (`text-embedding-3-large`), called directly by our own pipeline<br>- Full control of batching, retry, and per-document cost/token tracking<br><br>**Links:**<br>https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/embeddings<br>https://ai.azure.com/catalog/models/text-embedding-3-large | - Azure OpenAI Embedding skill — same underlying models (ada-002, 3-small, 3-large)<br>- Batching/retry built-in but not configurable<br>- Also supports Azure Vision multimodal embeddings and AML-catalog models<br><br>**Links:**<br>https://learn.microsoft.com/en-us/azure/search/cognitive-search-skill-azure-openai-embedding<br>https://learn.microsoft.com/en-us/azure/search/vector-search-integrated-vectorization |
| **Storage** | - PostgreSQL + pgvector (open-source Postgres extension) — vectors, metadata, and permissions in one existing database<br>- No new infrastructure, fits existing approved stack<br><br>**Links:**<br>https://github.com/pgvector/pgvector | - Azure AI Search vector index — built-in HNSW indexing, hybrid search, semantic ranking<br>- Index projections (one document → many searchable chunks)<br><br>**Links:**<br>https://learn.microsoft.com/en-us/azure/search/vector-search-overview<br>https://learn.microsoft.com/en-us/azure/search/search-how-to-define-index-projections |

---

## Takeaway

For **parsing, chunking, and embedding**, our planned strategy gives more control and better fits banking/on-prem constraints than Azure AI Search's native, fixed-path approach.

For **storage**, Azure AI Search's native capabilities (hybrid search + semantic ranking) are stronger than pgvector alone — this is the one stage where adopting Azure AI Search (via the "bring your own vectors" pattern: we keep our own parsing/chunking/embedding, and just push finished chunks + vectors into an Azure AI Search index instead of pgvector) is worth serious consideration.

## Recommendation

Keep our own pipeline for parsing, chunking, and embedding. Evaluate Azure AI Search as a potential replacement for pgvector specifically at the storage/search layer, using the Push API (https://learn.microsoft.com/en-us/azure/search/vector-search-vectorizer-custom-web-api) — no dependency on Azure's integrated vectorization, indexer, or skillset pipeline required.
