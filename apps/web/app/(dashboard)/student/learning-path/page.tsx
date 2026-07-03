import type { Metadata } from 'next'
import { LearningPathView } from '@/features/student/components/LearningPathView'

export const metadata: Metadata = { title: 'Learning Path' }

export default function LearningPathPage() {
  return <LearningPathView />
}
