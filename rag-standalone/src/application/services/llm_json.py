"""Small helper: call the LLM and parse a single JSON object from its reply.

Used by the guardrail + grounding services for structured decisions. Defensive:
returns {} on any parse failure so callers can fall back to safe defaults.
"""
import json
import re

from src.infrastructure.llm.base import AbstractLLMProvider, LLMConfig, LLMMessage


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return {}
    try:
        obj = json.loads(match.group(0))
        return obj if isinstance(obj, dict) else {}
    except (ValueError, TypeError):
        return {}


async def llm_json(
    llm: AbstractLLMProvider,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 400,
) -> dict:
    resp = await llm.complete(
        [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)],
        LLMConfig(model=model, temperature=0.0, max_tokens=max_tokens, stream=False),
    )
    return extract_json(resp.content)
