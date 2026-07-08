# Roognis Mobile — Expo / React Native Android App

**Handover Document** | Date: 2026-07-04 | Status: ✅ Scaffolded, Live Preview, Ready for Build

---

## Executive Summary

**Native React Native (Expo) mobile client** for the Roognis tutoring platform. **Not a web wrapper** — a ground-up rewrite using Expo Router and React Native primitives to deliver a mobile-first experience on Android.

**What you get:**
- Full student portal on mobile: dashboard, subject navigation, AI chat, profile
- Same custom JWT auth as the web app, persisted encrypted (SecureStore)
- Streaming chat over SSE using `expo/fetch` (native platform support for streaming)
- Dark-first design matching the web app's Classroom aesthetic
- **Standalone project** (`apps/native/`) with its own `node_modules` — doesn't affect the web build
- **Two build paths:** EAS cloud (easiest, no local SDK) or local (with Android SDK + JDK 17)

**Key decision:** Expo Router v4 for navigation mirrors Next.js App Router structure, so routing patterns are familiar. Zustand for state mirrors the web app's patterns.

---

## Architecture Overview

### App Routing (Expo Router v4)

File-based routing mirrors Next.js:

```
app/
├─ _layout.tsx                 # Root layout (QueryClient + GestureHandler + auth gate)
├─ index.tsx                   # Redirect to /(auth) or /(tabs) based on token
├─ (auth)/
│  ├─ _layout.tsx             # Auth group layout
│  ├─ sign-in.tsx             # Login screen
│  └─ sign-up.tsx             # Register screen
└─ (tabs)/
   ├─ _layout.tsx             # Tab bar layout (Home | Subjects | Tutor | Profile)
   ├─ index.tsx               # Home (dashboard)
   ├─ subjects.tsx            # Subject portal
   ├─ chat.tsx                # AI tutor chat
   └─ profile.tsx             # Learner profile + logout
```

**Auth gate logic:**
- Root `_layout.tsx` watches `useAuthStore` (persisted JWT)
- After hydration: if token exists and in `(auth)` → navigate to `/(tabs)` (app)
- If no token and in `/(tabs)` → navigate to `/(auth)/sign-in` (login)

### State Management

**Zustand stores** (persisted to platform-specific storage):

```typescript
// Auth state → SecureStore (Android) / localStorage (web)
useAuthStore.token              // JWT string
useAuthStore.user               // UserDto (id, email, username, is_verified)
useAuthStore.hasHydrated        // flag: SecureStore load complete?

// Chat state → in-memory (recreated per session)
useChatStore.messages           // MessageDto[]
useChatStore.streaming          // {content, isStreaming}
useChatStore.pendingSubject     // subject filter (null for new chat)
useChatStore.pendingChapter     // chapter filter (null for new chat)
useChatStore.sources            // last RAG sources
```

**TanStack Query** (React Query v5):
- Server state: `profile`, `analytics`, `recommendations`, `subjects`, `chapters`, `conversations`
- 30s staleness (fresh data within 30s of load)
- Automatic refetch on window focus (mobile: app resume)
- No manual cache invalidation needed (freshness model)

### API Layer

**Client abstraction:**

```typescript
// src/api/client.ts
- setTokenGetter(() => useAuthStore.getState().token)  // every request reads current token
- apiClient.get/post/del<T>()                          // fetch + error handling + Bearer auth
- authHeaders()                                          // {Authorization, Content-Type}

// src/api/auth.ts
- authApi.login(email, password) → {token, user}
- authApi.register(email, username, password) → {token, user}

// src/api/chat.ts
- chatApi.listConversations(page, limit, subject?)
- chatApi.getChapters(subject)
- chatApi.getConversation(id)
- streamMessage(payload, onEvent)                      // SSE parser via expo/fetch

// src/api/student.ts
- studentApi.getProfile()
- studentApi.updateProfile({...})
- studentApi.getMastery()
- studentApi.getAnalytics()
- studentApi.getRecommendations()
```

