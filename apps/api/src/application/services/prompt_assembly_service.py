import structlog

from src.application.dtos.knowledge import RetrievedContext
from src.infrastructure.llm.base import LLMMessage
from src.infrastructure.llm.prompt_loader import PromptLoader

logger = structlog.get_logger(__name__)

_MAX_CONTEXT_TOKENS = 3000


class PromptAssemblyService:
    """
    Assembles the LLM message list from history + retrieved context.
    Never concatenates strings manually — all templates come from PromptLoader.
    Enforces token budget on context injection.
    """

    def __init__(self, prompt_loader: PromptLoader) -> None:
        self._prompts = prompt_loader

    async def build_messages(
        self,
        user_message: str,
        history: list[LLMMessage],
        context: RetrievedContext,
        learner_context: str | None = None,
    ) -> list[LLMMessage]:
        if context.has_context:
            system_template = await self._prompts.get("rag_system")
            context_text = self._trim_context(context.formatted_context, _MAX_CONTEXT_TOKENS)
            system_content = system_template.replace("{context}", context_text)
        else:
            system_content = await self._prompts.get("rag_no_context")

        if learner_context:
            system_content = f"{system_content}\n\n{learner_context}"

        messages: list[LLMMessage] = [LLMMessage(role="system", content=system_content)]
        messages.extend(history)
        messages.append(LLMMessage(role="user", content=user_message))

        logger.info(
            "prompt_assembled",
            has_context=context.has_context,
            context_chunks=len(context.chunks),
            history_turns=len(history),
            has_learner_context=learner_context is not None,
        )
        return messages

    @staticmethod
    def _trim_context(context_text: str, max_tokens: int) -> str:
        # Rough 4-chars-per-token estimate to avoid importing tiktoken here
        max_chars = max_tokens * 4
        if len(context_text) <= max_chars:
            return context_text
        return context_text[:max_chars] + "\n\n[Context truncated due to length]"
