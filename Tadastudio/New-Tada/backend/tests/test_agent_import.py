"""Unit tests for agent import functionality."""

import pytest
from pydantic import ValidationError

from backend.api.library.import_schema import (
    ImportAgentConfig,
    ImportAgentMetadata,
    ImportAgentRequest,
    ImportLLMConfig,
)


class TestImportLLMConfig:
    """Tests for ImportLLMConfig validation."""

    def test_valid_minimal_config(self):
        """Test valid minimal LLM configuration."""
        config = ImportLLMConfig()
        assert config.provider == "azure_openai"
        assert config.model_name == "gpt-4o-latest"
        assert config.temperature == 0.0

    def test_valid_full_config(self):
        """Test valid full LLM configuration."""
        config = ImportLLMConfig(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.7,
            max_tokens=1000,
            api_key_env_var="OPENAI_API_KEY",
            base_url_env_var="OPENAI_BASE_URL",
            timeout=60,
            max_retries=5,
        )
        assert config.provider == "openai"
        assert config.model_name == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.max_retries == 5

    def test_invalid_temperature_too_high(self):
        """Test temperature validation - too high."""
        with pytest.raises(ValidationError):
            ImportLLMConfig(temperature=3.0)

    def test_invalid_temperature_negative(self):
        """Test temperature validation - negative."""
        with pytest.raises(ValidationError):
            ImportLLMConfig(temperature=-0.5)

    def test_invalid_max_tokens_zero(self):
        """Test max_tokens validation - zero."""
        with pytest.raises(ValidationError):
            ImportLLMConfig(max_tokens=0)


class TestImportAgentConfig:
    """Tests for ImportAgentConfig validation."""

    def test_valid_minimal_config(self):
        """Test valid minimal agent configuration."""
        config = ImportAgentConfig()
        assert config.agent_type == "conversational"
        assert config.max_iterations == 10
        assert config.memory_enabled is False
        assert config.document_search_enabled is False
        assert config.is_orchestrator is False

    def test_valid_react_agent(self):
        """Test valid React agent configuration."""
        config = ImportAgentConfig(
            agent_type="react",
            max_iterations=15,
            tools=["web_search", "file_reader"],
            memory_enabled=True,
            memory_window_size=20,
        )
        assert config.agent_type == "react"
        assert config.max_iterations == 15
        assert config.tools == ["web_search", "file_reader"]
        assert config.memory_enabled is True
        assert config.memory_window_size == 20

    def test_valid_orchestrator(self):
        """Test valid orchestrator configuration."""
        config = ImportAgentConfig(
            agent_type="plan_and_execute",
            is_orchestrator=True,
            orchestrator_mode="supervisor",
            delegation_strategy="dynamic",
            delegated_agents=["agent1", "agent2"],
        )
        assert config.is_orchestrator is True
        assert config.orchestrator_mode == "supervisor"
        assert config.delegation_strategy == "dynamic"
        assert len(config.delegated_agents) == 2

    def test_valid_document_search(self):
        """Test valid document search configuration."""
        config = ImportAgentConfig(
            document_search_enabled=True,
            document_collections=["docs", "research"],
            search_k=5,
            search_type="similarity",
            citation_format="structured",
        )
        assert config.document_search_enabled is True
        assert config.document_collections == ["docs", "research"]
        assert config.search_k == 5
        assert config.search_type == "similarity"
        assert config.citation_format == "structured"

    def test_invalid_agent_type(self):
        """Test agent_type validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(agent_type="invalid_type")
        assert "agent_type must be one of" in str(exc_info.value)

    def test_invalid_memory_strategy(self):
        """Test memory_strategy validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(memory_strategy="invalid_strategy")
        assert "memory_strategy must be one of" in str(exc_info.value)

    def test_invalid_search_type(self):
        """Test search_type validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(search_type="invalid_type")
        assert "search_type must be one of" in str(exc_info.value)

    def test_invalid_citation_format(self):
        """Test citation_format validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(citation_format="invalid_format")
        assert "citation_format must be one of" in str(exc_info.value)

    def test_invalid_orchestrator_mode(self):
        """Test orchestrator_mode validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(orchestrator_mode="invalid_mode")
        assert "orchestrator_mode must be one of" in str(exc_info.value)

    def test_invalid_delegation_strategy(self):
        """Test delegation_strategy validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(delegation_strategy="invalid_strategy")
        assert "delegation_strategy must be one of" in str(exc_info.value)

    def test_invalid_max_iterations_too_low(self):
        """Test max_iterations validation - too low."""
        with pytest.raises(ValidationError):
            ImportAgentConfig(max_iterations=0)

    def test_invalid_max_iterations_too_high(self):
        """Test max_iterations validation - too high."""
        with pytest.raises(ValidationError):
            ImportAgentConfig(max_iterations=101)


