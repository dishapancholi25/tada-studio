# Token Counting Service

## Overview

The token counting service provides accurate token estimation and cost calculation for LLM operations using tiktoken. It
supports counting tokens in LangChain messages, tool calls, and multi-modal content types, while also providing cost
estimation for various OpenAI models.

**Location:** [backend/services/token_counting/](../../backend/services/token_counting/)

**Primary Responsibilities:**

- Count tokens in strings, messages, and tool calls using tiktoken
- Handle multiple content types (string, dict, list, multi-modal)
- Provide token breakdowns by message type (system, human, AI, tool)
- Estimate costs based on token counts and model pricing
- Cache tiktoken encodings for performance
- Support both synchronous token counting operations

**Key Use Cases:**

- Estimating LLM API costs before making requests
- Tracking token usage for billing and analytics
- Validating input sizes against model context windows
- Breaking down token consumption by message type
- Calculating token overhead from tool calls

## Architecture

### Module Structure

```
backend/services/token_counting/
├── __init__.py              # Public API exports and factory function
├── base.py                  # Abstract base class for token counters
├── token_counter.py         # Main TokenCounter implementation
├── pricing.py               # Model pricing data and cost estimation
├── utils.py                 # EncodingCache and constants
├── content_handlers.py      # Content type handling strategies
└── message_handlers.py      # Message classification and tool call counting
```

**File Purposes:**

- ****init**.py** - Defines the public API with exports and provides `get_token_counter()` factory function implementing
  singleton pattern
- **base.py** - Defines `BaseTokenCounter` abstract class establishing the interface for token counters
- **token_counter.py** - Main `TokenCounter` class coordinating all token counting operations
- **pricing.py** - Contains `MODEL_PRICING` data and cost estimation functions
- **utils.py** - Provides `EncodingCache` for caching tiktoken encodings and defines token overhead constants
- **content_handlers.py** - Implements `ContentTokenCounter` for handling different content types (string, dict, list)
- **message_handlers.py** - Implements `MessageClassifier` and `ToolCallCounter` for message-specific operations

### Design Patterns

**Singleton Pattern:**
The `get_token_counter()` factory function implements singleton pattern to avoid re-initialising tiktoken encodings,
which are expensive to create. The module-level `_default_counter` variable caches the instance.

**Strategy Pattern:**
Different content types are handled by separate strategy classes:

- `ContentTokenCounter` - Handles string, dict, and list content
- `ToolCallCounter` - Handles tool call token counting
- `MessageClassifier` - Classifies and aggregates by message type

**Dependency Injection:**
The counter classes accept callable string counting functions as dependencies, allowing for flexible composition and
easier testing:

```python
content_counter = ContentTokenCounter(string_counter=self.count_string)
tool_call_counter = ToolCallCounter(string_counter=self.count_string)
```

**Component Relationships:**

```
TokenCounter (main coordinator)
    ├── EncodingCache (provides tiktoken encoding)
    ├── ContentTokenCounter (handles content types)
    │   └── count_string (injected dependency)
    ├── ToolCallCounter (handles tool calls)
    │   └── count_string (injected dependency)
    └── MessageClassifier (classifies message types)

Pricing Module (independent)
    ├── MODEL_PRICING (pricing data)
    ├── estimate_cost() (cost calculation)
    └── get_model_pricing() (pricing lookup)
```

### Dependencies

**Internal Dependencies:**

- None - This is a low-level service with no dependencies on other backend services

**External Dependencies:**

- `tiktoken` - OpenAI's token counting library for accurate tokenisation
- `langchain_core.messages` - Message types (BaseMessage, AIMessage, HumanMessage, etc.)

**Configuration:**

- No database dependencies
- No environment variables required
- All configuration is code-based (pricing data, constants)

## Public API

### Exported Classes

- `TokenCounter` - Main token counting service using tiktoken
- `BaseTokenCounter` - Abstract base class for token counter implementations
- `EncodingCache` - Singleton cache for tiktoken encodings

### Exported Functions

- `get_token_counter(model)` - Factory function to get or create a TokenCounter instance (singleton)
- `estimate_cost(token_counts, model)` - Calculate cost estimate from token counts
- `get_model_pricing(model)` - Get pricing information for a specific model

### Constants and Configuration

- `MODEL_PRICING` - Dictionary mapping model names to pricing per 1M tokens (input/output)

### Exceptions

This service does not define custom exceptions. Token counting errors are logged and fall back to character-based
estimation.

## Core Classes

### `TokenCounter`

Main service class for counting tokens in messages and content using tiktoken.

**Purpose:** Provides accurate token counting for LLM operations, supporting multiple content types and message formats
while maintaining compatibility with LangChain message structures.

**Responsibilities:**

- Count tokens in strings using tiktoken encoding
- Count tokens in LangChain messages with proper overhead
- Handle multi-modal content (string, dict, list)
- Count tool call tokens from AI messages
- Provide detailed breakdowns by message type
- Calculate combined input/output token counts

**Initialisation:**

```python
def __init__(
    self,
    model: str = "gpt-4o",
) -> None:
    """
    Initialise token counter with specified model encoding.

    Args:
        model: The model to use for tokenisation (default: gpt-4o)
    """
```

**Key Methods:**

#### `count_string()`

```python
def count_string(
    self,
    text: str,
) -> int:
    """Count tokens in a string."""
```

**Parameters:**

- `text` (str) - The text to count tokens for

**Returns:**

- `int` - Number of tokens in the text

**Raises:**

- No exceptions raised (errors are logged and fall back to estimation)

**Example:**

```python
from backend.services.token_counting import get_token_counter

counter = get_token_counter(model="gpt-4o")
token_count = counter.count_string("Hello, how are you?")
print(f"Tokens: {token_count}")  # Output: Tokens: 6
```

**Behaviour:**

- Uses tiktoken encoding to accurately count tokens
- Returns 0 for empty or None strings
- Falls back to character-based estimation (1 token per 4 chars) if tiktoken fails
- Logs errors but never raises exceptions
- Character fallback uses `CHARS_PER_TOKEN_FALLBACK` constant (4 chars per token)

**Use Cases:**

- Validate user input length before sending to LLM
- Estimate tokens in generated prompts
- Calculate tokens in tool descriptions
- Count tokens in any string content

#### `count_messages()`

```python
def count_messages(
    self,
    messages: List[BaseMessage],
) -> Dict[str, Any]:
    """Count tokens in a list of messages."""
```

**Parameters:**

- `messages` (List[BaseMessage]) - List of LangChain messages to count

**Returns:**

- `Dict[str, Any]` - Dictionary containing:
  - `total` (int) - Total token count including overhead
  - `breakdown` (dict) - Token counts by message type (system, human, ai, tool, other)
  - `messages` (int) - Number of messages processed

**Example:**

```python
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from backend.services.token_counting import get_token_counter

counter = get_token_counter()

messages = [
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is Python?"),
    AIMessage(content="Python is a programming language."),
]

result = counter.count_messages(messages)
print(f"Total tokens: {result['total']}")
print(f"Breakdown: {result['breakdown']}")
```

**Output:**

```python
{
    "total": 45,
    "breakdown": {
        "system": 12,
        "human": 8,
        "ai": 13,
        "tool": 0,
        "other": 0,
        "message_count": 3,
    },
    "messages": 3,
}
```

**Behaviour:**

- Counts role tokens for each message
- Counts content tokens using `ContentTokenCounter`
- Counts tool call tokens for AI messages
- Adds `TOKENS_PER_MESSAGE` overhead (4 tokens) per message
- Adds `CONVERSATION_END_TOKENS` overhead (3 tokens) for conversation structure
- Provides breakdown by message type for analytics

**Use Cases:**

- Calculate total token count before LLM API call
- Validate conversation fits within context window
- Track token distribution across message types
- Estimate costs for conversation history

#### `count_tool_calls()`

```python
def count_tool_calls(
    self,
    tool_calls: List[Dict[str, Any]],
) -> int:
    """Count tokens in tool calls."""
```

**Parameters:**

