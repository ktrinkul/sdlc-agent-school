from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from typing import Any

from openai import OpenAI


logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract interface for language model clients."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_structured(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        raise NotImplementedError


class OpenAIClient(LLMClient):
    """OpenAI-compatible chat completion client."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        referer: str | None = None,
        title: str | None = None,
    ) -> None:
        self._model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._extra_headers = {}
        if referer:
            self._extra_headers["HTTP-Referer"] = referer
        if title:
            self._extra_headers["X-Title"] = title

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Return plain-text completion."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        for attempt in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    extra_headers=self._extra_headers or None,
                )
                if response.usage:
                    logger.info(
                        "LLM usage: prompt=%s completion=%s total=%s",
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                        response.usage.total_tokens,
                    )
                return response.choices[0].message.content or ""
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    raise
                logger.warning("LLM request failed (%s), retrying", exc)

    def generate_structured(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        """Return a JSON object from the model, with repair fallback."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                response_format={"type": "json_object"},
                extra_headers=self._extra_headers or None,
            )
            content = response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("Structured response_format failed: %s", exc)
            content = self.generate(prompt=prompt, system=system)

        parsed = self._try_parse_json(content)
        if parsed is not None:
            return parsed

        repaired = self._repair_json(content)
        parsed = self._try_parse_json(repaired)
        if parsed is not None:
            return parsed

        logger.error("Failed to parse structured response after repair.")
        raise json.JSONDecodeError("Invalid JSON after repair", content, 0)

    def _try_parse_json(self, content: str) -> dict[str, Any] | None:
        if not content or not content.strip():
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start == -1 or end == -1 or end <= start:
                logger.error("Failed to parse structured response: empty JSON")
                return None
            snippet = content[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError as exc:
                logger.error("Failed to parse structured response: %s", exc)
                return None

    def _repair_json(self, content: str) -> str:
        prompt = (
            "Fix the following content to valid JSON. "
            "Return only the JSON object and nothing else.\n\n"
            f"Content:\n{content}"
        )
        return self.generate(prompt=prompt, system="Return only valid JSON.")


class YandexGPTClient(LLMClient):
    def __init__(self, api_key: str, folder_id: str, model: str) -> None:
        self._api_key = api_key
        self._folder_id = folder_id
        self._model = model

    def generate(self, prompt: str, system: str | None = None) -> str:
        raise NotImplementedError("YandexGPT client not implemented")

    def generate_structured(self, prompt: str, system: str | None = None) -> dict[str, Any]:
        raise NotImplementedError("YandexGPT client not implemented")


def create_llm_client(provider: str, **kwargs: Any) -> LLMClient:
    if provider == "openai":
        return OpenAIClient(**kwargs)
    if provider == "yandex":
        return YandexGPTClient(**kwargs)
    raise ValueError(f"Unsupported LLM provider: {provider}")
