'use client'

import { useQuery } from '@tanstack/react-query'
import { studentApi } from '@/lib/api/student'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ArrowRight, BookOpen, Map, Target } from 'lucide-react'

const DIFFICULTY_COLOR: Record<string, string> = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
}

function CoverageBar({ subject, mastered, total, pct }: { subject: string; mastered: number; total: number; pct: number }) {
  const color = pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-blue-500'
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium">{subject}</span>
        <span className="text-muted-foreground">{mastered}/{total} concepts ({pct}%)</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function LearningPathView() {
  const { data, isLoading } = useQuery({
    queryKey: ['student', 'learning-path'],
    queryFn: () => studentApi.getLearningPath(),
    select: (r) => r.data,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Learning Path</h1>
          <p className="text-sm text-muted-foreground mt-1">Computing your personalised path…</p>
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  const frontier = data?.frontier ?? []
  const coverage = data?.coverage ?? {}

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Learning Path</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Concepts you're ready to learn now, and curriculum coverage by subject
        </p>
      </div>

      {/* Curriculum Coverage */}
      {Object.keys(coverage).length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Map className="h-4 w-4 text-blue-500" />
              Curriculum Coverage
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(coverage).map(([subject, stats]) => (
              <CoverageBar
                key={subject}
                subject={subject}
                mastered={stats.mastered}
                total={stats.total}
                pct={stats.coverage_pct}
              />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Frontier — ready to learn */}
      <div>
        <h2 className="text-lg font-semibold mb-3 flex items-center gap-2">
          <Target className="h-4 w-4 text-green-500" />
          Ready to Learn Now
        </h2>
        {frontier.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-center text-muted-foreground text-sm">
              {coverage && Object.keys(coverage).length === 0
                ? 'Set your grade and subjects in your profile to see learning path suggestions.'
                : 'No new concepts are ready right now. Keep mastering your current topics!'}
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {frontier.map((item, idx) => (
              <Card key={item.concept_id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                        {idx + 1}
                      </span>
                      <div className="min-w-0">
                        <p className="font-medium truncate">{item.concept_name}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{item.reason}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {item.subject && (
                        <Badge variant="outline" className="text-xs">{item.subject}</Badge>
                      )}
                      <Badge className="text-xs bg-green-100 text-green-800 hover:bg-green-100">
                        {Math.round(item.readiness_score * 100)}% ready
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
