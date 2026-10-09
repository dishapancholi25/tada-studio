# Text Splitting Service Documentation

## Overview

The Text Splitting Service provides intelligent document chunking capabilities for AgenticStudio, enabling efficient text
segmentation for RAG pipelines, vector storage, and LLM processing. The service supports multiple splitting strategies
optimised for different document types, with automatic parameter optimisation and post-processing capabilities.

**Location:** [backend/services/text_splitting/](../../backend/services/text_splitting/)

**Primary Responsibilities:**

- Split documents into chunks using multiple strategies (recursive, character, token, semantic)
- Automatically analyse documents to recommend optimal chunking parameters
- Validate and adjust chunking parameters to ensure reasonable values
- Post-process chunks with context markers and small chunk merging
- Provide factory-based strategy selection for flexible splitting

**Key Use Cases:**

- Chunking documents for vector database ingestion
- Preparing text for LLM processing with token limits
- Creating overlapping chunks for RAG retrieval
- Processing large documents while preserving context
- Optimising chunk sizes based on document characteristics

## Architecture

### Module Structure

```
backend/services/text_splitting/
├── __init__.py              # Public API exports
├── factory.py               # TextSplitterFactory for strategy selection
├── optimizer.py             # ChunkingOptimizer for parameter analysis
├── postprocessor.py         # ChunkPostProcessor for chunk refinement
├── utils.py                 # High-level utility functions
└── strategies/              # Splitting strategy implementations
    ├── __init__.py         # Strategy exports
    ├── base.py             # TextSplitterStrategy protocol
    ├── character.py        # CharacterStrategy (single separator)
    ├── recursive.py        # RecursiveStrategy (hierarchical separators)
    ├── token.py            # TokenStrategy (token-aware splitting)
    └── semantic.py         # SemanticStrategy (NLP-based splitting)
```

**File Purposes:**

