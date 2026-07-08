import type { Metadata } from 'next'
import { QuizDashboardView } from '@/features/student/components/QuizDashboardView'

export const metadata: Metadata = { title: 'Quizzes' }

export default function QuizPage() {
  return <QuizDashboardView />
}
