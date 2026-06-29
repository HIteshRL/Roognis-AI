import pytest
from unittest.mock import AsyncMock
from src.application.dtos.knowledge import RetrievedContext, SearchResultItem
from src.application.services.prompt_assembly_service import PromptAssemblyService
from src.infrastructure.llm.base import LLMMessage

RAG_TEMPLATE = "System with context: {context}"
NO_CTX_TEMPLATE = "System without context."


@pytest.fixture
def mock_prompt_loader():
    loader = AsyncMock()
    async def get(name: str) -> str:
        return RAG_TEMPLATE if name == "rag_system" else NO_CTX_TEMPLATE
    loader.get = get
    return loader


@pytest.fixture
def svc(mock_prompt_loader):
    return PromptAssemblyService(mock_prompt_loader)


def _context(has: bool) -> RetrievedContext:
    chunks = [
        SearchResultItem(
            chunk_id="c1",
            document_id="d1",
            document_title="Algorithms",
            content="Binary search works on sorted arrays.",
            score=0.9,
            page_number=1,
            metadata={},
        )
    ] if has else []
    return RetrievedContext(chunks=chunks, has_context=has, query="test query")


@pytest.mark.asyncio
async def test_with_context_uses_rag_template(svc):
    msgs = await svc.build_messages("my question", [], _context(True))
    system = msgs[0]
    assert system.role == "system"
    assert "Binary search" in system.content


@pytest.mark.asyncio
async def test_without_context_uses_no_context_template(svc):
    msgs = await svc.build_messages("my question", [], _context(False))
    system = msgs[0]
    assert system.role == "system"
    assert NO_CTX_TEMPLATE in system.content


@pytest.mark.asyncio
async def test_history_is_included_between_system_and_user(svc):
    history = [
        LLMMessage(role="user", content="prev question"),
        LLMMessage(role="assistant", content="prev answer"),
    ]
    msgs = await svc.build_messages("new question", history, _context(False))
    assert msgs[0].role == "system"
    assert msgs[1].role == "user"
    assert msgs[2].role == "assistant"
    assert msgs[3].role == "user"
    assert msgs[3].content == "new question"


@pytest.mark.asyncio
async def test_user_message_always_last(svc):
    msgs = await svc.build_messages("final question", [], _context(True))
    assert msgs[-1].role == "user"
    assert msgs[-1].content == "final question"
