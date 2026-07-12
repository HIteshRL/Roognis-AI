import { state, setAccent, navigate, registerRoute } from '../state.js?v=2';
import { esc } from '../utils.js?v=2';
import { getInsights } from '../api.js?v=2';

/** Relative "time ago" for timeline stamps (epoch seconds). */
function ago(ts) {
  if (!ts) return '';
  const s = Date.now() / 1000 - ts;
  if (s < 90) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

/** Find the chapter whose title matches a recommended concept, for deep-linking. */
function chapterFor(concept) {
  for (const s of state.data.subjects) {
    const c = s.chapters.find(ch => ch.title === concept);
    if (c) return c.id;
  }
  return null;
}

const REC_ICON = { gap: '🩹', review: '↻', new: '🌱' };
const PCT = v => `${Math.max(2, Math.min(100, v))}%`;

export async function renderInsights() {
  setAccent('#16a34a');
  const app = document.getElementById('app');
  app.innerHTML = `<div class="ins-head"><h1>My Progress</h1>
    <p>Loading what the tutor has learned about you…</p></div>`;

  const d = await getInsights(state.student);
  const a = d.analytics;

  if (!a.evidence_events && !d.timeline.length) {
    app.innerHTML = `
      <button class="back" id="insBack">‹ Home</button>
      <div class="ins-head"><h1>My Progress</h1>
        <p>Everything here is derived from evidence — never assumed.</p></div>
      <div class="ins-empty"><div class="big">🌱</div>
        <b>No evidence yet</b>
        Ask the tutor a question and answer a quick check — this page comes alive
        with your mastery, gaps and next steps.</div>`;
    document.getElementById('insBack').onclick = () => navigate('home');
    return;
  }

  const stats = `
    <div class="stats">
      <div class="stat"><div class="v">${a.checks_answered}${a.accuracy != null
        ? `<small>${Math.round(a.accuracy * 100)}% correct</small>` : ''}</div>
        <div class="k">Checks answered</div></div>
      <div class="stat"><div class="v">${a.concepts_touched}</div><div class="k">Concepts explored</div></div>
      <div class="stat"><div class="v">${a.active_days}</div><div class="k">Active days</div></div>
      <div class="stat"><div class="v">${a.evidence_events}</div>
        <div class="k">Evidence events · ${esc(a.velocity)}</div></div>
    </div>`;

  const mastery = d.mastery.length ? d.mastery.map(m => `
    <div class="meter">
      <div class="mrow"><span class="mname">${esc(m.concept)}</span>
        <span class="mval">${Math.round(m.score)}</span></div>
      <div class="track"><div class="fill" style="width:${PCT(m.score)}"></div></div>
      <div class="msub"><span class="chip-t ${m.label}">${m.label}</span>
        <span>confidence ${m.confidence.toFixed(2)} · ${m.interactions} signals</span></div>
    </div>`).join('') : `<div class="none">No mastery signals yet.</div>`;

  const gaps = d.gaps.length ? d.gaps.map(g => `
    <div class="gap ${g.resolved ? 'resolved' : ''}">
      <span class="chip-s ${g.resolved ? 'done' : g.severity}">${g.resolved ? 'closed' : g.severity}</span>
      <div><div class="gname">${esc(g.concept)}</div>
        <div class="greason">${esc(g.reason)} · seen ${g.occurrences}×</div></div>
    </div>`).join('') : `<div class="none">No learning gaps detected — keep going!</div>`;

  const recs = d.recommendations.length ? d.recommendations.map(r => {
    const cid = chapterFor(r.concept);
    return `<div class="rec" ${cid ? `data-c="${cid}"` : ''}>
      <span class="ric">${REC_ICON[r.type] || '📖'}</span>
      <div><div class="rname">${esc(r.concept)}</div><div class="rwhy">${esc(r.reason)}</div></div>
      ${cid ? '<span class="go">›</span>' : ''}</div>`;
  }).join('') : `<div class="none">Recommendations appear once you start learning.</div>`;

  const skills = d.skills.length ? d.skills.map(s => `
    <div class="bloom">
      <div class="brow"><span class="bname">${esc(s.level)}</span>
        <span class="bval">${s.correct}/${s.attempted} · ${Math.round(s.accuracy * 100)}%</span></div>
      <div class="track" style="height:8px;border-radius:4px;background:color-mix(in srgb,var(--fg) 8%,transparent);overflow:hidden">
        <div class="fill" style="height:100%;border-radius:4px;width:${PCT(s.accuracy * 100)};background:linear-gradient(90deg,color-mix(in srgb,var(--brand) 65%,transparent),var(--brand))"></div></div>
    </div>`).join('') : `<div class="none">Answer a few checks to build your skill profile.</div>`;

  const tl = d.timeline.length ? d.timeline.map(t => `
    <div class="tli">
      <span class="tic">${t.kind === 'chat' ? '💬' : (t.correct ? '✓' : '↻')}</span>
      <div><div class="tt">${esc(t.title)}</div>
        ${t.meta ? `<div class="tm">${esc(t.meta)}</div>` : ''}</div>
      <span class="tw">${ago(t.at)}</span>
    </div>`).join('') : `<div class="none">Your activity shows up here.</div>`;

  app.innerHTML = `
    <button class="back" id="insBack">‹ Home</button>
    <div class="ins-head"><h1>My Progress</h1>
      <p>Everything below is derived from evidence of what you actually did — never assumed.</p></div>
    ${stats}
    <div class="ins-grid">
      <div class="panel"><h3>📈 Mastery</h3>
        <p class="ph">Score per concept, smoothed over every signal.</p>${mastery}</div>
      <div class="panel"><h3>🩹 Learning gaps</h3>
        <p class="ph">Detected from missed checks — closed when you recover.</p>${gaps}</div>
      <div class="panel"><h3>🧭 What to do next</h3>
        <p class="ph">Ranked: close gaps, review weak spots, then new topics.</p>${recs}</div>
      <div class="panel"><h3>🧠 Skills by depth</h3>
        <p class="ph">Accuracy at each thinking level (Bloom).</p>${skills}</div>
      <div class="panel" style="grid-column:1/-1"><h3>🕒 Timeline</h3>
        <p class="ph">Your recent conversations and checks.</p><div class="tl">${tl}</div></div>
    </div>`;

  document.getElementById('insBack').onclick = () => navigate('home');
  app.querySelectorAll('.rec[data-c]').forEach(el => {
    el.onclick = () => navigate('chat', el.dataset.c);
  });
}

registerRoute('insights', renderInsights);
