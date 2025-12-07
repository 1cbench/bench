import os
import time

from openai import OpenAI, APIConnectionError, RateLimitError

from .llm_provider import LLMProvider


class AnthropicProvider(LLMProvider):
    """LLM provider for Anthropic API."""

    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(
        self,
        system_prompt: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None
    ):
        super().__init__(system_prompt, model)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or self.BASE_URL
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate(
        self,
        prompt: str,
        max_tokens: int = 50,
        num_attempts: int = 5,
        temperature: float = 0.2,
        n: int = 1
    ) -> str | list[str] | None:
        params = {"temperature": temperature, "max_tokens": max_tokens, "n": n}
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        attempts = 0
        while attempts < num_attempts:
            try:
                chat = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    **params
                )
                return self._extract_response(chat)
            except (APIConnectionError, RateLimitError):
                attempts += 1
                time.sleep(1)
            except Exception:
                return None

        return None
