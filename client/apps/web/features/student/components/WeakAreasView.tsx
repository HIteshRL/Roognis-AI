'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { studentApi, type LearningGap } from '@/lib/api/student'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AlertTriangle, CheckCircle2, Shield } from 'lucide-react'
import { toast } from 'sonner'

const SEVERITY_CONFIG = {
  critical: { color: 'bg-red-100 text-red-700 border-red-200',    dot: 'bg-red-500',    icon: '🚨' },
  high:     { color: 'bg-orange-100 text-orange-700 border-orange-200', dot: 'bg-orange-500', icon: '⚠️' },
  medium:   { color: 'bg-yellow-100 text-yellow-700 border-yellow-200', dot: 'bg-yellow-500', icon: '📌' },
  low:      { color: 'bg-blue-100 text-blue-700 border-blue-200',  dot: 'bg-blue-400',   icon: 'ℹ️' },
}

export function WeakAreasView() {
  const [showResolved, setShowResolved] = useState(false)
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['student', 'gaps', showResolved],
    queryFn: () => studentApi.getGaps(showResolved),
    select: (r) => r.data,
  })

  const resolve = useMutation({
    mutationFn: (gapId: string) => studentApi.resolveGap(gapId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['student', 'gaps'] })
      toast.success('Gap marked as resolved')
    },
    onError: () => toast.error('Failed to resolve gap'),
  })

  const gaps = data ?? []
  const sorted = [...gaps].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 }
    return order[a.severity] - order[b.severity]
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Weak Areas</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Concepts where misconceptions were detected
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowResolved((v) => !v)}
        >
          {showResolved ? 'Hide resolved' : 'Show resolved'}
        </Button>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading gaps…</div>
      ) : sorted.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Shield className="h-10 w-10 text-green-500" />
            <p className="font-medium">No active weak areas</p>
            <p className="text-sm text-muted-foreground">
              {showResolved ? 'No gaps recorded yet.' : 'All detected gaps have been resolved.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {sorted.map((gap) => {
            const cfg = SEVERITY_CONFIG[gap.severity]
            return (
              <Card
                key={gap.id}
                className={`border ${gap.is_resolved ? 'opacity-60' : ''}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1">
                      <span className="mt-0.5 text-base leading-none">{cfg.icon}</span>
                      <div className="flex-1 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-medium text-sm">{gap.concept_name}</p>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-medium border ${cfg.color}`}>
                            {gap.severity}
                          </span>
                          {gap.is_resolved && (
                            <Badge variant="outline" className="text-xs text-green-600">resolved</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{gap.reason}</p>
                        <div className="flex gap-3 text-xs text-muted-foreground">
                          <span>Occurred {gap.occurrence_count}×</span>
                          <span>Confidence: {gap.confidence}</span>
                          <span>{new Date(gap.updated_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>

                    {!gap.is_resolved && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="shrink-0 text-green-600 hover:text-green-700 hover:bg-green-50"
                        onClick={() => resolve.mutate(gap.id)}
                        disabled={resolve.isPending}
                      >
                        <CheckCircle2 className="h-4 w-4 mr-1" />
                        Resolve
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {!isLoading && sorted.length > 0 && (
        <div className="flex gap-3 text-xs text-muted-foreground">
          {(['critical', 'high', 'medium', 'low'] as LearningGap['severity'][]).map((s) => {
            const count = gaps.filter((g) => g.severity === s).length
            if (!count) return null
            return (
              <span key={s} className="flex items-center gap-1">
                <span className={`h-2 w-2 rounded-full ${SEVERITY_CONFIG[s].dot}`} />
                {count} {s}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
