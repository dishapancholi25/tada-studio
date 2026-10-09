"""Text formatter for search results."""

from typing import Any, Dict, List

from .base import ResultFormatter


class TextFormatter(ResultFormatter):
    """Formats search results as readable text."""

    def format(
        self,
        results: Any,
        include_urls: bool = True,
        include_snippets: bool = True,
        max_snippet_length: int = 200,
    ) -> str:
        """
        Format search results as readable text.

        Args:
            results: Search results (list or dict)
            include_urls: Include URLs in output
            include_snippets: Include snippets in output
            max_snippet_length: Maximum snippet length

        Returns:
            Formatted text string
        """
        output_lines = []

        # Handle Tavily format (dict with 'results' key)
        if isinstance(results, dict):
            # Add AI answer if present (Tavily specific)
            output_lines.extend(self._format_ai_answer(results))

            # Add images section if present
            output_lines.extend(self._format_images_section(results))

        # Extract result list
        result_list = self._extract_result_list(results)

        # Format search results
        if result_list:
            output_lines.extend(
                self._format_search_results(
                    result_list, include_urls, include_snippets, max_snippet_length
                )
            )

        return "\n".join(output_lines)

    def _format_ai_answer(self, results: Dict) -> List[str]:
        """Format AI answer section if present."""
        output_lines = []
        if "answer" in results and results["answer"]:
            output_lines.append("AI Answer:")
            output_lines.append(results["answer"])
            output_lines.append("")
        return output_lines

    def _format_images_section(self, results: Dict) -> List[str]:
        """Format images section if present."""
        output_lines = []
        if "images" in results and results["images"]:
            images = results["images"]
            output_lines.append(f"\nImages ({len(images)} found):")
            for img in images[:3]:  # Show first 3 images
                if isinstance(img, dict):
                    output_lines.append(f"  - {img.get('url', 'Unknown URL')}")
                else:
                    output_lines.append(f"  - {img}")
            if len(images) > 3:
                output_lines.append(f"  ... and {len(images) - 3} more")
            output_lines.append("")
        return output_lines

    def _format_search_results(
        self,
        result_list: List[Dict],
        include_urls: bool,
        include_snippets: bool,
        max_snippet_length: int,
    ) -> List[str]:
        """Format the list of search results."""
        output_lines = []
        output_lines.append(f"Search Results ({len(result_list)} found):")
        output_lines.append("")

        for result in result_list:
            # Handle errors
            if "error" in result:
                output_lines.append(f"Error: {result['error']}")
                continue

            # Format regular result
            output_lines.extend(
                self._format_single_result(
                    result, include_urls, include_snippets, max_snippet_length
                )
            )
            output_lines.append("")  # Empty line between results

        return output_lines

    def _format_single_result(
        self,
        result: Dict,
        include_urls: bool,
        include_snippets: bool,
        max_snippet_length: int,
    ) -> List[str]:
        """Format a single search result."""
        output_lines = []

        # Add result header
        position = result.get("position", "")
        title = result.get("title", "No title")

        if position:
            output_lines.append(f"{position}. {title}")
        else:
            output_lines.append(f"- {title}")

        # Add URL if requested
        if include_urls and result.get("url"):
            output_lines.append(f"   URL: {result['url']}")

        # Add snippet if requested
        if include_snippets and result.get("snippet"):
            snippet = result["snippet"]
            if len(snippet) > max_snippet_length:
                snippet = snippet[:max_snippet_length] + "..."
            output_lines.append(f"   {snippet}")

        # Add score for Tavily results
        if "score" in result and result["score"]:
            output_lines.append(f"   Relevance: {result['score']:.2f}")

        return output_lines
