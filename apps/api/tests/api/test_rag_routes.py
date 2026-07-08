"""
Tests for /rag/* endpoints — curriculum-filtered RAG API.
"""
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("API_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("GROQ_API_KEY", "test-key")

from src.infrastructure.logging.setup import configure_logging

configure_logging("INFO", "console")

from src.application.dtos.knowledge import (
    RagChunkResult,
    RagObservability,
    RagQueryResponse,
)
from src.application.dtos.user import UserResponse


def _admin_user():
    return UserResponse(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="admin@example.com",
        username="admin",
        is_active=True,
        is_verified=True,
        is_admin=True,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )


def _student_user():
    return UserResponse(
        id="223e4567-e89b-12d3-a456-426614174001",
        email="student@example.com",
        username="student",
        is_active=True,
        is_verified=True,
        is_admin=False,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    )


@pytest.mark.asyncio
async def test_rag_query_returns_structured_response():
    from src.application.interfaces import dependencies
    from src.main import app

    mock_rag_result = RagQueryResponse(
        query="What is photosynthesis?",
        answer="Photosynthesis is the process by which green plants make food using sunlight.",
        has_context=True,
        chunks=[
            RagChunkResult(
                chunk_id="c1",
                document_id="d1",
                document_title="Nutrition in Plants",
                content="Photosynthesis is the process...",
                score=0.90,
                page_number=5,
                grade="7",
                subject="Science",
                chapter="Nutrition in Plants",
                topic="Photosynthesis",
            )
        ],
        curriculum_filter={"grade": "7", "subject": "Science"},
        observability=RagObservability(
            embedding_ms=12.3,
            retrieval_ms=45.6,
            llm_ms=210.0,
            total_ms=270.0,
            chunks_retrieved=1,
            chunks_used=1,
            similarity_scores=[0.90],
            token_usage={"prompt_tokens": 200, "completion_tokens": 50, "total_tokens": 250},
        ),
    )

    mock_rag_svc = AsyncMock()
    mock_rag_svc.query = AsyncMock(return_value=mock_rag_result)

    app.dependency_overrides[dependencies.get_current_user] = lambda: _student_user()
    app.dependency_overrides[dependencies.get_rag_service] = lambda: mock_rag_svc

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/rag/query",
                json={
                    "query": "What is photosynthesis?",
                    "curriculum": {"grade": "7", "subject": "Science"},
                    "top_k": 5,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["has_context"] is True
    assert "photosynthesis" in body["data"]["answer"].lower()
    assert len(body["data"]["chunks"]) == 1
    assert body["data"]["chunks"][0]["grade"] == "7"
    assert body["data"]["observability"]["chunks_used"] == 1
    assert body["data"]["curriculum_filter"]["grade"] == "7"


@pytest.mark.asyncio
async def test_rag_query_requires_auth():
    from src.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/rag/query",
            json={"query": "What is photosynthesis?"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rag_status_returns_job():
    from src.application.dtos.knowledge import IngestionJobResponse
    from src.application.interfaces import dependencies
    from src.main import app

    mock_doc_svc = AsyncMock()
    mock_doc_svc.get_job_status = AsyncMock(return_value=IngestionJobResponse(
        id="job-1",
        document_id="doc-1",
        status="done",
        progress=100,
        error_message=None,
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
    ))

    app.dependency_overrides[dependencies.get_current_user] = lambda: _student_user()
    app.dependency_overrides[dependencies.get_document_service] = lambda: mock_doc_svc

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/rag/status/123e4567-e89b-12d3-a456-426614174000")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "done"
    assert body["data"]["progress"] == 100


@pytest.mark.asyncio
async def test_rag_delete_requires_admin():
    from src.application.interfaces import dependencies
    from src.main import app

    # Student cannot delete
    app.dependency_overrides[dependencies.get_current_user] = lambda: _student_user()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/rag/document/123e4567-e89b-12d3-a456-426614174000")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_rag_delete_as_admin():
    from src.application.interfaces import dependencies
    from src.main import app

    mock_doc_svc = AsyncMock()
    mock_doc_svc.delete_document = AsyncMock(return_value=None)

    app.dependency_overrides[dependencies.get_current_user] = lambda: _admin_user()
    app.dependency_overrides[dependencies.require_admin] = lambda: _admin_user()
    app.dependency_overrides[dependencies.get_document_service] = lambda: mock_doc_svc

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/rag/document/123e4567-e89b-12d3-a456-426614174000")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "deleted" in body["message"].lower()


@pytest.mark.asyncio
async def test_rag_query_validation_error_on_empty_query():
    from src.application.interfaces import dependencies
    from src.main import app

    app.dependency_overrides[dependencies.get_current_user] = lambda: _student_user()
    app.dependency_overrides[dependencies.get_rag_service] = lambda: AsyncMock()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/rag/query",
                json={"query": ""},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
