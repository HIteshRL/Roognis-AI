# Roognis — Teacher Portal UI (LMS)

**Type:** Vanilla HTML/CSS/JS SPA (zero build step, zero dependencies)  
**Serves at:** `GET /teacher` on the FastAPI backend  
**Branch:** `portal/teacher-ui`

## What it is

The teacher-facing LMS for Roognis AI. Teachers manage classrooms, upload
PDFs that go into the chapter's AI-answerable corpus, approve or deny student
join requests, and review every conversation students have had with the AI
tutor.

Design language: **Google Classroom flair** — coloured banner cards with
monogram avatars, class join codes, tab-based class detail view.

## Screens

```
Classes grid (GC-style coloured cards with join code)
  └── Class detail
        ├── Chapters tab    — chapter list + Upload PDF button per chapter
        ├── Students tab    — approve / deny join requests
        └── Student activity tab — expandable per-student conversations
```

## Features

- **Create class** — modal with name, subject, section, emoji icon, and
  8-colour theme picker
- **Add chapter** — modal with title + summary
- **PDF upload** — per-chapter file picker; status polls every 1.5 s until
  `processing → ready | failed`; shows page count + chunk count on success
- **Approve / Deny students** — badge-driven UI; unapproved students can't
  chat with the AI
- **Student activity** — expandable conversation view showing raw Q+A messages
  and the guardrail decision tag per AI turn
- **Join code** displayed in header and in the class banner (monospace)

## API contract

All calls go to the same origin (`/api/*`). Run the backend on port 5050.

### Classrooms

```
GET  /api/teacher/classrooms
     Returns: [{ id, name, color, icon, join_code, seed, teacher, chapters[] }]

POST /api/teacher/classrooms
     Body: { name, subject, section, icon, color, teacher }
     Returns: { id, name, join_code, … }
```

### Chapters

```
GET  /api/teacher/classrooms/:classroom_id/chapters
     Returns: [{ id, title, summary, classroom_id }]

POST /api/teacher/classrooms/:classroom_id/chapters
     Body: { title, summary }
     Returns: chapter
```

### Documents (PDF upload)

```
POST /api/teacher/chapters/:chapter_id/documents
     Body: multipart/form-data  { file: <pdf> }
     Returns: { id, filename, status: "processing" }

GET  /api/teacher/chapters/:chapter_id/documents
     Returns: [{
       id, filename, status: "processing"|"ready"|"failed",
       pages, chunk_count, error
     }]
```

UI polls this endpoint every 1.5 s until no document is in `processing` state.

### Students (enrollment)

```
GET  /api/teacher/classrooms/:classroom_id/students
     Returns: [{ student_id, student_name, status: "pending"|"approved"|"denied" }]

POST /api/teacher/classrooms/:classroom_id/students/:student_id/approve
POST /api/teacher/classrooms/:classroom_id/students/:student_id/deny
     Returns: { ok: true }
```

### Conversations (student activity)

```
GET  /api/teacher/classrooms/:classroom_id/conversations
     Returns: [{
       id, title, student_name, chapter_title, msg_count, created_at
     }]

GET  /api/conversation/:conversation_id/messages
     Returns: [{
       id, role: "user"|"assistant", content, decision, created_at
     }]
```

## Local state

| Key | Storage | Value |
|---|---|---|
| `roognis_teacher` | `localStorage` | Teacher display name (default "Ms. Rao") |

## How to run

```bash
cd student-portal        # backend root
pip install -r requirements.txt
uvicorn app:app --port 5050
# Open http://localhost:5050/teacher
```

## Customisation

- **Colour palette** — `COLORS` array at the top of the script (8 colours, cycled per class)
- **Teacher name** — read from `localStorage.roognis_teacher`; change the `|| 'Ms. Rao'` fallback
- **Poll interval** — `pollDocs()` uses 1500 ms; adjust to taste
- **Conversation display** — messages rendered inline via `api('/api/conversation/:id/messages')`;
  expandable per row with click toggle
