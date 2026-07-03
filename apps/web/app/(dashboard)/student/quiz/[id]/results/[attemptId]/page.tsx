import type { Metadata } from 'next'
import { QuizResultsView } from '@/features/student/components/QuizResultsView'

export const metadata: Metadata = { title: 'Quiz Results' }

export default async function QuizResultsPage({
  params,
}: {
  params: Promise<{ id: string; attemptId: string }>
}) {
  const { id, attemptId } = await params
  return <QuizResultsView quizId={id} attemptId={attemptId} />
}
