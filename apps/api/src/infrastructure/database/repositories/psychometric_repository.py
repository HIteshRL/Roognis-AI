from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.psychometric import PsychometricProfile, PsychometricResponse
from src.domain.repositories.psychometric_repository import AbstractPsychometricRepository
from src.infrastructure.database.models.learning import StudentProfileModel
from src.infrastructure.database.models.psychometric import PsychometricResponseModel


def _to_response(m: PsychometricResponseModel) -> PsychometricResponse:
    r = PsychometricResponse.__new__(PsychometricResponse)
    r.id = UUID(m.id)
    r.user_id = UUID(m.user_id)
    r.question_key = m.question_key
    r.question_text = m.question_text
    r.dimension = m.dimension
    r.response_value = m.response_value
    r.response_raw = m.response_raw
    r.created_at = m.created_at
    return r


class PsychometricRepository(AbstractPsychometricRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_profile(self, user_id: UUID) -> PsychometricProfile | None:
        result = await self._db.execute(
            select(StudentProfileModel.psychometric_profile).where(
                StudentProfileModel.user_id == str(user_id)
            )
        )
        row = result.first()
        if row is None:
            return None
        return PsychometricProfile.from_dict(row[0])

    async def save_profile(self, user_id: UUID, profile: PsychometricProfile) -> None:
        result = await self._db.execute(
            select(StudentProfileModel).where(StudentProfileModel.user_id == str(user_id))
        )
        m = result.scalar_one_or_none()
        if m is None:
            return
        m.psychometric_profile = profile.to_dict()
        await self._db.flush()

    async def upsert_response(self, response: PsychometricResponse) -> PsychometricResponse:
        result = await self._db.execute(
            select(PsychometricResponseModel).where(
                PsychometricResponseModel.user_id == str(response.user_id),
                PsychometricResponseModel.question_key == response.question_key,
            )
        )
        m = result.scalar_one_or_none()
        if m is None:
            m = PsychometricResponseModel(
                id=str(response.id),
                user_id=str(response.user_id),
                question_key=response.question_key,
                question_text=response.question_text,
                dimension=response.dimension,
                response_value=response.response_value,
                response_raw=response.response_raw,
            )
            self._db.add(m)
        else:
            m.dimension = response.dimension
            m.response_value = response.response_value
            m.response_raw = response.response_raw
            m.question_text = response.question_text
        await self._db.flush()
        await self._db.refresh(m)
        return _to_response(m)

    async def list_responses(self, user_id: UUID) -> list[PsychometricResponse]:
        result = await self._db.execute(
            select(PsychometricResponseModel)
            .where(PsychometricResponseModel.user_id == str(user_id))
            .order_by(PsychometricResponseModel.created_at)
        )
        return [_to_response(m) for m in result.scalars().all()]

    async def answered_keys(self, user_id: UUID) -> set[str]:
        result = await self._db.execute(
            select(PsychometricResponseModel.question_key).where(
                PsychometricResponseModel.user_id == str(user_id)
            )
        )
        return {row[0] for row in result.all()}
