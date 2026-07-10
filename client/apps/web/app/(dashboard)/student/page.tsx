import type { Metadata } from 'next'
import { StudentDashboardView } from '@/features/student/components/StudentDashboardView'

export const metadata: Metadata = { title: 'Learning Dashboard' }

export default function StudentPage() {
  return <StudentDashboardView />
}
