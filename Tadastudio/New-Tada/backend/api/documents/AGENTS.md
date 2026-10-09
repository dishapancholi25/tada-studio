# Documents API Module

## Overview

The Documents API module provides comprehensive document management and Retrieval-Augmented Generation (RAG)
capabilities for AgenticStudio. It enables users to upload documents, organise them into collections, and perform advanced
semantic search using vector embeddings and hybrid search techniques.

**Location:** [backend/api/documents/](../../backend/api/documents/)

**Base Path:** `/api/documents`

**Primary Responsibilities:**

- Document upload and storage with intelligent chunking
- Collection management for organising documents
- Vector-based semantic search with multiple search modes
- Hybrid search combining vector and keyword search
- Text splitting and chunking preview
- Document metadata and status tracking
- Integration with RAG workflows and agent tools

## Architecture

### Module Structure

```
backend/api/documents/
├── __init__.py           # Module exports (router, document_service)
└── router.py             # All API endpoints, models, and logic (490 lines)
```

**Simplified Architecture:**
Unlike the Graph API module, the Documents API uses a streamlined architecture where all routes, models, and business
logic are contained in a single `router.py` file. This approach is suitable for the module's focused responsibility
around document operations.

**Models Defined Inline:**

- `CollectionCreate` - Request model for creating collections
- `CollectionResponse` - Response model for collection data
- `DocumentResponse` - Response model for document data
- `SearchRequest` - Request model for search operations
- `ChunkPreviewRequest` - Request model for chunking preview

### Design Pattern

The Documents API follows a **direct service integration pattern**:

```
HTTP Request
    ↓
Route Handler (router.py)
    ↓
DocumentStorageService / DocumentSearchService
    ↓
Database (PostgreSQL + pgvector) / File Storage
```

**Benefits:**

- Simple, direct integration for focused domain
- Minimal layers for straightforward CRUD operations
- Services handle all complex logic (chunking, embeddings, search)
- Easy to understand and maintain

### Database Models

The module relies on three core database models:

**DocumentCollection** ([models/documents/collection.py](../../models/documents/collection.py)):

- User-owned collections for organising documents
- Cascade deletion to all documents
- Indexed by user_id for fast queries

**Document** ([models/documents/document.py](../../models/documents/document.py)):

- Document metadata and status tracking
- Full-text search support with PostgreSQL tsvector
- Relationships to chunks and collection

**DocumentChunk** ([models/documents/chunk.py](../../models/documents/chunk.py)):

- Individual text chunks with 3072-dimensional embeddings
- Vector similarity search using pgvector
- Metadata for source tracking and filtering

## Authentication & Authorisation

### Authentication

The Documents API has **mixed authentication requirements**:

**Authenticated Endpoints (Collection Management):**

```python
from ..auth.dependencies import get_current_user

@router.get("/collections")
async def list_collections(current_user: Dict[str, Any] = Depends(get_current_user)):
    user_id = get_user_id_from_claims(current_user)
    collections = document_service.get_collections(user_id=user_id)
    return collections
```

**Unauthenticated Endpoints (Document Operations):**

- Document upload, listing, deletion
- Document search
- Chunk preview

**Headers Injected by OAuth2-Proxy:**

- `X-Forwarded-User` - Username or email
- `X-Forwarded-Email` - User email
- `X-Forwarded-Preferred-Username` - Display name

### Authorisation

**User-Scoped Collections:**
Collections are strictly scoped to the authenticated user:

- Users can only see and manage their own collections
- Collection deletion verifies ownership before proceeding
- Document operations within collections inherit permissions

**Implementation:**

```python
async def delete_collection(
    collection_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    user_id = get_user_id_from_claims(current_user)

    # Verify ownership before deletion
    collections = document_service.get_collections(user_id=user_id)
    if not any(col.id == collection_id for col in collections):
        raise HTTPException(status_code=403, detail="Not authorised to delete this collection")

    success = document_service.delete_collection(collection_id)
    return {"message": "Collection deleted successfully"}
```

**Note:** Current document operations (upload, search) do not enforce authentication. This allows for flexible
integration but should be reviewed for production security requirements.

## API Endpoints

### Document Operations (4 endpoints)

#### `POST /api/documents/upload`

Upload multiple documents to a collection with automatic chunking and embedding generation.

**Authentication:** Optional (currently not enforced)

**Request Body (multipart/form-data):**

- `files` - List of files to upload (File[])
- `collection_id` - Target collection ID (string)
- `chunk_size` - Size of text chunks in characters (integer, default: 1000)
- `chunk_overlap` - Overlap between chunks in characters (integer, default: 200)
- `loader_mode` - Document loading mode (string, default: "single")
- `strategy` - Chunking strategy: "recursive", "character", "sentence" (string, default: "recursive")

**Supported File Types:**

- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- Plain text (`.txt`)
- CSV (`.csv`)
- Excel (`.xlsx`, `.xls`)

**Response:**

```json
{
  "message": "Processed 3 documents",
  "documents": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "name": "Product Requirements Document.pdf",
      "status": "processed",
      "chunk_count": 42,
      "error_message": null
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "name": "Meeting Notes.docx",
      "status": "processed",
      "chunk_count": 15,
      "error_message": null
    },
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "name": "Corrupted File.pdf",
      "status": "failed",
      "chunk_count": 0,
      "error_message": "Unable to parse PDF: File is encrypted or corrupted"
    }
  ]
}
```

**Use Cases:**

- Upload documentation for RAG-enabled chatbots
- Import knowledge base articles for semantic search
- Batch process multiple files at once
- Create searchable document repositories

**Behaviour:**

1. **File Validation:** Each file is checked against `ALLOWED_EXTENSIONS`
2. **Document Processing:** Files are processed using appropriate loaders (PDF, DOCX, etc.)
3. **Chunking:** Text is split into chunks using the specified strategy and parameters
4. **Embedding Generation:** Each chunk gets a 3072-dimensional embedding via OpenAI's text-embedding-3-large
5. **Database Storage:** Document metadata, chunks, and embeddings are stored in PostgreSQL
6. **Status Tracking:** Documents are marked as "processing", "processed", or "failed"
7. **Error Handling:** Failed documents don't block successful ones; all results are returned

**Validation:**

- File types must be in the allowed extensions list
- `chunk_size` must be between 100 and 8000 characters
- `chunk_overlap` must be less than `chunk_size`
- `collection_id` must reference an existing collection

**Chunking Strategies:**

**Recursive (default):**

- Splits on paragraph breaks, then sentences, then characters
- Best for general-purpose text documents
- Maintains natural language boundaries

**Character:**

- Fixed-size character splits
- Fast and simple
- Use for uniform text or when structure is less important

**Sentence:**

- Splits on sentence boundaries
- Maintains complete thoughts
- Good for question-answering use cases

**Performance:**

- Upload is an **asynchronous operation**
- Processing time scales with document size and number
- Typical processing: 5-10 seconds per MB for PDFs with OCR

**Example (Python):**

```python
import requests

files = [
    ('files', ('document1.pdf', open('document1.pdf', 'rb'), 'application/pdf')),
    ('files', ('document2.docx', open('document2.docx', 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'))
]

data = {
    'collection_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'chunk_size': 1500,
    'chunk_overlap': 300,
    'strategy': 'recursive'
}

response = requests.post('http://localhost:8000/api/documents/upload', files=files, data=data)
print(response.json())
```

**Example (JavaScript):**

```javascript
const formData = new FormData();
formData.append('files', fileInput.files[0]);
formData.append('files', fileInput.files[1]);
formData.append('collection_id', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890');
formData.append('chunk_size', '1500');
formData.append('chunk_overlap', '300');
formData.append('strategy', 'recursive');

const response = await fetch('http://localhost:8000/api/documents/upload', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result);
```

**Errors:**

- **400 Bad Request:** Invalid file type, invalid chunking parameters
- **404 Not Found:** Collection does not exist
- **500 Internal Server Error:** Processing failure, embedding service unavailable

---

#### `GET /api/documents/`

List documents with optional filtering by collection and status.

**Authentication:** Optional (currently not enforced)

**Query Parameters:**

- `collection_id` - Filter by collection ID (optional)
- `status` - Filter by status: "pending", "processing", "processed", "failed" (optional)

**Response:**

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "collection_id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
    "name": "Product Requirements Document.pdf",
    "type": "pdf",
    "size": 2457600,
    "status": "processed",
    "chunk_count": 42,
    "upload_date": "2025-10-15T14:23:45.123456Z",
    "error_message": null
  },
  {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "collection_id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
    "name": "Meeting Notes.docx",
    "type": "docx",
    "size": 184320,
    "status": "processed",
    "chunk_count": 15,
    "upload_date": "2025-10-16T09:15:22.987654Z",
    "error_message": null
  },
  {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "collection_id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
    "name": "Corrupted File.pdf",
    "type": "pdf",
    "size": 512000,
    "status": "failed",
    "chunk_count": 0,
    "upload_date": "2025-10-16T10:30:11.456789Z",
    "error_message": "Unable to parse PDF: File is encrypted or corrupted"
  }
]
```

**Use Cases:**

- View all documents across all collections
- Check processing status of recently uploaded documents
- Filter documents by collection for display in UI
- Identify failed uploads for retry

**Behaviour:**

- Returns all documents if no filters specified
- Filters are applied with AND logic
- Results are ordered by upload date (newest first)
- Empty array returned if no documents match

**Example (Python):**

```python
import requests

# List all documents
response = requests.get('http://localhost:8000/api/documents/')

# List documents in specific collection
response = requests.get('http://localhost:8000/api/documents/', params={
    'collection_id': 'c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0'
})

# List failed documents
response = requests.get('http://localhost:8000/api/documents/', params={
    'status': 'failed'
})

documents = response.json()
for doc in documents:
    print(f"{doc['name']}: {doc['status']} ({doc['chunk_count']} chunks)")
```

**Example (JavaScript):**

```javascript
// List documents in a collection
const collectionId = 'c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0';
const response = await fetch(`http://localhost:8000/api/documents/?collection_id=${collectionId}`);
const documents = await response.json();

documents.forEach(doc => {
  console.log(`${doc.name}: ${doc.status} (${doc.chunk_count} chunks)`);
});
```

**Performance:**

- **Fast endpoint:** Database query with optional indexes
- Typical response time: 10-50ms
- Scales well with thousands of documents

**Errors:**

- **500 Internal Server Error:** Database connection failure

---

#### `DELETE /api/documents/{document_id}`

Delete a document and all its associated chunks and embeddings.

**Authentication:** Optional (currently not enforced)

**Path Parameters:**

- `document_id` - UUID of document to delete

**Response:**

```json
{
  "message": "Document deleted successfully"
}
```

**Use Cases:**

- Remove outdated or incorrect documents
- Clean up failed uploads
- Free up storage space
- Remove sensitive documents from collection

**Behaviour:**

1. **Document Lookup:** Verifies document exists
2. **Cascade Deletion:** Automatically deletes all related chunks via database cascade
3. **File Deletion:** Removes document from filesystem storage
4. **Vector Cleanup:** Chunk embeddings are automatically removed with chunks

**Implementation Note:**
The endpoint relies on database cascade delete for chunk cleanup. This is efficient and ensures consistency, but means
document deletion may take longer for documents with many chunks.

**Example (Python):**

```python
import requests

