import { state, navigate } from './state.js';
import { initStudent, getCurriculum } from './api.js';

// Import all views so they self-register their routes via registerRoute().
import './views/home.js';
import './views/subject.js';
import './views/chat.js';

async function boot() {
  const name = localStorage.getItem('roognis_student') || 'Aarav';
  localStorage.setItem('roognis_student', name);

  const s = await initStudent(name);
  state.student = s.id;

  state.data = await getCurriculum();

  const m = document.getElementById('mode');
  m.className = 'mode ' + (state.data.online ? 'online' : 'offline');
  m.innerHTML = `<span class="dot"></span>${state.data.online ? 'Live · Groq' : 'Demo · offline answers'}`;

  navigate('home');
}

boot();