- `tool_calls` (List[Dict[str, Any]]) - List of tool call dictionaries

**Returns:**

- `int` - Total number of tokens in all tool calls

**Example:**

```python
from backend.services.token_counting import get_token_counter

counter = get_token_counter()

tool_calls = [
    {
        "name": "search_web",
        "args": {"query": "Python tutorials"},
        "id": "call_123",
    },
    {
        "name": "calculate",
        "args": {"expression": "2 + 2"},
        "id": "call_124",
    },
]

tokens = counter.count_tool_calls(tool_calls)
print(f"Tool call tokens: {tokens}")
```

**Behaviour:**

- Serialises each tool call to JSON
- Counts tokens in the JSON representation
- Returns 0 for empty or None tool calls list
- Includes all tool call metadata (name, args, id)

**Use Cases:**

- Calculate overhead from function calling
- Estimate tokens for tool-use agents
- Track tool calling costs separately
- Validate tool call payload sizes

#### `count_input_output()`

```python
def count_input_output(
    self,
    input_messages: Optional[List[BaseMessage]] = None,
    output_content: Optional[Union[str, BaseMessage]] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Count tokens for both input and output of an LLM call."""
```

**Parameters:**

- `input_messages` (Optional[List[BaseMessage]]) - Input messages sent to the LLM
- `output_content` (Optional[Union[str, BaseMessage]]) - Output from the LLM (string or message)
- `tool_calls` (Optional[List[Dict[str, Any]]]) - Any tool calls made by the LLM

**Returns:**

- `Dict[str, Any]` - Dictionary containing:
  - `input_tokens` (int) - Input token count
  - `output_tokens` (int) - Output token count including tool calls
  - `total_tokens` (int) - Sum of input and output tokens
  - `metadata` (dict) - Detailed breakdowns and tool token counts

**Example:**

```python
from langchain_core.messages import HumanMessage, AIMessage
from backend.services.token_counting import get_token_counter, estimate_cost

counter = get_token_counter(model="gpt-4o")

# Input messages
input_messages = [
    HumanMessage(content="Explain quantum computing in simple terms."),
]

# Output from LLM
output_message = AIMessage(
    content="Quantum computing uses quantum mechanics principles..."
)

# Count tokens
result = counter.count_input_output(
    input_messages=input_messages,
    output_content=output_message,
)

print(f"Input tokens: {result['input_tokens']}")
print(f"Output tokens: {result['output_tokens']}")
print(f"Total tokens: {result['total_tokens']}")

# Estimate cost
cost = estimate_cost(result, model="gpt-4o")
print(f"Estimated cost: ${cost['total_cost']:.6f}")
```

**Behaviour:**

- Counts input messages if provided
- Counts output content (supports both string and BaseMessage)
- Adds tool call tokens to output count
- Stores detailed breakdowns in metadata
- Returns zero counts for missing parameters
- Combines all counts into total_tokens

**Use Cases:**

- Calculate complete token usage for an LLM call
- Estimate costs before making expensive API calls
- Track input vs output token distribution
- Monitor token consumption in agent loops

**Class Attributes:**

- `model: str` - Model name used for tokenisation
- `encoding: tiktoken.Encoding` - Cached tiktoken encoding instance
- `content_counter: ContentTokenCounter` - Handler for different content types
- `tool_call_counter: ToolCallCounter` - Handler for tool call counting

### `BaseTokenCounter`

Abstract base class defining the interface for token counter implementations.

**Purpose:** Provides a protocol that all token counter implementations must follow, enabling polymorphism and
testability.

**Responsibilities:**

- Define required methods for token counting
- Establish interface contract for implementations
- Enable dependency injection and testing with mock counters

**Abstract Methods:**

#### `count_string()`

```python
@abstractmethod
def count_string(self, text: str) -> int:
    """Count tokens in a string."""
```

#### `count_messages()`

```python
@abstractmethod
def count_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
    """Count tokens in a list of messages."""
```

**Example:**

```python
from backend.services.token_counting.base import BaseTokenCounter
from typing import Any, Dict, List
from langchain_core.messages import BaseMessage

class CustomTokenCounter(BaseTokenCounter):
    """Custom token counter implementation."""

    def count_string(self, text: str) -> int:
        """Simple character-based counting."""
        return len(text) // 4

    def count_messages(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        """Count all message content."""
        total = sum(self.count_string(str(msg.content)) for msg in messages)
        return {"total": total, "messages": len(messages)}

# Use custom counter
counter = CustomTokenCounter()
tokens = counter.count_string("Hello world")
```

**Use Cases:**

- Create custom token counting implementations
- Mock token counters for testing
- Implement alternative counting strategies
- Type hint counter dependencies

### `EncodingCache`

Singleton class that caches tiktoken encodings to avoid expensive re-initialisation.

**Purpose:** Optimise performance by reusing tiktoken encoding instances, which are expensive to create. Implements
class-level caching for thread-safe singleton pattern.

**Responsibilities:**

- Load and cache tiktoken encodings
- Handle model name to encoding mapping
- Provide fallback encoding for unknown models
- Support cache clearing for testing

**Class Methods:**

#### `get_encoding()`

```python
@classmethod
def get_encoding(
    cls,
    model: str = "gpt-4o",
):
    """Get or create cached tiktoken encoding for the specified model."""
```

**Parameters:**

- `model` (str) - The model name to get encoding for (default: gpt-4o)

**Returns:**

- `tiktoken.Encoding` - Cached or newly created encoding instance

**Example:**

```python
from backend.services.token_counting.utils import EncodingCache

# First call loads encoding
encoding1 = EncodingCache.get_encoding("gpt-4o")

# Second call returns cached encoding (fast)
encoding2 = EncodingCache.get_encoding("gpt-4o")

# Same instance is returned
assert encoding1 is encoding2

# Different model creates new encoding
encoding3 = EncodingCache.get_encoding("gpt-4")
```

**Behaviour:**

- Returns cached encoding if model matches cached model name
- Creates new encoding if model differs or cache is empty
- Falls back to "cl100k_base" encoding for unknown models
- Logs warnings when falling back to default encoding
- Thread-safe singleton pattern using class variables

**Use Cases:**

- Optimise repeated token counting operations
- Share encoding across multiple counter instances
- Handle unknown or custom model names gracefully

#### `clear_cache()`

```python
@classmethod
def clear_cache(cls):
    """Clear the encoding cache (useful for testing)."""
```

**Example:**

```python
from backend.services.token_counting.utils import EncodingCache

# Clear cache between tests
EncodingCache.clear_cache()

# Force reload of encoding
encoding = EncodingCache.get_encoding("gpt-4o")
```

**Use Cases:**

- Reset state between unit tests
- Free memory if needed
- Force reload of encoding after configuration changes

**Class Attributes:**

- `_encoding: Optional[tiktoken.Encoding]` - Cached encoding instance
- `_model_name: Optional[str]` - Model name for cached encoding

### `ContentTokenCounter`

Handles token counting for different content types using strategy pattern.

**Purpose:** Abstract away the complexity of handling multiple content types (string, dict, list) by providing
type-specific counting strategies.

**Responsibilities:**

- Dispatch counting to appropriate strategy based on content type
- Handle string content directly
- Serialise structured content (dict) to JSON for counting
- Count multi-part list content recursively

**Initialisation:**

```python
def __init__(
    self,
    string_counter: Callable[[str], int],
):
    """
    Initialise content counter with a string counting function.

    Args:
        string_counter: Function to count tokens in a string
    """
```

**Key Methods:**

#### `count_content()`

```python
def count_content(
    self,
    content: Any,
) -> int:
    """Count tokens in content of various types."""
```

**Parameters:**

- `content` (Any) - Content to count (str, dict, list, or other)

**Returns:**

- `int` - Number of tokens in the content

**Example:**

```python
from backend.services.token_counting import get_token_counter

counter = get_token_counter()

# String content
tokens1 = counter.content_counter.count_content("Hello world")

# Dictionary content (serialised to JSON)
tokens2 = counter.content_counter.count_content({
    "type": "text",
    "text": "Hello world",
})

# List content (multi-modal)
tokens3 = counter.content_counter.count_content([
    "Some text",
    {"type": "image_url", "url": "https://example.com/image.jpg"},
])
```