document_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
response = requests.delete(f'http://localhost:8000/api/documents/{document_id}')

if response.status_code == 200:
    print("Document deleted successfully")
else:
    print(f"Error: {response.json()}")
```

**Example (JavaScript):**

```javascript
const documentId = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';
const response = await fetch(`http://localhost:8000/api/documents/${documentId}`, {
  method: 'DELETE'
});

const result = await response.json();
console.log(result.message);
```

**Performance:**

- **Fast endpoint:** Single database delete with cascade
- Typical response time: 20-100ms depending on chunk count
- Filesystem cleanup is synchronous

**Errors:**

- **404 Not Found:** Document ID does not exist
- **500 Internal Server Error:** Database error, filesystem error

---

#### `GET /api/documents/{document_id}/chunks`

Preview document chunks for testing and debugging purposes.

**Authentication:** Optional (currently not enforced)

**Path Parameters:**

- `document_id` - UUID of document

**Query Parameters:**

- `limit` - Maximum number of chunks to return (default: 10)

**Response:**

```json
{
  "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "message": "Chunk preview not yet implemented",
  "chunks": []
}
```

**Status:** This endpoint is currently a **placeholder** and returns an empty chunks array. The implementation is
planned for a future release.

**Planned Behaviour:**
When implemented, this endpoint will return chunk previews with:

- Chunk content (truncated if necessary)
- Chunk index and position
- Metadata (page numbers, source information)
- Embedding status

**Use Cases (Planned):**

- Debug chunking strategies
- Verify document processing quality
- Inspect chunk boundaries
- Validate metadata extraction

---

### Collection Operations (4 endpoints)

#### `GET /api/documents/collections`

List all document collections owned by the authenticated user.

**Authentication:** **Required** (OAuth2-Proxy)

**Response:**

```json
[
  {
    "id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
    "name": "Product Documentation",
    "description": "Technical documentation for all products",
    "created_at": "2025-09-01T10:00:00.000000Z",
    "updated_at": "2025-10-15T14:23:45.123456Z"
  },
  {
    "id": "d1e2f3a4-b5c6-d7e8-f9a0-b1c2d3e4f5a6",
    "name": "Meeting Notes Q4 2025",
    "description": "All meeting notes and summaries from Q4",
    "created_at": "2025-10-01T08:30:00.000000Z",
    "updated_at": "2025-10-16T09:15:22.987654Z"
  },
  {
    "id": "e2f3a4b5-c6d7-e8f9-a0b1-c2d3e4f5a6b7",
    "name": "Customer Support Knowledge Base",
    "description": null,
    "created_at": "2025-08-15T12:45:00.000000Z",
    "updated_at": null
  }
]
```

**Use Cases:**

- Display collection picker in UI
- Show user's document organisation
- Calculate storage usage per collection
- Navigate to collection details

**Behaviour:**

- Returns only collections owned by the authenticated user
- Collections are ordered by creation date (newest first)
- Empty array returned if user has no collections
- `updated_at` reflects last modification to collection or its documents

**Example (Python):**

```python
import requests

headers = {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com'
}

response = requests.get('http://localhost:8000/api/documents/collections', headers=headers)
collections = response.json()

for collection in collections:
    print(f"{collection['name']}: {collection['description'] or 'No description'}")
```

**Example (JavaScript):**

```javascript
const response = await fetch('http://localhost:8000/api/documents/collections', {
  headers: {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com'
  }
});

const collections = await response.json();
collections.forEach(col => {
  console.log(`${col.name}: ${col.description || 'No description'}`);
});
```

**Performance:**

- **Fast endpoint:** Simple indexed database query
- Typical response time: 10-30ms
- Scales well with hundreds of collections per user

**Errors:**

- **401 Unauthorized:** Missing or invalid authentication headers
- **500 Internal Server Error:** Database connection failure

---

#### `GET /api/documents/collections-with-documents`

List all collections with their nested documents for the authenticated user.

**Authentication:** **Required** (OAuth2-Proxy)

**Response:**

```json
[
  {
    "id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
    "name": "Product Documentation",
    "description": "Technical documentation for all products",
    "document_count": 12,
    "documents": [
      {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "name": "API Reference.pdf",
        "type": "pdf",
        "size": 3145728,
        "status": "processed",
        "chunk_count": 87,
        "upload_date": "2025-10-15T14:23:45.123456Z"
      },
      {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "name": "User Guide.docx",
        "type": "docx",
        "size": 524288,
        "status": "processed",
        "chunk_count": 34,
        "upload_date": "2025-10-14T11:20:15.654321Z"
      }
    ]
  },
  {
    "id": "d1e2f3a4-b5c6-d7e8-f9a0-b1c2d3e4f5a6",
    "name": "Meeting Notes Q4 2025",
    "description": "All meeting notes and summaries from Q4",
    "document_count": 8,
    "documents": [
      {
        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "name": "Product Roadmap Meeting.docx",
        "type": "docx",
        "size": 102400,
        "status": "processed",
        "chunk_count": 12,
        "upload_date": "2025-10-16T09:15:22.987654Z"
      }
    ]
  }
]
```

**Use Cases:**

- Display complete collection browser in UI
- Calculate total storage usage
- Export collection contents
- Batch operations on collection documents

**Behaviour:**

- Returns collections with nested document arrays
- Documents within each collection are ordered by upload date (newest first)
- `document_count` matches the length of the `documents` array
- Empty `documents` array for collections with no documents

**Performance:**

- **Medium endpoint:** N+1 query pattern (collection query + document query per collection)
- Typical response time: 50-200ms depending on collection count
- Consider caching for frequently accessed data

**Optimisation Note:**
This endpoint performs one query per collection to fetch documents. For users with many collections, consider using the
separate `/collections` and `/` endpoints instead.

**Example (Python):**

```python
import requests

headers = {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com'
}

response = requests.get('http://localhost:8000/api/documents/collections-with-documents', headers=headers)
collections = response.json()

for collection in collections:
    print(f"\n{collection['name']} ({collection['document_count']} documents):")
    for doc in collection['documents']:
        print(f"  - {doc['name']} ({doc['chunk_count']} chunks)")
```

**Example (JavaScript):**

```javascript
const response = await fetch('http://localhost:8000/api/documents/collections-with-documents', {
  headers: {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com'
  }
});

const collections = await response.json();
collections.forEach(col => {
  console.log(`\n${col.name} (${col.document_count} documents):`);
  col.documents.forEach(doc => {
    console.log(`  - ${doc.name} (${doc.chunk_count} chunks)`);
  });
});
```

**Errors:**

- **401 Unauthorized:** Missing or invalid authentication headers
- **500 Internal Server Error:** Database connection failure

---

#### `POST /api/documents/collections`

Create a new document collection for the authenticated user.

**Authentication:** **Required** (OAuth2-Proxy)

**Request Body:**

```json
{
  "name": "Product Documentation",
  "description": "Technical documentation for all products"
}
```

**Fields:**

- `name` - Collection name (required, unique)
- `description` - Collection description (optional)

**Response:**

```json
{
  "id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
  "name": "Product Documentation",
  "description": "Technical documentation for all products",
  "created_at": "2025-10-20T15:30:45.123456Z",
  "updated_at": null
}
```

**Use Cases:**

- Create new document repository for a project
- Organise documents by topic or department
- Set up RAG knowledge base for specific domain
- Prepare collection before bulk document upload

**Behaviour:**

- Collection is automatically associated with the authenticated user
- Collection names must be unique across the system
- `created_at` is set to current timestamp
- `updated_at` is null until first document is added or collection is modified

**Validation:**

- `name` is required and cannot be empty
- `name` must be unique (returns 500 if duplicate)
- `description` is optional and can be null or empty string

**Example (Python):**

```python
import requests

headers = {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com',
    'Content-Type': 'application/json'
}

data = {
    'name': 'Product Documentation',
    'description': 'Technical documentation for all products'
}

response = requests.post('http://localhost:8000/api/documents/collections',
                        headers=headers,
                        json=data)

collection = response.json()
print(f"Created collection: {collection['id']}")
```

**Example (JavaScript):**

```javascript
const response = await fetch('http://localhost:8000/api/documents/collections', {
  method: 'POST',
  headers: {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Product Documentation',
    description: 'Technical documentation for all products'
  })
});

const collection = await response.json();
console.log(`Created collection: ${collection.id}`);
```

**Performance:**

- **Fast endpoint:** Single database insert
- Typical response time: 10-30ms

**Errors:**

- **400 Bad Request:** Missing required field `name`, validation error
- **401 Unauthorized:** Missing or invalid authentication headers
- **500 Internal Server Error:** Duplicate collection name, database error

---

#### `DELETE /api/documents/collections/{collection_id}`

Delete a collection and all its documents with ownership verification.

**Authentication:** **Required** (OAuth2-Proxy)

**Path Parameters:**

- `collection_id` - UUID of collection to delete

**Response:**

```json
{
  "message": "Collection deleted successfully"
}
```

**Use Cases:**

- Remove entire document repository when no longer needed
- Clean up test collections
- Free up significant storage space
- Reorganise document structure

**Behaviour:**

1. **Ownership Verification:** Ensures authenticated user owns the collection
2. **Cascade Deletion:** Automatically deletes all documents in the collection
3. **Chunk Cleanup:** All document chunks and embeddings are removed via cascade
4. **File Deletion:** All document files are removed from filesystem

**Security:**
This endpoint enforces strict ownership checks. Users cannot delete collections they don't own, even if they know the
collection ID.

**Implementation:**

```python
# Verify ownership before deletion
collections = document_service.get_collections(user_id=user_id)
if not any(col.id == collection_id for col in collections):
    raise HTTPException(status_code=403, detail="Not authorised to delete this collection")
```

**Example (Python):**

```python
import requests

headers = {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com'
}

collection_id = 'c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0'
response = requests.delete(f'http://localhost:8000/api/documents/collections/{collection_id}',
                          headers=headers)

if response.status_code == 200:
    print("Collection deleted successfully")
elif response.status_code == 403:
    print("Error: You don't own this collection")
else:
    print(f"Error: {response.json()}")
```

**Example (JavaScript):**

```javascript
const collectionId = 'c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0';
const response = await fetch(`http://localhost:8000/api/documents/collections/${collectionId}`, {
  method: 'DELETE',
  headers: {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com'
  }
});

