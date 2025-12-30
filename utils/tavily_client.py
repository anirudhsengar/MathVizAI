"""
Tavily search tool wrapper for the LLM.
"""
import logging
from typing import Any, Dict, List, Optional

from tavily import TavilyClient

import config

logger = logging.getLogger(__name__)


class TavilySearchTool:
    """Encapsulates Tavily web/image search for LLM tool-calling."""

    def __init__(self, default_max_results: Optional[int] = None):
        if not config.TAVILY_API_KEY:
            raise ValueError("TAVILY_API_KEY environment variable not set")

        self.client = TavilyClient(api_key=config.TAVILY_API_KEY)
        self.default_max_results = default_max_results or config.TAVILY_MAX_RESULTS

        self.tool_definition = {
            "type": "function",
            "function": {
                "name": "tavily_search",
                "description": (
                    "Search the web for up-to-date answers, references, or images. "
                    "Use this when you need external knowledge or visual inspiration."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to run against the web."
                        },
                        "max_results": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 10,
                            "description": "How many results to return (1-10)."
                        },
                        "search_depth": {
                            "type": "string",
                            "enum": ["basic", "advanced"],
                            "description": "Use 'advanced' for deeper research, 'basic' for speed."
                        },
                        "include_images": {
                            "type": "boolean",
                            "description": "Return a list of image URLs for visual reference."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def search(
        self,
        query: str,
        max_results: Optional[int] = None,
        search_depth: Optional[str] = None,
        include_images: bool = False
    ) -> str:
        """Execute a Tavily search and return formatted text for the LLM."""
        if not query:
            return "No search query provided."

        max_results = max_results or self.default_max_results
        search_depth = search_depth or config.TAVILY_SEARCH_DEPTH

        try:
            response = self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                include_images=include_images
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Tavily search failed: %s", exc)
            return f"Tavily search failed: {exc}"

        return self._format_response(response, include_images)

    def _format_response(self, response: Dict[str, Any], include_images: bool) -> str:
        results: List[Dict[str, Any]] = response.get("results", []) if isinstance(response, dict) else []
        if not results:
            return "No Tavily results found."

        lines: List[str] = []
        for idx, item in enumerate(results, 1):
            title = item.get("title") or "Untitled"
            url = item.get("url") or ""
            snippet = item.get("content") or item.get("snippet") or ""
            lines.append(f"{idx}. {title}\n   URL: {url}\n   Snippet: {snippet}")

        if include_images and isinstance(response, dict):
            images = response.get("images") or []
            if images:
                lines.append("Images:")
                lines.extend([f"- {img}" for img in images])

        return "\n".join(lines)
