'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Sparkles, X, Check } from 'lucide-react'
import { studentApi, type PsychometricProfile } from '@/lib/api/student'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'

const INTEREST_LABELS: Record<string, string> = {
  science_engineering: 'Science & engineering',
  mathematics: 'Mathematics',
  technology: 'Technology & computing',
  humanities: 'History & humanities',
  arts: 'Art, music & design',
  sports_health: 'Sports & health',
}

const STYLE_LABELS: Record<string, string> = {
  visual: 'Visual',
  verbal: 'Verbal',
  hands_on: 'Hands-on',
  reading: 'Reading',
}

const MOTIVATION_LABELS: Record<string, string> = {
  intrinsic: 'Curiosity-driven',
  extrinsic: 'Goal-driven',
  mixed: 'Balanced',
}

export function PsychometricSurveyCard() {
  const queryClient = useQueryClient()
  const [dismissed, setDismissed] = useState(false)

  const { data: profile } = useQuery({
    queryKey: ['student', 'psychometric', 'profile'],
    queryFn: () => studentApi.getPsychometricProfile(),
    select: (r) => r.data,
  })

  const { data: questions } = useQuery({
    queryKey: ['student', 'psychometric', 'questions'],
    queryFn: () => studentApi.getPsychometricQuestions(5),
    select: (r) => r.data,
  })

  const submit = useMutation({
    mutationFn: (payload: { question_key: string; value: string }) =>
      studentApi.submitPsychometricResponse(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['student', 'psychometric'] })
      // §6 of the system prompt derives from this — keep the profile fresh too.
      queryClient.invalidateQueries({ queryKey: ['student', 'profile'] })
    },
  })

  const pending = questions ?? []
  const complete = (profile?.completeness ?? 0) >= 1
  const hasData = profile ? Object.keys(profile.sources).length > 0 : false

  // Onboarding survey — until dismissed or the bank is exhausted.
  if (!dismissed && pending.length > 0) {
    const q = pending[0]
    return (
      <Card className="border-violet-500/30 bg-violet-500/5">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-violet-500" />
              Help your tutor understand you
            </span>
            <button
              onClick={() => setDismissed(true)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <Progress value={Math.round((profile?.completeness ?? 0) * 100)} className="h-1.5 flex-1" />
            <span className="text-xs text-muted-foreground">
              {Math.round((profile?.completeness ?? 0) * 100)}%
            </span>
          </div>
          <p className="text-sm font-medium">{q.text}</p>
          <div className="flex flex-col gap-2">
            {q.options.map((opt) => (
              <Button
                key={opt.value}
                variant="outline"
                size="sm"
                disabled={submit.isPending}
                onClick={() => submit.mutate({ question_key: q.key, value: opt.value })}
                className="justify-start text-left h-auto py-2 whitespace-normal"
              >
                {opt.label}
              </Button>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Answer a few — your tutor adapts as you go. You can skip anytime.
          </p>
        </CardContent>
      </Card>
    )
  }

  // Assessed dimensions summary — once there is anything to show.
  if (!hasData || !profile) return null

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-violet-500" />
            Motivation & Mindset
          </span>
          {complete ? (
            <Badge variant="secondary" className="gap-1 text-xs">
              <Check className="h-3 w-3" /> Complete
            </Badge>
          ) : (
            <span className="text-xs text-muted-foreground">
              {Math.round(profile.completeness * 100)}% assessed
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm sm:grid-cols-4">
          {profile.motivation_type && (
            <Dimension
              label="Motivation"
              value={MOTIVATION_LABELS[profile.motivation_type] ?? profile.motivation_type}
              source={profile.sources.motivation}
            />
          )}
          {profile.sources.discipline && (
            <Dimension
              label="Self-discipline"
              value={`${Math.round(profile.discipline * 100)}%`}
              source={profile.sources.discipline}
            />
          )}
          {profile.learning_style_preference && (
            <Dimension
              label="Learning style"
              value={STYLE_LABELS[profile.learning_style_preference] ?? profile.learning_style_preference}
              source={profile.sources.learning_style}
            />
          )}
          {profile.sources.confidence && (
            <Dimension
              label="Confidence"
              value={`${Math.round(profile.confidence_self_report * 100)}%`}
              source={profile.sources.confidence}
            />
          )}
          {profile.interests.length > 0 && (
            <div className="col-span-2">
              <p className="text-xs text-muted-foreground">Interests</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {profile.interests.map((i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {INTEREST_LABELS[i] ?? i}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function Dimension({
  label,
  value,
  source,
}: {
  label: string
  value: string
  source?: 'survey' | 'inferred' | 'blended'
}) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
      {source && source !== 'survey' && (
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground/70">
          {source}
        </span>
      )}
    </div>
  )
}
