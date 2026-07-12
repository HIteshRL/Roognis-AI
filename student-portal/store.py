"""Thin data-access layer over db.py — all SQL lives here."""
from db import connect, gen_code, gen_id, now


def _rows(cur) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]


def _row(cur) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None


# ── Classrooms ────────────────────────────────────────────────────────────────
def list_classrooms(teacher_name: str | None = None) -> list[dict]:
    with connect() as c:
        if teacher_name:
            cur = c.execute("SELECT * FROM classrooms WHERE teacher_name=? ORDER BY created_at DESC",
                            (teacher_name,))
        else:
            cur = c.execute("SELECT * FROM classrooms ORDER BY is_seed DESC, created_at DESC")
        rooms = _rows(cur)
        for r in rooms:
            r["chapter_count"] = c.execute("SELECT COUNT(*) FROM chapters WHERE classroom_id=?",
                                           (r["id"],)).fetchone()[0]
            r["student_count"] = c.execute(
                "SELECT COUNT(*) FROM enrollments WHERE classroom_id=? AND status='approved'",
                (r["id"],)).fetchone()[0]
        return rooms


def get_classroom(cid: str) -> dict | None:
    with connect() as c:
        return _row(c.execute("SELECT * FROM classrooms WHERE id=?", (cid,)))


def create_classroom(name, subject, section, grade, color, icon, teacher_name) -> dict:
    cid = gen_id()
    with connect() as c:
        # is_open=0 → Google-Classroom roster model: a student is in the class only
        # if the teacher added them or they joined with the class code.
        c.execute(
            "INSERT INTO classrooms(id,name,subject,section,grade,color,icon,join_code,"
            "teacher_name,is_open,is_seed,created_at) VALUES(?,?,?,?,?,?,?,?,?,0,0,?)",
            (cid, name, subject, section, grade, color or "#16a34a", icon or "📘",
             gen_code(), teacher_name, now()),
        )
        c.commit()
    return get_classroom(cid)


def delete_classroom(cid: str) -> None:
    """Remove a class and everything under it (chapters, material, roster, chats)."""
    with connect() as c:
        for (ch,) in c.execute("SELECT id FROM chapters WHERE classroom_id=?", (cid,)).fetchall():
            c.execute("DELETE FROM chunks WHERE chapter_id=?", (ch,))
            c.execute("DELETE FROM documents WHERE chapter_id=?", (ch,))
        c.execute("DELETE FROM chapters WHERE classroom_id=?", (cid,))
        c.execute("DELETE FROM enrollments WHERE classroom_id=?", (cid,))
        for (cv,) in c.execute("SELECT id FROM conversations WHERE classroom_id=?", (cid,)).fetchall():
            c.execute("DELETE FROM messages WHERE conversation_id=?", (cv,))
        c.execute("DELETE FROM conversations WHERE classroom_id=?", (cid,))
        c.execute("DELETE FROM classrooms WHERE id=?", (cid,))
        c.commit()


# ── Chapters ──────────────────────────────────────────────────────────────────
def list_chapters(classroom_id: str) -> list[dict]:
    with connect() as c:
        cur = c.execute("SELECT * FROM chapters WHERE classroom_id=? ORDER BY order_index, created_at",
                        (classroom_id,))
        chs = _rows(cur)
        for ch in chs:
            ch["doc_count"] = c.execute(
                "SELECT COUNT(*) FROM documents WHERE chapter_id=? AND status='ready'",
                (ch["id"],)).fetchone()[0]
        return chs


def get_chapter(chid: str) -> dict | None:
    with connect() as c:
        return _row(c.execute("SELECT * FROM chapters WHERE id=?", (chid,)))


def create_chapter(classroom_id, title, summary) -> dict:
    chid = gen_id()
    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM chapters WHERE classroom_id=?",
                      (classroom_id,)).fetchone()[0]
        c.execute("INSERT INTO chapters(id,classroom_id,title,summary,order_index,created_at)"
                  " VALUES(?,?,?,?,?,?)", (chid, classroom_id, title, summary or "", n, now()))
        c.commit()
    return get_chapter(chid)


# ── Documents + chunks (the PDF pipeline persistence) ─────────────────────────
def create_document(chapter_id, classroom_id, filename) -> str:
    did = gen_id()
    with connect() as c:
        c.execute("INSERT INTO documents(id,chapter_id,classroom_id,filename,status,uploaded_at)"
                  " VALUES(?,?,?,?, 'processing', ?)", (did, chapter_id, classroom_id, filename, now()))
        c.commit()
    return did


