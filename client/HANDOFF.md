# Roognis AI — Client (Frontend) Handoff

This folder is a **standalone, self-contained snapshot of the Roognis AI web client** — the entire frontend, extracted from the main monorepo with nothing server-side. It builds and runs on its own. The goal of this handoff is to **convert it into an installable PWA (Progressive Web App)**.

> This is the **real application** (Next.js 15 App Router), not a mockup. It talks to the Roognis backend over HTTP/SSE.

---

## 1. What's in here

```
client/
├── package.json            # npm-workspaces root (run everything from here)
├── tsconfig.base.json      # shared TS config the app extends
├── apps/
│   └── web/                # ← the Next.js 15 app (all UI lives here)
│       ├── app/            # App Router routes (route groups: (auth), (dashboard), (admin))
│       ├── components/     # Shared components incl. components/ui (shadcn/Radix primitives)
│       ├── features/       # Feature modules: chat, student, teacher, dashboard, auth, …
│       ├── lib/            # api/ (backend client), stores/ (Zustand), providers/, utils
│       ├── middleware.ts   # Clerk auth gate (protects all non-public routes)
│       ├── next.config.ts  # transpilePackages, image hosts
│       ├── tailwind.config.ts / postcss.config.mjs
│       └── public/         # ← EMPTY. PWA icons + manifest go here.
└── packages/               # Tiny workspace libs the app imports as @roognis/*
    ├── shared/             # @roognis/shared — types, DTOs, constants, utils
    ├── ui/                 # @roognis/ui — a few shared components
    ├── types/              # @roognis/types
    └── config/             # @roognis/config
```

The app imports `@roognis/shared` and `@roognis/ui`. These are transpiled from source by Next (see `transpilePackages` in `next.config.ts`) — **no build step for the packages is needed**. The workspace layout resolves them automatically.

---

## 2. Quick start

```bash
# from this client/ folder
npm install                     # sets up workspaces + symlinks @roognis/* packages
cp apps/web/.env.local.example apps/web/.env.local   # then fill in the values
npm run dev                     # → http://localhost:3000
```

Other scripts (run from `client/`): `npm run build`, `npm run start`, `npm run type-check`, `npm run lint`.

> pnpm also works (the original monorepo used pnpm@9). If you prefer it: `pnpm install && pnpm dev`.

---

## 3. Tech stack

| Area | Choice |
|------|--------|
| Framework | **Next.js 15.1.3** (App Router, Turbopack in dev), React 19 |
| Language | TypeScript (strict) |
| Auth | **Clerk** (`@clerk/nextjs`) — gates the whole app |
| Server state | **TanStack Query v5** |
| Client state | **Zustand** |
| UI | Radix UI primitives + shadcn/ui patterns (`components/ui`) |
| Styling | **Tailwind CSS v3** |
| Forms | react-hook-form + zod |
| Markdown | react-markdown + rehype-highlight + remark-gfm |
| Theme | next-themes (light/dark) |
| Toasts | sonner · Icons: lucide-react |

---

## 4. Auth — read this first

The app is **fully gated by Clerk**. `middleware.ts` runs `auth.protect()` on every route except the public ones (`/`, `/login`, `/register`, `/forgot-password`, `/api/v1/health`, `/api/v1/version`, `/api/v1/auth/*`). Without valid Clerk keys in `.env.local`, the dev server boots into a "Missing publishable key" error and nothing renders.

- Get test keys from the [Clerk dashboard](https://dashboard.clerk.com).
- The app attaches the Clerk session token as a **Bearer JWT** on every backend request (see `lib/api/client.ts` → `setTokenProvider`).

---

## 5. Backend API contract

All data + chat come from a separate **FastAPI backend** at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). The client layer is in **`apps/web/lib/api/`** — one file per domain:

| File | Covers |
|------|--------|
| `client.ts` | Fetch wrapper: `get/post/patch/delete`, `uploadForm` (multipart), `streamPost` (SSE) |
| `auth.ts` | Login / register / me |
| `chat.ts` | **Streaming chat** (SSE); `sendMessage(message, conversationId?, chapterId?)` |
| `student.ts` | Student learning analytics (profile, mastery, gaps, skills, path, timeline) |
| `classroom.ts` | Google-Classroom features — both `teacherApi` (classrooms/chapters/students/upload) and `classroomStudentApi` (join, list, chapters) |
| `knowledge.ts` / `search.ts` / `user.ts` | Documents/RAG, search, user settings |

