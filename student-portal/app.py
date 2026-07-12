"""Roognis MVP — no-auth FastAPI app: student portal + teacher LMS, one server."""
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import anyio

import bridge
import engine
import image_gen
import ingest
import insights
import question_engine
import store

app = FastAPI(title="Roognis MVP", docs_url="/api/docs")
_STATIC = Path(__file__).resolve().parent / "static"

# Serve the modular student portal (portals/student-portal-ui) — the build that
# carries the inline check-question UX. Its index.html links css/* and js/*.
_PORTAL = Path(__file__).resolve().parent.parent / "portals" / "student-portal-ui"
app.mount("/css", StaticFiles(directory=_PORTAL / "css"), name="portal-css")
app.mount("/js", StaticFiles(directory=_PORTAL / "js"), name="portal-js")
app.mount("/fonts", StaticFiles(directory=_PORTAL / "fonts"), name="portal-fonts")

_SUBJECT_ICONS = {s["name"]: s["icon"] for s in __import__("curriculum").SUBJECTS}


@app.middleware("http")
async def _no_store_portal(request, call_next):
    """Portal HTML/CSS/JS must never be served stale — the demo is edited live and a
    cached bundle would hide fixes. API responses keep default caching."""
    resp = await call_next(request)
    p = request.url.path
    if p in ("/", "/teacher") or p.startswith("/css") or p.startswith("/js") or p.startswith("/static"):
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
    return resp


# ── Shared / student read models ──────────────────────────────────────────────
def _classrooms_payload(student_id: str | None = None) -> list[dict]:
    """All classes (teacher view), or only the classes a student is enrolled in
    (Google-Classroom roster model) when student_id is given."""
    out = []
    for room in store.list_classrooms():
        if student_id and store.enrollment_status(room["id"], student_id) != "approved":
            continue
        out.append({
            "id": room["id"], "name": room["name"], "icon": room["icon"] or "📘",
            "color": room["color"] or "#4f46e5", "open": bool(room["is_open"]),
            "seed": bool(room["is_seed"]), "teacher": room["teacher_name"],
            "join_code": room["join_code"], "students": room["student_count"],
            "chapters": [
                {"id": ch["id"], "title": ch["title"], "summary": ch["summary"] or "",
                 "doc_count": ch["doc_count"]}
                for ch in store.list_chapters(room["id"])
            ],
        })
    return out


@app.get("/api/curriculum")
async def curriculum_api(student_id: str | None = None):
    return {"grade": "10", "board": "ICSE", "mode": engine.MODE, "online": engine.ONLINE,
            "subjects": _classrooms_payload(student_id)}


# ── Student ───────────────────────────────────────────────────────────────────
class InitIn(BaseModel):
    name: str = Field(default="Student", max_length=60)


@app.post("/api/student/init")
async def student_init(body: InitIn):
    return store.get_or_create_student(body.name)


class ChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    subject_id: str            # classroom id
    chapter_id: str
    student_id: str
    conversation_id: str | None = None


@app.post("/api/chat")
async def chat_api(body: ChatIn):
    if store.enrollment_status(body.subject_id, body.student_id) != "approved":
        return {"decision": "pending", "message": "You're not approved for this class yet — "
                "ask your teacher to accept your request.", "sources": [], "trail": {},
                "mode": engine.MODE, "conversation_id": None}
    return await engine.ask(body.question, body.subject_id, body.chapter_id,
                            body.student_id, body.conversation_id)


# ── Image Studio (right slide-out) ────────────────────────────────────────────
class ImageIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)


@app.post("/api/image/generate")
async def image_generate(body: ImageIn):
    """Text-to-image for the studio panel. Fail-open: always returns 200 with an
    {ok, data_url|error} body so the UI can render the result or the reason."""
    return await anyio.to_thread.run_sync(image_gen.generate, body.prompt.strip())


# ── Learner Intelligence: inline questioning ──────────────────────────────────
class QNextIn(BaseModel):
    student_id: str
    subject_id: str            # classroom id
    chapter_id: str
    last_question: str | None = None   # lets us target the concept the student engaged with


