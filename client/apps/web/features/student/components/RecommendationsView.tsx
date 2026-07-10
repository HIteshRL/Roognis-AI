'use client'

import { useQuery } from '@tanstack/react-query'
import { studentApi } from '@/lib/api/student'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Lightbulb, MessageSquare, ArrowRight } from 'lucide-react'
import Link from 'next/link'

function ReadinessBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-500' : 'bg-orange-400'
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>Readiness</span>
        <span className="font-medium text-foreground">{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export function RecommendationsView() {
  const { data, isLoading } = useQuery({
    queryKey: ['student', 'recommendations'],
    queryFn: () => studentApi.getRecommendations(),
    select: (r) => r.data,
  })

  const { data: profileData } = useQuery({
    queryKey: ['student', 'profile'],
    queryFn: () => studentApi.getProfile(),
    select: (r) => r.data,
  })

  const recs = data ?? []
  const hasProfile = profileData?.grade && profileData?.subjects?.length

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Recommendations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Next best topics based on your mastery and knowledge graph
        </p>
      </div>

      {!hasProfile && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="flex items-center justify-between p-4">
            <p className="text-sm text-yellow-800">
              Set your grade and subjects in your profile to get personalised recommendations.
            </p>
            <Link href="/student/profile-setup">
              <Button size="sm" variant="outline" className="shrink-0">Set up profile</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Generating recommendations…</div>
      ) : recs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Lightbulb className="h-10 w-10 text-muted-foreground" />
            <p className="font-medium">No recommendations yet</p>
            <p className="text-sm text-muted-foreground max-w-sm">
              Recommendations appear once you've chatted about a few topics and your knowledge graph has been built.
            </p>
            <Link href="/chat">
              <Button size="sm" variant="outline" className="mt-2">
                <MessageSquare className="mr-2 h-4 w-4" />
                Start a chat
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {recs.map((rec, idx) => (
            <Card key={rec.concept_id} className="flex flex-col transition-shadow hover:shadow-md">
              <CardContent className="flex flex-1 flex-col gap-3 p-5">
                {/* Rank badge */}
                <div className="flex items-start justify-between">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">
                    {idx + 1}
                  </span>
                  <div className="flex flex-wrap gap-1 justify-end">
                    {rec.subject && <Badge variant="secondary" className="text-xs">{rec.subject}</Badge>}
                    {rec.chapter && <Badge variant="outline" className="text-xs">{rec.chapter}</Badge>}
                  </div>
                </div>

                <div>
                  <p className="font-semibold text-base">{rec.concept_name}</p>
                  <p className="text-xs text-muted-foreground mt-1">{rec.reason}</p>
                </div>

                <ReadinessBar score={rec.readiness_score} />

                <Link href={`/chat?topic=${encodeURIComponent(rec.concept_name)}`} className="mt-auto">
                  <Button size="sm" className="w-full">
                    Study this
                    <ArrowRight className="ml-2 h-3.5 w-3.5" />
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