if (response.status_code === 200) {
  console.log("Collection deleted successfully");
} else if (response.status_code === 403) {
  console.log("Error: You don't own this collection");
} else {
  const error = await response.json();
  console.log(`Error: ${error.detail}`);
}
```

**Performance:**

- **Medium endpoint:** Multiple database operations with cascade
- Typical response time: 100-500ms depending on document count
- Large collections (100+ documents) may take several seconds

**Warning:**
This operation is **irreversible**. All documents, chunks, embeddings, and files will be permanently deleted.

**Errors:**

- **401 Unauthorized:** Missing or invalid authentication headers
- **403 Forbidden:** User does not own the collection
- **404 Not Found:** Collection ID does not exist
- **500 Internal Server Error:** Database error, filesystem error

---

### Search Operations (1 endpoint)

#### `POST /api/documents/search`

Advanced document search with multiple search modes: vector similarity, full-text keyword, and hybrid search combining
both.

**Authentication:** Optional (currently not enforced)

**Request Body:**

```json
{
  "query": "How do I configure authentication for the API?",
  "collection_ids": ["c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0"],
  "document_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
  "k": 5,
  "search_type": "hybrid",
  "include_metadata": true,
  "hybrid_enabled": true,
  "search_mode": "hybrid",
  "keyword_weight": 0.3,
  "rrf_k": 60,
  "text_config": "english"
}
```

**Fields:**

- `query` - Search query text (required)
- `collection_ids` - List of collection IDs to search (required)
- `document_ids` - Optional list of specific documents to search (optional)
- `k` - Number of results to return (default: 4)
- `search_type` - Search mode: "similarity", "text", "hybrid" (default: "similarity")
- `include_metadata` - Include chunk metadata in results (default: true)
- `hybrid_enabled` - Enable hybrid search (alternative to search_type) (default: false)
- `search_mode` - Alternative field for search mode (default: "vector")
- `keyword_weight` - Weight for keyword search in hybrid mode (0.0-1.0, default: 0.3)
- `rrf_k` - Reciprocal Rank Fusion constant for hybrid search (default: 60)
- `text_config` - PostgreSQL text search configuration (default: "english")

**Response:**

```json
{
  "query": "How do I configure authentication for the API?",
  "results": [
    {
      "content": "To configure authentication for the API, you need to set up OAuth2-Proxy with your identity provider. The API supports multiple authentication methods including Google OAuth, GitHub OAuth, and custom OIDC providers. Configure the following environment variables: OAUTH2_PROXY_CLIENT_ID, OAUTH2_PROXY_CLIENT_SECRET, and OAUTH2_PROXY_COOKIE_SECRET.",
      "score": 0.8734,
      "metadata": {
        "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "collection_id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
        "chunk_index": 12,
        "total_chunks": 87,
        "source": "API Reference.pdf",
        "file_type": "pdf",
        "page": 23
      }
    },
    {
      "content": "Authentication headers are automatically injected by OAuth2-Proxy when requests pass through the proxy. The following headers are available: X-Forwarded-User contains the username or email, X-Forwarded-Email contains the user's email address, and X-Forwarded-Preferred-Username contains the display name.",
      "score": 0.8521,
      "metadata": {
        "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "collection_id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
        "chunk_index": 13,
        "total_chunks": 87,
        "source": "API Reference.pdf",
        "file_type": "pdf",
        "page": 24
      }
    },
    {
      "content": "For development purposes, you can bypass authentication by setting DISABLE_AUTH=true in your environment variables. However, this should never be used in production as it exposes all endpoints without any security checks.",
      "score": 0.7893,
      "metadata": {
        "document_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "collection_id": "c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0",
        "chunk_index": 45,
        "total_chunks": 34,
        "source": "User Guide.docx",
        "file_type": "docx",
        "page": null
      }
    }
  ],
  "total_results": 3
}
```

**Use Cases:**

- RAG-enabled chatbots and question answering
- Semantic search across documentation
- Find relevant context for LLM prompts
- Compare vector vs keyword search effectiveness
- Implement hybrid search for best accuracy

**Search Modes:**

**1. Similarity Search (Vector):**

```json
{
  "query": "authentication configuration",
  "collection_ids": ["c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0"],
  "search_type": "similarity",
  "k": 5
}
```

- Uses OpenAI embeddings for semantic similarity
- Finds conceptually related content even with different wording
- Best for natural language questions
- Fast: O(log n) with HNSW index

**2. Text Search (Keyword):**

```json
{
  "query": "OAuth2 configuration variables",
  "collection_ids": ["c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0"],
  "search_type": "text",
  "k": 5,
  "text_config": "english"
}
```

- Uses PostgreSQL full-text search with tsvector
- Finds exact and stemmed keyword matches
- Best for specific terminology or code
- Supports multiple languages via `text_config`

**3. Hybrid Search (Vector + Keyword):**

```json
{
  "query": "OAuth2 authentication setup",
  "collection_ids": ["c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0"],
  "search_type": "hybrid",
  "k": 5,
  "keyword_weight": 0.3,
  "rrf_k": 60
}
```

- Combines vector and keyword search using Reciprocal Rank Fusion (RRF)
- Balances semantic understanding with exact term matching
- Best overall accuracy for most use cases
- `keyword_weight`: Higher values favour keyword matches (0.0 = pure vector, 1.0 = pure keyword)
- `rrf_k`: Constant for RRF algorithm (default 60 is standard)

**Behaviour:**

1. **Query Embedding:** Query is embedded using the same model as documents
2. **Multi-Collection Search:** Searches across all specified collections simultaneously
3. **Document Filtering:** Optional `document_ids` restricts search to specific documents
4. **Score Normalisation:** Scores are normalised to 0.0-1.0 range
5. **Result Ranking:** Results sorted by relevance score (highest first)
6. **Metadata Inclusion:** Full chunk metadata included when `include_metadata=true`

**Performance:**

- **Vector Search:** 10-50ms typical, scales logarithmically with HNSW index
- **Text Search:** 20-100ms typical, depends on text corpus size
- **Hybrid Search:** 30-150ms typical, runs both searches in parallel

**Reciprocal Rank Fusion (RRF):**
RRF combines rankings from multiple search methods without requiring score calibration:

```
RRF_score(chunk) = Σ 1 / (k + rank_i(chunk))
```

Where:

- `k` is the RRF constant (default: 60)
- `rank_i` is the rank from search method i
- Higher RRF scores indicate better relevance

**Example (Python):**

```python
import requests

# Simple vector search
search_request = {
    'query': 'How do I configure authentication?',
    'collection_ids': ['c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0'],
    'k': 5,
    'search_type': 'similarity'
}

response = requests.post('http://localhost:8000/api/documents/search', json=search_request)
results = response.json()

print(f"Found {results['total_results']} results:")
for result in results['results']:
    print(f"\nScore: {result['score']:.4f}")
    print(f"Source: {result['metadata']['source']} (page {result['metadata'].get('page', 'N/A')})")
    print(f"Content: {result['content'][:200]}...")
```

**Example (JavaScript) - Hybrid Search:**

```javascript
const searchRequest = {
  query: 'OAuth2 authentication setup',
  collection_ids: ['c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0'],
  search_type: 'hybrid',
  k: 5,
  keyword_weight: 0.3,
  include_metadata: true
};

const response = await fetch('http://localhost:8000/api/documents/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(searchRequest)
});

const results = await response.json();
console.log(`Found ${results.total_results} results:`);
results.results.forEach(result => {
  console.log(`\nScore: ${result.score.toFixed(4)}`);
  console.log(`Source: ${result.metadata.source}`);
  console.log(`Content: ${result.content.substring(0, 200)}...`);
});
```

**Advanced Use Case - RAG Pipeline:**

```python
import requests

def retrieve_context(query: str, collection_ids: list, k: int = 3) -> str:
    """Retrieve relevant context for RAG."""
    search_request = {
        'query': query,
        'collection_ids': collection_ids,
        'k': k,
        'search_type': 'hybrid',
        'keyword_weight': 0.3,
        'include_metadata': True
    }

    response = requests.post('http://localhost:8000/api/documents/search',
                            json=search_request)
    results = response.json()

    # Combine top results into context
    context_parts = []
    for i, result in enumerate(results['results'], 1):
        source = result['metadata']['source']
        page = result['metadata'].get('page', 'N/A')
        context_parts.append(f"[{i}] From {source} (page {page}):\n{result['content']}")

    return "\n\n".join(context_parts)

# Use in RAG workflow
query = "How do I configure OAuth2 authentication?"
context = retrieve_context(query, ['c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0'])

prompt = f"""Answer the following question using only the provided context.

Context:
{context}

Question: {query}

Answer:"""

# Send to LLM...
```

**Optimisation Tips:**

**For Speed:**

- Use `search_type="similarity"` (vector-only is fastest)
- Reduce `k` to minimum needed results
- Limit `collection_ids` to relevant collections only
- Consider caching frequently searched queries

**For Accuracy:**

- Use `search_type="hybrid"` with `keyword_weight=0.3`
- Increase `k` to 10-20 and filter programmatically
- Include `document_ids` to focus on relevant documents
- Tune `keyword_weight` based on query type (0.2 for natural language, 0.4 for technical terms)

**For Relevance:**

- Use smaller chunk sizes (500-1000 characters) for precise answers
- Use larger chunk sizes (1500-2000 characters) for broader context
- Adjust `chunk_overlap` to 20-30% of chunk size for continuity

**Errors:**

- **400 Bad Request:** Missing required fields, invalid parameters
- **500 Internal Server Error:** Embedding service failure, database error

---

### Utility Operations (1 endpoint)

#### `POST /api/documents/preview-chunks`

Preview how text will be chunked with given settings, including intelligent recommendations for optimal chunking
parameters.

**Authentication:** Optional (currently not enforced)

**Request Body:**

```json
{
  "text": "This is a long document that I want to preview chunking for. It contains multiple paragraphs and sections. The chunking preview will help me understand how the text will be split before actually uploading a document.",
  "strategy": "recursive",
  "chunk_size": 1000,
  "chunk_overlap": 200
}
```

**Fields:**

- `text` - Text to preview chunking for (required)
- `strategy` - Chunking strategy: "recursive", "character", "sentence", "auto" (default: "recursive")
- `chunk_size` - Desired chunk size in characters (default: 1000)
- `chunk_overlap` - Overlap between chunks in characters (default: 200)

**Response:**

```json
{
  "chunks": [
    {
      "index": 0,
      "content": "This is a long document that I want to preview chunking for. It contains multiple paragraphs and sections. The chunking preview will help me understand how the text will be split before actually uploading a document.",
      "length": 215,
      "start_position": 0,
      "has_overlap": false
    },
    {
      "index": 1,
      "content": "how the text will be split before actually uploading a document. This is the second chunk which demonstrates overlap between chunks. The overlap ensures continuity of context across chunk boundaries.",
      "length": 198,
      "start_position": 145,
      "has_overlap": true
    }
  ],
  "total_chunks": 2,
  "avg_chunk_size": 206.5,
  "recommendations": {
    "strategy": "recursive",
    "chunk_size": 1000,
    "chunk_overlap": 200
  }
}
```

**Use Cases:**

- Test chunking strategies before bulk document upload
- Optimise chunk parameters for specific document types
- Understand how overlap affects chunk boundaries
- Get intelligent recommendations for document characteristics
- Debug chunking issues

**Chunking Strategies:**

**Recursive (Default):**

- Splits on paragraph breaks (`\n\n`), then sentence breaks (`.`), then character boundaries
- Maintains natural language structure
- Best for general-purpose documents
- Recommended for: articles, reports, documentation

**Character:**

- Fixed-size splits at character boundaries
- Fast and predictable
- Ignores language structure
- Recommended for: structured data, logs, code

**Sentence:**

- Splits on sentence boundaries
- Maintains complete thoughts
- May create uneven chunk sizes
- Recommended for: Q&A pairs, conversational content

**Auto:**

- Analyzes text and recommends optimal strategy
- Considers document length, structure, and content type
- Provides intelligent parameter recommendations
- Recommended for: unknown document types, experimentation

**Auto Strategy Analysis:**
When `strategy="auto"`, the endpoint analyzes:

- **Document length:** Short vs long documents need different chunk sizes
- **Structural markers:** Presence of paragraphs, sections, lists
- **Sentence length:** Average sentence length affects optimal chunk size
- **Content type:** Technical vs narrative content

**Recommendations:**

```json
{
  "recommendations": {
    "strategy": "sentence",
    "chunk_size": 800,
    "chunk_overlap": 160,
    "reasoning": "Document has short, clear sentences ideal for sentence-based splitting. Reduced chunk size to maintain one topic per chunk."
  }
}
```

**Parameter Validation:**
The endpoint automatically validates and adjusts parameters:

- **chunk_size:** Constrained to 100-8000 characters
- **chunk_overlap:** Must be less than chunk_size
- **overlap ratio:** Typically 15-30% of chunk_size is optimal

**Behaviour:**

1. **Validation:** Parameters are validated and adjusted if needed
2. **Splitter Creation:** Text splitter is created with specified strategy
3. **Chunking:** Text is split into chunks
4. **Preview Limiting:** Only first 5 chunks returned (full count in `total_chunks`)
5. **Analysis:** Document is analyzed for recommendations
6. **Statistics:** Average chunk size and total chunks calculated

**Example (Python) - Test Chunking:**

```python
import requests

