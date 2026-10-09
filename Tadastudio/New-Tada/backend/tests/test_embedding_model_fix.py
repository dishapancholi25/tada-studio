"""Tests for embedding model test connection fix.

This test suite verifies that the LLM Factory correctly handles testing
both chat/completion models and embedding models by routing to the
appropriate API endpoints.
"""

from backend.models.workflow.configs.llm import LLMConfig
from backend.services.llm_models.factory import LLMFactory


class TestLLMConfigModelType:
    """Tests for LLMConfig model_type field."""

    def test_default_model_type(self):
        """Test that default model_type is 'llm'."""
        config = LLMConfig(provider="openai", model_name="gpt-4o")
        assert hasattr(config, "model_type"), "LLMConfig should have model_type field"
        assert config.model_type == "llm", "Default model_type should be 'llm'"

    def test_explicit_llm_type(self):
        """Test explicit 'llm' model_type."""
        config = LLMConfig(provider="openai", model_name="gpt-4o", model_type="llm")
        assert config.model_type == "llm"

    def test_embedding_model_type(self):
        """Test 'embedding' model_type."""
        config = LLMConfig(
            provider="openai",
            model_name="text-embedding-3-small",
            model_type="embedding",
        )
        assert config.model_type == "embedding"

    def test_azure_embedding_model_type(self):
        """Test embedding model with Azure provider."""
        config = LLMConfig(
            provider="azure_openai",
            model_name="text-embedding-ada-002",
            model_type="embedding",
            deployment_name="my-embedding-deployment",
        )
        assert config.model_type == "embedding"
        assert config.provider == "azure_openai"


class TestLLMFactoryEmbeddingSupport:
    """Tests for LLM Factory embedding model support."""

    def test_factory_has_embedding_test_method(self):
        """Verify LLMFactory has _test_embedding_connection method."""
        factory = LLMFactory()
        assert hasattr(factory, "_test_embedding_connection"), (
            "LLMFactory should have _test_embedding_connection method"
        )
        assert callable(factory._test_embedding_connection), (
            "_test_embedding_connection should be callable"
        )

    def test_llm_model_test_returns_dict(self):
        """Test that LLM model test returns proper error dict when credentials missing."""
        factory = LLMFactory()
        llm_config = LLMConfig(provider="openai", model_name="gpt-4o", model_type="llm")

        result = factory.test_llm_connection(llm_config)

        assert isinstance(result, dict), "Should return dict"
        assert "success" in result, "Should have 'success' key"
        assert "provider" in result, "Should have 'provider' key"
        assert "model" in result, "Should have 'model' key"
        assert result["success"] is False, "Should fail without credentials"
        assert "error" in result, "Should have 'error' key when failed"

    def test_embedding_model_test_returns_dict(self):
        """Test that embedding model test returns proper error dict when deployment_id missing."""
        factory = LLMFactory()
        embedding_config = LLMConfig(
            provider="openai",
            model_name="text-embedding-3-small",
            model_type="embedding",
            # No model_deployment_id provided
        )

        result = factory.test_llm_connection(embedding_config)

        assert isinstance(result, dict), "Should return dict"
        assert "success" in result, "Should have 'success' key"
        assert "provider" in result, "Should have 'provider' key"
        assert "model" in result, "Should have 'model' key"
        assert result["success"] is False, "Should fail without deployment_id"
        assert "error" in result, "Should have 'error' key when failed"
        assert "model_deployment_id" in result["error"], (
            "Error should mention missing deployment_id"
        )

    def test_model_type_routing(self):
        """Test that model_type correctly routes to appropriate test method."""
        factory = LLMFactory()

        # LLM model should not require deployment_id (though will fail on credentials)
        llm_config = LLMConfig(provider="openai", model_name="gpt-4o", model_type="llm")
        llm_result = factory.test_llm_connection(llm_config)
        # Should fail on API key, not deployment_id
        assert "api_key" in llm_result.get("error", "").lower()

        # Embedding model should require deployment_id
        embedding_config = LLMConfig(
            provider="openai",
            model_name="text-embedding-3-small",
            model_type="embedding",
        )
        embedding_result = factory.test_llm_connection(embedding_config)
        # Should fail on deployment_id
        assert "deployment_id" in embedding_result.get("error", "").lower()


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    def test_legacy_config_without_model_type(self):
        """Test that configs without explicit model_type still work."""
        # Old code might not specify model_type
        config = LLMConfig(
            provider="openai",
            model_name="gpt-4o",
            # model_type not specified, should default to "llm"
        )
        assert config.model_type == "llm", (
            "Should default to 'llm' for backward compatibility"
        )

    def test_anthropic_models_are_llm_type(self):
        """Test that Anthropic models are LLM type (they don't have embeddings)."""
        config = LLMConfig(
            provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            model_type="llm",
        )
        assert config.model_type == "llm"
        assert config.provider == "anthropic"
