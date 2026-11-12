from .base import BaseCollector, RawItem, RawSnapshot, ParsedPrice, fetch_html, fetch_json, hash_payload
from .openrouter import OpenRouterCollector
from .deepseek import DeepSeekCollector
from .gemini import GeminiCollector
from .anthropic import AnthropicCollector
from .openai import OpenAICollector

COLLECTORS: dict[str, type[BaseCollector]] = {
    "openrouter": OpenRouterCollector,
    "deepseek": DeepSeekCollector,
    "gemini": GeminiCollector,
    "anthropic": AnthropicCollector,
    "openai": OpenAICollector,
}

__all__ = [
    "BaseCollector", "RawItem", "RawSnapshot", "ParsedPrice", "COLLECTORS",
    "fetch_html", "fetch_json", "hash_payload",
]
