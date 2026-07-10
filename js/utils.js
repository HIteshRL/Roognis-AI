/** Create a DOM node from an HTML string. */
export function $(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstChild;
}

/** Escape special HTML characters. */
export function esc(s) {
  return (s || '').replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
}

/** Lighten (d > 0) or darken (d < 0) a hex colour. Returns rgb() string. */
export function shade(hex, d) {
  const n = parseInt(hex.slice(1), 16);
  const f = x => Math.max(0, Math.min(255, x + d));
  return `rgb(${f((n >> 16) & 255)},${f((n >> 8) & 255)},${f(n & 255)})`;
}

/** Show a bottom toast notification for 1.6 s. */
export function toast(text) {
  const n = document.getElementById('toast');
  n.textContent = text;
  n.classList.add('show');
  setTimeout(() => n.classList.remove('show'), 1600);
}

/** Tear down whatever modal is currently mounted. */
export function closeModal() {
  document.getElementById('modalRoot').innerHTML = '';
}
