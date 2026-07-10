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

/** Lighten (d > 0) or darken (d < 0) a hex colour. Returns an rgb() string. */
export function shade(hex, d) {
  const n = parseInt(hex.slice(1), 16);
  const f = x => Math.max(0, Math.min(255, x + d));
  return `rgb(${f((n >> 16) & 255)},${f((n >> 8) & 255)},${f(n & 255)})`;
}

/** Smooth-scroll the messages stream to the bottom. */
export function scroll() {
  const s = document.querySelector('.stream');
  if (s) s.scrollTop = s.scrollHeight;
}

/**
 * Typewriter animation.
 * Writes `text` into `node.textContent` character-by-character, then calls `done`.
 */
export function typewriter(node, text, done) {
  let i = 0;
  const step = Math.max(2, Math.round(text.length / 90));
  const t = setInterval(() => {
    i += step;
    node.textContent = text.slice(0, i);
    scroll();
    if (i >= text.length) {
      clearInterval(t);
      node.textContent = text;
      done && done();
    }
  }, 16);
}
