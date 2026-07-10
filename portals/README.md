# Roognis — Portal UIs

Self-contained frontend packages for the Roognis student-portal product.
Each folder is a single HTML file — no build step, no npm, no bundler.

| Folder | Branch | URL | What it is |
|---|---|---|---|
| `student-portal-ui/` | `portal/student-ui` | `GET /` | Student SPA — subject grid → chapter chat |
| `teacher-portal-ui/` | `portal/teacher-ui` | `GET /teacher` | Teacher LMS — classrooms, PDF upload, student activity |

Both are served by the FastAPI backend in `../student-portal/app.py`
via `StaticFiles`. They call the same `/api/*` routes.

## Running locally

```bash
cd ../student-portal
pip install -r requirements.txt
uvicorn app:app --port 5050

# Student: http://localhost:5050/
# Teacher: http://localhost:5050/teacher
```
