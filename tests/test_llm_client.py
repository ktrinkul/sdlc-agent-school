from unittest.mock import Mock

from src.core.llm_client import OpenAIClient


def test_openai_client_generate() -> None:
    fake_response = Mock()
    fake_choice = Mock()
    fake_choice.message.content = "ok"
    fake_response.choices = [fake_choice]
    fake_chat = Mock()
    fake_chat.completions.create.return_value = fake_response
    fake_client = Mock()
    fake_client.chat = fake_chat

    client = OpenAIClient(api_key="key", model="gpt-4o-mini")
    client._client = fake_client

    assert client.generate("ping") == "ok"


def test_openai_client_generate_structured() -> None:
    fake_response = Mock()
    fake_choice = Mock()
    fake_choice.message.content = '{"key": "value"}'
    fake_response.choices = [fake_choice]
    fake_chat = Mock()
    fake_chat.completions.create.return_value = fake_response
    fake_client = Mock()
    fake_client.chat = fake_chat

    client = OpenAIClient(api_key="key", model="gpt-4o-mini")
    client._client = fake_client

    assert client.generate_structured("ping") == {"key": "value"}
