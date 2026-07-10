import { $, toast, closeModal } from '../utils.js';
import { createChapter } from '../api.js';
import { renderRoom } from '../views/classroom.js';

export function addChapterModal(classroomId) {
  const m = $(`
    <div class="backdrop">
      <div class="modal">
        <div class="mh">
          <h2>Add chapter</h2>
          <button class="btn ghost" id="mClose">✕</button>
        </div>
        <div class="mbody">
          <div class="field"><label>Title</label><input id="c_t" placeholder="e.g. Electromagnetism"></div>
          <div class="field"><label>Summary (optional)</label><input id="c_s" placeholder="Short description"></div>
          <div class="mfoot">
            <button class="btn ghost" id="mCancel">Cancel</button>
            <button class="btn" id="c_go">Add</button>
          </div>
        </div>
      </div>
    </div>`);

  document.getElementById('modalRoot').appendChild(m);

  m.querySelector('#mClose').onclick  = closeModal;
  m.querySelector('#mCancel').onclick = closeModal;

  m.querySelector('#c_go').onclick = async () => {
    const title = m.querySelector('#c_t').value.trim();
    if (!title) return;
    await createChapter(classroomId, { title, summary: m.querySelector('#c_s').value });
    closeModal();
    toast('Chapter added');
    renderRoom();
  };
}
