'use client'

import { useRouter } from 'next/navigation'
import { LogOut } from 'lucide-react'
import { useAuthStore } from '@/lib/stores/auth.store'

/** Account chip + logout, replacing Clerk's <UserButton> for the custom-JWT flow. */
export function AccountButton() {
  const router = useRouter()
  const user = useAuthStore((s) => s.user)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  const logout = () => {
    clearAuth()
    router.replace('/login')
  }

  return (
    <div className="flex w-full items-center gap-2">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
        {(user?.username ?? 'U').slice(0, 2).toUpperCase()}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{user?.username ?? 'Account'}</div>
      </div>
      <button
        type="button"
        onClick={logout}
        title="Log out"
        aria-label="Log out"
        className="text-muted-foreground transition-colors hover:text-foreground"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  )
}