**Behaviour:**

- Returns 0 for None or unsupported types
- Counts string content directly using injected string_counter
- Serialises dict content to JSON before counting
- Iterates through list content, counting each part
- Handles mixed-type lists (strings and dicts together)

**Use Cases:**

- Count tokens in multi-modal messages
- Handle structured content in AI messages
- Support vision model content formats
- Process tool output with mixed content types

### `MessageClassifier`

Utility class for classifying messages by type and aggregating token counts.

**Purpose:** Categorise LangChain messages into types (system, human, AI, tool) and maintain token count breakdowns by
category.

**Responsibilities:**

- Classify messages into standard types
- Create breakdown dictionaries
- Update breakdowns with token counts
- Support analytics and monitoring

**Static Methods:**

#### `get_message_type()`

```python
@staticmethod
def get_message_type(message: BaseMessage) -> str:
    """Get the type/role of a message."""
```

**Parameters:**

- `message` (BaseMessage) - LangChain message to classify

**Returns:**

- `str` - Message type: "system", "human", "ai", "tool", or "other"

**Example:**

```python
from langchain_core.messages import HumanMessage, AIMessage
from backend.services.token_counting.message_handlers import MessageClassifier

msg_type = MessageClassifier.get_message_type(HumanMessage(content="Hello"))
print(msg_type)  # Output: human
```

#### `create_breakdown()`

```python
@staticmethod
def create_breakdown() -> Dict[str, int]:
    """Create an empty token breakdown dictionary."""
```

**Returns:**

- `Dict[str, int]` - Dictionary with all message type keys initialised to 0

**Example:**

```python
from backend.services.token_counting.message_handlers import MessageClassifier

breakdown = MessageClassifier.create_breakdown()
print(breakdown)
# Output: {"system": 0, "human": 0, "ai": 0, "tool": 0, "other": 0, "message_count": 0}
```

#### `update_breakdown()`

```python
@staticmethod
def update_breakdown(
    breakdown: Dict[str, int],
    message_type: str,
    tokens: int,
) -> None:
    """Update breakdown dictionary with token count for message type."""
```

**Parameters:**

- `breakdown` (Dict[str, int]) - The breakdown dictionary to update (modified in place)
- `message_type` (str) - Type of message
- `tokens` (int) - Number of tokens to add

**Example:**

```python
from backend.services.token_counting.message_handlers import MessageClassifier

breakdown = MessageClassifier.create_breakdown()
MessageClassifier.update_breakdown(breakdown, "human", 10)
MessageClassifier.update_breakdown(breakdown, "ai", 25)
print(breakdown)
# Output: {"system": 0, "human": 10, "ai": 25, "tool": 0, "other": 0, "message_count": 0}
```

**Use Cases:**

- Track token distribution across message types
- Monitor system prompt overhead
- Analyse tool usage token costs
- Generate token usage reports

### `ToolCallCounter`

Handles token counting for tool calls within AI messages.

**Purpose:** Extract and count tokens from tool calls attached to AI messages, supporting both LangChain tool call
format and custom tool call dictionaries.

**Responsibilities:**

- Detect tool calls in AI messages
- Serialise tool calls to JSON
- Count tokens in serialised tool call data
- Handle missing or empty tool calls gracefully

**Initialisation:**

```python
def __init__(
    self,
    string_counter: Callable[[str], int],
):
    """
    Initialise tool call counter.

    Args:
        string_counter: Function to count tokens in a string
    """
```

**Key Methods:**

#### `count_message_tool_calls()`

```python
def count_message_tool_calls(
    self,
    message: BaseMessage,
) -> int:
    """Count tokens in tool calls attached to a message."""
```

**Parameters:**

- `message` (BaseMessage) - Message to check for tool calls

**Returns:**

- `int` - Number of tokens in all tool calls

**Example:**

```python
from langchain_core.messages import AIMessage
from backend.services.token_counting import get_token_counter

counter = get_token_counter()

# AI message with tool calls
message = AIMessage(
    content="I'll search for that information.",
    tool_calls=[
        {
            "name": "search_web",
            "args": {"query": "Python tutorials"},
            "id": "call_abc123",
        }
    ],
)

tool_tokens = counter.tool_call_counter.count_message_tool_calls(message)
print(f"Tool call tokens: {tool_tokens}")
```

**Behaviour:**

- Returns 0 for non-AI messages
- Returns 0 if message has no tool_calls attribute
- Returns 0 for empty tool calls list
- Serialises each tool call to JSON
- Counts tokens in JSON representation
- Includes all tool call fields (name, args, id, etc.)

**Use Cases:**

- Calculate overhead from function calling
- Monitor tool usage costs
- Validate tool call payload sizes
- Track agent tool calling patterns

## Functions

### `get_token_counter()`

Factory function that returns a singleton token counter instance.

**Signature:**

```python
def get_token_counter(
    model: str = "gpt-4o",
) -> TokenCounter:
    """
    Get or create a token counter instance.

    This function implements the singleton pattern to avoid re-initialising
    the tiktoken encoding unnecessarily.

    Args:
        model: The model to use for tokenisation (default: gpt-4o)

    Returns:
        TokenCounter instance configured for the specified model
    """
```

**Parameters:**

- `model` (str) - The model to use for tokenisation (default: gpt-4o)

**Returns:**

- `TokenCounter` - Singleton instance configured for the specified model

**Example:**

```python
from backend.services.token_counting import get_token_counter

# Get default counter (gpt-4o)
counter = get_token_counter()

# Get counter for specific model
counter_gpt4 = get_token_counter(model="gpt-4")

# Subsequent calls return the same instance
counter2 = get_token_counter()
assert counter is counter2
```

**Use Cases:**

- Quick access to token counter without managing instances
- Benefit from singleton pattern for performance
- Default to gpt-4o encoding for most use cases
- Import and use in a single line

### `estimate_cost()`

Calculate cost estimate based on token counts and model pricing.

**Signature:**

```python
def estimate_cost(
    token_counts: Dict[str, int],
    model: str = "gpt-4o",
) -> Dict[str, float]:
    """
    Estimate cost based on token counts and model.

    Args:
        token_counts: Dictionary with input_tokens and output_tokens
        model: The model name for pricing

    Returns:
        Dictionary with cost breakdown including:
        - input_cost: Cost for input tokens
        - output_cost: Cost for output tokens
        - total_cost: Total cost
        - model: Model used for pricing
        - currency: Currency (USD)
    """
```

**Parameters:**

- `token_counts` (Dict[str, int]) - Dictionary with `input_tokens` and `output_tokens` keys
- `model` (str) - The model name for pricing (default: gpt-4o)

**Returns:**

- `Dict[str, float]` - Dictionary with cost breakdown:
  - `input_cost` (float) - Cost for input tokens in USD
  - `output_cost` (float) - Cost for output tokens in USD
  - `total_cost` (float) - Total cost in USD
  - `model` (str) - Model used for pricing
  - `currency` (str) - Currency code ("USD")

**Example:**

```python
from backend.services.token_counting import get_token_counter, estimate_cost
from langchain_core.messages import HumanMessage

counter = get_token_counter(model="gpt-4o")

# Count tokens
messages = [HumanMessage(content="Write a Python function to reverse a string.")]
result = counter.count_input_output(
    input_messages=messages,
    output_content="Here's a Python function...",  # Simplified
)

# Estimate cost
cost = estimate_cost(result, model="gpt-4o")
print(f"Input cost: ${cost['input_cost']:.6f}")
print(f"Output cost: ${cost['output_cost']:.6f}")
print(f"Total cost: ${cost['total_cost']:.6f}")
print(f"Model: {cost['model']}")

# Example output:
# Input cost: $0.000025
# Output cost: $0.000100
# Total cost: $0.000125
# Model: gpt-4o
```

**Use Cases:**

