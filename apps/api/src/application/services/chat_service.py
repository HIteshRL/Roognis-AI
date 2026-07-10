from collections.abc import AsyncGenerator
from uuid import UUID

import structlog

from src.application.dtos.chat import (
    ConversationResponse,
    ConversationWithMessagesResponse,
    MessageResponse,
    SendMessageRequest,
)
from src.application.services.context_validation_service import ContextValidationService
from src.application.services.learner_context_service import LearnerContextService
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.application.services.retrieval_service import RetrievalService
from src.domain.entities.conversation import Conversation, Message
from src.domain.exceptions import AuthorizationError, EntityNotFound
from src.domain.repositories.conversation_repository import (
    AbstractConversationRepository,
    AbstractMessageRepository,
)
from src.infrastructure.llm.base import AbstractLLMProvider, LLMConfig, LLMMessage
from src.infrastructure.llm.prompt_loader import PromptLoader

logger = structlog.get_logger(__name__)

_CONTEXT_MESSAGES = 20


class ChatService:
    def __init__(
        self,
        conversation_repo: AbstractConversationRepository,
        message_repo: AbstractMessageRepository,
        llm_provider: AbstractLLMProvider,
        prompt_loader: PromptLoader,
        retrieval_svc: RetrievalService | None = None,
        prompt_assembly_svc: PromptAssemblyService | None = None,
        context_validation_svc: ContextValidationService | None = None,
        retrieval_enabled: bool = True,
        learner_context_svc: LearnerContextService | None = None,
    ) -> None:
        self._conversations = conversation_repo
        self._messages = message_repo
        self._llm = llm_provider
        self._prompts = prompt_loader
        self._retrieval = retrieval_svc
        self._prompt_assembly = prompt_assembly_svc
        self._context_validation = context_validation_svc
        self._retrieval_enabled = retrieval_enabled
        self._learner_context = learner_context_svc

    async def stream_response(
        self,
        user_id: UUID,
        dto: SendMessageRequest,
        llm_model: str,
        temperature: float,
        current_intent: str = "unknown",
        knowledge_base_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        conversation = await self._get_or_create_conversation(user_id, dto.conversation_id)

        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=dto.message,
        )
        await self._messages.create(user_msg)

        if not conversation.title:
            conversation.set_title(dto.message[:80])
            await self._conversations.update(conversation)

        history = await self._messages.list_by_conversation(
            conversation.id, limit=_CONTEXT_MESSAGES
        )
        history_msgs = [
            LLMMessage(role=m.role, content=m.content) for m in history[:-1]
        ]

        # ── Phase 0.3: condition every response on the learner's profile ──────
        learner_context: str | None = None
        if self._learner_context:
            try:
                learner_context = await self._learner_context.build(user_id, current_intent=current_intent)
            except Exception as exc:
                logger.warning("learner_context_build_failed", error=str(exc), user_id=str(user_id))

        # ── RAG: retrieve context, build grounded prompt ──────────────────────
        if self._retrieval_enabled and self._retrieval and self._prompt_assembly:
            raw_context, _timing = await self._retrieval.retrieve(
                dto.message, knowledge_base_id=knowledge_base_id
            )
            if self._context_validation:
                context = self._context_validation.validate(raw_context)
            else:
                context = raw_context

            llm_messages = await self._prompt_assembly.build_messages(
                user_message=dto.message,
                history=history_msgs,
                context=context,
                learner_context=learner_context,
            )

            sources_meta = {
                "has_context": context.has_context,
                "source_count": len(context.chunks),
                "sources": [
                    {"title": c.document_title, "score": round(c.score, 3)}
                    for c in context.chunks
                ],
            }
        else:
            # Phase 0.1 fallback — plain LLM without RAG
            system_prompt = await self._prompts.get("default_system")
            if learner_context:
                system_prompt = f"{system_prompt}\n\n{learner_context}"
            llm_messages = [LLMMessage(role="system", content=system_prompt)]
            llm_messages.extend(history_msgs)
            llm_messages.append(LLMMessage(role="user", content=dto.message))
            sources_meta = {"has_context": False, "source_count": 0, "sources": []}

        config = LLMConfig(model=llm_model, temperature=temperature, stream=True)
        full_content: list[str] = []

        import json
        yield f'data: {{"type":"meta","conversation_id":"{conversation.id}","rag":{json.dumps(sources_meta)}}}\n\n'

        async for chunk in self._llm.stream(llm_messages, config):
            full_content.append(chunk)
            escaped = chunk.replace('"', '\\"').replace("\n", "\\n")
            yield f'data: {{"type":"chunk","content":"{escaped}"}}\n\n'

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="".join(full_content),
        )
        saved = await self._messages.create(assistant_msg)
        yield f'data: {{"type":"done","message_id":"{saved.id}"}}\n\n'

        logger.info(
            "chat_streamed",
            conversation_id=str(conversation.id),
            user_id=str(user_id),
            rag_enabled=self._retrieval_enabled and self._retrieval is not None,
            has_context=sources_meta["has_context"],
        )

    async def list_conversations(
        self, user_id: UUID, page: int, limit: int
    ) -> tuple[list[ConversationResponse], int]:
        convs, total = await self._conversations.list_by_user(user_id, page, limit)
        responses = []
        for c in convs:
            count = await self._messages.count_by_conversation(c.id)
            responses.append(self._conv_to_response(c, count))
        return responses, total

    async def get_conversation(
        self, user_id: UUID, conversation_id: UUID
    ) -> ConversationWithMessagesResponse:
        conv = await self._conversations.get_by_id(conversation_id)
        if not conv:
            raise EntityNotFound("Conversation not found")
        if conv.user_id != user_id:
            raise AuthorizationError("Access denied")

        messages = await self._messages.list_by_conversation(conversation_id)
        return ConversationWithMessagesResponse(
            conversation=self._conv_to_response(conv, len(messages)),
            messages=[self._msg_to_response(m) for m in messages],
        )

    async def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        conv = await self._conversations.get_by_id(conversation_id)
        if not conv:
            raise EntityNotFound("Conversation not found")
        if conv.user_id != user_id:
            raise AuthorizationError("Access denied")
        await self._conversations.delete(conversation_id)

    async def _get_or_create_conversation(
        self, user_id: UUID, conversation_id: UUID | None
    ) -> Conversation:
        if conversation_id:
            conv = await self._conversations.get_by_id(conversation_id)
            if not conv:
                raise EntityNotFound("Conversation not found")
            if conv.user_id != user_id:
                raise AuthorizationError("Access denied")
            return conv
        return await self._conversations.create(Conversation(user_id=user_id))

    @staticmethod
    def _conv_to_response(c: Conversation, count: int = 0) -> ConversationResponse:
        return ConversationResponse(
            id=str(c.id),
            user_id=str(c.user_id),
            title=c.title,
            is_archived=c.is_archived,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
            message_count=count,
        )

    @staticmethod
    def _msg_to_response(m: Message) -> MessageResponse:
        return MessageResponse(
            id=str(m.id),
            conversation_id=str(m.conversation_id),
            role=m.role,
            content=m.content,
            token_count=m.token_count,
            created_at=m.created_at.isoformat(),
        )
