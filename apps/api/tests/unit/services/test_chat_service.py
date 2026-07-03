from uuid import uuid4

import pytest

from src.application.services.chat_service import ChatService
from src.domain.exceptions import AuthorizationError, EntityNotFound


@pytest.fixture
def chat_service(mock_conversation_repo, mock_message_repo, mock_llm_provider, mock_prompt_loader):
    return ChatService(
        conversation_repo=mock_conversation_repo,
        message_repo=mock_message_repo,
        llm_provider=mock_llm_provider,
        prompt_loader=mock_prompt_loader,
    )


@pytest.mark.asyncio
async def test_list_conversations(chat_service, mock_conversation_repo, mock_message_repo, user_id, sample_conversation):
    mock_conversation_repo.list_by_user.return_value = ([sample_conversation], 1)
    mock_message_repo.count_by_conversation.return_value = 5

    result, total = await chat_service.list_conversations(user_id, page=1, limit=20)
    assert len(result) == 1
    assert total == 1
    assert result[0].message_count == 5


@pytest.mark.asyncio
async def test_get_conversation_not_found(chat_service, mock_conversation_repo, user_id):
    mock_conversation_repo.get_by_id.return_value = None
    with pytest.raises(EntityNotFound):
        await chat_service.get_conversation(user_id, uuid4())


@pytest.mark.asyncio
async def test_get_conversation_wrong_user(chat_service, mock_conversation_repo, sample_conversation):
    mock_conversation_repo.get_by_id.return_value = sample_conversation
    wrong_user_id = uuid4()

    with pytest.raises(AuthorizationError):
        await chat_service.get_conversation(wrong_user_id, sample_conversation.id)


@pytest.mark.asyncio
async def test_delete_conversation_not_found(chat_service, mock_conversation_repo, user_id):
    mock_conversation_repo.get_by_id.return_value = None
    with pytest.raises(EntityNotFound):
        await chat_service.delete_conversation(user_id, uuid4())
