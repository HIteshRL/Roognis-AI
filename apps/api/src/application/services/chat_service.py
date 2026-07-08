import asyncio
import json
from collections.abc import AsyncGenerator
from uuid import UUID

import structlog

from src.application.dtos.chat import (
    AttachmentResponse,
    ConversationResponse,
    ConversationWithMessagesResponse,
    MessageResponse,
    SendMessageRequest,
    SubjectCountResponse,
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
        profile_repo=None,
        attachment_repo=None,
        attachment_svc=None,
        vision_model: str | None = None,
        vision_enabled: bool = False,
        response_image_svc=None,
        response_image_enabled: bool = False,
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
        self._profile_repo = profile_repo
        self._attachment_repo = attachment_repo
        self._attachment_svc = attachment_svc
        self._vision_model = vision_model
        self._vision_enabled = vision_enabled
        self._response_image_svc = response_image_svc
        self._response_image_enabled = response_image_enabled

    async def stream_response(
        self,
        user_id: UUID,
        dto: SendMessageRequest,
        llm_model: str,
        temperature: float,
        current_intent: str = "unknown",
    ) -> AsyncGenerator[str, None]:
        conversation = await self._get_or_create_conversation(
            user_id, dto.conversation_id, subject=dto.subject, chapter=dto.chapter,
        )

        user_msg = Message(
            conversation_id=conversation.id,
            role="user",
            content=dto.message,
        )
        await self._messages.create(user_msg)

        # ── Phase 0.7: link uploaded images and prepare them for the vision call
        image_data_urls: list[str] = []
        if dto.attachment_ids and self._attachment_svc and self._attachment_repo:
            try:
                owned_ids, image_data_urls = await self._attachment_svc.data_urls_for(
                    dto.attachment_ids, user_id
                )
                if owned_ids:
                    await self._attachment_repo.link_to_message(owned_ids, user_msg.id)
            except Exception as exc:
                logger.warning(
                    "attachment_link_failed", error=str(exc), user_id=str(user_id)
                )
                image_data_urls = []

        use_vision = bool(image_data_urls) and self._vision_enabled and bool(
            self._vision_model
        )

        # ── v0.71: start generating the default illustrative image now so it
        # overlaps retrieval + text streaming. Persisted after the answer saves.
        image_task = None
        if self._response_image_enabled and self._response_image_svc:
            img_prompt = self._response_image_svc.build_prompt(
                question=dto.message,
                primary_concept=None,
                subject=conversation.subject,
                chapter=conversation.chapter,
            )
            image_task = asyncio.create_task(self._response_image_svc.generate(img_prompt))

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

        # ── Subject/chapter scoping — reduces hallucination ──────────────────
        subject_context = self._build_subject_context(conversation.subject, conversation.chapter)
        if subject_context:
            learner_context = (
                f"{learner_context}\n\n{subject_context}" if learner_context else subject_context
            )

        # ── CAG: context-aware retrieval with curriculum scoping ────────────
        if self._retrieval_enabled and self._retrieval and self._prompt_assembly:
            grade = await self._get_student_grade(user_id)

            raw_context, retrieve_timing = await self._retrieval.retrieve_contextual(
                query=dto.message,
                subject=conversation.subject,
                chapter=conversation.chapter,
                grade=grade,
            )
            cascade_level = retrieve_timing.get("cascade_level", "unscoped")

            if self._context_validation:
                context = self._context_validation.validate(raw_context)
            else:
                context = raw_context

            if context.has_context:
                llm_messages = await self._prompt_assembly.build_messages(
                    user_message=dto.message,
                    history=history_msgs,
                    context=context,
                    learner_context=learner_context,
                )
            else:
                system_prompt = await self._prompts.get("default_system")
                if learner_context:
                    system_prompt = f"{system_prompt}\n\n{learner_context}"
                llm_messages = [LLMMessage(role="system", content=system_prompt)]
                llm_messages.extend(history_msgs)
                llm_messages.append(LLMMessage(role="user", content=dto.message))

            sources_meta = {
                "has_context": context.has_context,
                "source_count": len(context.chunks),
                "cascade_level": cascade_level,
                "sources": [
                    {
                        "title": c.document_title,
                        "score": round(c.score, 3),
                        "subject": c.metadata.get("subject"),
                        "chapter": c.metadata.get("chapter"),
                    }
                    for c in context.chunks
                ],
            }
        else:
            system_prompt = await self._prompts.get("default_system")
            if learner_context:
                system_prompt = f"{system_prompt}\n\n{learner_context}"
            llm_messages = [LLMMessage(role="system", content=system_prompt)]
            llm_messages.extend(history_msgs)
            llm_messages.append(LLMMessage(role="user", content=dto.message))
            sources_meta = {
                "has_context": False,
                "source_count": 0,
                "cascade_level": "none",
                "sources": [],
            }

        # ── Phase 0.7: route to the vision model and attach images to the
        # final user turn. The image parts ride on the last user message
        # regardless of which prompt-assembly path produced llm_messages.
        if use_vision:
            for msg in reversed(llm_messages):
                if msg.role == "user":
                    msg.images = image_data_urls
                    break

        model = self._vision_model if use_vision else llm_model
        config = LLMConfig(model=model, temperature=temperature, stream=True)
        full_content: list[str] = []

        meta = {
            "type": "meta",
            "conversation_id": str(conversation.id),
            "subject": conversation.subject,
            "chapter": conversation.chapter,
            "rag": sources_meta,
            "vision": use_vision,
        }
        yield f"data: {json.dumps(meta)}\n\n"

        async for chunk in self._llm.stream(llm_messages, config):
            full_content.append(chunk)
            # json.dumps handles all escaping (backslashes, control chars, unicode).
            # Manual escaping corrupted LaTeX/backslash content, e.g. "\frac".
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content="".join(full_content),
        )
        saved = await self._messages.create(assistant_msg)

        # ── v0.71: persist the default generated image and notify the client.
        if image_task is not None:
            try:
                result = await image_task
            except Exception:
                result = None
            if result is not None:
                attachment = await self._response_image_svc.persist(
                    user_id, saved.id, result
                )
                if attachment is not None:
                    image_event = {
                        "type": "image",
                        "attachment_id": str(attachment.id),
                        "url": f"/api/v1/chat/attachments/{attachment.id}",
                        "content_type": attachment.content_type,
                    }
                    yield f"data: {json.dumps(image_event)}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'message_id': str(saved.id)})}\n\n"

        logger.info(
            "chat_streamed",
            conversation_id=str(conversation.id),
            user_id=str(user_id),
            rag_enabled=self._retrieval_enabled and self._retrieval is not None,
            has_context=sources_meta["has_context"],
        )

    async def list_conversations(
        self, user_id: UUID, page: int, limit: int,
        subject: str | None = None, chapter: str | None = None,
    ) -> tuple[list[ConversationResponse], int]:
        convs, total = await self._conversations.list_by_user(
            user_id, page, limit, subject=subject, chapter=chapter,
        )
        responses = []
        for c in convs:
            count = await self._messages.count_by_conversation(c.id)
            responses.append(self._conv_to_response(c, count))
        return responses, total

    async def get_subject_counts(self, user_id: UUID) -> list[SubjectCountResponse]:
        rows = await self._conversations.subject_counts(user_id)
        return [
            SubjectCountResponse(
                subject=subject or "General",
                count=count,
            )
            for subject, count in rows
        ]

    async def get_chapters(
        self, user_id: UUID, subject: str
    ) -> list[tuple[str, int]]:
        rows = await self._conversations.chapter_counts(user_id, subject)
        return [(chapter, count) for chapter, count in rows if chapter]

    async def get_conversation_scope(
        self, user_id: UUID, conversation_id: UUID
    ) -> tuple[str | None, str | None]:
        """The persisted (subject, chapter) for a conversation the user owns.

        Follow-up chat turns send only conversation_id — subject/chapter are
        absent from the request — so the learning pipeline must read the stored
        scope rather than the empty payload. Returns (None, None) if the
        conversation is missing or not owned by the user (fail-open)."""
        conv = await self._conversations.get_by_id(conversation_id)
        if not conv or conv.user_id != user_id:
            return None, None
        return conv.subject, conv.chapter

    async def get_conversation(
        self, user_id: UUID, conversation_id: UUID
    ) -> ConversationWithMessagesResponse:
        conv = await self._conversations.get_by_id(conversation_id)
        if not conv:
            raise EntityNotFound("Conversation not found")
        if conv.user_id != user_id:
            raise AuthorizationError("Access denied")

        messages = await self._messages.list_by_conversation(conversation_id)

        attachments_by_message: dict[UUID, list] = {}
        if self._attachment_repo and messages:
            try:
                rows = await self._attachment_repo.list_by_messages(
                    [m.id for m in messages]
                )
                for a in rows:
                    if a.message_id is not None:
                        attachments_by_message.setdefault(a.message_id, []).append(a)
            except Exception as exc:
                logger.warning("load_attachments_failed", error=str(exc))

        return ConversationWithMessagesResponse(
            conversation=self._conv_to_response(conv, len(messages)),
            messages=[
                self._msg_to_response(m, attachments_by_message.get(m.id, []))
                for m in messages
            ],
        )

    async def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        conv = await self._conversations.get_by_id(conversation_id)
        if not conv:
            raise EntityNotFound("Conversation not found")
        if conv.user_id != user_id:
            raise AuthorizationError("Access denied")
        await self._conversations.delete(conversation_id)

    async def _get_or_create_conversation(
        self,
        user_id: UUID,
        conversation_id: UUID | None,
        subject: str | None = None,
        chapter: str | None = None,
    ) -> Conversation:
        if conversation_id:
            conv = await self._conversations.get_by_id(conversation_id)
            if not conv:
                raise EntityNotFound("Conversation not found")
            if conv.user_id != user_id:
                raise AuthorizationError("Access denied")
            return conv
        return await self._conversations.create(
            Conversation(user_id=user_id, subject=subject, chapter=chapter)
        )

    @staticmethod
    def _conv_to_response(c: Conversation, count: int = 0) -> ConversationResponse:
        return ConversationResponse(
            id=str(c.id),
            user_id=str(c.user_id),
            title=c.title,
            subject=c.subject,
            chapter=c.chapter,
            is_archived=c.is_archived,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
            message_count=count,
        )

    async def _get_student_grade(self, user_id: UUID) -> str | None:
        if not self._profile_repo:
            return None
        try:
            profile = await self._profile_repo.get_by_user_id(user_id)
            return profile.grade if profile else None
        except Exception:
            return None

    @staticmethod
    def _build_subject_context(subject: str | None, chapter: str | None) -> str | None:
        if not subject:
            return None
        ctx = f"## Subject Focus\nThis conversation is scoped to **{subject}**"
        if chapter:
            ctx += f", chapter: **{chapter}**"
        ctx += (
            ".\nKeep all explanations relevant to this subject and chapter. "
            "If the student asks about unrelated topics, gently redirect them."
        )
        return ctx

    @staticmethod
    def _msg_to_response(m: Message, attachments: list | None = None) -> MessageResponse:
        return MessageResponse(
            id=str(m.id),
            conversation_id=str(m.conversation_id),
            role=m.role,
            content=m.content,
            token_count=m.token_count,
            created_at=m.created_at.isoformat(),
            attachments=[
                AttachmentResponse(
                    id=str(a.id),
                    kind=a.kind,
                    content_type=a.content_type,
                    file_size=a.file_size,
                    url=f"/api/v1/chat/attachments/{a.id}",
                    created_at=a.created_at.isoformat(),
                )
                for a in (attachments or [])
            ],
        )
