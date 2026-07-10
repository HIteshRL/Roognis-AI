import type { Metadata } from 'next'
import { LearningTimelineView } from '@/features/student/components/LearningTimelineView'

export const metadata: Metadata = { title: 'Learning Timeline' }

export default function TimelinePage() {
  return <LearningTimelineView />
}
