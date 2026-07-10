import { state, navigate } from '../state.js';
import { $, toast, closeModal } from '../utils.js';
import { createClassroom } from '../api.js';

const COLORS = ['#4f46e5','#1e8e3e','#e52592','#9334e6','#e8710a','#00897b','#d93025','#3949ab'];

export function createModal() {
  let color = COLORS[state.rooms.length % COLORS.length];
  const teacher = localStorage.getItem('roognis_teacher') || 'Ms. Rao';

  const m = $(`
    <div class="backdrop">
      <div class="modal">
        <div class="mh">
          <h2>Create class</h2>
          <button class="btn ghost" id="mClose">✕</button>
        </div>
        <div class="mbody">
          <div class="field"><label>Class name</label><input id="f_name" placeholder="e.g. Class 10 Robotics"></div>
          <div class="g2">
            <div class="field"><label>Subject</label><input id="f_sub" placeholder="Robotics"></div>
            <div class="field"><label>Section</label><input id="f_sec" placeholder="A"></div>
          </div>
          <div class="field"><label>Icon (emoji)</label><input id="f_icon" placeholder="🤖" maxlength="2"></div>
          <div class="field"><label>Theme</label><div class="sw" id="sw"></div></div>
          <div class="mfoot">
            <button class="btn ghost" id="mCancel">Cancel</button>
            <button class="btn" id="f_go">Create</button>
          </div>
        </div>
      </div>
    </div>`);

  document.getElementById('modalRoot').appendChild(m);

  m.querySelector('#mClose').onclick  = closeModal;
  m.querySelector('#mCancel').onclick = closeModal;

  const sw = m.querySelector('#sw');
  COLORS.forEach(c => {
    const b = document.createElement('button');
    b.className = 'swb' + (c === color ? ' on' : '');
    b.style.background = c;
    b.onclick = () => {
      color = c;
      sw.querySelectorAll('.swb').forEach(x => x.classList.remove('on'));
      b.classList.add('on');
    };
    sw.appendChild(b);
  });

  m.querySelector('#f_go').onclick = async () => {
    const name = m.querySelector('#f_name').value.trim();
    if (!name) return;
    await createClassroom({
      name,
      subject: m.querySelector('#f_sub').value,
      section: m.querySelector('#f_sec').value,
      icon:    m.querySelector('#f_icon').value,
      color,
      teacher,
    });
    closeModal();
    toast('Class created');
    navigate('home');
  };
}
