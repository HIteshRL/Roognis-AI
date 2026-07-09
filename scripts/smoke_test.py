"""
Golden-path smoke test — exercises the core MVP flow end-to-end against a
running stack (does NOT import the app; hits real HTTP).

Run the stack first, then:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --base-url http://localhost:8000 --skip-chat

Prints a PASS/FAIL line per step and exits non-zero on the first hard failure,
so it is safe to wire into CI or a deploy gate.

Covers: health → student register/login/me → AI tutor (SSE) → learning
pipeline (sessions/mastery) → teacher school+classroom → student join +
published syllabus → parent link + child overview → FAQ tier.

Requires: httpx (already a backend dependency).
"""
import argparse
import json
import sys
import time

import httpx

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
_failures = 0
_password = "Smoke1234!"


def _envelope(resp: httpx.Response) -> dict:
    """Unwrap the {success, data, ...} envelope; raise on non-2xx."""
    if resp.status_code >= 400:
        raise AssertionError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    return body.get("data", body) if isinstance(body, dict) else body


def step(name: str, fn):
    global _failures
    try:
        result = fn()
        print(f"[{PASS}] {name}")
        return result
    except Exception as exc:  # noqa: BLE001 — smoke test wants every failure surfaced
        print(f"[{FAIL}] {name}\n        → {exc}")
        _failures += 1
        raise SystemExit(1) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Roognis golden-path smoke test")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--skip-chat", action="store_true",
                        help="skip the LLM chat step (use when no GROQ key)")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    api = f"{base}/api/v1"
    stamp = int(time.time())
    client = httpx.Client(timeout=30.0)

    def register(role: str, tag: str) -> tuple[str, str]:
        data = _envelope(client.post(f"{api}/auth/register", json={
            "email": f"smoke_{tag}_{stamp}@demo.roognis.ai",
            "username": f"smoke_{tag}_{stamp}",
            "password": _password,
            "role": role,
        }))
        return data["token"], data["user"]["id"]

    def auth(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    print(f"→ Target: {base}\n")

    step("health endpoint responds",
         lambda: client.get(f"{api}/health").raise_for_status())

    student_token, student_id = step(
        "student registers (role=student)", lambda: register("student", "stu"))

    step("student can log in", lambda: _envelope(client.post(f"{api}/auth/login", json={
        "email": f"smoke_stu_{stamp}@demo.roognis.ai", "password": _password})))

    me = step("GET /auth/me returns student role",
              lambda: _envelope(client.get(f"{api}/auth/me", headers=auth(student_token))))
    assert me.get("role") == "student", f"expected role student, got {me.get('role')}"

    # ── AI Tutor (SSE) + learning pipeline ────────────────────────────────────
    if not args.skip_chat:
        def chat():
            seen = set()
            with client.stream("POST", f"{api}/chat", headers=auth(student_token),
                               json={"message": "What is a fraction?", "subject": "Mathematics",
                                     "chapter": "Fractions"}) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line.startswith("data:"):
                        try:
                            evt = json.loads(line[5:].strip())
                        except ValueError:
                            continue
                        if isinstance(evt, dict) and evt.get("type"):
                            seen.add(evt["type"])
                        if "done" in seen:
                            break
            assert "chunk" in seen, f"no chunk events (saw {seen})"
            assert "done" in seen, f"no done event (saw {seen})"
            return seen

        step("AI tutor streams a response (meta/chunk/done)", chat)

        def pipeline():
            for _ in range(15):  # ≤30s — pipeline runs as a background task
                sessions = _envelope(client.get(f"{api}/student/sessions", headers=auth(student_token)))
                rows = sessions if isinstance(sessions, list) else sessions.get("items", sessions)
                if rows:
                    return rows
                time.sleep(2)
            raise AssertionError("no learning session recorded within 30s")

        step("learning pipeline recorded a session", pipeline)
        step("student mastery endpoint responds",
             lambda: _envelope(client.get(f"{api}/student/mastery", headers=auth(student_token))))
    else:
        print("[SKIP] AI tutor + pipeline (--skip-chat)")

    # ── Teacher: school → classroom → published syllabus ──────────────────────
    teacher_token, _ = step("teacher registers (role=teacher)",
                            lambda: register("teacher", "tch"))

    school = step("teacher creates a school", lambda: _envelope(client.post(
        f"{api}/school/schools", headers=auth(teacher_token), json={"name": f"Smoke School {stamp}"})))

    classroom = step("teacher creates a classroom", lambda: _envelope(client.post(
        f"{api}/school/classrooms", headers=auth(teacher_token),
        json={"school_id": school["id"], "name": "Smoke Math", "subject": "Mathematics", "grade": "8"})))
    join_code = classroom["join_code"]
    classroom_id = classroom["id"]
    assert join_code, "classroom has no join code"

    step("teacher publishes a syllabus item", lambda: _envelope(client.post(
        f"{api}/school/classrooms/{classroom_id}/syllabus", headers=auth(teacher_token),
        json={"subject": "Mathematics", "chapter": "Fractions", "is_published": True})))

    # ── Student joins + sees published syllabus ───────────────────────────────
    step("student joins class by code", lambda: _envelope(client.post(
        f"{api}/school/classrooms/join", headers=auth(student_token), json={"join_code": join_code})))

    def sees_syllabus():
        items = _envelope(client.get(f"{api}/school/classrooms/{classroom_id}/syllabus",
                                    headers=auth(student_token)))
        rows = items if isinstance(items, list) else items.get("items", [])
        assert any(i.get("chapter") == "Fractions" for i in rows), "published item not visible to student"
        return rows

    step("student sees the published syllabus item", sees_syllabus)

    # ── Parent link + read-only child overview ────────────────────────────────
    link = step("student issues a parent link code", lambda: _envelope(
        client.post(f"{api}/parent/link-code", headers=auth(student_token))))
    code = link["code"]

    parent_token, _ = step("parent registers (role=parent)", lambda: register("parent", "par"))

    step("parent links to the child", lambda: _envelope(client.post(
        f"{api}/parent/link", headers=auth(parent_token), json={"code": code})))

    children = step("parent sees their child", lambda: _envelope(
        client.get(f"{api}/parent/children", headers=auth(parent_token))))
    rows = children if isinstance(children, list) else children.get("items", [])
    assert rows, "parent has no linked children"

    step("parent reads child overview", lambda: _envelope(client.get(
        f"{api}/parent/children/{student_id}/overview", headers=auth(parent_token))))

    # ── Cache/FAQ tier alive ──────────────────────────────────────────────────
    step("FAQ endpoint responds",
         lambda: _envelope(client.get(f"{api}/faq", headers=auth(student_token))))

    client.close()
    print("\n\033[92mAll smoke steps passed.\033[0m" if _failures == 0 else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
