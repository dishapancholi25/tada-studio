"""Utilities for optimizing chunking parameters based on document characteristics."""

from typing import Any, Dict


class ChunkingOptimizer:
    """Utilities for optimizing chunking parameters based on document characteristics."""

    @staticmethod
    def analyze_document(text: str) -> Dict[str, Any]:
        """
        Analyze document characteristics to recommend optimal chunking parameters.

        Args:
            text: The document text to analyze

        Returns:
            Dictionary with analysis results and recommendations
        """
        lines = text.split("\n")
        words = text.split()
        sentences = text.split(". ")

        analysis = {
            "total_characters": len(text),
            "total_words": len(words),
            "total_lines": len(lines),
            "total_sentences": len(sentences),
            "avg_line_length": len(text) / len(lines) if lines else 0,
            "avg_sentence_length": len(text) / len(sentences) if sentences else 0,
            "has_code_blocks": "```" in text or "    " in text,
            "has_tables": "|" in text and text.count("|") > 10,
            "has_lists": any(
                line.strip().startswith(("- ", "* ", "1.", "•")) for line in lines
            ),
        }

        # Recommend chunking parameters based on analysis
        if analysis["has_code_blocks"]:
            analysis["recommended_strategy"] = "recursive"
            analysis["recommended_chunk_size"] = 1500
            analysis["recommended_overlap"] = 200
        elif analysis["has_tables"]:
            analysis["recommended_strategy"] = "character"
            analysis["recommended_chunk_size"] = 2000
            analysis["recommended_overlap"] = 100
        elif analysis["avg_sentence_length"] > 100:
            # Long sentences, use smaller chunks
            analysis["recommended_strategy"] = "semantic"
            analysis["recommended_chunk_size"] = 800
            analysis["recommended_overlap"] = 150
        else:
            # Default balanced approach
            analysis["recommended_strategy"] = "recursive"
            analysis["recommended_chunk_size"] = 1000
            analysis["recommended_overlap"] = 200

        return analysis

    @staticmethod
    def validate_parameters(chunk_size: int, chunk_overlap: int) -> tuple[int, int]:
        """
        Validate and adjust chunking parameters to ensure they're reasonable.

        Args:
            chunk_size: Desired chunk size
            chunk_overlap: Desired overlap size

        Returns:
            Tuple of (validated_chunk_size, validated_chunk_overlap)
        """
        # Ensure chunk_size is within reasonable bounds
        chunk_size = max(100, min(chunk_size, 10000))

        # Ensure overlap is not greater than chunk_size
        chunk_overlap = min(chunk_overlap, int(chunk_size * 0.5))

        # Ensure overlap is not negative
        chunk_overlap = max(0, chunk_overlap)

        return chunk_size, chunk_overlap
