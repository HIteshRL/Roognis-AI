import { state, setAccent, navigate, registerRoute } from '../state.js?v=2';
import { shade } from '../utils.js?v=2';

export function renderHome() {
  setAccent('#16a34a');
  state.subject = null;
  state.chapter = null;

  const app = document.getElementById('app');

  // Roster model: nothing to show until the teacher adds you (or you join by code).
  if (!state.data.subjects.length) {
    app.innerHTML = `
      <div class="noclass">
        <div class="big">🎒</div>
        <b>No classes yet</b>
        <p>Ask your teacher for a class code — or if they've already added you,
           check that you entered the same name they used.</p>
        <button class="jbtn" id="homeJoin">➕ Join a class</button>
      </div>`;
    document.getElementById('homeJoin').onclick = () =>
      document.dispatchEvent(new CustomEvent('roognis:join'));
    return;
  }

  const rows = state.data.subjects.map(s => `
    <div class="subject" data-s="${s.id}">
      <div class="glow" style="background:${s.color}"></div>
      <div class="ic" style="background:linear-gradient(135deg, ${s.color}, ${shade(s.color, -26)})">${s.icon}</div>
      <div>
        <h3>${s.name}</h3>
        <div class="meta">${s.chapters.length} chapters</div>
      </div>
      <span class="go">›</span>
    </div>`).join('');

  app.innerHTML = `
    <div class="home-layout">
      <div class="rail">
        <div class="rail-head">My classes</div>
        ${rows}
      </div>
      <div class="welcome">
        <div class="kicker">Class 10 · ICSE</div>
        <h1>Hi! What will you<br>learn today?</h1>
        <p>Pick a subject from the rail, choose a chapter, and ask your AI tutor —
           it answers only from that chapter's material, and checks your understanding as you go.</p>
        <div class="facts">
          <span class="wfact">🌱 Learns from every answer</span>
          <span class="wfact">📖 Grounded in your chapters</span>
          <span class="wfact">✓ Safe &amp; on-subject</span>
        </div>
      </div>
    </div>`;

  app.querySelectorAll('.subject').forEach(el => {
    el.onclick = () => navigate('subject', el.dataset.s);
  });
}

registerRoute('home', renderHome);