text = """
# Authentication Guide

This guide explains how to configure authentication for the AgenticStudio API.

## OAuth2 Configuration

OAuth2 is the recommended authentication method for production deployments.
Configure the following environment variables:

- OAUTH2_PROXY_CLIENT_ID: Your OAuth2 client ID
- OAUTH2_PROXY_CLIENT_SECRET: Your OAuth2 client secret
- OAUTH2_PROXY_COOKIE_SECRET: Random 32-byte secret for cookie encryption

## Supported Providers

AgenticStudio supports the following OAuth2 providers:
- Google OAuth
- GitHub OAuth
- Custom OIDC providers
"""

# Test recursive chunking
preview_request = {
    'text': text,
    'strategy': 'recursive',
    'chunk_size': 500,
    'chunk_overlap': 100
}

response = requests.post('http://localhost:8000/api/documents/preview-chunks',
                        json=preview_request)
result = response.json()

print(f"Total chunks: {result['total_chunks']}")
print(f"Average chunk size: {result['avg_chunk_size']:.1f} characters")
print(f"\nRecommendations:")
print(f"  Strategy: {result['recommendations']['strategy']}")
print(f"  Chunk size: {result['recommendations']['chunk_size']}")
print(f"  Overlap: {result['recommendations']['chunk_overlap']}")

print(f"\nFirst chunk preview:")
print(result['chunks'][0]['content'][:200] + "...")
```

**Example (JavaScript) - Compare Strategies:**

```javascript
const text = "Your long document text here...";

// Test multiple strategies
const strategies = ['recursive', 'character', 'sentence', 'auto'];

for (const strategy of strategies) {
  const response = await fetch('http://localhost:8000/api/documents/preview-chunks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: text,
      strategy: strategy,
      chunk_size: 1000,
      chunk_overlap: 200
    })
  });

  const result = await response.json();
  console.log(`\n${strategy.toUpperCase()} Strategy:`);
  console.log(`  Total chunks: ${result.total_chunks}`);
  console.log(`  Avg size: ${result.avg_chunk_size.toFixed(1)} chars`);
}
```

**Example (Python) - Auto Recommendations:**

```python
import requests

# Let the system recommend optimal settings
preview_request = {
    'text': your_document_text,
    'strategy': 'auto',
    'chunk_size': 1000,  # Initial suggestion
    'chunk_overlap': 200
}

response = requests.post('http://localhost:8000/api/documents/preview-chunks',
                        json=preview_request)
result = response.json()

# Use recommendations for actual upload
recommended_strategy = result['recommendations']['strategy']
recommended_size = result['recommendations']['chunk_size']
recommended_overlap = result['recommendations']['chunk_overlap']

print(f"Recommended settings:")
print(f"  Strategy: {recommended_strategy}")
print(f"  Chunk size: {recommended_size}")
print(f"  Overlap: {recommended_overlap}")

# Now upload with optimal settings
# ... upload logic here ...
```

**Performance:**

- **Fast endpoint:** Pure text processing, no database or embedding calls
- Typical response time: 10-50ms depending on text length
- Scales linearly with text length

**Optimisation Tips:**

- **For Q&A:** Use `strategy="sentence"` with `chunk_size=500-800`
- **For Context:** Use `strategy="recursive"` with `chunk_size=1500-2000`
- **For Code:** Use `strategy="character"` with `chunk_size=1000-1500`
- **Unknown Type:** Use `strategy="auto"` to get recommendations

**Errors:**

- **400 Bad Request:** Missing required field `text`, invalid parameters
- **500 Internal Server Error:** Text splitting failure

---

## Document Processing

### Supported File Types

AgenticStudio supports the following document formats:

| File Type      | Extensions      | Loader      | Notes                                                   |
|----------------|-----------------|-------------|---------------------------------------------------------|
| PDF            | `.pdf`          | PDFLoader   | Supports text extraction, OCR fallback for scanned PDFs |
| Microsoft Word | `.docx`         | DOCXLoader  | Extracts text and basic formatting                      |
| Plain Text     | `.txt`          | TextLoader  | Direct text loading, UTF-8 encoding                     |
| CSV            | `.csv`          | CSVLoader   | Each row treated as separate document chunk             |
| Excel          | `.xlsx`, `.xls` | ExcelLoader | Extracts text from all sheets                           |

**Extension Check:**
Files are validated using `DocumentStorageService.allowed_file()` which checks against the `ALLOWED_EXTENSIONS` list.

### Document Lifecycle

```
1. Upload → 2. Validation → 3. Loading → 4. Chunking → 5. Embedding → 6. Storage → 7. Search Ready
```

**States:**

- `pending`: Document uploaded, awaiting processing
- `processing`: Currently being chunked and embedded
- `processed`: Successfully processed and search-ready
- `failed`: Processing failed, see `error_message`

### Chunking Process

**1. Document Loading:**

```python
# PDFLoader example
loader = PDFLoader(file_path)
documents = loader.load()
```

**2. Text Extraction:**

- PDF: Uses PyPDF or OCR fallback (Tesseract)
- DOCX: Extracts text via python-docx
- TXT: Direct UTF-8 read
- CSV/Excel: Converts rows/cells to text

**3. Text Splitting:**

```python
from backend.services.text_splitting import TextSplitterFactory

splitter = TextSplitterFactory.create_splitter(
    strategy="recursive",
    chunk_size=1000,
    chunk_overlap=200
)

chunks = splitter.split_text(document_text)
```

**4. Metadata Extraction:**
Each chunk includes:

- `document_id`: Parent document UUID
- `collection_id`: Parent collection UUID
- `chunk_index`: Sequential position in document (0-based)
- `total_chunks`: Total number of chunks in document
- `source`: Original filename
- `file_type`: File extension (pdf, docx, etc.)
- `page`: Page number (PDF only)
- `page_start` / `page_end`: For chunks spanning pages

**5. Embedding Generation:**

```python
from backend.services.document_storage import EmbeddingManager

# Batch process chunks for efficiency
embeddings = await embedding_manager.embed_batch(chunk_texts)
```

- **Model:** OpenAI `text-embedding-3-large`
- **Dimensions:** 3072
- **Batch Size:** Configured via `EMBEDDING_BATCH_SIZE`
- **Rate Limiting:** Automatic retry with exponential backoff

**6. Database Storage:**

```sql
-- Chunks stored with embeddings
INSERT INTO document_chunks (
    document_id,
    chunk_index,
    content,
    embedding,
    chunk_metadata
) VALUES (...);

-- Embeddings indexed for fast similarity search
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

### Chunking Strategies Explained

#### Recursive Chunking

**How It Works:**

1. Try to split on double newlines (`\n\n`) for paragraphs
2. If chunks still too large, split on sentence boundaries (`.`, `!`, `?`)
3. If still too large, split on single newlines (`\n`)
4. Last resort: split on character boundaries

**Best For:**

- General prose and documentation
- Mixed content with paragraphs and sections
- Maintaining natural reading flow

**Example:**

```
Original: "Paragraph 1 with multiple sentences. More text here.\n\nParagraph 2 starts here."

Recursive Split (chunk_size=100):
Chunk 0: "Paragraph 1 with multiple sentences. More text here."
Chunk 1: "Paragraph 2 starts here."
```

#### Character Chunking

**How It Works:**

1. Split at exact character boundaries
2. No regard for word or sentence boundaries
3. Fast and predictable

**Best For:**

- Structured data (logs, code)
- When exact chunk sizes are critical
- Very large uniform documents

**Example:**

```
Original: "This is a long piece of text that needs to be split into fixed-size chunks."

Character Split (chunk_size=30):
Chunk 0: "This is a long piece of text "
Chunk 1: "that needs to be split into f"
Chunk 2: "ixed-size chunks."
```

#### Sentence Chunking

**How It Works:**

1. Split on sentence boundaries (`.`, `!`, `?`)
2. Combine sentences until reaching target chunk size
3. Never splits mid-sentence

**Best For:**

- Q&A content
- Conversational text
- When complete thoughts are critical

**Example:**

```
Original: "First sentence here. Second sentence is longer. Third sentence wraps it up."

Sentence Split (chunk_size=50):
Chunk 0: "First sentence here. Second sentence is longer."
Chunk 1: "Third sentence wraps it up."
```

### Embedding Process

**Model Details:**

- **Provider:** OpenAI
- **Model:** `text-embedding-3-large`
- **Dimensions:** 3072
- **Context Length:** 8191 tokens
- **Cost:** $0.13 per million tokens (as of October 2025)

**Batch Processing:**

