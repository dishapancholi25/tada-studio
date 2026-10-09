"""
Utility functions for token counting service.

This module provides encoding management and common constants.
"""

import logging

import tiktoken


logger = logging.getLogger(__name__)

# Token overhead per message (based on GPT-4 format)
# Each message has format tokens: <|im_start|>role\n content<|im_end|>\n
TOKENS_PER_MESSAGE = 4

# Conversation structure overhead
CONVERSATION_END_TOKENS = 3  # <|im_start|>assistant at the end

# Character-based fallback ratio for encoding errors
CHARS_PER_TOKEN_FALLBACK = 4


class EncodingCache:
    """Cache for tiktoken encodings to avoid re-initialization."""

    _encoding = None
    _model_name = None

    @classmethod
    def get_encoding(cls, model: str = "gpt-4o"):
        """
        Get or create cached tiktoken encoding for the specified model.

        Args:
            model: The model name to get encoding for

        Returns:
            tiktoken Encoding instance
        """
        # Return cached encoding if same model
        if cls._encoding is not None and cls._model_name == model:
            return cls._encoding

        try:
            # Try to get encoding for the specific model
            cls._encoding = tiktoken.encoding_for_model(model)
            cls._model_name = model
            logger.info(f"Initialized tiktoken encoding for model: {model}")
        except KeyError:
            # Fallback to cl100k_base which is used by GPT-4 models
            logger.warning(
                f"Model {model} not found in tiktoken, using cl100k_base encoding"
            )
            cls._encoding = tiktoken.get_encoding("cl100k_base")
            cls._model_name = model

        return cls._encoding

    @classmethod
    def clear_cache(cls):
        """Clear the encoding cache (useful for testing)."""
        cls._encoding = None
        cls._model_name = None
