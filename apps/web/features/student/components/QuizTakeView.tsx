'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ArrowLeft, ArrowRight, Send } from 'lucide-react'
import { studentApi } from '@/lib/api/student'
import { useQuizStore } from '@/lib/stores/quiz.store'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import type { QuizQuestionDto } from '@roognis/shared'

interface QuizTakeViewProps {
  quizId: string
}

export function QuizTakeView({ quizId }: QuizTakeViewProps) {
  const router = useRouter()
  const [currentIndex, setCurrentIndex] = useState(0)
  const { responses, questionTimes, recordAnswer, startQuestionTimer, recordQuestionTime, reset } =
    useQuizStore()

  const { data: quizData, isLoading } = useQuery({
    queryKey: ['student', 'quiz', quizId],
    queryFn: () => studentApi.getQuiz(quizId),
    select: (r) => r.data,
  })

  const questions: QuizQuestionDto[] = quizData?.questions ?? []
  const currentQuestion = questions[currentIndex]
  const totalQuestions = questions.length
  const answeredCount = Object.keys(responses).length

  useEffect(() => {
    reset()
  }, [quizId, reset])

  useEffect(() => {
    startQuestionTimer()
  }, [currentIndex, startQuestionTimer])

  const submit = useMutation({
    mutationFn: () => {
      const submissionResponses = questions.map((q) => ({
        question_id: q.id,
        selected_answer: responses[q.id] ?? '',
        time_spent_ms: questionTimes[q.id] ?? 0,
      }))
      return studentApi.submitQuiz(quizId, submissionResponses)
    },
    onSuccess: (res) => {
      toast.success('Quiz submitted!')
      const attemptId = res.data?.id
      reset()
      if (attemptId) {
        router.push(`/student/quiz/${quizId}/results/${attemptId}`)
      } else {
        router.push('/student/quiz')
      }
    },
    onError: () => toast.error('Failed to submit quiz'),
  })

  const handleSelectAnswer = (answer: string) => {
    if (!currentQuestion) return
    recordAnswer(currentQuestion.id, answer)
  }

  const handleNext = () => {
    if (!currentQuestion) return
    recordQuestionTime(currentQuestion.id)
    if (currentIndex < totalQuestions - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  const handlePrev = () => {
    if (currentIndex > 0) {
      recordQuestionTime(currentQuestion?.id ?? '')
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleSubmit = () => {
    if (currentQuestion) {
      recordQuestionTime(currentQuestion.id)
    }
    submit.mutate()
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="h-64 animate-pulse rounded-lg bg-muted" />
      </div>
    )
  }

  if (!quizData || totalQuestions === 0) {
    return (
      <div className="flex flex-col items-center gap-4 p-12">
        <p className="text-muted-foreground">Quiz not found or has no questions.</p>
        <Button variant="outline" onClick={() => router.push('/student/quiz')}>
          Back to Quizzes
        </Button>
      </div>
    )
  }

  const selectedAnswer = currentQuestion ? responses[currentQuestion.id] : undefined
  const isLastQuestion = currentIndex === totalQuestions - 1
  const allAnswered = answeredCount === totalQuestions

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">{quizData.title}</h1>
          <div className="mt-1 flex items-center gap-2">
            {quizData.subject && (
              <Badge variant="secondary" className="text-xs">{quizData.subject}</Badge>
            )}
            {quizData.chapter && (
              <Badge variant="outline" className="text-xs">{quizData.chapter}</Badge>
            )}
          </div>
        </div>
        <span className="text-sm text-muted-foreground">
          {answeredCount}/{totalQuestions} answered
        </span>
      </div>

      <Progress value={((currentIndex + 1) / totalQuestions) * 100} className="h-2" />

      {currentQuestion && (
        <Card>
          <CardContent className="space-y-6 p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <span className="text-xs font-medium text-muted-foreground">
                  Question {currentIndex + 1} of {totalQuestions}
                </span>
                <p className="mt-2 text-lg font-medium">{currentQuestion.question_text}</p>
              </div>
              <div className="flex gap-1">
                <Badge variant="outline" className="text-[10px]">
                  {currentQuestion.bloom_level}
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  {currentQuestion.concept_name}
                </Badge>
              </div>
            </div>

            <div className="space-y-2">
              {currentQuestion.options.map((option) => (
                <button
                  key={option}
                  onClick={() => handleSelectAnswer(option)}
                  className={`w-full rounded-lg border p-3 text-left text-sm transition-all ${
                    selectedAnswer === option
                      ? 'border-primary bg-primary/10 font-medium'
                      : 'border-border hover:border-primary/50 hover:bg-accent/50'
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          onClick={handlePrev}
          disabled={currentIndex === 0}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Previous
        </Button>

        <div className="flex gap-1">
          {questions.map((_, i) => (
            <button
              key={i}
              onClick={() => {
                if (currentQuestion) recordQuestionTime(currentQuestion.id)
                setCurrentIndex(i)
              }}
              className={`h-2 w-2 rounded-full transition-all ${
                i === currentIndex
                  ? 'bg-primary scale-125'
                  : responses[questions[i].id]
                    ? 'bg-primary/50'
                    : 'bg-muted-foreground/30'
              }`}
            />
          ))}
        </div>

        {isLastQuestion ? (
          <Button onClick={handleSubmit} disabled={!allAnswered || submit.isPending}>
            <Send className="mr-2 h-4 w-4" />
            {submit.isPending ? 'Submitting...' : 'Submit Quiz'}
          </Button>
        ) : (
          <Button onClick={handleNext}>
            Next
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
