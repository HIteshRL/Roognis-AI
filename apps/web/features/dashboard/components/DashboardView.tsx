'use client'

import Link from 'next/link'
import { BrainCircuit, MessageSquare, TrendingUp } from 'lucide-react'
import { useAuthStore } from '@/lib/stores/auth.store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const quickActions = [
  {
    icon: MessageSquare,
    label: 'Start a conversation',
    description: 'Ask anything and get instant AI-powered answers.',
    href: '/chat',
    cta: 'Open chat',
  },
]

export function DashboardView() {
  const user = useAuthStore((s) => s.user)

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
          <BrainCircuit className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-semibold">
            Good {greeting()}, {user?.username ?? 'learner'}
          </h1>
          <p className="text-sm text-muted-foreground">Your learning OS is ready.</p>
        </div>
      </div>

      {/* Stats placeholder */}
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: 'Conversations', value: '—', icon: MessageSquare },
          { label: 'Messages', value: '—', icon: TrendingUp },
          { label: 'Days active', value: '1', icon: BrainCircuit },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardContent className="flex items-center gap-4 pt-6">
              <div className="rounded-lg bg-muted p-2">
                <Icon className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-sm text-muted-foreground">{label}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2">
        {quickActions.map(({ icon: Icon, label, description, href, cta }) => (
          <Card key={label} className="group transition-colors hover:border-primary/30">
            <CardHeader>
              <div className="mb-1 inline-flex rounded-lg bg-primary/10 p-2 w-fit">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <CardTitle className="text-base">{label}</CardTitle>
              <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button size="sm" asChild>
                <Link href={href}>{cta}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function greeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 18) return 'afternoon'
  return 'evening'
}
