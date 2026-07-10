import { state, setAccent, navigate, registerRoute } from '../state.js';
import { shade } from '../utils.js';

export function renderSubject(sid) {
  const s = state.data.subjects.find(x => x.id === sid);
  state.subject = s;
  setAccent(s.color);

  const rows = s.chapters.map((c, i) => `
    <div class="chapter" data-c="${c.id}">
      <div class="num">${i + 1}</div>
      <div>
        <h4>${c.title}</h4>
        <div class="sm">${c.summary}</div>
      </div>
      <span class="learn">Learn →</span>
    </div>`).join('');

  const app = document.getElementById('app');
  app.innerHTML = `
    <button class="back">‹ All subjects</button>
    <div class="band" style="background:linear-gradient(135deg, ${s.color}, ${shade(s.color, -30)})">
      <div class="ic">${s.icon}</div>
      <div>
        <h2>${s.name}</h2>
        <div class="sub">Class 10 · ICSE · ${s.chapters.length} chapters</div>
      </div>
    </div>
    <div class="chapters">${rows}</div>`;

  app.querySelector('.back').onclick = () => navigate('home');
  app.querySelectorAll('.chapter').forEach(el => {
    el.onclick = () => navigate('chat', el.dataset.c);
  });
}

registerRoute('subject', renderSubject);
