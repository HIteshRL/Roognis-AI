'use client'

import { useQuery } from '@tanstack/react-query'
import { studentApi } from '@/lib/api/student'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart3 } from 'lucide-react'

const BLOOM_ORDER = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']
const BLOOM_COLORS = [
  'bg-slate-400', 'bg-blue-400', 'bg-green-400',
  'bg-yellow-400', 'bg-orange-400', 'bg-purple-500',
]

export function StatisticsView() {
  const { data: analyticsData, isLoading } = useQuery({
    queryKey: ['student', 'analytics'],
    queryFn: () => studentApi.getAnalytics(),
    select: (r) => r.data,
  })

  const { data: masteryData } = useQuery({
    queryKey: ['student', 'mastery'],
    queryFn: () => studentApi.getMastery(),
    select: (r) => r.data,
  })

  const analytics = analyticsData
  const mastery = masteryData ?? []

  const bloomCounts = analytics?.recent_bloom_levels ?? {}
  const maxBloom = Math.max(...Object.values(bloomCounts), 1)

  const topMastered = [...mastery].sort((a, b) => b.score - a.score).slice(0, 5)
  const weakest = [...mastery].filter((r) => r.score > 0).sort((a, b) => a.score - b.score).slice(0, 5)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Statistics</h1>
        <p className="text-sm text-muted-foreground mt-1">A detailed view of your learning patterns</p>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading statistics…</div>
      ) : (
        <>
          {/* Bloom's taxonomy distribution */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <BarChart3 className="h-4 w-4" />
                Bloom's Taxonomy — Last 7 Days
              </CardTitle>
            </CardHeader>
            <CardContent>
              {Object.keys(bloomCounts).length === 0 ? (
                <p className="text-sm text-muted-foreground">No sessions in the last 7 days.</p>
              ) : (
                <div className="space-y-3">
                  {BLOOM_ORDER.map((level, i) => {
                    const count = bloomCounts[level] ?? 0
                    const pct = Math.round((count / maxBloom) * 100)
                    return (
                      <div key={level} className="flex items-center gap-3 text-sm">
                        <span className="w-20 shrink-0 text-xs text-muted-foreground">{level}</span>
                        <div className="flex-1 rounded-full bg-muted h-2.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all ${BLOOM_COLORS[i]}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="w-6 text-right text-xs text-muted-foreground">{count}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Summary numbers */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Overall Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { label: 'Total sessions', value: analytics?.total_sessions ?? 0 },
                  { label: 'Concepts encountered', value: analytics?.total_concepts_encountered ?? 0 },
                  { label: 'Average mastery', value: `${analytics?.average_mastery?.toFixed(1) ?? 0} / 100` },
                  { label: 'Active gaps', value: analytics?.active_gaps ?? 0 },
                  { label: 'Critical gaps', value: analytics?.critical_gaps ?? 0 },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between text-sm">
                    <span className="text-muted-foreground">{row.label}</span>
                    <span className="font-semibold">{row.value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Mastery breakdown */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Mastery Breakdown</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {[
                  { label: 'Mastered (≥85)', value: analytics?.mastered_count ?? 0, color: 'bg-green-500' },
                  { label: 'Developing (60–84)', value: analytics?.developing_count ?? 0, color: 'bg-yellow-500' },
                  { label: 'Emerging (30–59)', value: analytics?.emerging_count ?? 0, color: 'bg-orange-400' },
                  { label: 'Not started (<30)', value: analytics?.not_started_count ?? 0, color: 'bg-slate-300' },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between gap-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className={`h-2.5 w-2.5 rounded-full ${row.color}`} />
                      <span className="text-muted-foreground">{row.label}</span>
                    </div>
                    <span className="font-semibold">{row.value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Top concepts */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Top 5 Strongest</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {topMastered.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No concepts yet.</p>
                ) : (
                  topMastered.map((r, i) => (
                    <div key={r.id} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground w-4">{i + 1}.</span>
                        <span className="truncate max-w-[160px]">{r.concept_name}</span>
                      </div>
                      <span className="font-semibold text-green-600">{r.score.toFixed(0)}</span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Weakest */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Top 5 Weakest</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {weakest.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No concepts yet.</p>
                ) : (
                  weakest.map((r, i) => (
                    <div key={r.id} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground w-4">{i + 1}.</span>
                        <span className="truncate max-w-[160px]">{r.concept_name}</span>
                      </div>
                      <span className="font-semibold text-orange-600">{r.score.toFixed(0)}</span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
