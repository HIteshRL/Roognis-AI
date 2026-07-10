import { state, setAccent, navigate, registerRoute } from '../state.js';
import { $, esc, shade, scroll, typewriter } from '../utils.js';
import { sendChat } from '../api.js';

export function renderChapter(cid) {
  const s = state.subject;
  const c = s.chapters.find(x => x.id === cid);
  state.chapter = c;
  state.conversation = null;
  setAccent(s.color);

  const chips = c.summary
    .replace(/\.$/, '')
    .split(/,| and /)
    .map(x => x.trim())
    .filter(Boolean)
    .slice(0, 3)
    .map(x => `<button class="chip" data-q="Explain ${x}">${x.charAt(0).toUpperCase() + x.slice(1)}</button>`)
    .join('');

  const app = document.getElementById('app');
  app.innerHTML = `
    <div class="chatwrap">
      <div class="chead">
        <button class="back">‹ ${s.name}</button>
        <div class="row">
          <div class="ic" style="background:linear-gradient(135deg, ${s.color}, ${shade(s.color, -30)});color:#fff">${s.icon}</div>
          <div><h3>${c.title}</h3><div class="sub">${s.name} · Class 10 ICSE</div></div>
        </div>
        <div class="scope">
          <span class="tag">AI Tutor</span>
          Answers are grounded only in <b>${c.title}</b>. Safety &amp; subject guardrails are on.
        </div>
      </div>
      <div class="stream">
        <div class="thread" id="thread">
          <div class="empty" id="empty">
            <div class="big">💡</div>
            <b>Ask anything about "${c.title}".</b>
            <div style="font-size:13px;margin-top:4px">Your tutor checks the chapter before answering.</div>
            <div class="chips">${chips}</div>
          </div>
        </div>
      </div>
      <div class="inbar">
        <div class="inrow">
          <input id="q" placeholder="Ask about ${c.title}…" autocomplete="off" />
          <button class="send" id="send">Send</button>
        </div>
        <div class="disc">Roognis answers from your chapter. Verify important facts.</div>
      </div>
    </div>`;

  app.querySelector('.back').onclick = () => navigate('subject', s.id);

  const input = document.getElementById('q');
  const send  = document.getElementById('send');
  const go = () => { const v = input.value.trim(); if (v) ask(v); };
  send.onclick = go;
  input.onkeydown = e => { if (e.key === 'Enter') go(); };
  app.querySelectorAll('.chip').forEach(ch => ch.onclick = () => ask(ch.dataset.q));
  input.focus();
}

// ── Private helpers ──────────────────────────────────────────────────────────

function getThread() { return document.getElementById('thread'); }

function pushUser(text) {
  const empty = document.getElementById('empty');
  if (empty) empty.remove();
  getThread().appendChild($(`
    <div class="msg user">
      <div class="bubble">${esc(text)}</div>
      <div class="who">You</div>
    </div>`));
  scroll();
}

function pushTyping() {
  const el = $(`
    <div class="msg ai" id="typing">
      <div class="who">AI</div>
      <div class="bubble typing"><span></span><span></span><span></span></div>
    </div>`);
  getThread().appendChild(el);
  scroll();
  return el;
}

function renderDecision(d) {
  if (d.decision === 'answered') {
    const src = (d.sources && d.sources.length)
      ? `<div class="src">📎 From ${esc(d.sources[0].title || 'this chapter')}</div>`
      : '';
    const el = $(`<div class="msg ai"><div class="who">AI</div><div class="bubble"></div></div>`);
    getThread().appendChild(el);
    typewriter(el.querySelector('.bubble'), d.answer || '', () => {
      el.querySelector('.bubble').insertAdjacentHTML('beforeend',
        src + `<div class="verified">✓ Grounded in chapter</div>`);
      scroll();
    });
    return;
  }

  const map = {
    off_topic:       { cls: 'off',   em: '↪️',  g: 'Subject guardrail' },
    not_in_chapter:  { cls: 'nic',   em: '📕',  g: 'Not in this chapter' },
    blocked_unsafe:  { cls: 'block', em: '🛡️', g: 'Safety guardrail' },
    pending:         { cls: 'off',   em: '⏳',  g: 'Awaiting teacher approval' },
    error:           { cls: 'block', em: '⚠️', g: 'Error' },
  }[d.decision] || { cls: 'nic', em: 'ℹ️', g: '' };

  getThread().appendChild($(`
    <div class="notice ${map.cls}">
      <div class="em">${map.em}</div>
      <div><div class="t">${esc(d.message || '')}</div><div class="g">${map.g}</div></div>
    </div>`));
  scroll();
}

async function ask(question) {
  const input = document.getElementById('q');
  const send  = document.getElementById('send');
  if (input) input.value = '';
  if (send)  send.disabled = true;

  pushUser(question);
  const typing = pushTyping();

  try {
    const d = await sendChat({
      question,
      subject_id:      state.subject.id,
      chapter_id:      state.chapter.id,
      student_id:      state.student,
      conversation_id: state.conversation,
    });
    if (d.conversation_id) state.conversation = d.conversation_id;
    typing.remove();
    renderDecision(d);
  } catch {
    typing.remove();
    getThread().appendChild($(`
      <div class="notice block">
        <div class="em">⚠️</div>
        <div><div class="t">Something went wrong. Please try again.</div></div>
      </div>`));
  } finally {
    if (send)  send.disabled = false;
    scroll();
    if (input) input.focus();
  }
}

registerRoute('chat', renderChapter);