- Calculate costs before making LLM API calls
- Track spending across multiple LLM invocations
- Compare costs between different models
- Generate billing reports

### `get_model_pricing()`

Retrieve pricing information for a specific model.

**Signature:**

```python
def get_model_pricing(
    model: str,
) -> Dict[str, float]:
    """
    Get pricing information for a specific model.

    Args:
        model: Model name

    Returns:
        Dictionary with input and output pricing per 1M tokens
    """
```

**Parameters:**

- `model` (str) - Model name (e.g., "gpt-4o", "gpt-4o-mini")

**Returns:**

- `Dict[str, float]` - Dictionary with `input` and `output` keys containing price per 1M tokens

**Example:**

```python
from backend.services.token_counting import get_model_pricing, MODEL_PRICING

# Get pricing for specific model
gpt4o_pricing = get_model_pricing("gpt-4o")
print(f"GPT-4o input: ${gpt4o_pricing['input']}/1M tokens")
print(f"GPT-4o output: ${gpt4o_pricing['output']}/1M tokens")

# Compare models
for model_name in ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]:
    pricing = get_model_pricing(model_name)
    print(f"{model_name}: ${pricing['input']}/{pricing['output']} per 1M tokens")

# Unknown model falls back to default (gpt-4o)
unknown_pricing = get_model_pricing("unknown-model")
```

**Use Cases:**

- Display pricing information in UI
- Compare model costs for decision making
- Calculate price differences between models
- Validate budget constraints

## Configuration

### Constants

The service defines several constants in [utils.py](../../backend/services/token_counting/utils.py):

```python
# Token overhead per message (based on GPT-4 format)
TOKENS_PER_MESSAGE = 4

# Conversation structure overhead
CONVERSATION_END_TOKENS = 3

# Character-based fallback ratio for encoding errors
CHARS_PER_TOKEN_FALLBACK = 4
```

**Constant Descriptions:**

- `TOKENS_PER_MESSAGE` - Overhead tokens added per message for format tokens like
  `<|im_start|>role\n content<|im_end|>\n` (default: 4)
- `CONVERSATION_END_TOKENS` - Tokens for conversation structure overhead like `<|im_start|>assistant` at the end (
  default: 3)
- `CHARS_PER_TOKEN_FALLBACK` - Character-to-token ratio used when tiktoken encoding fails (default: 4 characters per
  token)

### Model Pricing Data

Pricing information is stored in `MODEL_PRICING` dictionary
in [pricing.py](../../backend/services/token_counting/pricing.py):

```python
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}
```

Prices are in USD per 1 million tokens. Update this dictionary when model pricing changes.

### Environment Variables

This service requires no environment variables. All configuration is code-based.

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.token_counting import get_token_counter

# Use factory function (recommended)
counter = get_token_counter()

# Count tokens
tokens = counter.count_string("Hello world")
```

**Direct Initialisation:**

```python
from backend.services.token_counting import TokenCounter

# Create instance directly
counter = TokenCounter(model="gpt-4o")

# Use counter
result = counter.count_messages(messages)
```

**Model-Specific Initialisation:**

```python
from backend.services.token_counting import get_token_counter

# Counter for GPT-4
gpt4_counter = get_token_counter(model="gpt-4")

# Counter for GPT-3.5
gpt35_counter = get_token_counter(model="gpt-3.5-turbo")
```

**Dependency Injection:**

```python
from backend.services.token_counting import TokenCounter

class MyService:
    """Service that depends on token counting."""

    def __init__(self, token_counter: TokenCounter):
        """Inject token counter dependency."""
        self.token_counter = token_counter

    def process(self, text: str) -> dict:
        """Process text and count tokens."""
        tokens = self.token_counter.count_string(text)
        return {"text": text, "tokens": tokens}

# Use with dependency injection
counter = get_token_counter()
service = MyService(token_counter=counter)
```

## Error Handling

### Exception Hierarchy

This service does not define custom exceptions. All errors are handled internally with logging and fallback behaviour.

```
Exception (built-in)
├── KeyError (from tiktoken for unknown models)
└── Exception (general errors during counting)
```

### Error Handling Strategy

The token counting service follows a **graceful degradation** strategy:

1. **Primary Method:** Use tiktoken encoding for accurate counting
2. **Fallback Method:** Use character-based estimation if tiktoken fails
3. **Logging:** Log all errors with context
4. **No Exceptions:** Never raise exceptions to calling code

**Example Internal Error Handling:**

```python
# From token_counter.py
def count_string(self, text: str) -> int:
    """Count tokens in a string."""
    if not text:
        return 0
    try:
        return len(self.encoding.encode(text))
    except Exception as e:
        logger.error(f"Error counting tokens in string: {e}")
        # Fallback to character-based estimation
        return len(text) // CHARS_PER_TOKEN_FALLBACK
```

### Error Handling Patterns

**Safe Token Counting:**

```python
from backend.services.token_counting import get_token_counter

counter = get_token_counter()

# Safe - never raises exceptions
tokens = counter.count_string(potentially_invalid_text)

# Always returns a valid integer
assert isinstance(tokens, int)
```

**Handling Fallback Behaviour:**

```python
from backend.services.token_counting import get_token_counter
import logging

# Enable logging to see fallback warnings
logging.basicConfig(level=logging.WARNING)

counter = get_token_counter()

# If encoding fails, character-based estimation is used
# Check logs for warnings about fallback
tokens = counter.count_string(problematic_text)
```

**Model Not Found Handling:**

```python
from backend.services.token_counting import get_token_counter
import logging

logging.basicConfig(level=logging.WARNING)

# Unknown model falls back to cl100k_base encoding
counter = get_token_counter(model="unknown-custom-model")
# Warning logged: "Model unknown-custom-model not found in tiktoken, using cl100k_base encoding"

# Still works with fallback encoding
tokens = counter.count_string("Hello world")
```

**Cost Estimation with Unknown Model:**

```python
from backend.services.token_counting import estimate_cost, get_model_pricing

# Unknown model uses default pricing (gpt-4o)
cost = estimate_cost(
    token_counts={"input_tokens": 1000, "output_tokens": 500},
    model="unknown-model",
)

# Check which pricing was used
print(f"Using pricing for: {cost['model']}")  # Shows "unknown-model"

# But prices come from default model
default_pricing = get_model_pricing("gpt-4o")
assert cost['input_cost'] == (1000 / 1_000_000) * default_pricing['input']
```

## Integration Patterns

### Integration with Execution Services

The token counting service is primarily used by execution services to track token usage during agent and workflow
execution.

**Example from [agent/token_utils.py](../../backend/services/execution/agent/token_utils.py):**

```python
from backend.services.token_counting import get_token_counter

def count_string_tokens(text: str) -> int:
    """Count tokens in a string.

    Args:
        text: Text to count tokens for

    Returns:
        Estimated token count
    """
    token_counter = get_token_counter()
    return token_counter.count_string(text)


def count_message_tokens(messages: list) -> Dict[str, int]:
    """Count tokens in messages.

    Args:
        messages: List of messages

    Returns:
        Dictionary with token counts
    """
    token_counter = get_token_counter()
    return token_counter.count_messages(messages)
```

**Example from [async_agent/token_handler.py](../../backend/services/execution/async_agent/token_handler.py):**

```python
from backend.services.token_counting import get_token_counter
from typing import List, Optional
from langchain_core.messages import BaseMessage

class TokenHandler:
    """Handles token counting and metadata extraction."""

    def __init__(self):
        """Initialise the token handler."""
        self.token_counter = None

    def _get_token_counter(self):
        """Lazy load token counter."""
        if self.token_counter is None:
            self.token_counter = get_token_counter()
        return self.token_counter

    def count_input_tokens(
        self,
        messages: List[BaseMessage],
        model_name: Optional[str] = None,
    ) -> TokenCounts:
        """Count tokens in input messages."""
        token_counter = self._get_token_counter()
        result = token_counter.count_messages(messages)
        input_tokens = result.get("total", 0)

        return TokenCounts(
            input_tokens=input_tokens,
            total_tokens=input_tokens,
            model=model_name,
        )