```python
# Efficient batch embedding
chunks = ["chunk 1 text", "chunk 2 text", ...]
embeddings = await embedding_manager.embed_batch(chunks, batch_size=100)

# Individual chunks embedded in parallel batches
# Automatic retry on rate limiting
# Progress tracking for large batches
```

**Vector Storage:**

- **Database:** PostgreSQL with pgvector extension
- **Index Type:** HNSW (Hierarchical Navigable Small World)
- **Distance Metric:** Cosine similarity
- **Index Parameters:** `m=16, ef_construction=64` (optimised for accuracy)

**Search Performance:**

- **Cold Search:** ~50ms (no cache)
- **Warm Search:** ~10ms (with query cache)
- **Complexity:** O(log n) with HNSW index
- **Scalability:** Supports millions of vectors

### Error Handling in Processing

**Common Failures:**

**1. Unsupported File Type:**

```json
{
  "name": "document.xyz",
  "status": "failed",
  "error_message": "Unsupported file type: .xyz"
}
```

**2. Corrupted or Encrypted PDF:**

```json
{
  "name": "encrypted.pdf",
  "status": "failed",
  "error_message": "Unable to parse PDF: File is encrypted or corrupted"
}
```

**3. Embedding Service Failure:**

```json
{
  "name": "large-doc.pdf",
  "status": "failed",
  "error_message": "Embedding generation failed: Rate limit exceeded"
}
```

**4. OCR Failure:**

```json
{
  "name": "scanned.pdf",
  "status": "failed",
  "error_message": "OCR processing failed: Tesseract not installed"
}
```

**Retry Logic:**

- Embedding rate limits: Automatic exponential backoff (3 retries)
- OCR failures: Fall back to basic text extraction
- Corrupted files: Fail immediately, no retry
- Temporary failures: Retry once after 5 seconds

---

## Search Capabilities

### Vector Search (Semantic Similarity)

**How It Works:**

1. Query is embedded using same model as documents
2. Cosine similarity computed between query embedding and chunk embeddings
3. Top-k most similar chunks returned
4. Scores normalised to 0.0-1.0 range

**SQL Query:**

```sql
SELECT
    content,
    1 - (embedding <=> query_embedding) AS score,
    chunk_metadata
FROM document_chunks
WHERE document_id IN (
    SELECT id FROM documents WHERE collection_id = ANY(collection_ids)
)
ORDER BY embedding <=> query_embedding
LIMIT k;
```

**Advantages:**

- Finds semantically similar content regardless of exact wording
- Handles synonyms and related concepts
- Works across languages (with multilingual models)
- Fast with HNSW index

**Disadvantages:**

- May miss exact keyword matches
- Requires embedding generation for every query
- Less effective for very short queries

**Best For:**

- Natural language questions
- Conceptual searches
- Cross-domain information retrieval

### Text Search (Full-Text Keyword)

**How It Works:**

1. Query is parsed into search terms and stemmed
2. PostgreSQL tsvector matches against document full-text content
3. Relevance scored using TF-IDF
4. Results ranked by text search rank

**SQL Query:**

```sql
SELECT
    content,
    ts_rank(search_vector, query_tsquery) AS score,
    chunk_metadata
FROM document_chunks
JOIN documents ON documents.id = document_chunks.document_id
WHERE search_vector @@ query_tsquery
    AND collection_id = ANY(collection_ids)
ORDER BY score DESC
LIMIT k;
```

**Configuration Languages:**

- `english` (default): English stemming and stop words
- `simple`: No stemming, all languages
- `spanish`, `french`, `german`, etc.: Language-specific configurations

**Advantages:**

- Fast exact and stemmed keyword matching
- No embedding API calls required
- Handles technical terms and acronyms well
- Supports Boolean operators

**Disadvantages:**

- Requires exact or stemmed matches
- Doesn't understand semantic relationships
- Language-dependent

**Best For:**

- Searching for specific terms or phrases
- Technical documentation with domain-specific vocabulary
- Code search
- Exact quote searches

### Hybrid Search (RRF)

**How It Works:**

1. **Parallel Execution:** Vector and text searches run simultaneously
2. **Separate Rankings:** Each method produces ranked result list
3. **Reciprocal Rank Fusion:** Combines rankings using RRF algorithm
4. **Unified Results:** Final results sorted by combined RRF score

**RRF Algorithm:**

```python
def reciprocal_rank_fusion(rankings: List[List[Document]], k: int = 60) -> List[Document]:
    """
    Combine multiple rankings using Reciprocal Rank Fusion.

    Args:
        rankings: List of ranked document lists from different search methods
        k: RRF constant (default: 60)

    Returns:
        Combined ranked list
    """
    scores = {}

    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            if doc.id not in scores:
                scores[doc.id] = 0
            scores[doc.id] += 1 / (k + rank)

    # Sort by RRF score descending
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**RRF Score Calculation:**

```
For each chunk:
    vector_rank = position in vector search results (1-based)
    text_rank = position in text search results (1-based)

    rrf_score = 1/(k + vector_rank) + 1/(k + text_rank)

Where k = 60 (standard RRF constant)
```

**Example:**

```
Query: "OAuth2 authentication"

Vector Search Results:
1. Chunk A (OAuth2 setup guide) - vector_rank = 1
2. Chunk B (Security overview) - vector_rank = 2
3. Chunk C (API reference) - vector_rank = 3

Text Search Results:
1. Chunk C (exact match "OAuth2") - text_rank = 1
2. Chunk A (contains "authentication") - text_rank = 2
3. Chunk D (OAuth2 example) - text_rank = 3

RRF Scores (k=60):
Chunk A: 1/(60+1) + 1/(60+2) = 0.0164 + 0.0161 = 0.0325
Chunk C: 1/(60+3) + 1/(60+1) = 0.0159 + 0.0164 = 0.0323
Chunk B: 1/(60+2) + 0 = 0.0161
Chunk D: 0 + 1/(60+3) = 0.0159

Final Ranking:
1. Chunk A (combines both methods)
2. Chunk C (strong in text, decent in vector)
3. Chunk B (only in vector)
4. Chunk D (only in text)
```

**Tuning Parameters:**

**keyword_weight (0.0-1.0):**

- **0.0:** Pure vector search (semantic only)
- **0.3 (default):** Balanced hybrid favouring semantic
- **0.5:** Equal weight to both methods
- **0.7:** Favour keyword matches
- **1.0:** Pure keyword search

**rrf_k (default: 60):**

- **Lower values (20-40):** Top results matter more, less importance to lower ranks
- **Standard (60):** Balanced consideration of all ranks
- **Higher values (80-100):** More consideration to lower-ranked results

**Advantages:**

- Best of both worlds: semantic understanding + exact matching
- No score calibration required (unlike weighted averaging)
- Robust to differences in scoring scales
- Proven effective in research and production

**Disadvantages:**

- Slower than individual methods (runs both)
- More complex to understand and debug
- Requires tuning for specific use cases

**Best For:**

- General-purpose search where accuracy is critical
- Queries mixing natural language and technical terms
- When you're unsure which search method is better
- Production RAG systems

### Search Filtering

**By Collection:**

```json
{
  "query": "authentication",
  "collection_ids": ["c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0"],
  "k": 5
}
```

- Searches only within specified collections
- Multiple collections searched simultaneously
- Results can come from any specified collection

**By Document:**

```json
{
  "query": "authentication",
  "collection_ids": ["c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0"],
  "document_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
  "k": 5
}
```

- Further restricts search to specific documents
- Useful for document-specific Q&A
- Improves performance when document scope is known

**By Metadata:**
Currently not exposed via API, but can be filtered in application code:

```python
# After receiving search results
filtered = [
    result for result in results['results']
    if result['metadata'].get('file_type') == 'pdf'
]
```

### Search Performance Optimisation

**Index Optimisation:**

```sql
-- Vector index for fast similarity search
CREATE INDEX document_chunks_embedding_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX documents_search_vector_idx
ON documents
USING gin(search_vector);

-- Covering index for metadata queries
CREATE INDEX document_chunks_document_id_idx
ON document_chunks(document_id);
```

**Query Optimisation:**

**1. Limit Result Count:**

```json
{
  "query": "...",
  "k": 3  // Request only what you need
}
```

**2. Filter Early:**

```json
{
  "collection_ids": ["specific-collection"],  // Reduce search space
  "document_ids": ["specific-document"]       // Further narrow scope
}
```

**3. Choose Right Search Mode:**

- Vector search: 10-20ms
- Text search: 20-40ms
- Hybrid search: 30-60ms

**4. Batch Queries:**

```python
# Instead of multiple sequential searches
queries = ["query1", "query2", "query3"]
results = [search(q) for q in queries]

# Consider caching common queries
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query, collection_id):
    return search(query, collection_id)
```

**Embedding Cache:**
The system caches query embeddings to avoid redundant API calls:

```python
# First query: Generates embedding (~100ms)
search("How to configure auth?")

# Repeat query: Uses cached embedding (~10ms)
search("How to configure auth?")
```

---

## Error Handling

### Error Response Format

All API errors follow a consistent format:

```json
{
  "detail": "Human-readable error message"
}
```

**Standard FastAPI Error Structure:**

```json
{
  "detail": {
    "type": "validation_error",
    "errors": [
      {
        "loc": ["body", "name"],
        "msg": "field required",
        "type": "value_error.missing"
      }
    ]
  }
}
```

### Common Error Codes

#### 400 Bad Request

**Validation Errors:**

```json
{
  "detail": "Invalid chunking parameters: chunk_overlap must be less than chunk_size"
}
```

**Causes:**

- Missing required fields in request body
- Invalid parameter values (negative numbers, out of range)
- Invalid file type
- Malformed JSON

**Example Scenarios:**

- `chunk_size` less than 100 or greater than 8000
- `chunk_overlap` greater than `chunk_size`
- Empty `collection_ids` array in search request
- Invalid `search_type` value

---

#### 401 Unauthorized

```json
{
  "detail": "User not found"
}
```

**Causes:**

- Missing authentication headers (X-Forwarded-User, X-Forwarded-Email)
- Invalid user credentials in headers
- User not found in database

**Affected Endpoints:**

- `GET /collections`
- `GET /collections-with-documents`
- `POST /collections`
- `DELETE /collections/{collection_id}`

**Resolution:**
Ensure OAuth2-Proxy is properly configured and authentication headers are being forwarded.

---

#### 403 Forbidden

```json
{
  "detail": "Not authorised to delete this collection"
}
```

**Causes:**

- User attempting to access resource they don't own
- Insufficient permissions for operation

**Example Scenarios:**

- Deleting another user's collection
- Accessing shared collection without permission

---

#### 404 Not Found

```json
{
  "detail": "Document not found"
}
```

**Causes:**

- Document ID does not exist
- Collection ID does not exist
- Resource was previously deleted

**Affected Operations:**

- Document deletion
- Document retrieval
- Collection operations

---

#### 500 Internal Server Error

```json
{
  "detail": "Embedding generation failed: Rate limit exceeded"
}
```

**Causes:**

- Database connection failure
- Embedding service (OpenAI API) unavailable or rate limited
- Filesystem errors
- Unexpected processing errors
- Document parsing failures

**Common Scenarios:**

**Embedding Service Failures:**

```json
{
  "detail": "Embedding generation failed: Invalid API key"
}
```

**Database Errors:**

```json
{
  "detail": "Database error: Connection timeout"
}
```

**File Processing:**

```json
{
  "detail": "Unable to parse PDF: File is encrypted or corrupted"
}
```

**Duplicate Collection:**

```json
{
  "detail": "Collection name already exists"
}
```

---

### Error Handling Examples

**Python Error Handling:**

```python
import requests
from requests.exceptions import RequestException

