from collections.abc import AsyncGenerator
from uuid import UUID

import structlog

from src.application.dtos.chat import (
    ConversationResponse,
    ConversationWithMessagesResponse,
    MessageResponse,
    SendMessageRequest,
)
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
    ) -> None:
        self._conversations = conversation_repo
        self._messages = message_repo
        self._llm = llm_provider
        self._prompts = prompt_loader

    async def stream_response(
        self,
        user_id: UUID,
        dto: SendMessageRequest,
        llm_model: str,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        conversation = await self._get_or_create_conversation(user_id, dto.conversation_id)

        # Persist user message
        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=dto.message,
        )
        await self._messages.create(user_msg)

        # Auto-title the conversation on first message
        if not conversation.title:
            conversation.set_title(dto.message[:80])
            await self._conversations.update(conversation)

        # Build LLM context
        history = await self._messages.list_by_conversation(
            conversation.id, limit=_CONTEXT_MESSAGES
        )
        system_prompt = await self._prompts.get("default_system")
        llm_messages = [LLMMessage(role="system", content=system_prompt)]
        llm_messages += [LLMMessage(role=m.role, content=m.content) for m in history[:-1]]
        llm_messages.append(LLMMessage(role="user", content=dto.message))

        config = LLMConfig(model=llm_model, temperature=temperature, stream=True)

        # Stream and collect full response
        full_content: list[str] = []

        # Yield conversation_id header chunk first so client knows which conversation
        yield f'data: {{"type":"meta","conversation_id":"{conversation.id}"}}\n\n'

        async for chunk in self._llm.stream(llm_messages, config):
            full_content.append(chunk)
            escaped = chunk.replace('"', '\\"').replace("\n", "\\n")
            yield f'data: {{"type":"chunk","content":"{escaped}"}}\n\n'

        # Persist assistant message after streaming completes
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
        new_conv = Conversation(user_id=user_id)
        return await self._conversations.create(new_conv)

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