```

### Integration with API Layer

While this service doesn't have direct API endpoints, it can be used in API routes for cost estimation:

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from backend.services.token_counting import get_token_counter, estimate_cost

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


class TokenEstimateRequest(BaseModel):
    """Request for token estimation."""

    messages: List[dict]
    model: str = "gpt-4o"


class TokenEstimateResponse(BaseModel):
    """Response with token counts and cost."""

    total_tokens: int
    breakdown: dict
    estimated_cost: dict


@router.post("/estimate", response_model=TokenEstimateResponse)
async def estimate_tokens(request: TokenEstimateRequest):
    """Estimate tokens and cost for messages."""
    try:
        # Convert dict messages to LangChain messages
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        message_map = {
            "human": HumanMessage,
            "ai": AIMessage,
            "system": SystemMessage,
        }

        messages = []
        for msg in request.messages:
            msg_class = message_map.get(msg["role"], HumanMessage)
            messages.append(msg_class(content=msg["content"]))

        # Count tokens
        counter = get_token_counter(model=request.model)
        result = counter.count_messages(messages)

        # Estimate cost
        cost = estimate_cost(
            {"input_tokens": result["total"], "output_tokens": 0},
            model=request.model,
        )

        return TokenEstimateResponse(
            total_tokens=result["total"],
            breakdown=result["breakdown"],
            estimated_cost=cost,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Dependency Flow

**Services that depend on token_counting:**

- `backend.services.execution.agent` - For tracking agent token usage
- `backend.services.execution.async_agent` - For async agent token tracking

**Services that token_counting depends on:**

- None - This is a low-level utility service

**Data Flow:**

```
Agent Execution
    └── TokenHandler
        └── get_token_counter()
            └── TokenCounter
                ├── count_messages(messages)
                ├── count_string(text)
                └── count_input_output(...)

API Routes (optional)
    └── estimate_cost(token_counts)
        └── MODEL_PRICING lookup
```

### Common Integration Patterns

#### Pattern 1: Simple Token Counting

```python
from backend.services.token_counting import get_token_counter

def validate_input_length(text: str, max_tokens: int = 4000) -> bool:
    """Validate that input doesn't exceed token limit."""
    counter = get_token_counter()
    tokens = counter.count_string(text)

    if tokens > max_tokens:
        raise ValueError(
            f"Input too long: {tokens} tokens exceeds limit of {max_tokens}"
        )

    return True
```

#### Pattern 2: Cost Tracking in Agent Execution

```python
from backend.services.token_counting import get_token_counter, estimate_cost
from langchain_core.messages import BaseMessage
from typing import List

class AgentExecutionTracker:
    """Track token usage and costs during agent execution."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialise tracker."""
        self.model = model
        self.counter = get_token_counter(model=model)
        self.total_cost = 0.0
        self.total_tokens = 0

    def track_llm_call(
        self,
        input_messages: List[BaseMessage],
        output_message: BaseMessage,
    ) -> dict:
        """Track a single LLM call."""
        # Count tokens
        result = self.counter.count_input_output(
            input_messages=input_messages,
            output_content=output_message,
        )

        # Estimate cost
        cost = estimate_cost(result, model=self.model)

        # Update totals
        self.total_tokens += result["total_tokens"]
        self.total_cost += cost["total_cost"]

        return {
            "tokens": result,
            "cost": cost,
            "cumulative_tokens": self.total_tokens,
            "cumulative_cost": self.total_cost,
        }
```

#### Pattern 3: Lazy Loading in Service Classes

```python
from backend.services.token_counting import TokenCounter, get_token_counter
from typing import Optional

class MyService:
    """Service with lazy-loaded token counter."""

    def __init__(self):
        """Initialise without loading counter."""
        self._token_counter: Optional[TokenCounter] = None

    @property
    def token_counter(self) -> TokenCounter:
        """Lazy load token counter on first access."""
        if self._token_counter is None:
            self._token_counter = get_token_counter()
        return self._token_counter

    def process(self, text: str) -> dict:
        """Process text with token counting."""
        tokens = self.token_counter.count_string(text)
        return {"text": text, "tokens": tokens}
```

#### Pattern 4: Batch Token Counting

```python
from backend.services.token_counting import get_token_counter
from typing import List

def count_batch_tokens(texts: List[str]) -> dict:
    """Count tokens for multiple texts efficiently."""
    counter = get_token_counter()

    results = []
    total_tokens = 0

    for text in texts:
        tokens = counter.count_string(text)
        total_tokens += tokens
        results.append({"text": text[:50] + "...", "tokens": tokens})

    return {
        "items": results,
        "total_tokens": total_tokens,
        "average_tokens": total_tokens // len(texts) if texts else 0,
    }
```

## Usage Examples

### Example 1: Basic String Token Counting

```python
from backend.services.token_counting import get_token_counter

# Get counter instance
counter = get_token_counter()

# Count tokens in a string
text = "Hello, how are you doing today?"
tokens = counter.count_string(text)

print(f"Text: {text}")
print(f"Tokens: {tokens}")

# Output:
# Text: Hello, how are you doing today?
# Tokens: 8
```

### Example 2: Message Token Counting with Breakdown

```python
from backend.services.token_counting import get_token_counter
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Create counter
counter = get_token_counter(model="gpt-4o")

# Create conversation
messages = [
    SystemMessage(content="You are a helpful Python programming assistant."),
    HumanMessage(content="How do I reverse a string in Python?"),
    AIMessage(content="You can reverse a string using slicing: reversed_string = my_string[::-1]"),
]

# Count tokens
result = counter.count_messages(messages)

print(f"Total tokens: {result['total']}")
print(f"Number of messages: {result['messages']}")
print("\nBreakdown by type:")
for msg_type, count in result['breakdown'].items():
    if count > 0 and msg_type != 'message_count':
        print(f"  {msg_type}: {count} tokens")

# Output:
# Total tokens: 47
# Number of messages: 3
#
# Breakdown by type:
#   system: 13
#   human: 14
#   ai: 20
```

### Example 3: Cost Estimation

```python
from backend.services.token_counting import get_token_counter, estimate_cost
from langchain_core.messages import HumanMessage, AIMessage

# Simulate an LLM interaction
counter = get_token_counter(model="gpt-4o")

input_messages = [
    HumanMessage(content="Explain quantum computing in 100 words."),
]

output_message = AIMessage(
    content="""Quantum computing harnesses quantum mechanics principles like superposition
    and entanglement to process information. Unlike classical bits (0 or 1), quantum bits
    (qubits) can exist in multiple states simultaneously. This allows quantum computers to
    perform certain calculations exponentially faster than classical computers. Applications
    include cryptography, drug discovery, optimisation problems, and artificial intelligence.
    However, quantum computers are extremely sensitive to environmental interference, requiring
    near-absolute zero temperatures and sophisticated error correction. Major tech companies
    and research institutions are actively developing quantum hardware and algorithms."""
)

# Count tokens
result = counter.count_input_output(
    input_messages=input_messages,
    output_content=output_message,
)

# Estimate cost
cost = estimate_cost(result, model="gpt-4o")

print("Token Usage:")
print(f"  Input tokens: {result['input_tokens']}")
print(f"  Output tokens: {result['output_tokens']}")
print(f"  Total tokens: {result['total_tokens']}")
print("\nCost Estimate (GPT-4o):")
print(f"  Input cost: ${cost['input_cost']:.6f}")
print(f"  Output cost: ${cost['output_cost']:.6f}")
print(f"  Total cost: ${cost['total_cost']:.6f}")

# Output:
# Token Usage:
#   Input tokens: 13
#   Output tokens: 127
#   Total tokens: 140
#
# Cost Estimate (GPT-4o):
#   Input cost: $0.000033
#   Output cost: $0.001270
#   Total cost: $0.001303
```

### Example 4: Tool Call Token Counting

```python
from backend.services.token_counting import get_token_counter
from langchain_core.messages import AIMessage

counter = get_token_counter()