def upload_document_safe(file_path: str, collection_id: str):
    """Upload document with comprehensive error handling."""
    try:
        with open(file_path, 'rb') as f:
            files = {'files': (file_path, f)}
            data = {'collection_id': collection_id}

            response = requests.post(
                'http://localhost:8000/api/documents/upload',
                files=files,
                data=data,
                timeout=300  # 5 minute timeout for large files
            )
            response.raise_for_status()

            result = response.json()
            for doc in result['documents']:
                if doc['status'] == 'failed':
                    print(f"❌ {doc['name']}: {doc['error_message']}")
                else:
                    print(f"✅ {doc['name']}: {doc['chunk_count']} chunks")

            return result

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return None

    except requests.exceptions.Timeout:
        print("Error: Upload timed out. File may be too large.")
        return None

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            print(f"Error: Invalid request - {e.response.json()['detail']}")
        elif e.response.status_code == 404:
            print(f"Error: Collection not found: {collection_id}")
        elif e.response.status_code == 500:
            print(f"Error: Server error - {e.response.json()['detail']}")
        else:
            print(f"Error: HTTP {e.response.status_code}")
        return None

    except RequestException as e:
        print(f"Error: Network error - {str(e)}")
        return None

# Usage
result = upload_document_safe('document.pdf', 'my-collection-id')
```

**JavaScript Error Handling:**

```javascript
async function searchDocuments(query, collectionIds) {
  try {
    const response = await fetch('http://localhost:8000/api/documents/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        collection_ids: collectionIds,
        search_type: 'hybrid',
        k: 5
      })
    });

    if (!response.ok) {
      const error = await response.json();

      switch (response.status) {
        case 400:
          throw new Error(`Invalid request: ${error.detail}`);
        case 500:
          throw new Error(`Server error: ${error.detail}`);
        default:
          throw new Error(`HTTP ${response.status}: ${error.detail}`);
      }
    }

    const results = await response.json();

    if (results.total_results === 0) {
      console.log('No results found. Try:');
      console.log('  - Using different search terms');
      console.log('  - Trying hybrid search mode');
      console.log('  - Expanding to more collections');
      return [];
    }

    return results.results;

  } catch (error) {
    if (error.name === 'TypeError') {
      console.error('Network error: Unable to reach server');
    } else {
      console.error(`Search failed: ${error.message}`);
    }
    return [];
  }
}

// Usage with error handling
const results = await searchDocuments('authentication', ['collection-id']);
if (results.length > 0) {
  console.log(`Found ${results.length} results`);
  results.forEach(r => console.log(`  - ${r.metadata.source}: ${r.score.toFixed(4)}`));
}
```

**Retry Logic Example:**

```python
import time
from typing import Optional

