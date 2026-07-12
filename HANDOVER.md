# Handover — Session Context for Next Claude Window

**Date**: 2026-07-10  
**Last Commit**: `6ce55b4` — Portal restructuring (modular CSS + ES-module JS)  
**Branch**: `Phase-0.8-#2`

---

## What Just Shipped

### Portal Restructuring (Complete)

Both student and teacher portals have been split from single monolithic HTML files into **modular project structures** with separated CSS and ES-module JavaScript.

#### Student Portal
- **Location**: `portals/student-portal-ui/`
- **Entry**: Thin `index.html` (links CSS, loads `js/app.js` as `type="module"`)
- **CSS** (`css/`): `base.css`, `header.css`, `home.css`, `subject.css`, `chat.css`
- **JS** (`js/`):
  - `utils.js` — `$`, `esc`, `shade`, `scroll`, `typewriter`
  - `api.js` — `initStudent`, `getCurriculum`, `sendChat`
  - `state.js` — shared state + navigation registry (`registerRoute`, `navigate`)
  - `views/home.js`, `subject.js`, `chat.js` — each view self-registers
  - `app.js` — imports all views, calls `navigate('home')`
- **Orphan Branch**: `portal/student-ui` (just pushed)

#### Teacher Portal
- **Location**: `portals/teacher-portal-ui/`
- **Entry**: Thin `index.html` (same pattern)
- **CSS** (`css/`): `base.css`, `header.css`, `home.css`, `classroom.css`, `chapters.css`, `students.css`, `insights.css`, `modal.css`
- **JS** (`js/`):
  - `utils.js`, `api.js`, `state.js` — shared utilities
  - `views/home.js`, `classroom.js`, `chapters.js`, `students.js`, `insights.js`
  - `modals/create-class.js`, `add-chapter.js` — modal factories
  - `app.js` — wires views, exposes `window.closeModal` for dynamic HTML
- **Orphan Branch**: `portal/teacher-ui` (just pushed)

---

## Key Design Patterns

### Navigation Registry (No Circular Imports)
```javascript
// In state.js
registerRoute('home', renderHome);   // View self-registers at load
navigate('home');                     // Dispatcher calls it
```
Views don't import each other — they dispatch by name. `app.js` imports all views (registration happens), then calls `navigate('home')`.

### Global Functions for Inline Handlers
```javascript
// In app.js (teacher portal)
window.closeModal = closeModal;  // Exposed for onclick="closeModal()" in dynamic HTML
```

### Per-View CSS
Each view has its own CSS file. Base/header/utilities are shared; page-specific styling stays in `home.css`, `subject.css`, etc.

---

## How to Add Features

### New View (Student Portal)
1. Create `js/views/my-feature.js`:
```javascript
import { registerRoute, navigate, state } from '../state.js';
export function renderMyFeature() { /* ... */ }
registerRoute('my-feature', renderMyFeature);
```
2. Import it in `app.js`:
```javascript
import './views/my-feature.js';
```
3. Navigate with `navigate('my-feature')` from another view.

### New Modal (Teacher Portal)
1. Create `js/modals/my-modal.js`:
```javascript
export function myModal() {
  const m = $(`<div class="backdrop"><div class="modal">...</div></div>`);
  document.getElementById('modalRoot').appendChild(m);
  // Wire event handlers...
}
```
2. Import in `app.js` or the view that opens it.
3. Call `myModal()` when needed.

### New CSS for a View
1. Create `css/my-view.css` with page-specific styles.
2. Link it in `index.html`:
```html
<link rel="stylesheet" href="css/my-view.css" />
```

---

## Orphan Branches
- `portal/student-ui` — pristine student portal (no main history)
- `portal/teacher-ui` — pristine teacher portal (no main history)

These are independently cloneable, deployable reference implementations.

---

## Next Steps (Optional)

1. **Test the portals locally** — verify ES-module loading works with your FastAPI static server.
2. **Add features** — follow the patterns above.
3. **Update StaticFiles routes** if needed (check `apps/api/src/presentation/api/v1/routes.py`).

---

## Known State

- ✅ Both portals split and committed to `Phase-0.8-#2`
- ✅ Orphan branches pushed to GitHub
- ✅ All 33 files created (CSS + JS + updated index.html)
- ✅ Navigation registry tested (no circular imports)
- ⚠️ Frontend preview not yet tested against live backend

---

## Files Modified / Created

**Modified**:
- `portals/student-portal-ui/index.html`
- `portals/teacher-portal-ui/index.html`

**Created** (33 new files):
- Student portal: 5 CSS, 8 JS (utils, api, state, 3 views, app)
- Teacher portal: 8 CSS, 13 JS (utils, api, state, 5 views, 2 modals, app)

---

**End of Handover** — Next Claude session should read this before continuing work on the portals or moving to new features.