@app.post("/api/question/next")
async def question_next(body: QNextIn):
    """Return one targeted check-question for the concept just discussed (or None).

    Never random — the objective is to reduce uncertainty about THIS learner on
    THIS concept. Reuses an outstanding question instead of stacking new ones.
    """
    if store.enrollment_status(body.subject_id, body.student_id) != "approved":
        return {"question": None}

    pending = store.next_pending_question(body.student_id)
    if pending:
        return {"question": _question_payload(pending)}

    chapter = store.get_chapter(body.chapter_id)
    if not chapter:
        return {"question": None}
    # The chapter is the concept scope for this demo; the summary supplies the
    # keywords the answer is graded against.
    concept = chapter["title"]

    q = question_engine.generate(
        concept=concept,
        objective="verify_confidence",
        # The demo doesn't model per-concept mastery, so use a neutral score to
        # keep the check at "Understand" level ("Explain in your own words …")
        # rather than down-ranking to a terse "State …" recall prompt.
        mastery_score=50.0,
        expected_answer=chapter.get("summary") or concept,
    )
    q.update(student_id=body.student_id, classroom_id=body.subject_id, chapter_id=body.chapter_id)
    saved = store.create_question(q)
    return {"question": _question_payload(saved)}


class QAnswerIn(BaseModel):
    student_id: str
    question_id: str
    answer: str = Field(min_length=1, max_length=5000)


@app.post("/api/question/answer")
async def question_answer(body: QAnswerIn, background: BackgroundTasks):
    q = store.get_question(body.question_id)
    if not q or q["student_id"] != body.student_id:
        raise HTTPException(404, "Question not found")
    if q["status"] == "evaluated":
        raise HTTPException(409, "Question already answered")

    ev = question_engine.evaluate(
        expected_answer=q["expected_answer"], concept=q["concept"],
        confidence_threshold=q["confidence_threshold"], answer=body.answer,
    )
    store.record_answer(body.question_id, body.answer, ev["is_correct"], ev["score"], ev["feedback"])
    store.add_evidence({
        "student_id": body.student_id, "concept": q["concept"], "signal": ev["signal"],
        "objective": q["objective"], "source": "question", "weight": q["evidence_weight"],
        "bloom_level": q["bloom_level"], "question_id": body.question_id,
        "detail": ev["feedback"],
    })
    confidence = question_engine.concept_confidence(
        store.concept_evidence(body.student_id, q["concept"])
    )

    # Phase 2 bridge: forward this evidence to apps/api's real engine (no-op unless
    # configured). Runs after the response so it never adds latency to the student.
    background.add_task(bridge.forward_evidence, {
        "external_ref": body.student_id, "concept_name": q["concept"], "signal": ev["signal"],
        "objective": q["objective"], "source": "question", "weight": q["evidence_weight"],
        "bloom_level": q["bloom_level"], "intent": "problem_solving", "detail": ev["feedback"],
    })

    return {
        "question_id": body.question_id, "concept": q["concept"],
        "evaluation": ev, "confidence_after": confidence,
    }


def _question_payload(q: dict) -> dict:
    return {
        "id": q["id"], "concept": q["concept"], "question": q["question"],
        "purpose": q["purpose"], "objective": q["objective"], "difficulty": q["difficulty"],
        "bloom_level": q["bloom_level"], "confidence_threshold": q["confidence_threshold"],
    }


class JoinIn(BaseModel):
    student_id: str
    join_code: str = Field(min_length=4, max_length=12)


@app.post("/api/student/join")
async def student_join(body: JoinIn):
    rooms = [r for r in store.list_classrooms() if r["join_code"] == body.join_code.strip().upper()]
    if not rooms:
        raise HTTPException(404, "No class found for that code")
    room = rooms[0]
    # Google-Classroom behaviour: a valid class code puts the student straight in.
    store.enroll(room["id"], body.student_id, "approved")
    return {"classroom_id": room["id"], "name": room["name"], "status": "approved"}


@app.get("/api/student/{student_id}/history")
async def student_history(student_id: str):
    return store.list_conversations_for_student(student_id)


