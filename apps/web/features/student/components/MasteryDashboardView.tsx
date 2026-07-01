'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { studentApi, type MasteryRecord } from '@/lib/api/student'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Search } from 'lucide-react'

const LABEL_CONFIG = {
  mastered:    { color: 'bg-green-100 text-green-700',  bar: 'bg-green-500',  label: 'Mastered' },
  developing:  { color: 'bg-yellow-100 text-yellow-700', bar: 'bg-yellow-500', label: 'Developing' },
  emerging:    { color: 'bg-orange-100 text-orange-700', bar: 'bg-orange-400', label: 'Emerging' },
  not_started: { color: 'bg-slate-100 text-slate-600',  bar: 'bg-slate-300',  label: 'Not Started' },
}

type FilterLabel = 'all' | MasteryRecord['label']

export function MasteryDashboardView() {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<FilterLabel>('all')

  const { data, isLoading } = useQuery({
    queryKey: ['student', 'mastery'],
    queryFn: () => studentApi.getMastery(),
    select: (r) => r.data,
  })

  const records = data ?? []

  const filtered = records.filter((r) => {
    const matchSearch = r.concept_name.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === 'all' || r.label === filter
    return matchSearch && matchFilter
  })

  const counts = {
    mastered: records.filter((r) => r.label === 'mastered').length,
    developing: records.filter((r) => r.label === 'developing').length,
    emerging: records.filter((r) => r.label === 'emerging').length,
    not_started: records.filter((r) => r.label === 'not_started').length,
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mastery Dashboard</h1>
        <p className="text-sm text-muted-foreground mt-1">{records.length} concepts tracked</p>
      </div>

      {/* Summary badges */}
      <div className="flex flex-wrap gap-2">
        {(Object.entries(LABEL_CONFIG) as [MasteryRecord['label'], typeof LABEL_CONFIG['mastered']][]).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setFilter(filter === key ? 'all' : key)}
            className={`rounded-full px-3 py-1 text-sm font-medium transition-all ${
              filter === key ? cfg.color + ' ring-2 ring-offset-1 ring-current' : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {cfg.label}: {counts[key]}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search concepts…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading mastery records…</div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {records.length === 0
              ? 'No concepts tracked yet. Start chatting to build mastery.'
              : 'No concepts match your filter.'}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((r) => {
            const cfg = LABEL_CONFIG[r.label]
            return (
              <Card key={r.id} className="transition-shadow hover:shadow-md">
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-sm leading-tight">{r.concept_name}</p>
                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${cfg.color}`}>
                      {cfg.label}
                    </span>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Score</span>
                      <span className="font-medium text-foreground">{r.score.toFixed(1)} / 100</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${cfg.bar}`}
                        style={{ width: `${r.score}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{r.interaction_count} interaction{r.interaction_count !== 1 ? 's' : ''}</span>
                    <span>{new Date(r.last_updated).toLocaleDateString()}</span>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