# AI message with tool calls
message_with_tools = AIMessage(
    content="I'll search for that information and calculate the result.",
    tool_calls=[
        {
            "name": "search_web",
            "args": {"query": "latest Python features"},
            "id": "call_search_123",
        },
        {
            "name": "calculate",
            "args": {"expression": "2 ** 10"},
            "id": "call_calc_456",
        },
    ],
)

# Count message tokens (includes tool calls)
result = counter.count_messages([message_with_tools])

# Count just the tool calls
tool_tokens = counter.count_tool_calls(message_with_tools.tool_calls)

print(f"Total message tokens: {result['total']}")
print(f"Tool call tokens: {tool_tokens}")
print(f"Message breakdown: {result['breakdown']}")

# Output:
# Total message tokens: 95
# Tool call tokens: 78
# Message breakdown: {'system': 0, 'human': 0, 'ai': 95, 'tool': 0, 'other': 0, 'message_count': 1}
```

### Example 5: Complete Workflow with Cost Tracking

```python
from backend.services.token_counting import get_token_counter, estimate_cost
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationCostTracker:
    """Track costs for a multi-turn conversation."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialise tracker."""
        self.model = model
        self.counter = get_token_counter(model=model)
        self.conversation_history: List = []
        self.total_cost = 0.0
        self.turn_count = 0

    def add_turn(self, user_input: str, assistant_output: str) -> dict:
        """Add a conversation turn and calculate costs."""
        # Add messages to history
        self.conversation_history.append(HumanMessage(content=user_input))
        self.conversation_history.append(AIMessage(content=assistant_output))

        # Count tokens (full conversation as input + new output)
        result = self.counter.count_input_output(
            input_messages=self.conversation_history[:-1],  # All except last AI message
            output_content=self.conversation_history[-1],  # Last AI message
        )

        # Estimate cost
        cost = estimate_cost(result, model=self.model)

        # Update tracking
        self.turn_count += 1
        self.total_cost += cost["total_cost"]

        turn_summary = {
            "turn": self.turn_count,
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "turn_cost": cost["total_cost"],
            "cumulative_cost": self.total_cost,
        }

        logger.info(
            f"Turn {self.turn_count}: "
            f"{result['input_tokens']} input + {result['output_tokens']} output tokens, "
            f"cost: ${cost['total_cost']:.6f}"
        )

        return turn_summary

    def get_summary(self) -> dict:
        """Get conversation summary."""
        full_count = self.counter.count_messages(self.conversation_history)

        return {
            "model": self.model,
            "turns": self.turn_count,
            "total_messages": len(self.conversation_history),
            "total_tokens": full_count["total"],
            "total_cost": self.total_cost,
            "breakdown": full_count["breakdown"],
        }


# Example usage
async def main():
    """Run conversation tracking example."""
    tracker = ConversationCostTracker(model="gpt-4o")

    # Turn 1
    tracker.add_turn(
        user_input="What is Python?",
        assistant_output="Python is a high-level programming language known for its simplicity and readability.",
    )

    # Turn 2
    tracker.add_turn(
        user_input="What are its main features?",
        assistant_output="Python's main features include dynamic typing, automatic memory management, extensive standard library, and support for multiple programming paradigms.",
    )

    # Turn 3
    tracker.add_turn(
        user_input="Thanks!",
        assistant_output="You're welcome! Feel free to ask if you have more questions.",
    )

    # Get summary
    summary = tracker.get_summary()

    print("\n=== Conversation Summary ===")
    print(f"Model: {summary['model']}")
    print(f"Turns: {summary['turns']}")
    print(f"Total messages: {summary['total_messages']}")
    print(f"Total tokens: {summary['total_tokens']}")
    print(f"Total cost: ${summary['total_cost']:.6f}")
    print(f"\nToken breakdown:")
    for msg_type, count in summary['breakdown'].items():
        if count > 0 and msg_type != 'message_count':
            print(f"  {msg_type}: {count} tokens")


# Run example
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Example 6: Model Comparison

```python
from backend.services.token_counting import get_model_pricing, estimate_cost

# Token counts from a typical request
token_counts = {
    "input_tokens": 500,
    "output_tokens": 1500,
}

# Compare costs across models
models = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]

print("Cost comparison for 500 input + 1500 output tokens:\n")

for model in models:
    pricing = get_model_pricing(model)
    cost = estimate_cost(token_counts, model=model)

    print(f"{model}:")
    print(f"  Pricing: ${pricing['input']}/1M input, ${pricing['output']}/1M output")
    print(f"  Total cost: ${cost['total_cost']:.6f}")
    print()

# Output:
# Cost comparison for 500 input + 1500 output tokens:
#
# gpt-4o:
#   Pricing: $2.5/1M input, $10.0/1M output
#   Total cost: $0.016250
#
# gpt-4o-mini:
#   Pricing: $0.15/1M input, $0.6/1M output
#   Total cost: $0.000975
#
# gpt-4-turbo:
#   Pricing: $10.0/1M input, $30.0/1M output
#   Total cost: $0.050000
#
# gpt-3.5-turbo:
#   Pricing: $0.5/1M input, $1.5/1M output
#   Total cost: $0.002500
```

### Example 7: Testing Usage

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.token_counting import (
    TokenCounter,
    get_token_counter,
    estimate_cost,
)
from langchain_core.messages import HumanMessage, AIMessage


def test_count_string():
    """Test basic string counting."""
    counter = get_token_counter()
    tokens = counter.count_string("Hello world")
    assert tokens > 0
    assert isinstance(tokens, int)


def test_count_empty_string():
    """Test empty string returns zero."""
    counter = get_token_counter()
    tokens = counter.count_string("")
    assert tokens == 0


def test_count_messages():
    """Test message counting."""
    counter = get_token_counter()
    messages = [
        HumanMessage(content="Test message"),
        AIMessage(content="Test response"),
    ]
    result = counter.count_messages(messages)

    assert "total" in result
    assert "breakdown" in result
    assert result["messages"] == 2
    assert result["breakdown"]["human"] > 0
    assert result["breakdown"]["ai"] > 0


def test_estimate_cost():
    """Test cost estimation."""
    token_counts = {"input_tokens": 1000, "output_tokens": 500}
    cost = estimate_cost(token_counts, model="gpt-4o")

    assert "input_cost" in cost
    assert "output_cost" in cost
    assert "total_cost" in cost
    assert cost["total_cost"] > 0
    assert cost["currency"] == "USD"


def test_singleton_pattern():
    """Test that factory returns same instance."""
    counter1 = get_token_counter()
    counter2 = get_token_counter()
    assert counter1 is counter2


@patch("backend.services.token_counting.utils.tiktoken.encoding_for_model")
def test_encoding_error_fallback(mock_encoding):
    """Test fallback when encoding fails."""
    # Make encoding raise an error
    mock_encoding.side_effect = Exception("Encoding failed")

    counter = TokenCounter(model="gpt-4o")

    # Should fall back to character-based counting
    # Won't actually happen because EncodingCache handles this,
    # but demonstrates error handling pattern
    with patch.object(counter, "encoding") as mock_enc:
        mock_enc.encode.side_effect = Exception("Encode failed")
        tokens = counter.count_string("Hello world")

        # Should return fallback value (11 chars / 4 = 2 tokens)
        assert tokens == 2
```

## Performance Considerations

### Performance Characteristics

**Token Counting Complexity:**

- `count_string()`: **O(n)** where n is string length - tiktoken encoding scales linearly with text length
- `count_messages()`: **O(m × n)** where m is number of messages and n is average message length
- `count_tool_calls()`: **O(t × s)** where t is number of tool calls and s is serialised size

**Memory Usage:**

- **Encoding Cache:** tiktoken encoding is loaded once and cached (~10-50 MB depending on model)
- **Message Processing:** Temporary memory proportional to message size during counting
- **No Persistent State:** Counter instances are lightweight wrappers around cached encoding

**I/O Characteristics:**

- **CPU-bound:** Token counting is primarily CPU-intensive (encoding operations)
- **No Network I/O:** All operations are local
- **No Database I/O:** No persistence required

### Optimisation Tips

#### Tip 1: Use Singleton Pattern

**Problem:**

```python
# Inefficient - creates new counter each time
def process_texts(texts: List[str]) -> List[int]:
    results = []
    for text in texts:
        counter = TokenCounter(model="gpt-4o")  # Recreates counter each iteration
        results.append(counter.count_string(text))
    return results
