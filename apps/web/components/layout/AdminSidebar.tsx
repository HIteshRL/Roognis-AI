'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { UserButton } from '@clerk/nextjs'
import {
  BookOpen,
  BrainCircuit,
  Database,
  FileText,
  LayoutDashboard,
  Search,
  Upload,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'

const navItems = [
  { href: '/admin', icon: LayoutDashboard, label: 'Overview', exact: true },
  { href: '/admin/library', icon: BookOpen, label: 'Knowledge Library' },
  { href: '/admin/upload', icon: Upload, label: 'Upload Documents' },
  { href: '/admin/search', icon: Search, label: 'Search Playground' },
  { href: '/admin/chunks', icon: FileText, label: 'Chunk Browser' },
  { href: '/admin/vector', icon: Database, label: 'Vector Stats' },
]

export function AdminSidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex h-full w-[220px] flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-14 items-center gap-2 px-4">
        <BrainCircuit className="h-6 w-6 text-primary" />
        <div className="flex flex-col leading-none">
          <span className="text-sm font-semibold">Roognis AI</span>
          <span className="text-xs text-muted-foreground">Admin Panel</span>
        </div>
      </div>
      <Separator />
      <ScrollArea className="flex-1 py-2">
        <nav className="flex flex-col gap-0.5 px-2">
          {navItems.map(({ href, icon: Icon, label, exact }) => {
            const isActive = exact ? pathname === href : pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-accent text-accent-foreground'
                    : 'text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground'
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            )
          })}
        </nav>
      </ScrollArea>
      <Separator />
      <div className="flex items-center gap-3 p-4">
        <UserButton afterSignOutUrl="/login" />
        <Link href="/dashboard" className="text-xs text-muted-foreground hover:text-foreground">
          ← Back to app
        </Link>
      </div>
    </aside>
  )
}
