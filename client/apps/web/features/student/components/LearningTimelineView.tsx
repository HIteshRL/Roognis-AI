'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { studentApi } from '@/lib/api/student'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight, MessageSquare, AlertCircle } from 'lucide-react'

const BLOOM_COLORS: Record<string, string> = {
  Remember: 'bg-slate-200 text-slate-700',
  Understand: 'bg-blue-100 text-blue-700',
  Apply: 'bg-green-100 text-green-700',
  Analyze: 'bg-yellow-100 text-yellow-700',
  Evaluate: 'bg-orange-100 text-orange-700',
  Create: 'bg-purple-100 text-purple-700',
}

const DIFFICULTY_COLORS: Record<string, string> = {
  low: 'bg-green-50 text-green-700',
  medium: 'bg-yellow-50 text-yellow-700',
  high: 'bg-red-50 text-red-700',
}

export function LearningTimelineView() {
  const [page, setPage] = useState(1)
  const limit = 15

  const { data, isLoading } = useQuery({
    queryKey: ['student', 'sessions', page],
    queryFn: () => studentApi.getSessions(page, limit),
    select: (r) => r.data,
  })

  const sessions = data?.data ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / limit)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Learning Timeline</h1>
        <p className="text-sm text-muted-foreground mt-1">{total} sessions recorded</p>
      </div>

      {isLoading ? (
        <div className="text-muted-foreground text-sm">Loading sessions…</div>
      ) : sessions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center">
            <MessageSquare className="h-8 w-8 text-muted-foreground" />
            <p className="font-medium">No sessions yet</p>
            <p className="text-sm text-muted-foreground">Start a chat to build your learning history.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="relative space-y-0">
          {sessions.map((session, idx) => (
            <div key={session.id} className="flex gap-4">
              {/* Timeline spine */}
              <div className="flex flex-col items-center">
                <div className="mt-4 h-3 w-3 rounded-full bg-primary shrink-0" />
                {idx < sessions.length - 1 && (
                  <div className="w-px flex-1 bg-border" />
                )}
              </div>

              {/* Card */}
              <Card className="mb-3 flex-1">
                <CardContent className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                    <div className="flex flex-wrap gap-1.5">
                      {session.bloom_level && (
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${BLOOM_COLORS[session.bloom_level] ?? 'bg-muted text-muted-foreground'}`}>
                          {session.bloom_level}
                        </span>
                      )}
                      {session.difficulty_level && (
                        <span className={`rounded px-2 py-0.5 text-xs font-medium ${DIFFICULTY_COLORS[session.difficulty_level] ?? 'bg-muted text-muted-foreground'}`}>
                          {session.difficulty_level}
                        </span>
                      )}
                      {session.subject && (
                        <Badge variant="outline" className="text-xs">{session.subject}</Badge>
                      )}
                    </div>
                    <time className="text-xs text-muted-foreground shrink-0">
                      {new Date(session.created_at).toLocaleString()}
                    </time>
                  </div>

                  <p className="text-sm font-medium line-clamp-2">{session.question}</p>

                  {session.primary_concept && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Concept: <span className="font-medium text-foreground">{session.primary_concept}</span>
                    </p>
                  )}

                  {session.concepts_discussed.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {session.concepts_discussed.map((c) => (
                        <Badge key={c} variant="secondary" className="text-xs">{c}</Badge>
                      ))}
                    </div>
                  )}

                  {session.misconceptions.length > 0 && (
                    <div className="mt-2 flex items-center gap-1.5 rounded-md bg-red-50 px-2 py-1">
                      <AlertCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />
                      <p className="text-xs text-red-700">{session.misconceptions.join(', ')}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}
