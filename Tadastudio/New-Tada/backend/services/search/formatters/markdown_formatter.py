"""Markdown formatter for search results."""

from typing import Any, Dict, List

from .base import ResultFormatter


class MarkdownFormatter(ResultFormatter):
    """Formats search results as Markdown."""

    def format(
        self, results: Any, include_urls: bool = True, include_snippets: bool = True
    ) -> str:
        """
        Format search results as Markdown.

        Args:
            results: Search results
            include_urls: Include URLs in output
            include_snippets: Include snippets in output

        Returns:
            Markdown formatted string
        """
        output_lines = []

        # Handle Tavily format
        if isinstance(results, dict):
            # Add AI answer if present
            output_lines.extend(self._format_ai_answer(results))

            # Add images section if present
            output_lines.extend(self._format_images_section(results))

        # Extract result list
        result_list = self._extract_result_list(results)

        # Format search results
        if result_list:
            output_lines.extend(
                self._format_search_results(result_list, include_urls, include_snippets)
            )

        return "\n".join(output_lines)

    def _format_ai_answer(self, results: Dict) -> List[str]:
        """Format AI answer section if present."""
        output_lines = []
        if "answer" in results and results["answer"]:
            output_lines.append("## AI-Generated Answer\n")
            output_lines.append(results["answer"])
            output_lines.append("\n---\n")
        return output_lines

    def _format_images_section(self, results: Dict) -> List[str]:
        """Format images section if present."""
        output_lines = []
        if "images" in results and results["images"]:
            output_lines.append("## Images\n")
            for img in results["images"][:5]:
                if isinstance(img, dict):
                    img_url = img.get("url", "")
                    img_title = img.get("title", "Image")
                else:
                    img_url = str(img)
                    img_title = "Image"
                if img_url:
                    output_lines.append(f"- [{img_title}]({img_url})")
            output_lines.append("")
        return output_lines

    def _format_search_results(
        self, result_list: List[Dict], include_urls: bool, include_snippets: bool
    ) -> List[str]:
        """Format the list of search results."""
        output_lines = []
        output_lines.append("## Search Results\n")

        for result in result_list:
            if "error" in result:
                output_lines.append(f"> ⚠️ **Error:** {result['error']}\n")
                continue

            output_lines.extend(
                self._format_single_result(result, include_urls, include_snippets)
            )
            output_lines.append("---\n")

        return output_lines

    def _format_single_result(
        self, result: Dict, include_urls: bool, include_snippets: bool
    ) -> List[str]:
        """Format a single search result."""
        output_lines = []

        title = result.get("title", "No title")
        url = result.get("url", "")
        snippet = result.get("snippet", "")

        # Format title as header with optional URL
        if url and include_urls:
            output_lines.append(f"### [{title}]({url})")
        else:
            output_lines.append(f"### {title}")

        # Add snippet
        if include_snippets and snippet:
            output_lines.append(f"\n{snippet}\n")

        # Add metadata
        metadata = self._format_metadata(result)
        if metadata:
            output_lines.append(metadata)

        return output_lines

    def _format_metadata(self, result: Dict) -> str:
        """Format metadata line for a result."""
        metadata = []

        if "score" in result and result["score"]:
            metadata.append(f"Relevance: {result['score']:.2f}")

        if "source" in result:
            metadata.append(f"Source: {result['source']}")

        if metadata:
            return f"*{' | '.join(metadata)}*\n"

        return ""