class TestImportAgentMetadata:
    """Tests for ImportAgentMetadata validation."""

    def test_valid_minimal_metadata(self):
        """Test valid minimal metadata."""
        metadata = ImportAgentMetadata()
        assert metadata.category == []
        assert metadata.tags == []
        assert metadata.complexity is None
        assert metadata.icon_color is None

    def test_valid_full_metadata(self):
        """Test valid full metadata."""
        metadata = ImportAgentMetadata(
            category=["Customer Service", "Support"],
            tags=["chatbot", "support", "customer-service"],
            complexity="beginner",
            icon_color="cyan",
            version="1.0.0",
            author="Test Author",
        )
        assert metadata.category == ["Customer Service", "Support"]
        assert metadata.tags == ["chatbot", "support", "customer-service"]
        assert metadata.complexity == "beginner"
        assert metadata.icon_color == "cyan"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"

    def test_invalid_complexity(self):
        """Test complexity validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentMetadata(complexity="expert")
        assert "complexity must be one of" in str(exc_info.value)

    def test_invalid_icon_color(self):
        """Test icon_color validation."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentMetadata(icon_color="red")
        assert "icon_color must be one of" in str(exc_info.value)


class TestImportAgentRequest:
    """Tests for ImportAgentRequest validation."""

    def test_valid_minimal_request(self):
        """Test valid minimal import request."""
        request = ImportAgentRequest(
            name="Test Agent",
            description="A test agent",
            system_prompt="You are a helpful assistant.",
        )
        assert request.name == "Test Agent"
        assert request.description == "A test agent"
        assert request.system_prompt == "You are a helpful assistant."
        assert request.llm_config is None
        assert request.agent_config is None
        assert request.metadata is None

    def test_valid_full_request(self):
        """Test valid full import request."""
        request = ImportAgentRequest(
            name="Customer Support Bot",
            description="A helpful customer service agent",
            system_prompt="You are a friendly customer service representative.",
            llm_config=ImportLLMConfig(
                provider="azure_openai",
                model_name="gpt-4o-latest",
                temperature=0.7,
            ),
            agent_config=ImportAgentConfig(
                agent_type="conversational",
                max_iterations=10,
                memory_enabled=True,
                tools=["web_search"],
            ),
            metadata=ImportAgentMetadata(
                category=["Customer Service"],
                tags=["support", "chatbot"],
                complexity="beginner",
                icon_color="cyan",
            ),
        )
        assert request.name == "Customer Support Bot"
        assert request.llm_config.provider == "azure_openai"
        assert request.agent_config.agent_type == "conversational"
        assert request.metadata.complexity == "beginner"

    def test_valid_request_from_dict(self):
        """Test creating request from dictionary."""
        data = {
            "name": "Research Assistant",
            "description": "An AI agent for research",
            "system_prompt": "You are a research assistant.",
            "llm_config": {
                "provider": "openai",
                "model_name": "gpt-4o",
                "temperature": 0.3,
            },
            "agent_config": {
                "agent_type": "react",
                "max_iterations": 15,
                "tools": ["web_search", "file_reader"],
            },
            "metadata": {
                "category": ["Research"],
                "tags": ["research", "analysis"],
                "complexity": "intermediate",
            },
        }
        request = ImportAgentRequest(**data)
        assert request.name == "Research Assistant"
        assert request.llm_config.provider == "openai"
        assert request.agent_config.agent_type == "react"
        assert request.metadata.complexity == "intermediate"

    def test_get_effective_metadata(self):
        """Test get_effective_metadata method."""
        # With metadata
        request = ImportAgentRequest(
            name="Test",
            description="Test",
            system_prompt="Test",
            metadata=ImportAgentMetadata(complexity="beginner"),
        )
        metadata = request.get_effective_metadata()
        assert metadata.complexity == "beginner"

        # Without metadata
        request = ImportAgentRequest(
            name="Test", description="Test", system_prompt="Test"
        )
        metadata = request.get_effective_metadata()
        assert metadata.complexity is None

    def test_get_effective_agent_config(self):
        """Test get_effective_agent_config method."""
        # With agent_config
        request = ImportAgentRequest(
            name="Test",
            description="Test",
            system_prompt="Test",
            agent_config=ImportAgentConfig(agent_type="react"),
        )
        config = request.get_effective_agent_config()
        assert config.agent_type == "react"

        # Without agent_config
        request = ImportAgentRequest(
            name="Test", description="Test", system_prompt="Test"
        )
        config = request.get_effective_agent_config()
        assert config.agent_type == "conversational"  # Default

    def test_get_effective_agent_config_with_top_level_tools(self):
        """Test get_effective_agent_config merges top-level tools."""
        request = ImportAgentRequest(
            name="Test",
            description="Test",
            system_prompt="Test",
            tools=["web_search", "file_reader"],
        )
        config = request.get_effective_agent_config()
        assert config.tools == ["web_search", "file_reader"]

    def test_missing_required_name(self):
        """Test validation when name is missing."""
        with pytest.raises(ValidationError):
            ImportAgentRequest(description="Test", system_prompt="Test")

    def test_missing_required_description(self):
        """Test validation when description is missing."""
        with pytest.raises(ValidationError):
            ImportAgentRequest(name="Test", system_prompt="Test")

    def test_missing_required_system_prompt(self):
        """Test validation when system_prompt is missing."""
        with pytest.raises(ValidationError):
            ImportAgentRequest(name="Test", description="Test")

    def test_empty_name(self):
        """Test validation when name is empty."""
        with pytest.raises(ValidationError):
            ImportAgentRequest(name="   ", description="Test", system_prompt="Test")

    def test_empty_description(self):
        """Test validation when description is empty."""
        with pytest.raises(ValidationError):
            ImportAgentRequest(name="Test", description="   ", system_prompt="Test")

    def test_empty_system_prompt(self):
        """Test validation when system_prompt is empty."""
        with pytest.raises(ValidationError):
            ImportAgentRequest(name="Test", description="Test", system_prompt="   ")

    def test_name_trimming(self):
        """Test that name is trimmed."""
        request = ImportAgentRequest(
            name="  Test Agent  ",
            description="Test",
            system_prompt="Test",
        )
        assert request.name == "Test Agent"

    def test_description_trimming(self):
        """Test that description is trimmed."""
        request = ImportAgentRequest(
            name="Test",
            description="  Test description  ",
            system_prompt="Test",
        )
        assert request.description == "Test description"

    def test_system_prompt_trimming(self):
        """Test that system_prompt is trimmed."""
        request = ImportAgentRequest(
            name="Test",
            description="Test",
            system_prompt="  You are a helpful assistant.  ",
        )
        assert request.system_prompt == "You are a helpful assistant."


