import { state } from '../state.js';
import { esc, toast } from '../utils.js';
import { getStudents, updateEnrolment } from '../api.js';

export async function paneStudents() {
  const pane = document.getElementById('pane');
  const r    = state.room;
  const en   = await getStudents(r.id);

  const rows = en.map(e => `
    <div class="person">
      <div class="av">${(e.student_name || '?')[0].toUpperCase()}</div>
      <div>
        <h4 style="margin:0">${esc(e.student_name)}</h4>
        <div class="m"><span class="badge ${e.status}">${e.status}</span></div>
      </div>
      <div class="spacer" style="display:flex;gap:6px">
        ${e.status !== 'approved' ? `<button class="btn green sm" data-a="approve" data-s="${e.student_id}">Approve</button>` : ''}
        ${e.status !== 'denied'   ? `<button class="btn red sm"   data-a="deny"    data-s="${e.student_id}">Deny</button>`    : ''}
      </div>
    </div>`).join('');

  pane.innerHTML = `
    <div class="sub" style="margin-bottom:12px">
      Share code <b style="font-family:ui-monospace">${r.join_code}</b> — students request to join, you approve.
    </div>
    ${en.length ? rows : `<div class="empty">No join requests yet.</div>`}`;

  pane.querySelectorAll('[data-a]').forEach(b => {
    b.onclick = async () => {
      await updateEnrolment(r.id, b.dataset.s, b.dataset.a);
      toast('Updated');
      paneStudents();
    };
  });
}
