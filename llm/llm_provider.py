from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, system_prompt: str, model: str):
        self.system_prompt = system_prompt
        self.model = model

    @abstractmethod
    def generate(
        self,
        prompt: str,
        max_tokens: int = 50,
        num_attempts: int = 5,
        temperature: float = 0.2,
        n: int = 1
    ) -> str | list[str] | None:
        """Generate a response from the LLM."""
        pass

    def _extract_response(self, chat) -> str | list[str] | None:
        """Extract response content from chat completion."""
        if len(chat.choices) > 1:
            result = []
            for choice in chat.choices:
                result.append(self._extract_choice_content(choice))
            return result
        return self._extract_choice_content(chat.choices[0])

    @staticmethod
    def _extract_choice_content(choice) -> str:
        """Extract content from a single choice."""
        if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
            return choice.message.content
        elif hasattr(choice, 'text'):
            return choice.text
        elif isinstance(choice, dict):
            if 'message' in choice and 'content' in choice['message']:
                return choice['message']['content']
            elif 'text' in choice:
                return choice['text']
            else:
                return str(choice)
        else:
            return str(choice)


def create_provider(
    provider_type: str,
    system_prompt: str,
    model: str,
    **kwargs
) -> LLMProvider:
    """Factory function to create LLM providers.

    Args:
        provider_type: 'anthropic' or 'openrouter'
        system_prompt: System prompt for the model
        model: Model ID
        **kwargs: Additional provider-specific arguments

    Returns:
        LLMProvider instance
    """
    from .anthropic import AnthropicProvider
    from .openrouter import OpenRouterProvider

    providers = {
        "anthropic": AnthropicProvider,
        "openrouter": OpenRouterProvider,
    }

    if provider_type not in providers:
        raise ValueError(f"Unknown provider: {provider_type}. Available: {list(providers.keys())}")

    return providers[provider_type](system_prompt, model, **kwargs)
