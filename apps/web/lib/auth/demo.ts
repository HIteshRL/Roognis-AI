import { authApi } from '@/lib/api/auth'
import { useAuthStore } from '@/lib/stores/auth.store'

/**
 * No-auth MVP: transparently provision a demo student session so the portal
 * opens without a login screen. Backend JWT auth stays intact — we just
 * auto-acquire a token for a fixed demo account (login first, register on
 * first run). Concurrent callers share one in-flight request.
 *
 * Toggle off by setting NEXT_PUBLIC_DEMO_MODE=false (falls back to real login).
 */
export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE !== 'false'

const DEMO_EMAIL = process.env.NEXT_PUBLIC_DEMO_EMAIL ?? 'demo.student@roognis.ai'
const DEMO_USERNAME = process.env.NEXT_PUBLIC_DEMO_USERNAME ?? 'demo_student'
const DEMO_PASSWORD = process.env.NEXT_PUBLIC_DEMO_PASSWORD ?? 'RoognisDemo!2026'

let inflight: Promise<boolean> | null = null

export function ensureDemoSession(): Promise<boolean> {
  if (useAuthStore.getState().token) return Promise.resolve(true)
  if (inflight) return inflight

  inflight = (async () => {
    // The demo account usually already exists → try login, then register.
    try {
      const res = await authApi.login(DEMO_EMAIL, DEMO_PASSWORD)
      useAuthStore.getState().setAuth(res.data.user, res.data.token)
      return true
    } catch {
      try {
        const res = await authApi.register(DEMO_EMAIL, DEMO_USERNAME, DEMO_PASSWORD, 'student')
        useAuthStore.getState().setAuth(res.data.user, res.data.token)
        return true
      } catch {
        return false
      }
    } finally {
      inflight = null
    }
  })()

  return inflight
}
