"""
Tests for the LMS layer — coursework lifecycle, submissions + grading, and
classroom invitations / join-approval flows. In-memory fakes, no database.
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.dtos.coursework import CreateCourseworkRequest, UpdateCourseworkRequest
from src.application.dtos.submission import GradeRequest
from src.application.services.coursework_service import CourseworkService
from src.application.services.submission_service import SubmissionService
from src.domain.entities.classroom import Classroom, Enrollment
from src.domain.entities.user import User
from src.domain.exceptions import (
    AuthorizationError,
    EntityNotFound,
    ValidationError,
)

# ── Fakes ────────────────────────────────────────────────────────────────────


class FakeClassroomRepo:
    def __init__(self):
        self.items = {}

    async def get_by_id(self, classroom_id):
        return self.items.get(classroom_id)


class FakeEnrollmentRepo:
    def __init__(self):
        self.enrollments: list[Enrollment] = []
        self.users: dict = {}

    async def is_enrolled(self, classroom_id, student_id):
        return any(
            e.classroom_id == classroom_id
            and e.student_id == student_id
            and e.status == "active"
            for e in self.enrollments
        )

    async def list_students(self, classroom_id, status="active"):
        return [
            self.users[e.student_id]
            for e in self.enrollments
            if e.classroom_id == classroom_id and e.status == status
        ]


class FakeTeacherRepo:
    def __init__(self):
        self.memberships = {}

    async def get(self, classroom_id, teacher_id):
        return self.memberships.get((classroom_id, teacher_id))


class FakeCourseworkRepo:
    def __init__(self):
        self.items = {}
        self.attachments = {}
        self.votes = {}

    async def create(self, coursework):
        self.items[coursework.id] = coursework
        return coursework

    async def get_by_id(self, coursework_id):
        return self.items.get(coursework_id)

    async def list_by_classroom(
        self, classroom_id, type=None, status=None, search=None,
        include_deleted=False, page=1, limit=50,
    ):
        out = [
            c for c in self.items.values()
            if c.classroom_id == classroom_id
            and (type is None or c.type == type)
            and (status is None or c.status == status)
            and (include_deleted or not c.is_deleted)
        ]
        return out, len(out)

    async def update(self, coursework, expected_version=None):
        if expected_version is not None:
            current = self.items[coursework.id]
            if current.version != expected_version:
                from src.domain.exceptions import ConcurrencyConflict

                raise ConcurrencyConflict("version mismatch")
        coursework.version += 1
        self.items[coursework.id] = coursework
        return coursework

    async def delete(self, coursework_id):
        self.items.pop(coursework_id, None)

    async def list_scheduled_due(self, now):
        return [
            c for c in self.items.values()
            if c.status == "scheduled" and c.scheduled_at and c.scheduled_at <= now
        ]

    async def add_attachment(self, attachment):
        self.attachments.setdefault(attachment.coursework_id, []).append(attachment)
        return attachment

    async def list_attachments(self, coursework_id):
        return self.attachments.get(coursework_id, [])

    async def delete_attachment(self, attachment_id):
        for atts in self.attachments.values():
            atts[:] = [a for a in atts if a.id != attachment_id]

    async def upsert_poll_vote(self, vote):
        self.votes[(vote.coursework_id, vote.user_id)] = vote
        return vote

    async def poll_results(self, coursework_id):
        results = {}
        for (cw_id, _), vote in self.votes.items():
            if cw_id == coursework_id:
                results[vote.option_index] = results.get(vote.option_index, 0) + 1
        return results

    async def get_poll_vote(self, coursework_id, user_id):
        return self.votes.get((coursework_id, user_id))


class FakeSubmissionRepo:
    def __init__(self):
        self.items = {}
        self.attachments = {}
        self.grades = {}

    async def create(self, submission):
        self.items[submission.id] = submission
        return submission

    async def get_by_id(self, submission_id):
        return self.items.get(submission_id)

    async def get_for_student(self, coursework_id, student_id):
        return next(
            (
                s for s in self.items.values()
                if s.coursework_id == coursework_id and s.student_id == student_id
            ),
            None,
        )

    async def list_by_coursework(self, coursework_id, status=None, page=1, limit=50):
        out = [
            s for s in self.items.values()
            if s.coursework_id == coursework_id and (status is None or s.status == status)
        ]
        return out, len(out)

    async def list_by_student(self, student_id, classroom_id=None, page=1, limit=50):
        out = [s for s in self.items.values() if s.student_id == student_id]
        return out, len(out)

    async def update(self, submission):
        self.items[submission.id] = submission
        return submission

    async def add_attachment(self, attachment):
        self.attachments.setdefault(attachment.submission_id, []).append(attachment)
        return attachment

    async def list_attachments(self, submission_id):
        return self.attachments.get(submission_id, [])

    async def clear_attachments(self, submission_id):
        return self.attachments.pop(submission_id, [])

    async def add_grade(self, grade):
        self.grades.setdefault(grade.submission_id, []).append(grade)
        return grade

    async def list_grades(self, submission_id):
        return list(reversed(self.grades.get(submission_id, [])))

    async def latest_grade(self, submission_id):
        grades = self.grades.get(submission_id, [])
        return grades[-1] if grades else None

    async def count_by_status(self, coursework_id):
        counts = {}
        for s in self.items.values():
            if s.coursework_id == coursework_id:
                counts[s.status] = counts.get(s.status, 0) + 1
        return counts

    async def average_score(self, coursework_id):
        return None


class FakeUserRepo:
    def __init__(self):
        self.users = {}

    async def get_by_id(self, user_id):
        return self.users.get(user_id)


class FakeStorage:
    def __init__(self):
        self.files = {}

    async def save(self, file_bytes, destination):
        self.files[destination] = file_bytes
        return destination

    async def read(self, storage_path):
        return self.files[storage_path]

    async def delete(self, storage_path):
        self.files.pop(storage_path, None)

    async def exists(self, storage_path):
        return storage_path in self.files


class FakeNotifier:
    def __init__(self):
        self.emitted = []

    async def emit(self, user_id, type, title, body="", data=None):
        self.emitted.append({"user_id": user_id, "type": type, "title": title})

    async def emit_many(self, user_ids, type, title, body="", data=None):
        for uid in user_ids:
            await self.emit(uid, type, title, body, data)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def world():
    teacher = User(email="t@x.com", username="teacher1", password_hash="h", role="teacher")
    student = User(email="s@x.com", username="student1", password_hash="h")
    classroom = Classroom(teacher_id=teacher.id, name="Physics 10")

    classroom_repo = FakeClassroomRepo()
    classroom_repo.items[classroom.id] = classroom
    enrollment_repo = FakeEnrollmentRepo()
    enrollment_repo.users[student.id] = student
    enrollment_repo.enrollments.append(
        Enrollment(classroom_id=classroom.id, student_id=student.id)
    )
    user_repo = FakeUserRepo()
    user_repo.users[teacher.id] = teacher
    user_repo.users[student.id] = student

    return {
        "teacher": teacher,
        "student": student,
        "classroom": classroom,
        "classrooms": classroom_repo,
        "enrollments": enrollment_repo,
        "teachers": FakeTeacherRepo(),
        "coursework": FakeCourseworkRepo(),
        "submissions": FakeSubmissionRepo(),
        "users": user_repo,
        "storage": FakeStorage(),
        "notifier": FakeNotifier(),
    }


@pytest.fixture
def coursework_svc(world):
    return CourseworkService(
        coursework_repo=world["coursework"],
        classroom_repo=world["classrooms"],
        enrollment_repo=world["enrollments"],
        teacher_repo=world["teachers"],
        submission_repo=world["submissions"],
        notification_svc=world["notifier"],
    )


@pytest.fixture
def submission_svc(world):
    return SubmissionService(
        submission_repo=world["submissions"],
        coursework_repo=world["coursework"],
        classroom_repo=world["classrooms"],
        enrollment_repo=world["enrollments"],
        teacher_repo=world["teachers"],
        user_repo=world["users"],
        storage=world["storage"],
        notification_svc=world["notifier"],
    )


def _assignment(publish=True, due_in_hours=24, allow_late=True, max_marks=100.0):
    return CreateCourseworkRequest(
        type="assignment",
        title="Newton's Laws worksheet",
        body="Answer all questions",
        due_at=datetime.now(UTC) + timedelta(hours=due_in_hours),
        allow_late=allow_late,
        max_marks=max_marks,
        publish=publish,
    )


# ── Coursework lifecycle ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_draft_not_visible_to_students(coursework_svc, world):
    result = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=False)
    )
    assert result.status == "draft"
    listed = await coursework_svc.list_for_student(world["student"].id, world["classroom"].id)
    assert listed.total == 0


@pytest.mark.asyncio
async def test_publish_notifies_enrolled_students(coursework_svc, world):
    result = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    assert result.status == "published"
    assert any(
        n["type"] == "new_assignment" and n["user_id"] == world["student"].id
        for n in world["notifier"].emitted
    )


@pytest.mark.asyncio
async def test_scheduled_coursework_auto_publishes_when_due(coursework_svc, world):
    dto = _assignment(publish=False)
    dto.scheduled_at = datetime.now(UTC) - timedelta(minutes=1)
    created = await coursework_svc.create(world["teacher"].id, world["classroom"].id, dto)
    assert created.status == "scheduled"
    listed = await coursework_svc.list_for_student(world["student"].id, world["classroom"].id)
    assert listed.total == 1
    assert listed.items[0].status == "published"


@pytest.mark.asyncio
async def test_optimistic_locking_conflict(coursework_svc, world):
    from src.domain.exceptions import ConcurrencyConflict

    created = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=False)
    )
    await coursework_svc.update(
        world["teacher"].id, uuid_of(created.id), UpdateCourseworkRequest(title="v2")
    )
    with pytest.raises(ConcurrencyConflict):
        await coursework_svc.update(
            world["teacher"].id,
            uuid_of(created.id),
            UpdateCourseworkRequest(title="stale", expected_version=created.version),
        )


@pytest.mark.asyncio
async def test_duplicate_creates_fresh_draft(coursework_svc, world):
    created = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    copy = await coursework_svc.duplicate(world["teacher"].id, uuid_of(created.id))
    assert copy.status == "draft"
    assert copy.title.endswith("(copy)")
    assert copy.id != created.id


@pytest.mark.asyncio
async def test_non_teacher_cannot_create(coursework_svc, world):
    with pytest.raises(AuthorizationError):
        await coursework_svc.create(
            world["student"].id, world["classroom"].id, _assignment()
        )


@pytest.mark.asyncio
async def test_poll_vote_and_results(coursework_svc, world):
    dto = CreateCourseworkRequest(
        type="poll", title="Field trip?", poll_options=["Yes", "No"], publish=True
    )
    poll = await coursework_svc.create(world["teacher"].id, world["classroom"].id, dto)
    results = await coursework_svc.vote(world["student"].id, uuid_of(poll.id), 0)
    assert results == {0: 1}
    with pytest.raises(ValidationError):
        await coursework_svc.vote(world["student"].id, uuid_of(poll.id), 5)


@pytest.mark.asyncio
async def test_poll_requires_options(coursework_svc, world):
    with pytest.raises(ValidationError):
        await coursework_svc.create(
            world["teacher"].id,
            world["classroom"].id,
            CreateCourseworkRequest(type="poll", title="Empty poll", publish=True),
        )


# ── Submissions & grading ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_and_teacher_notified(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    result = await submission_svc.submit(
        world["student"].id, uuid_of(cw.id), "My answer", [("hw.pdf", b"pdf-bytes", "application/pdf")]
    )
    assert result.status == "submitted"
    assert not result.is_late
    assert len(result.attachments) == 1
    assert any(n["type"] == "submission_received" for n in world["notifier"].emitted)


@pytest.mark.asyncio
async def test_late_submission_flagged(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id,
        _assignment(publish=True, due_in_hours=-1, allow_late=True),
    )
    result = await submission_svc.submit(world["student"].id, uuid_of(cw.id), "late work", [])
    assert result.is_late


@pytest.mark.asyncio
async def test_submission_blocked_when_late_disallowed(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id,
        _assignment(publish=True, due_in_hours=-1, allow_late=False),
    )
    with pytest.raises(ValidationError):
        await submission_svc.submit(world["student"].id, uuid_of(cw.id), "too late", [])


@pytest.mark.asyncio
async def test_resubmit_bumps_attempt_and_replaces_files(
    coursework_svc, submission_svc, world
):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    await submission_svc.submit(
        world["student"].id, uuid_of(cw.id), "v1", [("a.txt", b"1", "text/plain")]
    )
    result = await submission_svc.resubmit(
        world["student"].id, uuid_of(cw.id), "v2", [("b.txt", b"2", "text/plain")]
    )
    assert result.attempt == 2
    assert [a.filename for a in result.attachments] == ["b.txt"]


@pytest.mark.asyncio
async def test_withdraw_before_deadline(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    await submission_svc.submit(world["student"].id, uuid_of(cw.id), "answer", [])
    await submission_svc.withdraw(world["student"].id, uuid_of(cw.id))
    mine = await submission_svc.my_submission(world["student"].id, uuid_of(cw.id))
    assert mine.status == "withdrawn"


@pytest.mark.asyncio
async def test_grade_returns_and_notifies_student(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True, max_marks=50)
    )
    submitted = await submission_svc.submit(world["student"].id, uuid_of(cw.id), "answer", [])
    graded = await submission_svc.grade(
        world["teacher"].id,
        uuid_of(submitted.id),
        GradeRequest(score=42, comment="Good", private_feedback="Watch units"),
    )
    assert graded.status == "returned"
    assert graded.grade.score == 42
    assert graded.grade.private_feedback == "Watch units"
    assert any(
        n["type"] == "work_graded" and n["user_id"] == world["student"].id
        for n in world["notifier"].emitted
    )


@pytest.mark.asyncio
async def test_regrade_keeps_history(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    submitted = await submission_svc.submit(world["student"].id, uuid_of(cw.id), "answer", [])
    await submission_svc.grade(
        world["teacher"].id, uuid_of(submitted.id), GradeRequest(score=60)
    )
    regraded = await submission_svc.grade(
        world["teacher"].id, uuid_of(submitted.id), GradeRequest(score=75)
    )
    assert regraded.grade.score == 75
    assert regraded.grade.is_regrade
    assert len(regraded.grade_history) == 2


@pytest.mark.asyncio
async def test_score_cannot_exceed_max_marks(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True, max_marks=10)
    )
    submitted = await submission_svc.submit(world["student"].id, uuid_of(cw.id), "answer", [])
    with pytest.raises(ValidationError):
        await submission_svc.grade(
            world["teacher"].id, uuid_of(submitted.id), GradeRequest(score=11)
        )


@pytest.mark.asyncio
async def test_unenrolled_student_cannot_submit(coursework_svc, submission_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    outsider = uuid4()
    with pytest.raises(AuthorizationError):
        await submission_svc.submit(outsider, uuid_of(cw.id), "sneaky", [])


@pytest.mark.asyncio
async def test_announcement_rejects_submissions(coursework_svc, submission_svc, world):
    ann = await coursework_svc.create(
        world["teacher"].id,
        world["classroom"].id,
        CreateCourseworkRequest(type="announcement", title="Hello class", publish=True),
    )
    with pytest.raises(ValidationError):
        await submission_svc.submit(world["student"].id, uuid_of(ann.id), "hi", [])


@pytest.mark.asyncio
async def test_deleted_coursework_hidden(coursework_svc, world):
    cw = await coursework_svc.create(
        world["teacher"].id, world["classroom"].id, _assignment(publish=True)
    )
    await coursework_svc.delete(world["teacher"].id, uuid_of(cw.id))
    with pytest.raises(EntityNotFound):
        await coursework_svc.get_for_user(world["teacher"].id, uuid_of(cw.id), as_teacher=True)


def uuid_of(value: str):
    from uuid import UUID

    return UUID(value)
