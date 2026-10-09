"""Generates LLM factory functions for the exported Python file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.services.export.utils import safe_name

if TYPE_CHECKING:
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class LLMGenerator:
    """Generates LLM factory functions, one per distinct agent LLM config."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        if not analysis.agent_nodes:
            return ""

        lines = [
            "# " + "=" * 70,
            "# LLM Factory Functions",
            "# " + "=" * 70,
        ]

        for node in analysis.agent_nodes:
            if not node.agent_config or not node.agent_config.llm_config:
                continue
            lines.append("")
            lines.append("")
            lines.append(self._generate_llm_factory(node))

        return "\n".join(lines) if len(lines) > 3 else ""

    def _generate_llm_factory(self, node) -> str:
        sn = safe_name(node.name)
        llm = node.agent_config.llm_config
        provider = llm.provider or "openai"
        temp = llm.temperature if llm.temperature is not None else 0.7
        max_tokens = llm.max_tokens

        if provider == "azure_openai":
            return self._azure_openai_factory(sn, node.name, llm, temp, max_tokens)
        elif provider == "anthropic":
            return self._anthropic_factory(sn, node.name, llm, temp, max_tokens)
        elif provider == "google":
            return self._google_factory(sn, node.name, llm, temp, max_tokens)
        else:
            return self._openai_factory(sn, node.name, llm, temp, max_tokens)

    def _azure_openai_factory(self, sn, name, llm, temp, max_tokens) -> str:
        deployment = llm.deployment_name or llm.model_name or "gpt-4o"
        api_key_var = llm.api_key_env_var or "AZURE_OPENAI_API_KEY"
        base_url_var = llm.base_url_env_var or "AZURE_OPENAI_ENDPOINT"
        api_version = getattr(llm, "api_version", None) or "2024-02-01"

        parts = [
            f"def create_llm_{sn}():",
            f'    """Create LLM for agent: {name}"""',
            "    return AzureChatOpenAI(",
            f'        azure_deployment="{deployment}",',
            f'        api_key=os.environ["{api_key_var}"],',
            f'        azure_endpoint=os.environ["{base_url_var}"],',
            f'        api_version="{api_version}",',
            f"        temperature={temp},",
        ]
        if max_tokens:
            parts.append(f"        max_tokens={max_tokens},")
        parts.append("    )")
        return "\n".join(parts)

    def _openai_factory(self, sn, name, llm, temp, max_tokens) -> str:
        model = llm.model_name or "gpt-4o"
        api_key_var = llm.api_key_env_var or "OPENAI_API_KEY"

        parts = [
            f"def create_llm_{sn}():",
            f'    """Create LLM for agent: {name}"""',
            "    return ChatOpenAI(",
            f'        model="{model}",',
            f'        api_key=os.environ["{api_key_var}"],',
            f"        temperature={temp},",
        ]
        if max_tokens:
            parts.append(f"        max_tokens={max_tokens},")
        if llm.base_url_env_var:
            parts.append(f'        base_url=os.environ.get("{llm.base_url_env_var}"),')
        parts.append("    )")
        return "\n".join(parts)

    def _anthropic_factory(self, sn, name, llm, temp, max_tokens) -> str:
        model = llm.model_name or "claude-sonnet-4-5-20250929"
        api_key_var = llm.api_key_env_var or "ANTHROPIC_API_KEY"

        parts = [
            f"def create_llm_{sn}():",
            f'    """Create LLM for agent: {name}"""',
            "    return ChatAnthropic(",
            f'        model="{model}",',
            f'        api_key=os.environ["{api_key_var}"],',
            f"        temperature={temp},",
        ]
        if max_tokens:
            parts.append(f"        max_tokens={max_tokens},")
        parts.append("    )")
        return "\n".join(parts)

    def _google_factory(self, sn, name, llm, temp, max_tokens) -> str:
        model = llm.model_name or "gemini-pro"
        api_key_var = llm.api_key_env_var or "GOOGLE_API_KEY"

        parts = [
            f"def create_llm_{sn}():",
            f'    """Create LLM for agent: {name}"""',
            "    return ChatGoogleGenerativeAI(",
            f'        model="{model}",',
            f'        google_api_key=os.environ["{api_key_var}"],',
            f"        temperature={temp},",
        ]
        if max_tokens:
            parts.append(f"        max_output_tokens={max_tokens},")
        parts.append("    )")
        return "\n".join(parts)
