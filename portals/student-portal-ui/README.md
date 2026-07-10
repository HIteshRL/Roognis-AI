# Roognis — Student Portal UI

**Type:** Vanilla HTML/CSS/JS SPA (zero build step, zero dependencies)  
**Serves at:** `GET /` on the FastAPI backend  
**Branch:** `portal/student-ui`

## What it is

The student-facing single-page app for Roognis AI. Students browse subjects,
pick a chapter, and chat with the AI tutor — which answers only from that
chapter's material, with child-safety and subject-adherence guardrails enforced.

## Screens

```
Home (subject grid)
  └── Subject view (chapter list with summary)
        └── Chapter chat (grounded AI tutor)
```

## Features

- **8 ICSE Class 10 subjects** displayed as coloured cards with subject icons
- **Per-chapter AI tutor** — grounded only in that chapter's seed content
  and any PDFs the teacher has uploaded
- **Guardrail decision rendering** — four visual states:
  - ✓ `answered` — typewriter animation + "Grounded in chapter" badge
  - ↪️ `off_topic` — amber notice (question is outside the subject)
  - 📕 `not_in_chapter` — blue notice (right subject, wrong chapter)
  - 🛡️ `blocked_unsafe` — red notice (safety guardrail triggered)
  - ⏳ `pending` — amber notice (student awaiting teacher approval)
- **Quick-start chips** — suggested questions derived from the chapter summary
- **Live / offline badge** — header shows `Live · Groq` or `Demo · offline answers`
  depending on whether `GROQ_API_KEY` is set on the server

## API contract

All calls go to the same origin (`/api/*`). Run the backend on port 5050.

### Boot sequence

```
POST /api/student/init
  Body:  { "name": "<student name from localStorage>" }
  Returns: { "id": "<student_id>" }

GET /api/curriculum
  Returns: {
    "online": true|false,
    "subjects": [
      {
        "id": "physics",
        "name": "Physics",
        "color": "#4f46e5",
        "icon": "⚡",
        "chapters": [
          { "id": "physics-ch1", "title": "Electricity", "summary": "…" },
          …
        ]
      }, …
    ]
  }
```

### Chat

```
POST /api/chat
  Body: {
    "question": "<student message>",
    "subject_id": "<subject id>",
    "chapter_id": "<chapter id>",
    "student_id": "<student id from init>",
    "conversation_id": "<uuid | null — null to start new>"
  }
  Returns: {
    "decision": "answered" | "off_topic" | "not_in_chapter" | "blocked_unsafe" | "pending",
    "answer": "<string | null>",
    "message": "<guardrail message when not answered>",
    "sources": [{ "title": "…" }],
    "conversation_id": "<uuid>"
  }
```

## Local state

| Key | Storage | Value |
|---|---|---|
| `roognis_student` | `localStorage` | Student display name |

The `student_id` and `conversation_id` are held in the page-level `state`
object and reset on page reload.

## How to run

```bash
cd student-portal        # backend root
pip install -r requirements.txt
uvicorn app:app --port 5050
# Open http://localhost:5050
```

The backend serves this file at `GET /` via FastAPI `StaticFiles`.

## Customisation

- **Accent colour** — dynamically set per-subject via `setAccent(color)`.
  Subject colors come from the API response.
- **Student name** — read from `localStorage.roognis_student` on boot.
  Change the default by editing the `|| 'Aarav'` fallback in `boot()`.
- **Typewriter speed** — controlled by `step` and interval (`16ms`) in `typewriter()`.
- **Chip count** — at most 3 quick-start chips, derived from the chapter summary.