Conventions:
- **Response envelope:** every JSON response is `{ success, data, message, request_id }`. Components read `.data` (see the `select: (r) => r.data` pattern in TanStack Query hooks).
- **Chat is Server-Sent Events**, not JSON — `streamPost` returns a `ReadableStream`; the client parses `data: {...}` lines with event types `meta` / `chunk` / `done`. **This matters for offline/PWA caching (see §7).**
- **Chapter-scoped inference:** the student chapter view links to `/chat?chapter=<id>&title=<t>`; the chat then scopes answers to that chapter.

You do **not** need the backend to work on layout/PWA/design tasks — but you do to see live data. Ask the backend team for a running instance URL, or stub the `lib/api/*` calls.

---

## 6. Route map (App Router)

Under `app/`, using route groups:

- `(auth)/` → `/login`, `/register`, `/forgot-password`
- `(dashboard)/`
  - `/dashboard` — main dashboard
  - `/chat`, `/chat/[conversationId]` — tutor chat (SSE streaming)
  - `/student`, `/student/mastery`, `/student/gaps`, `/student/recommendations`, `/student/learning-path`, `/student/skills`, `/student/graph`, `/student/timeline`, `/student/statistics`
  - `/student/classes`, `/student/classes/[classroomId]` — student's joined classes → chapters
  - `/teacher`, `/teacher/[classroomId]` — teacher's classes (Google-Classroom style) → chapters, students, content upload
  - `/profile`, `/settings`
- `(admin)/` → `/admin`

Navigation lives in `components/layout/Sidebar.tsx`.

---

## 7. PWA conversion — the main task

Target: an **installable, offline-aware PWA** on top of this Next.js 15 App Router app.

### Recommended approach: Serwist
For Next 15 App Router, **[Serwist](https://serwist.pages.dev/)** (`@serwist/next`) is the current best-supported service-worker toolchain (the older `next-pwa` predates App Router). Alternative: `@ducanh2912/next-pwa`.

### Checklist
1. **Web App Manifest** — add `app/manifest.ts` (Next's typed metadata route) exporting name, short_name, `start_url: "/"`, `display: "standalone"`, `theme_color`, `background_color`, and `icons` (see §8). Next serves it at `/manifest.webmanifest` automatically.
2. **Icons** — place designer-provided icons in `public/` (currently empty): at minimum `192×192`, `512×512`, plus a **maskable** 512 variant, `apple-touch-icon` (180×180), and a favicon.
3. **Service worker** — install `@serwist/next`, add the SW entry (e.g. `app/sw.ts`), wrap `next.config.ts` with `withSerwist`, and register it. Precache the app shell; runtime-cache static assets.
4. **Metadata** — in `app/layout.tsx` add `themeColor`, `appleWebApp` (via the `metadata`/`viewport` exports) so iOS treats it as installable.
5. **Offline fallback** — provide an `/offline` route and a fallback in the SW for navigations that fail.
6. **Test** — Chrome DevTools → Application (manifest + SW) and Lighthouse → PWA audit. Installability needs HTTPS (or localhost), a valid manifest, a registered SW, and the icon set.

### Caveats specific to this app (please account for these)
- **Chat is SSE (streaming) and requires the network** — it can't be served from cache. Gate it behind an online check and show a friendly offline state.
- **Everything is auth-gated by Clerk** and most screens fetch live data. A cached shell will render, but data won't. Consider **persisting TanStack Query** (`@tanstack/query-persist-client-core` + IndexedDB) so analytics/dashboard screens show last-known data offline.
- **Clerk + service workers**: verify the SW doesn't intercept/caches Clerk auth requests or `/api/v1/auth/*`. Exclude auth and API routes from precache; use network-first (or network-only) for `NEXT_PUBLIC_API_URL` calls.
- Don't cache `POST`/SSE responses.

---

## 8. For designers

- **`public/` is intentionally empty** — it needs the full PWA icon set + (optional) splash screens. Deliverables: app icon (square, safe-area/maskable), 192/512 PNGs, 180×180 apple-touch, favicon, and a theme/background color pair for the manifest.
- The app is **theme-aware** (light/dark via `next-themes`) — provide both if the icon/splash should differ.
- Existing visual language: Google-Classroom-inspired class cards (colored banners, monogram avatars) in `features/teacher` and `features/student`; shadcn/Radix components in `components/ui`; Tailwind tokens in `tailwind.config.ts` + `app/globals.css`.

---

## 9. Notes

- This is a **snapshot** taken from the monorepo — it won't receive upstream changes automatically. Coordinate with the core team if the API contract changes.
- No `node_modules`, `.next`, or lockfile is included — run `npm install` fresh.
- The backend, database, and any `*-sim` preview mockups from the main repo are intentionally **not** included; this is client-only.