def search_with_retry(
    query: str,
    collection_ids: list,
    max_retries: int = 3,
    backoff_factor: float = 2.0
) -> Optional[dict]:
    """Search with exponential backoff retry."""

    for attempt in range(max_retries):
        try:
            response = requests.post(
                'http://localhost:8000/api/documents/search',
                json={
                    'query': query,
                    'collection_ids': collection_ids,
                    'search_type': 'hybrid',
                    'k': 5
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                print(f"Timeout on attempt {attempt + 1}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Search failed.")
                return None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 500:
                if attempt < max_retries - 1:
                    wait_time = backoff_factor ** attempt
                    print(f"Server error on attempt {attempt + 1}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print("Max retries reached. Server error persists.")
                    return None
            else:
                # Don't retry on 4xx errors
                print(f"Client error: {e.response.json()['detail']}")
                return None

    return None

# Usage
results = search_with_retry('authentication', ['collection-id'])
```

---

## Integration with Services Layer

### Dependency Flow

```
API Route (router.py)
    ↓
DocumentStorageService
    ├── CollectionService → CollectionRepository → Database
    ├── DocumentRepository → Database + FileStorage
    ├── ChunkingService → TextSplitterFactory
    ├── EmbeddingManager → OpenAI API
    └── LoaderFactory → PDF/DOCX/Text Loaders

API Route (router.py)
    ↓
DocumentSearchService
    ├── VectorStore (pgvector) → PostgreSQL
    ├── EmbeddingManager → OpenAI API
    └── SearchAlgorithms → RRF, Similarity, Text Search
```

### Services Used

#### DocumentStorageService

**Location:** [backend/services/document_storage/service.py](../../services/document_storage/service.py)

**Responsibilities:**

- Document upload and storage orchestration
- Collection management
- File system operations
- Status tracking and error handling
- Coordination between chunking, embedding, and storage

**Key Methods:**

```python
class DocumentStorageService:
    async def upload_document(
        self,
        file_name: str,
        file_content: bytes,
        collection_id: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        loader_mode: str = "single",
        strategy: str = "recursive"
    ) -> DocumentInfo:
        """Upload and process a document."""

    def get_documents(
        self,
        collection_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Document]:
        """Retrieve documents with optional filtering."""

    def delete_document(self, document_id: str) -> bool:
        """Delete document and associated files."""

    def get_collections(self, user_id: Optional[str] = None) -> List[DocumentCollection]:
        """List collections for user."""

    def create_collection(
        self,
        name: str,
        description: Optional[str],
        user_id: str
    ) -> DocumentCollection:
        """Create new collection."""

    def delete_collection(self, collection_id: str) -> bool:
        """Delete collection and all documents."""
```

**Usage in API:**

```python
from backend.services.document_storage import DocumentStorageService

document_service = DocumentStorageService()

@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    collection_id: str = Form(...)
):
    for file in files:
        content = await file.read()
        document = await document_service.upload_document(
            file_name=file.filename,
            file_content=content,
            collection_id=collection_id
        )
```

---

#### DocumentSearchService

**Location:
** [backend/services/document_storage/search_service.py](../../services/document_storage/search_service.py)

**Responsibilities:**

- Multi-modal search (vector, text, hybrid)
- Query embedding generation
- Result ranking and filtering
- RRF algorithm implementation
- Search performance optimisation

**Key Methods:**

```python
class DocumentSearchService:
    def search_multiple_collections(
        self,
        collection_ids: List[str],
        query: str,
        k: int = 4,
        search_type: str = "similarity",
        document_ids: Optional[List[str]] = None,
        alpha: float = 0.5,
        include_metadata: bool = True
    ) -> List[Dict]:
        """Search across multiple collections."""

    def _vector_search(
        self,
        query: str,
        collection_ids: List[str],
        k: int
    ) -> List[Dict]:
        """Perform vector similarity search."""

    def _text_search(
        self,
        query: str,
        collection_ids: List[str],
        k: int,
        text_config: str = "english"
    ) -> List[Dict]:
        """Perform full-text keyword search."""

    def _hybrid_search(
        self,
        query: str,
        collection_ids: List[str],
        k: int,
        alpha: float = 0.5
    ) -> List[Dict]:
        """Perform hybrid search with RRF."""
```

**Usage in API:**

```python
from backend.services.document_storage import document_search_service

@router.post("/search")
async def search_documents(search_request: SearchRequest):
    results = document_search_service.search_multiple_collections(
        collection_ids=search_request.collection_ids,
        query=search_request.query,
        k=search_request.k,
        search_type=search_request.search_type
    )

    return {
        "query": search_request.query,
        "results": results,
        "total_results": len(results)
    }
```

---

#### ChunkingOptimizer & TextSplitterFactory

**Location:** [backend/services/text_splitting/](../../backend/services/text_splitting/)

**Responsibilities:**

- Text splitting strategy selection
- Chunk parameter validation and optimisation
- Document analysis for recommendations
- Strategy-specific splitter creation

**Key Methods:**

```python
class ChunkingOptimizer:
    @staticmethod
    def validate_parameters(
        chunk_size: int,
        chunk_overlap: int
    ) -> Tuple[int, int]:
        """Validate and adjust chunking parameters."""

    @staticmethod
    def analyze_document(text: str) -> Dict[str, Any]:
        """Analyze document and recommend optimal chunking."""

class TextSplitterFactory:
    @staticmethod
    def create_splitter(
        strategy: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> TextSplitter:
        """Create text splitter for strategy."""
```

**Usage in API:**

```python
from backend.services.text_splitting import ChunkingOptimizer, TextSplitterFactory

@router.post("/preview-chunks")
async def preview_chunks(request: ChunkPreviewRequest):
    # Validate parameters
    chunk_size, chunk_overlap = ChunkingOptimizer.validate_parameters(
        request.chunk_size,
        request.chunk_overlap
    )

    # Create splitter
    splitter = TextSplitterFactory.create_splitter(
        strategy=request.strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    # Split and analyze
    chunks = splitter.split_text(request.text)
    analysis = ChunkingOptimizer.analyze_document(request.text)

    return {
        "chunks": chunks[:5],
        "total_chunks": len(chunks),
        "recommendations": analysis
    }
```

---

### Example Integration: Complete Upload Flow

```python
# Full document upload integration flow

# 1. API Route receives request
@router.post("/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    collection_id: str = Form(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    strategy: str = Form("recursive")
):
    uploaded_documents = []

    for file in files:
        # 2. Read file content
        content = await file.read()

        try:
            # 3. Call DocumentStorageService
            document = await document_service.upload_document(
                file_name=file.filename,
                file_content=content,
                collection_id=collection_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy=strategy
            )

            # Inside document_service.upload_document():
            # 4. LoaderFactory creates appropriate loader
            loader = LoaderFactory.get_loader(file_name)

            # 5. Loader extracts text
            text = loader.load(content)

            # 6. Save file to filesystem
            storage_path = file_storage.save(file_name, content)

            # 7. Create document record in database
            doc_record = document_repository.create(
                name=file_name,
                collection_id=collection_id,
                storage_path=storage_path,
                status="processing"
            )

            # 8. TextSplitterFactory creates splitter
            splitter = TextSplitterFactory.create_splitter(
                strategy=strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            # 9. Split text into chunks
            chunks = chunking_service.chunk_document(
                text=text,
                splitter=splitter,
                document_id=doc_record.id
            )

            # 10. Generate embeddings in batches
            embeddings = await embedding_manager.embed_batch(
                [chunk.content for chunk in chunks]
            )

            # 11. Save chunks with embeddings to database
            for chunk, embedding in zip(chunks, embeddings):
                chunk_repository.create(
                    document_id=doc_record.id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=embedding,
                    metadata=chunk.metadata
                )

            # 12. Update document status
            document_repository.update(
                doc_record.id,
                status="processed",
                chunk_count=len(chunks)
            )

            uploaded_documents.append({
                "id": str(document.id),
                "name": document.name,
                "status": "processed",
                "chunk_count": len(chunks)
            })

        except Exception as e:
            # Error handling
            logger.error(f"Error processing {file.filename}: {str(e)}")
            uploaded_documents.append({
                "name": file.filename,
                "status": "failed",
                "error_message": str(e)
            })

    return {
        "message": f"Processed {len(uploaded_documents)} documents",
        "documents": uploaded_documents
    }
```

---

## Usage Examples

### Complete RAG Workflow Example

**Scenario:** Build a documentation Q&A system with semantic search.

**Step 1: Create Collection**

```python
import requests

# API configuration
BASE_URL = "http://localhost:8000"
headers = {
    'X-Forwarded-User': 'user@example.com',
    'X-Forwarded-Email': 'user@example.com'
}

# Create collection for API documentation
collection_data = {
    'name': 'API Documentation',
    'description': 'Technical documentation for AgenticStudio API'
}

response = requests.post(
    f'{BASE_URL}/api/documents/collections',
    headers=headers,
    json=collection_data
)

collection = response.json()
collection_id = collection['id']
print(f"Created collection: {collection_id}")
```

**Step 2: Upload Documents**

```python
import os
from pathlib import Path

# Upload all PDF documentation files
docs_dir = Path('./documentation')
doc_files = list(docs_dir.glob('*.pdf'))

for doc_path in doc_files:
    with open(doc_path, 'rb') as f:
        files = {'files': (doc_path.name, f, 'application/pdf')}
        data = {
            'collection_id': collection_id,
            'chunk_size': 1500,
            'chunk_overlap': 300,
            'strategy': 'recursive'
        }

        response = requests.post(
            f'{BASE_URL}/api/documents/upload',
            files=files,
            data=data
        )

        result = response.json()
        for doc in result['documents']:
            if doc['status'] == 'processed':
                print(f"✅ Uploaded {doc['name']}: {doc['chunk_count']} chunks")
            else:
                print(f"❌ Failed {doc['name']}: {doc['error_message']}")

print(f"\nUploaded {len(doc_files)} documents")
```

**Step 3: List Documents**

```python
# Verify all documents uploaded successfully
response = requests.get(
    f'{BASE_URL}/api/documents/',
    params={'collection_id': collection_id}
)

documents = response.json()
total_chunks = sum(doc['chunk_count'] for doc in documents)

print(f"\nCollection contains {len(documents)} documents with {total_chunks} total chunks")
for doc in documents:
    print(f"  - {doc['name']}: {doc['status']} ({doc['chunk_count']} chunks)")
```

**Step 4: Implement Search Function**

```python
def search_documentation(query: str, collection_id: str, k: int = 5) -> list:
    """Search documentation using hybrid search."""

    search_request = {
        'query': query,
        'collection_ids': [collection_id],
        'k': k,
        'search_type': 'hybrid',
        'keyword_weight': 0.3,
        'include_metadata': True
    }

    response = requests.post(
        f'{BASE_URL}/api/documents/search',
        json=search_request
    )

    results = response.json()
    return results['results']
```

**Step 5: Build Q&A Function**

```python
from openai import OpenAI

openai_client = OpenAI()

def answer_question(question: str, collection_id: str) -> str:
    """Answer question using RAG with documentation."""

    # Retrieve relevant context
    search_results = search_documentation(question, collection_id, k=3)

    if not search_results:
        return "I couldn't find relevant information to answer your question."

    # Build context from search results
    context_parts = []
    for i, result in enumerate(search_results, 1):
        source = result['metadata']['source']
        page = result['metadata'].get('page', 'N/A')
        score = result['score']
        content = result['content']

        context_parts.append(
            f"[Source {i}: {source}, Page {page}, Relevance: {score:.2f}]\n{content}"
        )

    context = "\n\n".join(context_parts)

    # Create prompt for LLM
    prompt = f"""You are a helpful documentation assistant. Answer the user's question using ONLY the provided context. If the context doesn't contain enough information, say so.

Context from documentation:
{context}

User question: {question}

Answer:"""

    # Get answer from LLM
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful documentation assistant. Always cite sources when answering."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    answer = response.choices[0].message.content

    # Add sources
    sources_text = "\n\nSources:\n" + "\n".join([
        f"- {r['metadata']['source']} (page {r['metadata'].get('page', 'N/A')})"
        for r in search_results
    ])

    return answer + sources_text
```

**Step 6: Use Q&A System**

```python
# Ask questions about the documentation
questions = [
    "How do I configure OAuth2 authentication?",
    "What are the available search modes in the Documents API?",
    "How do I optimise chunk sizes for better search results?"
]

for question in questions:
    print(f"\n{'='*80}")
    print(f"Q: {question}")
    print(f"{'='*80}")

    answer = answer_question(question, collection_id)
    print(f"\nA: {answer}\n")
```

**Complete Example Output:**

```
Created collection: c0ff33c0-ff33-c0ff-33c0-ff33c0ff33c0

✅ Uploaded API_Reference.pdf: 87 chunks
✅ Uploaded User_Guide.pdf: 34 chunks
✅ Uploaded Authentication_Guide.pdf: 23 chunks

Uploaded 3 documents

Collection contains 3 documents with 144 total chunks
  - API_Reference.pdf: processed (87 chunks)
  - User_Guide.pdf: processed (34 chunks)
  - Authentication_Guide.pdf: processed (23 chunks)

================================================================================
Q: How do I configure OAuth2 authentication?
================================================================================

A: To configure OAuth2 authentication for AgenticStudio, you need to set up OAuth2-Proxy with your identity provider. Here are the steps:

1. Set the following environment variables:
   - OAUTH2_PROXY_CLIENT_ID: Your OAuth2 client ID from your provider
   - OAUTH2_PROXY_CLIENT_SECRET: Your OAuth2 client secret
   - OAUTH2_PROXY_COOKIE_SECRET: A random 32-byte secret for cookie encryption

2. AgenticStudio supports multiple OAuth2 providers including:
   - Google OAuth
   - GitHub OAuth
   - Custom OIDC providers

3. Authentication headers are automatically injected by OAuth2-Proxy:
   - X-Forwarded-User: Contains username or email
   - X-Forwarded-Email: Contains user's email address
   - X-Forwarded-Preferred-Username: Contains display name

For development purposes, you can bypass authentication by setting DISABLE_AUTH=true, but this should never be used in production.

Sources:
- Authentication_Guide.pdf (page 5)
- API_Reference.pdf (page 23)
- API_Reference.pdf (page 24)
```

---

### Document Management Example

**JavaScript/TypeScript Complete Example:**

```typescript
// document-manager.ts
import axios from 'axios';

interface Collection {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string | null;
}

interface Document {
  id: string;
  collection_id: string;
  name: string;
  type: string;
  size: number;
  status: string;
  chunk_count: number;
  upload_date: string;
  error_message: string | null;
}

interface SearchResult {
  content: string;
  score: number;
  metadata: {
    document_id: string;
    collection_id: string;
    source: string;
    page?: number;
    chunk_index: number;
  };
}

class DocumentManager {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor(baseUrl: string, userEmail: string) {
    this.baseUrl = baseUrl;
    this.headers = {
      'X-Forwarded-User': userEmail,
      'X-Forwarded-Email': userEmail
    };
  }

  async createCollection(name: string, description?: string): Promise<Collection> {
    const response = await axios.post<Collection>(
      `${this.baseUrl}/api/documents/collections`,
      { name, description },
      { headers: this.headers }
    );
    return response.data;
  }

  async listCollections(): Promise<Collection[]> {
    const response = await axios.get<Collection[]>(
      `${this.baseUrl}/api/documents/collections`,
      { headers: this.headers }
    );
    return response.data;
  }

  async uploadDocument(
    file: File,
    collectionId: string,
    options?: {
      chunkSize?: number;
      chunkOverlap?: number;
      strategy?: string;
    }
  ): Promise<any> {
    const formData = new FormData();
    formData.append('files', file);
    formData.append('collection_id', collectionId);
    formData.append('chunk_size', String(options?.chunkSize || 1000));
    formData.append('chunk_overlap', String(options?.chunkOverlap || 200));
    formData.append('strategy', options?.strategy || 'recursive');

    const response = await axios.post(
      `${this.baseUrl}/api/documents/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    );
    return response.data;
  }

  async listDocuments(collectionId?: string, status?: string): Promise<Document[]> {
    const params: Record<string, string> = {};
    if (collectionId) params.collection_id = collectionId;
    if (status) params.status = status;

    const response = await axios.get<Document[]>(
      `${this.baseUrl}/api/documents/`,
      { params }
    );
    return response.data;
  }

  async searchDocuments(
    query: string,
    collectionIds: string[],
    options?: {
      k?: number;
      searchType?: 'similarity' | 'text' | 'hybrid';
      keywordWeight?: number;
    }
  ): Promise<{ results: SearchResult[]; total: number }> {
    const response = await axios.post(
      `${this.baseUrl}/api/documents/search`,
      {
        query,
        collection_ids: collectionIds,
        k: options?.k || 5,
        search_type: options?.searchType || 'hybrid',
        keyword_weight: options?.keywordWeight || 0.3,
        include_metadata: true
      }
    );

    return {
      results: response.data.results,
      total: response.data.total_results
    };
  }

  async deleteDocument(documentId: string): Promise<void> {
    await axios.delete(`${this.baseUrl}/api/documents/${documentId}`);
  }

  async deleteCollection(collectionId: string): Promise<void> {
    await axios.delete(
      `${this.baseUrl}/api/documents/collections/${collectionId}`,
      { headers: this.headers }
    );
  }
}

// Usage example
async function main() {
  const manager = new DocumentManager('http://localhost:8000', 'user@example.com');

  // Create collection
  const collection = await manager.createCollection(
    'Project Documentation',
    'All documentation for the Q4 project'
  );
  console.log(`Created collection: ${collection.id}`);

  // Upload documents
  const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
  if (fileInput?.files) {
    for (const file of Array.from(fileInput.files)) {
      const result = await manager.uploadDocument(file, collection.id, {
        chunkSize: 1500,
        chunkOverlap: 300,
        strategy: 'recursive'
      });
      console.log(`Uploaded: ${file.name}`);
    }
  }

  // List documents
  const documents = await manager.listDocuments(collection.id);
  console.log(`Collection has ${documents.length} documents`);

  // Search
  const searchResults = await manager.searchDocuments(
    'How to configure the API?',
    [collection.id],
    { k: 5, searchType: 'hybrid' }
  );

  console.log(`Found ${searchResults.total} results:`);
  searchResults.results.forEach((result, i) => {
    console.log(`${i + 1}. ${result.metadata.source} (score: ${result.score.toFixed(4)})`);
    console.log(`   ${result.content.substring(0, 100)}...`);
  });
}
```

---

## Performance Considerations

### Endpoint Performance Categories

#### Fast Endpoints (<50ms typical)

**GET /collections**

- Simple indexed database query
- Returns user's collections
- Scales well to hundreds of collections

**GET /** (List Documents)

- Indexed query with optional filters
- Fast even with thousands of documents
- Response time: 10-50ms

**POST /collections** (Create)

- Single database insert
- Fast validation
- Response time: 10-30ms

**DELETE /{document_id}**

- Database delete with cascade
- Filesystem cleanup
- Response time: 20-100ms depending on chunk count

**DELETE /collections/{collection_id}**

- Multiple deletes with ownership check
- Response time: 100-500ms depending on document count

#### Medium Endpoints (50-200ms typical)

**GET /collections-with-documents**

- N+1 query pattern (one per collection)
- Returns nested document data
- Response time scales with collection count
- Consider caching for frequent access

**POST /search** (Vector or Text Only)

- Vector search: 10-50ms with HNSW index
- Text search: 20-100ms with GIN index
- Embedding generation: ~100ms (cached after first query)

**POST /preview-chunks**

- Pure text processing, no database
- Response time: 10-50ms
- Scales linearly with text length

#### Slow Endpoints (>200ms typical)

**POST /upload**

- Multi-stage processing pipeline
- Time scales with file size and count
- Typical breakdown:
  - File upload: 1-5 seconds
  - Text extraction: 2-10 seconds (PDF with OCR: 5-30 seconds)
  - Chunking: 1-2 seconds
  - Embedding generation: 5-15 seconds (100 chunks)
  - Database storage: 1-3 seconds
- **Total: 10-60 seconds per document**
- Consider implementing async processing with status polling

**POST /search** (Hybrid Mode)

- Runs vector + text search in parallel
- Response time: 30-150ms
- Slightly slower than individual methods
- Better accuracy justifies latency

### Optimisation Tips

#### 1. Reduce Chunk Size for Faster Processing

```python
# Slower: More chunks = more embeddings = more time
upload_data = {
    'chunk_size': 500,  # Creates 200 chunks for 100KB doc
    'chunk_overlap': 100
}

# Faster: Fewer chunks = fewer embeddings = less time
upload_data = {
    'chunk_size': 2000,  # Creates 50 chunks for 100KB doc
    'chunk_overlap': 400
}
```

**Trade-off:** Larger chunks may reduce search accuracy for specific questions.

#### 2. Batch Document Uploads

```python
# Good: Upload multiple files in single request
files = [
    ('files', ('doc1.pdf', open('doc1.pdf', 'rb'), 'application/pdf')),
    ('files', ('doc2.pdf', open('doc2.pdf', 'rb'), 'application/pdf')),
    ('files', ('doc3.pdf', open('doc3.pdf', 'rb'), 'application/pdf'))
]

response = requests.post(f'{BASE_URL}/api/documents/upload', files=files, data=data)
```

**Benefits:** Reduces HTTP overhead, shares connection pooling.

#### 3. Limit Search Results

```python
# Good: Request only what you need
search_request = {
    'query': 'authentication',
    'collection_ids': [collection_id],
    'k': 3  # Only get top 3 results
}

# Avoid: Requesting many results when few will be used
search_request = {
    'k': 50  # Slower, unnecessary if only showing top 3
}
```

#### 4. Filter Collections and Documents

```python
# Faster: Search specific collection
search_request = {
    'collection_ids': ['specific-collection-id'],
    'document_ids': ['relevant-doc-id'],  # Further narrow scope
    'query': 'authentication'
}

# Slower: Search all collections
search_request = {
    'collection_ids': all_collection_ids,  # Searches everything
    'query': 'authentication'
}
```

#### 5. Choose Appropriate Search Mode

```python
# Fastest: Vector similarity only
search_request = {'search_type': 'similarity'}  # ~20ms

# Medium: Text search only
search_request = {'search_type': 'text'}  # ~40ms

# Slowest but most accurate: Hybrid
search_request = {'search_type': 'hybrid'}  # ~80ms
```

#### 6. Cache Frequent Queries

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query: str, collection_id: str, k: int):
    """Cache search results for frequent queries."""
    return search_documents(query, [collection_id], k)

# First call: Full search (~80ms)
results = cached_search("authentication", collection_id, 5)

# Subsequent calls: Instant (<1ms)
results = cached_search("authentication", collection_id, 5)
```

#### 7. Use Separate Endpoints Instead of Combined

```python
# Slower: Get collections with documents (N+1 queries)
response = requests.get(f'{BASE_URL}/api/documents/collections-with-documents')

# Faster: Get collections and documents separately (2 queries total)
collections = requests.get(f'{BASE_URL}/api/documents/collections').json()
documents = requests.get(f'{BASE_URL}/api/documents/').json()

# Build structure client-side if needed
```

#### 8. Async/Parallel Processing for Multiple Operations

```python
import asyncio
import aiohttp

async def upload_multiple_async(files: list, collection_id: str):
    """Upload multiple documents in parallel."""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for file_path in files:
            task = upload_single_async(session, file_path, collection_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results

# Much faster than sequential uploads
results = asyncio.run(upload_multiple_async(file_paths, collection_id))
```

### Database Optimisation

**Ensure Indexes Exist:**

```sql
-- Vector similarity index (critical for search performance)
CREATE INDEX document_chunks_embedding_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-text search index
CREATE INDEX documents_search_vector_idx
ON documents
USING gin(search_vector);

-- Foreign key indexes for fast joins
CREATE INDEX document_chunks_document_id_idx
ON document_chunks(document_id);

CREATE INDEX documents_collection_id_idx
ON documents(collection_id);

-- Collection lookup by user
CREATE INDEX document_collections_user_id_idx
ON document_collections(user_id);
```

### Monitoring and Profiling

```python
import time
import logging

def profile_search(query: str, collection_ids: list):
    """Profile search performance."""

    start = time.time()

    # Vector search
    vector_start = time.time()
    vector_results = search_documents(query, collection_ids, search_type='similarity')
    vector_time = time.time() - vector_start

    # Text search
    text_start = time.time()
    text_results = search_documents(query, collection_ids, search_type='text')
    text_time = time.time() - text_start

    # Hybrid search
    hybrid_start = time.time()
    hybrid_results = search_documents(query, collection_ids, search_type='hybrid')
    hybrid_time = time.time() - hybrid_start

    total_time = time.time() - start

    logging.info(f"Search Performance for '{query}':")
    logging.info(f"  Vector:  {vector_time*1000:.1f}ms ({len(vector_results['results'])} results)")
    logging.info(f"  Text:    {text_time*1000:.1f}ms ({len(text_results['results'])} results)")
    logging.info(f"  Hybrid:  {hybrid_time*1000:.1f}ms ({len(hybrid_results['results'])} results)")
    logging.info(f"  Total:   {total_time*1000:.1f}ms")

# Run profiling
profile_search("authentication configuration", [collection_id])
```

---

## Related Documentation

### API Documentation

- [Graph API](../graph/graph.md) - Workflow management API (document search tools integrate here)
- [Auth API](../../../backend/api/auth/auth.md) - Authentication and user management
- [Execution API](../execution/execution.md) - Workflow execution with document context

### Architecture Documentation

- [Services Architecture](../architecture/services.md) - Service layer design patterns
- [Database Schema](../architecture/database.md) - Document and chunk models
- [RAG Architecture](../architecture/rag.md) - Retrieval-Augmented Generation design

### Service Documentation

- [DocumentStorageService](../../backend/services/document_storage/README.md) - Document storage implementation
- [DocumentSearchService](../../services/document_storage/search_service.py) - Search algorithms and RRF
- [Text Splitting](../../backend/services/text_splitting/README.md) - Chunking strategies and optimisation

### Tool Integration

- [Document Search Tool](../../backend/tools/document_search/README.md) - LangChain tool for agent integration
- [Agent Tools Factory](../../services/graph/agent_tools/factory.py) - Tool configuration for workflows

### External Resources

- [LangChain Document Loaders](https://python.langchain.com/docs/integrations/document_loaders) - Loader integrations
- [pgvector Documentation](https://github.com/pgvector/pgvector) - PostgreSQL vector extension
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings) - Embedding model details
- [Reciprocal Rank Fusion Paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) - RRF algorithm research

---

## Summary

The Documents API module provides a comprehensive document management and semantic search solution for AgenticStudio,
enabling powerful Retrieval-Augmented Generation (RAG) workflows with minimal complexity.

**Core Capabilities:**

- **Document Management:** Upload, organise, and manage documents in user-scoped collections
- **Intelligent Chunking:** Automatic text splitting with multiple strategies and intelligent parameter recommendations
- **Multi-Modal Search:** Vector similarity, full-text keyword, and hybrid search modes
- **RAG-Ready:** Optimised for agent workflows with document context retrieval
- **Flexible Integration:** Direct service access or RESTful API for any client

**Key Features:**

**Upload and Processing:**

- Support for PDF, DOCX, TXT, CSV, Excel formats
- Automatic OCR for scanned documents
- Configurable chunking strategies (recursive, character, sentence)
- Batch embedding generation with progress tracking
- Status monitoring and error handling

**Search Capabilities:**

- Vector similarity search using 3072-dimensional embeddings
- Full-text keyword search with PostgreSQL tsvector
- Hybrid search with Reciprocal Rank Fusion (RRF)
- Multi-collection and multi-document filtering
- Configurable result ranking and metadata inclusion

**Collection Management:**

- User-scoped collection organisation
- Nested document structures
- Cascade deletion for cleanup
- Flexible access control

**Performance Optimisations:**

- HNSW vector indexes for logarithmic search time
- Query embedding caching
- Batch processing for embeddings
- Configurable chunk sizes for speed/accuracy trade-offs

**Primary Use Cases:**

- **RAG-Enabled Chatbots:** Provide conversational AI with document context
- **Documentation Search:** Semantic search across technical documentation
- **Knowledge Management:** Organise and retrieve organisational knowledge
- **Question Answering:** Build Q&A systems over document repositories
- **Agent Workflows:** Enable AI agents to search and retrieve document context

**Integration Points:**

- **Graph API:** Document search tools available in workflow agent nodes
- **Agent Tools:** Seamless integration with LangChain-based agents
- **External Clients:** RESTful API for any programming language
- **Frontend Applications:** Direct integration for document management UIs

The Documents API is designed to be the foundation for intelligent document retrieval in AgenticStudio, providing the
context needed for accurate and informed AI agent responses while maintaining simplicity and performance.