```

**Solution:**

```python
# Efficient - reuse singleton counter
from backend.services.token_counting import get_token_counter

def process_texts(texts: List[str]) -> List[int]:
    counter = get_token_counter()  # Get singleton instance
    return [counter.count_string(text) for text in texts]
```

#### Tip 2: Batch Message Counting

**Problem:**

```python
# Inefficient - multiple overhead calculations
def count_individual_messages(messages: List[BaseMessage]) -> List[int]:
    counter = get_token_counter()
    return [
        counter.count_messages([msg])["total"]  # Adds overhead for each message
        for msg in messages
    ]
```

**Solution:**

```python
# Efficient - single count with proper overhead
def count_all_messages(messages: List[BaseMessage]) -> dict:
    counter = get_token_counter()
    result = counter.count_messages(messages)  # Overhead calculated once

    return {
        "total": result["total"],
        "average": result["total"] // len(messages) if messages else 0,
        "breakdown": result["breakdown"],
    }
```

#### Tip 3: Lazy Loading in Service Classes

**Problem:**

```python
# Inefficient - loads counter even if not used
class MyService:
    def __init__(self):
        self.counter = get_token_counter()  # Loaded immediately

    def maybe_count(self, text: Optional[str]) -> int:
        if text is None:
            return 0  # Counter loaded but not used
        return self.counter.count_string(text)
```

**Solution:**

```python
# Efficient - loads counter only when needed
class MyService:
    def __init__(self):
        self._counter = None  # Not loaded yet

    @property
    def counter(self):
        """Lazy load counter on first access."""
        if self._counter is None:
            self._counter = get_token_counter()
        return self._counter

    def maybe_count(self, text: Optional[str]) -> int:
        if text is None:
            return 0  # Counter not loaded
        return self.counter.count_string(text)  # Loaded here
```

#### Tip 4: Avoid Unnecessary Tool Call Counting

**Problem:**

```python
# Inefficient - counts tool calls separately when already included
def count_message_tokens(message: AIMessage) -> dict:
    counter = get_token_counter()

    # Count full message
    full_count = counter.count_messages([message])

    # Redundant - tool calls already counted in full_count
    tool_count = counter.count_tool_calls(message.tool_calls or [])

    return {
        "total": full_count["total"],
        "tools": tool_count,  # Already included in total!
    }
```

**Solution:**

```python
# Efficient - use metadata from count_messages
def count_message_tokens(message: AIMessage) -> dict:
    counter = get_token_counter()

    # Single count includes tool calls
    result = counter.count_messages([message])

    return {
        "total": result["total"],
        "breakdown": result["breakdown"],
    }
```

### Caching Strategies

The service implements internal caching via `EncodingCache`:

```python
from backend.services.token_counting.utils import EncodingCache

# Encoding is cached automatically
encoding1 = EncodingCache.get_encoding("gpt-4o")  # Loads encoding
encoding2 = EncodingCache.get_encoding("gpt-4o")  # Returns cached

# Same instance
assert encoding1 is encoding2

# Clear cache if needed (testing only)
EncodingCache.clear_cache()
```

### Async Support

This service is **synchronous only**. Token counting operations are CPU-bound and do not benefit from async/await.

**Using in Async Context:**

```python
import asyncio
from backend.services.token_counting import get_token_counter


async def async_function():
    """Token counting in async context."""
    counter = get_token_counter()

    # Synchronous call is fine in async context
    # Token counting is fast enough not to block
    tokens = counter.count_string("Hello world")

    return tokens


# If needed for very large operations, use thread executor
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)


async def count_large_batch(texts: List[str]) -> List[int]:
    """Count tokens for large batch using thread pool."""
    counter = get_token_counter()
    loop = asyncio.get_event_loop()

    # Run blocking count_string in thread pool
    tasks = [
        loop.run_in_executor(executor, counter.count_string, text)
        for text in texts
    ]

    return await asyncio.gather(*tasks)
```

## Testing Patterns

### Unit Testing

```python
import pytest
from backend.services.token_counting import (
    TokenCounter,
    get_token_counter,
    estimate_cost,
    get_model_pricing,
)
from backend.services.token_counting.utils import EncodingCache
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


@pytest.fixture
def counter():
    """Provide a fresh token counter for each test."""
    return get_token_counter()


@pytest.fixture(autouse=True)
def clear_encoding_cache():
    """Clear encoding cache before each test."""
    EncodingCache.clear_cache()
    yield
    EncodingCache.clear_cache()


def test_count_string_basic(counter):
    """Test basic string counting."""
    tokens = counter.count_string("Hello world")
    assert tokens > 0
    assert isinstance(tokens, int)


def test_count_string_empty(counter):
    """Test empty string handling."""
    assert counter.count_string("") == 0
    assert counter.count_string(None) == 0


def test_count_messages_basic(counter):
    """Test message counting."""
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there"),
    ]
    result = counter.count_messages(messages)

    assert result["total"] > 0
    assert result["messages"] == 2
    assert result["breakdown"]["human"] > 0
    assert result["breakdown"]["ai"] > 0


def test_count_messages_with_system(counter):
    """Test system message counting."""
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="Hello"),
    ]
    result = counter.count_messages(messages)

    assert result["breakdown"]["system"] > 0
    assert result["breakdown"]["human"] > 0


def test_cost_estimation():
    """Test cost calculation."""
    counts = {"input_tokens": 1000, "output_tokens": 500}
    cost = estimate_cost(counts, model="gpt-4o")

    assert cost["input_cost"] > 0
    assert cost["output_cost"] > 0
    assert cost["total_cost"] == cost["input_cost"] + cost["output_cost"]
    assert cost["model"] == "gpt-4o"
    assert cost["currency"] == "USD"


def test_get_model_pricing():
    """Test pricing retrieval."""
    pricing = get_model_pricing("gpt-4o")

    assert "input" in pricing
    assert "output" in pricing
    assert pricing["input"] > 0
    assert pricing["output"] > 0


def test_singleton_behavior():
    """Test singleton pattern."""
    counter1 = get_token_counter()
    counter2 = get_token_counter()
    assert counter1 is counter2


def test_encoding_cache():
    """Test encoding cache behavior."""
    EncodingCache.clear_cache()

    enc1 = EncodingCache.get_encoding("gpt-4o")
    enc2 = EncodingCache.get_encoding("gpt-4o")

    assert enc1 is enc2

    # Different model creates new encoding
    enc3 = EncodingCache.get_encoding("gpt-3.5-turbo")
    assert enc3 is not enc1
```

### Mocking Dependencies

```python
from unittest.mock import Mock, patch, MagicMock
import pytest


@patch("backend.services.token_counting.utils.tiktoken.encoding_for_model")
def test_encoding_initialization(mock_encoding_for_model):
    """Test encoding initialization."""
    mock_enc = MagicMock()
    mock_enc.encode.return_value = [1, 2, 3, 4, 5]
    mock_encoding_for_model.return_value = mock_enc

    EncodingCache.clear_cache()
    counter = TokenCounter(model="gpt-4o")

    tokens = counter.count_string("test")
    assert tokens == 5


def test_content_counter_with_mock():
    """Test content counter with mocked string counter."""
    from backend.services.token_counting.content_handlers import ContentTokenCounter

    # Mock string counter
    mock_counter = Mock(return_value=10)
    content_counter = ContentTokenCounter(string_counter=mock_counter)

    # Test with string
    tokens = content_counter.count_content("test string")
    assert tokens == 10
    mock_counter.assert_called_once_with("test string")


