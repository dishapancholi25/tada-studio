# LLM Models Service Module

## Overview

The LLM Models service provides a unified factory pattern for creating and configuring language model instances across
multiple providers (OpenAI, Azure OpenAI, Anthropic). It abstracts provider-specific implementations behind a consistent
interface, enabling seamless switching between LLM providers and simplifying model management throughout the AgenticStudio
platform.

**Location:** [backend/services/llm_models/](../../backend/services/llm_models/)

**Primary Responsibilities:**

- Creating LLM instances from configuration objects
- Managing provider-specific authentication and credentials
- Binding tools to LLMs for function calling
- Creating embedding instances for vector operations
- Validating LLM configurations before instantiation
- Supporting Azure Managed Identity authentication
- Testing LLM connections
- Provider registration and discovery

**Key Use Cases:**

- Agent compilation: Creating LLMs with tool calling capabilities
- Workflow execution: Instantiating configured LLMs for nodes
- API handlers: Testing and validating LLM configurations
- Embedding services: Creating embedding models for document processing
- Dynamic provider switching: Supporting multiple LLM providers in a single application

## Architecture

### Module Structure

```
backend/services/llm_models/
├── __init__.py              # Public API exports
├── factory.py               # Main LLM factory (329 lines)
├── embedding_factory.py     # Embedding model factory (221 lines)
├── models.py                # Data models (LLMInstance)
├── exceptions.py            # Custom exceptions (32 lines)
├── constants.py             # Provider constants and config (47 lines)
├── config_builders.py       # Helper functions for common configs (106 lines)
├── validators.py            # Configuration validation (53 lines)
└── providers/               # Provider implementations
    ├── __init__.py          # Provider exports
    ├── base.py              # Abstract base provider (66 lines)
    ├── openai.py            # OpenAI provider (53 lines)
    ├── azure_openai.py      # Azure OpenAI with managed identity (235 lines)
    └── anthropic.py         # Anthropic provider (53 lines)
```

**File Purposes:**

