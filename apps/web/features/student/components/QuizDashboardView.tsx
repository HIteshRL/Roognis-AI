'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ClipboardCheck, Plus, Trophy, Clock, ChevronRight } from 'lucide-react'
import { studentApi } from '@/lib/api/student'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import type { QuizSummaryDto } from '@roognis/shared'

export function QuizDashboardView() {
  const router = useRouter()
  const qc = useQueryClient()
  const [showGenerate, setShowGenerate] = useState(false)
  const [genSubject, setGenSubject] = useState('')
  const [genChapter, setGenChapter] = useState('')
  const [genCount, setGenCount] = useState(5)
  const [genDifficulty, setGenDifficulty] = useState('adaptive')

  const { data: profile } = useQuery({
    queryKey: ['student-profile'],
    queryFn: () => studentApi.getProfile(),
    select: (r) => r.data,
  })

  const { data: quizzesData, isLoading } = useQuery({
    queryKey: ['student', 'quizzes'],
    queryFn: () => studentApi.getQuizzes(1, 50),
    select: (r) => r.data,
  })

  const { data: historyData } = useQuery({
    queryKey: ['student', 'quiz-history'],
    queryFn: () => studentApi.getQuizHistory(10),
    select: (r) => r.data,
  })

  const quizzes: QuizSummaryDto[] = quizzesData ?? []
  const history = historyData ?? []

  const generate = useMutation({
    mutationFn: () =>
      studentApi.generateQuiz({
        subject: genSubject || null,
        chapter: genChapter || null,
        question_count: genCount,
        difficulty: genDifficulty,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['student', 'quizzes'] })
      toast.success('Quiz generated!')
      setShowGenerate(false)
      if (res.data?.id) {
        router.push(`/student/quiz/${res.data.id}`)
      }
    },
    onError: () => toast.error('Failed to generate quiz'),
  })

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Quizzes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {quizzes.length} quiz{quizzes.length !== 1 ? 'zes' : ''} created
          </p>
        </div>
        <Button onClick={() => setShowGenerate(!showGenerate)}>
          <Plus className="mr-2 h-4 w-4" />
          Generate Quiz
        </Button>
      </div>

      {showGenerate && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Generate New Quiz</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Subject</Label>
                {profile?.subjects && profile.subjects.length > 0 ? (
                  <select
                    value={genSubject}
                    onChange={(e) => setGenSubject(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  >
                    <option value="">All subjects (weak areas)</option>
                    {profile.subjects.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                ) : (
                  <Input
                    placeholder="Leave empty for weak areas"
                    value={genSubject}
                    onChange={(e) => setGenSubject(e.target.value)}
                  />
                )}
              </div>
              <div className="space-y-2">
                <Label>Chapter (optional)</Label>
                <Input
                  placeholder="e.g. Photosynthesis"
                  value={genChapter}
                  onChange={(e) => setGenChapter(e.target.value)}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Questions ({genCount})</Label>
                <input
                  type="range"
                  min={3}
                  max={10}
                  value={genCount}
                  onChange={(e) => setGenCount(Number(e.target.value))}
                  className="w-full"
                />
              </div>
              <div className="space-y-2">
                <Label>Difficulty</Label>
                <select
                  value={genDifficulty}
                  onChange={(e) => setGenDifficulty(e.target.value)}
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="adaptive">Adaptive (based on mastery)</option>
                  <option value="low">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="high">Hard</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowGenerate(false)}>
                Cancel
              </Button>
              <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
                {generate.isPending ? 'Generating...' : 'Generate'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : quizzes.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12">
            <ClipboardCheck className="h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No quizzes yet. Generate your first quiz to test your knowledge!
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {quizzes.map((quiz) => (
            <Card
              key={quiz.id}
              className="cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/student/quiz/${quiz.id}`)}
            >
              <CardContent className="flex items-center justify-between p-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{quiz.title}</span>
                    {quiz.subject && (
                      <Badge variant="secondary" className="text-xs">
                        {quiz.subject}
                      </Badge>
                    )}
                  </div>
                  <div className="mt-1 flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{quiz.question_count} questions</span>
                    <span>{quiz.total_attempts} attempt{quiz.total_attempts !== 1 ? 's' : ''}</span>
                    {quiz.total_attempts > 0 && (
                      <span className="flex items-center gap-1">
                        <Trophy className="h-3 w-3" />
                        Best: {Math.round(quiz.best_score * 100)}%
                      </span>
                    )}
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {history.length > 0 && (
        <>
          <h2 className="text-lg font-semibold">Recent Attempts</h2>
          <div className="space-y-2">
            {history.map((h, i) => (
              <Card
                key={i}
                className="cursor-pointer transition-shadow hover:shadow-md"
                onClick={() => router.push(`/student/quiz/${h.attempt.quiz_id}/results/${h.attempt.id}`)}
              >
                <CardContent className="flex items-center justify-between p-3">
                  <div>
                    <span className="text-sm font-medium">{h.quiz_title}</span>
                    {h.quiz_subject && (
                      <Badge variant="outline" className="ml-2 text-xs">{h.quiz_subject}</Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-20">
                      <Progress value={h.attempt.score * 100} className="h-2" />
                    </div>
                    <span className="min-w-[3rem] text-right text-sm font-medium">
                      {Math.round(h.attempt.score * 100)}%
                    </span>
                    <Badge variant={h.attempt.score >= 0.7 ? 'default' : 'secondary'} className="text-xs">
                      {h.attempt.correct_count}/{h.attempt.total_answered}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
