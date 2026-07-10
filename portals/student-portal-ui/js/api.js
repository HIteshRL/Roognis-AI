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

/** GET /api/curriculum — full subject → chapter tree. */
export async function getCurriculum() {
  const r = await fetch(BASE + '/api/curriculum');
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