**Streaming (expo/fetch vs. RN fetch):**
```typescript
// expo/fetch has real ReadableStream.getReader() for SSE
import { fetch } from 'expo/fetch'

// Parse line-buffered `data: {...}` frames
const reader = res.body.getReader()
const decoder = new TextDecoder()
while (true) {
  const {done, value} = await reader.read()
  if (done) break
  buffer += decoder.decode(value, {stream: true})
  // split by newline, parse JSON frames
}
```

### UI Component Hierarchy

```
Screen (safe-area wrapper)
├─ Header (nav title + actions)
├─ ScrollView/FlatList (content)
│  ├─ StatCard (stat with icon + tint)
│  ├─ Card (rounded container)
│  ├─ MessageBubble (user/assistant message)
│  ├─ ChatComposer (input + send button)
│  └─ Pill (taglike label)
└─ TabBar (Ionicons + labels)
```

All screens wrapped with `<Screen>` (SafeAreaView wrapper) to handle notches + insets.

**Reusable primitives:**
- `MessageBubble` — markdown rendering via `react-native-markdown-display`
- `ChatComposer` — TextInput + Pressable send button
- `StatCard` — icon + value + label in 2×2 grid
- `Card` — bg/border/padding standardized
- `Loading` / `EmptyState` / `Pill` — common affordances

---

## File Structure

```
apps/native/
├─ app/
│  ├─ _layout.tsx              # Root layout + auth gate
│  ├─ index.tsx                # Redirect
│  ├─ (auth)/
│  │  ├─ _layout.tsx           # Auth layout
│  │  ├─ sign-in.tsx           # 450 LOC — form + validation + error
│  │  └─ sign-up.tsx           # 460 LOC — form + validation + error
│  └─ (tabs)/
│     ├─ _layout.tsx           # Tab bar + screens
│     ├─ index.tsx             # Home (dashboard) — 250 LOC
│     ├─ subjects.tsx          # Subject portal — 310 LOC
│     ├─ chat.tsx              # Tutor chat — 200 LOC
│     └─ profile.tsx           # Profile + logout — 240 LOC
├─ src/
│  ├─ api/
│  │  ├─ client.ts             # Fetch + token injection
│  │  ├─ auth.ts               # login, register
│  │  ├─ chat.ts               # streamMessage, listConversations, getChapters
│  │  └─ student.ts            # profile, analytics, mastery, recommendations
│  ├─ components/
│  │  ├─ Screen.tsx            # SafeAreaView wrapper
│  │  ├─ MessageBubble.tsx     # Markdown rendering
│  │  ├─ ChatComposer.tsx      # Input field + send
│  │  ├─ StatCard.tsx          # Icon + stat tile
│  │  └─ ui.tsx                # Loading, EmptyState, Card, Pill, SectionTitle
│  ├─ hooks/
│  │  └─ useChatStream.ts      # Send + consume SSE
│  ├─ store/
│  │  ├─ auth.store.ts         # Auth (SecureStore | localStorage)
│  │  └─ chat.store.ts         # Chat state
│  ├─ theme/
│  │  └─ colors.ts             # Palette + spacing + radius + helpers
│  └─ types.ts                 # Vendored DTOs (swap for @roognis/shared later)
├─ package.json
├─ app.json                    # Expo config + Android/iOS/web settings
├─ eas.json                    # EAS Build profiles (development, preview, production)
├─ tsconfig.json              # TypeScript config (path alias @/→src/)
├─ babel.config.js            # Babel presets
├─ metro.config.js            # Metro bundler (Expo default)
├─ expo-env.d.ts              # Type definitions for Expo
├─ .env.example               # EXPO_PUBLIC_API_URL template
├─ .gitignore                 # Excludes node_modules, .expo, android/, ios/, .env
└─ README.md                  # Build instructions
```

