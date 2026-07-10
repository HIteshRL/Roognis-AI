import { navigate } from './state.js';
import { closeModal } from './utils.js';

// Import all views and modals so they self-register.
import './views/home.js';
import './views/classroom.js';
import './views/chapters.js';
import './views/students.js';
import './views/insights.js';

// Expose globals needed by inline onclick handlers generated dynamically.
// (closeModal is referenced in modal HTML strings as onclick="closeModal()")
window.closeModal = closeModal;

const teacher = localStorage.getItem('roognis_teacher') || 'Ms. Rao';
localStorage.setItem('roognis_teacher', teacher);

navigate('home');