- **factory.py**: Factory pattern for creating splitters based on strategy name
- **optimizer.py**: Document analysis and parameter recommendation
- **postprocessor.py**: Chunk refinement (context markers, merging)
- **utils.py**: High-level `create_optimized_chunks()` convenience function
- **strategies/**: Strategy pattern implementations for different splitting algorithms

### Design Patterns

**Factory Pattern**
The service uses the Factory pattern to create different text splitters based on strategy names. The
`TextSplitterFactory` maintains a registry of available strategies and instantiates the appropriate splitter.

```python
# Factory creates splitters based on strategy name
splitter = TextSplitterFactory.create_splitter(
    strategy="recursive",  # or "character", "token", "semantic"
    chunk_size=1000,
    chunk_overlap=200,
)
```

**Strategy Pattern**
Different splitting algorithms are implemented as strategy classes that conform to the `TextSplitterStrategy` protocol.
Each strategy encapsulates a specific splitting algorithm:

- **RecursiveStrategy**: Hierarchical separators (paragraphs → sentences → words)
- **CharacterStrategy**: Single separator splitting
- **TokenStrategy**: Token-aware splitting for LLM compatibility
- **SemanticStrategy**: NLP-based splitting with sentence detection

**Facade Pattern**
The `create_optimized_chunks()` function provides a simplified facade that combines factory creation, optimisation, and
post-processing in a single call.

```python
# Facade hides complexity of factory + optimizer + postprocessor
chunks = create_optimized_chunks(
    text=document_text,
    strategy="auto",  # Automatic strategy selection
)
```

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                   create_optimized_chunks()                  │
│                    (Facade Function)                         │
└──────────────┬──────────────┬────────────────┬──────────────┘
               │              │                │
       ┌───────▼──────┐  ┌───▼──────────┐  ┌──▼─────────────┐
       │ Chunking     │  │ TextSplitter │  │ ChunkPost      │
       │ Optimizer    │  │ Factory      │  │ Processor      │
       └──────────────┘  └───┬──────────┘  └────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼────┐      ┌──────▼───┐      ┌──────▼───┐
     │Recursive│      │Character │      │  Token   │
     │Strategy │      │Strategy  │      │ Strategy │
     └─────────┘      └──────────┘      └──────────┘
                             │
                      ┌──────▼───┐
                      │Semantic  │
                      │Strategy  │
                      └──────────┘
```

### Dependencies

**Internal Dependencies:**

- None (self-contained service)

**External Dependencies:**

- **langchain** (required): Core text splitting implementations
  - `langchain.text_splitter`: TextSplitter implementations
  - `langchain_core.documents.Document`: Document model
- **tiktoken** (optional): Token counting for TokenStrategy
- **spacy** (optional): NLP for SemanticStrategy (preferred)
- **nltk** (optional): NLP for SemanticStrategy (fallback)

**Database Dependencies:**

- None (stateless service)

**Environment Variables:**

- None (no configuration required)

## Public API

### Exported Classes

- `TextSplitterFactory` - Factory for creating text splitters based on strategy
- `ChunkingOptimizer` - Analyzes documents and recommends chunking parameters
- `ChunkPostProcessor` - Post-processes chunks with context markers and merging

### Exported Functions

- `create_optimized_chunks()` - High-level function for creating optimised chunks with automatic parameter selection

### Constants and Configuration

**Strategy Names:**

- `"recursive"` - Hierarchical separator splitting (default, recommended)
- `"character"` - Single separator splitting
- `"token"` - Token-aware splitting for LLM compatibility
- `"semantic"` - NLP-based splitting with sentence detection
- `"auto"` - Automatic strategy selection based on document analysis

**Default Parameters:**

- Default chunk size: `1000` characters
- Default chunk overlap: `200` characters
- Minimum chunk size: `100` characters (enforced by validator)
- Maximum chunk size: `10000` characters (enforced by validator)
- Maximum overlap ratio: `0.5` (50% of chunk size)

### Exceptions

This service does not define custom exceptions. It relies on:

- Standard Python exceptions (`ValueError`, `ImportError`)
- LangChain exceptions (if underlying splitters fail)

## Core Classes

### `TextSplitterFactory`

Factory class for creating text splitters based on strategy name.

**Purpose:** Provides a unified interface for creating different text splitters without needing to know the specific
strategy class.

**Responsibilities:**

- Maintain registry of available splitting strategies
- Instantiate appropriate splitter based on strategy name
- Provide fallback to default strategy for unknown names
- Pass strategy-specific parameters to splitter implementations

**Class Attributes:**

- `_strategies: Dict[str, Type]` - Registry mapping strategy names to strategy classes

**Key Methods:**

#### `create_splitter()`

```python
@staticmethod
def create_splitter(
    strategy: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **kwargs: Dict[str, Any],
):
    """Create a text splitter based on the specified strategy."""
```

**Parameters:**

- `strategy` (str) - Splitting strategy: "recursive", "character", "token", "semantic" (default: "recursive")
- `chunk_size` (int) - Target size for each chunk in characters (default: 1000)
- `chunk_overlap` (int) - Number of characters to overlap between chunks (default: 200)
- `**kwargs` (Dict[str, Any]) - Strategy-specific parameters

**Returns:**

- Text splitter instance (LangChain splitter type depends on strategy)

**Behaviour:**

- Looks up strategy class in registry
- Falls back to RecursiveStrategy if strategy name is unknown
- Logs warning if unknown strategy is requested
- Delegates to strategy's `create()` method

**Example:**

```python
from backend.services.text_splitting import TextSplitterFactory

# Create recursive splitter (default, recommended for most documents)
splitter = TextSplitterFactory.create_splitter(
    strategy="recursive",
    chunk_size=1000,
    chunk_overlap=200,
)

# Create token-aware splitter for LLM processing
token_splitter = TextSplitterFactory.create_splitter(
    strategy="token",
    chunk_size=500,
    chunk_overlap=50,
    encoding_name="cl100k_base",  # GPT-4 encoding
)

# Create semantic splitter with custom NLP pipeline
semantic_splitter = TextSplitterFactory.create_splitter(
    strategy="semantic",
    chunk_size=800,
    chunk_overlap=100,
    pipeline="en_core_web_sm",  # spaCy model
)

# Unknown strategy falls back to recursive
splitter = TextSplitterFactory.create_splitter(
    strategy="unknown",  # Logs warning, uses recursive
)
```

**Use Cases:**

- When you need to switch between splitting strategies based on configuration
- When processing different document types with different strategies
- When you want flexibility without hard-coding strategy classes

---

### `ChunkingOptimizer`

Utility class for analysing documents and recommending optimal chunking parameters.

**Purpose:** Analyses document characteristics (structure, content type) to recommend appropriate chunking strategy and
parameters.

**Responsibilities:**

- Analyse document structure (lines, sentences, words)
- Detect document features (code blocks, tables, lists)
- Recommend optimal strategy based on content type
- Recommend chunk size and overlap based on characteristics
- Validate and adjust parameters to reasonable bounds

**Key Methods:**

#### `analyze_document()`

```python
@staticmethod
def analyze_document(text: str) -> Dict[str, Any]:
    """Analyze document characteristics to recommend optimal chunking parameters."""
```

**Parameters:**

- `text` (str) - The document text to analyse

**Returns:**

- `Dict[str, Any]` - Analysis results with the following keys:
  - `total_characters` (int) - Total character count
  - `total_words` (int) - Total word count
  - `total_lines` (int) - Total line count
  - `total_sentences` (int) - Estimated sentence count
  - `avg_line_length` (float) - Average characters per line
  - `avg_sentence_length` (float) - Average characters per sentence
  - `has_code_blocks` (bool) - Whether document contains code blocks
  - `has_tables` (bool) - Whether document contains tables
  - `has_lists` (bool) - Whether document contains lists
  - `recommended_strategy` (str) - Recommended splitting strategy
  - `recommended_chunk_size` (int) - Recommended chunk size
  - `recommended_overlap` (int) - Recommended overlap size

**Example:**

```python
from backend.services.text_splitting import ChunkingOptimizer

# Analyze a code-heavy document
code_document = """
def example():
    ```python
    def hello():
        print("Hello")
    ```
"""

analysis = ChunkingOptimizer.analyze_document(code_document)
print(f"Strategy: {analysis['recommended_strategy']}")  # "recursive"
print(f"Chunk size: {analysis['recommended_chunk_size']}")  # 1500
print(f"Has code: {analysis['has_code_blocks']}")  # True

# Analyze a table-heavy document
table_document = """
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Data 1   | Data 2   | Data 3   |
"""

analysis = ChunkingOptimizer.analyze_document(table_document)
print(f"Strategy: {analysis['recommended_strategy']}")  # "character"
print(f"Has tables: {analysis['has_tables']}")  # True
```

**Behaviour:**

- Simple heuristic-based analysis (counts, patterns)
- Detects code blocks by looking for ``` or indentation
- Detects tables by counting pipe characters
- Detects lists by checking line prefixes (-, *, 1., •)
- Recommends larger chunks (1500) for code blocks
- Recommends larger chunks (2000) for tables
- Recommends smaller chunks (800) for long sentences
- Default balanced approach (1000) for regular text

**Use Cases:**

- When processing documents of unknown type
- When you want automatic parameter selection
- When optimising chunking for specific document characteristics
- When implementing "auto" mode in applications

#### `validate_parameters()`

```python
@staticmethod
def validate_parameters(
    chunk_size: int,
    chunk_overlap: int,
) -> tuple[int, int]:
    """Validate and adjust chunking parameters to ensure they're reasonable."""
```

**Parameters:**

- `chunk_size` (int) - Desired chunk size
- `chunk_overlap` (int) - Desired overlap size

**Returns:**

- `tuple[int, int]` - Tuple of (validated_chunk_size, validated_chunk_overlap)

**Behaviour:**

- Clamps chunk_size to range [100, 10000]
- Ensures overlap is not greater than 50% of chunk_size
- Ensures overlap is not negative
- Returns adjusted values

**Example:**

```python
from backend.services.text_splitting import ChunkingOptimizer

# Validate reasonable parameters (unchanged)
size, overlap = ChunkingOptimizer.validate_parameters(1000, 200)
print(f"Size: {size}, Overlap: {overlap}")  # Size: 1000, Overlap: 200

# Validate too-small chunk size (adjusted to minimum)
size, overlap = ChunkingOptimizer.validate_parameters(50, 10)
print(f"Size: {size}, Overlap: {overlap}")  # Size: 100, Overlap: 10

# Validate too-large chunk size (adjusted to maximum)
size, overlap = ChunkingOptimizer.validate_parameters(50000, 1000)
print(f"Size: {size}, Overlap: {overlap}")  # Size: 10000, Overlap: 1000

# Validate overlap > 50% of chunk size (adjusted)
size, overlap = ChunkingOptimizer.validate_parameters(1000, 600)
print(f"Size: {size}, Overlap: {overlap}")  # Size: 1000, Overlap: 500

# Validate negative overlap (adjusted to 0)
size, overlap = ChunkingOptimizer.validate_parameters(1000, -100)
print(f"Size: {size}, Overlap: {overlap}")  # Size: 1000, Overlap: 0
```

**Use Cases:**

- When accepting user-provided chunk parameters
- When you want to ensure parameters are within safe bounds
- Before creating splitters to avoid unreasonable values

---

### `ChunkPostProcessor`

Post-processing utilities for refining document chunks after splitting.

**Purpose:** Enhances chunks with metadata and improves chunk quality through merging and context markers.

**Responsibilities:**

- Add continuation context markers to chunks
- Merge chunks that are too small
- Preserve chunk relationships with metadata
- Improve chunk quality for retrieval

**Key Methods:**

#### `add_context_markers()`

```python
@staticmethod
def add_context_markers(
    chunks: List[Document],
    context_window: int = 50,
) -> List[Document]:
    """Add context markers to chunks to indicate continuation."""
```

**Parameters:**

- `chunks` (List[Document]) - List of document chunks
- `context_window` (int) - Number of characters to include as context (default: 50)

**Returns:**

- `List[Document]` - List of chunks with context markers added

**Added Metadata:**

- `has_previous` (bool) - Whether chunk has a previous chunk
- `previous_context` (str) - Last N characters of previous chunk (if exists)
- `has_next` (bool) - Whether chunk has a next chunk
- `next_context` (str) - First N characters of next chunk (if exists)

**Example:**

```python
from backend.services.text_splitting import ChunkPostProcessor
from langchain_core.documents import Document

chunks = [
    Document(page_content="This is the first chunk of text."),
    Document(page_content="This is the second chunk of text."),
    Document(page_content="This is the third chunk of text."),
]

# Add context markers
processed = ChunkPostProcessor.add_context_markers(chunks, context_window=20)

# First chunk
print(processed[0].metadata["has_previous"])  # False
print(processed[0].metadata["has_next"])  # True
print(processed[0].metadata["next_context"])  # "This is the second"

# Middle chunk
print(processed[1].metadata["has_previous"])  # True
print(processed[1].metadata["previous_context"])  # "k of text."
print(processed[1].metadata["has_next"])  # True
print(processed[1].metadata["next_context"])  # "This is the third c"

# Last chunk
print(processed[2].metadata["has_previous"])  # True
print(processed[2].metadata["has_next"])  # False
```

**Behaviour:**

- Iterates through chunks in order
- For each chunk (except first), adds previous_context
- For each chunk (except last), adds next_context
- Modifies chunks in-place and returns modified list
- Context windows are substring slices, not full chunks

**Use Cases:**

- When you need to provide context hints for retrieval
- When chunks might need to reference adjacent content
- When implementing RAG systems that benefit from continuation markers
- When debugging chunk boundaries

#### `merge_small_chunks()`

```python
@staticmethod
def merge_small_chunks(
    chunks: List[Document],
    min_size: int = 100,
) -> List[Document]:
    """Merge chunks that are too small with adjacent chunks."""
```

**Parameters:**

- `chunks` (List[Document]) - List of document chunks
- `min_size` (int) - Minimum size for a chunk in characters (default: 100)

**Returns:**

- `List[Document]` - List of chunks with small chunks merged

**Added Metadata:**

- `merged` (bool) - Set to True on chunks that were created by merging

**Example:**

```python
from backend.services.text_splitting import ChunkPostProcessor
from langchain_core.documents import Document

chunks = [
    Document(page_content="Short"),  # 5 chars, will be merged
    Document(page_content="This is a longer chunk that meets the minimum size requirement."),
    Document(page_content="Another short one"),  # 18 chars, will be merged
    Document(page_content="This is also a longer chunk that meets the minimum size requirement."),
]

# Merge small chunks
merged = ChunkPostProcessor.merge_small_chunks(chunks, min_size=50)

# First chunk is merged with second
print(len(merged))  # 3 (instead of 4)
print(merged[0].page_content)  # "Short\nThis is a longer chunk..."
print(merged[0].metadata.get("merged"))  # True

# Third chunk is merged with fourth
print(merged[2].page_content)  # "Another short one\nThis is also..."
print(merged[2].metadata.get("merged"))  # True
```

**Behaviour:**

- Iterates through chunks sequentially
- If current chunk is below min_size, merges with next chunk
- Joins chunk content with newline separator
- Marks merged chunks with metadata
- Always includes last chunk, even if small
- Returns new list (original chunks modified in-place)

**Use Cases:**

- When splitting produces very small chunks (e.g., single words)
- When you want to ensure minimum chunk size for quality
- When processing documents with irregular structure
- Before indexing chunks in vector database

## Functions

### `create_optimized_chunks()`

High-level convenience function that combines factory creation, optimisation, and post-processing into a single call.

**Purpose:** Provides a simple interface for creating optimised chunks from text without manually coordinating factory,
optimiser, and post-processor.

**Signature:**

```python
def create_optimized_chunks(
    text: str,
    strategy: str = "auto",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    optimize: bool = True,
    add_context: bool = True,
) -> List[Document]:
    """Create optimized chunks from text using the specified or auto-detected strategy."""
```

**Parameters:**

- `text` (str) - The text to split into chunks
- `strategy` (str) - Splitting strategy or "auto" for automatic selection (default: "auto")
- `chunk_size` (Optional[int]) - Target chunk size in characters (auto-detected if None)
- `chunk_overlap` (Optional[int]) - Chunk overlap in characters (auto-detected if None)
- `optimize` (bool) - Whether to optimise parameters based on document analysis (default: True)
- `add_context` (bool) - Whether to add context markers to chunks (default: True)

**Returns:**

- `List[Document]` - List of optimised document chunks with metadata

**Added Metadata:**

- `chunking_strategy` (str) - Strategy used for splitting
- `chunk_size_target` (int) - Target chunk size used
- `chunk_overlap` (int) - Overlap size used
- `merged` (bool) - Whether chunk was created by merging (if applicable)
- `has_previous` (bool) - Whether chunk has previous chunk (if add_context=True)
- `has_next` (bool) - Whether chunk has next chunk (if add_context=True)
- `previous_context` (str) - Previous chunk context (if add_context=True and has_previous=True)
- `next_context` (str) - Next chunk context (if add_context=True and has_next=True)

**Example:**

```python
from backend.services.text_splitting import create_optimized_chunks

document_text = """
# Introduction

This is a sample document with multiple paragraphs.

## Section 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

## Section 2

Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
"""

# Automatic optimisation (recommended)
chunks = create_optimized_chunks(
    text=document_text,
    strategy="auto",  # Automatically selects best strategy
)

for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}:")
    print(f"  Strategy: {chunk.metadata['chunking_strategy']}")
    print(f"  Size: {len(chunk.page_content)}")
    print(f"  Has next: {chunk.metadata.get('has_next', False)}")
    print()

# Manual parameters with optimisation disabled
chunks = create_optimized_chunks(
    text=document_text,
    strategy="recursive",
    chunk_size=500,
    chunk_overlap=100,
    optimize=False,  # Use exact parameters
    add_context=False,  # No context markers
)

# Token-aware splitting for LLM processing
chunks = create_optimized_chunks(
    text=document_text,
    strategy="token",
    chunk_size=400,  # Tokens, not characters
    chunk_overlap=50,
)
```

**Workflow:**

1. **Document Analysis** (if optimize=True or strategy="auto"):
    - Analyses document characteristics
    - Determines recommended strategy (if strategy="auto")
    - Determines recommended chunk_size and chunk_overlap (if None)

2. **Parameter Defaults**:
    - Sets chunk_size=1000 if not provided or auto-detected
    - Sets chunk_overlap=200 if not provided or auto-detected

3. **Parameter Validation**:
    - Validates and adjusts chunk_size to [100, 10000]
    - Ensures overlap ≤ 50% of chunk_size

4. **Splitting**:
    - Creates splitter using factory
    - Splits text into initial chunks

5. **Post-Processing**:
    - Merges small chunks (min_size=100)
    - Adds context markers (if add_context=True)
    - Adds metadata about strategy and parameters

6. **Logging**:
    - Logs chunk count and strategy used

**Use Cases:**

- When you want the simplest interface for chunking
- When processing documents of unknown type
- When you want automatic optimisation
- When you need chunks ready for vector database ingestion

## Configuration

### Initialisation Patterns

The text_splitting service is stateless and uses static methods. No initialisation is required.

**Basic Usage:**

```python
from backend.services.text_splitting import create_optimized_chunks

# Just import and use
chunks = create_optimized_chunks(text="Your document text here")
```

**Factory-Based Usage:**

```python
from backend.services.text_splitting import TextSplitterFactory

# Create splitter for reuse
splitter = TextSplitterFactory.create_splitter(
    strategy="recursive",
    chunk_size=1000,
    chunk_overlap=200,
)

# Use splitter multiple times
chunks1 = splitter.create_documents([text1])
chunks2 = splitter.create_documents([text2])
```

**Manual Workflow:**

```python
from backend.services.text_splitting import (
    TextSplitterFactory,
    ChunkingOptimizer,
    ChunkPostProcessor,
)

# Step 1: Analyze document
analysis = ChunkingOptimizer.analyze_document(text)

# Step 2: Validate parameters
chunk_size, chunk_overlap = ChunkingOptimizer.validate_parameters(
    analysis["recommended_chunk_size"],
    analysis["recommended_overlap"],
)

# Step 3: Create splitter
splitter = TextSplitterFactory.create_splitter(
    strategy=analysis["recommended_strategy"],
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
)

# Step 4: Split text
chunks = splitter.create_documents([text])

# Step 5: Post-process
chunks = ChunkPostProcessor.merge_small_chunks(chunks)
chunks = ChunkPostProcessor.add_context_markers(chunks)
```

### Environment Variables

This service does not use environment variables.

### Strategy-Specific Configuration

**Recursive Strategy:**

```python
splitter = TextSplitterFactory.create_splitter(
    strategy="recursive",
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", "!", "?", ";", ",", " ", ""],  # Custom hierarchy
)
```

**Character Strategy:**

```python
splitter = TextSplitterFactory.create_splitter(
    strategy="character",
    chunk_size=1000,
    chunk_overlap=200,
    separator="\n\n",  # Custom separator (default: "\n")
)
```

**Token Strategy:**

```python
splitter = TextSplitterFactory.create_splitter(
    strategy="token",
    chunk_size=500,  # In tokens
    chunk_overlap=50,
    encoding_name="cl100k_base",  # GPT-4: cl100k_base, GPT-3.5: p50k_base
)
```

**Semantic Strategy:**

```python
splitter = TextSplitterFactory.create_splitter(
    strategy="semantic",
    chunk_size=800,
    chunk_overlap=100,
    pipeline="en_core_web_sm",  # spaCy model (default: en_core_web_sm)
)
```

## Error Handling

### Common Errors

This service does not define custom exceptions. Common errors include:

#### Import Errors (Optional Dependencies)

**TokenStrategy without tiktoken:**

```python
# If tiktoken is not installed
splitter = TextSplitterFactory.create_splitter(strategy="token")
# Logs warning, falls back to CharacterTextSplitter
```

**SemanticStrategy without spacy/nltk:**

```python
# If neither spacy nor nltk is installed
splitter = TextSplitterFactory.create_splitter(strategy="semantic")
# Logs warning, falls back to RecursiveCharacterTextSplitter
```

**Error Handling Pattern:**

```python
import logging
from backend.services.text_splitting import TextSplitterFactory

logger = logging.getLogger(__name__)

try:
    # Attempt to use token strategy
    splitter = TextSplitterFactory.create_splitter(
        strategy="token",
        chunk_size=500,
    )
    chunks = splitter.create_documents([text])
except ImportError as e:
    # Fallback to recursive strategy
    logger.warning(f"Token strategy unavailable: {e}, using recursive")
    splitter = TextSplitterFactory.create_splitter(
        strategy="recursive",
        chunk_size=500,
    )
    chunks = splitter.create_documents([text])
```

### Best Practices for Error Handling

**1. Use "auto" strategy for robustness:**

```python
# Automatically selects available strategy
chunks = create_optimized_chunks(text=text, strategy="auto")
```

**2. Validate parameters before creating splitter:**

```python
from backend.services.text_splitting import (
    TextSplitterFactory,
    ChunkingOptimizer,
)

# User-provided parameters
user_chunk_size = 50000
user_overlap = -100

# Validate before use
chunk_size, chunk_overlap = ChunkingOptimizer.validate_parameters(
    user_chunk_size,
    user_overlap,
)
# chunk_size=10000 (clamped), chunk_overlap=0 (adjusted)
```

**3. Handle empty text:**

```python
def safe_chunk_text(text: str) -> List[Document]:
    """Safely chunk text with empty text handling."""
    if not text or not text.strip():
        return []  # Return empty list for empty text

    return create_optimized_chunks(text=text)
```

## Integration Patterns

### Integration with Document Storage Service

The text_splitting service is primarily used by the document_storage service for chunking documents before
vectorisation.

**Example
from [backend/services/document_storage/chunking/strategies.py:99](../../backend/services/document_storage/chunking/strategies.py#L99):
**

```python
from backend.services.text_splitting import TextSplitterFactory

class ChunkingService:
    """Service for chunking documents with page tracking support."""

    @staticmethod
    def _chunk_with_page_tracking(
        documents: List[Document],
        chunk_size: int,
        chunk_overlap: int,
        strategy: str,
    ) -> List[Document]:
        """Chunk documents while tracking which pages each chunk spans."""

        # Build page boundary tracker
        tracker = PageBoundaryTracker(documents)
        full_text = tracker.get_full_text()

        # Create splitter from text_splitting service
        text_splitter = TextSplitterFactory.create_splitter(
            strategy=strategy if strategy != "auto" else "recursive",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Split text
        text_chunks = text_splitter.split_text(full_text)

        # Add page metadata
        chunks = []
        for chunk_text in text_chunks:
            chunk_metadata = tracker.assign_chunk_to_pages(chunk_text)
            chunk_doc = Document(page_content=chunk_text, metadata=chunk_metadata)
            chunks.append(chunk_doc)

        return chunks
```

### Integration with API Layer

The document API uses text_splitting for chunk previews.

**Example pattern:**

```python
from fastapi import APIRouter
from pydantic import BaseModel
from backend.services.text_splitting import create_optimized_chunks

class ChunkPreviewRequest(BaseModel):
    text: str
    strategy: str = "recursive"
    chunk_size: int = 1000
    chunk_overlap: int = 200

@router.post("/chunk-preview")
async def preview_chunks(request: ChunkPreviewRequest):
    """Preview how text will be chunked with given parameters."""

    chunks = create_optimized_chunks(
        text=request.text,
        strategy=request.strategy,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        optimize=False,  # Use exact user parameters
    )

    return {
        "chunk_count": len(chunks),
        "chunks": [
            {
                "content": chunk.page_content,
                "size": len(chunk.page_content),
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ],
    }
```

### Common Integration Patterns

#### Pattern 1: Document Processing Pipeline

```python
from backend.services.document import process_document
from backend.services.text_splitting import create_optimized_chunks

async def process_and_chunk_document(file_path: str):
    """Process document and chunk for storage."""

    # Extract text from document
    result = await process_document(file_path)
    document_text = result["content"]

    # Chunk text with automatic optimisation
    chunks = create_optimized_chunks(text=document_text)

    return chunks
```

#### Pattern 2: Batch Document Chunking

```python
from typing import List
from backend.services.text_splitting import TextSplitterFactory

def batch_chunk_documents(
    documents: List[str],
    strategy: str = "recursive",
) -> List[List[Document]]:
    """Chunk multiple documents with same strategy."""

    # Create splitter once for efficiency
    splitter = TextSplitterFactory.create_splitter(
        strategy=strategy,
        chunk_size=1000,
        chunk_overlap=200,
    )

    # Chunk all documents
    all_chunks = []
    for doc_text in documents:
        chunks = splitter.create_documents([doc_text])
        all_chunks.append(chunks)

    return all_chunks
```

#### Pattern 3: Strategy Selection Based on File Type

```python
from backend.services.text_splitting import create_optimized_chunks

def chunk_by_file_type(text: str, file_extension: str):
    """Select chunking strategy based on file type."""

    # Map file types to strategies
    strategy_map = {
        ".py": "recursive",      # Code: use recursive
        ".js": "recursive",
        ".md": "character",      # Markdown: use character
        ".txt": "auto",          # Plain text: auto-detect
        ".pdf": "semantic",      # PDF: use semantic
    }

    strategy = strategy_map.get(file_extension, "auto")

    return create_optimized_chunks(
        text=text,
        strategy=strategy,
    )
```

## Usage Examples

### Example 1: Basic Usage

```python
from backend.services.text_splitting import create_optimized_chunks

# Sample document text
document_text = """
# Machine Learning Guide

Machine learning is a subset of artificial intelligence.

## Types of Machine Learning

1. Supervised Learning
2. Unsupervised Learning
3. Reinforcement Learning
"""

# Create optimised chunks
chunks = create_optimized_chunks(text=document_text)

# Inspect results
print(f"Created {len(chunks)} chunks")
print(f"Strategy: {chunks[0].metadata['chunking_strategy']}")
```

### Example 2: Advanced Configuration

```python
from backend.services.text_splitting import (
    TextSplitterFactory,
    ChunkingOptimizer,
    ChunkPostProcessor,
)

# Analyze document
code_document = "def example():\n    return True"
analysis = ChunkingOptimizer.analyze_document(code_document)

# Validate custom parameters
chunk_size, chunk_overlap = ChunkingOptimizer.validate_parameters(800, 150)

# Create splitter
splitter = TextSplitterFactory.create_splitter(
    strategy="recursive",
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap,
)

# Split and post-process
chunks = splitter.create_documents([code_document])
chunks = ChunkPostProcessor.merge_small_chunks(chunks)
chunks = ChunkPostProcessor.add_context_markers(chunks)
```

## Performance Considerations

### Performance Characteristics

**Strategy Complexity:**

- **RecursiveStrategy**: O(n) - Linear scan with multiple separator attempts
- **CharacterStrategy**: O(n) - Single pass through text
- **TokenStrategy**: O(n) - Tokenisation + splitting (slower)
- **SemanticStrategy**: O(n²) - NLP sentence detection (slowest)

**Memory Usage:**

- All strategies: O(n) - Creates new chunks in memory

### Optimisation Tips

#### Tip 1: Reuse Splitters for Batch Processing

**Problem:**

```python
# Inefficient: Creates new splitter for each document
for document in documents:
    splitter = TextSplitterFactory.create_splitter(strategy="recursive")
    chunks = splitter.create_documents([document])
```

**Solution:**

```python
# Efficient: Create splitter once, reuse
splitter = TextSplitterFactory.create_splitter(strategy="recursive")

for document in documents:
    chunks = splitter.create_documents([document])
```

#### Tip 2: Choose Appropriate Strategy

For large documents, use RecursiveStrategy (fastest) instead of SemanticStrategy (slowest).

## Best Practices

### Do's

✅ **Use "auto" strategy for unknown document types**

```python
chunks = create_optimized_chunks(text=text, strategy="auto")
```

✅ **Validate user-provided parameters**

```python
chunk_size, chunk_overlap = ChunkingOptimizer.validate_parameters(
    user_chunk_size, user_overlap
)
```

✅ **Reuse splitters for batch processing**

```python
splitter = TextSplitterFactory.create_splitter(strategy="recursive")
for doc in documents:
    chunks = splitter.create_documents([doc])
```

### Don'ts

❌ **Don't use semantic strategy for large documents without considering performance**

```python
# Slow for large documents
chunks = create_optimized_chunks(text=huge_text, strategy="semantic")

# Better: Use recursive
chunks = create_optimized_chunks(text=huge_text, strategy="recursive")
```

❌ **Don't create new splitters in loops**

```python
# Bad
for doc in documents:
    splitter = TextSplitterFactory.create_splitter(strategy="recursive")
    chunks = splitter.create_documents([doc])

# Good
splitter = TextSplitterFactory.create_splitter(strategy="recursive")
for doc in documents:
    chunks = splitter.create_documents([doc])
```

## Related Documentation

### Related Services

- [Document Service](./document.md) - Document processing and text extraction
- [Document Storage Service](./document_storage.md) - Vector storage using chunked documents

### Related API Modules

- [Documents API](../agents-guide/api/documents.md) - Document upload endpoints

### External Documentation

- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [tiktoken](https://github.com/openai/tiktoken)

## Summary

The Text Splitting Service provides intelligent document chunking for AgenticStudio's RAG pipelines. It offers multiple
strategies (recursive, character, token, semantic) with automatic optimisation and post-processing capabilities.

**Key Features:**

- Multiple splitting strategies for different document types
- Automatic document analysis and parameter optimisation
- Intelligent post-processing with context markers
- Factory pattern for flexible strategy selection

**Primary Use Cases:**

- Preparing documents for vector database ingestion
- Chunking text for LLM processing
- Creating overlapping chunks for RAG retrieval

**When to Use This Service:**

- When ingesting documents into vector stores
- When preparing text for LLM context windows
- When chunk quality matters for retrieval tasks
