import { state, navigate } from './state.js?v=2';
import { initStudent, getCurriculum, joinClass } from './api.js?v=2';
import { initStudio } from './studio.js?v=2';

// Import all views so they self-register their routes via registerRoute().
import './views/home.js?v=2';
import './views/subject.js?v=2';
import './views/chat.js?v=2';
import './views/insights.js?v=1';

// ── Theme (light / dark) ─────────────────────────────────────────────────────
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const icon = theme === 'dark' ? '☀️' : '🌙';
  ['themeBtn', 'navTheme'].forEach(id => { const b = document.getElementById(id); if (b) b.textContent = icon; });
}
function toggleTheme() {
  const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  localStorage.setItem('roognis_theme', next);
  applyTheme(next);
}
function initTheme() {
  const saved = localStorage.getItem('roognis_theme');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved || (prefersDark ? 'dark' : 'light'));
  document.getElementById('themeBtn').onclick = toggleTheme;
  const nt = document.getElementById('navTheme');
  if (nt) nt.onclick = toggleTheme;
}

// ── First-visit name gate (roster model needs to know who you are) ──────────
function askName() {
  return new Promise(resolve => {
    const app = document.getElementById('app');
    app.innerHTML = `
      <div class="gate">
        <div class="glogo"></div>
        <h2>Welcome to Roognis</h2>
        <p>Enter your name — if your teacher added you to a class, it'll be waiting.</p>
        <input id="gateName" maxlength="60" placeholder="Your name" autocomplete="off" />
        <button id="gateGo">Start learning</button>
      </div>`;
    const inp = document.getElementById('gateName');
    const go = () => {
      const name = inp.value.trim();
      if (!name) { inp.focus(); return; }
      resolve(name);
    };
    document.getElementById('gateGo').onclick = go;
    inp.onkeydown = e => { if (e.key === 'Enter') go(); };
    inp.focus();
  });
}

// ── Drawers (left nav menu + right image studio) share one scrim ─────────────
function initDrawers() {
  const nav = document.getElementById('navDrawer');
  const img = document.getElementById('imgDrawer');
  const scrim = document.getElementById('scrim');

  const closeAll = () => {
    [nav, img].forEach(d => { d.classList.remove('open'); d.setAttribute('aria-hidden', 'true'); });
    scrim.classList.remove('open');
  };
  const open = (d) => {
    closeAll();
    d.classList.add('open');
    d.setAttribute('aria-hidden', 'false');
    scrim.classList.add('open');
  };

  document.getElementById('navBtn').onclick = () => open(nav);
  document.getElementById('studioBtn').onclick = () => open(img);
  document.getElementById('navClose').onclick = closeAll;
  document.getElementById('drawerClose').onclick = closeAll;
  scrim.onclick = closeAll;
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeAll(); });

  document.getElementById('navHome').onclick = () => { navigate('home'); closeAll(); };
  document.getElementById('navInsights').onclick = () => { navigate('insights'); closeAll(); };
  document.getElementById('insightsBtn').onclick = () => { navigate('insights'); closeAll(); };
  return { closeAll };
}

// ── Join class (code entry) ──────────────────────────────────────────────────
function initJoin(closeAll, refresh) {
  const back = document.getElementById('joinModal');
  const inp = document.getElementById('joinCode');
  const err = document.getElementById('joinErr');
  const go = document.getElementById('joinGo');

  const open = () => { closeAll(); err.hidden = true; inp.value = ''; back.hidden = false; inp.focus(); };
  const close = () => { back.hidden = true; };

  document.getElementById('navJoin').onclick = open;
  document.addEventListener('roognis:join', open);
  document.getElementById('joinCancel').onclick = close;
  back.onclick = e => { if (e.target === back) close(); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  const submit = async () => {
    const code = inp.value.trim().toUpperCase();
    if (code.length < 4) { inp.focus(); return; }
    go.disabled = true;
    try {
      const res = await joinClass(state.student, code);
      close();
      await refresh();
      navigate('subject', res.classroom_id);
    } catch (e) {
      err.textContent = e.message;
      err.hidden = false;
    } finally {
      go.disabled = false;
    }
  };
  go.onclick = submit;
  inp.onkeydown = e => { if (e.key === 'Enter') submit(); };
}

// ── Populate the nav menu's class quick-links ────────────────────────────────
function fillNavSubjects(closeAll) {
  const box = document.getElementById('navSubjects');
  box.innerHTML = state.data.subjects.map(s => `
    <button class="nav-subject" data-s="${s.id}">
      <span class="ns-ic" style="background:${s.color}">${s.icon}</span>${s.name}
    </button>`).join('')
    || `<div class="nav-label" style="text-transform:none;letter-spacing:0;font-weight:600">No classes yet</div>`;
  box.querySelectorAll('.nav-subject').forEach(el => {
    el.onclick = () => { navigate('subject', el.dataset.s); closeAll(); };
  });
}

async function boot() {
  initTheme();
  const { closeAll } = initDrawers();
  initStudio();

  let name = localStorage.getItem('roognis_student');
  if (!name) {
    name = await askName();
    localStorage.setItem('roognis_student', name);
  }

  const who = document.getElementById('navWho');
  if (who) {
    who.textContent = name;
    who.onclick = () => { localStorage.removeItem('roognis_student'); location.reload(); };
  }

  const s = await initStudent(name);
  state.student = s.id;

  const refresh = async () => {
    state.data = await getCurriculum(state.student);
    fillNavSubjects(closeAll);
  };
  await refresh();
  initJoin(closeAll, refresh);

  const m = document.getElementById('mode');
  m.className = 'mode ' + (state.data.online ? 'online' : 'offline');
  m.innerHTML = `<span class="dot"></span>${state.data.online ? 'Live · Groq' : 'Demo · offline answers'}`;

  navigate('home');
}

boot();
