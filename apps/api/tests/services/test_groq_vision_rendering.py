"""Unit tests for Phase 0.7 multimodal message rendering in GroqProvider.

_render_message must keep text-only messages as plain strings (backward
compatible) and expand image-bearing messages into the content-parts array
that Groq's vision models expect.
"""
from src.infrastructure.llm.base import LLMMessage
from src.infrastructure.llm.groq_provider import _render_message, _render_messages

_DATA_URL = "data:image/png;base64,AAAA"


def test_text_only_message_renders_as_plain_string():
    msg = LLMMessage(role="user", content="What is 2 + 2?")
    rendered = _render_message(msg)
    assert rendered == {"role": "user", "content": "What is 2 + 2?"}


def test_message_without_images_property_is_false():
    assert LLMMessage(role="user", content="hi").has_images is False
    assert LLMMessage(role="user", content="hi", images=[]).has_images is False


def test_image_message_renders_content_parts():
    msg = LLMMessage(role="user", content="Solve this", images=[_DATA_URL])
    rendered = _render_message(msg)

    assert rendered["role"] == "user"
    assert isinstance(rendered["content"], list)
    assert rendered["content"][0] == {"type": "text", "text": "Solve this"}
    assert rendered["content"][1] == {
        "type": "image_url",
        "image_url": {"url": _DATA_URL},
    }


def test_image_message_without_text_omits_text_part():
    msg = LLMMessage(role="user", content="", images=[_DATA_URL])
    rendered = _render_message(msg)

    parts = rendered["content"]
    assert len(parts) == 1
    assert parts[0]["type"] == "image_url"


def test_multiple_images_render_all_parts():
    msg = LLMMessage(role="user", content="Compare", images=[_DATA_URL, _DATA_URL])
    parts = _render_message(msg)["content"]
    image_parts = [p for p in parts if p["type"] == "image_url"]
    assert len(image_parts) == 2


def test_render_messages_mixes_text_and_vision_turns():
    messages = [
        LLMMessage(role="system", content="You are a tutor."),
        LLMMessage(role="user", content="Earlier question"),
        LLMMessage(role="assistant", content="Earlier answer"),
        LLMMessage(role="user", content="Look at this", images=[_DATA_URL]),
    ]
    rendered = _render_messages(messages)

    # History + system turns stay plain strings.
    assert rendered[0]["content"] == "You are a tutor."
    assert isinstance(rendered[1]["content"], str)
    assert isinstance(rendered[2]["content"], str)
    # Only the final user turn carries image parts.
    assert isinstance(rendered[3]["content"], list)
