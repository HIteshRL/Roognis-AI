import { shade } from './utils.js';

/** Shared mutable application state. */
export const state = {
  data: null,          // curriculum payload
  subject: null,       // currently selected subject object
  chapter: null,       // currently selected chapter object
  student: null,       // student session id
  conversation: null,  // active conversation id
};

/** Apply a subject colour as the --accent CSS custom property. */
export function setAccent(color) {
  document.documentElement.style.setProperty('--accent', color);
}

// ── Navigation registry ──────────────────────────────────────────────────────
// Views register themselves; navigate() dispatches by name without direct imports
// between view modules (avoids circular dependencies).

const _routes = {};

/** Register a view function under a name. Called by each view module at load time. */
export function registerRoute(name, fn) {
  _routes[name] = fn;
}

/**
 * Navigate to a registered view.
 * @param {string} name  - route name as registered
 * @param {any}    param - optional argument forwarded to the view function
 */
export function navigate(name, param) {
  const fn = _routes[name];
  if (!fn) throw new Error(`Unknown route: "${name}"`);
  fn(param);
}
