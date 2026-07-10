"""Roognis MVP — no-auth FastAPI app: student portal + teacher LMS, one server."""
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import engine
import ingest
import store

app = FastAPI(title="Roognis MVP", docs_url="/api/docs")
_STATIC = Path(__file__).resolve().parent / "static"

_SUBJECT_ICONS = {s["name"]: s["icon"] for s in __import__("curriculum").SUBJECTS}


# ── Shared / student read models ──────────────────────────────────────────────
def _classrooms_payload() -> list[dict]:
    out = []
    for room in store.list_classrooms():
        out.append({
            "id": room["id"], "name": room["name"], "icon": room["icon"] or "📘",
            "color": room["color"] or "#4f46e5", "open": bool(room["is_open"]),
            "seed": bool(room["is_seed"]), "teacher": room["teacher_name"],
            "join_code": room["join_code"],
            "chapters": [
                {"id": ch["id"], "title": ch["title"], "summary": ch["summary"] or "",
                 "doc_count": ch["doc_count"]}
                for ch in store.list_chapters(room["id"])
            ],
        })
    return out


@app.get("/api/curriculum")
async def curriculum_api():
    return {"grade": "10", "board": "ICSE", "mode": engine.MODE, "online": engine.ONLINE,
            "subjects": _classrooms_payload()}


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


class JoinIn(BaseModel):
    student_id: str
    join_code: str = Field(min_length=4, max_length=12)


@app.post("/api/student/join")
async def student_join(body: JoinIn):
    rooms = [r for r in store.list_classrooms() if r["join_code"] == body.join_code.strip().upper()]
    if not rooms:
        raise HTTPException(404, "No class found for that code")
    room = rooms[0]
    status = ("approved" if room["is_open"]
              else store.request_enrollment(room["id"], body.student_id))
    return {"classroom_id": room["id"], "name": room["name"], "status": status}


@app.get("/api/student/{student_id}/history")
async def student_history(student_id: str):
    return store.list_conversations_for_student(student_id)


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
    return FileResponse(_STATIC / "index.html")


@app.get("/teacher")
async def teacher_spa():
    return FileResponse(_STATIC / "teacher.html")
