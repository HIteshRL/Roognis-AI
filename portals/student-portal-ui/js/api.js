const BASE = '';   // same origin; set to 'http://localhost:8000' for dev cross-origin

async function post(path, body) {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}

/** POST /api/student/init — register or look up the student session. */
export async function initStudent(name) {
  return post('/api/student/init', { name });
}

/** GET /api/curriculum — the classes this student is enrolled in (roster model).
 *  Without studentId it returns every class (teacher view). */
export async function getCurriculum(studentId) {
  const r = await fetch(BASE + '/api/curriculum' + (studentId ? `?student_id=${studentId}` : ''));
  return r.json();
}

/** POST /api/student/join — join a class with its code (straight in, GC-style). */
export async function joinClass(studentId, code) {
  const r = await fetch(BASE + '/api/student/join', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ student_id: studentId, join_code: code }),
  });
  if (!r.ok) throw new Error((await r.json()).detail || 'No class found for that code');
  return r.json();
}

/**
 * POST /api/chat — send a student question and receive the guardrail decision + answer.
 * @param {{ question, subject_id, chapter_id, student_id, conversation_id }} payload
 */
export async function sendChat(payload) {
  return post('/api/chat', payload);
}

/**
 * POST /api/question/next — fetch one inline check-question for the concept just
 * discussed. Returns { question: {...} | null }.
 * @param {{ student_id, subject_id, chapter_id, last_question }} payload
 */
export async function nextQuestion(payload) {
  return post('/api/question/next', payload);
}

/**
 * POST /api/question/answer — submit the student's answer to a check-question.
 * Returns { evaluation: {...}, confidence_after }.
 * @param {{ student_id, question_id, answer }} payload
 */
export async function answerQuestion(payload) {
  return post('/api/question/answer', payload);
}

/**
 * GET /api/student/{id}/insights — learner-intelligence dashboard payload
 * (mastery, gaps, skills, recommendations, timeline, analytics).
 */
export async function getInsights(studentId) {
  const r = await fetch(`${BASE}/api/student/${studentId}/insights`);
  return r.json();
}

/**
 * POST /api/image/generate — text-to-image for the Image Studio.
 * Always resolves to { ok: true, data_url } or { ok: false, error }.
 * @param {string} prompt
 */
export async function generateImage(prompt) {
  return post('/api/image/generate', { prompt });
}
