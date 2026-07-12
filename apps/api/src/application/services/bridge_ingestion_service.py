"""
BridgeIngestionService — folds evidence from an external surface into the real engine.

This is the application-layer home for the demo→engine bridge. It maps an external
learner reference (e.g. the standalone demo's student id) to a namespaced bridge
user, resolves the concept by name, and drives the ConfidenceUpdater so mastery,
gaps, recall, and the evidence log all advance exactly as they would for a
first-party interaction.

Extracted from the route handler so the presentation layer stays thin (transport +
auth only) and this orchestration is unit-testable and reusable — per the project
rule that routes receive fully-assembled services and hold no business logic.
"""
from src.application.services.confidence_updater import ConfidenceUpdater
from src.domain.entities.question import LearnerEvidence
from src.domain.entities.user import User
from src.domain.repositories.learning_repository import AbstractConceptNodeRepository
from src.domain.repositories.user_repository import AbstractUserRepository

# Bridge users live in their own email namespace and carry an unusable password
# hash — the value can never equal a real bcrypt hash, so the account cannot be
# authenticated with; it exists only to key per-learner state.
_BRIDGE_EMAIL = "bridge+{ref}@bridge.local"
_UNUSABLE_PASSWORD = "!bridge-no-login"


class BridgeIngestionService:
    def __init__(
        self,
        user_repo: AbstractUserRepository,
        concept_repo: AbstractConceptNodeRepository,
        confidence_updater: ConfidenceUpdater,
    ) -> None:
        self._users = user_repo
        self._concepts = concept_repo
        self._confidence = confidence_updater

    async def ingest(
        self,
        external_ref: str,
        concept_name: str,
        signal: str,
        objective: str = "verify_confidence",
        source: str = "question",
        weight: float = 1.0,
        bloom_level: str = "Understand",
        intent: str = "unknown",
        detail: str = "",
    ) -> LearnerEvidence:
        user = await self._bridge_user(external_ref)
        node = await self._concepts.get_or_create(concept_name, None, None, None)
        return await self._confidence.apply_signal(
            user_id=user.id,
            concept_id=node.id,
            concept_name=node.name,
            signal=signal,
            objective=objective,
            source=source,
            weight=weight,
            bloom_level=bloom_level,
            intent=intent,
            detail=detail,
        )

    async def _bridge_user(self, external_ref: str) -> User:
        email = _BRIDGE_EMAIL.format(ref=external_ref)
        user = await self._users.get_by_email(email)
        if user is None:
            user = await self._users.create(
                User(
                    email=email,
                    username=f"bridge_{external_ref}"[:50],
                    password_hash=_UNUSABLE_PASSWORD,
                    role="student",
                )
            )
        return user
