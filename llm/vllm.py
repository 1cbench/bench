import os
import time

from openai import OpenAI, APIConnectionError, RateLimitError

from .llm_provider import LLMProvider


class VLLMProvider(LLMProvider):
    """LLM provider for a local vLLM OpenAI-compatible endpoint (e.g. via SSH tunnel)."""

    def __init__(
        self,
        system_prompt: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        reasoning: bool = False
    ):
        super().__init__(system_prompt, model)
        # vLLM doesn't validate the key, but the OpenAI client requires a non-empty value.
        self.api_key = api_key or os.getenv("VLLM_API_KEY", "EMPTY")
        self.base_url = base_url or os.getenv("VLLM_BASE_URL")
        if not self.base_url:
            raise ValueError("VLLM_BASE_URL must be set (e.g. http://localhost:8123/v1).")
        self.reasoning = reasoning
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
        # Toggle the model's chain-of-thought. With thinking on, the reasoning is
        # returned in a separate `reasoning` field and `content` holds the clean answer.
        extra_body = {"chat_template_kwargs": {"thinking": self.reasoning}}
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]

        self.last_reasoning = None
        attempts = 0
        while attempts < num_attempts:
            try:
                chat = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    extra_body=extra_body,
                    **params
                )
                self.last_reasoning = self._extract_reasoning(chat)
                return self._extract_response(chat)
            except (APIConnectionError, RateLimitError):
                attempts += 1
                time.sleep(1)
            except Exception as e:
                return None

        return None
