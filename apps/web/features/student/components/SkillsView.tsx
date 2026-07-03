'use client'

import { useQuery } from '@tanstack/react-query'
import { studentApi } from '@/lib/api/student'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Brain, Zap, AlertCircle } from 'lucide-react'

const BLOOM_ORDER = ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']
const BLOOM_COLORS: Record<string, string> = {
  Remember:  'bg-slate-400',
  Understand: 'bg-blue-400',
  Apply:     'bg-cyan-500',
  Analyze:   'bg-yellow-500',
  Evaluate:  'bg-orange-500',
  Create:    'bg-purple-500',
}

function ProficiencyBar({ skill, proficiency }: { skill: string; proficiency: number }) {
  const color = proficiency >= 80 ? 'bg-green-500' : proficiency >= 60 ? 'bg-yellow-500' : 'bg-blue-500'
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="font-medium">{skill}</span>
        <span className="text-muted-foreground font-mono">{proficiency.toFixed(0)}/100</span>
      </div>
      <div className="h-2 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${proficiency}%` }} />
      </div>
    </div>
  )
}

export function SkillsView() {
  const { data, isLoading } = useQuery({
    queryKey: ['student', 'skills'],
    queryFn: () => studentApi.getSkillProfile(),
    select: (r) => r.data,
  })

  const { data: memoryData } = useQuery({
    queryKey: ['student', 'memory'],
    queryFn: () => studentApi.getConceptMemory(),
    select: (r) => r.data,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Skills & Competencies</h1>
          <p className="text-sm text-muted-foreground mt-1">Analysing your skill profile…</p>
        </div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  const topSkills = data?.top_skills ?? []
  const bloomDist = data?.bloom_distribution ?? {}
  const struggling = memoryData?.filter(m => m.needs_different_approach) ?? []

  const totalBloomSessions = Object.values(bloomDist).reduce((a, b) => a + b, 0)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Skills & Competencies</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Your cognitive skill profile derived from mastery and session patterns
        </p>
      </div>

      {/* Top skill proficiencies */}
      {topSkills.length > 0 ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-500" />
              Top Skills
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {topSkills.map(({ skill, proficiency }) => (
              <ProficiencyBar key={skill} skill={skill} proficiency={proficiency} />
            ))}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground text-sm">
            Start chatting to build your skill profile.
          </CardContent>
        </Card>
      )}

      {/* Bloom taxonomy distribution */}
      {totalBloomSessions > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Brain className="h-4 w-4 text-purple-500" />
              Cognitive Depth Distribution
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {BLOOM_ORDER.map(level => {
              const count = bloomDist[level] ?? 0
              const pct = totalBloomSessions > 0 ? Math.round((count / totalBloomSessions) * 100) : 0
              if (count === 0) return null
              return (
                <div key={level} className="space-y-0.5">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">{level}</span>
                    <span className="text-muted-foreground">{count} sessions ({pct}%)</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded-full ${BLOOM_COLORS[level] ?? 'bg-primary'} transition-all`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </CardContent>
        </Card>
      )}

      {/* Concepts needing different approach */}
      {struggling.length > 0 && (
        <Card className="border-orange-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2 text-orange-700">
              <AlertCircle className="h-4 w-4" />
              Needs Reinforcement
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              These concepts have been explained multiple times with low success — ask for a different explanation approach.
            </p>
            {struggling.map(m => (
              <div key={m.id} className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium text-sm">{m.concept_name}</p>
                  {m.teaching_notes.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Recurring confusion: "{m.teaching_notes[m.teaching_notes.length - 1]}"
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <Badge variant="outline" className="text-xs">{m.times_taught}x taught</Badge>
                  <Badge className="text-xs bg-orange-100 text-orange-800 hover:bg-orange-100">
                    {Math.round(m.success_rate * 100)}% success
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