@app.get("/api/student/{student_id}/insights")
async def student_insights(student_id: str):
    """Learner-intelligence dashboard payload — mastery, gaps, skills,
    recommendations, timeline, analytics. Derived fresh from the evidence log."""
    return insights.student_insights(student_id)


@app.get("/api/conversation/{conversation_id}/messages")
async def conversation_messages(conversation_id: str):
    return store.list_messages(conversation_id)


# ── Teacher (no auth; teacher_name identifies ownership) ──────────────────────
@app.get("/api/teacher/classrooms")
async def teacher_classrooms():
    return _classrooms_payload()


class ClassroomIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    subject: str | None = None
    section: str | None = None
    grade: str | None = "10"
    color: str | None = None
    icon: str | None = None
    teacher: str = "Teacher"


@app.post("/api/teacher/classrooms")
async def create_classroom(body: ClassroomIn):
    room = store.create_classroom(body.name, body.subject or body.name, body.section,
                                  body.grade, body.color, body.icon, body.teacher)
    engine.rebuild_corpus()
    return room


class ChapterIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str | None = None


@app.get("/api/teacher/classrooms/{cid}/chapters")
async def teacher_chapters(cid: str):
    return store.list_chapters(cid)


@app.post("/api/teacher/classrooms/{cid}/chapters")
async def add_chapter(cid: str, body: ChapterIn):
    return store.create_chapter(cid, body.title, body.summary)


async def _process_upload(document_id, chapter_id, classroom_id, data, filename):
    await ingest.ingest_pdf(document_id, chapter_id, classroom_id, data, filename)
    engine.rebuild_corpus()


@app.post("/api/teacher/chapters/{chid}/documents", status_code=201)
async def upload_document(chid: str, background: BackgroundTasks, file: UploadFile = File(...)):
    chapter = store.get_chapter(chid)
    if not chapter:
        raise HTTPException(404, "Chapter not found")
    name = file.filename or "upload.pdf"
    if not name.lower().endswith(".pdf") and (file.content_type or "") != "application/pdf":
        raise HTTPException(400, "Only .pdf files are accepted.")
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 25 MB).")
    doc_id = store.create_document(chid, chapter["classroom_id"], name)
    background.add_task(_process_upload, doc_id, chid, chapter["classroom_id"], data, name)
    return {"document_id": doc_id, "status": "processing", "filename": name}


@app.get("/api/teacher/chapters/{chid}/documents")
async def chapter_documents(chid: str):
    return store.list_documents(chid)


@app.get("/api/teacher/classrooms/{cid}/students")
async def classroom_students(cid: str):
    return store.list_enrollments(cid)


class AddStudentIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)


@app.post("/api/teacher/classrooms/{cid}/students", status_code=201)
async def add_student(cid: str, body: AddStudentIn):
    """Teacher adds a student to the roster by name (Google-Classroom 'invite')."""
    if not store.get_classroom(cid):
        raise HTTPException(404, "Class not found")
    student = store.get_or_create_student(body.name)
    store.enroll(cid, student["id"], "approved")
    return {"student_id": student["id"], "student_name": student["name"], "status": "approved"}


@app.delete("/api/teacher/classrooms/{cid}")
async def delete_classroom(cid: str):
    if not store.get_classroom(cid):
        raise HTTPException(404, "Class not found")
    store.delete_classroom(cid)
    engine.rebuild_corpus()
    return {"ok": True}


@app.post("/api/teacher/classrooms/{cid}/students/{sid}/{action}")
async def student_action(cid: str, sid: str, action: str):
    if action not in ("approve", "deny", "remove"):
        raise HTTPException(400, "Invalid action")
    store.set_enrollment(cid, sid, {"approve": "approved", "deny": "denied",
                                    "remove": "denied"}[action])
    return {"ok": True, "status": action}


@app.get("/api/teacher/classrooms/{cid}/conversations")
async def classroom_conversations(cid: str):
    return store.list_conversations_for_classroom(cid)


# ── Static SPAs ───────────────────────────────────────────────────────────────
@app.get("/")
async def student_spa():
    return FileResponse(_PORTAL / "index.html")


@app.get("/teacher")
async def teacher_spa():
    return FileResponse(_STATIC / "teacher.html")
