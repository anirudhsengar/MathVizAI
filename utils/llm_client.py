"""
LLM Client wrapper for OpenAI with tool-calling support.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

import config
from utils.tavily_client import TavilySearchTool

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper class for LLM API calls."""

    def __init__(self):
        """Initialize the LLM client and register available tools."""
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.MODEL_NAME

        self.tools: List[Dict[str, Any]] = []
        self.tool_handlers: Dict[str, Any] = {}
        self._register_tools()

    def _register_tools(self) -> None:
        """Register optional tools (Tavily search) for tool-calling."""
        try:
            tavily_tool = TavilySearchTool(default_max_results=config.TAVILY_MAX_RESULTS)
            self.tools.append(tavily_tool.tool_definition)
            self.tool_handlers["tavily_search"] = tavily_tool.search
            logger.info("Tavily search tool registered.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Tavily tool unavailable: %s", exc)

    def generate_response(
        self,
        system_prompt: str,
        query: str,
        temperature: float,
        max_tokens: Optional[int] = None,
        allow_tools: bool = False,
        additional_tools: Optional[List[Dict[str, Any]]] = None,
        max_tool_rounds: int = 4
    ) -> str:
        """
        Generate a response from the LLM, optionally allowing tool use.

        Args:
            system_prompt: The system prompt defining the AI's role.
            query: The user query or input.
            temperature: Temperature for response generation.
            max_tokens: Maximum tokens for response (defaults to config value).
            allow_tools: Whether to expose registered tools to the model.
            additional_tools: Extra tool definitions to expose alongside defaults.
            max_tool_rounds: Safety cap on tool-calling loops.

        Returns:
            Generated response as string.
        """
        if max_tokens is None:
            max_tokens = config.MAX_TOKENS

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        tools_to_use: List[Dict[str, Any]] = []
        tool_handlers: Dict[str, Any] = {}

        if allow_tools:
            tools_to_use.extend(self.tools)
            tool_handlers.update(self.tool_handlers)

        if additional_tools:
            tools_to_use.extend(additional_tools)

        tool_choice = "auto" if tools_to_use else None
        rounds = 0

        while True:
            rounds += 1
            response = self.client.chat.completions.create(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                model=self.model,
                tools=tools_to_use or None,
                tool_choice=tool_choice,
            )

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)

            if not tool_calls:
                return message.content

            # Record the assistant message that invoked tools
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            if rounds >= max_tool_rounds:
                return message.content or ""

            for tc in tool_calls:
                handler = tool_handlers.get(tc.function.name)

                try:
                    args = json.loads(tc.function.arguments or "{}") if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}

                if not handler:
                    tool_output = f"Tool '{tc.function.name}' not available."
                else:
                    try:
                        tool_output = handler(**args)
                    except Exception as exc:  # noqa: BLE001
                        logger.error("Tool '%s' failed: %s", tc.function.name, exc)
                        tool_output = f"Tool '{tc.function.name}' failed: {exc}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": tool_output,
                    }
                )
