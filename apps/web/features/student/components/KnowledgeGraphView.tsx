'use client'

import { useQuery } from '@tanstack/react-query'
import { studentApi, type MasteryRecord } from '@/lib/api/student'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Network } from 'lucide-react'

const LABEL_STYLES = {
  mastered:    { dot: 'bg-green-500',  ring: 'ring-green-200',  text: 'text-green-700' },
  developing:  { dot: 'bg-yellow-500', ring: 'ring-yellow-200', text: 'text-yellow-700' },
  emerging:    { dot: 'bg-orange-400', ring: 'ring-orange-200', text: 'text-orange-700' },
  not_started: { dot: 'bg-slate-300',  ring: 'ring-slate-200',  text: 'text-slate-500' },
}

export function KnowledgeGraphView() {
  const { data: masteryData, isLoading } = useQuery({
    queryKey: ['student', 'mastery'],
    queryFn: () => studentApi.getMastery(),
    select: (r) => r.data,
  })

  const records = masteryData ?? []

  // Group by label tier for visual organisation
  const tiers: MasteryRecord['label'][] = ['mastered', 'developing', 'emerging', 'not_started']
  const grouped = tiers.reduce<Record<string, MasteryRecord[]>>((acc, t) => {
    acc[t] = records.filter((r) => r.label === t)
    return acc
  }, {})

  const tierLabels: Record<string, string> = {
    mastered: 'Mastered',
    developing: 'Developing',
    emerging: 'Emerging',
    not_started: 'Not Started',
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Knowledge Graph</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Concepts grouped by mastery level — {records.length} total
        </p>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading knowledge graph…</div>
      ) : records.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Network className="h-10 w-10 text-muted-foreground" />
            <p className="font-medium">No concepts yet</p>
            <p className="text-sm text-muted-foreground max-w-xs">
              Your knowledge graph builds automatically as you chat. Each question you ask adds concepts here.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Legend */}
          <div className="flex flex-wrap gap-3">
            {tiers.map((t) => {
              const s = LABEL_STYLES[t]
              return (
                <div key={t} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className={`h-2.5 w-2.5 rounded-full ${s.dot}`} />
                  {tierLabels[t]} ({grouped[t].length})
                </div>
              )
            })}
          </div>

          {/* Tier rows */}
          <div className="space-y-6">
            {tiers.map((tier) => {
              const nodes = grouped[tier]
              if (!nodes.length) return null
              const s = LABEL_STYLES[tier]

              return (
                <div key={tier}>
                  <h2 className={`mb-3 text-xs font-semibold uppercase tracking-wider ${s.text}`}>
                    {tierLabels[tier]}
                  </h2>
                  <div className="flex flex-wrap gap-3">
                    {nodes.map((node) => (
                      <div
                        key={node.id}
                        className={`group flex items-center gap-2 rounded-full border bg-background px-3 py-1.5 shadow-sm ring-2 ${s.ring} transition-transform hover:-translate-y-0.5`}
                      >
                        <span className={`h-2 w-2 rounded-full ${s.dot}`} />
                        <span className="text-sm font-medium">{node.concept_name}</span>
                        <span className="text-xs text-muted-foreground">{node.score.toFixed(0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Score distribution mini chart */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Score Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[
                  { range: '85–100', label: 'Mastered', count: records.filter(r => r.score >= 85).length, color: 'bg-green-500' },
                  { range: '60–84', label: 'Developing', count: records.filter(r => r.score >= 60 && r.score < 85).length, color: 'bg-yellow-500' },
                  { range: '30–59', label: 'Emerging', count: records.filter(r => r.score >= 30 && r.score < 60).length, color: 'bg-orange-400' },
                  { range: '0–29', label: 'Not started', count: records.filter(r => r.score < 30).length, color: 'bg-slate-300' },
                ].map((row) => (
                  <div key={row.range} className="flex items-center gap-3 text-sm">
                    <span className="w-14 text-xs text-muted-foreground">{row.range}</span>
                    <div className="flex-1 rounded-full bg-muted h-2 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${row.color}`}
                        style={{ width: `${records.length ? (row.count / records.length) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="w-8 text-right text-xs text-muted-foreground">{row.count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
