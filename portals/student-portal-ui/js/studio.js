import { generateImage } from './api.js?v=2';

// Image Studio (right slide-out): prompt → text-to-image, shown on an iPhone-15
// portrait screen. The screen has four mutually-exclusive states — empty, image,
// loading, error — toggled via the shared show() helper.
export function initStudio() {
  const gen = document.getElementById('imgGen');
  const prompt = document.getElementById('imgPrompt');
  if (!gen || !prompt) return;

  const empty = document.getElementById('phEmpty');
  const img = document.getElementById('phImg');
  const load = document.getElementById('phLoad');
  const err = document.getElementById('phErr');

  const show = (el) => [empty, img, load, err].forEach(n => { n.hidden = n !== el; });
  const showError = (msg) => { err.textContent = msg; show(err); };

  let busy = false;
  const run = async () => {
    const p = prompt.value.trim();
    if (!p || busy) return;
    busy = true;
    gen.disabled = true;
    show(load);
    try {
      const r = await generateImage(p);
      if (r && r.ok && r.data_url) {
        img.src = r.data_url;
        img.alt = p;
        show(img);
      } else {
        showError((r && r.error) || "Couldn't generate that image. Please try again.");
      }
    } catch {
      showError('Network error — please try again.');
    } finally {
      busy = false;
      gen.disabled = false;
    }
  };

  gen.onclick = run;
  // ⌘/Ctrl+Enter generates without leaving the textarea.
  prompt.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); run(); }
  });
}