- **factory.py** - Core factory for creating LLM instances with provider registry pattern
- **embedding_factory.py** - Specialised factory for embedding models with deployment service integration
- **models.py** - Dataclass wrapper for LLM instances with metadata
- **exceptions.py** - Exception hierarchy for configuration and authentication errors
- **constants.py** - Provider lists, model catalogues, and configuration constants
- **config_builders.py** - Convenience functions for creating common LLM configurations
- **validators.py** - Validation logic for LLM configurations
- **providers/** - Provider-specific implementations following Strategy pattern

### Design Patterns

#### Factory Pattern

The module uses the Factory Pattern to abstract LLM creation:

```python
# Factory creates instances without exposing instantiation logic
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)
```

#### Strategy Pattern

Providers implement a common interface (`LLMProvider`), allowing runtime provider selection:

```python
class LLMProvider(ABC):
    @abstractmethod
    def create(self, config: LLMConfig) -> BaseChatModel:
        pass

    @abstractmethod
    def validate(self, config: LLMConfig) -> list[str]:
        pass
```

#### Registry Pattern

Providers are registered in a class-level dictionary, enabling extensibility:

```python
_providers: Dict[str, Type[LLMProvider]] = {
    "azure_openai": AzureOpenAIProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}
```

#### Dependency Injection

The factory accepts optional dependencies for flexible integration:

```python
def __init__(
    self,
    graph_manager: Optional["GraphManager"] = None,
    model_service: Optional[ModelDeploymentService] = None,
):
```

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                      API/Service Layer                       │
│  (AgentCompiler, GraphManager, ExecutionService)            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                       LLMFactory                             │
│  - create_llm_instance()                                     │
│  - create_tool_calling_llm()                                 │
│  - create_agent_llm()                                        │
└──────────────┬──────────────────┬─────────────────┬─────────┘
               │                  │                 │
               ▼                  ▼                 ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  OpenAIProvider  │  │AzureOpenAIProvider│  │AnthropicProvider│
│  - create()      │  │  - create()       │  │  - create()     │
│  - validate()    │  │  - validate()     │  │  - validate()   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────────────────────────────────────────────────────┐
│               LangChain Chat Models                          │
│  (ChatOpenAI, AzureChatOpenAI, ChatAnthropic)               │
└──────────────────────────────────────────────────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.services.model_deployment` - Model deployment service for config enrichment
- `backend.models.workflow.configs.llm` - LLMConfig data model
- `backend.models.workflow.configs.agent` - AgentConfig data model

**External Dependencies:**

- `langchain_core` - Base interfaces (BaseChatModel, BaseTool, HumanMessage)
- `langchain_openai` - OpenAI and Azure OpenAI chat models
- `langchain_anthropic` - Anthropic chat models
- `azure.identity` - Azure Managed Identity (DefaultAzureCredential)

**Database Dependencies:**

- None directly (delegates to ModelDeploymentService)

**Environment Variables:**

- `OPENAI_API_KEY` - OpenAI API key (fallback)
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key (fallback)
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint (fallback)
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Azure deployment name (fallback)
- `AZURE_OPENAI_API_VERSION` - Azure API version (fallback)
- `ANTHROPIC_API_KEY` - Anthropic API key (fallback)

## Public API

### Exported Classes

- `LLMFactory` - Main factory for creating LLM instances
- `EmbeddingFactory` - Factory for creating embedding model instances
- `LLMInstance` - Wrapper dataclass containing LLM with metadata

### Exported Functions

- `create_azure_openai_config()` - Create Azure OpenAI configuration
- `create_openai_config()` - Create OpenAI configuration
- `create_anthropic_config()` - Create Anthropic configuration

### Constants and Configuration

- `SUPPORTED_PROVIDERS` - List of supported provider names: `["azure_openai", "openai", "anthropic"]`
- `TOOL_CALLING_PROVIDERS` - Providers supporting tool calling: `["azure_openai", "openai", "anthropic"]`
- `TOOL_CHOICE_PROVIDERS` - Providers supporting tool_choice parameter
- `AVAILABLE_MODELS` - Dictionary mapping providers to available model names
- `AZURE_COGNITIVE_SERVICES_SCOPE` - Azure OAuth scope: `"https://cognitiveservices.azure.com/.default"`
- `MIN_TEMPERATURE` - Minimum temperature value: `0.0`
- `MAX_TEMPERATURE` - Maximum temperature value: `2.0`

### Exceptions

```
Exception
└── LLMConfigurationError
    ├── ProviderNotFoundError
    ├── ManagedIdentityError
    ├── CredentialMissingError
    └── ValidationError
```

## Core Classes

### `LLMFactory`

Central factory class for creating and managing language model instances across multiple providers.

**Purpose:** Provides a unified interface for instantiating LLMs regardless of provider, handling authentication, tool
binding, and configuration validation.

**Responsibilities:**

- Creating LLM instances from configuration objects
- Binding tools to LLMs for function calling capabilities
- Filtering and managing tools for agent-specific usage
- Validating LLM configurations before instantiation
- Testing LLM connections
- Registering and discovering providers
- Enriching configurations with deployment metadata

**Initialisation:**

```python
def __init__(
    self,
    graph_manager: Optional["GraphManager"] = None,
    model_service: Optional[ModelDeploymentService] = None,
) -> None:
    """
    Initialise LLM factory.

    Args:
        graph_manager: Optional graph manager for context
        model_service: Optional model deployment service for config enrichment
            (default: creates new ModelDeploymentService instance)
    """
```

**Example:**

```python
from backend.services.llm_models import LLMFactory
from backend.services.model_deployment import ModelDeploymentService

# Basic initialisation
factory = LLMFactory()

# With dependencies
model_service = ModelDeploymentService()
factory = LLMFactory(model_service=model_service)
```

**Key Methods:**

#### `create_llm_instance()`

Create a basic LLM instance from configuration without tool binding.

```python
def create_llm_instance(
    self,
    llm_config: LLMConfig,
) -> LLMInstance:
    """
    Create an LLM instance based on configuration.

    Args:
        llm_config: LLM configuration with provider, model, credentials

    Returns:
        LLMInstance: Configured LLM wrapped with metadata

    Raises:
        ProviderNotFoundError: If provider is not supported
        CredentialMissingError: If required credentials are missing
        ManagedIdentityError: If Azure managed identity auth fails
    """
```

**Parameters:**

- `llm_config` (LLMConfig) - Configuration object containing provider, model_name, credentials, temperature, max_tokens,
  etc.

**Returns:**

- `LLMInstance` - Wrapper containing the LLM instance, configuration, and metadata (supports_tool_calling flag)

**Raises:**

- `ProviderNotFoundError` - When the specified provider is not in the registry
- `CredentialMissingError` - When required API keys or credentials are missing
- `ManagedIdentityError` - When Azure managed identity authentication fails

**Example:**

```python
from backend.services.llm_models import LLMFactory, create_openai_config

# Create configuration
config = create_openai_config(
    model_name="gpt-4",
    temperature=0.7,
    max_tokens=1000,
)

# Create LLM instance
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)

# Use the LLM
from langchain_core.messages import HumanMessage
messages = [HumanMessage(content="Hello!")]
response = llm_instance.llm.invoke(messages)
print(response.content)
```

**Behaviour:**

- Enriches configuration with deployment metadata if `model_deployment_id` is present
- Selects appropriate provider from registry based on `config.provider`
- Delegates creation to provider-specific implementation
- Wraps result in LLMInstance with metadata
- Logs creation with provider and model details

**Use Cases:**

- Creating LLMs for simple text generation without tools
- Testing LLM configurations
- Building custom LLM pipelines

#### `create_tool_calling_llm()`

Create an LLM instance with tools bound for function calling capabilities.

```python
def create_tool_calling_llm(
    self,
    llm_config: LLMConfig,
    tools: List[BaseTool],
    tool_choice: str = "auto",
) -> LLMInstance:
    """
    Create an LLM instance with tools bound for tool calling.

    Args:
        llm_config: LLM configuration
        tools: List of tools to bind to the LLM
        tool_choice: How to select tools - "auto", "any"/"required", or specific tool name

    Returns:
        LLMInstance: LLM instance with tools bound
    """
```

**Parameters:**

- `llm_config` (LLMConfig) - LLM configuration object
- `tools` (List[BaseTool]) - LangChain tools to bind for function calling
- `tool_choice` (str) - Tool selection strategy:
  - `"auto"` (default) - LLM decides whether to use tools
  - `"any"` or `"required"` - LLM must use at least one tool
  - `"tool_name"` - LLM must use specific tool

**Returns:**

- `LLMInstance` - LLM with tools bound and `tools` field populated

**Raises:**

- Same as `create_llm_instance()`

**Example:**

```python
from backend.services.llm_models import LLMFactory, create_openai_config
from backend.services.tools import get_tool_registry

# Get tools
tool_registry = get_tool_registry()
search_tool = tool_registry.get_tool("web_search")
calculator_tool = tool_registry.get_tool("calculator")
tools = [search_tool, calculator_tool]

# Create LLM with tools
config = create_openai_config(model_name="gpt-4")
factory = LLMFactory()
llm_instance = factory.create_tool_calling_llm(
    llm_config=config,
    tools=tools,
    tool_choice="auto",
)

# Use with tool calling
from langchain_core.messages import HumanMessage
messages = [HumanMessage(content="What is 25 * 47?")]
response = llm_instance.llm.invoke(messages)
# Response may contain tool_calls to invoke calculator
```

**Behaviour:**

- Creates base LLM instance using `create_llm_instance()`
- Checks if provider supports tool calling
- Binds tools using LangChain's `bind_tools()` method
- Adds `tool_choice` parameter only if provider supports it
- Logs warnings if provider doesn't support tool calling or tool_choice
- Gracefully degrades to non-tool LLM on binding errors

**Use Cases:**

- Creating agents that can use tools/functions
- Building ReAct-style agents
- Implementing function calling workflows

#### `create_agent_llm()`

Create an LLM instance specifically configured for an agent with filtered tools.

```python
def create_agent_llm(
    self,
    agent_config: AgentConfig,
    available_tools: Optional[List[BaseTool]] = None,
) -> LLMInstance:
    """
    Create an LLM instance specifically for an agent.

    Args:
        agent_config: Agent configuration containing LLM config and tool restrictions
        available_tools: Tools available to the agent (filtered by allowed_tools)

    Returns:
        LLMInstance: Configured LLM for the agent

    Raises:
        ValueError: If agent configuration is missing LLM config
    """
```

**Parameters:**

- `agent_config` (AgentConfig) - Agent configuration containing `llm_config`, `allowed_tools`, and `tool_choice`
- `available_tools` (Optional[List[BaseTool]]) - Pool of available tools to filter from

**Returns:**

- `LLMInstance` - LLM configured for agent with filtered tools bound

**Raises:**

- `ValueError` - When `agent_config.llm_config` is None

**Example:**

```python
from backend.services.llm_models import LLMFactory, create_openai_config
from backend.models.workflow import AgentConfig
from backend.services.tools import get_tool_registry

# Create agent configuration
agent_config = AgentConfig(
    name="research_agent",
    llm_config=create_openai_config(model_name="gpt-4"),
    allowed_tools=["web_search", "wikipedia"],  # Only these tools
    tool_choice="auto",
)

# Get all available tools
tool_registry = get_tool_registry()
all_tools = [
    tool_registry.get_tool("web_search"),
    tool_registry.get_tool("wikipedia"),
    tool_registry.get_tool("calculator"),
    tool_registry.get_tool("database_query"),
]

# Create agent LLM (only web_search and wikipedia will be bound)
factory = LLMFactory()
llm_instance = factory.create_agent_llm(agent_config, all_tools)

# llm_instance.tools will only contain web_search and wikipedia
print(f"Bound tools: {[t.name for t in llm_instance.tools]}")
# Output: Bound tools: ['web_search', 'wikipedia']
```

**Behaviour:**

- Extracts LLM config from agent config
- Filters available_tools based on `agent_config.allowed_tools` list
- Uses tool name matching to filter tools
- Gets `tool_choice` from agent config (defaults to "auto")
- Delegates to `create_tool_calling_llm()` with filtered tools

**Use Cases:**

- Agent compilation in workflow execution
- Restricting agent tool access for security
- Creating specialised agents with curated toolsets

#### `validate_llm_config()`

Validate an LLM configuration without creating an instance.

```python
def validate_llm_config(
    self,
    llm_config: LLMConfig,
) -> list[str]:
    """
    Validate LLM configuration.

    Args:
        llm_config: LLM configuration to validate

    Returns:
        List of validation error messages (empty if valid)
    """
```

**Parameters:**

- `llm_config` (LLMConfig) - Configuration to validate

**Returns:**

- `list[str]` - List of error messages (empty list if configuration is valid)

**Example:**

```python
from backend.services.llm_models import LLMFactory, create_openai_config

# Create potentially invalid config
config = create_openai_config(
    model_name="invalid-model",
    temperature=3.0,  # Too high
)

# Validate before creating
factory = LLMFactory()
errors = factory.validate_llm_config(config)

if errors:
    print("Configuration errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Configuration valid!")
    llm_instance = factory.create_llm_instance(config)
```

**Behaviour:**

- Validates provider is supported
- Checks model name against AVAILABLE_MODELS catalogue
- Validates temperature range (0.0 - 2.0)
- Validates max_tokens is positive
- Delegates to provider-specific validation (credentials, endpoints)

**Use Cases:**

- API request validation before persisting
- Configuration UI feedback
- Pre-flight checks before workflow execution

#### `test_llm_connection()`

Test an LLM configuration by sending a simple test message.

```python
def test_llm_connection(
    self,
    llm_config: LLMConfig,
) -> Dict[str, Any]:
    """
    Test LLM connection with a simple query.

    Args:
        llm_config: LLM configuration to test

    Returns:
        Dict with test results containing:
            - success: bool
            - response: str (if successful)
            - error: str (if failed)
            - provider: str
            - model: str
    """
```

**Parameters:**

- `llm_config` (LLMConfig) - Configuration to test

**Returns:**

- `Dict[str, Any]` - Test result dictionary with success status and details

**Example:**

```python
from backend.services.llm_models import LLMFactory, create_openai_config

config = create_openai_config(
    model_name="gpt-4",
    api_key="sk-...",
)

factory = LLMFactory()
result = factory.test_llm_connection(config)

if result["success"]:
    print(f"✓ Connection successful!")
    print(f"  Provider: {result['provider']}")
    print(f"  Model: {result['model']}")
    print(f"  Response: {result['response']}")
else:
    print(f"✗ Connection failed!")
    print(f"  Error: {result['error']}")
```

**Behaviour:**

- Creates LLM instance from config
- Sends test message: "Hello! Please respond with 'Connection successful'."
- Invokes LLM and captures response
- Returns success/failure with details
- Catches and returns all exceptions as error messages

**Use Cases:**

- Testing API keys before saving
- Troubleshooting connection issues
- Validating deployment configurations

#### `register_provider()` (classmethod)

Register a custom LLM provider at runtime.

```python
@classmethod
def register_provider(
    cls,
    name: str,
    provider_class: Type[LLMProvider],
) -> None:
    """
    Register a new LLM provider.

    Args:
        name: Provider name (e.g., "custom_provider")
        provider_class: Provider class (must inherit from LLMProvider)

    Raises:
        TypeError: If provider doesn't inherit from LLMProvider
    """
```

**Parameters:**

- `name` (str) - Provider identifier for configuration (e.g., "groq", "together")
- `provider_class` (Type[LLMProvider]) - Class implementing LLMProvider interface

**Returns:**

- None

**Raises:**

- `TypeError` - When provider_class doesn't inherit from LLMProvider

**Example:**

```python
from backend.services.llm_models import LLMFactory
from backend.services.llm_models.providers.base import LLMProvider
from backend.models.workflow.configs.llm import LLMConfig
from langchain_core.language_models import BaseChatModel
from langchain_together import ChatTogether

class TogetherProvider(LLMProvider):
    """Provider for Together AI models."""

    def create(self, config: LLMConfig) -> BaseChatModel:
        api_key = self._get_credential(config, "api_key", "TOGETHER_API_KEY")
        if not api_key:
            raise CredentialMissingError("Together AI requires api_key")

        return ChatTogether(
            api_key=api_key,
            model=config.model_name,
            temperature=config.temperature,
        )

    def validate(self, config: LLMConfig) -> list[str]:
        errors = []
        api_key = self._get_credential(config, "api_key", "TOGETHER_API_KEY")
        if not api_key:
            errors.append("Together AI requires api_key")
        return errors

# Register custom provider
LLMFactory.register_provider("together", TogetherProvider)

# Now use it
from backend.models.workflow.configs.llm import LLMConfig
config = LLMConfig(
    provider="together",
    model_name="mistralai/Mixtral-8x7B-Instruct-v0.1",
    temperature=0.7,
    credentials={"api_key": "..."},
)
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)
```

**Behaviour:**

- Validates provider_class inherits from LLMProvider
- Adds provider to class-level `_providers` registry
- Logs registration
- Makes provider immediately available to all factory instances

**Use Cases:**

- Adding support for new LLM providers
- Custom provider implementations
- Plugin architecture for extensibility

#### `get_available_providers()` (classmethod)

Get list of registered provider names.

```python
@classmethod
def get_available_providers(cls) -> list[str]:
    """
    Get list of available provider names.

    Returns:
        List of provider name strings
    """
```

**Example:**

```python
from backend.services.llm_models import LLMFactory

providers = LLMFactory.get_available_providers()
print(f"Available providers: {providers}")
# Output: Available providers: ['azure_openai', 'openai', 'anthropic']
```

#### `get_available_models()` (staticmethod)

Get catalogue of available models per provider.

```python
@staticmethod
def get_available_models(
    provider: Optional[str] = None,
) -> Dict[str, List[str]]:
    """
    Get available models for each provider.

    Args:
        provider: Optional provider filter (returns all if None)

    Returns:
        Dict mapping provider names to lists of model names
    """
```

**Parameters:**

- `provider` (Optional[str]) - Filter for specific provider (returns all if None)

**Returns:**

- `Dict[str, List[str]]` - Dictionary mapping provider names to model lists

**Example:**

```python
from backend.services.llm_models import LLMFactory

# Get all models
all_models = LLMFactory.get_available_models()
print(all_models)
# {
#     "openai": ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo", ...],
#     "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", ...],
#     ...
# }

# Get models for specific provider
openai_models = LLMFactory.get_available_models("openai")
print(openai_models)
# {"openai": ["gpt-4", "gpt-4-turbo-preview", "gpt-3.5-turbo", ...]}
```

**Use Cases:**

- Populating UI dropdowns for model selection
- Validating model names in configurations
- API endpoints returning available options

**Class Attributes:**

- `_providers: Dict[str, Type[LLMProvider]]` - Class-level provider registry

**Properties:**

- `graph_manager: Optional[GraphManager]` - Optional graph manager for context
- `model_service: ModelDeploymentService` - Model deployment service for config enrichment

---

### `EmbeddingFactory`

Factory for creating embedding model instances with model deployment integration and managed identity support.

**Purpose:** Provides specialised functionality for creating embedding models (vector generators) from deployment
configurations, with support for Azure Managed Identity.

**Responsibilities:**

- Creating embedding instances from deployment IDs
- Supporting Azure OpenAI and OpenAI embedding models
- Managing Azure Managed Identity authentication for embeddings
- Validating embedding configurations
- Integrating with ModelDeploymentService for credential management

**Initialisation:**

```python
def __init__(
    self,
    model_service: Optional[ModelDeploymentService] = None,
) -> None:
    """
    Initialise embedding factory.

    Args:
        model_service: Optional model deployment service
            (default: creates new ModelDeploymentService instance)
    """
```

**Example:**

```python
from backend.services.llm_models import EmbeddingFactory
from backend.services.model_deployment import ModelDeploymentService

# Basic initialisation
factory = EmbeddingFactory()

# With existing service
model_service = ModelDeploymentService()
factory = EmbeddingFactory(model_service=model_service)
```

**Key Methods:**

#### `create_embedding_instance()`

Create an embedding model instance from a deployment ID.

```python
def create_embedding_instance(
    self,
    deployment_id: str,
):
    """
    Create an embedding instance from a model deployment.

    Args:
        deployment_id: ID of the model deployment

    Returns:
        Embedding instance (AzureOpenAIEmbeddings or OpenAIEmbeddings)

    Raises:
        ValueError: If deployment not found, not embedding type, or inactive
        ManagedIdentityError: If managed identity authentication fails
    """
```

**Parameters:**

- `deployment_id` (str) - Database ID of the model deployment record

**Returns:**

- `AzureOpenAIEmbeddings` or `OpenAIEmbeddings` - LangChain embedding instance

**Raises:**

- `ValueError` - When deployment not found, wrong type, or inactive
- `ManagedIdentityError` - When Azure managed identity authentication fails

**Example:**

```python
from backend.services.llm_models import EmbeddingFactory

# Create embedding instance from deployment
factory = EmbeddingFactory()
embeddings = factory.create_embedding_instance("emb-deploy-123")

# Use for embedding text
text_embeddings = embeddings.embed_documents([
    "This is document 1",
    "This is document 2",
])
print(f"Generated {len(text_embeddings)} embeddings")

# Embed query
query_embedding = embeddings.embed_query("search query")
```

**Behaviour:**

- Fetches deployment config from ModelDeploymentService
- Validates deployment is type "embedding" and active
- Extracts provider, model, credentials, and settings
- Routes to provider-specific creation method
- Supports Azure Managed Identity as fallback for Azure OpenAI
- Logs creation details including key source

**Use Cases:**

- Document processing pipelines requiring embeddings
- Vector database population
- Semantic search implementations
- RAG (Retrieval Augmented Generation) systems

#### `validate_embedding_config()`

Validate embedding configuration dictionary.

```python
def validate_embedding_config(
    self,
    config: dict,
) -> list[str]:
    """
    Validate embedding configuration.

    Args:
        config: Configuration dict with provider, model_name, credentials, settings

    Returns:
        List of error messages (empty if valid)
    """
```

**Parameters:**

- `config` (dict) - Configuration dictionary with keys:
  - `provider` (str) - Provider name ("azure_openai" or "openai")
  - `model_name` (str) - Model name
  - `credentials` (dict) - API keys
  - `settings` (dict) - Provider-specific settings

**Returns:**

- `list[str]` - List of validation error messages (empty if valid)

**Example:**

```python
from backend.services.llm_models import EmbeddingFactory

config = {
    "provider": "openai",
    "model_name": "text-embedding-3-small",
    "credentials": {"api_key": "sk-..."},
    "settings": {},
}

factory = EmbeddingFactory()
errors = factory.validate_embedding_config(config)

if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Configuration valid!")
```

**Behaviour:**

- Validates provider is present and supported
- Validates model_name is present
- For Azure OpenAI: validates endpoint, checks api_key or managed identity flag
- For OpenAI: validates api_key is present
- Returns all errors as list

**Use Cases:**

- Pre-deployment configuration validation
- API request validation
- Configuration UI feedback

**Class Attributes:**

- None

**Properties:**

- `model_service: ModelDeploymentService` - Service for fetching deployment configs

---

### `LLMInstance`

Dataclass wrapper for LLM instances with associated metadata.

**Purpose:** Provides a standardised container for LLM instances with their configuration and capabilities.

**Initialisation:**

```python
@dataclass
class LLMInstance:
    """Wrapper for LLM instance with metadata."""

    llm: Any  # BaseChatModel instance
    config: LLMConfig  # Original configuration
    tools: List[Any] = field(default_factory=list)  # Bound tools
    supports_tool_calling: bool = False  # Provider capability flag
```

**Example:**

```python
from backend.services.llm_models import LLMFactory, create_openai_config

config = create_openai_config(model_name="gpt-4")
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)

# Access fields
print(f"Model: {llm_instance.config.model_name}")
print(f"Provider: {llm_instance.config.provider}")
print(f"Supports tool calling: {llm_instance.supports_tool_calling}")
print(f"Tools bound: {len(llm_instance.tools)}")

# Use the LLM
from langchain_core.messages import HumanMessage
response = llm_instance.llm.invoke([HumanMessage(content="Hello!")])
```

**Class Attributes:**

- `llm: Any` - The actual LangChain BaseChatModel instance
- `config: LLMConfig` - Configuration used to create the LLM
- `tools: List[Any]` - List of BaseTool instances bound to this LLM (empty if no tools)
- `supports_tool_calling: bool` - Flag indicating if provider supports tool calling

**Use Cases:**

- Passing LLM instances with metadata through pipelines
- Tracking which tools are available to an LLM
- Conditionally enabling tool calling based on provider capabilities

---

## Functions

### `create_azure_openai_config()`

Convenience function for creating Azure OpenAI configurations with sensible defaults.

**Signature:**

```python
def create_azure_openai_config(
    model_name: str = "gpt-4",
    api_key: Optional[str] = None,
    endpoint: Optional[str] = None,
    api_version: str = "2024-02-15-preview",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    """
    Create Azure OpenAI configuration.

    Args:
        model_name: Azure OpenAI model name (default: "gpt-4")
        api_key: Optional API key (uses AZURE_OPENAI_API_KEY env var if not provided)
        endpoint: Optional Azure endpoint (uses AZURE_OPENAI_ENDPOINT env var if not provided)
        api_version: Azure API version (default: "2024-02-15-preview")
        temperature: Sampling temperature 0.0-2.0 (default: 0.7)
        max_tokens: Maximum tokens to generate (default: None/unlimited)

    Returns:
        LLMConfig configured for Azure OpenAI
    """
```

**Parameters:**

- `model_name` (str) - Azure deployment name or model name
- `api_key` (Optional[str]) - API key (falls back to environment variable)
- `endpoint` (Optional[str]) - Azure OpenAI endpoint URL
- `api_version` (str) - Azure API version
- `temperature` (float) - Sampling temperature
- `max_tokens` (Optional[int]) - Token limit

**Returns:**

- `LLMConfig` - Configuration object ready for use with LLMFactory

**Example:**

```python
from backend.services.llm_models import create_azure_openai_config, LLMFactory

# Basic usage with environment variables
config = create_azure_openai_config(
    model_name="gpt-4",
    temperature=0.7,
)

# Explicit credentials
config = create_azure_openai_config(
    model_name="gpt-4-turbo",
    api_key="your-api-key",
    endpoint="https://your-resource.openai.azure.com/",
    api_version="2024-02-15-preview",
    temperature=0.5,
    max_tokens=2000,
)

# Use with factory
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)
```

**Use Cases:**

- Quick setup for Azure OpenAI in scripts
- Testing with different Azure configurations
- API request handling with sensible defaults

---

### `create_openai_config()`

Convenience function for creating OpenAI configurations with sensible defaults.

**Signature:**

```python
def create_openai_config(
    model_name: str = "gpt-4",
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    """
    Create OpenAI configuration.

    Args:
        model_name: OpenAI model name (default: "gpt-4")
        api_key: Optional API key (uses OPENAI_API_KEY env var if not provided)
        temperature: Sampling temperature 0.0-2.0 (default: 0.7)
        max_tokens: Maximum tokens to generate (default: None/unlimited)

    Returns:
        LLMConfig configured for OpenAI
    """
```

**Parameters:**

- `model_name` (str) - OpenAI model name (e.g., "gpt-4", "gpt-3.5-turbo")
- `api_key` (Optional[str]) - API key (falls back to OPENAI_API_KEY environment variable)
- `temperature` (float) - Sampling temperature
- `max_tokens` (Optional[int]) - Token limit

**Returns:**

- `LLMConfig` - Configuration object ready for use with LLMFactory

**Example:**

```python
from backend.services.llm_models import create_openai_config, LLMFactory

# Using environment variable for API key
config = create_openai_config(
    model_name="gpt-4-turbo-preview",
    temperature=0.3,
)

# Explicit API key
config = create_openai_config(
    model_name="gpt-3.5-turbo",
    api_key="sk-...",
    temperature=0.9,
    max_tokens=500,
)

# Create instance
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)
```

**Use Cases:**

- Quick setup for OpenAI in scripts
- Testing with different models
- Development and prototyping

---

### `create_anthropic_config()`

Convenience function for creating Anthropic configurations with sensible defaults.

**Signature:**

```python
def create_anthropic_config(
    model_name: str = "claude-3-sonnet-20240229",
    api_key: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> LLMConfig:
    """
    Create Anthropic configuration.

    Args:
        model_name: Anthropic model name (default: "claude-3-sonnet-20240229")
        api_key: Optional API key (uses ANTHROPIC_API_KEY env var if not provided)
        temperature: Sampling temperature 0.0-2.0 (default: 0.7)
        max_tokens: Maximum tokens to generate (default: None/unlimited)

    Returns:
        LLMConfig configured for Anthropic
    """
```

**Parameters:**

- `model_name` (str) - Anthropic model name (e.g., "claude-3-opus-20240229")
- `api_key` (Optional[str]) - API key (falls back to ANTHROPIC_API_KEY environment variable)
- `temperature` (float) - Sampling temperature
- `max_tokens` (Optional[int]) - Token limit

**Returns:**

- `LLMConfig` - Configuration object ready for use with LLMFactory

**Example:**

```python
from backend.services.llm_models import create_anthropic_config, LLMFactory

# Using environment variable
config = create_anthropic_config(
    model_name="claude-3-opus-20240229",
    temperature=0.5,
)

# Explicit API key
config = create_anthropic_config(
    model_name="claude-3-haiku-20240307",
    api_key="sk-ant-...",
    temperature=0.8,
    max_tokens=1024,
)

# Create instance
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)
```

**Use Cases:**

- Quick setup for Anthropic models
- Testing Claude models
- Switching between Claude variants

---

## Configuration

### Configuration Classes

The module uses the `LLMConfig` Pydantic model from `backend.models.workflow.configs.llm`:

```python
class LLMConfig(BaseModel):
    """LLM configuration model."""

    provider: str  # Provider name (e.g., "openai", "azure_openai")
    model_name: str  # Model name (e.g., "gpt-4")
    temperature: float = 0.7  # Sampling temperature (0.0-2.0)
    max_tokens: Optional[int] = None  # Max tokens to generate
    credentials: Dict[str, Any] = {}  # API keys and auth
    config: Dict[str, Any] = {}  # Provider-specific config
    timeout: Optional[int] = None  # Request timeout in seconds
    max_retries: int = 3  # Max retry attempts

    # Azure-specific fields
    deployment_name: Optional[str] = None  # Azure deployment name
    api_version: Optional[str] = None  # Azure API version

    # Deployment reference
    model_deployment_id: Optional[str] = None  # Reference to deployment record
```

**Fields:**

- `provider` (str) - Provider identifier: "openai", "azure_openai", "anthropic"
- `model_name` (str) - Model name or deployment name
- `temperature` (float) - Sampling temperature, default 0.7, range 0.0-2.0
- `max_tokens` (Optional[int]) - Maximum tokens to generate, None for unlimited
- `credentials` (Dict[str, Any]) - API keys and authentication data
- `config` (Dict[str, Any]) - Provider-specific settings (api_version, use_managed_identity, etc.)
- `timeout` (Optional[int]) - Request timeout in seconds
- `max_retries` (int) - Number of retry attempts on failures, default 3
- `deployment_name` (Optional[str]) - Azure-specific deployment name
- `api_version` (Optional[str]) - Azure API version
- `model_deployment_id` (Optional[str]) - Reference to model deployment database record for enrichment

### Environment Variables

The service supports the following environment variables as fallbacks:

**OpenAI:**

- `OPENAI_API_KEY` - OpenAI API key (required if not in credentials)

**Azure OpenAI:**

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key (optional if using managed identity)
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL (required)
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Deployment name (optional, falls back to model_name)
- `AZURE_OPENAI_API_VERSION` - API version (optional, defaults to "2024-02-15-preview")

**Anthropic:**

- `ANTHROPIC_API_KEY` - Anthropic API key (required if not in credentials)

### Initialisation Patterns

#### Basic Initialisation

```python
from backend.services.llm_models import LLMFactory

# Simple factory creation
factory = LLMFactory()

# Create LLM from config
from backend.services.llm_models import create_openai_config
config = create_openai_config(model_name="gpt-4")
llm_instance = factory.create_llm_instance(config)
```

#### Advanced Initialisation with Dependencies

```python
from backend.services.llm_models import LLMFactory
from backend.services.model_deployment import ModelDeploymentService
from backend.services.graph.manager import GraphManager

# Initialise dependencies
model_service = ModelDeploymentService()
graph_manager = GraphManager()

# Create factory with dependencies
factory = LLMFactory(
    graph_manager=graph_manager,
    model_service=model_service,
)

# Now factory can enrich configs from model deployments
from backend.models.workflow.configs.llm import LLMConfig
config = LLMConfig(
    provider="azure_openai",
    model_name="gpt-4",
    model_deployment_id="deploy-123",  # Will be enriched
)
llm_instance = factory.create_llm_instance(config)
```

#### Embedding Factory Initialisation

```python
from backend.services.llm_models import EmbeddingFactory

# Basic initialisation
embedding_factory = EmbeddingFactory()

# Create embedding from deployment
embeddings = embedding_factory.create_embedding_instance("emb-deploy-456")
```

#### Azure Managed Identity Pattern

```python
from backend.services.llm_models import LLMFactory
from backend.models.workflow.configs.llm import LLMConfig

# Configure for managed identity
config = LLMConfig(
    provider="azure_openai",
    model_name="gpt-4",
    credentials={},  # No API key
    config={
        "endpoint": "https://your-resource.openai.azure.com/",
        "use_managed_identity": True,  # Explicit flag
        "api_version": "2024-02-15-preview",
    },
)

# Factory will use Azure DefaultAzureCredential
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)
# Logs: "Using Azure Managed Identity for LLM (deployment=gpt-4)"
```

## Error Handling

### Exception Hierarchy

```
Exception
└── LLMConfigurationError (Base exception for LLM configuration issues)
    ├── ProviderNotFoundError (Requested provider not in registry)
    ├── ManagedIdentityError (Azure managed identity authentication failed)
    ├── CredentialMissingError (Required API key/credentials not provided)
    └── ValidationError (Configuration validation failed)
```

### Exception Details

#### `LLMConfigurationError`

Base exception for all LLM configuration-related errors.

**Inherits from:** `Exception`

**When raised:**

- General configuration issues
- Base class for more specific errors

**Example:**

```python
from backend.services.llm_models import LLMFactory, LLMConfigurationError

try:
    factory = LLMFactory()
    llm_instance = factory.create_llm_instance(config)
except LLMConfigurationError as e:
    # Catches all LLM configuration errors
    logger.error(f"LLM configuration error: {e}")
```

#### `ProviderNotFoundError`

Raised when the specified provider is not registered in the factory.

**Inherits from:** `LLMConfigurationError`

**When raised:**

- Provider name in config doesn't match any registered provider
- Typo in provider name
- Custom provider not registered

**Example:**

```python
from backend.services.llm_models import LLMFactory, ProviderNotFoundError
from backend.models.workflow.configs.llm import LLMConfig

config = LLMConfig(
    provider="unknown_provider",  # Not registered
    model_name="some-model",
)

try:
    factory = LLMFactory()
    llm_instance = factory.create_llm_instance(config)
except ProviderNotFoundError as e:
    print(f"Error: {e}")
    # Output: Unsupported LLM provider: unknown_provider.
    #         Supported providers: azure_openai, openai, anthropic

    # Show available providers
    providers = LLMFactory.get_available_providers()
    print(f"Available: {providers}")
```

#### `ManagedIdentityError`

Raised when Azure Managed Identity authentication fails.

**Inherits from:** `LLMConfigurationError`

**When raised:**

- DefaultAzureCredential fails to acquire token
- Not authenticated with `az login` in development
- Managed identity not configured in production
- Incorrect Azure permissions

**Example:**

```python
from backend.services.llm_models import LLMFactory, ManagedIdentityError
from backend.models.workflow.configs.llm import LLMConfig

config = LLMConfig(
    provider="azure_openai",
    model_name="gpt-4",
    config={
        "endpoint": "https://your-resource.openai.azure.com/",
        "use_managed_identity": True,
    },
)

try:
    factory = LLMFactory()
    llm_instance = factory.create_llm_instance(config)
except ManagedIdentityError as e:
    logger.error(f"Managed identity error: {e}")
    print("Make sure you have run 'az login' or configured managed identity")
    print("Required permission: Cognitive Services User role")

    # Fallback to API key
    config.credentials["api_key"] = os.getenv("AZURE_OPENAI_API_KEY")
    config.config["use_managed_identity"] = False
    llm_instance = factory.create_llm_instance(config)
```

#### `CredentialMissingError`

Raised when required credentials (API keys, endpoints) are missing.

**Inherits from:** `LLMConfigurationError`

**When raised:**

- API key not provided in credentials or environment
- Azure endpoint not configured
- Required authentication data missing

**Example:**

```python
from backend.services.llm_models import LLMFactory, CredentialMissingError, create_openai_config

# Config without API key and no environment variable
config = create_openai_config(
    model_name="gpt-4",
    api_key=None,  # No key provided
)
# Assuming OPENAI_API_KEY not in environment

try:
    factory = LLMFactory()
    llm_instance = factory.create_llm_instance(config)
except CredentialMissingError as e:
    logger.error(f"Credential missing: {e}")
    # Prompt user for API key
    api_key = input("Please enter OpenAI API key: ")
    config.credentials["api_key"] = api_key
    llm_instance = factory.create_llm_instance(config)
```

#### `ValidationError`

Raised when configuration validation fails.

**Inherits from:** `LLMConfigurationError`

**When raised:**

- Temperature outside valid range (0.0-2.0)
- Invalid model name for provider
- Negative max_tokens
- Other configuration constraint violations

**Example:**

```python
from backend.services.llm_models import LLMFactory, ValidationError, create_openai_config

# Invalid configuration
config = create_openai_config(
    model_name="gpt-4",
    temperature=3.0,  # Too high!
)

try:
    factory = LLMFactory()
    errors = factory.validate_llm_config(config)

    if errors:
        raise ValidationError(f"Configuration invalid: {', '.join(errors)}")

    llm_instance = factory.create_llm_instance(config)
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    # Fix configuration
    config.temperature = 0.7
    llm_instance = factory.create_llm_instance(config)
```

### Error Handling Patterns

#### Recommended Error Handling Pattern

```python
from backend.services.llm_models import (
    LLMFactory,
    LLMConfigurationError,
    ProviderNotFoundError,
    CredentialMissingError,
    ManagedIdentityError,
    ValidationError,
    create_openai_config,
)
import logging

logger = logging.getLogger(__name__)

def create_llm_with_error_handling(config):
    """Create LLM with comprehensive error handling."""

    factory = LLMFactory()

    try:
        # Validate first
        errors = factory.validate_llm_config(config)
        if errors:
            logger.warning(f"Configuration issues: {errors}")
            return {"success": False, "errors": errors}

        # Create instance
        llm_instance = factory.create_llm_instance(config)

        return {"success": True, "llm": llm_instance}

    except ValidationError as e:
        # Handle validation errors
        logger.error(f"Validation failed: {e}")
        return {"success": False, "error": "Invalid configuration", "details": str(e)}

    except CredentialMissingError as e:
        # Handle missing credentials
        logger.error(f"Credentials missing: {e}")
        return {
            "success": False,
            "error": "Missing credentials",
            "details": str(e),
            "action": "Please provide API key or configure managed identity",
        }

    except ManagedIdentityError as e:
        # Handle managed identity issues
        logger.error(f"Managed identity failed: {e}")
        return {
            "success": False,
            "error": "Authentication failed",
            "details": str(e),
            "action": "Run 'az login' or provide API key",
        }

    except ProviderNotFoundError as e:
        # Handle unknown provider
        logger.error(f"Provider not found: {e}")
        available = LLMFactory.get_available_providers()
        return {
            "success": False,
            "error": "Provider not supported",
            "details": str(e),
            "available_providers": available,
        }

    except LLMConfigurationError as e:
        # Catch-all for other configuration errors
        logger.error(f"Configuration error: {e}")
        return {"success": False, "error": "Configuration error", "details": str(e)}

    except Exception as e:
        # Catch unexpected errors
        logger.exception(f"Unexpected error creating LLM: {e}")
        return {"success": False, "error": "Unexpected error", "details": str(e)}

# Usage
config = create_openai_config(model_name="gpt-4")
result = create_llm_with_error_handling(config)

if result["success"]:
    llm_instance = result["llm"]
    print("LLM created successfully!")
else:
    print(f"Error: {result['error']}")
    print(f"Details: {result['details']}")
    if "action" in result:
        print(f"Action: {result['action']}")
```

## Integration Patterns

### Integration with API Layer

The LLM Models service is commonly used in API handlers for configuration testing and retrieval.

```python
# Example from backend/api/graph/handlers/llm_config.py
from fastapi import APIRouter, HTTPException
from backend.services.llm_models import LLMFactory, LLMConfigurationError
from backend.models.workflow.configs.llm import LLMConfig

router = APIRouter()

@router.get("/llm/providers")
async def get_llm_providers():
    """Get available LLM providers and their models."""
    factory = LLMFactory()
    providers_dict = factory.get_available_models()

    # Transform for API response
    providers = []
    for provider_name, models in providers_dict.items():
        providers.append({
            "name": provider_name,
            "display_name": provider_name.replace("_", " ").title(),
            "models": models,
        })

    return {"success": True, "providers": providers}

@router.post("/llm/test")
async def test_llm_connection(llm_config: dict):
    """Test LLM connection."""
    try:
        config = LLMConfig(**llm_config)
        factory = LLMFactory()
        result = factory.test_llm_connection(config)
        return {"success": True, "test_result": result}
    except LLMConfigurationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Integration with Agent Service

The Agent Compiler uses LLMFactory to create LLMs with tool calling during compilation.

```python
# Example from backend/services/agent/compiler.py
from backend.services.llm_models import LLMFactory, LLMConfigurationError
from backend.services.tools import get_tool_registry
from backend.models.workflow import AgentConfig

class AgentCompiler:
    """Compiles agents with LLMs and tools."""

    def __init__(self):
        self.llm_factory = LLMFactory()
        self.tool_registry = get_tool_registry()

    async def compile_agent(self, agent_node, graph):
        """Compile agent with LLM and tools."""
        try:
            # Get agent configuration
            agent_config: AgentConfig = agent_node.data.agent_config

            # Get available tools from graph
            available_tools = self._get_available_tools(agent_node, graph)

            # Create LLM with tools for agent
            llm_instance = self.llm_factory.create_agent_llm(
                agent_config=agent_config,
                available_tools=available_tools,
            )

            # Build compiled agent
            compiled_agent = CompiledAgent(
                node_id=agent_node.id,
                name=agent_node.name,
                llm=llm_instance.llm,
                tools=llm_instance.tools,
                supports_tool_calling=llm_instance.supports_tool_calling,
            )

            return CompilationResult(success=True, agent=compiled_agent)

        except LLMConfigurationError as e:
            logger.error(f"Failed to create LLM for agent: {e}")
            return CompilationResult(
                success=False,
                errors=[f"LLM configuration error: {e}"],
            )

    def _get_available_tools(self, agent_node, graph):
        """Get tools connected to agent in graph."""
        # Find tool nodes connected to this agent
        tool_nodes = find_connected_tools(agent_node, graph)

        # Get tool instances from registry
        tools = []
        for tool_node in tool_nodes:
            tool = self.tool_registry.get_tool(tool_node.data.tool_id)
            if tool:
                tools.append(tool)

        return tools
```

### Integration with Execution Service

The Execution Service uses LLMFactory to create LLMs during workflow execution.

```python
# Example from backend/services/execution/async_agent/llm_builder.py
from backend.services.llm_models import LLMFactory, LLMInstance
from backend.models.workflow import EnhancedNodeData

class LLMBuilder:
    """Builds LLM instances for agent execution."""

    def __init__(self):
        self.factory = LLMFactory()

    def build_llm_for_node(
        self,
        node: EnhancedNodeData,
        tools: list,
    ) -> LLMInstance:
        """Build LLM instance for agent node."""

        # Extract LLM config from node
        agent_config = node.data.agent_config

        if not agent_config or not agent_config.llm_config:
            raise ValueError(f"Node {node.id} missing LLM configuration")

        # Create LLM with tools
        llm_instance = self.factory.create_tool_calling_llm(
            llm_config=agent_config.llm_config,
            tools=tools,
            tool_choice=agent_config.tool_choice or "auto",
        )

        return llm_instance
```

### Dependency Flow

```
┌─────────────────────────────────────────────────────────┐
│                    API Handlers                          │
│  (LLM configuration, testing, provider discovery)       │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   LLM Models Service                     │
│  ┌─────────────┐  ┌──────────────────┐                 │
│  │ LLMFactory  │  │ EmbeddingFactory │                 │
│  └─────────────┘  └──────────────────┘                 │
└────────────┬───────────────────┬────────────────────────┘
             │                   │
             ▼                   ▼
┌────────────────────┐  ┌───────────────────────┐
│ ModelDeployment    │  │  Azure Identity       │
│ Service            │  │  (Managed Identity)   │
└────────────────────┘  └───────────────────────┘

Services depending on LLM Models:
┌─────────────────────────────────────────────────────────┐
│  Agent Service (AgentCompiler)                          │
│  Execution Service (AsyncAgentExecutor, LLMBuilder)     │
│  Graph Service (GraphManager)                           │
│  Document Service (embedding integration)               │
└─────────────────────────────────────────────────────────┘
```

**Upstream Dependencies (used by LLM Models):**

- ModelDeploymentService - For enriching configs with deployment metadata
- Azure Identity libraries - For managed identity authentication

**Downstream Dependencies (depend on LLM Models):**

- Agent Service - For compiling agents with LLMs
- Execution Service - For creating LLMs during workflow execution
- Graph Service - For LLM configuration validation
- Document Service - For embedding models
- API Handlers - For provider discovery and connection testing

### Common Integration Patterns

#### Pattern 1: Configuration Validation Before Persistence

When saving LLM configurations via API, validate before persisting to database.

```python
from fastapi import APIRouter, HTTPException
from backend.services.llm_models import LLMFactory
from backend.models.workflow.configs.llm import LLMConfig
from backend.services.database import get_db_session

router = APIRouter()

@router.post("/agent/llm-config")
async def save_agent_llm_config(agent_id: str, llm_config_dict: dict):
    """Save LLM configuration for an agent."""

    # Parse configuration
    try:
        llm_config = LLMConfig(**llm_config_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid config: {e}")

    # Validate configuration
    factory = LLMFactory()
    errors = factory.validate_llm_config(llm_config)

    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Configuration invalid", "errors": errors},
        )

    # Optional: Test connection
    test_result = factory.test_llm_connection(llm_config)
    if not test_result["success"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Connection test failed",
                "error": test_result["error"],
            },
        )

    # Persist to database
    db = get_db_session()
    # ... save to database ...

    return {"success": True, "message": "Configuration saved"}
```

#### Pattern 2: Dynamic Provider Selection

Allow users to switch providers without code changes.

```python
from backend.services.llm_models import LLMFactory, create_openai_config, create_anthropic_config

def create_llm_for_user_preference(user_preferences: dict):
    """Create LLM based on user's provider preference."""

    factory = LLMFactory()

    # User selects provider dynamically
    preferred_provider = user_preferences.get("llm_provider", "openai")

    if preferred_provider == "openai":
        config = create_openai_config(
            model_name=user_preferences.get("model", "gpt-4"),
            temperature=user_preferences.get("temperature", 0.7),
        )
    elif preferred_provider == "anthropic":
        config = create_anthropic_config(
            model_name=user_preferences.get("model", "claude-3-sonnet-20240229"),
            temperature=user_preferences.get("temperature", 0.7),
        )
    else:
        raise ValueError(f"Unsupported provider: {preferred_provider}")

    llm_instance = factory.create_llm_instance(config)
    return llm_instance
```

#### Pattern 3: Tool Filtering for Security

Restrict agent tool access based on user permissions or agent type.

```python
from backend.services.llm_models import LLMFactory
from backend.services.tools import get_tool_registry
from backend.models.workflow import AgentConfig

def create_restricted_agent_llm(agent_config: AgentConfig, user_role: str):
    """Create agent LLM with role-based tool filtering."""

    tool_registry = get_tool_registry()
    factory = LLMFactory()

    # Define role-based tool restrictions
    role_tool_whitelist = {
        "analyst": ["web_search", "calculator", "wikipedia"],
        "developer": ["web_search", "code_executor", "database_query"],
        "admin": None,  # All tools
    }

    # Get all available tools
    all_tools = tool_registry.get_all_tools()

    # Filter based on role
    allowed_tool_names = role_tool_whitelist.get(user_role)
    if allowed_tool_names is not None:
        # Filter to whitelist
        available_tools = [
            tool for tool in all_tools
            if tool.name in allowed_tool_names
        ]
    else:
        # Admin gets all tools
        available_tools = all_tools

    # Create LLM with filtered tools
    llm_instance = factory.create_agent_llm(
        agent_config=agent_config,
        available_tools=available_tools,
    )

    return llm_instance
```

#### Pattern 4: Deployment-Based Configuration

Use model deployments for centralised credential management.

```python
from backend.services.llm_models import LLMFactory
from backend.services.model_deployment import ModelDeploymentService
from backend.models.workflow.configs.llm import LLMConfig

def create_llm_from_deployment(deployment_id: str):
    """Create LLM from deployment with centralised credentials."""

    # Initialise with model service
    model_service = ModelDeploymentService()
    factory = LLMFactory(model_service=model_service)

    # Create config referencing deployment
    config = LLMConfig(
        provider="azure_openai",  # Will be enriched from deployment
        model_name="gpt-4",  # Will be enriched from deployment
        model_deployment_id=deployment_id,  # Reference to deployment
        temperature=0.7,
    )

    # Factory enriches config automatically
    llm_instance = factory.create_llm_instance(config)

    return llm_instance
```

## Usage Examples

### Example 1: Basic Usage

Simple LLM creation and invocation.

```python
from backend.services.llm_models import LLMFactory, create_openai_config
from langchain_core.messages import HumanMessage

# Step 1: Create configuration
config = create_openai_config(
    model_name="gpt-4",
    temperature=0.7,
    max_tokens=500,
)

# Step 2: Initialise factory
factory = LLMFactory()

# Step 3: Create LLM instance
llm_instance = factory.create_llm_instance(config)

# Step 4: Use the LLM
messages = [
    HumanMessage(content="Explain quantum computing in simple terms.")
]
response = llm_instance.llm.invoke(messages)

# Step 5: Process result
print(f"Model: {llm_instance.config.model_name}")
print(f"Response: {response.content}")
```

### Example 2: Advanced Usage with Tool Calling

Create an agent LLM with tool calling capabilities.

```python
from backend.services.llm_models import (
    LLMFactory,
    create_openai_config,
    LLMConfigurationError,
)
from backend.services.tools import get_tool_registry
from langchain_core.messages import HumanMessage
import logging

logger = logging.getLogger(__name__)

# Step 1: Configure LLM
config = create_openai_config(
    model_name="gpt-4",
    temperature=0.3,  # Lower for more deterministic tool calling
)

# Step 2: Get tools from registry
tool_registry = get_tool_registry()
tools = [
    tool_registry.get_tool("web_search"),
    tool_registry.get_tool("calculator"),
    tool_registry.get_tool("wikipedia"),
]

# Step 3: Create factory and LLM with tools
factory = LLMFactory()

try:
    llm_instance = factory.create_tool_calling_llm(
        llm_config=config,
        tools=tools,
        tool_choice="auto",  # LLM decides when to use tools
    )

    # Step 4: Invoke with query requiring tools
    messages = [
        HumanMessage(
            content="What is the population of Tokyo, and what is that number divided by 7?"
        )
    ]

    response = llm_instance.llm.invoke(messages)

    # Step 5: Process tool calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        logger.info(f"LLM called {len(response.tool_calls)} tools")
        for tool_call in response.tool_calls:
            logger.info(f"  - {tool_call['name']}: {tool_call['args']}")

    print(f"Response: {response.content}")

except LLMConfigurationError as e:
    logger.error(f"Configuration error: {e}")
    # Handle error appropriately
```

### Example 3: Complete Workflow with Error Handling

Production-ready workflow with validation, testing, and error handling.

```python
from backend.services.llm_models import (
    LLMFactory,
    create_azure_openai_config,
    LLMConfigurationError,
    CredentialMissingError,
    ManagedIdentityError,
)
from backend.services.database import get_db_session
from backend.models.workflow import AgentConfig
import logging
import os

logger = logging.getLogger(__name__)

async def setup_agent_with_llm(agent_id: str, user_config: dict):
    """
    Complete workflow for setting up an agent with LLM.

    This example shows:
    - Configuration creation
    - Validation
    - Connection testing
    - Database persistence
    - Error handling
    """

    factory = LLMFactory()

    try:
        # Step 1: Create configuration from user input
        logger.info(f"Creating LLM configuration for agent {agent_id}")

        config = create_azure_openai_config(
            model_name=user_config.get("model_name", "gpt-4"),
            api_key=user_config.get("api_key"),
            endpoint=user_config.get("endpoint"),
            temperature=user_config.get("temperature", 0.7),
            max_tokens=user_config.get("max_tokens", 2000),
        )

        # Step 2: Validate configuration
        logger.info("Validating LLM configuration")
        errors = factory.validate_llm_config(config)

        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            return {
                "success": False,
                "error": "Configuration invalid",
                "validation_errors": errors,
            }

        # Step 3: Test connection
        logger.info("Testing LLM connection")
        test_result = factory.test_llm_connection(config)

        if not test_result["success"]:
            logger.error(f"Connection test failed: {test_result['error']}")
            return {
                "success": False,
                "error": "Connection test failed",
                "details": test_result["error"],
            }

        logger.info(f"Connection test successful: {test_result['response']}")

        # Step 4: Create agent configuration
        agent_config = AgentConfig(
            name=f"Agent {agent_id}",
            llm_config=config,
            allowed_tools=user_config.get("allowed_tools", []),
            tool_choice=user_config.get("tool_choice", "auto"),
        )

        # Step 5: Save to database
        db = get_db_session()
        # ... save agent_config to database ...
        logger.info(f"Agent {agent_id} configuration saved to database")

        # Step 6: Create LLM instance to verify
        llm_instance = factory.create_llm_instance(config)

        return {
            "success": True,
            "message": "Agent LLM configured successfully",
            "agent_id": agent_id,
            "provider": config.provider,
            "model": config.model_name,
            "supports_tool_calling": llm_instance.supports_tool_calling,
        }

    except CredentialMissingError as e:
        logger.error(f"Credentials missing: {e}")
        return {
            "success": False,
            "error": "Missing credentials",
            "details": str(e),
            "action": "Please provide API key or configure managed identity",
        }

    except ManagedIdentityError as e:
        logger.error(f"Managed identity authentication failed: {e}")
        return {
            "success": False,
            "error": "Authentication failed",
            "details": str(e),
            "action": "Run 'az login' or provide API key in configuration",
        }

    except LLMConfigurationError as e:
        logger.error(f"LLM configuration error: {e}")
        return {
            "success": False,
            "error": "Configuration error",
            "details": str(e),
        }

    except Exception as e:
        logger.exception(f"Unexpected error setting up agent LLM: {e}")
        return {
            "success": False,
            "error": "Unexpected error",
            "details": str(e),
        }

# Usage
user_config = {
    "model_name": "gpt-4",
    "temperature": 0.7,
    "allowed_tools": ["web_search", "calculator"],
    "tool_choice": "auto",
}

result = await setup_agent_with_llm("agent-123", user_config)

if result["success"]:
    print(f"✓ {result['message']}")
    print(f"  Provider: {result['provider']}")
    print(f"  Model: {result['model']}")
else:
    print(f"✗ {result['error']}")
    print(f"  Details: {result['details']}")
    if "action" in result:
        print(f"  Action: {result['action']}")
```

### Example 4: Testing Usage

Unit tests for LLM factory functionality.

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.llm_models import (
    LLMFactory,
    create_openai_config,
    LLMConfigurationError,
    ProviderNotFoundError,
    CredentialMissingError,
)
from backend.models.workflow.configs.llm import LLMConfig

class TestLLMFactory:
    """Test cases for LLMFactory."""

    @pytest.fixture
    def factory(self):
        """Factory fixture."""
        return LLMFactory()

    @pytest.fixture
    def valid_config(self):
        """Valid configuration fixture."""
        return create_openai_config(
            model_name="gpt-4",
            api_key="sk-test-key",
            temperature=0.7,
        )

    def test_create_llm_instance_success(self, factory, valid_config):
        """Test successful LLM instance creation."""
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_chat.return_value = MagicMock()

            llm_instance = factory.create_llm_instance(valid_config)

            assert llm_instance is not None
            assert llm_instance.config == valid_config
            assert llm_instance.supports_tool_calling is True
            assert mock_chat.called

    def test_create_llm_instance_invalid_provider(self, factory):
        """Test creation with invalid provider."""
        config = LLMConfig(
            provider="invalid_provider",
            model_name="some-model",
        )

        with pytest.raises(ProviderNotFoundError) as exc_info:
            factory.create_llm_instance(config)

        assert "Unsupported LLM provider" in str(exc_info.value)

    def test_validate_llm_config_valid(self, factory, valid_config):
        """Test validation of valid configuration."""
        errors = factory.validate_llm_config(valid_config)

        assert errors == []

    def test_validate_llm_config_invalid_temperature(self, factory):
        """Test validation with invalid temperature."""
        config = create_openai_config(
            model_name="gpt-4",
            api_key="sk-test",
            temperature=3.0,  # Too high
        )

        errors = factory.validate_llm_config(config)

        assert len(errors) > 0
        assert any("temperature" in error.lower() for error in errors)

    def test_create_tool_calling_llm(self, factory, valid_config):
        """Test LLM creation with tools."""
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        tools = [mock_tool]

        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_llm.bind_tools.return_value = mock_llm
            mock_chat.return_value = mock_llm

            llm_instance = factory.create_tool_calling_llm(
                llm_config=valid_config,
                tools=tools,
                tool_choice="auto",
            )

            assert llm_instance.tools == tools
            assert mock_llm.bind_tools.called

    def test_get_available_providers(self):
        """Test getting available providers."""
        providers = LLMFactory.get_available_providers()

        assert isinstance(providers, list)
        assert "openai" in providers
        assert "azure_openai" in providers
        assert "anthropic" in providers

    def test_get_available_models(self):
        """Test getting available models."""
        all_models = LLMFactory.get_available_models()

        assert isinstance(all_models, dict)
        assert "openai" in all_models
        assert isinstance(all_models["openai"], list)
        assert len(all_models["openai"]) > 0

        # Test filtering by provider
        openai_models = LLMFactory.get_available_models("openai")
        assert "openai" in openai_models
        assert "anthropic" not in openai_models

    @patch("backend.services.llm_models.factory.HumanMessage")
    def test_test_llm_connection_success(self, mock_message, factory, valid_config):
        """Test successful connection test."""
        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Connection successful"
            mock_llm.invoke.return_value = mock_response
            mock_chat.return_value = mock_llm

            result = factory.test_llm_connection(valid_config)

            assert result["success"] is True
            assert result["provider"] == "openai"
            assert result["model"] == "gpt-4"
            assert "response" in result

    def test_test_llm_connection_failure(self, factory):
        """Test failed connection test."""
        config = create_openai_config(
            model_name="gpt-4",
            api_key="invalid-key",
        )

        with patch("langchain_openai.ChatOpenAI") as mock_chat:
            mock_chat.side_effect = Exception("Authentication failed")

            result = factory.test_llm_connection(config)

            assert result["success"] is False
            assert "error" in result

if __name__ == "__main__":
    pytest.main([__file__])
```

## Performance Considerations

### Performance Characteristics

**LLM Instance Creation:**

- **Time Complexity:** O(1) - Provider lookup and instantiation are constant time
- **Memory Usage:** Minimal - Creates single LLM client instance
- **I/O Characteristics:** Network-bound during token acquisition for Azure Managed Identity

**Tool Binding:**

- **Time Complexity:** O(n) where n is the number of tools
- **Memory Usage:** O(n) - Stores tool references in LLMInstance
- **I/O Characteristics:** CPU-bound for tool schema serialisation

**Configuration Validation:**

- **Time Complexity:** O(1) - Fixed validation checks
- **Memory Usage:** Minimal - Only validation error list
- **I/O Characteristics:** CPU-bound

**Connection Testing:**

- **Time Complexity:** O(1) - Single test request
- **Memory Usage:** Minimal - Single message and response
- **I/O Characteristics:** Network-bound - Full LLM API call

### Optimisation Tips

#### Tip 1: Reuse Factory Instances

**Problem:**

```python
# Inefficient: Creating new factory for each request
def handle_request(config):
    factory = LLMFactory()  # Creates new ModelDeploymentService each time
    return factory.create_llm_instance(config)
```

**Solution:**

```python
# Efficient: Reuse factory instance
class ServiceManager:
    def __init__(self):
        self.llm_factory = LLMFactory()  # Created once

    def handle_request(self, config):
        return self.llm_factory.create_llm_instance(config)
```

#### Tip 2: Cache LLM Instances

**Problem:**

```python
# Inefficient: Creating new LLM for repeated identical configs
for i in range(100):
    llm_instance = factory.create_llm_instance(config)
    result = llm_instance.llm.invoke(messages)
```

**Solution:**

```python
# Efficient: Cache and reuse LLM instances
from functools import lru_cache
import hashlib
import json

def config_to_cache_key(config: LLMConfig) -> str:
    """Generate cache key from config."""
    config_dict = config.dict()
    config_str = json.dumps(config_dict, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()

@lru_cache(maxsize=32)
def get_cached_llm_instance(config_key: str, config_json: str) -> LLMInstance:
    """Get cached LLM instance."""
    config = LLMConfig(**json.loads(config_json))
    factory = LLMFactory()
    return factory.create_llm_instance(config)

# Usage
config = create_openai_config(model_name="gpt-4")
config_key = config_to_cache_key(config)
config_json = config.json()

for i in range(100):
    llm_instance = get_cached_llm_instance(config_key, config_json)
    result = llm_instance.llm.invoke(messages)
```

#### Tip 3: Validate Before Testing Connection

**Problem:**

```python
# Inefficient: Testing connection with invalid config (network call wasted)
result = factory.test_llm_connection(invalid_config)
# Fails with network error after timeout
```

**Solution:**

```python
# Efficient: Validate first to catch errors early
errors = factory.validate_llm_config(config)
if errors:
    return {"success": False, "errors": errors}  # Fast fail

# Only test if valid
result = factory.test_llm_connection(config)
```

#### Tip 4: Batch Tool Binding

**Problem:**

```python
# Inefficient: Creating separate LLM for each tool combination
tool_combinations = [
    [search_tool],
    [search_tool, calculator_tool],
    [search_tool, calculator_tool, wikipedia_tool],
]

llms = []
for tools in tool_combinations:
    llm = factory.create_tool_calling_llm(config, tools)
    llms.append(llm)
```

**Solution:**

```python
# Efficient: Create once with all tools, use subset dynamically
all_tools = [search_tool, calculator_tool, wikipedia_tool]
llm_instance = factory.create_tool_calling_llm(config, all_tools)

# LangChain allows dynamic tool filtering at invoke time
# Just create one LLM with all possible tools
```

### Async/Await Support

The LLM Models service does not directly implement async methods, but it's compatible with async workflows since
LangChain supports async invocation.

```python
from backend.services.llm_models import LLMFactory, create_openai_config
from langchain_core.messages import HumanMessage
import asyncio

async def async_llm_workflow():
    """Example async workflow with LLM."""

    # Factory creation is synchronous
    factory = LLMFactory()
    config = create_openai_config(model_name="gpt-4")
    llm_instance = factory.create_llm_instance(config)

    # LangChain LLMs support async invocation
    messages = [HumanMessage(content="Hello, world!")]
    response = await llm_instance.llm.ainvoke(messages)  # Note: ainvoke

    print(f"Response: {response.content}")
    return response

# Run async
asyncio.run(async_llm_workflow())
```

**Concurrent LLM Creation:**

```python
import asyncio
from backend.services.llm_models import LLMFactory, create_openai_config

async def create_multiple_llms():
    """Create multiple LLM instances concurrently."""

    factory = LLMFactory()

    configs = [
        create_openai_config(model_name="gpt-4"),
        create_openai_config(model_name="gpt-3.5-turbo"),
    ]

    # Create in thread pool (since factory is sync)
    loop = asyncio.get_event_loop()
    llm_instances = await asyncio.gather(*[
        loop.run_in_executor(None, factory.create_llm_instance, config)
        for config in configs
    ])

    return llm_instances

# Usage
llms = asyncio.run(create_multiple_llms())
```

### Connection Pooling

The service relies on LangChain's underlying HTTP client connection pooling. No explicit configuration needed, but you
can tune LangChain client settings:

```python
from backend.services.llm_models import LLMFactory
from backend.models.workflow.configs.llm import LLMConfig

# Configure timeout and retries for connection management
config = LLMConfig(
    provider="openai",
    model_name="gpt-4",
    credentials={"api_key": "sk-..."},
    timeout=30,  # 30 second timeout
    max_retries=3,  # Retry up to 3 times
)

factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.llm_models import LLMFactory, create_openai_config

@pytest.fixture
def llm_factory():
    """Fixture for LLM factory."""
    return LLMFactory()

@pytest.fixture
def openai_config():
    """Fixture for OpenAI configuration."""
    return create_openai_config(
        model_name="gpt-4",
        api_key="sk-test-key",
        temperature=0.7,
    )

def test_factory_initialisation(llm_factory):
    """Test factory initialises correctly."""
    assert llm_factory is not None
    assert llm_factory.model_service is not None
    assert isinstance(llm_factory._providers, dict)

def test_create_llm_instance(llm_factory, openai_config):
    """Test LLM instance creation."""
    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        mock_chat.return_value = MagicMock()

        llm_instance = llm_factory.create_llm_instance(openai_config)

        assert llm_instance is not None
        assert llm_instance.config == openai_config
        assert llm_instance.supports_tool_calling is True

def test_validation(llm_factory, openai_config):
    """Test configuration validation."""
    errors = llm_factory.validate_llm_config(openai_config)
    assert errors == []

    # Test invalid config
    openai_config.temperature = 5.0  # Too high
    errors = llm_factory.validate_llm_config(openai_config)
    assert len(errors) > 0
```

### Mocking Dependencies

```python
@patch("backend.services.llm_models.factory.ModelDeploymentService")
def test_with_mocked_deployment_service(mock_service_class, llm_factory, openai_config):
    """Test with mocked model deployment service."""

    # Configure mock
    mock_service = Mock()
    mock_service.enrich_llm_config.return_value = openai_config
    mock_service_class.return_value = mock_service

    # Create factory with mocked service
    factory = LLMFactory(model_service=mock_service)

    # Test enrichment
    openai_config.model_deployment_id = "test-deploy-123"

    with patch("langchain_openai.ChatOpenAI"):
        llm_instance = factory.create_llm_instance(openai_config)

        # Verify enrichment was called
        mock_service.enrich_llm_config.assert_called_once_with(openai_config)
```

### Integration Testing

```python
@pytest.mark.integration
async def test_real_llm_creation():
    """Integration test with real LLM (requires API key)."""
    import os

    # Skip if no API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    from backend.services.llm_models import LLMFactory, create_openai_config
    from langchain_core.messages import HumanMessage

    # Create real LLM
    config = create_openai_config(
        model_name="gpt-3.5-turbo",  # Use cheaper model for testing
        api_key=api_key,
        temperature=0.7,
        max_tokens=50,
    )

    factory = LLMFactory()
    llm_instance = factory.create_llm_instance(config)

    # Test real invocation
    messages = [HumanMessage(content="Say hello")]
    response = await llm_instance.llm.ainvoke(messages)

    assert response is not None
    assert len(response.content) > 0
    print(f"Real LLM response: {response.content}")
```

## Best Practices

### Do's

✅ **Always validate configurations before persistence**

```python
from backend.services.llm_models import LLMFactory

factory = LLMFactory()
errors = factory.validate_llm_config(config)

if not errors:
    # Safe to persist
    save_to_database(config)
else:
    # Show errors to user
    return {"errors": errors}
```

✅ **Use config builder functions for consistency**

```python
from backend.services.llm_models import create_openai_config, create_azure_openai_config

# Good: Use builders
openai_config = create_openai_config(model_name="gpt-4", temperature=0.7)

# Avoid: Manual construction
config = LLMConfig(
    provider="openai",
    model_name="gpt-4",
    temperature=0.7,
    credentials={},
    config={},
    # ... easy to miss fields
)
```

✅ **Handle exceptions appropriately with specific error types**

```python
from backend.services.llm_models import (
    LLMFactory,
    CredentialMissingError,
    ManagedIdentityError,
)

try:
    llm_instance = factory.create_llm_instance(config)
except CredentialMissingError:
    # Prompt for credentials
    return {"error": "Please provide API key"}
except ManagedIdentityError:
    # Suggest authentication
    return {"error": "Please run 'az login'"}
```

### Don'ts

❌ **Don't create factory instances repeatedly**

```python
# Bad: Creates ModelDeploymentService on every call
def process_request(config):
    factory = LLMFactory()  # Expensive!
    return factory.create_llm_instance(config)

# Good: Reuse factory instance
class RequestHandler:
    def __init__(self):
        self.factory = LLMFactory()  # Created once

    def process_request(self, config):
        return self.factory.create_llm_instance(config)
```

❌ **Don't ignore validation errors**

```python
# Bad: Ignoring validation errors
factory = LLMFactory()
llm_instance = factory.create_llm_instance(config)  # May fail at runtime

# Good: Validate first
errors = factory.validate_llm_config(config)
if errors:
    raise ValueError(f"Invalid config: {errors}")
llm_instance = factory.create_llm_instance(config)
```

❌ **Don't hardcode API keys in configurations**

```python
# Bad: Hardcoded credentials
config = create_openai_config(
    model_name="gpt-4",
    api_key="sk-hardcoded-key-12345",  # Never do this!
)

# Good: Use environment variables or secure config
config = create_openai_config(
    model_name="gpt-4",
    # Reads from OPENAI_API_KEY env var
)

# Better: Use model deployments for centralised credential management
config = LLMConfig(
    provider="openai",
    model_name="gpt-4",
    model_deployment_id="secure-deployment-123",
)
```

## Related Documentation

### Related Services

- [Agent Service](./agent.md) - Uses LLMFactory for agent compilation
- [Execution Service](./execution.md) - Uses LLMFactory for workflow execution
- [Model Deployment Service](./model_deployment.md) - Provides deployment-based configuration enrichment
- [Graph Service](./graph.md) - Integrates with LLMFactory for validation

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - LLM configuration endpoints for workflow nodes
- [Model Deployments API](../agents-guide/api/model_deployments.md) - Deployment management for LLMs

### External Documentation

- [LangChain Documentation](https://python.langchain.com/docs/) - Underlying LLM framework
- [OpenAI API Documentation](https://platform.openai.com/docs/) - OpenAI models and configuration
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/) - Azure-specific LLM setup
- [Anthropic Documentation](https://docs.anthropic.com/) - Claude models and API
- [Azure Identity Documentation](https://learn.microsoft.com/python/api/azure-identity/) - Managed identity setup

## Summary

The LLM Models service is the central abstraction layer for language model management in AgenticStudio. It provides a
unified factory pattern that enables seamless creation and configuration of LLMs across multiple providers (OpenAI,
Azure OpenAI, Anthropic) without exposing provider-specific implementation details to consuming services.

The service architecture leverages the Strategy pattern for providers and the Factory pattern for instantiation, making
it highly extensible. New providers can be added by implementing the `LLMProvider` interface and registering them with
`LLMFactory.register_provider()`. The service integrates deeply with the ModelDeploymentService for centralised
credential management and supports Azure Managed Identity for secure, keyless authentication in Azure environments.

Tool calling capabilities are first-class citizens in the service design, with dedicated methods for binding tools to
LLMs and filtering tools based on agent permissions. This makes the service ideal for building agentic workflows where
LLMs need access to external functions and APIs.

**Key Features:**

- **Multi-provider support** - OpenAI, Azure OpenAI, and Anthropic with consistent interface
- **Tool calling integration** - First-class support for LangChain tool binding with tool_choice configuration
- **Azure Managed Identity** - Secure authentication without storing API keys
- **Configuration validation** - Pre-flight validation and connection testing
- **Deployment integration** - Centralised credential management via ModelDeploymentService
- **Extensibility** - Provider registration system for custom LLM providers
- **Embedding support** - Specialised factory for embedding models

**Primary Use Cases:**

- **Agent compilation** - Creating LLMs with bound tools for agent execution
- **Workflow execution** - Instantiating configured LLMs for workflow nodes
- **API configuration** - Testing and validating LLM configurations via API endpoints
- **Multi-tenant applications** - Supporting user-specific provider preferences
- **Secure deployments** - Using managed identity in production Azure environments

**When to Use This Service:**

- When you need to create LLM instances from configuration objects
- When building agents that require tool calling capabilities
- When supporting multiple LLM providers in your application
- When implementing secure, keyless authentication with Azure
- When validating LLM configurations before persistence or execution
- When creating embedding models for document processing
