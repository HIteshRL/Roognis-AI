"""
Curriculum seed for the demo RAG path.

Opt-in (SEED_CURRICULUM=1): ingests a few Grade-8 Mathematics chapters through
the REAL ingestion pipeline (parse → adaptive chunk → embed → Qdrant), so that
with RETRIEVAL_ENABLED=true the tutor gives curriculum-grounded, cited answers
in the demo. Matches the demo classroom's subject (Mathematics, Grade 8).

Idempotent: skips if the demo knowledge base already exists.

Run:  SEED_CURRICULUM=1 python scripts/seed_curriculum.py
(docker-compose.prod runs it on boot, after seed.py.)
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "api"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.services.ingestion_pipeline import IngestionPipeline
from src.config import get_settings
from src.domain.entities.knowledge import Document, IngestionJob, KnowledgeBase
from src.infrastructure.database.models.knowledge import KnowledgeBaseModel
from src.infrastructure.database.repositories.knowledge_repository import (
    DocumentRepository,
    IngestionJobRepository,
    KnowledgeBaseRepository,
)
from src.infrastructure.database.repositories.school_repository import ClassroomRepository
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.embeddings.factory import get_embedding_provider
from src.infrastructure.vector.factory import get_vector_store

KB_NAME = "Demo — Grade 8 Mathematics"

# (chapter, topic, body). Kept short but real so retrieval has something to cite.
CHAPTERS: list[tuple[str, str, str]] = [
    (
        "Fractions",
        "Adding and Subtracting Fractions",
        """Fractions

A fraction represents a part of a whole. It is written as a numerator over a
denominator, for example 1/2, where 1 is the numerator and 2 is the denominator.

Adding fractions with the same denominator:
Add the numerators and keep the denominator. For example, 1/4 + 2/4 = 3/4.

Adding fractions with different denominators:
First find a common denominator (a common multiple of both denominators), rewrite
each fraction, then add the numerators. To add 1/2 and 1/4, rewrite 1/2 as 2/4.
Then 2/4 + 1/4 = 3/4.

Subtracting fractions works the same way: make the denominators equal, then
subtract the numerators. For example, 3/4 - 1/4 = 2/4 = 1/2.

Always simplify the result to its lowest terms by dividing the numerator and
denominator by their greatest common factor.""",
    ),
    (
        "Proportions",
        "Ratios and Proportions",
        """Ratios and Proportions

A ratio compares two quantities, written as a:b or a/b. For example, if a class
has 12 boys and 8 girls, the ratio of boys to girls is 12:8, which simplifies to
3:2.

A proportion states that two ratios are equal, such as 3/2 = 12/8. To check
whether two ratios form a proportion, use cross-multiplication: the ratios a/b
and c/d are equal when a × d = b × c.

Solving a proportion: if 3/4 = x/20, cross-multiply to get 4x = 60, so x = 15.

Direct proportion: as one quantity increases, the other increases at the same
rate. If 2 pens cost 10 rupees, then 5 pens cost 25 rupees, because the cost per
pen stays constant.""",
    ),
    (
        "Percentages",
        "Percentage and Its Applications",
        """Percentages

A percentage is a fraction out of 100. The symbol % means "per hundred", so 45%
means 45 out of 100, or 45/100 = 0.45.

Converting a fraction to a percentage: multiply by 100. For example, 3/4 = 0.75 =
75%.

Finding a percentage of a number: multiply the number by the percentage written
as a decimal. To find 20% of 150, compute 0.20 × 150 = 30.

Percentage increase and decrease: a price of 200 rupees increased by 10% becomes
200 + (0.10 × 200) = 220 rupees. The same price decreased by 10% becomes 180
rupees.

Percentages are used in discounts, interest, marks, and statistics.""",
    ),
]


async def main() -> None:
    if os.getenv("SEED_CURRICULUM") != "1":
        print("SEED_CURRICULUM not set — skipping curriculum seed.")
        return

    settings = get_settings()
    engine = create_async_engine(str(settings.database_url), echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        existing = await db.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.name == KB_NAME)
        )
        if existing.scalar_one_or_none():
            print("Curriculum already seeded — skipping.")
            await engine.dispose()
            return

        owner = await UserRepository(db).get_by_email("teacher@demo.roognis.ai")
        if owner is None:
            print("Demo teacher not found — run seed.py (SEED_DEMO=1) first. Skipping.")
            await engine.dispose()
            return

        kb = await KnowledgeBaseRepository(db).create(
            KnowledgeBase(
                name=KB_NAME,
                created_by=owner.id,
                description="Grade 8 Mathematics chapters for the demo RAG path.",
                subject="Mathematics",
                grade="8",
            )
        )

        # Wire the KB to the demo classroom so enrolled students' tutor grounds
        # in it via the teacher content bridge (resolve_kb_for_student). Without
        # this the demo still works through global subject/chapter retrieval,
        # but linking it demonstrates the exact teacher→student path.
        classroom_repo = ClassroomRepository(db)
        teacher_classes = await classroom_repo.list_by_teacher(owner.id)
        demo_class = next(
            (c for c in teacher_classes if (c.subject or "").lower() == "mathematics"),
            teacher_classes[0] if teacher_classes else None,
        )
        if demo_class and not demo_class.knowledge_base_id:
            demo_class.knowledge_base_id = kb.id
            await classroom_repo.update(demo_class)
            print(f"Linked demo classroom '{demo_class.name}' to curriculum KB.")

        storage_dir = Path(settings.storage_local_path) / "curriculum"
        storage_dir.mkdir(parents=True, exist_ok=True)

        doc_repo = DocumentRepository(db)
        job_repo = IngestionJobRepository(db)
        docs: list[tuple[Document, str]] = []
        for chapter, topic, body in CHAPTERS:
            path = storage_dir / f"{chapter.lower()}.txt"
            path.write_text(body, encoding="utf-8")
            doc = await doc_repo.create(
                Document(
                    knowledge_base_id=kb.id,
                    uploaded_by=owner.id,
                    filename=f"{chapter}.txt",
                    file_type="text/plain",
                    file_size=len(body.encode("utf-8")),
                    title=f"Grade 8 Mathematics — {chapter}",
                    storage_path=str(path),
                    metadata={"subject": "Mathematics", "grade": "8", "chapter": chapter, "topic": topic},
                )
            )
            await job_repo.create(IngestionJob(document_id=doc.id))
            docs.append((doc, str(path)))
        await db.commit()

    # Run the real pipeline per document (it opens its own sessions).
    pipeline = IngestionPipeline(
        vector_store=get_vector_store(),
        embedding_provider=get_embedding_provider(),
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        chunk_strategy=settings.chunk_strategy,
        chunk_target_tokens=settings.chunk_target_tokens,
        chunk_min_tokens=settings.chunk_min_tokens,
        chunk_safety_ratio=settings.chunk_safety_ratio,
        chunk_semantic_threshold=settings.chunk_semantic_threshold,
        chunk_semantic_enabled=settings.chunk_semantic_enabled,
    )
    for doc, path in docs:
        try:
            await pipeline.run(doc.id, path, "text/plain")
            print(f"Ingested curriculum chapter: {doc.filename}")
        except Exception as exc:  # noqa: BLE001 — fail-open, keep booting
            print(f"Curriculum ingest failed for {doc.filename}: {exc}")

    await engine.dispose()
    print("Curriculum seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