def test_tool_call_counter_with_mock():
    """Test tool call counter with mocked string counter."""
    from backend.services.token_counting.message_handlers import ToolCallCounter

    # Mock string counter
    mock_counter = Mock(return_value=20)
    tool_counter = ToolCallCounter(string_counter=mock_counter)

    # Create message with tool calls
    message = AIMessage(
        content="I'll help with that.",
        tool_calls=[{"name": "search", "args": {"query": "test"}, "id": "call_1"}],
    )

    tokens = tool_counter.count_message_tool_calls(message)
    assert tokens == 20  # Mock returns 20
    assert mock_counter.called
```

### Integration Testing

```python
import pytest
from langchain_core.messages import HumanMessage, AIMessage


@pytest.mark.integration
def test_full_token_counting_workflow():
    """Integration test for complete token counting workflow."""
    from backend.services.token_counting import get_token_counter, estimate_cost

    # Setup
    counter = get_token_counter(model="gpt-4o")

    # Create realistic conversation
    messages = [
        HumanMessage(content="What is the capital of France?"),
        AIMessage(content="The capital of France is Paris."),
        HumanMessage(content="What is its population?"),
        AIMessage(content="Paris has a population of approximately 2.2 million people in the city proper, and over 12 million in the metropolitan area."),
    ]

    # Count tokens
    result = counter.count_messages(messages)

    # Verify structure
    assert "total" in result
    assert "breakdown" in result
    assert result["messages"] == 4

    # Verify counts are reasonable
    assert result["total"] > 30  # Should have substantial tokens
    assert result["breakdown"]["human"] > 0
    assert result["breakdown"]["ai"] > 0

    # Estimate cost
    cost = estimate_cost(
        {"input_tokens": result["total"], "output_tokens": 0},
        model="gpt-4o",
    )

    assert cost["total_cost"] > 0
    assert cost["currency"] == "USD"


@pytest.mark.integration
def test_tool_call_integration():
    """Integration test with tool calls."""
    from backend.services.token_counting import get_token_counter

    counter = get_token_counter()

    # Message with actual tool call structure
    message = AIMessage(
        content="I'll search for that information.",
        tool_calls=[
            {
                "name": "web_search",
                "args": {
                    "query": "Python async programming best practices",
                    "max_results": 10,
                },
                "id": "call_abc123def456",
            },
        ],
    )

    # Count with tool calls
    result = counter.count_messages([message])

    # Tool call tokens should be included
    assert result["total"] > 0
    assert result["breakdown"]["ai"] > 0

    # Count tool calls separately for comparison
    tool_tokens = counter.count_tool_calls(message.tool_calls)
    assert tool_tokens > 0
```

## Best Practices

### Do's

✅ **Use the factory function for singleton pattern:**

```python
from backend.services.token_counting import get_token_counter

# Recommended
counter = get_token_counter()
```

✅ **Count full conversations together for accurate overhead:**

```python
# Correct - proper conversation overhead
result = counter.count_messages(all_messages)
total = result["total"]
```

✅ **Use cost estimation before expensive operations:**

```python
from backend.services.token_counting import get_token_counter, estimate_cost

counter = get_token_counter(model="gpt-4o")
count = counter.count_messages(messages)
cost = estimate_cost(count, model="gpt-4o")

if cost["total_cost"] > max_budget:
    raise ValueError(f"Operation exceeds budget: ${cost['total_cost']:.6f}")
```

✅ **Leverage token breakdowns for analytics:**

```python
result = counter.count_messages(messages)

# Analyse token distribution
breakdown = result["breakdown"]
system_overhead = breakdown["system"]
user_tokens = breakdown["human"]
assistant_tokens = breakdown["ai"]

print(f"User input: {user_tokens} tokens ({user_tokens/result['total']*100:.1f}%)")
print(f"Assistant output: {assistant_tokens} tokens ({assistant_tokens/result['total']*100:.1f}%)")
```

✅ **Use lazy loading in service classes:**

```python
class MyService:
    def __init__(self):
        self._counter = None

    @property
    def counter(self):
        if self._counter is None:
            self._counter = get_token_counter()
        return self._counter
```

### Don'ts

❌ **Don't create new counter instances repeatedly:**

```python
# Bad - creates new counter each call
def bad_count(text: str) -> int:
    return TokenCounter().count_string(text)  # Inefficient

# Good - reuse singleton
counter = get_token_counter()

def good_count(text: str) -> int:
    return counter.count_string(text)
```

❌ **Don't count messages individually when you need the total:**

```python
# Bad - incorrect overhead calculation
def bad_total(messages: List[BaseMessage]) -> int:
    counter = get_token_counter()
    return sum(counter.count_messages([msg])["total"] for msg in messages)
    # Adds overhead multiple times!

# Good - count together
def good_total(messages: List[BaseMessage]) -> int:
    counter = get_token_counter()
    return counter.count_messages(messages)["total"]
```

❌ **Don't ignore the breakdown for detailed tracking:**

```python
# Bad - loses valuable information
def bad_track(messages: List[BaseMessage]) -> int:
    return counter.count_messages(messages)["total"]  # Only total

# Good - preserve breakdown
def good_track(messages: List[BaseMessage]) -> dict:
    return counter.count_messages(messages)  # Full result with breakdown
```

❌ **Don't assume pricing is static:**

```python
# Bad - hardcoded pricing
COST_PER_TOKEN = 0.00001

def bad_cost(tokens: int) -> float:
    return tokens * COST_PER_TOKEN  # Pricing changes!

# Good - use pricing functions
from backend.services.token_counting import estimate_cost

def good_cost(token_counts: dict, model: str) -> float:
    return estimate_cost(token_counts, model)["total_cost"]
```

❌ **Don't forget to handle empty inputs:**

```python
# Bad - doesn't check for None/empty
def bad_validate(text: str, limit: int) -> bool:
    tokens = counter.count_string(text)  # May fail if text is None
    return tokens <= limit

# Good - handle edge cases
def good_validate(text: Optional[str], limit: int) -> bool:
    if not text:
        return True
    tokens = counter.count_string(text)
    return tokens <= limit
```

## Related Documentation

### Related Services

- [Execution Service](./execution.md) - Uses token counting for tracking agent execution costs
- [LLM Models Service](./llm_models.md) - Model configuration and provider management

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - Workflow execution that generates token usage

### Architecture Documentation

- [Service Layer Architecture](../architecture/services.md) - Overview of service layer patterns
- [Cost Tracking](../architecture/cost-tracking.md) - System-wide cost tracking architecture

### External Documentation

- [tiktoken Documentation](https://github.com/openai/tiktoken) - Token counting library
- [OpenAI Pricing](https://openai.com/pricing) - Current model pricing
- [LangChain Messages](https://python.langchain.com/docs/modules/model_io/messages/) - Message types

## Summary

The token counting service provides accurate, efficient token estimation and cost calculation for LLM operations in the
AgenticStudio backend. Built on tiktoken, it offers precise token counting for strings, messages, tool calls, and
multi-modal content while supporting multiple OpenAI models.

The service implements several optimisation patterns including singleton caching of tiktoken encodings, strategy pattern
for handling different content types, and graceful fallback to character-based estimation when encoding fails. It
integrates seamlessly with LangChain message structures and provides detailed breakdowns by message type for analytics
and monitoring.

**Key Features:**

- Accurate token counting using tiktoken encoding
- Support for multiple content types (string, dict, list, multi-modal)
- Token breakdown by message type (system, human, AI, tool)
- Cost estimation with current model pricing
- Tool call token counting
- Encoding cache for performance optimisation
- Graceful error handling with fallback estimation
- Zero external configuration required

**Primary Use Cases:**

- Pre-flight cost estimation before LLM API calls
- Token usage tracking for billing and analytics
- Input validation against context window limits
- Cost comparison between different models
- Monitoring token distribution in conversations
- Tracking tool calling overhead

**When to Use This Service:**

- Before making any LLM API call to estimate costs
- When implementing token budgets or limits
- For analytics dashboards showing token usage
- When validating user input lengths
- For comparing model costs in decision logic
- When tracking conversation token consumption
