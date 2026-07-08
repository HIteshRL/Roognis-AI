import type { Metadata } from 'next'
import { QuizTakeView } from '@/features/student/components/QuizTakeView'

export const metadata: Metadata = { title: 'Take Quiz' }

export default async function QuizTakePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  return <QuizTakeView quizId={id} />
}