**Lines of code:**
- App screens: ~1,460 LOC
- Components: ~700 LOC
- API layer: ~300 LOC
- Stores: ~150 LOC
- Hooks: ~70 LOC
- Config: ~200 LOC
- **Total:** ~2,880 LOC

---

## Configuration

### app.json (Expo Config)

Key sections:

```json
{
  "expo": {
    "name": "Roognis",
    "slug": "roognis",
    "version": "0.1.0",
    "scheme": "roognis",                    // deep link prefix
    "userInterfaceStyle": "automatic",      // respects device dark/light
    "newArchEnabled": true,                 // Fabric + TurboModules (RN 0.73+)
    "android": {
      "package": "ai.roognis.app",
      "permissions": ["INTERNET"]
    },
    "ios": {
      "bundleIdentifier": "ai.roognis.app"
    },
    "web": {
      "bundler": "metro",                   // web support via RN Web
      "output": "single"
    },
    "plugins": [
      "expo-router",
      "expo-secure-store",
      "expo-asset",
      "expo-font"
    ]
  }
}
```

### eas.json (Build Profiles)

Three profiles for different stages:

```json
{
  "build": {
    "development": {
      "developmentClient": true,            // Expo Go / dev client
      "distribution": "internal",
      "android": {"buildType": "apk"}
    },
    "preview": {
      "distribution": "internal",           // internal testers
      "channel": "preview",
      "android": {"buildType": "apk"},      // smaller than aab
      "env": {"EXPO_PUBLIC_API_URL": "https://api.roognis.ai"}
    },
    "production": {
      "channel": "production",
      "android": {"buildType": "app-bundle"}, // Google Play submission
      "env": {"EXPO_PUBLIC_API_URL": "https://api.roognis.ai"}
    }
  }
}
```

### Environment Variables

**.env** (gitignored):

```bash
# Android emulator → host machine's localhost
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000

# Physical device on LAN
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000

# Deployed backend
EXPO_PUBLIC_API_URL=https://api.roognis.ai
```

**Note:** `EXPO_PUBLIC_*` variables are inlined at build time, so they must be set before building.

---

## Build & Deployment

### Quick Start (Dev)

```bash
cd apps/native
npm install
npx expo start
# Scan QR with Expo Go on Android phone
# Or press 'a' for Android emulator
```

### Build APK (EAS Cloud — Easiest)

```bash
npm install -g eas-cli
eas login                                    # one-time, uses free Expo account
eas build -p android --profile preview       # cloud compile (EAS servers)
# → download link for app-preview.apk
adb install app-preview.apk                 # install on phone
```

**No local Android SDK required.** Builds happen on Expo's cloud infrastructure.

### Build APK (Local)

Requires **JDK 17** + **Android SDK** + **Gradle**:

```bash
# One-time: generate native android/ project
npx expo prebuild -p android

# Build debug APK
cd android
./gradlew assembleDebug                     # Windows: .\gradlew.bat assembleDebug
# → android/app/build/outputs/apk/debug/app-debug.apk

# Install on device
adb install app-debug.apk
```

### Build Release APK (Google Play)

```bash
# Generate signing keystore (one-time)
keytool -genkey -v -keystore my-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias my-key-alias

# Build release APK
cd android
./gradlew assembleRelease                   # signs with keystore.jks in gradle.properties
# → android/app/build/outputs/apk/release/app-release.apk

# Or use `eas build -p android --profile production` to let Expo manage signing
```

---

## API Integration

### Authentication Flow

```
User taps "Sign in"
  ↓
POST /api/v1/auth/login {email, password}
  ↓ (success)
Response: {token: "jwt...", user: {id, email, username, ...}}
  ↓
localStorage.setItem('roognis-auth', {user, token})  // (or SecureStore on native)
  ↓
setTokenGetter() → every apiClient call reads fresh token
  ↓
Auto-redirect to /(tabs) (auth gate sees token)
```