def finalize_document(document_id, chapter_id, pages, chunk_texts) -> None:
    with connect() as c:
        for i, t in enumerate(chunk_texts):
            c.execute("INSERT INTO chunks(id,chapter_id,document_id,ordinal,content,source)"
                      " VALUES(?,?,?,?,?, 'upload')", (gen_id(), chapter_id, document_id, i, t))
        c.execute("UPDATE documents SET status='ready', pages=?, chunk_count=? WHERE id=?",
                  (pages, len(chunk_texts), document_id))
        c.commit()


def fail_document(document_id, error) -> None:
    with connect() as c:
        c.execute("UPDATE documents SET status='failed', error=? WHERE id=?", (error, document_id))
        c.commit()


def list_documents(chapter_id: str) -> list[dict]:
    with connect() as c:
        return _rows(c.execute("SELECT * FROM documents WHERE chapter_id=? ORDER BY uploaded_at DESC",
                               (chapter_id,)))


def get_chapter_chunks(chapter_id: str) -> list[str]:
    with connect() as c:
        return [r[0] for r in c.execute(
            "SELECT content FROM chunks WHERE chapter_id=? ORDER BY document_id IS NULL DESC, ordinal",
            (chapter_id,)).fetchall()]


# ── Students + enrollment (allow / deny) ──────────────────────────────────────
def get_or_create_student(name: str) -> dict:
    name = (name or "Student").strip()[:60] or "Student"
    with connect() as c:
        r = _row(c.execute("SELECT * FROM students WHERE name=?", (name,)))
        if r:
            return r
        sid = gen_id()
        c.execute("INSERT INTO students(id,name,created_at) VALUES(?,?,?)", (sid, name, now()))
        c.commit()
        return {"id": sid, "name": name}


def enrollment_status(classroom_id: str, student_id: str) -> str:
    with connect() as c:
        room = _row(c.execute("SELECT is_open FROM classrooms WHERE id=?", (classroom_id,)))
        if room and room["is_open"]:
            return "approved"  # open (seeded) classrooms need no approval
        r = _row(c.execute("SELECT status FROM enrollments WHERE classroom_id=? AND student_id=?",
                           (classroom_id, student_id)))
        return r["status"] if r else "none"


def enroll(classroom_id: str, student_id: str, status: str = "approved") -> None:
    """Upsert an enrollment at the given status — used when the teacher adds a
    student to the roster, and when a student joins with the class code
    (Google-Classroom behaviour: a valid code puts you straight in)."""
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO enrollments(id,classroom_id,student_id,status,requested_at)"
                  " VALUES(?,?,?,?,?)", (gen_id(), classroom_id, student_id, status, now()))
        c.execute("UPDATE enrollments SET status=? WHERE classroom_id=? AND student_id=?",
                  (status, classroom_id, student_id))
        c.commit()


def request_enrollment(classroom_id: str, student_id: str) -> str:
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO enrollments(id,classroom_id,student_id,status,requested_at)"
                  " VALUES(?,?,?, 'pending', ?)", (gen_id(), classroom_id, student_id, now()))
        c.commit()
    return enrollment_status(classroom_id, student_id)


def set_enrollment(classroom_id: str, student_id: str, status: str) -> None:
    with connect() as c:
        c.execute("UPDATE enrollments SET status=? WHERE classroom_id=? AND student_id=?",
                  (status, classroom_id, student_id))
        c.commit()


def list_enrollments(classroom_id: str) -> list[dict]:
    with connect() as c:
        return _rows(c.execute(
            "SELECT e.*, s.name AS student_name FROM enrollments e JOIN students s ON s.id=e.student_id"
            " WHERE e.classroom_id=? ORDER BY e.requested_at DESC", (classroom_id,)))


# ── Conversations + messages (teacher review) ─────────────────────────────────
def create_conversation(student_id, classroom_id, chapter_id, title) -> str:
    cvid = gen_id()
    with connect() as c:
        c.execute("INSERT INTO conversations(id,student_id,classroom_id,chapter_id,title,created_at,"
                  "updated_at) VALUES(?,?,?,?,?,?,?)",
                  (cvid, student_id, classroom_id, chapter_id, title, now(), now()))
        c.commit()
    return cvid


def add_message(conversation_id, role, content, decision=None) -> None:
    with connect() as c:
        c.execute("INSERT INTO messages(id,conversation_id,role,content,decision,created_at)"
                  " VALUES(?,?,?,?,?,?)", (gen_id(), conversation_id, role, content, decision, now()))
        c.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now(), conversation_id))
        c.commit()


