import { state, navigate, registerRoute } from '../state.js';
import { esc, shade } from '../utils.js';
import { getClassrooms } from '../api.js';
import { createModal } from '../modals/create-class.js';

export async function home() {
  state.rooms = await getClassrooms();
  state.room = null;

  const cards = state.rooms.map(r => `
    <div class="cc" data-r="${r.id}">
      <div class="ban" style="background:linear-gradient(135deg,${r.color},${shade(r.color, -30)})">
        <h3>${esc(r.name)}</h3>
        <div class="s">${esc(r.teacher || '')}${r.seed ? ' · demo' : ''}</div>
        <div class="mono" style="background:${shade(r.color, -40)};color:#fff">${r.icon || '📘'}</div>
      </div>
      <div class="body">
        <span>📚 ${r.chapters.length} chapters</span>
        <span class="spacer" style="font-family:ui-monospace;letter-spacing:.1em">${r.join_code}</span>
      </div>
    </div>`).join('');

  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="row">
      <div><h1>Classes</h1><div class="sub">Create classes, add chapters, upload PDFs and review what students ask.</div></div>
      <button class="btn" id="new">＋ Create class</button>
    </div>
    ${state.rooms.length
      ? `<div class="grid">${cards}</div>`
      : `<div class="empty" style="margin-top:24px">No classes yet.</div>`}`;

  document.getElementById('new').onclick = createModal;
  app.querySelectorAll('.cc').forEach(el => {
    el.onclick = () => navigate('classroom', el.dataset.r);
  });
}

registerRoute('home', home);
