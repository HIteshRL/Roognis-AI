'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Activity,
  AlertTriangle,
  BookOpen,
  Flame,
  GraduationCap,
  LinkIcon,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { parentApi } from '@/lib/api/parent'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

function Stat({ icon: Icon, label, value }: { icon: typeof Flame; label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div>
          <div className="text-lg font-semibold leading-none">{value}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  )
}

function ChildOverview({ studentId }: { studentId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['parent', 'overview', studentId],
    queryFn: () => parentApi.getChildOverview(studentId),
    select: (r) => r.data,
  })

  if (isLoading) return <div className="p-4 text-sm text-muted-foreground">Loading…</div>
  if (!data) return null

  return (
    <div className="mt-3 flex flex-col gap-4 border-t pt-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat icon={TrendingUp} label="Avg mastery" value={`${Math.round(data.average_mastery)}%`} />
        <Stat icon={Sparkles} label="Mastered" value={data.mastered_count} />
        <Stat icon={Flame} label="Day streak" value={data.engagement_streak} />
        <Stat icon={Activity} label="Sessions" value={data.total_sessions} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
            <Sparkles className="h-4 w-4 text-green-500" /> Strengths
          </h4>
          {data.strengths.length === 0 ? (
            <p className="text-xs text-muted-foreground">No mastered concepts yet.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {data.strengths.map((s) => (
                <Badge key={s} variant="secondary">{s}</Badge>
              ))}
            </div>
          )}
        </div>
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
            <AlertTriangle className="h-4 w-4 text-orange-400" /> Needs attention
          </h4>
          {data.weak_areas.length === 0 ? (
            <p className="text-xs text-muted-foreground">No active gaps. 🎉</p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {data.weak_areas.map((w) => (
                <div key={w.concept} className="flex items-center justify-between text-sm">
                  <span>{w.concept}</span>
                  <Badge variant="outline" className="text-[10px] capitalize">{w.severity}</Badge>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div>
        <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
          <BookOpen className="h-4 w-4 text-primary" /> Recent activity
        </h4>
        {data.recent_activity.length === 0 ? (
          <p className="text-xs text-muted-foreground">No recent questions.</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {data.recent_activity.map((a, i) => (
              <div key={i} className="flex items-center gap-2 rounded-md bg-muted/50 px-3 py-2 text-sm">
                <span className="flex-1 truncate">{a.question}</span>
                {a.subject && <Badge variant="outline" className="text-[10px]">{a.subject}</Badge>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function ParentPortalView() {
  const qc = useQueryClient()
  const [code, setCode] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const { data: children = [], isLoading } = useQuery({
    queryKey: ['parent', 'children'],
    queryFn: () => parentApi.getChildren(),
    select: (r) => r.data,
  })

  const link = useMutation({
    mutationFn: () => parentApi.linkChild(code.trim().toUpperCase()),
    onSuccess: (r) => {
      toast.success(`Linked to ${r.data.username}`)
      setCode('')
      qc.invalidateQueries({ queryKey: ['parent', 'children'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Parent Portal</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Follow your child&apos;s learning progress. Ask them to share their family access code.
        </p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2 text-sm font-medium">
            <LinkIcon className="h-4 w-4 text-primary" /> Link a child
          </div>
          <div className="flex flex-1 gap-2">
            <Input
              placeholder="Enter family access code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              className="font-mono uppercase"
              maxLength={16}
            />
            <Button disabled={!code.trim() || link.isPending} onClick={() => link.mutate()}>
              Link
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : children.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <GraduationCap className="h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No children linked yet. Enter a family access code above.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {children.map((c) => (
            <Card key={c.link_id}>
              <CardContent className="p-4">
                <button
                  className="flex w-full items-center gap-3 text-left"
                  onClick={() => setExpanded(expanded === c.student_id ? null : c.student_id)}
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                    {c.username.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-semibold">{c.username}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {c.grade ? `Grade ${c.grade}` : c.email}
                    </div>
                  </div>
                  <Badge variant="secondary">{expanded === c.student_id ? 'Hide' : 'View'}</Badge>
                </button>
                {expanded === c.student_id && <ChildOverview studentId={c.student_id} />}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
