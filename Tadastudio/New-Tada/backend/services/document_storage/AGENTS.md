# Document Storage Service

## Overview

The document_storage service provides a comprehensive Retrieval-Augmented Generation (RAG) solution for managing
document uploads, processing, chunking, embedding, and semantic search. It supports multiple document formats (PDF,
DOCX, TXT, CSV, XLSX), implements intelligent text chunking with page tracking, generates vector embeddings for semantic
search, and provides hybrid search capabilities combining vector similarity and full-text search.

**Location:** `backend/services/document_storage/`

**Primary Responsibilities:**

- Upload and store document files (PDF, DOCX, TXT, CSV, XLSX)
- Process documents through appropriate loaders (factory pattern)
- Chunk documents intelligently with page boundary tracking
- Generate vector embeddings for semantic search
- Store documents, chunks, and embeddings in PostgreSQL with pgvector
- Provide vector similarity, full-text, and hybrid search capabilities
- Manage document collections for multi-tenancy
- Handle batch embedding processing with retry logic

**Key Use Cases:**

- Building RAG-enabled chatbots and agents with document knowledge
- Document search and retrieval for knowledge bases
- Semantic question-answering over document collections
- Multi-document analysis and comparison
- Document-grounded content generation

## Architecture

### Module Structure

```
backend/services/document_storage/
├── __init__.py                    # Public API exports
├── service.py                     # Main orchestration service
├── search_service.py              # Document search operations
├── models.py                      # Pydantic data models
├── exceptions.py                  # Custom exception hierarchy
├── config.py                      # Configuration constants
├── loaders/                       # Document loading (Factory pattern)
│   ├── __init__.py
│   ├── base.py                    # Abstract base loader
│   ├── factory.py                 # Loader factory
│   ├── pdf_loader.py              # PDF document loader
│   ├── docx_loader.py             # Word document loader
│   ├── text_loader.py             # Text/CSV loader
│   └── excel_loader.py            # Excel spreadsheet loader
├── chunking/                      # Text chunking strategies
│   ├── __init__.py
│   ├── strategies.py              # Chunking service
│   └── page_tracker.py            # Page boundary tracking
├── embeddings/                    # Embedding generation
│   ├── __init__.py
│   ├── manager.py                 # Embedding manager
│   └── batch_processor.py         # Batch processing with retry
├── storage/                       # File and database storage
│   ├── __init__.py
│   ├── file_storage.py            # File system management
│   └── repository.py              # Database operations
└── collections/                   # Collection management
    ├── __init__.py
    ├── service.py                 # Collection service
    └── repository.py              # Collection repository
```

**File Purposes:**