class TestAgentImportExamples:
    """Tests using complete example JSON from documentation."""

    def test_example_1_customer_service_agent(self):
        """Test Example 1 from AGENT_IMPORT.md."""
        data = {
            "name": "Customer Support Bot",
            "description": "A helpful customer service agent that can answer questions and resolve issues",
            "system_prompt": "You are a friendly and helpful customer service representative. Always be polite, patient, and focus on solving the customer's problems efficiently.",
            "llm_config": {
                "provider": "azure_openai",
                "model_name": "gpt-4o-latest",
                "temperature": 0.7,
            },
            "agent_config": {
                "agent_type": "conversational",
                "max_iterations": 10,
                "memory_enabled": True,
                "memory_window_size": 20,
            },
            "metadata": {
                "category": ["Customer Service"],
                "tags": ["support", "customer-service", "chatbot"],
                "complexity": "beginner",
                "icon_color": "cyan",
            },
        }
        request = ImportAgentRequest(**data)
        assert request.name == "Customer Support Bot"
        assert request.llm_config.temperature == 0.7
        assert request.agent_config.memory_enabled is True
        assert request.metadata.complexity == "beginner"

    def test_example_2_research_agent(self):
        """Test Example 2 from AGENT_IMPORT.md."""
        data = {
            "name": "Research Assistant",
            "description": "An AI agent that can research topics using web search and document analysis",
            "system_prompt": "You are a research assistant. Use web search and document analysis to provide comprehensive, well-researched answers. Always cite your sources.",
            "llm_config": {
                "provider": "openai",
                "model_name": "gpt-4o",
                "temperature": 0.3,
            },
            "agent_config": {
                "agent_type": "react",
                "max_iterations": 15,
                "tools": ["web_search", "file_reader"],
                "document_search_enabled": True,
                "search_k": 5,
                "citation_format": "structured",
            },
            "metadata": {
                "category": ["Research", "Analysis"],
                "tags": ["research", "analysis", "web-search", "documents"],
                "complexity": "intermediate",
                "icon_color": "purple",
            },
        }
        request = ImportAgentRequest(**data)
        assert request.name == "Research Assistant"
        assert request.agent_config.agent_type == "react"
        assert request.agent_config.document_search_enabled is True
        assert request.metadata.complexity == "intermediate"

    def test_example_3_orchestrator_agent(self):
        """Test Example 3 from AGENT_IMPORT.md."""
        data = {
            "name": "Task Manager",
            "description": "An orchestrator agent that delegates work to specialized agents",
            "system_prompt": "You are a task manager. Analyze requests and delegate work to the most appropriate specialized agents.",
            "llm_config": {
                "provider": "anthropic",
                "model_name": "claude-3-5-sonnet-20241022",
                "temperature": 0.5,
            },
            "agent_config": {
                "agent_type": "plan_and_execute",
                "max_iterations": 20,
                "is_orchestrator": True,
                "orchestrator_mode": "supervisor",
                "delegation_strategy": "dynamic",
            },
            "metadata": {
                "category": ["Orchestration", "Management"],
                "tags": ["orchestrator", "delegation", "multi-agent"],
                "complexity": "advanced",
                "icon_color": "orange",
            },
        }
        request = ImportAgentRequest(**data)
        assert request.name == "Task Manager"
        assert request.agent_config.is_orchestrator is True
        assert request.agent_config.orchestrator_mode == "supervisor"
        assert request.metadata.complexity == "advanced"


