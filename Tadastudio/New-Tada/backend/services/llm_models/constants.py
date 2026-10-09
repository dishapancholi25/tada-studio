"""Constants for LLM models service."""

# Logging prefix
LOG_PREFIX = "[LLM-FACTORY]"

# Supported providers
SUPPORTED_PROVIDERS = ["azure_openai", "azure_openai_ptu", "gpu_con", "openai", "anthropic"]

# Providers that support tool calling
TOOL_CALLING_PROVIDERS = ["azure_openai", "azure_openai_ptu", "gpu_con", "openai", "anthropic"]

# Providers that support tool_choice parameter
TOOL_CHOICE_PROVIDERS = ["azure_openai","azure_openai_ptu","gpu_con","openai","mistralai","fireworksai","groq",]

# Available models per provider
AVAILABLE_MODELS = {
    "azure_openai": [
        "gpt-4",
        "gpt-4-32k",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-35-turbo",
        "gpt-35-turbo-16k",
    ],
    "azure_openai_ptu": [
        "gpt-4.1",
        "gpt-4o",
        "gpt-4",
        "gpt-4-turbo",
    ],
    "gpu_con": [],
    "openai": [
        "gpt-4",
        "gpt-4-32k",
        "gpt-4-turbo-preview",
        "gpt-4o",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ],
    "anthropic": [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-instant-1.2",
    ],
}

# Azure Cognitive Services scope
AZURE_COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"

# Temperature range
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
