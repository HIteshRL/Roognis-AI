'use client'

import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, XCircle, ArrowLeft, RotateCcw, Trophy } from 'lucide-react'
import { studentApi } from '@/lib/api/student'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

interface QuizResultsViewProps {
  quizId: string
  attemptId: string
}

export function QuizResultsView({ quizId, attemptId }: QuizResultsViewProps) {
  const router = useRouter()

  const { data, isLoading } = useQuery({
    queryKey: ['student', 'quiz-results', attemptId],
    queryFn: () => studentApi.getAttemptResults(attemptId),
    select: (r) => r.data,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="h-32 animate-pulse rounded-lg bg-muted" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center gap-4 p-12">
        <p className="text-muted-foreground">Results not found.</p>
        <Button variant="outline" onClick={() => router.push('/student/quiz')}>
          Back to Quizzes
        </Button>
      </div>
    )
  }

  const { attempt, quiz_title, results } = data
  const percentage = Math.round(attempt.score * 100)
  const passed = attempt.score >= 0.7
  const totalTimeSeconds = Math.round(attempt.total_time_ms / 1000)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => router.push('/student/quiz')}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back
        </Button>
      </div>

      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-8">
          <Trophy className={`h-12 w-12 ${passed ? 'text-yellow-500' : 'text-muted-foreground'}`} />
          <h1 className="text-2xl font-bold">{quiz_title}</h1>
          <div className="flex items-center gap-3">
            <div className="w-32">
              <Progress value={percentage} className="h-3" />
            </div>
            <span className="text-2xl font-bold">{percentage}%</span>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <Badge variant={passed ? 'default' : 'secondary'} className="text-sm">
              {passed ? 'Passed' : 'Needs Practice'}
            </Badge>
            <span>
              {attempt.correct_count}/{attempt.total_answered} correct
            </span>
            {totalTimeSeconds > 0 && <span>{totalTimeSeconds}s total</span>}
          </div>
          <div className="flex gap-2 pt-2">
            <Button variant="outline" onClick={() => router.push(`/student/quiz/${quizId}`)}>
              <RotateCcw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>

      <h2 className="text-lg font-semibold">Question Breakdown</h2>

      <div className="space-y-3">
        {results.map((r, i) => (
          <Card key={r.question_id} className={r.is_correct ? 'border-green-200' : 'border-red-200'}>
            <CardContent className="space-y-3 p-4">
              <div className="flex items-start gap-3">
                {r.is_correct ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-500" />
                ) : (
                  <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
                )}
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    <span className="text-muted-foreground">Q{i + 1}.</span>{' '}
                    {r.question_text}
                  </p>
                  <Badge variant="outline" className="mt-1 text-[10px]">
                    {r.concept_name}
                  </Badge>
                </div>
              </div>

              <div className="ml-8 space-y-1">
                {r.options.map((opt) => {
                  const isSelected = opt === r.selected_answer
                  const isCorrect = opt === r.correct_answer
                  let optClass = 'border-border text-muted-foreground'
                  if (isCorrect) optClass = 'border-green-300 bg-green-50 text-green-800 font-medium'
                  else if (isSelected && !r.is_correct) optClass = 'border-red-300 bg-red-50 text-red-800 line-through'
                  return (
                    <div
                      key={opt}
                      className={`rounded-md border px-3 py-1.5 text-xs ${optClass}`}
                    >
                      {opt}
                      {isCorrect && <span className="ml-2 text-green-600">&check;</span>}
                      {isSelected && !r.is_correct && <span className="ml-2 text-red-600">&cross;</span>}
                    </div>
                  )
                })}
              </div>

              {r.explanation && (
                <div className="ml-8 rounded-md bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">
                    <span className="font-medium">Explanation:</span> {r.explanation}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
