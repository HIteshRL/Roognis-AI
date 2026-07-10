import { state } from '../state.js';
import { esc } from '../utils.js';
import { getConversations, getMessages } from '../api.js';

export async function paneInsights() {
  const pane = document.getElementById('pane');
  const r    = state.room;
  const cs   = await getConversations(r.id);

  const cards = cs.map(c => `
    <div class="conv" data-c="${c.id}">
      <div class="row">
        <b>${esc(c.student_name || 'Student')}</b>
        <span class="m" style="color:var(--muted);font-size:12px">${esc(c.chapter_title || '')} · ${c.msg_count} msgs</span>
      </div>
      <div class="m" style="color:var(--muted);font-size:12.5px;margin-top:2px">${esc(c.title || '')}</div>
      <div class="msgs" id="m-${c.id}"></div>
    </div>`).join('');

  pane.innerHTML = `
    <div class="sub" style="margin-bottom:12px">Review what students are asking — every conversation is logged.</div>
    ${cs.length ? cards : `<div class="empty">No student activity yet.</div>`}`;

  pane.querySelectorAll('.conv').forEach(el => {
    el.onclick = async () => {
      const box = el.querySelector('.msgs');
      if (box.style.display === 'flex') { box.style.display = 'none'; return; }
      const ms = await getMessages(el.dataset.c);
      box.innerHTML = ms.map(m => `
        <div class="mb ${m.role === 'user' ? 'user' : 'ai'}">
          ${esc(m.content)}
          ${m.decision ? `<div class="dtag">${m.decision.replace('_', ' ')}</div>` : ''}
        </div>`).join('');
      box.style.display = 'flex';
    };
  });
}
