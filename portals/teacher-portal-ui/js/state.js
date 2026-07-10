/** Shared mutable application state. */
export const state = {
  rooms: [],     // all classroom objects
  room:  null,   // currently open classroom
  tab:   'chapters',
};

// ── Navigation registry ──────────────────────────────────────────────────────

const _routes = {};

/** Register a view function under a name. */
export function registerRoute(name, fn) {
  _routes[name] = fn;
}

/**
 * Navigate to a registered view.
 * @param {string} name  - route name
 * @param {any}    param - optional arg forwarded to the view fn
 */
export function navigate(name, param) {
  const fn = _routes[name];
  if (!fn) throw new Error(`Unknown route: "${name}"`);
  fn(param);
}
