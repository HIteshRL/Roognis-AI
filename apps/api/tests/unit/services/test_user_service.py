import pytest
from uuid import uuid4

from src.application.dtos.user import UpdateProfileRequest, UpdateSettingsRequest
from src.application.services.user_service import UserService
from src.domain.exceptions import EntityNotFound


@pytest.fixture
def user_service(mock_profile_repo, mock_settings_repo):
    return UserService(profile_repo=mock_profile_repo, settings_repo=mock_settings_repo)


@pytest.mark.asyncio
async def test_get_profile_success(user_service, mock_profile_repo, sample_profile, user_id):
    mock_profile_repo.get_by_user_id.return_value = sample_profile
    result = await user_service.get_profile(user_id)
    assert result.user_id == str(user_id)


@pytest.mark.asyncio
async def test_get_profile_not_found(user_service, mock_profile_repo):
    mock_profile_repo.get_by_user_id.return_value = None
    with pytest.raises(EntityNotFound):
        await user_service.get_profile(uuid4())


@pytest.mark.asyncio
async def test_update_profile(user_service, mock_profile_repo, sample_profile, user_id):
    mock_profile_repo.get_by_user_id.return_value = sample_profile
    updated = sample_profile
    updated.full_name = "Updated Name"
    mock_profile_repo.update.return_value = updated

    dto = UpdateProfileRequest(full_name="Updated Name")
    result = await user_service.update_profile(user_id, dto)
    assert result.full_name == "Updated Name"


@pytest.mark.asyncio
async def test_update_settings(user_service, mock_settings_repo, sample_settings, user_id):
    mock_settings_repo.get_by_user_id.return_value = sample_settings
    updated = sample_settings
    updated.theme = "light"
    mock_settings_repo.update.return_value = updated

    dto = UpdateSettingsRequest(theme="light")
    result = await user_service.update_settings(user_id, dto)
    assert result.theme == "light"
