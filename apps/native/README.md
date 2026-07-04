# Roognis Mobile (Android) — Expo / React Native

Native mobile client for the Roognis AI tutor. It talks to the **hosted FastAPI
backend** over HTTPS and reuses the exact same auth + API contract as the web app.

This is a **standalone** project — it is intentionally *not* part of the root npm
workspace (`apps/web` + `packages/*`), so it installs and builds independently
without touching the web build.

## What's inside (this iteration)

| Feature | Screen | Backend |
|---|---|---|
| Email/password auth (JWT) | `app/(auth)/sign-in`, `sign-up` | `POST /api/v1/auth/login` · `register` |
| Student dashboard | `app/(tabs)/index` | `/student/profile` · `/student/analytics` · `/student/recommendations` |
| Subject portal (syllabus → chapter → chat) | `app/(tabs)/subjects` | `/chat/subjects` · `/chat/subjects/{s}/chapters` |
| AI inference (streaming chat) | `app/(tabs)/chat` | `POST /api/v1/chat` (SSE) |
| Profile + learning style + sign out | `app/(tabs)/profile` | `/student/profile` |

> Not yet on mobile: default generated images / on-demand video, and the
> Parent/Teacher portals + school-admin syllabus upload. Those are the next builds.

## Tech

- **Expo SDK 52** / React Native 0.76 / **Expo Router v4** (file-based, mirrors Next.js App Router)
- **TanStack Query v5** (server state) + **Zustand** (auth + chat state)
- **expo-secure-store** — encrypted JWT storage (Android Keystore)
- **expo/fetch** — real streaming `ReadableStream` for SSE-over-POST (RN's global fetch can't stream)
- **react-native-markdown-display** — renders the tutor's markdown answers

---

## 1. Prerequisites

- **Node.js 20+**
- A running/deployed **Roognis backend** the phone can reach (see Networking below)
- To produce an `.apk`, pick ONE:
  - **EAS Build (cloud — recommended, no local Android SDK):** a free [Expo account](https://expo.dev)
  - **Local build:** Android Studio + Android SDK + **JDK 17**

## 2. Install & configure

```bash
cd apps/native
npm install
cp .env.example .env
# edit .env → set EXPO_PUBLIC_API_URL to your backend
```

`EXPO_PUBLIC_API_URL` rules of thumb:
- Android emulator → `http://10.0.2.2:8000` (10.0.2.2 = the host machine's localhost)
- Physical device on same Wi-Fi → `http://<your-LAN-ip>:8000` (e.g. `http://192.168.1.20:8000`)
- Deployed backend → `https://api.roognis.ai`

## 3. Run in development

```bash
npx expo start
```

Then either:
- Press **`a`** to open an Android emulator, or
- Scan the QR code with **Expo Go** (Play Store) on a physical device.

Hot reload works. Sign up once, then land on the dashboard.

## 4. Build the installable `.apk`

### Option A — EAS Build (cloud, easiest)

```bash
npm install -g eas-cli
eas login
eas build -p android --profile preview
```

`eas.json`'s `preview` profile is configured to output an **APK** (not AAB). When
the build finishes, EAS gives you a URL to download `app-preview.apk`. Set the
production API URL in `eas.json` (`build.preview.env.EXPO_PUBLIC_API_URL`) first.

### Option B — Local build (needs Android SDK + JDK 17)

```bash
# one-time: generates the native android/ project
npx expo prebuild -p android

# build a debug apk
cd android
./gradlew assembleDebug        # Windows: .\gradlew.bat assembleDebug
```

Output: `android/app/build/outputs/apk/debug/app-debug.apk`
Install on a connected device: `adb install app-debug.apk`

> For a release APK: `./gradlew assembleRelease` (requires a signing keystore —
> see [Expo docs on app signing](https://docs.expo.dev/app-signing/local-credentials/)).

## 5. Networking & backend notes

- The device/emulator must be able to reach `EXPO_PUBLIC_API_URL`. `localhost`
  from the phone is the *phone*, not your PC — use `10.0.2.2` (emulator) or your
  LAN IP (device).
- Native apps don't send a browser `Origin`, so CORS usually isn't the blocker;
  reachability + the JWT are. If you front the API with a proxy, make sure it
  doesn't buffer the SSE stream (`text/event-stream`).
- Auth is the **same custom JWT** the web app uses (`/auth/login` → `{ user, token }`),
  stored encrypted via SecureStore and sent as `Authorization: Bearer <token>`.

## Project structure

```
apps/native/
├── app/                     # Expo Router routes
│   ├── _layout.tsx          # providers + auth-gate redirect
│   ├── index.tsx            # cold-start redirect (auth vs tabs)
│   ├── (auth)/              # sign-in, sign-up
│   └── (tabs)/              # index(Home) · subjects · chat · profile
├── src/
│   ├── api/                 # client (token injection) · auth · chat(SSE) · student
│   ├── hooks/useChatStream  # send + consume the SSE stream
│   ├── store/               # auth (SecureStore-persisted) · chat
│   ├── components/          # Screen · MessageBubble · ChatComposer · StatCard · ui
│   ├── theme/colors.ts      # palette / spacing / radius
│   └── types.ts             # vendored DTOs (swap for @roognis/shared later)
├── app.json · eas.json · metro/babel/tsconfig
```

## Troubleshooting

- **`TextDecoder is not defined`** during streaming: Expo SDK 52 provides it, but
  if a custom runtime strips it, add `import 'text-encoding-polyfill'` at the top
  of `app/_layout.tsx` (and `npm i text-encoding-polyfill`).
- **Version mismatch warnings**: run `npx expo install --fix` to align native deps
  to the installed SDK.
- **Blank screen after login**: confirm `EXPO_PUBLIC_API_URL` is reachable from the
  device (`curl` it from the same network) and the backend is running.
```
