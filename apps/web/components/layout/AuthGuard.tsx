'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/stores/auth.store'

/**
 * Client-side route guard for the custom-JWT auth flow. Waits for the persisted
 * auth store to hydrate, then redirects to /login when there is no token.
 * Replaces the previous Clerk server middleware (which couldn't read the
 * localStorage-persisted JWT anyway).
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const token = useAuthStore((s) => s.token)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => setHydrated(true), [])

  useEffect(() => {
    if (hydrated && !token) router.replace('/login')
  }, [hydrated, token, router])

  if (!hydrated || !token) return null
  return <>{children}</>
}