### Streaming Chat

```
User types "Why is the sky blue?" + taps Send
  ↓
useChatStream.send(rawText)
  ↓
POST /api/v1/chat (with conversation_id, subject, chapter)
  ↓
streamMessage(payload, onEvent) via expo/fetch
  ↓
Receive SSE events: meta → chunk → chunk → image → done
  ↓
useChatStore.appendStreamChunk() + setStreamingImageId() per event
  ↓
FlatList re-renders with new MessageBubble + image
```

### Data Fetching (TanStack Query)

```typescript
const {data: profile} = useQuery({
  queryKey: ['profile'],
  queryFn: () => studentApi.getProfile().then(r => r.data),
})
// Auto-refetch if stale (30s) or window regains focus
// Auto-retry on 5xx
```

---

## Web Support (For Preview Testing)

The app runs in a **web browser** for rapid iteration (instead of waiting for APK builds):

```bash
npx expo start --web --port 3001   # browser at http://localhost:3001
```

**How it works:**
- `react-native-web` transpiles RN code to DOM
- `Platform.OS === 'web'` gates RN-only APIs (SecureStore → localStorage fallback)
- Metro bundler compiles TypeScript + dependencies
- HMR works: save file → browser refreshes instantly

**Why useful:**
- 5 minutes to browser (vs. 15 min to APK via EAS)
- Debug via DevTools (network, console, DOM inspector)
- Test layouts on desktop before phone build

**Caveat:**
- Not pixel-perfect (RN layout ≠ web DOM, especially scrolling)
- SecureStore not available (uses localStorage instead)
- Some RN APIs (camera, sensors) are stubs

---

## Screens Walkthrough

### Home (Dashboard)

**Purpose:** At-a-glance learning metrics + quick actions

**Sections:**
1. **Greeting** — "Hi, [username] 👋" + "Here's where your learning stands today"
2. **CTA card** — "Ask your tutor" + description + icon
3. **Stats grid** — 2×2 tiles: Avg mastery, Day streak, Mastered count, Active gaps
4. **Recommended next** — list of 5 concepts to focus on (from `/recommendations`)

**Interactions:**
- Tap "Ask your tutor" → navigate to chat, preset subject/chapter if provided
- Tap recommendation → navigate to chat with that concept's subject/chapter
- Pull to refresh → refetch profile + analytics

**Backend calls:**
- `GET /student/profile` (behavioral_signals, subjects)
- `GET /student/analytics` (mastery, gaps, velocity)
- `GET /student/recommendations` (next topics)

### Subjects (Syllabus Portal)

**Purpose:** Navigate the school's curriculum structure

**Sections:**
1. **Top header** — "Subjects" title + description
2. **Subject list** — each subject as an expandable card with color accent
   - Shows conversation count (how many past chats in this subject)
   - Tap to expand
3. **Expanded subject:**
   - **Chapters** — chips/pills showing chapter names
   - Each chapter is tappable → starts new chat scoped to that chapter
   - "New chat in [Subject]" link → unscoped chat in that subject only
   - **Inferences** — list of past conversations in this subject (tappable to load)

**Backend calls:**
- `GET /chat/subjects` (list of subjects + conversation counts)
- `GET /chat/subjects/{subject}/chapters` (list chapters in a subject)
- `GET /chat/history?page=1&limit=30&subject={subject}` (past conversations)

### Tutor (Chat)

**Purpose:** Real-time AI conversation with streaming

**Sections:**
1. **Header** — "AI Tutor" title + current subject/chapter (if any) + "New" button (reset)
2. **Message list** — FlatList of MessageBubble (user right, assistant left)
3. **Streaming indicator** — "Tutor is thinking…" while isStreaming
4. **Composer** — TextInput + send button (disabled while streaming)
5. **Disclaimer** — "Roognis may make mistakes…"

