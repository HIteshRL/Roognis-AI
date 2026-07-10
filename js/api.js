const BASE = '';  // same origin; override for cross-origin dev

async function api(url, opts) {
  const r = await fetch(BASE + url, opts);
  if (r.ok) return r.json();
  return r.json().then(e => Promise.reject(e));
}

// ── Classrooms ───────────────────────────────────────────────────────────────

export const getClassrooms = () =>
  api('/api/teacher/classrooms');

export const createClassroom = body =>
  api('/api/teacher/classrooms', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

// ── Chapters ─────────────────────────────────────────────────────────────────

export const getChapters = roomId =>
  api(`/api/teacher/classrooms/${roomId}/chapters`);

export const createChapter = (roomId, body) =>
  api(`/api/teacher/classrooms/${roomId}/chapters`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

// ── Documents ────────────────────────────────────────────────────────────────

export const getDocs = chapterId =>
  api(`/api/teacher/chapters/${chapterId}/documents`);

export const uploadDoc = (chapterId, formData) =>
  api(`/api/teacher/chapters/${chapterId}/documents`, { method: 'POST', body: formData });

// ── Students ─────────────────────────────────────────────────────────────────

export const getStudents = roomId =>
  api(`/api/teacher/classrooms/${roomId}/students`);

export const updateEnrolment = (roomId, studentId, action) =>
  api(`/api/teacher/classrooms/${roomId}/students/${studentId}/${action}`, { method: 'POST' });

// ── Insights ─────────────────────────────────────────────────────────────────

export const getConversations = roomId =>
  api(`/api/teacher/classrooms/${roomId}/conversations`);

export const getMessages = conversationId =>
  api(`/api/conversation/${conversationId}/messages`);
