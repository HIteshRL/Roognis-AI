import { state, navigate, registerRoute } from '../state.js';
import { esc, shade } from '../utils.js';
import { paneChapters } from './chapters.js';
import { paneStudents } from './students.js';
import { paneInsights } from './insights.js';

export function openRoom(id) {
  state.room = state.rooms.find(r => r.id === id);
  state.tab  = 'chapters';
  renderRoom();
}

export function renderRoom() {
  const r = state.room;
  const app = document.getElementById('app');

  app.innerHTML = `
    <button class="back" id="backBtn">‹ Classes</button>
    <div class="band" style="background:linear-gradient(135deg,${r.color},${shade(r.color, -30)})">
      <div class="mono">${r.icon || '📘'}</div>
      <div><h2>${esc(r.name)}</h2><div class="s">${esc(r.teacher || '')}</div></div>
      <div class="code"><div class="l">Class code</div><div class="v">${r.join_code}</div></div>
    </div>
    <div class="tabs">
      <button class="tab" data-t="chapters">Chapters</button>
      <button class="tab" data-t="students">Students</button>
      <button class="tab" data-t="insights">Student activity</button>
    </div>
    <div class="pane" id="pane"></div>`;

  document.getElementById('backBtn').onclick = () => navigate('home');

  app.querySelectorAll('.tab').forEach(t => {
    t.onclick = () => { state.tab = t.dataset.t; renderRoom(); };
  });
  app.querySelector(`.tab[data-t="${state.tab}"]`).classList.add('on');

  const panes = { chapters: paneChapters, students: paneStudents, insights: paneInsights };
  panes[state.tab]();
}

registerRoute('classroom', id => {
  state.room = state.rooms.find(r => r.id === id);
  state.tab  = 'chapters';
  renderRoom();
});