def list_messages(conversation_id: str) -> list[dict]:
    with connect() as c:
        return _rows(c.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at",
                               (conversation_id,)))


def list_conversations_for_student(student_id: str) -> list[dict]:
    with connect() as c:
        return _rows(c.execute(
            "SELECT cv.*, cl.name AS classroom_name, cl.icon AS classroom_icon, cl.color AS color,"
            " ch.title AS chapter_title FROM conversations cv"
            " LEFT JOIN classrooms cl ON cl.id=cv.classroom_id"
            " LEFT JOIN chapters ch ON ch.id=cv.chapter_id"
            " WHERE cv.student_id=? ORDER BY cv.updated_at DESC", (student_id,)))


def list_conversations_for_classroom(classroom_id: str) -> list[dict]:
    with connect() as c:
        return _rows(c.execute(
            "SELECT cv.*, s.name AS student_name, ch.title AS chapter_title,"
            " (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=cv.id) AS msg_count"
            " FROM conversations cv LEFT JOIN students s ON s.id=cv.student_id"
            " LEFT JOIN chapters ch ON ch.id=cv.chapter_id"
            " WHERE cv.classroom_id=? ORDER BY cv.updated_at DESC", (classroom_id,)))


# ── Learner Intelligence: questions + evidence ────────────────────────────────
def create_question(q: dict) -> dict:
    """Persist a generated question (dict shaped like apps/api QuestionOutput)."""
    qid = gen_id()
    with connect() as c:
        c.execute(
            "INSERT INTO learner_questions(id,student_id,classroom_id,chapter_id,concept,"
            "question,objective,purpose,difficulty,bloom_level,expected_answer,"
            "confidence_threshold,evidence_weight,status,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?, 'asked', ?)",
            (qid, q["student_id"], q.get("classroom_id"), q.get("chapter_id"), q["concept"],
             q["question"], q.get("objective"), q.get("purpose"), q.get("difficulty"),
             q.get("bloom_level"), q.get("expected_answer"), q.get("confidence_threshold", 0.6),
             q.get("evidence_weight", 1.0), now()),
        )
        c.commit()
    return get_question(qid)


def get_question(qid: str) -> dict | None:
    with connect() as c:
        return _row(c.execute("SELECT * FROM learner_questions WHERE id=?", (qid,)))


def next_pending_question(student_id: str) -> dict | None:
    with connect() as c:
        return _row(c.execute(
            "SELECT * FROM learner_questions WHERE student_id=? AND status IN ('asked','pending')"
            " ORDER BY created_at LIMIT 1", (student_id,)))


def record_answer(qid: str, answer: str, is_correct: bool, score: float, feedback: str) -> dict | None:
    with connect() as c:
        c.execute(
            "UPDATE learner_questions SET status='evaluated', student_answer=?, is_correct=?,"
            " score=?, feedback=?, answered_at=? WHERE id=?",
            (answer, 1 if is_correct else 0, score, feedback, now(), qid),
        )
        c.commit()
    return get_question(qid)


def list_questions(student_id: str, limit: int = 20) -> list[dict]:
    with connect() as c:
        return _rows(c.execute(
            "SELECT * FROM learner_questions WHERE student_id=? ORDER BY created_at DESC LIMIT ?",
            (student_id, limit)))


def add_evidence(ev: dict) -> str:
    eid = gen_id()
    with connect() as c:
        c.execute(
            "INSERT INTO learner_evidence(id,student_id,concept,signal,objective,source,weight,"
            "bloom_level,intent,question_id,detail,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (eid, ev["student_id"], ev.get("concept"), ev["signal"], ev.get("objective"),
             ev.get("source", "question"), ev.get("weight", 1.0), ev.get("bloom_level"),
             ev.get("intent"), ev.get("question_id"), ev.get("detail", ""), now()),
        )
        c.commit()
    return eid


def list_evidence(student_id: str, limit: int = 100) -> list[dict]:
    with connect() as c:
        return _rows(c.execute(
            "SELECT * FROM learner_evidence WHERE student_id=? ORDER BY created_at DESC LIMIT ?",
            (student_id, limit)))


def concept_evidence(student_id: str, concept: str) -> list[dict]:
    with connect() as c:
        return _rows(c.execute(
            "SELECT * FROM learner_evidence WHERE student_id=? AND concept=? ORDER BY created_at DESC",
            (student_id, concept)))