class TestSecurityValidations:
    """Tests for security-related validations."""

    def test_invalid_api_key_env_var_with_special_chars(self):
        """Test that API key env var with special characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportLLMConfig(api_key_env_var="API-KEY")
        assert "api_key_env_var must be a valid environment variable name" in str(
            exc_info.value
        )

    def test_invalid_api_key_env_var_starting_with_number(self):
        """Test that API key env var starting with number is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportLLMConfig(api_key_env_var="1API_KEY")
        assert "api_key_env_var must be a valid environment variable name" in str(
            exc_info.value
        )

    def test_valid_api_key_env_var(self):
        """Test that valid API key env var is accepted."""
        config = ImportLLMConfig(api_key_env_var="OPENAI_API_KEY")
        assert config.api_key_env_var == "OPENAI_API_KEY"

        # Starting with underscore is also valid
        config2 = ImportLLMConfig(api_key_env_var="_PRIVATE_KEY")
        assert config2.api_key_env_var == "_PRIVATE_KEY"

    def test_invalid_base_url_env_var_with_special_chars(self):
        """Test that base URL env var with special characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportLLMConfig(base_url_env_var="BASE$URL")
        assert "base_url_env_var must be a valid environment variable name" in str(
            exc_info.value
        )

    def test_api_key_env_var_too_long(self):
        """Test that overly long env var names are rejected."""
        long_var_name = "A" * 101
        with pytest.raises(ValidationError) as exc_info:
            ImportLLMConfig(api_key_env_var=long_var_name)
        assert "too long" in str(exc_info.value)

    def test_invalid_tool_not_in_whitelist(self):
        """Test that tools not in whitelist are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(tools=["malicious_tool"])
        assert "Invalid tools" in str(exc_info.value)
        assert "malicious_tool" in str(exc_info.value)

    def test_valid_tools_in_whitelist(self):
        """Test that valid tools are accepted."""
        config = ImportAgentConfig(tools=["web_search", "file_reader"])
        assert config.tools == ["web_search", "file_reader"]

    def test_mixed_valid_invalid_tools(self):
        """Test that mix of valid and invalid tools is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(tools=["web_search", "bad_tool", "file_reader"])
        assert "Invalid tools" in str(exc_info.value)
        assert "bad_tool" in str(exc_info.value)

    def test_system_prompt_with_script_tag(self):
        """Test that system prompt with script tag is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentRequest(
                name="Test",
                description="Test",
                system_prompt="You are helpful <script>alert('xss')</script>",
            )
        assert "potentially dangerous content" in str(exc_info.value)

    def test_system_prompt_with_javascript(self):
        """Test that system prompt with javascript: is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentRequest(
                name="Test",
                description="Test",
                system_prompt="Click javascript:void(0)",
            )
        assert "potentially dangerous content" in str(exc_info.value)

    def test_custom_instructions_with_script_tag(self):
        """Test that custom instructions with script tag is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(
                custom_instructions="Follow these <script>evil()</script> instructions"
            )
        assert "potentially dangerous content" in str(exc_info.value)

    def test_system_prompt_too_long(self):
        """Test that overly long system prompt is rejected."""
        long_prompt = "A" * 50001
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentRequest(
                name="Test", description="Test", system_prompt=long_prompt
            )
        assert "at most 50000 characters" in str(exc_info.value)

    def test_custom_instructions_too_long(self):
        """Test that overly long custom instructions is rejected."""
        long_instructions = "A" * 10001
        with pytest.raises(ValidationError) as exc_info:
            ImportAgentConfig(custom_instructions=long_instructions)
        assert "at most 10000 characters" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
