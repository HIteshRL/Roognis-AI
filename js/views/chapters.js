import { state } from '../state.js';
import { $, esc, toast } from '../utils.js';
import { getChapters, getDocs, uploadDoc } from '../api.js';
import { addChapterModal } from '../modals/add-chapter.js';

export async function paneChapters() {
  const pane = document.getElementById('pane');
  const r    = state.room;
  const chs  = await getChapters(r.id);

  pane.innerHTML = `
    <div class="row" style="margin-bottom:12px">
      <div class="sub">${chs.length} chapters</div>
      <button class="btn sm" id="addch">＋ Add chapter</button>
    </div>
    <div id="chlist"></div>`;

  document.getElementById('addch').onclick = () => addChapterModal(r.id);

  const list = document.getElementById('chlist');
  for (const [i, ch] of chs.entries()) {
    const row = $(`
      <div>
        <div class="listrow">
          <div class="num">${i + 1}</div>
          <div><h4>${esc(ch.title)}</h4><div class="m">${esc(ch.summary || '')}</div></div>
          <button class="btn ghost sm spacer" data-up="${ch.id}">⬆ Upload PDF</button>
        </div>
        <div class="docs" id="docs-${ch.id}"></div>
      </div>`);
    list.appendChild(row);
    row.querySelector('[data-up]').onclick = () => pickFile(ch.id);
    loadDocs(ch.id);
  }
}

export function pickFile(chid) {
  const inp = document.createElement('input');
  inp.type   = 'file';
  inp.accept = 'application/pdf,.pdf';
  inp.onchange = async () => {
    const f = inp.files[0];
    if (!f) return;
    const fd = new FormData();
    fd.append('file', f);
    toast('Uploading ' + f.name + '…');
    try {
      await uploadDoc(chid, fd);
      pollDocs(chid);
    } catch (e) {
      toast(e.detail || 'Upload failed');
    }
  };
  inp.click();
}

export async function loadDocs(chid) {
  const docs = await getDocs(chid);
  const el   = document.getElementById('docs-' + chid);
  if (!el) return;
  el.innerHTML = docs.map(d =>
    `<div class="doc">
       📄 ${esc(d.filename)}
       <span class="stt ${d.status}">${d.status}</span>
       ${d.status === 'ready' ? `· ${d.pages}p · ${d.chunk_count} chunks` : ''}
       ${d.error ? `· ${esc(d.error)}` : ''}
     </div>`
  ).join('') || `<div class="doc" style="opacity:.6">No documents yet — upload a PDF to teach this chapter.</div>`;
}

export function pollDocs(chid) {
  let n = 0;
  const t = setInterval(async () => {
    await loadDocs(chid);
    n++;
    const el = document.getElementById('docs-' + chid);
    if (n > 20 || (el && !el.innerHTML.includes('processing'))) clearInterval(t);
  }, 1500);
}
