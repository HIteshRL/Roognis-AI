'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { BrainCircuit } from 'lucide-react'
import { useAuthStore } from '@/lib/stores/auth.store'
import { DEMO_MODE, ensureDemoSession } from '@/lib/auth/demo'

/**
 * Route gate for the custom-JWT flow. Waits for the persisted auth store to
 * hydrate. In demo mode (default for the MVP) it transparently provisions a
 * demo student session instead of bouncing to /login.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const token = useAuthStore((s) => s.token)
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => setHydrated(true), [])

  useEffect(() => {
    if (!hydrated || token) return
    if (DEMO_MODE) {
      ensureDemoSession()
      return
    }
    router.replace('/login')
  }, [hydrated, token, router])

  if (!hydrated || !token) return <PortalBooting />
  return <>{children}</>
}

function PortalBooting() {
  return (
    <div className="relative flex h-screen w-full flex-col items-center justify-center overflow-hidden bg-background">
      <div className="aurora" aria-hidden />
      <div className="relative flex flex-col items-center gap-5">
        <div className="relative">
          <div className="absolute inset-0 animate-ping rounded-2xl bg-primary/30" />
          <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 ring-1 ring-primary/30">
            <BrainCircuit className="h-7 w-7 text-primary" />
          </div>
        </div>
        <div className="flex flex-col items-center gap-1.5">
          <p className="text-sm font-medium text-foreground">Preparing your learning space</p>
          <div className="flex gap-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
          </div>
        </div>
      </div>
    </div>
  )
}