- **service.py** - Main orchestration service coordinating upload, processing, chunking, embedding
- **search_service.py** - Search operations (vector, text, hybrid) with RRF fusion
- **models.py** - Pydantic models for data validation and serialisation
- **exceptions.py** - Domain-specific exception classes
- **config.py** - Constants, defaults, and configuration values
- **loaders/** - Factory pattern for loading different document types
- **chunking/** - Intelligent text splitting with page awareness
- **embeddings/** - Embedding generation with fallback and retry logic
- **storage/** - File storage and database repository
- **collections/** - Multi-tenancy collection management

### Design Patterns

**Factory Pattern (Loaders):**
The `LoaderFactory` selects appropriate document loaders based on file extension, providing extensibility for new
document types without modifying core logic.

```python
# Factory maps extensions to loader classes
LOADER_MAP = {
    ".pdf": PDFLoader,
    ".docx": DOCXLoader,
    ".txt": TextLoader,
    ".csv": CSVLoader,
    ".xlsx": ExcelLoader,
}
```

**Repository Pattern (Data Access):**
`DocumentRepository` and `CollectionRepository` encapsulate all database operations, providing a clean abstraction over
SQLAlchemy operations.

**Service Layer Pattern:**

- `DocumentStorageService` - High-level orchestration
- `DocumentSearchService` - Search-specific operations
- `CollectionService` - Collection management
- `ChunkingService` - Text chunking logic
- `EmbeddingManager` - Embedding instance management

**Manager Pattern:**

- `FileStorageManager` - File system operations
- `EmbeddingManager` - Embedding instance lifecycle

**Dependency Injection:**
Services accept dependencies through constructors, with sensible defaults:

```python
class DocumentSearchService:
    def __init__(self, storage_service: Optional[DocumentStorageService] = None):
        self.storage_service = storage_service or DocumentStorageService()
```

### Component Relationships

```
API Layer (FastAPI routes)
    ↓
DocumentStorageService (orchestrator)
    ├── FileStorageManager → File system
    ├── DocumentRepository → PostgreSQL (documents table)
    ├── CollectionService → PostgreSQL (collections table)
    ├── LoaderFactory → PDF/DOCX/TXT/CSV/XLSX loaders
    ├── ChunkingService → TextSplitterFactory
    └── EmbeddingManager → Azure/OpenAI embeddings
         └── BatchEmbeddingProcessor → Retry logic

DocumentSearchService
    ├── DocumentStorageService → Embedding instances
    └── PostgreSQL (pgvector) → Vector similarity search
```

### Dependencies

**Internal Dependencies:**

- `backend.services.database` - Database session management
- `backend.services.text_splitting` - Text chunking strategies
- `backend.services.llm_models.embedding_factory` - Embedding deployment loading
- `backend.models` - SQLAlchemy models (Document, DocumentChunk, DocumentCollection)

**External Dependencies:**

- `langchain_core.documents` - Document abstraction
- `langchain_openai` - Azure/OpenAI embedding clients
- `pydantic` - Data validation and serialisation
- `sqlalchemy` - Database ORM
- `azure.identity` - Azure credential management (optional)

**Database Dependencies:**

- **Tables:** `documents`, `document_chunks`, `document_collections`
- **Extensions:** `pgvector` for vector similarity search
- **PostgreSQL features:** Full-text search (tsvector), array operations

**Environment Variables:**

- `AZURE_OPENAI_API_KEY` / `AZURE_OPENAI_EMBEDDING_KEY` - Azure OpenAI credentials
- `AZURE_OPENAI_ENDPOINT` / `AZURE_OPENAI_EMBEDDING_HOST` - Azure endpoint
- `KEY_OPENAI_API_EMBEDDING_MODEL` - Deployment name
- `OPENAI_API_KEY` - OpenAI credentials (fallback)

## Public API

### Exported Classes

**Main Services:**

- `DocumentStorageService` - Main orchestration service for document operations
- `DocumentSearchService` - Document search with vector, text, and hybrid modes

**Models:**

- `DocumentInfo` - Document metadata and status
- `ChunkInfo` - Information about a text chunk
- `ChunkMetadata` - Chunk metadata including page tracking
- `CollectionInfo` - Collection metadata
- `UploadResult` - Result of document upload operation
- `ProcessingMetadata` - Statistics about document processing
- `SearchResult` - Individual search result
- `BatchEmbeddingResult` - Batch embedding operation result

**Loaders:**

- `LoaderFactory` - Factory for creating document loaders
- `BaseLoader` - Abstract loader interface
- `PDFLoader` - Load PDF documents
- `DOCXLoader` - Load Word documents
- `TextLoader` - Load text files
- `CSVLoader` - Load CSV files
- `ExcelLoader` - Load Excel spreadsheets

**Chunking:**

- `ChunkingService` - Document chunking with page tracking
- `PageBoundaryTracker` - Track page boundaries in chunks

**Embeddings:**

- `EmbeddingManager` - Manage embedding instances
- `BatchEmbeddingProcessor` - Batch embedding with retry logic

**Storage:**

- `FileStorageManager` - File system operations
- `DocumentRepository` - Document database operations
- `CollectionService` - Collection management
- `CollectionRepository` - Collection database operations

### Exported Functions

- `create_document_storage_service(upload_dir=None)` - Factory function for creating service instance
- `get_document_search_service()` - Get singleton search service instance
- `document_search_service` - Pre-instantiated singleton (backward compatibility)

### Constants and Configuration

- `ALLOWED_EXTENSIONS` - Set of supported file extensions: `{".pdf", ".docx", ".txt", ".csv", ".xlsx"}`
- `DEFAULT_CHUNK_SIZE` - Default chunk size: `1000` characters
- `DEFAULT_CHUNK_OVERLAP` - Default overlap: `200` characters
- `EMBEDDING_BATCH_SIZE` - Batch size for embeddings: `64`
- `LOG_PREFIX` - Log message prefix: `"[DOC-STORAGE]"`

**Configuration Constants (config.py):**

- `MIN_CHUNK_SIZE` = 100
- `MAX_CHUNK_SIZE` = 4000
- `MIN_CHUNK_OVERLAP` = 0
- `MAX_CHUNK_OVERLAP` = 500
- `EMBEDDING_MAX_RETRIES` = 3
- `EMBEDDING_RETRY_DELAY` = 1.0 seconds
- `DEFAULT_UPLOAD_DIR` = Path("workspace/documents")
- `FALLBACK_EMBEDDING_DEPLOYMENTS` - List of deployment names to try

### Exceptions

```
Exception
└── DocumentStorageError (base)
    ├── UnsupportedFileTypeError
    ├── LoaderNotAvailableError
    ├── ChunkingError
    ├── EmbeddingError
    ├── FileStorageError
    ├── CollectionNotFoundError
    └── DocumentNotFoundError
```

## Core Classes

### `DocumentStorageService`

Main orchestration service that coordinates document upload, processing, chunking, embedding generation, and storage
operations.

**Purpose:** Provide a unified interface for all document storage operations, coordinating multiple subsystems (file
storage, loaders, chunking, embeddings, database) into a cohesive workflow.

**Responsibilities:**

- Accept document uploads and save files to storage
- Route documents to appropriate loaders based on file type
- Orchestrate chunking and embedding generation
- Store document metadata, chunks, and embeddings in database
- Manage document lifecycle (processing, processed, failed states)
- Delegate collection operations to CollectionService
- Provide document retrieval and deletion

**Initialisation:**

```python
def __init__(
    self,
    upload_dir: Optional[Path] = None,
) -> None:
    """Initialise document storage service.

    Args:
        upload_dir: Custom upload directory (default: workspace/documents)
    """
```

**Key Methods:**

#### `upload_document()`

```python
async def upload_document(
    self,
    file_name: str,
    file_content: bytes,
    collection_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    loader_mode: str = "single",
    strategy: str = "recursive",
    embedding_deployment_id: Optional[str] = None,
) -> UploadResult:
    """Upload and process a document."""
```

**Parameters:**

- `file_name` (str) - Original filename with extension
- `file_content` (bytes) - Raw file bytes
- `collection_id` (str) - Collection to add document to
- `chunk_size` (int) - Maximum chunk size in characters (default: 1000)
- `chunk_overlap` (int) - Overlap between chunks (default: 200)
- `loader_mode` (str) - Legacy parameter, not currently used
- `strategy` (str) - Chunking strategy: "recursive", "character", "auto"
- `embedding_deployment_id` (Optional[str]) - Specific embedding deployment to use

**Returns:**

- `UploadResult` - Contains document info, chunks, success status, message

**Raises:**

- `FileStorageError` - If file saving fails
- `UnsupportedFileTypeError` - If file type not supported
- `ChunkingError` - If chunking fails
- `EmbeddingError` - If embedding generation fails

**Example:**

```python
from backend.services.document_storage import DocumentStorageService

# Initialise service
service = DocumentStorageService()

# Upload a document
with open("report.pdf", "rb") as f:
    file_content = f.read()

result = await service.upload_document(
    file_name="report.pdf",
    file_content=file_content,
    collection_id="collection-uuid",
    chunk_size=1000,
    chunk_overlap=200,
    strategy="recursive",
)

if result.success:
    print(f"Uploaded: {result.document.name}")
    print(f"Chunks: {len(result.chunks)}")
    print(f"Status: {result.document.status}")
else:
    print(f"Failed: {result.message}")
```

**Behaviour:**

1. Saves file to storage with UUID-based filename
2. Creates database record with "processing" status
3. Loads document using appropriate loader (factory pattern)
4. Chunks document with selected strategy
5. Generates embeddings in batches with retry logic
6. Stores chunks and embeddings in database
7. Updates document status to "processed" or "failed"
8. Returns result with document info and chunk summaries

**Use Cases:**

- API endpoints accepting document uploads
- Bulk document import workflows
- Admin panels for knowledge base management
- RAG system document ingestion

#### `process_document()`

```python
def process_document(
    self,
    file_path: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    strategy: str = "recursive",
) -> tuple:
    """Process document and split into chunks."""
```

**Parameters:**

- `file_path` (str) - Path to document file on disk
- `chunk_size` (int) - Maximum chunk size in characters
- `chunk_overlap` (int) - Overlap between chunks
- `strategy` (str) - Chunking strategy

**Returns:**

- `tuple` - (chunks: List[Document], metadata: Dict)

**Raises:**

- `ChunkingError` - If chunking fails
- `UnsupportedFileTypeError` - If file type not supported

**Example:**

```python
# Process an already-saved file
chunks, metadata = service.process_document(
    file_path="workspace/documents/abc-123.pdf",
    chunk_size=1000,
    chunk_overlap=200,
    strategy="recursive",
)

print(f"Created {metadata['chunk_count']} chunks")
print(f"Total characters: {metadata['total_characters']}")
```

**Behaviour:**

- Uses LoaderFactory to select appropriate loader
- Loads document into Document objects
- Applies chunking strategy (page-aware for multi-page docs)
- Returns chunks with metadata including page tracking

**Use Cases:**

- Reprocessing documents with different chunking parameters
- Testing chunking strategies
- Document analysis workflows

#### `get_documents()`

```python
def get_documents(
    self,
    collection_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[DocumentInfo]:
    """Get documents with optional filtering."""
```

**Parameters:**

- `collection_id` (Optional[str]) - Filter by collection ID
- `status` (Optional[str]) - Filter by status ("processing", "processed", "failed")

**Returns:**

- `List[DocumentInfo]` - List of document information objects

**Example:**

```python
# Get all documents in a collection
docs = service.get_documents(collection_id="collection-uuid")

# Get failed documents
failed_docs = service.get_documents(status="failed")

# Get all documents
all_docs = service.get_documents()

for doc in docs:
    print(f"{doc.name}: {doc.status} ({doc.chunk_count} chunks)")
```

**Use Cases:**

- Listing documents in UI
- Monitoring document processing status
- Finding failed documents for reprocessing

#### `delete_document()`

```python
def delete_document(self, document_id: str) -> bool:
    """Delete a document and its file."""
```

**Parameters:**

- `document_id` (str) - UUID of document to delete

**Returns:**

- `bool` - True if deleted successfully

**Example:**

```python
success = service.delete_document(document_id="doc-uuid")
if success:
    print("Document deleted")
```

**Behaviour:**

- Deletes database record (cascades to chunks via foreign key)
- Deletes physical file from storage
- Returns False if document not found

#### `get_embeddings()`

```python
def get_embeddings(self, embedding_deployment_id: Optional[str] = None):
    """Get embeddings instance."""
```

**Parameters:**

- `embedding_deployment_id` (Optional[str]) - Specific deployment ID

**Returns:**

- Embeddings instance (AzureOpenAIEmbeddings, OpenAIEmbeddings, or MockEmbeddings)

**Example:**

```python
# Get default embeddings
embeddings = service.get_embeddings()

# Get specific deployment
embeddings = service.get_embeddings(embedding_deployment_id="deployment-uuid")

# Use embeddings
query_vector = embeddings.embed_query("search query")
```

**Use Cases:**

- Custom embedding generation
- Testing embeddings configuration
- Direct vector operations

#### Collection Operations

The service delegates collection operations to `CollectionService`:

```python
def create_collection(
    self,
    name: str,
    description: Optional[str] = None,
    user_id: Optional[str] = None,
) -> CollectionInfo:
    """Create a new document collection."""

def get_collections(self, user_id: Optional[str] = None) -> List[CollectionInfo]:
    """Get all document collections."""

def delete_collection(self, collection_id: str) -> bool:
    """Delete a collection and all its documents."""
```

**Example:**

```python
# Create collection
collection = service.create_collection(
    name="Technical Reports",
    description="Engineering documentation",
    user_id="user-uuid",
)

# List collections
collections = service.get_collections(user_id="user-uuid")

# Delete collection (cascades to documents)
service.delete_collection(collection_id=collection.id)
```

**Class Attributes:**

- `file_storage: FileStorageManager` - File system operations
- `repository: DocumentRepository` - Database operations
- `collection_service: CollectionService` - Collection management
- `embedding_manager: EmbeddingManager` - Embedding instances
- `chunking_service: ChunkingService` - Text chunking

**Static Methods:**

- `allowed_file(filename: str) -> bool` - Check if file extension is allowed

---

### `DocumentSearchService`

Service for searching documents using vector similarity, full-text search, or hybrid search with Reciprocal Rank
Fusion (RRF).

**Purpose:** Provide flexible search capabilities over stored documents, supporting vector similarity (semantic search),
PostgreSQL full-text search (keyword matching), and hybrid search combining both with RRF fusion.

**Responsibilities:**

- Generate query embeddings for semantic search
- Execute vector similarity search using pgvector
- Execute PostgreSQL full-text search with ranking
- Combine searches using Reciprocal Rank Fusion
- Search across multiple collections
- Filter results by document IDs
- Retrieve all chunks for a specific document

**Initialisation:**

```python
def __init__(
    self,
    storage_service: Optional[DocumentStorageService] = None,
) -> None:
    """Initialise document search service.

    Args:
        storage_service: Storage service instance (creates new if None)
    """
```

**Key Methods:**

#### `vector_search()`

```python
def vector_search(
    self,
    collection_id: str,
    query: str,
    k: int = 5,
    include_metadata: bool = True,
    document_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Perform vector similarity search."""
```

**Parameters:**

- `collection_id` (str) - Collection to search
- `query` (str) - Search query text
- `k` (int) - Number of results to return (default: 5)
- `include_metadata` (bool) - Include chunk metadata (default: True)
- `document_ids` (Optional[List[str]]) - Filter to specific documents

**Returns:**

- `List[Dict[str, Any]]` - List of search results with content, score, metadata

**Raises:**

- `EmbeddingError` - If embedding generation fails

**Example:**

```python
from backend.services.document_storage import DocumentSearchService

search_service = DocumentSearchService()

results = search_service.vector_search(
    collection_id="collection-uuid",
    query="What are the performance requirements?",
    k=5,
    include_metadata=True,
)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Content: {result['content'][:200]}...")
    print(f"Document: {result['metadata']['document_name']}")
    print(f"Page: {result['metadata'].get('page', 'N/A')}")
    print("---")
```

**Behaviour:**

1. Generates query embedding using configured embeddings service
2. Executes PostgreSQL query with pgvector cosine similarity (`<=>` operator)
3. Filters by collection_id and optional document_ids
4. Returns top-k results ordered by similarity (1.0 - distance)
5. Includes chunk metadata (document info, page numbers, etc.)

**Use Cases:**

- Semantic question-answering over documents
- Finding conceptually similar content
- RAG retrieval for agent tools
- Document recommendations

#### `text_search()` (static)

```python
@staticmethod
def text_search(
    collection_id: str,
    query: str,
    k: int = 5,
    include_metadata: bool = True,
    document_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Perform full-text search."""
```

**Parameters:**

- Same as `vector_search()`

**Returns:**

- `List[Dict[str, Any]]` - Results with highlighted snippets

**Example:**

```python
results = DocumentSearchService.text_search(
    collection_id="collection-uuid",
    query="database performance optimization",
    k=5,
)

for result in results:
    print(f"Rank: {result['score']}")
    print(f"Snippet: {result['content']}")  # Contains <mark> tags
    print("---")
```

**Behaviour:**

- Uses PostgreSQL `websearch_to_tsquery` for query parsing
- Supports quoted phrases, AND/OR operators, negation
- Uses `ts_rank` for relevance scoring
- Generates highlighted snippets with `ts_headline`
- Returns results with `<mark>` tags around matches

**Use Cases:**

- Keyword-based document search
- Finding exact phrases or terms
- Complement to semantic search

#### `hybrid_search()`

```python
def hybrid_search(
    self,
    collection_id: str,
    query: str,
    k: int = 5,
    alpha: float = 0.5,
    include_metadata: bool = True,
    document_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Perform hybrid search combining vector and text search with RRF."""
```

**Parameters:**

- `collection_id` (str) - Collection to search
- `query` (str) - Search query
- `k` (int) - Number of final results
- `alpha` (float) - Weight for vector search (0-1), where (1-alpha) weights text search
- `include_metadata` (bool) - Include metadata
- `document_ids` (Optional[List[str]]) - Filter to specific documents

**Returns:**

- `List[Dict[str, Any]]` - Fused results with search quality metadata

**Example:**

```python
results = search_service.hybrid_search(
    collection_id="collection-uuid",
    query="machine learning model evaluation metrics",
    k=10,
    alpha=0.6,  # Favour vector search slightly
)

for result in results:
    quality = result['metadata']['search_quality']
    print(f"Confidence: {quality['confidence']:.3f}")
    print(f"Source: {quality['source']}")  # 'hybrid', 'vector', or 'text'
    print(f"RRF Score: {quality['rrf_score']:.4f}")
    print(f"Vector Rank: {quality['vector_rank']}")
    print(f"Text Rank: {quality['text_rank']}")
    print(f"Content: {result['content'][:200]}...")
    print("---")
```

**Behaviour:**

1. Executes both vector and text search (fetches k*3 results each)
2. Applies Reciprocal Rank Fusion (RRF) with parameter k=60
3. Weights RRF scores by alpha (vector) and (1-alpha) (text)
4. Combines results by chunk_id, preferring highlighted text when available
5. Calculates confidence scores based on presence in both searches
6. Sorts by RRF score and returns top-k results
7. Includes detailed search quality metadata

**RRF Formula:**

```
RRF_score = alpha / (60 + vector_rank) + (1-alpha) / (60 + text_rank)
```

**Use Cases:**

- Best-of-both-worlds search combining semantic and keyword matching
- Finding results that match both meaning and specific terms
- Robust search that works well for diverse query types

#### `search_multiple_collections()`

```python
def search_multiple_collections(
    self,
    collection_ids: List[str],
    query: str,
    k: int = 5,
    search_type: str = "similarity",
    document_ids: Optional[List[str]] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    """Search across multiple collections."""
```

**Parameters:**

- `collection_ids` (List[str]) - List of collection IDs to search
- `query` (str) - Search query
- `k` (int) - Total number of results across all collections
- `search_type` (str) - "similarity", "text", or "hybrid"
- `document_ids` (Optional[List[str]]) - Filter to specific documents
- `**kwargs` - Additional arguments for search methods (e.g., alpha for hybrid)

**Returns:**

- `List[Dict[str, Any]]` - Combined results from all collections, sorted by score

**Example:**

```python
results = search_service.search_multiple_collections(
    collection_ids=["col-1", "col-2", "col-3"],
    query="API authentication methods",
    k=15,
    search_type="hybrid",
    alpha=0.5,
)

# Results are sorted by score across all collections
for result in results:
    print(f"Collection: {result['metadata']['collection_id']}")
    print(f"Document: {result['metadata']['document_name']}")
    print(f"Score: {result['score']:.3f}")
    print("---")
```

**Use Cases:**

- Searching across user's entire knowledge base
- Multi-tenant search with collection-based isolation
- Finding information across different document categories

#### `get_all_chunks_for_document()` (static)

```python
@staticmethod
def get_all_chunks_for_document(
    document_id: str,
    include_metadata: bool = True,
) -> List[Dict[str, Any]]:
    """Get all chunks for a specific document, ordered by chunk index."""
```

**Parameters:**

- `document_id` (str) - Document UUID
- `include_metadata` (bool) - Include metadata

**Returns:**

- `List[Dict[str, Any]]` - All chunks in order

**Example:**

```python
chunks = DocumentSearchService.get_all_chunks_for_document(
    document_id="doc-uuid",
    include_metadata=True,
)

# Reconstruct full document
full_text = "\n\n".join(chunk['content'] for chunk in chunks)

# Show page distribution
for chunk in chunks:
    meta = chunk['metadata']
    print(f"Chunk {meta['chunk_index']}: Page {meta.get('page', 'N/A')}")
```

**Use Cases:**

- Displaying full document content
- Document export or analysis
- Chunk-level debugging

**Class Attributes:**

- `storage_service: DocumentStorageService` - Access to embeddings and storage

**Global Functions:**

- `get_document_search_service()` - Get or create singleton instance
- `document_search_service` - Pre-instantiated singleton for backward compatibility

---

### `LoaderFactory`

Factory for creating appropriate document loaders based on file type.

**Purpose:** Decouple document loading from file type detection, enabling easy addition of new document formats without
modifying core service logic.

**Responsibilities:**

- Map file extensions to loader classes
- Instantiate appropriate loader for a given file
- Validate file type support
- Provide list of supported extensions

**Class Methods:**

#### `get_loader()`

```python
@classmethod
def get_loader(cls, file_path: str) -> BaseLoader:
    """Get appropriate loader for the file type."""
```

**Parameters:**

- `file_path` (str) - Path to file

**Returns:**

- `BaseLoader` - Instantiated loader

**Raises:**

- `UnsupportedFileTypeError` - If file extension not supported

**Example:**

```python
from backend.services.document_storage import LoaderFactory

# Get loader for PDF
loader = LoaderFactory.get_loader("document.pdf")
documents = loader.load("path/to/document.pdf")

# Get loader for Word
loader = LoaderFactory.get_loader("report.docx")
documents = loader.load("path/to/report.docx")
```

#### `is_supported()`

```python
@classmethod
def is_supported(cls, file_path: str) -> bool:
    """Check if file type is supported."""
```

**Example:**

```python
if LoaderFactory.is_supported("data.xlsx"):
    print("Excel files supported")

if not LoaderFactory.is_supported("archive.zip"):
    print("ZIP files not supported")
```

#### `get_supported_extensions()`

```python
@classmethod
def get_supported_extensions(cls) -> list:
    """Get list of supported file extensions."""
```

**Example:**

```python
supported = LoaderFactory.get_supported_extensions()
print(f"Supported: {', '.join(supported)}")
# Output: Supported: .pdf, .docx, .txt, .csv, .xlsx
```

**Loader Map:**

```python
LOADER_MAP = {
    ".pdf": PDFLoader,
    ".docx": DOCXLoader,
    ".txt": TextLoader,
    ".csv": CSVLoader,
    ".xlsx": ExcelLoader,
}
```

**Extensibility:**
To add a new document type:

1. Create loader class inheriting from `BaseLoader`
2. Add mapping to `LOADER_MAP`
3. Add extension to `ALLOWED_EXTENSIONS` in config.py

---

### `ChunkingService`

Service for chunking documents with intelligent page tracking support.

**Purpose:** Split documents into appropriately-sized chunks for embedding and retrieval, while preserving page boundary
information for citation and navigation.

**Responsibilities:**

- Chunk documents using configurable strategies (recursive, character, etc.)
- Track page boundaries when chunking multi-page documents
- Preserve metadata through chunking process
- Provide chunking statistics

**Static Methods:**

#### `chunk_documents()`

```python
@staticmethod
def chunk_documents(
    documents: List[Document],
    chunk_size: int,
    chunk_overlap: int,
    strategy: str = "recursive",
) -> Tuple[List[Document], Dict]:
    """Chunk documents with optional page tracking."""
```

**Parameters:**

- `documents` (List[Document]) - LangChain Document objects
- `chunk_size` (int) - Maximum chunk size in characters
- `chunk_overlap` (int) - Overlap between chunks
- `strategy` (str) - "recursive", "character", "auto"

**Returns:**

- `Tuple` - (chunks: List[Document], metadata: Dict)

**Example:**

```python
from backend.services.document_storage import ChunkingService
from langchain_core.documents import Document

# Documents from loader
documents = [
    Document(page_content="Page 1 content...", metadata={"page": 0}),
    Document(page_content="Page 2 content...", metadata={"page": 1}),
]

# Chunk with page tracking
chunks, metadata = ChunkingService.chunk_documents(
    documents=documents,
    chunk_size=1000,
    chunk_overlap=200,
    strategy="recursive",
)

print(f"Created {metadata['chunk_count']} chunks")
print(f"Page tracking: {metadata['has_page_tracking']}")

# Check page metadata
for chunk in chunks[:5]:
    page_info = chunk.metadata.get('page', 'N/A')
    pages = chunk.metadata.get('pages', [])
    print(f"Chunk spans pages: {pages if pages else page_info}")
```

**Behaviour:**

- Detects multi-page documents with page metadata
- For multi-page docs: uses `PageBoundaryTracker` to preserve page information
- For single-page docs: uses standard chunking
- Adds metadata: `page`, `pages`, `page_start`, `page_end`, `spans_pages`

**Chunking Strategies:**

- **recursive** - Recursively splits on separators (\n\n, \n, space)
- **character** - Splits at exact character boundaries
- **auto** - Automatically selects best strategy (currently defaults to recursive)

**Metadata Added:**

```python
{
    "page": 0,  # Primary page (for single-page chunks)
    "pages": [0, 1],  # All pages spanned (for multi-page chunks)
    "page_start": 0,  # First page
    "page_end": 1,  # Last page
    "spans_pages": True,  # Whether chunk crosses page boundary
}
```

---

### `EmbeddingManager`

Manages embedding instances with automatic fallback and configuration from environment variables or model deployments.

**Purpose:** Abstract embedding instance creation, providing automatic fallback between Azure OpenAI, OpenAI, and mock
embeddings based on available credentials.

**Responsibilities:**

- Initialise embeddings from environment variables
- Try Azure OpenAI with multiple deployment names
- Fall back to OpenAI if Azure unavailable
- Fall back to mock embeddings for testing
- Load embeddings from specific deployment IDs
- Handle Azure credential token acquisition

**Initialisation:**

```python
def __init__(self):
    """Initialise embedding manager."""
```

**Key Methods:**

#### `get_embeddings()`

```python
def get_embeddings(
    self,
    embedding_deployment_id: Optional[str] = None,
):
    """Get embeddings instance, either from deployment or default."""
```

**Parameters:**

- `embedding_deployment_id` (Optional[str]) - Specific deployment ID from database

**Returns:**

- Embeddings instance (AzureOpenAIEmbeddings, OpenAIEmbeddings, or MockEmbeddings)

**Raises:**

- `EmbeddingError` - If specified deployment not found or invalid

**Example:**

```python
from backend.services.document_storage import EmbeddingManager

manager = EmbeddingManager()

# Get default embeddings (from environment)
embeddings = manager.get_embeddings()

# Get specific deployment
embeddings = manager.get_embeddings(embedding_deployment_id="deployment-uuid")

# Use embeddings
query_vector = embeddings.embed_query("machine learning")
doc_vectors = embeddings.embed_documents(["doc 1", "doc 2"])
```

**Fallback Chain:**

1. **Specified deployment** (if `embedding_deployment_id` provided)
2. **Azure OpenAI** with primary deployment from `KEY_OPENAI_API_EMBEDDING_MODEL`
3. **Azure OpenAI** with fallback deployments (text-embedding-3-large, etc.)
4. **OpenAI** with `OPENAI_API_KEY`
5. **MockEmbeddings** for testing (warns user)

**Behaviour:**

- Tests each embedding instance with a test query
- Logs which embedding service is being used
- Warns if falling back to mock embeddings
- Supports Azure DefaultAzureCredential for managed identity

---

### `BatchEmbeddingProcessor`

Processes embeddings in batches with retry logic to handle rate limits and transient failures.

**Purpose:** Efficiently generate embeddings for large numbers of texts while handling API failures gracefully.

**Responsibilities:**

- Batch texts to stay within API limits
- Retry failed batches with exponential backoff
- Track success/failure statistics
- Return partial results on failure

**Initialisation:**

```python
def __init__(
    self,
    embeddings,
    batch_size: int = EMBEDDING_BATCH_SIZE,
    max_retries: int = EMBEDDING_MAX_RETRIES,
):
    """Initialise batch processor.

    Args:
        embeddings: Embeddings instance (AzureOpenAIEmbeddings, etc.)
        batch_size: Texts per batch (default: 64)
        max_retries: Maximum retry attempts (default: 3)
    """
```

**Key Methods:**

#### `process_batch()`

```python
def process_batch(self, texts: List[str]) -> BatchEmbeddingResult:
    """Process texts in batches and generate embeddings."""
```

**Parameters:**

- `texts` (List[str]) - List of text strings to embed

**Returns:**

- `BatchEmbeddingResult` - Contains embeddings, statistics, and errors

**Example:**

```python
from backend.services.document_storage import (
    EmbeddingManager,
    BatchEmbeddingProcessor,
)

# Get embeddings instance
manager = EmbeddingManager()
embeddings = manager.get_embeddings()

# Create batch processor
processor = BatchEmbeddingProcessor(
    embeddings=embeddings,
    batch_size=64,
    max_retries=3,
)

# Process large list of texts
texts = [chunk.page_content for chunk in chunks]  # 500 chunks
result = processor.process_batch(texts)

print(f"Processed {result.total} texts")
print(f"Successful: {result.successful}")
print(f"Failed: {result.failed}")

# Use embeddings
for i, embedding in enumerate(result.embeddings):
    if embedding is not None:
        print(f"Chunk {i}: {len(embedding)} dimensions")
    else:
        print(f"Chunk {i}: Failed - {result.errors[i]}")
```

**BatchEmbeddingResult Model:**

```python
class BatchEmbeddingResult(BaseModel):
    total: int  # Total number of texts
    successful: int  # Number of successful embeddings
    failed: int  # Number of failed embeddings
    embeddings: List[Optional[List[float]]]  # Embedding vectors (None on failure)
    errors: List[Optional[str]]  # Error messages (None on success)
```

**Behaviour:**

- Processes texts in batches of `batch_size`
- Retries failed batches up to `max_retries` times
- Returns partial results if some batches fail
- Logs detailed progress and errors

**Use Cases:**

- Document upload with hundreds of chunks
- Bulk reprocessing of documents
- Robust embedding generation with fallback

---

### `FileStorageManager`

Manages file system storage for uploaded document files.

**Purpose:** Abstract file system operations, providing UUID-based file naming, safe storage, and cleanup.

**Responsibilities:**

- Save uploaded files with UUID-based names
- Delete files by ID
- Check file existence
- Manage upload directory

**Initialisation:**

```python
def __init__(self, upload_dir: Optional[Path] = None):
    """Initialise file storage manager.

    Args:
        upload_dir: Directory for storing files (default: workspace/documents)
    """
```

**Key Methods:**

#### `save_file()`

```python
def save_file(
    self,
    file_name: str,
    file_content: bytes,
    file_id: Optional[str] = None,
) -> tuple[str, Path]:
    """Save file to storage."""
```

**Parameters:**

- `file_name` (str) - Original filename (for extension extraction)
- `file_content` (bytes) - Raw file bytes
- `file_id` (Optional[str]) - UUID (generates if not provided)

**Returns:**

- `tuple[str, Path]` - (file_id, file_path)

**Raises:**

- `FileStorageError` - If file saving fails

**Example:**

```python
from backend.services.document_storage import FileStorageManager

manager = FileStorageManager()

# Save file
file_id, file_path = manager.save_file(
    file_name="report.pdf",
    file_content=pdf_bytes,
)

print(f"Saved as: {file_path}")
# Output: workspace/documents/abc-123-def-456.pdf
```

#### `delete_file()`

```python
def delete_file(self, file_id: str) -> bool:
    """Delete file from storage."""
```

**Parameters:**

- `file_id` (str) - File UUID

**Returns:**

- `bool` - True if deleted, False if not found

**Example:**

```python
success = manager.delete_file(file_id="abc-123-def-456")
```

---

### `DocumentRepository`

Repository for document and chunk database operations.

**Purpose:** Encapsulate all database operations for documents and chunks, providing a clean abstraction over
SQLAlchemy.

**Responsibilities:**

- Create document records
- Update document status and content
- Store chunks with embeddings
- Retrieve documents with filtering
- Delete documents
- Query chunk counts

**Static Methods:**

#### `create_document()`

```python
@staticmethod
def create_document(
    file_id: str,
    collection_id: str,
    file_name: str,
    file_type: str,
    file_size: int,
    storage_path: str,
) -> DocumentModel:
    """Create a new document record."""
```

**Example:**

```python
from backend.services.document_storage import DocumentRepository

doc = DocumentRepository.create_document(
    file_id="doc-uuid",
    collection_id="col-uuid",
    file_name="report.pdf",
    file_type="PDF",
    file_size=1024000,
    storage_path="workspace/documents/doc-uuid.pdf",
)
```

#### `store_chunks()`

```python
@staticmethod
def store_chunks(
    document_id: str,
    chunks: List[tuple[str, Optional[List[float]], dict]],
    db_session=None,
) -> List[ChunkInfo]:
    """Store document chunks with embeddings."""
```

**Parameters:**

- `document_id` (str) - Document UUID
- `chunks` (List[tuple]) - List of (content, embedding, metadata) tuples
- `db_session` - Optional existing session

**Example:**

```python
chunk_data = [
    ("chunk content 1", [0.1, 0.2, ...], {"page": 0}),
    ("chunk content 2", [0.3, 0.4, ...], {"page": 0}),
]

stored = DocumentRepository.store_chunks(
    document_id="doc-uuid",
    chunks=chunk_data,
)

print(f"Stored {len(stored)} chunks")
```

---

### `CollectionService`

Service for managing document collections (multi-tenancy).

**Purpose:** Provide collection-level operations for organising documents into logical groups (e.g., per user, per
project).

**Responsibilities:**

- Create collections
- List collections (optionally filtered by user)
- Get collection details
- Delete collections (cascades to documents)

**Key Methods:**

#### `create_collection()`

```python
def create_collection(
    self,
    name: str,
    description: Optional[str] = None,
    user_id: Optional[str] = None,
) -> CollectionInfo:
    """Create a new document collection."""
```

**Example:**

```python
from backend.services.document_storage import CollectionService

service = CollectionService()

collection = service.create_collection(
    name="Technical Documentation",
    description="API and architecture docs",
    user_id="user-uuid",
)

print(f"Created collection: {collection.id}")
```

#### `get_collections()`

```python
def get_collections(
    self,
    user_id: Optional[str] = None,
) -> List[CollectionInfo]:
    """Get all collections, optionally filtered by user."""
```

**Example:**

```python
# Get user's collections
collections = service.get_collections(user_id="user-uuid")

# Get all collections
all_collections = service.get_collections()

for col in collections:
    print(f"{col.name}: {col.document_count} documents")
```

---

## Functions

### `create_document_storage_service()`

Factory function for creating configured DocumentStorageService instances.

**Signature:**

```python
def create_document_storage_service(
    upload_dir=None,
) -> DocumentStorageService:
    """Create and configure document storage service.

    Args:
        upload_dir: Optional custom upload directory

    Returns:
        Configured DocumentStorageService instance
    """
```

**Example:**

```python
from backend.services.document_storage import create_document_storage_service

# Create with default upload directory
service = create_document_storage_service()

# Create with custom directory
service = create_document_storage_service(
    upload_dir="/custom/path/documents"
)
```

**Use Cases:**

- Dependency injection in API routes
- Testing with custom upload directories
- Service initialisation

---

### `get_document_search_service()`

Get or create global DocumentSearchService singleton instance.

**Signature:**

```python
def get_document_search_service() -> DocumentSearchService:
    """Get or create global document search service instance.

    Returns:
        DocumentSearchService instance
    """
```

**Example:**

```python
from backend.services.document_storage import get_document_search_service

# Get singleton instance
search_service = get_document_search_service()

# Subsequent calls return same instance
search_service2 = get_document_search_service()
assert search_service is search_service2
```

**Use Cases:**

- Reusing search service across requests
- Avoiding repeated initialisation
- Backward compatibility

---

## Configuration

### Configuration Constants

Defined in [config.py](backend/services/document_storage/config.py:1):

**File Storage:**

```python
DEFAULT_UPLOAD_DIR = Path("workspace/documents")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx"}
```

**Chunking Defaults:**

```python
DEFAULT_CHUNK_SIZE = 1000  # characters
DEFAULT_CHUNK_OVERLAP = 200  # characters
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 4000
MIN_CHUNK_OVERLAP = 0
MAX_CHUNK_OVERLAP = 500
```

**Embedding Configuration:**

```python
EMBEDDING_BATCH_SIZE = 64  # texts per batch
EMBEDDING_MAX_RETRIES = 3  # retry attempts
EMBEDDING_RETRY_DELAY = 1.0  # seconds

FALLBACK_EMBEDDING_DEPLOYMENTS = [
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
    "embedding",
]
```

**Azure Configuration:**

```python
AZURE_API_VERSION = "2023-05-15"
AZURE_COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"
```

**Logging:**

```python
LOG_PREFIX = "[DOC-STORAGE]"
```

### Environment Variables

**Azure OpenAI (Recommended):**

- `AZURE_OPENAI_API_KEY` or `AZURE_OPENAI_EMBEDDING_KEY` - Azure OpenAI API key (required: yes)
- `AZURE_OPENAI_ENDPOINT` or `AZURE_OPENAI_EMBEDDING_HOST` - Azure endpoint URL (required: yes)
- `KEY_OPENAI_API_EMBEDDING_MODEL` - Primary deployment name (required: no, default: fallback list)

**OpenAI (Fallback):**

- `OPENAI_API_KEY` - OpenAI API key (required: no, used if Azure unavailable)

**Notes:**

- If no credentials provided, falls back to MockEmbeddings with warning
- Can use Azure DefaultAzureCredential for managed identity authentication

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.document_storage import DocumentStorageService

# Create service with defaults
service = DocumentStorageService()
```

**Custom Upload Directory:**

```python
from pathlib import Path
from backend.services.document_storage import DocumentStorageService

# Custom storage location
service = DocumentStorageService(
    upload_dir=Path("/data/documents")
)
```

**Dependency Injection (FastAPI):**

```python
from fastapi import Depends
from backend.services.document_storage import (
    DocumentStorageService,
    create_document_storage_service,
)

async def get_storage_service() -> DocumentStorageService:
    """Dependency for storage service."""
    return create_document_storage_service()

@router.post("/upload")
async def upload_document(
    service: DocumentStorageService = Depends(get_storage_service),
):
    # Use service
    pass
```

**Testing Configuration:**

```python
import pytest
from pathlib import Path
from backend.services.document_storage import DocumentStorageService

@pytest.fixture
def storage_service(tmp_path):
    """Test storage service with temporary directory."""
    return DocumentStorageService(upload_dir=tmp_path / "documents")

def test_upload(storage_service):
    result = await storage_service.upload_document(...)
    assert result.success
```

## Error Handling

### Exception Hierarchy

```
Exception
└── DocumentStorageError (base exception for all document storage errors)
    ├── UnsupportedFileTypeError (file type not supported)
    ├── LoaderNotAvailableError (required loader dependencies missing)
    ├── ChunkingError (document chunking failed)
    ├── EmbeddingError (embedding generation failed)
    ├── FileStorageError (file storage operation failed)
    ├── CollectionNotFoundError (collection ID not found)
    └── DocumentNotFoundError (document ID not found)
```

### Exception Details

#### `DocumentStorageError`

Base exception for all document storage errors. Catch this to handle any document storage-related error.

**Inherits from:** `Exception`

**When raised:**

- Never raised directly
- Parent class for all specific exceptions

**Example:**

```python
from backend.services.document_storage import (
    DocumentStorageService,
    DocumentStorageError,
)

try:
    service = DocumentStorageService()
    result = await service.upload_document(...)
except DocumentStorageError as e:
    # Catches any document storage error
    logger.error(f"Document storage error: {e}")
    return {"error": "Document operation failed"}
```

#### `UnsupportedFileTypeError`

Raised when attempting to process a file with an unsupported extension.

**Inherits from:** `DocumentStorageError`

**Attributes:**

- `file_type: str` - The unsupported file extension
- `supported_types: list` - List of supported extensions

**When raised:**

- File extension not in `ALLOWED_EXTENSIONS`
- LoaderFactory cannot find loader for file type

**Example:**

```python
from backend.services.document_storage import (
    DocumentStorageService,
    UnsupportedFileTypeError,
)

try:
    result = await service.upload_document(
        file_name="archive.zip",
        file_content=zip_bytes,
        collection_id="col-uuid",
    )
except UnsupportedFileTypeError as e:
    print(f"File type '{e.file_type}' not supported")
    print(f"Supported types: {', '.join(e.supported_types)}")
    return {"error": f"Unsupported file type. Supported: {e.supported_types}"}
```

#### `LoaderNotAvailableError`

Raised when required document loader dependencies are missing.

**Inherits from:** `DocumentStorageError`

**Attributes:**

- `loader_name: str` - Name of the loader
- `install_instruction: str` - How to install missing dependencies (optional)

**When raised:**

- Required library not installed (e.g., pypdf, python-docx)
- Import fails for loader dependencies

**Example:**

```python
from backend.services.document_storage import LoaderNotAvailableError

try:
    result = await service.upload_document(
        file_name="document.pdf",
        file_content=pdf_bytes,
        collection_id="col-uuid",
    )
except LoaderNotAvailableError as e:
    logger.error(f"Loader not available: {e.loader_name}")
    if e.install_instruction:
        logger.info(f"Install with: {e.install_instruction}")
    return {"error": "PDF processing unavailable. Contact administrator."}
```

#### `ChunkingError`

Raised when document chunking fails.

**Inherits from:** `DocumentStorageError`

**When raised:**

- Text splitter initialisation fails
- Chunking strategy invalid
- Document processing error during chunking

**Example:**

```python
from backend.services.document_storage import ChunkingError

try:
    chunks, metadata = service.process_document(
        file_path="document.pdf",
        chunk_size=1000,
        chunk_overlap=200,
    )
except ChunkingError as e:
    logger.error(f"Chunking failed: {e}")
    return {"error": "Document processing failed"}
```

#### `EmbeddingError`

Raised when embedding generation fails.

**Inherits from:** `DocumentStorageError`

**When raised:**

- Embedding deployment not found
- Embedding API call fails
- Invalid embedding configuration

**Example:**

```python
from backend.services.document_storage import EmbeddingError

try:
    result = await service.upload_document(
        file_name="document.pdf",
        file_content=pdf_bytes,
        collection_id="col-uuid",
        embedding_deployment_id="invalid-deployment-id",
    )
except EmbeddingError as e:
    logger.error(f"Embedding error: {e}")
    return {"error": "Embedding generation failed. Check configuration."}
```

#### `FileStorageError`

Raised when file storage operations fail.

**Inherits from:** `DocumentStorageError`

**When raised:**

- Disk write fails (permissions, disk full)
- File path invalid
- File deletion fails

**Example:**

```python
from backend.services.document_storage import FileStorageError

try:
    file_id, file_path = storage_manager.save_file(
        file_name="document.pdf",
        file_content=pdf_bytes,
    )
except FileStorageError as e:
    logger.error(f"File storage error: {e}")
    return {"error": "Failed to save file. Contact administrator."}
```

#### `CollectionNotFoundError`

Raised when collection ID does not exist.

**Inherits from:** `DocumentStorageError`

**Attributes:**

- `collection_id: str` - The collection ID that was not found

**When raised:**

- Querying non-existent collection
- Uploading document to non-existent collection

**Example:**

```python
from backend.services.document_storage import CollectionNotFoundError

try:
    result = await service.upload_document(
        file_name="document.pdf",
        file_content=pdf_bytes,
        collection_id="non-existent-uuid",
    )
except CollectionNotFoundError as e:
    logger.error(f"Collection not found: {e.collection_id}")
    return {"error": f"Collection '{e.collection_id}' not found"}
```

#### `DocumentNotFoundError`

Raised when document ID does not exist.

**Inherits from:** `DocumentStorageError`

**Attributes:**

- `document_id: str` - The document ID that was not found

**When raised:**

- Querying non-existent document
- Updating or deleting non-existent document

**Example:**

```python
from backend.services.document_storage import DocumentNotFoundError

try:
    repository.update_document_status(
        document_id="non-existent-uuid",
        status="processed",
    )
except DocumentNotFoundError as e:
    logger.error(f"Document not found: {e.document_id}")
    return {"error": f"Document '{e.document_id}' not found"}
```

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.document_storage import (
    DocumentStorageService,
    DocumentStorageError,
    UnsupportedFileTypeError,
    EmbeddingError,
    CollectionNotFoundError,
)
import logging

logger = logging.getLogger(__name__)

async def upload_document_handler(
    file_name: str,
    file_content: bytes,
    collection_id: str,
):
    """Handle document upload with comprehensive error handling."""
    try:
        service = DocumentStorageService()

        result = await service.upload_document(
            file_name=file_name,
            file_content=file_content,
            collection_id=collection_id,
        )

        if not result.success:
            # Processing failed but file was saved
            logger.warning(
                f"Document {result.document.id} processing failed: "
                f"{result.message}"
            )
            return {
                "status": "partial",
                "document_id": result.document.id,
                "message": result.message,
            }

        return {
            "status": "success",
            "document_id": result.document.id,
            "chunks": len(result.chunks),
        }

    except UnsupportedFileTypeError as e:
        logger.error(f"Unsupported file type: {e.file_type}")
        return {
            "status": "error",
            "error": "unsupported_file_type",
            "message": f"File type '{e.file_type}' not supported",
            "supported_types": e.supported_types,
        }

    except CollectionNotFoundError as e:
        logger.error(f"Collection not found: {e.collection_id}")
        return {
            "status": "error",
            "error": "collection_not_found",
            "message": f"Collection '{e.collection_id}' not found",
        }

    except EmbeddingError as e:
        logger.error(f"Embedding generation failed: {e}")
        return {
            "status": "error",
            "error": "embedding_failed",
            "message": "Failed to generate embeddings. Check configuration.",
        }

    except DocumentStorageError as e:
        # Catch-all for other document storage errors
        logger.error(f"Document storage error: {e}")
        return {
            "status": "error",
            "error": "storage_error",
            "message": "Document operation failed",
        }

    except Exception as e:
        # Catch unexpected errors
        logger.exception(f"Unexpected error during document upload: {e}")
        return {
            "status": "error",
            "error": "unexpected_error",
            "message": "An unexpected error occurred",
        }
```

**Search Error Handling:**

```python
from backend.services.document_storage import (
    DocumentSearchService,
    EmbeddingError,
)

def search_documents_handler(collection_id: str, query: str):
    """Handle document search with error handling."""
    try:
        search_service = DocumentSearchService()

        results = search_service.hybrid_search(
            collection_id=collection_id,
            query=query,
            k=10,
        )

        return {"status": "success", "results": results}

    except EmbeddingError as e:
        logger.error(f"Embedding generation failed during search: {e}")
        # Fallback to text search
        logger.info("Falling back to text-only search")
        results = DocumentSearchService.text_search(
            collection_id=collection_id,
            query=query,
            k=10,
        )
        return {"status": "partial", "results": results, "note": "Using text search only"}

    except Exception as e:
        logger.exception(f"Search error: {e}")
        return {"status": "error", "error": str(e)}
```

## Integration Patterns

### Integration with API Layer

Document storage service is typically used in FastAPI routes for document upload, search, and management.

**Example API Route:**

```python
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from typing import List
from backend.services.document_storage import (
    DocumentStorageService,
    DocumentSearchService,
    create_document_storage_service,
    UnsupportedFileTypeError,
    CollectionNotFoundError,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

async def get_storage_service() -> DocumentStorageService:
    """Dependency for storage service."""
    return create_document_storage_service()

async def get_search_service() -> DocumentSearchService:
    """Dependency for search service."""
    from backend.services.document_storage import get_document_search_service
    return get_document_search_service()

@router.post("/upload")
async def upload_document(
    collection_id: str,
    file: UploadFile = File(...),
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    service: DocumentStorageService = Depends(get_storage_service),
):
    """Upload and process a document."""
    try:
        # Read file content
        file_content = await file.read()

        # Upload document
        result = await service.upload_document(
            file_name=file.filename,
            file_content=file_content,
            collection_id=collection_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if not result.success:
            raise HTTPException(status_code=500, detail=result.message)

        return {
            "document_id": result.document.id,
            "name": result.document.name,
            "status": result.document.status,
            "chunks": len(result.chunks),
        }

    except UnsupportedFileTypeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {e.file_type}. "
                   f"Supported: {', '.join(e.supported_types)}"
        )
    except CollectionNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Collection not found: {e.collection_id}")

@router.get("/collections/{collection_id}/documents")
async def list_documents(
    collection_id: str,
    service: DocumentStorageService = Depends(get_storage_service),
):
    """List documents in a collection."""
    documents = service.get_documents(collection_id=collection_id)
    return {"documents": documents}

@router.post("/search")
async def search_documents(
    collection_id: str,
    query: str,
    k: int = 5,
    search_type: str = "hybrid",
    service: DocumentSearchService = Depends(get_search_service),
):
    """Search documents."""
    if search_type == "hybrid":
        results = service.hybrid_search(
            collection_id=collection_id,
            query=query,
            k=k,
        )
    elif search_type == "vector":
        results = service.vector_search(
            collection_id=collection_id,
            query=query,
            k=k,
        )
    else:
        results = service.text_search(
            collection_id=collection_id,
            query=query,
            k=k,
        )

    return {"results": results}
```

### Integration with Other Services

**Integration with Tools Service (RAG Tools):**

The document_storage service integrates with the tools service to create document search tools for agents:

```python
# backend/tools/document_search/factory.py
from backend.services.document_storage.search_service import document_search_service
from langchain_core.tools import StructuredTool

def create_document_search_tool(
    collection_names: List[str],
    search_k: int = 5,
) -> StructuredTool:
    """Create document search tool for agents."""

    def search_documents_impl(query: str) -> str:
        """Search through configured documents."""
        # Use document_search_service singleton
        results = document_search_service.search_multiple_collections(
            collection_ids=collection_names,
            query=query,
            k=search_k,
            search_type="hybrid",
        )

        # Format results for agent
        formatted = []
        for result in results:
            formatted.append(
                f"[{result['metadata']['document_name']}] "
                f"{result['content']}"
            )

        return "\n\n".join(formatted)

    return StructuredTool(
        name="search_documents",
        description="Search through document knowledge base",
        func=search_documents_impl,
    )
```

**Integration with LLM Models Service:**

The document_storage service depends on the llm_models service for embedding deployment management:

```python
from backend.services.llm_models.embedding_factory import EmbeddingFactory

class EmbeddingManager:
    def __init__(self):
        self.embedding_factory = EmbeddingFactory()

    def get_embeddings(self, embedding_deployment_id: Optional[str] = None):
        if embedding_deployment_id:
            # Load from deployment database
            return self.embedding_factory.create_embedding_instance(
                embedding_deployment_id
            )
        else:
            # Use default from environment
            return self.embeddings
```

**Integration with Database Service:**

The document_storage service uses the database service for session management:

```python
from backend.services.database import get_db

class DocumentRepository:
    @staticmethod
    def get_documents(collection_id: Optional[str] = None):
        with get_db() as db:
            query = db.query(DocumentModel)
            if collection_id:
                query = query.filter(DocumentModel.collection_id == collection_id)
            return query.all()
```

### Dependency Flow

```
document_storage service
├── Depends on:
│   ├── database service (get_db session management)
│   ├── text_splitting service (TextSplitterFactory)
│   ├── llm_models service (EmbeddingFactory)
│   └── models (SQLAlchemy Document, DocumentChunk, DocumentCollection)
│
└── Used by:
    ├── tools service (create_document_search_tool)
    ├── API routes (document upload, search endpoints)
    └── agent service (RAG-enabled agents)
```

**Data Flow:**

1. API receives file upload
2. DocumentStorageService saves file → FileStorageManager
3. DocumentStorageService loads file → LoaderFactory → PDFLoader/DOCXLoader/etc.
4. DocumentStorageService chunks text → ChunkingService → text_splitting service
5. DocumentStorageService generates embeddings → EmbeddingManager → llm_models service
6. DocumentStorageService stores data → DocumentRepository → database service
7. Agent uses search tool → document_search_service → PostgreSQL pgvector

### Common Integration Patterns

#### Pattern 1: Document Upload with Collection Creation

```python
from backend.services.document_storage import DocumentStorageService

async def upload_to_user_knowledge_base(
    user_id: str,
    file_name: str,
    file_content: bytes,
):
    """Upload document to user's personal collection."""
    service = DocumentStorageService()

    # Get or create user collection
    collections = service.get_collections(user_id=user_id)
    if not collections:
        collection = service.create_collection(
            name=f"{user_id}'s Knowledge Base",
            description="Personal document collection",
            user_id=user_id,
        )
    else:
        collection = collections[0]

    # Upload document
    result = await service.upload_document(
        file_name=file_name,
        file_content=file_content,
        collection_id=collection.id,
    )

    return result
```

#### Pattern 2: RAG Tool Creation for Agent

```python
from backend.services.document_storage import DocumentSearchService
from langchain_core.tools import tool

def create_rag_tool_for_collections(collection_ids: List[str]):
    """Create RAG tool for specific collections."""
    search_service = DocumentSearchService()

    @tool
    def search_knowledge_base(query: str) -> str:
        """Search the knowledge base for relevant information.

        Args:
            query: The question or search query

        Returns:
            Relevant information from documents
        """
        results = search_service.search_multiple_collections(
            collection_ids=collection_ids,
            query=query,
            k=5,
            search_type="hybrid",
        )

        if not results:
            return "No relevant information found."

        # Format with citations
        formatted = []
        for i, result in enumerate(results, 1):
            meta = result['metadata']
            formatted.append(
                f"[{i}] {result['content']}\n"
                f"Source: {meta['document_name']}, "
                f"Page: {meta.get('page', 'N/A')}"
            )

        return "\n\n".join(formatted)

    return search_knowledge_base
```

#### Pattern 3: Bulk Document Import

```python
from pathlib import Path
from backend.services.document_storage import DocumentStorageService
import asyncio

async def bulk_import_directory(
    directory: Path,
    collection_id: str,
):
    """Import all supported documents from a directory."""
    service = DocumentStorageService()

    results = []
    for file_path in directory.iterdir():
        if service.allowed_file(file_path.name):
            with open(file_path, "rb") as f:
                file_content = f.read()

            result = await service.upload_document(
                file_name=file_path.name,
                file_content=file_content,
                collection_id=collection_id,
            )

            results.append({
                "file": file_path.name,
                "success": result.success,
                "document_id": result.document.id,
                "chunks": len(result.chunks),
            })

    return results
```

## Usage Examples

### Example 1: Basic Document Upload and Search

Complete end-to-end example of uploading a document and searching it:

```python
from backend.services.document_storage import (
    DocumentStorageService,
    DocumentSearchService,
)

async def basic_workflow():
    """Basic document upload and search workflow."""

    # Step 1: Create service instances
    storage_service = DocumentStorageService()
    search_service = DocumentSearchService()

    # Step 2: Create a collection
    collection = storage_service.create_collection(
        name="Product Documentation",
        description="Product manuals and guides",
    )
    print(f"Created collection: {collection.id}")

    # Step 3: Upload a document
    with open("user_manual.pdf", "rb") as f:
        file_content = f.read()

    result = await storage_service.upload_document(
        file_name="user_manual.pdf",
        file_content=file_content,
        collection_id=collection.id,
        chunk_size=1000,
        chunk_overlap=200,
        strategy="recursive",
    )

    if result.success:
        print(f"Document uploaded: {result.document.id}")
        print(f"Status: {result.document.status}")
        print(f"Chunks created: {len(result.chunks)}")
    else:
        print(f"Upload failed: {result.message}")
        return

    # Step 4: Search the document
    search_results = search_service.hybrid_search(
        collection_id=collection.id,
        query="How do I reset the password?",
        k=3,
    )

    # Step 5: Display results
    print(f"\nFound {len(search_results)} results:")
    for i, result in enumerate(search_results, 1):
        print(f"\n[{i}] Confidence: {result['score']:.3f}")
        print(f"Content: {result['content'][:200]}...")
        print(f"Document: {result['metadata']['document_name']}")
        print(f"Page: {result['metadata'].get('page', 'N/A')}")
```

### Example 2: Multi-Collection Search with Custom Embeddings

Advanced example showing custom embedding deployment and multi-collection search:

```python
from backend.services.document_storage import (
    DocumentStorageService,
    DocumentSearchService,
)

async def advanced_workflow():
    """Advanced workflow with custom embeddings and multi-collection search."""

    storage_service = DocumentStorageService()
    search_service = DocumentSearchService()

    # Create multiple collections
    collections = {
        "technical": storage_service.create_collection(
            name="Technical Docs",
            description="API and architecture documentation",
        ),
        "product": storage_service.create_collection(
            name="Product Guides",
            description="User manuals and guides",
        ),
        "legal": storage_service.create_collection(
            name="Legal Documents",
            description="Policies and terms",
        ),
    }

    # Upload documents with specific embedding deployment
    embedding_deployment_id = "deployment-uuid"  # From database

    documents = [
        ("api_reference.pdf", collections["technical"].id),
        ("user_guide.pdf", collections["product"].id),
        ("privacy_policy.pdf", collections["legal"].id),
    ]

    for file_name, collection_id in documents:
        with open(file_name, "rb") as f:
            file_content = f.read()

        result = await storage_service.upload_document(
            file_name=file_name,
            file_content=file_content,
            collection_id=collection_id,
            embedding_deployment_id=embedding_deployment_id,
            chunk_size=1200,  # Larger chunks
            chunk_overlap=300,
            strategy="recursive",
        )

        print(f"Uploaded {file_name}: {result.document.status}")

    # Search across multiple collections
    collection_ids = [col.id for col in collections.values()]

    results = search_service.search_multiple_collections(
        collection_ids=collection_ids,
        query="What are the API rate limits?",
        k=10,
        search_type="hybrid",
        alpha=0.6,  # Favour vector search
    )

    # Group results by collection
    results_by_collection = {}
    for result in results:
        col_id = result['metadata']['collection_id']
        if col_id not in results_by_collection:
            results_by_collection[col_id] = []
        results_by_collection[col_id].append(result)

    # Display grouped results
    for col_name, col_info in collections.items():
        col_results = results_by_collection.get(col_info.id, [])
        print(f"\n{col_name.upper()} ({len(col_results)} results):")
        for result in col_results:
            print(f"  - {result['metadata']['document_name']}: {result['score']:.3f}")
```

### Example 3: Complete RAG Workflow with Agent Tool

Show realistic usage in RAG-enabled agent context:

```python
from backend.services.document_storage import (
    DocumentStorageService,
    DocumentSearchService,
)
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI

async def rag_agent_workflow():
    """Complete RAG workflow with document search tool."""

    # Setup: Upload documents to knowledge base
    storage_service = DocumentStorageService()
    search_service = DocumentSearchService()

    # Create collection for company knowledge base
    kb_collection = storage_service.create_collection(
        name="Company Knowledge Base",
        description="Internal documentation and policies",
        user_id="admin",
    )

    # Upload multiple documents
    documents = [
        "employee_handbook.pdf",
        "it_policies.docx",
        "org_chart.xlsx",
    ]

    for doc_file in documents:
        with open(doc_file, "rb") as f:
            await storage_service.upload_document(
                file_name=doc_file,
                file_content=f.read(),
                collection_id=kb_collection.id,
            )

    # Create document search tool
    @tool
    def search_company_knowledge_base(query: str) -> str:
        """Search the company knowledge base for policies, procedures, and information.

        Args:
            query: The question or topic to search for

        Returns:
            Relevant information from company documents with citations
        """
        results = search_service.hybrid_search(
            collection_id=kb_collection.id,
            query=query,
            k=5,
            alpha=0.5,
        )

        if not results:
            return "No relevant information found in the knowledge base."

        # Format results with citations
        formatted_results = []
        for i, result in enumerate(results, 1):
            meta = result['metadata']
            quality = meta.get('search_quality', {})

            formatted_results.append(
                f"[{i}] (Confidence: {quality.get('confidence', result['score']):.2f})\n"
                f"{result['content']}\n\n"
                f"Source: {meta['document_name']}"
                + (f", Page {meta['page']}" if meta.get('page') else "")
            )

        return "\n\n---\n\n".join(formatted_results)

    # Create agent with tool
    llm = AzureChatOpenAI(
        deployment_name="gpt-4",
        temperature=0,
    )

    llm_with_tools = llm.bind_tools([search_company_knowledge_base])

    # Use agent to answer question
    user_question = "What is the remote work policy?"

    messages = [HumanMessage(content=user_question)]
    response = llm_with_tools.invoke(messages)

    # Check if agent wants to use tool
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        print(f"Agent calling tool: {tool_call['name']}")
        print(f"Query: {tool_call['args']['query']}")

        # Execute tool
        tool_result = search_company_knowledge_base.invoke(
            tool_call['args']
        )

        print(f"\nTool Results:\n{tool_result}")

        # Agent generates final answer based on tool results
        # (This would continue with tool result message and final response)

    print(f"\nAgent Response: {response.content}")
```

### Example 4: Testing and Validation

Show how to use the service in tests:

```python
import pytest
from pathlib import Path
from backend.services.document_storage import (
    DocumentStorageService,
    DocumentSearchService,
    UnsupportedFileTypeError,
)

@pytest.fixture
def storage_service(tmp_path):
    """Test storage service with temporary directory."""
    return DocumentStorageService(upload_dir=tmp_path / "documents")

@pytest.fixture
def search_service(storage_service):
    """Test search service."""
    return DocumentSearchService(storage_service=storage_service)

@pytest.fixture
async def uploaded_document(storage_service):
    """Fixture providing an uploaded test document."""
    # Create collection
    collection = storage_service.create_collection(name="Test Collection")

    # Create test PDF content
    test_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n%%EOF"

    # Upload
    result = await storage_service.upload_document(
        file_name="test.pdf",
        file_content=test_content,
        collection_id=collection.id,
    )

    return result

@pytest.mark.asyncio
async def test_document_upload_success(storage_service):
    """Test successful document upload."""
    collection = storage_service.create_collection(name="Test")

    result = await storage_service.upload_document(
        file_name="test.txt",
        file_content=b"Test content",
        collection_id=collection.id,
    )

    assert result.success is True
    assert result.document.status == "processed"
    assert len(result.chunks) > 0

@pytest.mark.asyncio
async def test_unsupported_file_type(storage_service):
    """Test unsupported file type raises exception."""
    collection = storage_service.create_collection(name="Test")

    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        await storage_service.upload_document(
            file_name="archive.zip",
            file_content=b"ZIP content",
            collection_id=collection.id,
        )

    assert exc_info.value.file_type == ".zip"
    assert ".pdf" in exc_info.value.supported_types

@pytest.mark.asyncio
async def test_hybrid_search(search_service, uploaded_document):
    """Test hybrid search returns results."""
    collection_id = uploaded_document.document.collection_id

    results = search_service.hybrid_search(
        collection_id=collection_id,
        query="test query",
        k=5,
    )

    assert isinstance(results, list)
    for result in results:
        assert 'content' in result
        assert 'score' in result
        assert 'metadata' in result
        assert 'search_quality' in result['metadata']

def test_loader_factory_supported_extensions():
    """Test loader factory returns correct extensions."""
    from backend.services.document_storage import LoaderFactory

    extensions = LoaderFactory.get_supported_extensions()

    assert ".pdf" in extensions
    assert ".docx" in extensions
    assert ".txt" in extensions
    assert ".csv" in extensions
    assert ".xlsx" in extensions
    assert ".zip" not in extensions

@pytest.mark.asyncio
async def test_document_deletion(storage_service, uploaded_document):
    """Test document deletion removes file and database record."""
    document_id = uploaded_document.document.id

    # Verify exists
    doc = storage_service.repository.get_document(document_id)
    assert doc is not None

    # Delete
    success = storage_service.delete_document(document_id)
    assert success is True

    # Verify deleted
    doc = storage_service.repository.get_document(document_id)
    assert doc is None
```

## Performance Considerations

### Performance Characteristics

**Upload Performance:**

- **File I/O:** O(1) disk write per file
- **Document Loading:** Varies by format (PDF parsing slower than text)
- **Chunking:** O(n) where n = document length
- **Embedding Generation:** O(n/batch_size) API calls where n = number of chunks
- **Database Operations:** O(n) inserts for chunks

**Search Performance:**

- **Vector Search:** O(log n) with pgvector IVFFLAT/HNSW index
- **Text Search:** O(log n) with PostgreSQL GIN index on tsvector
- **Hybrid Search:** 2x search cost + O(k) RRF fusion

**Memory Usage:**

- **Document Loading:** Loads entire document into memory
- **Chunking:** Processes documents in memory
- **Embedding:** Batches of 64 texts in memory
- **Search:** Retrieves k results, minimal memory

**Database:**

- **Embedding Storage:** ~1536 floats × 4 bytes = ~6KB per chunk (text-embedding-3-small)
- **Full Text Index:** Additional ~50-100% of text size
- **pgvector Index:** Additional ~10-20% of embedding size

### Optimisation Tips

#### Tip 1: Batch Upload Documents

**Problem:**

```python
# Inefficient: Upload one at a time
for file_name in file_list:
    with open(file_name, "rb") as f:
        await service.upload_document(
            file_name=file_name,
            file_content=f.read(),
            collection_id=collection_id,
        )
```

**Solution:**

```python
# Efficient: Use asyncio.gather for parallel uploads
import asyncio

async def upload_files(file_list, collection_id):
    tasks = []
    for file_name in file_list:
        with open(file_name, "rb") as f:
            file_content = f.read()

        task = service.upload_document(
            file_name=file_name,
            file_content=file_content,
            collection_id=collection_id,
        )
        tasks.append(task)

    # Upload in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

#### Tip 2: Adjust Chunk Size for Use Case

**Guideline:**

- **Short Q&A:** chunk_size=500, chunk_overlap=100 (precise answers)
- **General RAG:** chunk_size=1000, chunk_overlap=200 (default, balanced)
- **Long Context:** chunk_size=2000, chunk_overlap=400 (more context, fewer API calls)
- **Code/Structured:** chunk_size=1500, chunk_overlap=300 (preserve structure)

**Example:**

```python
# Optimise for short, precise answers
result = await service.upload_document(
    file_name="faq.txt",
    file_content=faq_content,
    collection_id=collection_id,
    chunk_size=500,
    chunk_overlap=100,
)

# Optimise for long-form content
result = await service.upload_document(
    file_name="report.pdf",
    file_content=report_content,
    collection_id=collection_id,
    chunk_size=2000,
    chunk_overlap=400,
)
```

#### Tip 3: Use Appropriate Search Type

**Guideline:**

- **Semantic similarity:** Use `vector_search()` for conceptual matching
- **Keyword matching:** Use `text_search()` for exact terms
- **Best of both:** Use `hybrid_search()` for most use cases

**Example:**

```python
# User asking conceptual question
results = search_service.vector_search(
    collection_id=collection_id,
    query="What is the company's approach to sustainability?",
    k=5,
)

# User searching for specific term
results = search_service.text_search(
    collection_id=collection_id,
    query="Form W-9",
    k=5,
)

# General search (recommended)
results = search_service.hybrid_search(
    collection_id=collection_id,
    query="employee benefits dental coverage",
    k=5,
)
```

#### Tip 4: Implement Result Caching

**Problem:**

```python
# Every search hits database
def search_handler(query: str):
    return search_service.hybrid_search(
        collection_id="static-docs",
        query=query,
        k=5,
    )
```

**Solution:**

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=128)
def cached_search(collection_id: str, query: str, k: int) -> str:
    """Cached search for common queries."""
    results = search_service.hybrid_search(
        collection_id=collection_id,
        query=query,
        k=k,
    )
    # Return serialised results
    return json.dumps(results)

def search_handler(query: str):
    # Check cache first
    cached = cached_search("static-docs", query, 5)
    return json.loads(cached)
```

#### Tip 5: Database Index Optimisation

**Ensure indexes are created:**

```sql
-- Vector similarity index (HNSW recommended for production)
CREATE INDEX idx_document_chunks_embedding ON document_chunks
USING hnsw (embedding vector_cosine_ops);

-- Full-text search index
CREATE INDEX idx_document_chunks_content_tsvector ON document_chunks
USING gin (to_tsvector('english', content));

-- Filtering indexes
CREATE INDEX idx_documents_collection_id ON documents (collection_id);
CREATE INDEX idx_document_chunks_document_id ON document_chunks (document_id);
```

### Async/Await Support

The main `upload_document()` method is async to support concurrent processing:

```python
import asyncio

async def concurrent_uploads():
    """Upload multiple documents concurrently."""
    service = DocumentStorageService()

    # Create upload tasks
    tasks = [
        service.upload_document(
            file_name=f"doc{i}.pdf",
            file_content=content,
            collection_id=collection_id,
        )
        for i, content in enumerate(document_contents)
    ]

    # Run concurrently
    results = await asyncio.gather(*tasks)

    successful = sum(1 for r in results if r.success)
    print(f"Uploaded {successful}/{len(results)} documents")
```

**Note:** Search operations are synchronous as they are typically fast (<100ms).

### Batch Operations

**Embedding Generation:**
Already optimised with `BatchEmbeddingProcessor` (batch_size=64).

**Bulk Chunk Retrieval:**

```python
# Get all chunks for multiple documents
document_ids = ["doc1", "doc2", "doc3"]

all_chunks = []
for doc_id in document_ids:
    chunks = DocumentSearchService.get_all_chunks_for_document(doc_id)
    all_chunks.extend(chunks)
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.document_storage import (
    DocumentStorageService,
    EmbeddingManager,
)

@pytest.fixture
def mock_embeddings():
    """Mock embeddings instance."""
    mock = Mock()
    mock.embed_query.return_value = [0.1] * 1536
    mock.embed_documents.return_value = [[0.1] * 1536, [0.2] * 1536]
    return mock

@pytest.fixture
def storage_service_with_mocks(tmp_path, mock_embeddings):
    """Storage service with mocked dependencies."""
    service = DocumentStorageService(upload_dir=tmp_path / "docs")

    # Mock embedding manager
    with patch.object(service.embedding_manager, 'get_embeddings', return_value=mock_embeddings):
        yield service

def test_allowed_file():
    """Test file extension validation."""
    assert DocumentStorageService.allowed_file("doc.pdf") is True
    assert DocumentStorageService.allowed_file("doc.docx") is True
    assert DocumentStorageService.allowed_file("doc.zip") is False

@patch('backend.services.document_storage.embeddings.manager.AzureOpenAIEmbeddings')
def test_embedding_manager_initialisation(mock_azure_embeddings):
    """Test embedding manager initialises correctly."""
    mock_instance = Mock()
    mock_instance.embed_query.return_value = [0.1] * 1536
    mock_azure_embeddings.return_value = mock_instance

    manager = EmbeddingManager()

    assert manager.embeddings is not None
```

### Mocking Dependencies

```python
@patch('backend.services.document_storage.service.LoaderFactory')
@patch('backend.services.document_storage.service.ChunkingService')
async def test_document_processing(mock_chunking, mock_loader_factory, storage_service_with_mocks):
    """Test document processing with mocked loader and chunking."""
    # Mock loader
    mock_loader = Mock()
    mock_loader.load.return_value = [
        Mock(page_content="Test content", metadata={"page": 0})
    ]
    mock_loader_factory.get_loader.return_value = mock_loader

    # Mock chunking
    mock_chunking.chunk_documents.return_value = (
        [Mock(page_content="Chunk 1", metadata={})],
        {"chunk_count": 1}
    )

    # Test processing
    chunks, metadata = storage_service_with_mocks.process_document(
        file_path="test.pdf",
        chunk_size=1000,
        chunk_overlap=200,
    )

    assert len(chunks) == 1
    assert metadata["chunk_count"] == 1
    mock_loader.load.assert_called_once()
```

### Integration Testing

```python
@pytest.mark.integration
async def test_full_upload_and_search_workflow(tmp_path):
    """Integration test with real database and embeddings."""
    # Setup
    service = DocumentStorageService(upload_dir=tmp_path / "docs")
    search_service = DocumentSearchService(storage_service=service)

    # Create collection
    collection = service.create_collection(name="Integration Test")

    # Upload document
    test_content = b"This is a test document about machine learning."
    result = await service.upload_document(
        file_name="test.txt",
        file_content=test_content,
        collection_id=collection.id,
    )

    assert result.success is True
    assert result.document.status == "processed"

    # Search
    results = search_service.hybrid_search(
        collection_id=collection.id,
        query="machine learning",
        k=5,
    )

    assert len(results) > 0
    assert "machine learning" in results[0]['content'].lower()

    # Cleanup
    service.delete_document(result.document.id)
    service.delete_collection(collection.id)
```

## Best Practices

### Do's

**Use hybrid search for general queries:**

```python
# Hybrid search works well for most use cases
results = search_service.hybrid_search(
    collection_id=collection_id,
    query=user_query,
    k=5,
    alpha=0.5,  # Balanced
)
```

**Validate file types before upload:**

```python
# Check file type early
if not DocumentStorageService.allowed_file(filename):
    return {"error": "Unsupported file type"}

result = await service.upload_document(...)
```

**Handle partial failures gracefully:**

```python
# Check UploadResult.success
result = await service.upload_document(...)

if not result.success:
    logger.warning(f"Processing failed: {result.message}")
    # File is saved but processing failed
    # Can retry processing later
    return {"status": "partial", "document_id": result.document.id}
```

**Use collections for multi-tenancy:**

```python
# Create per-user collections
user_collection = service.create_collection(
    name=f"{user.name}'s Documents",
    user_id=user.id,
)

# Filter by user_id
collections = service.get_collections(user_id=user.id)
```

**Include metadata in search results:**

```python
# Include metadata for citations
results = search_service.hybrid_search(
    collection_id=collection_id,
    query=query,
    k=5,
    include_metadata=True,  # Enable metadata
)

# Use metadata for citations
for result in results:
    print(f"Source: {result['metadata']['document_name']}")
    print(f"Page: {result['metadata'].get('page', 'N/A')}")
```

**Use appropriate chunk sizes:**

```python
# Adjust chunk size based on content type
if file_type == "code":
    chunk_size, overlap = 1500, 300  # Preserve code structure
elif file_type == "faq":
    chunk_size, overlap = 500, 100   # Short, precise chunks
else:
    chunk_size, overlap = 1000, 200  # Default
```

### Don'ts

**Don't ignore UploadResult.success flag:**

```python
# BAD: Assumes upload always succeeds
result = await service.upload_document(...)
document_id = result.document.id  # May have status="failed"

# GOOD: Check success flag
result = await service.upload_document(...)
if result.success:
    process_document(result.document.id)
else:
    handle_failure(result.message)
```

**Don't use text search for semantic queries:**

```python
# BAD: Text search for conceptual question
results = DocumentSearchService.text_search(
    collection_id=collection_id,
    query="What is the company's sustainability strategy?",  # Won't match well
    k=5,
)

# GOOD: Use vector or hybrid search
results = search_service.hybrid_search(
    collection_id=collection_id,
    query="What is the company's sustainability strategy?",
    k=5,
)
```

**Don't process large files synchronously in API routes:**

```python
# BAD: Blocks API thread
@router.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()  # May be 100MB+
    result = await service.upload_document(...)  # Takes 30+ seconds
    return result

# GOOD: Use background tasks
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    content = await file.read()

    # Process in background
    background_tasks.add_task(
        process_document_async,
        file.filename,
        content,
        collection_id,
    )

    return {"status": "processing", "message": "Document queued"}
```

**Don't forget to handle embedding errors:**

```python
# BAD: Assume embeddings always work
embeddings = service.get_embeddings(deployment_id)
vector = embeddings.embed_query(query)  # May fail

# GOOD: Handle embedding errors
try:
    embeddings = service.get_embeddings(deployment_id)
    if not embeddings:
        raise EmbeddingError("No embeddings available")
    vector = embeddings.embed_query(query)
except EmbeddingError as e:
    logger.error(f"Embedding error: {e}")
    # Fall back to text search
    results = DocumentSearchService.text_search(...)
```

**Don't create collections per document:**

```python
# BAD: Creates too many collections
for doc in documents:
    collection = service.create_collection(name=doc.name)  # Anti-pattern
    await service.upload_document(..., collection_id=collection.id)

# GOOD: Group documents logically
collection = service.create_collection(name="User Knowledge Base")
for doc in documents:
    await service.upload_document(..., collection_id=collection.id)
```

## Related Documentation

### Related Services

- [database service](./database.md) - Database session management and migrations
- [text_splitting service](./text_splitting.md) - Text chunking strategies
- [llm_models service](./llm_models.md) - Embedding deployment management

### Related API Modules

- [Tools API](../agents-guide/api/tools.md) - Document search tool creation

### Database Schema

- [Document Models](../models/document.md) - SQLAlchemy models for documents, chunks, collections

### External Documentation

- [LangChain Document Loaders](https://python.langchain.com/docs/modules/data_connection/document_loaders/) - Document
  loading concepts
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL vector similarity extension
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html) - Text search features

## Summary

The document_storage service provides a complete RAG (Retrieval-Augmented Generation) solution for the AgenticStudio
platform, handling the entire lifecycle of documents from upload through processing, embedding, and search. It supports
multiple document formats (PDF, DOCX, TXT, CSV, XLSX) through a factory pattern, implements intelligent text chunking
with page boundary tracking, generates vector embeddings with automatic fallback, and provides flexible search
capabilities including vector similarity, PostgreSQL full-text search, and hybrid search with Reciprocal Rank Fusion.

**Key Features:**

- Multi-format document loading (PDF, DOCX, TXT, CSV, XLSX)
- Intelligent text chunking with page tracking
- Vector embeddings with Azure/OpenAI support
- Hybrid search combining semantic and keyword matching
- Collection-based multi-tenancy
- Batch processing with retry logic
- Comprehensive error handling
- Integration with agent tools

**Primary Use Cases:**

- Building RAG-enabled chatbots and agents with document knowledge
- Semantic search over knowledge bases
- Document-grounded question answering
- Multi-document analysis and retrieval
- Context injection for LLM prompts

**When to Use This Service:**

- Need to add document knowledge to agents or chatbots
- Want semantic search over documents (not just keyword matching)
- Building a knowledge base or documentation search system
- Implementing context retrieval for RAG workflows
- Need to chunk and embed large documents efficiently
- Require multi-tenant document storage (collections per user/project)

The service is designed to be the primary document management and retrieval component for RAG workflows, providing
production-ready features including error handling, retry logic, batch processing, and flexible search strategies. It
integrates seamlessly with the tools service to create document search tools for agents, and with the llm_models service
for embedding deployment management.
