import { state, setAccent, navigate, registerRoute } from '../state.js';
import { shade } from '../utils.js';

export function renderHome() {
  setAccent('#4f46e5');
  state.subject = null;
  state.chapter = null;

  const cards = state.data.subjects.map(s => `
    <div class="subject" data-s="${s.id}">
      <div class="glow" style="background:${s.color}"></div>
      <span class="go">›</span>
      <div class="ic" style="background:linear-gradient(135deg, ${s.color}, ${shade(s.color, -26)})">${s.icon}</div>
      <h3>${s.name}</h3>
      <div class="meta">${s.chapters.length} chapters</div>
    </div>`).join('');

  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="hero">
      <h1>Hi! What will you learn today?</h1>
      <p>Pick a subject, choose a chapter, and ask your AI tutor — it answers only from that chapter's material.</p>
    </div>
    <div class="grid">${cards}</div>`;

  app.querySelectorAll('.subject').forEach(el => {
    el.onclick = () => navigate('subject', el.dataset.s);
  });
}

registerRoute('home', renderHome);
