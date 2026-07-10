"""
SQLite data layer for the Roognis MVP (teacher LMS + student portal).

One file, stdlib sqlite3, no extra deps. Compartmentalises everything the LMS
needs: classrooms -> chapters -> documents -> chunks, plus students, enrollments
(allow/deny), conversations and messages (for teacher review).
"""
import secrets
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "roognis.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS classrooms (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, subject TEXT, section TEXT, grade TEXT,
  color TEXT, icon TEXT, join_code TEXT UNIQUE, teacher_name TEXT,
  is_open INTEGER DEFAULT 0, is_seed INTEGER DEFAULT 0, created_at REAL
);
CREATE TABLE IF NOT EXISTS chapters (
  id TEXT PRIMARY KEY, classroom_id TEXT NOT NULL, title TEXT NOT NULL,
  summary TEXT, order_index INTEGER DEFAULT 0, created_at REAL,
  FOREIGN KEY(classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL, classroom_id TEXT NOT NULL,
  filename TEXT, status TEXT DEFAULT 'processing', pages INTEGER DEFAULT 0,
  chunk_count INTEGER DEFAULT 0, error TEXT, uploaded_at REAL,
  FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL, document_id TEXT,
  ordinal INTEGER, content TEXT NOT NULL, source TEXT DEFAULT 'seed',
  FOREIGN KEY(chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_chunks_chapter ON chunks(chapter_id);
CREATE TABLE IF NOT EXISTS students (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at REAL
);
CREATE TABLE IF NOT EXISTS enrollments (
  id TEXT PRIMARY KEY, classroom_id TEXT NOT NULL, student_id TEXT NOT NULL,
  status TEXT DEFAULT 'pending', requested_at REAL,
  UNIQUE(classroom_id, student_id)
);
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY, student_id TEXT, classroom_id TEXT, chapter_id TEXT,
  title TEXT, created_at REAL, updated_at REAL
);
CREATE INDEX IF NOT EXISTS ix_conv_student ON conversations(student_id);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, role TEXT, content TEXT,
  decision TEXT, created_at REAL,
  FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_msg_conv ON messages(conversation_id);
"""

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def gen_id() -> str:
    return secrets.token_hex(8)


def gen_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(6))


def now() -> float:
    return time.time()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def seed_from_curriculum(subjects: list[dict], sentence_fn) -> None:
    """Seed 8 demo classrooms (one per ICSE subject) with chapters + chunks.
    Idempotent — skips if a seed classroom already exists."""
    with connect() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM classrooms WHERE is_seed=1").fetchone()[0]
        if existing:
            return
        t = now()
        for s in subjects:
            conn.execute(
                "INSERT INTO classrooms(id,name,subject,section,grade,color,icon,join_code,"
                "teacher_name,is_open,is_seed,created_at) VALUES(?,?,?,?,?,?,?,?,?,1,1,?)",
                (s["id"], s["name"], s["name"], "Section A", "10", s["color"], s["icon"],
                 gen_code(), "Roognis Faculty", t),
            )
            for i, c in enumerate(s["chapters"]):
                conn.execute(
                    "INSERT INTO chapters(id,classroom_id,title,summary,order_index,created_at)"
                    " VALUES(?,?,?,?,?,?)",
                    (c["id"], s["id"], c["title"], c["summary"], i, t),
                )
                for j, sent in enumerate(sentence_fn(c["content"])):
                    conn.execute(
                        "INSERT INTO chunks(id,chapter_id,document_id,ordinal,content,source)"
                        " VALUES(?,?,?,?,?,'seed')",
                        (gen_id(), c["id"], None, j, sent),
                    )
        conn.commit()