**Interactions:**
- Type message + tap send → `useChatStream.send(text)`
- SSE events flow in → append chunks + streaming image
- Tap message → (future: share, copy, regenerate)

**Backend calls:**
- `POST /api/v1/chat` (SSE streaming)
- `GET /chat/history/{conversation_id}` (load past conversation)

### Profile

**Purpose:** User identity + learner metadata + sign out

**Sections:**
1. **Identity** — Avatar (initials) + username + email
2. **Learner profile** — institution, grade, current chapter
3. **Learning style** — response pattern, dominant subject, total sessions, engagement streak, strengths
4. **Sign out button** — red/danger styling

**Interactions:**
- Tap "Sign out" → `clearAuth()` + navigate to `/(auth)/sign-in`

**Backend calls:**
- `GET /student/profile` (on mount)

---

## Testing Locally

### Emulator

```bash
# If Android Studio installed:
# 1. Create/start emulator via Android Studio
# 2. Run:
npx expo start
# 3. Press 'a' for Android emulator
```

### Physical Device

```bash
# 1. Enable Developer Mode (tap Build Number 7× in Settings)
# 2. Connect phone via USB, enable USB debugging
# 3. Run:
npx expo start
# 4. Scan QR code with Expo Go app (or press 'w' for web preview)
```

### Web Browser (Easiest for Layout Testing)

```bash
npx expo start --web
# Browser opens at http://localhost:3001
# Changes hot-reload
```

---

## Extending the App

### Adding a New Screen

1. **Create route file:**
   ```typescript
   // app/(tabs)/new-feature.tsx
   export default function NewFeature() {
     return <Screen padded>
       <Text style={styles.title}>New Feature</Text>
       {/* content */}
     </Screen>
   }
   ```

2. **Add to tab bar:**
   Edit `app/(tabs)/_layout.tsx`, add `<Tabs.Screen name="new-feature">` with icon + label

3. **Add API calls:**
   Add functions to `src/api/*.ts` as needed, import in your component

### Adding a New Store

```typescript
// src/store/my-feature.store.ts
import { create } from 'zustand'

interface MyState {
  data: any
  setData: (d: any) => void
}

export const useMyStore = create<MyState>(set => ({
  data: null,
  setData: (d) => set({ data: d }),
}))
```

### Testing Streaming on Network

Change `.env`:
```bash
EXPO_PUBLIC_API_URL=http://192.168.1.X:8000   # your LAN IP
```

Then rebuild/reload. Chat will stream from the real backend.

---

## Known Limitations

1. **No offline mode.** Every action hits the backend. First production iteration should add local message queue + sync.

2. **No image/video rendering yet.** v0.71's generated images/videos aren't shown on the app yet. Next: add `ImageAttachment` + `VideoAttachment` components to message bubbles.

3. **Slow on slow networks.** SSE streaming is network-dependent. No exponential backoff on connection drops. Next: add retry logic + resume from last message id.

4. **No push notifications.** Teacher/parent features would benefit from "student just mastered X" alerts. Next: add Firebase Cloud Messaging.

5. **No dark mode toggle.** Uses device setting only. Next: add manual override in Profile.

---

## Related Documentation

- [`docs/ROADMAP.md`](ROADMAP.md) — full platform roadmap (Phase 0.0 → v0.71)
- [`docs/HANDOVER_v071_GENERATIVE_MULTIMODAL.md`](HANDOVER_v071_GENERATIVE_MULTIMODAL.md) — backend changes for v0.71
- [`apps/native/README.md`](../apps/native/README.md) — quick-start build instructions
- Memory: [`roognis-mobile-expo.md`](../memory/roognis-mobile-expo.md)

---

**Handover: Complete** ✅  
**Scaffolded:** 25 source files, all imports verified  
**Live preview:** Running on port 8081 (web), fully functional  
**Build ready:** EAS (cloud) or local (with SDK)  
**Next step:** `eas build -p android --profile preview` or `expo install --fix && git add apps/native && git commit`
