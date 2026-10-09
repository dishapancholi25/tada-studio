# Agent Import Documentation

This document describes how to import agent configurations into Agentic Studio using JSON format.

## Overview

Agentic Studio supports importing agent configurations from JSON files. The import format is designed to be compatible with
the A2A (Agent-to-Agent) Protocol Agent Card format where possible, while extending it to support Agentic Studio's advanced
features.

Before importing, ensure your JSON is valid and includes at minimum the `name`, `description`, and `system_prompt` fields.
Full validation rules are described in the [Security & Validation](#security--validation) section below.

## Schema Format

### Basic Structure

The import schema follows this structure:

```json
{
  "name": "Agent Name",
  "description": "Agent description",
  "version": "1.0.0",
  "system_prompt": "Your system prompt here",
  "llm_config": {
    "provider": "azure_openai",
    "model_name": "gpt-4o-latest",
    "temperature": 0.7
  },
  "agent_config": {
    "agent_type": "conversational",
    "max_iterations": 10,
    "tools": [
      "web_search",
      "file_reader"
    ]
  },
  "metadata": {
    "category": [
      "Customer Service",
      "Support"
    ],
    "tags": [
      "chatbot",
      "support",
      "customer-service"
    ],
    "complexity": "beginner",
    "icon_color": "cyan"
  }
}
```

### Required Fields

- **name** (string): The agent's display name
- **description** (string): A description of what the agent does
- **system_prompt** (string): The system instructions for the agent

### Optional Fields

#### LLM Configuration (`llm_config`)

Configures the language model to use:

- **provider** (string): LLM provider - `"azure_openai"`, `"openai"`, `"anthropic"`, `"ollama"`, etc.
- **model_name** (string): Model identifier (e.g., `"gpt-4o-latest"`, `"claude-3-5-sonnet"`)
- **temperature** (number): Sampling temperature (0.0 to 2.0, default: 0.0)
- **max_tokens** (number): Maximum tokens in response
- **api_key_env_var** (string): Environment variable name for API key
- **base_url_env_var** (string): Environment variable name for base URL

#### Agent Configuration (`agent_config`)

Configures agent behavior:

- **agent_type** (string): `"conversational"`, `"react"`, or `"plan_and_execute"` (default: `"conversational"`)
- **max_iterations** (number): Maximum reasoning iterations (default: 10)
- **temperature** (number): Override temperature for this agent
- **tools** (array of strings): List of tool names to make available
- **memory_enabled** (boolean): Enable conversation memory (default: false)
- **memory_window_size** (number): Number of recent messages in context (default: 10)
- **structured_outputs** (array): Structured output schemas
- **custom_instructions** (string): Additional instructions for the agent

#### Document Search Configuration

Enable document search capability:

```json
"agent_config": {
"document_search_enabled": true,
"document_collections": ["collection1", "collection2"],
"search_k": 3,
"search_type": "similarity",
"citation_format": "structured"
}
```

#### Orchestration Configuration

For agents that orchestrate other agents:

```json
"agent_config": {
"is_orchestrator": true,
"orchestrator_mode": "supervisor",
"delegation_strategy": "dynamic",
"delegated_agents": ["agent1_id", "agent2_id"]
}
```

#### Metadata (`metadata`)

Library categorization and discovery:

- **category** (array of strings): Categories (e.g., `["Customer Service", "Support"]`)
- **tags** (array of strings): Tags for search and filtering
- **complexity** (string): `"beginner"`, `"intermediate"`, or `"advanced"`
- **icon_color** (string): Icon color - `"cyan"`, `"purple"`, `"orange"`, `"green"`, `"pink"`, or `"blue"`
- **version** (string): Version identifier (e.g., `"1.0.0"`)
- **author** (string): Agent author/creator

## A2A Protocol Compatibility

The Agentic Studio agent import format is inspired by and partially compatible with the A2A Protocol's Agent Card
specification. Key differences:

### What's Compatible

- Basic agent metadata (name, description, version)
- System prompts and instructions
- Tool/capability definitions

### Agentic Studio Extensions

Agentic Studio extends the basic A2A format to support:

- **Advanced LLM Configuration**: Multi-provider support with detailed configuration
- **Memory Management**: Fine-grained control over conversation memory
- **Document Search**: Built-in RAG capabilities
- **Orchestration**: Multi-agent coordination and delegation
- **Structured Outputs**: Schema-based output validation
- **Library Metadata**: Categorization and discovery features

### Future A2A Alignment

As the A2A Protocol evolves, compatibility will be maintained while preserving extended features. Agents imported
using the pure A2A format are automatically enhanced with Agentic Studio defaults.

## Examples

### Example 1: Simple Customer Service Agent

```json
{
  "name": "Customer Support Bot",
  "description": "A helpful customer service agent that can answer questions and resolve issues",
  "system_prompt": "You are a friendly and helpful customer service representative. Always be polite, patient, and focus on solving the customer's problems efficiently.",
  "llm_config": {
    "provider": "azure_openai",
    "model_name": "gpt-4o-latest",
    "temperature": 0.7
  },
  "agent_config": {
    "agent_type": "conversational",
    "max_iterations": 10,
    "memory_enabled": true,
    "memory_window_size": 20
  },
  "metadata": {
    "category": [
      "Customer Service"
    ],
    "tags": [
      "support",
      "customer-service",
      "chatbot"
    ],
    "complexity": "beginner",
    "icon_color": "cyan"
  }
}
```

### Example 2: Research Agent with Tools

```json
{
  "name": "Research Assistant",
  "description": "An AI agent that can research topics using web search and document analysis",
  "system_prompt": "You are a research assistant. Use web search and document analysis to provide comprehensive, well-researched answers. Always cite your sources.",
  "llm_config": {
    "provider": "openai",
    "model_name": "gpt-4o",
    "temperature": 0.3
  },
  "agent_config": {
    "agent_type": "react",
    "max_iterations": 15,
    "tools": [
      "web_search",
      "file_reader"
    ],
    "document_search_enabled": true,
    "search_k": 5,
    "citation_format": "structured"
  },
  "metadata": {
    "category": [
      "Research",
      "Analysis"
    ],
    "tags": [
      "research",
      "analysis",
      "web-search",
      "documents"
    ],
    "complexity": "intermediate",
    "icon_color": "purple"
  }
}
```

### Example 3: Orchestrator Agent

```json
{
  "name": "Task Manager",
  "description": "An orchestrator agent that delegates work to specialized agents",
  "system_prompt": "You are a task manager. Analyze requests and delegate work to the most appropriate specialized agents.",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-3-5-sonnet-20241022",
    "temperature": 0.5
  },
  "agent_config": {
    "agent_type": "plan_and_execute",
    "max_iterations": 20,
    "is_orchestrator": true,
    "orchestrator_mode": "supervisor",
    "delegation_strategy": "dynamic"
  },
  "metadata": {
    "category": [
      "Orchestration",
      "Management"
    ],
    "tags": [
      "orchestrator",
      "delegation",
      "multi-agent"
    ],
    "complexity": "advanced",
    "icon_color": "orange"
  }
}
```

## Importing Agents

### Via Web UI

1. Navigate to the Workflow Library page
2. Click the "Import Agent" button
3. Paste your JSON configuration
4. Review and optionally modify metadata (categories, tags, icon color)
5. Click "Import" to add the agent to your library

### Validation

The import process validates:

- JSON syntax and structure
- Required fields are present
- Field types match schema
- LLM configuration is valid
- Tool references are valid
- Enum values (agent_type, complexity, etc.) are valid

Import errors will display specific messages indicating what needs to be corrected.

## Security & Validation

Agentic Studio implements comprehensive security measures for agent import:

### Input Sanitization

- **System Prompt**: Maximum 50,000 characters. Checked for potentially dangerous content (script tags, javascript:)
- **Custom Instructions**: Maximum 10,000 characters. Same sanitization as system prompt
- **Name & Description**: Trimmed and validated for non-empty content

### Tool Whitelist

Only the following tools are allowed:

- `web_search` - Web search functionality
- `file_reader` - Read files
- `file_writer` - Write files
- `document_search` - Search documents
- `database_query` - Query databases
- `http_request` - Make HTTP requests
- `mcp_server` - MCP server integration
- `email_send` - Send emails

Any tool not in this list will be rejected during import.

### Environment Variable Validation

- **api_key_env_var** and **base_url_env_var** must be valid environment variable names
- Must start with a letter or underscore
- Can only contain alphanumeric characters and underscores
- Maximum 100 characters

Examples of valid env var names:

- `OPENAI_API_KEY` ✓
- `_PRIVATE_KEY` ✓
- `MY_API_KEY_123` ✓

Examples of invalid env var names:

- `API-KEY` ✗ (contains dash)
- `1API_KEY` ✗ (starts with number)
- `API$KEY` ✗ (contains special character)

### Rate Limiting

The import endpoint is rate-limited to **10 requests per minute per user** to prevent abuse.

### Metadata Validation

When metadata is overridden via the UI, all fields are re-validated:

- **complexity**: Must be `beginner`, `intermediate`, or `advanced`
- **icon_color**: Must be `cyan`, `purple`, `orange`, `green`, `pink`, or `blue`
- **category** and **tags**: Arrays of strings

## Best Practices

1. **Start Simple**: Begin with basic configurations and add advanced features incrementally
2. **Test Thoroughly**: Import and test agents in a development environment first
3. **Use Descriptive Names**: Make names and descriptions clear and searchable
4. **Tag Appropriately**: Use relevant tags to make agents discoverable
5. **Version Control**: Maintain version numbers in metadata for tracking
6. **Document Tools**: Clearly specify which tools your agent expects
7. **Avoid Credentials**: Never include API keys or credentials in JSON - use environment variables

## Troubleshooting

### Common Import Errors

**"Invalid JSON syntax"**

- Check for missing commas, brackets, or quotes
- Use a JSON validator to verify syntax

**"Missing required field: name"**

- Ensure all required fields are present

**"Invalid agent_type"**

- Must be one of: `conversational`, `react`, `plan_and_execute`

**"Invalid complexity level"**

- Must be one of: `beginner`, `intermediate`, `advanced`

**"Unknown tool reference"**

- Verify tool names match available tools in Agentic Studio
