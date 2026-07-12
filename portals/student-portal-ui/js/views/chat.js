import { state, setAccent, navigate, registerRoute } from '../state.js?v=2';
import { $, esc, shade, scroll, typewriter } from '../utils.js?v=2';
import { sendChat, nextQuestion, answerQuestion } from '../api.js?v=2';

// Module-local: the outstanding inline check-question, if any. When set, the
// next typed message answers it instead of starting a new chat turn.
let pendingCheck = null;

export function renderChapter(cid) {
  const s = state.subject;
  const c = s.chapters.find(x => x.id === cid);
  state.chapter = c;
  state.conversation = null;
  pendingCheck = null;
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
  // The input routes to the check-answer when one is pending, else a normal ask.
  const go = () => {
    const v = input.value.trim();
    if (!v) return;
    if (pendingCheck) submitCheckAnswer(v);
    else ask(v);
  };
  send.onclick = go;
  input.onkeydown = e => { if (e.key === 'Enter') go(); };
  app.querySelectorAll('.chip').forEach(ch => ch.onclick = () => ask(ch.dataset.q));
  input.focus();
}

// ── Private helpers ──────────────────────────────────────────────────────────

function getThread() { return document.getElementById('thread'); }

function setPlaceholder(text) {
  const input = document.getElementById('q');
  if (input) input.placeholder = text;
}

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
      // After the tutor finishes explaining, weave in ONE check — never mid-flow.
      maybeAskCheck(d);
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
  // Tapping a chip / asking a new question abandons any pending check.
  clearCheck();

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

// ── Inline check-question (Tier-1 evidence capture) ──────────────────────────

async function maybeAskCheck(lastDecision) {
  if (pendingCheck) return;
  try {
    const r = await nextQuestion({
      student_id:  state.student,
      subject_id:  state.subject.id,
      chapter_id:  state.chapter.id,
      last_question: lastDecision && lastDecision.question ? lastDecision.question : null,
    });
    if (r && r.question) pushCheck(r.question);
  } catch {
    /* evidence capture is best-effort — never disrupt the chat */
  }
}

function pushCheck(q) {
  pendingCheck = q;
  const el = $(`
    <div class="msg ai check" id="check-${q.id}">
      <div class="who">Quick check</div>
      <div class="bubble">
        <div class="ck-q">${esc(q.question)}</div>
        <div class="ck-actions"><button class="ck-skip" type="button">Skip</button></div>
      </div>
    </div>`);
  getThread().appendChild(el);
  el.querySelector('.ck-skip').onclick = () => { clearCheck(); setPlaceholder(`Ask about ${state.chapter.title}…`); };
  setPlaceholder('Type your answer to the check…');
  scroll();
  const input = document.getElementById('q');
  if (input) input.focus();
}

async function submitCheckAnswer(answer) {
  const q = pendingCheck;
  const input = document.getElementById('q');
  const send  = document.getElementById('send');
  if (!q) return;
  if (input) input.value = '';
  if (send)  send.disabled = true;
  pendingCheck = null;   // consume before the await so double-Enter can't resubmit

  pushUser(answer);
  const typing = pushTyping();
  try {
    const r = await answerQuestion({ student_id: state.student, question_id: q.id, answer });
    typing.remove();
    renderCheckFeedback(r);
  } catch {
    typing.remove();
    getThread().appendChild($(`
      <div class="notice nic">
        <div class="em">ℹ️</div>
        <div><div class="t">Couldn't grade that just now — no worries, let's keep going.</div></div>
      </div>`));
  } finally {
    setPlaceholder(`Ask about ${state.chapter.title}…`);
    if (send)  send.disabled = false;
    scroll();
    if (input) input.focus();
  }
}

function renderCheckFeedback(r) {
  const ev = (r && r.evaluation) || {};
  const tone = ev.signal === 'correct'
    ? { cls: 'ck-good', em: '✓', head: "Nice — you've got this." }
    : ev.signal === 'partial'
      ? { cls: 'ck-part', em: '≈', head: 'Close — almost there.' }
      : { cls: 'ck-miss', em: '↻', head: "Let's revisit this together." };

  getThread().appendChild($(`
    <div class="msg ai">
      <div class="who">Tutor</div>
      <div class="bubble ck-fb ${tone.cls}">
        <div class="ck-head">${tone.em} ${tone.head}</div>
        <div class="ck-detail">${esc(ev.feedback || '')}</div>
      </div>
    </div>`));
  scroll();
}

function clearCheck() {
  if (!pendingCheck) return;
  const el = document.getElementById('check-' + pendingCheck.id);
  if (el) {
    const actions = el.querySelector('.ck-actions');
    if (actions) actions.remove();
  }
  pendingCheck = null;
}

registerRoute('chat', renderChapter);
