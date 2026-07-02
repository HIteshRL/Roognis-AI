'use client'

import { useQuery } from '@tanstack/react-query'
import { studentApi } from '@/lib/api/student'
import { Brain, BookOpen, AlertTriangle, TrendingUp, Zap, Target, Activity, Flame } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import Link from 'next/link'

export function StudentDashboardView() {
  const { data: analyticsRes, isLoading } = useQuery({
    queryKey: ['student', 'analytics'],
    queryFn: () => studentApi.getAnalytics(),
    select: (r) => r.data,
  })

  const { data: profileRes } = useQuery({
    queryKey: ['student', 'profile'],
    queryFn: () => studentApi.getProfile(),
    select: (r) => r.data,
  })

  const { data: recsRes } = useQuery({
    queryKey: ['student', 'recommendations'],
    queryFn: () => studentApi.getRecommendations(),
    select: (r) => r.data,
  })

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading your learning dashboard…</div>
      </div>
    )
  }

  const analytics = analyticsRes
  const profile = profileRes
  const recs = recsRes ?? []

  const masteryPct = analytics
    ? Math.round(
        ((analytics.mastered_count + analytics.developing_count * 0.6 + analytics.emerging_count * 0.3) /
          Math.max(analytics.total_concepts_encountered, 1)) *
          100
      )
    : 0

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Learning Dashboard</h1>
        {profile && (
          <p className="text-sm text-muted-foreground mt-1">
            {profile.grade && `Grade ${profile.grade}`}
            {profile.grade && profile.subjects.length > 0 && ' · '}
            {profile.subjects.join(', ')}
            {profile.current_chapter && ` · ${profile.current_chapter}`}
          </p>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard icon={BookOpen} label="Sessions" value={analytics?.total_sessions ?? 0} color="text-blue-500" />
        <StatCard icon={Brain} label="Concepts" value={analytics?.total_concepts_encountered ?? 0} color="text-purple-500" />
        <StatCard icon={Target} label="Mastered" value={analytics?.mastered_count ?? 0} color="text-green-500" />
        <StatCard icon={TrendingUp} label="Developing" value={analytics?.developing_count ?? 0} color="text-yellow-500" />
        <StatCard icon={AlertTriangle} label="Gaps" value={analytics?.active_gaps ?? 0} color="text-orange-500" />
        <StatCard icon={Zap} label="Critical" value={analytics?.critical_gaps ?? 0} color="text-red-500" />
      </div>

      {/* Overall mastery bar */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Overall Progress</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Weighted mastery</span>
            <span className="font-semibold">{masteryPct}%</span>
          </div>
          <Progress value={masteryPct} className="h-2" />
          <div className="flex gap-4 pt-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-500 inline-block" />Mastered: {analytics?.mastered_count ?? 0}</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-yellow-500 inline-block" />Developing: {analytics?.developing_count ?? 0}</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-orange-400 inline-block" />Emerging: {analytics?.emerging_count ?? 0}</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-muted inline-block" />Not started: {analytics?.not_started_count ?? 0}</span>
          </div>
        </CardContent>
      </Card>

      {/* Learner Intelligence card */}
      {profile?.behavioral_signals && profile.behavioral_signals.total_sessions >= 3 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="h-4 w-4 text-violet-500" />
              Learner Intelligence
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
              {profile.behavioral_signals.preferred_bloom_level && (
                <div>
                  <p className="text-xs text-muted-foreground">Operates at</p>
                  <p className="font-medium">{profile.behavioral_signals.preferred_bloom_level}</p>
                </div>
              )}
              {profile.behavioral_signals.struggle_bloom_level && (
                <div>
                  <p className="text-xs text-muted-foreground">Struggles at</p>
                  <p className="font-medium text-orange-600">{profile.behavioral_signals.struggle_bloom_level}</p>
                </div>
              )}
              <div>
                <p className="text-xs text-muted-foreground">Learning style</p>
                <p className="font-medium capitalize">{profile.behavioral_signals.response_pattern}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Complexity</p>
                <p className="font-medium capitalize">{profile.behavioral_signals.question_complexity_trend}</p>
              </div>
              {profile.behavioral_signals.engagement_streak > 0 && (
                <div className="flex items-center gap-1.5">
                  <Flame className="h-3.5 w-3.5 text-orange-500" />
                  <div>
                    <p className="text-xs text-muted-foreground">Streak</p>
                    <p className="font-medium">{profile.behavioral_signals.engagement_streak} days</p>
                  </div>
                </div>
              )}
              <div>
                <p className="text-xs text-muted-foreground">Frequency</p>
                <p className="font-medium">{profile.behavioral_signals.sessions_per_day.toFixed(1)}/day</p>
              </div>
              {profile.behavioral_signals.strengths.length > 0 && (
                <div className="col-span-2">
                  <p className="text-xs text-muted-foreground">Strengths</p>
                  <p className="font-medium truncate">{profile.behavioral_signals.strengths.slice(0, 3).join(', ')}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Recent concepts */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Recent Concepts</CardTitle>
          </CardHeader>
          <CardContent>
            {analytics?.recent_concepts?.length ? (
              <div className="flex flex-wrap gap-2">
                {analytics.recent_concepts.map((c) => (
                  <Badge key={c} variant="secondary">{c}</Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Start a chat session to begin tracking concepts.</p>
            )}
          </CardContent>
        </Card>

        {/* Top recommendations */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-base">
              <span>Up Next</span>
              <Link href="/student/recommendations" className="text-xs text-primary hover:underline">View all</Link>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {recs.length ? (
              <div className="space-y-2">
                {recs.slice(0, 3).map((r) => (
                  <div key={r.concept_id} className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2">
                    <div>
                      <p className="text-sm font-medium">{r.concept_name}</p>
                      <p className="text-xs text-muted-foreground">{r.subject ?? 'General'}</p>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {Math.round(r.readiness_score * 100)}% ready
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Set your grade and subjects in your profile to get recommendations.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { href: '/student/mastery', label: 'Mastery', desc: 'Concept scores' },
          { href: '/student/gaps', label: 'Weak Areas', desc: 'Misconceptions' },
          { href: '/student/timeline', label: 'Timeline', desc: 'Session history' },
          { href: '/student/graph', label: 'Knowledge Map', desc: 'Concept graph' },
        ].map((item) => (
          <Link key={item.href} href={item.href}>
            <Card className="cursor-pointer transition-colors hover:bg-accent/50">
              <CardContent className="p-4">
                <p className="font-medium text-sm">{item.label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: number
  color: string
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <Icon className={`h-4 w-4 ${color} mb-2`} />
        <p className="text-2xl font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </CardContent>
    </Card>
  )
}
