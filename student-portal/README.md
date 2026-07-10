# Roognis MVP — Student portal + Teacher LMS

A single **no-auth** FastAPI app: a student portal **and** a Google-Classroom-style teacher LMS,
both backed by SQLite, with per-chapter tutoring wired to the **guarded, agentic RAG** in
[`../rag-standalone`](../rag-standalone).

- **Student** → `http://localhost:5050/`
- **Teacher** → `http://localhost:5050/teacher`

## What works (verified end-to-end)

**Teacher LMS**
- Create & manage **classrooms** (GC-style, join codes) and **chapters**.
- **Upload `.pdf`** → stored on disk (compartmentalised by classroom/chapter) → parsed → chunked →
  written to the chapter's corpus in the DB. Status workflow: `processing → ready | failed`.
- **Approve / deny** students (join requests) — unapproved students can't chat.
- **Student activity** — review every student's conversation (question + AI answer + guardrail decision).

**Student portal**
- Browse subjects → chapters → chat. Answers are grounded **only** in that chapter's material
  (seed content **and** the teacher's uploaded PDFs).
- Real guardrail flow: `answered · off_topic · not_in_chapter · blocked_unsafe · pending`.

**The loop:** teacher uploads a PDF → a student (once approved) asks about it → grounded answer →
teacher reviews the conversation.

## Run

```bash
cd student-portal
pip install -r requirements.txt
uvicorn app:app --port 5050
```

Runs **offline** (extractive answers) with no key or external services. Set `GROQ_API_KEY` in `.env`
to make answers + the concept-grounding judge live Groq calls.

## Layout

```
app.py         FastAPI routes (student + teacher + upload)
db.py          SQLite schema + seed         store.py   data access
ingest.py      PDF parse → chunk → persist  engine.py  RAG wiring + conversation logging
providers.py   Db retrieval + corpus guardrail + offline LLM (rag-standalone adapters)
curriculum.py  ghost ICSE seed content
static/        index.html (student)  ·  teacher.html (teacher LMS)
data/          roognis.db + uploads/<classroom>/<chapter>/*.pdf   (git-ignored)
```

## Status

- **Done + verified:** the teacher LMS, PDF pipeline, DB, allow/deny, conversation review, and the
  student chat wired to DB-backed (uploaded) content.
- **Next (student UI overhaul):** heavier Google-Classroom flair, a Claude-style swipe-up composer
  (image-generation panel), swipe-right video panel, automatic context refresh on heavy context, and
  a left slide-out chat-history rail with subject/chapter logos. Image-gen and video inference need
  generative-model backends (not in this environment) — they'll ship as wired UI panels + stub endpoints.
