'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { UserButton } from '@clerk/nextjs'
import {
  AlertTriangle,
  BookOpen,
  BrainCircuit,
  BarChart3,
  ClipboardCheck,
  GitBranch,
  LayoutDashboard,
  Lightbulb,
  Map,
  MessageSquare,
  Network,
  Settings,
  Sparkles,
  User,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'

const mainNavItems = [
  { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/chat', icon: MessageSquare, label: 'Chat' },
  { href: '/profile', icon: User, label: 'Profile' },
  { href: '/settings', icon: Settings, label: 'Settings' },
  { href: '/admin', icon: BookOpen, label: 'Admin' },
]

const learningNavItems = [
  { href: '/student', icon: BrainCircuit, label: 'Learning' },
  { href: '/student/mastery', icon: BarChart3, label: 'Mastery' },
  { href: '/student/gaps', icon: AlertTriangle, label: 'Weak Areas' },
  { href: '/student/recommendations', icon: Lightbulb, label: 'Next Up' },
  { href: '/student/learning-path', icon: Map, label: 'Learning Path' },
  { href: '/student/skills', icon: Sparkles, label: 'Skills' },
  { href: '/student/quiz', icon: ClipboardCheck, label: 'Quizzes' },
  { href: '/student/graph', icon: Network, label: 'Knowledge Map' },
  { href: '/student/timeline', icon: GitBranch, label: 'Timeline' },
  { href: '/student/statistics', icon: BarChart3, label: 'Statistics' },
]

export function Sidebar() {
  const pathname = usePathname()

  const isActive = (href: string) =>
    href === '/student'
      ? pathname === '/student'
      : href !== '/dashboard' && pathname.startsWith(href)
      ? true
      : pathname === href

  return (
    <aside className="flex h-full w-[220px] flex-col border-r border-sidebar-border bg-sidebar">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 px-4">
        <BrainCircuit className="h-6 w-6 text-primary" />
        <span className="text-lg font-semibold tracking-tight">Roognis</span>
      </div>
      <Separator />

      {/* Navigation */}
      <ScrollArea className="flex-1 py-2">
        <nav className="flex flex-col gap-0.5 px-2">
          {mainNavItems.map(({ href, icon: Icon, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive(href)
                  ? 'bg-accent text-accent-foreground'
                  : 'text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          ))}

          <div className="mt-3 mb-1 px-3">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
              Learning Engine
            </span>
          </div>

          {learningNavItems.map(({ href, icon: Icon, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive(href)
                  ? 'bg-accent text-accent-foreground'
                  : 'text-sidebar-foreground/70 hover:bg-accent/50 hover:text-sidebar-foreground'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          ))}
        </nav>
      </ScrollArea>

      {/* User */}
      <Separator />
      <div className="flex items-center gap-3 p-4">
        <UserButton afterSignOutUrl="/login" />
        <span className="text-sm text-muted-foreground">Account</span>
      </div>
    </aside>
  )
}
