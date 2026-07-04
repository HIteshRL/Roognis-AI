# Roognis AI — Demo & Hosting Runbook (5-kid classroom)

A self-contained guide to host the MVP on a server and run a live demo for a
classroom of 5 students. The demo leads with **tangible features** (log in →
AI tutor → quiz → classes → progress → teacher/parent view); the learning-
intelligence and personalization layers run quietly in the background and are
**not required** for the demo to succeed.

---

## 1. What the demo shows

| Persona | Login | What they see |
|---------|-------|----------------|
| Teacher | `teacher@demo.roognis.ai` | Their school → "Grade 8 Mathematics" class → **roster of 5 students + analytics** (per-student mastery, weak concepts, sessions) → publish syllabus |
| Parent | `parent@demo.roognis.ai` | Read-only progress for their child (Aarav) — mastery, strengths, weak areas, recent activity |
| Students | `kid1@…` … `kid5@…` | Dashboard → **AI Tutor** (ask a question, get an answer + illustration) → **Quiz** → My Classes (join code `DEMO24`, published syllabus) → Progress screens |

All demo passwords: **`Demo1234!`**

The 5 students are pre-seeded across the mastery range so the teacher dashboard
looks real out of the box:

| Student | Login | Level |
|---------|-------|-------|
| Aarav | `kid1@demo.roognis.ai` | Mastered (~87%) |
| Diya | `kid2@demo.roognis.ai` | Proficient (~70%) |
| Kabir | `kid3@demo.roognis.ai` | Developing (~47%) |
| Meera | `kid4@demo.roognis.ai` | Struggling (~23%) |
| Rohan | `kid5@demo.roognis.ai` | Just joined (no data yet) |

---

## 2. Prerequisites

- A server with Docker + Docker Compose.
- A **Groq API key** (required — powers the AI tutor). Set `GROQ_API_KEY`.
- Optional: a **Fal API key** for real generated illustrations. Without it, set
  `IMAGE_GEN_PROVIDER=stub` (answers still work; images are placeholders).
- No GPU needed — video generation runs in `stub` mode for the demo.

---

## 3. Configure (`.env`)

Copy `.env.example` to `.env` and set the demo-lean values:

```dotenv
# Seed the 5-kid classroom on boot
SEED_DEMO=1

# AI tutor (required)
GROQ_API_KEY=<your-groq-key>

# Illustrations: real (needs key) or stub
IMAGE_GEN_PROVIDER=fal          # or: stub
FAL_API_KEY=<your-fal-key>      # omit if using stub

# Keep the heavy layers off the critical path for a lean demo
VIDEO_GEN_PROVIDER=stub         # no GPU
RETRIEVAL_ENABLED=false         # no curriculum uploaded → tutor answers generally,
                                # no Qdrant/embeddings dependency on the chat path

# Secrets / infra (compose fills DB/Redis/Qdrant URLs automatically)
API_SECRET_KEY=<32+ char random string>
```

> **Why `RETRIEVAL_ENABLED=false`?** For a 5-kid demo with no curriculum
> documents loaded, RAG has nothing to retrieve. Turning it off makes the tutor
> answer general questions directly (faster, fewer moving parts). If you *do*
> want curriculum-grounded answers, upload documents via the admin/RAG flow and
> set `RETRIEVAL_ENABLED=true` instead.

---

## 4. Launch

```bash
docker compose up -d --build
```

On boot the API container runs `alembic upgrade head` (migrations 001–013) and
`python scripts/seed.py` (prompt templates + the demo classroom, idempotent).

- Web app: `http://<server>:3000` (or port 80 via the bundled nginx)
- API: `http://<server>:8000` — health at `/api/v1/health`, docs at `/docs`

Re-running `docker compose up` is safe: the demo seed skips itself if the demo
classroom already exists.

---

## 5. Verify before the demo

Run the golden-path smoke test against the running stack:

```bash
python scripts/smoke_test.py --base-url http://<server>:8000
# no Groq key handy? add --skip-chat to skip only the LLM step
```

Every step should print `PASS`. It exercises: health, register/login, AI tutor
(SSE), the learning pipeline, teacher school/classroom/join-code, syllabus
visibility, parent link + child overview, and the FAQ cache tier.

---

## 6. Suggested demo script (~10 min)

1. **Kid (Rohan, `kid5`)** — the "new student": log in → open **AI Tutor** →
   pick Mathematics / Fractions → ask *"How do I add 1/2 and 1/4?"* → watch the
   answer stream in with an illustration → take a **quiz** → check **My Classes**
   (already enrolled, published syllabus visible).
2. **Kid (Aarav, `kid1`)** — the "advanced student": show a populated
   **Progress / Mastery** dashboard and **Weak Areas**.
3. **Teacher** — log in → open **Grade 8 Mathematics** → **Class Analytics**:
   5-student roster, mastery distribution across all buckets, common weak
   concepts, per-student table.
4. **Parent** — log in → see Aarav's read-only progress card.

New teachers/parents/students can also self-register and pick their role at
signup, and any student can share a **family access code** from *Family Access*
to link a parent live.

---

## 7. What's intentionally in the back seat

- **Personalization** (teaching-history-conditioned prompts) is applied
  invisibly and fail-open — the tutor works with or without it.
- **The learning pipeline** (concept extraction, mastery/gap updates) runs as a
  background task after each answer; it never blocks a response, and the
  dashboards are pre-seeded so they look complete regardless.
- **RAG / curriculum grounding** is optional and off by default for this demo.

These can all be turned up later without touching the tangible demo flow.
